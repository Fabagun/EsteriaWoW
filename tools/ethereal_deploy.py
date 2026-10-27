"""Back up and deploy only the matched Ethereal client/server package, retaining a rollback receipt."""

import argparse
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import shutil
import subprocess

import creature_race_pack
import ethereal_race_pack as pack
import ethereal_source as source
from slime_giant_deploy import docker, sql
import test_ethereal

WORK, STAGE, CLIENT = source.WORK, pack.STAGE, pack.p.CLIENT_DEFAULT
ROOT, SERVER = pack.p.ROOT, pack.p.SERVER_DBC_ROOT
IMAGE = 'esteria-ethereal:20261026'
ARCHIVE = Path('Data/Patch-ZzzzzzzzEthereal.MPQ')
COMPOSE = ROOT / 'docker-compose.twoforms.yml'
PLAN = WORK / 'deployment-plan.json'
SCOPES = {table: (field, '77,78') for table, field in {
    **creature_race_pack.WORLD_TABLES, 'custom_race_start_spell_exclude': 'race',
    'custom_race_start_skill_exclude': 'race', 'chrraces_dbc': 'ID'}.items()}
SCOPES.update(spell_dbc=('ID', '111004'), spell_script_names=('spell_id', '111004'),
              creature_model_info=('DisplayID', '60087,60088,60089,60090'),
              creaturemodeldata_dbc=('ID', '121064,121065,121066,121067'),
              creaturedisplayinfo_dbc=('ID', '60087,60088,60089,60090'))
CHARACTER_QUERIES = {
    'appearance': 'SELECT guid,race,gender,skin,face,hairStyle,hairColor,facialStyle,extraAppearance,teamId '
                  'FROM characters ORDER BY guid;',
    'retail-look': 'SELECT guid,HEX(data) FROM character_retail_look ORDER BY guid;',
    'form-look': 'SELECT guid,HEX(data) FROM character_form_look ORDER BY guid;'}


def digest(path):
    return pack.p.sha256(path)


def save(path, value):
    source.save(path, value)


def run(*command, **options):
    return subprocess.run(command, check=True, **options)


def closed():
    # Exclude console windows; check only the actual executable names that can hold the payload open.
    processes = subprocess.check_output(['tasklist', '/FO', 'CSV', '/NH'], text=True).lower()
    blocked = ('"wow.exe"', '"wowclient', '"waystone', '"eclipse.exe"', '"mpqeditor.exe"')
    assert not any(name in processes for name in blocked), 'Close the game and MPQ tools before deployment'


def vacant():
    for table, (field, ids) in SCOPES.items():
        assert sql(f'SELECT COUNT(*) FROM `{table}` WHERE `{field}` IN ({ids});').strip() == b'0', table
    assert sql('SELECT COUNT(*) FROM characters WHERE race IN (77,78);', 'acore_characters').strip() == b'0'
    assert not sql(f"SELECT name FROM updates WHERE name='{pack.MIGRATION.name}';").strip()


def fingerprints():
    return {table: hashlib.sha256(b'\n'.join(sorted(sql(
        f'SELECT * FROM `{table}` WHERE `{field}` NOT IN ({ids});').splitlines()))).hexdigest()
        for table, (field, ids) in SCOPES.items()}


def baseline_unchanged():
    actual, _ = pack.baseline()
    for name, raw in actual.items():
        path = STAGE / 'baseline' / (name if name.endswith('.lua') else name + '.dbc')
        assert path.read_bytes() == raw, 'Client baseline changed; restage before installing: ' + name


def copy_checked(incoming, target, expected):
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(target.name + '.ethereal-next')
    with temporary.open('xb') as output, incoming.open('rb') as stream:
        shutil.copyfileobj(stream, output)
    try:
        assert digest(temporary) == expected, 'Temporary file differs: ' + str(target)
        os.replace(temporary, target)
        assert digest(target) == expected
    finally:
        temporary.unlink(missing_ok=True)


