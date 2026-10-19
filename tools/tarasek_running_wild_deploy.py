"""Guarded matched installation, verification and rollback of the Drakkin self-mount update."""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import shutil
import socket
import struct

import tarasek_running_wild as r
import tarasek_deploy as d


def sources():
    report = d.read(r.STAGE / 'report.json')
    return {**{name: r.STAGE / 'client' / name for name in report['archives']},
            'Wow.exe': r.STAGE / 'Wow.exe', 'EsteriaAppearance.dll': r.STAGE / 'EsteriaAppearance.dll'}


def fingerprint():
    result = d.fingerprint()
    def hashed(query):
        return hashlib.sha256('\n'.join(sorted(d.sql(query).splitlines())).encode()).hexdigest()
    result['chrraces_dbc'] = hashed('SELECT * FROM chrraces_dbc WHERE ID<>12;')
    columns = [row.split('\t')[0] for row in d.sql('SHOW COLUMNS FROM chrraces_dbc;').splitlines()]
    selected = ','.join('`' + col + '`' for col in columns if col not in ('MaleDisplayId', 'FemaleDisplayId'))
    result['worgen_except_display'] = hashed(f'SELECT {selected} FROM chrraces_dbc WHERE ID=12;')
    for table, where in (('spell_dbc', 'ID NOT IN (110050,110051)'),
                         ('spell_script_names', 'spell_id NOT IN (110050,110051)'),
                         ('spell_ranks', 'first_spell_id<>110050')):
        result[table] = hashed(f'SELECT * FROM {table} WHERE {where};')
    return result


def worgen():
    return d.sql('SELECT MaleDisplayId,FemaleDisplayId FROM chrraces_dbc WHERE ID=12;')


def preflight():
    d.closed_client()
    baseline = d.read(r.WORK / 'baseline.json')
    report = d.read(r.STAGE / 'report.json')
    checks = d.read(r.STAGE / 'validation.json')
    assert checks['passed'] and checks['native_harnesses'] == 6
    for name, expected in checks['source_files'].items():
        assert d.digest(Path(name)) == expected, name
    assert d.digest(r.STAGE / 'EsteriaAppearance.dll') == checks['helper_sha256']
    assert d.digest(r.STAGE / 'Wow.exe') == checks['exe_sha256']
    for name, record in report['archives'].items():
        assert d.digest(d.CLIENT / name) == record['before'] == baseline['archives'][name]
        assert d.digest(sources()[name]) == record['after'] and record['readback_verified']
        assert record['bytes'] < 0x80000000
    for name, record in baseline['files'].items():
        if '\\' not in name:
            assert d.digest(d.CLIENT / name) == record['sha256'], name
    for name, expected in baseline['server_dbc'].items():
        assert d.digest(d.SERVER / name) == expected, name
    for name, expected in report['assets'].items():
        assert d.digest(r.STAGE / 'assets' / name) == expected
    assert r.SQL.read_bytes() == (r.STAGE / 'pending_db_world.sql').read_bytes()
    assert worgen() == baseline['worgen']
    assert d.sql('SELECT COUNT(*) FROM spell_dbc WHERE ID IN (110050,110051);').strip() == '0'
    assert d.sql(f"SELECT COUNT(*) FROM updates WHERE name='{r.MIGRATION}';").strip() == '0'
    server = d.read(r.STAGE / 'server-build.json')
    for name, expected in server['sources'].items():
        assert d.digest(Path(name)) == expected, name
    assert server['build_exit'] == 0
    assert d.command('docker', 'image', 'inspect', 'acore/ac-wotlk-worldserver:master', '--format', '{{.Id}}') \
        == server['image']
    environment = json.loads(d.command('docker', 'inspect', 'ac-worldserver', '--format', '{{json .Config.Env}}'))
    assert 'AC_UPDATES_ENABLE_DATABASES=0' in environment
    assert shutil.disk_usage(d.CLIENT).free > max(p.stat().st_size for p in sources().values()) + 64 * 2**20
    print('SELF-MOUNT PREFLIGHT PASS', flush=True)


