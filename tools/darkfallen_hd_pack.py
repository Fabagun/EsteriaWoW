"""Darkfallen HD v1: Retail HD Blood Elf bodies renamed to Darkfallen, with the supplied skins and red eyes.

Consumes the pinned acquisition in G:/RetroPorterWork/darkfallen-hd (see darkfallen_hd.py). Scope of v1:
5 supplied skins, red eyes, all retail hair styles with the first ten hair colours, no face/earring/facial
hair choices. Stages and packages a copy of the live locale archive; `install` is separate and guarded.
"""
import argparse
import hashlib
import json
import shutil
import struct
import subprocess
from datetime import datetime
from pathlib import Path

from PIL import Image

import darkfallen_hd as h
import retroported_race_pack as p
from cars_mount_pack import order_charsections_entry
from wotlkconv.blp import Blp, convert_blp
from wotlkconv.blp.bcn import encode_bc1, encode_bc3
from wotlkconv.blp.image import Image as BlpImage
from wotlkconv.options import Options

SRC = Path('C:/Users/Zach/wow.export/custom/Darkfallen')
OUT = Path('G:/RetroPorterWork/darkfallen-hd-pack')
REPO = Path(__file__).resolve().parents[1]
SQL = REPO / 'data/sql/updates/pending_db_characters/rev_20261016100000000_darkfallen_hd.sql'
LOCALE = p.LOCALE_ARCHIVE_REL
RACES = (43, 44)
SEXES = {'male': 0, 'female': 1}
MODEL_IDS = {'male': 3658, 'female': 3659}
EYE_NUMBER = 19
SKINS = 5
BASE = 'Character\\DarkfallenHD\\'
TABLES = ('CharSections', 'CharHairGeosets', 'CharacterFacialHairStyles', 'BarberShopStyle')
SERVER_TABLES = ('CharSections', 'BarberShopStyle')
# The client's race model table names these exact paths, so the HD model replaces the files in place.
MODEL_BASE = 'Character\\Darkfallen\\'
EYE_GEOSET = 3301


def digest(blob):
    return hashlib.sha256(blob).hexdigest()


def png_to_blp(path):
    image = Image.open(path).convert('RGBA')
    base = BlpImage.from_rgba(image.width, image.height, image.tobytes())
    images = base.mip_chain(None)
    if base.is_opaque():
        payloads, alpha_type, alpha_size = [encode_bc1(i.data, i.width, i.height) for i in images], 0, 0
    else:
        payloads, alpha_type, alpha_size = [encode_bc3(i.data, i.width, i.height) for i in images], 7, 8
    blob = Blp.from_images(images, compression=2, alpha_type=alpha_type, alpha_size=alpha_size,
                           payloads=payloads).serialize()
    checked = Blp.parse(blob)
    for level in range(checked.mip_count):
        checked.decode_level(level)
    return blob


def blank_blp():
    base = BlpImage.from_rgba(4, 4, bytes(4 * 4 * 4))
    images = base.mip_chain(None)
    return Blp.from_images(images, compression=2, alpha_type=7, alpha_size=8,
                           payloads=[encode_bc3(i.data, i.width, i.height) for i in images]).serialize()


def retail_blp(path, name):
    blob, result = convert_blp(Path(path).read_bytes(), name, Options())
    assert blob and result.ok, result.as_dict()
    return blob


def sex_art(sex):
    return SRC / ('bloodelf%s_hd_texture_%%d.png' % sex)


# --- models ---------------------------------------------------------------------------------------

