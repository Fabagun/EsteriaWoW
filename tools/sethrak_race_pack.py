"""Stage Alliance Sethrak (62) from the checked animated assets and current Esteria merge base."""

import argparse
from collections import Counter
import copy
import json
from pathlib import Path
import struct

from PIL import Image
from luaparser import ast
from wotlkconv.m2 import parse_m2, parse_skin, write_md20
from wotlkconv.m2.skin import write_skin

import creature_race_pack as c
import ogre_furbolg_race_pack as o
import race_portrait_pack as portraits
import retroported_race_pack as p
import sethrak_animation_pack as animations
import skyborne_visual_pack as visual

STAGE = Path(r'C:\Users\Zach\.codex\tmp\sethrak-playable')
ASSET_ARCHIVE = Path('Data/Patch-J.MPQ')
RACE = 62
TOKEN = 'SethrakAlliance'
TABLES = ('ChrRaces', 'CreatureModelData', 'CreatureDisplayInfo', 'CharSections', 'CharHairGeosets',
          'CharacterFacialHairStyles', 'CharBaseInfo', 'CharStartOutfit', 'NameGen', 'BarberShopStyle')
GLUE = ('CharacterInfo.lua', 'CharacterCreate.lua', 'GlueStrings.lua', 'GlueParent.lua',
        'CharacterSelect.lua', 'ECS_Schema.lua', 'ECS_Integrate.lua')
SERVER_TABLES = ('ChrRaces', 'CharStartOutfit', 'CharSections', 'BarberShopStyle',
                 'CreatureDisplayInfo', 'CreatureModelData')
RANGES = {'CreatureModelData': {'male': 120066, 'female': 120067},
          'CreatureDisplayInfo': {'male': 60057, 'female': 60058},
          'CharSections': [1101000, 1101999], 'CharHairGeosets': [1101000, 1101099],
          'BarberShopStyle': [1101000, 1101199], 'CharStartOutfit': [22040, 22059], 'NameGen': [66000, 68999]}


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8', newline='\n')


def allocation():
    result = p.load_json(p.ALLOCATION_PATH)
    existing = result['race_ids'].get('sethrak')
    if existing is not None and existing != [RACE]:
        raise ValueError('Sethrak race allocation differs')
    if any(RACE in ids for slug, ids in result['race_ids'].items() if slug != 'sethrak'):
        raise ValueError('Race 62 is reserved by another pack')
    old = result['race_allocations'].get('sethrak')
    if old is not None and old != RANGES:
        raise ValueError('Sethrak DBC allocations differ')
    result['race_ids']['sethrak'] = [RACE]
    result['race_allocations']['sethrak'] = copy.deepcopy(RANGES)
    for name, bounds in RANGES.items():
        if isinstance(bounds, list):
            result['dbc_ranges'][name][1] = max(result['dbc_ranges'][name][1], bounds[1])
    result['dbc_ranges']['CreatureDisplayInfo'][1] = max(result['dbc_ranges']['CreatureDisplayInfo'][1], 60058)
    return result


def apply_config():
    manifest = p.load_manifest('sethrak')
    registry_path = p.ROOT / 'modules/mod-custom-server/data/races/race_registry.json'
    registry = p.load_json(registry_path)
    entry = {'id': RACE, 'species_key': 'sethrak_alliance', 'display_name': 'Sethrak', 'faction': 'alliance',
             'species_selection': False, 'start_profile': 'elwynn', 'asset_owner': 'animated_sethrak',
             'legacy_mask_race': 1, 'visual_base_race': 11, 'supported_genders': [0, 1]}
    old = next((r for r in registry['playable'] if r['id'] == RACE), None)
    if old is not None and old != entry:
        raise ValueError('Registry slot 62 belongs to another contract')
    if old is None:
        registry['playable'].append(entry)
    registry['sources']['animated_sethrak'] = manifest['runtime_patch_root']
    save(p.ALLOCATION_PATH, allocation())
    save(registry_path, registry)
    c.header()


