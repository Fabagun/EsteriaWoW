"""Stage Slime Giant 175382 for the native retail renderer; never install or convert assets."""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import struct
import shutil
from datetime import datetime

import drakkin_drakonid_racials as racial_data
import ogre_furbolg_race_pack as o
import retroported_race_pack as p
import sethrak_race_pack as shared

WORK = Path('G:/RetroportWork/slime-giant-175382')
STAGE = WORK / 'stage'
MIGRATION = p.ROOT / 'data/sql/updates/pending_db_world/rev_20261020010000000_slime_giant.sql'
SPECS = ((71, 'alliance', 1, 120081, 60072), (72, 'horde', 2, 120082, 60073))
MODEL = 'retail\\slimegiant\\3490792.m2'
FALLBACK_MODEL = 'CHARACTER\\Naga_\\male\\kultiranmale.m2'
SOURCE_COLORS = ('Green', 'Amber', 'Mauve', 'Red', 'Gold')
CUSTOM_COLORS = tuple('Amber (Custom)' if row['name'] == 'amber' else row['name'].replace('_', ' ').title()
                      for row in p.load_json(p.ROOT / 'SlimeSkeleton/ColorVariants/manifest.json')['variants'])
COLORS = SOURCE_COLORS + CUSTOM_COLORS
CLASSES = (1, 2, 3, 4, 5, 6, 7, 8, 9, 11)
CAPACITIES = (len(COLORS), 2, 1, 1, 1)
TABLES = shared.TABLES
GLUE = shared.GLUE
SERVER_TABLES = shared.SERVER_TABLES


def digest(data):
    return hashlib.sha256(data).hexdigest()


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def pinned(path, data):
    if path.exists():
        assert path.read_bytes() == data, 'Baseline changed: ' + str(path)
    else:
        save(path, data)
    return data


def ranges(race):
    index = race - 71
    start = 1119300 + index * 1000
    return {'CreatureModelData': {'male': 120081 + index},
            'CreatureDisplayInfo': {'male': 60072 + index, 'female': 0},
            'CharSections': [start, start + 999], 'CharHairGeosets': [start, start + 99],
            'BarberShopStyle': [start, start + 99],
            'CharStartOutfit': [22220 + index * 10, 22229 + index * 10],
            'NameGen': [99000 + index * 3000, 101999 + index * 3000]}


def manifest(spec):
    race, faction, donor, model, display = spec
    return {'schema_version': 1, 'slug': 'slime_giant_' + faction, 'name': 'Slime Giant',
            'race_ids': [race], 'enum': 'RACE_SLIME_GIANT_' + faction.upper(), 'faction': faction,
            'source_race_id': donor, 'legacy_mask_race': donor, 'visual_base_race': 29,
            'helmet_prefix': 'Kt', 'client_file_strings': {str(race): 'SlimeGiant' + faction.title()},
            'glue_token': ('SlimeGiant' + faction).upper(),
            'start_profile': 'elwynn' if donor == 1 else 'durotar', 'donor_totem_race': donor,
            'classes': list(CLASSES), 'models': {'male': {'model_id': model, 'display_id': display,
                                                       'model_path': MODEL}},
            'appearance': {'mode': 'native-stock-five-byte-v1', 'source': 'retail-creature-175382',
                           'supported_genders': [0], 'hide_helm': False, 'profiles': {'0': {
                               'capacities': list(CAPACITIES), 'descriptors': [[0, len(COLORS), 1], [1, 2, 1]],
                               'options': [{'label': 'Slime Color', 'choices': list(COLORS)},
                                           {'label': 'Slime Drip', 'choices': ['Off', 'On']}]}}},
            'random_playerbot_enabled': False, 'custom_racial_spells': []}


