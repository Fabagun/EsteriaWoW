"""Guarded installation and verification of the staged male Drakkin package."""

import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import struct
import subprocess

ROOT = Path(__file__).resolve().parents[1]
WORK = Path('G:/RetroPorterWork/tarasek-drakkin-male')
STAGE = WORK / 'stage'
CLIENT = Path('G:/3.3.5a - Dev')
NATIVE = Path('G:/TarasekNative')
SERVER = ROOT / 'modules/mod-custom-server/data/dbc/retroported-races'
MIGRATION = 'rev_20261015020000000_tarasek_drakkin_male.sql'
APPEARANCE = ('SELECT guid,race,gender,skin,face,hairStyle,hairColor,facialStyle,extraAppearance,teamId '
              'FROM characters ORDER BY guid;')


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8', newline='\n')


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def command(*args):
    return subprocess.check_output(args, text=True, encoding='utf-8', errors='replace').strip()


def sql(query, database='world'):
    return subprocess.run(['docker', 'exec', '-i', 'ac-database', 'sh', '-c',
                           'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql -uroot --batch --skip-column-names '
                           + 'acore_' + database], input=query, capture_output=True, text=True,
                          encoding='utf-8', errors='replace', check=True).stdout


def migration(database):
    return ROOT / 'data/sql/updates' / ('pending_db_' + database) / MIGRATION


def sources():
    report = read(STAGE / 'report.json')
    return {**{name: STAGE / 'client' / name for name in report['archives']},
            **{name: STAGE / name for name in report['catalogs']},
            'EsteriaAppearance.dll': NATIVE / 'EsteriaAppearance.dll'}


def closed_client():
    processes = command('tasklist', '/FO', 'CSV', '/NH').lower()
    assert not any('"' + name + '"' in processes for name in ('wow.exe', 'eclipse.exe', 'mpqeditor.exe'))


def world_rows():
    return sql('SELECT ID,MaleDisplayId,FemaleDisplayId,ClientPrefix,Flags '
               'FROM chrraces_dbc WHERE ID IN (66,67) ORDER BY ID;')


def fingerprint():
    # Preserve every unrelated startup/racial row, including the female and retired race configuration.
    result = {}
    for table in ('playercreateinfo', 'playercreateinfo_action', 'playercreateinfo_cast_spell',
                  'playercreateinfo_item', 'playercreateinfo_skills', 'playercreateinfo_spell_custom',
                  'player_race_stats', 'player_totem_model', 'custom_race_start_spell',
                  'custom_race_start_skill', 'chrraces_dbc', 'creaturemodeldata_dbc', 'creaturedisplayinfo_dbc'):
        query = f'SELECT * FROM `{table}`' + (' WHERE ID<>66' if table == 'chrraces_dbc' else '') + ';'
        rows = '\n'.join(sorted(sql(query).splitlines()))
        result[table] = hashlib.sha256(rows.encode()).hexdigest()
    columns = [row.split('\t')[0] for row in sql('SHOW COLUMNS FROM chrraces_dbc;').splitlines()]
    selection = ','.join('`' + name + '`' for name in columns if name != 'MaleDisplayId')
    result['race66_except_male_display'] = hashlib.sha256(sql(
        f'SELECT {selection} FROM chrraces_dbc WHERE ID=66;').encode()).hexdigest()
    return result


