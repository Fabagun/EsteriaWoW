"""Stage (and, only when told to, install) the client half of the race racials.

The client needs three things the server does not:

* ``Spell.dbc``     - the racial rows from race_racials.py, pointing at their retail icons;
* ``SpellIcon.dbc`` - one new row per retail icon (ids from race_racials.SPELL_ICON_BASE);
* the icon BLPs     - pulled from the retail CASC install by FileDataID and downgraded to 3.3.5a BLPs.

    python tools/race_racials_update.py stage      # builds copies of the live archives; touches nothing live
    python tools/race_racials_update.py install    # hash-verified backup, then swap them in (client closed)
    python tools/race_racials_update.py rollback   # restore the backed-up archives

The retail source is whatever ``--retail`` points at (default G:/Blizzard/World of Warcraft); wotlkconv, the
listfile and the TACT keys come from the prepared retroport workspace.
"""

import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

WORKSPACE = Path('G:/RetroPorterWork/tool-workspace')
# The pinned wotlkconv in the prepared workspace must win over any copy installed in site-packages;
# only its vendor folder is added so the repo's own tools keep resolving to this checkout.
sys.path.insert(0, str(WORKSPACE / 'vendor'))

import race_racials as racials  # noqa: E402
import retroported_race_pack as p  # noqa: E402
from cars_mount_pack import Wdbc, build_wdbc  # noqa: E402

RETAIL = Path('G:/Blizzard/World of Warcraft')
STAGE = Path('G:/RetroPorterWork/racials-20261014')
BACKUPS = Path('G:/EsteriaBackups')
ARCHIVES = (p.GLOBAL_ARCHIVE_REL, p.LOCALE_ARCHIVE_REL)
ICON_DIR = 'Interface\\Icons\\'


def retail_icons(retail: Path) -> tuple[dict[int, tuple[str, bytes]], list[str]]:
    """FileDataID -> (listfile name, 3.3.5a BLP bytes) for every icon the spec uses."""
    from wotlkconv.blp.convert import convert_blp
    from wotlkconv.casc import CascStorage, KeyRing
    from wotlkconv.listfile import Listfile
    from wotlkconv.options import Options

    cache = Path.home() / '.cache' / 'wotlkconv'
    listfile = Listfile.load(cache / 'community-listfile.csv')
    storage = CascStorage.open(retail, product='wow', keys=KeyRing.load(cache / 'WoW.txt'))
    icons, notes = {}, []
    try:
        for fdid in sorted(set(racials.RETAIL_ICONS.values())):
            path = listfile.path_for(fdid)
            if not path or not path.lower().replace('\\', '/').startswith('interface/icons/'):
                raise ValueError(f'FileDataID {fdid} is not an Interface/Icons file: {path}')
            blp, result = convert_blp(storage.read_file_id(fdid), path, Options())
            if not blp:
                raise ValueError(f'{path} converted to nothing')
            notes.append(f'{fdid} {path} {result.source_version} -> {result.status.name}')
            icons[fdid] = (Path(path.replace('\\', '/')).stem.strip(), blp)
    finally:
        storage.close()
    return icons, notes


def merge_spell_icons(data: bytes, icons: dict[int, tuple[str, bytes]]) -> bytes:
    table = Wdbc(data)
    ids = racials.retail_icon_ids()
    records = [list(row) for row in table.rows]
    strings = {(i, 1): table.text(row[1]) for i, row in enumerate(records) if row[1]}
    existing = {row[0]: table.text(row[1]) for row in table.rows}
    for fdid, (name, _) in icons.items():
        row_id, path = ids[fdid], ICON_DIR + name
        if row_id in existing:
            assert existing[row_id].lower() == path.lower(), f'SpellIcon {row_id} already belongs to {existing[row_id]}'
            continue
        strings[(len(records), 1)] = path
        records.append([row_id, 0])
    return build_wdbc(records, table.fields, table.record_size, strings)


GLUE_INFO = p.GLUE_ROOT + 'CharacterInfo.lua'
GLUE_CREATE = p.GLUE_ROOT + 'CharacterCreate.lua'
MAX_SHOWN = 8   # the creator tooltip used to stop at six
# Races whose racials are defined elsewhere than race_racials.RACE_GRANTS.
EXTRA_RACIALS = {
    66: (110300, 110309, 110316, 110318), 67: (110300, 110309, 110316, 110318),
    69: (110400, 110404, 110405, 110406), 70: (110400, 110404, 110405, 110406),
    45: (110100, 110101, 110102, 110103), 68: (13990001, 13990002, 13990003, 13990004, 13990005),
}
RACIAL_CLIENT_FILESTRING = 11   # ChrRaces.dbc column


