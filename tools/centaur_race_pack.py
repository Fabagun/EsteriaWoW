"""Stage both Centaur factions against the effective client/server data; never build or install."""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import struct

import centaur_racials
import centaur_source
import creature_race_pack
import drakkin_drakonid_racials as racial_data
import ogre_furbolg_race_pack as o
import retroported_race_pack as p
import sethrak_race_pack as shared

WORK = centaur_source.WORK
STAGE = WORK / 'stage'
SPECS = ((73, 'alliance', 1), (74, 'horde', 2))
CLASSES = (1, 2, 3, 4, 5, 6, 7, 8, 9, 11)
MIGRATION = p.ROOT / 'data/sql/updates/pending_db_world/rev_20261020020000000_centaur.sql'


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def json_save(path, data):
    centaur_source.save(path, data)


def ranges(race):
    index = race - 73
    start = 1121300 + index * 1000
    return {'CreatureModelData': {'male': 120083 + index * 2, 'female': 120084 + index * 2},
            'CreatureDisplayInfo': {'male': 60074 + index * 2, 'female': 60075 + index * 2},
            'CharSections': [start, start + 999], 'CharHairGeosets': [start, start + 99],
            'BarberShopStyle': [start, start + 199], 'CharStartOutfit': [22240 + index * 20, 22259 + index * 20],
            'NameGen': [105000 + index * 3000, 107999 + index * 3000]}


def manifest(spec):
    race, faction, donor = spec
    bounds = ranges(race)
    return {'schema_version': 1, 'slug': 'centaur_' + faction, 'name': 'Centaur', 'race_ids': [race],
            'enum': 'RACE_CENTAUR_' + faction.upper(), 'faction': faction, 'source_race_id': donor,
            'legacy_mask_race': donor, 'visual_base_race': 11, 'helmet_prefix': 'Dr',
            'client_file_strings': {str(race): 'Centaur' + faction.title()},
            'glue_token': ('Centaur' + faction).upper(), 'start_profile': 'elwynn' if donor == 1 else 'durotar',
            'donor_totem_race': donor, 'classes': list(CLASSES),
            'source_patch_root': str(WORK / 'source'), 'runtime_patch_root': str(STAGE / 'assets'),
            'models': {name: {'model_id': bounds['CreatureModelData'][name],
                             'display_id': bounds['CreatureDisplayInfo'][name],
                             'model_path': f'retail\\centaur\\{centaur_source.MODELS[sex]}.m2'}
                       for sex, name in enumerate(('male', 'female'))},
            'appearance': {'mode': 'native-stock-five-byte-v1', 'source': 'retail-centaur2',
                           'supported_genders': [0, 1], 'hide_helm': False,
                           'profiles': {str(sex): {
                               'capacities': [16, 1, 14 if sex else 9, 1, 1 if sex else 8],
                               'descriptors': [[0, 16, 1], [2, 14 if sex else 9, 1]] +
                                   ([] if sex else [[4, 8, 1]]),
                               'options': [{'label': 'Skin Color', 'choices': list(range(16))},
                                           {'label': 'Head Style', 'choices': [0] + list(range(1001, 1014 if sex else 1009))}]
                                   + ([] if sex else [{'label': 'Facial Hair', 'choices': [0] + list(range(101, 108))}])}
                                        for sex in (0, 1)}},
            'random_playerbot_enabled': False,
            'custom_racial_spells': [ability[0] for ability in centaur_racials.ABILITIES]}


def ownership():
    allocation = p.load_json(p.ALLOCATION_PATH)
    registry = p.load_json(p.ROOT / 'modules/mod-custom-server/data/races/race_registry.json')
    for race, faction, _ in SPECS:
        slug = 'centaur_' + faction
        assert not any(race in ids for owner, ids in allocation['race_ids'].items() if owner != slug)
        assert not any(row['id'] == race for row in registry['npc_only'])
        assert all(row['species_key'] == slug for row in registry['playable'] if row['id'] == race)
        for owner, bounds in allocation['race_allocations'].items():
            if owner == slug:
                assert bounds == ranges(race)
                continue
            for table, values in ranges(race).items():
                previous = bounds.get(table)
                if isinstance(previous, list):
                    assert max(values[0], previous[0]) > min(values[1], previous[1]), (owner, table)
                elif isinstance(previous, dict):
                    assert not ((set(values.values()) - {0}) & (set(previous.values()) - {0})), (owner, table)
    return allocation, registry


