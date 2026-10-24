"""Stage the approved native races against Esteria's current data; never install or build."""

import argparse
import base64
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import shutil
import struct

import retroported_race_pack as p
from wod_model_migration import order_charsections_entry


SOURCE = Path(r"G:\Downloads\HDWoWModels\Kyrian-Venthyr-Approved-20261021")
STAGE = Path(r"W:\EsteriaStaging\kyrian-venthyr-20261022")
MIGRATION = p.ROOT / 'data/sql/updates/pending_db_world/rev_20261022010000000.sql'
SPECS = ((60, 75, 'kyrian', 'alliance', 11), (61, 76, 'venthyr', 'horde', 5))
CLASSES = [1, 2, 3, 4, 5, 7, 8, 9, 11]
FIXED = {'ChrRaces', 'CreatureModelData', 'CreatureDisplayInfo'}
COMPOSITE = {'CharBaseInfo', 'CharacterFacialHairStyles'}


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def json_save(path, data):
    save(path, (json.dumps(data, indent=2) + '\n').encode())


def verify_source(source):
    for line in (source / 'SHA256SUMS.txt').read_text().splitlines():
        expected, name = line.split('  ', 1)
        path = source / name
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError('Source checksum mismatch: ' + name)


def profile(source, name, sex):
    text = (source / 'source-reference/client/WoW/Common/ComponentCore/CreatureAppearance.h').read_text()
    stem = name.title() + ('Female' if sex else 'Male')
    def options(suffix):
        body = re.search(r'\b' + stem + suffix + r' = \{\{(.*?)\}\};', text, re.S).group(1)
        return [list(map(int, values)) for values in re.findall(r'\{(\d+), (\d+), (\d+)\}', body)]
    labels = re.search(stem + r'Labels = \{\{(.*?)\}\};', text).group(1)
    return {'capacities': [row[1] for row in options('')], 'descriptors': options('Controls'),
            'options': [{'label': label} for label in re.findall(r'"([^"]+)"', labels)]}


def reserve(source):
    verify_source(source)
    allocation = p.load_json(p.ALLOCATION_PATH)
    registry_path = p.ROOT / 'modules/mod-custom-server/data/races/race_registry.json'
    registry = p.load_json(registry_path)
    for old, race, name, faction, donor in SPECS:
        if any(race in ids for owner, ids in allocation['race_ids'].items() if owner != name):
            raise ValueError('Race ID already reserved: ' + str(race))
        if any(row['id'] == race and row.get('species_key') != name
               for row in registry['playable'] + registry['npc_only']):
            raise ValueError('Registry collision: ' + str(race))
        index = old - 60
        models = {sex: {'model_id': 121060 + index * 2 + i, 'display_id': 60083 + index * 2 + i,
                       'model_path': f'custom\\{name}\\native\\' +
                           (f'kyrian{sex}.m2' if name == 'kyrian' else f'vampire_{sex}.m2')}
                  for i, sex in enumerate(('male', 'female'))}
        manifest = {'schema_version': 1, 'slug': name, 'name': name.title(), 'race_ids': [race],
                    'source_race_id': old, 'source_package': str(source), 'faction': faction,
                    'legacy_mask_race': donor, 'visual_base_race': donor,
                    'start_profile': 'azuremyst' if donor == 11 else 'deathknell',
                    'classes': CLASSES, 'models': models, 'random_playerbot_enabled': False,
                    'appearance': {'mode': 'native-stock-five-byte-v1', 'supported_genders': [0, 1],
                                   'profiles': {str(sex): profile(source, name, sex) for sex in (0, 1)}}}
        json_save(p.manifest_path(name), manifest)
        allocation['race_ids'][name] = [race]
        allocation['race_allocations'][name] = {
            table: {sex: model[key] for sex, model in models.items()}
            for table, key in (('CreatureModelData', 'model_id'), ('CreatureDisplayInfo', 'display_id'))}
        for table, values in allocation['race_allocations'][name].items():
            allocation['dbc_ranges'][table][1] = max(allocation['dbc_ranges'][table][1], *values.values())
        entry = {'id': race, 'species_key': name, 'display_name': name.title(), 'faction': faction,
                 'asset_owner': 'approved_kyrian_venthyr', 'legacy_mask_race': donor,
                 'visual_base_race': donor, 'start_profile': manifest['start_profile'],
                 'supported_genders': [0, 1], 'species_selection': True}
        registry['playable'] = [row for row in registry['playable'] if row['id'] != race] + [entry]
    registry['sources']['approved_kyrian_venthyr'] = str(source)
    json_save(p.ALLOCATION_PATH, allocation)
    json_save(registry_path, registry)


