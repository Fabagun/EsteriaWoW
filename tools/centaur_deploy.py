"""Back up and install the matched Centaur client, server image, DBCs and scoped SQL."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess

import centaur_race_pack as pack
import centaur_racials
import creature_race_pack as creature
from slime_giant_deploy import sql, docker, atomic_copy
from slime_giant_client_install import closed
import test_centaur

ROOT, WORK, STAGE = pack.p.ROOT, pack.WORK, pack.STAGE
CLIENT = pack.p.CLIENT_DEFAULT
NATIVE = ROOT.parent / 'wowdecomp'
SERVER = pack.p.SERVER_DBC_ROOT
TABLES = (*pack.shared.SERVER_TABLES, 'Spell')
IMAGE = 'esteria-centaur:20261020'
ASSET = Path('Data/Patch-Cn.MPQ')
PLAN = WORK / 'installation-plan.json'
VALIDATION = WORK / 'build-validation.json'
SCOPES = {name: (field, '73,74') for name, field in {
    **creature.WORLD_TABLES, 'custom_race_start_spell_exclude': 'race',
    'custom_race_start_skill_exclude': 'race', 'chrraces_dbc': 'ID'}.items()}
SCOPES.update(spell_dbc=('ID', '111000,111001,111002,111003'),
              creaturemodeldata_dbc=('ID', '120083,120084,120085,120086'),
              creaturedisplayinfo_dbc=('ID', '60074,60075,60076,60077'))
APPEARANCE = ('SELECT guid,race,gender,skin,face,hairStyle,hairColor,facialStyle,extraAppearance,teamId '
              'FROM characters ORDER BY guid;')


def save(path, value):
    pack.json_save(path, value)


def fingerprints():
    return {name: hashlib.sha256(b'\n'.join(sorted(sql(
        f'SELECT * FROM `{name}` WHERE `{field}` NOT IN ({ids});').splitlines()))).hexdigest()
        for name, (field, ids) in SCOPES.items()}


def vacant():
    for name, (field, ids) in SCOPES.items():
        assert sql(f'SELECT COUNT(*) FROM `{name}` WHERE `{field}` IN ({ids});').strip() == b'0', name
    assert sql('SELECT COUNT(*) FROM characters WHERE race IN (73,74);', 'acore_characters').strip() == b'0'
    assert sql(f"SELECT COUNT(*) FROM updates WHERE name='{pack.MIGRATION.name}';").strip() == b'0'


def validate():
    test_centaur.main()
    report = pack.p.load_json(VALIDATION)
    assert report['all_passed'], 'Build validation has not passed'
    assert report['server_image'] == docker('image', 'inspect', IMAGE, '--format', '{{.Id}}')
    assert pack.p.sha256(NATIVE / 'bin/Win/WowClientRetailInventory.exe') == report['client_sha256']
    assert pack.p.sha256(pack.MIGRATION) == report['migration_sha256']
    for name, expected in report['source_files'].items():
        assert pack.p.sha256(ROOT / name) == expected, name
    for name, expected in report['native_source_files'].items():
        assert pack.p.sha256(NATIVE / name) == expected, name
    return report


def stage_client():
    closed()
    report = pack.p.load_json(STAGE / 'report.json')
    output = WORK / 'install/client'
    output.mkdir(parents=True, exist_ok=True)
    entries = {pack.p.DBC_ROOT + path.name: path.read_bytes() for path in (STAGE / 'client-dbc').glob('*.dbc')}
    entries.update({pack.p.GLUE_ROOT + path.name: path.read_bytes() for path in (STAGE / 'glue').glob('*.lua')})
    assets = {str(path.relative_to(STAGE / 'assets')).replace('/', '\\'): path.read_bytes()
              for path in (STAGE / 'assets').rglob('*') if path.is_file()}
    storm = pack.p.Storm(pack.p.DLL_DEFAULT)
    files = {}
    for relative in (pack.p.GLOBAL_ARCHIVE_REL, pack.p.LOCALE_ARCHIVE_REL, ASSET):
        live, target = CLIENT / relative, output / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if relative == ASSET:
            assert not live.exists(), 'Centaur asset archive slot is occupied'
            if target.exists():
                target.unlink()
            storm.create_archive(target, assets)
            payloads, baseline = assets, None
        else:
            baseline = report['archive_baselines'][str(relative)]
            assert pack.p.sha256(live) == baseline, 'Rebase changed client archive: ' + str(relative)
            shutil.copy2(live, target)
            storm.replace_archive_entries(target, entries)
            payloads = entries
        handle = storm.open_archive(target)
        try:
            for name, data in payloads.items():
                assert storm.read(handle, name) == data, name
        finally:
            storm.dll.SFileCloseArchive(handle)
        files[str(relative)] = {'source': str(target), 'before': baseline, 'after': pack.p.sha256(target)}
    save(WORK / 'install/client-stage.json', files)
    print('STAGED and read back all three matched client archives', flush=True)


def prepare():
    closed()
    validation = validate()
    vacant()
    files = pack.p.load_json(WORK / 'install/client-stage.json')
    executable = NATIVE / 'bin/Win/WowClientRetailInventory.exe'
    files['WowClientRetailVulkan.exe'] = {'source': str(executable),
        'before': pack.p.sha256(CLIENT / 'WowClientRetailVulkan.exe'), 'after': pack.p.sha256(executable)}
    root = Path('G:/EsteriaBackups') / ('Centaur-' + datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S'))
    root.mkdir(parents=True, exist_ok=False)
    metadata = pack.p.load_json(CLIENT / 'WowClientRetailVulkan.build.json')
    assert metadata['sha256'] == files['WowClientRetailVulkan.exe']['before']
    metadata.update(sha256=validation['client_sha256'], backup_directory=str(root), live_acceptance='pending',
                    staged_at_utc=datetime.now(timezone.utc).isoformat(),
                    centaur={'races': [73, 74], 'models': [4036647, 4081379], 'flight': 'bird'})
    metadata['features'].append('Centaur male/female, both factions, player armor, Gallop and bird flight form')
    for name, expected in validation['native_source_files'].items():
        found = next((row for row in metadata['source_files'] if row['path'] == name), None)
        if found is None:
            metadata['source_files'].append({'path': name, 'sha256': expected})
        else:
            found['sha256'] = expected
    metadata_file = WORK / 'install/WowClientRetailVulkan.build.json'
    save(metadata_file, metadata)
    files[metadata_file.name] = {'source': str(metadata_file), 'before': pack.p.sha256(CLIENT / metadata_file.name),
                                'after': pack.p.sha256(metadata_file)}
    for name, entry in files.items():
        target = CLIENT / name
        assert (pack.p.sha256(target) if target.exists() else None) == entry['before'], name
        assert pack.p.sha256(Path(entry['source'])) == entry['after'], name
        if target.exists():
            saved = root / 'client' / name
            saved.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(target, saved)
            assert pack.p.sha256(saved) == entry['before']
    server = {}
    for name in TABLES:
        target, source = SERVER / (name + '.dbc'), STAGE / 'server/dbc' / (name + '.dbc')
        assert pack.p.sha256(target) == pack.p.sha256(STAGE / 'baseline-server' / target.name), name
        pack.save(root / 'server' / target.name, target.read_bytes())
        server[name] = {'before': pack.p.sha256(target), 'after': pack.p.sha256(source), 'source': str(source)}
    tables = ','.join("'" + name + "'" for name in (*SCOPES, 'updates'))
    engines = sql('SELECT TABLE_NAME,ENGINE FROM information_schema.TABLES '
                  f"WHERE TABLE_SCHEMA='acore_world' AND TABLE_NAME IN ({tables});").splitlines()
    assert len(engines) == len(SCOPES) + 1 and all(row.endswith(b'\tInnoDB') for row in engines)
    rollback = '\n'.join(f'DELETE FROM `{name}` WHERE `{field}` IN ({ids});'
                         for name, (field, ids) in SCOPES.items())
    rollback += f"\nDELETE FROM `updates` WHERE `name`='{pack.MIGRATION.name}';\n"
    pack.save(root / 'rollback-world.sql', rollback.encode())
    compose = ROOT / 'docker-compose.override.yml'
    pack.save(root / compose.name, compose.read_bytes())
    before_image = docker('inspect', 'ac-worldserver', '--format', '{{.Image}}')
    rollback_tag = 'esteria-centaur-rollback:20261020'
    subprocess.run(['docker', 'image', 'tag', before_image, rollback_tag], check=True)
    plan = {'backup': str(root), 'client': files, 'server': server, 'server_image': validation['server_image'],
            'previous_image': before_image, 'rollback_tag': rollback_tag, 'world_fingerprints': fingerprints(),
            'compose_sha256': pack.p.sha256(compose), 'migration_sha256': pack.p.sha256(pack.MIGRATION),
            'auth_container': docker('inspect', 'ac-authserver', '--format', '{{.Id}}'),
            'database_container': docker('inspect', 'ac-database', '--format', '{{.Id}}')}
    save(root / 'installation-plan.json', plan)
    save(PLAN, plan)
    print('PREPARED matched client/server rollback:', root, flush=True)


def semantics():
    for race, faction, donor in pack.SPECS:
        actual = sql('SELECT class,map,zone,position_x,position_y,position_z,orientation '
                     f'FROM playercreateinfo WHERE race={race} ORDER BY class;')
        expected = sql('SELECT class,map,zone,position_x,position_y,position_z,orientation '
                       f'FROM playercreateinfo WHERE race={donor} ORDER BY class;')
        assert actual == expected, 'Creation starts/classes differ'
        bounds = pack.ranges(race)
        actual = sql('SELECT MaleDisplayId,FemaleDisplayId,ClientPrefix,BaseLanguage,Alliance '
                     f'FROM chrraces_dbc WHERE ID={race};').strip()
        expected = (f"{bounds['CreatureDisplayInfo']['male']}\t{bounds['CreatureDisplayInfo']['female']}\tDr\t"
                    f"{7 if donor == 1 else 1}\t{0 if donor == 1 else 1}").encode()
        assert actual == expected, 'Race identity differs'
    assert sql('SELECT COUNT(*) FROM spell_dbc WHERE ID BETWEEN 111000 AND 111003;').strip() == b'4'


def install():
    closed()
    validate()
    plan = pack.p.load_json(PLAN)
    root = Path(plan['backup'])
    assert not (root / 'installed.json').exists(), 'Already installed'
    assert pack.p.sha256(ROOT / 'docker-compose.override.yml') == plan['compose_sha256']
    assert pack.p.sha256(pack.MIGRATION) == plan['migration_sha256']
    for name, entry in plan['client'].items():
        target = CLIENT / name
        assert (pack.p.sha256(target) if target.exists() else None) == entry['before'], name
        assert pack.p.sha256(Path(entry['source'])) == entry['after'], name
    for name, entry in plan['server'].items():
        assert pack.p.sha256(SERVER / (name + '.dbc')) == entry['before'], name
    vacant()
    assert fingerprints() == plan['world_fingerprints']
    subprocess.run(['docker', 'compose', 'stop', 'ac-worldserver'], cwd=ROOT, check=True)
    pack.save(root / 'characters-appearance.tsv', sql(APPEARANCE, 'acore_characters'))
    try:
        sha1 = hashlib.sha1(pack.MIGRATION.read_bytes()).hexdigest().upper()
        receipt = (f"INSERT INTO updates (name,hash,state) VALUES ('{pack.MIGRATION.name}','{sha1}','PENDING');")
        sql('START TRANSACTION;\n' + pack.MIGRATION.read_text() + '\n' + receipt + '\nCOMMIT;')
        for name, entry in plan['client'].items():
            atomic_copy(Path(entry['source']), CLIENT / name, entry['after'])
        for name, entry in plan['server'].items():
            atomic_copy(Path(entry['source']), SERVER / (name + '.dbc'), entry['after'])
        compose = ROOT / 'docker-compose.override.yml'
        text, count = re.subn(r'(  ac-worldserver:\n    image: )[^\n]+', r'\g<1>' + IMAGE, compose.read_text())
        assert count == 1, 'Worldserver compose image anchor changed'
        compose.write_text(text, encoding='utf-8', newline='\n')
        semantics()
        assert fingerprints() == plan['world_fingerprints'], 'Unrelated world data changed'
        assert sql(APPEARANCE, 'acore_characters') == (root / 'characters-appearance.tsv').read_bytes()
        subprocess.run(['docker', 'compose', 'up', '-d', '--no-deps', '--no-build', '--pull', 'never',
                        '--force-recreate', 'ac-worldserver'], cwd=ROOT, check=True)
    except Exception:
        restore(plan)
        raise
    save(root / 'installed.json', {'installed': True, 'live_accepted': False})
    save(WORK / 'installation-receipt.json', {**plan, 'installed': True, 'live_accepted': False})
    print('INSTALLED matched Centaur package; runtime readiness pending:', root, flush=True)


def restore(plan):
    root = Path(plan['backup'])
    assert sql('SELECT COUNT(*) FROM characters WHERE race IN (73,74);', 'acore_characters').strip() == b'0', \
        'Preserve newly created Centaur characters before rollback'
    for name, entry in plan['client'].items():
        target = CLIENT / name
        if entry['before'] is None:
            if target.exists():
                assert pack.p.sha256(target) == entry['after']
                target.unlink()
        else:
            atomic_copy(root / 'client' / name, target, entry['before'])
    for name, entry in plan['server'].items():
        atomic_copy(root / 'server' / (name + '.dbc'), SERVER / (name + '.dbc'), entry['before'])
    sql('START TRANSACTION;\n' + (root / 'rollback-world.sql').read_text() + '\nCOMMIT;')
    shutil.copy2(root / 'docker-compose.override.yml', ROOT / 'docker-compose.override.yml')
    subprocess.run(['docker', 'compose', 'up', '-d', '--no-deps', '--no-build', '--pull', 'never',
                    '--force-recreate', 'ac-worldserver'], cwd=ROOT, check=True)
    save(root / 'rolled-back.json', {'restored': True})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('stage-client', 'prepare', 'install', 'rollback'))
    args = parser.parse_args()
    if args.action == 'rollback':
        closed()
        subprocess.run(['docker', 'compose', 'stop', 'ac-worldserver'], cwd=ROOT, check=True)
        restore(pack.p.load_json(PLAN))
    else:
        {'stage-client': stage_client, 'prepare': prepare, 'install': install}[args.action]()
