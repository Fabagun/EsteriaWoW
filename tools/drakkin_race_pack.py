"""Stage independent female Drakkin races and fitted player armor; never build or install."""

import argparse
import copy
import hashlib
import json
import math
from pathlib import Path, PureWindowsPath
import shutil
import struct
import subprocess

from PIL import Image
from wotlkconv.blp import Blp
from wotlkconv.blp.image import Image as BlpImage
from wotlkconv.m2 import parse_m2, parse_skin, write_md20
from wotlkconv.m2.skin import Skin, write_skin

import retroported_race_pack as p
import drakkin_drakonid_racials as racials
import ogre_furbolg_race_pack as o
import sethrak_race_pack as tables_lib
import sethrak_equipment_repair as equipment
import sethrak_body_regions as regions
import skyborne_visual_pack as visual
import vrykul_female_pack as arrays

ROOT = Path('G:/RetroPorterWork/kobold')
STAGE = ROOT / 'stage'
SOURCE = Path('G:/Kobold/KoboldTestV25')
COLORS = Path('G:/Kobold/KoboldColours_FIX')
MODEL = 'custom\\kobold\\koboldfemale.m2'
ASSET = Path('Data/Patch-9.MPQ')
CLASSES = [1, 2, 3, 4, 5, 6, 7, 8, 9, 11]
MIGRATION = p.ROOT / 'data/sql/updates/pending_db_world/rev_20261011010000000_drakkin.sql'
SPECS = ((66, 'alliance', 1, 120073, 60064, 12), (67, 'horde', 2, 120074, 60065, 4))


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8', newline='\n')


def local(root, key):
    return root.joinpath(*PureWindowsPath(key).parts)


def palettes():
    return list(sorted(COLORS.glob('*.blp'))) + [SOURCE / f'koboldfemaleskin{i:02d}_00.blp' for i in range(4)]


def ranges(race):
    index = race - 66
    start = 1114300 + index * 1000
    return {'CreatureModelData': {'female': 120073 + index},
            'CreatureDisplayInfo': {'male': 0, 'female': 60064 + index},
            'CharSections': [start, start + 999], 'CharHairGeosets': [start, start + 99],
            'BarberShopStyle': [start, start + 99], 'CharStartOutfit': [22120 + index * 10, 22129 + index * 10],
            'NameGen': [84000 + index * 3000, 86999 + index * 3000]}


def manifest(spec):
    race, faction, donor, model, display, count = spec
    sources = palettes()[:12] if race == 66 else palettes()[12:]
    return {'schema_version': 1, 'slug': 'drakkin_' + faction, 'name': 'Drakkin', 'race_ids': [race],
            'enum': 'RACE_DRAKKIN_' + faction.upper(), 'faction': faction, 'source_race_id': donor,
            'legacy_mask_race': donor, 'visual_base_race': 20, 'helmet_prefix': 'Vu',
            'client_file_strings': {str(race): 'Drakkin' + faction.title()},
            'glue_token': ('Drakkin' + faction).upper(), 'start_profile': 'elwynn' if race == 66 else 'durotar',
            'donor_totem_race': donor, 'classes': CLASSES, 'source_patch_root': str(COLORS if race == 66 else SOURCE),
            'runtime_patch_root': str(STAGE / 'assets'),
            'models': {'female': {'model_id': model, 'display_id': display, 'model_path': MODEL}},
            'appearance': {'mode': 'native-stock-five-byte-v1', 'supported_genders': [1],
                           'profiles': {'1': {'capacities': [count, 1, 1, 1, 1], 'options': [
                               {'label': label, 'choices': choices} for label, choices in
                               zip(('Skin Color', 'Face', 'Hair Style', 'Hair Color', 'Facial Hair'),
                                   ([f.stem for f in sources], [0], [0], [0], [0]))]}},
                           'armor': 'fitted-vulpera-garments-and-baked-player-atlas', 'hide_helm': False},
            'random_playerbot_enabled': False, 'custom_racial_spells': []}


def paint_protected(atlas, source, triangles):
    """Copy the source palette into the atlas where the protected surfaces sample it."""
    target = atlas.load()
    origin = source.load()
    for tri in triangles:
        us = [point[0] * atlas.width for point in tri]
        vs = [point[1] * atlas.height for point in tri]
        x0, x1 = max(0, int(min(us)) - 1), min(atlas.width - 1, int(max(us)) + 1)
        y0, y1 = max(0, int(min(vs)) - 1), min(atlas.height - 1, int(max(vs)) + 1)
        (ax, ay), (bx, by), (cx, cy) = (us[0], vs[0]), (us[1], vs[1]), (us[2], vs[2])
        denominator = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
        if abs(denominator) < 1e-9:
            continue
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                px, py = x + .5, y + .5
                wa = ((by - cy) * (px - cx) + (cx - bx) * (py - cy)) / denominator
                wb = ((cy - ay) * (px - cx) + (ax - cx) * (py - cy)) / denominator
                wc = 1 - wa - wb
                if min(wa, wb, wc) < -.05:
                    continue
                su = min(source.width - 1, max(0, int((wa * tri[0][0] + wb * tri[1][0]
                                                       + wc * tri[2][0]) * source.width)))
                sv = min(source.height - 1, max(0, int((wa * tri[0][1] + wb * tri[1][1]
                                                        + wc * tri[2][1]) * source.height)))
                target[x, y] = origin[su, sv]

