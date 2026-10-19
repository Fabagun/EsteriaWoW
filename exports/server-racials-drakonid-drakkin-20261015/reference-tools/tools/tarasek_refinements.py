"""Refine the installed Tarasek using a new, pinned baseline; preserve existing appearance indexes."""

import argparse
import copy
import json
from pathlib import Path
import shutil
import struct

import tarasek_drakkin as t
import creature_animation_repair as motion
import sethrak_equipment_repair as equipment
from wotlkconv.m2 import parse_m2, parse_skin, write_md20
from wotlkconv.m2.skin import write_skin

WORK = Path('R:/RetroPorterWork/tarasek-drakkin-refinements')
BASE = WORK / 'baseline'
STAGE = WORK / 'stage'
EYES = ('original', 'red', 'amber', 'green', 'blue', 'violet', 'silver')
PALETTE = ((210, 25, 45), (245, 160, 20), (55, 205, 65), (45, 135, 245), (180, 65, 230), (180, 210, 225))


def pin(path, blob):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        assert path.read_bytes() == blob, 'Pinned baseline changed: ' + str(path)
    else:
        path.write_bytes(blob)


def baseline():
    import tarasek_deploy as deploy
    receipt = deploy.read(t.STAGE / 'last-install.json')
    assert receipt['status'] == 'installed_and_server_ready_live_client_pending'
    for name, expected in receipt['after'].items():
        assert deploy.digest(t.p.CLIENT_DEFAULT / name) == expected, name
    files = t.p.ClientFiles(str(t.p.CLIENT_DEFAULT / 'Data'), 'enUS')
    names = [t.MODEL, t.MODEL[:-3] + '00.skin', 'Interface\\GlueXML\\CharacterCreate.lua']
    names += [t.p.DBC_ROOT + n + '.dbc' for n in ('ItemDisplayInfo', 'HelmetGeosetVisData', 'CharSections')]
    names += ['custom\\tarasek\\creature\\tarasek\\tarasek_' + n + '.blp' for n in t.SKINS]
    sources = {}
    try:
        for name in names:
            blob, provider = files.find(name)
            pin(BASE / name, blob)
            sources[name] = {'sha256': t.sha(blob), 'provider': str(provider)}
    finally:
        files.close()
    for name in ('EsteriaAppearance.bin', 'EsteriaAppearanceGeometry.bin', 'EsteriaTarasek.bin',
                 'EsteriaTarasekTextures.bin', 'EsteriaAppearance.dll', 'Wow.exe'):
        blob = (t.p.CLIENT_DEFAULT / name).read_bytes()
        pin(BASE / name, blob)
        sources[name] = {'sha256': t.sha(blob)}
    pin(BASE / 'server-CharSections.dbc', (t.p.SERVER_DBC_ROOT / 'CharSections.dbc').read_bytes())
    t.save(WORK / 'baseline.json', {'files': sources, 'archives': {
        name: value for name, value in receipt['after'].items() if name.endswith('.MPQ')}})
    print('Pinned installed model, skins, catalogs, GlueXML, tables and runtime')


