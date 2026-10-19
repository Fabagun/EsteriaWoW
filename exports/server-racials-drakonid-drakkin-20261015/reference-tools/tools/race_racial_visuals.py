"""Retail spell visuals for the racials, rebuilt as 3.3.5a SpellVisual rows plus converted models.

Retail chain: Spell -> SpellXSpellVisual -> SpellVisual -> SpellVisualEvent -> SpellVisualKit ->
SpellVisualKitEffect (type 2) -> SpellVisualKitModelAttach -> SpellVisualEffectName -> M2.  The retail tables are
encrypted in the local CASC install, so they come from wago.tools CSV exports of the same build (``fetch``).
3.3.5a keeps the same shape (SpellVisual slots -> SpellVisualKit -> SpellVisualKitModelAttach -> SpellVisualEffectName),
so each retail spell becomes one new SpellVisual whose kits carry the retail model attaches.  Only model effects are
ported; retail sound, camera, animation-kit and missile-set effects have no 3.3.5a counterpart.  Cast animations
come from the stock donor visual, so the cast pose is unchanged.

    python tools/race_racial_visuals.py fetch    # download the retail tables (raw game data, kept outside Git)
    python tools/race_racial_visuals.py report   # show what each racial ports and what falls back
"""

import argparse
import csv
from dataclasses import dataclass, field
import os
from pathlib import Path
import struct
import subprocess
import sys
import urllib.request

WORKSPACE = Path('G:/RetroPorterWork/tool-workspace')
WORK = Path('G:/RetroPorterWork/racials-visuals')   # raw retail tables and converted assets; not in Git
WAGO = WORK / 'wago'
BUILD = '12.1.0.69933'
RETAIL = Path('G:/Blizzard/World of Warcraft')
CACHE = Path.home() / '.cache' / 'wotlkconv'
TABLES = ('SpellXSpellVisual', 'SpellVisual', 'SpellVisualKit', 'SpellVisualKitEffect', 'SpellVisualEffectName',
          'SpellVisualKitModelAttach', 'SpellVisualEvent')
MODEL_DIR = 'Spells\\Racials\\'   # also the --path-prefix, so converted texture references land under it

# Fresh ids above the effective client maxima (visual 30112, kit 22076, attach 6076, effect name 8676).
VISUAL_BASE, KIT_BASE, ATTACH_BASE, EFFECT_BASE = 30200, 22200, 6200, 8800
SLOTS = {'precast': 1, 'cast': 2, 'impact': 3, 'state': 4, 'channel': 6, 'caster_impact': 14}
NONE = 0xFFFFFFFF
EVENT_STATE, EVENT_PRECAST, EVENT_CAST = 7, 1, 3
EFFECT_MODEL = 2    # SpellVisualKitEffect.EffectType whose Effect is a SpellVisualKitModelAttach id


@dataclass(frozen=True)
class Retail:
    spell: int                                  # retail spell id whose visual is ported
    visual: int = 0                             # which of the spell's SpellXSpellVisual rows (0 = first)
    remap: dict = field(default_factory=dict)   # slot the rules chose -> slot to use instead
    skip: tuple = ()                            # slots to leave out


