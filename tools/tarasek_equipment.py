"""Player equipment on Tarasek anatomy; retain source UVs and authored animations.

Region mapping adapted from the current Drakonid equipment pipeline. Coordinates remain in WoW space.
"""
import copy
from collections import defaultdict
import json
import math
from pathlib import Path
import struct

import tarasek_drakkin as t
from wotlkconv.m2 import parse_m2, parse_skin, write_md20
from wotlkconv.m2.skin import Skin, write_skin
import sethrak_equipment_repair as equipment
import skyborne_visual_pack as visual
import saberon_equipment_fit as fitting
from sethrak_body_regions import cylinder, mirrored_u

WORK = t.WORK / 'equipment'

def anatomy(model):
    bones = model.bones
    arms = []
    for key in (8, 13):
        palm = bones[model.key_bone_lookup[key]]['parent_bone']
        elbow = bones[palm]['parent_bone']
        upper = bones[elbow]['parent_bone']
        arms.append((equipment.descendants(model, upper), equipment.descendants(model, elbow),
                     equipment.descendants(model, palm), upper, elbow, palm))
    legs = []
    for keys in ((55, 57, 60), (56, 58, 59)):
        thigh, knee, foot = (model.key_bone_lookup[k] for k in keys)
        legs.append((equipment.descendants(model, thigh), thigh, knee, foot))
    protected = equipment.descendants(model, model.key_bone_lookup[6])
    protected |= equipment.descendants(model, model.key_bone_lookup[41])
    return arms, legs, protected


def weight(model, tri, group):
    return sum(model.vertices[v * 48 + 12 + i] for v in tri for i in range(4)
               if model.vertices[v * 48 + 16 + i] in group)


def region_uv(model, tri):
    arms, legs, protected = anatomy(model)
    bones = model.bones
    points = [equipment.vertex_record(model, v)['position'] for v in tri]
    if weight(model, tri, protected) >= 255:
        return None
    arm = max(arms, key=lambda a: weight(model, tri, a[0]))
    leg = max(legs, key=lambda a: weight(model, tri, a[0]))
    waist = bones[model.key_bone_lookup[51]]['pivot'][2]
    neck = bones[model.key_bone_lookup[49]]['pivot']
    hip = bones[model.key_bone_lookup[51]]['pivot']
    if weight(model, tri, arm[0]) >= 300:
        if weight(model, tri, arm[2]) >= 300:
            first = bones[arm[5]]['pivot']
            elbow = bones[arm[4]]['pivot']
            last = [first[i] + (first[i] - elbow[i]) * .8 for i in range(3)]
            region, low, high = 2, .5, .625
        elif weight(model, tri, arm[1]) >= 300:
            first, last = bones[arm[4]]['pivot'], bones[arm[5]]['pivot']
            region, low, high = 1, .25, .5
        else:
            first, last = bones[arm[3]]['pivot'], bones[arm[4]]['pivot']
            region, low, high = 0, 0, .25
        # Mirror around the limb like the torso and legs do, so the texture is continuous on every side
        # (an unmirrored wrap leaves a hard seam where the left and right edges of the item art meet).
        return region, [[.001 + .498 * abs(2 * u - 1), low + t * (high - low)]
                        for u, t in (cylinder(p, first, last) for p in points)]
    mean = sum(p[2] for p in points) / 3
    if weight(model, tri, leg[0]) >= 255 or mean < waist:
        first, knee, foot = (bones[i]['pivot'] for i in leg[1:])
        if mean < foot[2] + .15:
            region, a, b, low, high = 7, foot, [foot[0] + .75, foot[1], foot[2] - .3], .875, 1
        elif mean >= knee[2]:
            region, a, b, low, high = 5, [first[0], first[1], waist], knee, .375, .625
        else:
            region, a, b, low, high = 6, knee, foot, .625, .875
        uvs = []
        for p in points:
            if region == 7:
                u, t = cylinder(p, a, b)
                uvs.append([.5035 + abs(2 * u - 1) * .491, low + t * (high - low)])
            else:
                t = min(1, max(0, (a[2] - p[2]) / (a[2] - b[2])))
                cx, cy = (a[i] + t * (b[i] - a[i]) for i in (0, 1))
                uvs.append([mirrored_u(math.atan2(p[1] - cy, p[0] - cx)), low + t * (high - low)])
        return region, uvs
    top = neck[2] + .08
    split = waist + (top - waist) / 3
    region = 3 if mean >= split else 4
    uvs = []
    for x, y, z in points:
        t = min(1, max(0, (z - waist) / (top - waist)))
        cx = hip[0] + t * (neck[0] - hip[0])
        angle = math.atan2(y - hip[1], x - cx)
        v = (top - z) / (top - split) * .25 if region == 3 else .25 + (split - z) / (split - waist) * .125
        if region == 3:
            # The item art leaves its upper corners transparent (neck and shoulder cut-outs). This body's long
            # neck and hump sit in the corners of the back half, so push the back down into the opaque part.
            blend = min(1, max(0, (abs(angle) - 1.0) / 1.2))
            local = v / .25
            v = (local * (1 - blend) + (.38 + .62 * local) * blend) * .25
        uvs.append([mirrored_u(angle), min(.375, max(.004, v))])
    return region, uvs