def prepare_models(manifest):
    animations.check(animations.OUT)
    report = p.load_json(animations.OUT / 'report.json')
    entries = {key: animations.local(animations.OUT / 'patch-root', key).read_bytes()
               for key in report['entries'] if key.lower().endswith('.blp')}
    models, records = {}, []

    def record(gender, kind, target, value, selectors=(), path=''):
        choices = [i | v << 16 for i, v in selectors]
        assert len(choices) <= 3 and len(path.encode()) < 128
        records.append(struct.pack('<7I', gender, kind, target, value,
                       *(choices + [0xffffffff] * (3 - len(choices)))) + path.encode().ljust(128, b'\0'))

    for gender, sex in enumerate(('male', 'female')):
        source = report['models'][sex]['path']
        blob = animations.local(animations.OUT / 'patch-root', source).read_bytes()
        model = parse_m2(blob)
        skin = parse_skin(animations.local(animations.OUT / 'patch-root', source[:-3] + '00.skin').read_bytes())
        original_triangles = [(visual.u16(mesh, 0), tuple(skin.vertices[skin.indices[i]] for i in range(at, at + 3)))
                              for mesh in skin.submeshes
                              for start in [visual.u16(mesh, 8) | visual.u16(mesh, 2) << 16]
                              for at in range(start, start + visual.u16(mesh, 10), 3)]
        compact = visual.compact_bone_palettes(model, skin)
        compact_triangles = [(visual.u16(mesh, 0), tuple(compact.vertices[compact.indices[i]]
                              for i in range(at, at + 3))) for mesh in compact.submeshes
                             for start in [visual.u16(mesh, 8) | visual.u16(mesh, 2) << 16]
                             for at in range(start, start + visual.u16(mesh, 10), 3)]
        assert compact_triangles == original_triangles
        model.num_skin_profiles = 1
        model.replacable_texture_lookup = [65535] * 16
        for index, texture in enumerate(model.textures):
            if texture['type']:
                model.replacable_texture_lookup[texture['type']] = index
        target = manifest['models'][sex]['model_path']
        entries[target], entries[target[:-3] + '00.skin'] = write_md20(model), write_skin(compact)
        rebuilt = parse_m2(entries[target])
        animations.check_model(rebuilt, entries[target])
        assert rebuilt.vertices == parse_m2(blob).vertices
        animations.tracks_equal(parse_m2(blob), rebuilt, len(rebuilt.sequences))
        models[sex] = {'path': target, 'source_sha256': animations.digest(blob),
                       'vertices': rebuilt.vertex_count, 'sequences': len(rebuilt.sequences),
                       'triangles': len(compact.indices) // 3,
                       'maximum_palette': max(visual.u16(r, 12) for r in compact.submeshes)}
        if gender == 0:
            texture_root = animations.PREFIX + 'textures\\creature\\sethrak_melee\\'
            for choice, name in enumerate(manifest['appearance']['skin_textures']):
                record(gender, 1, 11, 0, [(0, choice)], texture_root + name + '.blp')
            for choice, name in enumerate(manifest['appearance']['armor_textures']):
                record(gender, 1, 12, 0, [(3, choice)], texture_root + name + '.blp')
            for choice, geoset in enumerate(manifest['appearance']['male_armor_geosets']):
                record(gender, 0, 1, geoset, [(2, choice)])
            for group in (2, 3, 4):
                record(gender, 0, group, group * 100 + 1)
        else:
            record(gender, 0, 1, manifest['appearance']['female_armor_geoset'])
    (STAGE / 'EsteriaSethrak.bin').write_bytes(struct.pack('<3I', 0x314D4845, 1, len(records)) + b''.join(records))
    (STAGE / 'EsteriaSethrakTextures.bin').write_bytes(struct.pack('<4I', 0x31544845, 1, 0, 0))
    return entries, models


def append_rows(data, name, rows, pool=None):
    table = p.RawWdbc(data)
    if name != 'CharacterFacialHairStyles':
        p._ensure_id_free(data, name, {p._value(row, 0) for row in rows})
    return table.build(list(table.records) + rows, table.strings if pool is None else bytes(pool))


