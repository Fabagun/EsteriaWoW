"""Stage Blood Elf ears for Retail Humans (custom/humanears/<human model>-ears.{m2,skin,ear}).

Geometry: each Blood Elf ear geoset (702 long, 703 swept, 704 short) keeps its authored shape and size. It is moved
per side onto the Human ear opening, its root ring is reshaped to seal that opening (no Human ear geometry is shown
with it), and it is rigidly skinned to the Human head bone.

Texture: the Blood Elf's own painted ear is copied (as UV islands at half resolution) into an area of the Human body
sheet that no Human mesh samples. It is stored as skin-relative detail (pixel / default Blood Elf skin tone, from its
torso), and the client multiplies it by the composed Human skin tone around the Human ear opening (RetailRace.cpp,
PaintElfEars), so the ear matches the skin it joins for every face and skin colour. The .ear file layout is:
'HEAR', u16 x, y, w, h (destination in sheet pixels), u16 n, n * (u16 x, u16 y) tone sample texels, then w*h RGBA
texels where rgb is detail * 128 and alpha is coverage.
"""

import copy
import hashlib
import json
from pathlib import Path
import struct
from collections import Counter

import numpy as np

WORK = Path('G:/RetroportWork/human-ears')
SOURCE = WORK / 'source'
PREVIEW = WORK / 'preview'
# sex: (human model, human skin, human skel, blood elf model, blood elf skin)
MODELS = {0: (1011653, 1012983, 2138400, 1100087, 1100099), 1: (1000764, 1000778, 2137789, 1100258, 1100298)}
EARS = (702, 703, 704)
SHEET = (2048, 1024)
TEXEL_SCALE = 0.5
PAD = 4  # dilated texels around each island against bilinear/mip bleed
TONE_REACH = 0.025  # yards around the ear opening whose head skin sets the ear tone
TONE_SAMPLES = 4096
ELF_TONE_BOX = (60, 300, 400, 460)  # sheet pixels (x0, y0, x1, y1): plain torso skin on the Blood Elf layouts
SEAL_REACH = 0.015  # yards from the elf root ring over which it is reshaped onto the Human head opening
SEAL_OUTSET = 0.0015  # overlap the opening's edge slightly so no sliver of the hole shows


def submesh_triangles(model, skin, geosets=None, texture_type=None):
    from sethrak_equipment_repair import mesh_triangles
    found = {}
    for ordinal, row in enumerate(skin.submeshes):
        geoset = struct.unpack_from('<H', row)[0]
        if geosets is not None and geoset not in geosets:
            continue
        if texture_type is not None:
            types = {model.textures[model.texture_combos[struct.unpack_from('<H', b, 16)[0]]]['type']
                     for b in skin.batches if struct.unpack_from('<H', b, 4)[0] == ordinal}
            if texture_type not in types:
                continue
        found.setdefault(geoset, {'row': row, 'triangles': []})['triangles'] += mesh_triangles(skin, row)
    return found


def ring_seal(human_ring, elf_ring):
    """Reshape the elf ear root so its open ring lies on the Human head opening; fades out into the authored ear."""
    centre = human_ring.mean(0)
    e1, e2, normal = np.linalg.svd(human_ring - centre)[2]

    def polar(points):
        q = points - centre
        height = q @ normal
        return np.arctan2(q @ e2, q @ e1), np.linalg.norm(q - np.outer(height, normal), axis=1), height

    def profile(points):
        angle, radius, height = polar(points)
        order = np.argsort(angle)
        return angle[order], radius[order], height[order]

    human, elf = profile(human_ring), profile(elf_ring)

    def at(curve, angle):
        return [np.interp(angle, curve[0], values, period=2 * np.pi) for values in curve[1:]]

    def apply(point):
        angle, radius, height = (value[0] for value in polar(point[None]))
        weight = np.clip(1 - np.linalg.norm(elf_ring - point, axis=1).min() / SEAL_REACH, 0, 1)
        weight = weight * weight * (3 - 2 * weight)
        (human_radius, human_height), (elf_radius, elf_height) = at(human, angle), at(elf, angle)
        q = point - centre
        planar = q - (q @ normal) * normal
        planar *= (radius + weight * (human_radius - elf_radius + SEAL_OUTSET)) / max(radius, 1e-6)
        return centre + planar + (height + weight * (human_height - elf_height)) * normal

    return apply