def export():
    STAGE.mkdir(parents=True, exist_ok=True)
    model = parse_m2((ROOT / 'converted/koboldfemale.m2').read_bytes())
    skin = parse_skin((ROOT / 'converted/koboldfemale00.skin').read_bytes())
    files = p.ClientFiles(str(p.CLIENT_DEFAULT / 'Data'), 'enUS')
    try:
        donor_key = 'custom\\vulpera\\native\\female\\vulperafemale.m2'
        donor_data, provider = files.find(donor_key)
        donor_skin_data = files.find(donor_key[:-3] + '00.skin')[0]
    finally:
        files.close()
    (STAGE / 'donor.m2').write_bytes(donor_data)
    (STAGE / 'donor.skin').write_bytes(donor_skin_data)
    donor, donor_skin = parse_m2(donor_data), parse_skin(donor_skin_data)
    by_crc = {b['bone_name_crc']: i for i, b in enumerate(model.bones) if b['bone_name_crc']}
    bone_map = {}
    for i, b in enumerate(donor.bones):
        if b['bone_name_crc'] in by_crc:
            bone_map[i] = by_crc[b['bone_name_crc']]
    assert len(bone_map) > 100, 'Player donor skeleton is unrelated'
    fitted = []
    for i in range(donor.vertex_count):
        vertex = equipment.vertex_record(donor, i)
        for slot, weight in enumerate(vertex['weights']):
            if weight:
                source_bone = vertex['bones'][slot]
                assert source_bone in bone_map, 'Garment bone has no exact Drakkin match'
                target = bone_map[source_bone]
                vertex['bones'][slot] = target
                for axis in range(3):
                    vertex['position'][axis] += weight / 255 * (
                        model.bones[target]['pivot'][axis] - donor.bones[source_bone]['pivot'][axis])
        fitted.append(vertex)
    protected = regions.children(model, model.key_bone_lookup[50])
    protected |= regions.children(model, model.key_bone_lookup[41])
    body, kept, surfaces = [], [], []
    for i, row in enumerate(skin.submeshes):
        kinds = {model.textures[model.texture_combos[visual.u16(b, 16)]]['type']
                 for b in skin.batches if visual.u16(b, 4) == i}
        for tri in equipment.mesh_triangles(skin, row):
            surfaces.append(tri)
            head_weight = sum(model.vertices[v * 48 + 12 + j] for v in tri for j in range(4)
                              if model.vertices[v * 48 + 16 + j] in protected)
            (body if kinds == {8} and head_weight < 255 else kept).append(tri)
    parts = []
    for i, row in enumerate(donor_skin.submeshes):
        geo = visual.u16(row, 0)
        kinds = {donor.textures[donor.texture_combos[visual.u16(b, 16)]]['type']
                 for b in donor_skin.batches if visual.u16(b, 4) == i}
        if (400 <= geo < 1600 or 1800 <= geo < 1900) and kinds <= {1, 2} and kinds \
                and geo not in (401, 501, 901, 1101, 1301, 1801):
            parts.append({'geoset': geo, 'triangles': equipment.mesh_triangles(donor_skin, row),
                          'texture_type': next(iter(kinds))})
    assert len(palettes()) == 16 and body and kept and parts
    pngs = []
    for i, path in enumerate(palettes()):
        image = Blp.parse(path.read_bytes()).decode_level(0)
        output = STAGE / f'source-{i}.png'
        Image.frombytes('RGBA', (image.width, image.height), bytes(image.data)).save(output)
        pngs.append(str(output))
    # Calibrate the existing atlas mapper to this body's neck/hip rather than Sethrak's fixed heights.
    collar = max(struct.unpack_from('<f', model.vertices, v * 48 + 8)[0] for tri in body for v in tri)
    calibrated = copy.deepcopy(model)
    neck = model.bones[model.key_bone_lookup[49]]['pivot'][2]
    waist = regions.waist_height(model)
    scale = 0.8 / (neck - waist)
    for b in calibrated.bones:
        b['pivot'] = (b['pivot'][0] * scale, b['pivot'][1] * scale, 1 + (b['pivot'][2] - waist) * scale)
    data = bytearray(calibrated.vertices)
    for i in range(calibrated.vertex_count):
        x, y, z = struct.unpack_from('<3f', data, i * 48)
        struct.pack_into('<3f', data, i * 48, x * scale, y * scale, 1 + (z - waist) * scale)
    calibrated.vertices = bytes(data)
    region_uvs = regions.body_uvs(calibrated, body, 1 + (collar - waist) * scale)
    feet = set().union(*(regions.children(model, model.key_bone_lookup[k]) for k in (59, 60)))
    floor = min(v['position'][2] for v in fitted)
    ankle = sum(model.bones[model.key_bone_lookup[k]]['pivot'][2] for k in (59, 60)) / 2
    for i, tri in enumerate(body):
        foot_weight = sum(model.vertices[v * 48 + 12 + j] for v in tri for j in range(4)
                          if model.vertices[v * 48 + 16 + j] in feet)
        if foot_weight >= 300:
            for j, v in enumerate(tri):
                z = struct.unpack_from('<f', model.vertices, v * 48 + 8)[0]
                region_uvs[i * 3 + j][1] = .875 + .125 * min(1, max(0, (ankle - z) / max(ankle - floor, .001)))
    assert all(math.isfinite(v) and 0 <= v <= 1 for uv in region_uvs for v in uv)
    save(STAGE / 'female-body-work.json', {'target': [equipment.vertex_record(model, i)
         for i in range(model.vertex_count)], 'body': body, 'original_only': kept, 'donor': fitted,
         'equipment': parts, 'skin_sources': pngs, 'region_uvs': region_uvs,
         'fit_surface': surfaces, 'fit_boots': True, 'bone_map': bone_map, 'donor_provider': provider})
    print('EXPORTED Drakkin body', len(body), 'triangles;', len(parts), 'garment meshes; 16 palettes', flush=True)


def bake():
    subprocess.run([str(equipment.BLENDER), '-b', '--factory-startup', '--python',
                    str(p.ROOT / 'tools/sethrak_body_blender.py'), '--', str(STAGE), 'female'], check=True)


_FOOTPRINTS = {}


def _footprint(baked):
    """Atlas texel -> source UV pairs for every baked triangle; independent of the palette."""
    import numpy as np
    key = id(baked)
    if key in _FOOTPRINTS:
        return _FOOTPRINTS[key]
    xs, ys, us, vs, sides = [], [], [], [], []
    for atlas_uv, source_uv, side in baked:
        pts = np.array(atlas_uv, dtype=np.float64) * 512
        (ax, ay), (bx, by), (cx, cy) = pts
        denominator = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
        if abs(denominator) < 1e-9:
            continue
        x0, x1 = max(0, int(pts[:, 0].min()) - 1), min(511, int(pts[:, 0].max()) + 1)
        y0, y1 = max(0, int(pts[:, 1].min()) - 1), min(511, int(pts[:, 1].max()) + 1)
        gx, gy = np.meshgrid(np.arange(x0, x1 + 1), np.arange(y0, y1 + 1))
        px, py = gx + .5, gy + .5
        wa = ((by - cy) * (px - cx) + (cx - bx) * (py - cy)) / denominator
        wb = ((cy - ay) * (px - cx) + (ax - cx) * (py - cy)) / denominator
        wc = 1 - wa - wb
        inside = (wa >= -.03) & (wb >= -.03) & (wc >= -.03)
        wa, wb, wc = (np.clip(w[inside], 0, 1) for w in (wa, wb, wc))
        src = np.array(source_uv, dtype=np.float64)
        xs.append(gx[inside])
        ys.append(gy[inside])
        us.append(wa * src[0, 0] + wb * src[1, 0] + wc * src[2, 0])
        vs.append(wa * src[0, 1] + wb * src[1, 1] + wc * src[2, 1])
        sides.append(np.full(len(wa), side))
    result = tuple(np.concatenate(v) for v in (xs, ys, us, vs, sides))
    _FOOTPRINTS[key] = result
    return result