def model():
    import vrykul_female_pack as arrays
    import sethrak_animation_pack as checks
    original = parse_m2((BASE / t.MODEL).read_bytes())
    body = copy.deepcopy(original)
    skin = parse_skin((BASE / t.MODEL).with_name('tarasek00.skin').read_bytes())
    import numpy as np
    matrices = motion.pose_matrices(original, 0, 0)
    sockets = []
    for attachment in body.attachments:
        if attachment['id'] in (26, 27, 28, 30, 31):
            before = attachment['position']
            # Fit in the authored standing pose, then convert the offset into the existing socket frame.
            # Every back slot follows the same spine motion and retains its original orientation/scale.
            delta = np.linalg.solve(matrices[attachment['bone']][:3, :3], np.array((0, 0, -.3)))
            attachment['position'] = tuple(np.array(before) + delta)
            sockets.append({'id': attachment['id'], 'before': before, 'after': attachment['position'],
                            'authored_idle_world_delta': (0, 0, -.3)})
        if attachment['id'] in (5, 6):
            track = attachment['animate_attached']
            track.global_sequence = -1
            track.timestamps = [[0] for _ in body.sequences]
            track.values = [[1] for _ in body.sequences]
            track.timestamp_spans = track.value_spans = [(0, 0)] * len(body.sequences)
            track.external.clear()
    # The modern reflection shader was downgraded to a default two-texture combiner. Use an opaque,
    # lit diffuse skin pass instead of multiplying the skin by an armor environment texture.
    changed = []
    for i, batch in enumerate(skin.batches):
        combo = struct.unpack_from('<H', batch, 16)[0]
        if body.textures[body.texture_combos[combo]]['type'] != 11:
            continue
        fixed = bytearray(batch)
        struct.pack_into('<H', fixed, 2, 0)
        struct.pack_into('<H', fixed, 14, 1)
        struct.pack_into('<H', fixed, 18, 0)
        skin.batches[i] = bytes(fixed)
        changed.append(i)
    assert len(changed) == 7
    blob, _ = arrays.separate_bone_track_arrays(write_md20(body))
    check = parse_m2(blob)
    checks.check_model(check, blob)
    expected = copy.deepcopy(original)
    for old, new in zip(expected.attachments, check.attachments, strict=True):
        if old['id'] in (5, 6):
            old['animate_attached'] = copy.deepcopy(new['animate_attached'])
    checks.tracks_equal(expected, check, len(body.sequences))
    assert check.vertices == original.vertices and check.sequences == original.sequences
    target = STAGE / 'assets' / t.MODEL
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(blob)
    target.with_name('tarasek00.skin').write_bytes(write_skin(skin))
    t.save(WORK / 'model-repair.json', {'model': str(target), 'sha256': t.sha(blob),
        'shoulder_visibility': 'constant-on, both shoulders, all 179 sequences',
        'back_sockets': sockets,
        'single_diffuse_batches': changed, 'authored_bones_vertices_and_sequences_preserved': True})
    print('Repaired shoulder attachment visibility and opaque skin material')


def back_audit():
    import numpy as np
    files = t.p.ClientFiles(str(t.p.CLIENT_DEFAULT / 'Data'), 'enUS')
    table = t.p.RawWdbc((BASE / 'DBFilesClient/ItemDisplayInfo.dbc').read_bytes())
    model = parse_m2((BASE / t.MODEL).read_bytes())
    matrices = motion.pose_matrices(model, 0, 0)
    items = {}
    try:
        for identifier, attachment_id in ((23875, 26), (45653, 28), (45884, 5)):
            row = next(r for r in table.records if t.p._value(r, 0) == identifier)
            stem = t.p._string(table.strings, t.p._value(row, 4)).decode()
            folder = 'Shield' if identifier == 45653 else 'Shoulder' if identifier == 45884 else 'Weapon'
            key = 'Item\\ObjectComponents\\' + folder + '\\' + Path(stem).stem + '.m2'
            raw, provider = files.find(key)
            pin(WORK / 'equipment' / key, raw)
            item = parse_m2(raw)
            attachment = next(a for a in model.attachments if a['id'] == attachment_id)
            points = np.array([equipment.vertex_record(item, i)['position'] for i in range(item.vertex_count)])
            points = np.c_[points + attachment['position'], np.ones(len(points))]
            posed = (matrices[attachment['bone']] @ points.T).T[:, :3]
            items[str(identifier)] = {'model': key, 'provider': str(provider), 'attachment': attachment_id,
                'min': posed.min(axis=0).tolist(), 'max': posed.max(axis=0).tolist(),
                'mean': posed.mean(axis=0).tolist(), 'stem': stem}
    finally:
        files.close()
    t.save(WORK / 'back-audit.json', items)
    print(json.dumps(items, indent=2))