def opening_texels(model, skin, rings):
    """Sheet texels of the head skin around the ear openings (ear geosets excluded), as (x, y) pixels."""
    from sethrak_equipment_repair import vertex_record
    near = []
    for geoset, mesh in submesh_triangles(model, skin, texture_type=1).items():
        if geoset // 100 == 7:
            continue
        for tri in mesh['triangles']:
            centre = np.mean([vertex_record(model, i)['position'] for i in tri], axis=0)
            if min(np.linalg.norm(ring - centre, axis=1).min() for ring in rings.values()) < TONE_REACH:
                near.append([vertex_record(model, i)['uv'] for i in tri])
    ys, xs = np.nonzero(raster(near, SHEET))
    assert len(xs) >= 256, 'no head skin found around the ear opening'
    pick = np.random.default_rng(0).choice(len(xs), min(TONE_SAMPLES, len(xs)), replace=False)
    return np.column_stack([xs[pick], ys[pick]])


def root_rings(model, triangles):
    """Points of the open root loop on each side (+y, -y)."""
    from sethrak_equipment_repair import vertex_record
    positions = {i: tuple(np.round(vertex_record(model, i)['position'], 4)) for tri in triangles for i in tri}
    edges = Counter(tuple(sorted((positions[a], positions[b])))
                    for tri in triangles for a, b in ((tri[0], tri[1]), (tri[1], tri[2]), (tri[2], tri[0])))
    boundary = {p for edge, count in edges.items() if count == 1 for p in edge}
    rings = {}
    for side in (1, -1):
        points = np.array([p for p in boundary if p[1] * side > 0])
        assert len(points) >= 8, 'ear root ring not found'
        rings[side] = points
    return rings


def uv_islands(model, triangles):
    """Vertex index -> island id, by triangle connectivity (a UV seam splits M2 vertices)."""
    parent = {}

    def find(i):
        while parent.setdefault(i, i) != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for a, b, c in triangles:
        parent[find(b)] = find(a)
        parent[find(c)] = find(a)
    roots = sorted({find(i) for i in parent})
    return {i: roots.index(find(i)) for i in parent}


def raster(triangles_uv, size):
    from PIL import Image, ImageDraw
    mask = Image.new('L', size, 0)
    draw = ImageDraw.Draw(mask)
    for tri in triangles_uv:
        draw.polygon([(u * size[0], v * size[1]) for u, v in tri], fill=255)
    return np.array(mask) > 0


def dilate(mask, texels):
    from PIL import Image, ImageFilter
    image = Image.fromarray(mask.astype(np.uint8) * 255).filter(ImageFilter.MaxFilter(2 * texels + 1))
    return np.array(image) > 0


def free_rectangle(occupied):
    """Largest empty axis-aligned rectangle (x, y, w, h) in a boolean mask."""
    best, heights = (0, 0, 0, 0, 0), np.zeros(occupied.shape[1], int)
    for y in range(occupied.shape[0]):
        heights = np.where(occupied[y], 0, heights + 1)
        stack = []
        for x in range(occupied.shape[1] + 1):
            current, start = (heights[x] if x < occupied.shape[1] else 0), x
            while stack and stack[-1][1] >= current:
                sx, sh = stack.pop()
                if sh * (x - sx) > best[0]:
                    best = (sh * (x - sx), sx, y - sh + 1, x - sx, sh)
                start = sx
            stack.append((start, current))
    return best[1:]


