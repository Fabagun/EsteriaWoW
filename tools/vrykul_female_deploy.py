"""Install the checked Vrykul/Ogre package with backups and a worldserver-only recreation."""

import argparse
from datetime import datetime
import hashlib
import os
from pathlib import Path
import shutil
import subprocess

import vrykul_female_pack as v
import mechagnome_race_pack as db
from test_vrykul_female_pack import check

p = v.p
NATIVE = v.STAGE/'native/EsteriaAppearance.dll'
ROLLBACK_IMAGE = 'esteria-worldserver:pre-vrykul-female-20261007'
IMAGE = 'acore/ac-wotlk-worldserver:master'
APPEARANCE = ('SELECT guid,race,gender,skin,face,hairStyle,hairColor,facialStyle,extraAppearance '
              'FROM characters ORDER BY guid;')
SOURCE_FILES = ('client-customization/NativeAppearance.cpp', 'client-customization/HaranirMaterials.inl',
                'src/server/shared/CreatureAppearance.h', 'src/server/shared/SharedDefines.h')


def files():
    report = p.load_json(v.STAGE/'report.json')
    result = {relative: v.STAGE/'client'/relative for relative in report['archives']}
    result.update({name: v.STAGE/name for name in report['catalog_after']})
    result['EsteriaAppearance.dll'] = NATIVE
    return result


def fingerprint():
    return {table: hashlib.sha256(db.sql(f'SELECT * FROM `{table}` WHERE `{key}`<>61 '
                                        'ORDER BY 1,2,3;').encode()).hexdigest()
            for table, key in v.old.WORLD.items()}


def preflight():
    report = p.load_json(v.STAGE/'report.json')
    processes = subprocess.check_output(['tasklist', '/FO', 'CSV', '/NH'], text=True).lower()
    if any(name in processes for name in ('wow.exe', 'eclipse.exe', 'mpqeditor.exe')):
        raise RuntimeError('Close WoW/Eclipse/MPQEditor before installing the checked package')
    assert p.sha256(p.CLIENT_DEFAULT/'Wow.exe') == report['exe_sha256']
    for relative, expected in report['before'].items():
        assert p.sha256(p.CLIENT_DEFAULT/relative) == expected, relative + ' baseline changed'
    assert not (p.CLIENT_DEFAULT/v.ASSET).exists()
    for name, expected in report['catalog_before'].items():
        assert p.sha256(p.CLIENT_DEFAULT/name) == expected, name + ' baseline changed'
    for name, expected in report['server_before'].items():
        assert p.sha256(p.SERVER_DBC_ROOT/(name+'.dbc')) == expected, name + ' server baseline changed'
    assert p.sha256(v.MIGRATION) == report['migration_sha256']
    for table, key in v.old.WORLD.items():
        assert db.sql(f'SELECT COUNT(*) FROM `{table}` WHERE `{key}`=61;').strip() == '0', table
    assert db.sql('SELECT COUNT(*) FROM characters WHERE race=61 OR (race IN (56,57) AND gender=1);',
                  'acore_characters').strip() == '0'
    assert db.sql('SELECT COUNT(*) FROM chrraces_dbc WHERE ID IN (56,57);').strip() == '0'
    assert db.sql('SELECT COUNT(*) FROM creaturemodeldata_dbc WHERE ID=120069;').strip() == '0'
    assert db.sql('SELECT COUNT(*) FROM creaturedisplayinfo_dbc WHERE ID=60060;').strip() == '0'
    assert db.sql(f"SELECT COUNT(*) FROM updates WHERE name='{v.MIGRATION.name}';").strip() == '0'
    checks = p.load_json(v.STAGE/'native-checks.json')
    assert checks['all_passed'] and p.sha256(NATIVE) == checks['dll_sha256']
    assert {name: p.sha256(p.ROOT/name) for name in SOURCE_FILES} == checks['source_files']
    subprocess.run(['docker', 'image', 'inspect', IMAGE],
                   capture_output=True, check=True)