def previews():
    import numpy as np
    from PIL import Image
    from wotlkconv.blp import Blp
    model = parse_m2((BASE / t.MODEL).read_bytes())
    table = t.p.RawWdbc((BASE / 'DBFilesClient/ItemDisplayInfo.dbc').read_bytes())
    cached = t.p.load_json(WORK / 'back-audit.json')
    items = []
    files = t.p.ClientFiles(str(t.p.CLIENT_DEFAULT / 'Data'), 'enUS')
    try:
        for identifier in ('23875', '45653'):
            info = cached[identifier]
            key = info['model']
            item = parse_m2((WORK / 'equipment' / key).read_bytes())
            companion = key[:-3] + '00.skin'
            raw, _ = files.find(companion)
            pin(WORK / 'equipment' / companion, raw)
            skin = parse_skin(raw)
            texture = item.textures[0]['filename']
            if not texture:
                row = next(row for row in table.records if t.p._value(row, 0) == int(identifier))
                name = t.p._string(table.strings, t.p._value(row, 12)).decode()
                texture = key.rsplit('\\', 1)[0] + '\\' + name + '.blp'
            raw, _ = files.find(texture)
            pin(WORK / 'equipment' / texture, raw)
            image = Blp.parse(raw).decode_level()
            png = WORK / 'equipment' / (identifier + '.png')
            Image.frombytes('RGBA', (image.width, image.height), bytes(image.data)).save(png)
            items.append((info, item, skin, png))
    finally:
        files.close()
    original = t.p.load_json(t.WORK / 'previews/naked/model.json')
    for label, shift in (('back-original', (0, 0, 0)), ('back-lower', (0, 0, -.3)),
                         ('back-forward-lower', (.15, 0, -.3)), ('back-rear-lower', (-.1, 0, -.3))):
        scene = copy.deepcopy(original)
        matrices = motion.pose_matrices(model, 0, 0)
        for info, item, skin, png in items:
            attachment = next(a for a in model.attachments if a['id'] == info['attachment'])
            start = len(scene['vertices'])
            for index in range(item.vertex_count):
                vertex = equipment.vertex_record(item, index)
                point = matrices[attachment['bone']] @ np.array([*(
                    np.array(vertex['position']) + attachment['position']), 1])
                vertex['position'] = (point[:3] + shift).tolist()
                scene['vertices'].append(vertex)
            for part in skin.submeshes:
                faces = [[i + start for i in tri] for tri in equipment.mesh_triangles(skin, part)]
                scene['meshes'].append({'geoset': 50000, 'triangles': faces, 'texture': str(png)})
        scene.update(camera=(0, -7, 2.5), target=(-.1, 0, 1.4), scale=3.3)
        t.save(WORK / 'previews' / label / 'model.json', scene)
    for eye in EYES:
        scene = copy.deepcopy(original)
        # The 34-triangle source blink lid is invisible during the open-eye frame being previewed.
        scene['meshes'] = [part for part in scene['meshes']
                           if not (part['geoset'] == 0 and len(part['triangles']) == 34)]
        if eye == 'original':
            texture = t.WORK / 'preview/tarasek_black.png'
        else:
            texture = WORK / 'previews' / ('eye-black-' + eye) / 'skin.png'
        for part in scene['meshes']:
            part['texture'] = str(texture)
        scene.update(camera=(3, -5, 3.1), target=(.45, 0, 2.15), scale=1.0)
        t.save(WORK / 'previews' / ('eye-black-' + eye) / 'model.json', scene)
    print('Exported actual Ashbringer/shield fit comparisons and seven eye-color portraits')