def preflight():
    closed_client()
    report = read(STAGE / 'report.json')
    reserve = max(path.stat().st_size for path in sources().values()) + 64 * 1024 * 1024
    assert shutil.disk_usage(CLIENT).free > reserve, 'Insufficient free space for verified archive replacement'
    build = read(STAGE / 'native-checks.json')
    assert build['all_passed'] and digest(NATIVE / 'EsteriaAppearance.dll') == build['dll_sha256']
    for name, expected in build['source_files'].items():
        assert digest(ROOT / name) == expected, name
    for name, expected in report['source_files'].items():
        assert digest(ROOT / name) == expected, name
    for name, expected in report['runtime_baselines'].items():
        assert digest(CLIENT / name) == expected, name
    baseline = read(WORK / 'baseline/receipt.json')['files']
    for name, receipt in baseline.items():
        if name.startswith('Esteria') and name.endswith('.bin'):
            assert digest(CLIENT / name) == receipt['sha256'], name
    for name, expected in report['catalogs'].items():
        assert digest(STAGE / name) == digest(NATIVE / name) == expected, name
        if name not in baseline:
            assert not (CLIENT / name).exists(), name
    for name, receipt in report['archives'].items():
        assert digest(CLIENT / name) == receipt['baseline'], name
        assert digest(STAGE / 'client' / name) == receipt['sha256'], name
        assert receipt['readback_verified']
    for name, expected in report['server_baselines'].items():
        assert digest(SERVER / (name + '.dbc')) == expected, name
    for name, expected in report['migrations'].items():
        assert digest(STAGE / name) == expected, name
    for database in ('world', 'characters'):
        assert migration(database).read_bytes() == (STAGE / ('pending_db_' + database + '.sql')).read_bytes()
        assert sql(f"SELECT COUNT(*) FROM updates WHERE name='{MIGRATION}';", database).strip() == '0'
    expected = read(WORK / 'baseline/population.json')
    assert [[int(v) for v in row.split('\t')] for row in sql(expected['query'], 'characters').splitlines()] \
        == expected['rows'], 'Saved Drakkin appearance changed'
    assert [row.split('\t') for row in world_rows().splitlines()] == report['world_override_baseline']['rows']
    for table, identifier in (('creaturemodeldata_dbc', 120079), ('creaturedisplayinfo_dbc', 60070)):
        assert sql(f'SELECT COUNT(*) FROM {table} WHERE ID={identifier};').strip() == '0'
    environment = json.loads(command('docker', 'inspect', 'ac-worldserver', '--format', '{{json .Config.Env}}'))
    assert 'AC_UPDATES_ENABLE_DATABASES=0' in environment, 'Unrelated automatic migrations must remain disabled'
    print('PREFLIGHT PASS', flush=True)


def backup():
    preflight()
    destination = Path('R:/EsteriaBackups') / ('Tarasek-' + datetime.now().strftime('%Y%m%d-%H%M%S'))
    destination.mkdir(parents=True)
    report = read(STAGE / 'report.json')
    plan = {'backup': str(destination), 'before': {}, 'after': {}, 'server_before': {}, 'server_after': {},
            'prior_worldserver': read(STAGE / 'prior-worldserver.json')}
    for name, source in sources().items():
        live = CLIENT / name
        plan['before'][name] = digest(live) if live.exists() else None
        plan['after'][name] = digest(source)
        if live.exists():
            target = destination / 'client' / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(live, target)
            assert digest(target) == plan['before'][name]
            print('BACKED UP', name, flush=True)
    for name, expected in report['server_baselines'].items():
        target = destination / 'server-dbc' / (name + '.dbc')
        target.parent.mkdir(exist_ok=True)
        shutil.copy2(SERVER / target.name, target)
        assert digest(target) == expected
        plan['server_before'][name] = expected
        plan['server_after'][name] = digest(STAGE / 'server-dbc' / target.name)
    for database in ('world', 'characters'):
        for name in ('pending_db_' + database + '.sql', 'rollback-' + database + '.sql'):
            shutil.copy2(STAGE / name, destination / name)
    plan['backup_checksums'] = {str(p.relative_to(destination)): digest(p)
                                for p in destination.rglob('*') if p.is_file()}
    save(destination / 'install-plan.json', plan)
    save(STAGE / 'install-plan.json', plan)
    print('VERIFIED BACKUP', destination, flush=True)


def replace(source, target, expected):
    temporary = target.with_suffix(target.suffix + '.tarasek-next')
    assert not temporary.exists(), temporary
    try:
        shutil.copy2(source, temporary)
        assert digest(temporary) == expected
        os.replace(temporary, target)
    finally:
        if temporary.exists():
            assert temporary.parent.resolve() == target.parent.resolve()
            temporary.unlink()


