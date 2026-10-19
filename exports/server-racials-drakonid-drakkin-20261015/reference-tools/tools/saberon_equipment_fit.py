"""Restore exact source fur UVs; paint clothing on Saberon-derived, transparent regional surfaces."""

import argparse
from collections import defaultdict
import copy
import hashlib
import math
from pathlib import Path
import struct

import numpy as np
from PIL import Image
from wotlkconv.m2 import parse_m2, parse_skin, write_md20
from wotlkconv.m2.skin import Skin, write_skin

import saberon_race_pack as s
import retroported_race_pack as p
import saberon_equipment_pack as q
import sethrak_equipment_repair as e
from sethrak_body_regions import cylinder, mirrored_u
import creature_animation_repair as motion

STAGE = Path('C:/Users/Zach/.codex/tmp/saberon-equipment-fit-v6')
SOURCE = Path('C:/Users/Zach/.codex/tmp/saberon-equipment')


def torso_surface(model, triangles):
    """Include the connected chest, back and neck ruff; exclude face, jaw, tail and arms."""
    adjacency = defaultdict(set)
    for tri in triangles:
        for vertex in tri:
            adjacency[vertex].update(tri)
    pending, torso = set(adjacency), set()
    while pending:
        todo = [pending.pop()]
        group = set(todo)
        while todo:
            added = adjacency[todo.pop()] - group
            todo.extend(added)
            group.update(added)
            pending.difference_update(added)
        bones = {model.vertices[v * 48 + 16 + i] for v in group for i in range(4)
                 if model.vertices[v * 48 + 12 + i]}
        if {2, 3} <= bones or ({4, 9, 16} <= bones and 29 not in bones and 17 not in bones):
            torso.update(group)
    return torso


def surface_normals(model, triangles):
    """Source shading normals can face inward. Clothing clearance follows the triangle surface."""
    positions = {v: np.array(struct.unpack_from('<3f', model.vertices, v * 48))
                 for tri in triangles for v in tri}
    keys = {v: tuple(np.round(point, 5)) for v, point in positions.items()}
    accumulated = defaultdict(lambda: np.zeros(3))
    for tri in triangles:
        a, b, c = (positions[v] for v in tri)
        normal = np.cross(b - a, c - a)
        for v in tri:
            accumulated[keys[v]] += normal
    return {v: (accumulated[key] / np.linalg.norm(accumulated[key])).tolist() for v, key in keys.items()}


def mix(a, b, t):
    result = {name: [x + t * (y - x) for x, y in zip(a[name], b[name])]
              for name in ('position', 'normal', 'uv')}
    if 'posed_position' in a and 'posed_position' in b:
        result['posed_position'] = [x + t * (y - x)
                                    for x, y in zip(a['posed_position'], b['posed_position'])]
    if 'neckline_v' in a and 'neckline_v' in b:
        result['neckline_v'] = a['neckline_v'] + t * (b['neckline_v'] - a['neckline_v'])
    weights = defaultdict(float)
    for vertex, factor in ((a, 1 - t), (b, t)):
        for bone, weight in zip(vertex['bones'], vertex['weights']):
            if weight:
                weights[bone] += weight * factor
    weights = sorted(weights.items(), key=lambda pair: pair[1], reverse=True)[:4]
    total = sum(weight for _, weight in weights)
    result['weights'] = [round(weight / total * 255) for _, weight in weights]
    result['weights'][0] += 255 - sum(result['weights'])
    result['bones'] = [bone for bone, _ in weights]
    return result


def clip(polygon, distance):
    result = []
    for a, b in zip(polygon, polygon[1:] + polygon[:1]):
        da, db = distance(a), distance(b)
        if da >= 0:
            result.append(a)
        if (da >= 0) != (db >= 0):
            result.append(mix(a, b, da / (da - db)))
    return result


