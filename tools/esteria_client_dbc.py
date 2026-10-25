"""Writes the Worgen / Dracthyr client DBC changes into a new top-priority archive.

The Esteria client (PatchFiles.cpp) sorts every Data\\patch-*.MPQ and Data\\<locale>\\patch-<locale>-*.MPQ by full path,
descending, and the first of them gets the highest priority: so every Data\\patch-* archive beats every locale patch, and
the locale archive that earlier tools wrote these tables to is shadowed by patch-Z.MPQ's own copy. This tool reads each
table from the archive that really wins, applies the changes and writes them to Data\\Patch-ZzzzzzzEsteriaClient.MPQ, which
sorts above everything.

    python tools/esteria_client_dbc.py <scratch dir>

Changes (see worgen_racials_client.py / dracthyr_animations_client.py for the details of each):
  Spell, SpellIcon                              Two Forms (68996), Worgen racials from the server's spell_dbc, Soar as free flight
  AnimationData, SpellVisualKit, SpellVisual    Dracthyr dragon animations and racial cast animations
Client closed. The archive is new, so the backup is its absence (delete it to roll back).
"""
import os, sys, shutil, subprocess, struct
from pathlib import Path
sys.path.insert(0, 'G:/RetroPorterWork/tool-workspace/vendor'); sys.path.insert(0, str(Path(__file__).parent))
import retroported_race_pack as p, drakkin_drakonid_racials as d
from cars_mount_pack import Wdbc, build_wdbc
import worgen_racials_client as wr, dracthyr_animations_client as da

DATA = Path(p.CLIENT_DEFAULT) / 'Data'
OUT = DATA / 'Patch-ZzzzzzzEsteriaClient.MPQ'
TABLES = ('Spell', 'SpellIcon', 'SpellVisual', 'SpellVisualKit', 'AnimationData')
BACK = chr(92)
ICON_DIR = 'Interface' + BACK + 'Icons' + BACK
TWO_FORMS, TWO_FORMS_ICON = 68996, ICON_DIR + 'Ability_Racial_TwoForms'


def chain():
    """Archives in client priority order, highest first (PatchFiles.cpp: full path, descending)."""
    found = []
    for folder, prefix in ((DATA, 'Data' + BACK), (DATA / 'enUS', 'Data' + BACK + 'enUS' + BACK)):
        if folder.is_dir():
            for f in os.listdir(folder):
                if f.lower().endswith('.mpq') and f.lower().startswith('patch') and (folder / f).is_file():
                    found.append(((prefix + f).lower(), folder / f))
    found.sort(key=lambda t: t[0], reverse=True)
    ordered = [path for _, path in found if path != OUT]
    for rel in ('lichking-locale-enUS.MPQ', 'expansion-locale-enUS.MPQ', 'locale-enUS.MPQ'):
        if (DATA / 'enUS' / rel).is_file(): ordered.append(DATA / 'enUS' / rel)
    for rel in ('lichking.MPQ', 'expansion.MPQ', 'common-3.MPQ', 'common-2.MPQ', 'common.MPQ'):
        if (DATA / rel).is_file(): ordered.append(DATA / rel)
    return ordered


def real_tables(storm):
    """{table: (Wdbc, archive name)} from the archive each really wins from."""
    out = {}
    for path in chain():
        try:
            handle = storm.open_archive(path)
        except OSError:
            continue
        try:
            for table in TABLES:
                if table in out: continue
                try:
                    out[table] = (Wdbc(storm.read(handle, p.DBC_ROOT + table + '.dbc')), path.name)
                except OSError:
                    pass
        finally:
            storm.dll.SFileCloseArchive(handle)
        if len(out) == len(TABLES): break
    return out