def reserve():
    allocation, registry = ownership()
    for spec in SPECS:
        race, faction, donor = spec
        data = manifest(spec)
        entry = {'id': race, 'species_key': data['slug'], 'display_name': 'Centaur', 'faction': faction,
                 'species_selection': True, 'start_profile': data['start_profile'], 'asset_owner': 'native_centaur',
                 'legacy_mask_race': donor, 'visual_base_race': 11, 'supported_genders': [0, 1]}
        old = next((row for row in registry['playable'] if row['id'] == race), None)
        assert old is None or old == entry
        if old is None:
            registry['playable'].append(entry)
        allocation['race_ids'][data['slug']] = [race]
        allocation['race_allocations'][data['slug']] = ranges(race)
        for table, values in ranges(race).items():
            maximum = values[1] if isinstance(values, list) else max(values.values())
            allocation['dbc_ranges'][table][1] = max(allocation['dbc_ranges'][table][1], maximum)
        json_save(p.manifest_path(data['slug']), data)
    pair = {'species_key': 'centaur', 'alliance_id': 73, 'horde_id': 74}
    assert all(row == pair for row in registry['faction_pairs'] if row['species_key'] == 'centaur')
    if pair not in registry['faction_pairs']:
        registry['faction_pairs'].append(pair)
    registry['sources']['native_centaur'] = str(STAGE / 'assets')
    json_save(p.ALLOCATION_PATH, allocation)
    json_save(p.ROOT / 'modules/mod-custom-server/data/races/race_registry.json', registry)
    creature_race_pack.header()


