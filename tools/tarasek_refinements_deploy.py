"""Install the follow-up as a matched client/helper/server update without changing saved appearance."""

import argparse
from datetime import datetime
import json
from pathlib import Path
import shutil
import socket
import struct

import tarasek_deploy as d
import tarasek_refinements as r


def sources():
    report = d.read(r.STAGE / 'report.json')
    result = {name: r.STAGE / 'client' / name for name in report['archives']}
    for name, digest in report['catalogs'].items():
        if digest != d.digest(r.BASE / name):
            result[name] = r.STAGE / name
    result['EsteriaAppearance.dll'] = r.STAGE / 'EsteriaAppearance.dll'
    return result


def preflight(require_server=False):
    d.closed_client()
    report = d.read(r.STAGE / 'report.json')
    baseline = d.read(r.WORK / 'baseline.json')
    for name, expected in report['archives'].items():
        assert d.digest(d.CLIENT / name) == expected['before'], name
        assert d.digest(r.STAGE / 'client' / name) == expected['after'], name
        assert expected['readback_verified'] and expected['bytes'] < 0x80000000
    for name, expected in baseline['files'].items():
        if '\\' not in name:
            assert d.digest(d.CLIENT / name) == expected['sha256'], name
    reserve = max(path.stat().st_size for path in sources().values()) + 64 * 1024 * 1024
    assert shutil.disk_usage(d.CLIENT).free > reserve
    validation = d.read(r.STAGE / 'validation.json')
    assert validation['passed']
    native = d.read(r.STAGE / 'native-checks.json')
    assert native['all_passed'] and d.digest(r.STAGE / 'EsteriaAppearance.dll') == native['dll_sha256']
    for receipt in (report, validation, native):
        for name, expected in receipt['source_files'].items():
            assert d.digest(Path(name)) == expected, name
    for name, expected in native['catalogs'].items():
        assert d.digest(r.STAGE / name) == expected, name
    if require_server:
        server = d.read(r.STAGE / 'server-build.json')
        assert d.command('docker', 'image', 'inspect', 'acore/ac-wotlk-worldserver:master', '--format', '{{.Id}}') \
            == server['image']
        assert d.digest(d.ROOT / 'src/server/shared/CreatureAppearance.h') == server['header_sha256']
    environment = json.loads(d.command('docker', 'inspect', 'ac-worldserver', '--format', '{{json .Config.Env}}'))
    assert 'AC_UPDATES_ENABLE_DATABASES=0' in environment
    print('REFINEMENT PREFLIGHT PASS', flush=True)


def backup():
    preflight()
    root = Path('R:/EsteriaBackups') / ('Tarasek-refinements-' + datetime.now().strftime('%Y%m%d-%H%M%S'))
    root.mkdir(parents=True)
    plan = {'backup': str(root), 'before': {}, 'after': {},
            'prior_worldserver': d.read(r.WORK / 'prior-worldserver.json'),
            'services_before': d.command('docker', 'compose', 'ps', '--format', 'json'),
            'server_dbc_hashes': {name: d.digest(d.SERVER / (name + '.dbc'))
                                  for name in ('ChrRaces', 'CreatureModelData', 'CreatureDisplayInfo',
                                               'CharSections', 'BarberShopStyle')}}
    for name, source in sources().items():
        live = d.CLIENT / name
        assert live.exists()
        plan['before'][name] = d.digest(live)
        plan['after'][name] = d.digest(source)
        target = root / 'client' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(live, target)
        assert d.digest(target) == plan['before'][name]
        print('BACKED UP', name, flush=True)
    d.save(root / 'install-plan.json', plan)
    d.save(r.STAGE / 'install-plan.json', plan)
    instructions = ('Close the development client and stop only ac-worldserver. From the repository:\n\n'
        'rtk proxy docker compose stop ac-worldserver\n'
        'rtk proxy python tools/tarasek_refinements_deploy.py rollback\n'
        'rtk proxy docker tag ' + plan['prior_worldserver']['image'] + ' acore/ac-wotlk-worldserver:master\n'
        'rtk proxy docker compose up -d --no-deps --no-build --pull never --force-recreate ac-worldserver\n\n'
        'This update has no SQL migration. New eye indexes 1..6 require the new helper/server; if any have\n'
        'been saved, audit and explicitly map them to original index 0 before restoring the old codec.\n')
    (root / 'ROLLBACK.txt').write_text(instructions, encoding='utf-8', newline='\n')
    print('VERIFIED REFINEMENT BACKUP', root, flush=True)


