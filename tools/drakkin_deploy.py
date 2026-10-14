"""Guarded install of the checked Drakkin package after explicitly authorized builds."""

import argparse
from datetime import datetime
import hashlib
from pathlib import Path
import shutil
import subprocess

import drakkin_race_pack as k
import creature_race_pack as c
import mechagnome_race_pack as db
from test_drakkin_race_pack import check

NATIVE = k.ROOT / 'native-build/EsteriaAppearance.dll'
TABLES = {**c.WORLD_TABLES, 'chrraces_dbc': 'ID'}
APPEARANCE = ('SELECT guid,race,gender,skin,face,hairStyle,hairColor,facialStyle,extraAppearance '
              'FROM characters ORDER BY guid;')


def inspect(name, field):
    return subprocess.check_output(['docker', 'inspect', name, '--format', field], text=True).strip()


def raw_sql(query, database='acore_world'):
    # Full-table reads can contain legacy non-UTF8 bytes; decode defensively.
    command = ['docker', 'exec', '-i', 'ac-database', 'sh', '-c',
               'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql -uroot --batch --skip-column-names ' + database]
    return subprocess.run(command, input=query.encode(), capture_output=True,
                          check=True).stdout.decode('utf-8', 'replace')


def fingerprint():
    return {table: hashlib.sha256('\n'.join(sorted(raw_sql(
        f'SELECT * FROM `{table}` WHERE `{field}` NOT IN (66,67);').splitlines())).encode()).hexdigest()
        for table, field in TABLES.items()}


def files():
    report = k.p.load_json(k.STAGE / 'report.json')
    return {**{name: k.STAGE / 'client' / name for name in report['archives']},
            **{name: k.STAGE / name for name in report['catalogs']}, 'EsteriaAppearance.dll': NATIVE}


def preflight():
    check()
    report = k.p.load_json(k.STAGE / 'report.json')
    processes = subprocess.check_output(['tasklist', '/FO', 'CSV', '/NH'], text=True).lower()
    assert not any(name in processes for name in ('wow.exe', 'eclipse.exe', 'mpqeditor.exe')), 'Close clients/editors'
    assert not (k.p.CLIENT_DEFAULT / k.ASSET).exists(), 'Asset MPQ already exists'
    for name in k.tables_lib.SERVER_TABLES:
        assert k.p.sha256(k.p.SERVER_DBC_ROOT / (name + '.dbc')) == \
            k.p.sha256(k.STAGE / 'baseline-server' / (name + '.dbc')), 'Server DBC changed: ' + name
    for table, field in TABLES.items():
        assert db.sql(f'SELECT COUNT(*) FROM `{table}` WHERE `{field}` IN (66,67);').strip() == '0', table
    assert db.sql('SELECT COUNT(*) FROM characters WHERE race IN (66,67);', 'acore_characters').strip() == '0'
    assert db.sql(f"SELECT COUNT(*) FROM updates WHERE name='{k.MIGRATION.name}';").strip() == '0'
    for table, ids in (('creaturemodeldata_dbc', '(120073,120074)'),
                       ('creaturedisplayinfo_dbc', '(60064,60065)')):
        assert db.sql(f'SELECT COUNT(*) FROM `{table}` WHERE ID IN {ids};').strip() == '0'
    build = k.p.load_json(k.STAGE / 'native-checks.json')
    assert build['all_passed'] and k.p.sha256(NATIVE) == build['dll_sha256']
    for name, expected in build['source_files'].items():
        assert k.p.sha256(k.p.ROOT / name) == expected, 'Native source changed: ' + name
    for name, expected in build['catalog_hashes'].items():
        target = k.STAGE / name if name in report['catalogs'] else k.p.CLIENT_DEFAULT / name
        assert k.p.sha256(target) == expected, 'Native harness catalog changed: ' + name
    server = k.p.load_json(k.STAGE / 'server-build.json')
    assert server['passed'] and server['image'] == subprocess.check_output(
        ['docker', 'image', 'inspect', server['tag'], '--format', '{{.Id}}'], text=True).strip()
    for name, expected in server['source_files'].items():
        assert k.p.sha256(k.p.ROOT / name) == expected, 'Server source changed: ' + name
    print('PREFLIGHT PASS', flush=True)


