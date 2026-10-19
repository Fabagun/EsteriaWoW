"""Reuse Tauren helmet meshes on a player-compatible Tarasek head socket.

The NPC's original socket adds a 1.21 scale and pitch to every helmet. Replace only that attachment
with a Tauren player socket. Fallback families receive translation only; helmet shapes remain intact.
"""
import copy
from pathlib import Path, PureWindowsPath
import struct

import tarasek_drakkin as t
import tarasek_equipment as e
import creature_animation_repair as motion
import numpy as np
from wotlkconv.m2 import parse_m2, parse_skin, write_md20


def socket():
    import sethrak_animation_pack as checks
    import vrykul_female_pack as arrays
    report = t.p.load_json(e.WORK / 'report.json')
    path = Path(report['model'])
    original = parse_m2(path.read_bytes())
    body = copy.deepcopy(original)
    if 'helmet_socket' in report:
        helper = report['helmet_socket']['bone']
        assert helper == len(body.bones) - 1
        body.bones = body.bones[:helper]
    donor = parse_m2(Path('G:/RetroPorterWork/drakonid/donors/Character/Tauren2/Male/TaurenMale2.m2').read_bytes())
    player_attachment = next(a for a in donor.attachments if a['id'] == 11)
    attachment = next(a for a in body.attachments if a['id'] == 11)
    source_head = donor.key_bone_lookup[6]
    target_head = body.key_bone_lookup[6]
    offset = np.array(body.bones[target_head]['pivot']) - donor.bones[source_head]['pivot']
    helper = copy.deepcopy(donor.bones[player_attachment['bone']])
    assert helper['parent_bone'] == source_head
    # The player's socket has no extra keyed rotation/translation/scale. Keep it that way.
    assert all(not any(helper[k].values) for k in ('translation', 'rotation'))
    scales = [value for values in helper['scale'].values for value in values]
    assert scales and all(np.allclose(value, scales[0]) for value in scales)
    # One uniform size adjustment at the socket keeps every donor helmet's proportions intact.
    scales = [(1.15, 1.15, 1.15)]
    helper.update(parent_bone=target_head, key_bone_id=-1, bone_name_crc=0,
                  pivot=tuple(np.array(helper['pivot']) + offset))
    for name in ('translation', 'rotation', 'scale'):
        track = helper[name]
        track.global_sequence = -1
        track.external.clear()
        track.timestamps = [[] for _ in body.sequences]
        value = tuple(scales[0]) if name == 'scale' else None
        track.timestamps = [[0] if value else [] for _ in body.sequences]
        track.values = [[value] if value else [] for _ in body.sequences]
        track.timestamp_spans = track.value_spans = [(0, 0)] * len(body.sequences)
    attachment['bone'] = len(body.bones)
    attachment['position'] = tuple(np.array(player_attachment['position']) + offset + np.array((-.14, 0, 0)))
    body.bones.append(helper)
    blob, separated = arrays.separate_bone_track_arrays(write_md20(body))
    check = parse_m2(blob)
    checks.check_model(check, blob)
    assert check.vertices == original.vertices and check.sequences == original.sequences
    before = copy.copy(original)
    after = copy.copy(check)
    count = len(original.bones) - (1 if 'helmet_socket' in report else 0)
    before.bones, after.bones = original.bones[:count], check.bones[:count]
    checks.tracks_equal(before, after, len(body.sequences))
    path.write_bytes(blob)
    report['sha256'] = t.sha(blob)
    report['helmet_socket'] = {'bone': len(body.bones) - 1, 'parent': target_head,
        'position': list(attachment['position']), 'uniform_scale': float(scales[0][0]),
        'source': 'TaurenMale attachment 11', 'discarded_npc_socket_bone': 118,
        'original_body_and_cloth_tracks_preserved': True}
    t.save(e.WORK / 'report.json', report)
    staged = t.STAGE / 'assets' / t.MODEL.replace('\\', '/')
    staged.parent.mkdir(parents=True, exist_ok=True)
    staged.write_bytes(blob)
    print('Reused Tauren player helmet socket; original body and cloth tracks preserved')


def translate_model(model, delta):
    """Move a fallback into the shared Tauren frame; retain its shape, normals and UVs."""
    def point(value):
        return tuple(float(value[i] + delta[i]) for i in range(3))
    vertices = bytearray(model.vertices)
    for index in range(model.vertex_count):
        struct.pack_into('<3f', vertices, index * 48, *point(struct.unpack_from('<3f', vertices, index * 48)))
    model.vertices = bytes(vertices)
    for bone in model.bones:
        bone['pivot'] = point(bone['pivot'])
    for owner in (*model.attachments, *model.events, *model.particles, *model.ribbons):
        if 'position' in owner:
            owner['position'] = point(owner['position'])
    if all(abs(x) < 1e7 for x in model.bounding_box):
        model.bounding_box = (*point(model.bounding_box[:3]), *point(model.bounding_box[3:]))
    if model.collision_positions:
        model.collision_positions = [point(v) for v in model.collision_positions]
        model.collision_box = (*point(model.collision_box[:3]), *point(model.collision_box[3:]))
    for seq in model.sequences:
        if all(abs(x) < 1e7 for x in (*seq['bounds_min'], *seq['bounds_max'])):
            seq['bounds_min'], seq['bounds_max'] = point(seq['bounds_min']), point(seq['bounds_max'])
    return model