def tables(baseline):
    result = dict(baseline)
    for spec in SPECS:
        race, faction, donor = spec
        data, bounds = manifest(spec), ranges(race)
        source = p.RawWdbc(result['ChrRaces'])
        pool = bytearray(source.strings)
        row = p._clone_strings('ChrRaces', source,
                              next(row for row in source.records if p._value(row, 0) == 11), pool)
        for field, value in ((0, race), (1, 14), (2, donor), (4, bounds['CreatureDisplayInfo']['male']),
                             (5, bounds['CreatureDisplayInfo']['female']), (7, 7 if donor == 1 else 1),
                             (12, 0), (13, 0 if donor == 1 else 1), (68, 0)):
            row = p._replace(row, field * 4, 4, value)
        for field, value in ((6, 'Dr'), (11, 'Centaur' + faction.title())):
            row = p._set_string(row, field, pool, value)
        for field in (*range(14, 30), *range(31, 47), *range(48, 64)):
            row = p._set_string(row, field, pool, 'Centaur')
        result['ChrRaces'] = shared.append_rows(result['ChrRaces'], 'ChrRaces', [row], pool)
        for sex, name in enumerate(('male', 'female')):
            for table, donor_id, identifier in (
                    ('CreatureModelData', 3654, bounds['CreatureModelData'][name]),
                    ('CreatureDisplayInfo', 60022, bounds['CreatureDisplayInfo'][name])):
                source = p.RawWdbc(result[table])
                pool = bytearray(source.strings)
                row = p._clone_strings(table, source,
                                      next(row for row in source.records if p._value(row, 0) == donor_id), pool)
                row = p._replace(row, 0, 4, identifier)
                if table == 'CreatureModelData':
                    row = p._replace(row, 4, 4, p._value(row, 4) | 0x804)
                    row = p._set_string(row, 2, pool, data['models'][name]['model_path'])
                else:
                    row = p._replace(row, 4, 4, bounds['CreatureModelData'][name])
                    row = row[:16] + struct.pack('<f', 1.0) + row[20:]
                    for offset in (12, 24, 28, 32):
                        row = p._replace(row, offset, 4, 0)
                result[table] = shared.append_rows(result[table], table, [row], pool)
        result['CharBaseInfo'] = p._build_char_base_info(result['CharBaseInfo'], data)
        for table, first in (('CharStartOutfit', bounds['CharStartOutfit'][0]), ('NameGen', bounds['NameGen'][0])):
            source = p.RawWdbc(result[table])
            pool = bytearray(source.strings)
            if table == 'CharStartOutfit':
                donors = {(row[5], row[6]): row for row in reversed(source.records)
                          if row[4] == donor and row[5] in CLASSES and row[6] in (0, 1) and row[7] == 0}
                assert set(donors) == {(cl, sex) for cl in CLASSES for sex in (0, 1)}
                additions = [p._replace(p._replace(donors[key], 0, 4, first + i), 4, 1, race)
                             for i, key in enumerate(sorted(donors))]
            else:
                donors = [row for row in source.records if p._value(row, 8) == donor]
                assert donors and len(donors) <= 3000
                additions = [p._replace(p._replace(p._clone_strings(table, source, row, pool),
                                                 0, 4, first + i), 8, 4, race) for i, row in enumerate(donors)]
            result[table] = shared.append_rows(result[table], table, additions, pool)
        sections, hair, facial = [], [], []
        for sex in (0, 1):
            for color in range(16):
                for kind in (0, 1, 4):
                    sections.append(struct.pack('<10I', bounds['CharSections'][0] + len(sections), race,
                                                sex, kind, 0, 0, 0, 17, 0, color))
            for kind in (2, 3):
                sections.append(struct.pack('<10I', bounds['CharSections'][0] + len(sections), race,
                                            sex, kind, 0, 0, 0, 17, 0, 0))
            hair.append(struct.pack('<6I', bounds['CharHairGeosets'][0] + sex, race, sex, 0, 0, 1))
            facial.append(struct.pack('<8I', race, sex, 0, 0, 0, 0, 0, 0))
        for table, rows in (('CharSections', sections), ('CharHairGeosets', hair),
                            ('CharacterFacialHairStyles', facial)):
            result[table] = shared.append_rows(result[table], table, rows)
        source = p.RawWdbc(result['BarberShopStyle'])
        barber = []
        for sex in (0, 1):
            for kind, count in ((0, 1), (2, 1), (3, 16)):
                template = next(row for row in source.records if p._value(row, 4) == kind)
                for value in range(count):
                    row = template
                    for offset, number in ((0, bounds['BarberShopStyle'][0] + len(barber)),
                                           (148, race), (152, sex), (156, value)):
                        row = p._replace(row, offset, 4, number)
                    barber.append(row)
        result['BarberShopStyle'] = shared.append_rows(result['BarberShopStyle'], 'BarberShopStyle', barber)
    result['CharSections'] = o.order_charsections_entry(p.DBC_ROOT + 'CharSections.dbc', result['CharSections'])
    result['Spell'], _ = centaur_racials.generate(result['Spell'])
    return result