def race_of(table, row):
    if table in ('CreatureModelData', 'CreatureDisplayInfo'):
        return None
    layout = p.WDBC_LAYOUTS[table]
    return int.from_bytes(row[layout.race_offset:layout.race_offset + layout.race_width], 'little')


def merge(table, blob, recipe, ids):
    base = p.RawWdbc(blob)
    if (base.fields, base.record_size) != (recipe['fields'], recipe['stride']):
        raise ValueError('DBC layout mismatch: ' + table)
    rows, pool = list(base.records), bytearray(base.strings)
    used = {p._value(row, 0) for row in rows} if table not in COMPOSITE else set()
    for item in recipe['rows']:
        row = bytearray(base64.b64decode(item['bytes']))
        old_id = p._value(row, 0)
        if table in FIXED:
            if table == 'ChrRaces':
                struct.pack_into('<I', row, 0, {60: 75, 61: 76}[old_id])
        elif table not in COMPOSITE:
            struct.pack_into('<I', row, 0, ids[table][old_id])
        if table not in ('CreatureModelData', 'CreatureDisplayInfo', 'ChrRaces'):
            layout = p.WDBC_LAYOUTS[table]
            old = race_of(table, row)
            row[layout.race_offset:layout.race_offset + layout.race_width] = \
                {60: 75, 61: 76}[old].to_bytes(layout.race_width, 'little')
        if table == 'CreatureModelData':
            struct.pack_into('<I', row, 4, p._value(row, 4) | 0x804)
        if table == 'CreatureDisplayInfo' and old_id in (60083, 60084):
            struct.pack_into('<f', row, 16, 0.75)  # package ships Kyrian at 0.48, smaller than Venthyr
        if table not in COMPOSITE and p._value(row, 0) in used:
            raise ValueError(f'{table} ID collision: {p._value(row, 0)}')
        if table == 'CharBaseInfo' and bytes(row) in rows:
            raise ValueError('Race/class already exists')
        for field, value in item['strings'].items():
            struct.pack_into('<I', row, int(field) * 4, len(pool))
            pool.extend(value.encode() + b'\0')
        rows.append(bytes(row))
        if table not in COMPOSITE:
            used.add(p._value(row, 0))
    result = base.build(rows, bytes(pool))
    if table == 'CharSections':
        result = order_charsections_entry(p.DBC_ROOT + table + '.dbc', result)
    after = p.RawWdbc(result)
    if Counter(base.records) - Counter(after.records) or not after.strings.startswith(base.strings):
        raise ValueError('Unrelated DBC data changed: ' + table)
    return result


