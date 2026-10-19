"""Prepare a separate Sethrak animation pack; never install the Draenei replacer into the live client."""

import argparse
import copy
import hashlib
import json
import math
from pathlib import Path, PureWindowsPath

from wotlkconv.m2 import parse_m2, parse_skin, write_md20
from wotlkconv.m2.types import value_size

from cars_mount_pack import DLL_DEFAULT, Storm
import creature_animation_repair as repair
import earthen_race_pack as e
import retroported_race_pack as p

SOURCE = p.ROOT / 'NewModels/_Race/sethrak for draenei male and female/patch-e.mpq'
OUT = Path(r'G:\RetroPorterWork\sethrak-animations')
PREFIX = 'custom\\sethrak\\animated\\'
# Basic player movement, interactions and emotes. Existing authored actions always win.
ACTIONS = (13, 37, 38, 39, 40, 43, 44, 45, 48, 49, 50, 64, 65, 66, 67, 68, 69, 70,
           73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 89, 90, 101, 102, 103, 104,
           106, 110, 113, 114, 115, 116, 119, 120, 133, 134, 187)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def local(root, key):
    return root.joinpath(*PureWindowsPath(key).parts)


def embedded_model(root, key, read):
    """Pin the complete model/ANIM set and use the previous native track embedder."""
    path = local(root, key)
    data = read(key)
    repair.c.immutable(path, data)
    model = parse_m2(data)
    hashes = {key: digest(data)}
    for seq in model.sequences:
        if seq['flags'] & (0x20 | 0x40):
            continue
        name = str(PureWindowsPath(key).with_suffix('')) + f'{seq["id"]:04d}-{seq["variation_index"]:02d}.anim'
        payload = read(name)
        repair.c.immutable(local(root, name), payload)
        hashes[name] = digest(payload)
    model = e.v.read_player_model(path)
    e.tracks.embed(model, path.parent, path.stem)
    return model, hashes


def tracks_equal(old, new, count):
    for index, (a, b) in enumerate(zip(old.tracks(), new.tracks(), strict=True)):
        # The shared retargeter expands constant global bind transforms to per-action constants.
        if a.global_sequence >= 0 and b.global_sequence == -1:
            assert hasattr(a, 'values') and a.values[0] and len(set(a.values[0])) == 1
            assert all(values == [a.values[0][0]] for values in b.values[:count]), index
            assert all(times == [0] for times in b.timestamps[:count]), index
            continue
        assert a.global_sequence == b.global_sequence, index
        assert a.interpolation == b.interpolation or (
            hasattr(a, 'values') and all(len(set(slot)) <= 1 for slot in a.values)), index
        assert a.timestamps == b.timestamps[:len(a.timestamps)]
        if hasattr(a, 'values'):
            assert a.values == b.values[:len(a.values)]
    assert new.sequences[:count] == old.sequences


def check_model(model, blob):
    assert model.version == 264 and all(s['flags'] & 0x20 for s in model.sequences)
    for track in model.tracks():
        assert not track.external
        assert -1 <= track.global_sequence < len(model.global_loops)
        for index, (count, offset) in enumerate(track.timestamp_spans):
            times = track.timestamps[index]
            assert len(times) == count and times == sorted(times)
            assert not count or 0 < offset <= offset + count * 4 <= len(blob)
            if times and track.global_sequence < 0:
                assert index < len(model.sequences)
                assert max(times) <= model.sequences[index]['duration'] + 1
            if hasattr(track, 'values'):
                n, pos = track.value_spans[index]
                assert n == count
                assert not n or 0 < pos <= pos + n * value_size(track.kind) <= len(blob)
                assert all(math.isfinite(x) for row in track.values[index]
                           for x in (row if isinstance(row, tuple) else (row,)))
    for seq in model.sequences:
        if seq['flags'] & 0x40:
            seen, index = set(), seq['alias_next']
            while model.sequences[index]['flags'] & 0x40:
                assert index not in seen
                seen.add(index)
                index = model.sequences[index]['alias_next']
            assert 0 <= index < len(model.sequences)
    for action in ACTIONS:
        index = repair.sequence(model, action)
        assert model.sequence_lookups[action] < len(model.sequences)
        assert model.sequences[index]['duration'] > 0


