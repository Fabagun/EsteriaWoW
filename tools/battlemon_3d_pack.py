"""Bake the Battlemon 3D package into stand-alone patch MPQs, with no eDBC / WXL continuation files.

    python tools/battlemon_3d_pack.py --plan            # select + validate, write nothing
    python tools/battlemon_3d_pack.py --build           # stage the MPQs and the merged server DBCs, then read them back
    python tools/battlemon_3d_pack.py --build --install # ... and copy the MPQs into <client>/Data, retiring the old eDBC files

The package's CreatureDisplayInfo/CreatureModelData continuation layers are merged into the client's effective
tables (highest-priority archive wins, in the client's own mount order). The package's ``dbc1-battlemon`` layer
is a snapshot of someone else's whole table, so only its Battlemon rows are taken. Archives stay under the
classic 2 GiB size every other pack in this repo uses.

Not taken from the package: the Pokemon Trainer profession (Spell/Skill* layers, PokemonTrainer.lua) and its
Interface overrides; WorldStateFrame.xml there is older than the client's own copy.
"""

from __future__ import annotations

import argparse
import ctypes as c
import hashlib
import shutil
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cars_mount_pack import DBC_STRING_FIELDS, FindData, Storm, Wdbc, build_wdbc, merge_wdbc_continuations  # noqa: E402

DLL = Path(r"G:\Downloads\x64\StormLib.dll")
CLIENT = Path(r"G:\3.3.5a - Dev")
PACKAGE = Path(r"G:\Downloads\HDWoWModels\3d-version\client\Data\patch-z.mpq")
STAGE = Path(r"G:\RetroPorterWork\battlemon-3d")
BACKUP = CLIENT / "_backups" / "battlemon-edbc-retired"
# Sorts after Patch-ZzzSC2.MPQ, the last loose patch: the client mounts Data\patch-*.MPQ in name order, highest wins.
NAMES = ("Patch-ZzzzBattlemon.MPQ", "Patch-ZzzzBattlemon2.MPQ")
MAX_ARCHIVE_BYTES = int(1.8 * 1024 ** 3)
ASSET_ROOTS = ("Creature", "World")
BS = "\\"
DBC_STRING_FIELDS.setdefault("GameObjectDisplayInfo", (1,))
FLAG_COMPRESS = 0x00000200
COMPRESSION_ZLIB = 0x02


def key(path: str) -> str:
    return path.replace("/", BS).casefold()


class Mounts:
    """The client's archives in true priority order (see PatchFiles.cpp / OpenArchives), highest first."""

    def __init__(self, storm: Storm, client: Path):
        self.storm = storm
        data = client / "Data"
        loose = [p for p in [*data.glob("patch-*"), *(data / "enUS").glob("patch-enUS-*")] if p.suffix.casefold() == ".mpq"]
        # Pass 0 is sorted by full path, so enUS\ sorts below every Data\patch-*; patch.MPQ / patch-enUS.MPQ come last.
        loose = [p for p in loose if p.name not in NAMES]  # rebuilds merge into the client without our own earlier output
        ascending = sorted(loose, key=lambda p: str(p.relative_to(data)).casefold())
        pass_one = [p for p in (data / "patch.MPQ", data / "enUS" / "patch-enUS.MPQ") if p.exists()]
        base = [data / n for n in ("common.MPQ", "common-2.MPQ", "common-3.MPQ", "expansion.MPQ", "lichking.MPQ")]
        base += sorted((data / "enUS").glob("*-enUS.MPQ")) + sorted((data / "enUS").glob("*-locale-enUS.MPQ"))
        self.order = [p for p in [*base, *reversed(pass_one), *ascending] if p.exists()][::-1]
        self.handles: dict[Path, object] = {}

    def _open(self, path: Path):
        if path not in self.handles:
            handle = c.c_void_p()
            if not self.storm.dll.SFileOpenArchive(str(path), 0, 0x100, c.byref(handle)):
                raise OSError(f"SFileOpenArchive failed: {path} ({c.get_last_error()})")
            self.handles[path] = handle
        return self.handles[path]

    def read(self, name: str) -> tuple[bytes, Path]:
        for archive in self.order:
            if archive.is_dir():
                loose = archive / name.replace(BS, "/")
                if loose.is_file():
                    return loose.read_bytes(), archive
                continue
            try:
                return self.storm.read(self._open(archive), name), archive
            except OSError:
                continue
        raise FileNotFoundError(name)

    def close(self) -> None:
        for handle in self.handles.values():
            self.storm.dll.SFileCloseArchive(handle)
        self.handles.clear()


