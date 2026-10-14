"""Install only the checked Horde Arakkoa race-68 package, with hash-verified file and scoped SQL rollback."""

import argparse
from datetime import datetime
import hashlib
import os
from pathlib import Path
import shutil
import socket
import struct
import subprocess

import arakkoa_race_pack as pack
import mechagnome_race_pack as db
import creature_race_pack as c

def _sql(query, database='acore_world'):
    """Tolerate legacy non-UTF-8 bytes in world rows; fingerprints stay stable across calls."""
    command = ['docker', 'exec', '-i', 'ac-database', 'sh', '-c',
               'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql -uroot --batch --skip-column-names ' + database]
    return subprocess.run(command, input=query, capture_output=True, text=True, encoding='utf-8',
                          errors='replace', check=True).stdout


db.sql = _sql

NATIVE = Path('G:/RetroPorterWork/arakkoa/native-build/EsteriaAppearance.dll')
SERVER = pack.TARGET / 'modules/mod-custom-server/data/dbc/retroported-races'
TABLES = {**c.WORLD_TABLES, 'chrraces_dbc': 'ID'}
APPEARANCE = ('SELECT guid,race,gender,skin,face,hairStyle,hairColor,facialStyle,extraAppearance,teamId '
              'FROM characters ORDER BY guid;')


def fingerprint():
    return {table: hashlib.sha256('\n'.join(sorted(db.sql(
        f'SELECT * FROM `{table}` WHERE `{field}` <> {pack.RACE};').splitlines())).encode()).hexdigest()
        for table, field in TABLES.items()}


def files():
    report = pack.p.load_json(pack.STAGE / 'report.json')
    result = {relative: pack.STAGE / 'client' / relative for relative in report['archives']}
    result['EsteriaAppearance.dll'] = NATIVE
    return result


def preflight():
    report = pack.p.load_json(pack.STAGE / 'report.json')
    checks = pack.p.load_json(pack.STAGE / 'checks.json')
    assert checks['passed'] and checks['race'] == pack.RACE
    processes = subprocess.check_output(['tasklist', '/FO', 'CSV', '/NH'], text=True).lower()
    if any(name in processes for name in ('wow.exe', 'eclipse.exe', 'mpqeditor.exe')):
        raise RuntimeError('Close WoW/Eclipse/MPQEditor before installing the matched package')
    if pack.p.sha256(pack.p.CLIENT_DEFAULT / 'Wow.exe') != report['exe_sha256']:
        raise ValueError('Executable baseline changed')
    for relative, expected in report['archive_baselines'].items():
        if pack.p.sha256(pack.p.CLIENT_DEFAULT / relative) != expected:
            raise ValueError('Archive baseline changed: ' + relative)
    for name in pack.SERVER_TABLES:
        if pack.p.sha256(SERVER / (name + '.dbc')) != \
                pack.p.sha256(pack.STAGE / 'baseline-server' / (name + '.dbc')):
            raise ValueError('Mounted server DBC changed: ' + name)
    if (pack.p.CLIENT_DEFAULT / pack.ASSET).exists():
        raise ValueError('New asset archive already exists')
    for table, field in TABLES.items():
        if db.sql(f'SELECT COUNT(*) FROM `{table}` WHERE `{field}`={pack.RACE};').strip() != '0':
            raise ValueError('Race 68 already owns startup rows: ' + table)
    if db.sql(f'SELECT COUNT(*) FROM characters WHERE race={pack.RACE};', 'acore_characters').strip() != '0':
        raise ValueError('Race 68 has saved characters; preserve their appearance before installing')
    for table, ids in (('creaturemodeldata_dbc', (120075, 120076)),
                       ('creaturedisplayinfo_dbc', (60066, 60067))):
        if db.sql(f'SELECT COUNT(*) FROM `{table}` WHERE ID IN {ids};').strip() != '0':
            raise ValueError('Model/display IDs have SQL overrides: ' + table)
    if db.sql(f"SELECT COUNT(*) FROM updates WHERE name='{pack.MIGRATION.name}';").strip() != '0':
        raise ValueError('Migration already has a receipt')
    build = pack.p.load_json(pack.STAGE / 'native-checks.json')
    if not build['all_passed'] or pack.p.sha256(NATIVE) != build['dll_sha256']:
        raise ValueError('Native DLL does not match the passing harnesses')
    for name, expected in build['source_files'].items():
        if pack.p.sha256(pack.TARGET / name) != expected:
            raise ValueError('Build source changed: ' + name)
    for name, expected in build['catalog_hashes'].items():
        if pack.p.sha256(pack.p.CLIENT_DEFAULT / name) != expected:
            raise ValueError('Live catalog differs from the tested catalog: ' + name)
    print('PREFLIGHT PASS', flush=True)