def tables(baseline, manifest, reserved):
    result = dict(baseline)
    race_table = p.RawWdbc(baseline['ChrRaces'])
    if any(p._value(row, 0) == RACE for row in race_table.records):
        raise ValueError('Live race 62 already exists; audit it before replacing any data')
    result['ChrRaces'] = p._merge_chr_races(result['ChrRaces'], manifest, reserved)
    table = p.RawWdbc(result['ChrRaces'])
    pool, rows = bytearray(table.strings), []
    for row in table.records:
        if p._value(row, 0) == RACE:
            for field, value in ((1, 14), (2, 1), (7, 7), (12, 0), (13, 0), (68, 0)):
                row = p._replace(row, field * 4, 4, value)
            row = p._set_string(row, 6, pool, manifest['helmet_prefix'])
        rows.append(row)
    result['ChrRaces'] = table.build(rows, bytes(pool))
    for name in ('CreatureModelData', 'CreatureDisplayInfo'):
        p._ensure_id_free(result[name], name, set(RANGES[name].values()))
        result[name] = p._merge_model_table(name, result[name], manifest, reserved)
    table = p.RawWdbc(result['CreatureDisplayInfo'])
    result['CreatureDisplayInfo'] = table.build([
        p._replace(row, 12, 4, 0) if p._value(row, 0) in RANGES['CreatureDisplayInfo'].values() else row
        for row in table.records])
    result['CharBaseInfo'] = p._build_char_base_info(result['CharBaseInfo'], manifest)
    outfits = p.RawWdbc(result['CharStartOutfit'])
    # The live table also carries older Human outfits. Keep the latest row for each Hero chassis/gender.
    donors = {}
    for row in sorted(outfits.records, key=lambda r: p._value(r, 0)):
        if row[4] == 1 and row[5] in manifest['classes'] and row[6] < 2 and row[7] == 0:
            donors[bytes(row[5:8])] = row
    assert len(donors) == 20
    rows = [p._replace(p._replace(row, 0, 4, RANGES['CharStartOutfit'][0] + index), 4, 1, RACE)
            for index, row in enumerate(donors.values())]
    result['CharStartOutfit'] = append_rows(result['CharStartOutfit'], 'CharStartOutfit', rows)
    result['NameGen'] = p._clone_namegen(result['NameGen'], manifest, reserved)
    section_table = p.RawWdbc(result['CharSections'])
    pool = bytearray(section_table.strings)
    sections, hair, facial, barber = [], [], [], []
    barber_table = p.RawWdbc(result['BarberShopStyle'])
    for gender, profile in manifest['appearance']['profiles'].items():
        gender = int(gender)
        counts = profile['capacities']
        body = animations.PREFIX + ('textures\\creature\\sethrak_melee\\sethrak_black.blp' if gender == 0
                                    else 'textures\\creature\\snakeloa\\snakeloa_1_body_blue.blp')

        def section(kind, style, color):
            row = struct.pack('<10I', RANGES['CharSections'][0] + len(sections), RACE, gender, kind,
                              0, 0, 0, 1 if kind == 1 else 17, style, color)
            if kind == 0:
                row = p._set_string(row, 4, pool, body)
            sections.append(row)

        for color in range(counts[0]):
            for kind in (0, 1, 4):
                section(kind, 0, color)
        for style in range(counts[2]):
            for color in range(counts[3]):
                section(3, style, color)
            hair.append(struct.pack('<6I', RANGES['CharHairGeosets'][0] + len(hair), RACE, gender, style, 0, 1))
        for color in range(counts[3]):
            section(2, 0, color)
        facial.append(struct.pack('<8I', RACE, gender, 0, 0, 0, 0, 0, 0))
        for kind, field in ((0, 2), (2, 4), (3, 0)):
            donor = next(row for row in barber_table.records if p._value(row, 4) == kind)
            for value in range(counts[field]):
                row = donor
                for offset, n in ((0, RANGES['BarberShopStyle'][0] + len(barber)),
                                  (148, RACE), (152, gender), (156, value)):
                    row = p._replace(row, offset, 4, n)
                barber.append(row)
    for name, rows, strings in (('CharSections', sections, pool), ('CharHairGeosets', hair, None),
                               ('CharacterFacialHairStyles', facial, None), ('BarberShopStyle', barber, None)):
        result[name] = append_rows(result[name], name, rows, strings)
    result['CharSections'] = o.order_charsections_entry(p.DBC_ROOT + 'CharSections.dbc', result['CharSections'])
    return result