def shiny_to_70000(row: list[int]) -> list[int]:
    # The package puts shiny displays at 60001-61581, on top of EsteriaBroken's 60001-60086; this server uses 70001-71581.
    return [row[0] + 10000, *row[1:]] if 60000 < row[0] <= 61581 else row


def extras_to_400000(row: list[int], table: str) -> list[int]:
    # 200000/200001 belong to the native-retail Gravewing and Writhing Brood displays; the extras need their own range.
    # a display row also points at its model, which moves with it
    return [row[0] + 200000, row[1] + 200000, *row[2:]] if table == "CreatureDisplayInfo" else [row[0] + 200000, *row[1:]]


def subset(raw: bytes, table: str, keep, remap=lambda row: row) -> bytes:
    """Rows of a WDBC for which keep(wdbc, row) holds, strings re-pooled."""
    w = Wdbc(raw)
    rows = [remap(row) for row in w.rows if keep(w, row)]
    strings = {(i, f): w.text(row[f]) for i, row in enumerate(rows) for f in DBC_STRING_FIELDS.get(table, ()) if row[f] and w.text(row[f])}
    return build_wdbc(rows, w.fields, w.record_size, strings)


def package_layers() -> dict[str, list[bytes]]:
    """Per table, the continuation layers that belong to Battlemon, lowest layer first."""
    d = PACKAGE / "DBFilesClient"
    models = Wdbc((d / "CreatureModelData.dbc1-battlemon").read_bytes())
    shipped = {key(n) for n in asset_files()}  # removed-appearances.csv: the layer still lists models whose files were dropped
    is_bm = lambda w, r: (n := w.text(r[2]).casefold()).startswith("creature\\battlemon") and key(n.rsplit(".", 1)[0] + ".m2") in shipped  # noqa: E731
    bm_ids = {r[0] for r in models.rows if is_bm(models, r)}
    layers = {
        "CreatureModelData": [subset((d / "CreatureModelData.dbc1-battlemon").read_bytes(), "CreatureModelData", is_bm)],
        "CreatureDisplayInfo": [subset((d / "CreatureDisplayInfo.dbc1-battlemon").read_bytes(), "CreatureDisplayInfo", lambda w, r: r[1] in bm_ids, shiny_to_70000)],
        "GameObjectDisplayInfo": [],
    }
    for table in layers:
        for p in sorted(d.glob(f"{table}.dbc9-*")):
            raw = p.read_bytes()
            if p.name.endswith("pixelmon-extras"):
                raw = subset(raw, table, lambda w, r: True, lambda r, t=table: extras_to_400000(r, t))
            layers[table].append(raw)
    return layers


def _wdbc_bytes(fields: int, rows: list[list[int]], strings: bytes) -> bytes:
    body = b"".join(struct.pack(f"<{fields}I", *row) for row in rows)
    return struct.pack("<4s4I", b"WDBC", len(rows), fields, fields * 4, len(strings)) + body + strings


def append_layer(base: bytes, extra: bytes, table: str) -> bytes:
    """Base rows and string block stay byte-identical (the client has out-of-order rows and native code
    reads this table); the layer's rows are appended with their strings added to the end of the block."""
    left, right = Wdbc(base), Wdbc(extra)
    if (left.fields, left.record_size) != (right.fields, right.record_size):
        raise ValueError(f"continuation layout mismatch for {table}")
    pool, rows = bytearray(left.strings), [list(r) for r in left.rows]
    for row in sorted(right.rows, key=lambda r: r[0]):
        row = list(row)
        for f in DBC_STRING_FIELDS.get(table, ()):
            if row[f]:
                text = right.strings[row[f]:right.strings.index(b"\0", row[f])]
                row[f] = len(pool) if text else 0
                if text:
                    pool += text + b"\0"
        rows.append(row)
    return _wdbc_bytes(left.fields, rows, bytes(pool))