def bake_atlas(baked, palette):
    """Bake the authored skin into the 512x512 player atlas through the anatomical region UVs.

    Both sides of the body share atlas texels; the +Y side wins and the other side only fills gaps.
    """
    import numpy as np
    xs, ys, us, vs, sides = _footprint(baked)
    # Both sides of the body share atlas texels. Averaging them mushes the pattern, so each texel takes the
    # model's +Y side (mirrored onto the other, as stock player textures are); the -Y side only fills gaps.
    taken = np.zeros(512 * 512, bool)
    taken[(ys * 512 + xs)[sides >= -.005]] = True
    keep = (sides >= -.005) | ~taken[ys * 512 + xs]
    xs, ys, us, vs = xs[keep], ys[keep], us[keep], vs[keep]
    source = np.frombuffer(bytes(palette.data), np.uint8).reshape(palette.height, palette.width, 4)[..., :3]
    source = source.astype(np.float64)
    fx = np.clip(us * palette.width - .5, 0, palette.width - 1.001)
    fy = np.clip(vs * palette.height - .5, 0, palette.height - 1.001)
    ix, iy = fx.astype(int), fy.astype(int)
    tx, ty = (fx - ix)[:, None], (fy - iy)[:, None]
    colors = (source[iy, ix] * (1 - tx) * (1 - ty) + source[iy, ix + 1] * tx * (1 - ty)
              + source[iy + 1, ix] * (1 - tx) * ty + source[iy + 1, ix + 1] * tx * ty)
    flat = ys * 512 + xs
    count = np.bincount(flat, minlength=512 * 512).astype(np.float64)
    total = np.stack([np.bincount(flat, weights=colors[:, c], minlength=512 * 512) for c in range(3)], axis=1)
    painted = count > 0
    atlas = np.zeros((512 * 512, 3))
    atlas[painted] = total[painted] / count[painted][:, None]
    mean = atlas[painted].mean(axis=0)
    atlas = atlas.reshape(512, 512, 3)
    known = painted.reshape(512, 512)
    for _ in range(6):  # pad the seams so mip levels and filtering never pull in unpainted texels
        grown, hits = np.zeros_like(atlas), np.zeros(known.shape)
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            grown += np.roll(np.where(known[..., None], atlas, 0), (dy, dx), (0, 1))
            hits += np.roll(known, (dy, dx), (0, 1))
        fill = ~known & (hits > 0)
        atlas[fill] = grown[fill] / hits[fill][:, None]
        known = known | fill
    atlas[~known] = mean
    rgba = np.concatenate([atlas, np.full((512, 512, 1), 255.)], axis=2)
    return np.clip(rgba + .5, 0, 255).astype(np.uint8).tobytes()