def backup():
    preflight()
    root = Path('C:/EsteriaBackups') / ('Tarasek-running-wild-' + datetime.now().strftime('%Y%m%d-%H%M%S'))
    root.mkdir(parents=True)
    plan = {'backup': str(root), 'before': {}, 'after': {},
            'prior_worldserver': d.read(r.STAGE / 'prior-worldserver.json'),
            'server_dbc': d.read(r.WORK / 'baseline.json')['server_dbc'],
            'services_before': d.command('docker', 'compose', 'ps', '--format', 'json')}
    assert shutil.disk_usage(root).free > sum(p.stat().st_size for p in sources().values()) + 2**30
    for name, source in sources().items():
        plan['before'][name] = d.digest(d.CLIENT / name)
        plan['after'][name] = d.digest(source)
        target = root / 'client' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(d.CLIENT / name, target)
        assert d.digest(target) == plan['before'][name]
        print('BACKED UP', name, flush=True)
    for name in ('pending_db_world.sql', 'rollback-world.sql'):
        shutil.copy2(r.STAGE / name, root / name)
    d.save(root / 'install-plan.json', plan)
    d.save(r.STAGE / 'install-plan.json', plan)
    (root / 'ROLLBACK.txt').write_text(
        'Close the development client and stop only worldserver. From the repository:\n\n'
        'rtk proxy docker compose stop ac-worldserver\n'
        'rtk proxy python tools/tarasek_running_wild_deploy.py rollback\n'
        'rtk proxy docker tag ' + plan['prior_worldserver']['image'] + ' acore/ac-wotlk-worldserver:master\n'
        'rtk proxy docker compose up -d --no-deps --no-build --pull never --force-recreate ac-worldserver\n\n'
        'Rollback refuses if either new spell has been learned/saved. Audit and back up those two spell/aura\n'
        'records before removing them for a rollback; do not reset appearance or riding skill.\n'
        'Restoring the old SQL deliberately restores the stale Worgen display override too.\n', encoding='utf-8')
    print('VERIFIED BACKUP', root, flush=True)


def install():
    preflight()
    assert d.command('docker', 'inspect', 'ac-worldserver', '--format', '{{.State.Running}}') == 'false'
    plan = d.read(r.STAGE / 'install-plan.json')
    root = Path(plan['backup'])
    for name, expected in plan['before'].items():
        assert d.digest(root / 'client' / name) == d.digest(d.CLIENT / name) == expected
        assert d.digest(sources()[name]) == plan['after'][name]
    plan['characters'] = d.sql(d.APPEARANCE, 'characters')
    plan['fingerprints'] = fingerprint()
    plan['world_before'] = worgen()
    plan['migration_sha1'] = hashlib.sha1(r.SQL.read_bytes()).hexdigest().upper()
    (root / 'characters-at-install.tsv').write_text(plan['characters'], encoding='utf-8', newline='\n')
    d.save(r.STAGE / 'install-plan.json', plan)
    d.save(root / 'install-plan.json', plan)
    try:
        d.sql('START TRANSACTION;\n' + r.SQL.read_text() +
              f"\nINSERT INTO updates (name,hash,state) VALUES ('{r.MIGRATION}','{plan['migration_sha1']}','PENDING');"
              '\nCOMMIT;')
        assert worgen().strip() == '29422\t29423'
        for name, source in sources().items():
            d.replace(source, d.CLIENT / name, plan['after'][name])
            print('INSTALLED', name, flush=True)
        assert d.sql(d.APPEARANCE, 'characters') == plan['characters']
        assert fingerprint() == plan['fingerprints']
    except Exception:
        rollback(plan)
        raise
    plan['status'] = 'installed_awaiting_worldserver_start'
    d.save(r.STAGE / 'last-install.json', plan)
    d.save(root / 'install-report.json', plan)
    print('INSTALLED self-mount update and Worgen identity repair; saved appearance unchanged', flush=True)