def backup():
    preflight()
    root = Path('G:/EsteriaBackups') / ('Arakkoa-' + datetime.now().strftime('%Y%m%d-%H%M%S'))
    root.mkdir(parents=True)
    report = {'backup': str(root), 'files': {name: str(path) for name, path in files().items()},
        'before': {}, 'install_hashes': {}, 'server_before': {}, 'server_after': {},
        'world_fingerprints': fingerprint(),
        'prior_worldserver': pack.p.load_json(pack.STAGE / 'prior-worldserver.json'),
        'migration': str(pack.MIGRATION), 'migration_sha256': pack.p.sha256(pack.MIGRATION)}
    for name, source in files().items():
        live = pack.p.CLIENT_DEFAULT / name
        report['before'][name] = pack.p.sha256(live) if live.exists() else None
        report['install_hashes'][name] = pack.p.sha256(source)
        if live.exists():
            dest = root / 'client' / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(live, dest)
            assert pack.p.sha256(dest) == report['before'][name]
            print('BACKED UP', name, flush=True)
    for name in pack.SERVER_TABLES:
        live = SERVER / (name + '.dbc')
        dest = root / 'server-dbc' / live.name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(live, dest)
        report['server_before'][name] = pack.p.sha256(live)
        report['server_after'][name] = pack.p.sha256(pack.STAGE / 'server/dbc' / live.name)
        assert pack.p.sha256(dest) == report['server_before'][name]
    shutil.copy2(pack.MIGRATION, root / pack.MIGRATION.name)
    rollback = '\n'.join(f'DELETE FROM `{table}` WHERE `{field}`={pack.RACE};' for table, field in TABLES.items())
    rollback += f"\nDELETE FROM `updates` WHERE `name`='{pack.MIGRATION.name}';\n"
    (root / 'rollback-world.sql').write_text(rollback, encoding='utf-8', newline='\n')
    (root / 'characters-appearance.tsv').write_text(db.sql(APPEARANCE, 'acore_characters'), encoding='utf-8')
    report['backup_checksums'] = {str(path.relative_to(root)): pack.p.sha256(path)
        for path in root.rglob('*') if path.is_file()}
    pack.save(root / 'install-plan.json', report)
    pack.save(pack.STAGE / 'install-plan.json', report)
    print('HASH-VERIFIED BACKUP', root, flush=True)


def install():
    preflight()
    running = subprocess.check_output(['docker', 'inspect', 'ac-worldserver', '--format',
                                      '{{.State.Running}}'], text=True).strip()
    if running != 'false':
        raise ValueError('Stop only ac-worldserver before this coordinated install')
    report = pack.p.load_json(pack.STAGE / 'install-plan.json')
    root = Path(report['backup'])
    for name, expected in report['backup_checksums'].items():
        assert pack.p.sha256(root / name) == expected, 'Rollback backup changed: ' + name
    for name, expected in report['before'].items():
        live = pack.p.CLIENT_DEFAULT / name
        assert (pack.p.sha256(live) if live.exists() else None) == expected, 'Live file changed: ' + name
        assert pack.p.sha256(Path(report['files'][name])) == report['install_hashes'][name]
    assert fingerprint() == report['world_fingerprints'], 'Unrelated startup rows changed'
    assert pack.p.sha256(pack.MIGRATION) == report['migration_sha256']
    characters = db.sql(APPEARANCE, 'acore_characters')
    (root / 'characters-at-install.tsv').write_text(characters, encoding='utf-8')
    receipt = hashlib.sha1(pack.MIGRATION.read_bytes()).hexdigest().upper()
    try:
        db.sql('START TRANSACTION;\n' + pack.MIGRATION.read_text() +
            f"\nINSERT INTO updates (name,hash,state) VALUES ('{pack.MIGRATION.name}','{receipt}','PENDING');\nCOMMIT;")
        for name, source in report['files'].items():
            target = pack.p.CLIENT_DEFAULT / name
            temporary = target.with_suffix(target.suffix + '.arakkoa-next')
            if temporary.exists():
                raise FileExistsError(temporary)
            shutil.copy2(source, temporary)
            assert pack.p.sha256(temporary) == report['install_hashes'][name]
            os.replace(temporary, target)
            print('INSTALLED', name, flush=True)
        for name in pack.SERVER_TABLES:
            source = pack.STAGE / 'server/dbc' / (name + '.dbc')
            target = SERVER / source.name
            shutil.copy2(source, target)
            assert pack.p.sha256(target) == report['server_after'][name]
        assert fingerprint() == report['world_fingerprints']
        assert db.sql(APPEARANCE, 'acore_characters') == characters
    except Exception:
        for name, expected in report['before'].items():
            target = pack.p.CLIENT_DEFAULT / name
            if expected is not None:
                shutil.copy2(root / 'client' / name, target)
            elif target.exists():
                assert pack.p.CLIENT_DEFAULT.resolve() in target.resolve().parents
                target.unlink()
        for name in pack.SERVER_TABLES:
            shutil.copy2(root / 'server-dbc' / (name + '.dbc'), SERVER / (name + '.dbc'))
        db.sql('START TRANSACTION;\n' + (root / 'rollback-world.sql').read_text() + '\nCOMMIT;')
        raise
    report.update(status='installed_awaiting_worldserver_recreation', receipt=receipt,
        installed_hashes={name: pack.p.sha256(pack.p.CLIENT_DEFAULT / name) for name in report['files']},
        character_appearance_sha256=hashlib.sha256(characters.encode()).hexdigest())
    pack.save(root / 'install-report.json', report)
    pack.save(pack.STAGE / 'last-install.json', report)
    print('MATCHED ARAKKOA PACKAGE INSTALLED', root, flush=True)


