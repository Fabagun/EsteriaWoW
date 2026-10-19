"""Prepare female Vrykul (56/57) and Alliance Ogre (61) against the installed Esteria package."""

import argparse
import copy
import json
from pathlib import Path
import struct

from luaparser import ast
from wotlkconv.m2 import parse_m2
import ogre_import as old

p, o = old.p, old.o
STAGE = Path('C:/Users/Zach/.codex/tmp/vrykul-female-ogre-alliance-20261007')
SOURCE = Path(r'G:\Downloads\HDWoWModels\Vrykul_client_files')
MODEL = r'custom\vrykul-female\VrykulPCFemale.m2'
ASSET = Path('Data/Patch-7.MPQ')
MODEL_ID, DISPLAY_ID = 120069, 60060
TABLES = old.TABLES
SERVER = old.SERVER
MIGRATION = p.ROOT / 'data/sql/updates/pending_db_world/rev_20261007040000000.sql'
CAPACITIES = [6, 1, 5, 5, 1]
SHARED_EFFECT = r'creature\vrykulfemale2\doomed_fog1.blp'
PRIVATE_EFFECT = r'custom\vrykul-female\doomed_fog1.blp'
RANGES = {'CharSections': [1112000, 1112299], 'CharHairGeosets': [1112000, 1112099],
          'BarberShopStyle': [1112000, 1112099], 'CharStartOutfit': [22070, 22089],
          'NameGen': [72000, 77999]}
OGRE_RANGES = {'CharSections': [1100700, 1100999], 'CharHairGeosets': [1100700, 1100999],
               'BarberShopStyle': [1100700, 1100999], 'CharStartOutfit': [22020, 22039],
               'NameGen': [63000, 65999]}


def configure():
    allocation = p.load_json(p.ALLOCATION_PATH)
    assert allocation['race_ids'].get('furbolg') == [61]
    allocation['race_ids'].pop('furbolg')
    allocation['race_ids']['ogre_alliance'] = [61]
    allocation['race_allocations'].pop('furbolg')
    allocation['race_allocations']['ogre_alliance'] = {
        **OGRE_RANGES, 'CreatureModelData': copy.deepcopy(allocation['race_allocations']['ogre']['CreatureModelData']),
        'CreatureDisplayInfo': copy.deepcopy(allocation['race_allocations']['ogre']['CreatureDisplayInfo'])}
    allocation['race_allocations']['vrykul']['CreatureModelData']['female'] = MODEL_ID
    allocation['race_allocations']['vrykul']['CreatureDisplayInfo']['female'] = DISPLAY_ID
    allocation['race_allocations']['vrykul_female'] = copy.deepcopy(RANGES)
    for table, bounds in RANGES.items():
        allocation['dbc_ranges'][table][1] = max(allocation['dbc_ranges'][table][1], bounds[1])
    allocation['dbc_ranges']['CreatureDisplayInfo'][1] = max(DISPLAY_ID,
        allocation['dbc_ranges']['CreatureDisplayInfo'][1])
    manifest = p.load_manifest('vrykul')
    female = {'capacities': CAPACITIES, 'options': [
        {'label': label, 'field': i, 'count': count, 'factor': 1, 'choices': list(range(count))}
        for i, (label, count) in enumerate(zip(('Skin Color', 'Face', 'Hair Style', 'Hair Color',
                                               'Facial Hair'), CAPACITIES))]}
    manifest['models']['female'] = {'model_id': MODEL_ID, 'display_id': DISPLAY_ID,
                                  'model_path': MODEL, 'display_scale': 1.0}
    manifest['appearance'].update(female_source='snowzocraft-player', supported_genders=[0, 1])
    manifest['appearance']['profiles']['1'] = female
    manifest['female_donor_root'] = str(SOURCE)
    registry_path = p.ROOT / 'modules/mod-custom-server/data/races/race_registry.json'
    registry = p.load_json(registry_path)
    for entry in registry['playable']:
        if entry['id'] in (56, 57):
            entry['supported_genders'] = [0, 1]
        if entry['id'] == 61:
            assert entry['species_key'] == 'furbolg'
            entry.update(species_key='ogre', display_name='Ogre', asset_owner='reforged_ogre_alliance',
                         legacy_mask_race=1, visual_base_race=2, start_profile='elwynn', species_selection=True)
        if entry['id'] == 60:
            entry['species_selection'] = True
    registry['faction_pairs'].append({'species_key': 'ogre', 'alliance_id': 61, 'horde_id': 60})
    alliance = copy.deepcopy(p.load_manifest('ogre'))
    alliance.update(slug='ogre_alliance', race_id=61, enum='RACE_OGRE_ALLIANCE', faction='alliance',
                    client_file_string='OgreAlliance', glue_token='OGREALLIANCE', legacy_mask_race=1,
                    visual_base_race=2, start_profile='elwynn', donor_start_race=1, donor_totem_race=11,
                    base_language=7, alliance_flag=0)
    alliance['portraits'] = {sex: str(o.PICTURES/'Alliance'/f'Charactercreate-races_ogre-{sex}_alliance.png')
                             for sex in ('male', 'female')}
    for path, data in ((p.ALLOCATION_PATH, allocation), (p.manifest_path('vrykul'), manifest),
                       (registry_path, registry), (p.manifest_path('ogre_alliance'), alliance)):
        old.save(path, data)