def main(scratch):
    assert 'wow.exe' not in subprocess.check_output(['tasklist', '/FO', 'CSV', '/NH'], text=True).lower(), 'close the client'
    storm = p.Storm(p.DLL_DEFAULT)
    tables = real_tables(storm)
    for t, (_, name) in tables.items(): print('winner', t, name)
    ix = d.field_index(); cols = d.spell_columns(); text = {ix[c] for c, _ in d.TEXT_COLUMNS}
    sp, ic, sv, kv, ad = (tables[t][0] for t in TABLES)

    # --- Spell / SpellIcon
    srows = [list(r) for r in sp.rows]; sid = {r[0]: i for i, r in enumerate(srows)}
    sstr = {}
    for i, r in enumerate(srows):
        for c, _ in d.TEXT_COLUMNS:
            if r[ix[c]]:
                v = sp.text(r[ix[c]])
                if v: sstr[(i, ix[c])] = v
    irows = [list(r) for r in ic.rows]; istr = {(i, 1): ic.text(r[1]) for i, r in enumerate(irows) if r[1]}
    ipath = {ic.text(r[1]).lower(): r[0] for r in ic.rows}
    next_icon = [max(r[0] for r in ic.rows) + 1]

    def icon_id(path):
        if path.lower() not in ipath:
            istr[(len(irows), 1)] = path; irows.append([next_icon[0], 0]); ipath[path.lower()] = next_icon[0]; next_icon[0] += 1
        return ipath[path.lower()]

    def put_spell(row, strings):
        slot = sid.get(row[0])
        if slot is None: slot = len(srows); srows.append(row); sid[row[0]] = slot
        else: srows[slot] = row
        for c, _ in d.TEXT_COLUMNS: sstr.pop((slot, ix[c]), None)
        for c, v in strings.items(): sstr[(slot, ix[c])] = v

    # Two Forms: Visage's row (self-cast, instant) renamed
    visage = list(srows[sid[110685]]); visage[0] = TWO_FORMS; visage[ix['SpellIconID']] = icon_id(TWO_FORMS_ICON)
    put_spell(visage, {'Name_Lang_enUS': 'Two Forms', 'Description_Lang_enUS': 'Switches between wolf and human form.'})
    # Worgen racials: the server's rows
    for spell, cells in wr.server_rows().items():
        row = []
        for n, ((name, kind), cell) in enumerate(zip(cols, cells)):
            try:
                if n in text or kind == 'string': row.append(0)
                elif kind == 'float': row.append(struct.unpack('<I', struct.pack('<f', float(cell)))[0])
                else: row.append(int(cell) & 0xFFFFFFFF)
            except ValueError:
                row.append(0)
        row[ix['SpellIconID']] = icon_id(ICON_DIR + wr.SPELLS[spell])
        put_spell(row, {c: cells[ix[c]] for c, _ in d.TEXT_COLUMNS if cells[ix[c]] not in ('', 'NULL')})
    # Soar: free flight
    soar = srows[sid[wr.SOAR]]
    for col, value in wr.SOAR_ROW.items(): soar[ix[col]] = value
    sstr[(sid[wr.SOAR], ix['Description_Lang_enUS'])] = 'Take to the air in free flight, increasing flight speed by 60%. Cancel the effect to land.'
    sstr[(sid[wr.SOAR], ix['AuraDescription_Lang_enUS'])] = 'Flying freely. Flight speed increased by 60%.'

    # Worgen Running Wild: the client lists a spell whose first aura is Mounted (78) as a companion mount, not in the spellbook,
    # so the Worgen pair's client rows use the dummy aura; the server still applies the mounted one.
    for new, src in ((110052, 110050), (110053, 110051)):
        row = list(srows[sid[src]]); row[0] = new; row[ix['EffectAura_1']] = 4
        put_spell(row, {c: sstr[(sid[src], ix[c])] for c, _ in d.TEXT_COLUMNS if (sid[src], ix[c]) in sstr})

    # Tail Swipe: Wing Buffet's row (self-centred knockback) renamed
    swipe = list(srows[sid[110680]]); swipe[0] = 110688; swipe[ix['SpellIconID']] = icon_id(ICON_DIR + 'Ability_Druid_Swipe')
    swipe[ix['ImplicitTargetA_1']] = 22
    put_spell(swipe, {'Name_Lang_enUS': 'Tail Swipe', 'NameSubtext_Lang_enUS': 'Racial',
                      'Description_Lang_enUS': 'Strike with your tail, knocking back enemies within 8 yards.'})

    # --- Dracthyr animations
    arows = [list(r) for r in ad.rows]; astr = {(i, 1): ad.text(r[1]) for i, r in enumerate(arows) if r[1]}
    aid = {r[0]: i for i, r in enumerate(arows)}
    for anim, (name, donor, fallback, behavior) in da.ANIMS.items():
        row = list(arows[aid[donor]]); row[0], row[5], row[6] = anim, fallback, behavior
        slot = aid.get(anim)
        if slot is not None and anim in da.KEEP_EXISTING: continue
        if slot is None: slot = len(arows); arows.append(row); aid[anim] = slot
        else: arows[slot] = row
        row[1] = 0; astr[(slot, 1)] = name
    kits = [list(r) for r in kv.rows]; kid = {r[0]: i for i, r in enumerate(kits)}
    vis = [list(r) for r in sv.rows]; vid = {r[0]: i for i, r in enumerate(vis)}
    for spell, (new, slot, anim) in da.RACIALS.items():
        donor_visual = vis[vid[30209 if spell in (110680, 110688) else 63]]
        kit = list(kits[kid[donor_visual[slot]]]); kit[0] = new; kit[2] = anim
        if new in kid: kits[kid[new]] = kit
        else: kid[new] = len(kits); kits.append(kit)
        visual = list(donor_visual); visual[0] = new; visual[slot] = new
        if new in vid: vis[vid[new]] = visual
        else: vid[new] = len(vis); vis.append(visual)
        srows[sid[spell]][ix['SpellVisualID_1']] = new

    changes = {
        p.DBC_ROOT + 'Spell.dbc': build_wdbc(srows, sp.fields, sp.record_size, sstr),
        p.DBC_ROOT + 'SpellIcon.dbc': build_wdbc(irows, ic.fields, ic.record_size, istr),
        p.DBC_ROOT + 'AnimationData.dbc': build_wdbc(arows, ad.fields, ad.record_size, astr),
        p.DBC_ROOT + 'SpellVisualKit.dbc': build_wdbc(kits, kv.fields, kv.record_size, {}),
        p.DBC_ROOT + 'SpellVisual.dbc': build_wdbc(vis, sv.fields, sv.record_size, {})}
    stage = Path(scratch) / OUT.name
    if stage.exists(): stage.unlink()
    storm.create_archive(stage, changes)
    handle = storm.open_archive(stage)
    for k, b in changes.items(): assert storm.read(handle, k) == b, k
    storm.dll.SFileCloseArchive(handle)
    assert stage.stat().st_size < 0x70000000
    nxt = OUT.with_suffix('.mpq.next')
    shutil.copy2(stage, nxt); nxt.replace(OUT)
    print('INSTALLED', OUT, OUT.stat().st_size)


if __name__ == '__main__':
    main(sys.argv[1])