def armor_uvs(model, triangles, torso):
    """Keep complete arm chains left of the atlas and both digitigrade legs on their own right-side axis."""
    bones = model.bones
    arms = []
    for key in (8, 13):
        palm = bones[model.key_bone_lookup[key]]['parent_bone']
        forearm, upper = bones[palm]['parent_bone'], bones[bones[palm]['parent_bone']]['parent_bone']
        arms.append((e.descendants(model, upper), e.descendants(model, forearm),
                     e.descendants(model, palm), upper, forearm, palm))
    legs = [(e.descendants(model, thigh), thigh, knee, hock, foot)
            for thigh, knee, hock, foot in ((6, 11, 20, 26), (7, 12, 21, 27))]
    waist = (bones[6]['pivot'][2] + bones[7]['pivot'][2]) / 2
    source = [struct.unpack_from('<3f', model.vertices, i * 48) for i in range(model.vertex_count)]
    matrices = motion.pose_matrices(model, 0, 0)
    posed = motion.posed_vertices(model, matrices)
    neck = (matrices[9] @ np.array([*bones[9]['pivot'], 1]))[:3]
    hip = (matrices[3] @ np.array([*bones[3]['pivot'], 1]))[:3]
    knee_z = sum((matrices[i] @ np.array([*bones[i]['pivot'], 1]))[2] for i in (11, 12)) / 2
    back_top = max(posed[v][2] for v in torso) - .055

    def weight(tri, group):
        return sum(model.vertices[v * 48 + 12 + slot] for v in tri for slot in range(4)
                   if model.vertices[v * 48 + 16 + slot] in group)

    result = []
    for tri in triangles:
        arm = max(arms, key=lambda item: weight(tri, item[0]))
        points = [source[v] for v in tri]
        is_torso = tri[0] in torso
        if not is_torso and weight(tri, arm[0]) >= 255:
            if weight(tri, arm[2]) >= 255:
                first = bones[arm[5]]['pivot']
                last = tuple(first[i] + .32 * (first[i] - bones[arm[4]]['pivot'][i])
                             / math.dist(first, bones[arm[4]]['pivot']) for i in range(3))
                region, bounds = 2, (.5, .625)
            elif weight(tri, arm[1]) >= 255:
                first, last, region, bounds = bones[arm[4]]['pivot'], bones[arm[5]]['pivot'], 1, (.25, .5)
            else:
                first, last, region, bounds = bones[arm[3]]['pivot'], bones[arm[4]]['pivot'], 0, (0, .25)
                length = math.dist(first, last)
                first = tuple(first[i] - .22 * (last[i] - first[i]) / length for i in range(3))
            uv = []
            for point in points:
                u, t = cylinder(point, first, last)
                uv.append([min(.499, max(.001, u * .5)), bounds[0] + t * (bounds[1] - bounds[0])])
        elif not is_torso and (sum(point[2] for point in points) / 3 < waist
                              or max(weight(tri, leg[0]) for leg in legs) >= 255):
            leg = max(legs, key=lambda item: (weight(tri, item[0]),
                      -abs(sum(p[1] for p in points) / 3 - bones[item[1]]['pivot'][1])))
            knee, hock, foot = (bones[i]['pivot'] for i in leg[2:])
            region = 5 if sum(p[2] for p in points) / 3 >= knee[2] else 6
            uv = []
            for x, y, z in points:
                first, last, low, high = (bones[leg[1]]['pivot'], knee, .375, .625) if z >= knee[2] else \
                    (knee, hock, .625, .75) if z >= hock[2] else (hock, foot, .75, .875)
                t = min(1, max(0, (first[2] - z) / (first[2] - last[2])))
                cx, cy = (first[i] + t * (last[i] - first[i]) for i in (0, 1))
                uv.append([mirrored_u(math.atan2(y - cy, x - cx)), low + t * (high - low)])
        else:
            points = [posed[v] for v in tri]
            height = sum(p[2] for p in points) / 3
            region = 5 if height < hip[2] else 3 if height >= hip[2] + .25 else 4
            uv = []
            for x, y, z in points:
                t = min(1, max(0, (z - hip[2]) / (back_top - hip[2])))
                cx = hip[0] + t * (neck[0] - hip[0])
                angle = math.atan2(y - hip[1], x - cx)
                if region == 5:
                    # Sample leggings below the waist instead of stretching the atlas boundary row.
                    v = .375 + min(1, max(0, (hip[2] - z) / (hip[2] - knee_z))) * .25
                    uv.append([mirrored_u(angle), v])
                    continue
                facing = max(0, math.cos(angle))
                top = back_top * (1 - facing) + (neck[2] - .025) * facing
                split = hip[2] + (top - hip[2]) / 3
                v = (top - z) / (top - split) * .25 if z >= split else \
                    .25 + (split - z) / (split - hip[2]) * .125
                uv.append([mirrored_u(angle), min(.375, v)])
        result.append((region, uv))
    return result