def racial_race_spells() -> dict[int, list[int]]:
    spells = {race: list(ids) for race, ids in EXTRA_RACIALS.items()}
    for race, keys in racials.RACE_GRANTS.items():
        spells[race] = [racials.KEYS[key] for key in keys]
    return spells


def racial_tooltip_lua(spell_dbc: bytes, icon_dbc: bytes, chr_races: bytes) -> str:
    """Lua appended to CharacterInfo.lua: English racial lines (name, icon, text) for every race we define."""
    spells, icons, races = Wdbc(spell_dbc), Wdbc(icon_dbc), Wdbc(chr_races)
    index = racials.field_index()
    by_id = {row[0]: row for row in spells.rows}
    icon_path = {row[0]: icons.text(row[1]) for row in icons.rows}
    tokens = {row[0]: races.text(row[RACIAL_CLIENT_FILESTRING]).upper() for row in races.rows}
    entries = []
    for race, ids in sorted(racial_race_spells().items()):
        lines = []
        for spell_id in ids:
            row = by_id.get(spell_id)
            if not row:
                continue
            name = spells.text(row[index['Name_Lang_enUS']])
            text = (spells.text(row[index['Description_Lang_enUS']])
                    or spells.text(row[index['AuraDescription_Lang_enUS']]))
            icon = icon_path.get(row[index['SpellIconID']], '').replace('/', chr(92)).split(chr(92))[-1]
            if name and text and icon:
                lines.append({'name': name, 'icon': icon, 'description': text})
        if lines and tokens.get(race):
            entries.append((tokens[race], lines[:MAX_SHOWN]))
    out = ['-- GENERATED by tools/race_racials_update.py: English racial lines for the character creator.',
           'do', 'local RACIALS = {']
    for token, lines in entries:
        out.append(f'    {token} = {{')
        for line in lines:
            assert all(ord(c) < 128 for c in json.dumps(line)), line
            out.append('        {name = %s, icon = %s, description = %s},' % (
                json.dumps(line['name']), json.dumps(line['icon']), json.dumps(line['description'])))
        out.append('    },')
    out += ['}', 'for token, spells in pairs(RACIALS) do', '    local info = {}',
            '    for key, value in pairs(RaceInfoByFileString[token] or {Name = token, Description = ""}) do info[key] = value end',
            f'    for i = 1, {MAX_SHOWN} do info["Spell_" .. i] = nil end',
            '    for i, spell in ipairs(spells) do info["Spell_" .. i] = spell end',
            '    RaceInfoByFileString[token] = info', 'end', 'end', '']
    return chr(10).join(out)


def patch_character_create(text: str) -> str:
    """Tooltip layout (icons inside the frame, text wrapped to it, up to eight racials) and the Drakonid female portrait."""
    if 'DRAKONIDHORDE_FEMALE' in text:   # already patched by an earlier install
        return text

    def swap(old: str, new: str, count: int = 1) -> None:
        nonlocal text
        assert text.count(old) == count, (old, text.count(old))
        text = text.replace(old, new)

    swap('for i = 1, 6 do', f'for i = 1, {MAX_SHOWN} do', 5)
    swap('tooltip["spellContainer"..i]:SetPoint("TOPLEFT", lastElement, "BOTTOMLEFT", 0, 3)',
         'if lastElement == tooltip.rightClickText then\n'
         '                    tooltip["spellContainer"..i]:SetPoint("TOPLEFT", tooltip.detailsText, "BOTTOMLEFT", 35, -(tooltip.rightClickText:GetHeight() + 16))\n'
         '                else\n'
         '                    tooltip["spellContainer"..i]:SetPoint("TOPLEFT", lastElement, "BOTTOMLEFT", 0, 3)\n'
         '                end')
    swap('tooltip["spellDesc"..i]:SetWidth(maxWidth - 60)', 'tooltip["spellDesc"..i]:SetWidth(205)')
    slash = chr(92) * 2
    for side in ('Horde', 'Alliance'):
        male = f'["DRAKONID{side.upper()}_MALE"] = "Interface{slash}Glues{slash}CharacterCreate{slash}UI-CharacterCreate-Drakonid{side}Male",'
        swap(male, male + '\n    ' + male.replace('_MALE', '_FEMALE'))
    return text


