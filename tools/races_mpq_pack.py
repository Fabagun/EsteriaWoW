"""Copy every custom playable race's client files into one stand-alone ``Races.MPQ``.

Read-only against the client: nothing is removed from, or changed in, the source archives. The new archive is
built in a stage folder and only copied into ``Data`` with ``--install``.

    python tools/races_mpq_pack.py --plan            # select + report sizes, write nothing
    python tools/races_mpq_pack.py --build           # stage Races.MPQ and verify it against the sources
    python tools/races_mpq_pack.py --build --install # ... and copy it into <client>/Data

What a race owns (everything is resolved through the client's real archive stack, highest priority wins):
models/skins/anims/bones/BLPs (DBC-derived model roots + custom\\<race> folders + M2 texture closure), CharSections
textures, race helmets, Glue/CharacterCreate/Select/Frame art and Glues\\Models backgrounds, GlueXML, the race and
racial DBCs, the racial icons/visual models (Patch-Rv), and the Esteria*.bin catalogs from the client root.

NOTE: this client only mounts ``patch-*.MPQ`` (see the loose-patch scan in the executable), so a file named
Races.MPQ is a self-contained package, not something the client loads by itself.
"""

from __future__ import annotations

import argparse
import ctypes as c
import hashlib
import json
import re
import struct
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cars_mount_pack import DLL_DEFAULT, FindData, Storm, Wdbc  # noqa: E402

CLIENT = Path(r"G:\3.3.5a - Dev")
STAGE = Path(r"G:\RetroPorterWork\races-mpq")
ROOT = Path(__file__).resolve().parent.parent
REGISTRY = ROOT / "modules" / "mod-custom-server" / "data" / "races" / "race_registry.json"
MANIFESTS = ROOT / "data" / "retroported-races"
STOCK_RACES = {1, 2, 3, 4, 5, 6, 7, 8, 10, 11}
MAX_BYTES = 2 * 1024 ** 3 - 64 * 1024 ** 2  # the client's proven read limit for a classic archive
META = {"(listfile)", "(attributes)", "(signature)"}
BS = "\\"

# Archives outside the stock patch-N/patch-Letter stack that still carry race files; they slot in after their letter.
AFTER = {"patch-d.mpq": ["patch-dn.mpq", "patch-dr.mpq"], "patch-r.mpq": ["patch-rv.mpq"], "patch-z.mpq": ["patch-zzz.mpq"]}
# Folders that belong to a race but are not reachable from a ChrRaces model path (donors, NPC-side, female donors).
EXTRA_ROOTS = (
    "custom\\kobold\\", "custom\\tarasek\\", "custom\\drakonid\\", "custom\\arakkoa\\", "custom\\jinyu\\",
    "custom\\gnoll\\", "custom\\saberon\\", "custom\\sethrak\\", "custom\\vrykul-female\\", "custom\\naga\\",
    "custom\\tuskarr\\", "custom\\thinhuman\\", "custom\\vulpera\\", "custom\\skyborne\\", "custom\\mechagnome\\",
    "custom\\highmountain\\", "custom\\earthen\\", "custom\\haranir\\", "custom\\maghar\\", "custom\\vrykul\\",
    "character\\vulpera\\", "character\\vulpera_hd\\", "character\\esteriabroken\\", "character\\pandaren\\",
    "character\\worgen\\", "character\\worgenwild\\", "character\\goblin\\", "character\\sethrak\\",
    "character\\maghar\\", "character\\ogre\\", "character\\jinyu\\", "character\\eredar\\", "character\\nightborne\\",
    "character\\voidelf\\", "character\\lightforgeddraenei\\", "character\\darkirondwarf\\",
    "character\\zandalaritroll\\", "character\\dracthyr\\", "character\\darkfallen\\", "character\\naga_\\",
)
# Interface keywords: file names (and Glues\Models\UI_* folder names) containing one belong to a race.
KEYWORDS = (
    "maghar", "skyborne", "mechagnome", "highmountain", "earthen", "haranir", "vulpera", "naga", "tuskarr", "vrykul",
    "thinhuman", "forgotten", "ogre", "furbolg", "sethrak", "gnoll", "saberon", "jinyu", "drakkin", "tarasek",
    "arakkoa", "drakonid", "darkfallen", "worgen", "goblin", "pandaren", "broken", "eredar", "nightborne", "voidelf",
    "lightforged", "darkiron", "zandalari", "dracthyr", "forsaken", "highelf", "kobold",
)
RACE_DBCS = (
    "ChrRaces", "CharSections", "CreatureDisplayInfo", "CreatureDisplayInfoExtra", "CreatureModelData",
    "CharHairGeosets", "CharHairTextures", "CharacterFacialHairStyles", "CharBaseInfo", "CharStartOutfit",
    "BarberShopStyle", "NameGen", "SkillRaceClassInfo", "SkillLine", "SkillLineAbility", "Languages",
    "HelmetGeosetVisData", "AnimationData", "Spell", "SpellIcon", "SpellVisual", "SpellVisualKit",
    "SpellVisualEffectName",
)


