"""Back up and install the checked Alliance-only Drakkin update while worldserver is stopped."""

import argparse
from datetime import datetime
import hashlib
from pathlib import Path
import shutil
import subprocess

import drakkin_options_update as u
import drakkin_deploy as old
from test_drakkin_options_update import check

p = u.p
NATIVE = Path('G:/Kb1011/EsteriaAppearance.dll')


def digest(data):
    return hashlib.sha256(data.encode()).hexdigest()


def targets():
    report = p.load_json(u.STAGE / 'report.json')
    return {**{str(p.CLIENT_DEFAULT / name): u.STAGE / 'client' / name for name in report['archives']},
            str(p.CLIENT_DEFAULT / 'EsteriaAppearance.bin'): u.STAGE / 'EsteriaAppearance.bin',
            str(p.CLIENT_DEFAULT / 'EsteriaAppearance.dll'): NATIVE,
            **{str(p.SERVER_DBC_ROOT / path.name): path for path in (u.STAGE / 'server-dbc').glob('*.dbc')}}


def world_fingerprints():
    return {table: digest('\n'.join(sorted(old.raw_sql(
        f'SELECT * FROM `{table}` WHERE `{field}` NOT IN (66,67);').splitlines())))
        for table, field in (('chrraces_dbc', 'ID'), ('playercreateinfo', 'race'))}


def preflight():
    assert old.inspect('ac-worldserver', '{{.State.Running}}') == 'false', 'Worldserver must be offline'
    processes = subprocess.check_output(['tasklist', '/FO', 'CSV', '/NH'], text=True).lower()
    assert not any(name in processes for name in ('wow.exe', 'eclipse.exe', 'mpqeditor.exe')), 'Close clients/editors'
    report = p.load_json(u.STAGE / 'report.json')
    for name, expected in report['baseline_hashes'].items():
        assert p.sha256(p.CLIENT_DEFAULT / name) == expected, 'Archive baseline changed: ' + name
        assert p.sha256(u.STAGE / 'client' / name) == report['archives'][name], 'Staged archive changed: ' + name
    for name, expected in report['runtime_baselines'].items():
        assert p.sha256(p.CLIENT_DEFAULT / name) == expected, 'Runtime changed: ' + name
    for name, expected in report['server_baselines'].items():
        assert p.sha256(p.SERVER_DBC_ROOT / (name + '.dbc')) == expected, 'Server DBC changed: ' + name
    for name, expected in report['sources'].items():
        assert p.sha256(Path(name)) == expected, 'Supplied art changed: ' + name
    build = p.load_json(u.STAGE / 'build-checks.json')
    assert build['native_passed'] and build['native_sha256'] == p.sha256(NATIVE)
    assert build['server_image'] == subprocess.check_output(
        ['docker', 'image', 'inspect', 'acore/ac-wotlk-worldserver:master', '--format', '{{.Id}}'], text=True).strip()
    for name, expected in build['source_files'].items():
        assert p.sha256(p.ROOT / name) == expected, 'Build source changed: ' + name
    assert old.raw_sql('SELECT COUNT(*) FROM characters WHERE race=67;', 'acore_characters').strip() == '0'
    assert old.raw_sql(f"SELECT COUNT(*) FROM updates WHERE name='{u.SQL.name}';").strip() == '0'
    check()


def backup():
    preflight()
    root = Path('G:/EsteriaBackups') / ('Drakkin-Alliance-options-' + datetime.now().strftime('%Y%m%d-%H%M%S'))
    root.mkdir(parents=True)
    plan = {'backup': str(root), 'files': {}, 'before': {}, 'after': {},
            'world_fingerprints': world_fingerprints(),
            'characters': digest(old.raw_sql(old.APPEARANCE, 'acore_characters')),
            'prior_image': old.inspect('ac-worldserver', '{{.Image}}'),
            'migration_sha256': p.sha256(u.SQL)}
    for index, (name, source) in enumerate(targets().items()):
        live = Path(name)
        saved = root / 'files' / (str(index) + '-' + live.name)
        saved.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(live, saved)
        expected = p.sha256(live)
        assert p.sha256(saved) == expected
        plan['files'][name] = {'source': str(source), 'backup': str(saved)}
        plan['before'][name] = expected
        plan['after'][name] = p.sha256(source)
    rollback = "DELETE FROM `chrraces_dbc` WHERE `ID` IN (66,67);\n"
    rollback += "DELETE FROM `playercreateinfo` WHERE `race`=67;\n"
    for table, where in (('chrraces_dbc', 'ID IN (66,67)'), ('playercreateinfo', 'race=67')):
        command = ['docker', 'exec', 'ac-database', 'sh', '-c',
                   'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysqldump -uroot --no-create-info '
                   '--skip-add-locks --skip-disable-keys --skip-comments '
                   '--set-gtid-purged=OFF --column-statistics=0 '
                   f'--where="{where}" acore_world {table}']
        rollback += subprocess.check_output(command).decode('utf-8', 'replace') + '\n'
    rollback += f"DELETE FROM `updates` WHERE `name`='{u.SQL.name}';\n"
    (root / 'rollback-world.sql').write_text(rollback, encoding='utf-8', newline='\n')
    plan['rollback_sha256'] = p.sha256(root / 'rollback-world.sql')
    shutil.copy2(u.SQL, root / u.SQL.name)
    (root / 'character-appearance-before.tsv').write_text(old.raw_sql(old.APPEARANCE, 'acore_characters'),
                                                        encoding='utf-8', newline='\n')
    u.k.save(root / 'install-plan.json', plan)
    u.k.save(u.STAGE / 'install-plan.json', plan)
    print('HASH-VERIFIED BACKUP', root, flush=True)


