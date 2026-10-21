"""Stage/install Centaur belt layers, clean cloak geometry and chest atlas-edge repairs."""

import argparse
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import shutil
import subprocess

import centaur_deploy as deploy
import centaur_v4 as art
import centaur_v4_deploy as previous
import test_centaur_v7 as checks

WORK = checks.WORK
NATIVE = ('Engine/Source/Retail/Centaur.h', 'WoW/Common/ComponentCore/RetailRace.cpp',
          'Tools/RetailAssets/tests.cpp')


def stage():
    checks.main()
    tests = deploy.NATIVE / 'build/retail-satchel/Release/RetailAssetTests.exe'
    for name, args in [('native-regression', []), ('native-art', ['--centaur-source',
            str(deploy.CLIENT / 'Data/Retail/RetailCasc.ini'), str(deploy.WORK)])]:
        with (WORK / (name + '.log')).open('w') as log:
            subprocess.run([str(tests), *args], check=True, stdout=log, stderr=subprocess.STDOUT)
    storm = deploy.pack.p.Storm(deploy.pack.p.DLL_DEFAULT)
    live, target = deploy.CLIENT / deploy.ASSET, WORK / 'client' / deploy.ASSET
    baseline = previous.archive_entries(storm, live)
    originals = WORK / 'baseline'
    originals.mkdir(exist_ok=True)
    payloads = {}
    for identifier in (4036647, 4081379):
        for extension in ('.m2', '00.skin'):
            name = f'{identifier}-clothing{extension}'
            key = 'custom/centaur/' + name
            (originals / name).write_bytes(baseline[key])
            payloads[key] = (deploy.pack.STAGE / 'assets/custom/centaur' / name).read_bytes()
        old = art.triangle_records(originals, identifier)
        new = art.triangle_records(deploy.pack.STAGE / 'assets/custom/centaur', identifier)
        assert set(new) == {g for g in old if g // 100 != 18} | {1805}
        assert all(new[g] == old[g] for g in new if g != 1 and g // 100 not in (15, 18))
        def without_u(counter):
            result = Counter()
            for tri, count in counter.items():
                result[tuple(v[:32] + v[36:] for v in tri)] += count
            return result
        assert without_u(new[1]) == without_u(old[1]), 'Body geometry/weights/V changed outside the chest U repair'
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(live, target)
    storm.replace_archive_entries(target, payloads)
    assert previous.archive_entries(storm, target) == {**baseline, **payloads}
    exe = deploy.NATIVE / 'bin/Win/WowClientRetailInventory.exe'
    meta_name = 'WowClientRetailVulkan.build.json'
    metadata = deploy.pack.p.load_json(deploy.CLIENT / meta_name)
    assert metadata['sha256'] == previous.digest(deploy.CLIENT / 'WowClientRetailVulkan.exe')
    native = {name: previous.digest(deploy.NATIVE / name) for name in NATIVE}
    for name, sha in native.items():
        row = next((r for r in metadata['source_files'] if r['path'] == name), None)
        if row is None:
            metadata['source_files'].append({'path': name, 'sha256': sha})
        else:
            row['sha256'] = sha
    metadata.update(sha256=previous.digest(exe), staged_at_utc=datetime.now(timezone.utc).isoformat(),
                    centaur_regional_armor={'receipt': str(WORK / 'receipt.json'), 'live_accepted': False})
    metadata['features'].append('Centaur four-leg belt layer, forward clean cloak hem and chest atlas gutter repair')
    deploy.pack.json_save(WORK / meta_name, metadata)
    files = {str(deploy.ASSET): {'source': str(target), 'before': previous.digest(live),
                               'after': previous.digest(target)}}
    for name, source in [('WowClientRetailVulkan.exe', exe), (meta_name, WORK / meta_name)]:
        files[name] = {'source': str(source), 'before': previous.digest(deploy.CLIENT / name),
                       'after': previous.digest(source)}
    report = {'files': files, 'native': native, 'checks_passed': True, 'unrelated_archive_entries_preserved': True,
              'generator_sha256': previous.digest(Path('tools/centaur_clothing.py')),
              'server_image_unchanged': deploy.docker('inspect', 'ac-worldserver', '--format', '{{.Image}}')}
    deploy.pack.json_save(WORK / 'stage.json', report)
    print('STAGED matched client/belt layers and four clothing entries; gloves, pants and boots preserved', flush=True)


def install():
    report = deploy.pack.p.load_json(WORK / 'stage.json')
    assert report['checks_passed'] and report['unrelated_archive_entries_preserved']
    assert previous.digest(Path('tools/centaur_clothing.py')) == report['generator_sha256']
    for name, sha in report['native'].items():
        assert previous.digest(deploy.NATIVE / name) == sha
    processes = subprocess.check_output(['tasklist', '/fo', 'csv', '/nh'], text=True).lower()
    assert not any('"' + n in processes for n in ('wowclient', 'mpqeditor', 'eclipse')), 'Close WoW first'
    backup = Path('G:/EsteriaBackups') / ('Centaur-v7-' + datetime.now().strftime('%Y%m%d-%H%M%S'))
    backup.mkdir()
    meta = WORK / 'WowClientRetailVulkan.build.json'
    metadata = deploy.pack.p.load_json(meta)
    metadata['backup_directory'] = str(backup)
    deploy.pack.json_save(meta, metadata)
    report['files'][meta.name]['after'] = previous.digest(meta)
    for name, row in report['files'].items():
        assert previous.digest(deploy.CLIENT / name) == row['before'], name
        assert previous.digest(Path(row['source'])) == row['after'], name
        saved = backup / name
        saved.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(deploy.CLIENT / name, saved)
        assert previous.digest(saved) == row['before']
    try:
        for name, row in report['files'].items():
            deploy.atomic_copy(Path(row['source']), deploy.CLIENT / name, row['after'])
    except Exception:
        for name, row in report['files'].items():
            deploy.atomic_copy(backup / name, deploy.CLIENT / name, row['before'])
        raise
    assert all(previous.digest(deploy.CLIENT / n) == r['after'] for n, r in report['files'].items())
    assert deploy.docker('inspect', 'ac-worldserver', '--format', '{{.Image}}') == report['server_image_unchanged']
    storm = deploy.pack.p.Storm(deploy.pack.p.DLL_DEFAULT)
    installed = previous.archive_entries(storm, deploy.CLIENT / deploy.ASSET)
    for identifier in (4036647, 4081379):
        for extension in ('.m2', '00.skin'):
            name = f'{identifier}-clothing{extension}'
            assert installed['custom/centaur/' + name] == (
                deploy.pack.STAGE / 'assets/custom/centaur' / name).read_bytes()
    report.update(installed=True, backup=str(backup), installed_at=datetime.now(timezone.utc).isoformat(),
                  installed_entry_readback_passed=True, live_visual_accepted=False)
    deploy.pack.json_save(WORK / 'receipt.json', report)
    deploy.pack.json_save(backup / 'receipt.json', report)
    print('INSTALLED matched Centaur v7 client/art; backup:', backup, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('stage', 'install'))
    args = parser.parse_args()
    stage() if args.action == 'stage' else install()
