"""Client half of the Worgen racials: appends the server's spell_dbc rows (Viciousness, Aberration, Flayer, Darkflight)
and their retail icon rows to the live client's Spell.dbc / SpellIcon.dbc in the locale archive.

    python tools/worgen_racials_client.py <scratch dir>     # stage, verify, back up to G:/EsteriaBackups, install

Client closed. Rows already in the client are left alone. The icon BLPs are already in the client's archives.
"""
import sys, shutil, hashlib, subprocess
from pathlib import Path
from datetime import datetime
sys.path.insert(0, 'G:/RetroPorterWork/tool-workspace/vendor'); sys.path.insert(0, str(Path(__file__).parent))
import retroported_race_pack as p, drakkin_drakonid_racials as d
from cars_mount_pack import Wdbc, build_wdbc
import struct

SPELLS = {68975: 'ability_racial_viciousness', 68976: 'ability_racial_aberration',
          68978: 'ability_racial_flayer', 68992: 'ability_racial_darkflight'}
SOAR = 110684
SOAR_ROW = {'EffectAura_1': 201, 'EffectBasePoints_1': 0, 'EffectAura_2': 207, 'EffectBasePoints_2': 59,
            'DurationIndex': 21, 'RecoveryTime': 3000}
ICON_DIR = 'Interface' + chr(92) + 'Icons' + chr(92)


def unescape(cell):
    bs = chr(92)
    return cell.replace(bs + 't', chr(9)).replace(bs + 'n', chr(10)).replace(bs + bs, bs)


def server_rows():
    pw = subprocess.check_output(['docker', 'exec', 'ac-database', 'printenv', 'MYSQL_ROOT_PASSWORD'], text=True).strip()
    sql = 'select * from acore_world.spell_dbc where ID in (%s)' % ','.join(map(str, SPELLS))
    out = subprocess.check_output(['docker', 'exec', 'ac-database', 'mysql', '-uroot', '-p' + pw, '-N', '-B', '-e', sql],
                                  text=True, encoding='utf-8', errors='replace', stderr=subprocess.DEVNULL)
    rows = {}
    for line in out.splitlines():
        cells = [unescape(c) for c in line.split(chr(9))]
        rows[int(cells[0])] = cells
    assert set(rows) == set(SPELLS), rows.keys()
    return rows


def main(scratch):
    assert 'wow.exe' not in subprocess.check_output(['tasklist', '/FO', 'CSV', '/NH'], text=True).lower(), 'close the client'
    cols = d.spell_columns(); ix = d.field_index(); text = {ix[c] for c, _ in d.TEXT_COLUMNS}
    files = p.ClientFiles(str(p.CLIENT_DEFAULT / 'Data'), 'enUS')
    sp = Wdbc(files.find(p.DBC_ROOT + 'Spell.dbc')[0]); ic = Wdbc(files.find(p.DBC_ROOT + 'SpellIcon.dbc')[0]); files.close()
    have = {r[0] for r in sp.rows}
    todo = {i: c for i, c in server_rows().items() if i not in have}
    soar = next((i for i, r in enumerate(sp.rows) if r[0] == SOAR), None)
    if not todo and soar is None:
        print('nothing to add'); return
    irec = [list(r) for r in ic.rows]; istr = {(i, 1): ic.text(r[1]) for i, r in enumerate(irec) if r[1]}
    paths = {ic.text(r[1]).lower(): r[0] for r in ic.rows}
    next_icon = max(r[0] for r in ic.rows) + 1
    rec = [list(r) for r in sp.rows]; strings = {}
    for i, r in enumerate(rec):
        for c, _ in d.TEXT_COLUMNS:
            v = sp.text(r[ix[c]]) if r[ix[c]] else ''
            if v: strings[(i, ix[c])] = v
    for sid, cells in todo.items():
        path = ICON_DIR + SPELLS[sid]
        if path.lower() not in paths:
            istr[(len(irec), 1)] = path; irec.append([next_icon, 0]); paths[path.lower()] = next_icon; next_icon += 1
        row = []
        for n, ((name, kind), cell) in enumerate(zip(cols, cells)):
            try:
                if n in text or kind == 'string': row.append(0)
                elif kind == 'float': row.append(struct.unpack('<I', struct.pack('<f', float(cell)))[0])
                else: row.append(int(cell) & 0xFFFFFFFF)
            except ValueError:   # a locale text column the schema does not mark as a string: empty in the client
                row.append(0)
        row[ix['SpellIconID']] = paths[path.lower()]
        slot = len(rec); rec.append(row)
        for c, _ in d.TEXT_COLUMNS:
            if cells[ix[c]] != 'NULL' and cells[ix[c]]: strings[(slot, ix[c])] = cells[ix[c]]
    if soar is not None:   # Dracthyr Soar becomes free flight (same values as the server migration)
        r = rec[soar]
        for col, value in SOAR_ROW.items(): r[ix[col]] = value
        strings[(soar, ix['Description_Lang_enUS'])] = 'Take to the air in free flight, increasing flight speed by 60%. Cancel the effect to land.'
        strings[(soar, ix['AuraDescription_Lang_enUS'])] = 'Flying freely. Flight speed increased by 60%.'
    changes = {p.DBC_ROOT + 'Spell.dbc': build_wdbc(rec, sp.fields, sp.record_size, strings),
               p.DBC_ROOT + 'SpellIcon.dbc': build_wdbc(irec, ic.fields, ic.record_size, istr)}
    sha = lambda f: hashlib.sha256(open(f, 'rb').read()).hexdigest()
    live = p.CLIENT_DEFAULT / p.LOCALE_ARCHIVE_REL
    stage = Path(scratch) / live.name; shutil.copy2(live, stage)
    storm = p.Storm(p.DLL_DEFAULT); storm.replace_archive_entries(stage, changes)
    h = storm.open_archive(stage)
    for k, b in changes.items(): assert storm.read(h, k) == b, k
    storm.dll.SFileCloseArchive(h)
    backup = Path('G:/EsteriaBackups') / ('Worgen-racials-' + datetime.now().strftime('%Y%m%d-%H%M%S')) / live.name
    backup.parent.mkdir(parents=True); shutil.copy2(live, backup); assert sha(backup) == sha(live)
    tmp = live.with_suffix('.mpq.worgen-next'); shutil.copy2(stage, tmp); tmp.replace(live)
    print('INSTALLED', sorted(todo), 'soar' if soar is not None else '', 'backup', backup)


if __name__ == '__main__':
    main(sys.argv[1])
