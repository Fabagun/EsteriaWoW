"""Exact, reversible Solosis material repair. No geometry/animation/texture conversion."""
from pathlib import Path
import argparse
import hashlib
import json
import struct

MODULE = Path(__file__).resolve().parents[1]
EXPECTED = {
    '0577_Solosis': 'e13a7e1f7e282a1765f821f6a82c5b66b60080570235a387b3372f55254148bd',
    '0577_Solosis_s': 'ad5897edd1f0e7b9083bccbdfd00c4067d3c567decb183be31ed5c3ed25cecc0',
}
SKIN_HASH = '647702e23a9ffed0600885c337dcf6af7fbc71a122e20b26af14ec931d999195'

def digest(data):
    return hashlib.sha256(data).hexdigest()

def repair(stem, model, skin):
    if stem not in EXPECTED or digest(model) != EXPECTED[stem] or digest(skin) != SKIN_HASH:
        raise ValueError('Unrecognized Solosis source; refusing to patch')
    # The source body has 325 vertices / 486 faces, followed by 130 shell vertices / 192 faces.
    # Preserve every index, palette entry and animation byte; split only draw sections/materials.
    d, s = bytearray(model), bytearray(skin)
    ns, so = struct.unpack_from('<II', s, 28)
    assert ns == 1
    original = list(struct.unpack_from('<10H7f', s, so))
    assert original[2:6] == [0, 455, 0, 2034]
    def append_array(data, header, count, payload):
        data.extend(bytes(-len(data) % 16))
        offset = len(data)
        data.extend(payload)
        struct.pack_into('<II', data, header, count, offset)
    # Separate solid/cutout body from source-alpha shell. Shell depth writes are disabled.
    append_array(d, 0x70, 2, struct.pack('<4H', 0, 1, 16, 2))
    sections = []
    for vs, vc, ts, tc in [(0, 325, 0, 1458), (325, 130, 1458, 576)]:
        section = original.copy()
        section[2:6] = [vs, vc, ts, tc]
        sections.append(struct.pack('<10H7f', *section))
    append_array(s, 28, 2, b''.join(sections))
    batches = [struct.pack('<BB11H', 0, 0, 0, i, i, 65535, i, 0, 1, 0, 0, 0, 0)
               for i in range(2)]
    append_array(s, 36, 2, b''.join(batches))
    verify(model, skin, d, s)
    return bytes(d), bytes(s)

def verify(old_model, old_skin, model, skin):
    # Exact byte preservation outside the material pointer and draw-section/batch pointers.
    restored = bytearray(model[:len(old_model)])
    restored[0x70:0x78] = old_model[0x70:0x78]
    assert restored == old_model
    restored = bytearray(skin[:len(old_skin)])
    restored[28:44] = old_skin[28:44]
    assert restored == old_skin
    n, o = struct.unpack_from('<II', model, 0x70)
    assert n == 2 and struct.unpack_from('<4H', model, o) == (0, 1, 16, 2)
    n, o = struct.unpack_from('<II', skin, 28)
    assert n == 2
    sections = [struct.unpack_from('<10H7f', skin, o+i*48) for i in range(n)]
    assert [v[2:6] for v in sections] == [(0, 325, 0, 1458), (325, 130, 1458, 576)]
    nt, to = struct.unpack_from('<II', skin, 12)
    triangles = struct.unpack_from('<'+str(nt)+'H', skin, to)
    for section in sections:
        _, _, vs, vc, ts, tc, bc, bs, influences, *_ = section
        assert 0 < bc <= 64 and 0 < influences <= 4
        assert all(vs <= t < vs+vc for t in triangles[ts:ts+tc])
    n, o = struct.unpack_from('<II', skin, 36)
    assert n == 2
    for i in range(n):
        assert struct.unpack_from('<BB11H', skin, o+i*24) == (0, 0, 0, i, i, 65535, i, 0, 1, 0, 0, 0, 0)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.source.resolve() == args.output.resolve():
        raise ValueError('Stage into a separate directory before installing')
    args.output.mkdir(parents=True, exist_ok=True)
    receipt = {'status': 'candidate', 'live_client_verified': False, 'files': []}
    for stem in EXPECTED:
        model_path, skin_path = args.source/(stem+'.m2'), args.source/(stem+'00.skin')
        old_model, old_skin = model_path.read_bytes(), skin_path.read_bytes()
        model, skin = repair(stem, old_model, old_skin)
        for filename, old, new in [(model_path.name, old_model, model), (skin_path.name, old_skin, skin)]:
            (args.output/filename).write_bytes(new)
            receipt['files'].append(dict(name=filename, before=digest(old), after=digest(new)))
    (args.output/'receipt.json').write_text(json.dumps(receipt, indent=2)+'\n')
    print('Staged both Solosis palettes; geometry, animations, UVs and textures unchanged.')

if __name__ == '__main__':
    main()
