"""Stage the supplied HD Outland Arakkoa player pack as Horde race 68.

The pack was built for a different server: race 45, spells 13990001-5, display ids 977475/6 and a
private Spell/Sound/CharSections numbering. Nothing from it is copied verbatim. Every row is
rebased onto Esteria's free ids, every asset moves under `custom\\arakkoa\\`, and each id is checked
against the live client tables before it is written.
"""

import argparse
from collections import Counter, defaultdict
import copy
import hashlib
import json
from pathlib import Path, PureWindowsPath
import shutil
import struct

from PIL import Image
from wotlkconv.blp import Blp
from wotlkconv.m2 import parse_m2, parse_skin
import retroported_race_pack as p
import ogre_furbolg_race_pack as o
import race_portrait_pack as portraits
import sethrak_race_pack as s

TARGET = Path('R:/Users/Zach/Documents/GitHub/EsteriaWoW')
PACKAGE = TARGET / 'Arakkoa-race'
PACKAGE_MPQ = PACKAGE / 'client/patch-ZR.MPQ'
PACKAGE_DBC = PACKAGE / 'server/dbc'
REFORGED_MPQ = Path('G:/Downloads/HDWoWModels/Project Reforged/Data/patch-V.MPQ')
STAGE = Path('G:/RetroPorterWork/arakkoa/stage-20261011')
ASSET = Path('Data/Patch-H.MPQ')
RACE = 68
SOURCE_RACE = 45
TOKEN = 'ArakkoaHorde'
KEY = TOKEN.upper()
PREFIX = 'custom\\arakkoa\\'
DONOR_RACE = 2
CLASSES = [1, 2, 3, 4, 5, 6, 7, 8, 9, 11]
SPELLS = (13990001, 13990002, 13990003, 13990004, 13990005)
RANGES = {'CreatureModelData': {'male': 120075, 'female': 120076},
          'CreatureDisplayInfo': {'male': 60066, 'female': 60067},
          'CharSections': [1116300, 1117299], 'CharHairGeosets': [1116300, 1116399],
          'BarberShopStyle': [1116300, 1116499], 'CharStartOutfit': [22180, 22199],
          'NameGen': [90000, 92999]}
EXTRA = {'SoundEntries': [414401, 414406], 'CreatureSoundData': [9045001, 9045001],
         'Spell': [SPELLS[0], SPELLS[-1]], 'EmotesTextSound': [680001, 680099]}
TABLES = s.TABLES + ('SoundEntries', 'CreatureSoundData', 'EmotesTextSound', 'Spell', 'EmotesText')
SERVER_TABLES = s.SERVER_TABLES + ('Spell',)
SPELL_STRINGS = (tuple(range(136, 152)) + tuple(range(153, 169)) + tuple(range(170, 186))
                 + tuple(range(187, 203)))
SOUND_STRINGS = (2,) + tuple(range(3, 13)) + (23,)
MIGRATION = TARGET / 'data/sql/updates/pending_db_world/rev_20261011030000000_arakkoa_horde.sql'
RACIALS = ((SPELLS[0], "Outcast's Curse"), (SPELLS[1], 'Feathered Descent'), (SPELLS[2], 'Lore of Skettis'),
           (SPELLS[3], 'Flight of the Raven'), (SPELLS[4], 'Skyward Glide'))


def local(root, key):
    return root.joinpath(*PureWindowsPath(key).parts)


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8', newline='\n')