# Racial key (race_racials.KEYS) -> the retail spell it takes its look from.  Signature retail effects first, then
# custom-race abilities that borrow a fitting retail effect.  Anything absent (Mole Machine, Make Camp, Headbutt,
# Pounce, ...) has no model effect in retail and keeps the stock donor visual.
RETAIL_VISUALS = {
    'ARCANE_PULSE': Retail(260364),
    'LIGHTS_JUDGMENT': Retail(255647),
    'SPATIAL_RIFT': Retail(256948),
    'SPATIAL_RIFT_OPEN': Retail(256948),
    'BULL_RUSH': Retail(255654),
    'AZERITE_SURGE': Retail(436344),
    'THORN_BLOOM': Retail(1237885),
    'FIREBLOOD': Retail(265221),
    'BAG_OF_TRICKS': Retail(318128, remap={'state': 'cast'}),
    'WING_BUFFET': Retail(357214, visual=2, skip=('state',)),
    'QUAKING_PALM': Retail(107079),
    'ENTROPIC_EMBRACE_BUFF': Retail(256374, remap={'cast': 'state'}),
    'LIGHTS_RECKONING_DAMAGE': Retail(256896),
    'REGENERATIN': Retail(263933),
    'CANTRIPS': Retail(255661),
    'FORGE_OF_LIGHT': Retail(259930),
    'HOLO': Retail(312924),
    # custom races
    'STATIC_COIL': Retail(188443),          # Chain Lightning
    'COILING_GRASP': Retail(339, visual=1),  # Entangling Roots
    'HARPOON_TOSS': Retail(190925),         # Hunter Harpoon impact (the missile is not ported)
    'SAVAGE_BITE': Retail(17253),           # pet Bite impact
    'TIDAL_MEND': Retail(61295, skip=('caster_impact',)),           # Riptide
}


def visual_id(key: str) -> int:
    return VISUAL_BASE + list(RETAIL_VISUALS).index(key)


def slot_for(start_event: int, target_type: int) -> str | None:
    """SpellVisualEvent (start event, target type) -> 3.3.5a SpellVisual slot, or None when it has no counterpart."""
    if start_event == EVENT_STATE:
        return 'state'
    if start_event == EVENT_PRECAST:
        return 'precast'
    if start_event == EVENT_CAST:
        return 'cast' if target_type == 1 else 'impact'
    if start_event in (4, 5, 6, 9):    # missile hit, impact, area and destination effects
        return 'caster_impact' if target_type == 1 else 'impact'
    return None


# ---------------------------------------------------------------------------------------
# Retail tables
# ---------------------------------------------------------------------------------------
def fetch(directory: Path = WAGO) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    for table in TABLES:
        target = directory / f'{table}.csv'
        if target.exists():
            continue
        url = f'https://wago.tools/db2/{table}/csv?build={BUILD}'
        with urllib.request.urlopen(url, timeout=300) as response:
            data = response.read()
        assert data.startswith(b'ID,') or data.startswith(b'\xef\xbb\xbfID,'), (table, data[:80])
        target.write_bytes(data)
        print('fetched', table, len(data), flush=True)


def _rows(directory: Path, table: str) -> list[dict]:
    with open(directory / f'{table}.csv', encoding='utf-8-sig', newline='') as handle:
        return list(csv.DictReader(handle))


class Tables:
    def __init__(self, directory: Path = WAGO):
        self.by_spell: dict[int, list[dict]] = {}
        for row in _rows(directory, 'SpellXSpellVisual'):
            self.by_spell.setdefault(int(row['SpellID']), []).append(row)
        self.visual = {int(r['ID']): r for r in _rows(directory, 'SpellVisual')}
        self.events: dict[int, list[dict]] = {}
        for row in _rows(directory, 'SpellVisualEvent'):
            self.events.setdefault(int(row['SpellVisualID']), []).append(row)
        self.effects: dict[int, list[dict]] = {}
        for row in _rows(directory, 'SpellVisualKitEffect'):
            self.effects.setdefault(int(row['ParentSpellVisualKitID']), []).append(row)
        self.attach = {int(r['ID']): r for r in _rows(directory, 'SpellVisualKitModelAttach')}
        self.effect_name = {int(r['ID']): r for r in _rows(directory, 'SpellVisualEffectName')}


@dataclass(frozen=True)
class Attach:
    model: int          # retail ModelFileDataID
    attachment: int
    offset: tuple
    yaw: float
    pitch: float
    roll: float
    scale: float