def reuse():
    report = t.p.load_json(t.WORK / 'reports/helmets.json')
    copied = 0
    for key, info in report['sources'].items():
        source = PureWindowsPath(key)
        stem = source.stem.rsplit('_', 1)[0]
        cached = t.WORK / 'helmet-sources' / (info.get('cache_stem', stem) + '.m2')
        data = cached.read_bytes()
        assert t.sha(data) == info['m2_sha256'], 'Donor cache changed: ' + key
        model = parse_m2(data)
        assert model.version == 264
        destination = t.STAGE / 'assets/Item/ObjectComponents/Head' / (stem + '_KbM.m2')
        base_delta = info.setdefault('frame_translation', info.get('translation', [0, 0, 0]))
        delta = np.array(base_delta)
        if stem.lower().startswith(('helm_goggles', 'helm_blindfold', 'helm_eyepatch', 'helm_monocle')):
            delta = delta + np.array((.30, 0, .13))
        delta = delta.tolist()
        info['translation'] = delta
        if any(delta):
            # Translate vertices, bone pivots and effect anchors together. Animation vectors,
            # materials, normals, UVs and the relative shape are preserved.
            import highmountain_complete_tracks as tracks
            import skyborne_visual_pack as visual
            import vrykul_female_pack as arrays
            embedded = visual.read_player_model(cached)
            tracks.embed(embedded, cached.parent, cached.stem)
            modified = translate_model(embedded, delta)
            payload, _ = arrays.separate_bone_track_arrays(write_md20(modified))
            destination.write_bytes(payload)
        else:
            destination.write_bytes(data)
        skin = destination.with_name(destination.stem + '00.skin')
        assert t.sha(skin.read_bytes()) == info['skin_sha256'], 'Donor SKIN changed'
        for seq in model.sequences:
            if seq['flags'] & (0x20 | 0x40):
                continue
            suffix = f'{seq["id"]:04d}-{seq["variation_index"]:02d}.anim'
            payload = cached.with_name(cached.stem + suffix).read_bytes()
            destination.with_name(destination.stem + suffix).write_bytes(payload)
        copied += 1
    report.pop('scale', None)
    report.pop('local_shift', None)
    report['fit_method'] = 'Tauren helmets and player socket; fallback families translated without stretching'
    report['donor_models_byte_identical'] = sum(not any(row.get('translation', []))
                                               for row in report['sources'].values())
    report['per_model_deformation'] = False
    report['socket_uniform_scale'] = 1.15
    report['missing_source_families'] = report.pop('missing_worgen_families',
                                                 report.get('missing_source_families', []))
    t.save(t.WORK / 'reports/helmets.json', report)
    socket()
    print('Reused', copied, 'donor helmet shapes and matching companions')