def glue(original):
    result = {name: data.decode('utf-8-sig') for name, data in original.items()}

    def insert(name, anchor, payload):
        result[name] = o._insert_once(result[name], anchor, payload, 'Sethrak ' + name)

    insert('CharacterInfo.lua', 'local EXACT_RACE_DATA = {\n',
           '    [62] = { glueString="SETHRAKALLIANCE", name="Sethrak", faction="Alliance", '
           'fileString="SethrakAlliance" },\n')
    result['CharacterInfo.lua'] += ('\nRaceInfoByFileString.SETHRAKALLIANCE = {Name="Sethrak", '
        'Description="These serpentine adventurers have joined the Alliance."};\n')
    insert('CharacterCreate.lua', 'RACE_ICON_TEXTURES = {\n',
           '    ["SETHRAKALLIANCE_MALE"] = "Interface\\\\Glues\\\\CharacterCreate\\\\'
           'UI-CharacterCreate-SethrakAllianceMale",\n'
           '    ["SETHRAKALLIANCE_FEMALE"] = "Interface\\\\Glues\\\\CharacterCreate\\\\'
           'UI-CharacterCreate-SethrakAllianceFemale",\n')
    insert('CharacterCreate.lua', 'local RACE_BACKGROUND_KEYS = {\n',
           '        ["SETHRAKALLIANCE"] = "HUMAN",\n')
    marker = 'CharacterCreate.selectedRaceID == 54'
    result['CharacterCreate.lua'] = result['CharacterCreate.lua'].replace(marker,
        '(' + marker + ' or CharacterCreate.selectedRaceID == 62)')
    anchor = 'then CycleCharCustomization("EA_RANDOM",1);'
    assert result['CharacterCreate.lua'].count(anchor) == 1
    result['CharacterCreate.lua'] = result['CharacterCreate.lua'].replace(anchor,
        'or CharacterCreate.selectedRaceID == 62 ' + anchor, 1)
    anchor = 'if CharacterCustomizationButtonFrame1:IsShown() then frame:Show(); else frame:Hide(); end'
    assert result['CharacterCreate.lua'].count(anchor) == 1
    result['CharacterCreate.lua'] = result['CharacterCreate.lua'].replace(anchor,
        'if CharCreateOkayButton:IsShown() then frame:Show(); else frame:Hide(); end', 1)
    result['GlueStrings.lua'] += '\nSETHRAKALLIANCE="Sethrak"; SETHRAKALLIANCE_MALE=SETHRAKALLIANCE; '
    result['GlueStrings.lua'] += 'SETHRAKALLIANCE_FEMALE=SETHRAKALLIANCE;\n'
    insert('GlueParent.lua', '        ["THINHUMAN"] = true,\n', '        ["SETHRAKALLIANCE"] = true,\n')
    result['GlueParent.lua'] += ('\nCharModelFogInfo.SETHRAKALLIANCE=CharModelFogInfo.HUMAN;\n'
        'CharModelGlowInfo.SETHRAKALLIANCE=CharModelGlowInfo.HUMAN;\n'
        'GlueAmbienceTracks.SETHRAKALLIANCE=GlueAmbienceTracks.HUMAN;\n')
    anchor = 'raceModel == "THINHUMAN"'
    assert result['CharacterSelect.lua'].count(anchor) == 1
    result['CharacterSelect.lua'] = result['CharacterSelect.lua'].replace(anchor,
        anchor + ' or raceModel == "SETHRAKALLIANCE"', 1)
    insert('ECS_Schema.lua', 'S.RaceOverride = {\n',
           '    [62] = {name="Sethrak", faction=1, artKey="SethrakAlliance"},\n')
    insert('ECS_Schema.lua', 'S.RaceByModelKey = {\n',
           '    { "SETHRAKALLIANCE", { name = "Sethrak", faction = 1, artKey = "SethrakAlliance" } },\n')
    insert('ECS_Schema.lua', 'S.PortraitArtKeys = {\n', '    SethrakAlliance=true,\n')
    anchor = '(race >= 54 and race <= 59)'
    assert result['ECS_Integrate.lua'].count(anchor) == 1
    result['ECS_Integrate.lua'] = result['ECS_Integrate.lua'].replace(anchor, '(' + anchor + ' or race == 62)', 1)
    for text in result.values():
        ast.parse(text)
    return {name: text.encode() for name, text in result.items()}