def kit_attaches(tables: Tables, kit: int) -> list[Attach]:
    found = []
    for effect in tables.effects.get(kit, []):
        if int(effect['EffectType']) != EFFECT_MODEL:
            continue
        row = tables.attach.get(int(effect['Effect']))
        if not row or int(row['ParentSpellVisualKitID']) != kit:
            continue
        name = tables.effect_name.get(int(row['SpellVisualEffectNameID']))
        if not name or not int(name['ModelFileDataID']):
            continue
        found.append(Attach(
            int(name['ModelFileDataID']), int(row['AttachmentID']),
            tuple(float(row[f'Offset_{i}']) for i in range(3)), float(row['Yaw']), float(row['Pitch']), float(row['Roll']),
            float(row['Scale']) * float(name['Scale'])))
    return found


def trace(tables: Tables, spec: Retail) -> dict[str, list[Attach]]:
    """Slot -> model attaches for one racial; empty when retail has no model effect for the spell."""
    rows = tables.by_spell.get(spec.spell, [])
    if len(rows) <= spec.visual:
        return {}
    visual_id_ = int(rows[spec.visual]['SpellVisualID'])
    kits: list[tuple[str, int]] = []
    state = int(tables.visual[visual_id_]['StateKit']) if visual_id_ in tables.visual else 0
    if state:
        kits.append(('state', state))
    for event in tables.events.get(visual_id_, []):
        slot = slot_for(int(event['StartEvent']), int(event['TargetType']))
        if slot and int(event['SpellVisualKitID']):
            kits.append((slot, int(event['SpellVisualKitID'])))
    slots: dict[str, list[Attach]] = {}
    seen = set()
    for slot, kit in kits:
        slot = spec.remap.get(slot, slot)
        if slot in spec.skip or (slot, kit) in seen:
            continue
        seen.add((slot, kit))
        slots.setdefault(slot, []).extend(kit_attaches(tables, kit))
    return {slot: attaches for slot, attaches in slots.items() if attaches}


def plan(tables: Tables) -> dict[str, dict[str, list[Attach]]]:
    return {key: found for key, spec in RETAIL_VISUALS.items() if (found := trace(tables, spec))}


def usable(found: dict, good: set[int]) -> dict:
    """Drop the attaches whose model did not convert, then the slots and racials that end up empty."""
    kept = {}
    for key, slots in found.items():
        slots = {slot: [a for a in attaches if a.model in good] for slot, attaches in slots.items()}
        slots = {slot: attaches for slot, attaches in slots.items() if attaches}
        if slots:
            kept[key] = slots
    return kept


def model_paths(listfile: dict[int, str], fdids) -> dict[int, str]:
    """FileDataID -> the in-game model path written into SpellVisualEffectName (the client maps .mdx to .m2)."""
    return {fdid: MODEL_DIR + Path(listfile[fdid].replace(chr(92), '/')).stem + '.mdx' for fdid in fdids}


# ---------------------------------------------------------------------------------------
# DBC rows (3.3.5a layouts: SpellVisual 32 fields, Kit 38, ModelAttach 10, EffectName 7)
# ---------------------------------------------------------------------------------------
def _f(value: float) -> int:
    return struct.unpack('<I', struct.pack('<f', value))[0]


