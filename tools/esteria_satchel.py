"""Stage Esteria's 237-slot bag without installing, compiling, or changing the database.

Art is only tiled/converted, never redrawn. The source PNG remains outside Git.
The full Item.dbc preserves the effective custom client's existing rows and strings.
"""

from __future__ import annotations

import argparse
import ctypes as c
import hashlib
import json
from pathlib import Path
import re
import shutil
import struct

from PIL import Image

from cars_mount_pack import DLL_DEFAULT, H, Storm, Wdbc

ROOT = Path(__file__).resolve().parents[1]
ADDON = ROOT / "client-customization/EsteriaSatchel"
MIGRATION = ROOT / "data/sql/updates/pending_db_world/rev_20261017230000000_esteria_satchel.sql"
ITEM = 910237
ARCHIVE = "Patch-ZzzSatchel.MPQ"
DRAGON = "Interface/AddOns/DragonUI/modules/bagster"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def effective(storm: Storm, client: Path, key: str) -> tuple[bytes, Path, list[dict]]:
    # Matches PatchFiles.cpp's descending full-path order and Client.cpp's priorities.
    patches = [p for directory, prefix in ((client / "Data", "patch-"),
                                           (client / "Data/enUS", "patch-enus-"))
               for p in directory.glob("*")
               if p.is_file() and p.name.lower().startswith(prefix)
               and p.suffix.lower() == ".mpq" and p.name.lower() != ARCHIVE.lower()]
    patches.sort(key=lambda p: str(p.relative_to(client)).replace("/", "\\").upper(), reverse=True)
    providers = []
    winner = None
    for path in patches:
        archive = storm.open_archive(path)
        try:
            try:
                data = storm.read(archive, key)
            except OSError:
                continue
            providers.append({"path": str(path), "sha256": digest(data)})
            if winner is None:
                winner = data, path
        finally:
            storm.dll.SFileCloseArchive(archive)
    if winner is None:
        raise ValueError(f"No patch provider for {key}; inspect base archives explicitly")
    return *winner, providers


def item_table(original: bytes) -> bytes:
    table = Wdbc(original)
    assert (table.fields, table.record_size) == (8, 32)
    assert all(row[0] != ITEM for row in table.rows), f"Item {ITEM} is already allocated"
    donor = table.row(51809)
    assert donor[1] == 1 and donor[5:7] == [64151, 18], donor
    donor[0] = ITEM
    # Append the one new row while retaining all original bytes/string offsets.
    end = 20 + table.count * table.record_size
    header = struct.pack("<4s4I", b"WDBC", table.count + 1, 8, 32, len(table.strings))
    result = header + original[20:end] + struct.pack("<8I", *donor) + original[end:]
    check = Wdbc(result)
    assert check.rows[:-1] == table.rows and check.strings == table.strings
    return result


def compressed_mpq(storm: Storm, path: Path, entries: dict[str, bytes]) -> None:
    if path.exists():
        raise FileExistsError(path)
    archive = H()
    if not storm.dll.SFileCreateArchive(str(path), 0x00100000 | 0x00200000,
                                       len(entries) + 64, c.byref(archive)):
        raise OSError(f"SFileCreateArchive failed: {c.get_last_error()}")
    try:
        for name, data in entries.items():
            handle = H()
            if not storm.dll.SFileCreateFile(archive, name.encode("ascii"), 0, len(data), 0,
                                            0x00000200, c.byref(handle)):
                raise OSError(f"SFileCreateFile failed: {name}")
            finished = False
            try:
                buffer = c.create_string_buffer(data)
                if not storm.dll.SFileWriteFile(handle, buffer, len(data), 0x00000002):
                    raise OSError(f"SFileWriteFile failed: {name}")
                if not storm.dll.SFileFinishFile(handle):
                    raise OSError(f"SFileFinishFile failed: {name}")
                finished = True
            finally:
                if not finished:
                    storm.dll.SFileCloseFile(handle)
    finally:
        storm.dll.SFileCloseArchive(archive)
    archive = storm.open_archive(path)
    try:
        for name, data in entries.items():
            assert storm.read(archive, name) == data, name
        payload_names = {name.lower() for name, *_ in storm.list_files(archive)
                         if not name.startswith("(")}
        assert payload_names == {name.lower() for name in entries}
    finally:
        storm.dll.SFileCloseArchive(archive)