def append_rows(base, donor, name, selected, transforms):
    target, source = p.RawWdbc(base), p.RawWdbc(donor)
    assert (target.fields, target.record_size) == (source.fields, source.record_size)
    rows, pool = list(target.records), bytearray(target.strings)
    additions = []
    for row, fields in zip(selected, transforms):
        clone = p._clone_strings(name, source, row, pool)
        for offset, width, value in fields:
            clone = p._replace(clone, offset, width, value)
        additions.append(clone)
    if name not in ('CharBaseInfo', 'CharacterFacialHairStyles'):
        p._ensure_id_free(base, name, {p._value(r, 0) for r in additions})
    return target.build(rows + additions, bytes(pool))


def clone_gender(base, donor, name, source_race, target_race, start, gender=1):
    layout = p.WDBC_LAYOUTS[name]
    gender_offset = {'CharSections': 8, 'CharHairGeosets': 8, 'CharacterFacialHairStyles': 4,
                     'CharStartOutfit': 6, 'NameGen': 12, 'BarberShopStyle': 152}[name]
    width = 1 if name == 'CharStartOutfit' else 4
    source = p.RawWdbc(donor)
    rows = [r for r in source.records if p._value(r, layout.race_offset, layout.race_width) == source_race
            and p._value(r, gender_offset, width) == gender]
    if name == 'CharStartOutfit':
        rows = list({tuple(r[5:8]): r for r in rows}.values())
    transforms = [[(layout.race_offset, layout.race_width, target_race)] +
                  ([] if name == 'CharacterFacialHairStyles' else [(0, 4, start + i)])
                  for i in range(len(rows))]
    assert rows, name + ' donor rows missing'
    return append_rows(base, donor, name, rows, transforms), len(rows)


