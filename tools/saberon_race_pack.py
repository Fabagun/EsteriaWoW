"""Stage Horde Saberon64; live installation and compilation are separate actions."""

import argparse
import copy
import hashlib
import json
import os
from pathlib import Path, PureWindowsPath
import struct
import uuid
from dataclasses import asdict

from PIL import Image
from retroporter.discovery import rows_by_id
from retroporter.wotlk import load_db2
from wotlkconv.casc.config import BuildInfo
from wotlkconv.blp import convert_blp
from wotlkconv.m2 import convert_m2, parse_m2, parse_skin, write_md20
from wotlkconv.m2.skin import write_skin
from wotlkconv.options import Options
from wotlkconv.resolve import AssetSource

import creature_race_pack as c
import retroported_race_pack as p
import skyborne_visual_pack as visual

ROOT = c.WORK / 'saberon'
CACHE = c.PROJECT / 'sources/retail/races/saberon'
STAGE = Path('C:/Users/Zach/.codex/tmp/saberon-playable')
RACE = 64
TOKEN = 'SaberonHorde'
PREFIX = 'custom\\saberon\\native\\'
MODEL = PREFIX + 'saberon.m2'
MODEL_FID = 982557
BODY_IDS = (982811, 982810, 982813, 982812)
OUTFIT_IDS = ((999926, 999927), (999928, 999929), (999930, 999931))
REFERENCES = (83076, 83077, 83080, 83074, 83081, 83082, 83084, 83083, 83075, 83086, 83085, 83055)
ASSET_ARCHIVE = Path('Data/Patch-8.MPQ')
MIGRATION = p.ROOT / 'data/sql/updates/pending_db_world/rev_20261007230000000.sql'
LABELS = ('Fur Color', 'Outfit Style', 'Armor Color', 'Cloth Color', 'Facial Features')
CHOICES = (BODY_IDS, tuple(range(100, 110)), tuple(p[0] for p in OUTFIT_IDS),
           tuple(p[1] for p in OUTFIT_IDS), (0,))
RANGES = {'CreatureModelData': {'male': 120070}, 'CreatureDisplayInfo': {'male': 60061, 'female': 0},
          'CharSections': [1112300, 1113299], 'CharHairGeosets': [1112300, 1112399],
          'BarberShopStyle': [1112300, 1112499], 'CharStartOutfit': [22090, 22099], 'NameGen': [78000, 80999]}
save = c.save
local = p._patch_root_path


def acquire():
    pin = asdict(BuildInfo.load(c.DEFAULT.retail_root, c.DEFAULT.product))
    source = c.Source(p.load_json(CACHE / 'source-pin.json') if (CACHE / 'source-pin.json').exists() else pin)
    try:
        c.immutable(CACHE / 'source-pin.json', (json.dumps(source.pin, indent=2) + '\n').encode())
        for name in ('creature', 'creaturedisplayinfo', 'creaturemodeldata', 'creaturedisplayinfogeosetdata'):
            source.read(source.listfile.id_for('dbfilesclient/' + name + '.db2'),
                        ROOT / 'retail-db2/dbfilesclient' / (name + '.db2'), True)
        creatures = rows_by_id(load_db2(c.DEFAULT, 'saberon', 'Creature'), set(REFERENCES))
        if {r['ID'] for r in creatures} != set(REFERENCES):
            raise ValueError('A requested Retail creature is absent')
        displays = rows_by_id(load_db2(c.DEFAULT, 'saberon', 'CreatureDisplayInfo'),
                             {i for r in creatures for i in r['DisplayID'] if i})
        models = rows_by_id(load_db2(c.DEFAULT, 'saberon', 'CreatureModelData'),
                           {r['ModelID'] for r in displays})
        if {r['FileDataID'] for r in models} != {MODEL_FID}:
            raise ValueError('Requested creatures do not all resolve to the expected Saberon model')
        geosets = [dict(_row_id=i, **r) for i, r in load_db2(c.DEFAULT, 'saberon',
                   'CreatureDisplayInfoGeosetData') if r['CreatureDisplayInfoID'] in {d['ID'] for d in displays}]
        save(ROOT / 'reports/references.json', {'creatures': creatures, 'displays': displays,
                                               'models': models, 'display_geosets': geosets})
        queue = [(MODEL_FID, 'model'), *[(i, 'body') for i in BODY_IDS],
                 *[(i, 'outfit') for pair in OUTFIT_IDS for i in pair]]
        assets = {}
        while queue:
            fid, role = queue.pop(0)
            if str(fid) in assets:
                continue
            name = source.listfile.path_for(fid)
            path = CACHE / 'raw' / (str(fid) + (PureWindowsPath(name).suffix if name else '.bin'))
            data = source.read(fid, path)
            assets[str(fid)] = {'file_data_id': fid, 'logical_name': name, 'path': str(path), 'role': role,
                                'sha256': hashlib.sha256(data).hexdigest(),
                                'content_key': source.storage.root.ckey_for(fid).hex(),
                                'dependencies': c.references(data)}
            queue.extend(assets[str(fid)]['dependencies'])
        save(CACHE / 'inventory.json', {'pin': source.pin, 'assets': assets})
        print('PINNED SABERON', len(assets), 'files', source.pin['version'], flush=True)
    finally:
        source.close()


