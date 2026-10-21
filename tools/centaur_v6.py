"""Stage/install only the Centaur regional armor collection repair with archive preservation checks."""

import argparse
from datetime import datetime, timezone
from pathlib import Path
import shutil
import subprocess

import centaur_deploy as deploy
import centaur_v4 as art
import centaur_v4_deploy as previous
import test_centaur_v6 as checks

WORK = checks.WORK


def stage():
    checks.main()
    storm = deploy.pack.p.Storm(deploy.pack.p.DLL_DEFAULT)
    live, target = deploy.CLIENT / deploy.ASSET, WORK / 'client' / deploy.ASSET
    baseline = previous.archive_entries(storm, live)
    originals = WORK / 'baseline'
    originals.mkdir(exist_ok=True)
    payloads = {}
    geometry = {}
    for identifier in (4036647, 4081379):
        for extension in ('.m2', '00.skin'):
            name = f'{identifier}-clothing{extension}'
            key = 'custom/centaur/' + name
            (originals / name).write_bytes(baseline[key])
            payloads[key] = (deploy.pack.STAGE / 'assets/custom/centaur' / name).read_bytes()
        old = art.triangle_records(originals, identifier)
        new = art.triangle_records(deploy.pack.STAGE / 'assets/custom/centaur', identifier)
        assert set(new) == set(old) - {401}
        retained = [g for g in new if g != 1 and g // 100 not in (4, 8, 15)]
        assert all(new[g] == old[g] for g in retained), 'Unrelated accessory/hoof vertex records changed'
        geometry[str(identifier)] = {'unchanged_geosets': retained, 'removed_naked_duplicate': 401}
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(live, target)
    storm.replace_archive_entries(target, payloads)
    assert previous.archive_entries(storm, target) == {**baseline, **payloads}
    metadata_path = deploy.CLIENT / 'WowClientRetailVulkan.build.json'
    metadata = deploy.pack.p.load_json(metadata_path)
    exe_hash = previous.digest(deploy.CLIENT / 'WowClientRetailVulkan.exe')
    assert metadata['sha256'] == exe_hash
    metadata['centaur_regional_armor'] = {'receipt': str(WORK / 'receipt.json'), 'live_accepted': False}
    metadata['features'].append('Centaur anatomical UV regions, full gloves, stable cuffs and upper-leg pants')
    deploy.pack.json_save(WORK / metadata_path.name, metadata)
    report = {'files': {str(deploy.ASSET): {'source': str(target), 'before': previous.digest(live),
                'after': previous.digest(target)}, metadata_path.name: {
                'source': str(WORK / metadata_path.name), 'before': previous.digest(metadata_path),
                'after': previous.digest(WORK / metadata_path.name)}},
              'geometry': geometry, 'native_executable_unchanged': exe_hash,
              'server_image_unchanged': deploy.docker('inspect', 'ac-worldserver', '--format', '{{.Image}}'),
              'generator_sha256': previous.digest(Path('tools/centaur_clothing.py')),
              'checks_passed': True, 'unrelated_archive_entries_preserved': True}
    deploy.pack.json_save(WORK / 'stage.json', report)
    print('STAGED four regional armor entries; unrelated accessories, boots and archive payloads preserved')


def install():
    report = deploy.pack.p.load_json(WORK / 'stage.json')
    assert report['checks_passed'] and report['unrelated_archive_entries_preserved']
    assert previous.digest(Path('tools/centaur_clothing.py')) == report['generator_sha256']
    assert previous.digest(deploy.CLIENT / 'WowClientRetailVulkan.exe') == report['native_executable_unchanged']
    processes = subprocess.check_output(['tasklist', '/fo', 'csv', '/nh'], text=True).lower()
    assert not any('"' + n in processes for n in ('wowclient', 'mpqeditor', 'eclipse')), 'Close WoW first'
    backup = Path('G:/EsteriaBackups') / ('Centaur-v6-' + datetime.now().strftime('%Y%m%d-%H%M%S'))
    backup.mkdir()
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
    for name, row in report['files'].items():
        assert previous.digest(deploy.CLIENT / name) == row['after'], name
    assert previous.digest(deploy.CLIENT / 'WowClientRetailVulkan.exe') == report['native_executable_unchanged']
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
    print('INSTALLED four Centaur armor entries; backup:', backup, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('stage', 'install'))
    args = parser.parse_args()
    stage() if args.action == 'stage' else install()