def tables(baseline):
    donor = {f.stem: f.read_bytes() for f in (SOURCE/'DBFilesClient').glob('*.dbc')}
    result = dict(baseline)
    for name, donor_id, target_id in (('CreatureModelData', 3632, MODEL_ID),
                                     ('CreatureDisplayInfo', 62117, DISPLAY_ID)):
        source = p.RawWdbc(donor[name])
        row = next(r for r in source.records if p._value(r, 0) == donor_id)
        fields = [(0, 4, target_id)]
        if name == 'CreatureDisplayInfo':
            fields += [(4, 4, MODEL_ID)]
        result[name] = append_rows(result[name], donor[name], name, [row], [fields])
        if name == 'CreatureModelData':
            t = p.RawWdbc(result[name])
            pool = bytearray(t.strings)
            rows = [p._set_string(r, 2, pool, MODEL) if p._value(r, 0) == MODEL_ID else r for r in t.records]
            result[name] = t.build(rows, bytes(pool))
    chr_table = p.RawWdbc(result['ChrRaces'])
    pool, rows = bytearray(chr_table.strings), []
    for row in chr_table.records:
        if p._value(row, 0) in (56, 57):
            assert p._value(row, 20) == 0, 'female Vrykul already installed'
            row = p._replace(row, 20, 4, DISPLAY_ID)
        rows.append(row)
    horde = next(r for r in rows if p._value(r, 0) == 60)
    assert not any(p._value(r, 0) == 61 for r in rows), 'race 61 already installed'
    alliance = horde
    for field, value in ((0, 61), (2, 1), (7, 7), (13, 0)):
        alliance = p._replace(alliance, field*4, 4, value)
    alliance = p._set_string(alliance, 11, pool, 'OgreAlliance')
    result['ChrRaces'] = chr_table.build(rows + [alliance], bytes(pool))
    for name in ('CharSections', 'CharHairGeosets', 'CharacterFacialHairStyles', 'CharStartOutfit', 'NameGen'):
        cursor = RANGES.get(name, [0])[0]
        for race, start_race in ((56, 1), (57, 2)):
            source = donor[name] if name in ('CharSections', 'CharHairGeosets', 'CharacterFacialHairStyles') \
                else baseline[name]
            donor_race = 16 if source is donor.get(name) else start_race
            result[name], count = clone_gender(result[name], source, name, donor_race, race, cursor)
            cursor += count
        if name in RANGES:
            assert cursor <= RANGES[name][1] + 1, name + ' female allocation exhausted'
    for name in ('CharSections', 'CharHairGeosets', 'CharacterFacialHairStyles', 'BarberShopStyle',
                 'CharStartOutfit', 'NameGen'):
        source = baseline[name]
        race = 1 if name in ('CharStartOutfit', 'NameGen') else 60
        cursor = OGRE_RANGES.get(name, [0])[0]
        for gender in (0, 1):
            result[name], count = clone_gender(result[name], source, name, race, 61, cursor, gender)
            cursor += count
        if name in OGRE_RANGES:
            assert cursor <= OGRE_RANGES[name][1]+1, name + ' Ogre allocation exhausted'
    result['CharBaseInfo'] = o.clone_char_base_info(result['CharBaseInfo'],
        {'race_id': 61, 'class_compat': p.load_manifest('vrykul')['classes']})
    barber = p.RawWdbc(result['BarberShopStyle'])
    rows, pool, next_id = list(barber.records), bytearray(barber.strings), RANGES['BarberShopStyle'][0]
    template = next(r for r in barber.records if p._value(r, 148) == 1 and p._value(r, 152) == 1)
    for race in (56, 57):
        for kind, values in ((0, range(5)), (1, range(1)), (2, range(6))):
            for value in values:
                row = template
                for field, number in ((0, next_id), (1, kind), (37, race), (38, 1), (39, value)):
                    row = p._replace(row, field*4, 4, number)
                row = p._set_string(row, 2, pool, 'Vrykul')
                rows.append(row)
                next_id += 1
    result['BarberShopStyle'] = barber.build(rows, bytes(pool))
    return result


