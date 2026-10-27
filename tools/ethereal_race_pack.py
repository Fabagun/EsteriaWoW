"""Stage additive native-CASC Ethereal races and their saved Darkweaver/Dreadnaught form pair."""

import argparse
from collections import Counter
import hashlib
from pathlib import Path
import struct

import drakkin_drakonid_racials as racial_data
import ethereal_source as source
import ogre_furbolg_race_pack as o
import retroported_race_pack as p
import sethrak_race_pack as shared

WORK, STAGE = source.WORK, source.WORK / 'stage'
SPECS = ((77, 'alliance', 1), (78, 'horde', 2))
CLASSES = tuple(p.load_manifest('kyrian')['classes'])
SPELL = 111004
MIGRATION = p.ROOT / 'data/sql/updates/pending_db_world/rev_20261026010000000_ethereal.sql'


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def ranges(race):
    index = race - 77
    first = 1126000 + index * 1000
    return {'CreatureModelData': {'male': 121064 + index * 2, 'female': 121065 + index * 2},
            'CreatureDisplayInfo': {'male': 60087 + index * 2, 'female': 60088 + index * 2},
            'CharSections': [first, first + 999], 'CharHairGeosets': [first, first + 99],
            'BarberShopStyle': [first, first + 199], 'CharStartOutfit': [22400 + index * 100, 22499 + index * 100],
            'NameGen': [111000 + index * 3000, 113999 + index * 3000]}


def manifest(spec):
    race, faction, donor = spec
    bounds = ranges(race)
    return {'schema_version': 1, 'slug': 'ethereal_' + faction, 'name': 'Ethereal', 'race_ids': [race],
            'enum': 'RACE_ETHEREAL_' + faction.upper(), 'faction': faction, 'source_race_id': donor,
            'legacy_mask_race': donor, 'visual_base_race': 4, 'helmet_prefix': 'Nb',
            'client_file_strings': {str(race): 'Ethereal' + faction.title()},
            'glue_token': ('Ethereal' + faction).upper(), 'start_profile': 'elwynn' if donor == 1 else 'durotar',
            'classes': list(CLASSES), 'donor_totem_race': donor, 'random_playerbot_enabled': False,
            'models': {name: {'model_id': bounds['CreatureModelData'][name],
                             'display_id': bounds['CreatureDisplayInfo'][name],
                             'model_path': f'retail\\ethereal\\{source_id}.m2'}
                       for name, source_id in (('male', 5926159), ('female', 6152557))},
            'appearance': {'mode': 'native-retail-look-v2', 'supported_genders': [0, 1],
                           'profiles': {str(sex): {'capacities': [1] * 5, 'descriptors': [], 'options': []}
                                        for sex in (0, 1)},
                           'native_profile': 0xf0030000, 'source_build': source.BUILD,
                           'forms': [{'id': 5, 'name': 'Darkweaver', 'npc': 247577, 'models': [5926159, 6152557]},
                                     {'id': 6, 'name': 'Dreadnaught', 'npc': 246331, 'models': [6254042]}],
                           'transport': 'RLK1/RLE1/RLP1, independent 132-byte looks per form'},
            'custom_racial_spells': [SPELL], 'runtime_patch_root': str(STAGE),
            'source_patch_root': str(WORK / 'source')}


def reserve():
    allocation = p.load_json(p.ALLOCATION_PATH)
    registry_path = p.ROOT / 'modules/mod-custom-server/data/races/race_registry.json'
    registry = p.load_json(registry_path)
    for spec in SPECS:
        race, faction, donor = spec
        data = manifest(spec)
        slug = data['slug']
        assert not any(race in ids for owner, ids in allocation['race_ids'].items() if owner != slug)
        assert not any(row['id'] == race for row in registry['npc_only'])
        for owner, previous in allocation['race_allocations'].items():
            if owner == slug:
                assert previous == ranges(race)
                continue
            for table, values in ranges(race).items():
                old = previous.get(table)
                if isinstance(old, list):
                    assert max(old[0], values[0]) > min(old[1], values[1]), (owner, table)
                elif isinstance(old, dict):
                    assert not ((set(old.values()) - {0}) & set(values.values())), (owner, table)
        entry = {'id': race, 'species_key': slug, 'display_name': 'Ethereal', 'faction': faction,
                 'species_selection': True, 'start_profile': data['start_profile'],
                 'asset_owner': 'native_ethereal', 'legacy_mask_race': donor, 'visual_base_race': 4,
                 'supported_genders': [0, 1]}
        old = next((row for row in registry['playable'] if row['id'] == race), None)
        assert old is None or old == entry
        if old is None:
            registry['playable'].append(entry)
        allocation['race_ids'][slug] = [race]
        allocation['race_allocations'][slug] = ranges(race)
        for table, values in ranges(race).items():
            maximum = values[1] if isinstance(values, list) else max(values.values())
            allocation['dbc_ranges'][table][1] = max(allocation['dbc_ranges'][table][1], maximum)
        source.save(p.manifest_path(slug), data)
    pair = {'species_key': 'ethereal', 'alliance_id': 77, 'horde_id': 78}
    assert all(row == pair for row in registry['faction_pairs'] if row['species_key'] == 'ethereal')
    if pair not in registry['faction_pairs']:
        registry['faction_pairs'].append(pair)
    registry['sources']['native_ethereal'] = str(WORK / 'source')
    source.save(p.ALLOCATION_PATH, allocation)
    source.save(registry_path, registry)