def install():
    preflight(True)
    assert d.command('docker', 'inspect', 'ac-worldserver', '--format', '{{.State.Running}}') == 'false'
    plan = d.read(r.STAGE / 'install-plan.json')
    root = Path(plan['backup'])
    for name, expected in plan['before'].items():
        assert d.digest(root / 'client' / name) == d.digest(d.CLIENT / name) == expected, name
        assert d.digest(sources()[name]) == plan['after'][name], name
    plan['characters'] = d.sql(d.APPEARANCE, 'characters')
    plan['world_rows'] = d.world_rows()
    plan['fingerprints'] = d.fingerprint()
    (root / 'characters-at-install.tsv').write_text(plan['characters'], encoding='utf-8', newline='\n')
    d.save(r.STAGE / 'install-plan.json', plan)
    d.save(root / 'install-plan.json', plan)
    try:
        for name, source in sources().items():
            d.replace(source, d.CLIENT / name, plan['after'][name])
            print('INSTALLED', name, flush=True)
        assert d.sql(d.APPEARANCE, 'characters') == plan['characters']
        assert d.world_rows() == plan['world_rows'] and d.fingerprint() == plan['fingerprints']
    except Exception:
        rollback(plan)
        raise
    plan['status'] = 'installed_awaiting_worldserver_start'
    d.save(r.STAGE / 'last-install.json', plan)
    d.save(root / 'install-report.json', plan)
    print('REFINEMENTS INSTALLED; no SQL or saved-character changes', flush=True)


def rollback(plan):
    assert d.command('docker', 'inspect', 'ac-worldserver', '--format', '{{.State.Running}}') == 'false'
    d.closed_client()
    # Expanding a former constant is index-compatible going forward. Reverting after a new eye was saved is not.
    assert d.sql('SELECT COUNT(*) FROM characters WHERE race=66 AND gender=0 AND hairColor<>0;',
                 'characters').strip() == '0', 'Audit/map newly saved eye choices before restoring the old codec'
    root = Path(plan['backup'])
    for name, expected in plan['before'].items():
        assert d.digest(root / 'client' / name) == expected, name
        assert d.digest(d.CLIENT / name) in (expected, plan['after'][name]), name
        d.replace(root / 'client' / name, d.CLIENT / name, expected)
    plan['status'] = 'rolled_back_files_requires_prior_server_image'
    d.save(r.STAGE / 'last-install.json', plan)
    print('Restored exact prior client package; restore server image', plan['prior_worldserver']['image'])


def verify():
    plan = d.read(r.STAGE / 'last-install.json')
    report = d.read(r.STAGE / 'report.json')
    for name, expected in plan['after'].items():
        assert d.digest(d.CLIENT / name) == expected, name
    for name, info in d.read(r.WORK / 'baseline.json')['files'].items():
        if '\\' not in name and name not in plan['after']:
            assert d.digest(d.CLIENT / name) == info['sha256'], name
    assert d.fingerprint() == plan['fingerprints'] and d.world_rows() == plan['world_rows']
    assert set(plan['characters'].splitlines()) <= set(d.sql(d.APPEARANCE, 'characters').splitlines())
    for name, expected in plan['server_dbc_hashes'].items():
        path = '/azerothcore/env/dist/data/dbc/' + name + '.dbc'
        assert d.command('docker', 'exec', 'ac-worldserver', 'sha256sum', path).split()[0] == expected, name
    prior = [json.loads(line) for line in plan['services_before'].splitlines()]
    current = {row['Name']: row['ID'] for row in (json.loads(line) for line in
               d.command('docker', 'compose', 'ps', '--format', 'json').splitlines())}
    assert all(current.get(row['Name']) == row['ID'] for row in prior if row['Name'] != 'ac-worldserver')
    image = d.read(r.STAGE / 'server-build.json')['image']
    assert d.command('docker', 'inspect', 'ac-worldserver', '--format', '{{.Image}} {{.State.Running}}') \
        == image + ' true'
    files = r.t.p.ClientFiles(str(d.CLIENT / 'Data'), 'enUS')
    try:
        for name, expected in report['assets'].items():
            raw, provider = files.find(name)
            assert r.t.sha(raw) == expected, (name, provider)
        for name in r.t.SKINS:
            key = 'custom\\tarasek\\creature\\tarasek\\tarasek_' + name + '.blp'
            assert files.find(key)[0] == (r.BASE / key).read_bytes(), key
    finally:
        files.close()
    with socket.create_connection(('127.0.0.1', 8085), timeout=5) as connection:
        header = b''
        while len(header) < 4:
            block = connection.recv(4 - len(header))
            assert block, 'Worldserver is still starting'
            header += block
        assert struct.unpack_from('<H', header, 2)[0] == 0x1ec
    plan['status'] = 'installed_and_server_ready_live_refinement_check_pending'
    d.save(r.STAGE / 'last-install.json', plan)
    d.save(Path(plan['backup']) / 'install-report.json', plan)
    report.update(state=plan['status'], installed=True, server_built=True, runtime_readback_passed=True,
                  live_accepted=False)
    d.save(r.STAGE / 'report.json', report)
    print('VERIFIED refinements, preserved characters/DBCs/services, source skins and authentication handshake')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('preflight', 'backup', 'install', 'rollback', 'verify'))
    action = parser.parse_args().action
    if action == 'rollback':
        rollback(d.read(r.STAGE / 'install-plan.json'))
    else:
        globals()[action]()
