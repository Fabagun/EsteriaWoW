"""Stage matched Slime Giant/Centaur racial data against current client/server baselines."""

import json
import re
import shutil
from pathlib import Path
import struct
import subprocess

from PIL import Image

import drakkin_drakonid_racials as d
import retroported_race_pack as p

WORK = Path('G:/RetroportWork/slime-centaur-racials')
STAGE = WORK / 'stage'
MIGRATION = p.ROOT / 'data/sql/updates/pending_db_world/rev_20261021010000000_slime_centaur_racials.sql'
VEHICLE, SEAT, SLIME = 900306, 900408, 900720
FLIGHT_MODEL, FLIGHT_DISPLAY = 120087, 60078
PASSIVE, ACTIVE = 0x50, 0x10
SPECS = (
    (111010, 'Bouncy', 'Reduces fall damage by 50%. Damaging falls bounce you back into the air. '
     'Bounce height is 25% of the drop, up to 12 yards. Bounce landings cannot trigger another bounce.',
     {**d.effect(1, 4, 0)}, True),
    (111011, 'Toxic Composition', 'Reduces all poison damage received by 20% and poison duration by 10%.',
     {**d.effect(1, 245, -10, 4)}, True),
    (111012, 'Reconstitution', 'Regenerates 1% maximum health every 5 seconds outside combat, even while moving.',
     {**d.effect(1, 226, 0, EffectAuraPeriod=5000)}, True),
    (111013, 'Slime Trail', 'For 6 seconds, leave sticky slimes beneath your feet. Each slime lives for 6 seconds, '
     'slows enemies within 3 yards by 30%, and attacks enemies fighting you.',
     {**d.effect(1, 226, 0, EffectAuraPeriod=1000), 'DurationIndex': 32, 'RecoveryTime': 120000}, False),
    (111014, 'Sticky Slime', 'Movement speed reduced by 30%.',
     {**d.effect(1, 33, -30, target=6), **d.effect(2, 226, 0, target=6, EffectAuraPeriod=200),
      'DurationIndex': 39, 'RangeIndex': 2,
      'Attributes': 0x04000010, 'DispelType': 0}, False),
    (111020, 'Polearm Specialty', 'Grants 5 Expertise while wielding a polearm.',
     {**d.effect(1, 240, 5), 'EquippedItemClass': 2, 'EquippedItemSubclass': 64}, True),
    (111021, 'High Horsepower', 'Reduces knockback distance by 20% and knockdown duration by 10%.',
     {**d.effect(1, 4, 0)}, True),
    (111022, 'Warband Plainsrunner', 'After running for 8 seconds outside combat, gain 5% movement speed indoors '
     'or 10% outdoors. Moving party members within 30 yards share the benefit. Stopping or entering combat '
     'removes it. Does not stack with another Centaur.', {**d.effect(1, 4, 0)}, True),
    (111023, 'Warband Plainsrunner', 'Movement speed increased while running outside combat near a Centaur.',
     {**d.effect(1, 4, 10, target=21), 'DurationIndex': 39}, False),
    (111024, 'Warcry of the Plains', 'Increases your damage dealt by 5% and party members\' damage by 3% '
     'within 30 yards for 10 seconds. Does not stack with another Centaur\'s Warcry.',
     {'Effect_1': 3, 'ImplicitTargetA_1': 1, 'RecoveryTime': 120000}, False),
    (111025, 'Warcry of the Plains', 'Damage dealt increased. Does not stack with another Centaur\'s Warcry.',
     {**d.effect(1, 79, 5, 127, target=21), 'DurationIndex': 1}, False),
    (111026, 'Unaided Travel', 'A party or raid member can ride you during Gallop or Flight.',
     {**d.effect(1, 296, 0, VEHICLE), 'DurationIndex': 21, 'Attributes': 0x90}, False),
    (111027, 'Unaided Flight', 'A party or raid member can ride you during Flight.',
     {**d.effect(1, 296, 0, VEHICLE + 1), **d.effect(2, 206, 150),
      'DurationIndex': 21, 'Attributes': 0x90}, False),
)
GRANTS = {72: (111010, 111011, 111012, 111013), 73: (111020, 111021, 111022, 111024)}
BINDINGS = {111012: 'spell_slime_reconstitution', 111013: 'spell_slime_trail',
            111014: 'spell_sticky_slime',
            111023: 'spell_centaur_plainsrunner_speed',
            111024: 'spell_centaur_warcry',
            **{i: 'spell_centaur_travel_passenger' for i in range(111000, 111004)}}


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def spell_sql(table, records):
    columns = d.spell_columns()
    statements = []
    for raw in records:
        row = struct.unpack('<234I', raw)
        names, values = [], []
        for i, (name, kind) in enumerate(columns):
            names.append('`' + name + '`')
            values.append(d._quote(p._string(table.strings, row[i]).decode()) if kind == 'string'
                          else d._sql_value(row[i], kind))
        statements.append(f'DELETE FROM `spell_dbc` WHERE `ID` = {row[0]};\n'
                          'INSERT INTO `spell_dbc` (' + ', '.join(names) + ') VALUES\n('
                          + ', '.join(values) + ');')
    return '\n'.join(statements) + '\n'