def build_model(sex, inventory):
    """Rename to Darkfallen, repoint textures, drop unresolvable layers; returns {mpq key: bytes}."""
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
    directory = BASE + title + '\\'
    model = visual.read_player_model(work / (new + '.m2'))
    tracks.embed(model, work, new)
    skin = parse_skin((work / (new + '00.skin')).read_bytes())
    slot_of_geoset = {}
    for batch in skin.batches:
        fields = struct.unpack_from('<BbHHHhHHHHHHH', bytes(batch))
        geoset = struct.unpack_from('<H', skin.submeshes[fields[3]])[0]
        slot_of_geoset.setdefault(geoset, set()).add(model.texture_combos[fields[9]])
    eye_slot = next(iter(slot_of_geoset[EYE_GEOSET]))
    files = {}
    for slot, texture in enumerate(model.textures):
        if texture['filename']:
            name = Path(texture['filename'].replace('\\', '/')).name.replace(old, new)
            texture['filename'] = directory + name
            files[directory + name] = ('retail', Path(texture['filename']).name)
        elif slot == eye_slot:
            texture['type'], texture['filename'] = 0, directory + 'DarkfallenEyes.blp'
        elif texture['type'] in (9, 11):
            texture['type'], texture['filename'] = 0, BASE + 'Blank.blp'
    blank_slots = {i for i, t in enumerate(model.textures) if t['filename'] == BASE + 'Blank.blp'}
    keep = []
    for batch in skin.batches:
        fields = struct.unpack_from('<BbHHHhHHHHHHH', bytes(batch))
        slots = {model.texture_combos[fields[9] + k] for k in range(fields[8])}
        geoset = struct.unpack_from('<H', skin.submeshes[fields[3]])[0]
        # geoset 1507 keeps its first (cloak) layer; every other batch that needs a blanked slot is dropped
        if slots & blank_slots and geoset != 1507:
            continue
        keep.append(batch)
    removed = len(skin.batches) - len(keep)
    skin.batches = keep
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
    model_dir = MODEL_BASE + title + '\\'
    entries = {model_dir + new + '.m2': payload, model_dir + new + '00.skin': write_skin(skin)}
    for path in sorted(work.glob(new + '*.anim')):
        entries[model_dir + path.name] = path.read_bytes()
    raw = h.ROOT / 'raw'
    for key, (_, original) in files.items():
        stem = original.replace(new, old)
        match = next(r for r in inventory['assets'].values() if (r['logical_name'] or '').lower().endswith(stem.lower()))
        entries[key] = retail_blp(match['path'], match['logical_name'])
    entries[directory + 'DarkfallenEyes.blp'] = png_to_blp(sex_art(sex) .with_name(sex_art(sex).name % EYE_NUMBER))
    return entries, {'batches_removed': removed, 'eye_slot': eye_slot, 'blank_slots': sorted(blank_slots)}


# --- DBCs -----------------------------------------------------------------------------------------

def hair_plan():
    plan = h.hair_plan()
    return {sex: {'styles': d['styles'], 'colors': len(d['colors']),
                  'files': {k: v for k, v in d['files'].items()}} for sex, d in plan.items()}


class Rows:
    """Owned-row replacement for one table: deletes the Darkfallen rows, then reuses their IDs."""

    def __init__(self, blob, races, race_at):
        self.table = p.RawWdbc(blob)
        self.pool = bytearray(self.table.strings)
        self.race_at = race_at
        self.old = [r for r in self.table.records if p._value(r, race_at) in races]
        self.rows = [r for r in self.table.records if p._value(r, race_at) not in races]
        self.free = iter(sorted(p._value(r, 0) for r in self.old))
        self.top = max(p._value(r, 0) for r in self.table.records)

    def new_id(self):
        freed = next(self.free, None)
        if freed is None:  # the replacement is larger than the retired rows: continue above every existing ID
            self.top += 1
            return self.top
        return freed

    def string(self, row, field, value):
        return p._set_string(row, field, self.pool, value) if value else p._replace(row, field * 4, 4, 0)

    def build(self):
        return self.table.build(self.rows, bytes(self.pool))


def edit_sections(blob, plan, skins, hair_path):
    t = Rows(blob, RACES, 4)
    templates = {}
    for r in t.old:
        templates.setdefault((p._value(r, 8), p._value(r, 12)), r)
    for race in RACES:
        for sex_name, sex in SEXES.items():
            data = plan[sex_name]
            styles, colors = len(data['styles']), data['colors']

            def add(kind, variation, color, tex1=''):
                row = p._replace(templates[(sex, kind)], 4, 4, race)
                row = p._replace(row, 0, 4, t.new_id())
                row = p._replace(row, 32, 4, variation)
                row = p._replace(row, 36, 4, color)
                row = t.string(row, 4, tex1)
                row = t.string(row, 5, '')
                row = t.string(row, 6, '')
                t.rows.append(row)

            for color in range(len(skins[sex_name])):
                add(0, 0, color, skins[sex_name][color])
                add(1, 0, color)
                add(4, 0, color)
            if sex == 0:
                for color in range(colors):
                    add(2, 0, color)
            for style in range(styles):
                for color in range(colors):
                    add(3, style, color, hair_path(sex_name, color))
    return order_charsections_entry(p.DBC_ROOT + 'CharSections.dbc', t.build())


