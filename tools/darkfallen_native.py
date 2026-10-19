"""Darkfallen (races 43/44) on the retail HD Blood Elf bodies, driven by the native appearance system.

Same mechanism as Tarasek/Drakonid: the skin is a replaceable type-11 texture chosen by native selection
records, hair meshes are renumbered into the native-only 22xxx range and shown by selection records, and
the creator uses the stock five selectors with counts taken from CharSections. Stage, pack and install are
separate; nothing here builds the native helper or the worldserver.
"""
import argparse
import hashlib
import json
import shutil
import struct
import subprocess
from datetime import datetime
from pathlib import Path

import creature_race_pack as c
import darkfallen_hd as h
import darkfallen_hd_pack as k
import retroported_race_pack as p
from cars_mount_pack import order_charsections_entry

OUT = Path('G:/RetroPorterWork/darkfallen-native')
SQL = p.ROOT / 'data/sql/updates/pending_db_characters/rev_20261016120000000_darkfallen_native.sql'
MANIFEST = p.manifest_path('darkfallen')
RACES = (43, 44)
SEXES = {'male': 0, 'female': 1}
MODEL_PATHS = {'male': 'Character\\Darkfallen\\Male\\DarkfallenMale.m2',
               'female': 'Character\\Darkfallen\\Female\\DarkfallenFemale.m2'}
TEX = k.BASE
HAIR_BASE = 22000
FIXED_GROUPS = {20: 2001, 22: 2201, 23: 2301, 32: 3202}  # group 32's 3202 is the head; 3201 is the hidden-head stub
SKIN_TYPE = 12
CATALOGS = ('EsteriaAppearance.bin', 'EsteriaAppearanceGeometry.bin', 'EsteriaDarkfallen.bin',
            'EsteriaDarkfallenTextures.bin')
SERVER_TABLES = ('CharSections', 'BarberShopStyle')
CLIENT_TABLES = ('CharSections', 'CharHairGeosets', 'CharacterFacialHairStyles', 'BarberShopStyle')
FIELD_OFFSETS = (0x28, 0x2C, 0x34, 0x24, 0x30)  # skin, face, hair style, hair colour, facial style


def digest(blob):
    return hashlib.sha256(blob).hexdigest()


NEW_ART = Path('C:/Users/Zach/wow.export/character/bloodelf')
HEADER_SKINS, HEADER_COLORS = 5, 10  # server/client header bounds; the data below decides what the creator offers


def art(sex):
    """Re-extracted skins (textures 1-5) and hair atlases (6-10); identical pixels are offered once."""
    import hashlib
    from PIL import Image

    def unique(numbers):
        seen, result = set(), []
        for number in numbers:
            path = NEW_ART / sex / ('bloodelf%s_hd_texture_%d.png' % (sex, number))
            digest_ = hashlib.md5(Image.open(path).convert('RGBA').tobytes()).hexdigest()
            if digest_ not in seen:
                seen.add(digest_)
                result.append(path)
        return result

    return {'skins': unique(range(1, 6)), 'hair': unique(range(6, 11))}


def plan():
    data = k.hair_plan()
    for sex in SEXES:
        data[sex]['colors'] = len(art(sex)['hair'])
    return data


def capacities(sex, data):
    return [len(art(sex)['skins']), 1, len(data[sex]['styles']), data[sex]['colors'], 1]


def bounds(sex, data):
    return capacities(sex, data)


# --- models ---------------------------------------------------------------------------------------