def backup():
    check()
    preflight()
    root = Path('C:/Users/Zach/.codex/backups')/('vrykul-female-ogre-'+datetime.now().strftime('%Y%m%d-%H%M%S'))
    root.mkdir(parents=True)
    report = {'backup': str(root), 'before': {}, 'after': {}, 'server_before': {}, 'server_after': {},
              'files': {relative: str(source) for relative, source in files().items()},
              'world': fingerprint(), 'migration_sha256': p.sha256(v.MIGRATION)}
    report['old_image'] = subprocess.check_output(['docker', 'inspect', 'ac-worldserver',
        '--format', '{{.Image}}'], text=True).strip()
    subprocess.run(['docker', 'image', 'tag', report['old_image'], ROLLBACK_IMAGE], check=True)
    for relative, source in files().items():
        target = p.CLIENT_DEFAULT/relative
        report['before'][relative] = p.sha256(target) if target.exists() else None
        report['after'][relative] = p.sha256(source)
        if target.exists():
            saved = root/'client'/relative
            saved.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(target, saved)
            assert p.sha256(saved) == report['before'][relative]
    for name in v.SERVER:
        source = p.SERVER_DBC_ROOT/(name+'.dbc')
        target = root/'server'/source.name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        report['server_before'][name] = p.sha256(source)
        report['server_after'][name] = p.sha256(v.STAGE/'server'/source.name)
        assert p.sha256(target) == report['server_before'][name]
    (root/'characters.tsv').write_text(db.sql(APPEARANCE, 'acore_characters'), encoding='utf-8')
    shutil.copy2(v.MIGRATION, root/v.MIGRATION.name)
    rollback = '\n'.join(f'DELETE FROM `{table}` WHERE `{key}`=61;' for table, key in v.old.WORLD.items())
    rollback += f"\nDELETE FROM `updates` WHERE `name`='{v.MIGRATION.name}';\n"
    (root/'rollback.sql').write_text(rollback, encoding='utf-8', newline='\n')
    v.old.save(root/'install-plan.json', report)
    v.old.save(v.STAGE/'install-plan.json', report)
    print('SHA-256 VERIFIED BACKUP', root, flush=True)


def install():
    preflight()
    build = p.load_json(v.STAGE/'worldserver-build.json')
    assert build['success']
    image = subprocess.check_output(['docker', 'image', 'inspect', IMAGE, '--format', '{{.Id}}'],
                                    text=True).strip()
    assert image == build['image_id'], 'worldserver image differs from the successful build'
    assert build['headers'] == {name: p.sha256(p.ROOT/name) for name in SOURCE_FILES if name.startswith('src/')}
    report = p.load_json(v.STAGE/'install-plan.json')
    root = Path(report['backup'])
    assert fingerprint() == report['world'], 'world startup data changed since backup'
    for relative, before in report['before'].items():
        live = p.CLIENT_DEFAULT/relative
        assert (p.sha256(live) if live.exists() else None) == before
        assert p.sha256(Path(report['files'][relative])) == report['after'][relative]
    for name, expected in report['server_before'].items():
        assert p.sha256(p.SERVER_DBC_ROOT/(name+'.dbc')) == expected
    characters = db.sql(APPEARANCE, 'acore_characters')
    (root/'characters-at-install.tsv').write_text(characters, encoding='utf-8')
    receipt = hashlib.sha1(v.MIGRATION.read_bytes()).hexdigest().upper()
    subprocess.run(['docker', 'stop', 'ac-worldserver'], check=True)
    try:
        db.sql('START TRANSACTION;\n'+v.MIGRATION.read_text()+
            f"\nINSERT INTO updates (name,hash,state) VALUES ('{v.MIGRATION.name}','{receipt}','PENDING');\nCOMMIT;")
        for relative, source in report['files'].items():
            target = p.CLIENT_DEFAULT/relative
            temporary = target.with_suffix(target.suffix+'.vrykul-next')
            shutil.copy2(source, temporary)
            assert p.sha256(temporary) == report['after'][relative]
            os.replace(temporary, target)
        for name in v.SERVER:
            target = p.SERVER_DBC_ROOT/(name+'.dbc')
            shutil.copy2(v.STAGE/'server'/target.name, target)
            assert p.sha256(target) == report['server_after'][name]
        assert fingerprint() == report['world'], 'unrelated world data changed'
        assert db.sql(APPEARANCE, 'acore_characters') == characters, 'saved character appearances changed'
        subprocess.run(['docker', 'compose', 'up', '-d', '--no-deps', '--force-recreate', 'ac-worldserver'],
                       check=True)
    except BaseException:
        for relative, before in report['before'].items():
            target = p.CLIENT_DEFAULT/relative
            if before is not None:
                shutil.copy2(root/'client'/relative, target)
            elif target.exists():
                assert p.CLIENT_DEFAULT.resolve() in target.resolve().parents
                target.unlink()
        for name in v.SERVER:
            shutil.copy2(root/'server'/(name+'.dbc'), p.SERVER_DBC_ROOT/(name+'.dbc'))
        db.sql('START TRANSACTION;\n'+(root/'rollback.sql').read_text()+'\nCOMMIT;')
        subprocess.run(['docker', 'image', 'tag', report['old_image'], IMAGE], check=True)
        subprocess.run(['docker', 'compose', 'up', '-d', '--no-deps', '--force-recreate', 'ac-worldserver'],
                       check=True)
        raise
    report.update(status='installed_awaiting_live_client_test', receipt=receipt)
    v.old.save(root/'installed.json', report)
    v.old.save(v.STAGE/'installed.json', report)
    print('INSTALLED female Vrykul and Alliance Ogre', root, flush=True)