def edit_hair_geosets(blob, plan):
    t = Rows(blob, RACES, 4)
    template = t.old[0]
    for race in RACES:
        for sex_name, sex in SEXES.items():
            for variation, (_, geoset) in enumerate(plan[sex_name]['styles']):
                row = p._replace(template, 0, 4, t.new_id())
                for offset, value in ((4, race), (8, sex), (12, variation), (16, geoset), (20, 0)):
                    row = p._replace(row, offset, 4, value)
                t.rows.append(row)
    return t.build()


def edit_facial(blob):
    """Facial hair is not part of v1: keep exactly one 'none' variation per race/sex."""
    table = p.RawWdbc(blob)
    keep, seen = [], set()
    for r in table.records:
        race, sex, variation = (p._value(r, o) for o in (0, 4, 8))
        if race in RACES:
            if variation != 0 or (race, sex) in seen:
                continue
            seen.add((race, sex))
            r = r[:12] + bytes(len(r) - 12)
        keep.append(r)
    assert len(seen) == 4, seen
    return table.build(keep, table.strings)


def edit_barber(blob, plan):
    t = Rows(blob, RACES, 148)
    templates = {}
    for r in t.old:
        templates.setdefault((p._value(r, 152), p._value(r, 4)), r)
    for race in RACES:
        for sex_name, sex in SEXES.items():
            for variation, (name, _) in enumerate(plan[sex_name]['styles']):
                row = p._replace(templates[(sex, 0)], 0, 4, t.new_id())
                row = p._replace(row, 148, 4, race)
                row = p._replace(row, 152, 4, sex)
                row = p._replace(row, 156, 4, variation)
                row = t.string(row, 2, name)
                t.rows.append(row)
    return t.build()


def edit_models(blob):
    table = p.RawWdbc(blob)
    pool, rows = bytearray(table.strings), []
    wanted = {MODEL_IDS[s]: BASE + s.title() + '\\Darkfallen' + s.title() + '.m2' for s in MODEL_IDS}
    for r in table.records:
        if p._value(r, 0) in wanted:
            r = p._set_string(r, 2, pool, wanted[p._value(r, 0)])
        rows.append(r)
    return table.build(rows, bytes(pool))


def transforms(plan, skins, hair_path):
    return {'CharSections': lambda b: edit_sections(b, plan, skins, hair_path),
            'CharHairGeosets': lambda b: edit_hair_geosets(b, plan),
            'CharacterFacialHairStyles': edit_facial,
            'BarberShopStyle': lambda b: edit_barber(b, plan)}


# --- actions --------------------------------------------------------------------------------------