def build_rows(visuals: dict[str, dict[str, list[Attach]]], paths: dict[int, str], donor_anim) -> dict:
    """Return {table: (rows, strings)} for every ported racial.  ``donor_anim(key, slot)`` -> (start, anim) or None."""
    names: dict[tuple, int] = {}
    rows = {'SpellVisual': [], 'SpellVisualKit': [], 'SpellVisualKitModelAttach': [], 'SpellVisualEffectName': []}
    effect_strings: dict[int, str] = {}
    kits_made = attaches_made = 0
    attach_rows, kit_rows, effect_rows, visual_rows = rows['SpellVisualKitModelAttach'], rows['SpellVisualKit'], \
        rows['SpellVisualEffectName'], rows['SpellVisual']
    for key in RETAIL_VISUALS:
        slots = dict(visuals.get(key, {}))
        if not slots:
            continue
        for slot in ('precast', 'cast'):    # keep the stock cast pose even when retail adds no model to the slot
            if slot not in slots and donor_anim(key, slot):
                slots[slot] = []
        visual = [0] * 32
        visual[0], visual[10], visual[16] = visual_id(key), 1, NONE
        for slot, attaches in slots.items():
            kit = KIT_BASE + kits_made
            kits_made += 1
            start, anim = donor_anim(key, slot) or (NONE, NONE)
            row = [kit, start, anim] + [0] * 14 + [NONE] * 4 + [0] * 17
            kit_rows.append(row)
            for item in attaches:
                effect_key = (item.model, round(item.scale, 4))
                if effect_key not in names:
                    names[effect_key] = EFFECT_BASE + len(names)
                    effect_rows.append([names[effect_key], 0, 0, 0, _f(1.0), _f(item.scale), _f(item.scale)])
                    effect_strings[len(effect_rows) - 1] = paths[item.model]
                attach_rows.append([ATTACH_BASE + attaches_made, kit, names[effect_key], item.attachment & 0xFFFFFFFF,
                                    *(_f(v) for v in item.offset), _f(item.yaw), _f(item.pitch), _f(item.roll)])
                attaches_made += 1
            visual[SLOTS[slot]] = kit
        visual_rows.append(visual)
    return {'rows': rows, 'effect_strings': effect_strings}


def merge_table(data: bytes, new_rows: list[list[int]], string_columns: tuple = (), new_strings: dict | None = None) -> bytes:
    """Append (or refresh by id) rows in a WDBC table, keeping its existing strings."""
    from cars_mount_pack import Wdbc, build_wdbc
    table = Wdbc(data)
    records = [list(row) for row in table.rows]
    strings = {(i, c): table.text(row[c]) for i, row in enumerate(records) for c in string_columns if row[c]}
    position = {row[0]: i for i, row in enumerate(records)}
    for index, row in enumerate(new_rows):
        slot = position.get(row[0])
        if slot is None:
            slot = len(records)
            records.append(row)
        else:
            records[slot] = row
        for column in string_columns:
            strings.pop((slot, column), None)
        for column, value in (new_strings or {}).get(index, {}).items():
            strings[(slot, column)] = value
    return build_wdbc(records, table.fields, table.record_size, strings)


# ---------------------------------------------------------------------------------------
# Model conversion (wotlkconv, the pinned copy in the retroport workspace)
# ---------------------------------------------------------------------------------------
# This install keeps index entries for some effect files whose data blocks were never written, so reading them
# fails with "not a BLTE stream" and --casc-cdn is never consulted.  Fall back to the CDN for those, without
# touching the pinned wotlkconv copy.
CDN_FALLBACK = """
import sys
from wotlkconv.casc import blte
from wotlkconv.casc.storage import CascStorage
from wotlkconv.errors import MalformedFileError
read = CascStorage._read_by_ekey
def patched(self, ekey, what='file', zero_encrypted=False):
    try:
        return read(self, ekey, what, zero_encrypted)
    except MalformedFileError:
        if self.cdn is None:
            raise
        return blte.decode(self.cdn.read(ekey, what), self.keys, zero_encrypted)
CascStorage._read_by_ekey = patched
from wotlkconv.cli import main
sys.exit(main(sys.argv[1:]))
"""


def _convert(fdids, out: Path) -> None:
    command = [sys.executable, '-c', CDN_FALLBACK, 'convert', '--casc', str(RETAIL), '--casc-keys', str(CACHE / 'WoW.txt'),
               '--casc-cdn', '-l', str(CACHE / 'community-listfile.csv'), '--path-prefix', MODEL_DIR.rstrip('\\'), '-o', str(out), '-q']
    for fdid in sorted(fdids):
        command += ['--fileid', str(fdid)]
    env = dict(os.environ, PYTHONPATH=str(WORKSPACE / 'vendor'))
    subprocess.run(command, check=True, env=env)