def raw(fid):
    row = p.load_json(CACHE / 'inventory.json')['assets'][str(fid)]
    data = Path(row['path']).read_bytes()
    if hashlib.sha256(data).hexdigest() != row['sha256']:
        raise ValueError('Pinned source hash differs: ' + str(fid))
    return data


def convert():
    from wotlkconv.listfile import Listfile
    source = AssetSource(listfile=Listfile.load(c.DEFAULT.listfile), roots=[CACHE / 'raw'])
    opts = Options(path_prefix='custom\\saberon', strict_limits=True)
    data, report, companions = convert_m2(raw(MODEL_FID), 'creature/saberon/saberon.m2', opts,
                                          source.listfile, source)
    save(ROOT / 'reports/conversion.json', {'model': report.as_dict(),
                                          'companions': [r.result.as_dict() for r in companions]})
    if not data or not report.ok or any(not r.data or not r.result.ok for r in companions):
        raise ValueError('Saberon conversion failed; see conversion.json')
    out = ROOT / 'converted'
    out.mkdir(parents=True, exist_ok=True)
    (out / 'saberon.m2').write_bytes(data)
    for asset in companions:
        (out / asset.filename).write_bytes(asset.data)
    for fid in (*BODY_IDS, *(i for pair in OUTFIT_IDS for i in pair), 982522):
        blob, result = convert_blp(raw(fid), str(fid) + '.blp', opts)
        if not blob or not result.ok:
            raise ValueError('Texture conversion failed: ' + str(fid))
        (out / (str(fid) + '.blp')).write_bytes(blob)
    print('CONVERTED', parse_m2(data).describe(), flush=True)


def audit():
    model = parse_m2((ROOT / 'converted/saberon.m2').read_bytes())
    skin = parse_skin((ROOT / 'converted/saberon00.skin').read_bytes())
    report = {'vertices': model.vertex_count, 'bones': len(model.bones),
              'geosets': sorted({visual.u16(r, 0) for r in skin.submeshes}),
              'textures': model.textures,
              'attachments': [{k: r[k] for k in ('id', 'bone', 'position')} for r in model.attachments],
              'sequences': [r['id'] for r in model.sequences]}
    save(ROOT / 'reports/audit.json', report)
    print(json.dumps(report), flush=True)


def profile():
    return {'capacities': [len(v) for v in CHOICES],
            'options': [{'label': n, 'choices': list(v)} for n, v in zip(LABELS, CHOICES)]}


def manifest():
    return {'schema_version': 1, 'slug': 'saberon', 'name': 'Saberon', 'race_ids': [RACE],
            'enum': 'RACE_SABERON_HORDE', 'faction': 'horde', 'client_file_strings': {str(RACE): TOKEN},
            'glue_token': TOKEN.upper(), 'helmet_prefix': 'Sb', 'source_race_id': 2, 'legacy_mask_race': 2,
            'visual_base_race': 12, 'start_profile': 'durotar', 'donor_totem_race': 2,
            'classes': [1, 2, 3, 4, 5, 6, 7, 8, 9, 11], 'source_patch_root': str(ROOT / 'converted'),
            'runtime_patch_root': str(STAGE / 'assets'),
            'models': {'male': {'model_id': 120070, 'display_id': 60061, 'model_path': MODEL}},
            'appearance': {'mode': 'native-stock-five-byte-v1', 'source': 'retail-creature-saberon',
                           'hide_helm': True, 'supported_genders': [0], 'profiles': {'0': profile()},
                           'equipped_armor_geosets': p.load_manifest('saberon')['appearance'].get(
                               'equipped_armor_geosets', 'deferred') if p.manifest_path('saberon').exists()
                               else 'deferred'},
            'random_playerbot_enabled': False, 'custom_racial_spells': []}


def allocation():
    result = p.load_json(p.ALLOCATION_PATH)
    if any(RACE in ids for slug, ids in result['race_ids'].items() if slug != 'saberon'):
        raise ValueError('Race64 belongs to another pack')
    old = result['race_allocations'].get('saberon')
    if old is not None and old != RANGES:
        raise ValueError('Saberon allocation differs')
    for slug, tables in result['race_allocations'].items():
        if slug == 'saberon':
            continue
        for name, bounds in RANGES.items():
            other = tables.get(name)
            if (isinstance(bounds, list) and isinstance(other, list)
                    and max(bounds[0], other[0]) <= min(bounds[1], other[1])):
                raise ValueError('Saberon allocation overlaps ' + slug + '/' + name)
            if (isinstance(bounds, dict) and isinstance(other, dict)
                    and (set(bounds.values()) - {0}) & set(other.values())):
                raise ValueError('Saberon model/display allocation overlaps ' + slug)
    result['race_ids']['saberon'] = [RACE]
    result['race_allocations']['saberon'] = copy.deepcopy(RANGES)
    for name, bounds in RANGES.items():
        result['dbc_ranges'][name][1] = max(result['dbc_ranges'][name][1],
                                            bounds[1] if isinstance(bounds, list) else max(bounds.values()))
    return result


