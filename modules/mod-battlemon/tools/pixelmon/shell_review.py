"""Closed review allowance for exact source-alpha multipart exports; no material edits."""
import hashlib
import json
from pathlib import Path
import struct

REGISTRY = Path(__file__).with_name('reviewed_alpha_shells.json')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def key(value):
    return sha(json.dumps(value, sort_keys=True, separators=(',', ':')).encode())


def source_snapshot(appearance):
    parts = appearance.get('parts') or [appearance]
    ordered = []
    for part in parts:
        animations = part.get('animations', appearance.get('animations', {}))
        paths = dict(model=part['model'], texture=part['texture'], **animations)
        if part.get('metadata'):
            paths['metadata'] = part['metadata']
        if part.get('emissive'):
            paths['emissive'] = part['emissive']
        ordered.append(dict(files={name: dict(path=str(Path(path).resolve()),
                                             sha256=sha(Path(path).read_bytes()))
                                   for name, path in paths.items()},
                            transform=part.get('source_transform')))
    return dict(parts=ordered, fps=appearance['fps'],
                motion=appearance.get('source_motion', 'animated'),
                legacy_metadata=appearance.get('legacy_texture_transparency', []))


def export_signature(model):
    model = Path(model)
    data = bytearray(model.read_bytes())
    if data[:8] != b'MD20'+struct.pack('<I', 264):
        raise ValueError('Invalid reviewed M2 header')
    count, table = struct.unpack_from('<II', data, 0x50)
    if count != 1 or table < 304 or table+16 > len(data):
        raise ValueError('Invalid reviewed texture table')
    name_size, name_at = struct.unpack_from('<II', data, 8)
    tex_size, tex_at = struct.unpack_from('<II', data, table+8)
    expected_name = model.stem.encode('ascii')+b'\0'
    expected_texture = ('Creature\\Battlemon3DBatch\\'+model.stem+'.blp').encode('ascii')+b'\0'
    if (bytes(data[name_at:name_at+name_size]) != expected_name
            or bytes(data[tex_at:tex_at+tex_size]) != expected_texture):
        raise ValueError('Unexpected reviewed asset references')
    # Cache names are the only permitted difference from the reviewed bytes.
    token = model.stem.encode('ascii')
    if len(token) != 22 or not token.startswith(b'a_'):
        raise ValueError('Unexpected cache asset identity')
    data[name_at:name_at+len(token)] = bytes(len(token))
    base_at = tex_at+len('Creature\\Battlemon3DBatch\\')
    data[base_at:base_at+len(token)] = bytes(len(token))
    return dict(m2=sha(data), skin=sha(model.with_name(model.stem+'00.skin').read_bytes()),
                texture=sha(model.with_suffix('.blp').read_bytes()))


def verify_proof(proof, registry=REGISTRY):
    reviews = json.loads(Path(registry).read_text())
    if reviews.get('schema') != 1:
        raise ValueError('Unknown alpha-shell review registry')
    if key(proof['source']) != proof['source_key']:
        raise ValueError('Alpha-shell source proof changed')
    allowed = reviews['entries'].get(proof['source_key'])
    if allowed is None or allowed != dict(source=proof['source'], export=proof['export']):
        raise ValueError('Multipart source/export has no matching visual review')
    for part in proof['source']['parts']:
        for item in part['files'].values():
            if sha(Path(item['path']).read_bytes()) != item['sha256']:
                raise ValueError('Reviewed alpha-shell source changed')
    return proof


def approve_export(appearance, model, registry=REGISTRY):
    source = source_snapshot(appearance)
    proof = dict(source_key=key(source), source=source, export=export_signature(model))
    return verify_proof(proof, registry)