def armor():
    model = parse_m2((ROOT / 'converted/koboldfemale.m2').read_bytes())
    skin = parse_skin((ROOT / 'converted/koboldfemale00.skin').read_bytes())
    donor = parse_m2((STAGE / 'donor.m2').read_bytes())
    donor_skin = parse_skin((STAGE / 'donor.skin').read_bytes())
    work = p.load_json(STAGE / 'female-body-work.json')
    for index, point in p.load_json(STAGE / 'female-equipment-fit.json').items():
        work['donor'][int(index)]['position'] = point
    vertices, meshes = bytearray(model.vertices), []
    texture_combos = {}
    for kind in (1, 2):
        texture_combos[kind] = len(model.texture_combos)
        model.texture_combos.append(len(model.textures))
        model.textures.append({'type': kind, 'flags': 0, 'filename': ''})
    material = len(model.materials)
    model.materials.append({'flags': 0, 'blending_mode': 0})
    # 3.3.5a player models carry a texture-coordinate lookup; every batch references entry 0.
    model.texture_coord_combos = [0, 0]

    def batch(kind):
        return struct.pack('<12H', 0, 0, 0, 0, 65535, material, 0, 1, texture_combos[kind], 0, 0, 0)

    uv = p.load_json(STAGE / 'female-body-uv.json')
    uv_by_tri = {tuple(tri): uv[i * 3:i * 3 + 3] for i, tri in enumerate(work['body'])}
    # Arm cylinders wrap at the back of the limb: a triangle straddling the seam spans the whole region width
    # and smears one stripe of texture across the arm. Unwrap it across the seam and clamp to the region edge.
    for key, coords in uv_by_tri.items():
        if all(c[0] < .5 for c in coords) and max(c[0] for c in coords) - min(c[0] for c in coords) > .2:
            uv_by_tri[key] = [[min(c[0] + .5, .4995) if c[0] < .25 else c[0], c[1]] for c in coords]
    # Both arms share one authored island (u 0-.25, v 0-.5) whose v already runs along the limb 1:1 with the
    # atlas arm column. Use it directly rather than the bone-cylinder angle, which stretched the arm texture.
    # The hands sit just below it (v .47-.55) and map onto the atlas hand rectangle the same way.
    for key, coords in list(uv_by_tri.items()):
        source = [struct.unpack_from('<2f', model.vertices, v * 48 + 32) for v in key]
        if not all(u <= .26 for u, v in source):
            continue
        if all(c[0] < .5 and c[1] < .5 for c in coords) and all(v <= .51 for u, v in source):
            uv_by_tri[key] = [[min(max(u * 2, 0), .4995), min(max(v, 0), .4995)] for u, v in source]
        elif all(c[0] < .5 and .5 <= c[1] < .875 for c in coords) and all(.46 <= v <= .64 for u, v in source):
            # The region mapper spreads the fingers over the rows beneath the hand rectangle, which the client
            # overwrites with (here empty) face components. Squeeze the whole hand patch into the hand rectangle.
            uv_by_tri[key] = [[min(max(u * 2, 0), .4995),
                               min(max(.5 + (v - .47) / .17 * .125, .5), .6245)] for u, v in source]
    # Anything else in the hand rectangle (the claws, authored elsewhere in the texture) keeps its original UVs.
    for key, coords in list(uv_by_tri.items()):
        if all(c[0] < .5 and .5 <= c[1] < .875 for c in coords):
            source = [struct.unpack_from('<2f', model.vertices, v * 48 + 32) for v in key]
            if not (all(u <= .26 for u, v in source) and all(.46 <= v <= .64 for u, v in source)):
                del uv_by_tri[key]
    # Feet keep their authored UVs and textures: gloves/boots are separate garment geosets with their own art.
    for key in [key for key, c in uv_by_tri.items() if c[0][1] >= .875]:
        del uv_by_tri[key]
    mapped, baked = {}, []

    # Anatomical body triangles sample the player atlas (where armor art is composited) with region UVs; the
    # skin is baked into that atlas. Head, ears and tail keep their source UVs and type-8 batches: type 8 is
    # the client's CharSections kind-0 "extra skin" slot, fed with the unmodified source palette.
    protected_by_row = {}
    for i, row in enumerate(skin.submeshes):
        native, player = [], []
        for tri in equipment.mesh_triangles(skin, row):
            if tri not in uv_by_tri:
                native.append(tri)
                continue
            converted = []
            for index, coords in zip(tri, uv_by_tri[tri], strict=True):
                key = (index, *coords)
                if key not in mapped:
                    data = bytearray(model.vertices[index * 48:(index + 1) * 48])
                    struct.pack_into('<2f', data, 32, *coords)
                    mapped[key] = len(vertices) // 48
                    vertices.extend(data)
                converted.append(mapped[key])
            player.append(tuple(converted))
            baked.append((tuple(uv_by_tri[tri]), tuple(struct.unpack_from('<2f', model.vertices, v * 48 + 32)
                                                      for v in tri),
                          sum(struct.unpack_from('<f', model.vertices, v * 48 + 4)[0] for v in tri) / 3))
        if native:
            meshes.append({'row': row, 'batches': [b for b in skin.batches if visual.u16(b, 4) == i],
                           'geoset': 0, 'triangles': native, 'family': 'body'})
        if player:
            meshes.append({'row': row, 'batches': [batch(1)], 'geoset': 0, 'triangles': player, 'family': 'body'})
    donor_map = {}
    for part in work['equipment']:
        for index in {v for tri in part['triangles'] for v in tri}:
            if index not in donor_map:
                vertex = work['donor'][index]
                data = bytearray(donor.vertices[index * 48:(index + 1) * 48])
                struct.pack_into('<3f', data, 0, *vertex['position'])
                data[16:20] = bytes(vertex['bones'])
                donor_map[index] = len(vertices) // 48
                vertices.extend(data)
        row = next(r for r in donor_skin.submeshes if visual.u16(r, 0) == part['geoset'])
        meshes.append({'row': row, 'batches': [batch(part['texture_type'])], 'geoset': part['geoset'],
                       'triangles': [tuple(donor_map[v] for v in tri) for tri in part['triangles']], 'family': 'armor'})
    model.vertices, model.vertex_count = bytes(vertices), len(vertices) // 48
    model.replacable_texture_lookup = [65535] * 16
    for i, texture in enumerate(model.textures):
        if texture['type']:
            model.replacable_texture_lookup[texture['type']] = i
    raw = Skin()
    for i, mesh in enumerate(meshes):
        row = bytearray(mesh['row'])
        first_index, first_vertex = len(raw.indices), len(raw.vertices)
        used = list(dict.fromkeys(v for tri in mesh['triangles'] for v in tri))
        lookup = {v: first_vertex + j for j, v in enumerate(used)}
        raw.vertices.extend(used)
        raw.indices.extend(lookup[v] for tri in mesh['triangles'] for v in tri)
        for offset, value in ((0, mesh['geoset']), (2, first_index >> 16), (4, first_vertex),
                              (6, len(used)), (8, first_index & 65535), (10, len(mesh['triangles']) * 3)):
            visual.patch16(row, offset, value)
        raw.submeshes.append(bytes(row))
        for original in mesh['batches']:
            cloned = bytearray(original)
            if visual.u16(cloned, 14) > 1:
                # The source eye batch multiplies two layers that are now the same texture, which blackens it.
                visual.patch16(cloned, 14, 1)
            visual.patch16(cloned, 4, i)
            visual.patch16(cloned, 6, i)
            raw.batches.append(bytes(cloned))
    output_skin = visual.compact_bone_palettes(model, raw)
    payload, separated = arrays.separate_bone_track_arrays(write_md20(model))
    output = local(STAGE / 'assets', MODEL)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(payload)
    output.with_name('koboldfemale00.skin').write_bytes(write_skin(output_skin))
    local(STAGE / 'assets', 'custom\\kobold\\koboldeyes00_00.blp').write_bytes(
        (SOURCE / 'koboldeyes00_00.blp').read_bytes())
    for i, path in enumerate(palettes()):
        palette = Blp.parse(path.read_bytes()).decode_level(0)
        atlas = bake_atlas(baked, palette)
        local(STAGE / 'assets', f'custom\\kobold\\body-{i}.blp').write_bytes(
            p._encode_wotlk_paletted(BlpImage(512, 512, atlas)))
        # The unmodified source palette (DXT, authored UVs) is the type-8 fur/skin layer.
        local(STAGE / 'assets', f'custom\\kobold\\extra-{i}.blp').write_bytes(path.read_bytes())
    save(STAGE / 'armor.json', {'vertices': model.vertex_count, 'submeshes': len(output_skin.submeshes),
         'garments': sorted({part['geoset'] for part in work['equipment']}), 'palettes': 16,
         'body_triangles': sum(len(m['triangles']) for m in meshes), 'protected_triangles': 0,
         'track_arrays_separated': separated, 'live_armor_checked': False})
    print('PREPARED Drakkin armor and 16 baked palettes', flush=True)


def allocation():
    result = p.load_json(p.ALLOCATION_PATH)
    registry = p.load_json(p.ROOT / 'modules/mod-custom-server/data/races/race_registry.json')
    for spec in SPECS:
        race, faction = spec[:2]
        slug = 'drakkin_' + faction
        bounds = ranges(race)
        assert all(race not in ids for key, ids in result['race_ids'].items() if key != slug)
        assert not any(r['id'] == race for r in registry['npc_only'])
        for key, other in result['race_allocations'].items():
            if key == slug:
                assert other == bounds
                continue
            for table, values in bounds.items():
                previous = other.get(table)
                if isinstance(values, list) and isinstance(previous, list):
                    assert max(values[0], previous[0]) > min(values[1], previous[1]), (key, table)
                elif isinstance(values, dict) and isinstance(previous, dict):
                    assert not ((set(values.values()) - {0}) & (set(previous.values()) - {0})), (key, table)
        result['race_ids'][slug] = [race]
        result['race_allocations'][slug] = bounds
        for table, values in bounds.items():
            result['dbc_ranges'][table][1] = max(result['dbc_ranges'][table][1],
                values[1] if isinstance(values, list) else max(values.values()))
    return result


