"""Stage Awakening Tarasek as male Drakkin, preserving the installed female profile.

Run with Python 3.14 and a prepared wow-retroport workspace. All generated art remains outside Git.
No command configures, compiles, installs, applies SQL, or changes saved characters.
"""

import argparse
from collections import Counter
import copy
import hashlib
import json
import os
from pathlib import Path
from pathlib import PureWindowsPath
import shutil
import struct
import subprocess
import sys

REPO = Path(__file__).resolve().parents[1]
WORK = Path('G:/RetroPorterWork/tarasek-drakkin-male')
WORKSPACE = WORK / 'tool-workspace'
runtime = json.loads((WORKSPACE / 'runtime.json').read_text())
os.environ.update(runtime['environment'])
sys.path[:0] = [str(REPO / 'tools'), *runtime['python_paths']]

from PIL import Image
from wotlkconv.blp import Blp
from wotlkconv.m2 import parse_m2, parse_skin, write_md20
import retroported_race_pack as p
import sethrak_equipment_repair as equipment

MODEL_SOURCE = WORK / 'converted/patch-root/custom/tarasek/creature/tarasek/tarasek.m2'
SKINS = ('white', 'black', 'blue', 'bronze', 'green', 'red', 'purple')
MODEL = 'custom\\tarasek\\creature\\tarasek\\tarasek.m2'
MODEL_ID = 120079
DISPLAY_ID = 60070
STAGE = WORK / 'stage'
CAPACITIES = (len(SKINS), 1, 5, 1, 1)


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8', newline='\n')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def inspect():
    model = parse_m2(MODEL_SOURCE.read_bytes())
    skin = parse_skin(MODEL_SOURCE.with_name('tarasek00.skin').read_bytes())
    preview = WORK / 'preview'
    preview.mkdir(parents=True, exist_ok=True)
    pngs = {}
    for path in MODEL_SOURCE.parent.glob('*.blp'):
        image = Blp.parse(path.read_bytes()).decode_level(0)
        target = preview / (path.stem + '.png')
        Image.frombytes('RGBA', (image.width, image.height), bytes(image.data)).save(target)
        pngs[path.stem] = str(target)
    surfaces = []
    vertices = [equipment.vertex_record(model, i) for i in range(model.vertex_count)]
    meshes = []
    for i, mesh in enumerate(skin.submeshes):
        geo = struct.unpack_from('<H', mesh)[0]
        triangles = equipment.mesh_triangles(skin, mesh)
        batches = [b for b in skin.batches if struct.unpack_from('<H', b, 4)[0] == i]
        textures = []
        for b in batches:
            count, combo = struct.unpack_from('<HH', b, 14)
            textures.append([model.textures[model.texture_combos[combo + j]] for j in range(count)])
        used = {v for tri in triangles for v in tri}
        points = [vertices[v]['position'] for v in used]
        surfaces.append({'index': i, 'geoset': geo, 'triangles': len(triangles), 'textures': textures,
                         'min': [min(v[k] for v in points) for k in range(3)],
                         'max': [max(v[k] for v in points) for k in range(3)]})
        if geo in (0, 301):
            meshes.append({'geoset': geo, 'triangles': triangles, 'texture': pngs['tarasek_white']})
    save(preview / 'model.json', {'vertices': vertices, 'meshes': meshes,
        'camera': [6, -9, 4.5], 'target': [-.5, 0, 1.4], 'scale': 4.2})
    report = {'model': str(MODEL_SOURCE), 'vertices': model.vertex_count, 'bones': len(model.bones),
              'surfaces': surfaces, 'textures': model.textures,
              'sequences': model.sequences, 'key_bones': model.key_bone_lookup,
              'bone_keys': [{'index': i, 'parent': b['parent_bone'], 'crc': b['bone_name_crc'],
                             'pivot': b['pivot']} for i, b in enumerate(model.bones)]}
    save(WORK / 'reports/surface-audit.json', report)
    print(json.dumps({'surfaces': surfaces, 'textures': model.textures}, indent=2))


