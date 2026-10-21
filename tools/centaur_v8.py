"""Install only the centered cloak UVs and pants-boundary belts, preserving all other client content."""

import argparse
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import shutil
import subprocess

import centaur_deploy as deploy
import centaur_v4 as art
import centaur_v4_deploy as previous
import test_centaur_v8 as checks

WORK = checks.WORK


def stage():
    checks.main()
    storm = deploy.pack.p.Storm(deploy.pack.p.DLL_DEFAULT)
    live, target = deploy.CLIENT / deploy.ASSET, WORK / 'client' / deploy.ASSET
    baseline = previous.archive_entries(storm, live)
    originals = WORK / 'baseline'
    originals.mkdir(exist_ok=True)
    payloads, geometry = {}, {}
    for identifier in (4036647, 4081379):
        for extension in ('.m2', '00.skin'):
            name = f'{identifier}-clothing{extension}'
            key = 'custom/centaur/' + name
            (originals / name).write_bytes(baseline[key])
            payloads[key] = (deploy.pack.STAGE / 'assets/custom/centaur' / name).read_bytes()
        old = art.triangle_records(originals, identifier)
        new = art.triangle_records(deploy.pack.STAGE / 'assets/custom/centaur', identifier)
        assert old.keys() == new.keys()
        retained = [g for g in new if g != 1805 and g // 100 != 15]
        assert all(new[g] == old[g] for g in retained), 'Unrelated armor vertex records changed'
        for geoset in old:
            if geoset // 100 == 15:
                def without_uv(triangles):
                    records = Counter()
                    for tri, count in triangles.items():
                        records[tuple(r[:32] + r[40:] for r in tri)] += count
                    return records
                assert without_uv(old[geoset]) == without_uv(new[geoset]), 'Cloak geometry/weights changed'
        geometry[str(identifier)] = {'unchanged_geosets': retained, 'cloak_geometry_and_weights_unchanged': True}
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(live, target)
    storm.replace_archive_entries(target, payloads)
    assert previous.archive_entries(storm, target) == {**baseline, **payloads}
    metadata_path = deploy.CLIENT / 'WowClientRetailVulkan.build.json'
    metadata = deploy.pack.p.load_json(metadata_path)
    exe_hash = previous.digest(deploy.CLIENT / 'WowClientRetailVulkan.exe')
    assert metadata['sha256'] == exe_hash
    metadata['centaur_boundary_armor'] = {'receipt': str(WORK / 'receipt.json'), 'live_accepted': False}
    metadata['features'].append('Centaur centered mirrored cape panels and belts following exact pants sockets')
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
    print('STAGED four clothing entries; only belt geometry and cloak UVs changed')


def install():
    report = deploy.pack.p.load_json(WORK / 'stage.json')
    assert report['checks_passed'] and report['unrelated_archive_entries_preserved']
    assert previous.digest(Path('tools/centaur_clothing.py')) == report['generator_sha256']
    assert previous.digest(deploy.CLIENT / 'WowClientRetailVulkan.exe') == report['native_executable_unchanged']
    processes = subprocess.check_output(['tasklist', '/fo', 'csv', '/nh'], text=True).lower()
    assert not any('"' + n in processes for n in ('wowclient', 'mpqeditor', 'eclipse')), 'Close WoW first'
    backup = Path('G:/EsteriaBackups') / ('Centaur-v8-' + datetime.now().strftime('%Y%m%d-%H%M%S'))
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
        for name, row in report['files'].items():
            assert previous.digest(deploy.CLIENT / name) == row['after'], name
        storm = deploy.pack.p.Storm(deploy.pack.p.DLL_DEFAULT)
        installed = previous.archive_entries(storm, deploy.CLIENT / deploy.ASSET)
        for identifier in (4036647, 4081379):
            for extension in ('.m2', '00.skin'):
                name = f'{identifier}-clothing{extension}'
                assert installed['custom/centaur/' + name] == (
                    deploy.pack.STAGE / 'assets/custom/centaur' / name).read_bytes()
    except Exception:
        for name, row in report['files'].items():
            deploy.atomic_copy(backup / name, deploy.CLIENT / name, row['before'])
        raise
    assert previous.digest(deploy.CLIENT / 'WowClientRetailVulkan.exe') == report['native_executable_unchanged']
    assert deploy.docker('inspect', 'ac-worldserver', '--format', '{{.Image}}') == report['server_image_unchanged']
    report.update(installed=True, backup=str(backup), installed_at=datetime.now(timezone.utc).isoformat(),
                  installed_entry_readback_passed=True, live_visual_accepted=False)
    deploy.pack.json_save(WORK / 'receipt.json', report)
    deploy.pack.json_save(backup / 'receipt.json', report)
    print('INSTALLED four Centaur clothing entries; backup:', backup, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('stage', 'install'))
    args = parser.parse_args()
    stage() if args.action == 'stage' else install()