def tables(baseline):
    result, reserved = dict(baseline), allocation()
    for spec in SPECS:
        race, faction, donor_id, model_id, display_id, count = spec
        m, r = manifest(spec), ranges(race)
        p._ensure_id_free(result['ChrRaces'], 'ChrRaces', {race})
        result['ChrRaces'] = p._merge_chr_races(result['ChrRaces'], m, reserved)
        table = p.RawWdbc(result['ChrRaces'])
        pool, rows = bytearray(table.strings), []
        for row in table.records:
            if p._value(row, 0) == race:
                for field, value in ((1, 14), (2, donor_id), (7, 7 if race == 66 else 1),
                                      (12, 0), (13, 0 if race == 66 else 1), (68, 0)):
                    row = p._replace(row, field * 4, 4, value)
                row = p._set_string(row, 6, pool, 'Vu')
            rows.append(row)
        result['ChrRaces'] = table.build(rows, bytes(pool))
        donor_race = next(row for row in table.records if p._value(row, 0) == 20)
        displays = p.RawWdbc(result['CreatureDisplayInfo'])
        display = next(row for row in displays.records if p._value(row, 0) == p._value(donor_race, 20))
        models = p.RawWdbc(result['CreatureModelData'])
        model = next(row for row in models.records if p._value(row, 0) == p._value(display, 4))
        for name, row, identifier in (('CreatureModelData', model, model_id),
                                       ('CreatureDisplayInfo', display, display_id)):
            t = p.RawWdbc(result[name])
            pool = bytearray(t.strings)
            row = p._clone_strings(name, t, row, pool)
            row = p._replace(row, 0, 4, identifier)
            if name == 'CreatureModelData':
                row = p._set_string(row, 2, pool, MODEL)
                row = p._replace(row, 4, 4, p._value(row, 4) | 0x804)
            else:
                row = p._replace(row, 4, 4, model_id)
                for offset in (8, 12, 24, 28, 32, 36):
                    row = p._replace(row, offset, 4, 0)
                row = row[:16] + struct.pack('<f', 1.0) + row[20:]
            result[name] = tables_lib.append_rows(result[name], name, [row], pool)
        result['CharBaseInfo'] = p._build_char_base_info(result['CharBaseInfo'], m)
        outfit = p.RawWdbc(result['CharStartOutfit'])
        donors = {}
        for row in sorted(outfit.records, key=lambda v: p._value(v, 0)):
            if row[4] == donor_id and row[5] in CLASSES and row[6] == 1 and row[7] == 0:
                donors[bytes(row[5:8])] = row
        assert len(donors) == 10, 'Missing faction/class female outfit'
        additions = [p._replace(p._replace(row, 0, 4, r['CharStartOutfit'][0] + i), 4, 1, race)
                     for i, row in enumerate(donors.values())]
        result['CharStartOutfit'] = tables_lib.append_rows(result['CharStartOutfit'], 'CharStartOutfit', additions)
        source = p.RawWdbc(result['NameGen'])
        pool = bytearray(source.strings)
        donors = [row for row in source.records if p._value(row, 8) == donor_id and p._value(row, 12) == 1]
        assert donors and len(donors) <= 3000
        additions = [p._replace(p._replace(p._clone_strings('NameGen', source, row, pool), 0, 4,
                     r['NameGen'][0] + i), 8, 4, race) for i, row in enumerate(donors)]
        result['NameGen'] = tables_lib.append_rows(result['NameGen'], 'NameGen', additions, pool)
        source = p.RawWdbc(result['CharSections'])
        pool, sections = bytearray(source.strings), []
        for color in range(count):
            index = color if race == 66 else 12 + color
            for kind in (0, 1, 4):
                row = struct.pack('<10I', r['CharSections'][0] + len(sections), race, 1, kind,
                                  0, 0, 0, 1 if kind == 1 else 17, 0, color)
                if kind == 0:
                    row = p._set_string(row, 4, pool, f'custom\\kobold\\body-{index}.blp')
                    row = p._set_string(row, 5, pool, f'custom\\kobold\\extra-{index}.blp')
                sections.append(row)
        for kind in (2, 3):
            sections.append(struct.pack('<10I', r['CharSections'][0] + len(sections), race, 1, kind,
                                        0, 0, 0, 17, 0, 0))
        result['CharSections'] = tables_lib.append_rows(result['CharSections'], 'CharSections', sections, pool)
        result['CharHairGeosets'] = tables_lib.append_rows(result['CharHairGeosets'], 'CharHairGeosets',
            [struct.pack('<6I', r['CharHairGeosets'][0], race, 1, 0, 0, 1)])
        result['CharacterFacialHairStyles'] = tables_lib.append_rows(result['CharacterFacialHairStyles'],
            'CharacterFacialHairStyles', [struct.pack('<8I', race, 1, 0, 0, 0, 0, 0, 0)])
        source, styles = p.RawWdbc(result['BarberShopStyle']), []
        for kind, capacity in ((0, 1), (2, 1), (3, count)):
            row = next(v for v in source.records if p._value(v, 4) == kind)
            for value in range(capacity):
                clone = row
                for offset, n in ((0, r['BarberShopStyle'][0] + len(styles)), (148, race), (152, 1), (156, value)):
                    clone = p._replace(clone, offset, 4, n)
                styles.append(clone)
        result['BarberShopStyle'] = tables_lib.append_rows(result['BarberShopStyle'], 'BarberShopStyle', styles)
    result['CharSections'] = o.order_charsections_entry(p.DBC_ROOT + 'CharSections.dbc', result['CharSections'])
    return result