def prepare(source, out):
    out.mkdir(parents=True, exist_ok=True)
    storm = Storm(DLL_DEFAULT)
    handle = storm.open_archive(source)
    files = p.ClientFiles(str(p.CLIENT_DEFAULT / 'Data'), 'enUS')
    entries = {}
    report = {'status': 'staging', 'source_archive': str(source), 'source_sha256': p.sha256(source),
              'output': str(out), 'models': {}, 'live_install_performed': False}
    try:
        names = {n.replace('/', '\\').lower(): n for n, *_ in storm.list_files(handle)}

        def read_source(key):
            return storm.read(handle, names[key.replace('/', '\\').lower()])

        textures = {name: read_source(name) for name in names if name.endswith('.blp')}
        for key, data in textures.items():
            entries[PREFIX + 'textures\\' + key] = data
        for sex in ('Male', 'Female'):
            key = f'Character\\Draenei\\{sex}\\Draenei{sex}.m2'
            model, source_hashes = embedded_model(out / 'source', key, read_source)
            original = copy.deepcopy(model)
            # Draenei has the strongest name match among the installed HD humanoid donors, including the tail.
            donor_key = f'Character\\Draenei2\\{sex}\\Draenei{sex}2.m2'
            _, provider = files.find(donor_key)
            donor, donor_hashes = embedded_model(out / 'donors', donor_key, lambda k: files.find(k)[0])
            source_names = {b['bone_name_crc'] for b in donor.bones if b['bone_name_crc']}
            matched = [i for i, b in enumerate(model.bones) if b['bone_name_crc'] in source_names]
            missing = [action for action in ACTIONS if action not in {s['id'] for s in model.sequences}]
            added = [repair.retarget(model, donor, action) for action in missing]
            for seq in model.sequences[len(original.sequences):]:
                seq.update(bounds_min=model.bounding_box[:3], bounds_max=model.bounding_box[3:],
                           bounds_radius=model.bounding_sphere_radius)
            # Reuse the NPC-to-Wrath casting/sitting compatibility mappings without requesting other donors.
            aliases = repair.repair_model('sethrak', 0, model)['wrath_action_aliases']
            tracks_equal(original, model, len(original.sequences))
            target = PREFIX + f'{sex.lower()}\\sethrak{sex.lower()}.m2'
            for texture in model.textures:
                name = texture['filename'].replace('/', '\\').lower()
                if name in textures:
                    texture['filename'] = PREFIX + 'textures\\' + name
                elif texture['type'] == 0 and name:
                    raise ValueError('Missing source texture: ' + name)
            blob = write_md20(model)
            rebuilt = parse_m2(blob)
            check_model(rebuilt, blob)
            assert rebuilt.vertices == original.vertices
            assert rebuilt.bone_combos == original.bone_combos
            assert [(b['parent_bone'], b['pivot'], b['bone_name_crc']) for b in rebuilt.bones] == [
                (b['parent_bone'], b['pivot'], b['bone_name_crc']) for b in original.bones]
            assert [(a['id'], a['bone'], a['position']) for a in rebuilt.attachments] == [
                (a['id'], a['bone'], a['position']) for a in original.attachments]
            tracks_equal(original, rebuilt, len(original.sequences))
            entries[target] = blob
            skins = []
            for index in range(original.num_skin_profiles):
                source_skin = key[:-3] + f'{index:02d}.skin'
                skin_blob = read_source(source_skin)
                skin = parse_skin(skin_blob)
                assert all(v < rebuilt.vertex_count for v in skin.vertices)
                assert all(i < len(skin.vertices) for i in skin.indices)
                target_skin = target[:-3] + f'{index:02d}.skin'
                entries[target_skin] = skin_blob
                skins.append(target_skin)
            report['models'][sex.lower()] = {'path': target, 'source_hashes': source_hashes,
                'donor_path': donor_key, 'donor_provider': provider, 'donor_hashes': donor_hashes,
                'matched_bones': len(matched), 'bones': len(rebuilt.bones),
                'original_sequences': len(original.sequences), 'sequences': len(rebuilt.sequences),
                'added_actions': added, 'wrath_action_aliases': aliases, 'skins': skins,
                'vertices_sha256': digest(rebuilt.vertices), 'model_sha256': digest(blob)}
            print('PREPARED', sex, len(original.sequences), '->', len(rebuilt.sequences),
                  'sequences;', len(added), 'retargeted actions;', len(matched), 'matched bones', flush=True)
    finally:
        files.close()
        storm.dll.SFileCloseArchive(handle)
    for key, blob in entries.items():
        path = local(out / 'patch-root', key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(blob)
    archive = out / 'Patch-Sethrak-Animations.MPQ'
    # Stage a new archive atomically; an interrupted prepare must not replace the last checked package.
    temporary = out / 'Patch-Sethrak-Animations.next.MPQ'
    if temporary.exists():
        raise FileExistsError('Previous staging archive exists: ' + str(temporary))
    storm.create_archive(temporary, entries)
    handle = storm.open_archive(temporary)
    try:
        for key, blob in entries.items():
            assert storm.read(handle, key) == blob
    finally:
        storm.dll.SFileCloseArchive(handle)
    temporary.replace(archive)
    assert p.sha256(source) == report['source_sha256']
    report.update(status='prepared_awaiting_visual_test', archive=str(archive),
                  archive_sha256=p.sha256(archive), entries={k: digest(v) for k, v in entries.items()})
    (out / 'report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8', newline='\n')
    (out / 'README.md').write_text(
        '# Sethrak animation assets\n\n'
        'Both models from the supplied Sethrak-for-Draenei replacer retain their original geometry, rig, '
        'skin profiles, attachments and authored motion. External animation keys are embedded in native '
        'M2 version 264. Missing actions use the installed HD Draenei donor of the corresponding gender.\n\n'
        'Each model has 134 sequence records: 83 original, 46 retargeted actions, and five Wrath '
        'casting/sitting compatibility entries. Added actions include fishing cast/loop (133/134), '
        'jump start/air/landing (37/38/39), fall (40), running landing (187), backwards movement, '
        'swimming turns/backwards, looting, rifle actions, stealth, kneeling, chair sitting and emotes.\n\n'
        'Loose assets are in `patch-root/custom/sethrak/animated/`; the matching '
        '`Patch-Sethrak-Animations.MPQ` contains the same 60 files. `report.json` records input/output '
        'hashes, donor provenance and the moving bones for every added action.\n\n'
        'This is a model asset pack. It contains no race registry, DBC or server changes. Its custom '
        'paths must be selected by the existing/new Sethrak display before they appear in-game; copying '
        'the archive into a client alone does not select these models. The original Draenei replacer '
        'archives and the live client/server were not modified.\n\n'
        'Reproduce and verify from the EsteriaWoW repository:\n\n'
        '```powershell\npython tools/sethrak_animation_pack.py prepare\n'
        'python tools/sethrak_animation_pack.py check\n```\n\n'
        'Visual testing remains required for both bodies: fishing pole grip and cast/loop transitions; '
        'standing/running jumps, falls and landings; feet/tail motion; swimming, stealth, chair sitting, '
        'casting and weapon sheathing. Structural and keyframe checks do not establish visual quality.\n',
        encoding='utf-8', newline='\n')
    check(out)


def check(out):
    report = p.load_json(out / 'report.json')
    assert p.sha256(Path(report['source_archive'])) == report['source_sha256']
    assert p.sha256(Path(report['archive'])) == report['archive_sha256']
    storm = Storm(DLL_DEFAULT)
    handle = storm.open_archive(Path(report['archive']))
    try:
        actual = {n.replace('/', '\\').lower() for n, *_ in storm.list_files(handle)
                  if n not in ('(listfile)', '(attributes)')}
        assert actual == {k.lower() for k in report['entries']}
        for key, sha in report['entries'].items():
            assert digest(storm.read(handle, key)) == sha
            assert digest(local(out / 'patch-root', key).read_bytes()) == sha
        for sex, info in report['models'].items():
            key = info['path']
            blob = storm.read(handle, key)
            model = parse_m2(blob)
            check_model(model, blob)
            source_key = f'Character\\Draenei\\{sex.title()}\\Draenei{sex.title()}.m2'
            original, hashes = embedded_model(out / 'source', source_key,
                                              lambda k: local(out / 'source', k).read_bytes())
            assert hashes == info['source_hashes']
            tracks_equal(original, model, len(original.sequences))
            assert model.vertices == original.vertices
            for action in info['added_actions']:
                index = repair.sequence(model, action['animation'])
                assert action['moving_matched_bones']
                assert any(len(set(b[name].values[index])) > 1
                           for b in model.bones for name in ('rotation', 'translation')
                           if b[name].global_sequence < 0 and index < len(b[name].values))
            for alias in info['wrath_action_aliases']:
                index = repair.sequence(model, alias['animation'])
                source_index = repair.sequence(model, alias['authored_source'])
                for track in model.tracks():
                    if track.global_sequence < 0 and source_index < len(track.timestamps):
                        assert track.timestamps[index] == track.timestamps[source_index]
                        if hasattr(track, 'values'):
                            assert track.values[index] == track.values[source_index]
            print('PASS', sex, 'original keys/geometry, new motion, lookup and embedded spans', flush=True)
    finally:
        storm.dll.SFileCloseArchive(handle)
    print('PASS', len(report['entries']), 'archive entries; source archive unchanged', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare', 'check'))
    parser.add_argument('--source', type=Path, default=SOURCE)
    parser.add_argument('--out', type=Path, default=OUT)
    args = parser.parse_args()
    if args.action == 'prepare':
        prepare(args.source, args.out)
    else:
        check(args.out)