def rollback(plan):
    d.closed_client()
    assert d.command('docker', 'inspect', 'ac-worldserver', '--format', '{{.State.Running}}') == 'false'
    assert d.sql('SELECT COUNT(*) FROM character_spell WHERE spell IN (110050,110051);',
                 'characters').strip() == '0', 'Audit/back up newly learned self-mount spells before rollback'
    assert d.sql('SELECT COUNT(*) FROM character_aura WHERE spell IN (110050,110051);',
                 'characters').strip() == '0', 'Audit/back up active self-mount auras before rollback'
    root = Path(plan['backup'])
    assert (root / 'rollback-world.sql').read_bytes() == (r.STAGE / 'rollback-world.sql').read_bytes()
    for name, expected in plan['before'].items():
        assert d.digest(root / 'client' / name) == expected
        assert d.digest(d.CLIENT / name) in (expected, plan['after'][name])
    d.sql('START TRANSACTION;\n' + (root / 'rollback-world.sql').read_text() +
          f"\nDELETE FROM updates WHERE name='{r.MIGRATION}' AND hash='{plan['migration_sha1']}';\nCOMMIT;")
    for name, expected in plan['before'].items():
        d.replace(root / 'client' / name, d.CLIENT / name, expected)
    plan['status'] = 'rolled_back_requires_prior_server_image'
    d.save(r.STAGE / 'last-install.json', plan)


def verify():
    plan = d.read(r.STAGE / 'last-install.json')
    report = d.read(r.STAGE / 'report.json')
    baseline = d.read(r.WORK / 'baseline.json')
    for name, expected in plan['after'].items():
        assert d.digest(d.CLIENT / name) == expected, name
    for name, record in baseline['files'].items():
        if '\\' not in name and name not in plan['after']:
            assert d.digest(d.CLIENT / name) == record['sha256'], name
    assert fingerprint() == plan['fingerprints']
    assert worgen().strip() == '29422\t29423'
    assert set(plan['characters'].splitlines()) <= set(d.sql(d.APPEARANCE, 'characters').splitlines())
    assert d.sql('SELECT ID,EffectAura_1,EffectAura_2,EffectMiscValue_1,EffectBasePoints_2 '
                 'FROM spell_dbc WHERE ID IN (110050,110051) ORDER BY ID;') \
        == '110050\t78\t32\t0\t59\n110051\t78\t32\t0\t99\n'
    assert d.sql('SELECT COUNT(*) FROM spell_script_names WHERE spell_id IN (110050,110051) '
                 "AND ScriptName='spell_drakkin_running_wild';").strip() == '2'
    for name, expected in plan['server_dbc'].items():
        assert d.command('docker', 'exec', 'ac-worldserver', 'sha256sum',
                         '/azerothcore/env/dist/data/dbc/' + name).split()[0] == expected, name
    prior = [json.loads(line) for line in plan['services_before'].splitlines()]
    current = {row['Name']: row['ID'] for row in (json.loads(line) for line in
               d.command('docker', 'compose', 'ps', '--format', 'json').splitlines())}
    assert all(current.get(row['Name']) == row['ID'] for row in prior if row['Name'] != 'ac-worldserver')
    image = d.read(r.STAGE / 'server-build.json')['image']
    assert d.command('docker', 'inspect', 'ac-worldserver', '--format', '{{.Image}} {{.State.Running}}') \
        == image + ' true'
    with r.t.p.ClientFiles(str(d.CLIENT / 'Data'), 'enUS') as files:
        for name, expected in report['assets'].items():
            assert r.t.sha(files.find(name)[0]) == expected, name
        for name in (r.t.MODEL, r.t.MODEL.replace('.m2', '00.skin')):
            assert r.t.sha(files.find(name)[0]) == baseline['files'][name]['sha256']
    with socket.create_connection(('127.0.0.1', 8085), timeout=5) as connection:
        header = b''
        while len(header) < 4:
            block = connection.recv(4 - len(header))
            assert block, 'Worldserver is still starting'
            header += block
        assert struct.unpack_from('<H', header, 2)[0] == 0x1ec
    plan['status'] = 'installed_and_server_ready_live_movement_and_worgen_relog_pending'
    d.save(r.STAGE / 'last-install.json', plan)
    d.save(Path(plan['backup']) / 'install-report.json', plan)
    report.update(installed=True, server_built=True, runtime_readback_passed=True,
                  live_accepted=False, state=plan['status'])
    d.save(r.STAGE / 'report.json', report)
    print('VERIFIED matched files, SQL identities, preserved appearance/model/DBCs/services and auth handshake')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('preflight', 'backup', 'install', 'rollback', 'verify'))
    action = parser.parse_args().action
    if action == 'rollback':
        rollback(d.read(r.STAGE / 'install-plan.json'))
    else:
        globals()[action]()
