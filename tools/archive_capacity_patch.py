"""Guard every boot archive-slot write in the fingerprinted Esteria executable."""

import argparse
import hashlib
import json
import os
import shutil
import struct
import subprocess
from datetime import datetime
from pathlib import Path

from native_appearance_patch import align
from wow_xref import Pe

CLIENT = Path("G:/3.3.5a - Dev/Wow.exe")
STAGE = Path("C:/Users/Zach/.codex/tmp/archive-capacity-20261007")
EXPECTED = "cee5c80cbfb9723f5f180837eab5b1e83a99ae1dadfd2287c872099b19ce88d0"
SITES = (
    (0x00405E90, "a140fab200", "89f8"),       # Loose/named patch scan: EDI is the slot.
    (0x00404963, "8b0d40fab200", "8b450c"),   # Required/optional archives: stack argument is the slot.
    (0x00405FD6, "8b1540fab200", "89f8"),     # Nested alternate archives: EDI is the slot.
    (0x00406040, "8b1540fab200", "89f8"),     # Reserved-slot clear, before the optional mount.
)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def branch(opcode, address, target):
    return opcode + struct.pack("<i", target - address - len(opcode) - 4)


def patch(source=CLIENT, output=STAGE / "Wow.exe"):
    pe = Pe(source)
    if digest(source) != EXPECTED:
        raise ValueError("Client image differs from the audited archive-overflow image")
    signature = b"ESTERIA_CLIENT_FOUNDATION_V3"
    if pe.read_va(0x00DFE000, len(signature)) != signature:
        raise ValueError("Client foundation fingerprint differs")
    if pe.read_va(0x004037F0, 13) != bytes.fromhex("558bec8b45085356576a106afe"):
        raise ValueError("Native array-resize entry differs")
    if pe.read_va(0x00403879, 5) != bytes.fromhex("5f5e5b5dc2"):
        raise ValueError("Native array-resize epilogue differs")

    data = bytearray(pe.data)
    nt = struct.unpack_from("<I", data, 0x3C)[0]
    optional = nt + 24
    count, size = struct.unpack_from("<H", data, nt + 6)[0], struct.unpack_from("<H", data, nt + 20)[0]
    header = optional + size + count * 40
    if header + 40 > min(s[4] for s in pe.sections):
        raise ValueError("No spare PE section header")
    if struct.unpack_from("<H", data, optional + 70)[0] & 0x40:
        raise ValueError("ASLR requires relocated archive guards")
    section_align, file_align = struct.unpack_from("<II", data, optional + 32)
    rva = align(max(s[1] + max(s[2], s[3]) for s in pe.sections), section_align)
    base = pe.image_base + rva
    blob = bytearray(b"ESTERIA_ARCHIVE_CAPACITY_V1\0")

    def add(payload):
        offset = align(len(blob), 16)
        blob.extend(bytes(offset - len(blob)))
        blob.extend(payload)
        return base + offset

    helper = base + align(len(blob), 16)
    # EAX is the slot index. Preserve all registers/flags and the native logical count.
    # Native resize's allocation fallback copies `count` slots, so expose the entire old capacity
    # during growth. This also preserves entries on subsequent 128 -> 192 -> ... expansions.
    code = bytearray.fromhex("9c603b0538fab2000f82000000008b353cfab2008b1538fab20089153cfab200"
                             "83c04083e0c050b938fab200")
    code.extend(branch(b"\xe8", helper + len(code), 0x004037F0))
    code.extend(bytes.fromhex("89353cfab200"))
    done = helper + len(code)
    struct.pack_into("<i", code, 10, done - (helper + 14))
    code.extend(bytes.fromhex("619dc3"))
    assert add(code) == helper
    sites = []
    for va, expected_hex, index_hex in SITES:
        expected = bytes.fromhex(expected_hex)
        if pe.read_va(va, len(expected)) != expected:
            raise ValueError(f"Archive-slot load fingerprint differs at {va:x}")
        thunk = base + align(len(blob), 16)
        wrapper = bytearray(b"\x50" + bytes.fromhex(index_hex))
        wrapper.extend(branch(b"\xe8", thunk + len(wrapper), helper))
        wrapper.extend(b"\x58" + expected)
        wrapper.extend(branch(b"\xe9", thunk + len(wrapper), va + len(expected)))
        assert add(wrapper) == thunk
        raw = next(raw + va - pe.image_base - start for _, start, _, raw_size, raw in pe.sections
                   if start <= va - pe.image_base < start + raw_size)
        replacement = branch(b"\xe9", va, thunk) + b"\x90" * (len(expected) - 5)
        data[raw:raw + len(expected)] = replacement
        sites.append({"va": va, "raw": raw, "before": expected.hex(), "after": replacement.hex(),
                      "thunk": thunk, "length": len(wrapper)})

    raw = align(len(data), file_align)
    data.extend(bytes(raw - len(data)))
    data.extend(blob)
    raw_size = align(len(blob), file_align)
    data.extend(bytes(raw_size - len(blob)))
    struct.pack_into("<8s8I", data, header, b".empq\0\0\0", len(blob), rva, raw_size, raw, 0, 0, 0, 0x60000020)
    struct.pack_into("<H", data, nt + 6, count + 1)
    struct.pack_into("<I", data, optional + 4, struct.unpack_from("<I", data, optional + 4)[0] + raw_size)
    struct.pack_into("<I", data, optional + 56, align(rva + len(blob), section_align))
    struct.pack_into("<I", data, optional + 64, 0)
    # Prove the existing image is byte-for-byte preserved outside the four jumps and PE metadata.
    restored = bytearray(data[:len(pe.data)])
    for site in sites:
        restored[site["raw"]:site["raw"] + len(bytes.fromhex(site["before"]))] = bytes.fromhex(site["before"])
    for offset, length in ((nt + 6, 2), (optional + 4, 4), (optional + 56, 4),
                           (optional + 64, 4), (header, 40)):
        restored[offset:offset + length] = pe.data[offset:offset + length]
    if restored != pe.data:
        raise ValueError("Patch changed unrelated existing image bytes")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(data)
    result = {"source_sha256": EXPECTED, "patched_sha256": digest(output), "source": str(source),
              "output": str(output), "section_va": base, "helper_va": helper, "helper_length": len(code),
              "sites": sites}
    (output.parent / "archive-patch-report.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def install(source=CLIENT, staged=STAGE / "Wow.exe"):
    processes = subprocess.check_output(["tasklist", "/FO", "CSV", "/NH"], text=True).lower()
    if '"wow.exe"' in processes or '"eclipse.exe"' in processes:
        raise RuntimeError("WoW/Eclipse must be closed before replacing the executable")
    report = json.loads((staged.parent / "archive-patch-report.json").read_text())
    if digest(source) != report["source_sha256"] or digest(staged) != report["patched_sha256"]:
        raise ValueError("Live or staged executable changed since patch preparation")
    backup = source.parent / "Backups" / ("archive-capacity-" + datetime.now().strftime("%Y%m%d-%H%M%S"))
    backup.mkdir(parents=True, exist_ok=False)
    shutil.copy2(source, backup / source.name)
    if digest(backup / source.name) != report["source_sha256"]:
        raise ValueError("Executable backup verification failed")
    temporary = source.with_suffix(".exe.archive-next")
    shutil.copy2(staged, temporary)
    if digest(temporary) != report["patched_sha256"]:
        raise ValueError("Executable install copy verification failed")
    try:
        os.replace(temporary, source)
        if digest(source) != report["patched_sha256"]:
            raise ValueError("Installed executable verification failed")
    except Exception:
        shutil.copy2(backup / source.name, source)
        raise
    report["backup"] = str(backup)
    (backup / "install-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    (staged.parent / "install-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("stage", "install"))
    args = parser.parse_args()
    print(json.dumps(patch() if args.operation == "stage" else install(), indent=2))