def backup():
    preflight()
    root = Path('G:/EsteriaBackups') / ('Drakkin-' + datetime.now().strftime('%Y%m%d-%H%M%S'))
    root.mkdir(parents=True)
    plan = {'backup': str(root), 'files': {name: str(path) for name, path in files().items()},
            'before': {}, 'install_hashes': {}, 'server_before': {}, 'server_after': {},
            'world_fingerprints': fingerprint(), 'prior_world_image': inspect('ac-worldserver', '{{.Image}}')}
    subprocess.run(['docker', 'tag', plan['prior_world_image'],
                    'esteria-drakkin-rollback:' + root.name], check=True)
    for name, path in files().items():
        live = k.p.CLIENT_DEFAULT / name
        plan['before'][name] = k.p.sha256(live) if live.exists() else None
        plan['install_hashes'][name] = k.p.sha256(path)
        if live.exists():
            target = root / 'client' / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(live, target)
            assert k.p.sha256(target) == plan['before'][name]
    for name in k.tables_lib.SERVER_TABLES:
        live = k.p.SERVER_DBC_ROOT / (name + '.dbc')
        target = root / 'server-dbc' / live.name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(live, target)
        plan['server_before'][name] = k.p.sha256(live)
        plan['server_after'][name] = k.p.sha256(k.STAGE / 'server/dbc' / live.name)
        assert k.p.sha256(target) == plan['server_before'][name]
    rollback = '\n'.join(f'DELETE FROM `{table}` WHERE `{field}` IN (66,67);' for table, field in TABLES.items())
    rollback += f"\nDELETE FROM `updates` WHERE `name`='{k.MIGRATION.name}';\n"
    (root / 'rollback-world.sql').write_text(rollback, encoding='utf-8', newline='\n')
    (root / 'appearance-before.tsv').write_text(db.sql(APPEARANCE, 'acore_characters'), encoding='utf-8')
    shutil.copy2(k.MIGRATION, root / k.MIGRATION.name)
    plan['migration_sha256'] = k.p.sha256(k.MIGRATION)
    plan['backup_hashes'] = {str(path.relative_to(root)): k.p.sha256(path)
                             for path in root.rglob('*') if path.is_file()}
    k.save(root / 'install-plan.json', plan)
    k.save(k.STAGE / 'install-plan.json', plan)
    print('HASH-VERIFIED BACKUP', root, flush=True)