def install():
    preflight()
    server = read(STAGE / 'server-build.json')
    assert command('docker', 'image', 'inspect', 'acore/ac-wotlk-worldserver:master', '--format', '{{.Id}}') \
        == server['image']
    assert command('docker', 'inspect', 'ac-worldserver', '--format', '{{.State.Running}}') == 'false'
    plan = read(STAGE / 'install-plan.json')
    root = Path(plan['backup'])
    for name, expected in plan['backup_checksums'].items():
        assert digest(root / name) == expected, name
    for name, expected in plan['before'].items():
        target = CLIENT / name
        assert (digest(target) if target.exists() else None) == expected, name
        assert digest(sources()[name]) == plan['after'][name], name
    plan['fingerprints'] = fingerprint()
    before = sql(APPEARANCE, 'characters')
    plan['characters_before'] = before
    (root / 'characters-at-install.tsv').write_text(before, encoding='utf-8')
    plan['world_before'] = world_rows()
    plan['receipts'] = {db: hashlib.sha1(migration(db).read_bytes()).hexdigest().upper()
                        for db in ('world', 'characters')}
    save(root / 'install-plan.json', plan)
    save(STAGE / 'install-plan.json', plan)
    try:
        for database, receipt in plan['receipts'].items():
            sql('START TRANSACTION;\n' + migration(database).read_text() +
                f"\nINSERT INTO updates (name,hash,state) VALUES ('{MIGRATION}','{receipt}','PENDING');"
                '\nCOMMIT;', database)
        after = sql(APPEARANCE, 'characters')
        expected = []
        for row in before.splitlines():
            fields = row.split('\t')
            if fields[0] == '546':
                assert fields[1:9] == ['66', '0', '7', '0', '0', '6', '0', '0']
                fields[3:9] = ['0'] * 6
            expected.append('\t'.join(fields))
        assert after.splitlines() == expected, 'Unexpected character appearance changes'
        plan['characters_after'] = after
        assert world_rows() == plan['world_before'].replace('66\t60064\t60064\t', '66\t60070\t60064\t', 1)
        for name, source in sources().items():
            replace(source, CLIENT / name, plan['after'][name])
            print('INSTALLED', name, flush=True)
        for name, expected in plan['server_after'].items():
            replace(STAGE / 'server-dbc' / (name + '.dbc'), SERVER / (name + '.dbc'), expected)
        assert fingerprint() == plan['fingerprints'], 'Unrelated startup data changed'
    except Exception:
        rollback(plan)
        raise
    plan['status'] = 'installed_awaiting_worldserver_recreation'
    save(root / 'install-report.json', plan)
    save(STAGE / 'last-install.json', plan)
    print('MATCHED PACKAGE INSTALLED', flush=True)


def rollback(plan):
    assert command('docker', 'inspect', 'ac-worldserver', '--format', '{{.State.Running}}') == 'false'
    closed_client()
    root = Path(plan['backup'])
    for name, expected in plan['backup_checksums'].items():
        assert digest(root / name) == expected, name
    for name, expected in plan['before'].items():
        target = CLIENT / name
        current = digest(target) if target.exists() else None
        assert current in (expected, plan['after'][name]), name
        if expected is not None:
            replace(root / 'client' / name, target, expected)
        elif target.exists():
            assert CLIENT.resolve() in target.resolve().parents
            target.unlink()
    for name, expected in plan['server_before'].items():
        replace(root / 'server-dbc' / (name + '.dbc'), SERVER / (name + '.dbc'), expected)
    for database, receipt in plan['receipts'].items():
        sql('START TRANSACTION;\n' + (root / ('rollback-' + database + '.sql')).read_text() +
            f"\nDELETE FROM updates WHERE name='{MIGRATION}' AND hash='{receipt}';\nCOMMIT;", database)
    assert sql(APPEARANCE, 'characters') == plan['characters_before']
    assert world_rows() == plan['world_before']
    plan['status'] = 'rolled_back_files_and_sql_requires_prior_image_start'
    save(STAGE / 'last-install.json', plan)
    print('ROLLED BACK files and SQL; prior image:', plan['prior_worldserver'], flush=True)