def verify():
    report = pack.p.load_json(pack.STAGE / 'last-install.json')
    build = pack.p.load_json(pack.STAGE / 'server-build.json')
    for name, expected in report['installed_hashes'].items():
        assert pack.p.sha256(pack.p.CLIENT_DEFAULT / name) == expected, name
    paths = ['/azerothcore/env/dist/data/dbc/' + name + '.dbc' for name in pack.SERVER_TABLES]
    hashes = subprocess.check_output(['docker', 'exec', 'ac-worldserver', 'sha256sum', *paths], text=True)
    for line in hashes.splitlines():
        digest, path = line.split(maxsplit=1)
        assert digest == report['server_after'][Path(path).stem], path
    image = subprocess.check_output(['docker', 'inspect', 'ac-worldserver', '--format',
                                    '{{.Image}} {{.State.Running}}'], text=True).strip()
    assert image == build['image'] + ' true', image
    assert fingerprint() == report['world_fingerprints']
    assert hashlib.sha256(db.sql(APPEARANCE, 'acore_characters').encode()).hexdigest() \
        == report['character_appearance_sha256']
    rows = db.sql('SELECT class FROM playercreateinfo WHERE race=68 ORDER BY class;')
    classes = [int(row) for row in rows.splitlines()]
    assert classes == pack.manifest()['classes']
    spells = db.sql('SELECT spell FROM custom_race_start_spell WHERE race=68 ORDER BY spell;').split()
    skill = db.sql('SELECT * FROM custom_race_start_skill WHERE race=68;').strip().split('\t')
    assert spells == ['669'] + [str(spell) for spell in pack.SPELLS] and skill[:4] == ['68', '0', '109', '0']
    receipt = db.sql(f"SELECT hash,state FROM updates WHERE name='{pack.MIGRATION.name}';").strip().split('\t')
    assert receipt == [report['receipt'], 'PENDING']
    files = pack.p.ClientFiles(str(pack.p.CLIENT_DEFAULT / 'Data'), 'enUS')
    try:
        races, provider = files.find(pack.p.DBC_ROOT + 'ChrRaces.dbc')
        table = pack.p.RawWdbc(races)
        row = next(row for row in table.records if pack.p._value(row, 0) == 68)
        assert [pack.p._value(row, i*4) for i in (2, 4, 5, 7, 13)] == [2, 60066, 60067, 1, 1]
        assert pack.p._string(table.strings, pack.p._value(row, 44)).decode() == pack.TOKEN
        for model in pack.manifest()['models'].values():
            blob, _ = files.find(model['model_path'])
            assert hashlib.sha256(blob).hexdigest() == \
                pack.p.load_json(pack.STAGE / 'report.json')['assets'][model['model_path']]
    finally:
        files.close()
    with socket.create_connection(('127.0.0.1', 8085), timeout=5) as connection:
        header = b''
        while len(header) < 4:
            data = connection.recv(4 - len(header))
            if not data:
                raise ValueError('Worldserver closed before the authentication challenge')
            header += data
        assert struct.unpack_from('<H', header, 2)[0] == 0x1ec, header.hex()
    ready = 'worldserver-daemon) ready...' in (pack.TARGET / 'env/dist/logs/Server.log').read_text(encoding='utf-8')
    assert ready, 'Worldserver has not reported ready'
    report.update(status='installed_and_server_ready_live_client_pending', server_image=build['image'],
        client_race_provider=provider, runtime_readback_passed=True, live_client_checked=False)
    pack.save(Path(report['backup']) / 'install-report.json', report)
    pack.save(pack.STAGE / 'last-install.json', report)
    pack.save(pack.STAGE / 'runtime-checks.json', {'passed': True, 'race': 68, 'server_image': build['image'],
        'world_authentication_challenge': True, 'mounted_dbc_hashes_match': True,
        'unrelated_world_data_preserved': True, 'saved_appearance_preserved': True, 'live_client_checked': False})
    print('VERIFIED installed Arakkoa, mounted DBCs, Common, preserved data and ready worldserver', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('preflight', 'backup', 'install', 'verify'))
    args = parser.parse_args()
    {'preflight': preflight, 'backup': backup, 'install': install, 'verify': verify}[args.action]()