def make_portraits(read):
    source = p.ROOT / 'NewModels/_Race/sethrak for draenei male and female/character icon'
    source /= 'for normal character/UI-CharacterCreate-Races.blp'
    atlas = portraits.decode_client_blp(source.read_bytes())
    assert atlas.size == (512, 256)
    template = read(portraits.ICON_TEMPLATE_ENTRY)
    ring = portraits.ring_layer(portraits.decode_client_blp(read(portraits.RING_ENTRY)))
    result = {}
    for sex, y in (('Male', 0), ('Female', 128)):
        art = atlas.crop((258, y + 2, 318, y + 62)).resize((64, 64), Image.Resampling.LANCZOS)
        art.putalpha(portraits.circular_mask())
        art.save(STAGE / ('portrait-' + sex.lower() + '.png'))
        plain = portraits.encode_portrait(art, template)
        icon = portraits.encode_portrait(portraits.compose_race_icon(art, ring), template)
        result[portraits.CREATOR_ICON_ROOT + 'UI-CharacterCreate-' + TOKEN + sex + '.blp'] = icon
        stem = portraits.CHARACTER_FRAME_ROOT + 'TemporaryPortrait-' + sex + '-' + TOKEN
        result[stem] = result[stem + '.blp'] = plain
        result['Interface\\Glues\\CharacterSelect\\ECS-Portrait-' + TOKEN + sex + '.blp'] = plain
    return result


def sql(manifest):
    entry = {'name': 'Sethrak', 'race_id': RACE, 'faction': 'alliance',
             'donor_start_race': 1, 'donor_totem_race': 11}
    text = o.build_sql(entry).replace('tools/ogre_furbolg_race_pack.py', 'tools/sethrak_race_pack.py')
    text += o.CHRRACES_TEMPLATE.format(race=RACE, faction_template=1, male_display=60057,
        female_display=60058, prefix=manifest['helmet_prefix'], base_language=7,
        file_string=TOKEN, alliance=0, name='Sethrak')
    return text.rstrip() + '\n'


def geometry_catalog(original, assets, manifest):
    magic, version, count = struct.unpack_from('<3I', original)
    assert (magic, version) == (0x4D474145, 1)
    offset, names = 12, set()
    for _ in range(count):
        names.add(original[offset:offset + 128].split(b'\0')[0].decode().lower())
        size = struct.unpack_from('<I', original, offset + 128)[0]
        offset += 132 + size
    assert offset == len(original)
    additions = []
    for model in manifest['models'].values():
        key = model['model_path']
        assert key.lower() not in names
        skin = assets[key[:-3] + '00.skin']
        additions.append(key.encode().ljust(128, b'\0') + struct.pack('<I', len(skin)) + skin)
    return struct.pack('<3I', magic, version, count + 2) + original[12:] + b''.join(additions)