def glue(name, payload):
    text = payload.decode('utf-8-sig')
    if name == 'CharacterCreate.lua':
        text = patch_creator_gender(text)
        for sex in ('Male', 'Female'):
            text = o._insert_once(text, 'RACE_ICON_TEXTURES = {\n',
                f'    ["OGREALLIANCE_{sex.upper()}"] = "Interface\\\\Glues\\\\CharacterCreate\\\\'
                f'UI-CharacterCreate-OgreAlliance{sex}",\n', name)
    elif name == 'CharacterInfo.lua':
        text = o._insert_once(text, 'local EXACT_RACE_DATA = {\n',
            '    [61] = {glueString="OGREALLIANCE", name="Ogre", faction="Alliance",'
            ' fileString="OgreAlliance"},\n', name)
        text += '\nRaceInfoByFileString.OGREALLIANCE = {Name="Ogre",'
        text += ' Description="These mighty adventurers have joined the Alliance."};\n'
    elif name == 'GlueStrings.lua':
        text += '\nOGREALLIANCE="Ogre"; OGREALLIANCE_MALE=OGREALLIANCE; OGREALLIANCE_FEMALE=OGREALLIANCE;\n'
    elif name == 'GlueParent.lua':
        text = o._insert_once(text, '        ["THINHUMAN"] = true,\n', '        ["OGREALLIANCE"] = true,\n', name)
        for table in ('CharModelFogInfo', 'CharModelGlowInfo', 'GlueAmbienceTracks'):
            text += f'\n{table}["OGREALLIANCE"]={table}["HUMAN"];\n'
    elif name == 'CharacterSelect.lua':
        anchor = 'elseif ( raceModel == "OGREHORDE"'
        assert text.count(anchor) == 1
        text = text.replace(anchor, 'elseif ( raceModel == "OGREALLIANCE" or raceModel == "OGREHORDE"')
    elif name == 'ECS_Schema.lua':
        text = o._insert_once(text, 'S.RaceOverride = {\n',
            '    [61] = {name="Ogre", faction=1, artKey="OgreAlliance"},\n', name)
        text = o._insert_once(text, 'S.PortraitArtKeys = {\n', '    OgreAlliance=true,\n', name)
        # Exact race override supplies faction and art even when both factions share the display name.
    elif name == 'ECS_Integrate.lua':
        anchor = 'or race == 60 or race == 62'
        assert anchor in text
        text = text.replace(anchor, 'or race == 60 or race == 61 or race == 62')
    ast.parse(text)
    return text.encode('utf-8')


def patch_creator_gender(text):
    helper = ('function CharacterCreate_IsMaleOnlyRace(race)\n'
              '    return race == 55 or race == 58 or race == 59 or race == 63;\n'
              'end\n')
    if helper not in text:
        assert 'CharacterCreate_IsMaleOnlyRace' not in text, 'unexpected gender policy'
        text = o._insert_once(text, 'MAX_CLASSES_PER_RACE = 10;\n', '\n'+helper, 'creator gender policy')
    guards = {
        'target and target.raceID and ((target.raceID >= 55 and target.raceID <= 59) or target.raceID == 63)':
            'target and CharacterCreate_IsMaleOnlyRace(target.raceID)',
        'CharacterCreate.selectedRaceID and ((CharacterCreate.selectedRaceID >= 55 '
        'and CharacterCreate.selectedRaceID <= 59) or CharacterCreate.selectedRaceID == 63)':
            'CharacterCreate_IsMaleOnlyRace(CharacterCreate.selectedRaceID)',
        'race and ((race >= 55 and race <= 59) or race == 63)': 'CharacterCreate_IsMaleOnlyRace(race)',
        'race and (race == 55 or race == 58 or race == 59 or race == 63)':
            'CharacterCreate_IsMaleOnlyRace(race)',
    }
    for old_guard, new_guard in guards.items():
        text = text.replace(old_guard, new_guard)
    assert text.count('CharacterCreate_IsMaleOnlyRace(') == 4, 'all three gender callers must use the shared policy'
    assert '>= 55 and' not in text, 'stale male-only Vrykul policy'
    ast.parse(text)
    return text