def drop_rows(raw: bytes, ids: set[int]) -> bytes:
    w = Wdbc(raw)
    return _wdbc_bytes(w.fields, [list(r) for r in w.rows if r[0] not in ids], w.strings)


def merge_tables(mounts: Mounts, layers: dict[str, list[bytes]], base_dir: Path | None = None) -> tuple[dict[str, bytes], dict[str, str]]:
    out, winners = {}, {}
    for table, extras in layers.items():
        name = f"DBFilesClient{BS}{table}.dbc"
        if base_dir:
            if not (base_dir / f"{table}.dbc").exists():  # the server only overrides some tables
                continue
            base, winners[table] = (base_dir / f"{table}.dbc").read_bytes(), str(base_dir)
            # A server folder that already took an earlier run: drop those rows (ours, incl. the old 200000 extras) first.
            ours = {r[0] for extra in extras for r in Wdbc(extra).rows} | set(range(200000, 200980))
            base = drop_rows(base, ours)
        else:
            base, source = mounts.read(name)
            winners[table] = source.name
        have = {r[0] for r in Wdbc(base).rows}
        for extra in extras:
            clash = have & {r[0] for r in Wdbc(extra).rows}
            if clash:
                raise ValueError(f"{table}: {len(clash)} package ids already exist in the base table, e.g. {sorted(clash)[:5]}")
            merged = append_layer(base, extra, table)
            before, after = Wdbc(base), Wdbc(merged)
            assert after.rows[:before.count] == before.rows and after.strings.startswith(before.strings), table
            base = merged
            have = {r[0] for r in Wdbc(base).rows}
        out[table] = base
    return out, winners


def asset_files() -> dict[str, Path]:
    files = {}
    for root in ASSET_ROOTS:
        for path in (PACKAGE / root).rglob("*"):
            if path.is_file():
                files[str(path.relative_to(PACKAGE)).replace("/", BS)] = path
    return files


def validate(merged: dict[str, bytes], assets: dict[str, Path], layers: dict[str, list[bytes]]) -> list[str]:
    problems = []
    added_displays = {r[0] for raw in layers["CreatureDisplayInfo"] for r in Wdbc(raw).rows}
    have = {key(n) for n in assets}
    models, displays = Wdbc(merged["CreatureModelData"]), Wdbc(merged["CreatureDisplayInfo"])
    model_ids = {r[0] for r in models.rows}
    for r in models.rows:
        name = models.text(r[2])
        if name.casefold().startswith(("creature\\battlemon", "creature\\pokemontrainers")):
            stem = name.rsplit(".", 1)[0]
            for suffix in (".m2", "00.skin"):
                if key(stem + suffix) not in have:
                    problems.append(f"model {r[0]}: missing {stem + suffix}")
    problems += [f"display {r[0]}: unknown model {r[1]}" for r in displays.rows if r[0] in added_displays and r[1] not in model_ids]
    godi = Wdbc(merged["GameObjectDisplayInfo"])
    problems += [f"gameobject display {r[0]}: missing {godi.text(r[1])}" for r in godi.rows if godi.text(r[1]).casefold().startswith("world\\wmo\\battlemon") and key(godi.text(r[1])) not in have]
    return problems


def write_archives(storm: Storm, stage: Path, entries: list[tuple[str, bytes | Path]]) -> list[Path]:
    """Compressed v1 archives, a new one whenever the current would pass MAX_ARCHIVE_BYTES."""
    made, handle, current = [], None, None
    capacity = len(entries) + 16

    def close():
        if handle is not None:
            storm.dll.SFileCloseArchive(handle)

    try:
        for name, source in entries:
            if handle is None or current.stat().st_size > MAX_ARCHIVE_BYTES:
                close()
                if len(made) == len(NAMES):
                    raise ValueError("payload needs more archives than NAMES provides")
                current = stage / NAMES[len(made)]
                current.unlink(missing_ok=True)
                handle = c.c_void_p()
                if not storm.dll.SFileCreateArchive(str(current), 0x1 | 0x2, capacity, c.byref(handle)):
                    raise OSError(f"SFileCreateArchive failed: {current} ({c.get_last_error()})")
                made.append(current)
            payload = source if isinstance(source, bytes) else source.read_bytes()
            file_handle = c.c_void_p()
            if not storm.dll.SFileCreateFile(handle, name.encode("ascii"), 0, len(payload), 0, FLAG_COMPRESS, c.byref(file_handle)):
                raise OSError(f"SFileCreateFile failed: {name} ({c.get_last_error()})")
            try:
                if not storm.dll.SFileWriteFile(file_handle, c.create_string_buffer(payload or b"\0"), len(payload), COMPRESSION_ZLIB):
                    raise OSError(f"SFileWriteFile failed: {name} ({c.get_last_error()})")
            finally:
                storm.dll.SFileCloseFile(file_handle)
    finally:
        close()
    return made