def eyes(skins=None):
    import colorsys
    from PIL import Image, ImageDraw
    from wotlkconv.blp import Blp, Image as BlpImage
    body = parse_m2((BASE / t.MODEL).read_bytes())
    skin = parse_skin((BASE / t.MODEL).with_name('tarasek00.skin').read_bytes())
    faces = []
    for tri in equipment.mesh_triangles(skin, skin.submeshes[0]):
        uv = [struct.unpack_from('<2f', body.vertices, i * 48 + 32) for i in tri]
        if all(0 <= u < .09 and .30 < v < .4 for u, v in uv) and all(
                struct.unpack_from('<3f', body.vertices, i * 48)[2] > 2.3 for i in tri):
            faces.append(uv)
    assert len(faces) == 20, 'Authored iris UV ownership changed'
    report = {'options': EYES, 'iris_triangles': len(faces), 'textures': {}}
    for name in t.SKINS if skins is None else skins:
        key = 'custom\\tarasek\\creature\\tarasek\\tarasek_' + name + '.blp'
        path = BASE / key
        if not path.exists():
            assert name == 'purple', 'Installed skin missing from baseline: ' + name
            path = t.MODEL_SOURCE.parent / 'tarasek_purple.blp'
        source = path.read_bytes()
        original = Blp.parse(source)
        for eye, rgb in zip(EYES[1:], PALETTE, strict=True):
            levels = []
            pixels_changed = []
            hue, saturation, _ = colorsys.rgb_to_hsv(*(v / 255 for v in rgb))
            for level in range(len(original.mips)):
                image = original.decode_level(level)
                pixels = bytearray(image.data)
                mask = Image.new('L', (image.width, image.height))
                if image.width >= 64:
                    draw = ImageDraw.Draw(mask)
                    for face in faces:
                        draw.polygon([(u * image.width, v * image.height) for u, v in face], fill=255)
                mask_bytes = mask.tobytes()
                changed = 0
                for index, selected in enumerate(mask_bytes):
                    if not selected:
                        continue
                    offset = index * 4
                    red, green, blue = pixels[offset:offset + 3]
                    _, old_saturation, value = colorsys.rgb_to_hsv(red / 255, green / 255, blue / 255)
                    if old_saturation < .18 or value < .035:
                        continue  # Preserve pupil darkness and neutral highlights.
                    color = colorsys.hsv_to_rgb(hue, saturation * old_saturation, value)
                    pixels[offset:offset + 3] = bytes(round(c * 255) for c in color)
                    changed += 1
                assert all(pixels[i:i + 4] == image.data[i:i + 4] for i in range(0, len(pixels), 4)
                           if not mask_bytes[i // 4])
                assert pixels[3::4] == image.data[3::4]
                levels.append(BlpImage.from_rgba(image.width, image.height, pixels))
                pixels_changed.append(changed)
            assert 50 <= pixels_changed[0] <= 500
            blob = Blp.from_images(levels, compression=3, alpha_size=8,
                                   payloads=[bytes(image.to_bgra()) for image in levels]).serialize()
            destination = key[:-4] + '_eyes_' + eye + '.blp'
            target = STAGE / 'assets' / destination
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(blob)
            preview = WORK / 'previews' / ('eye-' + name + '-' + eye)
            preview.mkdir(parents=True, exist_ok=True)
            Image.frombytes('RGBA', (levels[0].width, levels[0].height), bytes(levels[0].data)).save(
                preview / 'skin.png')
            report['textures'][destination] = {'sha256': t.sha(blob), 'changed_pixels_per_mip': pixels_changed,
                'outside_iris_unchanged': True, 'alpha_unchanged': True}
    t.save(WORK / 'eyes.json', report)
    print('Generated', len(report['textures']), 'iris-only variants; original skin files remain unchanged')


def catalogs():
    baseline = (BASE / 'EsteriaAppearance.bin').read_bytes()
    magic, version, count = struct.unpack_from('<3I', baseline)
    assert (magic, version) == (0x50504145, 2)
    rows = [baseline[12 + i * 2316:12 + (i + 1) * 2316] for i in range(count)]
    index = next(i for i, row in enumerate(rows) if struct.unpack_from('<2I', row) == (66, 0))
    male = bytearray(rows[index])
    assert struct.unpack_from('<I', male, 12 + 3 * 144 + 4)[0] == 1
    struct.pack_into('<I', male, 12 + 3 * 144 + 4, len(EYES))
    rows[index] = bytes(male)
    STAGE.mkdir(exist_ok=True)
    (STAGE / 'EsteriaAppearance.bin').write_bytes(baseline[:12] + b''.join(rows))
    old = (BASE / 'EsteriaTarasek.bin').read_bytes()
    magic, version, count = struct.unpack_from('<3I', old)
    assert (magic, version) == (0x314D4845, 1)
    records = []
    for i in range(count):
        row = old[12 + i * 156:12 + (i + 1) * 156]
        _, kind, target = struct.unpack_from('<3I', row)
        if kind != 4 and not (kind == 1 and target == 11):
            records.append(row)
    for skin, name in enumerate(t.SKINS):
        for eye, color in enumerate(EYES):
            path = 'custom\\tarasek\\creature\\tarasek\\tarasek_' + name
            path += ('' if not eye else '_eyes_' + color) + '.blp'
            records.append(struct.pack('<7I', 0, 1, 11, 0, skin << 16, 3 | eye << 16, 0xffffffff)
                           + path.encode().ljust(128, b'\0'))
    visibility = t.p.RawWdbc((BASE / 'DBFilesClient/HelmetGeosetVisData.dbc').read_bytes())
    # The physical helmet donor is Tauren male: map its stock hair/horn hide bit into custom group 33.
    # Race 66 cannot be represented in this legacy 32-bit mask; never truncate the custom race ID.
    hide_ids = {t.p._value(row, 0) for row in visibility.records if t.p._value(row, 4) & (1 << (6 - 1))}
    table = t.p.RawWdbc((BASE / 'DBFilesClient/ItemDisplayInfo.dbc').read_bytes())
    hidden = []
    for row in table.records:
        if t.p._value(row, 13 * 4) in hide_ids:
            identifier = t.p._value(row, 0)
            records.append(struct.pack('<7I', 0, 4, identifier, 33, 0xffffffff, 0xffffffff, 0xffffffff)
                           + bytes(128))
            hidden.append(identifier)
    assert 45684 not in hidden, 'Lightbringer War-Helm must retain horns'
    (STAGE / 'EsteriaTarasek.bin').write_bytes(struct.pack('<3I', magic, version, len(records)) + b''.join(records))
    shutil.copy2(BASE / 'EsteriaTarasekTextures.bin', STAGE / 'EsteriaTarasekTextures.bin')
    geometry = (BASE / 'EsteriaAppearanceGeometry.bin').read_bytes()
    gmagic, gversion, gcount = struct.unpack_from('<3I', geometry)
    assert (gmagic, gversion) == (0x4D474145, 1)
    offset, entries, changed = 12, [], 0
    for _ in range(gcount):
        path = geometry[offset:offset + 128]
        length = struct.unpack_from('<I', geometry, offset + 128)[0]
        end = offset + 132 + length
        if path.split(b'\0')[0].decode().lower() == t.MODEL.lower():
            raw = (STAGE / 'assets' / t.MODEL).with_name('tarasek00.skin').read_bytes()
            entries.append(path + struct.pack('<I', len(raw)) + raw)
            changed += 1
        else:
            entries.append(geometry[offset:end])
        offset = end
    assert offset == len(geometry) and changed == 1
    (STAGE / 'EsteriaAppearanceGeometry.bin').write_bytes(geometry[:12] + b''.join(entries))
    data = (BASE / 'Interface/GlueXML/CharacterCreate.lua').read_text()
    old_layout = '''            for _,i in ipairs({2,4,5}) do _G["CharacterCustomizationButtonFrame"..i]:Hide(); end
            CharacterCustomizationButtonFrame3:Show();
            CharacterCustomizationButtonFrame3Text:SetText("Horns");'''
    if old_layout not in data:
        old_layout = old_layout.replace('            CharacterCustomizationButtonFrame3:Show();',
            '            if CharCreateOkayButton:IsShown() then CharacterCustomizationButtonFrame3:Show();\n'
            '            else CharacterCustomizationButtonFrame3:Hide(); end')
    new_layout = '''            for _,i in ipairs({2,5}) do _G["CharacterCustomizationButtonFrame"..i]:Hide(); end
            if CharCreateOkayButton:IsShown() then CharacterCustomizationButtonFrame3:Show();
            else CharacterCustomizationButtonFrame3:Hide(); end
            CharacterCustomizationButtonFrame3Text:SetText("Horns");
            if CharCreateOkayButton:IsShown() then CharacterCustomizationButtonFrame4:Show();
            else CharacterCustomizationButtonFrame4:Hide(); end
            CharacterCustomizationButtonFrame4Text:SetText("Eye Color");'''
    assert data.count(old_layout) == 1
    data = data.replace(old_layout, new_layout)
    marker = 'local function ChoiceText(id, value, label)\n'
    assert data.count(marker) == 1
    data = data.replace(marker, marker + '''    if CharacterCreate.selectedRaceID == 66
        and GetSelectedSex() == SEX_MALE and id == 4 then
        return ({"Original", "Red", "Amber", "Green", "Blue", "Violet", "Silver"})[value + 1]
            or label.." "..(value + 1);
    end
''')
    from lupa.lua51 import LuaRuntime
    LuaRuntime().eval('function(s) local f,e=loadstring(s); assert(f,e); end')(data)
    target = STAGE / 'assets/Interface/GlueXML/CharacterCreate.lua'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(data, encoding='utf-8', newline='\n')
    t.save(WORK / 'helmet-visibility.json', {'method': 'Tauren male stock hair/horn hide mask',
        'hidden_displays': hidden, 'lightbringer_45684_retains_horns': True})
    print('Staged seven eye choices, source-driven helmet visibility and male-only GlueXML control')


def pack():
    import os
    files = {str(path.relative_to(STAGE / 'assets')): path.read_bytes()
             for path in (STAGE / 'assets').rglob('*') if path.is_file()}
    assert len(files) == 39
    report = {'state': 'refinements_packaged', 'assets': {key: t.sha(blob) for key, blob in files.items()},
        'catalogs': {path.name: t.p.sha256(path) for path in STAGE.glob('*.bin')}, 'archives': {},
        'runtime_baseline': t.p.load_json(WORK / 'baseline.json')['files'],
        'skin_count': 6, 'horn_count': 5, 'eye_count': len(EYES), 'saved_index_migration_required': False,
        'native_built': True, 'server_built': False, 'installed': False, 'live_accepted': False}
    before = t.p.load_json(WORK / 'baseline.json')['archives']
    storm = t.p.Storm(t.p.DLL_DEFAULT)
    for name, digest in before.items():
        source = t.p.CLIENT_DEFAULT / name
        assert t.p.sha256(source) == digest, name
        target = STAGE / 'client' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        assert t.p.sha256(target) == digest
        storm.replace_archive_entries(target, files)
        if target.stat().st_size >= 0x80000000:
            compressed = target.with_suffix('.compressed')
            t.p.rebuild_archive_streaming(storm, target, compressed, compress=True)
            os.replace(compressed, target)
        assert target.stat().st_size < 0x80000000
        handle = storm.open_archive(target)
        try:
            for key, blob in files.items():
                assert storm.read(handle, key) == blob, key
        finally:
            storm.dll.SFileCloseArchive(handle)
        report['archives'][name] = {'before': digest, 'after': t.p.sha256(target),
            'bytes': target.stat().st_size, 'readback_verified': True, 'replacement_entries': len(files)}
        print('PACKED', name, target.stat().st_size, flush=True)
    report['source_files'] = {str(path): t.p.sha256(path) for path in (
        Path('tools/tarasek_refinements.py'), Path('client-customization/NativeAppearance.cpp'),
        Path('src/server/shared/CreatureAppearance.h'), Path('data/retroported-races/drakkin_alliance.json'))}
    t.save(STAGE / 'report.json', report)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('baseline', 'model', 'back-audit', 'eyes', 'catalogs', 'previews', 'pack'))
    globals()[parser.parse_args().action.replace('-', '_')]()
