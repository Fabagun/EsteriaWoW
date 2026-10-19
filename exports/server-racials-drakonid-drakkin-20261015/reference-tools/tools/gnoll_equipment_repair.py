"""Stage and install Gnoll-only anatomical, clothing and attachment corrections."""

import argparse
from datetime import datetime
from pathlib import Path
import shutil
import struct
import subprocess

from wotlkconv.m2 import parse_m2, parse_skin

import gnoll_race_pack as g
import retroported_race_pack as p

STAGE = Path('C:/Users/Zach/.codex/tmp/gnoll-equipment-fit-v2')


def prepare():
    old = g.STAGE
    STAGE.mkdir(parents=True, exist_ok=True)
    for name in ('donors', 'source-images'):
        shutil.copytree(old / name, STAGE / name, dirs_exist_ok=True)
    shutil.copy2(old / 'animated.m2', STAGE / 'animated.m2')
    work, uv = p.load_json(old / 'male-body-work.json'), p.load_json(old / 'male-body-uv.json')
    g.save(STAGE / 'frozen-upper-uv.json', {','.join(map(str, tri)): uv[i * 3:i * 3 + 3]
                                         for i, tri in enumerate(work['body'])})
    g.STAGE = STAGE
    g.export_body()
    subprocess.run(['C:/Program Files/Blender Foundation/Blender 5.2/blender.exe', '-b', '--factory-startup',
                    '--python', str(p.ROOT / 'tools/sethrak_body_blender.py'), '--', str(STAGE), 'male'], check=True)
    g.prepare()
    g.preview()
    g.preview_equipment()
    print('PREPARED Gnoll complete anatomy, garment surfaces, authored cape mesh and forearm shield frame', flush=True)


def stage():
    from test_gnoll_equipment import check
    check()
    storm = p.Storm(p.DLL_DEFAULT)
    archive = p.CLIENT_DEFAULT / g.ASSET_ARCHIVE
    files = {str(g.ASSET_ARCHIVE): str(STAGE / 'Patch-6.MPQ'),
             'EsteriaAppearanceGeometry.bin': str(STAGE / 'EsteriaAppearanceGeometry.bin'),
             'EsteriaGnoll.bin': str(STAGE / 'EsteriaGnoll.bin'),
             'EsteriaGnollTextures.bin': str(STAGE / 'EsteriaGnollTextures.bin'),
             'EsteriaAppearance.dll': 'C:/g63-build/EsteriaAppearance.dll'}
    updates = {'\\'.join(path.relative_to(STAGE / 'assets').parts): path.read_bytes()
               for path in (STAGE / 'assets').rglob('*') if path.is_file()}
    shutil.copy2(archive, STAGE / 'Patch-6.MPQ')
    storm.replace_archive_entries(STAGE / 'Patch-6.MPQ', updates)
    handle = storm.open_archive(STAGE / 'Patch-6.MPQ')
    try:
        assert all(storm.read(handle, key) == value for key, value in updates.items())
    finally:
        storm.dll.SFileCloseArchive(handle)
    original = (p.CLIENT_DEFAULT / 'EsteriaAppearanceGeometry.bin').read_bytes()
    magic, version, count = struct.unpack_from('<3I', original)
    at, rows, changed = 12, [], 0
    for _ in range(count):
        path = original[at:at + 128].split(b'\0')[0].decode()
        size = struct.unpack_from('<I', original, at + 128)[0]
        row = original[at:at + 132 + size]
        if path.lower() == g.MODEL.lower():
            skin = updates[g.MODEL[:-3] + '00.skin']
            row = original[at:at + 128] + struct.pack('<I', len(skin)) + skin
            changed += 1
        rows.append(row)
        at += 132 + size
    assert changed == 1 and at == len(original) and (magic, version) == (0x4D474145, 1)
    (STAGE / 'EsteriaAppearanceGeometry.bin').write_bytes(original[:12] + b''.join(rows))
    report = {'files': files, 'before': {name: p.sha256(p.CLIENT_DEFAULT / name) for name in files},
              'after': {name: p.sha256(Path(path)) for name, path in files.items()},
              'exe_sha256': p.sha256(p.CLIENT_DEFAULT / 'Wow.exe')}
    g.save(STAGE / 'stage.json', report)
    print('PASS isolated Gnoll asset/catalog archive readback; all other geometry records retained', flush=True)


def install(validate=None):
    if validate is None:
        from test_gnoll_equipment import check
        validate = check
    validate()
    processes = subprocess.check_output(['tasklist', '/FO', 'CSV', '/NH'], text=True).lower()
    if any(name in processes for name in ('wow.exe', 'eclipse.exe', 'mpqeditor.exe')):
        raise RuntimeError('Close both WoW clients and archive editors before replacing the loaded Gnoll files')
    r = p.load_json(STAGE / 'stage.json')
    assert p.sha256(p.CLIENT_DEFAULT / 'Wow.exe') == r['exe_sha256']
    for name, digest in r.get('protected', {}).items():
        assert p.sha256(p.CLIENT_DEFAULT / name) == digest
    for name, source in r['files'].items():
        assert p.sha256(p.CLIENT_DEFAULT / name) == r['before'][name]
        assert p.sha256(Path(source)) == r['after'][name]
    backup = Path('C:/Users/Zach/.codex/backups') / ('gnoll-equipment-' + datetime.now().strftime('%Y%m%d-%H%M%S'))
    backup.mkdir(parents=True)
    for name in r['files']:
        target = backup / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p.CLIENT_DEFAULT / name, target)
        assert p.sha256(target) == r['before'][name]
    try:
        for name, source in r['files'].items():
            shutil.copy2(source, p.CLIENT_DEFAULT / name)
            assert p.sha256(p.CLIENT_DEFAULT / name) == r['after'][name]
        for name, digest in r.get('protected', {}).items():
            assert p.sha256(p.CLIENT_DEFAULT / name) == digest
    except Exception:
        for name in r['files']:
            shutil.copy2(backup / name, p.CLIENT_DEFAULT / name)
        raise
    r.update(backup=str(backup), status='installed_pending_live_equipment_retest')
    g.save(STAGE / 'installed.json', r)
    g.save(backup / 'install-report.json', r)
    print('INSTALLED Gnoll equipment repair with verified backup', backup, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare', 'stage', 'install'))
    globals()[parser.parse_args().action]()