def collar_texture_v(u, v):
    """Keep the authored front opening; sample below the rear cutout along the smooth mesh collar."""
    back = min(1, max(0, (u - .85) / .145))
    back = back * back * (3 - 2 * back)
    fade = min(1, max(0, (.14 - v) / .136))
    fade = fade * fade * (3 - 2 * fade)
    return v + .075 * back * fade


def clothing_polygons(model, triangles, torso, normals):
    """Refine only the neckline; raise rear coverage while preserving the face and lower region joins."""
    matrices = motion.pose_matrices(model, 0, 0)
    posed = motion.posed_vertices(model, matrices)
    neck = (matrices[9] @ np.array([*model.bones[9]['pivot'], 1]))[:3]
    hip = (matrices[3] @ np.array([*model.bones[3]['pivot'], 1]))[:3]
    back_top = max(posed[v][2] for v in torso) + .045
    half_width = max(abs(posed[v][1] - hip[1]) for v in torso)
    for tri, (region, uvs) in zip(triangles, armor_uvs(model, triangles, torso), strict=True):
        polygon = [dict(e.vertex_record(model, index), uv=uv, normal=normals[index],
                        posed_position=posed[index].tolist(),
                        record=model.vertices[index * 48:(index + 1) * 48])
                   for index, uv in zip(tri, uvs, strict=True)]
        polygons = [polygon]
        if region == 3 and min(v['uv'][1] for v in polygon) < .14:
            for _ in range(2):
                refined = []
                for a, b, c in polygons:
                    ab, bc, ca = mix(a, b, .5), mix(b, c, .5), mix(c, a, .5)
                    refined.extend(([a, ab, ca], [ab, b, bc], [ca, bc, c], [ab, bc, ca]))
                polygons = refined
            for polygon in polygons:
                for index, vertex in enumerate(polygon):
                    x, y, z = vertex['posed_position']
                    t = min(1, max(0, (z - hip[2]) / (back_top - hip[2])))
                    cx = hip[0] + t * (neck[0] - hip[0])
                    facing = max(0, math.cos(math.atan2(y - hip[1], x - cx))) ** 4
                    top = back_top * (1 - facing) + (neck[2] - .025) * facing
                    split = hip[2] + (top - hip[2]) / 3
                    target_v = (top - z) / (top - split) * .25
                    old_v = vertex['uv'][1]
                    fade = min(1, max(0, (.14 - old_v) / .14))
                    fade = fade * fade * (3 - 2 * fade)
                    rear = min(1, max(0, (neck[0] + .05 - x) / .12))
                    normal = sum((matrices[bone][:3, :3] @ np.array(vertex['normal'])) * weight / 255
                                 for bone, weight in zip(vertex['bones'], vertex['weights']) if weight)
                    rear = max(rear, min(1, max(0, normal[2] * 3)))
                    rear = rear * rear * (3 - 2 * rear)
                    back_u = .994 - min(1, abs(y - hip[1]) / half_width) * .244
                    u = vertex['uv'][0] + fade * rear * (back_u - vertex['uv'][0])
                    # Shared subdivision corners must be assigned fresh UV lists, never mutated in place.
                    polygon[index] = dict(vertex, uv=[u, old_v + fade * (target_v - old_v)])
        for polygon in polygons:
            if region == 3:
                polygon = [dict(v, neckline_v=v['uv'][1]) for v in polygon]
                polygon = clip(polygon, lambda v: v['neckline_v'] - .004)
            elif region == 4:
                polygon = clip(polygon, lambda v: v['uv'][1] - .004)
            if region == 3:
                # Interpolated skin weights must be corrected to stay on the rendered triangle plane.
                fitted = []
                for vertex in polygon:
                    transform = sum(matrices[bone] * weight / 255
                                    for bone, weight in zip(vertex['bones'], vertex['weights']) if weight)
                    point = np.linalg.inv(transform) @ np.array([*vertex['posed_position'], 1])
                    u, v = vertex['uv']
                    fitted.append(dict(vertex, position=point[:3].tolist(), uv=[u, collar_texture_v(u, v)]))
                polygon = fitted
            if len(polygon) >= 3:
                yield region, polygon


