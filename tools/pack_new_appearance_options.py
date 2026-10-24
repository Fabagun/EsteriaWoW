r"""Additional appearance options as one patch MPQ: new textures plus the catalogs that select them.

    python tools/pack_new_appearance_options.py

Catalogs are rebuilt from the base Esteria\\ catalog MPQ (pack_appearance_catalogs.py), so the script can be re-run.
Option counts live in CreatureAppearance.h (client WoW/Common/ComponentCore and server src/server/shared) and must match.

* Venthyr male: skin choices 7..13 from vampire_male_body_1..7.blp.
* Nightborne male (retail-driven race 17): faces 12..17 from Niceborne, through Esteria\RetailExtras.txt (see nightborne_faces).
* Forgotten (races 58/59): face 1 from thinhumanmale{faceupper,skin}00_0N.blp. Each skin tone N uses its own pair when
  one is supplied and the tone-2 pair otherwise. Face 1 needs CharSections rows (client DBC in the MPQ, server DBC patched
  in place with a backup), because the creator counts faces from those rows.
"""
from __future__ import annotations

import ctypes as c
import shutil
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cars_mount_pack import Storm  # noqa: E402

DLL = Path(r"G:\Downloads\x64\StormLib.dll")
CLIENT = Path(r"G:\3.3.5a - Dev")
BASE = CLIENT / "Data" / "Patch-ZzzzzCatalogs.MPQ"
TARGET = CLIENT / "Data" / "Patch-ZzzzzNewOptions.MPQ"  # sorts after the base catalogs, so its files win
CLIENT_DBC = CLIENT / "Data" / "patch-Z.MPQ"  # winning CharSections.dbc
SERVER_DBC = Path(r"R:\Users\Zach\Documents\GitHub\EsteriaWoW\modules\mod-custom-server\data\dbc\retroported-races\CharSections.dbc")
SOURCE = Path(r"G:\Downloads\HDWoWModels")
FLAG_COMPRESS = 0x00000200
COMPRESSION_ZLIB = 0x02

RECORD = struct.Struct("<7I128s")
UNCONDITIONAL = 0xFFFFFFFF


def selector(option: int, value: int) -> int:
    return option | value << 16


def record(gender: int, kind: int, target: int, value: int, choices: tuple[int, ...], path: str) -> bytes:
    padded = (choices + (UNCONDITIONAL,) * 3)[:3]
    return RECORD.pack(gender, kind, target, value, *padded, path.encode("ascii"))


def parse(catalog: bytes) -> list[list]:
    magic, version, count = struct.unpack_from("<3I", catalog)
    assert magic == 0x314D4845 and version == 1 and len(catalog) == 12 + count * RECORD.size
    return [list(RECORD.unpack_from(catalog, 12 + i * RECORD.size)) for i in range(count)]


def build(records: list[list]) -> bytes:
    return struct.pack("<3I", 0x314D4845, 1, len(records)) + b"".join(RECORD.pack(*r) for r in records)


def venthyr_male(catalog: bytes) -> tuple[bytes, dict[str, bytes]]:
    records, files = parse(catalog), {}
    for n in range(1, 8):
        skin = 6 + n  # existing skins are 0..6
        path = rf"custom\venthyr\native\textures\vampire_male_body_{n}.blp"
        files[path] = (SOURCE / f"vampire_male_body_{n}.blp").read_bytes()
        records.append(list(RECORD.unpack(record(0, 1, 11, 0, (selector(0, skin),), path))))  # body slot 11, option 0 == skin
    return build(records), files


