"""Stage/install the female Centaur source belt/quiver suppression without changing armor assets."""

import argparse
from datetime import datetime, timezone
from pathlib import Path
import shutil
import subprocess

import centaur_deploy as deploy
from centaur_v4_deploy import digest

WORK = deploy.WORK / 'repair-v9'
NATIVE = ('Engine/Source/Retail/Centaur.h', 'Tools/RetailAssets/tests.cpp')


def stage(feature='Playable female Centaur permanently suppresses source waist belts and quiver',
          metadata_field='centaur_native_accessories'):
    WORK.mkdir(exist_ok=True)
    tests = deploy.NATIVE / 'build/retail-satchel/Release/RetailAssetTests.exe'
    for name, args in [('native-regression', []), ('native-art', ['--centaur-source',
            str(deploy.CLIENT / 'Data/Retail/RetailCasc.ini'), str(deploy.WORK)])]:
        with (WORK / (name + '.log')).open('w') as log:
            subprocess.run([str(tests), *args], check=True, stdout=log, stderr=subprocess.STDOUT)
    native = {name: digest(deploy.NATIVE / name) for name in NATIVE}
    exe = WORK / 'WowClientRetailVulkan.exe'
    shutil.copy2(deploy.NATIVE / 'bin/Win/WowClientRetailInventory.exe', exe)
    metadata = deploy.pack.p.load_json(deploy.CLIENT / 'WowClientRetailVulkan.build.json')
    assert metadata['sha256'] == digest(deploy.CLIENT / exe.name)
    for name, sha in native.items():
        row = next((r for r in metadata['source_files'] if r['path'] == name), None)
        if row is None:
            metadata['source_files'].append({'path': name, 'sha256': sha})
        else:
            row['sha256'] = sha
    metadata.update(sha256=digest(exe), staged_at_utc=datetime.now(timezone.utc).isoformat())
    metadata[metadata_field] = {'receipt': str(WORK / 'receipt.json'), 'live_accepted': False}
    metadata['features'].append(feature)
    meta = WORK / 'WowClientRetailVulkan.build.json'
    deploy.pack.json_save(meta, metadata)
    preserved = {str(path): digest(deploy.CLIENT / path) for path in
                 (deploy.ASSET, Path('Data/patch-Z.MPQ'), Path('Data/enUS/patch-enUS-Z.MPQ'))}
    report = {'files': {p.name: {'source': str(p), 'before': digest(deploy.CLIENT / p.name),
                                'after': digest(p)} for p in (exe, meta)},
              'native': native, 'preserved_archives': preserved, 'native_checks_passed': True,
              'server_image_unchanged': deploy.docker('inspect', 'ac-worldserver', '--format', '{{.Image}}')}
    deploy.pack.json_save(WORK / 'stage.json', report)
    print('STAGED native-only Centaur repair; armor archives preserved')


def install():
    report = deploy.pack.p.load_json(WORK / 'stage.json')
    assert report['native_checks_passed']
    processes = subprocess.check_output(['tasklist', '/fo', 'csv', '/nh'], text=True).lower()
    assert not any('"' + n in processes for n in ('wowclient', 'mpqeditor', 'eclipse')), 'Close WoW first'
    for name, sha in report['native'].items():
        assert digest(deploy.NATIVE / name) == sha
    for name, sha in report['preserved_archives'].items():
        assert digest(deploy.CLIENT / name) == sha
    revision = WORK.name.removeprefix('repair-')
    backup = Path('G:/EsteriaBackups') / (f'Centaur-{revision}-' + datetime.now().strftime('%Y%m%d-%H%M%S'))
    backup.mkdir()
    meta = WORK / 'WowClientRetailVulkan.build.json'
    metadata = deploy.pack.p.load_json(meta)
    metadata['backup_directory'] = str(backup)
    deploy.pack.json_save(meta, metadata)
    report['files'][meta.name]['after'] = digest(meta)
    for name, row in report['files'].items():
        assert digest(deploy.CLIENT / name) == row['before'] and digest(Path(row['source'])) == row['after']
        shutil.copy2(deploy.CLIENT / name, backup / name)
        assert digest(backup / name) == row['before']
    try:
        for name, row in report['files'].items():
            deploy.atomic_copy(Path(row['source']), deploy.CLIENT / name, row['after'])
        for name, row in report['files'].items():
            assert digest(deploy.CLIENT / name) == row['after']
        for name, sha in report['preserved_archives'].items():
            assert digest(deploy.CLIENT / name) == sha
        assert deploy.docker('inspect', 'ac-worldserver', '--format', '{{.Image}}') == report['server_image_unchanged']
    except Exception:
        for name, row in report['files'].items():
            deploy.atomic_copy(backup / name, deploy.CLIENT / name, row['before'])
        raise
    report.update(installed=True, backup=str(backup), installed_at=datetime.now(timezone.utc).isoformat(),
                  installed_hashes_verified=True, live_visual_accepted=False)
    deploy.pack.json_save(WORK / 'receipt.json', report)
    deploy.pack.json_save(backup / 'receipt.json', report)
    print('INSTALLED native Centaur repair; backup:', backup)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('stage', 'install'))
    args = parser.parse_args()
    stage() if args.action == 'stage' else install()
