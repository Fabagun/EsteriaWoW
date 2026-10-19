"""Stage the supplied SnowzoCraft Jinyu/Ankoan player pack as Alliance race 65."""

import argparse
from collections import Counter
import copy
import hashlib
import json
from pathlib import Path, PureWindowsPath
import shutil
import struct

from PIL import Image
from wotlkconv.m2 import parse_m2, parse_skin
from wotlkconv.blp import Blp
import retroported_race_pack as p
import ogre_furbolg_race_pack as o
import race_portrait_pack as portraits
import sethrak_race_pack as s

TARGET = Path('R:/Users/Zach/Documents/GitHub/EsteriaWoW')
SOURCE = Path('G:/Downloads/HDWoWModels/Jinyu_race_files')
DEPENDENCIES = Path('G:/RetroPorterWork/jinyu/dependencies')
STAGE = Path('G:/RetroPorterWork/jinyu/stage-20261008')
ASSET = Path('Data/Patch-5.MPQ')
RACE = 65
TOKEN = 'JinyuAlliance'
PREFIX = 'custom\\jinyu\\'
RANGES = {'CreatureModelData': {'male': 120071, 'female': 120072},
          'CreatureDisplayInfo': {'male': 60062, 'female': 60063},
          'CharSections': [1113300, 1114299], 'CharHairGeosets': [1113300, 1113399],
          'BarberShopStyle': [1113300, 1113499], 'CharStartOutfit': [22100, 22119],
          'NameGen': [81000, 83999]}
MIGRATION = TARGET / 'data/sql/updates/pending_db_world/rev_20261009020000000_jinyu_alliance.sql'


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


def allocation():
    result = p.load_json(TARGET / 'data/retroported-races/allocation.json')
    if any(RACE in ids for slug, ids in result['race_ids'].items() if slug != 'jinyu'):
        raise ValueError('Race 65 is occupied')
    for slug, tables in result['race_allocations'].items():
        if slug == 'jinyu':
            if tables != RANGES:
                raise ValueError('Jinyu allocation changed')
            continue
        for name, bounds in RANGES.items():
            other = tables.get(name)
            if isinstance(bounds, list) and isinstance(other, list):
                if max(bounds[0], other[0]) <= min(bounds[1], other[1]):
                    raise ValueError('Allocation overlap: ' + slug + '/' + name)
            elif isinstance(other, dict) and isinstance(bounds, dict):
                if set(bounds.values()) & set(other.values()):
                    raise ValueError('Model/display overlap: ' + slug)
    result['race_ids']['jinyu'] = [RACE]
    result['race_allocations']['jinyu'] = copy.deepcopy(RANGES)
    for name, bounds in RANGES.items():
        result['dbc_ranges'][name][1] = max(result['dbc_ranges'][name][1],
            bounds[1] if isinstance(bounds, list) else max(bounds.values()))
    return result


def manifest():
    profiles = {str(g): {'capacities': [n, 1, 1, n, 1],
        'options': [{'label': label, 'choices': list(range(count))}
                    for label, count in zip(('Skin Color', 'Face', 'Hair Style', 'Fin Color', 'Facial Hair'),
                                           (n, 1, 1, n, 1))]} for g, n in enumerate((7, 4))}
    return {'schema_version': 1, 'slug': 'jinyu', 'name': 'Jinyu', 'race_ids': [RACE],
        'enum': 'RACE_JINYU_ALLIANCE', 'faction': 'alliance', 'source_race_id': 1,
        'source_donor_race_id': 18, 'legacy_mask_race': 1, 'visual_base_race': 1,
        'client_file_strings': {str(RACE): TOKEN}, 'glue_token': TOKEN.upper(), 'helmet_prefix': 'Jn',
        'start_profile': 'elwynn', 'donor_totem_race': 1, 'classes': [1, 2, 3, 4, 5, 6, 7, 8, 9, 11],
        'source_patch_root': str(SOURCE), 'runtime_patch_root': str(STAGE / 'assets'),
        'models': {sex.lower(): {'model_id': RANGES['CreatureModelData'][sex.lower()],
            'display_id': RANGES['CreatureDisplayInfo'][sex.lower()],
            'model_path': PREFIX + 'Character\\Jinyu\\' + sex + '\\Jinyu' + sex + '.m2'}
            for sex in ('Male', 'Female')},
        'appearance': {'mode': 'native-stock-five-byte-v1', 'source': 'snowzocraft-player',
            'supported_genders': [0, 1], 'body_labels': ['River Jinyu', 'Ankoan'], 'profiles': profiles,
            'equipped_armor_geosets': 'authored-human-player', 'hide_helm': False,
            'constants': ['Face', 'Hair Style', 'Facial Hair']},
        'random_playerbot_enabled': False, 'custom_racial_spells': []}