def ownership():
    allocation = p.load_json(p.ALLOCATION_PATH)
    registry = p.load_json(p.ROOT / 'modules/mod-custom-server/data/races/race_registry.json')
    for row in registry['playable']:
        if row['id'] in (71, 72):
            assert row['species_key'] == 'slime_giant_' + ('alliance' if row['id'] == 71 else 'horde')
    assert not any(row['id'] in (71, 72) for row in registry['npc_only'])
    assert not any(set(ids) & {71, 72} for owner, ids in allocation['race_ids'].items()
                   if owner not in ('slime_giant_alliance', 'slime_giant_horde'))
    for race, *_ in SPECS:
        for owner, bounds in allocation['race_allocations'].items():
            if owner in ('slime_giant_alliance', 'slime_giant_horde'):
                continue
            for table, proposed in ranges(race).items():
                prior = bounds.get(table)
                if isinstance(prior, list) and isinstance(proposed, list):
                    assert max(prior[0], proposed[0]) > min(prior[1], proposed[1]), (owner, table)
                elif isinstance(prior, dict) and isinstance(proposed, dict):
                    assert not ((set(prior.values()) - {0}) & (set(proposed.values()) - {0})), (owner, table)
    return allocation


def reserve():
    allocation = ownership()
    path = p.ROOT / 'modules/mod-custom-server/data/races/race_registry.json'
    registry = p.load_json(path)
    for spec in SPECS:
        race, faction, donor = spec[:3]
        m = manifest(spec)
        slug = m['slug']
        entry = {'id': race, 'species_key': slug, 'display_name': 'Slime Giant', 'faction': faction,
                 'species_selection': True, 'start_profile': m['start_profile'],
                 'asset_owner': 'native_slime_giant', 'legacy_mask_race': donor, 'visual_base_race': 29,
                 'supported_genders': [0]}
        old = next((row for row in registry['playable'] if row['id'] == race), None)
        assert old is None or {**old, 'visual_base_race': 29} == entry, 'Race registry definition changed'
        if old is None:
            registry['playable'].append(entry)
        else:
            old.update(entry)
        allocation['race_ids'][slug] = [race]
        allocation['race_allocations'][slug] = ranges(race)
        for table, bounds in ranges(race).items():
            high = bounds[1] if isinstance(bounds, list) else max(bounds.values())
            allocation['dbc_ranges'][table][1] = max(allocation['dbc_ranges'][table][1], high)
        save(p.manifest_path(slug), (json.dumps(m, indent=2) + '\n').encode())
    pair = {'species_key': 'slime_giant', 'alliance_id': 71, 'horde_id': 72}
    assert all(row == pair for row in registry['faction_pairs'] if row['species_key'] == 'slime_giant')
    if pair not in registry['faction_pairs']:
        registry['faction_pairs'].append(pair)
    registry['sources']['native_slime_giant'] = str(STAGE / 'assets')
    save(p.ALLOCATION_PATH, (json.dumps(allocation, indent=2) + '\n').encode())
    save(path, (json.dumps(registry, indent=2) + '\n').encode())
    import creature_race_pack
    creature_race_pack.header()
    print('Reserved Slime Giant races 71/72 and generated server appearance bounds')


