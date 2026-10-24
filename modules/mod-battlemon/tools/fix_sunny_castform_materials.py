"""Hash-guarded Sunny Castform repair: opaque faces first, source-alpha faces without depth writes."""
from pathlib import Path
import hashlib
import json
import struct
import numpy as np
from PIL import Image

MODULE = Path(__file__).resolve().parents[1]
EXPECTED = {
    '0351_Castform_01': '8351051914dda6a36fa6f19b1f6f544d9df117c7bcf1bc8045297b9c396002aa',
    '0351_Castform_01_s': '335c7ad4f9c7ff43c583280d3e6740236016e4cec9f3632e10039426ea6d3ebd',
}
SKIN = 'a01d98fd11eb39e6ca05de844103d46f7f542b009c47a607eccff22f493f3ad0'

def digest(data):
    return hashlib.sha256(data).hexdigest()

def repair(stem, model, skin, solid):
    if digest(model) != EXPECTED.get(stem) or digest(skin) != SKIN:
        raise ValueError('Unrecognized Sunny Castform bytes')
    solid = np.asarray(solid, dtype=bool)
    assert solid.shape == (1382,) and sum(solid) == 654
    assert digest(bytes(solid.tolist())) == '5adda44e2200b6d47c7634b89e9dbc56ad9772494bd2a97f465281724710c46c'
    d, s = bytearray(model), bytearray(skin)
    n, o = struct.unpack_from('<II', s, 12)
    triangles = np.array(struct.unpack_from('<'+str(n)+'H', s, o), dtype=np.uint16).reshape(-1, 3)
    _, section_at = struct.unpack_from('<II', s, 28)
    original = list(struct.unpack_from('<10H7f', s, section_at))
    assert original[2:6] == [0, 1635, 0, 4146]
    def append(data, header, count, payload):
        data.extend(bytes(-len(data) % 16)); offset = len(data); data.extend(payload)
        struct.pack_into('<II', data, header, count, offset)
    append(d, 0x70, 2, struct.pack('<4H', 0, 1, 16, 2))
    ordered = np.concatenate([triangles[solid], triangles[~solid]])
    append(s, 12, n, ordered.astype('<u2').tobytes())
    sections = []
    for start, count in [(0, 654*3), (654*3, 728*3)]:
        section = original.copy(); section[4:6] = [start, count]
        sections.append(struct.pack('<10H7f', *section))
    append(s, 28, 2, b''.join(sections))
    append(s, 36, 2, b''.join(struct.pack('<BB11H', 0, 0, 0, i, i, 65535, i, 0, 1, 0, 0, 0, 0) for i in range(2)))
    # Only array pointers change in existing bytes; geometry, UVs, weights and all keys remain exact.
    check = bytearray(d[:len(model)]); check[112:120] = model[112:120]; assert check == model
    check = bytearray(s[:len(skin)])
    for start, end in [(12,20), (28,44)]: check[start:end] = skin[start:end]
    assert check == skin
    assert sorted(map(tuple, ordered)) == sorted(map(tuple, triangles))
    assert ordered.max() < 1635
    return bytes(d), bytes(s)

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assert args.source.resolve() != args.output.resolve()
    args.output.mkdir(parents=True, exist_ok=True)
    receipt = dict(live_client_verified=False, files=[], classification={})
    for stem in EXPECTED:
        model = (args.source/(stem+'.m2')).read_bytes(); skin = (args.source/(stem+'00.skin')).read_bytes()
        n,o = struct.unpack_from('<II', model, 60)
        vertices = np.array(list(struct.iter_unpack('<3f4B4B3f2f2f', model[o:o+n*48])))
        n,o = struct.unpack_from('<II',skin,4); lookup=np.array(struct.unpack_from('<'+str(n)+'H',skin,o))
        n,o = struct.unpack_from('<II',skin,12); triangles=lookup[np.array(struct.unpack_from('<'+str(n)+'H',skin,o))].reshape(-1,3)
        tex = args.source/(stem+'.blp'); alpha=np.array(Image.open(tex).convert('RGBA'))[:,:,3]; solid=[]
        for tri in triangles:
            uv=vertices[tri,14:16]
            lo=np.maximum(0,np.floor(uv.min(0)*512-1).astype(int)); hi=np.minimum(511,np.ceil(uv.max(0)*512+1).astype(int))
            solid.append(bool(alpha[lo[1]:hi[1]+1,lo[0]:hi[0]+1].min()==255))
        receipt['classification'][stem]=dict(solid=solid,texture_sha256=digest(tex.read_bytes()))
        fixed, fixed_skin=repair(stem,model,skin,solid)
        for name,old,new in [(stem+'.m2',model,fixed),(stem+'00.skin',skin,fixed_skin)]:
            before=args.output/'before'/name;before.parent.mkdir(exist_ok=True);before.write_bytes(old)
            (args.output/name).write_bytes(new)
            receipt['files'].append(dict(name=name,before=digest(old),after=digest(new)))
    (args.output/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    print('PASS: both palettes, 654 opaque + 728 translucent faces; all 1382 faces and all original animation bytes preserved.')