def verify():
    plan = read(STAGE / 'last-install.json')
    report = read(STAGE / 'report.json')
    assert digest(CLIENT / 'Wow.exe') == report['runtime_baselines']['Wow.exe']
    baseline = read(WORK / 'baseline/receipt.json')['files']
    for name, receipt in baseline.items():
        if name.startswith('Esteria') and name.endswith('.bin') and name not in plan['after']:
            assert digest(CLIENT / name) == receipt['sha256'], name
    for name, expected in plan['after'].items():
        assert digest(CLIENT / name) == expected, name
    for name, expected in plan['server_after'].items():
        path = '/azerothcore/env/dist/data/dbc/' + name + '.dbc'
        assert command('docker', 'exec', 'ac-worldserver', 'sha256sum', path).split()[0] == expected, name
    image = read(STAGE / 'server-build.json')['image']
    assert command('docker', 'inspect', 'ac-worldserver', '--format', '{{.Image}} {{.State.Running}}') \
        == image + ' true'
    assert fingerprint() == plan['fingerprints']
    assert world_rows() == plan['world_before'].replace('66\t60064\t60064\t', '66\t60070\t60064\t', 1)
    before = [json.loads(line) for line in read(STAGE / 'services-before.json').splitlines()]
    current_services = [json.loads(line) for line in
                        command('docker', 'compose', 'ps', '--format', 'json').splitlines()]
    current_ids = {row['Name']: row['ID'] for row in current_services}
    assert all(current_ids.get(row['Name']) == row['ID'] for row in before if row['Name'] != 'ac-worldserver')
    current = set(sql(APPEARANCE, 'characters').splitlines())
    assert set(plan['characters_after'].splitlines()) <= current
    for database, receipt in plan['receipts'].items():
        assert sql(f"SELECT hash,state FROM updates WHERE name='{MIGRATION}';", database).strip() \
            == receipt + '\tPENDING'
    import tarasek_drakkin as t
    files = t.p.ClientFiles(str(CLIENT / 'Data'), 'enUS')
    try:
        for name, expected in report['client_tables'].items():
            data, provider = files.find('DBFilesClient\\' + name + '.dbc')
            assert hashlib.sha256(data).hexdigest() == expected, (name, provider)
        for name in (t.MODEL, 'Interface\\GlueXML\\CharacterCreate.lua'):
            data, provider = files.find(name)
            expected = report['assets'][name] if name in report['assets'] else digest(STAGE / 'CharacterCreate.lua')
            assert hashlib.sha256(data).hexdigest() == expected, (name, provider)
    finally:
        files.close()
    with socket.create_connection(('127.0.0.1', 8085), timeout=5) as connection:
        header = b''
        while len(header) < 4:
            block = connection.recv(4 - len(header))
            assert block
            header += block
        assert struct.unpack_from('<H', header, 2)[0] == 0x1ec
    plan['status'] = 'installed_and_server_ready_live_client_pending'
    plan['live_accepted'] = False
    save(STAGE / 'last-install.json', plan)
    save(Path(plan['backup']) / 'install-report.json', plan)
    report.update(state=plan['status'], installed=True, native_built=True, server_built=True,
                  runtime_readback_passed=True, live_accepted=False)
    save(STAGE / 'report.json', report)
    print('VERIFIED matched client, mounted DBCs, SQL, preserved characters and worldserver handshake', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('preflight', 'backup', 'install', 'verify', 'rollback'))
    action = parser.parse_args().action
    if action == 'rollback':
        rollback(read(STAGE / 'install-plan.json'))
    else:
        globals()[action]()