def glue(baseline):
    result = {name: raw.decode('utf-8-sig').replace('\r\n', '\n') for name, raw in baseline.items()}
    for race, faction, donor in SPECS:
        token, key = 'Centaur' + faction.title(), ('Centaur' + faction).upper()
        background = 'HUMAN' if donor == 1 else 'ORC'
        insertions = (
            ('CharacterInfo.lua', 'local EXACT_RACE_DATA = {\n',
             f'    [{race}] = {{glueString="{key}", name="Centaur", faction="{faction.title()}", '
             f'fileString="{token}"}},\n'),
            ('CharacterCreate.lua', 'local RACE_BACKGROUND_KEYS = {\n', f'        ["{key}"] = "{background}",\n'),
            ('GlueParent.lua', '    local ' + faction + 'Races = {\n', f'        ["{key}"] = true,\n'),
            ('ECS_Schema.lua', 'S.RaceOverride = {\n',
             f'    [{race}] = {{name="Centaur", faction={donor}, artKey="{token}"}},\n'),
            ('ECS_Schema.lua', 'S.RaceByModelKey = {\n',
             f'    {{"{key}", {{name="Centaur", faction={donor}, artKey="{token}"}}}},\n'),
            ('ECS_Schema.lua', 'S.PortraitArtKeys = {\n', f'    {token}=true,\n'))
        for name, anchor, text in insertions:
            result[name] = o._insert_once(result[name], anchor, text, 'Centaur ' + name)
        result['CharacterInfo.lua'] += (f'\nRaceInfoByFileString.{key}={{Name="Centaur", '
            f'Description="Centaur of the {faction.title()}. Gallop across the land and take bird form in the sky."}};\n')
        result['GlueStrings.lua'] += f'\n{key}="Centaur"; {key}_MALE={key}; {key}_FEMALE={key};\n'
        for sex in ('MALE', 'FEMALE'):
            entry = (f'    ["{key}_{sex}"] = "Interface\\\\Glues\\\\CharacterCreate\\\\'
                     f'UI-CharacterCreate-{token}{sex.title()}",\n')
            result['CharacterCreate.lua'] = o._insert_once(result['CharacterCreate.lua'],
                'RACE_ICON_TEXTURES = {\n', entry, 'Centaur portrait')
            result['CharacterCreate.lua'] += f'\nRACE_ICON_TCOORDS["{key}_{sex}"]=RACE_ICON_TCOORDS["{background}_{sex}"];\n'
        result['GlueParent.lua'] += ''.join(f'\n{table}.{key}={table}.{background};'
            for table in ('CharModelFogInfo', 'CharModelGlowInfo', 'GlueAmbienceTracks')) + '\n'
    anchor = 'race == 71 or race == 72)) then'
    assert result['ECS_Integrate.lua'].count(anchor) == 1, 'Roster race list changed'
    result['ECS_Integrate.lua'] = result['ECS_Integrate.lua'].replace(anchor,
        'race == 71 or race == 72 or race == 73 or race == 74)) then')
    anchor = 'raceModel == "SLIMEGIANTALLIANCE"'
    assert result['CharacterSelect.lua'].count(anchor) == 1
    result['CharacterSelect.lua'] = result['CharacterSelect.lua'].replace(anchor,
        anchor + ' or raceModel == "CENTAURALLIANCE" or raceModel == "CENTAURHORDE"')
    from lupa.lua51 import LuaRuntime
    compile_chunk = LuaRuntime().eval('function(s) local f,e=loadstring(s); assert(f,e); end')
    for text in result.values():
        compile_chunk(text)
    return {name: text.encode() for name, text in result.items()}


def model_info_sql():
    rows = []
    for race, _, _ in SPECS:
        displays = ranges(race)['CreatureDisplayInfo']
        rows.extend(f"({displays[sex]}, 0.5, 1.5, {gender}, {displays[other]})"
                    for gender, sex, other in ((0, 'male', 'female'), (1, 'female', 'male')))
    return ('-- Restore the original player gender after a gender-neutral bird transformation.\n'
            'DELETE FROM `creature_model_info` WHERE `DisplayID` IN (60074, 60075, 60076, 60077);\n'
            'INSERT INTO `creature_model_info`\n'
            '(`DisplayID`, `BoundingRadius`, `CombatReach`, `Gender`, `DisplayID_Other_Gender`) VALUES\n'
            + ',\n'.join(rows) + ';\n')