def glue(original):
    result = {name: data.decode('utf-8-sig') for name, data in original.items()}

    def insert(name, anchor, text):
        result[name] = o._insert_once(result[name], anchor, text, 'Drakkin ' + name)

    for race, faction, donor, _, _, _ in SPECS:
        token, key = 'Drakkin' + faction.title(), ('Drakkin' + faction).upper()
        insert('CharacterInfo.lua', 'local EXACT_RACE_DATA = {\n',
            f'    [{race}] = {{glueString="{key}", name="Drakkin", faction="{faction.title()}", '
            f'fileString="{token}"}},\n')
        result['CharacterInfo.lua'] += (f'\nRaceInfoByFileString.{key} = {{Name="Drakkin", '
            f'Description="Drakkin adventurers of the {faction.title()}."}};\n')
        insert('CharacterCreate.lua', 'RACE_ICON_TEXTURES = {\n',
            f'    ["{key}_FEMALE"] = "Interface\\\\Glues\\\\CharacterCreate\\\\UI-CharacterCreate-{token}Female",\n')
        insert('CharacterCreate.lua', 'local RACE_BACKGROUND_KEYS = {\n',
            f'        ["{key}"] = "HUMAN",\n')
        insert('GlueParent.lua', '        ["THINHUMAN"] = true,\n', f'        ["{key}"] = true,\n')
        result['GlueParent.lua'] += (f'\nCharModelFogInfo.{key}=CharModelFogInfo.HUMAN;\n'
                                   f'CharModelGlowInfo.{key}=CharModelGlowInfo.HUMAN;\n'
                                   f'GlueAmbienceTracks.{key}=GlueAmbienceTracks.HUMAN;\n')
        result['GlueStrings.lua'] += f'\n{key}="Drakkin"; {key}_MALE={key}; {key}_FEMALE={key};\n'
        insert('ECS_Schema.lua', 'S.RaceOverride = {\n',
               f'    [{race}] = {{name="Drakkin", faction={donor}, artKey="{token}"}},\n')
        insert('ECS_Schema.lua', 'S.RaceByModelKey = {\n',
               f'    {{"{key}", {{name="Drakkin", faction={donor}, artKey="{token}"}}}},\n')
        insert('ECS_Schema.lua', 'S.PortraitArtKeys = {\n', f'    {token}=true,\n')
    result['CharacterCreate.lua'] += '''
-- This supplied Drakkin pack has one authored female body.
local drakkinSetRace = SetCharacterRace;
local drakkinSetGender = SetCharacterGender;
function SetCharacterGender(sex)
    if CharacterCreate.selectedRaceID == 66 or CharacterCreate.selectedRaceID == 67 then
        sex = SEX_FEMALE;
    end
    drakkinSetGender(sex);
end
function SetCharacterRace(id)
    local button = _G["CharacterCreateRaceButton"..id];
    local isDrakkin = button and (button.raceID == 66 or button.raceID == 67);
    if isDrakkin then SetSelectedSex(SEX_FEMALE); end
    drakkinSetRace(id);
    if isDrakkin then
        CharacterCreateGenderButtonMale:Hide();
        CharacterCreateGenderButtonFemale:Hide();
        if GetSelectedSex() ~= SEX_FEMALE then SetCharacterGender(SEX_FEMALE); end
    end
end
'''
    anchor = '        for i=6,29 do _G["CharacterCustomizationButtonFrame"..i]:Hide(); end'
    insert('CharacterCreate.lua', anchor, '''
        if CharacterCreate.selectedRaceID == 66 or CharacterCreate.selectedRaceID == 67 then
            for i=2,5 do _G["CharacterCustomizationButtonFrame"..i]:Hide(); end
        end''')
    anchor = 'raceModel == "THINHUMAN"'
    assert result['CharacterSelect.lua'].count(anchor) == 1
    result['CharacterSelect.lua'] = result['CharacterSelect.lua'].replace(anchor,
        anchor + ' or raceModel == "DRAKKINALLIANCE" or raceModel == "DRAKKINHORDE"', 1)
    from lupa.lua51 import LuaRuntime
    compile_chunk = LuaRuntime().eval('function(s) local f,e=loadstring(s); assert(f,e); end')
    for text in result.values():
        compile_chunk(text)
    return {name: text.encode() for name, text in result.items()}


def migration_sql():
    sql = ''
    for race, faction, donor, _, display, _ in SPECS:
        sql += o.build_sql({'name': 'Drakkin', 'race_id': race, 'faction': faction,
                           'donor_start_race': donor, 'donor_totem_race': donor})
        sql = sql.rstrip() + '\n' + racials.racial_grant_sql(race) + '\n'
        sql += o.CHRRACES_TEMPLATE.format(race=race, faction_template=donor, male_display=0,
            female_display=display, prefix='Vu', base_language=7 if race == 66 else 1,
            file_string='Drakkin' + faction.title(), alliance=0 if race == 66 else 1, name='Drakkin')
    return sql.replace('ogre_furbolg_race_pack.py', 'drakkin_race_pack.py').rstrip() + '\n'