def norm(path: str) -> str:
    return path.replace("/", BS).casefold()


class Stack:
    """The client archive stack, lowest priority first, with a per-path winner index."""

    def __init__(self, storm: Storm, client: Path):
        self.storm, self.client = storm, client
        self.archives = self._order()
        self.handles: dict[Path, c.c_void_p] = {}
        self.winner: dict[str, tuple[Path, str, int, int]] = {}
        for archive in self.archives:
            for name, size, comp in self._list(archive):
                if name.casefold() not in META:
                    self.winner[norm(name)] = (archive, name, size, comp)

    def _order(self) -> list[Path]:
        data = self.client / "Data"
        found = {p.name.casefold(): p for p in [*data.glob("*.[mM][pP][qQ]"), *(data / "enUS").glob("*.[mM][pP][qQ]")] if p.is_file()}
        found.pop("races.mpq", None)
        low_to_high = ["common.mpq", "common-2.mpq", "common-3.mpq", "expansion.mpq", "lichking.mpq", "patch.mpq"]
        for key in [str(n) for n in range(2, 10)] + [chr(x) for x in range(ord("a"), ord("z") + 1)]:
            low_to_high += [f"patch-{key}.mpq", *AFTER.get(f"patch-{key}.mpq", [])]
        low_to_high += ["base-enus.mpq", "locale-enus.mpq", "speech-enus.mpq", "expansion-locale-enus.mpq",
                        "expansion-speech-enus.mpq", "lichking-locale-enus.mpq", "lichking-speech-enus.mpq", "patch-enus.mpq"]
        for key in [str(n) for n in range(2, 10)] + [chr(x) for x in range(ord("a"), ord("z") + 1)]:
            low_to_high.append(f"patch-enus-{key}.mpq")
        order = []
        for name in low_to_high:
            path = found.get(name)
            if path and path not in order:
                # Root and locale archives share one namespace; the locale ones sit above the root ones by design.
                order.append(path)
        return order

    def handle(self, archive: Path):
        if archive not in self.handles:
            handle = c.c_void_p()  # read-only (STREAM_FLAG_READ_ONLY) so a running client's locks don't block us
            if not self.storm.dll.SFileOpenArchive(str(archive), 0, 0x100, c.byref(handle)):
                raise OSError(f"SFileOpenArchive failed: {archive} ({c.get_last_error()})")
            self.handles[archive] = handle
        return self.handles[archive]

    def _list(self, archive: Path):
        handle = self.handle(archive)
        data, result = FindData(), []
        finder = self.storm.dll.SFileFindFirstFile(handle, b"*", c.byref(data), None)
        if not finder:
            return result
        try:
            while True:
                result.append((data.cFileName.split(b"\0", 1)[0].decode("ascii", "replace"), data.dwFileSize, data.dwCompSize))
                if not self.storm.dll.SFileFindNextFile(finder, c.byref(data)):
                    break
        finally:
            self.storm.dll.SFileFindClose(finder)
        return result

    def has(self, path: str) -> bool:
        return norm(path) in self.winner

    def read(self, path: str) -> bytes:
        archive, name, *_ = self.winner[norm(path)]
        return self.storm.read(self.handle(archive), name)

    def close(self):
        for handle in self.handles.values():
            self.storm.dll.SFileCloseArchive(handle)
        self.handles.clear()


def playable_ids() -> list[int]:
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    return sorted({row["id"] for row in registry["playable"]} - STOCK_RACES)