def build_model(sex, inventory):
    import highmountain_complete_tracks as tracks
    import sethrak_animation_pack as animations
    import skyborne_visual_pack as visual
    import vrykul_female_pack as arrays
    from wotlkconv.m2 import parse_m2, parse_skin, write_md20
    from wotlkconv.m2.skin import write_skin

    title = sex.title()
    old, new = 'bloodelf%s_hd' % sex, 'Darkfallen' + title
    source = h.ROOT / 'converted/patch-root/custom/darkfallenhd/character/bloodelf' / sex
    work = OUT / 'model' / sex
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    for path in source.iterdir():
        if path.name.startswith(old):
            shutil.copy2(path, work / (new + path.name[len(old):]))
    directory = TEX + title + '\\'
    model = visual.read_player_model(work / (new + '.m2'))
    tracks.embed(model, work, new)
    skin = parse_skin((work / (new + '00.skin')).read_bytes())

    def fields(batch):
        return struct.unpack_from('<BbHHHhHHHHHHH', bytes(batch))

    def geoset_of(batch):
        return struct.unpack_from('<H', skin.submeshes[fields(batch)[3]])[0]

    usage = {}
    for batch in skin.batches:
        f = fields(batch)
        for n in range(f[8]):
            usage.setdefault(geoset_of(batch), set()).add(model.texture_combos[f[9] + n])
    eye_slot = next(iter(usage[3301]))
    skin_slot = next(slot for slot in usage[0] if model.textures[slot]['type'] == 1)
    files = {}
    for slot, texture in enumerate(model.textures):
        if texture['filename']:
            name = Path(texture['filename'].replace('\\', '/')).name.replace(old, new)
            texture['filename'] = directory + name
            files[directory + name] = name
        elif slot == eye_slot:
            texture['type'], texture['filename'] = 0, directory + 'DarkfallenEyes.blp'
        elif texture['type'] in (9, 11):
            texture['type'], texture['filename'] = 0, TEX + 'Blank.blp'
    blank = {i for i, t in enumerate(model.textures) if t['filename'] == TEX + 'Blank.blp'}
    model.textures[skin_slot]['type'] = SKIN_TYPE
    model.replacable_texture_lookup = [65535] * 20
    for slot, texture in enumerate(model.textures):
        if texture['type']:
            model.replacable_texture_lookup[texture['type']] = slot
    keep = []
    for batch in skin.batches:
        f = fields(batch)
        slots = {model.texture_combos[f[9] + n] for n in range(f[8])}
        geoset = geoset_of(batch)
        # Retail eye-reflect/glow shells, beards and the hair-cap shell need shaders Wrath lacks or are not offered.
        if geoset in (3401, 5101, 5102, 5103) or 1700 < geoset < 1706 or 100 <= geoset < 114 or (
                slots & blank and geoset != 1507):
            continue
        keep.append(batch)
    removed = len(skin.batches) - len(keep)
    skin.batches = keep
    hair = []
    for index, row in enumerate(skin.submeshes):
        geoset = struct.unpack_from('<H', row)[0]
        if 1 <= geoset <= 25:  # retail hair meshes; renumbered so only native selection records show them
            raw = bytearray(row)
            struct.pack_into('<H', raw, 0, HAIR_BASE + geoset)
            skin.submeshes[index] = bytes(raw)
            hair.append(geoset)
    # The native geometry loader accepts at most 75 bones per submesh; split meshes whose palette is larger.
    skin = visual.compact_bone_palettes(model, skin)
    payload, _ = arrays.separate_bone_track_arrays(write_md20(model))
    rebuilt = parse_m2(payload)
    assert rebuilt.vertices == model.vertices and rebuilt.version == 264
    assert all(not t.external for t in rebuilt.tracks())
    actions = {q['id'] for q in rebuilt.sequences}
    required = animations.ACTIONS
    animations.ACTIONS = tuple(a for a in required if a in actions)
    try:
        animations.check_model(rebuilt, payload)
    finally:
        animations.ACTIONS = required
    model_dir = k.MODEL_BASE + title + '\\'
    skin_bytes = write_skin(skin)
    entries = {model_dir + new + '.m2': payload, model_dir + new + '00.skin': skin_bytes}
    for key, name in files.items():
        stem = name.replace(new, old)
        match = next(r for r in inventory['assets'].values() if (r['logical_name'] or '').lower().endswith(stem.lower()))
        entries[key] = k.retail_blp(match['path'], match['logical_name'])
    entries[directory + 'DarkfallenEyes.blp'] = k.png_to_blp(
        k.sex_art(sex).with_name(k.sex_art(sex).name % k.EYE_NUMBER))
    assert sorted(hair) == sorted(set(hair)) and hair, 'Hair meshes not found'
    assert all(not t.external for t in rebuilt.tracks()) and all(q['flags'] & 0x20 for q in rebuilt.sequences)
    return entries, skin_bytes, {'batches_removed': removed, 'eye_slot': eye_slot, 'skin_slot': skin_slot,
                                 'hair_geosets': sorted(hair)}


# --- catalogs -------------------------------------------------------------------------------------

