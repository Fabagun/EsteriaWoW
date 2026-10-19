"""Prepare Horde Gnoll63 on isolated copies; installation is a separate coordinated step."""

import argparse
import copy
import hashlib
import json
import math
import os
import shutil
from pathlib import Path, PureWindowsPath
import struct
import uuid
from dataclasses import asdict

from PIL import Image
from wotlkconv.blp import Blp
from wotlkconv.m2 import parse_m2, parse_skin, write_md20
from wotlkconv.m2.skin import write_skin

import creature_race_pack as c
import retroported_race_pack as p
import skyborne_visual_pack as visual

ROOT = c.WORK / 'gnoll'
CACHE = c.PROJECT / 'sources/retail/races/gnoll'
STAGE = Path('C:/Users/Zach/.codex/tmp/gnoll-horde-deploy-20261006')
RACE = 63
TOKEN = 'GnollHorde'
PREFIX = 'custom\\gnoll\\native\\'
MODEL = PREFIX + 'gnoll.m2'
ASSET_ARCHIVE = Path('Data/Patch-6.MPQ')
BODY_IDS = (3886649, 3886650, 3886651, 3925236, 3925237, 3886648, 3886652, 3886646, 3887342, 3887343)
ARMOR_IDS = (3886645, 3886644, 3886643)
LABELS = ('Fur Color', 'Mane', 'Beard', 'Ears', 'Eyes', 'Outfit Color', 'Chest Sling',
          'Cuffs', 'Waist', 'Loincloth', 'Tail', 'Leg Wraps', 'Pauldrons', 'Belt Strap', 'Trousers')
CHOICES = (BODY_IDS, (101, 102, 103, 104, 105, 106), (201, 202, 203), (301, 302, 303),
           (401, 402, 403), ARMOR_IDS, (500, 502, 503, 504), (600, 602, 603, 604, 605),
           (701, 702), (801, 802), (901, 902, 903, 904), (1001, 1002),
           (1100, 1102, 1103), (1200, 1202), (1302, 1303, 1304))
FIELDS = ((0, 4, 10), (1, 2, 3), (5, 6, 7), (8, 9, 11, 12, 13), (14,))
RANGES = {'CreatureModelData': {'male': 120068}, 'CreatureDisplayInfo': {'male': 60059, 'female': 0},
          'CharSections': [1102000, 1111999], 'CharHairGeosets': [1102000, 1102099],
          'BarberShopStyle': [1102000, 1102499], 'CharStartOutfit': [22060, 22069], 'NameGen': [69000, 71999]}


def codec():
    descriptors = [None] * len(LABELS)
    capacities = []
    for field, indices in enumerate(FIELDS):
        factor = 1
        for index in indices:
            descriptors[index] = (field, len(CHOICES[index]), factor)
            factor *= len(CHOICES[index])
        if factor > 256:
            raise ValueError('Gnoll appearance byte exceeds capacity')
        capacities.append(factor)
    return {'descriptors': descriptors, 'capacities': capacities,
            'options': [{'label': label, 'choices': list(values)} for label, values in zip(LABELS, CHOICES)]}


def manifest():
    return {'schema_version': 1, 'slug': 'gnoll', 'name': 'Gnoll', 'race_ids': [RACE],
            'enum': 'RACE_GNOLL_HORDE', 'faction': 'horde', 'client_file_strings': {'63': TOKEN},
            'glue_token': 'GNOLLHORDE', 'helmet_prefix': 'Gn', 'source_race_id': 2,
            'legacy_mask_race': 2, 'visual_base_race': 12, 'start_profile': 'durotar', 'donor_totem_race': 2,
            'classes': [1, 2, 3, 4, 5, 6, 7, 8, 9, 11], 'source_patch_root': str(ROOT / 'converted'),
            'runtime_patch_root': str(STAGE / 'assets'),
            'models': {'male': {'model_id': 120068, 'display_id': 60059, 'model_path': MODEL}},
            'appearance': {'mode': 'native-stock-five-byte-v1', 'source': 'retail-creature-gnoll2',
                           'hide_helm': True, 'supported_genders': [0], 'profiles': {'0': codec()}},
            'random_playerbot_enabled': False, 'custom_racial_spells': []}


def allocation():
    result = p.load_json(p.ALLOCATION_PATH)
    if any(RACE in ids for slug, ids in result['race_ids'].items() if slug != 'gnoll'):
        raise ValueError('Race63 is reserved by another pack')
    old = result['race_allocations'].get('gnoll')
    if old is not None and old != RANGES:
        raise ValueError('Gnoll allocation differs')
    result['race_ids']['gnoll'] = [RACE]
    result['race_allocations']['gnoll'] = copy.deepcopy(RANGES)
    return result


def config():
    save(p.manifest_path('gnoll'), manifest())
    reserved = allocation()
    for name, bounds in RANGES.items():
        if isinstance(bounds, list):
            reserved['dbc_ranges'][name][1] = max(reserved['dbc_ranges'][name][1], bounds[1])
    reserved['dbc_ranges']['CreatureDisplayInfo'][1] = max(reserved['dbc_ranges']['CreatureDisplayInfo'][1], 60059)
    save(p.ALLOCATION_PATH, reserved)
    path = p.ROOT / 'modules/mod-custom-server/data/races/race_registry.json'
    registry = p.load_json(path)
    entry = {'id': RACE, 'species_key': 'gnoll_horde', 'display_name': 'Gnoll', 'faction': 'horde',
             'species_selection': False, 'start_profile': 'durotar', 'asset_owner': 'retroporter_gnoll',
             'legacy_mask_race': 2, 'visual_base_race': 12, 'supported_genders': [0]}
    old = next((r for r in registry['playable'] if r['id'] == RACE), None)
    if old is not None and old != entry:
        raise ValueError('Registry slot63 differs')
    if old is None:
        registry['playable'].append(entry)
    registry['sources']['retroporter_gnoll'] = manifest()['runtime_patch_root']
    save(path, registry)
    c.header()


def prepare_motion():
    import creature_animation_repair as repair
    import earthen_race_pack as e
    import sethrak_animation_pack as animations
    model = visual.read_player_model(ROOT / 'converted/gnoll2.m2')
    e.tracks.embed(model, ROOT / 'converted', 'gnoll2')
    before = copy.deepcopy(model)
    files = p.ClientFiles(str(p.CLIENT_DEFAULT / 'Data'), 'enUS')
    try:
        key = 'Character\\Worgen\\Male\\WorgenMale.m2'
        donor, hashes = animations.embedded_model(STAGE / 'donors', key, lambda k: files.find(k)[0])
        skin, provider = files.find(key[:-3] + '00.skin')
        c.immutable(STAGE / 'donors/worgen00.skin', skin)
    finally:
        files.close()
    c.immutable(STAGE / 'donors/worgen.m2', write_md20(donor))
    report = {'donor': key, 'donor_hashes': hashes, 'skin_provider': provider, 'added': []}
    actions = set(animations.ACTIONS) | {18, 22, 23, 24, 27, 29, 30, 46, 47, 61, 71, 84, 85, 86,
                                      87, 88, 95, 105, 108, 109, 118, 121, 185, 186}
    present = {s['id'] for s in model.sequences}
    for action in sorted(actions - present - {47, 71}):
        report['added'].append(repair.retarget(model, donor, action))
    for action, source_action in ((2, 53), (31, 51), (32, 53), (33, 54), (72, 97)):
        if action not in {s['id'] for s in model.sequences}:
            row = copy.deepcopy(model.sequences[repair.sequence(model, source_action)])
            row.update(id=action, variation_index=0, flags=row['flags'] | 0x40,
                       alias_next=repair.sequence(model, source_action), variation_next=-1)
            model.sequences.append(row)
            for track in model.tracks():
                repair.per_sequence(track, model)
    e.rebuild_sequence_lookup(model)
    retained = copy.deepcopy(model)
    retained.events = retained.events[:len(before.events)]
    animations.tracks_equal(before, retained, len(before.sequences))
    from sethrak_equipment_repair import use_running_landing
    report['running_landing'] = use_running_landing(model)
    encoded = write_md20(model)
    animations.check_model(parse_m2(encoded), encoded)
    STAGE.mkdir(parents=True, exist_ok=True)
    (STAGE / 'animated.m2').write_bytes(encoded)
    save(STAGE / 'motion.json', report)
    print('PREPARED Gnoll motion', len(model.sequences), 'sequences', flush=True)