def m2_textures(data: bytes) -> list[str]:
    count, offset = struct.unpack_from('<II', data, 0x50)
    names = []
    for i in range(count):
        _, _, length, name_offset = struct.unpack_from('<IIII', data, offset + 16 * i)
        if length:
            names.append(data[name_offset:name_offset + length].rstrip(b'\0').decode('latin1'))
    return names


def convert_assets(fdids, listfile: dict[int, str], out: Path = WORK / 'converted') -> tuple[dict[str, bytes], list[str], set[int]]:
    """Convert the models and their textures.

    Returns ({MPQ path: bytes}, notes, FileDataIDs of the models that converted with every texture).  A model whose
    file or any texture is not in the local CASC install (it would have to come from the CDN) is left out entirely.
    """
    models, textures = out / 'models', out / 'textures'
    _convert(fdids, models)
    by_path = {Path(v.replace(chr(92), '/')).as_posix().lower(): k for k, v in listfile.items()}
    parts: dict[int, dict[str, bytes]] = {}
    wanted: dict[int, dict[str, str]] = {}   # model -> {texture reference: original retail path}
    notes = []
    for fdid in sorted(fdids):
        stem = Path(listfile[fdid].replace(chr(92), '/')).stem
        found = [p for p in models.rglob('*') if p.suffix.lower() == '.m2' and p.stem == stem]
        if not found:
            notes.append(f'{stem}: model not converted (not in the local CASC install)')
            continue
        parts[fdid] = {MODEL_DIR + p.name: p.read_bytes() for p in sorted(found[0].parent.glob(stem + '*'))
                       if p.suffix.lower() in ('.m2', '.skin', '.anim')}
        wanted[fdid] = {}
        prefix = MODEL_DIR.lower().replace(chr(92), '/')
        for texture in m2_textures(found[0].read_bytes()):
            original = texture.lower().replace(chr(92), '/')
            original = original[len(prefix):] if original.startswith(prefix) else original
            if original in by_path:
                wanted[fdid][texture.lower()] = original
            else:
                notes.append(f'{stem}: texture {texture} has no FileDataID')
                parts.pop(fdid, None)
                break
    needed = {original for fdid in parts for original in wanted[fdid].values()}
    built: dict[str, Path] = {}
    if needed:
        _convert({by_path[o] for o in needed}, textures)
        built = {p.relative_to(textures).as_posix().lower(): p for p in textures.rglob('*.blp')}
    files: dict[str, bytes] = {}
    for fdid in list(parts):
        missing = [t for t, original in wanted[fdid].items() if original not in built]
        if missing:
            notes.append(f'{Path(listfile[fdid]).stem}: {len(missing)} texture(s) not in the local CASC install, model left out')
            del parts[fdid]
            continue
        files.update(parts[fdid])
        files.update({t.replace('/', chr(92)): built[o].read_bytes() for t, o in wanted[fdid].items()})
    return files, notes, set(parts)


def load_listfile() -> dict[int, str]:
    sys.path.insert(0, str(WORKSPACE / 'vendor'))
    from wotlkconv.listfile import Listfile
    return dict(Listfile.load(CACHE / 'community-listfile.csv'))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('action', choices=('fetch', 'report', 'convert'))
    action = parser.parse_args().action
    if action == 'fetch':
        fetch()
        return
    tables = Tables()
    found = plan(tables)
    listfile = load_listfile()
    if action == 'convert':
        files, notes, good = convert_assets({a.model for slots in found.values() for attaches in slots.values() for a in attaches}, listfile)
        print(len(files), 'files,', sum(map(len, files.values())), 'bytes;', len(good), 'models'); print(*notes, sep=chr(10))
        return
    for key in RETAIL_VISUALS:
        slots = found.get(key)
        print(key, '->', 'FALLS BACK to the stock donor' if not slots else {
            slot: [listfile.get(a.model, a.model).split('/')[-1] for a in attaches] for slot, attaches in slots.items()})


if __name__ == '__main__':
    main()