def install():
    preflight()
    assert inspect('ac-worldserver', '{{.State.Running}}') == 'false', 'Stop only ac-worldserver before install'
    plan = k.p.load_json(k.STAGE / 'install-plan.json')
    root = Path(plan['backup'])
    for name, expected in plan['backup_hashes'].items():
        assert k.p.sha256(root / name) == expected, 'Backup changed: ' + name
    for name, expected in plan['before'].items():
        live = k.p.CLIENT_DEFAULT / name
        assert (k.p.sha256(live) if live.exists() else None) == expected
        assert k.p.sha256(Path(plan['files'][name])) == plan['install_hashes'][name]
    assert fingerprint() == plan['world_fingerprints']
    assert k.p.sha256(k.MIGRATION) == plan['migration_sha256']
    appearance = db.sql(APPEARANCE, 'acore_characters')
    (root / 'appearance-at-install.tsv').write_text(appearance, encoding='utf-8')
    receipt = hashlib.sha1(k.MIGRATION.read_bytes()).hexdigest().upper()
    try:
        db.sql('START TRANSACTION;\n' + k.MIGRATION.read_text() +
            f"\nINSERT INTO updates (name,hash,state) VALUES ('{k.MIGRATION.name}','{receipt}','PENDING');\nCOMMIT;")
        for name, source in plan['files'].items():
            live = k.p.CLIENT_DEFAULT / name
            temporary = live.with_suffix(live.suffix + '.drakkin-next')
            assert not temporary.exists(), 'Prior incomplete copy needs review'
            shutil.copy2(source, temporary)
            assert k.p.sha256(temporary) == plan['install_hashes'][name]
            temporary.replace(live)
        for name in k.tables_lib.SERVER_TABLES:
            source = k.STAGE / 'server/dbc' / (name + '.dbc')
            shutil.copy2(source, k.p.SERVER_DBC_ROOT / source.name)
            assert k.p.sha256(k.p.SERVER_DBC_ROOT / source.name) == plan['server_after'][name]
        assert fingerprint() == plan['world_fingerprints']
        assert db.sql(APPEARANCE, 'acore_characters') == appearance
    except Exception:
        for name, expected in plan['before'].items():
            live = k.p.CLIENT_DEFAULT / name
            if expected is None:
                live.unlink(missing_ok=True)
            else:
                shutil.copy2(root / 'client' / name, live)
        for name in k.tables_lib.SERVER_TABLES:
            shutil.copy2(root / 'server-dbc' / (name + '.dbc'), k.p.SERVER_DBC_ROOT / (name + '.dbc'))
        db.sql('START TRANSACTION;\n' + (root / 'rollback-world.sql').read_text() + '\nCOMMIT;')
        raise
    plan.update(installed_hashes={name: k.p.sha256(k.p.CLIENT_DEFAULT / name) for name in plan['files']},
                appearance_sha256=hashlib.sha256(appearance.encode()).hexdigest(), receipt=receipt)
    k.save(root / 'install-report.json', plan)
    k.save(k.STAGE / 'last-install.json', plan)
    print('INSTALLED checked Drakkin package; worldserver still stopped', flush=True)


def verify():
    plan = k.p.load_json(k.STAGE / 'last-install.json')
    for name, digest in plan['installed_hashes'].items():
        assert k.p.sha256(k.p.CLIENT_DEFAULT / name) == digest, name
    assert fingerprint() == plan['world_fingerprints']
    assert hashlib.sha256(db.sql(APPEARANCE, 'acore_characters').encode()).hexdigest() == plan['appearance_sha256']
    build = k.p.load_json(k.STAGE / 'server-build.json')
    assert inspect('ac-worldserver', '{{.Image}} {{.State.Running}}') == build['image'] + ' true'
    paths = ['/azerothcore/env/dist/data/dbc/' + name + '.dbc' for name in k.tables_lib.SERVER_TABLES]
    hashes = subprocess.check_output(['docker', 'exec', 'ac-worldserver', 'sha256sum', *paths], text=True)
    for line in hashes.splitlines():
        digest, path = line.split(maxsplit=1)
        assert digest == plan['server_after'][Path(path).stem]
    for race, _, _, _, display, _ in k.SPECS:
        assert [int(value) for value in db.sql(
            f'SELECT class FROM playercreateinfo WHERE race={race} ORDER BY class;').splitlines()] == k.CLASSES
        assert db.sql(f'SELECT MaleDisplayId,FemaleDisplayId FROM chrraces_dbc WHERE ID={race};').strip() \
            == '0\t' + str(display)
        assert db.sql(f'SELECT spell FROM custom_race_start_spell WHERE race={race};').strip() \
            == str(668 if race == 66 else 669)
        assert db.sql(f'SELECT skill,`rank` FROM custom_race_start_skill WHERE race={race};').strip() \
            == ('98\t0' if race == 66 else '109\t0')
    assert db.sql(f"SELECT hash,state FROM updates WHERE name='{k.MIGRATION.name}';").strip() \
        == plan['receipt'] + '\tPENDING'
    k.save(k.STAGE / 'runtime-checks.json', {'installed_hashes_passed': True, 'server_image': build['image'],
           'mounted_dbc_passed': True, 'unrelated_appearance_preserved': True, 'live_client_checked': False})
    print('VERIFIED installed file hashes, mounted DBCs, server image and saved-appearance preservation')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('preflight', 'backup', 'install', 'verify'))
    args = parser.parse_args()
    {'preflight': preflight, 'backup': backup, 'install': install, 'verify': verify}[args.action]()