def export_body():
    import sethrak_equipment_repair as equipment
    from sethrak_body_regions import body_uvs
    model = parse_m2((STAGE / 'animated.m2').read_bytes())
    skin = parse_skin((ROOT / 'converted/gnoll200.skin').read_bytes())
    donor = parse_m2((STAGE / 'donors/worgen.m2').read_bytes())
    donor_skin = parse_skin((STAGE / 'donors/worgen00.skin').read_bytes())
    by_crc = {b['bone_name_crc']: i for i, b in enumerate(model.bones) if b['bone_name_crc']}
    semantic = arm_bones(model, donor)

    def target_bone(index):
        visited = set()
        while index >= 0 and index not in visited:
            visited.add(index)
            if index in semantic:
                return semantic[index]
            if donor.bones[index]['bone_name_crc'] in by_crc:
                return by_crc[donor.bones[index]['bone_name_crc']]
            index = donor.bones[index]['parent_bone']
        raise ValueError('Worgen equipment has no matching Gnoll ancestor')

    fitted = []
    for i in range(donor.vertex_count):
        v = equipment.vertex_record(donor, i)
        for slot, weight in enumerate(v['weights']):
            if weight:
                bone = v['bones'][slot]
                target = target_bone(bone)
                v['bones'][slot] = target
                for axis in range(3):
                    v['position'][axis] += weight / 255 * (model.bones[target]['pivot'][axis]
                                                          - donor.bones[bone]['pivot'][axis])
        fitted.append(v)
    protected = set()
    for key in (50, 41, 59, 60):
        if key < len(model.key_bone_lookup) and model.key_bone_lookup[key] < len(model.bones):
            protected |= equipment.descendants(model, model.key_bone_lookup[key])
    body, original = [], []
    for row in skin.submeshes:
        source_geo = visual.u16(row, 0)
        if source_geo not in (0, 701, 801, 1001):
            continue
        for tri in triangles(skin, row):
            weight = sum(model.vertices[v * 48 + 12 + s] for v in tri for s in range(4)
                         if model.vertices[v * 48 + 16 + s] in protected)
            (original if source_geo == 0 and weight >= 255 else body).append(tri)
    garments, donor_body = [], []
    for index, row in enumerate(donor_skin.submeshes):
        geo = visual.u16(row, 0)
        batches = [b for b in donor_skin.batches if visual.u16(b, 4) == index]
        types = {donor.textures[donor.texture_combos[visual.u16(b, 16)]]['type'] for b in batches}
        if geo == 0 and types == {1}:
            donor_body.extend(triangles(donor_skin, row))
        elif ((400 <= geo < 1400 or 1800 <= geo < 1900) and types == {1}):
            garments.append({'geoset': geo, 'triangles': triangles(donor_skin, row), 'texture_type': 1})
    sources = []
    for index, fid in enumerate(BODY_IDS):
        image = Blp.parse(raw(fid)).decode_level(0)
        path = STAGE / 'source-images' / (str(index) + '.png')
        path.parent.mkdir(parents=True, exist_ok=True)
        Image.frombytes('RGBA', (image.width, image.height), bytes(image.data)).save(path)
        sources.append(str(path))
    assert body and original and garments and donor_body
    # Gnoll's back rises above its shoulder pivots; the visible torso, not a bone-height cutoff, owns armor UVs.
    collar = max(struct.unpack_from('<f', model.vertices, v * 48 + 8)[0] for tri in body for v in tri) + .02
    fit_surface = [tri for row in skin.submeshes if visual.u16(row, 0) in (0, 701, 801, 1001, 1302)
                   for tri in triangles(skin, row)]
    # Hanging cloth follows the source model's visible body envelope rather than mismatched NPC bind pivots.
    source_points = [struct.unpack_from('<3f', donor.vertices, i * 48) for i in range(donor.vertex_count)]
    target_points = [struct.unpack_from('<3f', model.vertices, i * 48) for i in range(model.vertex_count)]
    scale = max(v[2] for v in target_points) / max(v[2] for v in source_points)
    for part in garments:
        if part['geoset'] not in (1202, 1302):
            continue
        for index in {v for tri in part['triangles'] for v in tri}:
            x, y, z = source_points[index]
            fitted[index]['position'] = [x * scale, y * scale * .7, z * scale]
    regions = body_uvs(model, body, collar)
    frozen = STAGE / 'frozen-upper-uv.json'
    if frozen.exists():
        previous = p.load_json(frozen)
        for i, tri in enumerate(body):
            key = ','.join(map(str, tri))
            if key in previous:
                regions[i * 3:i * 3 + 3] = previous[key]
    save(STAGE / 'male-body-work.json', {'sex': 'male', 'target': [equipment.vertex_record(model, i)
        for i in range(model.vertex_count)], 'body': body, 'original_only': original, 'donor': fitted,
        'donor_body': donor_body, 'equipment': garments, 'skin_sources': sources,
        'region_uvs': gnoll_uvs(model, body, regions),
        'fit_surface': fit_surface, 'fit_boots': True})
    print('EXPORTED Gnoll body and', len(garments), 'garment geosets', flush=True)