def verify(storm: Storm, archives: list[Path], entries: list[tuple[str, bytes | Path]]) -> None:
    expected = {key(n): s for n, s in entries}
    seen = set()
    for archive in archives:
        handle = storm.open_archive(archive)
        try:
            for name, size, comp, _ in storm.list_files(handle):
                if name.startswith("("):
                    continue
                source = expected.get(key(name))
                if source is None:
                    raise AssertionError(f"{archive.name}: unexpected {name}")
                seen.add(key(name))
                if isinstance(source, bytes) or size < 4096 or hash(name) % 40 == 0:  # DBCs always, other files sampled
                    want = source if isinstance(source, bytes) else source.read_bytes()
                    if hashlib.sha256(storm.read(handle, name)).digest() != hashlib.sha256(want).digest():
                        raise AssertionError(f"{archive.name}: {name} differs from source")
        finally:
            storm.dll.SFileCloseArchive(handle)
    if seen != set(expected):
        raise AssertionError(f"{len(set(expected) - seen)} files missing from the archives")


def install(archives: list[Path]) -> None:
    data = CLIENT / "Data"
    BACKUP.mkdir(parents=True, exist_ok=True)
    retired = [data / "dbc-continuations" / n for n in ("CreatureDisplayInfo.dbc1-battlemon", "CreatureModelData.dbc1-battlemon")]
    retired += [data / "patch-K.mpq" / "DBFilesClient" / n for n in ("CreatureDisplayInfo.dbc1-battlemon", "CreatureModelData.dbc1-battlemon")]
    retired += [data / "patch-K.mpq" / "Creature"]
    for path in retired:
        if path.exists():
            target = BACKUP / path.relative_to(data)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(path), str(target))
            print("retired", path, "->", target)
    for archive in archives:
        shutil.copy2(archive, data / archive.name)
        print("installed", data / archive.name)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--build", action="store_true")
    ap.add_argument("--install", action="store_true")
    ap.add_argument("--server-dbc", type=Path, help="server dbc folder: also write merged server DBCs next to the stage")
    args = ap.parse_args()
    if not (args.plan or args.build):
        ap.error("pass --plan or --build")

    storm = Storm(DLL)
    mounts = Mounts(storm, CLIENT)
    try:
        layers = package_layers()
        merged, winners = merge_tables(mounts, layers)
    finally:
        mounts.close()
    assets = asset_files()
    problems = validate(merged, assets, layers)
    for table, raw in merged.items():
        print(f"{table}: base from {winners[table]}, {Wdbc(raw).count} rows after merge")
    print(f"assets: {len(assets)} files, {sum(p.stat().st_size for p in assets.values()) / 1024 ** 3:.2f} GiB uncompressed")
    print(f"problems: {len(problems)}", *problems[:10], sep="\n  ")
    if problems:
        return 1
    if args.plan:
        return 0

    STAGE.mkdir(parents=True, exist_ok=True)
    entries: list[tuple[str, bytes | Path]] = [(f"DBFilesClient{BS}{t}.dbc", raw) for t, raw in merged.items()]
    entries += sorted(assets.items())
    archives = write_archives(storm, STAGE, entries)
    for a in archives:
        print(f"built {a} {a.stat().st_size / 1024 ** 3:.2f} GiB")
    verify(storm, archives, entries)
    print("read-back verified")
    if args.server_dbc:
        server, _ = merge_tables(mounts, layers, args.server_dbc)
        out = STAGE / "server-dbc"
        out.mkdir(exist_ok=True)
        for t, raw in server.items():
            (out / f"{t}.dbc").write_bytes(raw)
        print("server DBCs ->", out)
    if args.install:
        install(archives)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