def selection_catalog(data, hair_files, skin_files):
    records = []

    def record(gender, kind, target, value, selectors, path=''):
        selected = [i | j << 16 for i, j in selectors]
        assert len(selected) <= 3 and len(path.encode()) < 128
        records.append(struct.pack('<7I', gender, kind, target, value,
                                   *(selected + [0xffffffff] * (3 - len(selected)))) + path.encode().ljust(128, b'\0'))

    for sex, gender in SEXES.items():
        for choice, path in enumerate(skin_files[sex]):
            record(gender, 1, SKIN_TYPE, 0, [(0, choice)], path)
        for color in range(data[sex]['colors']):
            record(gender, 1, 6, 0, [(3, color)], hair_files[(sex, color)])
        for style, (_, geoset) in enumerate(data[sex]['styles']):
            if geoset:
                record(gender, 2, 0, HAIR_BASE + geoset, [(2, style)])
        # Retail groups above 19 have no stock default: pick one variant each (feet follow the equipped boots).
        for group, value in FIXED_GROUPS.items():
            record(gender, 0, group, value, [])
    assert len(records) <= 16384
    return struct.pack('<3I', 0x314D4845, 1, len(records)) + b''.join(records), len(records)


def texture_bank():
    return struct.pack('<4I', 0x31544845, 1, 0, 0)


def appearance_catalog(original, data):
    magic, version, count = struct.unpack_from('<3I', original)
    stride = 12 + 16 * 144
    assert (magic, version) == (0x50504145, 2) and len(original) == 12 + count * stride
    assert all(struct.unpack_from('<I', original, 12 + i * stride)[0] not in RACES for i in range(count)), \
        'Darkfallen already has appearance profiles'
    rows = []
    for race in RACES:
        for sex, gender in SEXES.items():
            row = bytearray(struct.pack('<3I', race, gender, 5))
            for offset, n in zip(FIELD_OFFSETS, capacities(sex, data)):
                row.extend(struct.pack('<4I', offset, n, 1, 0) + bytes(128))
            row.extend(bytes(11 * 144))
            assert len(row) == stride
            rows.append(bytes(row))
    return struct.pack('<3I', magic, version, count + len(rows)) + original[12:] + b''.join(rows)


def geometry_catalog(original, skins):
    magic, version, count = struct.unpack_from('<3I', original)
    assert (magic, version) == (0x4D474145, 1)
    at = 12
    for _ in range(count):
        name = original[at:at + 128].split(b'\0')[0].decode().lower()
        assert name not in {v.lower() for v in MODEL_PATHS.values()}, 'Darkfallen geometry already registered'
        at += 132 + struct.unpack_from('<I', original, at + 128)[0]
    assert at == len(original)
    result = struct.pack('<3I', magic, version, count + len(skins)) + original[12:]
    for sex, skin in skins.items():
        result += MODEL_PATHS[sex].encode().ljust(128, b'\0') + struct.pack('<I', len(skin)) + skin
    return result


# --- tables ---------------------------------------------------------------------------------------

def edit_hair_geosets(blob, data):
    """Stock hair meshes are disabled (geoset 0, scalp on); the native records show the renumbered meshes."""
    t = k.Rows(blob, RACES, 4)
    template = t.old[0]
    for race in RACES:
        for sex, gender in SEXES.items():
            for variation in range(len(data[sex]['styles'])):
                row = p._replace(template, 0, 4, t.new_id())
                for offset, value in ((4, race), (8, gender), (12, variation), (16, 0), (20, 1)):
                    row = p._replace(row, offset, 4, value)
                t.rows.append(row)
    return t.build()


def transforms(data, skins, hair_path):
    return {'CharSections': lambda b: k.edit_sections(b, data, skins, hair_path),
            'CharHairGeosets': lambda b: edit_hair_geosets(b, data),
            'CharacterFacialHairStyles': k.edit_facial,
            'BarberShopStyle': lambda b: k.edit_barber(b, data)}