def tables(baseline):
    result = dict(baseline)
    for spec in SPECS:
        race, faction, donor, model_id, display_id = spec
        bounds = ranges(race)
        token = 'SlimeGiant' + faction.title()
        source = p.RawWdbc(result['ChrRaces'])
        row = next(row for row in source.records if p._value(row, 0) == 29)
        pool = bytearray(source.strings)
        row = p._clone_strings('ChrRaces', source, row, pool)
        for field, value in ((0, race), (1, 14), (2, donor), (4, display_id), (5, 0),
                             (7, 7 if donor == 1 else 1), (12, 0), (13, 0 if donor == 1 else 1), (68, 0)):
            row = p._replace(row, field * 4, 4, value)
        for field, value in ((6, 'Kt'), (11, token)):
            row = p._set_string(row, field, pool, value)
        for field in (*range(14, 30), *range(31, 47), *range(48, 64)):
            row = p._set_string(row, field, pool, 'Slime Giant')
        result['ChrRaces'] = shared.append_rows(result['ChrRaces'], 'ChrRaces', [row], pool)
        for table_name, source_id, new_id in (('CreatureModelData', 3654, model_id),
                                             ('CreatureDisplayInfo', 60022, display_id)):
            source = p.RawWdbc(result[table_name])
            pool = bytearray(source.strings)
            row = next(row for row in source.records if p._value(row, 0) == source_id)
            row = p._clone_strings(table_name, source, row, pool)
            row = p._replace(row, 0, 4, new_id)
            if table_name == 'CreatureModelData':
                row = p._replace(row, 4, 4, p._value(row, 4) | 0x804)
                row = p._set_string(row, 2, pool, FALLBACK_MODEL)
            else:
                row = p._replace(row, 4, 4, model_id)
                row = row[:16] + struct.pack('<f', 1.0) + row[20:]
            result[table_name] = shared.append_rows(result[table_name], table_name, [row], pool)
        result['CharBaseInfo'] = p._build_char_base_info(result['CharBaseInfo'], manifest(spec))
        for table_name, first_id in (('CharStartOutfit', bounds['CharStartOutfit'][0]),
                                      ('NameGen', bounds['NameGen'][0])):
            source = p.RawWdbc(result[table_name])
            pool = bytearray(source.strings)
            if table_name == 'CharStartOutfit':
                by_class = {row[5]: row for row in sorted(source.records, key=lambda row: p._value(row, 0))
                            if row[4] == donor and row[5] in CLASSES and row[6] == 0 and row[7] == 0}
                assert set(by_class) == set(CLASSES), 'Missing donor class outfit'
                rows = list(by_class.values())
                additions = [p._replace(p._replace(row, 0, 4, first_id + i), 4, 1, race)
                             for i, row in enumerate(sorted(rows, key=lambda row: row[5]))]
            else:
                rows = [row for row in source.records if p._value(row, 8) == donor and p._value(row, 12) == 0]
                assert rows and len(rows) <= 3000
                additions = [p._replace(p._replace(p._clone_strings(table_name, source, row, pool),
                             0, 4, first_id + i), 8, 4, race) for i, row in enumerate(rows)]
            result[table_name] = shared.append_rows(result[table_name], table_name, additions, pool)
        source = p.RawWdbc(result['CharSections'])
        pool, sections = bytearray(source.strings), []
        for color in range(len(COLORS)):
            for kind, style in ((0, 0), (1, 0), (1, 1), (4, 0)):
                row = struct.pack('<10I', bounds['CharSections'][0] + len(sections), race, 0,
                                  kind, 0, 0, 0, 1 if kind == 1 else 17, style, color)
                sections.append(row)
        for kind in (2, 3):
            sections.append(struct.pack('<10I', bounds['CharSections'][0] + len(sections), race,
                                        0, kind, 0, 0, 0, 17, 0, 0))
        result['CharSections'] = shared.append_rows(result['CharSections'], 'CharSections', sections, pool)
        result['CharHairGeosets'] = shared.append_rows(result['CharHairGeosets'], 'CharHairGeosets',
            [struct.pack('<6I', bounds['CharHairGeosets'][0], race, 0, 0, 0, 1)])
        result['CharacterFacialHairStyles'] = shared.append_rows(result['CharacterFacialHairStyles'],
            'CharacterFacialHairStyles', [struct.pack('<8I', race, 0, 0, 0, 0, 0, 0, 0)])
        source = p.RawWdbc(result['BarberShopStyle'])
        barber = []
        for kind, count in ((0, 1), (2, 1), (3, len(COLORS))):
            template = next(row for row in source.records if p._value(row, 4) == kind)
            for value in range(count):
                row = template
                for offset, number in ((0, bounds['BarberShopStyle'][0] + len(barber)),
                                       (148, race), (152, 0), (156, value)):
                    row = p._replace(row, offset, 4, number)
                barber.append(row)
        result['BarberShopStyle'] = shared.append_rows(result['BarberShopStyle'], 'BarberShopStyle', barber)
    result['CharSections'] = o.order_charsections_entry(p.DBC_ROOT + 'CharSections.dbc', result['CharSections'])
    return result