def overlay_sql(name, data, identifiers):
    schema = (p.ROOT / 'data/sql/base/db_world' / (name + '.sql')).read_text()
    definitions = re.findall(r'^\s*`([^`]+)`\s+([^\n,]+),', schema, re.M)
    table = p.RawWdbc(data)
    assert len(definitions) * 4 == table.record_size, (name, len(definitions), table.record_size)
    columns = ', '.join('`' + column + '`' for column, _ in definitions)
    rows = []
    for raw in table.records:
        if p._value(raw, 0) not in identifiers:
            continue
        values = []
        for i, (_, kind) in enumerate(definitions):
            value = p._value(raw, i * 4)
            if 'char' in kind or 'text' in kind:
                values.append(d._quote(p._string(table.strings, value).decode()))
            else:
                values.append(d._sql_value(value, 'float' if kind.startswith('float') else
                                          'unsigned' if 'unsigned' in kind else 'signed'))
        rows.append('(' + ', '.join(values) + ')')
    assert len(rows) == len(identifiers)
    return (f'DELETE FROM `{name}` WHERE `ID` IN ({", ".join(map(str, sorted(identifiers)))});\n'
            f'INSERT INTO `{name}` ({columns}) VALUES\n' + ',\n'.join(rows) + ';\n')


def spells(data):
    table = p.RawWdbc(data)
    index, columns = d.field_index(), d.spell_columns()
    rows = {p._value(row, 0): row for row in table.records}
    pool, additions = bytearray(table.strings), []
    for identifier, name, description, fields, passive in SPECS:
        if identifier in rows:
            old_name = p._string(table.strings, p._value(rows[identifier], 136 * 4)).decode()
            if old_name != name:
                raise ValueError(f'Spell collision: {identifier}: {old_name}')
        row = [0] * 234
        defaults = {'ID': identifier, 'Attributes': PASSIVE if passive else ACTIVE,
                    'CastingTimeIndex': 1, 'DurationIndex': 21 if passive else 0, 'RangeIndex': 1,
                    'SchoolMask': 1, 'EquippedItemClass': -1,
                    'SpellIconID': p._value(rows[20550 if passive else 20572], index['SpellIconID'] * 4)}
        for key, value in {**defaults, **fields}.items():
            row[index[key]] = d._pack(value, columns[index[key]][1])
        for field, value in ((136, name), (153, 'Slime Giant Racial' if identifier < 111020 else 'Centaur Racial'),
                             (170, description), (187, description)):
            row[field] = len(pool)
            pool.extend(value.encode() + b'\0')
        additions.append(struct.pack('<234I', *row))
    owned = {s[0] for s in SPECS}
    # Retain learned legacy travel ranks, but update their visible names and requirements together.
    for identifier in range(111000, 111004):
        row = rows[identifier]
        for field, value in ((136, 'Gallop' if identifier < 111002 else 'Flight'),
                             (170, 'Travel speed scales with your riding training. '
                              'Requires a suitable location and applicable flying training. '
                              'A party or raid member can ride with you.'),
                             (187, 'Travel speed scales with your riding training.')):
            row = p._replace(row, field * 4, 4, len(pool))
            pool.extend(value.encode() + b'\0')
        additions.append(row)
        owned.add(identifier)
    result = table.build([r for r in table.records if p._value(r, 0) not in owned] + additions, bytes(pool))
    return result, spell_sql(p.RawWdbc(result), additions)