def migration(spell_baseline):
    _, sql = centaur_racials.generate(spell_baseline)
    for spec in SPECS:
        race, faction, donor = spec
        bounds = ranges(race)
        sql += o.build_sql({'name': 'Centaur', 'race_id': race, 'faction': faction,
                            'donor_start_race': donor, 'donor_totem_race': donor})
        spells = racial_data.HUMAN_RACIALS if donor == 1 else racial_data.ORC_RACIALS
        sql += 'DELETE FROM `custom_race_start_spell_exclude` WHERE `race` = @RACE;\n'
        sql += 'INSERT INTO `custom_race_start_spell_exclude` (`race`, `spell`, `comment`) VALUES\n'
        sql += ',\n'.join(f"(@RACE, {spell}, 'Donor racial: {name}')" for spell, name in spells) + ';\n'
        sql += 'DELETE FROM `custom_race_start_skill_exclude` WHERE `race` = @RACE;\n'
        sql += 'INSERT INTO `custom_race_start_skill_exclude` (`race`, `skill`, `comment`) VALUES\n'
        sql += f"(@RACE, {754 if donor == 1 else 125}, 'Donor racial skill');\n"
        sql += o.CHRRACES_TEMPLATE.format(race=race, faction_template=donor,
            male_display=bounds['CreatureDisplayInfo']['male'], female_display=bounds['CreatureDisplayInfo']['female'],
            prefix='Dr', base_language=7 if donor == 1 else 1, file_string='Centaur' + faction.title(),
            alliance=0 if donor == 1 else 1, name='Centaur')
    return sql.replace('ogre_furbolg_race_pack.py', 'centaur_race_pack.py').rstrip() + '\n' + model_info_sql()


def clone_server_row(name, source, row, pool):
    clone = p._clone_strings(name, source, row, pool)
    if name == 'Spell':
        for field in p.SPELL_STRING_FIELDS:
            value = p._string(source.strings, p._value(row, field * 4)).decode('utf-8')
            clone = p._set_string(clone, field, pool, value)
    return clone


def stage():
    ownership()
    names = (*shared.TABLES, 'Spell')
    with p.ClientFiles(str(p.CLIENT_DEFAULT / 'Data'), 'enUS') as files:
        baseline = {name: files.find(p.DBC_ROOT + name + '.dbc')[0] for name in names}
        original = {name: files.find(p.GLUE_ROOT + name)[0] for name in shared.GLUE}
    for name, data in {**{n + '.dbc': b for n, b in baseline.items()}, **original}.items():
        path = STAGE / 'baseline' / name
        assert not path.exists() or path.read_bytes() == data, 'Baseline changed: ' + name
        save(path, data)
    output, patched = tables(baseline), glue(original)
    for name, data in output.items():
        save(STAGE / 'client-dbc' / (name + '.dbc'), data)
    for name, data in patched.items():
        save(STAGE / 'glue' / name, data)
    for name in (*shared.SERVER_TABLES, 'Spell'):
        base = (p.SERVER_DBC_ROOT / (name + '.dbc')).read_bytes()
        save(STAGE / 'baseline-server' / (name + '.dbc'), base)
        target, source = p.RawWdbc(base), p.RawWdbc(output[name])
        if name == 'Spell':
            ids = {a[0] for a in centaur_racials.ABILITIES}
        elif name in ('CreatureModelData', 'CreatureDisplayInfo'):
            ids = {value for spec in SPECS for value in ranges(spec[0])[name].values()}
        else:
            ids = {p._value(row, 0) for spec in SPECS
                   for row in p._table_rows_for_race(output[name], name, spec[0])}
        p._ensure_id_free(base, name, ids)
        pool = bytearray(target.strings)
        additions = [clone_server_row(name, source, row, pool) for row in source.records if p._value(row, 0) in ids]
        save(STAGE / 'server/dbc' / (name + '.dbc'), target.build([*target.records, *additions], bytes(pool)))
    sql = migration(baseline['Spell']).encode()
    save(MIGRATION, sql)
    save(STAGE / 'centaur.sql', sql)
    for spec in SPECS:
        json_save(STAGE / 'manifests' / (manifest(spec)['slug'] + '.json'), manifest(spec))
    for folder, source_folder, tables_to_check in (('client-dbc', 'baseline', names),
            ('server/dbc', 'baseline-server', (*shared.SERVER_TABLES, 'Spell'))):
        for name in tables_to_check:
            before = p.RawWdbc((STAGE / source_folder / (name + '.dbc')).read_bytes())
            after = p.RawWdbc((STAGE / folder / (name + '.dbc')).read_bytes())
            # Strings are rebased for added rows; every old record and its pool must be byte-identical.
            assert not (Counter(before.records) - Counter(after.records)), (folder, name)
            assert after.strings.startswith(before.strings), (folder, name)
    json_save(STAGE / 'report.json', {'race_ids': [73, 74], 'installed': False, 'live_accepted': False,
        'source_build': centaur_source.BUILD, 'native_profile': 0xf0020000,
        'source_models': centaur_source.MODELS, 'flight_visual': 'bird transformation',
        'archive_baselines': {str(rel): p.sha256(p.CLIENT_DEFAULT / rel)
                              for rel in (p.GLOBAL_ARCHIVE_REL, p.LOCALE_ARCHIVE_REL)},
        'client_dbc_sha256': {name: hashlib.sha256(data).hexdigest() for name, data in output.items()},
        'remaining': ['native client build', 'server build', 'equipment visual acceptance', 'live acceptance']})
    print('PASS staged Centaur client/server data, Lua syntax, travel spells and preserved baseline records:', STAGE)


