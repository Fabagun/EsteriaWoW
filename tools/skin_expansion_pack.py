"""Consolidate the skin-expansion and female Tuskarr stages into one reviewable package.

Builds a copy of the live patch-enUS-Z.MPQ with every replaced entry, and gathers the loose catalogs, server
DBCs and the built native DLL beside it. Never touches the live client or server and installs nothing.
The racials stage is already live (Patch-Rv.MPQ is identical and its DBC entries are newer than that stage),
so it is deliberately not re-applied.
"""

import argparse
import hashlib
import json
from pathlib import Path, PureWindowsPath
import shutil

import skin_expansion as s
import tuskarr_female_pack as f

p = s.t.p
OUT = Path('G:/RetroPorterWork/consolidated-20261015')
NATIVE = Path('C:/Users/Zach/AppData/Local/Temp/claude/native-out/EsteriaAppearance.dll')
LOCALE = p.LOCALE_ARCHIVE_REL
CATALOGS = {'EsteriaAppearance.bin': f.STAGE, 'EsteriaAppearanceGeometry.bin': f.STAGE,
            'EsteriaTuskarr.bin': f.STAGE, 'EsteriaTuskarrTextures.bin': f.STAGE,
            'EsteriaDrakonid.bin': s.WORK / 'stage/catalogs', 'EsteriaTarasek.bin': s.WORK / 'stage/catalogs'}
SERVER = {'BarberShopStyle': s.WORK / 'stage/server'}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def replacements():
    """Entry key -> bytes, with the female stage's chained CharSections superseding the skin stage's."""
    entries = {}
    root = s.WORK / 'stage/client/DBFilesClient'
    entries[p.DBC_ROOT + 'BarberShopStyle.dbc'] = (root / 'BarberShopStyle.dbc').read_bytes()
    for path in sorted((f.STAGE / 'client-dbc').glob('*.dbc')):
        entries[p.DBC_ROOT + path.name] = path.read_bytes()
    entries[p.GLUE_ROOT + 'CharacterCreate.lua'] = (f.STAGE / 'CharacterCreate.lua').read_bytes()
    for base in (s.WORK / 'stage/assets', f.STAGE / 'assets'):
        for path in sorted(base.rglob('*')):
            if path.is_file():
                key = str(PureWindowsPath(path.relative_to(base)))
                assert key not in entries or entries[key] == path.read_bytes(), 'Conflicting asset: ' + key
                entries[key] = path.read_bytes()
    return entries


def check_chain():
    """The female stage must build on the skin stage, and both must build on today's live files."""
    skin_sections = (s.WORK / 'stage/client/DBFilesClient/CharSections.dbc').read_bytes()
    assert (f.BASELINE / 'client/CharSections.dbc').read_bytes() == skin_sections, 'CharSections chain broken'
    server = (s.WORK / 'stage/server/CharSections.dbc').read_bytes()
    assert (f.BASELINE / 'server/CharSections.dbc').read_bytes() == server, 'Server CharSections chain broken'
    assert (f.BASELINE / 'EsteriaAppearance.bin').read_bytes() == (
        s.WORK / 'stage/catalogs/EsteriaAppearance.bin').read_bytes(), 'Appearance catalog chain broken'
    files = p.ClientFiles(str(p.CLIENT_DEFAULT / 'Data'), 'enUS')
    try:
        for key in (p.DBC_ROOT + 'BarberShopStyle.dbc',):
            assert digest(files.find(key)[0]) == digest((s.WORK / 'baseline/client' / key.replace('\\', '/')).read_bytes()), key
        for name in f.TABLES:
            if name == 'CharSections':
                live = files.find(p.DBC_ROOT + name + '.dbc')[0]
                assert digest(live) == digest((s.WORK / 'baseline/client/DBFilesClient/CharSections.dbc').read_bytes())
                continue
            live = files.find(p.DBC_ROOT + name + '.dbc')[0]
            assert digest(live) == digest((f.BASELINE / 'client' / (name + '.dbc')).read_bytes()), 'Live changed: ' + name
        live = files.find(p.GLUE_ROOT + 'CharacterCreate.lua')[0]
        assert digest(live) == digest((f.BASELINE / 'CharacterCreate.lua').read_bytes()), 'Live Glue changed'
    finally:
        files.close()
    for name, base in (('EsteriaDrakonid.bin', s.WORK / 'baseline/catalogs'), ('EsteriaTarasek.bin', s.WORK / 'baseline/catalogs'),
                       ('EsteriaTuskarr.bin', f.BASELINE), ('EsteriaTuskarrTextures.bin', f.BASELINE),
                       ('EsteriaAppearanceGeometry.bin', f.BASELINE)):
        assert (p.CLIENT_DEFAULT / name).read_bytes() == (base / name).read_bytes(), 'Live catalog changed: ' + name
    assert digest((p.CLIENT_DEFAULT / 'EsteriaAppearance.bin').read_bytes()) == digest(
        (s.WORK / 'baseline/catalogs/EsteriaAppearance.bin').read_bytes()), 'Live appearance catalog changed'