def migration(source):
    text = (source / 'server/data/sql/updates/pending_db_world/rev_20261020235900000.sql').read_text()
    # Only tuple-leading race IDs and explicit race predicates are rewritten; asset paths retain provenance IDs.
    text = re.sub(r'(?m)^\(60,', '(75,', text)
    text = re.sub(r'(?m)^\(61,', '(76,', text)
    text = text.replace('IN (60, 61)', 'IN (75, 76)')
    text = re.sub(r'(?m)^\((12106[0-3]), 0,', r'(\1, 2052,', text)
    text = re.sub(r'(?m)^\((6008[34]), (12106[01]), 0, 0, [\d.]+,', r'(\1, \2, 0, 0, 0.75,', text)
    start = text.index('INSERT INTO `player_totem_model`')
    text = text[:start] + re.sub(r'(?m)^\(([1-4]), (60|61),',
        lambda match: f'({match[1]}, {int(match[2]) + 15},', text[start:])
    # Start actions for unsupported donor classes included unrelated donor racials. Keep only shared class actions.
    spells = (20572, 33697, 28730, 28734, 20549)
    for spell in spells:
        text = re.sub(r'(?m)^\(76, \d+, \d+, ' + str(spell) + r', 0\),?\n', '', text)
    for _, race, name, faction, donor in SPECS:
        language_spell, language_skill = (668, 98) if faction == 'alliance' else (669, 109)
        text += f"\nDELETE FROM `custom_race_start_spell` WHERE `race` = {race};\n"
        text += 'INSERT INTO `custom_race_start_spell` (`race`, `classMask`, `spell`, `comment`) VALUES\n'
        spells = [(language_spell, 0, name.title() + ' faction language')]
        if race == 75:
            # The realm permits additional classes whose Draenei donor rows omit some racials.
            spells += [(spell, 0, label) for spell, label in (
                (20579, 'Shadow Resistance'), (28875, 'Gemcutting'),
                (28880, 'Gift of the Naaru'), (29932, 'Language Draenei'))]
            spells += [(6562, 7, 'Heroic Presence'), (28878, 1496, 'Inspiring Presence')]
        text += ',\n'.join(f"({race}, {mask}, {spell}, '{label}')" for spell, mask, label in spells) + ';\n'
        text += f'DELETE FROM `custom_race_start_skill` WHERE `race` = {race};\n'
        text += 'INSERT INTO `custom_race_start_skill` (`race`, `classMask`, `skill`, `rank`, `comment`) VALUES\n'
        text += f"({race}, 0, {language_skill}, 0, '{name.title()} faction language');\n"
    text += '\nDELETE FROM `creature_model_info` WHERE `DisplayID` IN (60083, 60084, 60085, 60086);\n'
    text += 'INSERT INTO `creature_model_info` '
    text += '(`DisplayID`, `BoundingRadius`, `CombatReach`, `Gender`, `DisplayID_Other_Gender`) VALUES\n'
    text += ',\n'.join(f'({60083+i}, 0.5, 1.5, {i%2}, {60083+(i^1)})' for i in range(4)) + ';\n'
    text += '\nDELETE FROM `playercreateinfo_action` WHERE `race` = 75 AND `class` IN (4,9,11) AND `button` = 4;\n'
    text += 'INSERT INTO `playercreateinfo_action` (`race`, `class`, `button`, `action`, `type`) VALUES\n'
    text += ',\n'.join(f'(75, {class_id}, 4, 28880, 0)' for class_id in (4, 9, 11)) + ';\n'
    guard = '''-- Refuse to replace foreign ownership; apply as a batch without mysql --force.
CREATE TEMPORARY TABLE `_kyrian_venthyr_guard` (`ok` TINYINT NOT NULL CHECK (`ok` = 1));
DELETE FROM `_kyrian_venthyr_guard`;
INSERT INTO `_kyrian_venthyr_guard` (`ok`)
SELECT IF(
    NOT EXISTS (SELECT 1 FROM `chrraces_dbc` WHERE
        (`ID` = 75 AND `ClientFilestring` <> 'KyrianAlliance') OR
        (`ID` = 76 AND `ClientFilestring` <> 'VenthyrHorde'))
    AND NOT EXISTS (SELECT 1 FROM `creaturedisplayinfo_dbc` WHERE
        `ID` BETWEEN 60083 AND 60086 AND `ModelID` <> 121060 + `ID` - 60083)
    AND NOT EXISTS (SELECT 1 FROM `creaturemodeldata_dbc` WHERE
        `ID` BETWEEN 121060 AND 121063 AND `ModelName` <> CASE `ID`
            WHEN 121060 THEN 'custom\\\\kyrian\\\\native\\\\kyrianmale.m2'
            WHEN 121061 THEN 'custom\\\\kyrian\\\\native\\\\kyrianfemale.m2'
            WHEN 121062 THEN 'custom\\\\venthyr\\\\native\\\\vampire_male.m2'
            WHEN 121063 THEN 'custom\\\\venthyr\\\\native\\\\vampire_female.m2' END), 1, 0);
DROP TEMPORARY TABLE `_kyrian_venthyr_guard`;
'''
    lines = []
    for line in (guard + '\nSTART TRANSACTION;\n' + text + '\nCOMMIT;\n').splitlines():
        if len(line) <= 120 or line.startswith('--'):
            lines.append(line)
            continue
        current = ''
        for token in re.findall(r"'(?:\\.|[^'\\])*'|`[^`]*`|[^\s'`]+", line):
            if current and len(current) + len(token) + 1 > 120:
                lines.append(current)
                current = '    ' + token
            else:
                current += (' ' if current else '') + token
        lines.append(current)
    return '\n'.join(lines) + '\n'