def stage():
    assert not (p.CLIENT_DEFAULT / ASSET).exists(), 'MPQ slot is occupied'
    files = p.ClientFiles(str(p.CLIENT_DEFAULT / 'Data'), 'enUS')
    try:
        baseline = {name: files.find(p.DBC_ROOT + name + '.dbc')[0] for name in tables_lib.TABLES}
        original = {name: files.find(p.GLUE_ROOT + name)[0] for name in tables_lib.GLUE}
        spell_baseline = files.find(p.DBC_ROOT + 'Spell.dbc')[0]
    finally:
        files.close()
    output, patched = tables(baseline), glue(original)
    # Spell.dbc is shared with the other racial packs, so it is rebuilt from whatever the client
    # ships now rather than pinned; racial rows already present are skipped.
    output['Spell'] = racials.merge_spell_table(spell_baseline)
    (STAGE / 'baseline').mkdir(parents=True, exist_ok=True)
    (STAGE / 'baseline/Spell.dbc').write_bytes(spell_baseline)
    for directory, values in (('baseline', baseline), ('client-dbc', output), ('glue', patched)):
        for name, data in values.items():
            path = STAGE / directory / (name if directory == 'glue' else name + '.dbc')
            path.parent.mkdir(parents=True, exist_ok=True)
            if directory == 'baseline' and path.exists():
                assert path.read_bytes() == data, 'Baseline changed'
            path.write_bytes(data)
    for name in tables_lib.SERVER_TABLES:
        base = (p.SERVER_DBC_ROOT / (name + '.dbc')).read_bytes()
        path = STAGE / 'baseline-server' / (name + '.dbc')
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            assert path.read_bytes() == base, 'Mounted baseline changed'
        path.write_bytes(base)
        source, target = p.RawWdbc(output[name]), p.RawWdbc(base)
        rows = [row for race in (66, 67) for row in p._table_rows_for_race(output[name], name, race)] \
            if name not in ('CreatureModelData', 'CreatureDisplayInfo') else [row for row in source.records
            if p._value(row, 0) in ({120073, 120074} if name == 'CreatureModelData' else {60064, 60065})]
        p._ensure_id_free(base, name, {p._value(row, 0) for row in rows})
        pool = bytearray(target.strings)
        data = target.build(list(target.records) + [p._clone_strings(name, source, row, pool) for row in rows],
                            bytes(pool))
        path = STAGE / 'server/dbc' / (name + '.dbc')
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    sql = migration_sql()
    if MIGRATION.exists():
        assert MIGRATION.read_text() == sql, 'Migration revision is occupied'
    MIGRATION.write_text(sql, encoding='utf-8', newline='\n')
    (STAGE / 'drakkin.sql').write_text(sql, encoding='utf-8', newline='\n')
    geometry = (p.CLIENT_DEFAULT / 'EsteriaAppearanceGeometry.bin').read_bytes()
    magic, version, count = struct.unpack_from('<3I', geometry)
    assert (magic, version) == (0x4d474145, 1)
    skin = local(STAGE / 'assets', MODEL[:-3] + '00.skin').read_bytes()
    (STAGE / 'EsteriaAppearanceGeometry.bin').write_bytes(struct.pack('<3I', magic, version, count + 1)
        + geometry[12:] + MODEL.encode().ljust(128, b'\0') + struct.pack('<I', len(skin)) + skin)
    catalog = (p.CLIENT_DEFAULT / 'EsteriaAppearance.bin').read_bytes()
    magic, version, count = struct.unpack_from('<3I', catalog)
    assert (magic, version) == (0x50504145, 2) and len(catalog) == 12 + count * 2316
    records = []
    for spec in SPECS:
        record = bytearray(struct.pack('<3I', spec[0], 1, 5))
        for offset, capacity in zip((0x28, 0x2c, 0x34, 0x24, 0x30), (spec[5], 1, 1, 1, 1)):
            record.extend(struct.pack('<4I', offset, capacity, 1, 0) + bytes(128))
        record.extend(bytes(11 * 144))
        records.append(record)
    (STAGE / 'EsteriaAppearance.bin').write_bytes(struct.pack('<3I', magic, version, count + 2)
        + catalog[12:] + b''.join(records))
    replacements = {p.DBC_ROOT + name + '.dbc': data for name, data in output.items()}
    replacements.update({p.GLUE_ROOT + name: data for name, data in patched.items()})
    assets = {'\\'.join(path.relative_to(STAGE / 'assets').parts): path.read_bytes()
              for path in (STAGE / 'assets').rglob('*') if path.is_file()}
    storm = p.Storm(p.DLL_DEFAULT)
    dest = STAGE / 'client' / ASSET
    dest.parent.mkdir(parents=True, exist_ok=True)
    assert not dest.exists(), 'Existing staged archive must be reviewed before regeneration'
    storm.create_archive(dest, assets)
    report = {'race_ids': [66, 67], 'source': p.load_json(ROOT / 'conversion.json'),
              'armor': p.load_json(STAGE / 'armor.json'), 'exe_sha256': p.sha256(p.CLIENT_DEFAULT / 'Wow.exe'),
              'assets': {key: hashlib.sha256(value).hexdigest() for key, value in assets.items()},
              'archive_baselines': {}, 'archives': {str(ASSET): p.sha256(dest)},
              'status': 'staged_build_and_install_required', 'live_installed': False}
    for relative in (p.GLOBAL_ARCHIVE_REL, p.LOCALE_ARCHIVE_REL):
        live = p.CLIENT_DEFAULT / relative
        snapshot, dest = STAGE / 'baseline-archives' / relative, STAGE / 'client' / relative
        snapshot.parent.mkdir(parents=True, exist_ok=True)
        dest.parent.mkdir(parents=True, exist_ok=True)
        before = p.sha256(live)
        if not snapshot.exists():
            shutil.copy2(live, snapshot)
        assert p.sha256(snapshot) == before, 'Archive baseline changed'
        print('STAGING', relative, flush=True)
        o.rebuild_archive_replacing(storm, snapshot, dest, replacements, compress=True)
        assert p.sha256(live) == before, 'Live archive changed during staging'
        report['archive_baselines'][str(relative)] = before
        report['archives'][str(relative)] = p.sha256(dest)
    save(STAGE / 'report.json', report)
    print('STAGED Drakkin races 66/67', STAGE, flush=True)


def config():
    path = p.ROOT / 'modules/mod-custom-server/data/races/race_registry.json'
    registry = p.load_json(path)
    for spec in SPECS:
        race, faction, donor = spec[:3]
        m = manifest(spec)
        entry = {'id': race, 'species_key': m['slug'], 'display_name': 'Drakkin', 'faction': faction,
                 'species_selection': False, 'start_profile': m['start_profile'], 'asset_owner': 'supplied_drakkin',
                 'legacy_mask_race': donor, 'visual_base_race': 20, 'supported_genders': [1]}
        previous = next((row for row in registry['playable'] if row['id'] == race), None)
        assert previous is None or previous == entry, 'Race registry owner changed'
        if previous is None:
            registry['playable'].append(entry)
        save(p.manifest_path(m['slug']), m)
    registry['sources']['supplied_drakkin'] = str(STAGE / 'assets')
    save(p.ALLOCATION_PATH, allocation())
    save(path, registry)
    print('RESERVED independent Drakkin races 66/67', flush=True)