def knockdown_header(visual_data, kit_data):
    kits = p.RawWdbc(kit_data)
    # SpellVisualKit.AnimID (field 2) identifies actual Knockdown motion (Wrath animation 121).
    targets = {p._value(r, 0) for r in kits.records if p._value(r, 8) == 121}
    visuals = p.RawWdbc(visual_data)
    identifiers = sorted(p._value(r, 0) for r in visuals.records
                         if p._value(r, 12) in targets or p._value(r, 16) in targets)
    assert 522 in identifiers and targets
    body = ', '.join(map(str, identifiers))
    header = ('// Generated by tools/slime_centaur_racials.py from target SpellVisual/SpellVisualKit.\n'
              '#ifndef SLIME_CENTAUR_RACIAL_DATA_H\n#define SLIME_CENTAUR_RACIAL_DATA_H\n\n'
              '#include <algorithm>\n#include <array>\n#include "Define.h"\n\n'
              'namespace SlimeCentaurRacials\n{\n'
              f'    constexpr std::array<uint32, {len(identifiers)}> KnockdownVisuals =\n    {{\n')
    import textwrap
    header += textwrap.fill(body, width=112, initial_indent='        ', subsequent_indent='        ')
    header += ('\n    };\n\n    constexpr bool IsKnockdownVisual(uint32 visual)\n    {\n'
               '        return std::binary_search(KnockdownVisuals.begin(), KnockdownVisuals.end(), visual);\n'
               '    }\n\n    static_assert(IsKnockdownVisual(522));\n'
               '    static_assert(!IsKnockdownVisual(0));\n}\n\n#endif\n')
    save(p.ROOT / 'src/server/shared/SlimeCentaurRacialData.h', header.encode())
    return identifiers


def vehicle(data, seat_data):
    table, seats = p.RawWdbc(data), p.RawWdbc(seat_data)
    assert not any(p._value(r, 0) == VEHICLE for r in table.records)
    assert not any(p._value(r, 0) == SEAT for r in seats.records)
    row = bytearray(next(r for r in table.records if p._value(r, 0) == 117))
    struct.pack_into('<I', row, 0, VEHICLE)
    struct.pack_into('<8I', row, 24, SEAT, 0, 0, 0, 0, 0, 0, 0)
    struct.pack_into('<I', row, 36 * 4, 0)
    seat = bytearray(next(r for r in seats.records if p._value(r, 0) == 1649))
    struct.pack_into('<I', seat, 0, SEAT)
    flags = (p._value(seat, 4) | 0x02000000) & ~(0x00000200 | 0x00000800 | 0x20000000)
    struct.pack_into('<I', seat, 4, flags)
    struct.pack_into('<I', seat, 8, 39)  # Centaur's authored rider socket.
    struct.pack_into('<3f', seat, 12, 0.0, 0.0, 0.0)
    struct.pack_into('<I', seat, 45 * 4, p._value(seat, 45 * 4) | 0x20)
    flight, flight_seat = bytearray(row), bytearray(seat)
    struct.pack_into('<I', flight, 0, VEHICLE + 1)
    struct.pack_into('<I', flight, 24, SEAT + 1)
    struct.pack_into('<I', flight_seat, 0, SEAT + 1)
    struct.pack_into('<I', flight_seat, 8, 0)  # Ohn'ahra's authored back socket.
    return (table.build([*table.records, bytes(row), bytes(flight)]),
            seats.build([*seats.records, bytes(seat), bytes(flight_seat)]))