def stage():
    closed()
    test_ethereal.main()
    actual, providers = pack.baseline()
    for name, raw in actual.items():
        path = STAGE / 'baseline' / (name if name.endswith('.lua') else name + '.dbc')
        assert path.read_bytes() == raw, 'Client baseline changed; restage: ' + name
    entries = {pack.p.DBC_ROOT + path.name: path.read_bytes() for path in (STAGE / 'client-dbc').glob('*.dbc')}
    entries.update({pack.p.GLUE_ROOT + path.name: path.read_bytes() for path in (STAGE / 'glue').glob('*.lua')})
    entries.update({str(path.relative_to(STAGE / 'assets')).replace('/', '\\'): path.read_bytes()
                    for path in (STAGE / 'assets').rglob('*') if path.is_file()})
    destination = WORK / 'deploy/client' / ARCHIVE
    destination.parent.mkdir(parents=True, exist_ok=True)
    assert not (CLIENT / ARCHIVE).exists(), 'Deployment archive slot is occupied'
    storm = pack.p.Storm(pack.p.DLL_DEFAULT)
    if destination.exists():
        destination.unlink()
    storm.create_archive(destination, entries)
    handle = storm.open_archive(destination)
    try:
        for name, raw in entries.items():
            assert storm.read(handle, name) == raw, name
    finally:
        storm.dll.SFileCloseArchive(handle)
    files = {str(ARCHIVE): {'source': str(destination), 'before': None, 'after': digest(destination)}}
    executable = source.NATIVE / 'bin/Win/WowClientRetailInventory.exe'
    files['Wow.exe'] = {'source': str(executable), 'before': digest(CLIENT / 'Wow.exe'), 'after': digest(executable)}
    for name in (*pack.shared.SERVER_TABLES, 'Spell'):
        assert (SERVER / (name + '.dbc')).read_bytes() == (STAGE / 'baseline-server' / (name + '.dbc')).read_bytes(), name
    # The metadata is additive and describes the executable actually launched from this client.
    metadata = {'source_build': source.BUILD, 'sha256': digest(executable), 'race_ids': [77,78], 'forms': [5,6],
                'native_tests': ['RetailAssetTests', '--ethereal-source'],
                'customization_controls': {'Darkweaver': 38, 'Dreadnaught': 8},
                'live_acceptance': 'pending', 'stage': str(STAGE)}
    metadata_path = WORK / 'deploy/client/Wow.ethereal.build.json'
    save(metadata_path, metadata)
    live_metadata = CLIENT / metadata_path.name
    files[metadata_path.name] = {'source': str(metadata_path), 'before': digest(live_metadata) if live_metadata.exists() else None,
                                 'after': digest(metadata_path)}
    save(WORK / 'client-deployment.json', {'files': files, 'providers': providers,
        'entry_hashes': {name: hashlib.sha256(raw).hexdigest() for name, raw in entries.items()},
        'preservation_passed': True, 'readback_passed': True})
    print('STAGED and read back', len(entries), 'entries; deploy target is G:/3.3.5a - Dev/Wow.exe')