def baseline():
    # PatchFiles.cpp sorts complete root/locale archive paths descending, including multi-letter suffixes.
    data = p.CLIENT_DEFAULT / 'Data'
    patches = [path for folder in (data, data / 'enUS') for path in folder.iterdir()
               if path.is_file() and path.suffix.lower() == '.mpq' and path.name.lower().startswith('patch')]
    patches.sort(key=lambda path: str(path).lower(), reverse=True)
    from esteria_client_dbc import chain
    paths = list(dict.fromkeys([*patches, *chain()]))
    pending = {p.DBC_ROOT + name + '.dbc': name for name in (*shared.TABLES, 'Spell')}
    pending.update({p.GLUE_ROOT + name: name for name in shared.GLUE})
    result, providers = {}, {}
    storm = p.Storm(p.DLL_DEFAULT)
    for path in paths:
        handle = storm.open_archive(path)
        try:
            for key, name in list(pending.items()):
                try:
                    raw = storm.read(handle, key)
                except OSError:
                    continue
                result[name], providers[name] = raw, str(path)
                del pending[key]
        finally:
            storm.dll.SFileCloseArchive(handle)
        if not pending:
            break
    assert not pending, pending
    return result, providers


def tables(original):
    result = {name: original[name] for name in (*shared.TABLES, 'Spell')}
    allocation = p.load_json(p.ALLOCATION_PATH)
    for spec in SPECS:
        race, faction, donor = spec
        data, bounds = manifest(spec), ranges(race)
        table = p.RawWdbc(result['ChrRaces'])
        pool = bytearray(table.strings)
        row = p._clone_strings('ChrRaces', table, next(row for row in table.records if p._value(row, 0) == 17), pool)
        for field, value in ((0, race), (1, 14), (2, donor), (4, bounds['CreatureDisplayInfo']['male']),
                             (5, bounds['CreatureDisplayInfo']['female']), (7, 7 if donor == 1 else 1),
                             (12, 0), (13, donor - 1), (68, 0)):
            row = p._replace(row, field * 4, 4, value)
        row = p._set_string(row, 11, pool, 'Ethereal' + faction.title())
        for field in (*range(14, 30), *range(31, 47), *range(48, 64)):
            row = p._set_string(row, field, pool, 'Ethereal')
        result['ChrRaces'] = shared.append_rows(result['ChrRaces'], 'ChrRaces', [row], pool)
        for sex in ('male', 'female'):
            for name, template_id in (('CreatureModelData', 3654), ('CreatureDisplayInfo', 60022)):
                table = p.RawWdbc(result[name])
                pool = bytearray(table.strings)
                row = p._clone_strings(name, table, next(row for row in table.records if p._value(row, 0) == template_id), pool)
                row = p._replace(row, 0, 4, bounds[name][sex])
                if name == 'CreatureModelData':
                    row = p._replace(row, 4, 4, p._value(row, 4) | 0x804)
                    row = p._set_string(row, 2, pool, data['models'][sex]['model_path'])
                else:
                    row = p._replace(row, 4, 4, bounds['CreatureModelData'][sex])
                    row = row[:16] + struct.pack('<f', 1.0) + row[20:]
                    for offset in (12, 24, 28, 32):
                        row = p._replace(row, offset, 4, 0)
                result[name] = shared.append_rows(result[name], name, [row], pool)
        result['CharBaseInfo'] = p._build_char_base_info(result['CharBaseInfo'], data)
        result['CharStartOutfit'] = p._build_char_start_outfit(result['CharStartOutfit'], data, allocation)
        result['NameGen'] = p._clone_namegen(result['NameGen'], data, allocation)
        sections, hair, facial = [], [], []
        for sex in (0, 1):
            first_section = bounds['CharSections'][0] + len(sections)
            sections.extend(struct.pack('<10I', first_section + kind, race, sex, kind, 0, 0, 0, 17, 0, 0)
                            for kind in range(5))
            hair.append(struct.pack('<6I', bounds['CharHairGeosets'][0] + sex, race, sex, 0, 0, 1))
            facial.append(struct.pack('<8I', race, sex, 0, 0, 0, 0, 0, 0))
        for name, rows in (('CharSections', sections), ('CharHairGeosets', hair), ('CharacterFacialHairStyles', facial)):
            result[name] = shared.append_rows(result[name], name, rows)
    result['CharSections'] = o.order_charsections_entry(p.DBC_ROOT + 'CharSections.dbc', result['CharSections'])
    result['Spell'], spell_sql = spell(result['Spell'])
    return result, spell_sql