def catalogs(assets):
    original = (p.CLIENT_DEFAULT/'EsteriaAppearance.bin').read_bytes()
    magic, version, count = struct.unpack_from('<3I', original)
    assert (magic, version, len(original)) == (0x50504145, 2, 12+count*(12+16*144))
    additions = []
    for race in (56, 57):
        assert not any(struct.unpack_from('<2I', original, 12+i*(12+16*144)) == (race, 1)
                       for i in range(count))
        record = struct.pack('<3I', race, 1, 5)
        for offset, capacity in zip((0x28, 0x2C, 0x34, 0x24, 0x30), CAPACITIES):
            record += struct.pack('<4I', offset, capacity, 1, 0) + bytes(128)
        additions.append(record+bytes(11*144))
    result = {'EsteriaAppearance.bin': struct.pack('<3I', magic, version, count+2)
              +original[12:]+b''.join(additions)}
    original = (p.CLIENT_DEFAULT/'EsteriaAppearanceGeometry.bin').read_bytes()
    magic, version, count = struct.unpack_from('<3I', original)
    assert (magic, version) == (0x4D474145, 1)
    assert MODEL.encode() not in original
    skin = assets[MODEL[:-3]+'00.skin']
    result['EsteriaAppearanceGeometry.bin'] = struct.pack('<3I', magic, version, count+1)+original[12:]
    result['EsteriaAppearanceGeometry.bin'] += MODEL.encode().ljust(128, b'\0')+struct.pack('<I', len(skin))+skin
    return result


def isolate_effect(assets):
    """Repoint one shadowed fixed texture without rewriting geometry or animation tracks."""
    payload = assets[MODEL]
    count, offset = struct.unpack_from('<2I', payload, 0x50)
    assert count == len(parse_m2(payload).textures)
    result = bytearray(payload)
    matches = 0
    for i in range(count):
        base = offset+i*16
        kind, _, length, start = struct.unpack_from('<4I', payload, base)
        filename = payload[start:start+length].split(b'\0')[0].decode()
        if kind == 0 and filename.casefold() == SHARED_EFFECT.casefold():
            replacement = PRIVATE_EFFECT.encode()+b'\0'
            struct.pack_into('<2I', result, base+8, len(replacement), len(result))
            result.extend(replacement)
            matches += 1
    assert matches == 1
    assets[MODEL] = bytes(result)
    assets[PRIVATE_EFFECT] = assets.pop(SHARED_EFFECT)
    assert any(t['filename'] == PRIVATE_EFFECT for t in parse_m2(assets[MODEL]).textures)


def normalize_components(assets):
    """Use the native character compositor's indexed BLP contract, preserving authored alpha."""
    report = {}
    for key, payload in list(assets.items()):
        if not key.casefold().startswith('character\\vrykul\\female\\') or not key.lower().endswith('.blp'):
            continue
        source = p.Blp.parse(payload)
        image = source.decode_level(0)
        palette = p.build_palette(image.data, 256)
        mapper = p.PaletteMapper(palette)
        alpha_size = 0 if set(image.data[3::4]) == {255} else 8
        levels = image.mip_chain(levels=min(image.width, image.height).bit_length())
        pixels = [bytes(mapper.map_image(level.data)) + (bytes(level.data[3::4]) if alpha_size else b'')
                  for level in levels]
        colors = [(b & 255) | ((g & 255) << 8) | ((r & 255) << 16) for r, g, b in palette]
        encoded = p.Blp.from_images(levels, compression=1, alpha_type=8, alpha_size=alpha_size,
                                    palette=colors, payloads=pixels).serialize()
        assert len(encoded) <= 0xfffff, 'component buffer size overlaps native flags'
        decoded = p.Blp.parse(encoded).decode_level(0)
        assert bytes(decoded.data[3::4]) == bytes(image.data[3::4]), 'component alpha changed'
        assets[key] = encoded
        report[key] = {'source_bytes': len(payload), 'converted_bytes': len(encoded),
                       'width': image.width, 'height': image.height, 'alpha_size': alpha_size}
    assert len(report) == 25
    return report


def separate_bone_track_arrays(payload):
    """The native reader rebases outer arrays in place; each bone track needs its own metadata."""
    count, offset = struct.unpack_from('<2I', payload, 0x2c)
    assert offset+count*88 <= len(payload)
    result, seen, changes = bytearray(payload), set(), []
    for bone in range(count):
        for track in (16, 36, 56):
            for array in (4, 12):
                field = offset+bone*88+track+array
                length, start = struct.unpack_from('<2I', payload, field)
                if not length:
                    continue
                assert start+length*8 <= len(payload)
                if start in seen:
                    new = len(result)
                    result.extend(payload[start:start+length*8])
                    struct.pack_into('<I', result, field+4, new)
                    changes.append((bone, track, array, start, new, length))
                seen.add(start)
    return bytes(result), changes