def prepare():
    closed()
    vacant()
    baseline_unchanged()
    validation = pack.p.load_json(WORK / 'validation.json')
    assert validation['native_regression_passed'] and validation['all_three_native_sources_passed']
    assert validation['native_client_sha256'] == digest(source.NATIVE / 'bin/Win/WowClientRetailInventory.exe')
    image = docker('image', 'inspect', IMAGE, '--format', '{{.Id}}')
    client = pack.p.load_json(WORK / 'client-deployment.json')
    assert client['readback_passed'] and client['preservation_passed']
    backup = Path('G:/EsteriaBackups') / ('Ethereal-' + datetime.now().strftime('%Y%m%d-%H%M%S'))
    backup.mkdir(parents=True, exist_ok=False)
    for name, row in client['files'].items():
        live = CLIENT / name
        assert (digest(live) if live.exists() else None) == row['before'], name
        assert digest(Path(row['source'])) == row['after'], name
        if live.exists():
            target = backup / 'client' / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(live, target)
            assert digest(target) == row['before']
    server = {}
    for name in (*pack.shared.SERVER_TABLES, 'Spell'):
        live, staged = SERVER / (name + '.dbc'), STAGE / 'server/dbc' / (name + '.dbc')
        assert live.read_bytes() == (STAGE / 'baseline-server' / live.name).read_bytes(), name
        target = backup / 'server' / live.name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(live, target)
        server[name] = {'before': digest(live), 'after': digest(staged), 'source': str(staged)}
    shutil.copy2(COMPOSE, backup / COMPOSE.name)
    shutil.copy2(pack.MIGRATION, backup / pack.MIGRATION.name)
    names = ','.join("'" + name + "'" for name in (*SCOPES, 'updates'))
    engines = sql('SELECT TABLE_NAME,ENGINE FROM information_schema.TABLES '
                  f"WHERE TABLE_SCHEMA='acore_world' AND TABLE_NAME IN ({names});").splitlines()
    assert len(engines) == len(SCOPES) + 1 and all(row.endswith(b'\tInnoDB') for row in engines)
    rollback = '\n'.join(f'DELETE FROM `{name}` WHERE `{field}` IN ({ids});'
                         for name, (field, ids) in SCOPES.items())
    rollback += f"\nDELETE FROM `updates` WHERE `name`='{pack.MIGRATION.name}';\n"
    (backup / 'rollback-world.sql').write_text(rollback, encoding='utf-8', newline='\n')
    previous_image = docker('inspect', 'ac-worldserver', '--format', '{{.Image}}')
    rollback_tag = 'esteria-ethereal-rollback:pre-20261026'
    run('docker', 'image', 'tag', previous_image, rollback_tag)
    plan = {'backup': str(backup), 'client': client['files'], 'server': server, 'server_image': image,
            'previous_image': previous_image, 'rollback_tag': rollback_tag,
            'compose_before': digest(COMPOSE), 'migration_sha256': digest(pack.MIGRATION),
            'world_fingerprints': fingerprints(),
            'auth_container': docker('inspect', 'ac-authserver', '--format', '{{.Id}}'),
            'database_container': docker('inspect', 'ac-database', '--format', '{{.Id}}')}
    save(PLAN, plan)
    save(backup / PLAN.name, plan)
    print('PREPARED verified backups:', backup)


def compose(*arguments):
    run('docker', 'compose', '-f', 'docker-compose.yml', '-f', 'docker-compose.override.yml',
        '-f', 'docker-compose.twoforms.yml', *arguments, cwd=ROOT)


def semantics():
    for race, _, donor in pack.SPECS:
        actual = sql('SELECT class,map,zone,position_x,position_y,position_z,orientation '
                     f'FROM playercreateinfo WHERE race={race} ORDER BY class;')
        expected = sql('SELECT class,map,zone,position_x,position_y,position_z,orientation '
                       f'FROM playercreateinfo WHERE race={donor} ORDER BY class;')
        assert actual == expected, 'Wrong faction creation starts'
        bounds = pack.ranges(race)['CreatureDisplayInfo']
        expected = f"{bounds['male']}\t{bounds['female']}\tNb\t{7 if donor == 1 else 1}\t{donor - 1}".encode()
        assert sql(f'SELECT MaleDisplayId,FemaleDisplayId,ClientPrefix,BaseLanguage,Alliance FROM chrraces_dbc WHERE ID={race};').strip() == expected
        assert sql(f'SELECT spell FROM custom_race_start_spell WHERE race={race} AND spell=111004;').strip() == b'111004'
    assert sql('SELECT ScriptName FROM spell_script_names WHERE spell_id=111004;').strip() == b'spell_race_ethereal_two_forms'