def baseline():
    out = WORK / 'baseline'
    out.mkdir(parents=True, exist_ok=True)
    files = p.ClientFiles(str(p.CLIENT_DEFAULT / 'Data'), 'enUS')
    report = {'client': str(p.CLIENT_DEFAULT), 'files': {}}
    keys = [p.DBC_ROOT + n + '.dbc' for n in ('ChrRaces', 'CreatureModelData', 'CreatureDisplayInfo',
        'CharSections', 'CharHairGeosets', 'CharacterFacialHairStyles', 'CharBaseInfo', 'CharStartOutfit',
        'NameGen', 'BarberShopStyle', 'ItemDisplayInfo')]
    keys += [p.GLUE_ROOT + n for n in ('CharacterCreate.lua', 'ECS_Schema.lua')]
    try:
        for key in keys:
            data, provider = files.find(key)
            target = out / key.replace('\\', '/')
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                assert target.read_bytes() == data, 'Baseline changed: ' + key
            else:
                target.write_bytes(data)
            report['files'][key] = {'provider': str(provider), 'sha256': sha(data), 'bytes': len(data)}
    finally:
        files.close()
    for path in sorted(p.CLIENT_DEFAULT.glob('Esteria*.bin')):
        data = path.read_bytes()
        target = out / path.name
        if target.exists():
            assert target.read_bytes() == data, 'Baseline changed: ' + path.name
        else:
            target.write_bytes(data)
        report['files'][path.name] = {'provider': str(path), 'sha256': sha(data), 'bytes': len(data)}
    for name in ('Wow.exe', 'EsteriaAppearance.dll'):
        path = p.CLIENT_DEFAULT / name
        report['files'][name] = {'sha256': sha(path.read_bytes()), 'bytes': path.stat().st_size}
    report['git_head'] = subprocess.check_output(['rtk', 'git', 'rev-parse', 'HEAD'], text=True).strip()
    save(out / 'receipt.json', report)
    print('Captured effective baseline:', len(report['files']), 'files')


def animations():
    import creature_animation_repair as motion
    import highmountain_complete_tracks as tracks
    import sethrak_animation_pack as checks
    import skyborne_visual_pack as visual
    import vrykul_female_pack as arrays

    original = parse_m2(MODEL_SOURCE.read_bytes())
    missing = set(checks.ACTIONS) - {s['id'] for s in original.sequences}
    candidates, donors = [], {}
    for path in Path('G:/RetroPorterWork/drakonid/donors/Character').rglob('*.m2'):
        donor = visual.read_player_model(path)
        tracks.embed(donor, path.parent, path.stem)
        names = {b['bone_name_crc'] for b in donor.bones if b['bone_name_crc']}
        row = {'path': str(path), 'matched_bones': sum(b['bone_name_crc'] in names for b in original.bones
                                                     if b['bone_name_crc']),
               'missing': sorted(missing - {s['id'] for s in donor.sequences}),
               'hashes': {str(q): sha(q.read_bytes()) for q in path.parent.iterdir() if q.is_file()}}
        candidates.append(row)
        donors[str(path)] = donor
    selected = max((r for r in candidates if not r['missing']), key=lambda r: r['matched_bones'])
    model = copy.deepcopy(original)
    added = []
    for action in sorted(missing):
        added.append(motion.retarget(model, donors[selected['path']], action))
        model.sequences[-1].update(bounds_min=model.bounding_box[:3], bounds_max=model.bounding_box[3:],
                                   bounds_radius=model.bounding_sphere_radius)
    aliases = motion.repair_model('tarasek', 0, model)['wrath_action_aliases']
    checks.tracks_equal(original, model, len(original.sequences))
    blob, separated = arrays.separate_bone_track_arrays(write_md20(model))
    rebuilt = parse_m2(blob)
    checks.check_model(rebuilt, blob)
    checks.tracks_equal(original, rebuilt, len(original.sequences))
    assert rebuilt.vertices == original.vertices
    target = WORK / 'animation-repair/tarasek.m2'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(blob)
    report = {'model': str(target), 'sha256': sha(blob), 'original_sequences': len(original.sequences),
              'sequences': len(rebuilt.sequences), 'candidates': candidates, 'selected_donor': selected['path'],
              'added_actions': added, 'compatibility_aliases': aliases,
              'authored_tracks_preserved': True, 'vertices_preserved': True,
              'shared_track_arrays_separated': separated, 'installed': False, 'live_accepted': False}
    save(WORK / 'reports/animation-repair.json', report)
    print('Animation stage:', len(original.sequences), '->', len(rebuilt.sequences),
          'sequences;', selected['matched_bones'], 'matching donor bones; source tracks preserved')