def manifest(data):
    profiles = {str(gender): {'capacities': bounds(sex, data),
                              'descriptors': [[i, n, 1] for i, n in enumerate(bounds(sex, data))],
                              'options': [{'label': label, 'choices': list(range(n))} for label, n in zip(
                                  ('Skin Color', 'Face', 'Hair Style', 'Hair Color', 'Facial Hair'),
                                  bounds(sex, data))]}
                for sex, gender in SEXES.items()}
    return {'schema_version': 1, 'slug': 'darkfallen', 'name': 'Darkfallen', 'race_ids': list(RACES),
            'client_file_strings': {'43': 'Darkfallen', '44': 'DarkfallenHorde'},
            'asset_prefix': 'Character\\Darkfallen', 'supported_genders': [0, 1],
            'models': {s: {'model_path': MODEL_PATHS[s]} for s in SEXES},
            'appearance': {'mode': 'native-stock-five-byte-v1', 'source': 'retail-bloodelf-hd',
                           'supported_genders': [0, 1], 'profiles': profiles}}


# --- actions --------------------------------------------------------------------------------------

def stage():
    assert not (OUT / 'stage.json').exists(), 'Already staged: ' + str(OUT)
    inventory = json.loads((h.ROOT / 'reports/inventory.json').read_text())
    data = plan()
    entries, skins, model_report = {}, {}, {}
    for sex in SEXES:
        entries_sex, skins[sex], model_report[sex] = build_model(sex, inventory)
        entries.update(entries_sex)
    entries[TEX + 'Blank.blp'] = k.blank_blp()
    skin_files = {}
    for sex in SEXES:
        skin_files[sex] = []
        for color, path in enumerate(art(sex)['skins']):
            key = '%s%s\\DarkfallenSkin%02d.blp' % (TEX, sex.title(), color)
            entries[key] = k.png_to_blp(path)
            skin_files[sex].append(key)
    hair_files = {}
    for sex in SEXES:
        for color, path in enumerate(art(sex)['hair']):
            key = '%s%s\\Hair%02d.blp' % (TEX, sex.title(), color)
            entries[key] = k.png_to_blp(path)
            hair_files[(sex, color)] = key
    hair_path = lambda sex, color: hair_files[(sex, color)]

    files = p.ClientFiles(str(p.CLIENT_DEFAULT / 'Data'), 'enUS')
    try:
        baselines = {name: files.find(p.DBC_ROOT + name + '.dbc')[0] for name in CLIENT_TABLES}
    finally:
        files.close()
    work = transforms(data, skin_files, hair_path)
    dbcs = {name: work[name](baselines[name]) for name in CLIENT_TABLES}
    server, server_baseline = {}, {}
    for name in SERVER_TABLES:
        blob = (p.SERVER_DBC_ROOT / (name + '.dbc')).read_bytes()
        server_baseline[name] = digest(blob)
        server[name] = work[name](blob)

    baseline = OUT / 'baseline'
    cats = {}
    for name in ('EsteriaAppearance.bin', 'EsteriaAppearanceGeometry.bin'):
        blob = (p.CLIENT_DEFAULT / name).read_bytes()
        (baseline / name).parent.mkdir(parents=True, exist_ok=True)
        (baseline / name).write_bytes(blob)
        cats[name + ' baseline'] = digest(blob)
    appearance = appearance_catalog((baseline / 'EsteriaAppearance.bin').read_bytes(), data)
    geometry = geometry_catalog((baseline / 'EsteriaAppearanceGeometry.bin').read_bytes(), skins)
    selections, count = selection_catalog(data, hair_files, skin_files)
    catalogs = {'EsteriaAppearance.bin': appearance, 'EsteriaAppearanceGeometry.bin': geometry,
                'EsteriaDarkfallen.bin': selections, 'EsteriaDarkfallenTextures.bin': texture_bank()}

    stage_root = OUT / 'stage'
    for key, blob in entries.items():
        path = stage_root / ('model' if key.startswith(k.MODEL_BASE) else 'assets') / key.replace('\\', '/')  # models are served from patch-Z.MPQ
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(blob)
    for name, blob in dbcs.items():
        (stage_root / 'client').mkdir(parents=True, exist_ok=True)
        (stage_root / 'client' / (name + '.dbc')).write_bytes(blob)
    for name, blob in server.items():
        (stage_root / 'server').mkdir(parents=True, exist_ok=True)
        (stage_root / 'server' / (name + '.dbc')).write_bytes(blob)
    for name, blob in catalogs.items():
        (stage_root / 'catalogs').mkdir(parents=True, exist_ok=True)
        (stage_root / 'catalogs' / name).write_bytes(blob)
    manifest_data = manifest(data)
    MANIFEST.write_text(json.dumps(manifest_data, indent=2) + '\n', encoding='utf-8', newline='\n')
    c.header()
    male, female = capacities('male', data), capacities('female', data)
    SQL.write_text(
        '-- Darkfallen HD (native appearance): supplied skins/hair, one face, retail hair styles, no facial hair.\n'
        'UPDATE `characters` SET `skin` = LEAST(`skin`, IF(`gender` = 0, %d, %d)), `face` = 0, `facialStyle` = 0,\n'
        '    `hairStyle` = LEAST(`hairStyle`, IF(`gender` = 0, %d, %d)),\n'
        '    `hairColor` = LEAST(`hairColor`, IF(`gender` = 0, %d, %d))\n'
        'WHERE `race` IN (43, 44);\n' % (male[0] - 1, female[0] - 1, male[2] - 1, female[2] - 1, male[3] - 1, female[3] - 1),
        encoding='utf-8', newline='\n')
    report = {'state': 'staged_not_built_not_installed', 'models': model_report, 'selection_records': count,
              'capacities': {'male': male, 'female': female}, **cats,
              'client_baseline': {k_: digest(v) for k_, v in baselines.items()},
              'server_baseline': server_baseline,
              'assets': {key: digest(value) for key, value in sorted(entries.items())},
              'catalogs': {name: digest(blob) for name, blob in catalogs.items()}}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'stage.json').write_text(json.dumps(report, indent=2) + '\n')
    print('Staged', len(entries), 'assets,', count, 'selection records; header regenerated')