def world_sql(spell_statements):
    result = '-- Slime Giant Horde and Centaur Alliance racial integration.\n' + spell_statements
    for identifier, binding in BINDINGS.items():
        result += (f'DELETE FROM `spell_script_names` WHERE `spell_id` = {identifier} AND `ScriptName` = '
                   f"'{binding}';\nINSERT INTO `spell_script_names` (`spell_id`, `ScriptName`) VALUES\n"
                   f"({identifier}, '{binding}');\n")
    for race, identifiers in GRANTS.items():
        ids = ', '.join(map(str, identifiers))
        result += f'DELETE FROM `custom_race_start_spell` WHERE `race` = {race} AND `spell` IN ({ids});\n'
        result += 'INSERT INTO `custom_race_start_spell` (`race`, `classMask`, `spell`, `comment`) VALUES\n'
        result += ',\n'.join(f"({race}, 0, {i}, 'Racial: {next(s[1] for s in SPECS if s[0] == i)}')"
                            for i in identifiers) + ';\n'
    result += ('UPDATE `chrraces_dbc` SET `Flags` = `Flags` | 1 WHERE `ID` IN (71, 74);\n'
               'UPDATE `chrraces_dbc` SET `Flags` = `Flags` & ~1 WHERE `ID` IN (72, 73);\n')
    result += (f'DELETE FROM `creature_template` WHERE `entry` = {SLIME};\n'
               'INSERT INTO `creature_template` (`entry`, `name`, `minlevel`, `maxlevel`, `faction`, '
               '`type`, `BaseAttackTime`, `unit_class`, `ScriptName`) VALUES\n'
               f"({SLIME}, 'Sticky Slime', 1, 80, 35, 4, 2000, 1, 'npc_racial_sticky_slime');\n"
               f'DELETE FROM `creature_template_model` WHERE `CreatureID` = {SLIME};\n'
               'INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, '
               '`DisplayScale`, `Probability`) VALUES\n'
               f'({SLIME}, 0, 15436, 1, 1);\n')
    result += (f'DELETE FROM `creature_model_info` WHERE `DisplayID` = {FLIGHT_DISPLAY};\n'
               'INSERT INTO `creature_model_info` (`DisplayID`, `BoundingRadius`, `CombatReach`, `Gender`, '
               f'`DisplayID_Other_Gender`) VALUES\n({FLIGHT_DISPLAY}, 0.5, 1.5, 2, 0);\n')
    return result


def portraits():
    from derive_playable_race_portraits import encode_portrait, validate_portrait
    entries, receipts = {}, []
    with p.ClientFiles(str(p.CLIENT_DEFAULT / 'Data'), 'enUS') as files:
        template = files.find('Interface\\Glues\\CharacterCreate\\UI-CharacterCreate-HumanMale.blp')[0]
    for faction in ('Alliance', 'Horde'):
        for sex in ('Male', 'Female'):
            source = Path('R:/Users/Zach/Pictures/Portraits') / faction / (
                f'Charactercreate-races_centaur-{sex.lower()}_{faction.lower()}.png')
            image = Image.open(source).convert('RGBA')
            portrait = image.resize((64, 64), Image.Resampling.LANCZOS)
            data = encode_portrait(portrait, template)
            validate_portrait(data, source)
            token = 'Centaur' + faction
            for name in (f'Interface\\Glues\\CharacterCreate\\UI-CharacterCreate-{token}{sex}.blp',
                         f'Interface\\CharacterFrame\\TemporaryPortrait-{sex}-{token}.blp',
                         f'Interface\\Glues\\CharacterSelect\\ECS-Portrait-{token}{sex}.blp'):
                entries[name] = data
                if name.startswith('Interface\\CharacterFrame\\'):
                    entries[name[:-4]] = data
            receipts.append({'source': str(source), 'sha256': p.sha256(source), 'size': list(image.size)})
    return entries, receipts