def stage():
    STAGE.mkdir(parents=True, exist_ok=True)
    baseline = {name: p._full_table(p.CLIENT_DEFAULT/'Data', name)[0] for name in TABLES}
    output = tables(baseline)
    assets = {}
    for path in (SOURCE/'Character/Vrykul/Female').iterdir():
        if path.suffix.lower() in ('.m2', '.skin', '.anim'):
            assets[str(Path(MODEL).parent/path.name)] = path.read_bytes()
        elif path.suffix.lower() == '.blp':
            assets[str(path.relative_to(SOURCE))] = path.read_bytes()
    for folder in ('creature', 'ITEM'):
        for path in (SOURCE/folder).rglob('*'):
            if path.is_file() and (folder == 'creature' or '_vrf' in path.name.casefold()):
                assets[str(path.relative_to(SOURCE))] = path.read_bytes()
    isolate_effect(assets)
    assets[MODEL], _ = separate_bone_track_arrays(assets[MODEL])
    normalize_components(assets)
    read = lambda key: p._effective_file(p.CLIENT_DEFAULT/'Data', key)[0]
    model = parse_m2(assets[MODEL])
    for texture in model.textures:
        if texture['type'] == 0 and texture['filename'] and texture['filename'] not in assets:
            read(texture['filename'])
    catalog = catalogs(assets)
    original_glue = {name: read(p.GLUE_ROOT+name) for name in o.GLUE_PATCHERS}
    patched = {p.GLUE_ROOT+name: glue(name, data) for name, data in original_glue.items()}
    for folder, data in (('baseline-tables', baseline), ('tables', output)):
        for name, payload in data.items():
            path = STAGE/folder/(name+'.dbc')
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(payload)
    before_server = {}
    for name in SERVER:
        source = p.RawWdbc(output[name])
        base = (p.SERVER_DBC_ROOT/(name+'.dbc')).read_bytes()
        table = p.RawWdbc(base)
        before_server[name] = p.sha256(p.SERVER_DBC_ROOT/(name+'.dbc'))
        old_records = p.RawWdbc(baseline[name]).records
        selected = source.records[len(old_records):]
        if name == 'ChrRaces':
            selected = [r for r in source.records if p._value(r, 0) == 61]
            target_rows = [p._replace(r, 20, 4, DISPLAY_ID) if p._value(r, 0) in (56, 57)
                           else r for r in table.records]
            assert not any(p._value(r, 0) == 61 for r in target_rows)
        else:
            target_rows = list(table.records)
            p._ensure_id_free(base, name, {p._value(r, 0) for r in selected})
        pool = bytearray(table.strings)
        additions = [p._clone_strings(name, source, r, pool) for r in selected]
        for folder, payload in (('baseline-server', base), ('server', table.build(target_rows+additions, bytes(pool)))):
            path = STAGE/folder/(name+'.dbc')
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(payload)
    spec = {'name': 'Ogre', 'race_id': 61, 'faction': 'alliance', 'donor_start_race': 1, 'donor_totem_race': 11}
    sql = o.build_sql(spec) + o.CHRRACES_TEMPLATE.format(race=61, faction_template=1,
        male_display=60053, female_display=60054, prefix='Og', base_language=7,
        file_string='OgreAlliance', alliance=0, name='Ogre')
    sql = sql.rstrip()+'\n\nUPDATE `chrraces_dbc` SET `FemaleDisplayId` = 60060 WHERE `ID` IN (56, 57);\n'
    MIGRATION.write_text(sql.rstrip()+'\n', encoding='utf-8', newline='\n')
    for name, payload in catalog.items():
        (STAGE/name).write_bytes(payload)
        path = STAGE/'baseline'/name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((p.CLIENT_DEFAULT/name).read_bytes())
    for name, payload in original_glue.items():
        path = STAGE/'baseline-glue'/name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
    updates = {**patched, **{p.DBC_ROOT+name+'.dbc': data for name, data in output.items()}}
    storm = o.Storm(p.DLL_DEFAULT)
    before, after = {}, {}
    for relative in (p.GLOBAL_ARCHIVE_REL, p.LOCALE_ARCHIVE_REL):
        before[str(relative)] = p.sha256(p.CLIENT_DEFAULT/relative)
        target = STAGE/'client'/relative
        target.parent.mkdir(parents=True, exist_ok=True)
        o.rebuild_archive_replacing(storm, p.CLIENT_DEFAULT/relative, target, updates)
        assert target.stat().st_size < 0x80000000
        after[str(relative)] = p.sha256(target)
        print('STAGED', relative, flush=True)
    assert not (p.CLIENT_DEFAULT/ASSET).exists(), 'asset archive already exists'
    storm.create_archive(STAGE/'client'/ASSET, assets)
    after[str(ASSET)] = p.sha256(STAGE/'client'/ASSET)
    old.save(STAGE/'report.json', {'before': before, 'archives': after, 'server_before': before_server,
        'catalog_before': {name: p.sha256(STAGE/'baseline'/name) for name in catalog},
        'catalog_after': {name: p.sha256(STAGE/name) for name in catalog},
        'exe_sha256': p.sha256(p.CLIENT_DEFAULT/'Wow.exe'), 'migration': str(MIGRATION),
        'migration_sha256': p.sha256(MIGRATION), 'status': 'staged_awaiting_authorized_builds'})
    check()


