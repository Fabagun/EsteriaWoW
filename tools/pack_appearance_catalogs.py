"""Pack every Esteria*.bin appearance catalog into one patch MPQ under Esteria\\, where the decomp client reads them.

    python tools/pack_appearance_catalogs.py            # build in the client's Data folder and read it back
"""
from __future__ import annotations

import argparse
import ctypes as c
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cars_mount_pack import Storm  # noqa: E402

DLL = Path(r"G:\Downloads\x64\StormLib.dll")
CLIENT = Path(r"G:\3.3.5a - Dev")
# Sorts after Patch-ZzzzBattlemon.MPQ; the paths are unique, so load order does not matter.
NAME = "Patch-ZzzzzCatalogs.MPQ"
FLAG_COMPRESS = 0x00000200
COMPRESSION_ZLIB = 0x02


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--client", type=Path, default=CLIENT)
    args = parser.parse_args()

    sources = sorted(args.client.glob("Esteria*.bin"))
    if not sources:
        sys.exit(f"no Esteria*.bin in {args.client}")
    target = args.client / "Data" / NAME
    storm = Storm(DLL)

    target.unlink(missing_ok=True)
    handle = c.c_void_p()
    if not storm.dll.SFileCreateArchive(str(target), 0x1 | 0x2, len(sources) + 16, c.byref(handle)):
        raise OSError(f"SFileCreateArchive failed: {target} ({c.get_last_error()})")
    try:
        for source in sources:
            payload = source.read_bytes()
            name = f"Esteria\\{source.name}".encode("ascii")
            file_handle = c.c_void_p()
            if not storm.dll.SFileCreateFile(handle, name, 0, len(payload), 0, FLAG_COMPRESS, c.byref(file_handle)):
                raise OSError(f"SFileCreateFile failed: {source.name} ({c.get_last_error()})")
            try:
                if not storm.dll.SFileWriteFile(file_handle, c.create_string_buffer(payload or b"\0"), len(payload), COMPRESSION_ZLIB):
                    raise OSError(f"SFileWriteFile failed: {source.name} ({c.get_last_error()})")
            finally:
                storm.dll.SFileCloseFile(file_handle)
    finally:
        storm.dll.SFileCloseArchive(handle)

    archive = storm.open_archive(target)
    try:
        for source in sources:
            if storm.read(archive, f"Esteria\\{source.name}") != source.read_bytes():
                sys.exit(f"readback mismatch: {source.name}")
    finally:
        storm.dll.SFileCloseArchive(archive)
    print(f"{target}: {len(sources)} catalogs, {target.stat().st_size} bytes, readback ok")


if __name__ == "__main__":
    main()