def pin(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_bytes() != data:
        raise ValueError('Baseline changed: ' + str(path))
    path.write_bytes(data)


def package_table(name):
    return p.RawWdbc((PACKAGE_DBC / (name + '.dbc')).read_bytes())


def text(table, offset):
    return p._string(table.strings, offset).decode('utf-8')


def prefixed(path):
    return PREFIX + path if path else ''


def appearance():
    """Per-gender option counts and rows of the supplied CharSections, with completeness proof."""
    table = package_table('CharSections')
    selected = [r for r in table.records if p._value(r, 4) == SOURCE_RACE]
    result = {}
    for gender in (0, 1):
        by_kind = defaultdict(set)
        cells = set()
        for r in selected:
            if p._value(r, 8) != gender:
                continue
            kind, style, color = p._value(r, 12), p._value(r, 32), p._value(r, 36)
            by_kind[kind].add((style, color))
            cells.add((kind, style, color))
        skins = sorted({c for _, c in by_kind[0]})
        faces = sorted({v for v, _ in by_kind[1]})
        hair_styles = sorted({v for v, _ in by_kind[3]})
        hair_colors = sorted({c for _, c in by_kind[3]})
        facial = sorted({v for v, _ in by_kind[2]}) or [0]
        assert skins == list(range(len(skins))) and faces == list(range(len(faces)))
        assert hair_styles == list(range(len(hair_styles))) and hair_colors == list(range(len(hair_colors)))
        assert all((0, 0, c) in cells and (4, 0, c) in cells for c in skins), 'Skin/underwear gap'
        assert all((1, f, c) in cells for f in faces for c in skins), 'Face/skin gap'
        assert all((3, v, c) in cells for v in hair_styles for c in hair_colors), 'Hair gap'
        result[gender] = {'skins': len(skins), 'faces': len(faces), 'hair_styles': len(hair_styles),
                          'hair_colors': len(hair_colors), 'facial': len(facial)}
    return result


def manifest():
    shape = appearance()
    profiles = {}
    for gender, a in shape.items():
        counts = (a['skins'], a['faces'], a['hair_styles'], a['hair_colors'], a['facial'])
        labels = ('Skin Color', 'Face', 'Hair Style', 'Hair Color', 'Facial Hair')
        profiles[str(gender)] = {'capacities': list(counts), 'options': [
            {'label': label, 'choices': list(range(count))} for label, count in zip(labels, counts)]}
    models = {}
    for sex in ('Male', 'Female'):
        models[sex.lower()] = {'model_id': RANGES['CreatureModelData'][sex.lower()],
            'display_id': RANGES['CreatureDisplayInfo'][sex.lower()],
            'model_path': PREFIX + 'Character\\Arakkoa\\' + sex + '\\Arakkoa' + sex + '.m2'}
    return {'schema_version': 1, 'slug': 'arakkoa_horde', 'name': 'Arakkoa', 'race_ids': [RACE],
        'enum': 'RACE_ARAKKOA_HORDE', 'faction': 'horde', 'source_race_id': DONOR_RACE,
        'source_package_race_id': SOURCE_RACE, 'legacy_mask_race': DONOR_RACE, 'visual_base_race': DONOR_RACE,
        'client_file_strings': {str(RACE): TOKEN}, 'glue_token': KEY, 'helmet_prefix': 'Ak',
        'start_profile': 'durotar', 'donor_totem_race': DONOR_RACE, 'classes': CLASSES,
        'source_patch_root': str(PACKAGE), 'runtime_patch_root': str(STAGE / 'assets'),
        'models': models,
        'appearance': {'mode': 'native-stock-five-byte-v1', 'source': 'hd-outland-arakkoa-pack',
            'supported_genders': [0, 1], 'profiles': profiles,
            'equipped_armor_geosets': 'authored-player-geosets', 'hide_helm': False},
        'random_playerbot_enabled': False,
        'custom_racial_spells': [{'spell': spell, 'name': name} for spell, name in RACIALS],
        'extra_allocations': EXTRA}


def allocation():
    result = p.load_json(TARGET / 'data/retroported-races/allocation.json')
    if any(RACE in ids for slug, ids in result['race_ids'].items() if slug != 'arakkoa_horde'):
        raise ValueError('Race 68 is occupied')
    for slug, tables in result['race_allocations'].items():
        if slug == 'arakkoa_horde':
            if tables != RANGES:
                raise ValueError('Arakkoa allocation changed')
            continue
        for name, bounds in RANGES.items():
            other = tables.get(name)
            if isinstance(bounds, list) and isinstance(other, list):
                if max(bounds[0], other[0]) <= min(bounds[1], other[1]):
                    raise ValueError('Allocation overlap: ' + slug + '/' + name)
            elif isinstance(other, dict) and isinstance(bounds, dict):
                if (set(bounds.values()) - {0}) & (set(other.values()) - {0}):
                    raise ValueError('Model/display overlap: ' + slug)
    for slug, extra in result.get('extra_allocations', {}).items():
        if slug == 'arakkoa_horde':
            continue
        for name, bounds in EXTRA.items():
            other = extra.get(name)
            if other and max(bounds[0], other[0]) <= min(bounds[1], other[1]):
                raise ValueError('Extra allocation overlap: ' + slug + '/' + name)
    result['race_ids']['arakkoa_horde'] = [RACE]
    result['race_allocations']['arakkoa_horde'] = copy.deepcopy(RANGES)
    result.setdefault('extra_allocations', {})['arakkoa_horde'] = copy.deepcopy(EXTRA)
    for name, bounds in RANGES.items():
        result['dbc_ranges'][name][1] = max(result['dbc_ranges'][name][1],
            bounds[1] if isinstance(bounds, list) else max(bounds.values()))
    return result


def config():
    reserved = allocation()
    path = TARGET / 'modules/mod-custom-server/data/races/race_registry.json'
    registry = p.load_json(path)
    entry = {'id': RACE, 'species_key': 'arakkoa_horde', 'display_name': 'Arakkoa', 'faction': 'horde',
        'species_selection': False, 'start_profile': 'durotar', 'asset_owner': 'supplied_arakkoa',
        'legacy_mask_race': DONOR_RACE, 'visual_base_race': DONOR_RACE, 'supported_genders': [0, 1]}
    old = next((r for r in registry['playable'] if r['id'] == RACE), None)
    if old is not None and old != entry:
        raise ValueError('Registry slot 68 has a different owner')
    if any(r['id'] == RACE for r in registry['npc_only']):
        raise ValueError('Race 68 is reserved for NPC use')
    if old is None:
        registry['playable'].append(entry)
    registry['sources']['supplied_arakkoa'] = str(STAGE / 'assets')
    save(TARGET / 'data/retroported-races/arakkoa_horde.json', manifest())
    save(TARGET / 'data/retroported-races/allocation.json', reserved)
    save(path, registry)
    print('RESERVED Horde Arakkoa race 68', flush=True)


def rebase_textures(blob):
    """Append private texture strings; keep geometry and animation data unchanged."""
    result = bytearray(blob)
    count, start = struct.unpack_from('<2I', blob, 0x50)
    for i in range(count):
        at = start + i * 16
        kind, _, length, offset = struct.unpack_from('<4I', blob, at)
        if kind == 0 and length:
            name = blob[offset:offset + length].split(b'\0')[0].decode('ascii')
            path = (PREFIX + name).encode('ascii') + b'\0'
            struct.pack_into('<2I', result, at + 8, len(path), len(result))
            result.extend(path)
    return bytes(result)


def source_files():
    storm = p.Storm(p.DLL_DEFAULT)
    handle = storm.open_archive(PACKAGE_MPQ)
    try:
        return {name: storm.read(handle, name) for name, *_ in storm.list_files(handle)
                if name.lower().startswith(('character\\arakkoa\\', 'sound\\creature\\higharakkoa\\',
                                            'interface\\icons\\race_arakkoa'))}
    finally:
        storm.dll.SFileCloseArchive(handle)


def reforged_files():
    storm = p.Storm(p.DLL_DEFAULT)
    handle = storm.open_archive(REFORGED_MPQ)
    try:
        return {name: storm.read(handle, name) for name, *_ in storm.list_files(handle)
                if name.lower().startswith('creature\\arakkoaoutland\\') and name.lower().endswith('.blp')}
    finally:
        storm.dll.SFileCloseArchive(handle)


def assets():
    """Private-prefixed models and textures, the borrowed Outland textures and the female voice set."""
    source, result = source_files(), {}
    for name, data in source.items():
        low = name.lower()
        if low.startswith('character\\arakkoa\\'):
            result[PREFIX + name] = rebase_textures(data) if low.endswith('.m2') else data
        elif low.startswith('sound\\'):
            result[name] = data
    needed = set()
    for sex in ('Male', 'Female'):
        model = parse_m2(source['Character\\Arakkoa\\' + sex + '\\Arakkoa' + sex + '.m2'])
        needed.update(t['filename'] for t in model.textures if t['type'] == 0 and t['filename'])
    sections = package_table('CharSections')
    for row in sections.records:
        if p._value(row, 4) == SOURCE_RACE:
            needed.update(name for name in (text(sections, p._value(row, field * 4)) for field in (4, 5, 6))
                          if name)
    held = {key.casefold() for key in source}
    borrowed = reforged_files()
    by_name = {key.casefold(): (key, data) for key, data in borrowed.items()}
    for name in sorted(needed):
        if name.casefold() in held:
            continue
        key, data = by_name.get(name.casefold(), (None, None))
        if data is None:
            raise ValueError('Texture is in neither the pack nor Project Reforged: ' + name)
        result[PREFIX + key] = data
    return result


def tables(baseline):
    m, reserved, result = manifest(), allocation(), dict(baseline)
    p._ensure_id_free(result['ChrRaces'], 'ChrRaces', {RACE})
    result['ChrRaces'] = p._merge_chr_races(result['ChrRaces'], m, reserved)
    races = p.RawWdbc(result['ChrRaces'])
    pool, rows = bytearray(races.strings), []
    for row in races.records:
        if p._value(row, 0) == RACE:
            for field, value in ((1, 14), (2, 2), (7, 1), (12, 0), (13, 1), (68, 0)):
                row = p._replace(row, field * 4, 4, value)
            row = p._set_string(row, 6, pool, 'Ak')
        rows.append(row)
    result['ChrRaces'] = races.build(rows, bytes(pool))
    # Models: the pack's own size/collision/mount fields, with ids, path and sound rebased.
    models, displays = package_table('CreatureModelData'), package_table('CreatureDisplayInfo')
    package_models = {p._value(r, 0): r for r in models.records}
    package_displays = {p._value(r, 0): r for r in displays.records}
    for sex, display_source in (('male', 977475), ('female', 977476)):
        display = package_displays[display_source]
        model = package_models[p._value(display, 4)]
        table = p.RawWdbc(result['CreatureModelData'])
        pool = bytearray(table.strings)
        row = p._clone_strings('CreatureModelData', models, model, pool)
        row = p._replace(row, 0, 4, RANGES['CreatureModelData'][sex])
        row = p._set_string(row, 2, pool, m['models'][sex]['model_path'])
        row = p._replace(row, 4, 4, p._value(row, 4) | 0x804)
        result['CreatureModelData'] = s.append_rows(result['CreatureModelData'], 'CreatureModelData', [row], pool)
        table = p.RawWdbc(result['CreatureDisplayInfo'])
        row = p._replace(display, 0, 4, RANGES['CreatureDisplayInfo'][sex])
        row = p._replace(row, 4, 4, RANGES['CreatureModelData'][sex])
        for offset in (8, 12, 24, 28, 32, 36):
            row = p._replace(row, offset, 4, 0)
        row = row[:16] + struct.pack('<f', 1.0) + row[20:]
        result['CreatureDisplayInfo'] = s.append_rows(result['CreatureDisplayInfo'], 'CreatureDisplayInfo',
                                                      [row], bytearray(table.strings))
    result['CharBaseInfo'] = p._build_char_base_info(result['CharBaseInfo'], m)
    table = p.RawWdbc(result['CharStartOutfit'])
    donors = {}
    for row in sorted(table.records, key=lambda r: p._value(r, 0)):
        if row[4] == DONOR_RACE and row[5] in CLASSES and row[6] < 2 and row[7] == 0:
            donors[bytes(row[5:8])] = row
    assert len(donors) == 20, 'Missing Horde class/gender outfit'
    outfits = [p._replace(p._replace(r, 0, 4, RANGES['CharStartOutfit'][0] + i), 4, 1, RACE)
               for i, r in enumerate(donors.values())]
    result['CharStartOutfit'] = s.append_rows(result['CharStartOutfit'], 'CharStartOutfit', outfits)
    # Names: the pack's own Arakkoa name lists.
    names, source = package_table('NameGen'), p.RawWdbc(result['NameGen'])
    pool, additions = bytearray(source.strings), []
    for row in names.records:
        if p._value(row, 8) == SOURCE_RACE:
            clone = p._set_string(row, 1, pool, text(names, p._value(row, 4)))
            clone = p._replace(clone, 8, 4, RACE)
            additions.append(p._replace(clone, 0, 4, RANGES['NameGen'][0] + len(additions)))
    assert 0 < len(additions) <= RANGES['NameGen'][1] - RANGES['NameGen'][0] + 1
    result['NameGen'] = s.append_rows(result['NameGen'], 'NameGen', additions, pool)
    # Appearance rows come straight from the pack's CharSections with only ids/race/paths rebased.
    package = package_table('CharSections')
    table = p.RawWdbc(result['CharSections'])
    pool, sections = bytearray(table.strings), []
    selected = sorted((r for r in package.records if p._value(r, 4) == SOURCE_RACE), key=lambda r: p._value(r, 0))
    for source_row in selected:
        row = p._replace(source_row, 0, 4, RANGES['CharSections'][0] + len(sections))
        row = p._replace(row, 4, 4, RACE)
        kind = p._value(row, 12)
        row = p._replace(row, 28, 4, 1 if kind == 1 else 17)
        for field in (4, 5, 6):
            value = text(package, p._value(source_row, field * 4))
            row = p._replace(row, field * 4, 4, 0)
            if value:
                row = p._set_string(row, field, pool, prefixed(value))
        sections.append(row)
    assert len(sections) <= RANGES['CharSections'][1] - RANGES['CharSections'][0] + 1
    result['CharSections'] = s.append_rows(result['CharSections'], 'CharSections', sections, pool)
    hair, facial = [], []
    for row in sorted((r for r in package_table('CharHairGeosets').records if p._value(r, 4) == SOURCE_RACE),
                      key=lambda r: p._value(r, 0)):
        row = p._replace(row, 0, 4, RANGES['CharHairGeosets'][0] + len(hair))
        hair.append(p._replace(row, 4, 4, RACE))
    for row in package_table('CharacterFacialHairStyles').records:
        if p._value(row, 0) == SOURCE_RACE:
            facial.append(p._replace(row, 0, 4, RACE))
    result['CharHairGeosets'] = s.append_rows(result['CharHairGeosets'], 'CharHairGeosets', hair)
    result['CharacterFacialHairStyles'] = s.append_rows(result['CharacterFacialHairStyles'],
        'CharacterFacialHairStyles', facial)
    barber = []
    source = p.RawWdbc(result['BarberShopStyle'])
    for gender in (0, 1):
        capacities = m['appearance']['profiles'][str(gender)]['capacities']
        for kind, field in ((0, 2), (2, 4), (3, 3)):
            donor_style = next(r for r in source.records if p._value(r, 4) == kind)
            for value in range(capacities[field]):
                row = donor_style
                for offset, n in ((0, RANGES['BarberShopStyle'][0] + len(barber)),
                                  (148, RACE), (152, gender), (156, value)):
                    row = p._replace(row, offset, 4, n)
                barber.append(row)
    assert len(barber) <= RANGES['BarberShopStyle'][1] - RANGES['BarberShopStyle'][0] + 1
    result['BarberShopStyle'] = s.append_rows(result['BarberShopStyle'], 'BarberShopStyle', barber)
    result['CharSections'] = o.order_charsections_entry(p.DBC_ROOT + 'CharSections.dbc', result['CharSections'])
    # Female voice set and race emotes.
    sounds, source = package_table('SoundEntries'), p.RawWdbc(result['SoundEntries'])
    package_sounds = {p._value(r, 0): r for r in sounds.records}
    pool, entries = bytearray(source.strings), []
    for identifier in range(EXTRA['SoundEntries'][0], EXTRA['SoundEntries'][1] + 1):
        row = package_sounds[identifier]
        for field in SOUND_STRINGS:
            value = text(sounds, p._value(row, field * 4))
            row = p._replace(row, field * 4, 4, p._append_string(pool, value) if value else 0)
        entries.append(row)
    result['SoundEntries'] = s.append_rows(result['SoundEntries'], 'SoundEntries', entries, pool)
    voices = package_table('CreatureSoundData')
    voice = next(r for r in voices.records if p._value(r, 0) == EXTRA['CreatureSoundData'][0])
    result['CreatureSoundData'] = s.append_rows(result['CreatureSoundData'], 'CreatureSoundData', [voice])
    live_sounds = {p._value(r, 0) for r in p.RawWdbc(result['SoundEntries']).records}
    for column in range(1, 38):
        assert p._value(voice, column * 4) in live_sounds | {0}, ('Voice sound entry is missing', column)
    text_ids = {p._value(r, 0) for r in p.RawWdbc(result['EmotesText']).records}
    emotes, skipped = [], []
    package_emotes = package_table('EmotesTextSound')
    for row in package_emotes.records:
        if p._value(row, 8) != SOURCE_RACE:
            continue
        if p._value(row, 4) not in text_ids or p._value(row, 16) not in live_sounds:
            skipped.append(p._value(row, 0))
            continue
        row = p._replace(row, 0, 4, EXTRA['EmotesTextSound'][0] + len(emotes))
        emotes.append(p._replace(row, 8, 4, RACE))
    assert emotes and len(emotes) <= EXTRA['EmotesTextSound'][1] - EXTRA['EmotesTextSound'][0] + 1
    result['EmotesTextSound'] = s.append_rows(result['EmotesTextSound'], 'EmotesTextSound', emotes)
    result['_skipped_emotes'] = skipped
    # Racial spells: rows from the pack's Spell.dbc, rebased only for string pools.
    package_spells = package_table('Spell')
    wanted = {p._value(r, 0): r for r in package_spells.records if p._value(r, 0) in SPELLS}
    assert set(wanted) == set(SPELLS)
    source = p.RawWdbc(result['Spell'])
    pool, spells = bytearray(source.strings), []
    for identifier in SPELLS:
        row = wanted[identifier]
        for field in SPELL_STRINGS:
            offset = p._value(row, field * 4)
            if offset:
                row = p._replace(row, field * 4, 4, p._append_string(pool, p._string(package_spells.strings, offset)))
        spells.append(row)
    result['Spell'] = s.append_rows(result['Spell'], 'Spell', spells, pool)
    return result


def sql_text(spell_names):
    sql = o.build_sql({'name': 'Arakkoa', 'race_id': RACE, 'faction': 'horde',
        'donor_start_race': DONOR_RACE, 'donor_totem_race': DONOR_RACE}).replace(
        'ogre_furbolg_race_pack.py', 'arakkoa_race_pack.py')
    sql = sql.rstrip() + '\n'
    sql += ('INSERT INTO `custom_race_start_spell` (`race`, `classMask`, `spell`, `comment`) VALUES\n'
            + ',\n'.join("(@RACE, 0, {}, '{}')".format(spell, ('Arakkoa racial: ' + name).replace("'", "''"))
                         for spell, name in spell_names) + ';\n\n')
    sql += o.CHRRACES_TEMPLATE.format(race=RACE, faction_template=2, male_display=RANGES['CreatureDisplayInfo']['male'],
        female_display=RANGES['CreatureDisplayInfo']['female'], prefix='Ak', base_language=1,
        file_string=TOKEN, alliance=1, name='Arakkoa')
    return sql.rstrip() + '\n'


def glue(original):
    result = {n: b.decode('utf-8-sig') for n, b in original.items()}

    def insert(name, anchor, payload):
        result[name] = o._insert_once(result[name], anchor, payload, 'Arakkoa ' + name)

    insert('CharacterInfo.lua', 'local EXACT_RACE_DATA = {\n',
        f'    [{RACE}] = {{glueString="{KEY}", name="Arakkoa", faction="Horde", fileString="{TOKEN}"}},\n')
    result['CharacterInfo.lua'] += (f'\nRaceInfoByFileString.{KEY} = {{Name="Arakkoa", '
        'Description="Winged people of Draenor\'s Skettis, outcast by their own kind and now sworn to the Horde."};\n')
    for sex in ('Male', 'Female'):
        insert('CharacterCreate.lua', 'RACE_ICON_TEXTURES = {\n',
            f'    ["{KEY}_{sex.upper()}"] = "Interface\\\\Glues\\\\CharacterCreate\\\\'
            f'UI-CharacterCreate-{TOKEN}{sex}",\n')
    insert('CharacterCreate.lua', 'local RACE_BACKGROUND_KEYS = {\n', f'        ["{KEY}"] = "ORC",\n')
    anchor = '        for i=6,29 do _G["CharacterCustomizationButtonFrame"..i]:Hide(); end'
    if result['CharacterCreate.lua'].count(anchor) != 1:
        raise ValueError('Stock customization refresh changed')
    result['CharacterCreate.lua'] = result['CharacterCreate.lua'].replace(anchor, anchor + f'''
        if CharacterCreate.selectedRaceID == {RACE} then
            _G["CharacterCustomizationButtonFrame5"]:Hide();
        end''', 1)
    insert('GlueParent.lua', '    local hordeRaces = {\n', f'        ["{KEY}"] = true,\n')
    result['GlueParent.lua'] += (f'\nCharModelFogInfo.{KEY}=CharModelFogInfo.ORC;\n'
        f'CharModelGlowInfo.{KEY}=CharModelGlowInfo.ORC;\n'
        f'GlueAmbienceTracks.{KEY}=GlueAmbienceTracks.ORC;\n')
    result['GlueStrings.lua'] += f'\n{KEY}="Arakkoa"; {KEY}_MALE={KEY}; {KEY}_FEMALE={KEY};\n'
    insert('ECS_Schema.lua', 'S.RaceOverride = {\n', f'    [{RACE}] = {{name="Arakkoa", faction=2, artKey="{TOKEN}"}},\n')
    insert('ECS_Schema.lua', 'S.RaceByModelKey = {\n',
        f'    {{"{KEY}", {{name="Arakkoa", faction=2, artKey="{TOKEN}"}}}},\n')
    insert('ECS_Schema.lua', 'S.PortraitArtKeys = {\n', f'    {TOKEN}=true,\n')
    from lupa.lua51 import LuaRuntime
    compile_chunk = LuaRuntime().eval('function(s) local f,e=loadstring(s); assert(f,e); end')
    for source in result.values():
        compile_chunk(source)
    return {n: source.encode() for n, source in result.items()}


def stage():
    if (p.CLIENT_DEFAULT / ASSET).exists():
        raise FileExistsError('Asset archive slot already exists')
    a = assets()
    files = p.ClientFiles(str(p.CLIENT_DEFAULT / 'Data'), 'enUS')
    try:
        baseline = {n: files.find(p.DBC_ROOT + n + '.dbc')[0] for n in TABLES}
        original = {n: files.find(p.GLUE_ROOT + n)[0] for n in s.GLUE}
        output, patched = tables(baseline), glue(original)
        skipped = output.pop('_skipped_emotes')
        output = {n: b for n, b in output.items() if b != baseline[n]}
        template = files.find(portraits.ICON_TEMPLATE_ENTRY)[0]
        ring = portraits.ring_layer(portraits.decode_client_blp(files.find(portraits.RING_ENTRY)[0]))
        icons = source_files()
    finally:
        files.close()
    for sex in ('Male', 'Female'):
        level = Blp.parse(icons['Interface\\Icons\\Race_Arakkoa_' + sex + '.blp']).decode_level(0)
        art = Image.frombytes('RGBA', (level.width, level.height), bytes(level.data))
        art = art.resize((64, 64), Image.Resampling.LANCZOS)
        art.putalpha(portraits.circular_mask())
        plain = portraits.encode_portrait(art, template)
        a[portraits.CREATOR_ICON_ROOT + 'UI-CharacterCreate-' + TOKEN + sex + '.blp'] = \
            portraits.encode_portrait(portraits.compose_race_icon(art, ring), template)
        key = portraits.CHARACTER_FRAME_ROOT + 'TemporaryPortrait-' + sex + '-' + TOKEN
        a[key] = a[key + '.blp'] = plain
        a['Interface\\Glues\\CharacterSelect\\ECS-Portrait-' + TOKEN + sex + '.blp'] = plain
    for key, blob in a.items():
        path = local(STAGE / 'assets', key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(blob)
    for folder, values in (('baseline', baseline), ('client-dbc', output), ('glue', patched)):
        for name, data in values.items():
            path = STAGE / folder / (name + '.dbc' if folder != 'glue' else name)
            if folder == 'baseline':
                pin(path, data)
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
    for name in SERVER_TABLES:
        base = (TARGET / 'modules/mod-custom-server/data/dbc/retroported-races' / (name + '.dbc')).read_bytes()
        pin(STAGE / 'baseline-server' / (name + '.dbc'), base)
        source, table = p.RawWdbc(output[name]), p.RawWdbc(base)
        if name == 'Spell':
            rows = [r for r in source.records if p._value(r, 0) in SPELLS]
        elif name in RANGES and isinstance(RANGES[name], dict):
            rows = [r for r in source.records if p._value(r, 0) in RANGES[name].values()]
        else:
            rows = p._table_rows_for_race(output[name], name, RACE)
        p._ensure_id_free(base, name, {p._value(r, 0) for r in rows})
        pool = bytearray(table.strings)
        string_fields = SPELL_STRINGS if name == 'Spell' else None
        added = []
        for row in rows:
            if string_fields:
                for field in string_fields:
                    offset = p._value(row, field * 4)
                    if offset:
                        row = p._replace(row, field * 4, 4,
                                         p._append_string(pool, p._string(source.strings, offset)))
                added.append(row)
            else:
                added.append(p._clone_strings(name, source, row, pool))
        pin(STAGE / 'server/dbc' / (name + '.dbc'), table.build(list(table.records) + added, bytes(pool)))
    sql = sql_text(RACIALS)
    pin(MIGRATION, sql.encode())
    pin(STAGE / 'arakkoa.sql', MIGRATION.read_bytes())
    storm = p.Storm(p.DLL_DEFAULT)
    target = STAGE / 'client' / ASSET
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name('arakkoa-assets-next.MPQ')
    if temporary.exists():
        raise FileExistsError(temporary)
    storm.create_archive(temporary, a)
    temporary.replace(target)
    replacements = {p.DBC_ROOT + n + '.dbc': b for n, b in output.items()}
    replacements.update({p.GLUE_ROOT + n: b for n, b in patched.items()})
    report = {'status': 'staged_build_and_deployment_required', 'race': RACE, 'client': str(p.CLIENT_DEFAULT),
        'exe_sha256': p.sha256(p.CLIENT_DEFAULT / 'Wow.exe'), 'archives': {str(ASSET): p.sha256(target)},
        'archive_baselines': {}, 'migration': str(MIGRATION), 'source': str(PACKAGE),
        'dependency_source': str(REFORGED_MPQ), 'skipped_emote_rows': skipped,
        'assets': {k: hashlib.sha256(v).hexdigest() for k, v in a.items()}, 'live_install_performed': False}
    for relative in (p.GLOBAL_ARCHIVE_REL, p.LOCALE_ARCHIVE_REL):
        live, snapshot, dest = p.CLIENT_DEFAULT / relative, STAGE / 'baseline-archives' / relative, \
            STAGE / 'client' / relative
        snapshot.parent.mkdir(parents=True, exist_ok=True)
        dest.parent.mkdir(parents=True, exist_ok=True)
        before = p.sha256(live)
        if not snapshot.exists():
            shutil.copy2(live, snapshot)
        if p.sha256(snapshot) != before:
            raise ValueError('Archive baseline changed: ' + str(relative))
        print('STAGING', relative, flush=True)
        o.rebuild_archive_replacing(storm, snapshot, dest, replacements, compress=True)
        if p.sha256(live) != before:
            raise ValueError('Live archive changed during staging')
        report['archive_baselines'][str(relative)] = before
        report['archives'][str(relative)] = p.sha256(dest)
    save(STAGE / 'report.json', report)
    print('STAGED HORDE ARAKKOA', STAGE, flush=True)


def check():
    report = p.load_json(STAGE / 'report.json')
    for relative, expected in report['archives'].items():
        assert p.sha256(STAGE / 'client' / relative) == expected
    for name in [n for n in TABLES if (STAGE / 'client-dbc' / (n + '.dbc')).exists()]:
        old = p.RawWdbc((STAGE / 'baseline' / (name + '.dbc')).read_bytes())
        new = p.RawWdbc((STAGE / 'client-dbc' / (name + '.dbc')).read_bytes())
        assert not (Counter(old.records) - Counter(new.records)), name + ' lost baseline rows'
        assert new.strings.startswith(old.strings), name + ' changed baseline strings'
        if name in ('ChrRaces', 'CharSections', 'BarberShopStyle', 'CharStartOutfit', 'NameGen', 'Spell',
                    'SoundEntries', 'CreatureSoundData', 'EmotesTextSound', 'CreatureModelData',
                    'CreatureDisplayInfo', 'CharHairGeosets'):
            ids = [p._value(r, 0) for r in new.records]
            assert len(ids) == len(set(ids)), name + ' has duplicate ids'
    m = manifest()
    races = p.RawWdbc((STAGE / 'client-dbc/ChrRaces.dbc').read_bytes())
    race = next(row for row in races.records if p._value(row, 0) == RACE)
    assert [p._value(race, field * 4) for field in (2, 4, 5, 7, 13)] == [2, 60066, 60067, 1, 1]
    assert p._string(races.strings, p._value(race, 44)).decode() == TOKEN
    assert sum(1 for row in races.records if p._string(races.strings, p._value(row, 44)).decode() == TOKEN) == 1
    pairs = p.RawWdbc((STAGE / 'client-dbc/CharBaseInfo.dbc').read_bytes())
    assert sorted(row[1] for row in pairs.records if row[0] == RACE) == CLASSES
    a = report['assets']
    asset_keys = {key.casefold() for key in a}
    for key, expected in a.items():
        blob = local(STAGE / 'assets', key).read_bytes()
        assert hashlib.sha256(blob).hexdigest() == expected, key
        if key.lower().endswith('.m2'):
            model = parse_m2(blob)
            assert model.version == 264
            for texture in model.textures:
                assert texture['type'] != 0 or not texture['filename'] \
                    or texture['filename'].casefold() in asset_keys, (key, texture)
            for lod in range(model.num_skin_profiles):
                skin = parse_skin(local(STAGE / 'assets', key[:-3] + f'{lod:02d}.skin').read_bytes())
                assert all(v < model.vertex_count for v in skin.vertices), key
                assert all(v < len(skin.vertices) for v in skin.indices), key
    for sex in ('Male', 'Female'):
        key = m['models'][sex.lower()]['model_path']
        source = parse_m2(source_files()['Character\\Arakkoa\\' + sex + '\\Arakkoa' + sex + '.m2'])
        staged = parse_m2(local(STAGE / 'assets', key).read_bytes())
        assert source.vertices == staged.vertices and source.sequences == staged.sequences
    sections = p.RawWdbc((STAGE / 'client-dbc/CharSections.dbc').read_bytes())
    mine = p._table_rows_for_race((STAGE / 'client-dbc/CharSections.dbc').read_bytes(), 'CharSections', RACE)
    for row in mine:
        for field in (4, 5, 6):
            key = p._string(sections.strings, p._value(row, field * 4)).decode()
            assert not key or key.casefold() in asset_keys, key
    shape = appearance()
    for gender, a_ in shape.items():
        rows = [r for r in mine if p._value(r, 8) == gender]
        counts = Counter(p._value(r, 12) for r in rows)
        assert counts[0] == a_['skins'] and counts[4] == a_['skins']
        assert counts[1] == a_['skins'] * a_['faces']
        assert counts[3] == a_['hair_styles'] * a_['hair_colors']
    hair = p.RawWdbc((STAGE / 'client-dbc/CharHairGeosets.dbc').read_bytes())
    for gender, a_ in shape.items():
        styles = {p._value(r, 12) for r in hair.records if p._value(r, 4) == RACE and p._value(r, 8) == gender}
        assert styles >= set(range(a_['hair_styles'])), ('Hair geoset gap', gender)
    spell_table = p.RawWdbc((STAGE / 'client-dbc/Spell.dbc').read_bytes())
    assert [p._value(r, 0) for r in spell_table.records if p._value(r, 0) in SPELLS] == list(SPELLS)
    server_spells = p.RawWdbc((STAGE / 'server/dbc/Spell.dbc').read_bytes())
    assert [p._value(r, 0) for r in server_spells.records if p._value(r, 0) in SPELLS] == list(SPELLS)
    storm = p.Storm(p.DLL_DEFAULT)
    for relative in (p.GLOBAL_ARCHIVE_REL, p.LOCALE_ARCHIVE_REL, ASSET):
        handle = storm.open_archive(STAGE / 'client' / relative)
        try:
            entries = a if relative == ASSET else {
                p.DBC_ROOT + n + '.dbc': p.sha256(STAGE / 'client-dbc' / (n + '.dbc'))
                for n in TABLES if (STAGE / 'client-dbc' / (n + '.dbc')).exists()}
            for key, expected in entries.items():
                assert hashlib.sha256(storm.read(handle, key)).hexdigest() == expected, key
            if relative != ASSET:
                source = storm.open_archive(STAGE / 'baseline-archives' / relative)
                try:
                    old = {n.casefold(): size for n, size, _, _ in storm.list_files(source)
                           if n.casefold() not in ('(listfile)', '(attributes)')}
                    new = {n.casefold(): size for n, size, _, _ in storm.list_files(handle)}
                    assert old.keys() <= new.keys(), str(relative) + ' lost archive entries'
                    changed = {k.casefold() for k in entries}
                    changed.update((p.GLUE_ROOT + n).casefold() for n in s.GLUE)
                    assert all(new[n] == size for n, size in old.items() if n not in changed)
                    for name in s.GLUE:
                        assert storm.read(handle, p.GLUE_ROOT + name) == (STAGE / 'glue' / name).read_bytes()
                finally:
                    storm.dll.SFileCloseArchive(source)
        finally:
            storm.dll.SFileCloseArchive(handle)
    save(STAGE / 'checks.json', {'passed': True, 'asset_count': len(a), 'race': RACE,
        'appearance': shape, 'scope': 'source closure, model/SKIN bounds, id uniqueness, preserved DBC rows, '
        'archive readback', 'live_client_checked': False})
    print('CHECKED Arakkoa assets, DBC preservation and three MPQs', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('config', 'stage', 'check'))
    args = parser.parse_args()
    {'config': config, 'stage': stage, 'check': check}[args.action]()