def source():
    info = json.loads((t.WORK / 'reports/animation-repair.json').read_text())
    blob = Path(info['model']).read_bytes()
    assert t.sha(blob) == info['sha256']
    model = parse_m2(blob)
    keys = t.player_keys(model)
    skin = parse_skin(t.MODEL_SOURCE.with_name('tarasek00.skin').read_bytes())
    t.save(WORK / 'player-key-bones.json', keys)
    return model, skin


def donor():
    import sethrak_animation_pack as motion
    key = 'Character\\Worgen\\Male\\WorgenMale.m2'
    pinned = t.WORK / 'donors' / key.replace('\\', '/')
    skin_path = WORK / 'donor00.skin'
    receipt = WORK / 'donor-receipt.json'
    if pinned.exists() and skin_path.exists() and receipt.exists():
        import highmountain_complete_tracks as tracks
        data = json.loads(receipt.read_text())
        for name, expected in data['hashes'].items():
            assert t.sha((t.WORK / 'donors' / name.replace('\\', '/')).read_bytes()) == expected
        assert t.sha(skin_path.read_bytes()) == data['skin_sha256']
        model = visual.read_player_model(pinned)
        tracks.embed(model, pinned.parent, pinned.stem)
        return model, parse_skin(skin_path.read_bytes())
    files = t.p.ClientFiles(str(t.p.CLIENT_DEFAULT / 'Data'), 'enUS')
    try:
        model, hashes = motion.embedded_model(t.WORK / 'donors', key, lambda k: files.find(k)[0])
        blob, provider = files.find(key[:-3] + '00.skin')
        path = WORK / 'donor00.skin'
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            assert path.read_bytes() == blob
        else:
            path.write_bytes(blob)
    finally:
        files.close()
    t.save(WORK / 'donor-receipt.json', {'hashes': hashes, 'skin_sha256': t.sha(blob),
                                        'skin_provider': str(provider)})
    return model, parse_skin(blob)


def fit_work():
    model, skin = source()
    player, player_skin = donor()
    by_crc = {b['bone_name_crc']: i for i, b in enumerate(model.bones) if b['bone_name_crc']}
    mapped = {}

    def bone(index):
        old = index
        while old >= 0:
            crc = player.bones[old]['bone_name_crc']
            if crc in by_crc:
                mapped[index] = {'target': by_crc[crc], 'ancestor_fallback': old != index}
                return by_crc[crc]
            old = player.bones[old]['parent_bone']
        raise ValueError('No garment bone ancestor: ' + str(index))

    meshes = []
    for i, row in enumerate(player_skin.submeshes):
        geo = visual.u16(row, 0)
        batches = [b for b in player_skin.batches if visual.u16(b, 4) == i]
        types = {player.textures[player.texture_combos[visual.u16(b, 16)]]['type'] for b in batches}
        # Base/sleeve/leg coverage comes from the body shells. Add loose cuffs, tabard and robe.
        if geo in (502, 503, 902, 903, 1102, 1104, 1202, 1302) and types <= {1, 2}:
            meshes.append({'geoset': geo, 'triangles': equipment.mesh_triangles(player_skin, row)})
    assert {1202, 1302} <= {m['geoset'] for m in meshes}, 'Missing tabard/robe donor'
    used = {v for m in meshes for tri in m['triangles'] for v in tri}
    records = [equipment.vertex_record(player, i) for i in range(player.vertex_count)]
    for index in used:
        record = records[index]
        point = record['position'][:]
        for slot, influence in enumerate(record['weights']):
            if not influence:
                continue
            old = record['bones'][slot]
            new = bone(old)
            record['bones'][slot] = new
            for axis in range(3):
                point[axis] += influence / 255 * (model.bones[new]['pivot'][axis] - player.bones[old]['pivot'][axis])
        record['position'] = point
    body = [tri for row in skin.submeshes if visual.u16(row, 0) == 0
            for tri in equipment.mesh_triangles(skin, row)]
    protected = equipment.descendants(model, model.key_bone_lookup[41])
    arms, _, _ = anatomy(model)
    protected |= arms[0][0] | arms[1][0]
    robe = [tri for tri in body if weight(model, tri, protected) < 255]
    # Fit the actual authored crouched standing pose. Fitting only bind coordinates can leave a
    # nominally loose robe inside the thighs once the source animation pitches the pelvis and legs.
    import creature_animation_repair as motion
    import numpy as np
    matrices = motion.pose_matrices(model, 0, 0)
    posed = motion.posed_vertices(model, matrices)
    target_records = [equipment.vertex_record(model, i) for i in range(model.vertex_count)]
    for record, point in zip(target_records, posed, strict=True):
        record['position'] = list(map(float, point))
    inverses = {}
    for index in used:
        record = records[index]
        transform = sum(matrices[b] * w / 255 for b, w in zip(record['bones'], record['weights']) if w)
        record['position'] = (transform @ np.array([*record['position'], 1]))[:3].tolist()
        inverses[str(index)] = np.linalg.inv(transform).tolist()
    hip = model.key_bone_lookup[51]
    waist = (matrices[hip] @ np.array([*model.bones[hip]['pivot'], 1]))[2]
    t.save(WORK / 'fit-work.json', {'target': target_records, 'donor': records, 'equipment': meshes, 'body': body,
        'robe_body': robe, 'waist': float(waist), 'fit_space': 'authored-idle-0',
        'inverse_skinning': inverses, 'bone_mapping': mapped})
    print('Exported', len(meshes), 'garment meshes for surface fitting')


