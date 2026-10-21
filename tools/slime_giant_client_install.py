"""Install or restore the validated SlimeSkeleton client package with per-file hash backups."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

import slime_giant_race_pack as pack

CLIENT = pack.p.CLIENT_DEFAULT
NATIVE = Path('R:/Users/Zach/Documents/GitHub/wowdecomp')
PLAN = pack.WORK / 'client-install-plan.json'


def save(path, value):
    pack.save(path, (json.dumps(value, indent=2) + '\n').encode())


def closed():
    processes = subprocess.check_output(['tasklist', '/FO', 'CSV', '/NH'], text=True).lower()
    import re
    assert not re.search(r'"(?:wowclient[^"\\]*|wow|wow64|eclipse)\.exe"', processes), \
        'Close the game before replacing client files'


def prepare():
    closed()
    validation = pack.p.load_json(pack.WORK / 'native-validation/validation.json')
    assert validation['all_passed'] and validation['model'] == 3490792
    packages = sorted((pack.WORK / 'packages').glob('*/package-receipt.json'))
    package = pack.p.load_json(packages[-1])
    assets = {str(path.relative_to(pack.STAGE / 'assets')).replace('/', '\\'): path.read_bytes()
              for path in (pack.STAGE / 'assets').rglob('*') if path.is_file()}
    asset_info = package['archives'][str(Path('Data/Patch-SG.MPQ'))]
    storm = pack.p.Storm(pack.p.DLL_DEFAULT)
    storm.replace_archive_entries(Path(asset_info['path']), assets)
    handle = storm.open_archive(Path(asset_info['path']))
    try:
        for name, data in assets.items():
            assert storm.read(handle, name) == data
    finally:
        storm.dll.SFileCloseArchive(handle)
    asset_info['sha256'] = pack.p.sha256(Path(asset_info['path']))
    package['ready_for_install'] = True
    package['source_model'] = 3490792
    save(packages[-1], package)
    files = {}
    for name, info in package['archives'].items():
        target = CLIENT / name
        assert (pack.p.sha256(target) if target.exists() else None) == info['baseline'], name
        assert pack.p.sha256(Path(info['path'])) == info['sha256'], name
        files[name] = Path(info['path'])
    source = NATIVE / 'bin/Win/WowClientRetailInventory.exe'
    assert pack.p.sha256(source) == validation['client_executable_sha256'], 'Validated native build changed'
    files['WowClientRetailVulkan.exe'] = source
    metadata_path = CLIENT / 'WowClientRetailVulkan.build.json'
    metadata = pack.p.load_json(metadata_path)
    assert metadata['sha256'] == pack.p.sha256(CLIENT / 'WowClientRetailVulkan.exe')
    root = CLIENT / '_backups' / ('slime-giant-' + datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S'))
    root.mkdir(parents=True, exist_ok=False)
    metadata.update(sha256=pack.p.sha256(source), backup_directory=str(root),
                    staged_at_utc=datetime.now(timezone.utc).isoformat(), live_acceptance='pending',
                    slime_giant={'source_model': 3490792, 'races': [71, 72],
                                 'choices': ['Slime Color', 'Slime Drip'], 'validation': str(validation)})
    metadata['features'].append('SlimeSkeleton races 71/72: five colors, drip, Kul Tiran armor UVs and sockets')
    staged_metadata = pack.STAGE / metadata_path.name
    save(staged_metadata, metadata)
    files[metadata_path.name] = staged_metadata
    entries = []
    for name, source in files.items():
        target = CLIENT / name
        entry = {'relative': name, 'source': str(source), 'sha256': pack.p.sha256(source),
                 'existed': target.exists(), 'before': pack.p.sha256(target) if target.exists() else None}
        if target.exists():
            backup = root / name
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(target, backup)
            assert pack.p.sha256(backup) == entry['before'], name
            entry['backup'] = str(backup)
        entries.append(entry)
    plan = {'backup': str(root), 'files': entries, 'installed': False}
    save(root / 'client-install-plan.json', plan)
    save(PLAN, plan)
    print('PREPARED client rollback:', root, flush=True)


def install():
    closed()
    plan = pack.p.load_json(PLAN)
    for entry in plan['files']:
        target = CLIENT / entry['relative']
        assert (pack.p.sha256(target) if target.exists() else None) == entry['before'], entry['relative']
        assert pack.p.sha256(Path(entry['source'])) == entry['sha256']
    try:
        for entry in plan['files']:
            target = CLIENT / entry['relative']
            temporary = target.with_name(target.name + '.slimegiant-next')
            shutil.copy2(entry['source'], temporary)
            assert pack.p.sha256(temporary) == entry['sha256']
            temporary.replace(target)
            assert pack.p.sha256(target) == entry['sha256']
    except Exception:
        rollback()
        raise
    plan['installed'] = True
    save(pack.WORK / 'client-install-receipt.json', plan)
    save(Path(plan['backup']) / 'client-install-receipt.json', plan)
    print('INSTALLED hash-verified matched client:', CLIENT, flush=True)


def rollback():
    closed()
    plan = pack.p.load_json(PLAN)
    for entry in plan['files']:
        target = CLIENT / entry['relative']
        if entry['existed']:
            assert pack.p.sha256(Path(entry['backup'])) == entry['before']
            shutil.copy2(entry['backup'], target)
            assert pack.p.sha256(target) == entry['before']
        elif target.exists():
            assert pack.p.sha256(target) == entry['sha256'], 'New archive has unrelated later changes'
            target.unlink()
    print('Restored matched client backup:', plan['backup'])


def repair_assets():
    closed()
    receipt = pack.WORK / 'client-install-receipt.json'
    result = pack.p.load_json(receipt)
    entry = next(row for row in result['files'] if row['relative'] == str(Path('Data/Patch-SG.MPQ')))
    live = CLIENT / entry['relative']
    assert pack.p.sha256(live) == entry['sha256'], 'Installed asset archive changed'
    saved = Path(result['backup']) / ('Patch-SG-' + entry['sha256'][:12] + '.MPQ')
    if not saved.exists():
        shutil.copy2(live, saved)
    assert pack.p.sha256(saved) == entry['sha256']
    temporary = live.with_name(live.name + '.slimegiant-next')
    shutil.copy2(live, temporary)
    assets = {str(path.relative_to(pack.STAGE / 'assets')).replace('/', '\\'): path.read_bytes()
              for path in (pack.STAGE / 'assets').rglob('*') if path.is_file()}
    storm = pack.p.Storm(pack.p.DLL_DEFAULT)
    storm.replace_archive_entries(temporary, assets)
    handle = storm.open_archive(temporary)
    try:
        for name, data in assets.items():
            assert storm.read(handle, name) == data
    finally:
        storm.dll.SFileCloseArchive(handle)
    expected = pack.p.sha256(temporary)
    temporary.replace(live)
    assert pack.p.sha256(live) == expected
    entry['sha256'] = expected
    save(receipt, result)
    save(Path(result['backup']) / receipt.name, result)
    plan = pack.p.load_json(PLAN)
    next(row for row in plan['files'] if row['relative'] == entry['relative'])['sha256'] = expected
    save(PLAN, plan)
    print('Installed checked asset revision:', expected)


def repair_native():
    closed()
    source = NATIVE / 'bin/Win/WowClientRetailInventory.exe'
    receipt = pack.WORK / 'client-install-receipt.json'
    result = pack.p.load_json(receipt)
    entry = next(row for row in result['files'] if row['relative'] == 'WowClientRetailVulkan.exe')
    target = CLIENT / entry['relative']
    assert pack.p.sha256(target) == entry['sha256'], 'Installed native client changed'
    metadata = CLIENT / 'WowClientRetailVulkan.build.json'
    data = pack.p.load_json(metadata)
    assert data['sha256'] == entry['sha256'], 'Native build metadata differs'
    backup = CLIENT / '_backups' / ('slime-login-memory-' +
        datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S'))
    backup.mkdir(parents=True, exist_ok=False)
    for path in (target, metadata):
        shutil.copy2(path, backup / path.name)
        assert pack.p.sha256(backup / path.name) == pack.p.sha256(path)
    expected = pack.p.sha256(source)
    data.update(sha256=expected, backup_directory=str(backup), live_acceptance='pending',
                staged_at_utc=datetime.now(timezone.utc).isoformat())
    data['features'].append('Vulkan optional terrain CPU shadow can fail without Storm fatal-new exit')
    source_file = NATIVE / 'Engine/Source/Gx/CGxDeviceVulkan/CGxDeviceVulkanPool.cpp'
    data['slime_login_memory_fix'] = {'source': str(source_file), 'sha256': pack.p.sha256(source_file),
                                     'backup': str(backup)}
    temporary = target.with_name(target.name + '.slimegiant-next')
    shutil.copy2(source, temporary)
    assert pack.p.sha256(temporary) == expected
    temporary.replace(target)
    save(metadata, data)
    entry.update(sha256=expected, source=str(source))
    next(row for row in result['files'] if row['relative'] == metadata.name)['sha256'] = pack.p.sha256(metadata)
    save(receipt, result)
    plan = pack.p.load_json(PLAN)
    for row in plan['files']:
        installed = next(item for item in result['files'] if item['relative'] == row['relative'])
        row['sha256'] = installed['sha256']
    save(PLAN, plan)
    save(backup / 'repair-receipt.json', {'backup': str(backup), 'sha256': expected,
                                        'source': str(source), 'live_acceptance': 'pending'})
    print('Installed native memory fallback:', expected, 'backup:', backup, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare', 'install', 'rollback', 'repair-assets', 'repair-native'))
    args = parser.parse_args()
    {'prepare': prepare, 'install': install, 'rollback': rollback, 'repair-assets': repair_assets,
     'repair-native': repair_native}[args.action]()