def player_keys(model):
    """Fill absent NPC key-bone semantics by exact CRC from proven player-compatible rigs."""
    names = {b['bone_name_crc']: i for i, b in enumerate(model.bones) if b['bone_name_crc']}
    sources = [Path('G:/RetroPorterWork/drakonid/animation-repair/drakonid2.m2')]
    sources += list(Path('G:/RetroPorterWork/drakonid/donors/Character').rglob('*.m2'))
    added = {}
    for path in sources:
        donor = parse_m2(path.read_bytes())
        for key, bone in enumerate(donor.key_bone_lookup):
            while len(model.key_bone_lookup) <= key:
                model.key_bone_lookup.append(65535)
            if model.key_bone_lookup[key] < len(model.bones) or bone >= len(donor.bones):
                continue
            crc = donor.bones[bone]['bone_name_crc']
            if crc in names:
                model.key_bone_lookup[key] = names[crc]
                added[key] = {'bone': names[crc], 'crc': crc, 'source': str(path)}
    # This NPC leaves player-only keys unset. The pinned surface/rig audit identifies its neck,
    # pelvis, digitigrade leg chains and five-link tail by hierarchy and bind pivots.
    semantics = {41: (9, 129936242), 49: (10, 3764035607), 50: (17, 2035544493),
                 51: (3, 3690404639), 55: (7, 3947676041), 56: (8, 289668330),
                 57: (14, 2215716567), 58: (15, 2115902388)}
    for key, (bone, crc) in semantics.items():
        assert model.bones[bone]['bone_name_crc'] == crc, 'Tarasek rig changed'
        assert model.key_bone_lookup[key] in (65535, bone), 'Authored key conflicts with anatomy'
        model.key_bone_lookup[key] = bone
        added[key] = {'bone': bone, 'crc': crc, 'source': 'pinned Tarasek hierarchy/pivot audit'}
    required = (0, 1, 4, 6, 8, 13, 41, 49, 50, 51, 53, 55, 56, 57, 58, 59, 60)
    assert all(model.key_bone_lookup[k] < len(model.bones) for k in required), [
        k for k in required if model.key_bone_lookup[k] >= len(model.bones)]
    return added


def population():
    import mechagnome_race_pack as db
    query = ('SELECT guid,race,gender,skin,face,hairStyle,hairColor,facialStyle,extraAppearance '
             'FROM characters WHERE race IN (66,67) ORDER BY guid;')
    data = db.sql(query, 'acore_characters')
    rows = [list(map(int, row.split('\t'))) for row in data.splitlines() if row]
    save(WORK / 'baseline/population.json', {'query': query, 'rows': rows, 'sha256': sha(data.encode())})
    print('Existing Drakkin:', dict(Counter((r[1], r[2]) for r in rows)))
    for name in ('CreatureModelData', 'CreatureDisplayInfo'):
        table = p.RawWdbc((WORK / 'baseline/DBFilesClient' / (name + '.dbc')).read_bytes())
        ids = {p._value(row, 0) for row in table.records}
        low = 120079 if name == 'CreatureModelData' else 60070
        print(name, 'first free candidate:', next(i for i in range(low, low + 100) if i not in ids))


def config():
    path = p.manifest_path('drakkin_alliance')
    original = p.load_json(path)
    result = copy.deepcopy(original)
    result['models']['male'] = {'model_id': MODEL_ID, 'display_id': DISPLAY_ID, 'model_path': MODEL}
    result['appearance']['profiles']['0'] = {
        'capacities': list(CAPACITIES),
        'options': [{'label': label, 'choices': list(choices)} for label, choices in zip(
            ('Skin Color', 'Face', 'Horns', 'Hair Color', 'Facial Hair'),
            (SKINS, (0,), (3301, 3302, 3303, 3304, 3305), (0,), (0,)), strict=True)]}
    result['appearance']['male_source'] = {'creature_id': 183829, 'display_id': 109404,
        'file_data_id': 4485357, 'product': 'wow', 'version': '12.1.0.69933',
        'build_key': 'dcfc90fffd79ba00406ae46f5f657592', 'npc_armor': False,
        'armor': 'source-uvs-with-alpha-player-shells-fitted-garments-and-animated-cloak',
        'runtime_patch_root': str(STAGE / 'assets')}
    assert result['appearance']['profiles']['1'] == original['appearance']['profiles']['1']
    assert result['models']['female'] == original['models']['female']
    save(path, result)
    allocation = p.load_json(p.ALLOCATION_PATH)
    own = allocation['race_allocations']['drakkin_alliance']
    for name, value in (('CreatureModelData', MODEL_ID), ('CreatureDisplayInfo', DISPLAY_ID)):
        for slug, bounds in allocation['race_allocations'].items():
            if slug != 'drakkin_alliance' and isinstance(bounds.get(name), dict):
                assert value not in bounds[name].values(), (slug, name, value)
        own[name]['male'] = value
        allocation['dbc_ranges'][name][1] = max(allocation['dbc_ranges'][name][1], value)
    save(p.ALLOCATION_PATH, allocation)
    print('Updated male manifest/allocation; female and retired Horde identities preserved')


