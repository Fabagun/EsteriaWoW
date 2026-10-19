"""Stage Saberon player clothing and fitted geosets using the existing Gnoll/Sethrak tools."""

import argparse
import copy
import hashlib
from pathlib import Path
import struct
import subprocess

from PIL import Image
from wotlkconv.blp import Blp
from wotlkconv.m2 import parse_m2, parse_skin, write_md20
from wotlkconv.m2.skin import Skin, write_skin

import saberon_race_pack as s
import retroported_race_pack as p
import gnoll_race_pack as g
import sethrak_equipment_repair as e
import sethrak_animation_pack as a
from sethrak_body_regions import body_uvs

STAGE = Path(p.load_manifest('saberon')['appearance'].get(
    'equipment_stage', 'C:/Users/Zach/.codex/tmp/saberon-equipment'))
SKIN = s.MODEL[:-3] + '00.skin'


def anatomy(model):
    """Name existing WOD anatomy for the shared atlas fitter; never replace an authored lookup."""
    keys = {41: 8, 48: 2, 49: 9, 50: 16, 51: 3, 55: 7, 56: 6, 57: 12, 58: 11}
    assert model.bones[16]['parent_bone'] == 9 and model.bones[9]['parent_bone'] == 4
    assert model.bones[12]['parent_bone'] == 7 and model.bones[11]['parent_bone'] == 6
    for key, bone in keys.items():
        assert model.key_bone_lookup[key] in (65535, bone)
        model.key_bone_lookup[key] = bone
    return model


def export():
    STAGE.mkdir(parents=True, exist_ok=True)
    files = p.ClientFiles(str(p.CLIENT_DEFAULT / 'Data'), 'enUS')
    try:
        data, skin_data = files.find(s.MODEL)[0], files.find(SKIN)[0]
        s.c.immutable(STAGE / 'before.m2', data)
        s.c.immutable(STAGE / 'before.skin', skin_data)
        key = 'Character\\Worgen\\Male\\WorgenMale.m2'
        donor, hashes = a.embedded_model(STAGE / 'donors', key, lambda k: files.find(k)[0])
        s.c.immutable(STAGE / 'donor.m2', write_md20(donor))
        donor_skin_data = files.find(key[:-3] + '00.skin')[0]
        s.c.immutable(STAGE / 'donor.skin', donor_skin_data)
    finally:
        files.close()
    model = anatomy(parse_m2(data))
    skin, donor_skin = parse_skin(skin_data), parse_skin(donor_skin_data)
    by_crc = {b['bone_name_crc']: i for i, b in enumerate(model.bones) if b['bone_name_crc']}
    semantic = g.arm_bones(model, donor)

    def target_bone(index):
        visited = set()
        while index >= 0 and index not in visited:
            visited.add(index)
            if index in semantic:
                return semantic[index]
            crc = donor.bones[index]['bone_name_crc']
            if crc in by_crc:
                return by_crc[crc]
            index = donor.bones[index]['parent_bone']
        raise ValueError('Worgen garment has no Saberon ancestor')

    fitted = []
    for i in range(donor.vertex_count):
        vertex = e.vertex_record(donor, i)
        for slot, weight in enumerate(vertex['weights']):
            if weight:
                source = vertex['bones'][slot]
                target = target_bone(source)
                vertex['bones'][slot] = target
                for axis in range(3):
                    vertex['position'][axis] += weight / 255 * (
                        model.bones[target]['pivot'][axis] - donor.bones[source]['pivot'][axis])
        fitted.append(vertex)
    protected = set()
    for key in (41, 50, 59, 60):
        protected |= e.descendants(model, model.key_bone_lookup[key])
    body, kept = [], []
    for row in skin.submeshes:
        if s.visual.u16(row, 0) != 0:
            continue
        for tri in e.mesh_triangles(skin, row):
            weight = sum(model.vertices[v * 48 + 12 + slot] for v in tri for slot in range(4)
                         if model.vertices[v * 48 + 16 + slot] in protected)
            (kept if weight >= 255 else body).append(tri)
    garments, donor_body = [], []
    for i, row in enumerate(donor_skin.submeshes):
        geo = s.visual.u16(row, 0)
        types = {donor.textures[donor.texture_combos[s.visual.u16(b, 16)]]['type']
                 for b in donor_skin.batches if s.visual.u16(b, 4) == i}
        if geo == 0 and types == {1}:
            donor_body.extend(e.mesh_triangles(donor_skin, row))
        elif ((400 <= geo < 1400 or 1800 <= geo < 1900) and types == {1}):
            # Keep the Saberon's own default anatomy; donor surfaces supply only equipped garment variants.
            if geo not in (401, 501, 901, 1101, 1301, 1801):
                garments.append({'geoset': geo, 'triangles': e.mesh_triangles(donor_skin, row), 'texture_type': 1})
    for part in garments:
        if part['geoset'] not in (1202, 1302):
            continue
        scale = max(struct.unpack_from('<f', model.vertices, i * 48 + 8)[0]
                    for i in range(model.vertex_count)) / max(v['position'][2] for v in fitted)
        for index in {v for tri in part['triangles'] for v in tri}:
            x, y, z = struct.unpack_from('<3f', donor.vertices, index * 48)
            fitted[index]['position'] = [x * scale, y * scale, z * scale]
    pngs = []
    for color, fid in enumerate(s.BODY_IDS):
        image = Blp.parse(s.raw(fid)).decode_level(0)
        path = STAGE / 'source-images' / (str(color) + '.png')
        path.parent.mkdir(exist_ok=True)
        Image.frombytes('RGBA', (image.width, image.height), bytes(image.data)).save(path)
        pngs.append(str(path))
    collar = max(struct.unpack_from('<f', model.vertices, v * 48 + 8)[0] for tri in body for v in tri) + .02
    assert body and kept and garments and donor_body
    s.save(STAGE / 'male-body-work.json', {'target': [e.vertex_record(model, i) for i in range(model.vertex_count)],
        'body': body, 'original_only': kept, 'donor': fitted, 'donor_body': donor_body,
        'equipment': garments, 'skin_sources': pngs, 'region_uvs': body_uvs(model, body, collar),
        'fit_surface': [tri for row in skin.submeshes if s.visual.u16(row, 0) == 0
                        for tri in e.mesh_triangles(skin, row)], 'fit_boots': True, 'donor_hashes': hashes})
    print('EXPORTED', len(body), 'body triangles,', len(garments), 'garment variants')


