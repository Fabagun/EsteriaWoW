"""Bake Retail Human presets into native Wrath appearance fields, with reversible installation."""

from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime
from functools import lru_cache
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from wotlkconv.blp import Blp
from wotlkconv.blp.image import Image as BlpImage
from wotlkconv.m2 import parse_m2, parse_skin, write_md20
from wotlkconv.m2.downgrade import mark_external
from wotlkconv.m2.skin import write_skin
from wotlkconv.m2.split import _rebuild_skin

import retroported_race_pack as p
import skyborne_visual_pack as v

WORK = Path('G:/RetroPorterWork/human')
SOURCE = WORK / 'output/patch-root'
STAGE = WORK / 'native'
ART = STAGE / 'patch-root'
PREFIX = 'custom\\human\\wrath'
JEWELRY = ((3501, 'earrings'), (3505, 'nose'), (3601, 'necklace'))
RELATIVES = (p.GLOBAL_ARCHIVE_REL, p.ASSET_ARCHIVE_REL, p.LOCALE_ARCHIVE_REL)
SOURCE_BUILD_KEY = 'dcfc90fffd79ba00406ae46f5f657592'


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')


def source():
    """Use the existing converter with the pinned Human graph; never change the donor installation."""
    from retroporter.assets import build_asset_plan, convert_asset_plan, write_asset_plan
    from retroporter.config import DEFAULT
    from retroporter.discovery import discover_race
    from retroporter.races import RaceSpec
    from retroporter.wotlk import extract_db2

    lines = (DEFAULT.retail_root / '.build.info').read_text().splitlines()
    header = [x.split('!')[0] for x in lines[0].split('|')]
    builds = [dict(zip(header, line.split('|'), strict=True)) for line in lines[1:] if line]
    build = next(b for b in builds if b['Product'] == 'wow' and b['Active'] == '1')
    if build['Build Key'] != SOURCE_BUILD_KEY or build['Version'] != '12.1.0.69933':
        raise ValueError('Retail source changed; select and audit a new source build explicitly')
    save(WORK / 'reports/source-build.json', {k: build[k] for k in ('Build Key', 'CDN Key', 'Version', 'Product')})
    spec = RaceSpec('human', 'Human', 'Human', ('character\\human\\',),
                    (1011653, 1000764), retail_race_ids=(1,))
    extract_db2(DEFAULT, 'human')
    discovery = discover_race(DEFAULT, spec)
    save(WORK / 'reports/discovery.json', discovery)
    plan = build_asset_plan(DEFAULT, spec)
    write_asset_plan(DEFAULT, spec, plan)
    return {'output': str(convert_asset_plan(DEFAULT, spec, plan))}


def image(data):
    level = Blp.parse(data).decode_level(0)
    return Image.frombytes('RGBA', (level.width, level.height), bytes(level.data))


def indexed(art, alpha=False):
    """Match the native indexed compositor format, including fragment mip termination."""
    rgb = art.convert('RGB')
    palette_image = rgb.quantize(colors=256)
    colors = palette_image.getpalette()
    colors += [0] * (768 - len(colors))
    palette = [(colors[i + 2] | colors[i + 1] << 8 | colors[i] << 16) for i in range(0, 768, 3)]
    levels = BlpImage(art.width, art.height, bytearray(art.tobytes())).mip_chain(
        levels=min(art.size).bit_length())
    payloads = []
    for level in levels:
        layer = Image.frombytes('RGBA', (level.width, level.height), bytes(level.data))
        payload = layer.convert('RGB').quantize(palette=palette_image, dither=Image.Dither.NONE).tobytes()
        if alpha:
            payload += layer.getchannel('A').tobytes()
        payloads.append(payload)
    return Blp.from_images(levels, compression=1, alpha_size=8 if alpha else 0,
                           alpha_type=8, palette=palette, payloads=payloads).serialize()


def project(art, coordinates):
    source = BlpImage(art.width, art.height, bytearray(art.tobytes()))
    target = p._project_maghar_face(source, coordinates)
    return Image.frombytes('RGBA', (target.width, target.height), bytes(target.data))


def face_fragments(sheet):
    if sheet.size != (256, 192):
        raise ValueError('Unexpected native face sheet dimensions')
    return ((4, 'lower', sheet.crop((0, 64, 256, 192))),
            (5, 'upper', sheet.crop((0, 0, 256, 64))))


def triangles(skin, mesh):
    start = v.u16(mesh, 8) | v.u16(mesh, 2) << 16
    return [tuple(skin.vertices[j] for j in skin.indices[i:i + 3])
            for i in range(start, start + v.u16(mesh, 10), 3)]


def batch_types(model, batch):
    return [model.textures[j]['type'] for j in
            model.texture_combos[v.u16(batch, 16):v.u16(batch, 16) + v.u16(batch, 14)]]


def occupied_extra(model, skin):
    mask = Image.new('L', (512, 512))
    draw = ImageDraw.Draw(mask)
    for i, mesh in enumerate(skin.submeshes):
        if not any(8 in batch_types(model, b) for b in skin.batches if v.u16(b, 4) == i):
            continue
        for tri in triangles(skin, mesh):
            uv = [struct.unpack_from('<2f', model.vertices, j * 48 + 32) for j in tri]
            draw.polygon([(u * 511, y * 511) for u, y in uv], fill=255)
    return np.asarray(mask.filter(ImageFilter.MaxFilter(9))).copy()