def package():
    import race_portrait_pack as portraits
    from PIL import Image

    report = p.load_json(STAGE / 'report.json')
    assert p.load_json(WORK / 'inventory.json')['complete'], 'Source closure is incomplete'
    with p.ClientFiles(str(p.CLIENT_DEFAULT / 'Data'), 'enUS') as files:
        template = files.find(portraits.ICON_TEMPLATE_ENTRY)[0]
        ring = portraits.ring_layer(portraits.decode_client_blp(files.find(portraits.RING_ENTRY)[0]))
    for sex, name in enumerate(('Male', 'Female')):
        art = Image.open(WORK / 'preview' / str(sex) / 'bare/portrait.png').convert('RGBA')
        art = art.resize((64, 64), Image.Resampling.LANCZOS)
        art.putalpha(portraits.circular_mask())
        plain = portraits.encode_portrait(art, template)
        icon = portraits.encode_portrait(portraits.compose_race_icon(art, ring), template)
        for _, faction, _ in SPECS:
            token = 'Centaur' + faction.title()
            paths = {portraits.CREATOR_ICON_ROOT + f'UI-CharacterCreate-{token}{name}.blp': icon,
                portraits.CHARACTER_FRAME_ROOT + f'TemporaryPortrait-{name}-{token}.blp': plain,
                f'Interface\\Glues\\CharacterSelect\\ECS-Portrait-{token}{name}.blp': plain}
            for key, data in paths.items():
                save(STAGE / 'assets' / Path(key.replace('\\', '/')), data)
    from datetime import datetime
    destination = WORK / 'packages' / datetime.now().strftime('%Y%m%d-%H%M%S')
    destination.mkdir(parents=True, exist_ok=False)
    assets = {str(path.relative_to(STAGE / 'assets')).replace('/', '\\'): path.read_bytes()
              for path in (STAGE / 'assets').rglob('*') if path.is_file()}
    # Overlay is intentionally uninstalled: precedence and native/server binaries must be matched first.
    entries = dict(assets)
    entries.update({p.DBC_ROOT + path.name: path.read_bytes() for path in (STAGE / 'client-dbc').glob('*.dbc')})
    entries.update({p.GLUE_ROOT + path.name: path.read_bytes() for path in (STAGE / 'glue').glob('*.lua')})
    archive = destination / 'centaur-staged-overlay.MPQ'
    storm = p.Storm(p.DLL_DEFAULT)
    storm.create_archive(archive, entries)
    handle = storm.open_archive(archive)
    try:
        for name, data in entries.items():
            assert storm.read(handle, name) == data, name
    finally:
        storm.dll.SFileCloseArchive(handle)
    json_save(destination / 'package-receipt.json', {**report, 'archive': str(archive),
        'archive_sha256': p.sha256(archive), 'entry_count': len(entries), 'all_entries_readback_verified': True,
        'installable': False, 'required': ['compile Centaur native adapter and server module',
            'native adapter fixture tests', 'posed equipment and action validation',
            'coordinated backed-up deployment and live client acceptance']})
    print('PACKAGED and read back every entry:', archive)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('reserve', 'stage', 'package'))
    args = parser.parse_args()
    globals()[args.action]()