def ohnahra():
    import centaur_source as source
    from slime_giant_source import references
    from wotlkconv.m2 import parse_m2, parse_skin
    config = dict(line.split('=', 1) for line in source.CONFIG.read_text().splitlines() if '=' in line)
    assert config['build'] == source.BUILD and config['product'] == 'wow'
    root = WORK / 'ohnahra/source'
    root.mkdir(parents=True, exist_ok=True)
    pending, completed, assets = {(4077816, 'm2'), (4080563, 'blp')}, set(), {}
    while pending:
        identifier, extension = min(pending)
        pending.remove((identifier, extension))
        if (identifier, extension) in completed:
            continue
        path = root / f'{identifier}.{extension}'
        if not path.exists():
            result = subprocess.run([str(source.PROBE), str(source.CONFIG), f'retail/{path.name}',
                                     '--extract', str(path)], capture_output=True, text=True)
            save(path.with_suffix('.log'), (result.stdout + result.stderr).encode())
            result.check_returncode()
        data = path.read_bytes()
        if extension in ('m2', 'skel'):
            pending.update(references(data) - completed)
        if extension == 'skin':
            skin = parse_skin(data)
            assert skin.vertices and skin.indices
        completed.add((identifier, extension))
        assets[path.name] = {'path': str(path), 'sha256': p.sha256(path), 'bytes': len(data)}
        print('SOURCE Ohn\'ahra:', path.name, flush=True)
    model = parse_m2((root / '4077816.m2').read_bytes())
    assert model.version == 274 and model.vertex_count > 0
    report = {'npc': 194796, 'display': 106285, 'model': 12885, 'model_file': 4077816,
              'texture_file': 4080563, 'product': 'wow', 'build': source.BUILD,
              'identity_url': 'https://www.wowhead.com/npc=194796/ohnahra',
              'complete': True, 'assets': assets,
              'attachments': sorted({a['id'] for a in model.attachments}),
              'sequences': sorted({s['id'] for s in model.sequences})}
    save(WORK / 'ohnahra/inventory.json', (json.dumps(report, indent=2) + '\n').encode())
    return report


def flight_tables(model_data, display_data):
    result = {}
    for name, data, identifier, donor in (('CreatureModelData', model_data, FLIGHT_MODEL, 3654),
                                         ('CreatureDisplayInfo', display_data, FLIGHT_DISPLAY, 21243)):
        table = p.RawWdbc(data)
        assert not any(p._value(r, 0) == identifier for r in table.records), name
        pool = bytearray(table.strings)
        row = p._clone_strings(name, table, next(r for r in table.records if p._value(r, 0) == donor), pool)
        row = p._replace(row, 0, 4, identifier)
        if name == 'CreatureModelData':
            row = p._set_string(row, 2, pool, 'retail\\4077816.m2')
            row = p._replace(row, 4, 4, 1027)
            # Pinned Retail model 12885 collision, rider height and bounds at unit display scale.
            for field, value in ((14, 1058828743), (15, 1073873013), (16, 1066209777),
                                 (17, -1064975691), (18, -1083510966), (19, -1111975645),
                                 (20, 1064498007), (21, 1064092958), (22, 1073925900)):
                row = p._replace(row, field * 4, 4, value & 0xFFFFFFFF)
        else:
            row = p._replace(row, 4, 4, FLIGHT_MODEL)
            row = row[:16] + struct.pack('<f', 1.0) + row[20:]
            for field, value in ((6, '4080563.blp'), (7, '4080563.blp'), (8, '')):
                row = p._set_string(row, field, pool, value)
        result[name] = table.build([*table.records, row], bytes(pool))
    return result


def render_migration(outputs, spell_statements):
    statements = world_sql(spell_statements)
    for name, table, identifiers in (('vehicle_dbc', 'Vehicle', {VEHICLE, VEHICLE + 1}),
                                     ('vehicleseat_dbc', 'VehicleSeat', {SEAT, SEAT + 1}),
                                     ('creaturemodeldata_dbc', 'CreatureModelData', {FLIGHT_MODEL}),
                                     ('creaturedisplayinfo_dbc', 'CreatureDisplayInfo', {FLIGHT_DISPLAY})):
        statements += overlay_sql(name, outputs[table], identifiers)
    for form in (27, 29):
        statements += ('DELETE FROM `player_shapeshift_model` WHERE `RaceID` = 73 AND '
                       f'`ShapeshiftID` = {form} AND `CustomizationID` = 255 AND `GenderID` = 2;\n'
                       'INSERT INTO `player_shapeshift_model` (`ShapeshiftID`, `RaceID`, `CustomizationID`, '
                       f'`GenderID`, `ModelID`) VALUES\n({form}, 73, 255, 2, {FLIGHT_DISPLAY});\n')
    return statements