def prepare():
    from haranir_race_pack import lznt1
    STAGE.mkdir(parents=True, exist_ok=True)
    original = parse_m2((SOURCE / 'before.m2').read_bytes())
    original_skin = parse_skin((SOURCE / 'before.skin').read_bytes())
    model = parse_m2(s.local(SOURCE / 'assets', s.MODEL).read_bytes())
    current = parse_skin(s.local(SOURCE / 'assets', q.SKIN).read_bytes())
    model.materials[10] = {'flags': 16, 'blending_mode': 2}  # Clothing only; original fur stays opaque.
    body_batch = struct.pack('<12H', 0, 0, 0, 0, 65535, 10, 0, 1, 6, 0, 0, 0)
    assert model.textures[model.texture_combos[6]]['type'] == 1
    meshes = []
    for index, row in enumerate(original_skin.submeshes):
        batches = [b for b in original_skin.batches if s.visual.u16(b, 4) == index]
        geo = s.visual.u16(row, 0)
        types = {model.textures[model.texture_combos[s.visual.u16(b, 16)]]['type'] for b in batches}
        geo = 21000 + geo - 3100 if geo and types & {12, 13} else geo
        meshes.append({'row': row, 'batches': batches, 'geoset': geo,
                       'triangles': e.mesh_triangles(original_skin, row)})
    work = s.p.load_json(SOURCE / 'male-body-work.json')
    source_triangles = [tri for row in original_skin.submeshes if s.visual.u16(row, 0) == 0
                        for tri in e.mesh_triangles(original_skin, row)]
    torso = torso_surface(original, source_triangles)
    normals = surface_normals(original, source_triangles)
    triangles = list(dict.fromkeys([tuple(tri) for tri in work['body']]
                                  + [tri for tri in source_triangles if tri[0] in torso]))
    vertices, remapped, regions = bytearray(model.vertices), {}, {}
    for region, polygon in clothing_polygons(original, triangles, torso, normals):
        face = []
        for vertex in polygon:
            uv = vertex['uv']
            key = (*vertex['position'], *vertex['normal'], *vertex['bones'], *vertex['weights'],
                   *[round(v, 7) for v in uv])
            if key not in remapped:
                record = bytearray(vertex.get('record', bytes(48)))
                point, normal = vertex['position'], vertex['normal']
                record[12:16] = bytes(vertex['weights'] + [0] * (4 - len(vertex['weights'])))
                record[16:20] = bytes(vertex['bones'] + [0] * (4 - len(vertex['bones'])))
                struct.pack_into('<3f', record, 20, *normal)
                # UV regions share one geometric shell; different offsets open holes at their joins.
                clearance = .018
                struct.pack_into('<3f', record, 0, *[x + n * clearance for x, n in zip(point, normal)])
                struct.pack_into('<2f', record, 32, *uv)
                remapped[key] = len(vertices) // 48
                vertices.extend(record)
            face.append(remapped[key])
        regions.setdefault(region, []).extend((face[0], face[i], face[i + 1]) for i in range(1, len(face) - 1))
    for region, faces in regions.items():
        meshes.append({'row': original_skin.submeshes[0], 'batches': [body_batch],
                       'geoset': 20001 + region, 'triangles': faces})
    # A separate leggings component retains every pixel while the belt uses its own waist surface.
    pants_texture = len(model.textures)
    model.textures.append({'type': 10, 'flags': 0, 'filename': ''})
    pants_combo = len(model.texture_combos)
    model.texture_combos.append(pants_texture)
    pants_batch = struct.pack('<12H', 0, 0, 0, 0, 65535, 10, 0, 1, pants_combo, 0, 0, 0)
    cropped = []
    for face in regions[5]:
        mapped_face = []
        for index in face:
            record = bytearray(vertices[index * 48:(index + 1) * 48])
            u, v = struct.unpack_from('<2f', record, 32)
            struct.pack_into('<2f', record, 32, (u - .5) * 2, (v - .375) * 4)
            mapped_face.append(len(vertices) // 48)
            vertices.extend(record)
        cropped.append(tuple(mapped_face))
    meshes.append({'row': original_skin.submeshes[0], 'batches': [pants_batch],
                   'geoset': 20009, 'triangles': cropped})
    belt_texture = len(model.textures)
    model.textures.append({'type': 9, 'flags': 0, 'filename': ''})
    belt_combo = len(model.texture_combos)
    model.texture_combos.append(belt_texture)
    belt_batch = struct.pack('<12H', 0, 0, 0, 0, 65535, 10, 0, 1, belt_combo, 0, 0, 0)
    belt_faces = []

    for row in original_skin.submeshes:
        if s.visual.u16(row, 0) != 0:
            continue
        for tri in e.mesh_triangles(original_skin, row):
            if tri[0] not in torso:
                continue
            polygon = [dict(e.vertex_record(original, index), normal=normals[index]) for index in tri]
            polygon = clip(polygon, lambda v: v['position'][2] - 1.42)
            polygon = clip(polygon, lambda v: 1.65 - v['position'][2])
            indices = []
            for vertex in polygon:
                point, normal = vertex['position'], vertex['normal']
                record = bytearray(48)
                struct.pack_into('<3f', record, 0, *[x + n * .035 for x, n in zip(point, normal)])
                record[12:16] = bytes(vertex['weights'] + [0] * (4 - len(vertex['weights'])))
                record[16:20] = bytes(vertex['bones'] + [0] * (4 - len(vertex['bones'])))
                struct.pack_into('<3f', record, 20, *normal)
                struct.pack_into('<2f', record, 32, abs(math.atan2(point[1], point[0] - .04)) / math.pi,
                                 (1.65 - point[2]) / .23 * .254)
                indices.append(len(vertices) // 48)
                vertices.extend(record)
            belt_faces.extend((indices[0], indices[i], indices[i + 1]) for i in range(1, len(indices) - 1))
    meshes.append({'row': original_skin.submeshes[0], 'batches': [belt_batch],
                   'geoset': 20008, 'triangles': belt_faces})
    # Retain the separate hanging garments and the already fitted cape. Discard all borrowed limb/belt pieces.
    for index, row in enumerate(current.submeshes):
        geo = s.visual.u16(row, 0)
        if geo not in (1202, 1302, 1502, 1503, 1504, 1505, 1506):
            continue
        batches = [b for b in current.batches if s.visual.u16(b, 4) == index]
        meshes.append({'row': row, 'batches': batches, 'geoset': geo, 'triangles': e.mesh_triangles(current, row)})
    model.vertices, model.vertex_count = bytes(vertices), len(vertices) // 48
    raw = Skin()
    for index, mesh in enumerate(meshes):
        row = bytearray(mesh['row'])
        first, lookup = len(raw.indices), len(raw.vertices)
        used = list(dict.fromkeys(v for tri in mesh['triangles'] for v in tri))
        table = {v: lookup + i for i, v in enumerate(used)}
        raw.vertices.extend(used)
        raw.indices.extend(table[v] for tri in mesh['triangles'] for v in tri)
        for offset, value in ((0, mesh['geoset']), (2, first >> 16), (4, lookup), (6, len(used)),
                              (8, first & 65535), (10, 3 * len(mesh['triangles']))):
            s.visual.patch16(row, offset, value)
        raw.submeshes.append(bytes(row))
        for source in mesh['batches']:
            batch = bytearray(source)
            s.visual.patch16(batch, 4, index)
            s.visual.patch16(batch, 6, index)
            raw.batches.append(bytes(batch))
    compact = s.visual.compact_bone_palettes(model, raw)
    model.replacable_texture_lookup[9] = belt_texture
    model.replacable_texture_lookup[10] = pants_texture
    from creature_clothing_repair import redirect
    redirect(model)
    target = s.local(STAGE / 'assets', s.MODEL)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(write_md20(model))
    target.with_name(target.stem + '00.skin').write_bytes(write_skin(compact))
    records = (SOURCE / 'EsteriaSaberon.bin').read_bytes()
    rows = [records[at:at + 156] for at in range(12, len(records), 156)
            if struct.unpack_from('<I', records, at + 4)[0] != 3]
    empty = bytearray(512 * 512 * 4)
    # RtlCompressBuffer treats all-zero input as a sparse block; invisible RGB keeps a valid compressed stream.
    empty[0] = 1
    packed = lznt1(bytes(empty))
    bank = bytearray(struct.pack('<4I', 0x31544845, 1, 1, 0) + struct.pack('<3I', 512, 512, len(packed)) + packed)
    rows.append(struct.pack('<7I', 0, 3, 0, 16, 0xffffffff, 0xffffffff, 0xffffffff) + b'1:0'.ljust(128, b'\0'))
    for region in range(9):
        rows.append(struct.pack('<7I', 0, 2, 0, 20001 + region, 0xffffffff, 0xffffffff, 0xffffffff) + bytes(128))
    struct.pack_into('<I', bank, 12, int.from_bytes(hashlib.sha256(bank[16:]).digest()[:4], 'little'))
    (STAGE / 'EsteriaSaberonTextures.bin').write_bytes(bank)
    (STAGE / 'EsteriaSaberon.bin').write_bytes(struct.pack('<3I', 0x314D4845, 1, len(rows)) + b''.join(rows))
    files = p.ClientFiles(str(p.CLIENT_DEFAULT / 'Data'), 'enUS')
    try:
        table = p.RawWdbc(files.find(p.DBC_ROOT + 'ItemDisplayInfo.dbc')[0])
        coverage = [(p._value(row, 0), sum((1 << region) for region in range(7)
                     if p._value(row, (15 + region) * 4))) for row in table.records]
        coverage = [(display, mask) for display, mask in coverage if mask]
        (STAGE / 'EsteriaSaberonCoverage.bin').write_bytes(
            struct.pack('<3I', 0x56434253, 1, len(coverage)) + b''.join(struct.pack('<2I', *row) for row in coverage))
        belt_path = 'Item\\TextureComponents\\LegUpperTexture\\leather_raidrogue_h_01blood_belt_lu_U.blp'
        files.find(belt_path)  # Verify the reported belt resolves before enabling its material.
        rows.append(struct.pack('<7I', 0, 5, 9, 64430, 0xffffffff, 0xffffffff, 0xffffffff)
                    + belt_path.encode().ljust(128, b'\0'))
        pants_row = next(row for row in table.records if p._value(row, 0) == 64588)
        pants_stem = p._string(table.strings, p._value(pants_row, 20 * 4)).decode()
        pants_path = 'Item\\TextureComponents\\LegUpperTexture\\' + pants_stem + '_U.blp'
        files.find(pants_path)
        rows.append(struct.pack('<7I', 0, 5, 10, 64588, 0xffffffff, 0xffffffff, 0xffffffff)
                    + pants_path.encode().ljust(128, b'\0'))
        (STAGE / 'EsteriaSaberon.bin').write_bytes(struct.pack('<3I', 0x314D4845, 1, len(rows)) + b''.join(rows))
    finally:
        files.close()
    Image.new('RGBA', (512, 512)).save(STAGE / 'male-player-skin-0.png')
    s.save(STAGE / 'fit-report.json', {'indices': len(compact.indices), 'vertices': model.vertex_count,
        'restored_source_uvs': True, 'regions': {str(k): len(v) for k, v in regions.items()},
        'source': str(SOURCE), 'preserved_original_materials': len(original.materials)})
    print('PREPARED exact original fur plus transparent Saberon-derived clothing regions; no donor limb meshes')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare', 'stage', 'native', 'install'))
    action = parser.parse_args().action
    if action == 'prepare':
        prepare()
    else:
        q.STAGE = STAGE
        getattr(q, action)()