def install():
    preflight()
    plan = p.load_json(u.STAGE / 'install-plan.json')
    root = Path(plan['backup'])
    assert p.sha256(root / 'rollback-world.sql') == plan['rollback_sha256']
    assert p.sha256(u.SQL) == plan['migration_sha256']
    assert world_fingerprints() == plan['world_fingerprints']
    assert digest(old.raw_sql(old.APPEARANCE, 'acore_characters')) == plan['characters']
    for name, paths in plan['files'].items():
        assert p.sha256(Path(name)) == plan['before'][name]
        assert p.sha256(Path(paths['backup'])) == plan['before'][name]
        assert p.sha256(Path(paths['source'])) == plan['after'][name]
    receipt = hashlib.sha1(u.SQL.read_bytes()).hexdigest().upper()
    try:
        old.raw_sql('START TRANSACTION;\n' + u.SQL.read_text() +
                    f"INSERT INTO updates (name,hash,state) VALUES ('{u.SQL.name}','{receipt}','PENDING');\nCOMMIT;")
        for name, paths in plan['files'].items():
            live = Path(name)
            # Clients are closed and every target has a verified rollback copy; avoid another archive-sized copy.
            shutil.copy2(paths['source'], live)
            assert p.sha256(live) == plan['after'][name]
        assert world_fingerprints() == plan['world_fingerprints']
        assert digest(old.raw_sql(old.APPEARANCE, 'acore_characters')) == plan['characters']
        assert p.sha256(p.CLIENT_DEFAULT / 'Wow.exe') == p.load_json(u.STAGE / 'report.json')[
            'runtime_baselines']['Wow.exe']
    except BaseException:
        for name, paths in plan['files'].items():
            shutil.copy2(paths['backup'], name)
        old.raw_sql('START TRANSACTION;\n' + (root / 'rollback-world.sql').read_text() + '\nCOMMIT;')
        raise
    plan['receipt'] = receipt
    plan['installed'] = {name: p.sha256(Path(name)) for name in plan['files']}
    u.k.save(root / 'installed.json', plan)
    u.k.save(u.STAGE / 'installed.json', plan)
    print('INSTALLED matching client and server data; saved appearance unchanged', flush=True)


def verify():
    plan = p.load_json(u.STAGE / 'installed.json')
    for name, expected in plan['installed'].items():
        assert p.sha256(Path(name)) == expected, name
    assert world_fingerprints() == plan['world_fingerprints']
    assert digest(old.raw_sql(old.APPEARANCE, 'acore_characters')) == plan['characters']
    rows = old.raw_sql('SELECT ID,Flags,FactionID,MaleDisplayId,FemaleDisplayId,ClientPrefix '
                       'FROM chrraces_dbc WHERE ID IN (66,67) ORDER BY ID;').splitlines()
    assert rows == ['66\t14\t1\t60064\t60064\tKb', '67\t15\t2\t60065\t60065\tKb'], rows
    assert old.raw_sql('SELECT COUNT(*) FROM playercreateinfo WHERE race=67;').strip() == '0'
    assert old.raw_sql('SELECT COUNT(*) FROM playercreateinfo WHERE race=66;').strip() == '10'
    build = p.load_json(u.STAGE / 'build-checks.json')
    assert old.inspect('ac-worldserver', '{{.Image}} {{.State.Running}}') == build['server_image'] + ' true'
    paths = ['/azerothcore/env/dist/data/dbc/' + path.name for path in (u.STAGE / 'server-dbc').glob('*.dbc')]
    hashes = subprocess.check_output(['docker', 'exec', 'ac-worldserver', 'sha256sum', *paths], text=True)
    for line in hashes.splitlines():
        expected, name = line.split(maxsplit=1)
        assert expected == p.sha256(u.STAGE / 'server-dbc' / Path(name).name)
    report = p.load_json(u.STAGE / 'report.json')
    report.update(status='installed_runtime_verified_live_client_pending', installed=True,
                  backup=plan['backup'], saved_character_appearance_preserved=True,
                  server_image=build['server_image'])
    u.k.save(u.STAGE / 'report.json', report)
    print('VERIFIED Alliance-only world rows, mounted DBCs, image, file hashes and saved appearance', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('backup', 'install', 'verify'))
    args = parser.parse_args()
    {'backup': backup, 'install': install, 'verify': verify}[args.action]()