def bake():
    subprocess.run([str(e.BLENDER), '-b', '--factory-startup', '--python',
                    str(p.ROOT / 'tools/sethrak_body_blender.py'), '--', str(STAGE), 'male'], check=True)


def prepare():
    if (STAGE / 'fit-report.json').exists():
        from saberon_equipment_fit import prepare as prepare_fit
        prepare_fit()
        return
    from haranir_race_pack import lznt1
    model = anatomy(parse_m2((STAGE / 'before.m2').read_bytes()))
    skin = parse_skin((STAGE / 'before.skin').read_bytes())
    donor = parse_m2((STAGE / 'donor.m2').read_bytes())
    donor_skin = parse_skin((STAGE / 'donor.skin').read_bytes())
    work = p.load_json(STAGE / 'male-body-work.json')
    for index, point in p.load_json(STAGE / 'male-equipment-fit.json').items():
        work['donor'][int(index)]['position'] = point
    uvs = p.load_json(STAGE / 'male-body-uv.json')
    uv_by_tri = {tuple(tri): uvs[i * 3:i * 3 + 3] for i, tri in enumerate(work['body'])}
    body_texture = len(model.textures)
    model.textures.append({'type': 1, 'flags': 0, 'filename': ''})
    body_combo = len(model.texture_combos)
    model.texture_combos.append(body_texture)
    material = len(model.materials)
    model.materials.append({'flags': 0, 'blending_mode': 0})
    body_batch = struct.pack('<12H', 0, 0, 0, 0, 65535, material, 0, 1, body_combo, 0, 0, 0)
    vertices, meshes, remapped = bytearray(model.vertices), [], {}
    for i, row in enumerate(skin.submeshes):
        geo = s.visual.u16(row, 0)
        batches = [b for b in skin.batches if s.visual.u16(b, 4) == i]
        original, player = [], []
        for tri in e.mesh_triangles(skin, row):
            if tri not in uv_by_tri:
                original.append(tri)
                continue
            mapped = []
            for index, uv in zip(tri, uv_by_tri[tri], strict=True):
                key = (index, *[round(x, 7) for x in uv])
                if key not in remapped:
                    data = bytearray(model.vertices[index * 48:(index + 1) * 48])
                    struct.pack_into('<2f', data, 32, *uv)
                    remapped[key] = len(vertices) // 48
                    vertices.extend(data)
                mapped.append(remapped[key])
            player.append(tuple(mapped))
        if original:
            types = {model.textures[model.texture_combos[s.visual.u16(b, 16)]]['type'] for b in batches}
            # Native outfits keep separate surfaces so equipped clothes can reveal the complete underlying body.
            native = 21000 + geo - 3100 if geo and types & {12, 13} else geo
            meshes.append({'row': row, 'batches': batches, 'triangles': original, 'geoset': native, 'family': 'body'})
        if player:
            meshes.append({'row': row, 'batches': [body_batch], 'triangles': player, 'geoset': 0, 'family': 'body'})
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
        row = next(r for r in donor_skin.submeshes if s.visual.u16(r, 0) == part['geoset'])
        meshes.append({'row': row, 'batches': [body_batch], 'geoset': part['geoset'],
                       'triangles': [tuple(donor_map[v] for v in tri) for tri in part['triangles']], 'family': 'armor'})
    cape_texture = len(model.textures)
    model.textures.append({'type': 2, 'flags': 0, 'filename': ''})
    cape_combo = len(model.texture_combos)
    model.texture_combos.append(cape_texture)
    cape_material = len(model.materials)
    model.materials.append({'flags': 4, 'blending_mode': 1})
    cape_batch = struct.pack('<12H', 16, 0, 0, 0, 65535, cape_material, 0, 1, cape_combo, 0, 0, 0)
    g.cape_surfaces(model, vertices, meshes, skin, donor, donor_skin, cape_batch)
    socket_donor = copy.deepcopy(donor)
    for identifier in (5, 6):
        source = next(a for a in socket_donor.attachments if a['id'] == identifier)
        track = socket_donor.bones[source['bone']]['scale']
        reference = next(values[0] for values in track.values if values)
        assert all(all(abs(x - y) < .00001 for x, y in zip(value, reference))
                   for values in track.values for value in values)
        track.values = [[reference for _ in values] for values in track.values]
    e.repair_attachment_points(model, socket_donor, socket_donor, g.arm_bones(model, donor))
    model.vertices, model.vertex_count = bytes(vertices), len(vertices) // 48
    # Preserve the expanded index high word instead of dropping any of the nine native outfits.
    raw = Skin()
    for index, mesh in enumerate(meshes):
        row = bytearray(mesh['row'])
        first_index, first_vertex = len(raw.indices), len(raw.vertices)
        used = list(dict.fromkeys(v for tri in mesh['triangles'] for v in tri))
        mapping = {v: first_vertex + i for i, v in enumerate(used)}
        raw.vertices.extend(used)
        raw.indices.extend(mapping[v] for tri in mesh['triangles'] for v in tri)
        for offset, value in ((0, mesh['geoset']), (2, first_index >> 16), (4, first_vertex),
                              (6, len(used)), (8, first_index & 65535), (10, len(mesh['triangles']) * 3)):
            s.visual.patch16(row, offset, value)
        raw.submeshes.append(bytes(row))
        for original in mesh['batches']:
            batch = bytearray(original)
            s.visual.patch16(batch, 4, index)
            s.visual.patch16(batch, 6, index)
            raw.batches.append(bytes(batch))
    compact = s.visual.compact_bone_palettes(model, raw)
    model.replacable_texture_lookup = [65535] * 16
    for i, texture in enumerate(model.textures):
        if texture['type']:
            model.replacable_texture_lookup[texture['type']] = i
    target = s.local(STAGE / 'assets', s.MODEL)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(write_md20(model))
    target.with_name(target.stem + '00.skin').write_bytes(write_skin(compact))
    a.check_model(parse_m2(target.read_bytes()), target.read_bytes())
    old = (p.CLIENT_DEFAULT / 'EsteriaSaberon.bin').read_bytes()
    magic, version, count = struct.unpack_from('<3I', old)
    assert (magic, version) == (0x314D4845, 1)
    records = [old[at:at + 156] for at in range(12, len(old), 156)]
    for choice in range(1, 10):
        records.append(struct.pack('<7I', 0, 2, 3100 + choice, 21000 + choice,
                                   1 | choice << 16, 0xffffffff, 0xffffffff) + bytes(128))
    bank = bytearray(struct.pack('<4I', 0x31544845, 1, 4, 0))
    for color in range(4):
        art = Image.open(STAGE / ('male-player-skin-' + str(color) + '.png')).convert('RGBA')
        art.putalpha(255)
        packed = lznt1(art.tobytes())
        offset = len(bank)
        bank.extend(struct.pack('<3I', art.width, art.height, len(packed)) + packed)
        records.append(struct.pack('<7I', 0, 3, 0, offset, color << 16, 0xffffffff, 0xffffffff)
                       + b'1:0'.ljust(128, b'\0'))
    struct.pack_into('<I', bank, 12, int.from_bytes(hashlib.sha256(bank[16:]).digest()[:4], 'little'))
    (STAGE / 'EsteriaSaberonTextures.bin').write_bytes(bank)
    (STAGE / 'EsteriaSaberon.bin').write_bytes(struct.pack('<3I', magic, version, len(records)) + b''.join(records))
    s.save(STAGE / 'model-report.json', {'vertices': model.vertex_count, 'indices': len(compact.indices),
        'meshes': len(compact.submeshes), 'geosets': sorted({s.visual.u16(r, 0) for r in compact.submeshes}),
        'equipment_geosets': sorted({part['geoset'] for part in work['equipment']})})
    print('PREPARED Saberon clothing, garment geosets, cape and attachment frames')