def repair_portrait_glue(result):
    """Use faction-specific Slime Giant art instead of the visual donor's portraits."""
    result = dict(result)
    for race, faction, donor, *_ in SPECS:
        token, key = 'SlimeGiant' + faction.title(), ('SlimeGiant' + faction).upper()
        for sex in ('MALE', 'FEMALE'):
            entry = f'    ["{key}_{sex}"] = "Interface\\\\Glues\\\\CharacterCreate\\\\UI-CharacterCreate-{token}Male",'
            if entry not in result['CharacterCreate.lua']:
                anchor = 'RACE_ICON_TEXTURES = {\n'
                assert result['CharacterCreate.lua'].count(anchor) == 1
                result['CharacterCreate.lua'] = result['CharacterCreate.lua'].replace(anchor, anchor + entry + '\n', 1)
        schema = result['ECS_Schema.lua']
        for pattern in (r'(\[' + str(race) + r'\]\s*=\s*\{[^\n]*artKey\s*=\s*)"[^"]+"',
                        r'(\{"' + key + r'",\s*\{[^\n]*artKey\s*=\s*)"[^"]+"'):
            schema, count = re.subn(pattern, lambda match: match[1] + '"' + token + '"', schema)
            assert count == 1, 'Slime Giant ECS identity changed: ' + token
        entry = '    ' + token + '=true,\n'
        if entry not in schema:
            anchor = 'S.PortraitArtKeys = {\n'
            assert schema.count(anchor) == 1
            schema = schema.replace(anchor, anchor + entry, 1)
        result['ECS_Schema.lua'] = schema
    return result


def glue(original):
    result = {name: data.decode('utf-8-sig').replace('\r\n', '\n') for name, data in original.items()}

    def insert(name, anchor, text):
        result[name] = o._insert_once(result[name], anchor, text, 'Slime Giant ' + name)

    assert 'EA_IS_RETAIL()' in result['CharacterCreate.lua'], 'Native retail customization panel is required'
    for race, faction, donor, *_ in SPECS:
        token, key = 'SlimeGiant' + faction.title(), ('SlimeGiant' + faction).upper()
        background, art = ('HUMAN', 'Human') if donor == 1 else ('ORC', 'Orc')
        insert('CharacterInfo.lua', 'local EXACT_RACE_DATA = {\n',
               f'    [{race}] = {{glueString="{key}", name="Slime Giant", faction="{faction.title()}", '
               f'fileString="{token}"}},\n')
        result['CharacterInfo.lua'] += (f'\nRaceInfoByFileString.{key} = {{Name="Slime Giant", '
            f'Description="Slime Giants who have joined the {faction.title()}."}};\n')
        result['CharacterCreate.lua'] += (f'\nRACE_ICON_TCOORDS["{key}_MALE"] = '
                                           f'RACE_ICON_TCOORDS["{background}_MALE"];\n')
        insert('CharacterCreate.lua', 'local RACE_BACKGROUND_KEYS = {\n', f'        ["{key}"] = "{background}",\n')
        insert('GlueParent.lua', '    local ' + faction + 'Races = {\n', f'        ["{key}"] = true,\n')
        result['GlueParent.lua'] += ''.join(f'\n{table}.{key}={table}.{background};'
            for table in ('CharModelFogInfo', 'CharModelGlowInfo', 'GlueAmbienceTracks')) + '\n'
        result['GlueStrings.lua'] += f'\n{key}="Slime Giant"; {key}_MALE={key};\n'
        insert('ECS_Schema.lua', 'S.RaceOverride = {\n',
               f'    [{race}] = {{name="Slime Giant", faction={donor}, artKey="{art}"}},\n')
        insert('ECS_Schema.lua', 'S.RaceByModelKey = {\n',
               f'    {{"{key}", {{name="Slime Giant", faction={donor}, artKey="{art}"}}}},\n')
    pattern = r'(function CharacterCreate_IsMaleOnlyRace\(race\)\n\s+return )([^;]+);'
    result['CharacterCreate.lua'], count = re.subn(pattern, r'\g<1>\g<2> or race == 71 or race == 72;',
                                                 result['CharacterCreate.lua'])
    assert count == 1, 'Male-only race helper changed'
    anchor = 'race == 69 or race == 70)) then'
    assert result['ECS_Integrate.lua'].count(anchor) == 1, 'Roster race list changed'
    result['ECS_Integrate.lua'] = result['ECS_Integrate.lua'].replace(anchor,
        'race == 69 or race == 70 or race == 71 or race == 72)) then')
    anchor = 'raceModel == "DRAKONIDALLIANCE"'
    assert result['CharacterSelect.lua'].count(anchor) == 1
    result['CharacterSelect.lua'] = result['CharacterSelect.lua'].replace(anchor,
        anchor + ' or raceModel == "SLIMEGIANTALLIANCE" or raceModel == "SLIMEGIANTHORDE"')
    result = repair_portrait_glue(result)
    from lupa.lua51 import LuaRuntime
    compile_chunk = LuaRuntime().eval('function(s) local f,e=loadstring(s); assert(f,e); end')
    for text in result.values():
        compile_chunk(text)
    return {name: text.encode() for name, text in result.items()}