def prepare():
    """Retain authored anatomy; fit player garments and select cosmetics in separate geoset groups."""
    import sethrak_equipment_repair as equipment
    import sethrak_animation_pack as animations
    from gnoll_texture_repair import clothing_catalog, restore_fur
    model = parse_m2((STAGE / 'animated.m2').read_bytes())
    original = copy.deepcopy(model)
    skin = parse_skin((ROOT / 'converted/gnoll200.skin').read_bytes())
    donor = parse_m2((STAGE / 'donors/worgen.m2').read_bytes())
    donor_skin = parse_skin((STAGE / 'donors/worgen00.skin').read_bytes())
    work = p.load_json(STAGE / 'male-body-work.json')
    fit = p.load_json(STAGE / 'male-equipment-fit.json')
    for index, position in fit.items():
        work['donor'][int(index)]['position'] = position
    uvs = p.load_json(STAGE / 'male-body-uv.json')
    uv_by_tri = {tuple(tri): uvs[i * 3:i * 3 + 3] for i, tri in enumerate(work['body'])}
    vertices, meshes = bytearray(model.vertices), []
    body_texture = len(model.textures)
    model.textures.append({'type': 1, 'flags': 0, 'filename': ''})
    combo = len(model.texture_combos)
    model.texture_combos.append(body_texture)
    material = len(model.materials)
    model.materials.append({'flags': 0, 'blending_mode': 0})
    body_batch = struct.pack('<12H', 0, 0, 0, 0, 65535, material, 0, 1, combo, 0, 0, 0)
    feet = equipment.descendants(model, model.key_bone_lookup[59])
    feet |= equipment.descendants(model, model.key_bone_lookup[60])
    hands = equipment.descendants(model, model.bones[model.key_bone_lookup[8]]['parent_bone'])
    hands |= equipment.descendants(model, model.bones[model.key_bone_lookup[13]]['parent_bone'])
    legs = equipment.descendants(model, model.key_bone_lookup[55])
    legs |= equipment.descendants(model, model.key_bone_lookup[56])

    def dominant(tri, bones):
        return sum(model.vertices[v * 48 + 12 + s] for v in tri for s in range(4)
                   if model.vertices[v * 48 + 16 + s] in bones) >= 300

    remapped = {}
    for index, row in enumerate(skin.submeshes):
        batches = [b for b in skin.batches if visual.u16(b, 4) == index]
        geo = visual.u16(row, 0)
        parts = {}
        for tri in triangles(skin, row):
            if tri in uv_by_tri:
                group = 0  # Equipment selectors must never remove the authored hands, calves or pelvis.
                mapped = []
                for vertex, uv in zip(tri, uv_by_tri[tri], strict=True):
                    key = (vertex, *[round(v, 7) for v in uv])
                    if key not in remapped:
                        data = bytearray(model.vertices[vertex * 48:(vertex + 1) * 48])
                        struct.pack_into('<2f', data, 32, *uv)
                        remapped[key] = len(vertices) // 48
                        vertices.extend(data)
                    mapped.append(remapped[key])
                parts.setdefault((group, True), []).append(tuple(mapped))
            else:
                # ChrRaces BARE_FEET keeps Gnoll's authored paws; standard boots supply fitted calf garments.
                group = 3000 + geo if geo else 0
                parts.setdefault((group, False), []).append(tri)
        for (group, player), tris in parts.items():
            meshes.append({'row': row, 'batches': [body_batch] if player else batches,
                           'geoset': group, 'triangles': tris, 'family': 'body'})
    # Paint retained anatomy; borrowed cuff/boot surfaces cannot follow this NPC armature.
    cloth_surfaces(model, vertices, meshes, skin, body_batch)
    cape_texture = len(model.textures)
    model.textures.append({'type': 2, 'flags': 0, 'filename': ''})
    cape_combo = len(model.texture_combos)
    model.texture_combos.append(cape_texture)
    cape_material = len(model.materials)
    model.materials.append({'flags': 4, 'blending_mode': 1})
    batch = struct.pack('<12H', 16, 0, 0, 0, 65535, cape_material, 0, 1, cape_combo, 0, 0, 0)
    cape_surfaces(model, vertices, meshes, skin, donor, donor_skin, batch)
    # Worgen shoulder-anchor scales repeat 1.5 with exporter float noise below 0.000004.
    # Normalize only those static scale keys; retain real animation and the immutable donor unchanged.
    socket_donor = copy.deepcopy(donor)
    for identifier in (5, 6):
        anchor = next(a for a in socket_donor.attachments if a['id'] == identifier)
        track = socket_donor.bones[anchor['bone']]['scale']
        reference = next(values[0] for values in track.values if values)
        if any(abs(x - y) > .00001 for values in track.values for value in values
               for x, y in zip(reference, value, strict=True)):
            raise ValueError('Worgen shoulder frame has real scale animation')
        reference = tuple(value * .7 for value in reference)
        track.values = [[reference for _ in values] for values in track.values]
    equipment.repair_attachment_points(model, socket_donor, socket_donor, arm_bones(model, donor))
    model.vertices, model.vertex_count = bytes(vertices), len(vertices) // 48
    model.num_skin_profiles = 1
    for texture in model.textures:
        if texture['type'] == 0:
            texture['filename'] = PREFIX + 'textures\\3886653.blp'
    compact = equipment.packed_skin(model, meshes)
    compact, _ = restore_fur(model, compact, original, skin)
    from creature_clothing_repair import redirect
    redirect(model)
    model.replacable_texture_lookup = [65535] * 16
    for i, texture in enumerate(model.textures):
        if texture['type']:
            model.replacable_texture_lookup[texture['type']] = i
    output = local(STAGE / 'assets', MODEL)
    output.parent.mkdir(parents=True, exist_ok=True)
    data = write_md20(model)
    output.write_bytes(data)
    output.with_name(output.stem + '00.skin').write_bytes(write_skin(compact))
    animations.check_model(parse_m2(data), data)
    # Exact source positions, weights and normals survive even where clothing needs new UVs.
    assert {original.vertices[i:i + 32] for i in range(0, len(original.vertices), 48)} <= {
        model.vertices[i:i + 32] for i in range(0, len(model.vertices), 48)}
    for fid in (*BODY_IDS, *ARMOR_IDS, 3886653):
        path = local(STAGE / 'assets', PREFIX + 'textures\\' + str(fid) + '.blp')
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((ROOT / 'converted' / (str(fid) + '.blp')).read_bytes())
    records = []

    def record(kind, target, value, selectors=(), key=''):
        assert len(selectors) <= 3 and len(key.encode()) < 128
        selected = [i | j << 16 for i, j in selectors]
        records.append(struct.pack('<7I', 0, kind, target, value,
                       *(selected + [0xffffffff] * (3 - len(selected)))) + key.encode().ljust(128, b'\0'))

    for i, fid in enumerate(BODY_IDS):
        record(1, 11, 0, [(0, i)], PREFIX + 'textures\\' + str(fid) + '.blp')
    for i, fid in enumerate(ARMOR_IDS):
        record(1, 12, 0, [(5, i)], PREFIX + 'textures\\' + str(fid) + '.blp')
    for option, values in enumerate(CHOICES):
        if option in (0, 5):
            continue
        for choice, geo in enumerate(values):
            record(0, 30 + geo // 100, 3000 + geo, [(option, choice)])
    catalog, bank = clothing_catalog(struct.pack('<3I', 0x314D4845, 1, len(records)) + b''.join(records))
    (STAGE / 'EsteriaGnoll.bin').write_bytes(catalog)
    (STAGE / 'EsteriaGnollTextures.bin').write_bytes(bank)
    for i in range(len(BODY_IDS)):
        Image.new('RGBA', (512, 512)).save(STAGE / ('male-player-skin-' + str(i) + '.png'))
    save(STAGE / 'model.json', {'vertices': model.vertex_count, 'skin_vertices': len(compact.vertices),
        'indices': len(compact.indices), 'meshes': len(compact.submeshes), 'sequences': len(model.sequences),
        'events': len(model.events), 'attachments': [a['id'] for a in model.attachments],
        'geosets': sorted({visual.u16(r, 0) for r in compact.submeshes}),
        'maximum_palette': max(visual.u16(r, 12) for r in compact.submeshes)})
    print('PREPARED Gnoll geometry/materials', model.vertex_count, len(compact.indices), flush=True)


def preview():
    """Export the exact staged meshes/materials for an offline Blender preview and creator portrait."""
    import sethrak_equipment_repair as equipment
    model = parse_m2(local(STAGE / 'assets', MODEL).read_bytes())
    skin = parse_skin(local(STAGE / 'assets', MODEL[:-3] + '00.skin').read_bytes())
    textures = {}
    for fid in (BODY_IDS[0], ARMOR_IDS[0], 3886653):
        art = Blp.parse(raw(fid)).decode_level(0)
        path = STAGE / 'preview' / (str(fid) + '.png')
        path.parent.mkdir(parents=True, exist_ok=True)
        Image.frombytes('RGBA', (art.width, art.height), bytes(art.data)).save(path)
        textures[fid] = str(path)
    source_textures = {0: textures[3886653], 11: textures[BODY_IDS[0]], 12: textures[ARMOR_IDS[0]],
                       1: str(STAGE / 'male-player-skin-0.png'), 14: str(STAGE / 'male-player-skin-0.png')}
    selected = {0, 401, 501, 1301}
    selected.update(3000 + choices[0] for i, choices in enumerate(CHOICES) if i not in (0, 5))
    # Preview a visibly dressed native outfit while retaining the default body-feature selections.
    selected.difference_update((3500, 3600, 4100, 4200))
    selected.update((3502, 3602, 4102, 4202))
    parts = []
    for index, row in enumerate(skin.submeshes):
        geo = visual.u16(row, 0)
        if geo not in selected:
            continue
        batch = next(b for b in skin.batches if visual.u16(b, 4) == index)
        slot = model.textures[model.texture_combos[visual.u16(batch, 16)]]['type']
        parts.append({'geoset': geo, 'triangles': triangles(skin, row), 'texture': source_textures[slot]})
    save(STAGE / 'preview/model.json', {'vertices': [equipment.vertex_record(model, i)
        for i in range(model.vertex_count)], 'meshes': parts})


def preview_equipment():
    """Reuse the prior garment renderer with the actual installed shirt, plate and robe texture components."""
    import sethrak_equipment_repair as equipment
    regions = ('ArmUpperTexture', 'ArmLowerTexture', 'HandTexture', 'TorsoUpperTexture',
               'TorsoLowerTexture', 'LegUpperTexture', 'LegLowerTexture', 'FootTexture')
    rects = ((0, 0, 256, 128), (0, 128, 256, 256), (0, 256, 256, 320), (256, 0, 512, 128),
             (256, 128, 512, 192), (256, 192, 512, 320), (256, 320, 512, 448), (256, 448, 512, 512))
    files = p.ClientFiles(str(p.CLIENT_DEFAULT / 'Data'), 'enUS')
    gear = {}
    try:
        table = p.RawWdbc(files.find(p.DBC_ROOT + 'ItemDisplayInfo.dbc')[0])
        displays = {p._value(r, 0): r for r in table.records}
        for kind, ids in (('shirt', (18924,)), ('plate', (25749, 24513)), ('robe', (15820,))):
            atlas = Image.open(STAGE / 'male-player-skin-0.png').convert('RGBA')
            for display in ids:
                row = displays[display]
                for field, directory, rect in zip(range(15, 23), regions, rects, strict=True):
                    stem = p._string(table.strings, p._value(row, field * 4)).decode()
                    if not stem:
                        continue
                    for suffix in ('_U', '_M', '', '_F'):
                        key = 'Item\\TextureComponents\\' + directory + '\\' + stem + suffix + '.blp'
                        try:
                            data = files.find(key)[0]
                            break
                        except FileNotFoundError:
                            continue
                    else:
                        raise FileNotFoundError('Gnoll preview item component absent: ' + stem)
                    image = Blp.parse(data).decode_level(0)
                    art = Image.frombytes('RGBA', (image.width, image.height), bytes(image.data))
                    atlas.alpha_composite(art.resize((rect[2] - rect[0], rect[3] - rect[1]),
                                                     Image.Resampling.LANCZOS), (rect[0], rect[1]))
            path = STAGE / ('male-preview-' + kind + '.png')
            atlas.save(path)
            gear[kind] = str(path)
    finally:
        files.close()
    model = parse_m2(local(STAGE / 'assets', MODEL).read_bytes())
    skin = parse_skin(local(STAGE / 'assets', MODEL[:-3] + '00.skin').read_bytes())
    source = {11: STAGE / 'preview' / (str(BODY_IDS[0]) + '.png'),
              12: STAGE / 'preview' / (str(ARMOR_IDS[0]) + '.png'),
              0: STAGE / 'preview/3886653.png'}
    textures = {str(i): str(source[t['type']]) for i, t in enumerate(model.textures) if t['type'] in source}
    cosmetic = {3000 + choices[0] for i, choices in enumerate(CHOICES) if i not in (0, 5)}
    meshes = []
    for index, row in enumerate(skin.submeshes):
        geo = visual.u16(row, 0)
        if geo >= 3000 and geo not in cosmetic:
            continue
        batch = next(b for b in skin.batches if visual.u16(b, 4) == index)
        texture = model.texture_combos[visual.u16(batch, 16)]
        meshes.append({'geoset': 0 if geo >= 3000 else geo, 'native_group': geo // 100 if geo >= 3000 else 0,
                       'triangles': triangles(skin, row), 'texture': texture,
                       'texture_type': 1 if model.textures[texture]['type'] == 14 else model.textures[texture]['type']})
    save(STAGE / 'male-preview.json', {'vertices': [equipment.vertex_record(model, i)
        for i in range(model.vertex_count)], 'meshes': meshes, 'textures': textures,
        'base_atlas': str(STAGE / 'male-player-skin-0.png'), 'gear_textures': gear})


def appearance_catalog(original):
    magic, version, count = struct.unpack_from('<3I', original)
    stride = 12 + 16 * 144
    assert (magic, version) == (0x50504145, 2) and len(original) == 12 + count * stride
    assert all(struct.unpack_from('<I', original, 12 + i * stride)[0] != RACE for i in range(count))
    offsets = (0x28, 0x2C, 0x34, 0x24, 0x30)
    row = bytearray(struct.pack('<3I', RACE, 0, len(LABELS)))
    for field, n, factor in codec()['descriptors']:
        row.extend(struct.pack('<4I', offsets[field], n, factor, 0) + bytes(128))
    row.extend(bytes((16 - len(LABELS)) * 144))
    return struct.pack('<3I', magic, version, count + 1) + original[12:] + row


def tables(baseline):
    import sethrak_race_pack as s
    import ogre_furbolg_race_pack as o
    result = dict(baseline)
    spec = manifest()
    p._ensure_id_free(result['ChrRaces'], 'ChrRaces', {RACE})
    result['ChrRaces'] = p._merge_chr_races(result['ChrRaces'], spec, allocation())
    table = p.RawWdbc(result['ChrRaces'])
    pool, rows = bytearray(table.strings), []
    for row in table.records:
        if p._value(row, 0) == RACE:
            for field, value in ((1, 14), (2, 2), (7, 1), (12, 0), (13, 1), (68, 0)):
                row = p._replace(row, field * 4, 4, value)
            row = p._set_string(row, 6, pool, 'Gn')
        rows.append(row)
    result['ChrRaces'] = table.build(rows, bytes(pool))
    displays = p.RawWdbc(result['CreatureDisplayInfo'])
    source_display = next(r for r in displays.records if p._value(r, 0) == 501)
    model_id = p._value(source_display, 4)
    models = p.RawWdbc(result['CreatureModelData'])
    model_row = next(r for r in models.records if p._value(r, 0) == model_id)
    pool = bytearray(models.strings)
    model_row = p._clone_strings('CreatureModelData', models, model_row, pool)
    model_row = p._replace(model_row, 0, 4, 120068)
    # Player rendering tests bit4 before creating CCharComponent; 0x800 selects the installed HD compositor.
    model_row = p._replace(model_row, 4, 4, p._value(model_row, 4) | 0x804)
    model_row = p._set_string(model_row, 2, pool, MODEL)
    # Exact modern Gnoll collision dimensions; its NPC display's 1.5 scale is not inherited.
    model_row = model_row[:16] + struct.pack('<f', 1.0) + model_row[20:]
    model_row = model_row[:56] + struct.pack('<2f', .6111111044883728, 2.031277894973755) + model_row[64:]
    result['CreatureModelData'] = s.append_rows(result['CreatureModelData'], 'CreatureModelData',
                                               [model_row], pool)
    pool = bytearray(displays.strings)
    display = p._clone_strings('CreatureDisplayInfo', displays, source_display, pool)
    for offset, value in ((0, 60059), (4, 120068), (12, 0), (28, 0), (32, 0), (36, 0)):
        display = p._replace(display, offset, 4, value)
    display = display[:16] + struct.pack('<f', 1.0) + display[20:]
    result['CreatureDisplayInfo'] = s.append_rows(result['CreatureDisplayInfo'], 'CreatureDisplayInfo',
                                                 [display], pool)
    result['CharBaseInfo'] = p._build_char_base_info(result['CharBaseInfo'], spec)
    outfits = p.RawWdbc(result['CharStartOutfit'])
    donors = {}
    for row in sorted(outfits.records, key=lambda r: p._value(r, 0)):
        if row[4] == 2 and row[5] in spec['classes'] and row[6] == 0 and row[7] == 0:
            donors[row[5]] = row
    assert len(donors) == 10
    rows = [p._replace(p._replace(row, 0, 4, 22060 + i), 4, 1, RACE)
            for i, row in enumerate(donors.values())]
    result['CharStartOutfit'] = s.append_rows(result['CharStartOutfit'], 'CharStartOutfit', rows)
    names = p.RawWdbc(result['NameGen'])
    male_names = names.build([r for r in names.records if p._value(r, 8) != 2 or p._value(r, 12) == 0])
    generated = p._clone_namegen(male_names, spec, allocation())
    additions = [r for r in p.RawWdbc(generated).records if p._value(r, 8) == RACE]
    result['NameGen'] = s.append_rows(result['NameGen'], 'NameGen', additions, p.RawWdbc(generated).strings)
    sections = p.RawWdbc(result['CharSections'])
    pool, added, hair, facial, barber = bytearray(sections.strings), [], [], [], []
    capacities = codec()['capacities']
    body = PREFIX + 'textures\\' + str(BODY_IDS[0]) + '.blp'

    def section(kind, style, color):
        row = struct.pack('<10I', 1102000 + len(added), RACE, 0, kind, 0, 0, 0,
                          1 if kind == 1 else 17, style, color)
        if kind == 0:
            row = p._set_string(row, 4, pool, body)
        added.append(row)

    for color in range(capacities[0]):
        for kind in (0, 1, 4):
            section(kind, 0, color)
    for face in range(capacities[1]):
        for color in range(capacities[0]):
            if face:
                section(1, face, color)
    for style in range(capacities[2]):
        for color in range(capacities[3]):
            section(3, style, color)
        hair.append(struct.pack('<6I', 1102000 + style, RACE, 0, style, 0, 1))
    for style in range(capacities[4]):
        for color in range(capacities[3]):
            section(2, style, color)
        facial.append(struct.pack('<8I', RACE, 0, style, 0, 0, 0, 0, 0))
    if len(added) > RANGES['CharSections'][1] - RANGES['CharSections'][0] + 1:
        raise ValueError('Gnoll section allocation is too small')
    source = p.RawWdbc(result['BarberShopStyle'])
    for kind, field in ((0, 2), (2, 4), (3, 0)):
        donor = next(r for r in source.records if p._value(r, 4) == kind)
        for value in range(capacities[field]):
            row = donor
            for offset, n in ((0, 1102000 + len(barber)), (148, RACE), (152, 0), (156, value)):
                row = p._replace(row, offset, 4, n)
            barber.append(row)
    for name, new, strings in (('CharSections', added, pool), ('CharHairGeosets', hair, None),
                               ('CharacterFacialHairStyles', facial, None), ('BarberShopStyle', barber, None)):
        result[name] = s.append_rows(result[name], name, new, strings)
    result['CharSections'] = o.order_charsections_entry(p.DBC_ROOT + 'CharSections.dbc', result['CharSections'])
    return result


def male_only_glue(text):
    """Enforce Gnoll's body type after creator refreshes, using its exact model token."""
    anchor = 'target.raceID >= 55 and target.raceID <= 59 then'
    replacement = '((target.raceID >= 55 and target.raceID <= 59) or target.raceID == 63) then'
    assert text.count(anchor) == 1
    text = text.replace(anchor, replacement)
    marker = '-- Gnoll has one authored playable body; refreshes must not restore the female button.'
    assert marker not in text
    return text + '\n' + marker + '''
local function GnollRefreshGender()
    local _, fileString = GetNameForRace();
    local gnoll = fileString and strupper(fileString) == "GNOLLHORDE";
    if gnoll then
        CharacterCreateGenderButtonFemale:Hide();
        CharacterCreateGenderButtonFemale:Disable();
        if GetSelectedSex() ~= SEX_MALE then SetCharacterGender(SEX_MALE); end
    else
        CharacterCreateGenderButtonFemale:Enable();
    end
end
local gnollOriginalCheckedStates = CharacterCreate_UpdateButtonCheckedStates;
function CharacterCreate_UpdateButtonCheckedStates(...)
    gnollOriginalCheckedStates(...);
    GnollRefreshGender();
end
local gnollOriginalResetState = CharacterCreate_ResetState;
function CharacterCreate_ResetState(...)
    gnollOriginalResetState(...);
    GnollRefreshGender();
end
'''


def glue(original):
    import ogre_furbolg_race_pack as o
    from luaparser import ast
    result = {name: data.decode('utf-8-sig') for name, data in original.items()}

    def insert(name, anchor, payload):
        result[name] = o._insert_once(result[name], anchor, payload, 'Gnoll ' + name)

    insert('CharacterInfo.lua', 'local EXACT_RACE_DATA = {\n',
           '    [63] = {glueString="GNOLLHORDE", name="Gnoll", faction="Horde", fileString="GnollHorde"},\n')
    result['CharacterInfo.lua'] += '\nRaceInfoByFileString.GNOLLHORDE = {Name="Gnoll", '
    result['CharacterInfo.lua'] += 'Description="These resourceful scavengers have joined the Horde."};\n'
    insert('CharacterCreate.lua', 'RACE_ICON_TEXTURES = {\n',
           '    ["GNOLLHORDE_MALE"] = "Interface\\\\Glues\\\\CharacterCreate\\\\UI-CharacterCreate-GnollHordeMale",\n')
    insert('CharacterCreate.lua', 'local RACE_BACKGROUND_KEYS = {\n', '        ["GNOLLHORDE"] = "ORC",\n')
    result['CharacterCreate.lua'] = result['CharacterCreate.lua'].replace(
        'CharacterCreate.selectedRaceID == 62',
        '(CharacterCreate.selectedRaceID == 62 or CharacterCreate.selectedRaceID == 63)')
    result['CharacterCreate.lua'] = result['CharacterCreate.lua'].replace(
        'CharacterCreate.selectedRaceID >= 55 and CharacterCreate.selectedRaceID <= 59',
        '((CharacterCreate.selectedRaceID >= 55 and CharacterCreate.selectedRaceID <= 59) '
        'or CharacterCreate.selectedRaceID == 63)')
    result['CharacterCreate.lua'] = result['CharacterCreate.lua'].replace(
        'local maleOnly = race and race >= 55 and race <= 59;',
        'local maleOnly = race and ((race >= 55 and race <= 59) or race == 63);')
    result['CharacterCreate.lua'] = male_only_glue(result['CharacterCreate.lua'])
    result['GlueStrings.lua'] += '\nGNOLLHORDE="Gnoll"; GNOLLHORDE_MALE=GNOLLHORDE;\n'
    insert('GlueParent.lua', '    local hordeRaces = {\n', '        ["GNOLLHORDE"] = true,\n')
    result['GlueParent.lua'] += ('\nCharModelFogInfo.GNOLLHORDE=CharModelFogInfo.ORC;\n'
        'CharModelGlowInfo.GNOLLHORDE=CharModelGlowInfo.ORC;\n'
        'GlueAmbienceTracks.GNOLLHORDE=GlueAmbienceTracks.ORC;\n')
    # Horde backgrounds already take the common Horde branch; GlueParent resolves the exact Gnoll token.
    insert('ECS_Schema.lua', 'S.RaceOverride = {\n',
           '    [63] = {name="Gnoll", faction=2, artKey="GnollHorde"},\n')
    insert('ECS_Schema.lua', 'S.RaceByModelKey = {\n',
           '    {"GNOLLHORDE", {name="Gnoll", faction=2, artKey="GnollHorde"}},\n')
    insert('ECS_Schema.lua', 'S.PortraitArtKeys = {\n', '    GnollHorde=true,\n')
    result['ECS_Integrate.lua'] = result['ECS_Integrate.lua'].replace('or race == 62', 'or race == 62 or race == 63')
    for text in result.values():
        ast.parse(text)
    return {name: text.encode() for name, text in result.items()}


def stage():
    import sethrak_race_pack as s
    import ogre_furbolg_race_pack as o
    import race_portrait_pack as portraits
    client = p.CLIENT_DEFAULT
    if (client / ASSET_ARCHIVE).exists():
        raise FileExistsError('Gnoll archive slot is already in use')
    files = p.ClientFiles(str(client / 'Data'), 'enUS')
    try:
        baseline = {name: files.find(p.DBC_ROOT + name + '.dbc')[0] for name in s.TABLES}
        original_glue = {name: files.find(p.GLUE_ROOT + name)[0] for name in s.GLUE}
        output = tables(baseline)
        patched = glue(original_glue)
        template = files.find(portraits.ICON_TEMPLATE_ENTRY)[0]
        ring = portraits.ring_layer(portraits.decode_client_blp(files.find(portraits.RING_ENTRY)[0]))
    finally:
        files.close()
    assets = {'\\'.join(path.relative_to(STAGE / 'assets').parts): path.read_bytes()
              for path in (STAGE / 'assets').rglob('*') if path.is_file()}
    art = Image.open(STAGE / 'preview/portrait.png').convert('RGBA').resize((64, 64), Image.Resampling.LANCZOS)
    art.putalpha(portraits.circular_mask())
    plain = portraits.encode_portrait(art, template)
    icon = portraits.encode_portrait(portraits.compose_race_icon(art, ring), template)
    assets[portraits.CREATOR_ICON_ROOT + 'UI-CharacterCreate-GnollHordeMale.blp'] = icon
    stem = portraits.CHARACTER_FRAME_ROOT + 'TemporaryPortrait-Male-GnollHorde'
    assets[stem] = assets[stem + '.blp'] = plain
    assets['Interface\\Glues\\CharacterSelect\\ECS-Portrait-GnollHordeMale.blp'] = plain
    for key, data in assets.items():
        path = local(STAGE / 'assets', key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    before = client / 'EsteriaAppearance.bin'
    native = appearance_catalog(before.read_bytes())
    (STAGE / before.name).write_bytes(native)
    geometry = (client / 'EsteriaAppearanceGeometry.bin').read_bytes()
    magic, version, count = struct.unpack_from('<3I', geometry)
    assert (magic, version) == (0x4D474145, 1)
    addition = MODEL.encode().ljust(128, b'\0') + struct.pack('<I', len(assets[MODEL[:-3] + '00.skin']))
    addition += assets[MODEL[:-3] + '00.skin']
    (STAGE / 'EsteriaAppearanceGeometry.bin').write_bytes(
        struct.pack('<3I', magic, version, count + 1) + geometry[12:] + addition)
    for name, data in {**{n + '.dbc': b for n, b in baseline.items()}, **original_glue,
                       'EsteriaAppearance.bin': before.read_bytes(), 'EsteriaAppearanceGeometry.bin': geometry}.items():
        path = STAGE / 'baseline' / name
        path.parent.mkdir(parents=True, exist_ok=True)
        c.immutable(path, data)
    for folder, values in (('client-dbc', output), ('glue', patched)):
        for name, data in values.items():
            path = STAGE / folder / (name + '.dbc' if folder == 'client-dbc' else name)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
    for name in s.SERVER_TABLES:
        base = (p.SERVER_DBC_ROOT / (name + '.dbc')).read_bytes()
        source, table = p.RawWdbc(output[name]), p.RawWdbc(base)
        new = [r for r in source.records if p._value(r, 0) in RANGES[name].values()] \
            if name in ('CreatureModelData', 'CreatureDisplayInfo') \
            else p._table_rows_for_race(output[name], name, RACE)
        p._ensure_id_free(base, name, {p._value(r, 0) for r in new})
        pool = bytearray(table.strings)
        data = table.build(list(table.records) + [p._clone_strings(name, source, r, pool) for r in new], bytes(pool))
        path = STAGE / 'server/dbc' / (name + '.dbc')
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        c.immutable(STAGE / 'baseline-server' / path.name, base)
    migration = o.build_sql({'name': 'Gnoll', 'race_id': RACE, 'faction': 'horde', 'donor_start_race': 2,
                             'donor_totem_race': 2}).replace('ogre_furbolg_race_pack.py', 'gnoll_race_pack.py')
    migration += o.CHRRACES_TEMPLATE.format(race=RACE, faction_template=2, male_display=60059, female_display=0,
        prefix='Gn', base_language=1, file_string=TOKEN, alliance=1, name='Gnoll')
    (STAGE / 'gnoll.sql').write_text(migration.rstrip() + '\n', encoding='utf-8', newline='\n')
    pending = p.ROOT / 'data/sql/updates/pending_db_world/rev_20261006230000000.sql'
    c.immutable(pending, (STAGE / 'gnoll.sql').read_bytes())
    storm = p.Storm(p.DLL_DEFAULT)
    asset_archive = STAGE / 'client' / ASSET_ARCHIVE
    asset_archive.parent.mkdir(parents=True, exist_ok=True)
    if asset_archive.exists():
        handle = storm.open_archive(asset_archive)
        try:
            differs = any(storm.read(handle, key) != data for key, data in assets.items())
        finally:
            storm.dll.SFileCloseArchive(handle)
        if differs:
            temporary = asset_archive.with_name('gnoll-' + uuid.uuid4().hex + '.MPQ')
            storm.create_archive(temporary, assets)
            os.replace(temporary, asset_archive)
    else:
        storm.create_archive(asset_archive, assets)
    replacements = {p.DBC_ROOT + n + '.dbc': b for n, b in output.items()}
    replacements.update({p.GLUE_ROOT + n: b for n, b in patched.items()})
    report = {'status': 'staged_build_and_deployment_required', 'race': RACE, 'client': str(client),
              'source_pin': p.load_json(CACHE / 'source-pin.json'), 'exe_sha256': p.sha256(client / 'Wow.exe'),
              'archives': {str(ASSET_ARCHIVE): p.sha256(asset_archive)}, 'archive_baselines': {},
              'assets': {k: hashlib.sha256(v).hexdigest() for k, v in assets.items()},
              'migration': str(pending), 'live_install_performed': False}
    for relative in (p.GLOBAL_ARCHIVE_REL, p.LOCALE_ARCHIVE_REL):
        live, target = client / relative, STAGE / 'client' / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        before_hash = p.sha256(live)
        snapshot = STAGE / 'baseline-archives' / relative
        snapshot.parent.mkdir(parents=True, exist_ok=True)
        if not snapshot.exists():
            shutil.copy2(live, snapshot)
        if p.sha256(snapshot) != before_hash or p.sha256(live) != before_hash:
            raise ValueError('Archive changed while taking the read-only merge snapshot')
        print('STAGING', relative, flush=True)
        o.rebuild_archive_replacing(storm, snapshot, target, replacements, compress=True)
        assert p.sha256(live) == before_hash
        report['archive_baselines'][str(relative)] = before_hash
        report['archives'][str(relative)] = p.sha256(target)
    save(STAGE / 'report.json', report)
    print('STAGED Horde Gnoll client/server pack', STAGE, flush=True)


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8', newline='\n')


def local(root, key):
    return root.joinpath(*PureWindowsPath(key).parts)


def arm_bones(model, donor):
    """Match actual arm chains where NPC/player forearm names differ."""
    result = {}
    for key in (8, 13):
        source, target = donor.key_bone_lookup[key], model.key_bone_lookup[key]
        for _ in range(5):
            if source < 0 or target < 0:
                break
            result[source] = target
            source, target = donor.bones[source]['parent_bone'], model.bones[target]['parent_bone']
    return result


def gnoll_uvs(model, triangles, initial):
    """Keep upper-body layout; use Wrath's mirrored front/back leg atlas on the complete lower anatomy."""
    from sethrak_body_regions import children, mirrored_u
    arms = children(model, model.key_bone_lookup[0]) | children(model, model.key_bone_lookup[1])
    waist = 1.008  # Top of the authored pelvis801, rather than the lower animation hip pivot.
    result = []
    for n, tri in enumerate(triangles):
        arm = sum(model.vertices[v * 48 + 12 + i] for v in tri for i in range(4)
                  if model.vertices[v * 48 + 16 + i] in arms) >= 300
        for j, vertex in enumerate(tri):
            x, y, z = struct.unpack_from('<3f', model.vertices, vertex * 48)
            uv = initial[n * 3 + j]
            if z < waist and not arm:
                thigh, knee, ankle = (model.key_bone_lookup[k] for k in
                                     ((56, 58, 59) if y >= 0 else (55, 57, 60)))
                a, b = (model.bones[k]['pivot'] for k in ((thigh, knee) if z >= .474 else (knee, ankle)))
                t = min(1, max(0, (a[2] - z) / max(.001, a[2] - b[2])))
                cx, cy = (a[i] + t * (b[i] - a[i]) for i in (0, 1))
                v = .375 + (waist - z) / (waist - .474) * .25 if z >= .474 \
                    else .625 + (.474 - z) / (.474 - .139) * .25
                uv = [mirrored_u(math.atan2(y - cy, x - cx)), min(.875, max(.375, v))]
            result.append(uv)
    return result


def cloth_surfaces(model, vertices, meshes, skin, batch):
    """Fit a continuous robe and belt directly to Gnoll's hips; preserve the original body underneath."""
    hip = model.bones[model.key_bone_lookup[55]]['parent_bone']
    row = bytearray(skin.submeshes[0])
    visual.patch16(row, 18, hip)

    def tube(geoset, rings):
        first = len(vertices) // 48
        sides = 24
        for z, rx, ry, v in rings:
            for i in range(sides + 1):
                angle = -math.pi + i * 2 * math.pi / sides
                data = bytearray(48)
                struct.pack_into('<3f', data, 0, .026 + rx * math.cos(angle), ry * math.sin(angle), z)
                data[12], data[16] = 255, hip
                struct.pack_into('<3f', data, 20, math.cos(angle), math.sin(angle), 0)
                struct.pack_into('<2f', data, 32, .5035 + abs(angle) / math.pi * .491, v)
                vertices.extend(data)
        tris = []
        for ring in range(len(rings) - 1):
            for i in range(sides):
                a = first + ring * (sides + 1) + i
                b = a + sides + 1
                tris.extend(((a, a + 1, b), (a + 1, b + 1, b)))
        meshes.append({'row': bytes(row), 'batches': [batch], 'geoset': geoset, 'triangles': tris,
                       'family': 'armor'})

    tube(1302, ((1.01, .235, .27, .375), (.82, .26, .29, .47), (.55, .29, .32, .62),
                (.30, .32, .35, .77), (.16, .34, .37, .875)))
    # Equipped belts paint the torso-lower atlas; another belt ring creates a floating strip.


def cape_body_triangles(model, skin):
    from sethrak_equipment_repair import descendants
    excluded = descendants(model, model.key_bone_lookup[0]) | descendants(model, model.key_bone_lookup[1])
    excluded |= descendants(model, model.key_bone_lookup[41])
    return [tri for row in skin.submeshes if visual.u16(row, 0) in (0, 701, 801, 1001)
            for tri in triangles(skin, row) if sum(
                model.vertices[v * 48 + 12 + s] for v in tri for s in range(4)
                if model.vertices[v * 48 + 16 + s] in excluded) < 384]


def cape_rig(model, skin, donor, donor_skin):
    """Fit in the actual standing pose; append only three cloth bones, rooted at the upper spine."""
    import numpy as np
    import creature_animation_repair as animation
    CAPE_BONES = (18, 28, 37)
    parent = model.key_bone_lookup[53]
    authored = copy.deepcopy(model)
    authored.bones = authored.bones[:parent + 1]
    reference = animation.pose_matrices(model, 0, 0)
    points = animation.posed_vertices(model, reference)
    shoulders = [(reference[model.key_bone_lookup[k]] @ np.array(
        (*model.bones[model.key_bone_lookup[k]]['pivot'], 1)))[:3] for k in (0, 1)]
    center_y = sum(point[1] for point in shoulders) / 2
    top = sum(point[2] for point in shoulders) / 2 + .22
    used = {v for tri in cape_body_triangles(model, skin) for v in tri}
    rear = [points[v, 0] for v in used if abs(points[v, 2] - top) < .14
            and abs(points[v, 1] - center_y) < .24]
    assert rear
    back = min(rear)
    anchor_triangles = []
    for tri in cape_body_triangles(model, skin):
        a, b, c = points[list(tri)]
        determinant = (b[2] - c[2]) * (a[1] - c[1]) + (c[1] - b[1]) * (a[2] - c[2])
        if abs(determinant) < .000001:
            continue
        u = ((b[2] - c[2]) * (center_y - c[1]) + (c[1] - b[1]) * (top - c[2])) / determinant
        v = ((c[2] - a[2]) * (center_y - c[1]) + (a[1] - c[1]) * (top - c[2])) / determinant
        barycentric = np.array((u, v, 1 - u - v))
        if min(barycentric) >= 0:
            anchor_triangles.append((float(barycentric @ points[list(tri), 0]), tri, barycentric))
    assert anchor_triangles
    back, anchor_tri, anchor_weights = min(anchor_triangles, key=lambda item: item[0])
    anchor_bind = np.column_stack((np.ndarray((model.vertex_count, 3), '<f4', model.vertices, strides=(48, 4)),
                                   np.ones(model.vertex_count)))[list(anchor_tri)]
    anchor_skin = np.ndarray((model.vertex_count, 4), 'u1', model.vertices, offset=12,
                             strides=(48, 1))[list(anchor_tri)] / 255
    anchor_bones = np.ndarray((model.vertex_count, 4), 'u1', model.vertices, offset=16,
                              strides=(48, 1))[list(anchor_tri)]
    authored.bones = model.bones[:max(parent, int(anchor_bones.max())) + 1]
    inverse = np.linalg.inv(reference[parent])
    cape = {v for row in donor_skin.submeshes if 1502 <= visual.u16(row, 0) <= 1506
            for tri in triangles(donor_skin, row) for v in tri}
    heights = [struct.unpack_from("<f", donor.vertices, v * 48 + 8)[0] for v in cape]
    high, low = max(heights), min(heights)
    body_faces = points[np.array(cape_body_triangles(model, skin))]

    def positioned(source):
        _, y, z = source
        depth = max(0, min(1, (high - z) / (high - low)))
        x = back - .03 - .28 * depth + .02 * (abs(y) / .48) ** 2
        y, height = center_y + y * .72, top - (high - z) * .68
        if depth < .32:
            a, b, c = (body_faces[:, i] for i in range(3))
            determinant = (b[:, 2] - c[:, 2]) * (a[:, 1] - c[:, 1]) + (c[:, 1] - b[:, 1]) * (a[:, 2] - c[:, 2])
            valid = abs(determinant) > .000001
            u = np.divide((b[:, 2] - c[:, 2]) * (y - c[:, 1]) + (c[:, 1] - b[:, 1]) * (height - c[:, 2]),
                          determinant, out=np.zeros(len(a)), where=valid)
            v = np.divide((c[:, 2] - a[:, 2]) * (y - c[:, 1]) + (a[:, 1] - c[:, 1]) * (height - c[:, 2]),
                          determinant, out=np.zeros(len(a)), where=valid)
            hits = valid & (u >= 0) & (v >= 0) & (u + v <= 1)
            if hits.any():
                rear = (u * a[:, 0] + v * b[:, 0] + (1 - u - v) * c[:, 0])[hits].min()
                x = min(x, rear - .055)
        x += .025 * max(0, 1 - depth / .32)
        reference_point = (x, y, height, 1)
        return (inverse @ np.array(reference_point))[:3]

    mapping = {}
    for index in CAPE_BONES:
        source = donor.bones[index]
        assert source['parent_bone'] == (10 if index == 18 else CAPE_BONES[CAPE_BONES.index(index) - 1])
        bone = copy.deepcopy(source)
        pivot = (inverse @ np.array((back - .03, center_y, top, 1)))[:3] if index == 18 \
            else positioned(source['pivot'])
        bone.update(parent_bone=parent if index == 18 else mapping[source['parent_bone']],
                    key_bone_id=-1, bone_name_crc=0, pivot=tuple(pivot))
        for name in ('rotation', 'translation', 'scale'):
            track = bone[name]
            track.global_sequence = -1
            track.external.clear()
            track.timestamps, track.values = [], []
            for sequence_index, q in enumerate(model.sequences):
                resolved = model.sequences[animation.sequence(model, q['id'])]
                action = resolved['id']
                if action not in {seq['id'] for seq in donor.sequences}:
                    action = 0
                source_index = animation.sequence(donor, action)
                times, values = animation.keys(source[name], source_index)
                times, values = copy.deepcopy(times), copy.deepcopy(values)
                if name == 'rotation' and values:
                    _, initial = animation.keys(source[name], animation.sequence(donor, 0))
                    a = animation.quat(initial[0])
                    initial_inverse = (-a[0], -a[1], -a[2], a[3])
                    remapped = []
                    for value in values:
                        delta = np.array(animation.multiply(animation.quat(value), initial_inverse))
                        if delta[3] < 0:
                            delta = -delta
                        # Retain the authored flutter with a smaller swing on this shorter cape.
                        delta = np.array((0, 0, 0, 1)) * .55 + delta * .45
                        remapped.append(animation.packed(delta))
                    values = remapped
                if name == 'rotation' and index == 18:
                    # Cloth is held at the shoulder but hangs under gravity as the torso pitches.
                    source_duration = donor.sequences[source_index]['duration']
                    key_times = sorted(set([round(q['duration'] * i / 16) for i in range(17)]
                                           + [round(t * q['duration'] / max(1, source_duration)) for t in times]))
                    def donor_delta(clock):
                        if not values:
                            return (0, 0, 0, 1)
                        at = min(range(len(times)), key=lambda i: abs(times[i] - clock))
                        return animation.quat(values[at])
                    corrected = []
                    for clock in key_times:
                        current = animation.pose_matrices(authored, q['id'], clock, sequence_index)[parent]
                        rotation = np.linalg.inv(current[:3, :3]) @ reference[parent, :3, :3]
                        # Keep the hanging frame upright while the shoulder attachment moves with the torso.
                        pitch = (math.copysign(math.sqrt(max(0, 1 + rotation[0, 0]
                                     - rotation[1, 1] - rotation[2, 2])) / 2, rotation[2, 1] - rotation[1, 2]),
                                 math.copysign(math.sqrt(max(0, 1 - rotation[0, 0]
                                     + rotation[1, 1] - rotation[2, 2])) / 2, rotation[0, 2] - rotation[2, 0]),
                                 math.copysign(math.sqrt(max(0, 1 - rotation[0, 0]
                                     - rotation[1, 1] + rotation[2, 2])) / 2, rotation[1, 0] - rotation[0, 1]),
                                 math.sqrt(max(0, 1 + np.trace(rotation))) / 2)
                        lean = max(0, -math.atan2(rotation[0, 2], rotation[2, 2]))
                        flare = (0, math.sin(lean / 2), 0, math.cos(lean / 2))
                        pitch = animation.multiply(pitch, flare)
                        corrected.append(animation.packed(animation.multiply(
                            pitch, donor_delta(clock * source_duration / max(1, q['duration'])))))
                    times, values = key_times, corrected
                    duration = q['duration']
                else:
                    duration = donor.sequences[source_index]['duration']
                track.timestamps.append([min(q['duration'], round(t * q['duration'] / max(1, duration)))
                                         for t in times])
                track.values.append(values)
            track.timestamp_spans = track.value_spans = [(0, 0)] * len(model.sequences)
        if index == 18:
            track = bone['translation']
            track.interpolation = 1
            for sequence_index, q in enumerate(model.sequences):
                times = bone['rotation'].timestamps[sequence_index]
                values = []
                for clock in times:
                    matrices = animation.pose_matrices(authored, q['id'], clock, sequence_index)
                    anchor_points = np.einsum('vs,vsij,vj->vi', anchor_skin, matrices[anchor_bones], anchor_bind)[:, :3]
                    normal = np.cross(anchor_points[1] - anchor_points[0], anchor_points[2] - anchor_points[0])
                    normal /= np.linalg.norm(normal)
                    if normal[0] > 0:
                        normal = -normal
                    anchor = anchor_weights @ anchor_points + normal * .03
                    local = np.linalg.inv(matrices[parent]) @ np.array((*anchor, 1))
                    values.append(tuple(local[:3] - np.array(bone['pivot'])))
                track.timestamps[sequence_index], track.values[sequence_index] = times, values
        mapping[index] = len(model.bones)
        model.bones.append(bone)
    assert len(model.bones) <= 256

    def fit(record):
        data = bytearray(record)
        struct.pack_into('<3f', data, 0, *positioned(struct.unpack_from('<3f', data)))
        normal = inverse[:3, :3] @ np.array((-1, 0, 0))
        struct.pack_into('<3f', data, 20, *(normal / np.linalg.norm(normal)))
        z = struct.unpack_from('<f', record, 8)[0]
        depth = max(0, min(1, (high - z) / (high - low)))
        stops = ((0, parent), (.15, mapping[18]), (.58, mapping[28]), (1, mapping[37]))
        at = min(2, next((i for i in range(3) if depth <= stops[i + 1][0]), 2))
        fraction = (depth - stops[at][0]) / (stops[at + 1][0] - stops[at][0])
        weight = round(max(0, min(1, fraction)) * 255)
        ordered = [(stops[at][1], 255 - weight), (stops[at + 1][1], weight)]
        data[12:20] = bytes([weight for _, weight in ordered] + [0] * (4 - len(ordered))
                            + [bone for bone, _ in ordered] + [0] * (4 - len(ordered)))
        return data

    return fit, {'parent': parent, 'bones': list(mapping.values()), 'top': top, 'back': back}


def cape_body_surface(model, skin):
    """Rear torso triangles, excluding the arms, head and tail from the cloak fitting surface."""
    torso = {model.key_bone_lookup[k] for k in (4, 48, 51, 53)}
    surface = []
    for row in skin.submeshes:
        if visual.u16(row, 0) not in (0, 701, 801):
            continue
        for tri in triangles(skin, row):
            records = [model.vertices[v * 48:(v + 1) * 48] for v in tri]
            if sum(r[12 + s] for r in records for s in range(4) if r[16 + s] in torso) < 540:
                continue
            if sum(struct.unpack_from('<f', r, 20)[0] for r in records) >= -.3:
                continue
            surface.append((records, [struct.unpack_from('<3f', r) for r in records]))
    assert surface, 'Gnoll rear torso is absent'
    return surface


def fit_cape_vertex(model, surface, donor_record, high, low):
    """Bind the upper cloth to the actual back surface; let its lower half hang from the hips."""
    data = bytearray(donor_record)
    _, y, z = struct.unpack_from('<3f', data)
    t = (high - z) / (high - low)
    top = max(model.bones[model.key_bone_lookup[k]]['pivot'][2] for k in (2, 3)) + .075
    height, y = top - (high - z) * .68, y * .72
    query_y, query_z = max(-.18, min(.18, y)), max(1.0, height)
    hits = []
    for records, (a, b, c) in surface:
        determinant = (b[2] - c[2]) * (a[1] - c[1]) + (c[1] - b[1]) * (a[2] - c[2])
        if abs(determinant) < .000001:
            continue
        u = ((b[2] - c[2]) * (query_y - c[1]) + (c[1] - b[1]) * (query_z - c[2])) / determinant
        v = ((c[2] - a[2]) * (query_y - c[1]) + (a[1] - c[1]) * (query_z - c[2])) / determinant
        barycentric = (u, v, 1 - u - v)
        if min(barycentric) >= -.00001:
            hits.append((sum(w * p[0] for w, p in zip(barycentric, (a, b, c))), records, barycentric))
    if hits:
        back, records, barycentric = min(hits, key=lambda hit: hit[0])
    else:
        record = min((r for records, _ in surface for r in records), key=lambda r:
                     (struct.unpack_from('<f', r, 4)[0] - query_y) ** 2
                     + (struct.unpack_from('<f', r, 8)[0] - query_z) ** 2)
        back, records, barycentric = struct.unpack_from('<f', record)[0], [record], [1.0]
    weights = {}
    for record, factor in zip(records, barycentric, strict=True):
        for slot in range(4):
            if record[12 + slot]:
                bone = record[16 + slot]
                weights[bone] = weights.get(bone, 0) + factor * record[12 + slot]
    if height < 1.0:
        weights = {model.key_bone_lookup[51]: 255}
    weights = sorted(weights.items(), key=lambda row: row[1], reverse=True)[:4]
    total = sum(weight for _, weight in weights)
    quantized = [round(weight / total * 255) for _, weight in weights]
    quantized[0] += 255 - sum(quantized)
    data[12:20] = bytes(quantized + [0] * (4 - len(weights))
                        + [bone for bone, _ in weights] + [0] * (4 - len(weights)))
    struct.pack_into('<3f', data, 0, back - .015 - .02 * t, y, height)
    struct.pack_into('<3f', data, 20, -1, 0, 0)
    return data


def cape_surfaces(model, vertices, meshes, skin, donor, donor_skin, batch):
    """Retain authored cape topology and UVs on an animated chain suspended from the upper back."""
    spine = model.key_bone_lookup[4]
    fit, _ = cape_rig(model, skin, donor, donor_skin)
    for geoset in range(1502, 1507):
        source = [r for r in donor_skin.submeshes if visual.u16(r, 0) == geoset]
        used = {v for row in source for tri in triangles(donor_skin, row) for v in tri}
        mapping = {}
        for vertex in sorted(used):
            data = fit(donor.vertices[vertex * 48:(vertex + 1) * 48])
            mapping[vertex] = len(vertices) // 48
            vertices.extend(data)
        row = bytearray(source[0])
        visual.patch16(row, 18, spine)
        faces = [tuple(mapping[v] for v in tri) for mesh in source for tri in triangles(donor_skin, mesh)]
        meshes.append({'row': bytes(row), 'batches': [batch], 'geoset': geoset, 'triangles': faces,
                       'family': 'armor'})


def acquire():
    """Fetch only the pinned source model, its referenced files and authored skin palettes."""
    from wotlkconv.casc.config import BuildInfo
    current = asdict(BuildInfo.load(c.DEFAULT.retail_root, c.DEFAULT.product))
    prior = p.load_json(c.SEED / 'reports/source-pin.json')
    for key in ('product', 'version', 'build_key', 'root_ckey', 'encoding_ckey'):
        if current[key] != prior[key]:
            raise ValueError('Retail content build differs from previous ports: ' + key)
    # Blizzard refreshed CDN distribution metadata while retaining the exact content build.
    pin_path = CACHE / 'source-pin.json'
    source = c.Source(p.load_json(pin_path) if pin_path.exists() else current)
    try:
        pin = CACHE / 'source-pin.json'
        c.immutable(pin, (json.dumps(source.pin, indent=2) + '\n').encode())
        old = p.load_json(CACHE / 'inventory.json') if (CACHE / 'inventory.json').exists() else {}
        assets = old.get('assets', {})
        queue = [(3886641, 'model'), *[(fid, 'body') for fid in BODY_IDS],
                 *[(fid, 'armor') for fid in ARMOR_IDS]]
        seen = set()
        while queue:
            fid, role = queue.pop(0)
            if fid in seen:
                continue
            seen.add(fid)
            name = source.listfile.path_for(fid)
            suffix = PureWindowsPath(name).suffix if name else '.bin'
            path = CACHE / 'raw' / (str(fid) + suffix)
            data = source.read(fid, path)
            row = {'file_data_id': fid, 'logical_name': name, 'path': str(path), 'role': role,
                   'sha256': hashlib.sha256(data).hexdigest(),
                   'content_key': source.storage.root.ckey_for(fid).hex(), 'dependencies': c.references(data)}
            if str(fid) in assets and assets[str(fid)] != row:
                raise ValueError('Pinned Gnoll asset inventory changed: ' + str(fid))
            assets[str(fid)] = row
            queue.extend(row['dependencies'])
        save(CACHE / 'inventory.json', {'pin': source.pin, 'assets': assets})
        print('PINNED GNOLL', len(assets), 'files', source.pin['version'], flush=True)
    finally:
        source.close()


def raw(fid):
    row = p.load_json(CACHE / 'inventory.json')['assets'][str(fid)]
    data = Path(row['path']).read_bytes()
    if hashlib.sha256(data).hexdigest() != row['sha256']:
        raise ValueError('Source hash differs: ' + str(fid))
    return data


def convert():
    from wotlkconv.listfile import Listfile
    from wotlkconv.resolve import AssetSource
    from wotlkconv.options import Options
    from wotlkconv.m2 import convert_m2
    from wotlkconv.blp import convert_blp
    listfile = Listfile.load(c.DEFAULT.listfile)
    source = AssetSource(listfile=listfile, roots=[CACHE / 'raw'])
    opts = Options(path_prefix='custom\\gnoll', strict_limits=True)
    output = ROOT / 'converted'
    model, result, companions = convert_m2(raw(3886641), 'creature/gnoll2/gnoll2.m2', opts, listfile, source)
    save(ROOT / 'reports/conversion.json', {'model': result.as_dict(),
                                           'companions': [a.result.as_dict() for a in companions]})
    if not result.ok or not model or any(not a.result.ok or not a.data for a in companions):
        raise ValueError('Gnoll conversion failed; see reports/conversion.json')
    output.mkdir(parents=True, exist_ok=True)
    (output / 'gnoll2.m2').write_bytes(model)
    for asset in companions:
        (output / asset.filename).write_bytes(asset.data)
    for fid in (*BODY_IDS, *ARMOR_IDS, 3886653):
        data, report = convert_blp(raw(fid), str(fid) + '.blp', opts)
        if not data or not report.ok:
            raise ValueError('Gnoll texture conversion failed: ' + str(fid))
        (output / (str(fid) + '.blp')).write_bytes(data)
    print('CONVERTED', parse_m2(model).describe(), flush=True)


def triangles(skin, mesh):
    start = visual.u16(mesh, 8) | visual.u16(mesh, 2) << 16
    count = visual.u16(mesh, 10)
    return [tuple(skin.vertices[i] for i in skin.indices[at:at + 3])
            for at in range(start, start + count, 3)]


def audit():
    model, skin = parse_m2(raw(3886641)), parse_skin(raw(3886655))
    groups = {}
    for mesh in skin.submeshes:
        geo = visual.u16(mesh, 0)
        groups.setdefault(str(geo // 100), set()).add(geo)
    report = {'source_vertices': model.vertex_count, 'primary_vertices': len(set(skin.vertices)),
              'primary_indices': len(skin.indices), 'geosets': {g: sorted(v) for g, v in groups.items()},
              'attachments': [a['id'] for a in model.attachments],
              'sequences': [s['id'] for s in model.sequences], 'bones': len(model.bones)}
    save(ROOT / 'reports/audit.json', report)
    # Isolated mesh overview makes the source feature mappings reviewable before assigning labels.
    from PIL import ImageDraw
    positions = [struct.unpack_from('<3f', model.vertices, i * 48) for i in range(model.vertex_count)]
    canvas = Image.new('RGB', (1600, 1600), '#fafafa')
    draw = ImageDraw.Draw(canvas)
    colors = ('#d45f55', '#388ed1', '#67ae63', '#b88ade', '#d69e36', '#47b0ac')
    for n, (group, geosets) in enumerate(sorted(report['geosets'].items(), key=lambda x: int(x[0]))):
        x0, y0 = (n % 4) * 400, (n // 4) * 400
        def point(i):
            x, y, z = positions[i]
            return (x0 + 200 + (y * .8 + x * .6) * 130, y0 + 360 - z * 130)
        base = [tri for mesh in skin.submeshes if visual.u16(mesh, 0) == 0 for tri in triangles(skin, mesh)]
        for tri in sorted(base, key=lambda t: sum(positions[i][0] for i in t)):
            draw.polygon([point(i) for i in tri], fill='#e1e1e1')
        for j, geo in enumerate(geosets):
            faces = [t for mesh in skin.submeshes if visual.u16(mesh, 0) == geo for t in triangles(skin, mesh)]
            for tri in faces:
                draw.polygon([point(i) for i in tri], fill=colors[j % len(colors)])
        draw.text((x0 + 10, y0 + 10), str(geosets), fill='black')
    canvas.save(ROOT / 'reports/geosets.png')
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('acquire', 'audit', 'convert', 'config', 'prepare_motion', 'export_body',
                                           'prepare', 'preview', 'preview_equipment', 'stage'))
    globals()[parser.parse_args().action]()