def preview():
    """Use actual installed item components and the shared equipment renderer."""
    model = parse_m2(s.local(STAGE / 'assets', s.MODEL).read_bytes())
    skin = parse_skin(s.local(STAGE / 'assets', SKIN).read_bytes())
    files = p.ClientFiles(str(p.CLIENT_DEFAULT / 'Data'), 'enUS')
    regions = ('ArmUpperTexture', 'ArmLowerTexture', 'HandTexture', 'TorsoUpperTexture',
               'TorsoLowerTexture', 'LegUpperTexture', 'LegLowerTexture', 'FootTexture')
    rects = ((0, 0, 256, 128), (0, 128, 256, 256), (0, 256, 256, 320), (256, 0, 512, 128),
             (256, 128, 512, 192), (256, 192, 512, 320), (256, 320, 512, 448), (256, 448, 512, 512))
    gear = {}
    try:
        table = p.RawWdbc(files.find(p.DBC_ROOT + 'ItemDisplayInfo.dbc')[0])
        displays = {p._value(r, 0): r for r in table.records}
        for mode, ids in (('shirt', (18924,)), ('plate', (25749, 24506, 24513)), ('robe', (15820,))):
            atlas = Image.open(STAGE / 'male-player-skin-0.png').convert('RGBA')
            for display in ids:
                row = displays[display]
                for field, directory, rect in zip(range(15, 23), regions, rects, strict=True):
                    stem = p._string(table.strings, p._value(row, field * 4)).decode()
                    if not stem:
                        continue
                    for suffix in ('_U', '_M', '', '_F'):
                        try:
                            key = 'Item\\TextureComponents\\' + directory + '\\' + stem + suffix + '.blp'
                            data = files.find(key)[0]
                            break
                        except FileNotFoundError:
                            continue
                    else:
                        raise FileNotFoundError('Item preview component absent: ' + stem)
                    image = Blp.parse(data).decode_level(0)
                    art = Image.frombytes('RGBA', (image.width, image.height), bytes(image.data))
                    atlas.alpha_composite(art.resize((rect[2] - rect[0], rect[3] - rect[1]),
                                                     Image.Resampling.LANCZOS), (rect[0], rect[1]))
            path = STAGE / ('male-preview-' + mode + '.png')
            atlas.save(path)
            gear[mode] = str(path)
        textures = {}
        for index, texture in enumerate(model.textures):
            if texture['type'] in (1, 2, 14):
                continue
            path = texture['filename']
            if texture['type']:
                fid = {11: s.BODY_IDS[0], 12: s.OUTFIT_IDS[0][0], 13: s.OUTFIT_IDS[0][1]}[texture['type']]
                path = s.PREFIX + 'textures\\' + str(fid) + '.blp'
            image = Blp.parse(files.find(path)[0]).decode_level(0)
            png = STAGE / ('texture-' + str(index) + '.png')
            Image.frombytes('RGBA', (image.width, image.height), bytes(image.data)).save(png)
            textures[str(index)] = str(png)
    finally:
        files.close()
    meshes = []
    for index, row in enumerate(skin.submeshes):
        batch = next(b for b in skin.batches if s.visual.u16(b, 4) == index)
        texture = model.texture_combos[s.visual.u16(batch, 16)]
        meshes.append({'geoset': s.visual.u16(row, 0), 'texture': texture,
                       'texture_type': 1 if model.textures[texture]['type'] == 14 else model.textures[texture]['type'],
                       'triangles': e.mesh_triangles(skin, row)})
    s.save(STAGE / 'male-preview.json', {'vertices': [e.vertex_record(model, i) for i in range(model.vertex_count)],
        'meshes': meshes, 'textures': textures, 'gear_textures': gear,
        'base_atlas': str(STAGE / 'male-player-skin-0.png'),
        'preview_groups': {'base': [0], 'shirt': [0], 'plate': [0, 403, 503, 903, 1104], 'robe': [0, 1302]}})
    subprocess.run([str(e.BLENDER), '-b', '--factory-startup', '--python',
                    str(p.ROOT / 'tools/sethrak_equipment_preview.py'), '--', str(STAGE), 'male'], check=True)