def stage(client: Path, source: Path, out: Path, storm: Storm) -> None:
    out.mkdir(parents=True, exist_ok=False)
    image = Image.open(source).convert("RGBA")
    assert image.size == (1122, 1402), image.size
    shutil.copy2(source, out / "source.png")
    client_stage = out / "client"
    addon = client_stage / "Interface/AddOns/EsteriaSatchel"
    shutil.copytree(ADDON, addon)
    art = addon / "Art"
    art.mkdir()
    restored = Image.new("RGBA", image.size)
    for row in range(3):
        for col in range(3):
            x, y = col * 512, row * 512
            w, h = min(512, image.width - x), min(512, image.height - y)
            tile = Image.new("RGBA", (512, 512))
            tile.paste(image.crop((x, y, x + w, y + h)), (0, 0))
            target = art / f"Bag{row}{col}.tga"
            tile.save(target, compression=None)
            decoded = Image.open(target).convert("RGBA")
            restored.paste(decoded.crop((0, 0, w, h)), (x, y))
    assert restored.tobytes() == image.tobytes(), "RGBA conversion changed source pixels"
    original, provider, providers = effective(storm, client, "DBFilesClient/Item.dbc")
    table_path = client_stage / "DBFilesClient/Item.dbc"
    table_path.parent.mkdir()
    table_path.write_bytes(item_table(original))
    baseline = out / "baseline"
    baseline.mkdir()
    (baseline / "Item.dbc").write_bytes(original)
    compat = []
    for filename, old, new in (
        ("bagster_data.lua", "bagId * 100", "bagId * 1000"),
        ("bagster_classes.lua", "bag * 100", "bag * 1000"),
    ):
        path = client / DRAGON / filename
        if not path.exists():
            continue
        data = path.read_bytes()
        text = data.decode("utf-8")
        # Exactly the two positive/negative-key expressions; never alter other numbers.
        pattern = re.escape(old) + r"\b"
        if len(re.findall(pattern, text)) == 2:
            text = re.sub(pattern, new, text)
        elif text.count(new) != 2:
            raise ValueError(f"Unexpected DragonUI index expression in {path}; inspect before changing")
        target = client_stage / DRAGON / filename
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(text.encode("utf-8"))
        compat.append({"relative": f"{DRAGON}/{filename}", "baseline_sha256": digest(data),
                       "staged_sha256": digest(target.read_bytes())})
    entries = {str(p.relative_to(client_stage)).replace("/", "\\"): p.read_bytes()
               for p in client_stage.rglob("*") if p.is_file()}
    compressed_mpq(storm, out / ARCHIVE, entries)
    shutil.copy2(MIGRATION, out / MIGRATION.name)
    report = {
        "status": "packaged; builds/installation and in-game acceptance pending",
        "client": str(client), "item": ITEM, "name": "Esteria Grand Satchel", "slots": 237,
        "source": str(source), "source_sha256": digest(source.read_bytes()),
        "source_dimensions": list(image.size), "art_rgba_roundtrip": True,
        "archive": ARCHIVE, "archive_sha256": digest((out / ARCHIVE).read_bytes()),
        "entries": {name: digest(data) for name, data in entries.items()},
        "item_baseline": {"path": str(provider), "sha256": digest(original), "providers": providers},
        "dragonui": compat,
        "layout": {"quest_slots": 25, "max_classes": 32, "container_slots": 254,
                   "container_dwords": 574, "active_player_dwords": 1326, "update_mask_words": 42},
        "client_executable_baseline_sha256": digest((client / "WowClientRetailVulkan.exe").read_bytes()),
        "migration": MIGRATION.name,
    }
    (out / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Packaged {len(entries)} entries, exact RGBA round-trip, Item.dbc rows preserved: {out}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--client", type=Path, default=Path("G:/3.3.5a - Dev"))
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--stormlib", type=Path, default=DLL_DEFAULT)
    args = parser.parse_args()
    stage(args.client, args.source, args.out, Storm(args.stormlib))