def install():
    closed()
    plan = pack.p.load_json(PLAN)
    backup = Path(plan['backup'])
    assert not (backup / 'installed.json').exists(), 'Already installed'
    assert digest(COMPOSE) == plan['compose_before'] and digest(pack.MIGRATION) == plan['migration_sha256']
    assert docker('image', 'inspect', IMAGE, '--format', '{{.Id}}') == plan['server_image']
    assert docker('inspect', 'ac-worldserver', '--format', '{{.Image}}') == plan['previous_image']
    baseline_unchanged()
    for name, row in plan['client'].items():
        live = CLIENT / name
        assert (digest(live) if live.exists() else None) == row['before']
        assert digest(Path(row['source'])) == row['after']
    for name, row in plan['server'].items():
        assert digest(SERVER / (name + '.dbc')) == row['before'] and digest(Path(row['source'])) == row['after']
    vacant()
    assert fingerprints() == plan['world_fingerprints']
    compose('stop', 'ac-worldserver')
    for name, query in CHARACTER_QUERIES.items():
        (backup / (name + '.tsv')).write_bytes(sql(query, 'acore_characters'))
    try:
        sha1 = hashlib.sha1(pack.MIGRATION.read_bytes()).hexdigest().upper()
        sql('START TRANSACTION;\n' + pack.MIGRATION.read_text() +
            f"INSERT INTO updates(name,hash,state) VALUES('{pack.MIGRATION.name}','{sha1}','PENDING');\nCOMMIT;")
        for name, row in plan['client'].items():
            copy_checked(Path(row['source']), CLIENT / name, row['after'])
        for name, row in plan['server'].items():
            copy_checked(Path(row['source']), SERVER / (name + '.dbc'), row['after'])
        COMPOSE.write_text('services:\n  ac-worldserver:\n    image: ' + IMAGE + '\n', encoding='utf-8', newline='\n')
        semantics()
        assert fingerprints() == plan['world_fingerprints'], 'Unrelated world records changed'
        for name, query in CHARACTER_QUERIES.items():
            assert sql(query, 'acore_characters') == (backup / (name + '.tsv')).read_bytes(), 'Existing appearance changed'
        compose('up', '-d', '--no-deps', '--no-build', '--pull', 'never', '--force-recreate', 'ac-worldserver')
    except Exception:
        for name, row in plan['client'].items():
            if row['before'] is None:
                (CLIENT / name).unlink(missing_ok=True)
            else:
                copy_checked(backup / 'client' / name, CLIENT / name, row['before'])
        for name, row in plan['server'].items():
            copy_checked(backup / 'server' / (name + '.dbc'), SERVER / (name + '.dbc'), row['before'])
        sql('START TRANSACTION;\n' + (backup / 'rollback-world.sql').read_text() + 'COMMIT;')
        shutil.copy2(backup / COMPOSE.name, COMPOSE)
        compose('up', '-d', '--no-deps', '--no-build', '--pull', 'never', '--force-recreate', 'ac-worldserver')
        raise
    for name, row in plan['client'].items():
        assert digest(CLIENT / name) == row['after']
    for name, row in plan['server'].items():
        assert digest(SERVER / (name + '.dbc')) == row['after']
    assert docker('inspect', 'ac-authserver', '--format', '{{.Id}}') == plan['auth_container']
    assert docker('inspect', 'ac-database', '--format', '{{.Id}}') == plan['database_container']
    receipt = {**plan, 'installed': True, 'installed_utc': datetime.now(timezone.utc).isoformat(),
               'live_accepted': False, 'protocol_test': 'pending', 'server_ready': 'pending'}
    save(WORK / 'deployment-receipt.json', receipt)
    save(backup / 'installed.json', receipt)
    print('INSTALLED matched Ethereal client/server; backup:', backup)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('stage', 'prepare', 'install'))
    args = parser.parse_args()
    globals()[args.action]()
