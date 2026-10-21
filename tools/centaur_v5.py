"""Stage the Centaur loot, model-preview, claw, cloak and head-choice follow-up."""

import argparse
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import shutil
import struct
import subprocess

import centaur_deploy as deploy
import centaur_v4_deploy as previous
import centaur_v4 as art
from sethrak_equipment_repair import mesh_triangles
from wotlkconv.m2 import parse_m2, parse_skin

WORK = deploy.WORK / 'repair-v5'
TABLES = ('CharSections', 'CharHairGeosets', 'BarberShopStyle')
NATIVE_FILES = (*previous.NATIVE_FILES, 'Engine/Source/Model2/M2Model.cpp', 'Engine/Source/Model2/M2Model.h',
                'Engine/Source/Retail/Appearance.cpp', 'WoW/Source/Ui/CharacterModelBase.cpp',
                'WoW/Source/Glue/CharacterCreation.cpp', 'WoW/Source/Glue/CharacterSelectionDisplay.cpp')


def filter_heads(name, data):
    table = deploy.pack.p.RawWdbc(data)
    race_at, sex_at, style_at = (148, 152, 156) if name == 'BarberShopStyle' else (
        (4, 8, 32) if name == 'CharSections' else (4, 8, 12))
    removed, records = [], []
    for row in table.records:
        race, sex, style = (deploy.pack.p._value(row, at) for at in (race_at, sex_at, style_at))
        head = name == 'CharHairGeosets' or deploy.pack.p._value(row, 12 if name == 'CharSections' else 4) == (
            3 if name == 'CharSections' else 0)
        (removed if race in (73, 74) and sex in (0, 1) and head and style >= (8 if sex else 4)
         else records).append(row)
    assert removed, 'Expected installed helmet head rows: ' + name
    result = table.build(records, table.strings)
    assert Counter(table.records) - Counter(records) == Counter(removed)
    assert not (Counter(records) - Counter(table.records))
    return result, len(removed)