def prepare():
    import sethrak_animation_pack as checks
    import tarasek_cape as cape
    original, skin = source()
    model = copy.deepcopy(original)
    vertices = bytearray(model.vertices)
    meshes = []
    removed = []
    for i, row in enumerate(skin.submeshes):
        batches = [b for b in skin.batches if visual.u16(b, 4) == i]
        types = {model.textures[model.texture_combos[visual.u16(b, 16)]]['type'] for b in batches}
        if 12 in types:
            removed.append(i)
            continue
        geo = visual.u16(row, 0)
        assert geo == 0 or 301 <= geo <= 305
        meshes.append({'row': row, 'batches': batches, 'geoset': geo + 3000 if geo else 0,
                       'triangles': equipment.mesh_triangles(skin, row)})
    assert len(removed) == 11 and len(meshes) == 7, 'Source surface ownership changed'
    # Keep source skin and its UVs. A separate alpha-preserving surface receives equipped item art.
    texture = len(model.textures)
    model.textures.append({'type': 14, 'flags': 0, 'filename': ''})
    combo = len(model.texture_combos)
    model.texture_combos.append(texture)
    material = len(model.materials)
    model.materials.append({'flags': 16, 'blending_mode': 2})
    if not model.texture_coord_combos:
        model.texture_coord_combos.append(0)
    else:
        model.texture_coord_combos[0] = 0
    batch = struct.pack('<12H', 0, 0, 0, 0, 65535, material, 0, 1, combo, 0, 0, 0)
    body = [tri for row in skin.submeshes if visual.u16(row, 0) == 0
            for tri in equipment.mesh_triangles(skin, row)]
    normals = fitting.surface_normals(model, body)
    regional, mapped = defaultdict(list), {}
    for tri in body:
        result = region_uv(model, tri)
        if result is None:
            continue
        region, uvs = result
        face = []
        for v, uv in zip(tri, uvs, strict=True):
            identity = (v, *[round(x, 7) for x in uv])
            if identity not in mapped:
                record = bytearray(original.vertices[v * 48:(v + 1) * 48])
                point = equipment.vertex_record(original, v)['position']
                normal = normals[v]
                struct.pack_into('<3f', record, 0, *[p + n * .012 for p, n in zip(point, normal)])
                struct.pack_into('<3f', record, 20, *normal)
                struct.pack_into('<2f', record, 32, *uv)
                mapped[identity] = len(vertices) // 48
                vertices.extend(record)
            face.append(mapped[identity])
        regional[region].append(tuple(face))
    assert set(regional) == set(range(8)), 'Missing armor region: ' + str(sorted(regional))
    for region, faces in regional.items():
        meshes.append({'row': skin.submeshes[0], 'batches': [batch], 'geoset': 20001 + region,
                       'triangles': faces})
    work = json.loads((WORK / 'fit-work.json').read_text())
    fitted = json.loads((WORK / 'donor-fit.json').read_text())
    remap = {}
    for mesh in work['equipment']:
        faces = []
        for tri in mesh['triangles']:
            face = []
            for index in tri:
                if index not in remap:
                    v = work['donor'][index]
                    record = bytearray(48)
                    import numpy as np
                    point = np.array(work['inverse_skinning'][str(index)]) @ np.array([*fitted[str(index)], 1])
                    struct.pack_into('<3f', record, 0, *point[:3])
                    record[12:20] = bytes(v['weights'] + v['bones'])
                    struct.pack_into('<3f', record, 20, *v['normal'])
                    struct.pack_into('<2f', record, 32, *v['uv'])
                    remap[index] = len(vertices) // 48
                    vertices.extend(record)
                face.append(remap[index])
            faces.append(tuple(face))
        meshes.append({'row': skin.submeshes[0], 'batches': [batch], 'geoset': mesh['geoset'],
                       'triangles': faces})
    player, player_skin = donor()
    cape_texture = len(model.textures)
    model.textures.append({'type': 2, 'flags': 0, 'filename': ''})
    cape_combo = len(model.texture_combos)
    model.texture_combos.append(cape_texture)
    cape_material = len(model.materials)
    model.materials.append({'flags': 4, 'blending_mode': 1})
    cape_batch = struct.pack('<12H', 16, 0, 0, 0, 65535, cape_material, 0, 1, cape_combo, 0, 0, 0)
    cape.cape_surfaces(model, vertices, meshes, skin, player, player_skin, cape_batch)
    model.vertices, model.vertex_count = bytes(vertices), len(vertices) // 48
    raw = Skin()
    for mesh in meshes:
        row = bytearray(mesh['row'])
        first, lookup = len(raw.indices), len(raw.vertices)
        used = list(dict.fromkeys(v for tri in mesh['triangles'] for v in tri))
        indices = {v: lookup + i for i, v in enumerate(used)}
        raw.vertices.extend(used)
        raw.indices.extend(indices[v] for tri in mesh['triangles'] for v in tri)
        for offset, value in ((0, mesh['geoset']), (2, first >> 16), (4, lookup), (6, len(used)),
                              (8, first & 65535), (10, len(mesh['triangles']) * 3)):
            visual.patch16(row, offset, value)
        index = len(raw.submeshes)
        raw.submeshes.append(bytes(row))
        for b in mesh['batches']:
            row_batch = bytearray(b)
            visual.patch16(row_batch, 4, index)
            visual.patch16(row_batch, 6, index)
            raw.batches.append(bytes(row_batch))
    compact = visual.compact_bone_palettes(model, raw)
    assert model.vertices[:len(original.vertices)] == original.vertices
    view = copy.copy(model)
    view.bones = model.bones[:len(original.bones)]
    checks.tracks_equal(original, view, len(original.sequences))
    model.replacable_texture_lookup = [65535] * 16
    for i, texture in enumerate(model.textures):
        if texture['type']:
            model.replacable_texture_lookup[texture['type']] = i
    import vrykul_female_pack as arrays
    blob, separated = arrays.separate_bone_track_arrays(write_md20(model))
    checks.check_model(parse_m2(blob), blob)
    target = WORK / 'assets/custom/tarasek/creature/tarasek/tarasek.m2'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(blob)
    target.with_name('tarasek00.skin').write_bytes(write_skin(compact))
    report = {'model': str(target), 'sha256': t.sha(blob), 'vertices': model.vertex_count,
              'skin_vertices': len(compact.vertices), 'indices': len(compact.indices),
              'maximum_palette': max(visual.u16(row, 12) for row in compact.submeshes),
              'removed_npc_armor_submeshes': removed, 'horn_geosets': list(range(3301, 3306)),
              'regional_triangles': {str(k): len(v) for k, v in regional.items()},
              'garment_geosets': [m['geoset'] for m in work['equipment']],
              'source_vertices_uvs_tracks_preserved': True, 'added_cloth_bones': len(model.bones) - len(original.bones),
              'shared_track_arrays_separated': separated, 'installed': False, 'live_accepted': False}
    t.save(WORK / 'report.json', report)
    print('Prepared naked body, five horns, armor regions, garments and animated cloak:', model.vertex_count)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('fit_work', 'prepare'))
    args = parser.parse_args()
    globals()[args.action]()


