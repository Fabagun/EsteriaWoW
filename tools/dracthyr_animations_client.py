"""Client half of the Dracthyr animations: retail dragon animation rows and the racials' cast animations.

    python tools/dracthyr_animations_client.py <scratch dir>     # stage, verify, back up to G:/EsteriaBackups, install

Client closed. Adds to the live locale archive:
  AnimationData   rows for the dragon's retail ids (hover/glide for flight, wing cast), with swim / spell-cast fallbacks so a
                  model without the sequence still plays something sensible. The client picks the flight ids itself (Unit_C.cpp).
  SpellVisualKit  a copy of each racial's cast kit whose animation is the dragon's own.
  SpellVisual     a copy of each racial's visual using that kit.
  Spell           the racials point at those visuals.
"""
import sys, shutil, hashlib, subprocess
from pathlib import Path
from datetime import datetime
sys.path.insert(0, 'G:/RetroPorterWork/tool-workspace/vendor'); sys.path.insert(0, str(Path(__file__).parent))
import retroported_race_pack as p, drakkin_drakonid_racials as d
from cars_mount_pack import Wdbc, build_wdbc

# AnimationData: id -> (name, donor row, fallback, behavior). Behavior drives the client's cast/emote classification.
ANIMS = {
    1604: ('DracHoverIdle', 193, 229, 193), 1606: ('DracHoverLeft', 43, 43, 43), 1608: ('DracHoverRight', 44, 44, 44),
    1610: ('DracHoverBackward', 45, 45, 45), 1612: ('DracHoverForward', 42, 42, 42), 1694: ('Glide', 42, 42, 42),
    1614: ('DracAttackWings', 32, 32, 32), 1708: ('DracSpellCastWings', 32, 32, 32),
    1472: ('TakeOffStart', 32, 32, 32),
    # the flying-mount family: stock rows are kept when the client has them
    550: ('MountFlightBackwards', 45, 45, 45), 552: ('MountFlightLeft', 43, 43, 43), 554: ('MountFlightRight', 44, 44, 44),
    556: ('MountFlightRun', 42, 42, 42), 558: ('MountFlightSprint', 42, 42, 42),
}
KEEP_EXISTING = {550, 552, 554, 556, 558}
# racial spell -> (new visual/kit id, donor visual's kit slot that carries the cast animation, animation to play)
RACIALS = {110680: (110680, 2, 1614),   # Wing Buffet: wing attack (an instant spell plays its cast kit, not the precast one)
           110681: (110681, 2, 1708),   # Glide: wings spread
           110684: (110684, 2, 1472),   # Soar: take-off
           110688: (110688, 2, 1616)}   # Tail Swipe: tail attack


def main(scratch):
    assert 'wow.exe' not in subprocess.check_output(['tasklist', '/FO', 'CSV', '/NH'], text=True).lower(), 'close the client'
    ix = d.field_index()
    files = p.ClientFiles(str(p.CLIENT_DEFAULT / 'Data'), 'enUS')
    T = {n: Wdbc(files.find(p.DBC_ROOT + n + '.dbc')[0]) for n in ('Spell', 'SpellVisual', 'SpellVisualKit', 'AnimationData')}
    files.close()

    # AnimationData
    ad = T['AnimationData']; arows = [list(r) for r in ad.rows]; astr = {(i, 1): ad.text(r[1]) for i, r in enumerate(arows) if r[1]}
    byid = {r[0]: i for i, r in enumerate(arows)}
    for aid, (name, donor, fallback, behavior) in ANIMS.items():
        row = list(arows[byid[donor]]); row[0], row[5], row[6] = aid, fallback, behavior
        slot = byid.get(aid)
        if slot is None: slot = len(arows); arows.append(row); byid[aid] = slot
        else: arows[slot] = row
        astr[(slot, 1)] = name; row[1] = 0
    # Kits / visuals
    kits = [list(r) for r in T['SpellVisualKit'].rows]; kid = {r[0]: i for i, r in enumerate(kits)}
    vis = [list(r) for r in T['SpellVisual'].rows]; vid = {r[0]: i for i, r in enumerate(vis)}
    sp = T['Spell']; srows = [list(r) for r in sp.rows]; sid = {r[0]: i for i, r in enumerate(srows)}
    sstr = {}
    for i, r in enumerate(srows):
        for c, _ in d.TEXT_COLUMNS:
            if r[ix[c]]:
                v = sp.text(r[ix[c]])
                if v: sstr[(i, ix[c])] = v
    for spell, (new, slot, anim) in RACIALS.items():
        srow = srows[sid[spell]]
        cur = srow[ix['SpellVisualID_1']]
        donor_visual = vis[vid[cur if cur in vid and cur != new else (30209 if spell == 110680 else 63)]]
        donor_kit = kits[kid[donor_visual[slot]]]
        kit = list(donor_kit); kit[0] = new; kit[2] = anim
        if new in kid: kits[kid[new]] = kit
        else: kid[new] = len(kits); kits.append(kit)
        visual = list(donor_visual); visual[0] = new; visual[slot] = new
        if new in vid: vis[vid[new]] = visual
        else: vid[new] = len(vis); vis.append(visual)
        srow[ix['SpellVisualID_1']] = new
    changes = {
        p.DBC_ROOT + 'AnimationData.dbc': build_wdbc(arows, ad.fields, ad.record_size, astr),
        p.DBC_ROOT + 'SpellVisualKit.dbc': build_wdbc(kits, T['SpellVisualKit'].fields, T['SpellVisualKit'].record_size, {}),
        p.DBC_ROOT + 'SpellVisual.dbc': build_wdbc(vis, T['SpellVisual'].fields, T['SpellVisual'].record_size, {}),
        p.DBC_ROOT + 'Spell.dbc': build_wdbc(srows, sp.fields, sp.record_size, sstr)}
    sha = lambda f: hashlib.sha256(open(f, 'rb').read()).hexdigest()
    live = p.CLIENT_DEFAULT / p.LOCALE_ARCHIVE_REL
    stage = Path(scratch) / live.name; shutil.copy2(live, stage)
    storm = p.Storm(p.DLL_DEFAULT); storm.replace_archive_entries(stage, changes)
    h = storm.open_archive(stage)
    for k, b in changes.items(): assert storm.read(h, k) == b, k
    storm.dll.SFileCloseArchive(h)
    backup = Path('G:/EsteriaBackups') / ('Dracthyr-animations-' + datetime.now().strftime('%Y%m%d-%H%M%S')) / live.name
    backup.parent.mkdir(parents=True); shutil.copy2(live, backup); assert sha(backup) == sha(live)
    tmp = live.with_suffix('.mpq.dracthyr-next'); shutil.copy2(stage, tmp); tmp.replace(live)
    print('INSTALLED', sorted(ANIMS), sorted(RACIALS), 'backup', backup)


if __name__ == '__main__':
    main(sys.argv[1])