def spell(raw):
    table = p.RawWdbc(raw)
    columns, index = racial_data.spell_columns(), racial_data.field_index()
    assert not any(p._value(row, 0) == SPELL for row in table.records), 'Ethereal spell ID collision'
    row = list(struct.unpack('<234I', next(row for row in table.records if p._value(row, 0) == 110685)))
    values = {'ID': SPELL, 'Effect_1': 3, 'Effect_2': 0, 'Effect_3': 0,
              'EffectAura_1': 0, 'EffectAura_2': 0, 'EffectAura_3': 0,
              'EffectMiscValue_1': 0, 'SpellClassSet': 0, 'ManaCost': 0, 'ManaCostPct': 0,
              'RecoveryTime': 0, 'CategoryRecoveryTime': 0}
    for name, value in values.items():
        row[index[name]] = value
    # Keep transformation usable in combat, with no shapeshift or resource restriction.
    row[index['Attributes']] &= ~0x10000000
    for name in ('ShapeshiftMask', 'ShapeshiftExclude', 'ShapeshiftMask_1', 'ShapeshiftMask_2',
                 'ShapeshiftExclude_1', 'ShapeshiftExclude_2'):
        if name in index:
            row[index[name]] = 0
    pool = bytearray(table.strings)
    for field in {field for start in (136, 153, 170, 187) for field in range(start, start + 16)}:
        row[field] = 0
    for field, text in ((136, 'Ethereal Two Forms'), (153, 'Ethereal Racial'),
                        (170, 'Switch between your customized Darkweaver and Dreadnaught forms.')):
        row[field] = len(pool)
        pool.extend(text.encode() + b'\0')
    names, values = [], []
    for i, (name, kind) in enumerate(columns):
        if not row[i]:
            continue
        names.append('`' + name + '`')
        values.append(racial_data._quote(p._string(bytes(pool), row[i]).decode()) if kind == 'string'
                      else racial_data._sql_value(row[i], kind))
    def lines(parts):
        result, line = [], '    '
        for i, part in enumerate(parts):
            token = part + (',' if i + 1 < len(parts) else '')
            if len(line) + len(token) > 116 and line.strip():
                result.append(line.rstrip())
                line = '    '
            line += token + ' '
        return '\n'.join([*result, line.rstrip()])

    sql = (f'DELETE FROM `spell_dbc` WHERE `ID` = {SPELL};\nINSERT INTO `spell_dbc` (\n'
           + lines(names) + '\n) VALUES (\n' + lines(values) + '\n);\n')
    return table.build([*table.records, struct.pack('<234I', *row)], bytes(pool)), sql