def build(sex):
    from PIL import Image
    from wotlkconv.m2 import parse_m2, parse_skin, write_md20
    from wotlkconv.m2.skel import parse_skel
    from wotlkconv.m2.skin import write_skin
    from wotlkconv.m2.types import Track
    from sethrak_equipment_repair import packed_skin, vertex_record

    human_id, human_skin_id, skel_id, elf_id, elf_skin_id = MODELS[sex]
    source = SOURCE / f'{human_id}.m2'
    original = hashlib.sha256(source.read_bytes()).hexdigest()
    model = parse_m2(source.read_bytes())
    skel = parse_skel((SOURCE / f'{skel_id}.skel').read_bytes())
    model.bones, model.key_bone_lookup = copy.deepcopy(skel.bones), list(skel.key_bone_lookup)
    human_skin = parse_skin((SOURCE / f'{human_skin_id}.skin').read_bytes())
    elf = parse_m2((SOURCE / f'{elf_id}.m2').read_bytes())
    elf_skin = parse_skin((SOURCE / f'{elf_skin_id}.skin').read_bytes())

    human_ears = submesh_triangles(model, human_skin, {702})[702]['triangles']
    elf_ears = submesh_triangles(elf, elf_skin, set(EARS))
    assert set(elf_ears) == set(EARS)
    target_rings, source_rings = root_rings(model, human_ears), root_rings(elf, elf_ears[702]['triangles'])
    offsets = {side: target_rings[side].mean(0) - source_rings[side].mean(0) for side in (1, -1)}
    seals = {side: ring_seal(target_rings[side], source_rings[side] + offsets[side]) for side in (1, -1)}
    head = model.key_bone_lookup[6]
    assert head < 256 and model.bones[head]['bone_name_crc'] == 0x7c159a2  # the shared humanoid Head bone

    # Texture: Blood Elf ear islands -> a free area of the Human sheet.
    elf_tris = [t for g in EARS for t in elf_ears[g]['triangles']]
    island = uv_islands(elf, elf_tris)
    uv = {i: np.array(vertex_record(elf, i)['uv']) for i in island}
    boxes = {}
    for i, k in island.items():
        lo, hi = boxes.get(k, (uv[i], uv[i]))
        boxes[k] = (np.minimum(lo, uv[i]), np.maximum(hi, uv[i]))
    # Both sides and all three styles reuse the same painted areas: merge overlapping islands into one region.
    merged = True
    while merged:
        merged = False
        for a in list(boxes):
            for b in list(boxes):
                if a < b and a in boxes and b in boxes and (boxes[a][0] <= boxes[b][1]).all() and (boxes[b][0] <= boxes[a][1]).all():
                    boxes[a] = (np.minimum(boxes[a][0], boxes[b][0]), np.maximum(boxes[a][1], boxes[b][1]))
                    del boxes[b]
                    island = {i: a if k == b else k for i, k in island.items()}
                    merged = True
    sheet = np.array(SHEET)
    human_uv = [[vertex_record(model, i)['uv'] for i in t]
                for g in submesh_triangles(model, human_skin, texture_type=1).values() for t in g['triangles']]
    quarter = raster(human_uv, tuple(sheet // 4))
    quarter = dilate(quarter, 2)
    fx, fy, fw, fh = (np.array(free_rectangle(quarter)) * 4).tolist()
    placements, cursor, shelf = {}, np.array([fx, fy]), 0
    for k in sorted(boxes, key=lambda k: -(boxes[k][1] - boxes[k][0])[1]):
        size = np.ceil((boxes[k][1] - boxes[k][0]) * sheet * TEXEL_SCALE).astype(int) + 2 * PAD
        if cursor[0] + size[0] > fx + fw:
            cursor, shelf = np.array([fx, cursor[1] + shelf]), 0
        assert cursor[1] + size[1] <= fy + fh, 'Blood Elf ear islands do not fit the free sheet area'
        placements[k] = cursor + PAD
        cursor, shelf = cursor + [size[0], 0], max(shelf, size[1])
    used = np.array([max(placements[k][0] + (boxes[k][1] - boxes[k][0])[0] * sheet[0] * TEXEL_SCALE + PAD
                         for k in boxes), max(placements[k][1] + (boxes[k][1] - boxes[k][0])[1] * sheet[1] *
                                                TEXEL_SCALE + PAD for k in boxes)])
    dx, dy = fx, fy
    dw, dh = (np.ceil(used) - [dx, dy]).astype(int)

    def target_uv(i):
        k = island[i]
        pixel = placements[k] + (uv[i] - boxes[k][0]) * sheet * TEXEL_SCALE
        return pixel / sheet

    # Paint the patch: sample the composed Blood Elf sheet per destination texel through each island's transform.
    elf_sheet = np.asarray(Image.open(PREVIEW / f'elf{sex}-type1.png').convert('RGB'), dtype=np.float64)
    patch = np.zeros((dh, dw, 3))
    coverage = np.zeros((dh, dw), bool)
    for k in boxes:
        tris = [[(target_uv(i) * sheet - [dx, dy]) / [dw, dh] for i in t] for t in elf_tris if island[t[0]] == k]
        mask = raster([[tuple(p) for p in t] for t in tris], (dw, dh))
        mask = dilate(mask, PAD)
        ys, xs = np.nonzero(mask)
        src = boxes[k][0] * sheet + ((np.column_stack([xs, ys]) + [dx, dy]) - placements[k]) / TEXEL_SCALE
        src = np.clip(src.round().astype(int), 0, sheet - 1)
        patch[ys, xs] = elf_sheet[src[:, 1], src[:, 0]]
        coverage |= mask
    # Human tone comes from the head skin the ear joins: face choices paint their own ears in different shades
    # (some much darker than the face), and the torso can differ from the face. The Blood Elf reference is its
    # default look, whose face matches its torso; the torso avoids the female's painted hairline.
    x0, y0, x1, y1 = ELF_TONE_BOX
    elf_tone = np.median(elf_sheet[y0:y1, x0:x1].reshape(-1, 3), axis=0)
    detail = np.clip(patch / elf_tone * 128, 0, 255).astype(np.uint8)
    samples = opening_texels(model, human_skin, target_rings)
    texels = np.dstack([detail, coverage.astype(np.uint8) * 255])
    ear = (b'HEAR' + struct.pack('<5H', dx, dy, dw, dh, len(samples)) + samples.astype('<u2').tobytes()
           + texels.tobytes())

    vertices, meshes, emitted = bytearray(), [], {}

    def emit(index):
        if index not in emitted:
            v = vertex_record(elf, index)
            side = 1 if v['position'][1] > 0 else -1
            point = seals[side](np.array(v['position']) + offsets[side])
            assert np.isfinite(point).all()
            emitted[index] = len(vertices) // 48
            vertices.extend(struct.pack('<3f4B4B3f2f2f', *point, 255, 0, 0, 0, head, 0, 0, 0,
                                        *v['normal'], *target_uv(index), 0, 0))
        return emitted[index]

    batch = struct.pack('<12H', 0, 0, 0, 0, 65535, 0, 0, 1, 0, 0, 0, 0)
    for geoset in EARS:
        meshes.append({'family': 'body', 'geoset': geoset, 'row': elf_ears[geoset]['row'], 'batches': [batch],
                       'triangles': [tuple(emit(i) for i in tri) for tri in elf_ears[geoset]['triangles']]})

    model.vertices, model.vertex_count = bytes(vertices), len(vertices) // 48
    model.textures = [{'type': 1, 'flags': 0, 'filename': ''}]
    model.replacable_texture_lookup = [65535] * 16
    model.replacable_texture_lookup[1] = 0
    model.texture_combos, model.texture_coord_combos = [0], [0]
    model.texture_weight_combos, model.texture_transform_combos = [0], [65535]
    model.materials = [{'flags': 0, 'blending_mode': 0}]
    idle = copy.deepcopy(next(s for s in skel.sequences if s['id'] == 0 and s['variation_index'] == 0))
    idle.update(flags=0x20, variation_next=-1, alias_next=0)
    model.sequences, model.sequence_lookups, model.global_loops = [idle], [0], []
    model.anim_file_ids, model.bone_file_ids, model.skin_file_ids, model.texture_file_ids = [], [], [], []
    model.attachments, model.attachment_lookup = [], []
    model.events, model.lights, model.cameras, model.ribbons, model.particles = [], [], [], [], []
    model.colors, model.texture_transforms, model.camera_lookup = [], [], []
    model.texture_weights = [{'weight': Track(kind='fixed16', timestamps=[[0]], values=[[32767]])}]
    for bone in model.bones:
        for key, kind in (('translation', 'vec3'), ('rotation', 'quat16'), ('scale', 'vec3')):
            bone[key] = Track(kind=kind)
    for mesh in meshes:
        row = bytearray(mesh['row'])
        struct.pack_into('<H', row, 16, 1)
        points = np.array([struct.unpack_from('<3f', model.vertices, i * 48) for tri in mesh['triangles'] for i in tri])
        center = (points.min(axis=0) + points.max(axis=0)) / 2
        struct.pack_into('<3f3ff', row, 20, *center, *center, np.linalg.norm(points - center, axis=1).max())
        mesh['row'] = bytes(row)

    # Same section/palette expansion as centaur_clothing.prepare: each section owns a contiguous lookup window.
    output_skin = packed_skin(model, meshes)
    expanded, submeshes, lookups, local_bones = [], [], [], bytearray()
    for original_row in output_skin.submeshes:
        row = bytearray(original_row)
        first, count = struct.unpack_from('<2H', row, 8)
        first |= struct.unpack_from('<H', row, 2)[0] << 16
        used = output_skin.indices[first:first + count]
        unique = list(dict.fromkeys(used))
        remap = {value: len(lookups) + index for index, value in enumerate(unique)}
        palette_count, palette_start = struct.unpack_from('<2H', row, 12)
        palette = {bone: index for index, bone in enumerate(model.bone_combos[palette_start:palette_start + palette_count])}
        struct.pack_into('<2H', row, 4, len(lookups), len(unique))
        for index in unique:
            lookups.append(index)
            at = index * 48
            local_bones.extend(palette[model.vertices[at + 16 + slot]] if model.vertices[at + 12 + slot] else 0
                               for slot in range(4))
        start = len(expanded)
        struct.pack_into('<H', row, 2, start >> 16)
        struct.pack_into('<H', row, 8, start & 65535)
        expanded.extend(remap[index] for index in used)
        submeshes.append(bytes(row))
    output_skin.indices, output_skin.submeshes = expanded, submeshes
    output_skin.vertices, output_skin.bones = lookups, bytes(local_bones)
    model.num_skin_profiles = 1
    output, companion = write_md20(model), write_skin(output_skin)

    restored, restored_skin = parse_m2(output), parse_skin(companion)
    assert max(restored_skin.vertices) < restored.vertex_count
    assert max(restored_skin.indices) < len(restored_skin.vertices)
    assert {struct.unpack_from('<H', r)[0] for r in restored_skin.submeshes} == set(EARS)
    for before, after in zip(skel.bones, restored.bones, strict=True):
        assert all(before[key] == after[key] for key in ('parent_bone', 'bone_name_crc', 'pivot'))
    assert not (raster(human_uv, tuple(sheet))[dy:dy + dh, dx:dx + dw] & coverage).any(), 'patch overlaps Human UVs'
    assert hashlib.sha256(source.read_bytes()).hexdigest() == original
    destination = WORK / 'stage/assets/custom/humanears'
    destination.mkdir(parents=True, exist_ok=True)
    files = {f'{human_id}-ears.m2': output, f'{human_id}-ears00.skin': companion, f'{human_id}-ears.ear': ear}
    for name, data in files.items():
        (destination / name).write_bytes(data)
    return {'human': human_id, 'blood_elf': elf_id, 'vertices': restored.vertex_count,
            'triangles': len(restored_skin.indices) // 3, 'head_bone': head, 'islands': len(boxes),
            'patch': [int(dx), int(dy), int(dw), int(dh)], 'tone_samples': len(samples), 'elf_tone': elf_tone.round(1).tolist(),
            **{name: hashlib.sha256(data).hexdigest() for name, data in files.items()}}


def archive():
    """A standalone patch-HumanEars.MPQ; installing it touches no existing client archive."""
    from cars_mount_pack import DLL_DEFAULT, Storm
    stage = WORK / 'stage/assets'
    entries = {str(path.relative_to(stage)).replace('/', '\\'): path.read_bytes()
               for path in sorted((stage / 'custom/humanears').iterdir())}
    assert len(entries) == 3 * len(MODELS)
    target = WORK / 'patch-HumanEars.MPQ'
    target.unlink(missing_ok=True)
    Storm(DLL_DEFAULT).create_archive(target, entries)
    return {'archive': str(target), 'sha256': hashlib.sha256(target.read_bytes()).hexdigest(), 'entries': sorted(entries)}


if __name__ == '__main__':
    report = {str(sex): build(sex) for sex in MODELS}
    report['archive'] = archive()
    (WORK / 'ears-report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