def check():
    report = p.load_json(STAGE/'report.json')
    storm = o.Storm(p.DLL_DEFAULT)
    for relative, expected in report['archives'].items():
        assert p.sha256(STAGE/'client'/relative) == expected
    for name in TABLES:
        baseline = p.RawWdbc((STAGE/'baseline-tables'/(name+'.dbc')).read_bytes())
        current = p.RawWdbc((STAGE/'tables'/(name+'.dbc')).read_bytes())
        if name == 'ChrRaces':
            for original in baseline.records:
                row = next(r for r in current.records if p._value(r, 0) == p._value(original, 0))
                assert row == (p._replace(original, 20, 4, DISPLAY_ID)
                               if p._value(original, 0) in (56, 57) else original)
        else:
            assert current.records[:len(baseline.records)] == baseline.records, name
        assert current.strings.startswith(baseline.strings), name
        if name not in ('CharBaseInfo', 'CharacterFacialHairStyles'):
            ids = [p._value(r, 0) for r in current.records]
            assert len(ids) == len(set(ids)), name+' duplicate IDs'
    data = (STAGE/'tables/CharSections.dbc').read_bytes()
    for race in (56, 57):
        rows = [r for r in p._table_rows_for_race(data, 'CharSections', race) if p._value(r, 8) == 1]
        assert len(rows) == 48
        for skin in range(6):
            for hair in range(5):
                for color in range(5):
                    assert any(p._value(r, 12) == 0 and p._value(r, 36) == skin for r in rows)
                    assert any(p._value(r, 12) == 3 and p._value(r, 32) == hair
                               and p._value(r, 36) == color for r in rows)
    assert len(p._table_rows_for_race(data, 'CharSections', 61)) == 294
    for relative in (p.GLOBAL_ARCHIVE_REL, p.LOCALE_ARCHIVE_REL):
        handle = storm.open_archive(STAGE/'client'/relative)
        try:
            for name in TABLES:
                expected = o.order_charsections_entry(p.DBC_ROOT+name+'.dbc',
                    (STAGE/'tables'/(name+'.dbc')).read_bytes())
                assert storm.read(handle, p.DBC_ROOT+name+'.dbc') == expected
            for name in o.GLUE_PATCHERS:
                ast.parse(storm.read(handle, p.GLUE_ROOT+name).decode('utf-8-sig'))
        finally:
            storm.dll.SFileCloseArchive(handle)
    print('CHECKED female Vrykul choices, Alliance Ogre, unchanged old rows and archive readback', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('configure', 'stage', 'check'))
    globals()[parser.parse_args().action]()
