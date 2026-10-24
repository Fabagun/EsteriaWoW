"""Repair the captured Azsuna sky's stale SKIN palette spans; preserve the shared rig and art."""

import argparse
import hashlib
from pathlib import Path
import shutil
import struct

import kyrian_venthyr_pack as k


MODEL = 'environments\\stars\\azsuna_sky01.m2'
SKIN = 'environments\\stars\\azsuna_sky0100.skin'
WORK = k.STAGE / 'sky-palette-fix'


def repair(model, skin):
    if model[:8] != b'MD20\x08\x01\x00\x00' or skin[:4] != b'SKIN':
        raise ValueError('Unexpected model format')
    bones = struct.unpack_from('<I', model, 44)[0]
    palette_count, palette_offset = struct.unpack_from('<2I', model, 120)
    palette = struct.unpack_from('<' + str(palette_count) + 'H', model, palette_offset)
    if not 0 < palette_count <= 75 or any(bone >= bones for bone in palette):
        raise ValueError('Shared palette contains an invalid rig bone')
    lookup_count, lookup_offset = struct.unpack_from('<2I', skin, 4)
    properties_count, properties_offset = struct.unpack_from('<2I', skin, 20)
    sections_count, sections_offset = struct.unpack_from('<2I', skin, 28)
    if properties_count != lookup_count:
        raise ValueError('Vertex/property counts differ')
    if any(index >= palette_count for index in skin[properties_offset:properties_offset + properties_count * 4]):
        raise ValueError('Skin properties do not address the shared palette')
    result = bytearray(skin)
    changes = []
    for index in range(sections_count):
        at = sections_offset + index * 48
        begin, count = struct.unpack_from('<2H', skin, at + 4)
        bone_count, bone_offset = struct.unpack_from('<2H', skin, at + 12)
        if begin + count > lookup_count:
            raise ValueError('Section vertex span is invalid')
        changes.append({'section': index, 'before': [bone_offset, bone_count], 'after': [0, palette_count]})
        struct.pack_into('<2H', result, at + 12, palette_count, 0)
    allowed = {sections_offset + i * 48 + byte for i in range(sections_count) for byte in range(12, 16)}
    if any(a != b and index not in allowed for index, (a, b) in enumerate(zip(skin, result))):
        raise AssertionError('Repair changed bytes outside palette span fields')
    return bytes(result), changes


def run(install=False):
    storm = k.p.Storm(k.p.DLL_DEFAULT)
    with k.p.ClientFiles(str(k.p.CLIENT_DEFAULT / 'Data'), 'enUS') as files:
        model, model_provider = files.find(MODEL)
        skin, skin_provider = files.find(SKIN)
    provider = Path(skin_provider)
    if provider != k.p.CLIENT_DEFAULT / 'Data/patch-E.MPQ':
        raise ValueError('Effective provider changed: ' + str(provider))
    original = WORK / 'azsuna_sky0100.skin'
    if not original.is_file() or skin != original.read_bytes():
        raise ValueError('Sky no longer matches the captured faulty input')
    fixed, changes = repair(model, skin)
    target = WORK / 'patch-E.fixed.mpq'
    backup = WORK / 'patch-E.before.mpq'
    for path in (target, backup):
        if path.exists():
            raise FileExistsError(path)
        shutil.copy2(provider, path)
    before_hash = k.p.sha256(provider)
    if any(k.p.sha256(path) != before_hash for path in (target, backup)):
        raise ValueError('Archive backup verification failed')
    storm.replace_archive_entries(target, {SKIN: fixed})
    handles = [storm.open_archive(path) for path in (provider, target)]
    try:
        names = [name for name, *_ in storm.list_files(handles[0]) if not name.startswith('(')]
        for name in names:
            expected = fixed if name.casefold() == SKIN.casefold() else storm.read(handles[0], name)
            if storm.read(handles[1], name) != expected:
                raise ValueError('Payload preservation mismatch: ' + name)
    finally:
        for handle in handles:
            storm.dll.SFileCloseArchive(handle)
    report = {'model': MODEL, 'model_provider': str(model_provider), 'skin': SKIN,
        'skin_provider': str(provider), 'before': before_hash, 'after': k.p.sha256(target),
        'model_sha256_unchanged': hashlib.sha256(model).hexdigest(), 'skin_changes': changes,
        'unrelated_payloads_verified': len(names) - 1, 'backup': str(backup),
        'installed': False, 'normal_launcher_visual_acceptance': False}
    k.save(WORK / 'azsuna_sky0100.fixed.skin', fixed)
    if install:
        import kyrian_venthyr_deploy as deploy
        deploy.ensure_client_closed()
        if k.p.sha256(provider) != before_hash:
            raise ValueError('Live provider changed during staging')
        try:
            shutil.copy2(target, provider)
            if k.p.sha256(provider) != report['after']:
                raise ValueError('Installed archive hash mismatch')
        except Exception:
            shutil.copy2(backup, provider)
            raise
        report['installed'] = True
    k.json_save(WORK / 'palette-repair.json', report)
    print('PASS all palette spans bounded, model unchanged, unrelated archive payloads verified; installed:', install)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--install', action='store_true')
    run(parser.parse_args().install)