def glue(original):
    result = {name: original[name].decode('utf-8-sig').replace('\r\n', '\n') for name in shared.GLUE}
    assert 'EA_IS_RETAIL()' in result['CharacterCreate.lua']
    for race, faction, donor in SPECS:
        token, key = 'Ethereal' + faction.title(), ('Ethereal' + faction).upper()
        background = 'HUMAN' if donor == 1 else 'ORC'
        entries = (
            ('CharacterInfo.lua', 'local EXACT_RACE_DATA = {\n',
             f'    [{race}]={{glueString="{key}",name="Ethereal",faction="{faction.title()}",fileString="{token}"}},\n'),
            ('CharacterCreate.lua', 'local RACE_BACKGROUND_KEYS = {\n', f'        ["{key}"]="{background}",\n'),
            ('GlueParent.lua', '    local ' + faction + 'Races = {\n', f'        ["{key}"]=true,\n'),
            ('ECS_Schema.lua', 'S.RaceOverride = {\n',
             f'    [{race}]={{name="Ethereal",faction={donor},artKey="{token}"}},\n'),
            ('ECS_Schema.lua', 'S.RaceByModelKey = {\n',
             f'    {{"{key}",{{name="Ethereal",faction={donor},artKey="{token}"}}}},\n'),
            ('ECS_Schema.lua', 'S.PortraitArtKeys = {\n', f'    {token}=true,\n'))
        for name, anchor, text in entries:
            result[name] = o._insert_once(result[name], anchor, text, 'Ethereal ' + name)
        result['CharacterInfo.lua'] += (f'\nRaceInfoByFileString.{key}={{Name="Ethereal",'
            'Description="Customize your Ethereal Darkweaver and Dreadnaught forms independently. '
            'Use Ethereal Two Forms to change form while retaining your abilities and equipment."};\n')
        result['GlueStrings.lua'] += f'\n{key}="Ethereal"; {key}_MALE={key}; {key}_FEMALE={key};\n'
        result['GlueParent.lua'] += ''.join(f'\n{table}.{key}={table}.{background};'
            for table in ('CharModelFogInfo', 'CharModelGlowInfo', 'GlueAmbienceTracks')) + '\n'
        for sex in ('MALE', 'FEMALE'):
            result['CharacterCreate.lua'] += (f'\nRACE_ICON_TCOORDS["{key}_{sex}"]={{0,1,0,1}};\n'
                f'RACE_ICON_TEXTURES["{key}_{sex}"]="Interface\\\\Glues\\\\CharacterCreate\\\\'
                f'UI-CharacterCreate-{token}{sex.title()}";\n')
    anchor = 'race == 75 or race == 76)) then'
    assert result['ECS_Integrate.lua'].count(anchor) == 1
    result['ECS_Integrate.lua'] = result['ECS_Integrate.lua'].replace(anchor,
        'race == 75 or race == 76 or race == 77 or race == 78)) then')
    anchor = 'raceModel == "KYRIANALLIANCE"'
    assert result['CharacterSelect.lua'].count(anchor) == 1
    result['CharacterSelect.lua'] = result['CharacterSelect.lua'].replace(anchor,
        anchor + ' or raceModel == "ETHEREALALLIANCE"')
    from lupa.lua51 import LuaRuntime
    compile_chunk = LuaRuntime().eval('function(s) local f,e=loadstring(s); assert(f,e); end')
    for text in result.values():
        compile_chunk(text)
    return {name: text.encode() for name, text in result.items()}


def migration(spell_sql):
    result = '-- Generated by tools/ethereal_race_pack.py. Stage only; install with the matched native client/server.\n'
    result += spell_sql
    result += (f'DELETE FROM `spell_script_names` WHERE `spell_id` = {SPELL};\n'
               f"INSERT INTO `spell_script_names` (`spell_id`,`ScriptName`) VALUES ({SPELL},'spell_race_ethereal_two_forms');\n")
    for spec in SPECS:
        race, faction, donor = spec
        bounds = ranges(race)
        result += o.build_sql({'name': 'Ethereal', 'race_id': race, 'faction': faction,
                               'donor_start_race': donor, 'donor_totem_race': donor})
        result += (f'DELETE FROM `custom_race_start_spell` WHERE `race` = {race} AND `spell` = {SPELL};\n'
                   f"INSERT INTO `custom_race_start_spell` (`race`,`classMask`,`spell`,`comment`) VALUES\n"
                   f"({race},0,{SPELL},'Ethereal Two Forms');\n")
        result += 'DELETE FROM `custom_race_start_spell_exclude` WHERE `race` = @RACE;\n'
        result += 'INSERT INTO `custom_race_start_spell_exclude` (`race`,`spell`,`comment`) VALUES\n'
        donor_spells = racial_data.HUMAN_RACIALS if donor == 1 else racial_data.ORC_RACIALS
        result += ',\n'.join(f"(@RACE,{identifier},'Donor racial: {name}')" for identifier, name in donor_spells) + ';\n'
        result += 'DELETE FROM `custom_race_start_skill_exclude` WHERE `race` = @RACE;\n'
        result += ('INSERT INTO `custom_race_start_skill_exclude` (`race`,`skill`,`comment`) VALUES\n'
                   f"(@RACE,{754 if donor == 1 else 125},'Donor racial skill');\n")
        result += o.CHRRACES_TEMPLATE.format(race=race, faction_template=donor,
            male_display=bounds['CreatureDisplayInfo']['male'], female_display=bounds['CreatureDisplayInfo']['female'],
            prefix='Nb', base_language=7 if donor == 1 else 1, file_string='Ethereal' + faction.title(),
            alliance=donor - 1, name='Ethereal')
    result += ('DELETE FROM `creature_model_info` WHERE `DisplayID` IN (60087,60088,60089,60090);\n'
               'INSERT INTO `creature_model_info`\n'
               '(`DisplayID`,`BoundingRadius`,`CombatReach`,`Gender`,`DisplayID_Other_Gender`) VALUES\n'
               '(60087,0.5,1.5,0,60088),\n(60088,0.5,1.5,1,60087),\n'
               '(60089,0.5,1.5,0,60090),\n(60090,0.5,1.5,1,60089);\n')
    return result.rstrip() + '\n'