def migration_sql():
    sql = ''
    for race, faction, donor, _, display in SPECS:
        sql += o.build_sql({'name': 'Slime Giant', 'race_id': race, 'faction': faction,
                            'donor_start_race': donor, 'donor_totem_race': donor})
        spells = racial_data.HUMAN_RACIALS if donor == 1 else racial_data.ORC_RACIALS
        skill = 754 if donor == 1 else 125
        sql += 'DELETE FROM `custom_race_start_spell_exclude` WHERE `race` = @RACE;\n'
        sql += 'INSERT INTO `custom_race_start_spell_exclude` (`race`, `spell`, `comment`) VALUES\n'
        sql += ',\n'.join(f"(@RACE, {spell}, 'Donor racial: {name}')" for spell, name in spells) + ';\n'
        sql += 'DELETE FROM `custom_race_start_skill_exclude` WHERE `race` = @RACE;\n'
        sql += 'INSERT INTO `custom_race_start_skill_exclude` (`race`, `skill`, `comment`) VALUES\n'
        sql += f"(@RACE, {skill}, 'Donor racial skill');\n\n"
        sql += o.CHRRACES_TEMPLATE.format(race=race, faction_template=donor, male_display=display,
            female_display=0, prefix='Kt', base_language=7 if donor == 1 else 1,
            file_string='SlimeGiant' + faction.title(), alliance=0 if donor == 1 else 1, name='Slime Giant')
    return sql.replace('ogre_furbolg_race_pack.py', 'slime_giant_race_pack.py').rstrip() + '\n'