def config():
    reserved = allocation()
    path = TARGET / 'modules/mod-custom-server/data/races/race_registry.json'
    registry = p.load_json(path)
    entry = {'id': RACE, 'species_key': 'jinyu_alliance', 'display_name': 'Jinyu', 'faction': 'alliance',
        'species_selection': False, 'start_profile': 'elwynn', 'asset_owner': 'snowzocraft_jinyu',
        'legacy_mask_race': 1, 'visual_base_race': 1, 'supported_genders': [0, 1]}
    old = next((r for r in registry['playable'] if r['id'] == RACE), None)
    if old is not None and old != entry:
        raise ValueError('Registry slot 65 has a different owner')
    if any(r['id'] == RACE for r in registry['npc_only']):
        raise ValueError('Race 65 is reserved for NPC use')
    if old is None:
        registry['playable'].append(entry)
    registry['sources']['snowzocraft_jinyu'] = str(STAGE / 'assets')
    save(TARGET / 'data/retroported-races/jinyu.json', manifest())
    save(TARGET / 'data/retroported-races/allocation.json', reserved)
    save(path, registry)
    print('RESERVED Alliance Jinyu race 65', flush=True)


def rebase_textures(blob):
    """Append private texture strings; keep geometry and external animation offsets unchanged."""
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


def motion():
    """Add the three missing player actions using the current HumanMale rig."""
    import creature_animation_repair as repair
    import sethrak_animation_pack as animation
    import vrykul_female_pack as arrays
    key = 'Character\\Jinyu\\Male\\JinyuMale.m2'
    model, hashes = animation.embedded_model(STAGE / 'motion/source', key,
        lambda name: local(SOURCE, name).read_bytes())
    original = copy.deepcopy(model)
    repair.ROOT = STAGE / 'motion/donor'
    donor, donor_receipt = repair.donor('jinyu', 0)
    actions = (69, 133, 134)
    existing = {seq['id'] for seq in model.sequences}
    added = [repair.retarget(model, donor, action) for action in actions if action not in existing]
    repair.e.rebuild_sequence_lookup(model)
    for seq in model.sequences[len(original.sequences):]:
        seq.update(bounds_min=model.bounding_box[:3], bounds_max=model.bounding_box[3:],
                   bounds_radius=model.bounding_sphere_radius)
    animation.tracks_equal(original, model, len(original.sequences))
    from wotlkconv.m2 import write_md20
    blob, metadata_changes = arrays.separate_bone_track_arrays(write_md20(model))
    parsed = parse_m2(blob)
    animation.ACTIONS = actions
    animation.check_model(parsed, blob)
    assert parsed.vertices == original.vertices
    (STAGE / 'motion/JinyuMale.m2').write_bytes(blob)
    save(STAGE / 'motion/report.json', {'source_hashes': hashes, 'donor': donor_receipt,
        'added': added, 'metadata_repairs': len(metadata_changes), 'source_sequences': len(original.sequences),
        'final_sequences': len(parsed.sequences), 'preserved_source_motion': True})
    print('ADDED', [(r['animation'], len(r['moving_matched_bones'])) for r in added], flush=True)


