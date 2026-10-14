"""Repair aliased bone track metadata in the imported female M2; preserve all keyframe payloads."""

from datetime import datetime
from pathlib import Path
import ctypes as c
import os
import shutil
import struct
import subprocess

from wotlkconv.m2 import parse_m2
import vrykul_female_pack as v

STAGE = v.STAGE/'track-fix'


def check(before, after):
    expected, changes = v.separate_bone_track_arrays(before)
    assert after == expected and changes
    allowed = {struct.unpack_from('<I', before, 0x30)[0]+bone*88+track+array+4+i
               for bone, track, array, _, _, _ in changes for i in range(4)}
    assert all(after[i] == before[i] for i in range(len(before)) if i not in allowed)
    for _, _, _, old, new, count in changes:
        assert after[new:new+count*8] == before[old:old+count*8]
    original, repaired = parse_m2(before), parse_m2(after)
    assert original.vertices == repaired.vertices and original.sequences == repaired.sequences
    for old, new in zip(original.bones, repaired.bones, strict=True):
        assert old['pivot'] == new['pivot']
        for kind in ('translation', 'rotation', 'scale'):
            assert old[kind].timestamps == new[kind].timestamps
            # Unloaded external tracks may contain NaN when parsed without their .anim payload.
            assert repr(old[kind].values) == repr(new[kind].values)
    assert v.separate_bone_track_arrays(after)[0] == after
    print('CHECKED', len(changes), 'private bone metadata arrays; unchanged animation keys and geometry', flush=True)
    return changes


def prepare():
    STAGE.mkdir(parents=True, exist_ok=True)
    storm = v.o.Storm(v.p.DLL_DEFAULT)
    live = v.p.CLIENT_DEFAULT/v.ASSET
    handle = c.c_void_p()
    assert storm.dll.SFileOpenArchive(str(live), 0, 0x100, c.byref(handle))
    try:
        assets = {key: storm.read(handle, key) for key, *_ in storm.list_files(handle)
                  if key not in ('(listfile)', '(attributes)')}
    finally:
        storm.dll.SFileCloseArchive(handle)
    original = assets[v.MODEL]
    assets[v.MODEL], changes = v.separate_bone_track_arrays(original)
    check(original, assets[v.MODEL])
    target = STAGE/'Patch-7.MPQ'
    storm.create_archive(target, assets)
    handle = storm.open_archive(target)
    try:
        assert all(storm.read(handle, key) == data for key, data in assets.items())
    finally:
        storm.dll.SFileCloseArchive(handle)
    v.old.save(STAGE/'report.json', {'before': v.p.sha256(live), 'after': v.p.sha256(target),
        'array_repairs': changes, 'asset_count': len(assets), 'live_client_test': False})
    print('STAGED only female bone-array metadata repair', flush=True)


def install():
    report = v.p.load_json(STAGE/'report.json')
    processes = subprocess.check_output(['tasklist', '/FO', 'CSV', '/NH'], text=True).lower()
    if any(name in processes for name in ('wow.exe', 'eclipse.exe', 'mpqeditor.exe')):
        raise RuntimeError('Close WoW/Eclipse/MPQEditor before installing the checked model repair')
    live = v.p.CLIENT_DEFAULT/v.ASSET
    assert v.p.sha256(live) == report['before']
    assert v.p.sha256(STAGE/'Patch-7.MPQ') == report['after']
    backup = Path('C:/Users/Zach/.codex/backups')/('vrykul-tracks-'+datetime.now().strftime('%Y%m%d-%H%M%S'))
    backup.mkdir(parents=True)
    shutil.copy2(live, backup/live.name)
    assert v.p.sha256(backup/live.name) == report['before']
    temporary = live.with_suffix('.tracks-next.MPQ')
    shutil.copy2(STAGE/'Patch-7.MPQ', temporary)
    assert v.p.sha256(temporary) == report['after']
    os.replace(temporary, live)
    report['backup'] = str(backup)
    v.old.save(backup/'installed.json', report)
    v.old.save(STAGE/'installed.json', report)
    print('INSTALLED female model track repair:', backup, flush=True)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare', 'install'))
    globals()[parser.parse_args().action]()