def read_baseline(name):
    return (WORK / 'baseline/DBFilesClient' / (name + '.dbc')).read_bytes()


def replace_male_rows(data, name, added, strings=None):
    table = p.RawWdbc(data)
    offsets = {'CharSections': (4, 8), 'CharHairGeosets': (4, 8),
               'CharacterFacialHairStyles': (0, 4), 'BarberShopStyle': (148, 152)}
    race_at, sex_at = offsets[name]
    rows = [row for row in table.records if not (p._value(row, race_at) == 66 and p._value(row, sex_at) == 0)]
    return table.build(rows + added, bytes(strings) if strings is not None else table.strings)


def table_updates(bases):
    """Change only the existing male profile and newly reserved model/display rows."""
    import ogre_furbolg_race_pack as order
    import sethrak_race_pack as tables
    result = dict(bases)
    table = p.RawWdbc(bases['ChrRaces'])
    rows = [p._replace(row, 16, 4, DISPLAY_ID) if p._value(row, 0) == 66 else row for row in table.records]
    result['ChrRaces'] = table.build(rows, table.strings)
    for name, old_id, new_id in (('CreatureModelData', 120073, MODEL_ID),
                                  ('CreatureDisplayInfo', 60064, DISPLAY_ID)):
        table = p.RawWdbc(bases[name])
        assert not any(p._value(r, 0) == new_id for r in table.records), 'New ID is occupied: ' + name
        row = next(r for r in table.records if p._value(r, 0) == old_id)
        pool = bytearray(table.strings)
        row = p._clone_strings(name, table, row, pool)
        row = p._replace(row, 0, 4, new_id)
        if name == 'CreatureModelData':
            row = p._replace(row, 4, 4, p._value(row, 4) | 0x804)
            row = p._set_string(row, 2, pool, MODEL)
            retail = p.load_json(WORK / 'reports/discovery.json')['models'][0]
            for field, value in ((4, retail['ModelScale']), (14, retail['CollisionWidth']),
                                 (15, retail['CollisionHeight']), (16, retail['MountHeight']),
                                 *[(17 + i, value) for i, value in enumerate(retail['GeoBox'])],
                                 (23, retail['WorldEffectScale']), (24, retail['AttachedEffectScale']),
                                 (25, retail['MissileCollisionRadius']), (26, retail['MissileCollisionPush']),
                                 (27, retail['MissileCollisionRaise'])):
                row = row[:field * 4] + struct.pack('<f', value) + row[field * 4 + 4:]
        else:
            row = p._replace(row, 4, 4, MODEL_ID)
            for offset in (12, 28, 32, 36):
                row = p._replace(row, offset, 4, 0)
            row = row[:16] + struct.pack('<f', 1.0) + row[20:]
        result[name] = tables.append_rows(bases[name], name, [row], pool)
    source = p.RawWdbc(bases['CharSections'])
    pool, added = bytearray(source.strings), []
    # Reuse only previously owned male IDs; preserve every female ID and row byte.
    male_ids = sorted(p._value(r, 0) for r in source.records if p._value(r, 4) == 66 and p._value(r, 8) == 0)

    def section(kind, style, color):
        row = struct.pack('<10I', male_ids[len(added)], 66, 0, kind, 0, 0, 0,
                          1 if kind == 1 else 17, style, color)
        if kind == 0:
            row = p._set_string(row, 4, pool, 'custom\\tarasek\\creature\\tarasek\\tarasek_' + SKINS[color] + '.blp')
        elif kind == 3:
            row = p._set_string(row, 4, pool, 'custom\\tarasek\\creature\\tarasek\\tarasek_white.blp')
        added.append(row)

    for color in range(len(SKINS)):
        for kind in (0, 1, 4):
            section(kind, 0, color)
    for horn in range(5):
        section(3, horn, 0)
    section(2, 0, 0)
    result['CharSections'] = order.order_charsections_entry(p.DBC_ROOT + 'CharSections.dbc',
        replace_male_rows(bases['CharSections'], 'CharSections', added, pool))
    for name in ('CharHairGeosets', 'CharacterFacialHairStyles', 'BarberShopStyle'):
        table = p.RawWdbc(bases[name])
        if name == 'CharHairGeosets':
            # The native selection catalog owns horns in reserved group 33; stock hair stays hidden.
            ids = {p._value(row, 0) for row in table.records}
            owned = [r for r in table.records if p._value(r, 4) == 66 and p._value(r, 8) == 0]
            first = p._value(owned[0], 0)
            available = [first] + [i for i in range(1114300, 1114400) if i not in ids]
            assert len(available) >= 5
            additions = [struct.pack('<6I', available[i], 66, 0, i, 0, 1) for i in range(5)]
        elif name == 'CharacterFacialHairStyles':
            additions = [struct.pack('<8I', 66, 0, 0, 0, 0, 0, 0, 0)]
        else:
            additions = []
            for row in table.records:
                if p._value(row, 148) != 66 or p._value(row, 152) != 0:
                    continue
                kind, value = p._value(row, 4), p._value(row, 156)
                if (kind == 0 and value < 1) or (kind == 2 and value < 1) or (kind == 3 and value < len(SKINS)):
                    additions.append(row)
            # Independent horns are a creation control. Existing legacy barber remains in its declared scope.
        result[name] = replace_male_rows(bases[name], name, additions)
    return result