def stage():
    reserve()
    original, providers = baseline()
    output, sql = tables(original)
    patched = glue(original)
    for name, raw in original.items():
        save(STAGE / 'baseline' / (name if name.endswith('.lua') else name + '.dbc'), raw)
    for name, raw in output.items():
        before, after = p.RawWdbc(original[name]), p.RawWdbc(raw)
        assert not (Counter(before.records) - Counter(after.records)), 'Unrelated records changed: ' + name
        assert after.strings.startswith(before.strings), 'Unrelated string pool changed: ' + name
        save(STAGE / 'client-dbc' / (name + '.dbc'), raw)
    for name, raw in patched.items():
        save(STAGE / 'glue' / name, raw)
    portrait = (WORK / 'source' / f'{source.PORTRAIT}.blp').read_bytes()
    for _, faction, _ in SPECS:
        token = 'Ethereal' + faction.title()
        for sex in ('Male', 'Female'):
            for path in (f'Interface/Glues/CharacterCreate/UI-CharacterCreate-{token}{sex}.blp',
                         f'Interface/CharacterFrame/TemporaryPortrait-{sex}-{token}.blp',
                         f'Interface/Glues/CharacterSelect/ECS-Portrait-{token}{sex}.blp'):
                save(STAGE / 'assets' / path, portrait)
    from centaur_race_pack import clone_server_row
    for name in (*shared.SERVER_TABLES, 'Spell'):
        raw = (p.SERVER_DBC_ROOT / (name + '.dbc')).read_bytes()
        before, target = p.RawWdbc(raw), p.RawWdbc(output[name])
        if name == 'Spell':
            ids = {SPELL}
        elif name in ('CreatureDisplayInfo', 'CreatureModelData'):
            ids = {number for race, *_ in SPECS for number in ranges(race)[name].values()}
        else:
            ids = {p._value(row, 0) for race, *_ in SPECS for row in p._table_rows_for_race(output[name], name, race)}
        p._ensure_id_free(raw, name, ids)
        pool = bytearray(before.strings)
        rows = [clone_server_row(name, target, row, pool) for row in target.records if p._value(row, 0) in ids]
        save(STAGE / 'baseline-server' / (name + '.dbc'), raw)
        save(STAGE / 'server/dbc' / (name + '.dbc'), before.build([*before.records, *rows], bytes(pool)))
    save(MIGRATION, migration(sql).encode())
    source.save(STAGE / 'report.json', {'race_ids': [77, 78], 'forms': [5, 6], 'spell': SPELL,
        'source_build': source.BUILD, 'providers': providers, 'installed': False, 'live_accepted': False,
        'client_tables': {name: hashlib.sha256(raw).hexdigest() for name, raw in output.items()},
        'remaining': ['native and server build authorization', 'native fixture checks',
                      'backed-up deployment', 'live customization, animation, equipment and relog acceptance'],
        'portrait': {'source_file_data_id': source.PORTRAIT, 'source': 'Retail Shadowguard Ethereal caster icon'}})
    print('STAGED Ethereal 77/78 with independent form looks:', STAGE)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('reserve', 'stage'))
    args = parser.parse_args()
    globals()[args.action]()