def lznt1(pixels: bytes) -> bytes:
    ntdll = c.windll.ntdll
    work, fragment = c.c_ulong(), c.c_ulong()
    assert ntdll.RtlGetCompressionWorkSpaceSize(2, c.byref(work), c.byref(fragment)) == 0
    out = c.create_string_buffer(len(pixels) + len(pixels) // 8 + 4096)
    size = c.c_ulong()
    assert ntdll.RtlCompressBuffer(2, pixels, len(pixels), out, len(out), 4096, c.byref(size), c.create_string_buffer(work.value)) == 0
    return out.raw[:size.value]


def unlznt1(packed: bytes, length: int) -> bytes:
    out, size = c.create_string_buffer(length), c.c_ulong()
    assert c.windll.ntdll.RtlDecompressBuffer(2, out, length, packed, len(packed), c.byref(size)) == 0 and size.value == length
    return out.raw


def forgotten_face(catalog: bytes, bank: bytes) -> tuple[bytes, bytes]:
    from PIL import Image

    def rgba(path: Path, box=None) -> bytes:
        image = Image.open(path).convert("RGBA")
        return (image.crop(box) if box else image).tobytes()

    records, bank = parse(catalog), bytearray(bank)
    magic, version, count, tail = struct.unpack_from("<4I", bank)
    assert magic == 0x31544845 and version == 1
    # Skin-only layers apply to face 0 only; face 1 brings its own body and face art for every tone.
    for r in records:
        if r[1] == 3 and r[2] == 0 and r[4] != UNCONDITIONAL and r[4] & 0xFFFF == 0 and r[5] == UNCONDITIONAL:
            r[5] = selector(1, 0)
    extra = 0
    for tone in range(4):
        pair = (SOURCE / f"thinhumanmalefaceupper00_0{tone}.blp", SOURCE / f"thinhumanmaleskin00_0{tone}.blp")
        if not all(p.exists() for p in pair):
            pair = (SOURCE / "thinhumanmalefaceupper00_02.blp", SOURCE / "thinhumanmaleskin00_02.blp")
        # (group, blend path, pixels): the face atlas overlays the base face, the body replaces the base skin.
        for group, path, pixels in ((4, "5:15", rgba(pair[0])), (0, "1:1", rgba(pair[1], (0, 0, 512, 512)))):
            assert len(pixels) == 512 * 512 * 4
            packed = lznt1(pixels)
            assert unlznt1(packed, len(pixels)) == pixels
            offset = len(bank)
            bank += struct.pack("<3I", 512, 512, len(packed)) + packed
            row = [0, 3, group, offset, selector(1, 1), selector(0, tone), UNCONDITIONAL, path.encode("ascii")]
            # Layers compose in catalog order: the face goes under the eyebrow overlays, which are the first 8:15 rows.
            records.insert(next((i for i, r in enumerate(records) if r[1] == 3 and r[7].startswith(b"8:15")), len(records)) if group == 4 else len(records), row)
            extra += 1
    struct.pack_into("<4I", bank, 0, magic, version, count + extra, tail)
    return build(records), bytes(bank)


def nightborne_faces() -> dict[str, bytes]:
    """Six extra retail-model faces for Nightborne male, from the Niceborne pack.

    The client clones retail face choice 2693+k (option 234) as choice 9000001+k, with one material per skin tone.
    Tones 2689..2691 use the pack's _00.._02 files; the other tones show the face's _00 texture. File ids 8800000+ are
    the client's synthetic range (RetailRace.cpp) and map to custom\\nightborne\\faces\\<id>.blp.
    """
    files, lines = {}, ["# face <option> <source choice> <new choice> <default file> <skin choice>=<file> ..."]
    for face in range(6):
        ids = [8800000 + face * 3 + tone for tone in range(3)]
        for tone, fdid in enumerate(ids):
            files[rf"custom\nightborne\faces\{fdid}.blp"] = (SOURCE / "Niceborne" / f"nightbornemalefaceupper{face:02d}_{tone:02d}.blp").read_bytes()
        skins = " ".join(f"{2689 + tone}={fdid}" for tone, fdid in enumerate(ids))
        lines.append(f"face 234 {2693 + face} {9000001 + face} {ids[0]} {skins}")
    files[r"Esteria\RetailExtras.txt"] = ("\n".join(lines) + "\n").encode("ascii")
    return files


def charsections(dbc: bytes) -> bytes:
    """Face 1 (kind 1, variation 1) for Forgotten race 58/59, one row per skin tone; idempotent."""
    magic, count, fields, size, strings = struct.unpack_from("<4sIIII", dbc)
    assert magic == b"WDBC" and fields == 10 and size == 40
    table = [struct.unpack_from("<10I", dbc, 20 + i * size) for i in range(count)]
    if any(r[1] in (58, 59) and r[3] == 1 and r[8] == 1 for r in table):
        return dbc
    next_id = max(r[0] for r in table) + 1
    added = []
    for race in (58, 59):
        for tone in range(4):
            added.append(struct.pack("<10I", next_id, race, 0, 1, 0, 0, 0, 1, 1, tone))
            next_id += 1
    body = dbc[20:20 + count * size]
    return struct.pack("<4sIIII", magic, count + len(added), fields, size, strings) + body + b"".join(added) + dbc[20 + count * size:]


def main() -> None:
    storm = Storm(DLL)
    base = storm.open_archive(BASE)
    try:
        venthyr, files = venthyr_male(storm.read(base, r"Esteria\EsteriaVenthyr.bin"))
        human, bank = forgotten_face(storm.read(base, r"Esteria\EsteriaThinHuman.bin"), storm.read(base, r"Esteria\EsteriaThinHumanTextures.bin"))
    finally:
        storm.dll.SFileCloseArchive(base)
    source = storm.open_archive(CLIENT_DBC)
    try:
        client_dbc = charsections(storm.read(source, r"DBFilesClient\CharSections.dbc"))
    finally:
        storm.dll.SFileCloseArchive(source)
    entries = {
        r"Esteria\EsteriaVenthyr.bin": venthyr,
        r"Esteria\EsteriaThinHuman.bin": human,
        r"Esteria\EsteriaThinHumanTextures.bin": bank,
        r"DBFilesClient\CharSections.dbc": client_dbc,
        **files,
        **nightborne_faces(),
    }

    TARGET.unlink(missing_ok=True)
    handle = c.c_void_p()
    if not storm.dll.SFileCreateArchive(str(TARGET), 0x1 | 0x2, len(entries) + 16, c.byref(handle)):
        raise OSError(f"SFileCreateArchive failed: {TARGET} ({c.get_last_error()})")
    try:
        for name, payload in entries.items():
            file_handle = c.c_void_p()
            if not storm.dll.SFileCreateFile(handle, name.encode("ascii"), 0, len(payload), 0, FLAG_COMPRESS, c.byref(file_handle)):
                raise OSError(f"SFileCreateFile failed: {name} ({c.get_last_error()})")
            try:
                if not storm.dll.SFileWriteFile(file_handle, c.create_string_buffer(payload), len(payload), COMPRESSION_ZLIB):
                    raise OSError(f"SFileWriteFile failed: {name} ({c.get_last_error()})")
            finally:
                storm.dll.SFileCloseFile(file_handle)
    finally:
        storm.dll.SFileCloseArchive(handle)

    archive = storm.open_archive(TARGET)
    try:
        for name, payload in entries.items():
            if storm.read(archive, name) != payload:
                sys.exit(f"readback mismatch: {name}")
    finally:
        storm.dll.SFileCloseArchive(archive)
    print(f"{TARGET}: {len(entries)} files, readback ok")

    server = SERVER_DBC.read_bytes()
    patched = charsections(server)
    if patched != server:
        backup = SERVER_DBC.with_name(SERVER_DBC.name + ".pre-forgotten-face")
        if not backup.exists():
            shutil.copy2(SERVER_DBC, backup)
        SERVER_DBC.write_bytes(patched)
        print(f"{SERVER_DBC}: Forgotten face 1 rows added (backup {backup.name}); recreate ac-worldserver to load them")


if __name__ == "__main__":
    main()
