"""Stage both Drakkin genders, shared skins, independent eyes and supplied race portraits.

Uses current effective client data; does not build, install, or change saved characters.
"""

import copy
import hashlib
from pathlib import Path
import re
import shutil
import struct

from lupa.lua51 import LuaRuntime
from wotlkconv.blp import Blp

import drakkin_race_pack as k
import race_portrait_pack as portraits

p = k.p
STAGE = k.ROOT / 'options-20261011'
EYES = Path('G:/Kobold/NEW/Eyes')
PICTURES = Path('R:/Users/Zach/Pictures/Portraits')
TABLES = ('ChrRaces', 'CharBaseInfo', 'CharSections', 'CharHairGeosets', 'CharacterFacialHairStyles',
          'CharStartOutfit', 'NameGen', 'BarberShopStyle')
SQL = p.ROOT / 'data/sql/updates/pending_db_world/rev_20261011020000000_drakkin_options.sql'
OLD_GENDER_POLICY = '''-- This supplied Drakkin pack has one authored female body.
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


def skin_order(race):
    # Append missing skins; existing faction-local saved indexes must keep their original meaning.
    return list(range(16)) if race == 66 else list(range(12, 16)) + list(range(12))


def update_manifest(original):
    result = copy.deepcopy(original)
    race = result['race_ids'][0]
    result['models']['male'] = copy.deepcopy(result['models']['female'])
    result['helmet_prefix'] = 'Kb'
    if race == 67:
        result['playable'] = False
        result['retired_reason'] = 'Drakkin is Alliance only; slot and assets remain reserved.'
    result['runtime_patch_root'] = str(STAGE / 'assets')
    appearance = result['appearance']
    appearance['supported_genders'] = [0, 1]
    profile = copy.deepcopy(appearance['profiles']['1'])
    profile['capacities'] = [16, 1, 1, 25, 1]
    profile['options'][0]['choices'] = [k.palettes()[i].stem for i in skin_order(race)]
    profile['options'][3] = {'label': 'Eye Color',
                             'choices': [f'koboldeyes00_{i:02d}' for i in range(25)]}
    appearance['profiles'] = {'0': copy.deepcopy(profile), '1': profile}
    return result


def update_tables(baseline):
    result = dict(baseline)
    for name in TABLES:
        table = p.RawWdbc(result[name])
        pool, rows = bytearray(table.strings), list(table.records)
        for race in (66, 67):
            owned = p._table_rows_for_race(result[name], name, race)
            assert owned, (name, race)
            rows = [row for row in rows if row not in owned]
            bounds = k.ranges(race)
            if name == 'CharBaseInfo':
                if race == 66:
                    rows.extend(owned)
            elif name == 'ChrRaces':
                assert len(owned) == 1
                row = p._replace(owned[0], 16, 4, p._value(owned[0], 20))
                if race == 67:
                    row = p._replace(row, 4, 4, p._value(row, 4) | 1)
                rows.append(p._set_string(row, 6, pool, 'Kb'))
            elif name == 'CharSections':
                for gender in (0, 1):
                    for color, index in enumerate(skin_order(race)):
                        for kind in (0, 1, 4):
                            row = struct.pack('<10I', 0, race, gender, kind, 0, 0, 0,
                                              1 if kind == 1 else 17, 0, color)
                            if kind == 0:
                                row = p._set_string(row, 4, pool, f'custom\\kobold\\body-{index}.blp')
                                row = p._set_string(row, 5, pool, f'custom\\kobold\\extra-{index}.blp')
                            rows.append(row)
                    for eye in range(25):
                        row = struct.pack('<10I', 0, race, gender, 3, 0, 0, 0, 17, 0, eye)
                        rows.append(p._set_string(row, 4, pool, f'custom\\kobold\\koboldeyes00_{eye:02d}.blp'))
                    rows.append(struct.pack('<10I', 0, race, gender, 2, 0, 0, 0, 17, 0, 0))
                selected = [i for i, row in enumerate(rows) if p._value(row, 4) == race]
                assert len(selected) <= 1000
                for i, position in enumerate(selected):
                    rows[position] = p._replace(rows[position], 0, 4, bounds[name][0] + i)
            elif name in ('CharHairGeosets', 'CharacterFacialHairStyles'):
                female = [row for row in owned if p._value(row, 8 if name == 'CharHairGeosets' else 4) == 1]
                assert len(female) == 1
                rows.extend(female)
                row = p._replace(female[0], 8 if name == 'CharHairGeosets' else 4, 4, 0)
                if name == 'CharHairGeosets':
                    row = p._replace(row, 0, 4, bounds[name][0] + 1)
                rows.append(row)
            elif name == 'CharStartOutfit':
                female = [row for row in owned if row[6] == 1]
                assert len(female) == 10
                for gender in (0, 1):
                    for i, row in enumerate(female):
                        row = p._replace(p._replace(row, 6, 1, gender), 0, 4,
                                         22140 + (race - 66) * 20 + gender * 10 + i)
                        rows.append(row)
            elif name == 'NameGen':
                female = [row for row in owned if p._value(row, 12) == 1]
                assert female and len(female) * 2 <= 3000
                rows.extend(female)
                for i, row in enumerate(female):
                    rows.append(p._replace(p._replace(row, 12, 4, 0), 0, 4,
                                           bounds[name][0] + 3000 - len(female) + i))
            elif name == 'BarberShopStyle':
                styles = []
                for gender in (0, 1):
                    for kind, count in ((0, 1), (2, 1), (3, 16)):
                        template = next(row for row in owned if p._value(row, 4) == kind)
                        for value in range(count):
                            row = template
                            for offset, number in ((0, bounds[name][0] + len(styles)),
                                                   (152, gender), (156, value)):
                                row = p._replace(row, offset, 4, number)
                            styles.append(row)
                rows.extend(styles)
        ids = [p._value(row, 0) for row in rows]
        if name not in ('CharacterFacialHairStyles', 'CharBaseInfo'):
            assert len(ids) == len(set(ids)), 'Duplicate ID: ' + name
        result[name] = table.build(rows, bytes(pool))
    result['CharSections'] = k.o.order_charsections_entry(p.DBC_ROOT + 'CharSections.dbc', result['CharSections'])
    return result


def update_glue(data):
    text = data.decode('utf-8-sig')
    hidden = 'local hiddenRace = strupper(fileString) == "SETHRAK"'
    if 'local hiddenRace = strupper(fileString) == "DRAKKINHORDE"' not in text:
        assert text.count(hidden) == 1
        text = text.replace(hidden,
                            'local hiddenRace = strupper(fileString) == "DRAKKINHORDE"'
                            ' or strupper(fileString) == "SETHRAK"', 1)
    marker = '-- This supplied Drakkin pack has one authored female body.'
    if marker in text:
        assert text.count(OLD_GENDER_POLICY) == 1, 'Unexpected Drakkin gender wrapper'
        text = text.replace(OLD_GENDER_POLICY, '', 1)
    text = text.replace('for i=2,5 do _G["CharacterCustomizationButtonFrame"..i]:Hide(); end',
                        'for _,i in ipairs({2,3,5}) do _G["CharacterCustomizationButtonFrame"..i]:Hide(); end\n'
                        '            CharacterCustomizationButtonFrame4Text:SetText("Eye Color");')
    for token in ('DRAKKINALLIANCE', 'DRAKKINHORDE', 'GNOLLHORDE', 'SABERONHORDE'):
        sex, other = ('FEMALE', 'MALE') if token.startswith('DRAKKIN') else ('MALE', 'FEMALE')
        match = re.search(r'    \["' + token + '_' + sex + r'"\] = "([^"]+)",', text)
        assert match, token
        path = match[1]
        if token.startswith('DRAKKIN'):
            path = path[:-6] + 'Male'
        addition = f'    ["{token}_{other}"] = "{path}",\n'
        if f'["{token}_{other}"]' not in text:
            text = text.replace('RACE_ICON_TEXTURES = {\n', 'RACE_ICON_TEXTURES = {\n' + addition, 1)
    LuaRuntime().eval('function(s) local f,e=loadstring(s); assert(f,e); end')(text)
    return text.encode()


def model_eyes(data):
    original = k.parse_m2(data)
    assert original.textures[9]['filename'] == 'custom\\kobold\\koboldeyes00_00.blp'
    assert len(original.replacable_texture_lookup) > 6
    changed = bytearray(data)
    texture_count, texture_offset = struct.unpack_from('<2I', data, 0x50)
    assert texture_count == len(original.textures)
    # Reuse the stock hair-color texture slot for independent, saved eye colors.
    struct.pack_into('<I', changed, texture_offset + 9 * 16, 6)
    struct.pack_into('<2I', changed, texture_offset + 9 * 16 + 8, 0, 0)
    lookup_count, lookup_offset = struct.unpack_from('<2I', data, 0x68)
    assert lookup_count == len(original.replacable_texture_lookup)
    struct.pack_into('<H', changed, lookup_offset + 6 * 2, 9)
    parsed = k.parse_m2(changed)
    assert parsed.vertices == original.vertices and parsed.sequences == original.sequences
    assert parsed.textures[9]['type'] == 6 and parsed.replacable_texture_lookup[6] == 9
    return bytes(changed)


def stage():
    assert not STAGE.exists(), 'Review existing stage before regenerating'
    STAGE.mkdir(parents=True)
    files = p.ClientFiles(str(p.CLIENT_DEFAULT / 'Data'), 'enUS')
    replacements, sources = {}, {}
    try:
        baseline = {name: files.find(p.DBC_ROOT + name + '.dbc')[0] for name in TABLES}
        output = update_tables(baseline)
        for name, blob in output.items():
            replacements[p.DBC_ROOT + name + '.dbc'] = blob
            target = STAGE / 'client-dbc' / (name + '.dbc')
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(blob)
            target = STAGE / 'baseline' / (name + '.dbc')
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(baseline[name])
        original = files.find(p.GLUE_ROOT + 'CharacterCreate.lua')[0]
        replacements[p.GLUE_ROOT + 'CharacterCreate.lua'] = update_glue(original)
        (STAGE / 'CharacterCreate.lua').write_bytes(replacements[p.GLUE_ROOT + 'CharacterCreate.lua'])
        assets = {k.MODEL: model_eyes(files.find(k.MODEL)[0])}
        for eye in range(1, 25):
            path = EYES / f'koboldeyes00_{eye:02d}.blp'
            blob = path.read_bytes()
            image = Blp.parse(blob).decode_level(0)
            assert image.width and image.height
            sources[str(path)] = hashlib.sha256(blob).hexdigest()
            assets[f'custom\\kobold\\{path.name}'] = blob
        template = files.find(portraits.ICON_TEMPLATE_ENTRY)[0]
        ring = portraits.ring_layer(portraits.decode_client_blp(files.find(portraits.RING_ENTRY)[0]))
        for token, race, faction, genders in (
                ('DrakkinAlliance', 'kobold', 'alliance', ('Male', 'Female')),
                ('DrakkinHorde', 'kobold', 'horde', ('Male', 'Female')),
                ('JinyuAlliance', 'jinyu', 'alliance', ('Male', 'Female')),
                ('SaberonHorde', 'saberon', 'horde', ('Male', 'Female'))):
            for gender in genders:
                source_gender = 'male' if race == 'saberon' else gender.lower()
                source = PICTURES / f'Charactercreate-races_{race}-{source_gender}_{faction}.png'
                sources[str(source)] = p.sha256(source)
                art = portraits.portrait_bytes(source, portraits.circular_mask())
                plain = portraits.encode_portrait(art, template)
                icon = portraits.encode_portrait(portraits.compose_race_icon(art, ring), template)
                key = portraits.CREATOR_ICON_ROOT + f'UI-CharacterCreate-{token}{gender}.blp'
                replacements[key] = icon
                replacements[f'Interface\\Glues\\CharacterSelect\\ECS-Portrait-{token}{gender}.blp'] = plain
                key = f'Interface\\CharacterFrame\\TemporaryPortrait-{gender}-{token}'
                replacements[key] = replacements[key + '.blp'] = plain
        replacements[portraits.CREATOR_ICON_ROOT + 'UI-CharacterCreate-GnollHordeFemale.blp'] = files.find(
            portraits.CREATOR_ICON_ROOT + 'UI-CharacterCreate-GnollHordeMale.blp')[0]
        # Isolate the shared female model's helmet fit from Vulpera's own male equipment.
        names = set()
        inventory = p.Storm(p.DLL_DEFAULT)
        for archive in files.chain:
            handle = inventory.open_archive(Path(archive))
            try:
                listing = inventory.read(handle, '(listfile)').decode('utf-8', 'replace').splitlines()
                names.update(name for name in listing
                             if name.lower().startswith('item\\objectcomponents\\head\\')
                             and re.search(r'VuF(?:\d\d)?\.', name, re.I))
            finally:
                inventory.dll.SFileCloseArchive(handle)
        for name in sorted(names):
            if (name.lower().startswith('item\\objectcomponents\\head\\')
                    and re.search(r'VuF(?:\d\d)?\.', name, re.I)):
                blob = files.find(name)[0]
                for gender in ('M', 'F'):
                    assets[re.sub(r'VuF(?=(?:\d\d)?\.)', 'Kb' + gender, name, flags=re.I)] = blob
    finally:
        files.close()
    for name in set(TABLES) & set(k.tables_lib.SERVER_TABLES):
        live = p.SERVER_DBC_ROOT / (name + '.dbc')
        base = live.read_bytes()
        # Independently merge the same scoped edit into mounted server data.
        server_inputs = dict(baseline)
        server_inputs[name] = base
        blob = update_tables(server_inputs)[name]
        target = STAGE / 'server-dbc' / live.name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(blob)
        target = STAGE / 'baseline-server' / live.name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(base)
    catalog = (p.CLIENT_DEFAULT / 'EsteriaAppearance.bin').read_bytes()
    (STAGE / 'EsteriaAppearance-before.bin').write_bytes(catalog)
    magic, version, count = struct.unpack_from('<3I', catalog)
    assert (magic, version) == (0x50504145, 2) and len(catalog) == 12 + count * 2316
    records = [catalog[12 + i * 2316:12 + (i + 1) * 2316] for i in range(count)]
    records = [row for row in records if p._value(row, 0) not in (66, 67)]
    for race in (66, 67):
        for gender in (0, 1):
            row = bytearray(struct.pack('<3I', race, gender, 5))
            for offset, capacity in zip((0x28, 0x2c, 0x34, 0x24, 0x30), (16, 1, 1, 25, 1)):
                row.extend(struct.pack('<4I', offset, capacity, 1, 0) + bytes(128))
            row.extend(bytes(11 * 144))
            records.append(bytes(row))
    (STAGE / 'EsteriaAppearance.bin').write_bytes(struct.pack('<3I', magic, version, len(records))
                                               + b''.join(records))
    report = {'sources': sources, 'archives': {}, 'baseline_hashes': {},
              'client': str(p.CLIENT_DEFAULT), 'live_client_checked': False,
              'status': 'staged_requires_native_and_server_builds', 'asset_entries': len(assets)}
    report['runtime_baselines'] = {name: p.sha256(p.CLIENT_DEFAULT / name)
                                  for name in ('Wow.exe', 'EsteriaAppearance.dll', 'EsteriaAppearance.bin')}
    report['server_baselines'] = {name: p.sha256(STAGE / 'baseline-server' / (name + '.dbc'))
                                 for name in set(TABLES) & set(k.tables_lib.SERVER_TABLES)}
    storm = p.Storm(p.DLL_DEFAULT)
    for relative, changes in ((p.GLOBAL_ARCHIVE_REL, replacements), (p.LOCALE_ARCHIVE_REL, replacements),
                              (k.ASSET, assets)):
        live, target = p.CLIENT_DEFAULT / relative, STAGE / 'client' / relative
        report['baseline_hashes'][str(relative)] = p.sha256(live)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(live, target)
        storm.replace_archive_entries(target, changes)
        handle = storm.open_archive(target)
        try:
            for key, blob in changes.items():
                assert storm.read(handle, key) == blob, key
            if relative == k.ASSET:
                for key in storm.read(handle, '(listfile)').decode('utf-8').splitlines():
                    if key.lower() in ('(listfile)', '(attributes)'):
                        continue
                    path = k.local(STAGE / 'assets', key)
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(storm.read(handle, key))
        finally:
            storm.dll.SFileCloseArchive(handle)
        assert p.sha256(live) == report['baseline_hashes'][str(relative)], 'Live archive changed'
        report['archives'][str(relative)] = p.sha256(target)
        print('STAGED AND READ BACK', relative, flush=True)
    for key, blob in replacements.items():
        if key.startswith('Interface\\') and not key.startswith(p.GLUE_ROOT):
            path = k.local(STAGE / 'assets', key)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(blob)
    for spec in k.SPECS:
        slug = 'drakkin_' + spec[1]
        k.save(p.manifest_path(slug), update_manifest(p.load_manifest(slug)))
    registry_path = p.ROOT / 'modules/mod-custom-server/data/races/race_registry.json'
    registry = p.load_json(registry_path)
    for row in registry['playable']:
        if row['id'] in (66, 67):
            row['supported_genders'] = [0, 1]
    registry['playable'] = [row for row in registry['playable'] if row['id'] != 67]
    if not any(row['id'] == 67 for row in registry['npc_only']):
        registry['npc_only'].append({'id': 67, 'name': 'Drakkin Horde (retired)', 'not_playable': True})
    registry['sources']['supplied_drakkin'] = str(STAGE / 'assets')
    k.save(registry_path, registry)
    allocation = p.load_json(p.ALLOCATION_PATH)
    for faction, race in (('alliance', 66), ('horde', 67)):
        bounds = allocation['race_allocations']['drakkin_' + faction]
        for table in ('CreatureModelData', 'CreatureDisplayInfo'):
            bounds[table]['male'] = bounds[table]['female']
        bounds['CharStartOutfit'] = [22140 + (race - 66) * 20, 22159 + (race - 66) * 20]
    allocation['dbc_ranges']['CharStartOutfit'][1] = max(22179,
                                                       allocation['dbc_ranges']['CharStartOutfit'][1])
    k.save(p.ALLOCATION_PATH, allocation)
    import creature_race_pack
    creature_race_pack.header()
    report['source_files'] = {name: p.sha256(p.ROOT / name) for name in (
        'src/server/shared/CreatureAppearance.h', 'client-customization/NativeAppearance.cpp',
        'client-customization/TestNativeAppearance.cpp', 'tools/drakkin_options_update.py')}
    sql = ("-- Drakkin is Alliance only, with the same model for both selectable genders.\n"
           "UPDATE `chrraces_dbc` SET `MaleDisplayId` = `FemaleDisplayId`, `ClientPrefix` = 'Kb' "
           "WHERE `ID` IN (66, 67);\n"
           "UPDATE `chrraces_dbc` SET `Flags` = `Flags` | 1 WHERE `ID` = 67;\n"
           "DELETE FROM `playercreateinfo` WHERE `race` = 67;\n")
    if SQL.exists():
        assert SQL.read_text() == sql, 'Migration revision occupied'
    SQL.write_text(sql, encoding='utf-8', newline='\n')
    (STAGE / 'drakkin-options.sql').write_text(sql, encoding='utf-8', newline='\n')
    k.save(STAGE / 'report.json', report)
    print('STAGED', STAGE, flush=True)


if __name__ == '__main__':
    stage()