def m2_dependencies(blob: bytes) -> list[str]:
    """Texture file names an M2 refers to (type-0 texture records)."""
    if blob[:4] != b"MD20":
        return []
    count, offset = struct.unpack_from("<II", blob, 0x50)
    names = []
    if offset + count * 16 > len(blob):  # not a classic 3.3.5a texture table; the folder copy still covers its files
        return names
    for i in range(count):
        kind, _, length, name_offset = struct.unpack_from("<IIII", blob, offset + i * 16)
        if kind == 0 and length > 1 and name_offset + length <= len(blob):
            names.append(blob[name_offset:name_offset + length].split(b"\0", 1)[0].decode("latin1"))
    return names


def select(stack: Stack, client: Path) -> dict[str, str]:
    """Return {casefolded path: reason} for every file that belongs in Races.MPQ."""
    picked: dict[str, str] = {}
    keys = list(stack.winner)

    def add(path: str, why: str):
        if path and norm(path) in stack.winner:
            picked.setdefault(norm(path), why)

    def add_prefix(prefix: str, why: str):
        prefix = norm(prefix)
        for key in keys:
            if key.startswith(prefix):
                picked.setdefault(key, why)

    ids = playable_ids()
    races = Wdbc(stack.read(r"DBFilesClient\ChrRaces.dbc"))
    displays = {row[0]: row for row in Wdbc(stack.read(r"DBFilesClient\CreatureDisplayInfo.dbc")).rows}
    models_dbc = Wdbc(stack.read(r"DBFilesClient\CreatureModelData.dbc"))
    models = {row[0]: row for row in models_dbc.rows}
    for row in races.rows:
        if row[0] not in ids:
            continue
        for display_id in (row[4], row[5]):
            model = models.get(displays.get(display_id, [0, 0])[1])
            path = models_dbc.text(model[2]) if model else ""
            parts = norm(path).split(BS)
            # A model in a stock-race folder (e.g. High Elf on BloodElf) keeps only its own folder, never the whole race.
            if len(parts) > 2 and parts[0] == "custom":
                add_prefix(BS.join(parts[:2]) + BS, f"model root of race {row[0]}")
            elif len(parts) > 2:
                add_prefix(BS.join(parts[:-1]) + BS, f"model folder of race {row[0]}")
    for root in EXTRA_ROOTS:
        add_prefix(root, "race folder")
    sections = Wdbc(stack.read(r"DBFilesClient\CharSections.dbc"))
    for row in sections.rows:
        if row[1] in ids:
            for field in (4, 5, 6):
                add(sections.text(row[field]), f"CharSections race {row[1]}")
    for key in keys:
        if key.startswith("interface\\glues\\models\\ui_"):
            if any(word in key.split(BS)[3] for word in KEYWORDS):
                picked.setdefault(key, "creator background")
        elif key.startswith(("interface\\glues\\charactercreate\\", "interface\\glues\\characterselect\\",
                             "interface\\characterframe\\", "interface\\reforgedogre\\")):
            if any(word in key.rsplit(BS, 1)[-1] for word in KEYWORDS) or key.startswith("interface\\reforgedogre\\"):
                picked.setdefault(key, "race glue art")
        elif key.startswith("interface\\gluexml\\"):
            picked.setdefault(key, "GlueXML")
    prefixes: set[str] = set()
    for row in races.rows:
        if row[0] in ids and races.text(row[6]):
            prefixes.add(races.text(row[6]).casefold())
    for key in keys:
        if key.startswith("item\\objectcomponents\\head\\") and key.endswith((".m2", ".blp")):
            if any(re.search(rf"_{re.escape(p)}[mf]\.", key) for p in prefixes):
                picked.setdefault(key, "race helmet")
    for name in RACE_DBCS:
        add(f"DBFilesClient\\{name}.dbc", "race/racial DBC")
    for key, (archive, *_rest) in stack.winner.items():
        if archive.name.casefold() == "patch-rv.mpq":
            picked.setdefault(key, "racial visuals and icons")
    # Dependency closure: textures named by selected models, plus their skins/anims/bones beside them.
    for key in [k for k in picked if k.endswith(".m2")]:
        folder, stem = key.rsplit(BS, 1)[0], key.rsplit(BS, 1)[1][:-3]
        for dependency in m2_dependencies(stack.read(key)):
            add(dependency, "texture of " + key)
        for sibling in keys:
            if sibling.startswith(folder + BS + stem) and sibling.endswith((".skin", ".anim", ".bone")):
                picked.setdefault(sibling, "companion of " + key)
    return picked