def stage():
    STAGE.mkdir(parents=True, exist_ok=True)
    source = ohnahra()
    tables = ('Spell', 'Vehicle', 'VehicleSeat', 'ChrRaces', 'CharBaseInfo', 'SpellVisual', 'SpellVisualKit',
              'CreatureModelData', 'CreatureDisplayInfo')
    with p.ClientFiles(str(p.CLIENT_DEFAULT / 'Data'), 'enUS') as files:
        baseline = {name: files.find(p.DBC_ROOT + name + '.dbc')[0] for name in tables}
        lua = files.find(p.GLUE_ROOT + 'CharacterCreate.lua')[0].decode('utf-8-sig')
        info_lua = files.find(p.GLUE_ROOT + 'CharacterInfo.lua')[0].decode('utf-8-sig')
    outputs = {}
    outputs['Spell'], statements = spells(baseline['Spell'])
    outputs['Vehicle'], outputs['VehicleSeat'] = vehicle(baseline['Vehicle'], baseline['VehicleSeat'])
    outputs.update(flight_tables(baseline['CreatureModelData'], baseline['CreatureDisplayInfo']))
    table = p.RawWdbc(baseline['ChrRaces'])
    records = [p._replace(r, 4, 4, p._value(r, 4) | 1) if p._value(r, 0) in (71, 74) else r
               for r in table.records]
    outputs['ChrRaces'] = table.build(records)
    table = p.RawWdbc(baseline['CharBaseInfo'])
    outputs['CharBaseInfo'] = table.build([r for r in table.records if r[0] not in (71, 74)])
    visual_ids = knockdown_header(baseline['SpellVisual'], baseline['SpellVisualKit'])
    anchor = 'local hiddenRace = '
    start = lua.index(anchor)
    end = lua.index('\n', start)
    lua = lua[:end] + ' or strupper(fileString) == "SLIMEGIANTALLIANCE" or strupper(fileString) == "CENTAURHORDE"' + lua[end:]
    from lupa.lua51 import LuaRuntime
    LuaRuntime().eval('function(s) local f,e=loadstring(s); assert(f,e); end')(lua)
    entries, portrait_receipts = portraits()
    entries[p.GLUE_ROOT + 'CharacterCreate.lua'] = lua.encode()
    for race, key in ((72, 'SLIMEGIANTHORDE'), (73, 'CENTAURALLIANCE')):
        traits = [{'name': name, 'icon': 'Ability_Racial_ShadowMeld', 'description': description}
                  for identifier, name, description, _, _ in SPECS if identifier in GRANTS[race]]
        if race == 73:
            traits.insert(1, {'name': 'Unaided Travel', 'icon': 'Ability_Mount_RidingHorse',
                             'description': 'Learn mounts for your collection, but travel using Gallop and '
                             'Ohn\'ahra Flight. Riding training and zone restrictions apply. '
                             'A party or raid member can ride with you.'})
        text = '{' + ','.join('{name=' + json.dumps(t['name']) + ',icon=' + json.dumps(t['icon'])
                             + ',description=' + json.dumps(t['description']) + '}' for t in traits) + '}'
        info_lua += f'\nRaceInfoByFileString.{key}.RacialTraits={text};\n'
    LuaRuntime().eval('function(s) local f,e=loadstring(s); assert(f,e); end')(info_lua)
    entries[p.GLUE_ROOT + 'CharacterInfo.lua'] = info_lua.encode()
    for name, data in outputs.items():
        save(STAGE / 'client-dbc' / (name + '.dbc'), data)
        save(STAGE / 'baseline-client' / (name + '.dbc'), baseline[name])
        entries[p.DBC_ROOT + name + '.dbc'] = data
        if name != 'CharBaseInfo':
            server = p.SERVER_DBC_ROOT / (name + '.dbc')
            # Server spell rows are intentionally sparse; SQL supplies the new racial rows.
            if server.exists():
                old = server.read_bytes()
                if name == 'Spell':
                    new, _ = spells(old)
                elif name == 'ChrRaces':
                    t = p.RawWdbc(old)
                    new = t.build([p._replace(r, 4, 4, p._value(r, 4) | 1)
                                   if p._value(r, 0) in (71, 74) else r for r in t.records])
                else:
                    t, src = p.RawWdbc(old), p.RawWdbc(data)
                    identifiers = {'Vehicle': {VEHICLE, VEHICLE + 1}, 'VehicleSeat': {SEAT, SEAT + 1},
                                   'CreatureModelData': {FLIGHT_MODEL},
                                   'CreatureDisplayInfo': {FLIGHT_DISPLAY}}[name]
                    pool = bytearray(t.strings)
                    rows = [r for r in src.records if p._value(r, 0) in identifiers]
                    if name in ('CreatureModelData', 'CreatureDisplayInfo'):
                        rows = [p._clone_strings(name, src, row, pool) for row in rows]
                    new = t.build([*t.records, *rows], bytes(pool))
                save(STAGE / 'baseline-server' / server.name, old)
                save(STAGE / 'server' / server.name, new)
    save(MIGRATION, render_migration(outputs, statements).encode())
    storm = p.Storm(p.DLL_DEFAULT)
    archive = STAGE / 'slime-centaur-racials-overlay.MPQ'
    if archive.exists():
        archive.unlink()
    storm.create_archive(archive, entries)
    handle = storm.open_archive(archive)
    try:
        for key, value in entries.items():
            assert storm.read(handle, key) == value, key
    finally:
        storm.dll.SFileCloseArchive(handle)
    client_archives = {}
    for relative in (p.GLOBAL_ARCHIVE_REL, p.LOCALE_ARCHIVE_REL):
        live, target = p.CLIENT_DEFAULT / relative, STAGE / 'client' / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        before = p.sha256(live)
        shutil.copy2(live, target)
        assert p.sha256(target) == before
        storm.replace_archive_entries(target, entries)
        handle = storm.open_archive(target)
        try:
            for key, value in entries.items():
                assert storm.read(handle, key) == value, (str(relative), key)
        finally:
            storm.dll.SFileCloseArchive(handle)
        assert p.sha256(live) == before, 'Live archive changed during staging'
        client_archives[str(relative)] = {'before': before, 'after': p.sha256(target), 'source': str(target)}
    report = {'stage': str(STAGE), 'installed': False, 'built': False, 'live_accepted': False,
              'portraits': portrait_receipts, 'knockdown_visual_ids': visual_ids,
              'entries': len(entries), 'archive_sha256': p.sha256(archive)}
    report['client_archives'] = client_archives
    report['ohnahra'] = source
    allocation = json.loads(p.ALLOCATION_PATH.read_text())
    allocation['extra_allocations']['slime_centaur_racials'] = {
        'CreatureModelData': [FLIGHT_MODEL, FLIGHT_MODEL],
        'CreatureDisplayInfo': [FLIGHT_DISPLAY, FLIGHT_DISPLAY], 'Spell': [111010, 111027],
        'Vehicle': [VEHICLE, VEHICLE + 1], 'VehicleSeat': [SEAT, SEAT + 1]}
    allocation['dbc_ranges']['CreatureDisplayInfo'][1] = max(
        FLIGHT_DISPLAY, allocation['dbc_ranges']['CreatureDisplayInfo'][1])
    save(p.ALLOCATION_PATH, (json.dumps(allocation, indent=2) + '\n').encode())
    save(STAGE / 'report.json', (json.dumps(report, indent=2) + '\n').encode())
    print('STAGED racial spells, faction gates, portraits and vehicle seats; MPQ readback passed:', STAGE)


if __name__ == '__main__':
    stage()