def reserve(mask, width, height):
    for y in range(4, mask.shape[0] - height - 4, 4):
        for x in range(4, mask.shape[1] - width - 4, 4):
            if not mask[y - 4:y + height + 4, x - 4:x + width + 4].any():
                mask[y - 4:y + height + 4, x - 4:x + width + 4] = 255
                return [x, y, width, height]
    raise ValueError('No unused native skin-extra atlas region fits the requested tile')


def tile_uv(raw, tile):
    u, y = struct.unpack_from('<2f', raw, 32)
    if not (0 <= u <= 1 and 0 <= y <= 1):
        raise ValueError('Accessory UV outside its authored atlas')
    x, top, width, height = tile
    result = bytearray(raw)
    struct.pack_into('<2f', result, 32, (x + u * width) / 512, (top + y * height) / 512)
    return bytes(result)


def one_texture(model, batch, slot, material):
    out = bytearray(batch)
    model.texture_combos.append(slot)
    coord = len(model.texture_coord_combos)
    model.texture_coord_combos.append(0)
    for offset, value in ((0, 16), (2, 0), (10, material), (14, 1),
                          (16, len(model.texture_combos) - 1), (18, coord)):
        v.patch16(out, offset, value)
    return bytes(out)


def native_indices(skin, model):
    """Keep triangle starts in the low word; the final mesh may span past 65535."""
    largest = max(range(len(skin.submeshes)), key=lambda i: v.u16(skin.submeshes[i], 10))
    order = [i for i in range(len(skin.submeshes)) if i != largest] + [largest]
    skin = _rebuild_skin(skin, order, {i: i for i in range(model.vertex_count)})
    if any(v.u16(row, 2) for row in skin.submeshes):
        raise ValueError('Native Human geometry requires a wide triangle-start helper')
    if len(skin.vertices) > 65535 or model.vertex_count > 65535:
        raise ValueError('Native Human exceeds uint16 vertex addressing')
    return skin


def append_jewelry(model, skin, source, source_skin, geoset, tile, slot, material):
    base_by_crc = {b['bone_name_crc']: i for i, b in enumerate(model.bones) if b['bone_name_crc']}
    if len(base_by_crc) != len(model.bones):
        raise ValueError('Native Human bone identities are missing or ambiguous')
    meshes = [r for r in source_skin.submeshes if v.u16(r, 0) == geoset]
    if len(meshes) != 1:
        raise ValueError('Ambiguous source jewelry geometry')
    raw = meshes[0]
    tris = triangles(source_skin, raw)
    used = sorted({j for t in tris for j in t})
    vertex_start = model.vertex_count
    lookup_start = len(skin.vertices)
    local = {j: i for i, j in enumerate(used)}
    vertices = bytearray(model.vertices)
    for j in used:
        record = bytearray(tile_uv(source.vertices[j * 48:(j + 1) * 48], tile))
        for influence in range(4):
            if not record[12 + influence]:
                continue
            bone = source.bones[record[16 + influence]]
            target = base_by_crc.get(bone['bone_name_crc'])
            if target is None or max(abs(a - b) for a, b in zip(
                    bone['pivot'], model.bones[target]['pivot'])) > .001:
                raise ValueError('Retail jewelry bone has no matching native bind pivot')
            parent = bone['parent_bone']
            target_parent = model.bones[target]['parent_bone']
            if parent >= 0 and (target_parent < 0 or source.bones[parent]['bone_name_crc'] !=
                               model.bones[target_parent]['bone_name_crc']):
                raise ValueError('Retail jewelry bone hierarchy differs from the native Human')
            record[16 + influence] = target
        vertices.extend(record)
    model.vertices = bytes(vertices)
    model.vertex_count += len(used)
    skin.vertices.extend(range(vertex_start, model.vertex_count))
    skin.bones += bytes(4 * len(used))  # Rebuilt from the proven native bone bindings below.
    mesh = bytearray(raw)
    start = len(skin.indices)
    # Native helmet visibility can hide ears, including their baked facial jewelry.
    native_geoset = 702 if geoset < 3600 else 0
    for offset, value in ((0, native_geoset), (2, start >> 16), (4, lookup_start), (6, len(used)),
                          (8, start & 65535), (18, 0)):
        v.patch16(mesh, offset, value)
    new_mesh = len(skin.submeshes)
    skin.submeshes.append(bytes(mesh))
    skin.indices.extend(lookup_start + local[j] for t in tris for j in t)
    template = bytearray(skin.batches[0])
    for offset, value in ((2, 0), (4, new_mesh), (6, new_mesh), (8, 65535)):
        v.patch16(template, offset, value)
    skin.batches.append(one_texture(model, template, slot, material))
    return len(used)