def catalogs():
    import drakonid_race_pack as drakonid
    from gnoll_texture_repair import clothing_catalog
    STAGE.mkdir(parents=True, exist_ok=True)
    original = (WORK / 'baseline/EsteriaAppearance.bin').read_bytes()
    magic, version, count = struct.unpack_from('<3I', original)
    stride = 2316
    assert (magic, version) == (0x50504145, 2) and len(original) == 12 + count * stride
    rows = [original[12 + i * stride:12 + (i + 1) * stride] for i in range(count)]
    male = bytearray(struct.pack('<3I', 66, 0, 5))
    for offset, capacity in zip((0x28, 0x2c, 0x34, 0x24, 0x30), CAPACITIES, strict=True):
        male.extend(struct.pack('<4I', offset, capacity, 1, 0) + bytes(128))
    male.extend(bytes(11 * 144))
    changed = [i for i, row in enumerate(rows) if struct.unpack_from('<2I', row) == (66, 0)]
    assert len(changed) == 1
    rows[changed[0]] = bytes(male)
    (STAGE / 'EsteriaAppearance.bin').write_bytes(original[:12] + b''.join(rows))
    skin = (WORK / 'equipment/assets' / MODEL.replace('\\', '/')).with_name('tarasek00.skin').read_bytes()
    original = (WORK / 'baseline/EsteriaAppearanceGeometry.bin').read_bytes()
    # Reuse the existing guarded EAGM appender with this model's explicit identity.
    previous = drakonid.MODEL
    drakonid.MODEL = MODEL
    try:
        geometry = drakonid.geometry_catalog(original, skin)
    finally:
        drakonid.MODEL = previous
    (STAGE / 'EsteriaAppearanceGeometry.bin').write_bytes(geometry)
    records = []

    def record(kind, target, value, selectors=(), path=''):
        choices = [i | j << 16 for i, j in selectors]
        records.append(struct.pack('<7I', 0, kind, target, value,
            *(choices + [0xffffffff] * (3 - len(choices)))) + path.encode().ljust(128, b'\0'))

    for i, name in enumerate(SKINS):
        record(1, 11, 0, [(0, i)], 'custom\\tarasek\\creature\\tarasek\\tarasek_' + name + '.blp')
    for i in range(5):
        record(0, 33, 3301 + i, [(2, i)])
    for geo in range(20001, 20009):
        record(2, 0, geo)
    table = p.RawWdbc(read_baseline('ItemDisplayInfo'))
    for row in table.records:
        stem = p._string(table.strings, p._value(row, 4)).decode()
        # Full head coverings suppress horns; face-only items retain the authored horns.
        if stem.lower().startswith('helm') and not stem.lower().startswith(
            ('helm_goggles', 'helm_blindfold', 'helm_eyepatch', 'helm_monocle', 'helm_circlet')):
            record(4, p._value(row, 0), 33)
    catalog, bank = clothing_catalog(struct.pack('<3I', 0x314D4845, 1, len(records)) + b''.join(records))
    (STAGE / 'EsteriaTarasek.bin').write_bytes(catalog)
    (STAGE / 'EsteriaTarasekTextures.bin').write_bytes(bank)
    print('Staged male profile, prepared geometry, skin/horn/equipment catalogs')