def prepare():
    """Acquire the installed donor variants with their exact companions, without deformation."""
    files = t.p.ClientFiles(str(t.p.CLIENT_DEFAULT / 'Data'), 'enUS')
    table = t.p.RawWdbc(t.read_baseline('ItemDisplayInfo'))
    stems = {PureWindowsPath(t.p._string(table.strings, t.p._value(row, 4)).decode()).stem
             for row in table.records}
    source_root = t.WORK / 'helmet-sources'
    source_root.mkdir(parents=True, exist_ok=True)
    destination_root = t.STAGE / 'assets/Item/ObjectComponents/Head'
    destination_root.mkdir(parents=True, exist_ok=True)
    report = {'sources': {}, 'missing_source_families': [], 'installed': False, 'live_accepted': False}
    tauren = parse_m2(Path('G:/RetroPorterWork/drakonid/donors/Character/Tauren2/Male/TaurenMale2.m2').read_bytes())

    def relative_attachment(body):
        attachment = next(a for a in body.attachments if a['id'] == 11)
        return np.array(attachment['position']) - body.bones[body.key_bone_lookup[6]]['pivot']

    relative = {'TaM': relative_attachment(tauren)}

    def pin(path, data):
        if path.exists():
            assert path.read_bytes() == data, 'Pinned donor changed: ' + str(path)
        else:
            path.write_bytes(data)

    try:
        for stem in sorted(name for name in stems if name.lower().startswith('helm')):
            for suffix in ('TaM', 'WoM', 'HuM', 'DwM'):
                key = 'Item\\ObjectComponents\\Head\\' + stem + '_' + suffix
                try:
                    blob, provider = files.find(key + '.m2')
                    skin, skin_provider = files.find(key + '00.skin')
                except FileNotFoundError:
                    continue
                model = parse_m2(blob)
                if model.vertex_count:
                    break
            else:
                report['missing_source_families'].append(stem)
                continue
            assert model.version == 264
            # Different donors remain immutable in separate named caches.
            cache_stem = stem + '_' + suffix
            pin(source_root / (cache_stem + '.m2'), blob)
            if suffix not in relative:
                family = {'WoM': 'Worgen', 'DwM': 'Dwarf2', 'HuM': 'Human2'}[suffix]
                base = family[:-1] if family.endswith('2') else family
                key_body = f'Character\\{family}\\Male\\{base}Male' + ('2.m2' if family.endswith('2') else '.m2')
                relative[suffix] = relative_attachment(parse_m2(files.find(key_body)[0]))
            (destination_root / (stem + '_KbM.m2')).write_bytes(blob)
            (destination_root / (stem + '_KbM00.skin')).write_bytes(skin)
            skins = struct.unpack_from('<I', blob, 68)[0]
            assert 1 <= skins <= 4
            for index in range(1, skins):
                payload, _ = files.find(key + f'{index:02d}.skin')
                pin(source_root / (cache_stem + f'{index:02d}.skin'), payload)
                (destination_root / (stem + '_KbM' + f'{index:02d}.skin')).write_bytes(payload)
            companions = {}
            for seq in model.sequences:
                if seq['flags'] & (0x20 | 0x40):
                    continue
                name = f'{seq["id"]:04d}-{seq["variation_index"]:02d}.anim'
                payload, _ = files.find(key + name)
                pin(source_root / (cache_stem + name), payload)
                (destination_root / (stem + '_KbM' + name)).write_bytes(payload)
                companions[name] = t.sha(payload)
            report['sources'][key] = {'m2_sha256': t.sha(blob), 'skin_sha256': t.sha(skin),
                'provider': str(provider), 'skin_provider': str(skin_provider), 'animations': companions,
                'cache_stem': cache_stem, 'translation': (relative[suffix] - relative['TaM']).tolist()}
    finally:
        files.close()
    report['families'] = len(report['sources'])
    t.save(t.WORK / 'reports/helmets.json', report)
    reuse()


def previews():
    body_path = t.WORK / 'equipment/assets' / t.MODEL.replace('\\', '/')
    body = parse_m2(body_path.read_bytes())
    attachment = next(a for a in body.attachments if a['id'] == 11)
    transform = motion.pose_matrices(body, 0, 0)[attachment['bone']]
    table = t.p.RawWdbc(t.read_baseline('ItemDisplayInfo'))
    families = {'Helm_Plate_D_01', 'Helm_Cloth_A_01', 'Helm_Leather_B_01',
                'Helm_Circlet_B_02', 'Helm_Goggles_B_04'}
    files = t.p.ClientFiles(str(t.p.CLIENT_DEFAULT / 'Data'), 'enUS')
    seen = set()
    try:
        for row in table.records:
            stem = PureWindowsPath(t.p._string(table.strings, t.p._value(row, 4)).decode()).stem
            if stem.lower() not in {name.lower() for name in families} or stem.lower() in seen:
                continue
            seen.add(stem.lower())
            path = t.STAGE / 'assets/Item/ObjectComponents/Head' / (stem + '_KbM.m2')
            helm = parse_m2(path.read_bytes())
            skin = parse_skin(path.with_name(path.stem + '00.skin').read_bytes())
            texture = t.p._string(table.strings, t.p._value(row, 12)).decode()
            blob, provider = files.find('Item\\ObjectComponents\\Head\\' + texture + '.blp')
            image = t.Blp.parse(blob).decode_level(0)
            root = t.WORK / 'previews' / ('helmet-' + stem)
            root.mkdir(parents=True, exist_ok=True)
            from PIL import Image
            Image.frombytes('RGBA', (image.width, image.height), bytes(image.data)).save(root / 'helmet.png')
            scene = t.p.load_json(t.WORK / 'previews/naked/model.json')
            if not stem.lower().startswith(('helm_circlet', 'helm_goggles')):
                scene['meshes'] = [part for part in scene['meshes'] if part['geoset'] == 0]
            start = len(scene['vertices'])
            for index in range(helm.vertex_count):
                record = e.equipment.vertex_record(helm, index)
                point = np.array(record['position']) + attachment['position']
                record['position'] = (transform @ np.array([*point, 1]))[:3].tolist()
                scene['vertices'].append(record)
            for part in skin.submeshes:
                triangles = [[v + start for v in face] for face in e.equipment.mesh_triangles(skin, part)]
                scene['meshes'].append({'geoset': 50000, 'triangles': triangles, 'texture': str(root / 'helmet.png')})
            scene.update(camera=[5, -8, 3.2], target=[.3, 0, 2.3], scale=1.8)
            t.save(root / 'model.json', scene)
    finally:
        files.close()
    assert len(seen) == len(families), seen
    print('Exported representative full, open, cloth, circlet and goggles helmet previews')



if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare', 'reuse', 'socket', 'previews'))
    globals()[parser.parse_args().action]()