def stage():
    import shutil
    from test_saberon_equipment import check
    check()
    skin = s.local(STAGE / 'assets', SKIN).read_bytes()
    original = (p.CLIENT_DEFAULT / 'EsteriaAppearanceGeometry.bin').read_bytes()
    magic, version, count = struct.unpack_from('<3I', original)
    assert (magic, version) == (0x4D474145, 1)
    at, rows, changed = 12, [], 0
    for _ in range(count):
        name = original[at:at + 128].split(b'\0')[0].decode()
        length = struct.unpack_from('<I', original, at + 128)[0]
        row = original[at:at + 132 + length]
        if name.lower() == s.MODEL.lower():
            row = original[at:at + 128] + struct.pack('<I', len(skin)) + skin
            changed += 1
        rows.append(row)
        at += 132 + length
    assert changed == 1 and at == len(original)
    (STAGE / 'EsteriaAppearanceGeometry.bin').write_bytes(original[:12] + b''.join(rows))
    s.c.immutable(STAGE / 'before-geometry.bin', original)
    targets = {str(s.ASSET_ARCHIVE): STAGE / 'Patch-8.MPQ',
               **{name: STAGE / name for name in ('EsteriaSaberon.bin', 'EsteriaSaberonTextures.bin',
                                                 'EsteriaAppearanceGeometry.bin')}}
    if (STAGE / 'EsteriaSaberonCoverage.bin').exists():
        targets['EsteriaSaberonCoverage.bin'] = STAGE / 'EsteriaSaberonCoverage.bin'
    storm = p.Storm(p.DLL_DEFAULT)
    archive = p.CLIENT_DEFAULT / s.ASSET_ARCHIVE
    shutil.copy2(archive, STAGE / 'Patch-8.MPQ')
    updates = {s.MODEL: s.local(STAGE / 'assets', s.MODEL).read_bytes(), SKIN: skin}
    storm.replace_archive_entries(STAGE / 'Patch-8.MPQ', updates)
    handle = storm.open_archive(STAGE / 'Patch-8.MPQ')
    try:
        assert all(storm.read(handle, key) == value for key, value in updates.items())
    finally:
        storm.dll.SFileCloseArchive(handle)
    report = {'files': {name: str(path) for name, path in targets.items()},
              'before': {name: p.sha256(p.CLIENT_DEFAULT / name) if (p.CLIENT_DEFAULT / name).exists() else None
                         for name in targets},
              'after': {name: p.sha256(path) for name, path in targets.items()},
              'exe_sha256': p.sha256(p.CLIENT_DEFAULT / 'Wow.exe'),
              'dll_before': p.sha256(p.CLIENT_DEFAULT / 'EsteriaAppearance.dll'), 'live_test': False}
    s.save(STAGE / 'stage.json', report)
    print('STAGED only Saberon asset/catalog files; DLL build required')