def glue(data):
    from lupa.lua51 import LuaRuntime
    text = data.decode('utf-8-sig')
    old = '''        if CharacterCreate.selectedRaceID == 66 or CharacterCreate.selectedRaceID == 67 then
            for _,i in ipairs({2,3,5}) do _G["CharacterCustomizationButtonFrame"..i]:Hide(); end
            CharacterCustomizationButtonFrame4Text:SetText("Eye Color");
        end'''
    new = '''        if CharacterCreate.selectedRaceID == 66 and GetSelectedSex() == SEX_MALE then
            for _,i in ipairs({2,4,5}) do _G["CharacterCustomizationButtonFrame"..i]:Hide(); end
            if CharCreateOkayButton:IsShown() then CharacterCustomizationButtonFrame3:Show();
            else CharacterCustomizationButtonFrame3:Hide(); end
            CharacterCustomizationButtonFrame3Text:SetText("Horns");
        elseif CharacterCreate.selectedRaceID == 66 or CharacterCreate.selectedRaceID == 67 then
            for _,i in ipairs({2,3,5}) do _G["CharacterCustomizationButtonFrame"..i]:Hide(); end
            CharacterCustomizationButtonFrame4Text:SetText("Eye Color");
        end'''
    assert text.count(old) == 1, 'Installed Drakkin control layout changed'
    text = text.replace(old, new)
    # Existing current wrapper already shows both buttons for race 66. Explicitly enable both when
    # switching from a single-gender species; respect the established female-only/retired rules elsewhere.
    text += '''
-- Drakkin: Tarasek male and the existing female share race 66.
local tarasekSetRace = SetCharacterRace;
function SetCharacterRace(id)
    tarasekSetRace(id);
    if CharacterCreate.selectedRaceID == 66 then
        CharacterCreateGenderButtonMale:Enable();
        CharacterCreateGenderButtonFemale:Enable();
        CharacterCreateGenderButtonMale:Show();
        CharacterCreateGenderButtonFemale:Show();
    end
end
'''
    LuaRuntime().eval('function(s) local f,e=loadstring(s); assert(f,e); end')(text)
    return text.encode()


def migrations():
    population = p.load_json(WORK / 'baseline/population.json')['rows']
    columns = ('skin', 'face', 'hairStyle', 'hairColor', 'facialStyle', 'extraAppearance')
    forward = ['-- Existing male Drakkin becomes Awakening Tarasek; female appearance is unchanged.']
    rollback = ['-- Restore exact pre-Tarasek appearance, only while the staged new tuple still matches.']
    for guid, race, gender, *values in population:
        if race != 66 or gender != 0:
            continue
        before = ' AND '.join(f'`{c}` = {v}' for c, v in zip(columns, values, strict=True))
        after = ' AND '.join(f'`{c}` = 0' for c in columns)
        forward.append('UPDATE `characters` SET ' + ', '.join(f'`{c}` = 0' for c in columns)
            + f' WHERE `guid` = {guid} AND `race` = 66 AND `gender` = 0 AND {before};')
        rollback.append('UPDATE `characters` SET '
            + ', '.join(f'`{c}` = {v}' for c, v in zip(columns, values, strict=True))
            + f' WHERE `guid` = {guid} AND `race` = 66 AND `gender` = 0 AND {after};')
    for directory, name, lines in (
        ('pending_db_world', 'rev_20261015020000000_tarasek_drakkin_male.sql',
         ['-- Select Tarasek for male Drakkin without changing female displays or faction policy.',
          f'UPDATE `chrraces_dbc` SET `MaleDisplayId` = {DISPLAY_ID} WHERE `ID` = 66 AND `MaleDisplayId` = 60064;']),
        ('pending_db_characters', 'rev_20261015020000000_tarasek_drakkin_male.sql', forward)):
        path = REPO / 'data/sql/updates' / directory / name
        text = format_sql('\n'.join(lines) + '\n')
        if path.exists():
            assert ' '.join(path.read_text().split()) == ' '.join(text.split()), 'Migration revision occupied'
        path.write_text(text, encoding='utf-8', newline='\n')
        shutil.copy2(path, STAGE / (directory + '.sql'))
    (STAGE / 'rollback-characters.sql').write_text(format_sql('\n'.join(rollback) + '\n'),
        encoding='utf-8', newline='\n')
    (STAGE / 'rollback-world.sql').write_text(format_sql(
        '-- Restore the previous male Drakkin display.\n'
        f'UPDATE `chrraces_dbc` SET `MaleDisplayId` = 60064 WHERE `ID` = 66 AND `MaleDisplayId` = {DISPLAY_ID};\n'),
        encoding='utf-8', newline='\n')


def format_sql(text):
    lines = []
    for line in text.splitlines():
        if line.startswith('--'):
            lines.append(line)
        else:
            lines.append(line.replace(', ', ',\n    ')
                         .replace(' WHERE ', '\nWHERE ').replace(' AND ', '\n  AND '))
    return '\n'.join(lines) + '\n'