def assets():
    result, receipt = {}, {}
    policy = p.load_json(STAGE / 'helmet-policy.json')
    if any(row['target_items'] for row in policy):
        raise ValueError('An active helmet is missing authored textures')
    omitted = {row['model'].casefold() for row in policy}
    for path in sorted(SOURCE.rglob('*')):
        if not path.is_file() or path.suffix.lower() not in ('.m2', '.skin', '.anim', '.blp'):
            continue
        key = '\\'.join(path.relative_to(SOURCE).parts)
        data = path.read_bytes()
        receipt[key] = hashlib.sha256(data).hexdigest()
        model_key = key if path.suffix.lower() == '.m2' else key[:-7] + '.m2'
        if model_key.casefold() in omitted:
            continue
        target = key if key.lower().startswith('item\\') else PREFIX + key
        result[target] = rebase_textures(data) if path.suffix.lower() == '.m2' else data
    for path in (DEPENDENCIES / 'patch-root').rglob('*.blp'):
        result[PREFIX + '\\'.join(path.relative_to(DEPENDENCIES / 'patch-root').parts)] = path.read_bytes()
    for key in p.load_json(STAGE / 'helmet-dependencies.json')['found']:
        result[key] = local(STAGE / 'assets', key).read_bytes()
    male = STAGE / 'motion/JinyuMale.m2'
    if male.exists():
        result[manifest()['models']['male']['model_path']] = rebase_textures(male.read_bytes())
    save(STAGE / 'source-inventory.json', receipt)
    return result