def stage():
    ownership()
    files = p.ClientFiles(str(p.CLIENT_DEFAULT / 'Data'), 'enUS')
    try:
        baseline = {name: pinned(STAGE / 'baseline' / (name + '.dbc'),
                                files.find(p.DBC_ROOT + name + '.dbc')[0]) for name in TABLES}
        original = {name: pinned(STAGE / 'baseline' / name, files.find(p.GLUE_ROOT + name)[0]) for name in GLUE}
    finally:
        files.close()
    output, patched = tables(baseline), glue(original)
    for name, data in output.items():
        save(STAGE / 'client-dbc' / (name + '.dbc'), data)
    for name, data in patched.items():
        save(STAGE / 'glue' / name, data)
    server_hashes = {}
    for name in SERVER_TABLES:
        base = pinned(STAGE / 'baseline-server' / (name + '.dbc'),
                      (p.SERVER_DBC_ROOT / (name + '.dbc')).read_bytes())
        source, target = p.RawWdbc(output[name]), p.RawWdbc(base)
        assert (source.fields, source.record_size) == (target.fields, target.record_size)
        if name in ('CreatureModelData', 'CreatureDisplayInfo'):
            ids = {spec[3 if name == 'CreatureModelData' else 4] for spec in SPECS}
            rows = [row for row in source.records if p._value(row, 0) in ids]
        else:
            rows = [row for spec in SPECS for row in p._table_rows_for_race(output[name], name, spec[0])]
        p._ensure_id_free(base, name, {p._value(row, 0) for row in rows})
        pool = bytearray(target.strings)
        additions = [p._clone_strings(name, source, row, pool) for row in rows]
        save(STAGE / 'server/dbc' / (name + '.dbc'), target.build(list(target.records) + additions, bytes(pool)))
        server_hashes[name] = digest(base)
    sql = migration_sql().encode()
    save(MIGRATION, sql)
    save(STAGE / 'slime_giant.sql', sql)
    for spec in SPECS:
        save(STAGE / 'manifests' / (manifest(spec)['slug'] + '.json'),
             (json.dumps(manifest(spec), indent=2) + '\n').encode())
    audit = WORK / 'source-audit.json'
    if audit.exists():
        data = p.load_json(audit)
        assert data['npc_id'] == 175382 and '3490792' in data['models'], 'Source audit does not match SlimeSkeleton'
        model = data['models']['3490792']
        assert (model['bones'], model['sequences']) == (208, 320), 'Unexpected SlimeSkeleton rig'
    report = {'race_ids': [71, 72], 'live_installed': False, 'status': 'staged_native_renderer_required',
              'source_audit': str(audit), 'source_audit_sha256': p.sha256(audit) if audit.exists() else None,
              'source_audit_required_before_install': True,
              'native_profile_id': 0xF0010000, 'native_model': MODEL,
              'fallback_model': FALLBACK_MODEL, 'render_scale': 1.0, 'render_scale_calibration_required': False,
              'allocation_proposal': {str(spec[0]): ranges(spec[0]) for spec in SPECS},
              'baseline_hashes': {name: digest(data) for name, data in {**baseline, **original}.items()},
              'server_baseline_hashes': server_hashes,
              'client_dbc_hashes': {name: digest(data) for name, data in output.items()},
              'glue_hashes': {name: digest(data) for name, data in patched.items()},
              'migration': str(MIGRATION), 'migration_sha256': digest(sql),
              'archive_baselines': {str(relative): p.sha256(p.CLIENT_DEFAULT / relative)
                                    for relative in (p.GLOBAL_ARCHIVE_REL, p.LOCALE_ARCHIVE_REL)}}
    save(STAGE / 'report.json', (json.dumps(report, indent=2) + '\n').encode())
    self_check()
    print('STAGED Slime Giant races 71/72:', STAGE)


def self_check():
    assert all(manifest(spec)['appearance']['profiles']['0']['capacities'] == [5, 2, 1, 1, 1]
               for spec in SPECS)
    for folder, baseline_folder, names in (('client-dbc', 'baseline', TABLES),
                                          ('server/dbc', 'baseline-server', SERVER_TABLES)):
        for name in names:
            before = p.RawWdbc((STAGE / baseline_folder / (name + '.dbc')).read_bytes())
            after = p.RawWdbc((STAGE / folder / (name + '.dbc')).read_bytes())
            assert not (Counter(before.records) - Counter(after.records)), 'Existing DBC rows changed: ' + name
    for spec in SPECS:
        race = spec[0]
        for folder in ('client-dbc', 'server/dbc'):
            table = p.RawWdbc((STAGE / folder / 'ChrRaces.dbc').read_bytes())
            row = next(row for row in table.records if p._value(row, 0) == race)
            assert p._value(row, 16) == spec[4] and p._value(row, 20) == 0
            assert p._value(row, 52) == (0 if spec[2] == 1 else 1)
            assert p._string(table.strings, p._value(row, 24)).decode() == 'Kt'
            assert p._value(row, 32) == 7
            assert p._string(table.strings, p._value(row, 44)).decode() == 'SlimeGiant' + spec[1].title()
            for field in (*range(14, 30), *range(31, 47), *range(48, 64)):
                assert p._string(table.strings, p._value(row, field * 4)).decode() == 'Slime Giant'
            models = p.RawWdbc((STAGE / folder / 'CreatureModelData.dbc').read_bytes())
            model = next(row for row in models.records if p._value(row, 0) == spec[3])
            assert p._string(models.strings, p._value(model, 8)).decode() == FALLBACK_MODEL
            displays = p.RawWdbc((STAGE / folder / 'CreatureDisplayInfo.dbc').read_bytes())
            display = next(row for row in displays.records if p._value(row, 0) == spec[4])
            assert struct.unpack_from('<f', display, 16)[0] == 1.0
        options = manifest(spec)['appearance']['profiles']['0']['options']
        assert [option['label'] for option in options] == ['Slime Color', 'Slime Drip']
        assert options[0]['choices'] == list(COLORS)
    sql = (STAGE / 'slime_giant.sql').read_text()
    assert 'SET @RACE := 71;' in sql and 'SET @RACE := 72;' in sql
    print(f'SELF-CHECK PASS: two factions, male only, {len(COLORS)} colors, drip off/on, Kul Tiran fit')