def pack():
    report = json.loads((OUT / 'stage.json').read_text())
    stage_root = OUT / 'stage'
    live = p.CLIENT_DEFAULT / k.LOCALE
    package = OUT / 'client' / k.LOCALE
    assert not package.exists(), 'Package already exists'
    package.parent.mkdir(parents=True, exist_ok=True)
    before = p.sha256(live)
    shutil.copy2(live, package)
    entries = {p.DBC_ROOT + path.name: path.read_bytes() for path in sorted((stage_root / 'client').glob('*.dbc'))}
    for path in sorted((stage_root / 'assets').rglob('*')):
        if path.is_file():
            entries[str(path.relative_to(stage_root / 'assets')).replace('/', '\\')] = path.read_bytes()
    storm = p.Storm(p.DLL_DEFAULT)
    storm.replace_archive_entries(package, entries)
    assert package.stat().st_size < 0x80000000, 'Classic MPQ boundary exceeded: %d' % package.stat().st_size
    handle = storm.open_archive(package)
    try:
        for name, blob in entries.items():
            assert storm.read(handle, name) == order_charsections_entry(name, blob), name
    finally:
        storm.dll.SFileCloseArchive(handle)
    assert p.sha256(live) == before, 'Live archive changed while packaging'
    report.update(state='packaged_not_built_not_installed', archive_baseline=before, archive=p.sha256(package),
                  archive_bytes=package.stat().st_size)
    (OUT / 'stage.json').write_text(json.dumps(report, indent=2) + '\n')
    print('Packaged', len(entries), 'entries;', package.stat().st_size, 'bytes')


def patchz():
    """Put the model files into Data/patch-Z.MPQ (backup kept outside Data). Run once on an original archive."""
    root = OUT / 'stage/model/Character/Darkfallen'
    entries = {str(path.relative_to(root.parent.parent)).replace('/', chr(92)): path.read_bytes()
               for path in sorted(root.rglob('*')) if path.is_file()}
    live = p.CLIENT_DEFAULT / 'Data/patch-Z.MPQ'
    backup = Path('G:/EsteriaBackups/DarkfallenNative-patchZ')
    backup.mkdir(exist_ok=True)
    if not (backup / live.name).exists():
        shutil.copy2(live, backup / live.name)
    before = p.sha256(live)
    assert before == p.sha256(backup / live.name), 'patch-Z is not the backed-up original; restore it first'
    storm = p.Storm(p.DLL_DEFAULT)
    storm.replace_archive_entries(live, entries)
    assert live.stat().st_size < 0x80000000, live.stat().st_size
    handle = storm.open_archive(live)
    try:
        for name, blob in entries.items():
            assert storm.read(handle, name) == blob, name
    finally:
        storm.dll.SFileCloseArchive(handle)
    print('patch-Z updated:', len(entries), 'entries,', live.stat().st_size, 'bytes')


