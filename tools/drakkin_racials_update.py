"""Stage and install the Kobold -> Drakkin rename plus the Drakkin/Drakonid racial spells.

The first Drakkin install shipped under the old name, so this is an in-place update of the live
client archives (never a regeneration):

* ChrRaces.dbc: every "Kobold" string of races 66/67 becomes "Drakkin", the client file strings
  become DrakkinAlliance / DrakkinHorde.
* Spell.dbc: the racial rows from drakkin_drakonid_racials.py, merged into whatever the client ships.
* Glue Lua: the Kobold tokens become Drakkin tokens.
* Portraits: every Kobold* portrait entry is also stored under its Drakkin name (old entries stay).

    python tools/drakkin_racials_update.py stage      # builds copies of the live archives
    python tools/drakkin_racials_update.py install    # hash-verified backup, then swap them in
    python tools/drakkin_racials_update.py rollback   # restore the backed-up archives
"""

import argparse
from datetime import datetime
import json
from pathlib import Path
import re
import shutil
import subprocess

from lupa.lua51 import LuaRuntime

import drakkin_drakonid_racials as racials
import retroported_race_pack as p
import sethrak_race_pack as tables_lib

STAGE = Path('G:/RetroPorterWork/kobold/racials-20261014')
BACKUPS = Path('G:/EsteriaBackups')
RACES = (66, 67)
ARCHIVES = (p.GLOBAL_ARCHIVE_REL, p.LOCALE_ARCHIVE_REL)
TOKEN_FIELD = 11


def rename(text):
    return text.replace('Kobold', 'Drakkin').replace('KOBOLD', 'DRAKKIN').replace('kobold', 'drakkin')


def rename_chr_races(data):
    table = p.RawWdbc(data)
    pool, rows = bytearray(table.strings), []
    for row in table.records:
        if p._value(row, 0) in RACES:
            for field in range(len(row) // 4):
                offset = p._value(row, field * 4)
                if 0 < offset < len(table.strings):
                    text = p._string(table.strings, offset).decode('utf-8', 'replace')
                    if 'Kobold' in text:
                        row = p._set_string(row, field, pool, rename(text))
        rows.append(row)
    result = table.build(rows, bytes(pool))
    check = p.RawWdbc(result)
    for row in check.records:
        if p._value(row, 0) in RACES:
            assert p._string(check.strings, p._value(row, TOKEN_FIELD * 4)).decode().startswith('Drakkin')
    return result


def portrait_names(files):
    storm = p.Storm(p.DLL_DEFAULT)
    names = set()
    for archive in files.chain:
        handle = storm.open_archive(Path(archive))
        try:
            try:
                listing = storm.read(handle, '(listfile)').decode('utf-8', 'replace').splitlines()
            except Exception:
                continue
        finally:
            storm.dll.SFileCloseArchive(handle)
        names.update(name for name in listing if re.match(
            r'Interface\\(CharacterFrame|Glues)\\.*Kobold(Alliance|Horde)', name, re.I))
    return sorted(names)


def build_changes(files):
    changes = {p.DBC_ROOT + 'ChrRaces.dbc': rename_chr_races(files.find(p.DBC_ROOT + 'ChrRaces.dbc')[0]),
               p.DBC_ROOT + 'Spell.dbc': racials.merge_spell_table(files.find(p.DBC_ROOT + 'Spell.dbc')[0])}
    compile_chunk = LuaRuntime().eval('function(s) local f,e=loadstring(s); assert(f,e); end')
    for name in tables_lib.GLUE:
        text = files.find(p.GLUE_ROOT + name)[0].decode('utf-8-sig')
        updated = rename(text)
        if updated != text:
            compile_chunk(updated)
            changes[p.GLUE_ROOT + name] = updated.encode()
    for name in portrait_names(files):
        changes[rename(name)] = files.find(name)[0]
    return changes


def stage():
    assert not STAGE.exists(), 'Review the existing stage before regenerating'
    STAGE.mkdir(parents=True)
    files = p.ClientFiles(str(p.CLIENT_DEFAULT / 'Data'), 'enUS')
    try:
        changes = build_changes(files)
    finally:
        files.close()
    storm = p.Storm(p.DLL_DEFAULT)
    report = {'changes': sorted(changes), 'baseline': {}, 'staged': {}}
    for relative in ARCHIVES:
        live, target = p.CLIENT_DEFAULT / relative, STAGE / 'client' / relative
        report['baseline'][str(relative)] = p.sha256(live)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(live, target)
        storm.replace_archive_entries(target, changes)
        handle = storm.open_archive(target)
        try:
            for key, blob in changes.items():
                assert storm.read(handle, key) == blob, key
        finally:
            storm.dll.SFileCloseArchive(handle)
        assert p.sha256(live) == report['baseline'][str(relative)], 'Live archive changed while staging'
        report['staged'][str(relative)] = p.sha256(target)
        print('STAGED AND READ BACK', relative, flush=True)
    (STAGE / 'report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8', newline='\n')
    print('STAGED', len(changes), 'entries', flush=True)


def preflight():
    report = json.loads((STAGE / 'report.json').read_text(encoding='utf-8'))
    processes = subprocess.check_output(['tasklist', '/FO', 'CSV', '/NH'], text=True).lower()
    assert 'wow.exe' not in processes, 'Close the game client first'
    for relative in ARCHIVES:
        assert p.sha256(p.CLIENT_DEFAULT / relative) == report['baseline'][str(relative)], \
            'Live archive changed since staging: ' + str(relative)
        assert p.sha256(STAGE / 'client' / relative) == report['staged'][str(relative)], 'Staged archive changed'
    return report


def install():
    report = preflight()
    root = BACKUPS / ('Drakkin-racials-' + datetime.now().strftime('%Y%m%d-%H%M%S'))
    for relative in ARCHIVES:
        target = root / 'client' / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p.CLIENT_DEFAULT / relative, target)
        assert p.sha256(target) == report['baseline'][str(relative)], 'Backup mismatch'
    (root / 'report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8', newline='\n')
    (STAGE / 'last-backup.txt').write_text(str(root), encoding='utf-8')
    try:
        for relative in ARCHIVES:
            live = p.CLIENT_DEFAULT / relative
            temporary = live.with_suffix(live.suffix + '.drakkin-next')
            assert not temporary.exists(), 'Prior incomplete copy needs review'
            shutil.copy2(STAGE / 'client' / relative, temporary)
            assert p.sha256(temporary) == report['staged'][str(relative)]
            temporary.replace(live)
            assert p.sha256(live) == report['staged'][str(relative)]
    except Exception:
        restore(root, report)
        raise
    print('INSTALLED; backup', root, flush=True)


def restore(root, report):
    for relative in ARCHIVES:
        shutil.copy2(root / 'client' / relative, p.CLIENT_DEFAULT / relative)
        assert p.sha256(p.CLIENT_DEFAULT / relative) == report['baseline'][str(relative)]


def rollback():
    root = Path((STAGE / 'last-backup.txt').read_text(encoding='utf-8'))
    restore(root, json.loads((root / 'report.json').read_text(encoding='utf-8')))
    print('RESTORED from', root, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('stage', 'install', 'rollback'))
    {'stage': stage, 'install': install, 'rollback': rollback}[parser.parse_args().action]()