def esteria_bins(client: Path) -> dict[str, Path]:
    return {p.name: p for p in client.glob("Esteria*.bin") if "wings" not in p.name.casefold()}


def report(stack: Stack, picked: dict[str, str], bins: dict[str, Path]) -> dict:
    by_reason = defaultdict(lambda: [0, 0])
    total = comp = 0
    for key, why in picked.items():
        _, _, size, csize = stack.winner[key]
        total, comp = total + size, comp + csize
        bucket = by_reason[why if why.startswith(("race", "creator", "GlueXML", "racial", "CharSections")) else why.split(" of ")[0]]
        bucket[0] += 1
        bucket[1] += size
    extra = sum(p.stat().st_size for p in bins.values())
    return {"files": len(picked) + len(bins), "uncompressed": total + extra, "compressed_estimate": comp + extra,
            "by_reason": {k: v for k, v in sorted(by_reason.items())}, "bins": sorted(bins)}


def build(stack: Stack, picked: dict[str, str], bins: dict[str, Path], target: Path) -> dict:
    storm = stack.storm
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        target.unlink()
    archive = c.c_void_p()
    if not storm.dll.SFileCreateArchive(str(target), 0x00100000 | 0x00200000, len(picked) + len(bins) + 64, c.byref(archive)):
        raise OSError(f"SFileCreateArchive failed ({c.get_last_error()})")
    hashes: dict[str, str] = {}

    def write(name: str, payload: bytes):
        handle = c.c_void_p()
        if not storm.dll.SFileCreateFile(archive, name.encode("ascii"), 0, len(payload), 0, 0x00000200, c.byref(handle)):
            raise OSError(f"SFileCreateFile failed: {name} ({c.get_last_error()})")
        done = False
        try:
            if not storm.dll.SFileWriteFile(handle, c.create_string_buffer(payload or b"\0"), len(payload), 0x00000002):
                raise OSError(f"SFileWriteFile failed: {name} ({c.get_last_error()})")
            if not storm.dll.SFileFinishFile(handle):
                raise OSError(f"SFileFinishFile failed: {name} ({c.get_last_error()})")
            done = True
        finally:
            if not done:
                storm.dll.SFileCloseFile(handle)
        hashes[name.casefold()] = hashlib.sha256(payload).hexdigest()

    try:
        for index, key in enumerate(sorted(picked), 1):
            _, name, *_ = stack.winner[key]
            write(name, stack.read(key))
            if index % 2000 == 0:
                print(f"  wrote {index}/{len(picked)}")
        for name, path in sorted(bins.items()):
            write(name, path.read_bytes())
    finally:
        storm.dll.SFileCloseArchive(archive)
    # Read the finished archive back and compare every entry with its source bytes.
    check = storm.open_archive(target)
    try:
        for name, digest in hashes.items():
            if hashlib.sha256(storm.read(check, name)).hexdigest() != digest:
                raise AssertionError(f"read-back mismatch: {name}")
    finally:
        storm.dll.SFileCloseArchive(check)
    size = target.stat().st_size
    if size >= MAX_BYTES:
        raise AssertionError(f"{target} is {size} bytes, over the client's 2 GiB read limit")
    return {"entries": len(hashes), "bytes": size}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--client", type=Path, default=CLIENT)
    parser.add_argument("--stage", type=Path, default=STAGE)
    parser.add_argument("--plan", action="store_true")
    parser.add_argument("--build", action="store_true")
    parser.add_argument("--install", action="store_true")
    parser.add_argument("--list", type=Path, help="write the selected paths and reasons here")
    args = parser.parse_args()

    stack = Stack(Storm(DLL_DEFAULT), args.client)
    try:
        picked, bins = select(stack, args.client), esteria_bins(args.client)
        summary = report(stack, picked, bins)
        print(json.dumps(summary, indent=2))
        if args.list:
            args.list.write_text(json.dumps({k: [stack.winner[k][0].name, why] for k, why in sorted(picked.items())}, indent=1))
        if args.build:
            result = build(stack, picked, bins, args.stage / "Races.MPQ")
            print("built", result)
            if args.install:
                import shutil
                shutil.copy2(args.stage / "Races.MPQ", args.client / "Data" / "Races.MPQ")
                print("installed", args.client / "Data" / "Races.MPQ")
    finally:
        stack.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