def finish_assets():
    """Package resolved target helmets; retain foreign-server helmets in the immutable supplied source."""
    report = p.load_json(STAGE / 'report.json')
    a = assets()
    for key in report['assets']:
        if key.lower().startswith('interface\\'):
            a[key] = local(STAGE / 'assets', key).read_bytes()
    for key, data in a.items():
        path = local(STAGE / 'assets', key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    storm = p.Storm(p.DLL_DEFAULT)
    target = STAGE / 'client' / ASSET
    temporary = target.with_name('jinyu-resolved.MPQ')
    if temporary.exists():
        raise FileExistsError(temporary)
    storm.create_archive(temporary, a)
    temporary.replace(target)
    report['assets'] = {k: hashlib.sha256(v).hexdigest() for k, v in a.items()}
    report['archives'][str(ASSET)] = p.sha256(target)
    report['helmet_dependencies'] = p.load_json(STAGE / 'helmet-dependencies.json')
    report['unreferenced_donor_helmets'] = p.load_json(STAGE / 'helmet-policy.json')
    report['motion'] = p.load_json(STAGE / 'motion/report.json')
    save(STAGE / 'report.json', report)
    print('RESOLVED Jinyu assets', len(a), flush=True)


def tables(baseline):
    m, reserved, result = manifest(), allocation(), dict(baseline)
    p._ensure_id_free(result['ChrRaces'], 'ChrRaces', {RACE})
    result['ChrRaces'] = p._merge_chr_races(result['ChrRaces'], m, reserved)
    races = p.RawWdbc(result['ChrRaces'])
    pool, rows = bytearray(races.strings), []
    donor = next(r for r in races.records if p._value(r, 0) == 1)
    for row in races.records:
        if p._value(row, 0) == RACE:
            for field, value in ((1, 14), (2, 1), (7, 7), (12, 0), (13, 0), (68, 0)):
                row = p._replace(row, field * 4, 4, value)
            row = p._set_string(row, 6, pool, 'Jn')
        rows.append(row)
    result['ChrRaces'] = races.build(rows, bytes(pool))
    for gender, sex in enumerate(('male', 'female')):
        # Both authored bodies use HumanMale's player skeleton and component layout.
        displays = p.RawWdbc(baseline['CreatureDisplayInfo'])
        display = next(r for r in displays.records if p._value(r, 0) == p._value(donor, 16))
        models = p.RawWdbc(baseline['CreatureModelData'])
        model = next(r for r in models.records if p._value(r, 0) == p._value(display, 4))
        for name, row in (('CreatureModelData', model), ('CreatureDisplayInfo', display)):
            table = p.RawWdbc(result[name])
            pool = bytearray(table.strings)
            row = p._clone_strings(name, table, row, pool)
            row = p._replace(row, 0, 4, RANGES[name][sex])
            if name == 'CreatureModelData':
                row = p._set_string(row, 2, pool, m['models'][sex]['model_path'])
                row = p._replace(row, 4, 4, p._value(row, 4) | 0x804)
            else:
                row = p._replace(row, 4, 4, RANGES['CreatureModelData'][sex])
                for offset in (8, 12, 24, 28, 32, 36):
                    row = p._replace(row, offset, 4, 0)
                row = row[:16] + struct.pack('<f', 1.0) + row[20:]
            result[name] = s.append_rows(result[name], name, [row], pool)
    result['CharBaseInfo'] = p._build_char_base_info(result['CharBaseInfo'], m)
    table = p.RawWdbc(result['CharStartOutfit'])
    donors = {}
    for row in sorted(table.records, key=lambda r: p._value(r, 0)):
        if row[4] == 1 and row[5] in m['classes'] and row[6] < 2 and row[7] == 0:
            donors[bytes(row[5:8])] = row
    assert len(donors) == 20, 'Missing Alliance class/gender outfit'
    rows = [p._replace(p._replace(r, 0, 4, RANGES['CharStartOutfit'][0] + i), 4, 1, RACE)
            for i, r in enumerate(donors.values())]
    result['CharStartOutfit'] = s.append_rows(result['CharStartOutfit'], 'CharStartOutfit', rows)
    result['NameGen'] = p._clone_namegen(result['NameGen'], m, reserved)
    table = p.RawWdbc(result['CharSections'])
    pool, sections, hair, facial, barber = bytearray(table.strings), [], [], [], []
    for gender, sex in enumerate(('Male', 'Female')):
        count = m['appearance']['profiles'][str(gender)]['capacities'][0]
        stem = PREFIX + 'Character\\Jinyu\\' + sex + '\\Jinyu' + sex

        def section(kind, color, textures):
            row = struct.pack('<10I', RANGES['CharSections'][0] + len(sections), RACE, gender,
                              kind, 0, 0, 0, 1 if kind == 1 else 17, 0, color)
            for field, path in enumerate(textures, 4):
                row = p._set_string(row, field, pool, stem + path)
            sections.append(row)

        for color in range(count):
            section(0, color, [f'Skin00_{color:02d}.blp'])
            section(1, color, [f'FaceLower00_{color:02d}.blp', f'FaceUpper00_{color:02d}.blp'])
            section(3, color, [f'Hair00_{color:02d}.blp'])
            section(4, color, ['NakedPelvisSkin00_00.blp', 'NakedTorsoSkin00_00.blp'])
        hair.append(struct.pack('<6I', RANGES['CharHairGeosets'][0] + gender, RACE, gender, 0, 0, 1))
        facial.append(struct.pack('<8I', RACE, gender, 0, 0, 0, 0, 0, 0))
        source = p.RawWdbc(result['BarberShopStyle'])
        for kind, size in ((0, 1), (2, 1), (3, count)):
            donor_style = next(r for r in source.records if p._value(r, 4) == kind)
            for value in range(size):
                row = donor_style
                for offset, n in ((0, RANGES['BarberShopStyle'][0] + len(barber)),
                                  (148, RACE), (152, gender), (156, value)):
                    row = p._replace(row, offset, 4, n)
                barber.append(row)
    for name, rows, strings in (('CharSections', sections, pool), ('CharHairGeosets', hair, None),
            ('CharacterFacialHairStyles', facial, None), ('BarberShopStyle', barber, None)):
        result[name] = s.append_rows(result[name], name, rows, strings)
    result['CharSections'] = o.order_charsections_entry(p.DBC_ROOT + 'CharSections.dbc', result['CharSections'])
    return result


def glue(original):
    result = {n: b.decode('utf-8-sig') for n, b in original.items()}

    def insert(name, anchor, payload):
        result[name] = o._insert_once(result[name], anchor, payload, 'Jinyu ' + name)

    insert('CharacterInfo.lua', 'local EXACT_RACE_DATA = {\n',
        '    [65] = {glueString="JINYUALLIANCE", name="Jinyu", faction="Alliance", fileString="JinyuAlliance"},\n')
    result['CharacterInfo.lua'] += ('\nRaceInfoByFileString.JINYUALLIANCE = {Name="Jinyu", '
        'Description="River Jinyu and Ankoan adventurers allied with the Alliance."};\n')
    for sex in ('Male', 'Female'):
        insert('CharacterCreate.lua', 'RACE_ICON_TEXTURES = {\n',
            f'    ["JINYUALLIANCE_{sex.upper()}"] = "Interface\\\\Glues\\\\CharacterCreate\\\\'
            f'UI-CharacterCreate-JinyuAlliance{sex}",\n')
    insert('CharacterCreate.lua', 'local RACE_BACKGROUND_KEYS = {\n', '        ["JINYUALLIANCE"] = "HUMAN",\n')
    anchor = '        for i=6,29 do _G["CharacterCustomizationButtonFrame"..i]:Hide(); end'
    if result['CharacterCreate.lua'].count(anchor) != 1:
        raise ValueError('Stock customization refresh changed')
    result['CharacterCreate.lua'] = result['CharacterCreate.lua'].replace(anchor, anchor + '''
        if CharacterCreate.selectedRaceID == 65 then
            CharacterCustomizationButtonFrame4Text:SetText("Fin Color");
            for _, index in ipairs({2,3,5}) do
                _G["CharacterCustomizationButtonFrame"..index]:Hide();
            end
        end''', 1)
    insert('GlueParent.lua', '        ["THINHUMAN"] = true,\n', '        ["JINYUALLIANCE"] = true,\n')
    result['GlueParent.lua'] += ('\nCharModelFogInfo.JINYUALLIANCE=CharModelFogInfo.HUMAN;\n'
        'CharModelGlowInfo.JINYUALLIANCE=CharModelGlowInfo.HUMAN;\n'
        'GlueAmbienceTracks.JINYUALLIANCE=GlueAmbienceTracks.HUMAN;\n')
    result['GlueStrings.lua'] += ('\nJINYUALLIANCE="Jinyu"; JINYUALLIANCE_MALE=JINYUALLIANCE; '
        'JINYUALLIANCE_FEMALE=JINYUALLIANCE;\n')
    anchor = 'raceModel == "THINHUMAN"'
    if result['CharacterSelect.lua'].count(anchor) != 1:
        raise ValueError('Character Select background policy changed')
    result['CharacterSelect.lua'] = result['CharacterSelect.lua'].replace(anchor,
        anchor + ' or raceModel == "JINYUALLIANCE"', 1)
    insert('ECS_Schema.lua', 'S.RaceOverride = {\n', '    [65] = {name="Jinyu", faction=1, artKey="JinyuAlliance"},\n')
    insert('ECS_Schema.lua', 'S.RaceByModelKey = {\n',
        '    {"JINYUALLIANCE", {name="Jinyu", faction=1, artKey="JinyuAlliance"}},\n')
    insert('ECS_Schema.lua', 'S.PortraitArtKeys = {\n', '    JinyuAlliance=true,\n')
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
        baseline = {n: files.find(p.DBC_ROOT + n + '.dbc')[0] for n in s.TABLES}
        original = {n: files.find(p.GLUE_ROOT + n)[0] for n in s.GLUE}
        output, patched = tables(baseline), glue(original)
        template = files.find(portraits.ICON_TEMPLATE_ENTRY)[0]
        ring = portraits.ring_layer(portraits.decode_client_blp(files.find(portraits.RING_ENTRY)[0]))
        for sex in ('Male', 'Female'):
            data = (SOURCE / 'Interface/Custom_Glues/RACE_ICONS' / ('RaceIcon_Jinyu_' + sex + '.blp')).read_bytes()
            level = Blp.parse(data).decode_level(0)
            art = Image.frombytes('RGBA', (level.width, level.height), bytes(level.data))
            art = art.resize((64, 64), Image.Resampling.LANCZOS)
            art.putalpha(portraits.circular_mask())
            plain = portraits.encode_portrait(art, template)
            a[portraits.CREATOR_ICON_ROOT + 'UI-CharacterCreate-JinyuAlliance' + sex + '.blp'] = \
                portraits.encode_portrait(portraits.compose_race_icon(art, ring), template)
            key = portraits.CHARACTER_FRAME_ROOT + 'TemporaryPortrait-' + sex + '-' + TOKEN
            a[key] = a[key + '.blp'] = plain
            a['Interface\\Glues\\CharacterSelect\\ECS-Portrait-JinyuAlliance' + sex + '.blp'] = plain
    finally:
        files.close()
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
    for name in s.SERVER_TABLES:
        base = (TARGET / 'modules/mod-custom-server/data/dbc/retroported-races' / (name + '.dbc')).read_bytes()
        pin(STAGE / 'baseline-server' / (name + '.dbc'), base)
        source, table = p.RawWdbc(output[name]), p.RawWdbc(base)
        rows = ([r for r in source.records if p._value(r, 0) in RANGES[name].values()]
                if name in RANGES and isinstance(RANGES[name], dict)
                else p._table_rows_for_race(output[name], name, RACE))
        p._ensure_id_free(base, name, {p._value(r, 0) for r in rows})
        pool = bytearray(table.strings)
        data = table.build(list(table.records) + [p._clone_strings(name, source, r, pool) for r in rows], bytes(pool))
        pin(STAGE / 'server/dbc' / (name + '.dbc'), data)
    sql = o.build_sql({'name': 'Jinyu', 'race_id': RACE, 'faction': 'alliance',
        'donor_start_race': 1, 'donor_totem_race': 1}).replace('ogre_furbolg_race_pack.py', 'jinyu_race_pack.py')
    sql += o.CHRRACES_TEMPLATE.format(race=RACE, faction_template=1, male_display=60062, female_display=60063,
        prefix='Jn', base_language=7, file_string=TOKEN, alliance=0, name='Jinyu')
    pin(MIGRATION, (sql.rstrip() + '\n').encode())
    pin(STAGE / 'jinyu.sql', MIGRATION.read_bytes())
    storm = p.Storm(p.DLL_DEFAULT)
    target = STAGE / 'client' / ASSET
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name('jinyu-assets-next.MPQ')
    if temporary.exists():
        raise FileExistsError(temporary)
    storm.create_archive(temporary, a)
    temporary.replace(target)
    replacements = {p.DBC_ROOT + n + '.dbc': b for n, b in output.items()}
    replacements.update({p.GLUE_ROOT + n: b for n, b in patched.items()})
    report = {'status': 'staged_build_and_deployment_required', 'race': RACE, 'client': str(p.CLIENT_DEFAULT),
        'exe_sha256': p.sha256(p.CLIENT_DEFAULT / 'Wow.exe'), 'archives': {str(ASSET): p.sha256(target)},
        'archive_baselines': {}, 'migration': str(MIGRATION), 'source': str(SOURCE),
        'dependency_source': p.load_json(DEPENDENCIES / 'report.json'),
        'assets': {k: hashlib.sha256(v).hexdigest() for k, v in a.items()}, 'live_install_performed': False}
    for relative in (p.GLOBAL_ARCHIVE_REL, p.LOCALE_ARCHIVE_REL):
        live, snapshot, target = p.CLIENT_DEFAULT / relative, STAGE / 'baseline-archives' / relative, \
            STAGE / 'client' / relative
        snapshot.parent.mkdir(parents=True, exist_ok=True)
        target.parent.mkdir(parents=True, exist_ok=True)
        before = p.sha256(live)
        if not snapshot.exists():
            shutil.copy2(live, snapshot)
        if p.sha256(snapshot) != before:
            raise ValueError('Archive baseline changed: ' + str(relative))
        print('STAGING', relative, flush=True)
        o.rebuild_archive_replacing(storm, snapshot, target, replacements, compress=True)
        if p.sha256(live) != before:
            raise ValueError('Live archive changed during staging')
        report['archive_baselines'][str(relative)] = before
        report['archives'][str(relative)] = p.sha256(target)
    save(STAGE / 'report.json', report)
    print('STAGED ALLIANCE JINYU', STAGE, flush=True)


def check():
    report = p.load_json(STAGE / 'report.json')
    for relative, expected in report['archives'].items():
        assert p.sha256(STAGE / 'client' / relative) == expected
    for name in s.TABLES:
        old = p.RawWdbc((STAGE / 'baseline' / (name + '.dbc')).read_bytes())
        new = p.RawWdbc((STAGE / 'client-dbc' / (name + '.dbc')).read_bytes())
        assert not (Counter(old.records) - Counter(new.records)), name + ' lost baseline rows'
        assert new.strings.startswith(old.strings), name + ' changed baseline strings'
    races = p.RawWdbc((STAGE / 'client-dbc/ChrRaces.dbc').read_bytes())
    race = next(row for row in races.records if p._value(row, 0) == RACE)
    assert [p._value(race, field * 4) for field in (2, 4, 5, 7, 13)] == [1, 60062, 60063, 7, 0]
    pairs = p.RawWdbc((STAGE / 'client-dbc/CharBaseInfo.dbc').read_bytes())
    assert sorted(row[1] for row in pairs.records if row[0] == RACE) == manifest()['classes']
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
        source = SOURCE / 'Character/Jinyu' / sex / ('Jinyu' + sex + '.m2')
        key = manifest()['models'][sex.lower()]['model_path']
        original, staged = parse_m2(source.read_bytes()), parse_m2(local(STAGE / 'assets', key).read_bytes())
        assert original.vertices == staged.vertices
        if sex == 'Male':
            assert len(staged.sequences) == len(original.sequences) + 3
            assert {69, 133, 134} <= {q['id'] for q in staged.sequences}
        else:
            assert original.sequences == staged.sequences
        for sequence in staged.sequences:
            if not sequence['flags'] & (0x20 | 0x40):
                anim = key[:-3] + f"{sequence['id']:04d}-{sequence['variation_index']:02d}.anim"
                assert anim.casefold() in asset_keys, anim
    sections = p.RawWdbc((STAGE / 'client-dbc/CharSections.dbc').read_bytes())
    for row in p._table_rows_for_race((STAGE / 'client-dbc/CharSections.dbc').read_bytes(), 'CharSections', RACE):
        for field in (4, 5, 6):
            key = p._string(sections.strings, p._value(row, field * 4)).decode()
            assert not key or key.casefold() in asset_keys, key
    storm = p.Storm(p.DLL_DEFAULT)
    for relative in (p.GLOBAL_ARCHIVE_REL, p.LOCALE_ARCHIVE_REL, ASSET):
        handle = storm.open_archive(STAGE / 'client' / relative)
        try:
            entries = a if relative == ASSET else {
                p.DBC_ROOT + n + '.dbc': p.sha256(STAGE / 'client-dbc' / (n + '.dbc')) for n in s.TABLES}
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
        'scope': 'source closure, model/SKIN bounds, preserved DBC rows, archive readback',
        'live_client_checked': False})
    print('CHECKED Jinyu assets, DBC preservation and three MPQs', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('config', 'motion', 'stage', 'finish-assets', 'check'))
    args = parser.parse_args()
    {'config': config, 'motion': motion, 'stage': stage, 'finish-assets': finish_assets, 'check': check}[args.action]()