def package(source, client, output):
    import race_portrait_pack as art

    storm = p.Storm(p.DLL_DEFAULT)
    archive = storm.open_archive(source / 'client/race-assets.mpq')
    try:
        assets = {name: storm.read(archive, name) for name in p.load_json(source / 'manifest.json')['assets']}
    finally:
        storm.dll.SFileCloseArchive(archive)
    with p.ClientFiles(str(client / 'Data'), 'enUS') as files:
        template = files.find(art.ICON_TEMPLATE_ENTRY)[0]
        ring = art.ring_layer(art.decode_client_blp(files.find(art.RING_ENTRY)[0]))
    mask = art.circular_mask()
    portrait_sources = {}
    for _, _, name, faction, _ in SPECS:
        token = name.title() + faction.title()
        for sex in ('male', 'female'):
            candidates = list(Path('R:/Users/Zach/Pictures/Portraits').rglob(f'*{name}-{sex}_{faction}.png*'))
            if len(candidates) != 1:
                raise ValueError('Missing or ambiguous portrait source: ' + token + sex)
            image = art.portrait_bytes(candidates[0], mask)
            portrait_sources[str(candidates[0])] = p.sha256(candidates[0])
            plain = art.encode_portrait(image, template)
            creator = art.encode_portrait(art.compose_race_icon(image, ring), template)
            for path, blob in (
                (art.CREATOR_ICON_ROOT + f'UI-CharacterCreate-{token}{sex.title()}.blp', creator),
                (f'Interface\\Glues\\CharacterSelect\\ECS-Portrait-{token}{sex.title()}.blp', plain),
                (f'Interface\\CharacterFrame\\TemporaryPortrait-{sex.title()}-{token}.blp', plain)):
                art.validate_portrait(blob, Path(path))
                assets[path] = blob
    updates = {p.DBC_ROOT + file.name: file.read_bytes() for file in (output / 'client-dbc').glob('*.dbc')}
    updates.update({p.GLUE_ROOT + file.name: file.read_bytes() for file in (output / 'glue').glob('*.lua')})
    updates.update(assets)
    report = p.load_json(output / 'report.json')
    report['loose_client_files'] = {
        str(file.relative_to(output / 'client')): p.sha256(file)
        for file in (output / 'client').rglob('*') if file.is_file() and file.suffix.lower() not in ('.mpq', '.exe')}
    report['portrait_sources'] = portrait_sources
    report['payloads'] = {name: hashlib.sha256(blob).hexdigest() for name, blob in updates.items()}
    report['archives'] = {}
    for relative in (p.GLOBAL_ARCHIVE_REL, p.LOCALE_ARCHIVE_REL):
        live, target = client / relative, output / 'client' / relative
        if target.exists():
            raise FileExistsError(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        before_hash = p.sha256(live)
        shutil.copy2(live, target)
        storm.replace_archive_entries(target, updates)
        compressed = target.with_suffix('.compressed.mpq')
        if compressed.exists() or not target.resolve().is_relative_to(output.resolve()):
            raise ValueError('Unsafe or occupied compression output')
        p.rebuild_archive_streaming(storm, target, compressed, compress=True)
        if compressed.stat().st_size >= 0x80000000:
            raise ValueError('Compressed archive exceeds the verified 2 GiB boundary')
        target.unlink()
        compressed.replace(target)
        handles = [storm.open_archive(path) for path in (live, target)]
        try:
            before = [name for name, *_ in storm.list_files(handles[0]) if not name.startswith('(')]
            keys = {name.casefold(): name for name in updates}
            for name in before:
                expected = updates[keys[name.casefold()]] if name.casefold() in keys else storm.read(handles[0], name)
                if storm.read(handles[1], name) != expected:
                    raise ValueError('Archive preservation mismatch: ' + name)
            for name, blob in updates.items():
                if storm.read(handles[1], name) != blob:
                    raise ValueError('Archive readback mismatch: ' + name)
        finally:
            for handle in handles:
                storm.dll.SFileCloseArchive(handle)
        if p.sha256(live) != before_hash:
            raise ValueError('Live archive changed during staging')
        report['archives'][str(relative)] = {'before': before_hash, 'after': p.sha256(target),
            'unrelated_payloads_preserved': len(before) - len({name.casefold() for name in before} & set(keys)),
            'bytes': target.stat().st_size, 'compressed_payloads_verified': True}
        json_save(output / 'report.json', report)
        print('PASS archive readback and unrelated payload preservation:', relative, flush=True)


def patch_glue(data):
    text = data.decode('utf-8')
    text = text.replace('CharacterCreate.selectedRaceID == 54',
                        'CharacterCreate.selectedRaceID == 75 or CharacterCreate.selectedRaceID == 76 or '
                        'CharacterCreate.selectedRaceID == 54')
    for token, name in (('KYRIANALLIANCE', 'KyrianAlliance'), ('VENTHYRHORDE', 'VenthyrHorde')):
        background = 'DRAENEI' if name.startswith('Kyrian') else 'SCOURGE'
        marker = 'local RACE_BACKGROUND_KEYS = {'
        if text.count(marker) != 1:
            raise ValueError('Creator background dictionary changed')
        text = text.replace(marker, marker + f'\n    ["{token}"] = "{background}",', 1)
        for sex in ('Male', 'Female'):
            line = f'    ["{token}_{sex.upper()}"] = "Interface\\\\Glues\\\\CharacterCreate\\\\UI-CharacterCreate-{name}{sex}.blp",\n'
            marker = 'RACE_ICON_TEXTURES = {'
            if text.count(marker) != 1:
                raise ValueError('Creator portrait dictionary changed')
            text = text.replace(marker, marker + '\n' + line, 1)
        text = text.replace('local RACE_GRID_CUSTOM_ORDER = {',
                            'local RACE_GRID_CUSTOM_ORDER = {\n    ' + token + '=18,', 1)
    marker = 'local function GetRaceSelectionFaction(token, fallback)'
    if marker in text:
        text = text.replace(marker, marker + '\n    if token == "KYRIANALLIANCE" then return "Alliance"; end\n'
                            '    if token == "VENTHYRHORDE" then return "Horde"; end', 1)
    return text.encode()


def supporting_glue(files):
    names = ('CharacterInfo.lua', 'GlueStrings.lua', 'GlueParent.lua', 'ECS_Schema.lua',
             'ECS_Integrate.lua', 'CharacterSelect.lua')
    result = {name: files.find(p.GLUE_ROOT + name)[0].decode('utf-8-sig') for name in names}
    for _, race, name, faction, donor in SPECS:
        token = name.title() + faction.title()
        key = token.upper()
        team = 1 if faction == 'alliance' else 2
        background = 'DRAENEI' if donor == 11 else 'SCOURGE'
        insertions = (
            ('CharacterInfo.lua', 'local EXACT_RACE_DATA = {',
             f'    [{race}] = {{glueString="{key}", name="{name.title()}", faction="{faction.title()}", fileString="{token}"}},'),
            ('GlueParent.lua', '    local ' + faction + 'Races = {', f'        ["{key}"] = true,'),
            ('ECS_Schema.lua', 'S.RaceOverride = {',
             f'    [{race}] = {{name="{name.title()}", faction={team}, artKey="{token}"}},'),
            ('ECS_Schema.lua', 'S.RaceByModelKey = {',
             f'    {{"{key}", {{name="{name.title()}", faction={team}, artKey="{token}"}}}},'),
            ('ECS_Schema.lua', 'S.PortraitArtKeys = {', f'    {token}=true,'))
        for file, anchor, addition in insertions:
            if result[file].count(anchor) != 1:
                raise ValueError('Glue anchor changed: ' + file + ' ' + anchor)
            result[file] = result[file].replace(anchor, anchor + '\n' + addition, 1)
        result['CharacterInfo.lua'] += f'\nRaceInfoByFileString.{key}={{Name="{name.title()}", Description="{name.title()} of the {faction.title()}."}};\n'
        result['GlueStrings.lua'] += f'\n{key}="{name.title()}"; {key}_MALE={key}; {key}_FEMALE={key};\n'
        result['GlueStrings.lua'] += (
            f'RACE_INFO_{key}="{name.title()} of the {faction.title()}.";\n'
            f'for i=1,10 do _G["ABILITY_INFO_{key}"..i]=_G["ABILITY_INFO_{background}"..i]; end\n')
        result['GlueParent.lua'] += ''.join(f'\n{table}.{key}={table}.{background};'
            for table in ('CharModelFogInfo', 'CharModelGlowInfo', 'GlueAmbienceTracks')) + '\n'
    result['ECS_Integrate.lua'] = result['ECS_Integrate.lua'].replace(
        'race == 73 or race == 74', 'race == 73 or race == 74 or race == 75 or race == 76')
    result['CharacterSelect.lua'] = result['CharacterSelect.lua'].replace(
        'raceModel == "CENTAURALLIANCE"', 'raceModel == "KYRIANALLIANCE" or raceModel == "CENTAURALLIANCE"')
    return {name: text.encode() for name, text in result.items()}


def stage(source, client, output):
    verify_source(source)
    if output.exists():
        raise FileExistsError('Use a new staging folder: ' + str(output))
    recipe = p.load_json(source / 'client/dbc-rows.json')
    server_recipe = p.load_json(source / 'server/dbc-rows.json')
    with p.ClientFiles(str(client / 'Data'), 'enUS') as files:
        baseline = {name: files.find(p.DBC_ROOT + name + '.dbc')[0] for name in recipe}
        glue = files.find(p.GLUE_ROOT + 'CharacterCreate.lua')[0]
        extra_glue = supporting_glue(files)
    server = {name: (p.SERVER_DBC_ROOT / (name + '.dbc')).read_bytes()
              for name in recipe if (p.SERVER_DBC_ROOT / (name + '.dbc')).exists()}
    ids = {}
    for name, definition in recipe.items():
        if name in FIXED | COMPOSITE:
            continue
        used = {p._value(row, 0) for blob in (baseline[name], server.get(name, baseline[name]))
                for row in p.RawWdbc(blob).records}
        first = max(used) + 1
        ids[name] = {p._value(base64.b64decode(row['bytes']), 0): first + i
                     for i, row in enumerate(definition['rows'])}
    # Server recipes can have different original row IDs; preserve a common final client/server allocation.
    for name in ids:
        for client_row, server_row in zip(recipe[name]['rows'], server_recipe[name]['rows']):
            server_row['bytes'] = base64.b64encode(
                base64.b64decode(client_row['bytes'])[:4] + base64.b64decode(server_row['bytes'])[4:]).decode()
    output.mkdir(parents=True)
    for name, blob in baseline.items():
        save(output / 'baseline-client' / (name + '.dbc'), blob)
        save(output / 'client-dbc' / (name + '.dbc'), merge(name, blob, recipe[name], ids))
    for name, blob in server.items():
        save(output / 'baseline-server' / (name + '.dbc'), blob)
        save(output / 'server/dbc' / (name + '.dbc'), merge(name, blob, server_recipe[name], ids))
    save(output / 'baseline-client/CharacterCreate.lua', glue)
    save(output / 'glue/CharacterCreate.lua', patch_glue(glue))
    for name, blob in extra_glue.items():
        save(output / 'glue' / name, blob)
    for file in (source / 'client/Data').rglob('*'):
        if file.is_file():
            relative = file.relative_to(source / 'client')
            if relative.parent.name == 'EquipmentFitting':
                race, sex = file.stem.split('-')
                relative = relative.with_name(f'{int(race)+15}-{sex}.bin')
            save(output / 'client' / relative, file.read_bytes())
    for name in ('Kyrian', 'Venthyr'):
        for suffix in ('.bin', 'Textures.bin'):
            shutil.copy2(source / ('client/Data/Retail/Esteria' + name + suffix), output / ('client/Esteria' + name + suffix))
    shutil.copy2(source / 'client/race-assets.mpq', output / 'race-assets.mpq')
    sql = migration(source)
    save(MIGRATION, sql.encode())
    save(output / 'migration.dump', sql.encode())
    json_save(output / 'report.json', {'race_ids': {'Kyrian': 75, 'Venthyr': 76},
        'model_ids': list(range(121060, 121064)), 'display_ids': list(range(60083, 60087)),
        'installed': False, 'built': False, 'live_accepted': False,
        'source': str(source), 'client': str(client),
        'baseline_client_hashes': {name: hashlib.sha256(blob).hexdigest() for name, blob in baseline.items()},
        'baseline_server_hashes': {name: hashlib.sha256(blob).hexdigest() for name, blob in server.items()}})
    print('Staged only:', output)


def self_check():
    # Exercise packed fields and append preservation without game assets.
    for name, fields, stride, offset, width in (('CharBaseInfo', 2, 2, 0, 1), ('CharSections', 10, 40, 4, 4)):
        original = bytearray(stride)
        original[offset:offset+width] = (60).to_bytes(width, 'little')
        incoming = bytearray(stride)
        incoming[offset:offset+width] = (61).to_bytes(width, 'little')
        blob = struct.pack('<4s4I', b'WDBC', 1, fields, stride, 1) + original + b'\0'
        recipe = {'fields': fields, 'stride': stride, 'rows': [
            {'bytes': base64.b64encode(incoming).decode(), 'strings': {}}]}
        result = p.RawWdbc(merge(name, blob, recipe, {'CharSections': {0: 123}}))
        assert bytes(original) in result.records
        assert any(race_of(name, row) == 76 for row in result.records)
        assert not any(race_of(name, row) == 61 for row in result.records)
    print('PASS packed race remap and preservation self-check')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('reserve', 'stage', 'package', 'self-check'))
    parser.add_argument('--source', type=Path, default=SOURCE)
    parser.add_argument('--client', type=Path, default=p.CLIENT_DEFAULT)
    parser.add_argument('--output', type=Path, default=STAGE)
    args = parser.parse_args()
    if args.action == 'reserve':
        reserve(args.source)
    elif args.action == 'stage':
        stage(args.source, args.client, args.output)
    elif args.action == 'package':
        package(args.source, args.client, args.output)
    else:
        self_check()