def native():
    import shutil
    build = Path('C:/s64-gear')
    build.mkdir(exist_ok=True)
    for path in p.CLIENT_DEFAULT.glob('Esteria*.bin'):
        shutil.copy2(path, build / path.name)
    for name in ('EsteriaSaberon.bin', 'EsteriaSaberonTextures.bin', 'EsteriaAppearanceGeometry.bin'):
        shutil.copy2(STAGE / name, build / name)
    if (STAGE / 'EsteriaSaberonCoverage.bin').exists():
        shutil.copy2(STAGE / 'EsteriaSaberonCoverage.bin', build / 'EsteriaSaberonCoverage.bin')
    sources = ('client-customization/NativeAppearance.cpp', 'client-customization/HaranirMaterials.inl',
               'client-customization/NativeAppearance.def', 'client-customization/TestHighmountainMaterials.cpp',
               'client-customization/TestNativeAppearance.cpp', 'src/server/shared/CreatureAppearance.h')
    hashes = {name: p.sha256(p.ROOT / name) for name in sources}
    with (STAGE / 'native-build.log').open('w', encoding='utf-8') as log:
        result = subprocess.run(['cmd', '/c', str(p.ROOT / 'client-customization/build-native.bat'), str(build)],
                                stdout=log, stderr=subprocess.STDOUT)
    print((STAGE / 'native-build.log').read_text(errors='replace')[-7000:], flush=True)
    assert result.returncode == 0, 'Native build/harness failed; see native-build.log'
    assert all(p.sha256(p.ROOT / name) == sha for name, sha in hashes.items())
    s.save(STAGE / 'native-checks.json', {'all_passed': True, 'dll': str(build / 'EsteriaAppearance.dll'),
        'dll_sha256': p.sha256(build / 'EsteriaAppearance.dll'), 'source_hashes': hashes,
        'checks': ['TestNativeAppearance', 'TestHighmountainMaterials', 'TestCustomizationChoices',
                   'TestCosmeticWings']})