def pack():
    self_check()
    report = p.load_json(STAGE / 'report.json')
    target = WORK / 'packages' / datetime.now().strftime('%Y%m%d-%H%M%S')
    target.mkdir(parents=True, exist_ok=False)
    replacements = {p.DBC_ROOT + path.name: path.read_bytes() for path in (STAGE / 'client-dbc').glob('*.dbc')}
    replacements.update({p.GLUE_ROOT + path.name: path.read_bytes() for path in (STAGE / 'glue').glob('*.lua')})
    storm = p.Storm(p.DLL_DEFAULT)
    result = {'installed': False, 'ready_for_install': False, 'archives': {},
              'remaining_gates': ['client/server build', 'native adapter checks', 'robe/cape/rigid gear fitting',
                                  'scale and collision calibration', 'animation coverage', 'live acceptance']}
    for relative in (p.GLOBAL_ARCHIVE_REL, p.LOCALE_ARCHIVE_REL):
        live = p.CLIENT_DEFAULT / relative
        before = p.sha256(live)
        assert before == report['archive_baselines'][str(relative)], 'Installed baseline changed; restage first'
        output = target / relative
        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(live, output)
        storm.replace_archive_entries(output, replacements)
        handle = storm.open_archive(output)
        try:
            for name, payload in replacements.items():
                assert storm.read(handle, name) == payload, name
        finally:
            storm.dll.SFileCloseArchive(handle)
        assert p.sha256(live) == before, 'Installed archive changed while packaging'
        result['archives'][str(relative)] = {'path': str(output), 'sha256': p.sha256(output), 'baseline': before}
    assets = {str(path.relative_to(STAGE / 'assets')).replace('/', '\\'): path.read_bytes()
              for path in (STAGE / 'assets').rglob('*') if path.is_file()}
    assert {'custom\\slimegiant\\3490792-clothing.m2',
            'custom\\slimegiant\\3490792-clothing00.skin'} <= set(assets), 'Clothing collection is required'
    relative = Path('Data/Patch-SG.MPQ')
    output = target / relative
    assert not (p.CLIENT_DEFAULT / relative).exists(), 'Client asset archive slot is occupied'
    storm.create_archive(output, assets)
    handle = storm.open_archive(output)
    try:
        for name, payload in assets.items():
            assert storm.read(handle, name) == payload, name
    finally:
        storm.dll.SFileCloseArchive(handle)
    result['archives'][str(relative)] = {'path': str(output), 'sha256': p.sha256(output), 'baseline': None}
    save(target / 'package-receipt.json', (json.dumps(result, indent=2) + '\n').encode())
    print('PACKAGED draft only; native build and fitting gates remain:', target)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('stage', 'reserve', 'pack', 'self-check'))
    args = parser.parse_args()
    {'stage': stage, 'reserve': reserve, 'pack': pack, 'self-check': self_check}[args.action]()
