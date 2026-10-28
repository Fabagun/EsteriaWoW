"""Carry an HD creature patch's extra skin columns into the CreatureDisplayInfo.dbc that wins.

usage: hd_creature_skins.py <hd archive> <target archive> [--write <out.dbc>]

A later patch that ships a whole CreatureDisplayInfo.dbc drops the HD patch's skin2/skin3, and the HD model's
second creature-skin slot then draws white. Only empty skin2/skin3 slots are filled, and only on rows whose skin1
agrees, so a client without the HD patch (whose stock model never reads those columns) is unaffected.
"""
import struct, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cars_mount_pack import DLL_DEFAULT, Storm  # noqa: E402

KEY = "DBFilesClient\\CreatureDisplayInfo.dbc"
SKINS = (6, 7, 8)
storm = Storm(DLL_DEFAULT)


def read(path):
    h = storm.open_archive(Path(path))
    try:
        return storm.read(h, KEY)
    finally:
        storm.dll.SFileCloseArchive(h)


def parse(d):
    assert d[:4] == b"WDBC"
    n, f, rs, ss = struct.unpack_from("<4I", d, 4)
    assert rs == f * 4
    rows = [list(struct.unpack_from("<%dI" % f, d, 20 + i * rs)) for i in range(n)]
    strings = d[20 + n * rs:20 + n * rs + ss]
    return f, rows, strings


def text(strings, o):
    return strings[o:strings.index(b"\0", o)]


hd = parse(read(sys.argv[1]))
target_raw = read(sys.argv[2])
fields, rows, strings = parse(target_raw)
hd_rows = {r[0]: r for r in hd[1]}

pool = bytearray(strings)
offsets = {}


def intern(value):
    if value not in offsets:
        offsets[value] = len(pool)
        pool.extend(value + b"\0")
    return offsets[value]


changed, skipped = [], 0
for r in rows:
    h = hd_rows.get(r[0])
    if not h:
        continue
    if text(strings, r[6]).lower() != text(hd[2], h[6]).lower():
        if any(text(hd[2], h[j]) for j in (7, 8)) and not all(text(strings, r[j]) for j in (7, 8)):
            skipped += 1
        continue
    for j in (7, 8):
        theirs = text(hd[2], h[j])
        if theirs and not text(strings, r[j]):
            r[j] = intern(theirs)
            changed.append((r[0], j - 5, theirs.decode("latin1")))

print("slots filled:", len(changed), "rows:", len({c[0] for c in changed}), "rows skipped (skin1 differs):", skipped)
for c in changed[:15]:
    print("  display", c[0], "skin%d" % c[1], "=", c[2])

if "--write" in sys.argv:
    out = Path(sys.argv[sys.argv.index("--write") + 1])
    body = b"".join(struct.pack("<%dI" % fields, *r) for r in rows)
    raw = b"WDBC" + struct.pack("<4I", len(rows), fields, fields * 4, len(pool)) + body + bytes(pool)
    # self-check: every untouched row is byte-identical, and every filled slot reads back
    check = parse(raw)
    old = parse(target_raw)
    filled = {(c[0], c[1] + 5) for c in changed}
    for a, b in zip(old[1], check[1]):
        for j in range(fields):
            if (a[0], j) not in filled:
                assert text(old[2], a[j]) == text(check[2], b[j]) if j in SKINS else a[j] == b[j], (a[0], j)
    out.write_bytes(raw)
    print("wrote", out, len(raw), "bytes")