def config():
    reserved = allocation()
    registry_path = p.ROOT / 'modules/mod-custom-server/data/races/race_registry.json'
    registry = p.load_json(registry_path)
    entry = {'id': RACE, 'species_key': 'saberon_horde', 'display_name': 'Saberon', 'faction': 'horde',
             'species_selection': False, 'start_profile': 'durotar', 'asset_owner': 'retroporter_saberon',
             'legacy_mask_race': 2, 'visual_base_race': 12, 'supported_genders': [0]}
    old = next((r for r in registry['playable'] if r['id'] == RACE), None)
    if old is not None and old != entry:
        raise ValueError('Registry slot64 differs')
    if old is None:
        registry['playable'].append(entry)
    registry['sources']['retroporter_saberon'] = str(STAGE / 'assets')
    save(p.manifest_path('saberon'), manifest())
    save(p.ALLOCATION_PATH, reserved)
    save(registry_path, registry)
    c.header()


def prepare():
    if p.manifest_path('saberon').exists() and p.load_manifest('saberon')['appearance'].get(
            'equipped_armor_geosets') in ('player-atlas-v1', 'source-fur-overlay-v2'):
        import saberon_equipment_pack as gear
        gear.prepare()
        for key in (MODEL, MODEL[:-3] + '00.skin'):
            local(STAGE / 'assets', key).write_bytes(local(gear.STAGE / 'assets', key).read_bytes())
        for name in ('EsteriaSaberon.bin', 'EsteriaSaberonTextures.bin'):
            (STAGE / name).write_bytes((gear.STAGE / name).read_bytes())
        return
    import creature_animation_repair as repair
    import earthen_race_pack as e
    import sethrak_animation_pack as animation
    model = visual.read_player_model(ROOT / 'converted/saberon.m2')
    e.tracks.embed(model, ROOT / 'converted', 'saberon')
    original = copy.deepcopy(model)
    actions = set(animation.ACTIONS) | {13, 18, 22, 23, 24, 27, 29, 30, 46, 61,
                                       84, 85, 86, 87, 88, 95, 105, 108, 109, 118, 121, 185, 186}
    missing = actions - {q['id'] for q in model.sequences}
    report = {'added': []}
    if missing:
        files = p.ClientFiles(str(p.CLIENT_DEFAULT / 'Data'), 'enUS')
        try:
            key = 'Character\\Worgen\\Male\\WorgenMale.m2'
            donor, hashes = animation.embedded_model(STAGE / 'donors', key, lambda k: files.find(k)[0])
            report['donor_hashes'] = hashes
            for action in sorted(missing):
                report['added'].append(repair.retarget(model, donor, action))
        finally:
            files.close()
    report['compatibility'] = repair.repair_model('saberon', 0, model)
    animation.tracks_equal(original, model, len(original.sequences))
    skin = parse_skin((ROOT / 'converted/saberon00.skin').read_bytes())
    # Keep NPC outfit selectors clear of Wrath hair/equipment groups; every source mesh stays available.
    for index, row in enumerate(skin.submeshes):
        geo = visual.u16(row, 0)
        if geo:
            updated = bytearray(row)
            visual.patch16(updated, 0, 3000 + geo)
            skin.submeshes[index] = bytes(updated)
    skin = visual.compact_bone_palettes(model, skin)
    report['material_repair'] = normalize_materials(model, skin)
    # Esteria's existing geometry catalog and EsteriaWideSource retain the index high word.
    if len(skin.vertices) > 65535 or any(visual.u16(r, 10) > 65535 for r in skin.submeshes):
        raise ValueError('Saberon exceeds the vertex or per-mesh index budget')
    model.num_skin_profiles = 1
    model.replacable_texture_lookup = [65535] * 16
    entries = {}
    inventory = p.load_json(CACHE / 'inventory.json')['assets']
    for i, texture in enumerate(model.textures):
        if texture['type']:
            model.replacable_texture_lookup[texture['type']] = i
        else:
            name = PureWindowsPath(texture['filename']).name.lower()
            match = next(r for r in inventory.values() if PureWindowsPath(r['logical_name']).name.lower() == name)
            fid = match['file_data_id']
            data, result = convert_blp(raw(fid), name, Options())
            if not data or not result.ok:
                raise ValueError('Static material conversion failed: ' + name)
            texture['filename'] = PREFIX + 'textures\\' + name
            entries[texture['filename']] = data
    model.attachment_lookup[11] = 65535  # Helm fitting is part of the deferred equipment work.
    entries[MODEL] = write_md20(model)
    entries[MODEL[:-3] + '00.skin'] = write_skin(skin)
    animation.check_model(parse_m2(entries[MODEL]), entries[MODEL])
    records = []

    def record(kind, target, value, field, choice, path=''):
        if len(path.encode()) >= 128:
            raise ValueError('Native material path too long')
        records.append(struct.pack('<7I', 0, kind, target, value, field | choice << 16,
                                   0xffffffff, 0xffffffff) + path.encode().ljust(128, b'\0'))

    for field, slot in ((0, 11), (2, 12), (3, 13)):
        for choice, fid in enumerate(CHOICES[field]):
            path = PREFIX + 'textures\\' + str(fid) + '.blp'
            entries[path] = (ROOT / 'converted' / (str(fid) + '.blp')).read_bytes()
            record(1, slot, 0, field, choice, path)
    for choice, geo in enumerate(CHOICES[1]):
        record(0, 31, 3000 + geo, 1, choice)
    for key, data in entries.items():
        path = local(STAGE / 'assets', key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    (STAGE / 'EsteriaSaberon.bin').write_bytes(struct.pack('<3I', 0x314D4845, 1, len(records)) + b''.join(records))
    (STAGE / 'EsteriaSaberonTextures.bin').write_bytes(struct.pack('<4I', 0x31544845, 1, 0, 0))
    report.update(vertices=model.vertex_count, indices=len(skin.indices), sequences=len(model.sequences),
                  maximum_palette=max(visual.u16(r, 12) for r in skin.submeshes))
    save(STAGE / 'model.json', report)
    print('PREPARED SABERON', model.vertex_count, 'vertices', len(skin.indices), 'indices',
          len(model.sequences), 'sequences', flush=True)


def normalize_materials(model, skin):
    """Replace unsupported Retail reflective multiply combiners with the existing Wrath diffuse path."""
    fixed = {}
    for index, original in enumerate(skin.batches):
        count, combo, coordinates = (visual.u16(original, offset) for offset in (14, 16, 18))
        first = model.textures[model.texture_combos[combo]]['type']
        if first not in (11, 12, 13) or count != 2 or visual.u16(original, 2) != 0:
            continue
        if model.texture_coord_combos[coordinates:coordinates + 2] != [0, 65535]:
            raise ValueError('Saberon reflective material uses unexpected texture coordinates')
        second = model.textures[model.texture_combos[combo + 1]]
        if second['type'] != 0:
            raise ValueError('Saberon reflective material uses an unexpected second texture')
        batch = bytearray(original)
        batch[0] &= 0x7f
        visual.patch16(batch, 2, 0)
        visual.patch16(batch, 14, 1)
        skin.batches[index] = bytes(batch)
        fixed[str(first)] = fixed.get(str(first), 0) + 1
    return fixed


def preview():
    from wotlkconv.blp import Blp
    from gnoll_race_pack import triangles
    from sethrak_equipment_repair import vertex_record
    model = parse_m2(local(STAGE / 'assets', MODEL).read_bytes())
    skin = parse_skin(local(STAGE / 'assets', MODEL[:-3] + '00.skin').read_bytes())
    textures = {}
    root = STAGE / 'preview'
    root.mkdir(parents=True, exist_ok=True)
    for index, texture in enumerate(model.textures):
        path = texture['filename'] if texture['type'] == 0 else PREFIX + 'textures\\' + str(
            {11: BODY_IDS[0], 12: OUTFIT_IDS[0][0], 13: OUTFIT_IDS[0][1]}[texture['type']]) + '.blp'
        image = Blp.parse(local(STAGE / 'assets', path).read_bytes()).decode_level(0)
        target = root / (str(index) + '.png')
        Image.frombytes('RGBA', (image.width, image.height), bytes(image.data)).save(target)
        textures[index] = str(target)
    vertices = [vertex_record(model, i) for i in range(model.vertex_count)]
    for fid in BODY_IDS:
        image = Blp.parse(raw(fid)).decode_level(0)
        Image.frombytes('RGBA', (image.width, image.height), bytes(image.data)).save(root / (str(fid) + '.png'))
    for style, fur in [(style, 0) for style in range(10)] + [(0, fur) for fur in range(1, 4)]:
        parts = []
        for i, row in enumerate(skin.submeshes):
            geo = visual.u16(row, 0)
            if geo not in (0, 3100 + style):
                continue
            batch = next(b for b in skin.batches if visual.u16(b, 4) == i)
            index = model.texture_combos[visual.u16(batch, 16)]
            path = str(root / (str(BODY_IDS[fur]) + '.png')) if model.textures[index]['type'] == 11 else textures[index]
            parts.append({'geoset': geo, 'triangles': triangles(skin, row), 'texture': path})
        work = {'vertices': vertices, 'meshes': parts}
        save(root / ('style-' + str(style) + '-fur-' + str(fur)) / 'model.json', work)
        if style == 0 and fur == 0:
            save(root / 'model.json', work)


def tables(baseline):
    import sethrak_race_pack as s
    import ogre_furbolg_race_pack as o
    result = dict(baseline)
    p._ensure_id_free(result['ChrRaces'], 'ChrRaces', {RACE})
    result['ChrRaces'] = p._merge_chr_races(result['ChrRaces'], manifest(), allocation())
    races = p.RawWdbc(result['ChrRaces'])
    pool, rows = bytearray(races.strings), []
    for row in races.records:
        if p._value(row, 0) == RACE:
            for field, value in ((1, 14), (2, 2), (7, 1), (12, 0), (13, 1), (68, 0)):
                row = p._replace(row, field * 4, 4, value)
            row = p._set_string(row, 6, pool, 'Sb')
        rows.append(row)
    result['ChrRaces'] = races.build(rows, bytes(pool))
    donor_race = next(r for r in races.records if p._value(r, 0) == 12)
    displays = p.RawWdbc(result['CreatureDisplayInfo'])
    display = next(r for r in displays.records if p._value(r, 0) == p._value(donor_race, 16))
    models = p.RawWdbc(result['CreatureModelData'])
    row = next(r for r in models.records if p._value(r, 0) == p._value(display, 4))
    pool = bytearray(models.strings)
    row = p._clone_strings('CreatureModelData', models, row, pool)
    row = p._replace(p._replace(row, 0, 4, 120070), 4, 4, p._value(row, 4) | 0x804)
    row = p._set_string(row, 2, pool, MODEL)
    row = row[:16] + struct.pack('<f', 1.0) + row[20:]
    retail_model = p.load_json(ROOT / 'reports/references.json')['models'][0]
    row = row[:56] + struct.pack('<2f', retail_model['CollisionWidth'], retail_model['CollisionHeight']) + row[64:]
    result['CreatureModelData'] = s.append_rows(result['CreatureModelData'], 'CreatureModelData', [row], pool)
    pool = bytearray(displays.strings)
    row = p._clone_strings('CreatureDisplayInfo', displays, display, pool)
    for offset, value in ((0, 60061), (4, 120070), (8, 0), (12, 0), (24, 0), (28, 0), (32, 0), (36, 0)):
        row = p._replace(row, offset, 4, value)
    row = row[:16] + struct.pack('<f', 1.0) + row[20:]
    result['CreatureDisplayInfo'] = s.append_rows(result['CreatureDisplayInfo'], 'CreatureDisplayInfo', [row], pool)
    result['CharBaseInfo'] = p._build_char_base_info(result['CharBaseInfo'], manifest())
    outfits = p.RawWdbc(result['CharStartOutfit'])
    donors = {}
    for row in sorted(outfits.records, key=lambda r: p._value(r, 0)):
        if row[4] == 2 and row[5] in manifest()['classes'] and row[6] == 0 and row[7] == 0:
            donors[row[5]] = row
    if len(donors) != 10:
        raise ValueError('Missing Horde starter chassis')
    rows = [p._replace(p._replace(row, 0, 4, RANGES['CharStartOutfit'][0] + i), 4, 1, RACE)
            for i, row in enumerate(donors.values())]
    result['CharStartOutfit'] = s.append_rows(result['CharStartOutfit'], 'CharStartOutfit', rows)
    names = p.RawWdbc(result['NameGen'])
    male_names = names.build([r for r in names.records if p._value(r, 8) != 2 or p._value(r, 12) == 0])
    generated = p.RawWdbc(p._clone_namegen(male_names, manifest(), allocation()))
    result['NameGen'] = s.append_rows(result['NameGen'], 'NameGen',
                                     [r for r in generated.records if p._value(r, 8) == RACE], generated.strings)
    sections = p.RawWdbc(result['CharSections'])
    pool, added, hair, facial, barber = bytearray(sections.strings), [], [], [], []
    capacities = profile()['capacities']

    def section(kind, style, color):
        row = struct.pack('<10I', RANGES['CharSections'][0] + len(added), RACE, 0, kind,
                          0, 0, 0, 1 if kind == 1 else 17, style, color)
        if kind == 0:
            row = p._set_string(row, 4, pool, PREFIX + 'textures\\' + str(BODY_IDS[color]) + '.blp')
        added.append(row)

    for color in range(capacities[0]):
        for kind in (0, 4):
            section(kind, 0, color)
        for face in range(capacities[1]):
            section(1, face, color)
    for style in range(capacities[2]):
        for color in range(capacities[3]):
            section(3, style, color)
        hair.append(struct.pack('<6I', RANGES['CharHairGeosets'][0] + style, RACE, 0, style, 0, 1))
    for color in range(capacities[3]):
        section(2, 0, color)
    facial.append(struct.pack('<8I', RACE, 0, 0, 0, 0, 0, 0, 0))
    source = p.RawWdbc(result['BarberShopStyle'])
    for kind, field in ((0, 2), (2, 4), (3, 0)):
        donor = next(r for r in source.records if p._value(r, 4) == kind)
        for value in range(capacities[field]):
            row = donor
            for offset, n in ((0, RANGES['BarberShopStyle'][0] + len(barber)), (148, RACE), (152, 0), (156, value)):
                row = p._replace(row, offset, 4, n)
            barber.append(row)
    for name, new, strings in (('CharSections', added, pool), ('CharHairGeosets', hair, None),
                               ('CharacterFacialHairStyles', facial, None), ('BarberShopStyle', barber, None)):
        result[name] = s.append_rows(result[name], name, new, strings)
    result['CharSections'] = o.order_charsections_entry(p.DBC_ROOT + 'CharSections.dbc', result['CharSections'])
    return result


def glue(original):
    import ogre_furbolg_race_pack as o
    result = {name: data.decode('utf-8-sig') for name, data in original.items()}

    def insert(name, anchor, payload):
        result[name] = o._insert_once(result[name], anchor, payload, 'Saberon ' + name)

    insert('CharacterInfo.lua', 'local EXACT_RACE_DATA = {\n',
           '    [64] = {glueString="SABERONHORDE", name="Saberon", faction="Horde", fileString="SaberonHorde"},\n')
    result['CharacterInfo.lua'] += ('\nRaceInfoByFileString.SABERONHORDE = {Name="Saberon", '
        'Description="Fierce feline hunters from Draenor, these Saberon have joined the Horde."};\n')
    insert('CharacterCreate.lua', 'RACE_ICON_TEXTURES = {\n',
           '    ["SABERONHORDE_MALE"] = "Interface\\\\Glues\\\\CharacterCreate\\\\'
           'UI-CharacterCreate-SaberonHordeMale",\n')
    insert('CharacterCreate.lua', 'local RACE_BACKGROUND_KEYS = {\n', '        ["SABERONHORDE"] = "ORC",\n')
    creator = result['CharacterCreate.lua']
    for anchor in ('or race == 63', 'or target.raceID == 63', 'or CharacterCreate.selectedRaceID == 63'):
        creator = creator.replace(anchor, anchor + ' ' + anchor.replace('63', '64'))
    anchor = 'fileString and strupper(fileString) == "GNOLLHORDE";'
    if creator.count(anchor) != 1:
        raise ValueError('Installed single-body creator refresh changed')
    creator = creator.replace(anchor,
        'fileString and (strupper(fileString) == "GNOLLHORDE" or strupper(fileString) == "SABERONHORDE");')
    result['CharacterCreate.lua'] = creator
    result['GlueStrings.lua'] += '\nSABERONHORDE="Saberon"; SABERONHORDE_MALE=SABERONHORDE;\n'
    insert('GlueParent.lua', '    local hordeRaces = {\n', '        ["SABERONHORDE"] = true,\n')
    result['GlueParent.lua'] += ('\nCharModelFogInfo.SABERONHORDE=CharModelFogInfo.ORC;\n'
        'CharModelGlowInfo.SABERONHORDE=CharModelGlowInfo.ORC;\n'
        'GlueAmbienceTracks.SABERONHORDE=GlueAmbienceTracks.ORC;\n')
    insert('ECS_Schema.lua', 'S.RaceOverride = {\n',
           '    [64] = {name="Saberon", faction=2, artKey="SaberonHorde"},\n')
    insert('ECS_Schema.lua', 'S.RaceByModelKey = {\n',
           '    {"SABERONHORDE", {name="Saberon", faction=2, artKey="SaberonHorde"}},\n')
    insert('ECS_Schema.lua', 'S.PortraitArtKeys = {\n', '    SaberonHorde=true,\n')
    result['ECS_Integrate.lua'] = result['ECS_Integrate.lua'].replace('or race == 63', 'or race == 63 or race == 64')
    validate_glue(result)
    return {name: text.encode() for name, text in result.items()}


def validate_glue(entries):
    """Use the client's Lua version; permissive parsers accept malformed tokens such as 63or."""
    from lupa.lua51 import LuaRuntime
    lua = LuaRuntime()
    compile_chunk = lua.eval('function(source, name) local f, err = loadstring(source, name); '
                            'assert(f, err); return true end')
    for name, text in entries.items():
        compile_chunk(text.decode('utf-8-sig') if isinstance(text, bytes) else text, '@' + p.GLUE_ROOT + name)


def stage():
    import shutil
    import sethrak_race_pack as s
    import ogre_furbolg_race_pack as o
    import race_portrait_pack as portraits
    client = p.CLIENT_DEFAULT
    if (client / ASSET_ARCHIVE).exists():
        raise FileExistsError('Saberon asset archive slot already exists')
    files = p.ClientFiles(str(client / 'Data'), 'enUS')
    try:
        baseline = {name: files.find(p.DBC_ROOT + name + '.dbc')[0] for name in s.TABLES}
        original = {name: files.find(p.GLUE_ROOT + name)[0] for name in s.GLUE}
        output, patched = tables(baseline), glue(original)
        template = files.find(portraits.ICON_TEMPLATE_ENTRY)[0]
        ring = portraits.ring_layer(portraits.decode_client_blp(files.find(portraits.RING_ENTRY)[0]))
    finally:
        files.close()
    assets = {'\\'.join(path.relative_to(STAGE / 'assets').parts): path.read_bytes()
              for path in (STAGE / 'assets').rglob('*') if path.is_file()}
    art = Image.open(STAGE / 'preview/portrait.png').convert('RGBA').resize((64, 64), Image.Resampling.LANCZOS)
    art.putalpha(portraits.circular_mask())
    plain = portraits.encode_portrait(art, template)
    assets[portraits.CREATOR_ICON_ROOT + 'UI-CharacterCreate-SaberonHordeMale.blp'] = portraits.encode_portrait(
        portraits.compose_race_icon(art, ring), template)
    stem = portraits.CHARACTER_FRAME_ROOT + 'TemporaryPortrait-Male-SaberonHorde'
    assets[stem] = assets[stem + '.blp'] = plain
    assets['Interface\\Glues\\CharacterSelect\\ECS-Portrait-SaberonHordeMale.blp'] = plain
    for key, data in assets.items():
        path = local(STAGE / 'assets', key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    before = (client / 'EsteriaAppearance.bin').read_bytes()
    magic, version, count = struct.unpack_from('<3I', before)
    stride = 12 + 16 * 144
    if (magic, version) != (0x50504145, 2) or len(before) != 12 + count * stride:
        raise ValueError('Appearance catalog format changed')
    if any(struct.unpack_from('<I', before, 12 + i * stride)[0] == RACE for i in range(count)):
        raise ValueError('Saberon appearance record already exists')
    row = bytearray(struct.pack('<3I', RACE, 0, 5))
    for offset, n in zip((0x28, 0x2C, 0x34, 0x24, 0x30), profile()['capacities']):
        row.extend(struct.pack('<4I', offset, n, 1, 0) + bytes(128))
    row.extend(bytes(11 * 144))
    (STAGE / 'EsteriaAppearance.bin').write_bytes(struct.pack('<3I', magic, version, count + 1) + before[12:] + row)
    geometry = (client / 'EsteriaAppearanceGeometry.bin').read_bytes()
    magic, version, count = struct.unpack_from('<3I', geometry)
    if (magic, version) != (0x4D474145, 1):
        raise ValueError('Geometry catalog format changed')
    addition = MODEL.encode().ljust(128, b'\0') + struct.pack('<I', len(assets[MODEL[:-3] + '00.skin']))
    addition += assets[MODEL[:-3] + '00.skin']
    (STAGE / 'EsteriaAppearanceGeometry.bin').write_bytes(
        struct.pack('<3I', magic, version, count + 1) + geometry[12:] + addition)
    for name, data in {**{n + '.dbc': b for n, b in baseline.items()}, **original,
                       'EsteriaAppearance.bin': before, 'EsteriaAppearanceGeometry.bin': geometry}.items():
        c.immutable(STAGE / 'baseline' / name, data)
    for folder, values in (('client-dbc', output), ('glue', patched)):
        for name, data in values.items():
            path = STAGE / folder / (name + '.dbc' if folder == 'client-dbc' else name)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
    for name in s.SERVER_TABLES:
        base = (p.SERVER_DBC_ROOT / (name + '.dbc')).read_bytes()
        source, table = p.RawWdbc(output[name]), p.RawWdbc(base)
        if name in ('CreatureModelData', 'CreatureDisplayInfo'):
            new = [r for r in source.records if p._value(r, 0) in set(RANGES[name].values()) - {0}]
        else:
            new = p._table_rows_for_race(output[name], name, RACE)
        p._ensure_id_free(base, name, {p._value(r, 0) for r in new})
        pool = bytearray(table.strings)
        data = table.build(list(table.records) + [p._clone_strings(name, source, r, pool) for r in new], bytes(pool))
        path = STAGE / 'server/dbc' / (name + '.dbc')
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        c.immutable(STAGE / 'baseline-server' / path.name, base)
    migration = o.build_sql({'name': 'Saberon', 'race_id': RACE, 'faction': 'horde', 'donor_start_race': 2,
                             'donor_totem_race': 2}).replace('ogre_furbolg_race_pack.py', 'saberon_race_pack.py')
    migration += o.CHRRACES_TEMPLATE.format(race=RACE, faction_template=2, male_display=60061, female_display=0,
        prefix='Sb', base_language=1, file_string=TOKEN, alliance=1, name='Saberon')
    c.immutable(MIGRATION, (migration.rstrip() + '\n').encode())
    (STAGE / 'saberon.sql').write_bytes(MIGRATION.read_bytes())
    storm = p.Storm(p.DLL_DEFAULT)
    target = STAGE / 'client' / ASSET_ARCHIVE
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name('saberon-' + uuid.uuid4().hex + '.MPQ')
    storm.create_archive(temporary, assets)
    os.replace(temporary, target)
    replacements = {p.DBC_ROOT + n + '.dbc': b for n, b in output.items()}
    replacements.update({p.GLUE_ROOT + n: b for n, b in patched.items()})
    report = {'status': 'staged_build_and_deployment_required', 'race': RACE, 'client': str(client),
              'source_pin': p.load_json(CACHE / 'source-pin.json'), 'exe_sha256': p.sha256(client / 'Wow.exe'),
              'archives': {str(ASSET_ARCHIVE): p.sha256(target)}, 'archive_baselines': {},
              'assets': {k: hashlib.sha256(v).hexdigest() for k, v in assets.items()},
              'migration': str(MIGRATION), 'live_install_performed': False}
    for relative in (p.GLOBAL_ARCHIVE_REL, p.LOCALE_ARCHIVE_REL):
        live, target = client / relative, STAGE / 'client' / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        before_hash = p.sha256(live)
        snapshot = STAGE / 'baseline-archives' / relative
        snapshot.parent.mkdir(parents=True, exist_ok=True)
        if not snapshot.exists():
            shutil.copy2(live, snapshot)
        if p.sha256(snapshot) != before_hash or p.sha256(live) != before_hash:
            raise ValueError('Live archive changed while capturing the merge base')
        print('STAGING', relative, flush=True)
        o.rebuild_archive_replacing(storm, snapshot, target, replacements, compress=True)
        if p.sha256(live) != before_hash:
            raise ValueError('Live merge base changed during staging')
        report['archive_baselines'][str(relative)] = before_hash
        report['archives'][str(relative)] = p.sha256(target)
    save(STAGE / 'report.json', report)
    print('STAGED HORDE SABERON', STAGE, flush=True)


def preflight():
    """Read-only collision and merge-base check; does not require closing either client."""
    import mechagnome_race_pack as db
    import sethrak_race_pack as base
    report = p.load_json(STAGE / 'report.json')
    for relative, expected in report['archive_baselines'].items():
        if p.sha256(p.CLIENT_DEFAULT / relative) != expected:
            raise ValueError('Live archive changed; restage before deployment: ' + relative)
    for name in ('EsteriaAppearance.bin', 'EsteriaAppearanceGeometry.bin'):
        if p.sha256(p.CLIENT_DEFAULT / name) != p.sha256(STAGE / 'baseline' / name):
            raise ValueError('Live native catalog changed; restage: ' + name)
    for name in base.SERVER_TABLES:
        if p.sha256(p.SERVER_DBC_ROOT / (name + '.dbc')) != p.sha256(STAGE / 'baseline-server' / (name + '.dbc')):
            raise ValueError('Mounted server DBC changed; restage: ' + name)
    counts = {}
    for table, field in {**c.WORLD_TABLES, 'chrraces_dbc': 'ID'}.items():
        counts[table] = int(db.sql(f'SELECT COUNT(*) FROM `{table}` WHERE `{field}`=64;').strip())
    for table, identifier in (('creaturedisplayinfo_dbc', 60061), ('creaturemodeldata_dbc', 120070)):
        counts[table] = int(db.sql(f'SELECT COUNT(*) FROM `{table}` WHERE `ID`={identifier};').strip())
    counts['characters'] = int(db.sql('SELECT COUNT(*) FROM characters WHERE race=64;', 'acore_characters').strip())
    counts['updates'] = int(db.sql(f"SELECT COUNT(*) FROM updates WHERE name='{MIGRATION.name}';").strip())
    if any(counts.values()):
        raise ValueError('Saberon live targets already have rows: ' + json.dumps(counts))
    for name in (str(ASSET_ARCHIVE), 'EsteriaSaberon.bin', 'EsteriaSaberonTextures.bin'):
        if (p.CLIENT_DEFAULT / name).exists():
            raise ValueError('Saberon live target file already exists: ' + name)
    save(STAGE / 'preflight.json', {'counts': counts, 'live_install_performed': False})
    print('PASS current live targets are free; archive/catalog/mounted DBC merge bases unchanged', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('acquire', 'convert', 'audit', 'config', 'prepare', 'preview',
                                           'stage', 'preflight'))
    globals()[parser.parse_args().action]()