def stage():
    assert not (OUT / 'stage.json').exists(), 'Already staged: ' + str(OUT)
    inventory = json.loads((h.ROOT / 'reports/inventory.json').read_text())
    hair = json.loads((h.ROOT / 'reports/hair.json').read_text())
    plan = hair_plan()
    entries, model_report = {}, {}
    for sex in SEXES:
        entries_sex, model_report[sex] = build_model(sex, inventory)
        entries.update(entries_sex)
    entries[BASE + 'Blank.blp'] = blank_blp()
    skins = {}
    for sex in SEXES:
        skins[sex] = []
        for color in range(SKINS):
            key = '%s%s\\DarkfallenSkin%02d.blp' % (BASE, sex.title(), color)
            entries[key] = png_to_blp(sex_art(sex).with_name(sex_art(sex).name % (color + 1)))
            skins[sex].append(key)
    hair_files = {}
    for row in hair['assets'].values():
        key = '%s%s\\Hair%02d.blp' % (BASE, row['sex'].title(), row['color'])
        entries[key] = retail_blp(row['path'], row['logical_name'])
        hair_files[(row['sex'], row['color'])] = key
    hair_path = lambda sex, color: hair_files[(sex, color)]

    files = p.ClientFiles(str(p.CLIENT_DEFAULT / 'Data'), 'enUS')
    baselines, dbcs = {}, {}
    try:
        for name in TABLES:
            baselines[name] = files.find(p.DBC_ROOT + name + '.dbc')[0]
    finally:
        files.close()
    work = transforms(plan, skins, hair_path)
    for name in TABLES:
        dbcs[name] = work[name](baselines[name])
    server, server_baseline = {}, {}
    for name in SERVER_TABLES:
        blob = (p.SERVER_DBC_ROOT / (name + '.dbc')).read_bytes()
        server_baseline[name] = digest(blob)
        server[name] = work[name](blob)
    stage_root = OUT / 'stage'
    for key, blob in entries.items():
        path = stage_root / 'assets' / key.replace('\\', '/')
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(blob)
    for name, blob in dbcs.items():
        path = stage_root / 'client' / (name + '.dbc')
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(blob)
    for name, blob in server.items():
        path = stage_root / 'server' / (name + '.dbc')
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(blob)
    report = {'state': 'staged_not_installed', 'models': model_report,
              'styles': {s: [n for n, _ in d['styles']] for s, d in plan.items()},
              'hair_colors': {s: d['colors'] for s, d in plan.items()},
              'client_baseline': {k: digest(v) for k, v in baselines.items()},
              'server_baseline': server_baseline,
              'assets': {k: digest(v) for k, v in sorted(entries.items())}}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'stage.json').write_text(json.dumps(report, indent=2) + '\n')
    print('Staged', len(entries), 'assets;', len(dbcs), 'client and', len(server), 'server DBCs')


def sql():
    plan = hair_plan()
    male, female = len(plan['male']['styles']) - 1, len(plan['female']['styles']) - 1
    colors = plan['male']['colors'] - 1
    SQL.write_text(
        '-- Darkfallen HD: five skins, no face/facial choices, new hair style and colour counts.\n'
        'UPDATE `characters` SET `skin` = LEAST(`skin`, %d), `face` = 0, `facialStyle` = 0,\n'
        '    `hairStyle` = LEAST(`hairStyle`, IF(`gender` = 0, %d, %d)), `hairColor` = LEAST(`hairColor`, %d)\n'
        'WHERE `race` IN (43, 44);\n' % (SKINS - 1, male, female, colors), encoding='utf-8', newline='\n')
    print('Wrote', SQL)


def pack():
    report = json.loads((OUT / 'stage.json').read_text())
    stage_root = OUT / 'stage'
    live = p.CLIENT_DEFAULT / LOCALE
    package = OUT / 'client' / LOCALE
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
    report.update(state='packaged_not_installed', archive_baseline=before, archive=p.sha256(package),
                  archive_bytes=package.stat().st_size)
    (OUT / 'stage.json').write_text(json.dumps(report, indent=2) + '\n')
    print('Packaged', len(entries), 'entries;', package.stat().st_size, 'bytes')


def install():
    report = json.loads((OUT / 'stage.json').read_text())
    assert report['state'] == 'packaged_not_installed', report['state']
    running = subprocess.check_output(['tasklist', '/FO', 'CSV', '/NH'], text=True).lower()
    assert '"wow.exe"' not in running and '"wowclient64_d3d11.exe"' not in running, 'Close the client first'
    live = p.CLIENT_DEFAULT / LOCALE
    assert p.sha256(live) == report['archive_baseline'], 'Live archive changed since packaging'
    pairs = [(live, OUT / 'client' / LOCALE)]
    for name in SERVER_TABLES:
        target = p.SERVER_DBC_ROOT / (name + '.dbc')
        assert digest(target.read_bytes()) == report['server_baseline'][name], 'Server DBC changed: ' + name
        pairs.append((target, OUT / 'stage/server' / (name + '.dbc')))
    backup = Path('G:/EsteriaBackups') / ('DarkfallenHD-' + datetime.now().strftime('%Y%m%d-%H%M%S'))
    for old, _ in pairs:
        target = backup / old.drive.replace(':', '') / Path(*old.parts[1:])
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(old, target)
        assert p.sha256(target) == p.sha256(old)
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
    parser.add_argument('action', choices=('stage', 'sql', 'pack', 'install'))
    globals()[parser.parse_args().action]()