def verify():
    report = p.load_json(v.STAGE/'installed.json')
    build = p.load_json(v.STAGE/'worldserver-build.json')
    image = subprocess.check_output(['docker', 'inspect', 'ac-worldserver', '--format', '{{.Image}}'],
                                   text=True).strip()
    assert image == build['image_id'], 'running worldserver image differs from the checked build'
    assert p.sha256(p.CLIENT_DEFAULT/'Wow.exe') == p.load_json(v.STAGE/'report.json')['exe_sha256']
    for relative, expected in report['after'].items():
        assert p.sha256(p.CLIENT_DEFAULT/relative) == expected, relative
    for relative, expected in report['before'].items():
        if expected is not None:
            assert p.sha256(Path(report['backup'])/'client'/relative) == expected
    output = subprocess.check_output(['docker', 'exec', 'ac-worldserver', 'sha256sum',
        *['/azerothcore/env/dist/data/dbc/'+name+'.dbc' for name in v.SERVER]], text=True)
    mounted = {Path(line.split()[1]).stem: line.split()[0] for line in output.splitlines()}
    assert mounted == report['server_after']
    for name, expected in report['server_after'].items():
        assert p.sha256(p.SERVER_DBC_ROOT/(name+'.dbc')) == expected
    rows = db.sql('SELECT ID,Flags,FactionID,MaleDisplayId,FemaleDisplayId,ClientFilestring,Alliance '
                  'FROM chrraces_dbc WHERE ID=61; SELECT COUNT(*) FROM playercreateinfo WHERE race=61; '
                  'SELECT spell FROM custom_race_start_spell WHERE race=61; '
                  'SELECT skill FROM custom_race_start_skill WHERE race=61;')
    assert rows.splitlines() == ['61\t14\t1\t60053\t60054\tOgreAlliance\t0', '10', '668', '98']
    races = p.RawWdbc((p.SERVER_DBC_ROOT/'ChrRaces.dbc').read_bytes())
    for race in (56, 57):
        row = next(r for r in races.records if p._value(r, 0) == race)
        assert p._value(row, 20) == v.DISPLAY_ID
    receipt = db.sql(f"SELECT hash FROM updates WHERE name='{v.MIGRATION.name}';").strip()
    assert receipt == report['receipt']
    report.update(verified_client_files=True, verified_server_mounts=True, verified_database=True,
                  live_client_test=False)
    v.old.save(v.STAGE/'verified-install.json', report)
    print('VERIFIED female Vrykul, Alliance Ogre61/Common, ten starts, mounted DBCs and rollback hashes', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('preflight', 'backup', 'install', 'verify'))
    globals()[parser.parse_args().action]()