def prepare_models(files):
    report = {}
    for sex in ('male', 'female'):
        key = f'Character\\Human2\\{sex}\\Human{sex}2.m2'
        model_bytes = files.find(key)[0]
        skin_bytes = files.find(key[:-3] + '00.skin')[0]
        model = parse_m2(model_bytes, key)
        external = {i for i, sequence in enumerate(model.sequences) if not sequence['flags'] & 0x20}
        for track in model.tracks():
            if track.global_sequence < 0:
                mark_external(track, external)
        skin = parse_skin(skin_bytes)
        if sex == 'male':
            # The old base makes Natural 3D eyebrows unconditional; baked face presets own them now.
            src = SOURCE / 'custom/human/character/human/male/humanmale_hd.m2'
            retail = parse_m2(src.read_bytes(), str(src))
            retail_skin = parse_skin(src.with_name(src.stem + '00.skin').read_bytes())
            positions = lambda m, indexes: {tuple(round(x, 4) for x in struct.unpack_from('<3f', m.vertices, j * 48))
                                             for j in indexes}
            retail_brows = set().union(*(positions(retail, {j for t in triangles(retail_skin, r) for j in t})
                                        for r in retail_skin.submeshes if 3400 < v.u16(r, 0) < 3500))
            keep = []
            for i, mesh in enumerate(skin.submeshes):
                batches = [b for b in skin.batches if v.u16(b, 4) == i]
                if v.u16(mesh, 0) == 0 and any(batch_types(model, b) == [6] for b in batches):
                    if not positions(model, {j for t in triangles(skin, mesh) for j in t}) <= retail_brows:
                        raise ValueError('Unconditional Human hair geometry is not the Retail eyebrow mesh')
                    continue
                keep.append(i)
            skin = _rebuild_skin(skin, keep, {i: i for i in range(model.vertex_count)})
        mask = occupied_extra(model, skin)
        eye_tile = reserve(mask, 128, 64)
        extra_slot = next(i for i, t in enumerate(model.textures) if t['type'] == 8)
        material = len(model.materials)
        model.materials.append({'flags': 4, 'blending_mode': 0})
        vertices = bytearray(model.vertices)
        changed = set()
        for i, raw in enumerate(skin.batches):
            slots = model.texture_combos[v.u16(raw, 16):v.u16(raw, 16) + v.u16(raw, 14)]
            if not any('eyes00_' in model.textures[j]['filename'].lower() for j in slots):
                continue
            for j in {j for t in triangles(skin, skin.submeshes[v.u16(raw, 4)]) for j in t}:
                if j not in changed:
                    vertices[j * 48:(j + 1) * 48] = tile_uv(vertices[j * 48:(j + 1) * 48], eye_tile)
                    changed.add(j)
            skin.batches[i] = one_texture(model, raw, extra_slot, material)
        if not changed:
            raise ValueError('Native Human iris geometry was not identified')
        model.vertices = bytes(vertices)
        jewelry = {}
        if sex == 'female':
            src = SOURCE / 'custom/human/character/human/female/humanfemale_hd.m2'
            retail = parse_m2(src.read_bytes(), str(src))
            retail_skin = parse_skin(src.with_name(src.stem + '00.skin').read_bytes())
            jewelry_material = len(model.materials)
            model.materials.append({'flags': 0, 'blending_mode': 1})
            for geoset, name in JEWELRY:
                tile = reserve(mask, 128, 128)
                count = append_jewelry(model, skin, retail, retail_skin, geoset, tile,
                                      extra_slot, jewelry_material)
                jewelry[name] = {'source_geoset': geoset, 'native_geoset': 702 if geoset < 3600 else 0,
                                 'tile': tile, 'vertices': count}
        skin = v.compact_bone_palettes(model, skin)
        skin = native_indices(skin, model)
        model.num_skin_profiles = 1
        for entry, data in ((key, write_md20(model)), (key[:-3] + '00.skin', write_skin(skin))):
            target = ART.joinpath(*p.PureWindowsPath(entry).parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        baseline = STAGE / 'baseline' / sex
        baseline.mkdir(parents=True, exist_ok=True)
        (baseline / 'model.m2').write_bytes(model_bytes)
        (baseline / 'model00.skin').write_bytes(skin_bytes)
        report[sex] = {'model_path': key, 'eye_tile': eye_tile, 'iris_vertices': len(changed),
                       'jewelry': jewelry, 'indices': len(skin.indices), 'vertices': model.vertex_count,
                       'maximum_triangle_start': max(v.u16(r, 8) for r in skin.submeshes),
                       'model_sha256': p.sha256(baseline / 'model.m2'),
                       'skin_sha256': p.sha256(baseline / 'model00.skin')}
    return report


class Retail:
    def __init__(self):
        self.data = p.load_json(WORK / 'reports/discovery.json')
        if self.data['race_ids'] != [1]:
            raise ValueError('Retail Human source identity changed')
        mats = {r['ID']: r for r in self.data['linked']['ChrCustomizationMaterial']}
        tex = {r['MaterialResourcesID']: r['FileDataID'] for r in self.data['texture_files']}
        paths = {r['file_data_id']: r['path'] for r in self.data['file_assets']}
        self.materials = {}
        for e in self.data['elements']:
            mat = mats.get(e['ChrCustomizationMaterialID'])
            if mat:
                key = (e['ChrCustomizationChoiceID'], mat['ChrModelTextureTargetID'],
                       e['RelatedChrCustomizationChoiceID'])
                path = SOURCE / 'custom/human' / Path(paths[tex[mat['MaterialResourcesID']]].replace('\\', '/'))
                if key in self.materials and self.materials[key] != path:
                    raise ValueError('Ambiguous Retail Human material dependency')
                self.materials[key] = path

    def choices(self, sex, name):
        model = 1 if sex == 'male' else 2
        option = next(o['ID'] for o in self.data['options'] if o['ChrModelID'] == model and o['Name_lang'] == name)
        return sorted((c for c in self.data['choices'] if c['ChrCustomizationOptionID'] == option),
                      key=lambda c: (c['OrderIndex'], c['ID']))

    @lru_cache(maxsize=128)
    def art(self, choice, target, related=0):
        path = self.materials.get((choice, target, related))
        if path is None or not path.is_file():
            return None
        return image(path.read_bytes())


def put_image(key, art, alpha=False):
    path = ART.joinpath(*p.PureWindowsPath(key).parts)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(indexed(art, alpha))
    return key


def scalp_rows(records, table, pool, retail, sex, coordinates, files):
    gender = int(sex == 'female')
    hair_table = p.RawWdbc(files.find('DBFilesClient\\CharHairGeosets.dbc')[0])
    native = {p._value(r, 12): p._value(r, 16) for r in hair_table.records
              if p._value(r, 4) == 1 and p._value(r, 8) == gender}
    geosets = {r['ID']: r for r in retail.data['linked']['ChrCustomizationGeoset']}
    styles = {}
    for choice in retail.choices(sex, 'Hair Style'):
        for element in retail.data['elements']:
            if element['ChrCustomizationChoiceID'] != choice['ID']:
                continue
            geo = geosets.get(element['ChrCustomizationGeosetID'])
            if geo and geo['GeosetType'] == 0:
                styles[geo['GeosetID']] = choice['ID']
    colors = retail.choices(sex, 'Hair Color')
    count = 0
    for i, row in enumerate(records):
        if p._value(row, 4) != 1 or p._value(row, 8) != gender or p._value(row, 12) != 3:
            continue
        style, color = p._value(row, 32), p._value(row, 36)
        choice = styles[native[style]]
        hair_color = colors[color]['ID']
        sheet = Image.new('RGBA', (512, 512))
        for target in (11, 12):
            layer = retail.art(choice, target, hair_color)
            if layer is not None:
                sheet = Image.alpha_composite(sheet, layer)
        baked = project(sheet, coordinates)
        for field, name, art in face_fragments(baked):
            key = put_image(f'{PREFIX}\\{sex}\\scalp{style:02d}-{color:02d}-{name}.blp', art, True)
            row = p._set_string(row, field + 1, pool, key)
        records[i] = row
        count += 1
    return count


def scalps():
    retail = Retail()
    table = p.RawWdbc((ART / 'DBFilesClient/CharSections.dbc').read_bytes())
    pool, records = bytearray(table.strings), list(table.records)
    manifest = {'source_patch_root': str(SOURCE), 'models': {
        sex: {'runtime_model_path': f'Character\\Human2\\{sex}\\Human{sex}2.m2',
              'model_path': f'custom\\human\\character\\human\\{sex}\\human{sex}_hd.m2'}
        for sex in ('male', 'female')}}
    with p.ClientFiles(str(p.CLIENT_DEFAULT / 'Data'), 'enUS') as files:
        for sex in ('male', 'female'):
            coords, _, _ = p._maghar_face_uv_map(manifest, p.CLIENT_DEFAULT, sex)
            count = scalp_rows(records, table, pool, retail, sex, coords, files)
            print(f'{sex}: {count} retail scalp rows projected', flush=True)
    (ART / 'DBFilesClient/CharSections.dbc').write_bytes(table.build(records, bytes(pool)))
    return check()


def prepare():
    if (STAGE / 'last-install.json').is_file():
        raise ValueError('Restore the documented baseline before regenerating an installed Human replacement')
    protected = [p.CLIENT_DEFAULT / 'Wow.exe', p.CLIENT_DEFAULT / 'EsteriaAppearance.dll',
                 *p.CLIENT_DEFAULT.glob('Esteria*.bin')]
    save(STAGE / 'protected-files.json', {path.name: p.sha256(path) for path in protected if path.is_file()})
    ART.mkdir(parents=True, exist_ok=True)
    retail = Retail()
    report = {'source_build': '12.1.0.69933', 'race_id': 1, 'dll_required': False,
              'preset_policy': 'eye color and jewelry follow skin; eyebrows and makeup follow face',
              'preserved': ['five native fields', 'appearance keys and flags', 'race/display/model IDs',
                            'native hair/facial-hair styles', 'animation tracks', 'other races'],
              'limitations': ['native-compatible Human2 base; no selectable Retail BONE face morphs',
                              'curated combinations, not all independent Retail combinations'],
              'live_acceptance': 'unverified', 'presets': []}
    manifest = {'source_patch_root': str(SOURCE), 'models': {
        sex: {'runtime_model_path': f'Character\\Human2\\{sex}\\Human{sex}2.m2',
              'model_path': f'custom\\human\\character\\human\\{sex}\\human{sex}_hd.m2'}
        for sex in ('male', 'female')}}
    with p.ClientFiles(str(p.CLIENT_DEFAULT / 'Data'), 'enUS') as files:
        original = files.find('DBFilesClient\\CharSections.dbc')[0]
        baseline = STAGE / 'baseline/CharSections.dbc'
        baseline.parent.mkdir(parents=True, exist_ok=True)
        baseline.write_bytes(original)
        table = p.RawWdbc(original)
        report['models'] = prepare_models(files)
        pool = bytearray(table.strings)
        records = list(table.records)
        for gender, sex in enumerate(('male', 'female')):
            coordinates, covered, uv_report = p._maghar_face_uv_map(manifest, p.CLIENT_DEFAULT, sex)
            report['models'][sex]['face_projection'] = uv_report
            rows = [(i, r) for i, r in enumerate(records) if p._value(r, 4) == 1 and p._value(r, 8) == gender]
            skins = retail.choices(sex, 'Skin Color')
            eyes = [c for c in retail.choices(sex, 'Eye Color') if c['OrderIndex'] < 19]
            eyebrows = retail.choices(sex, 'Eyebrows')[:9 if sex == 'male' else 26]
            hair_color = retail.choices(sex, 'Hair Color')[0]['ID']
            makeup = retail.choices(sex, 'Makeup') if sex == 'female' else []
            skin_choices = {}
            for i, row in rows:
                if p._value(row, 12) != 0:
                    continue
                color = p._value(row, 36)
                if color < 15:
                    source_skin = next(c for c in skins if c['OrderIndex'] == color)
                else:
                    later = [c for c in skins if c['OrderIndex'] >= (18 if sex == 'male' else 17)]
                    source_skin = later[(color - 15) % len(later)]
                skin_choices[color] = source_skin['ID']
                source_body = retail.art(source_skin['ID'], 1)
                old_extra = image(files.find(p._string(table.strings, p._value(row, 20)).decode())[0])
                body = source_body.crop((0, 0, 512, 512)) if source_body else image(
                    files.find(p._string(table.strings, p._value(row, 16)).decode())[0])
                eye = eyes[color % len(eyes)]
                if p._value(row, 28) & 4:
                    eye = next(c for c in retail.choices(sex, 'Eye Color') if c['ChrCustomizationReqID'] == 142)
                eye_art = retail.art(eye['ID'], 25)
                if eye_art is None:
                    raise ValueError('A selected Human eye material is unavailable')
                extra = source_body.crop((512, 0, 1024, 512)) if source_body else old_extra.copy()
                eye_tile = report['models'][sex]['eye_tile']
                extra.paste(eye_art.resize(tuple(eye_tile[2:]), Image.Resampling.LANCZOS), tuple(eye_tile[:2]))
                jewelry_state = color % 5 if sex == 'female' and not p._value(row, 28) & 4 else 0
                enabled = ((), ('earrings',), ('nose',), ('necklace',), ('earrings', 'necklace'))[jewelry_state]
                if sex == 'female':
                    jewelry_path = SOURCE / 'custom/human/character/human/female/humanfemalenecklace.blp'
                    jewelry_art = image(jewelry_path.read_bytes())
                    for name, info in report['models'][sex]['jewelry'].items():
                        tile = info['tile']
                        art = jewelry_art.resize(tuple(tile[2:]), Image.Resampling.LANCZOS)
                        if name not in enabled:
                            art.putalpha(0)
                        extra.paste(art, tuple(tile[:2]))
                prefix = f'{PREFIX}\\{sex}\\skin{color:02d}'
                keys = (put_image(prefix + '-body.blp', body), put_image(prefix + '-extra.blp', extra, True))
                for field, key in zip((4, 5), keys):
                    row = p._set_string(row, field, pool, key)
                records[i] = row
                report['presets'].append({'sex': sex, 'skin_index': color, 'skin_choice': source_skin['ID'],
                                          'eye_choice': eye['ID'], 'jewelry': list(enabled),
                                          'body_source': ('retail' if source_body else
                                                          'preserved unavailable NPC texture')})
            faces_by_skin = defaultdict(list)
            for choice in retail.choices(sex, 'Face'):
                for source_skin in set(skin_choices.values()):
                    source = retail.materials.get((choice['ID'], 5, source_skin))
                    if source is not None and source.is_file():
                        faces_by_skin[source_skin].append(choice)
            for i, row in rows:
                if p._value(row, 12) != 1:
                    continue
                face, color = p._value(row, 32), p._value(row, 36)
                source_skin = skin_choices[color]
                options = faces_by_skin[source_skin]
                if not options:
                    continue  # NPC-only source complexion is unavailable; retain its existing face.
                choice = options[face % len(options)]
                head = retail.art(choice['ID'], 5, source_skin)
                brow = eyebrows[face % len(eyebrows)]
                brow_art = retail.art(brow['ID'], 8, hair_color)
                if brow_art is None:
                    raise ValueError('Selected baked eyebrow material is unavailable')
                head = Image.alpha_composite(head, brow_art.resize(head.size, Image.Resampling.LANCZOS))
                if makeup:
                    choice_makeup = makeup[(face // len(options)) % len(makeup)]
                    makeup_art = retail.art(choice_makeup['ID'], 29)
                    if makeup_art:
                        head = Image.alpha_composite(head, makeup_art.resize(head.size, Image.Resampling.LANCZOS))
                baked = project(head, coordinates)
                prefix = f'{PREFIX}\\{sex}\\face{face:02d}-{color:02d}'
                for field, fragment, art in face_fragments(baked):
                    key = put_image(prefix + '-' + fragment + '.blp', art)
                    row = p._set_string(row, field, pool, key)
                records[i] = row
                report['presets'].append({'sex': sex, 'face_index': face, 'skin_index': color,
                                          'face_choice': choice['ID'], 'eyebrow_choice': brow['ID']})
            scalp_rows(records, table, pool, retail, sex, coordinates, files)
            print(f'Prepared {sex}: {len(rows)} native appearance records', flush=True)
        data = table.build(records, bytes(pool))
        out = ART / 'DBFilesClient/CharSections.dbc'
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(data)
    report['baseline_charsections_sha256'] = p.sha256(baseline)
    save(STAGE / 'prepare.json', report)
    return check()


def check():
    report = p.load_json(STAGE / 'prepare.json')
    original = p.RawWdbc((STAGE / 'baseline/CharSections.dbc').read_bytes())
    staged = p.RawWdbc((ART / 'DBFilesClient/CharSections.dbc').read_bytes())
    if len(staged.records) != len(original.records) or not staged.strings.startswith(original.strings):
        raise ValueError('Native appearance table structure changed')
    changed = 0
    for before, after in zip(original.records, staged.records, strict=True):
        if p._value(before, 4) != 1:
            if before != after:
                raise ValueError('A non-Human appearance record changed')
        else:
            if before[:16] != after[:16] or before[28:] != after[28:]:
                raise ValueError('Human appearance identity, selection indexes or flags changed')
            changed += before != after
    with p.ClientFiles(str(p.CLIENT_DEFAULT / 'Data'), 'enUS') as files:
        for sex, info in report['models'].items():
            path = ART.joinpath(*p.PureWindowsPath(info['model_path']).parts)
            model = parse_m2(path.read_bytes(), str(path))
            skin = parse_skin(path.with_name(path.stem + '00.skin').read_bytes())
            base = parse_m2((STAGE / 'baseline' / sex / 'model.m2').read_bytes())
            if model.sequences != base.sequences or model.sequence_lookups != base.sequence_lookups:
                raise ValueError('Native Human animation sequences changed')
            if model.attachments != base.attachments:
                # Attachment tracks have relocated internal offsets; verify identity and bind anchors below.
                identity = lambda a: (a['id'], a['bone'], a['position'])
                if [identity(a) for a in model.attachments] != [identity(a) for a in base.attachments]:
                    raise ValueError('Native Human equipment attachment anchors changed')
            external = {i for i, sequence in enumerate(base.sequences) if not sequence['flags'] & 0x20}
            for before, after in zip(base.tracks(), model.tracks(), strict=True):
                if (type(before) is not type(after) or getattr(before, 'kind', None) != getattr(after, 'kind', None)
                        or before.global_sequence != after.global_sequence):
                    raise ValueError('Native Human animation track identity changed')
                if before.global_sequence < 0:
                    for sequence in external:
                        for name in ('timestamp_spans', 'value_spans'):
                            if not hasattr(before, name):
                                continue
                            a, b = getattr(before, name), getattr(after, name)
                            if sequence < len(a) and (sequence >= len(b) or a[sequence] != b[sequence]):
                                raise ValueError('Native Human external animation offsets changed')
            if any(v.u16(r, 2) or v.u16(r, 12) > 75 for r in skin.submeshes):
                raise ValueError('Human SKIN depends on expanded geometry support')
            if max(skin.indices) >= len(skin.vertices) or max(skin.vertices) >= model.vertex_count:
                raise ValueError('Human skin index outside its addressed array')
            if any(t['type'] in (11, 15) for t in model.textures):
                raise ValueError('Unsupported Retail replaceable texture survived')
            for texture in model.textures:
                if texture['filename']:
                    files.find(texture['filename'])
        for row in staged.records:
            if p._value(row, 4) != 1:
                continue
            for field in (4, 5, 6):
                key = p._string(staged.strings, p._value(row, field * 4)).decode()
                if not key:
                    continue
                art_path = ART.joinpath(*p.PureWindowsPath(key).parts)
                data = art_path.read_bytes() if art_path.is_file() else files.find(key)[0]
                blp = Blp.parse(data, key)
                if not blp.is_wotlk_compatible()[0]:
                    raise ValueError('Incompatible native Human texture: ' + key)
    report.update(status='static checks passed; live acceptance unverified', changed_records=changed,
                  generated_files=sum(1 for x in ART.rglob('*') if x.is_file()))
    save(STAGE / 'validation.json', report)
    return {k: report[k] for k in ('status', 'changed_records', 'generated_files', 'models')}


def stage():
    check()
    with p.ClientFiles(str(p.CLIENT_DEFAULT / 'Data'), 'enUS') as files:
        current_data = files.find('DBFilesClient\\CharSections.dbc')[0]
        baseline = STAGE / 'baseline/CharSections.dbc'
        if current_data != baseline.read_bytes():
            current, original = p.RawWdbc(current_data), p.RawWdbc(baseline.read_bytes())
            prepared = p.RawWdbc((ART / 'DBFilesClient/CharSections.dbc').read_bytes())

            def human(table):
                return {p._value(r, 0): (r[:16], r[28:], tuple(p._string(table.strings, p._value(r, f * 4))
                                                             for f in (4, 5, 6)))
                        for r in table.records if p._value(r, 4) == 1}

            if human(current) != human(original):
                raise ValueError('Human customization changed during preparation; do not merge concurrent Human edits')
            replacements = {p._value(r, 0): r for r in prepared.records if p._value(r, 4) == 1}
            pool, rows = bytearray(current.strings), []
            for row in current.records:
                if p._value(row, 4) == 1:
                    row = replacements[p._value(row, 0)]
                    for field in (4, 5, 6):
                        key = p._string(prepared.strings, p._value(row, field * 4)).decode()
                        row = p._set_string(row, field, pool, key) if key else p._replace(row, field * 4, 4, 0)
                rows.append(row)
            (ART / 'DBFilesClient/CharSections.dbc').write_bytes(current.build(rows, bytes(pool)))
            baseline.write_bytes(current_data)
            report = p.load_json(STAGE / 'prepare.json')
            report['baseline_charsections_sha256'] = p.sha256(baseline)
            save(STAGE / 'prepare.json', report)
            print('Preserved concurrent non-Human table changes in the current client baseline', flush=True)
        for sex in ('male', 'female'):
            key = f'Character\\Human2\\{sex}\\Human{sex}2.m2'
            if files.find(key)[0] != (STAGE / 'baseline' / sex / 'model.m2').read_bytes():
                raise ValueError('Native Human model changed during preparation')
    updates = {str(path.relative_to(ART)).replace('/', '\\'): path.read_bytes()
               for path in ART.rglob('*') if path.is_file()}
    storm = p.Storm(p.DLL_DEFAULT)
    report = {'archives': {}}
    for relative in RELATIVES:
        live = p.CLIENT_DEFAULT / relative
        destination = STAGE / 'install' / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        source_hash = p.sha256(live)
        shutil.copy2(live, destination)
        if p.sha256(destination) != source_hash:
            raise ValueError('Stage archive copy mismatch')
        selected = {key: data for key, data in updates.items()
                    if key.lower().startswith('custom\\') == (relative == p.ASSET_ARCHIVE_REL)}
        storm.replace_archive_entries(destination, selected)
        handle = storm.open_archive(destination)
        try:
            for key, data in selected.items():
                actual = storm.read(handle, key)
                if key.lower().endswith('charsections.dbc'):
                    # StormLib applies native CharSections ordering; compare semantic rows separately.
                    a, b = p.RawWdbc(actual), p.RawWdbc(data)
                    if sorted(a.records) != sorted(b.records) or a.strings != b.strings:
                        raise ValueError('Staged CharSections semantic readback mismatch')
                elif actual != data:
                    raise ValueError('Staged Human archive readback mismatch: ' + key)
        finally:
            storm.dll.SFileCloseArchive(handle)
        if destination.stat().st_size >= 0x80000000:
            storm.compact_archive(destination)
            if destination.stat().st_size >= 0x80000000:
                raise ValueError('Human staging exceeds the classic archive reader boundary')
        report['archives'][str(relative)] = {'source_sha256': source_hash, 'stage_sha256': p.sha256(destination)}
    save(STAGE / 'stage.json', report)
    return report


def install():
    check()
    running = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq Wow.exe', '/FO', 'CSV'],
                             capture_output=True, text=True, check=True).stdout
    if '"Wow.exe"' in running:
        raise RuntimeError('Close WoW before replacing its archives')
    receipt = p.load_json(STAGE / 'stage.json')
    backup = WORK / 'backups' / datetime.now().strftime('%Y%m%d-%H%M%S')
    for relative in RELATIVES:
        entry = receipt['archives'][str(relative)]
        live = p.CLIENT_DEFAULT / relative
        staged = STAGE / 'install' / relative
        if p.sha256(live) != entry['source_sha256'] or p.sha256(staged) != entry['stage_sha256']:
            raise ValueError('Human stage or live baseline changed; restage before installation')
        target = backup / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(live, target)
        if p.sha256(target) != entry['source_sha256']:
            raise ValueError('Human rollback backup hash mismatch')
    replaced = []
    try:
        for relative in RELATIVES:
            live = p.CLIENT_DEFAULT / relative
            entry = receipt['archives'][str(relative)]
            temporary = live.with_name(live.name + '.human-native.tmp')
            if not temporary.resolve().is_relative_to(p.CLIENT_DEFAULT.resolve()) or temporary.exists():
                raise ValueError('Unexpected Human installation temporary path')
            shutil.copy2(STAGE / 'install' / relative, temporary)
            if p.sha256(temporary) != entry['stage_sha256'] or p.sha256(live) != entry['source_sha256']:
                temporary.unlink()
                raise ValueError('Client archive changed before atomic replacement; restage')
            os.replace(temporary, live)
            replaced.append(relative)
            if p.sha256(live) != entry['stage_sha256']:
                raise ValueError('Installed Human archive hash mismatch')
    except BaseException:
        for relative in replaced:
            if p.sha256(p.CLIENT_DEFAULT / relative) != receipt['archives'][str(relative)]['stage_sha256']:
                raise RuntimeError('Concurrent archive modification detected; preserve it and use the recorded backup')
            shutil.copy2(backup / relative, p.CLIENT_DEFAULT / relative)
        raise
    receipt.update(backup=str(backup), status='installed; live acceptance unverified')
    save(backup / 'receipt.json', receipt)
    save(STAGE / 'last-install.json', receipt)
    return receipt


def preview():
    """Export the staged native texture composition to the existing offline Blender viewer."""
    import creature_animation_repair as motion

    check()
    sections = p.RawWdbc((ART / 'DBFilesClient/CharSections.dbc').read_bytes())
    with p.ClientFiles(str(p.CLIENT_DEFAULT / 'Data'), 'enUS') as files:
        for sex, color in (('male', 0), ('female', 1), ('female', 3), ('female', 4)):
            gender = int(sex == 'female')
            root = STAGE / 'previews' / (sex + '-' + str(color))
            root.mkdir(parents=True, exist_ok=True)

            def read(key):
                path = ART.joinpath(*p.PureWindowsPath(key).parts)
                return path.read_bytes() if path.is_file() else files.find(key)[0]

            def section(kind, style=0, shade=color):
                return next(r for r in sections.records if p._value(r, 4) == 1 and p._value(r, 8) == gender
                            and p._value(r, 12) == kind and p._value(r, 32) == style and p._value(r, 36) == shade)

            def fragment(row, field):
                key = p._string(sections.strings, p._value(row, field * 4)).decode()
                return image(read(key)) if key else None

            body = fragment(section(0), 4)
            extra = fragment(section(0), 5)
            face = section(1, style=1)
            for field, top in ((4, 384), (5, 320)):
                body.paste(fragment(face, field), (0, top))
            underwear = section(4)
            for field, xy in ((4, (256, 192)), (5, (256, 0))):
                art = fragment(underwear, field)
                if art:
                    body.alpha_composite(art, xy)
            hair = section(3, style=1, shade=0)
            hair_art = fragment(hair, 4)
            for field, top in ((5, 384), (6, 320)):
                art = fragment(hair, field)
                if art:
                    body.alpha_composite(art, (0, top))
            textures = {}
            for kind, art in ((1, body), (8, extra), (6, hair_art)):
                path = root / (str(kind) + '.png')
                art.save(path)
                textures[kind] = str(path)
            key = f'Character\\Human2\\{sex}\\Human{sex}2.m2'
            model = parse_m2(read(key), key)
            skin = parse_skin(read(key[:-3] + '00.skin'))
            posed = motion.posed_vertices(model, motion.pose_matrices(model, 0, 800))
            vertices = [{'position': posed[i].tolist(),
                         'normal': list(struct.unpack_from('<3f', model.vertices, i * 48 + 20)),
                         'uv': list(struct.unpack_from('<2f', model.vertices, i * 48 + 32))}
                        for i in range(model.vertex_count)]
            selected = {0, 2 if sex == 'male' else 3, 401, 501, 702, 802, 902,
                        1002, 1102, 1202, 1301, 1801, 2001}
            parts = []
            for i, mesh in enumerate(skin.submeshes):
                if v.u16(mesh, 0) not in selected:
                    continue
                batch = next(b for b in skin.batches if v.u16(b, 4) == i)
                texture = model.textures[model.texture_combos[v.u16(batch, 16)]]
                kind = texture['type']
                if kind == 0:
                    if 'eyereflect' in texture['filename'].lower():
                        continue  # The offline viewer cannot reproduce the native reflection shader.
                    path = root / ('fixed-' + str(i) + '.png')
                    image(read(texture['filename'])).save(path)
                    texture_path = str(path)
                elif kind in textures:
                    texture_path = textures[kind]
                else:
                    continue
                parts.append({'geoset': v.u16(mesh, 0), 'triangles': triangles(skin, mesh),
                              'texture': texture_path, 'unlit': bool(model.materials[v.u16(batch, 10)]['flags'] & 4)})
            save(root / 'model.json', {'vertices': vertices, 'meshes': parts,
                                      'camera': [5, -1.5, 1.9], 'target': [0, 0, 1.65], 'scale': .8})
    return {'previews': str(STAGE / 'previews'), 'status': 'offline material preview only'}


def rollback():
    receipt = p.load_json(STAGE / 'last-install.json')
    backup = Path(receipt['backup']).resolve()
    if not backup.is_relative_to((WORK / 'backups').resolve()):
        raise ValueError('Human rollback path is outside this task backup directory')
    running = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq Wow.exe', '/FO', 'CSV'],
                             capture_output=True, text=True, check=True).stdout
    if '"Wow.exe"' in running:
        raise RuntimeError('Close WoW before restoring its archives')
    for relative in RELATIVES:
        entry = receipt['archives'][str(relative)]
        if (p.sha256(p.CLIENT_DEFAULT / relative) != entry['stage_sha256']
                or p.sha256(backup / relative) != entry['source_sha256']):
            raise ValueError('Archives changed since installation; preserve later edits and restore Human selectively')
    for relative in RELATIVES:
        live = p.CLIENT_DEFAULT / relative
        temporary = live.with_name(live.name + '.human-rollback.tmp')
        if not temporary.resolve().is_relative_to(p.CLIENT_DEFAULT.resolve()) or temporary.exists():
            raise ValueError('Unexpected Human rollback temporary path')
        shutil.copy2(backup / relative, temporary)
        entry = receipt['archives'][str(relative)]
        if p.sha256(temporary) != entry['source_sha256'] or p.sha256(live) != entry['stage_sha256']:
            temporary.unlink()
            raise ValueError('Archive changed while preparing Human rollback')
        os.replace(temporary, live)
    receipt['status'] = 'rolled back'
    save(STAGE / 'last-rollback.json', receipt)
    (STAGE / 'last-install.json').unlink()
    return receipt


def verify():
    receipt = p.load_json(STAGE / 'last-install.json')
    providers = set()
    matched = 0
    with p.ClientFiles(str(p.CLIENT_DEFAULT / 'Data'), 'enUS') as files:
        for path in ART.rglob('*'):
            if not path.is_file():
                continue
            key = str(path.relative_to(ART)).replace('/', '\\')
            actual, provider = files.find(key)
            expected = path.read_bytes()
            if key.lower().endswith('charsections.dbc'):
                a, b = p.RawWdbc(actual), p.RawWdbc(expected)
                equal = a.strings == b.strings and sorted(a.records) == sorted(b.records)
            else:
                equal = actual == expected
            if not equal:
                raise ValueError('Effective client payload differs from the verified stage: ' + key)
            matched += 1
            providers.add(provider)
    for name, digest in p.load_json(STAGE / 'protected-files.json').items():
        if p.sha256(p.CLIENT_DEFAULT / name) != digest:
            raise ValueError('Protected client executable/helper/catalog changed: ' + name)
    result = {'effective_payloads': matched, 'protected_files_unchanged': True,
              'providers': sorted(providers), 'backup': receipt['backup'], 'live_acceptance': 'unverified'}
    save(STAGE / 'post-install.json', result)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('source', 'prepare', 'check', 'stage', 'install',
                                          'preview', 'scalps', 'rollback', 'verify'))
    args = parser.parse_args()
    print(json.dumps(globals()[args.action](), indent=2))