def server_merge(client_tables):
    """Append only the new race's rows to each actual mounted server merge base."""
    output, hashes = {}, {}
    for name in SERVER_TABLES:
        source = p.RawWdbc(client_tables[name])
        base = (p.SERVER_DBC_ROOT / (name + '.dbc')).read_bytes()
        table = p.RawWdbc(base)
        assert (source.fields, source.record_size) == (table.fields, table.record_size)
        if name in ('CreatureModelData', 'CreatureDisplayInfo'):
            rows = [r for r in source.records if p._value(r, 0) in RANGES[name].values()]
        else:
            rows = p._table_rows_for_race(client_tables[name], name, RACE)
        assert rows
        p._ensure_id_free(base, name, {p._value(r, 0) for r in rows})
        pool = bytearray(table.strings)
        additions = [p._clone_strings(name, source, row, pool) for row in rows]
        output[name] = table.build(list(table.records) + additions, bytes(pool))
        hashes[name] = animations.digest(base)
        path = STAGE / 'baseline-server' / (name + '.dbc')
        path.parent.mkdir(parents=True, exist_ok=True)
        c.immutable(path, base)
    return output, hashes


def refresh_server_stage():
    client_path = STAGE / 'client-dbc'
    client_path.mkdir(exist_ok=True)
    for name in TABLES:
        target = client_path / (name + '.dbc')
        if not target.exists():
            target.write_bytes((STAGE / 'server/dbc' / (name + '.dbc')).read_bytes())
    client_tables = {n: (client_path / (n + '.dbc')).read_bytes() for n in TABLES}
    output, hashes = server_merge(client_tables)
    for name, data in output.items():
        (STAGE / 'server/dbc' / (name + '.dbc')).write_bytes(data)
    report = p.load_json(STAGE / 'report.json')
    report['server_baseline_hashes'] = hashes
    save(STAGE / 'report.json', report)
    validate()