def preview():
    import creature_animation_repair as motion
    model = parse_m2(local(STAGE / 'assets', MODEL).read_bytes())
    skin = parse_skin(local(STAGE / 'assets', MODEL[:-3] + '00.skin').read_bytes())
    points = motion.posed_vertices(model, motion.pose_matrices(model, 0, 0))
    vertices = [equipment.vertex_record(model, i) for i in range(model.vertex_count)]
    for vertex, position in zip(vertices, points, strict=True):
        vertex['position'] = position.tolist()
    root = STAGE / 'preview'
    root.mkdir(parents=True, exist_ok=True)
    renderer = root / 'render.py'
    text = (p.ROOT / 'tools/gnoll_preview_blender.py').read_text()
    text = text.replace('Vector((.6, 0, 1.62))', 'Vector(work["portrait_target"])')
    text = text.replace("str(root / 'native-outfit.png')", "str(root / 'body.png')")
    renderer.write_text(text, encoding='utf-8', newline='\n')
    files = p.ClientFiles(str(p.CLIENT_DEFAULT / 'Data'), 'enUS')
    try:
        item_table = p.RawWdbc(files.find(p.DBC_ROOT + 'ItemDisplayInfo.dbc')[0])
        displays = {p._value(row, 0): row for row in item_table.records}
        parts = ('ArmUpperTexture', 'ArmLowerTexture', 'HandTexture', 'TorsoUpperTexture',
                 'TorsoLowerTexture', 'LegUpperTexture', 'LegLowerTexture', 'FootTexture')
        rectangles = ((0, 0, 256, 128), (0, 128, 256, 256), (0, 256, 256, 320), (256, 0, 512, 128),
                      (256, 128, 512, 192), (256, 192, 512, 320), (256, 320, 512, 448), (256, 448, 512, 512))
        for mode, color, ids, groups in (('alliance', 0, (), {0}), ('horde', 12, (), {0}),
            ('plate', 12, (25749, 24506, 24513), {0, 403, 503, 903, 1104}),
            ('robe', 12, (15820,), {0, 1302})):
            folder = root / mode
            folder.mkdir(parents=True, exist_ok=True)
            atlas = Image.open(STAGE / f'female-player-skin-{color}.png').convert('RGBA')
            for identifier in ids:
                row = displays[identifier]
                for field, directory, rectangle in zip(range(15, 23), parts, rectangles, strict=True):
                    stem = p._string(item_table.strings, p._value(row, field * 4)).decode()
                    if not stem:
                        continue
                    for suffix in ('_U', '_F', '', '_M'):
                        try:
                            blob = files.find(f'Item\\TextureComponents\\{directory}\\{stem}{suffix}.blp')[0]
                            break
                        except FileNotFoundError:
                            continue
                    else:
                        raise FileNotFoundError(stem)
                    image = Blp.parse(blob).decode_level(0)
                    art = Image.frombytes('RGBA', (image.width, image.height), bytes(image.data))
                    atlas.alpha_composite(art.resize((rectangle[2] - rectangle[0], rectangle[3] - rectangle[1]),
                        Image.Resampling.LANCZOS), (rectangle[0], rectangle[1]))
            atlas.save(folder / 'atlas.png')
            meshes, textures = [], {}
            for i, row in enumerate(skin.submeshes):
                if visual.u16(row, 0) not in groups:
                    continue
                b = next(v for v in skin.batches if visual.u16(v, 4) == i)
                index = model.texture_combos[visual.u16(b, 16)]
                kind = model.textures[index]['type']
                if index not in textures:
                    if kind == 1:
                        path = folder / 'atlas.png'
                    else:
                        path = folder / f'texture-{index}.png'
                        source = (palettes()[color] if kind == 8 else SOURCE / 'koboldeyes00_00.blp')
                        image = Blp.parse(source.read_bytes()).decode_level(0)
                        Image.frombytes('RGBA', (image.width, image.height), bytes(image.data)).save(path)
                    textures[index] = str(path)
                meshes.append({'geoset': visual.u16(row, 0), 'triangles': equipment.mesh_triangles(skin, row),
                               'texture': textures[index]})
            save(folder / 'model.json', {'vertices': vertices, 'meshes': meshes,
                 'camera': [4, -5, 2.0], 'target': [0, 0, .75], 'scale': 2.1,
                 'portrait_target': [.12, 0, 1.25]})
            subprocess.run([str(equipment.BLENDER), '-b', '--factory-startup', '--python', str(renderer),
                            '--', str(folder)], stdout=subprocess.DEVNULL, check=True)
    finally:
        files.close()
    print('RENDERED Alliance, Horde, plate and robe previews', flush=True)


def finish_assets():
    import race_portrait_pack as portraits
    files = p.ClientFiles(str(p.CLIENT_DEFAULT / 'Data'), 'enUS')
    try:
        template = files.find(portraits.ICON_TEMPLATE_ENTRY)[0]
        ring = portraits.ring_layer(portraits.decode_client_blp(files.find(portraits.RING_ENTRY)[0]))
    finally:
        files.close()
    for faction in ('alliance', 'horde'):
        art = Image.open(STAGE / 'preview' / faction / 'portrait.png').convert('RGBA')
        art = art.resize((64, 64), Image.Resampling.LANCZOS)
        art.putalpha(portraits.circular_mask())
        plain = portraits.encode_portrait(art, template)
        token = 'Drakkin' + faction.title()
        entries = {
            portraits.CREATOR_ICON_ROOT + f'UI-CharacterCreate-{token}Female.blp':
                portraits.encode_portrait(portraits.compose_race_icon(art, ring), template),
            f'Interface\\Glues\\CharacterSelect\\ECS-Portrait-{token}Female.blp': plain,
            f'Interface\\CharacterFrame\\TemporaryPortrait-Female-{token}': plain,
            f'Interface\\CharacterFrame\\TemporaryPortrait-Female-{token}.blp': plain}
        for key, data in entries.items():
            path = local(STAGE / 'assets', key)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
    original = (p.CLIENT_DEFAULT / 'EsteriaAppearanceGeometry.bin').read_bytes()
    magic, version, count = struct.unpack_from('<3I', original)
    skin = local(STAGE / 'assets', MODEL[:-3] + '00.skin').read_bytes()
    (STAGE / 'EsteriaAppearanceGeometry.bin').write_bytes(struct.pack('<3I', magic, version, count + 1)
        + original[12:] + MODEL.encode().ljust(128, b'\0') + struct.pack('<I', len(skin)) + skin)
    assets = {'\\'.join(path.relative_to(STAGE / 'assets').parts): path.read_bytes()
              for path in (STAGE / 'assets').rglob('*') if path.is_file()}
    storm = p.Storm(p.DLL_DEFAULT)
    target = STAGE / 'client' / ASSET
    temporary = target.with_name('drakkin-assets-next.MPQ')
    assert not temporary.exists(), 'Prior temporary asset archive needs review'
    storm.create_archive(temporary, assets)
    temporary.replace(target)
    report = p.load_json(STAGE / 'report.json')
    report['assets'] = {key: hashlib.sha256(value).hexdigest() for key, value in assets.items()}
    report['armor'] = p.load_json(STAGE / 'armor.json')
    report['archives'][str(ASSET)] = p.sha256(target)
    report['catalog_baselines'] = {name: p.sha256(p.CLIENT_DEFAULT / name)
        for name in ('EsteriaAppearance.bin', 'EsteriaAppearanceGeometry.bin', 'EsteriaAppearance.dll')}
    report['catalogs'] = {name: p.sha256(STAGE / name)
        for name in ('EsteriaAppearance.bin', 'EsteriaAppearanceGeometry.bin')}
    save(STAGE / 'report.json', report)
    print('FINALIZED Drakkin assets, portraits and geometry catalog', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('export', 'bake', 'armor', 'stage', 'config', 'preview', 'finish-assets'))
    args = parser.parse_args()
    {'export': export, 'bake': bake, 'armor': armor, 'stage': stage, 'config': config, 'preview': preview,
     'finish-assets': finish_assets}[args.action]()
