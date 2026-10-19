"""Stage extra skins for Human, Night Elf, High Elf and replace the Darkfallen skins.

Source art: C:/Users/Zach/wow.export/custom/{Darkfallen,High Elf,Human,Night Elf} (HD Blood Elf-layout
PNGs; texture_1..5 are 2048x1024 body atlases, texture_18/19 are 256x128 glow-eye sheets).

* Human / Night Elf / High Elf: new skin colours are appended after the highest existing colour, with
  cloned face/underwear rows. Existing colours and saved characters are untouched.
* Darkfallen (races 43/44): colours 0..4 keep their rows and file names but get the new art; colour 5 has
  no replacement and is removed, with a characters migration (skin 5 -> 4).

Stages only: the result is a copy of the live patch-enUS-Z.MPQ, two DBCs and a SQL file under OUT.
`install` is separate, guarded, and backs up everything it replaces.
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
from wotlkconv.blp import Blp
from wotlkconv.blp.bcn import encode_bc1, encode_bc3
from wotlkconv.blp.image import Image as BlpImage

import retroported_race_pack as p
from cars_mount_pack import Storm, order_charsections_entry

SRC = Path('C:/Users/Zach/wow.export/custom')
OUT = Path('G:/RetroPorterWork/skin-additions')
REPO = Path(__file__).resolve().parents[1]
SQL = REPO / 'data/sql/updates/pending_db_characters/rev_20261016000000000_darkfallen_skins.sql'
LOCALE = p.LOCALE_ARCHIVE_REL
CS = p.DBC_ROOT + 'CharSections.dbc'
FIRST_ID = 1119300  # above every allocation.json range; asserted free against both tables

# folder -> (CharSections races, art prefix, eye sheet used for new skins or None)
ADD = {'Human': ((1,), 'human', None), 'Night Elf': ((4,), 'nightelf', None),
       'High Elf': ((13,), 'bloodelf', 19)}
DARKFALLEN = (43, 44)
SEX = {'male': 0, 'female': 1}
EYE_DARKFALLEN = 19


def digest(blob):
    return hashlib.sha256(blob).hexdigest()


def png_to_blp(path):
    """DXT1 when fully opaque, otherwise DXT5; full mip chain."""
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
    assert (checked.width, checked.height) == (image.width, image.height)
    for level in range(checked.mip_count):
        checked.decode_level(level)
    return blob


def sheets(folder):
    """{(sex, texture number): path}"""
    found = {}
    for path in sorted((SRC / folder).glob('*.png')):
        name = path.stem
        sex = 'female' if 'female_' in name else 'male'
        found[(SEX[sex], int(name.rsplit('_', 1)[1]))] = path
    return found


def key(*parts):
    return '\\'.join(parts)


def edit(blob, server):
    """Apply every change to one CharSections table; returns (blob, assets, plan)."""
    table = p.RawWdbc(blob)
    pool = bytearray(table.strings)
    rows = list(table.records)
    used = {p._value(r, 0) for r in rows}
    assert FIRST_ID > max(used), 'Allocation is not above every existing CharSections ID'
    new_id = iter(range(FIRST_ID, FIRST_ID + 5000))
    assets, plan = {}, {}

    # --- additions -------------------------------------------------------------------------------
    for folder, (races, _prefix, eye) in ADD.items():
        art = sheets(folder)
        for race in races:
            for sex in (0, 1):
                numbers = sorted(n for s, n in art if s == sex and n <= 5)
                if not numbers:
                    continue
                own = [r for r in rows if p._value(r, 4) == race and p._value(r, 8) == sex]
                skin_colors = [p._value(r, 36) for r in own if p._value(r, 12) == 0]
                first = max(skin_colors) + 1
                templates = [r for r in own if p._value(r, 36) == min(skin_colors) and p._value(r, 12) in (0, 1, 4)]
                assert any(p._value(r, 12) == 0 for r in templates)
                stem = key('Character', 'EsteriaSkins', folder.replace(' ', ''), 'Female' if sex else 'Male')
                eye_key = None
                if eye:
                    eye_key = key(stem, folder.replace(' ', '') + ('Female' if sex else 'Male') + 'Eyes.blp')
                    assets[eye_key] = png_to_blp(art[(sex, eye)])
                for offset, number in enumerate(numbers):
                    color = first + offset
                    assert not any(p._value(r, 36) == color and p._value(r, 12) == 0 for r in own)
                    skin_key = key(stem, folder.replace(' ', '') + ('Female' if sex else 'Male') + 'Skin%02d.blp' % color)
                    assets[skin_key] = png_to_blp(art[(sex, number)])
                    for template in templates:
                        row = p._replace(template, 0, 4, next(new_id))
                        row = p._replace(row, 36, 4, color)
                        if p._value(template, 12) == 0:
                            row = p._set_string(row, 4, pool, skin_key)
                            if eye_key:
                                row = p._set_string(row, 5, pool, eye_key)
                        rows.append(row)
                    plan[(race, sex, color)] = 'texture_%d' % number

    # --- Darkfallen replacement ------------------------------------------------------------------
    for race in DARKFALLEN:
        for sex in (0, 1):
            names = sheets('Darkfallen')
            own = [r for r in rows if p._value(r, 4) == race and p._value(r, 8) == sex]
            skins = sorted((p._value(r, 36), r) for r in own if p._value(r, 12) == 0)
            assert [c for c, _ in skins] == [0, 1, 2, 3, 4, 5], 'Unexpected Darkfallen skin colours'
            # New paths, not the old keys: patch-Z.MPQ also holds those and can win the load order.
            stem = key('Character', 'EsteriaSkins', 'Darkfallen', 'Female' if sex else 'Male')
            eye_key = key(stem, 'DarkfallenEyes.blp')
            assets[eye_key] = png_to_blp(names[(sex, EYE_DARKFALLEN)])
            changed = {}
            for color, row in skins[:5]:
                skin_key = key(stem, 'DarkfallenSkin%02d.blp' % color)
                assets[skin_key] = png_to_blp(names[(sex, color + 1)])
                row = p._set_string(row, 4, pool, skin_key)
                changed[id(skins[color][1])] = p._set_string(row, 5, pool, eye_key)
            rows = [changed.get(id(r), r) for r in rows]
            own = [r for r in rows if p._value(r, 4) == race and p._value(r, 8) == sex]
            drop = {id(r) for r in own if p._value(r, 36) == 5 and p._value(r, 12) in (0, 1, 4)}
            assert sum(p._value(r, 12) == 0 for r in own if id(r) in drop) == 1
            rows = [r for r in rows if id(r) not in drop]
    return order_charsections_entry(CS, table.build(rows, bytes(pool))), assets, plan


def stage():
    target = OUT / 'stage'
    assert not target.exists(), 'Already staged: ' + str(target)
    files = p.ClientFiles(str(p.CLIENT_DEFAULT / 'Data'), 'enUS')
    try:
        client, provider = files.find(CS)
    finally:
        files.close()
    server = (p.SERVER_DBC_ROOT / 'CharSections.dbc').read_bytes()
    new_client, assets, plan = edit(client, False)
    new_server, server_assets, _ = edit(server, True)
    assert server_assets.keys() == assets.keys()
    for name, blob in ((target / 'client/CharSections.dbc', new_client), (target / 'server/CharSections.dbc', new_server)):
        name.parent.mkdir(parents=True, exist_ok=True)
        name.write_bytes(blob)
    for name, blob in assets.items():
        path = target / 'assets' / name.replace('\\', '/')
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(blob)
    report = {'state': 'staged_not_installed', 'provider': str(provider), 'client_baseline': digest(client),
              'server_baseline': digest(server), 'client': digest(new_client), 'server': digest(new_server),
              'assets': {k: digest(v) for k, v in sorted(assets.items())},
              'new_colors': {'%d/%d/%d' % k: v for k, v in sorted(plan.items())}}
    (OUT / 'stage.json').write_text(json.dumps(report, indent=2) + '\n')
    print('Staged', len(assets), 'textures;', len(plan), 'new skin colours')


def pack():
    stage_root = OUT / 'stage'
    report = json.loads((OUT / 'stage.json').read_text())
    live = p.CLIENT_DEFAULT / LOCALE
    package = OUT / 'client' / LOCALE
    assert not package.exists(), 'Package already exists'
    package.parent.mkdir(parents=True, exist_ok=True)
    before = p.sha256(live)
    shutil.copy2(live, package)
    entries = {CS: (stage_root / 'client/CharSections.dbc').read_bytes()}
    for path in sorted((stage_root / 'assets').rglob('*.blp')):
        entries[str(path.relative_to(stage_root / 'assets')).replace('/', '\\')] = path.read_bytes()
    storm = p.Storm(p.DLL_DEFAULT)
    storm.replace_archive_entries(package, entries)
    assert package.stat().st_size < 0x80000000, 'Classic MPQ boundary exceeded'
    handle = storm.open_archive(package)
    try:
        for name, blob in entries.items():
            assert storm.read(handle, name) == blob, name
    finally:
        storm.dll.SFileCloseArchive(handle)
    assert p.sha256(live) == before, 'Live archive changed while packaging'
    shutil.copy2(stage_root / 'server/CharSections.dbc', OUT / 'CharSections.server.dbc')
    report.update(state='packaged_not_installed', archive_baseline=before, archive=p.sha256(package))
    (OUT / 'stage.json').write_text(json.dumps(report, indent=2) + '\n')
    print('Packaged', len(entries), 'entries into', package)


def sql():
    SQL.write_text('-- Darkfallen skins were replaced; the sixth skin (5) no longer exists.\n'
                   'UPDATE `characters` SET `skin` = 4 WHERE `race` IN (43, 44) AND `skin` = 5;\n',
                   encoding='utf-8', newline='\n')
    print('Wrote', SQL)


def install():
    """Guarded: client must be closed and live files unchanged since pack; backs up first."""
    report = json.loads((OUT / 'stage.json').read_text())
    assert report['state'] == 'packaged_not_installed', report['state']
    running = subprocess.check_output(['tasklist', '/FO', 'CSV', '/NH'], text=True).lower()
    assert '"wow.exe"' not in running, 'Close the client first'
    live = p.CLIENT_DEFAULT / LOCALE
    server = p.SERVER_DBC_ROOT / 'CharSections.dbc'
    assert p.sha256(live) == report['archive_baseline'], 'Live archive changed since packaging'
    assert digest(server.read_bytes()) == report['server_baseline'], 'Server DBC changed since staging'
    backup = Path('G:/EsteriaBackups') / ('SkinAdditions-' + datetime.now().strftime('%Y%m%d-%H%M%S'))
    pairs = ((live, OUT / 'client' / LOCALE), (server, OUT / 'CharSections.server.dbc'))
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
    parser.add_argument('action', choices=('stage', 'pack', 'sql', 'install'))
    globals()[parser.parse_args().action]()