def pack():
    check_chain()
    entries = replacements()
    live = p.CLIENT_DEFAULT / LOCALE
    target = OUT / 'client' / LOCALE
    assert not target.exists(), 'Package already exists: ' + str(OUT)
    target.parent.mkdir(parents=True, exist_ok=True)
    before = p.sha256(live)
    shutil.copy2(live, target)
    assert p.sha256(target) == before
    storm = p.Storm(p.DLL_DEFAULT)
    handle = storm.open_archive(live)
    try:
        existing = {name.lower() for name, *_ in storm.list_files(handle)}
        old = {key: digest(storm.read(handle, key)) for key in entries if key.lower() in existing}
    finally:
        storm.dll.SFileCloseArchive(handle)
    storm.replace_archive_entries(target, entries)
    if target.stat().st_size >= 0x80000000:
        compressed = target.with_suffix('.compressed')
        p.rebuild_archive_streaming(storm, target, compressed, compress=True)
        import os
        os.replace(compressed, target)
    assert target.stat().st_size < 0x80000000, 'Classic MPQ boundary exceeded'
    handle = storm.open_archive(target)
    try:
        names = {name.lower() for name, *_ in storm.list_files(handle)}
        for key, blob in entries.items():
            assert storm.read(handle, key) == blob, key
        assert len(names) == len(existing) + sum(key.lower() not in existing for key in entries)
        assert existing <= names
    finally:
        storm.dll.SFileCloseArchive(handle)
    assert p.sha256(live) == before, 'Live archive changed while packaging'
    loose = {}
    for name, root in CATALOGS.items():
        data = (root / name).read_bytes()
        (OUT / 'client' / name).write_bytes(data)
        loose[name] = digest(data)
    dll = NATIVE.read_bytes()
    (OUT / 'client/EsteriaAppearance.dll').write_bytes(dll)
    server = {}
    for directory, name in ((f.STAGE / 'server-dbc', None), (s.WORK / 'stage/server', 'BarberShopStyle')):
        for path in sorted(directory.glob('*.dbc')):
            if name and path.stem != name:
                continue
            (OUT / 'server').mkdir(exist_ok=True)
            (OUT / 'server' / path.name).write_bytes(path.read_bytes())
            server[path.name] = digest(path.read_bytes())
    report = {'state': 'consolidated_staged_not_installed', 'installed': False, 'live_accepted': False,
              'archive': {'path': str(LOCALE), 'baseline_sha256': before, 'sha256': p.sha256(target),
                          'bytes': target.stat().st_size, 'replaced_entries': sum(k in old for k in entries),
                          'added_entries': sum(k not in old for k in entries), 'readback_verified': True,
                          'baseline_entry_sha256': old},
              'entries': {key: digest(blob) for key, blob in entries.items()},
              'loose_client_files': {**loose, 'EsteriaAppearance.dll': digest(dll)},
              'server_dbcs': server,
              'install_targets': {'client': str(p.CLIENT_DEFAULT), 'server_dbc': 'modules/mod-custom-server/data/dbc/retroported-races'},
              'racials': 'already live; not re-applied'}
    (OUT / 'report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8', newline='\n')
    print('Packaged', len(entries), 'entries;', report['archive']['replaced_entries'], 'replaced,',
          report['archive']['added_entries'], 'added;', target.stat().st_size, 'bytes')


if __name__ == '__main__':
    argparse.ArgumentParser(description=__doc__).parse_args()
    pack()