def portraits():
    import race_portrait_pack as art
    files = p.ClientFiles(str(p.CLIENT_DEFAULT / 'Data'), 'enUS')
    try:
        template = files.find(art.ICON_TEMPLATE_ENTRY)[0]
        ring = art.ring_layer(art.decode_client_blp(files.find(art.RING_ENTRY)[0]))
    finally:
        files.close()
    image = Image.open(WORK / 'previews/horn-1/native-outfit.png').convert('RGBA')
    # The preview is a portrait camera; crop its central square before the circular icon mask.
    width, height = image.size
    edge = min(width, height)
    image = image.crop(((width - edge) // 2, (height - edge) // 2,
                        (width + edge) // 2, (height + edge) // 2)).resize((64, 64), Image.Resampling.LANCZOS)
    image.putalpha(art.circular_mask())
    plain = art.encode_portrait(image, template)
    icon = art.encode_portrait(art.compose_race_icon(image, ring), template)
    stem = art.CHARACTER_FRAME_ROOT + 'TemporaryPortrait-Male-DrakkinAlliance'
    return {art.CREATOR_ICON_ROOT + 'UI-CharacterCreate-DrakkinAllianceMale.blp': icon,
            stem: plain, stem + '.blp': plain,
            'Interface\\Glues\\CharacterSelect\\ECS-Portrait-DrakkinAllianceMale.blp': plain}


def stage():
    names = ('ChrRaces', 'CreatureModelData', 'CreatureDisplayInfo', 'CharSections', 'CharHairGeosets',
             'CharacterFacialHairStyles', 'BarberShopStyle')
    # Verify the pinned effective files before changing a copy of their winning archives.
    baseline_report = p.load_json(WORK / 'baseline/receipt.json')
    files = p.ClientFiles(str(p.CLIENT_DEFAULT / 'Data'), 'enUS')
    try:
        for key, record in baseline_report['files'].items():
            if '\\' in key:
                data = files.find(key)[0]
            else:
                data = (p.CLIENT_DEFAULT / key).read_bytes()
            assert sha(data) == record['sha256'], 'Live baseline changed: ' + key
    finally:
        files.close()
    catalogs()
    migrations()
    client = table_updates({name: read_baseline(name) for name in names})
    server_base = {name: (p.SERVER_DBC_ROOT / (name + '.dbc')).read_bytes()
                   for name in names if (p.SERVER_DBC_ROOT / (name + '.dbc')).exists()}
    server = table_updates({**{name: read_baseline(name) for name in names}, **server_base})
    for name, blob in client.items():
        path = STAGE / 'client-dbc' / (name + '.dbc')
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(blob)
    for name, before in server_base.items():
        for directory, blob in (('baseline-server', before), ('server-dbc', server[name])):
            path = STAGE / directory / (name + '.dbc')
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(blob)
    lua = glue((WORK / 'baseline/Interface/GlueXML/CharacterCreate.lua').read_bytes())
    (STAGE / 'CharacterCreate.lua').write_bytes(lua)
    assets = {str(PureWindowsPath(path.relative_to(STAGE / 'assets'))): path.read_bytes()
              for path in (STAGE / 'assets').rglob('*') if path.is_file()}
    for path in (WORK / 'equipment/assets').rglob('*'):
        if path.is_file():
            assets[str(PureWindowsPath(path.relative_to(WORK / 'equipment/assets')))] = path.read_bytes()
    for path in MODEL_SOURCE.parent.glob('*.blp'):
        assets[str(PureWindowsPath(MODEL).parent / path.name)] = path.read_bytes()
    assets.update(portraits())
    for key, blob in assets.items():
        path = STAGE / 'assets' / key.replace('\\', '/')
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(blob)
    replacements = {p.DBC_ROOT + name + '.dbc': blob for name, blob in client.items()}
    replacements[p.GLUE_ROOT + 'CharacterCreate.lua'] = lua
    replacements.update(assets)
    report = {'state': 'integration_packaging', 'race_id': 66, 'gender': 0,
              'source_creature': 183829, 'source_pin': p.load_json(WORK / 'source-pin.json'),
              'model_id': MODEL_ID, 'display_id': DISPLAY_ID,
              'assets': {name: sha(blob) for name, blob in assets.items()},
              'client_tables': {name: sha(blob) for name, blob in client.items()},
              'server_baselines': {name: sha(blob) for name, blob in server_base.items()},
              'runtime_baselines': {name: baseline_report['files'][name]['sha256']
                                    for name in ('Wow.exe', 'EsteriaAppearance.dll')},
              'catalogs': {path.name: sha(path.read_bytes()) for path in STAGE.glob('Esteria*.bin')},
              'source_files': {str(PureWindowsPath(path.relative_to(REPO))): sha(path.read_bytes())
                  for path in [REPO / 'src/server/shared/CreatureAppearance.h',
                      REPO / 'client-customization/NativeAppearance.cpp',
                      REPO / 'client-customization/HaranirMaterials.inl',
                      REPO / 'client-customization/ClothingMaterials.inl',
                      REPO / 'client-customization/TestNativeAppearance.cpp',
                      *sorted((REPO / 'tools').glob('tarasek*.py'))]},
              'archives': {}, 'installed': False, 'native_built': False, 'server_built': False,
              'live_accepted': False}
    save(STAGE / 'report.json', report)
    storm = p.Storm(p.DLL_DEFAULT)
    for relative in (p.GLOBAL_ARCHIVE_REL, p.LOCALE_ARCHIVE_REL):
        live, target = p.CLIENT_DEFAULT / relative, STAGE / 'client' / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        before = p.sha256(live)
        shutil.copy2(live, target)
        assert p.sha256(target) == before
        storm.replace_archive_entries(target, replacements)
        if target.stat().st_size >= 0x80000000:
            compressed = target.with_suffix('.compressed')
            p.rebuild_archive_streaming(storm, target, compressed, compress=True)
            os.replace(compressed, target)
        assert target.stat().st_size < 0x80000000, 'Classic MPQ boundary exceeded'
        handle = storm.open_archive(target)
        try:
            for key, blob in replacements.items():
                assert storm.read(handle, key) == blob, key
        finally:
            storm.dll.SFileCloseArchive(handle)
        assert p.sha256(live) == before, 'Live archive changed while packaging'
        report['archives'][str(relative)] = {'baseline': before, 'sha256': p.sha256(target),
            'bytes': target.stat().st_size, 'replacement_entries': len(replacements), 'readback_verified': True}
        save(STAGE / 'report.json', report)
        print('Packaged and read back', relative, flush=True)
    report['state'] = 'integration_staged_requires_builds_and_install'
    save(STAGE / 'report.json', report)
    print('Reviewable matched stage:', STAGE, flush=True)


def refresh_stage():
    """Apply a reviewed derived-asset revision to the existing staged copies only."""
    report = p.load_json(STAGE / 'report.json')
    assets = {str(PureWindowsPath(path.relative_to(STAGE / 'assets'))): path.read_bytes()
              for path in (STAGE / 'assets').rglob('*') if path.is_file()}
    changed = {key: blob for key, blob in assets.items() if report['assets'].get(key) != sha(blob)}
    storm = p.Storm(p.DLL_DEFAULT)
    for relative, record in report['archives'].items():
        target = STAGE / 'client' / relative
        assert p.sha256(target) == record['sha256'], 'Staged archive changed'
        assert p.sha256(p.CLIENT_DEFAULT / relative) == record['baseline'], 'Live archive baseline changed'
        if changed:
            storm.replace_archive_entries(target, changed)
            handle = storm.open_archive(target)
            try:
                for key, blob in changed.items():
                    assert storm.read(handle, key) == blob
            finally:
                storm.dll.SFileCloseArchive(handle)
        assert target.stat().st_size < 0x80000000
        record.update(sha256=p.sha256(target), bytes=target.stat().st_size)
        record['replacement_entries'] = len(report['client_tables']) + 1 + len(assets)
    report['assets'] = {key: sha(blob) for key, blob in assets.items()}
    for name in list(report['source_files']):
        report['source_files'][name] = sha((REPO / name).read_bytes())
    for path in (REPO / 'tools').glob('tarasek*.py'):
        report['source_files'][str(PureWindowsPath(path.relative_to(REPO)))] = sha(path.read_bytes())
    for name in ('data/retroported-races/drakkin_alliance.json', 'data/retroported-races/allocation.json',
                 'tools/creature_race_pack.py', 'tools/drakkin_options_update.py', 'tools/test_tarasek_drakkin.py'):
        report['source_files'][str(PureWindowsPath(name))] = sha((REPO / name).read_bytes())
    report['helmets'] = p.load_json(WORK / 'reports/helmets.json')
    migrations()
    report['migrations'] = {path.name: sha(path.read_bytes()) for path in STAGE.glob('*.sql')}
    save(STAGE / 'report.json', report)
    print('Updated stage:', len(changed), 'asset entries; live files untouched')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('inspect', 'baseline', 'animations', 'population',
                                          'config', 'stage', 'refresh_stage'))
    args = parser.parse_args()
    globals()[args.action]()