def catalog():
    """Rewrite only EsteriaDarkfallen.bin from the staged naming (no model/skin changes)."""
    data = plan()
    skin_files = {sex: ['%s%s\\DarkfallenSkin%02d.blp' % (TEX, sex.title(), c) for c in range(capacities(sex, data)[0])] for sex in SEXES}
    hair_files = {(sex, c): '%s%s\\Hair%02d.blp' % (TEX, sex.title(), c) for sex in SEXES for c in range(data[sex]['colors'])}
    blob, count = selection_catalog(data, hair_files, skin_files)
    (OUT / 'stage/catalogs/EsteriaDarkfallen.bin').write_bytes(blob)
    live = p.CLIENT_DEFAULT / 'EsteriaDarkfallen.bin'
    backup = Path('G:/EsteriaBackups/DarkfallenNative-catalog')
    backup.mkdir(exist_ok=True)
    if live.exists():
        shutil.copy2(live, backup / ('EsteriaDarkfallen-' + datetime.now().strftime('%H%M%S') + '.bin'))
    live.write_bytes(blob)
    print('Catalog rewritten:', count, 'records')


def install():
    """Matched install: archive, catalogs, native helper, server DBCs and character migration."""
    report = json.loads((OUT / 'stage.json').read_text())
    assert report['state'] == 'packaged_not_built_not_installed', report['state']
    running = subprocess.check_output(['tasklist', '/FO', 'CSV', '/NH'], text=True).lower()
    assert '"wow.exe"' not in running and '"wowclient64_d3d11.exe"' not in running, 'Close the client first'
    dll = OUT / 'native/EsteriaAppearance.dll'
    assert dll.is_file(), 'Build the native helper first'
    live = p.CLIENT_DEFAULT / k.LOCALE
    assert p.sha256(live) == report['archive_baseline'], 'Live archive changed since packaging'
    for name in ('EsteriaAppearance.bin', 'EsteriaAppearanceGeometry.bin'):
        assert digest((p.CLIENT_DEFAULT / name).read_bytes()) == report[name + ' baseline'], 'Catalog changed: ' + name
    pairs = [(live, OUT / 'client' / k.LOCALE), (p.CLIENT_DEFAULT / 'EsteriaAppearance.dll', dll)]
    for name in CATALOGS:
        pairs.append((p.CLIENT_DEFAULT / name, OUT / 'stage/catalogs' / name))
    for name in SERVER_TABLES:
        target = p.SERVER_DBC_ROOT / (name + '.dbc')
        assert digest(target.read_bytes()) == report['server_baseline'][name], 'Server DBC changed: ' + name
        pairs.append((target, OUT / 'stage/server' / (name + '.dbc')))
    backup = Path('G:/EsteriaBackups') / ('DarkfallenNative-' + datetime.now().strftime('%Y%m%d-%H%M%S'))
    for old, _ in pairs:
        if old.exists():
            target = backup / old.drive.replace(':', '') / Path(*old.parts[1:])
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(old, target)
            assert p.sha256(target) == p.sha256(old)
    appearance = subprocess.check_output(
        ['docker', 'exec', 'ac-database', 'sh', '-c', 'mysql -uroot -p"$MYSQL_ROOT_PASSWORD" acore_characters -e '
         '"select guid,race,gender,skin,face,hairStyle,hairColor,facialStyle from characters where race in (43,44)"'],
        text=True, stderr=subprocess.DEVNULL)
    (backup / 'darkfallen-characters.tsv').write_text(appearance, encoding='utf-8')
    for old, new in pairs:
        temporary = old.with_name(old.name + '.installing')
        shutil.copy2(new, temporary)
        temporary.replace(old)
        assert p.sha256(old) == p.sha256(new), 'Install verify failed: ' + str(old)
    report.update(state='installed', backup=str(backup))
    (OUT / 'stage.json').write_text(json.dumps(report, indent=2) + '\n')
    print('Installed; backup:', backup)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('stage', 'pack', 'install', 'patchz', 'catalog'))
    globals()[parser.parse_args().action]()