def stage():
    import test_centaur_refine
    test_centaur_refine.main()
    WORK.mkdir(exist_ok=True)
    tests = deploy.NATIVE / 'build/retail-satchel/Release/RetailAssetTests.exe'
    for name, args in [('native-regression', []), ('native-art', ['--centaur-source',
            str(deploy.CLIENT / 'Data/Retail/RetailCasc.ini'), str(deploy.WORK)])]:
        with (WORK / (name + '.log')).open('w') as log:
            subprocess.run([str(tests), *args], check=True, stdout=log, stderr=subprocess.STDOUT)
    storm = deploy.pack.p.Storm(deploy.pack.p.DLL_DEFAULT)
    files, changes = {}, {}
    for relative in (deploy.ASSET, deploy.pack.p.GLOBAL_ARCHIVE_REL, deploy.pack.p.LOCALE_ARCHIVE_REL):
        live, target = deploy.CLIENT / relative, WORK / 'client' / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        before = previous.archive_entries(storm, live)
        payloads = {}
        if relative == deploy.ASSET:
            root = deploy.pack.STAGE / 'assets/custom/centaur'
            baseline = WORK / 'baseline'
            baseline.mkdir(exist_ok=True)
            for identifier in (4036647, 4081379):
                for extension in ('.m2', '00.skin'):
                    name = f'{identifier}-clothing{extension}'
                    (baseline / name).write_bytes(before['custom/centaur/' + name])
                    payloads['custom/centaur/' + name] = (root / name).read_bytes()
                old, new = art.triangle_records(baseline, identifier), art.triangle_records(root, identifier)
                assert old.keys() == new.keys()
                assert all(old[g] == new[g] for g in old if g != 1 and g // 100 != 15)
                def trunk(counter):
                    return Counter({tri: count for tri, count in counter.items()
                                    if all(abs(struct.unpack_from('<3f', v)[1]) < 1 for v in tri)})
                assert trunk(old[1]) == trunk(new[1]), 'Torso/horse armor changed outside the hands'
                model = parse_m2((root / f'{identifier}-clothing.m2').read_bytes())
                skin = parse_skin((root / f'{identifier}-clothing00.skin').read_bytes())
                points = [struct.unpack_from('<3f', model.vertices, i * 48)
                          for row in skin.submeshes if struct.unpack_from('<H', row)[0] == 1
                          for tri in mesh_triangles(skin, row) for i in tri]
                assert min(z for x, y, z in points if abs(y) > 1.1) > 1.76, 'Gloves cover the claw tips'
                capes = [struct.unpack_from('<3f', model.vertices, i * 48)
                         for row in skin.submeshes if struct.unpack_from('<H', row)[0] // 100 == 15
                         for tri in mesh_triangles(skin, row) for i in tri]
                assert max(abs(y) for x, y, z in capes) > .29
                assert all(z > 1.39 and -.76 < x < .5 and abs(y) < .36 for x, y, z in capes)
        else:
            for name in TABLES:
                key = (deploy.pack.p.DBC_ROOT + name + '.dbc').replace('\\', '/').lower()
                payloads[key], removed = filter_heads(name, before[key])
                changes[str(relative) + ':' + name] = {'removed_helmet_rows': removed}
        shutil.copy2(live, target)
        storm.replace_archive_entries(target, payloads)
        after = previous.archive_entries(storm, target)
        expected = {**before, **{key.replace('\\', '/').lower(): value for key, value in payloads.items()}}
        assert after == expected, 'Unrelated archive payload changed'
        files[str(relative)] = {'source': str(target), 'before': previous.digest(live),
                                'after': previous.digest(target)}
    exe = deploy.NATIVE / 'bin/Win/WowClientRetailInventory.exe'
    metadata = deploy.pack.p.load_json(deploy.CLIENT / 'WowClientRetailVulkan.build.json')
    assert metadata['sha256'] == previous.digest(deploy.CLIENT / 'WowClientRetailVulkan.exe')
    source_hashes = {name: previous.digest(deploy.NATIVE / name) for name in NATIVE_FILES}
    metadata.update(sha256=previous.digest(exe), staged_at_utc=datetime.now(timezone.utc).isoformat(),
                    centaur_repairs={'receipt': str(WORK / 'receipt.json'), 'visual_acceptance': 'pending'})
    metadata['features'].append('Centaur loot loading repair, equipped UI armor, natural claws and refined previews')
    for name, value in source_hashes.items():
        row = next((row for row in metadata['source_files'] if row['path'] == name), None)
        if row is None:
            metadata['source_files'].append({'path': name, 'sha256': value})
        else:
            row['sha256'] = value
    deploy.pack.json_save(WORK / 'WowClientRetailVulkan.build.json', metadata)
    for name, source in [('WowClientRetailVulkan.exe', exe),
                         ('WowClientRetailVulkan.build.json', WORK / 'WowClientRetailVulkan.build.json')]:
        files[name] = {'source': str(source), 'before': previous.digest(deploy.CLIENT / name),
                       'after': previous.digest(source)}
    deploy.pack.json_save(WORK / 'stage.json', {'files': files, 'native': source_hashes, 'head_filters': changes,
        'native_checks_passed': True, 'unrelated_archive_entries_preserved': True})
    print('STAGED Centaur v5 client-only repair; all unrelated archive entries preserved', flush=True)


def install():
    report = deploy.pack.p.load_json(WORK / 'stage.json')
    assert report['native_checks_passed'] and report['unrelated_archive_entries_preserved']
    processes = subprocess.check_output(['tasklist', '/fo', 'csv', '/nh'], text=True).lower()
    assert not any('"' + name in processes for name in ('wowclient', 'mpqeditor', 'eclipse')), 'Close WoW first'
    for name, value in report['native'].items():
        assert previous.digest(deploy.NATIVE / name) == value, name
    backup = Path('G:/EsteriaBackups') / ('Centaur-v5-' + datetime.now().strftime('%Y%m%d-%H%M%S'))
    backup.mkdir()
    meta_path = WORK / 'WowClientRetailVulkan.build.json'
    metadata = deploy.pack.p.load_json(meta_path)
    metadata['backup_directory'] = str(backup)
    deploy.pack.json_save(meta_path, metadata)
    report['files'][meta_path.name]['after'] = previous.digest(meta_path)
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
    report.update(installed=True, backup=str(backup), live_visual_accepted=False)
    deploy.pack.json_save(WORK / 'receipt.json', report)
    deploy.pack.json_save(backup / 'receipt.json', report)
    print('INSTALLED Centaur v5 client repair; backup:', backup, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('stage', 'install'))
    args = parser.parse_args()
    stage() if args.action == 'stage' else install()