def build_changes(files, retail: Path):
    icons, notes = retail_icons(retail)
    spell = racials.merge_spell_table(files.find(p.DBC_ROOT + 'Spell.dbc')[0], retail_icons=True)
    spell_icon = merge_spell_icons(files.find(p.DBC_ROOT + 'SpellIcon.dbc')[0], icons)
    changes = {p.DBC_ROOT + 'Spell.dbc': spell, p.DBC_ROOT + 'SpellIcon.dbc': spell_icon}
    for name, blp in icons.values():
        changes[ICON_DIR + name + '.blp'] = blp

    from lupa.lua51 import LuaRuntime
    compile_chunk = LuaRuntime().eval('function(s) local f,e=loadstring(s); assert(f,e); end')
    info = files.find(GLUE_INFO)[0].decode('utf-8-sig')
    info = info.split('-- GENERATED by tools/race_racials_update')[0].rstrip() + chr(10) + chr(10)   # replace our earlier block
    info += racial_tooltip_lua(spell, spell_icon, files.find(p.DBC_ROOT + 'ChrRaces.dbc')[0])
    create = patch_character_create(files.find(GLUE_CREATE)[0].decode('utf-8-sig'))
    glue = {'info': ((GLUE_INFO, info),), 'create': ((GLUE_CREATE, create),), 'none': ()}.get(
        os.environ.get('RACIALS_GLUE', 'all'), ((GLUE_INFO, info), (GLUE_CREATE, create)))
    for name, source in glue:
        compile_chunk(source)
        changes[name] = source.encode()
    return changes, notes


def stage(retail: Path):
    assert not STAGE.exists(), 'Review the existing stage before regenerating'
    STAGE.mkdir(parents=True)
    files = p.ClientFiles(str(p.CLIENT_DEFAULT / 'Data'), 'enUS')
    try:
        changes, notes = build_changes(files, retail)
    finally:
        files.close()
    storm = p.Storm(p.DLL_DEFAULT)
    report = {'icons': notes, 'baseline': {}, 'staged': {}, 'changes': {}}
    for relative in ARCHIVES:
        # The locale archive wins for DBCs; the icons only need to exist once, in the global archive.
        wanted = {key: blob for key, blob in changes.items() if relative == ARCHIVES[0] or key.startswith((p.DBC_ROOT, p.GLUE_ROOT))}
        live, target = p.CLIENT_DEFAULT / relative, STAGE / 'client' / relative
        report['baseline'][str(relative)] = p.sha256(live)
        report['changes'][str(relative)] = sorted(wanted)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(live, target)
        storm.replace_archive_entries(target, wanted)
        handle = storm.open_archive(target)
        try:
            for key, blob in wanted.items():
                assert storm.read(handle, key) == blob, key
        finally:
            storm.dll.SFileCloseArchive(handle)
        assert p.sha256(live) == report['baseline'][str(relative)], 'Live archive changed while staging'
        report['staged'][str(relative)] = p.sha256(target)
        print('STAGED AND READ BACK', relative, len(wanted), 'entries', flush=True)
    (STAGE / 'report.json').write_text(json.dumps(report, indent=2) + chr(10), encoding='utf-8', newline=chr(10))


def preflight():
    report = json.loads((STAGE / 'report.json').read_text(encoding='utf-8'))
    assert 'wow.exe' not in subprocess.check_output(['tasklist', '/FO', 'CSV', '/NH'], text=True).lower(), 'Close the game client first'
    for relative in ARCHIVES:
        assert p.sha256(p.CLIENT_DEFAULT / relative) == report['baseline'][str(relative)],             'Live archive changed since staging: ' + str(relative)
        assert p.sha256(STAGE / 'client' / relative) == report['staged'][str(relative)], 'Staged archive changed'
    return report


def install():
    report = preflight()
    root = BACKUPS / ('Race-racials-' + datetime.now().strftime('%Y%m%d-%H%M%S'))
    for relative in ARCHIVES:
        backup = root / 'client' / relative
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p.CLIENT_DEFAULT / relative, backup)
        assert p.sha256(backup) == report['baseline'][str(relative)], 'Backup mismatch'
    (root / 'report.json').write_text(json.dumps(report, indent=2) + chr(10), encoding='utf-8', newline=chr(10))
    (STAGE / 'last-backup.txt').write_text(str(root), encoding='utf-8')
    try:
        for relative in ARCHIVES:
            live = p.CLIENT_DEFAULT / relative
            temporary = live.with_suffix(live.suffix + '.racials-next')
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
    parser.add_argument('--retail', type=Path, default=RETAIL)
    args = parser.parse_args()
    {'stage': lambda: stage(args.retail), 'install': install, 'rollback': rollback}[args.action]()