def stage(client):
    manifest, reserved = p.load_manifest('sethrak'), allocation()
    STAGE.mkdir(parents=True, exist_ok=True)
    if (client / ASSET_ARCHIVE).exists():
        raise FileExistsError('Asset archive slot is in use: ' + str(client / ASSET_ARCHIVE))
    files = p.ClientFiles(str(client / 'Data'), 'enUS')
    try:
        read = lambda key: files.find(key)[0]
        baseline = {name: read(p.DBC_ROOT + name + '.dbc') for name in TABLES}
        original_glue = {name: read(p.GLUE_ROOT + name) for name in GLUE}
        for name, data in {**{n + '.dbc': b for n, b in baseline.items()}, **original_glue}.items():
            path = STAGE / 'baseline' / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        output = tables(baseline, manifest, reserved)
        patched = glue(original_glue)
        assets, models = prepare_models(manifest)
        assets.update(make_portraits(read))
    finally:
        files.close()
    for key, data in assets.items():
        path = animations.local(STAGE / 'assets', key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    original_geometry = (client / 'EsteriaAppearanceGeometry.bin').read_bytes()
    (STAGE / 'EsteriaAppearanceGeometry.bin').write_bytes(geometry_catalog(original_geometry, assets, manifest))
    (STAGE / 'baseline/EsteriaAppearanceGeometry.bin').write_bytes(original_geometry)
    server = STAGE / 'server/dbc'
    server.mkdir(parents=True, exist_ok=True)
    client_tables_path = STAGE / 'client-dbc'
    client_tables_path.mkdir(parents=True, exist_ok=True)
    for name, data in output.items():
        (client_tables_path / (name + '.dbc')).write_bytes(data)
    server_output, server_hashes = server_merge(output)
    for name, data in server_output.items():
        (server / (name + '.dbc')).write_bytes(data)
    for name, data in patched.items():
        path = STAGE / 'glue' / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    migration = STAGE / 'sethrak.sql'
    migration.write_text(sql(manifest), encoding='utf-8', newline='\n')
    report = {'status': 'data_staged_native_build_required', 'client': str(client), 'race': RACE,
              'models': models, 'assets': {k: animations.digest(v) for k, v in assets.items()},
              'baseline_hashes': {n: animations.digest(b) for n, b in baseline.items()},
              'geometry_before_sha256': animations.digest(original_geometry),
              'server_baseline_hashes': server_hashes,
              'archives': {}, 'live_install_performed': False}
    storm = p.Storm(p.DLL_DEFAULT)
    asset_path = STAGE / 'client' / ASSET_ARCHIVE
    asset_path.parent.mkdir(parents=True, exist_ok=True)
    if asset_path.exists():
        raise FileExistsError('Checked staging archive already exists; use a new stage or validate it')
    storm.create_archive(asset_path, assets)
    report['archives'][str(ASSET_ARCHIVE)] = p.sha256(asset_path)
    replacements = {p.DBC_ROOT + n + '.dbc': b for n, b in output.items()}
    replacements.update({p.GLUE_ROOT + n: b for n, b in patched.items()})
    for relative in (p.GLOBAL_ARCHIVE_REL, p.LOCALE_ARCHIVE_REL):
        live, target = client / relative, STAGE / 'client' / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        before = p.sha256(live)
        print('STAGING ARCHIVE', relative, flush=True)
        o.rebuild_archive_replacing(storm, live, target, replacements, compress=True)
        assert target.stat().st_size < 0x80000000
        assert p.sha256(live) == before
        report.setdefault('archive_baselines', {})[str(relative)] = before
        report['archives'][str(relative)] = p.sha256(target)
    save(STAGE / 'report.json', report)
    validate()


def validate():
    manifest = p.load_manifest('sethrak')
    report = p.load_json(STAGE / 'report.json')
    storm = p.Storm(p.DLL_DEFAULT)
    for relative, expected in report['archives'].items():
        path = STAGE / 'client' / relative
        assert p.sha256(path) == expected
        handle = storm.open_archive(path)
        try:
            if relative == str(ASSET_ARCHIVE):
                for key, sha in report['assets'].items():
                    assert animations.digest(storm.read(handle, key)) == sha
            else:
                for name in TABLES:
                    assert storm.read(handle, p.DBC_ROOT + name + '.dbc') == (STAGE / 'client-dbc' /
                                                                           (name + '.dbc')).read_bytes(), name
                for name in GLUE:
                    assert storm.read(handle, p.GLUE_ROOT + name) == (STAGE / 'glue' / name).read_bytes()
        finally:
            storm.dll.SFileCloseArchive(handle)
    for name in TABLES:
        before = p.RawWdbc((STAGE / 'baseline' / (name + '.dbc')).read_bytes())
        after = p.RawWdbc((STAGE / 'client-dbc' / (name + '.dbc')).read_bytes())
        if name == 'CharSections':
            # StormLib applies the established character-section priority order; retain every original row.
            assert not Counter(before.records) - Counter(after.records)
        else:
            assert after.records[:before.count] == before.records
        assert after.strings.startswith(before.strings)
        assert after.count > before.count
    for name in SERVER_TABLES:
        before = p.RawWdbc((STAGE / 'baseline-server' / (name + '.dbc')).read_bytes())
        after = p.RawWdbc((STAGE / 'server/dbc' / (name + '.dbc')).read_bytes())
        assert after.records[:before.count] == before.records
        assert after.strings.startswith(before.strings)
    for sex, info in report['models'].items():
        key = manifest['models'][sex]['model_path']
        data = animations.local(STAGE / 'assets', key).read_bytes()
        model = parse_m2(data)
        skin = parse_skin(animations.local(STAGE / 'assets', key[:-3] + '00.skin').read_bytes())
        animations.check_model(model, data)
        assert model.num_skin_profiles == 1 and skin.bone_count_max == 75
        assert all(visual.u16(r, 12) <= 75 for r in skin.submeshes)
        assert len(model.sequences) == 134
        for texture in model.textures:
            if texture['type'] == 0 and texture['filename']:
                assert animations.local(STAGE / 'assets', texture['filename']).exists()
    print('PASS Alliance Sethrak: assets, animations, native palettes and additive DBC/Glue archive round-trips',
          flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('config', 'stage', 'server', 'validate'))
    parser.add_argument('--client', type=Path, default=p.CLIENT_DEFAULT)
    args = parser.parse_args()
    if args.action == 'config':
        apply_config()
    elif args.action == 'stage':
        stage(args.client)
    elif args.action == 'server':
        refresh_server_stage()
    else:
        validate()