def install():
    import os
    import shutil
    from datetime import datetime
    from test_saberon_equipment import check
    check()
    processes = subprocess.check_output(['tasklist', '/FO', 'CSV', '/NH'], text=True).lower()
    if any(name in processes for name in ('wow.exe', 'eclipse.exe', 'mpqeditor.exe')):
        raise RuntimeError('Exit WoW/Eclipse/archive editors before installing Saberon equipment')
    report = p.load_json(STAGE / 'stage.json')
    native = p.load_json(STAGE / 'native-checks.json')
    assert native['all_passed']
    assert all(p.sha256(p.ROOT / name) == sha for name, sha in native['source_hashes'].items())
    targets = {name: Path(path) for name, path in report['files'].items()}
    targets['EsteriaAppearance.dll'] = Path(native['dll'])
    before = {**report['before'], 'EsteriaAppearance.dll': report['dll_before']}
    after = {**report['after'], 'EsteriaAppearance.dll': native['dll_sha256']}
    assert p.sha256(p.CLIENT_DEFAULT / 'Wow.exe') == report['exe_sha256']
    for name, source in targets.items():
        current = p.sha256(p.CLIENT_DEFAULT / name) if (p.CLIENT_DEFAULT / name).exists() else None
        assert current == before[name], 'Live file changed: ' + name
        assert p.sha256(source) == after[name], 'Staged file changed: ' + name
    backup = Path('C:/Users/Zach/.codex/backups') / ('saberon-equipment-' + datetime.now().strftime('%Y%m%d-%H%M%S'))
    backup.mkdir()
    for name in targets:
        if before[name] is None:
            continue
        saved = backup / name
        saved.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p.CLIENT_DEFAULT / name, saved)
        assert p.sha256(saved) == before[name]
    for name in ('report.json', 'last-install.json', 'deployment-verification.json', 'model.json'):
        shutil.copy2(s.STAGE / name, backup / name)
    shutil.copy2(p.manifest_path('saberon'), backup / 'saberon.json')
    from mechagnome_race_pack import sql
    appearance_query = ('SELECT guid,race,gender,skin,face,hairStyle,hairColor,facialStyle,extraAppearance '
                        'FROM characters ORDER BY guid;')
    characters = sql(appearance_query, 'acore_characters')
    (backup / 'character-appearances.tsv').write_text(characters, encoding='utf-8', newline='\n')
    server_hashes = {path.name: p.sha256(path) for path in p.SERVER_DBC_ROOT.glob('*.dbc')}
    try:
        for name, source in targets.items():
            target = p.CLIENT_DEFAULT / name
            temporary = target.with_suffix(target.suffix + '.saberon-equipment-next')
            shutil.copy2(source, temporary)
            assert p.sha256(temporary) == after[name]
            os.replace(temporary, target)
        assert characters == sql(appearance_query, 'acore_characters')
        assert server_hashes == {path.name: p.sha256(path) for path in p.SERVER_DBC_ROOT.glob('*.dbc')}
        assert p.sha256(p.CLIENT_DEFAULT / 'Wow.exe') == report['exe_sha256']
    except BaseException:
        for name in targets:
            target = p.CLIENT_DEFAULT / name
            if before[name] is None:
                assert p.CLIENT_DEFAULT.resolve() in target.resolve().parents
                if target.exists():
                    target.unlink()
            else:
                shutil.copy2(backup / name, target)
        raise
    shutil.copy2(STAGE / 'Patch-8.MPQ', s.STAGE / 'client' / s.ASSET_ARCHIVE)
    for key in (s.MODEL, SKIN):
        s.local(s.STAGE / 'assets', key).write_bytes(s.local(STAGE / 'assets', key).read_bytes())
    for name in ('EsteriaSaberon.bin', 'EsteriaSaberonTextures.bin', 'EsteriaAppearanceGeometry.bin'):
        shutil.copy2(STAGE / name, s.STAGE / name)
    if (STAGE / 'EsteriaSaberonCoverage.bin').exists():
        shutil.copy2(STAGE / 'EsteriaSaberonCoverage.bin', s.STAGE / 'EsteriaSaberonCoverage.bin')
    for name in ('report.json', 'last-install.json', 'deployment-verification.json'):
        data = p.load_json(s.STAGE / name)
        field = {'report.json': 'archives', 'last-install.json': 'installed_hashes',
                 'deployment-verification.json': 'client_hashes'}[name]
        data[field].update({key: sha for key, sha in after.items()
                            if name != 'report.json' or key == str(s.ASSET_ARCHIVE)})
        if name == 'report.json':
            for key in (s.MODEL, SKIN):
                data['assets'][key] = hashlib.sha256(s.local(STAGE / 'assets', key).read_bytes()).hexdigest()
        s.save(s.STAGE / name, data)
    manifest = p.load_manifest('saberon')
    manifest['appearance']['equipped_armor_geosets'] = (
        'source-fur-overlay-v2' if (STAGE / 'fit-report.json').exists() else 'player-atlas-v1')
    manifest['appearance']['equipment_stage'] = str(STAGE)
    s.save(p.manifest_path('saberon'), manifest)
    report.update(backup=str(backup), installed_hashes=after, native_checks=native,
                  character_appearance_sha256=hashlib.sha256(characters.encode()).hexdigest(),
                  server_dbc_hashes=server_hashes, live_test=False)
    s.save(STAGE / 'installed.json', report)
    s.save(backup / 'repair.json', report)
    print('INSTALLED matched Saberon equipment pack and native DLL with verified backup', backup)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('export', 'bake', 'prepare', 'preview', 'stage', 'native', 'install'))
    globals()[parser.parse_args().action]()
