"""Independent reader/validator for the emitted WotLK pilot assets."""
import argparse
import hashlib
import json
from pathlib import Path
import struct

import numpy as np
from PIL import Image

from convert import Dbc, MODULE, LAYER, PILOT
from texture import filtered_edge_alpha


def array(data, offset, stride):
    count, address = struct.unpack_from('<II', data, offset)
    if count and (address < 48 or address + count*stride > len(data)):
        raise ValueError(f'Array outside file at {offset:#x}')
    return count, address


def track(data, offset, sequence, fmt):
    interp, global_seq = struct.unpack_from('<Hh', data, offset)
    if interp not in [0, 1] or global_seq != -1:
        raise ValueError('Unexpected track interpolation')
    count, address = array(data, offset+4, 8)
    if not count:
        return np.array([]), np.array([])
    if sequence >= count:
        raise ValueError('Missing sequence track')
    n, t = array(data, address+sequence*8, 4)
    vcount, vaddress = array(data, offset+12, 8)
    if vcount != count:
        raise ValueError('Timestamp/value sequence mismatch')
    nv, v = array(data, vaddress+sequence*8, struct.calcsize('<'+fmt))
    if nv != n or not n:
        raise ValueError('Timestamp/value count mismatch')
    times = np.array(struct.unpack_from(f'<{n}I', data, t))
    values = np.array(list(struct.iter_unpack('<'+fmt, data[v:v+n*struct.calcsize('<'+fmt)])))
    if np.any(np.diff(times) < 0) or not np.isfinite(values).all():
        raise ValueError('Invalid animation keys')
    return times, values


def rotation_matrix(q):
    x, y, z, w = q / np.linalg.norm(q)
    return np.array([[1-2*y*y-2*z*z, 2*x*y-2*z*w, 2*x*z+2*y*w],
                     [2*x*y+2*z*w, 1-2*x*x-2*z*z, 2*y*z-2*x*w],
                     [2*x*z-2*y*w, 2*y*z+2*x*w, 1-2*x*x-2*y*y]])


def read_model(path, source_motion='animated', texture_policy='solid_alpha_key', skeleton_policy='baked'):
    if skeleton_policy not in {'baked', 'glb_hierarchical_trs'}:
        raise ValueError('Unknown skeleton policy')
    data = path.read_bytes()
    skin = path.with_name(path.stem+'00.skin').read_bytes()
    if data[:8] != b'MD20'+struct.pack('<I', 264) or skin[:4] != b'SKIN':
        raise ValueError('Wrong M2/SKIN version')
    count, offset = array(data, 0x3c, 48)
    vertices = list(struct.iter_unpack('<3f4B4B3f2f2f', data[offset:offset+count*48]))
    positions = np.array([v[:3] for v in vertices])
    weights = np.array([v[3:7] for v in vertices])/255
    indices = np.array([v[7:11] for v in vertices])
    if not np.allclose(weights.sum(axis=1), 1):
        raise ValueError('Weights do not total 255')
    uv = np.array([v[14:16] for v in vertices])
    nlookup, lookup_offset = array(skin, 4, 2)
    lookup = np.array(struct.unpack_from(f'<{nlookup}H', skin, lookup_offset))
    ntri, tri_offset = array(skin, 12, 2)
    triangles = np.array(struct.unpack_from(f'<{ntri}H', skin, tri_offset))
    if ntri % 3 or triangles.max() >= len(lookup) or lookup.max() >= count:
        raise ValueError('Triangle index out of range')
    triangles = lookup[triangles].reshape(-1, 3)
    nbones, bone_offset = array(data, 0x2c, 88)
    if indices.max() >= nbones:
        raise ValueError('Vertex bone out of range')
    ncombo, combo_offset = array(data, 0x78, 2)
    combos = struct.unpack_from(f'<{ncombo}H', data, combo_offset)
    if any(bone >= nbones for bone in combos):
        raise ValueError('Bone palette refers outside the skeleton')
    nprops, prop_offset = array(skin, 20, 4)
    props = np.array(list(struct.iter_unpack('<4B', skin[prop_offset:prop_offset+nprops*4])))
    if nprops != nlookup:
        raise ValueError('Skin bone property count mismatch')
    nsections, section_offset = array(skin, 28, 48)
    sections = list(struct.iter_unpack('<10H7f', skin[section_offset:section_offset+nsections*48]))
    tier = struct.unpack_from('<I', skin, 44)[0]
    # Independent literal: the writer must not be able to weaken its own acceptance test.
    if not nsections or not 1 <= tier <= 64:
        raise ValueError('Unsafe D3D9 skin bone tier (maximum 64)')
    covered_indices = np.zeros(ntri, dtype=bool)
    covered_vertices = np.zeros(nlookup, dtype=bool)
    raw_triangles = np.array(struct.unpack_from(f'<{ntri}H', skin, tri_offset))
    for section in sections:
        _, level, vs, vc, ts, tc, bc, bs, influences, _ = section[:10]
        if (level or not vc or not tc or tc % 3 or vs+vc > nlookup or ts+tc > ntri
                or not 1 <= bc <= tier or bs+bc > ncombo or not 1 <= influences <= 4):
            raise ValueError('Invalid skin section or bone budget')
        if covered_indices[ts:ts+tc].any() or covered_vertices[vs:vs+vc].any():
            raise ValueError('Overlapping skin sections')
        covered_indices[ts:ts+tc] = True
        covered_vertices[vs:vs+vc] = True
        section_triangles = raw_triangles[ts:ts+tc]
        if section_triangles.min() < vs or section_triangles.max() >= vs+vc:
            raise ValueError('Triangle leaves its skin section')
        local = props[vs:vs+vc]
        if local.max() >= bc:
            raise ValueError('Local bone index exceeds section palette')
        mapped = np.array(combos[bs:bs+bc])[local]
        global_vertices = lookup[vs:vs+vc]
        weighted = weights[global_vertices] > 0
        if not np.array_equal(mapped[weighted], indices[global_vertices][weighted]):
            raise ValueError('Skin local/global bone mapping mismatch')
        if int(np.count_nonzero(weighted, axis=1).max()) > influences:
            raise ValueError('Understated bone influences')
    if not covered_indices.all() or not covered_vertices.all():
        raise ValueError('Skin sections leave geometry uncovered')
    nbat, bat_offset = array(skin, 36, 24)
    batches = list(struct.iter_unpack('<BB11H', skin[bat_offset:bat_offset+nbat*24]))
    if nbat != nsections or sorted(batch[3] for batch in batches) != list(range(nsections)):
        raise ValueError('Material batches do not cover skin sections')
    if any(batch[4] != batch[3]
           or batch[6] not in ([0,1] if texture_policy in {'source_alpha_emissive', 'source_alpha_emissive_twosided'} else [0])
           or batch[8] != 1 for batch in batches):
        raise ValueError('Invalid material batch')
    # The solid seam budget is valid only for this exact alpha-key material.
    nm, material = array(data, 0x70, 4)
    if texture_policy not in {'solid_alpha_key', 'source_alpha_blend', 'source_alpha_emissive', 'source_alpha_emissive_twosided'}:
        raise ValueError('Unknown texture policy')
    if texture_policy in {'source_alpha_emissive', 'source_alpha_emissive_twosided'}:
        expected = (4,2,5,2) if texture_policy.endswith('_twosided') else (0,2,1,2)
        if nm != 2 or struct.unpack_from('<4H',data,material) != expected:
            raise ValueError('Expected lit base and unlit alpha-blended emissive materials')
        if nsections % 2 or [b[6] for b in batches] != [0]*(nsections//2)+[1]*(nsections//2):
            raise ValueError('Emissive sections must pair with every base section')
        half = count//2
        if count % 2 or not np.array_equal(positions[:half],positions[half:]):
            raise ValueError('Emissive overlay changed source positions')
        if not np.array_equal(weights[:half],weights[half:]) or not np.array_equal(indices[:half],indices[half:]):
            raise ValueError('Emissive overlay changed skinning')
        if not np.allclose(uv[half:]-uv[:half],[.5,0],atol=1e-7):
            raise ValueError('Emissive atlas UV references do not match source geometry')
        if not np.array_equal(triangles[len(triangles)//2:]-half,triangles[:len(triangles)//2]):
            raise ValueError('Emissive overlay dropped or changed faces')
    else:
        expected_blend = 2 if texture_policy == 'source_alpha_blend' else 1
        if nm != 1 or struct.unpack_from('<HH', data, material) != (0, expected_blend):
            raise ValueError('Expected lit alpha-key material with depth writes')
    nw, opacity = array(data, 0x58, 20)
    if nw != 1:
        raise ValueError('Expected one full-opacity texture weight track')
    nt, tex = array(data, 0x50, 16)
    kind, flags, length, string = struct.unpack_from('<4I', data, tex)
    if nt != 1 or kind != 0 or string+length > len(data) or data[string+length-1] != 0:
        raise ValueError('Invalid texture reference')
    texture = data[string:string+length-1].decode('ascii')
    nseq, seq_offset = array(data, 0x1c, 64)
    poses, sequences = [], []
    for sequence in range(nseq):
        weight_times, weight_values = track(data, opacity, sequence, 'H')
        if weight_times.tolist() != [0] or weight_values.tolist() != [[32767]]:
            raise ValueError('Expected constant full texture opacity')
        seq = struct.unpack_from('<HHIfI', data, seq_offset+sequence*64)
        if seq[0] not in [0, 4, 5] or not seq[4] & 0x20:
            raise ValueError('Unexpected sequence or external animation dependency')
        all_translations, all_rotations, all_scales, parents = [], [], [], []
        for bone in range(nbones):
            off = bone_offset+bone*88
            parent = struct.unpack_from('<h', data, off+8)[0]
            if (skeleton_policy == 'baked' and parent != -1) or not -1 <= parent < bone:
                raise ValueError('Invalid or unexpected bone parent')
            if struct.unpack_from('<3f',data,off+76) != (0,0,0):
                raise ValueError('Unexpected nonzero bone pivot')
            parents.append(parent)
            times, translations = track(data, off+16, sequence, '3f')
            rt, compressed = track(data, off+36, sequence, '4h')
            if not np.array_equal(times, rt) or times[0] != 0 or times[-1] != seq[2]:
                raise ValueError('Animation timing mismatch')
            q = np.where(compressed < 0, compressed+32768, compressed-32767)/32767
            if not np.allclose(np.linalg.norm(q, axis=1), 1, atol=0.0001):
                raise ValueError('Invalid compressed quaternion')
            if skeleton_policy == 'glb_hierarchical_trs':
                st, scales = track(data, off+56, sequence, '3f')
                if not np.array_equal(times,st) or np.any(scales<=0):
                    raise ValueError('Invalid hierarchical scale track')
                all_scales.append(scales)
            all_translations.append(translations)
            all_rotations.append([rotation_matrix(value) for value in q])
        translations = np.transpose(all_translations, (1, 0, 2))
        rotations = np.transpose(all_rotations, (1, 0, 2, 3))
        if skeleton_policy == 'glb_hierarchical_trs':
            scales = np.transpose(all_scales,(1,0,2))
            rotations = rotations * scales[:,:,None,:]
            for bone,parent in enumerate(parents):
                if parent >= 0:
                    translations[:,bone] = np.einsum('fij,fj->fi',rotations[:,parent],translations[:,bone])+translations[:,parent]
                    rotations[:,bone] = rotations[:,parent]@rotations[:,bone]
        posed = np.zeros((len(times), len(positions), 3))
        for slot in range(4):
            transformed = np.einsum('fvij,vj->fvi', rotations[:, indices[:, slot]], positions)
            transformed += translations[:, indices[:, slot]]
            posed += transformed * weights[None, :, slot, None]
        if not np.isfinite(posed).all():
            raise ValueError('Non-finite animated vertices')
        poses.append(posed)
        sequences.append(dict(id=seq[0], times=times.tolist(), duration=seq[2]))
    bounds = np.array(struct.unpack_from('<6f', data, 0xa0)).reshape(2, 3)
    all_poses = np.concatenate(poses)
    if np.any(all_poses.min(axis=(0, 1)) < bounds[0]-0.015) or np.any(all_poses.max(axis=(0, 1)) > bounds[1]+0.015):
        raise ValueError('Animated mesh leaves its bounding box')
    for offset, stride in [(0xd8, 2), (0xe0, 12), (0xe8, 12)]:
        array(data, offset, stride)
    if source_motion == 'static_bind_pose':
        if any(not np.allclose(p, positions[None, :, :], atol=1e-5, rtol=0) for p in poses):
            raise ValueError('Static source export does not preserve the bind pose')
    elif source_motion == 'source_constant_walk':
        if any(np.max(np.ptp(p,axis=0)) > 1e-5 for p in poses[1:]):
            raise ValueError('Constant source walk gained motion')
    elif source_motion == 'animated':
        if np.max(np.ptp(poses[1], axis=0)) < 0.005:
            raise ValueError('Walk sequence is static')
    else:
        raise ValueError('Unknown source motion policy')
    return dict(positions=positions, triangles=triangles, uv=uv, poses=poses, sequences=sequences,
                texture=texture, bounds=bounds)


def validate(output, export_preview=False):
    manifest = json.loads((output/'manifest.json').read_text())
    for relative, digest in manifest['files'].items():
        if hashlib.sha256((output/relative).read_bytes()).hexdigest() != digest:
            raise ValueError(f'Checksum mismatch: {relative}')
    models = Dbc(output/'client/DBFilesClient'/('CreatureModelData'+LAYER))
    displays = Dbc(output/'client/DBFilesClient'/('CreatureDisplayInfo'+LAYER))
    expected = {base+form for form, _, _ in PILOT for base in [50000, 60000]}
    if set(displays.rows) != expected or len(models.rows) != 8:
        raise ValueError('DBC layer touches unexpected forms')
    for table in ['CreatureModelData', 'CreatureDisplayInfo']:
        filename = table+LAYER
        client_bytes = (output/'client/DBFilesClient'/filename).read_bytes()
        server_bytes = (output/'server/dbc-continuations'/filename).read_bytes()
        if client_bytes != server_bytes:
            raise ValueError('Client/server DBC mismatch')
    preview = output/'preview'
    if export_preview:
        preview.mkdir(exist_ok=True)
    report = []
    for entry in manifest['models']:
        path = output/'client/Creature/Battlemon3D'/(entry['asset']+'.m2')
        result = read_model(path)
        row = displays.rows[entry['display']]
        if row[1] != entry['model']:
            raise ValueError('Display/model mismatch')
        filename = models.string(models.rows[row[1]][2]).replace('\\', '/').replace('.mdx', '.m2')
        if output/'client'/filename != path:
            raise ValueError('DBC/model asset mismatch')
        texture = output/'client'/result['texture'].replace('\\', '/')
        image = Image.open(texture).convert('RGBA')
        edges = filtered_edge_alpha(texture, result['uv'], result['triangles'])
        if any(level['minimum_alpha'] < 240 for level in edges):
            raise ValueError(f'Transparent UV-border samples in {texture.name}: {edges}')
        if export_preview:
            image.save(preview/(entry['asset']+'.png'))
            preview_data = dict(name=entry['name'], shiny=entry['shiny'], triangles=result['triangles'].tolist(),
                                uv=result['uv'].tolist(), texture=entry['asset']+'.png',
                                poses=[p[::max(1, len(p)//12)].tolist() for p in result['poses'][:2]])
            (preview/(entry['asset']+'.json')).write_text(json.dumps(preview_data), encoding='utf8')
        report.append(dict(asset=entry['asset'], vertices=len(result['positions']),
                           triangles=len(result['triangles']), sequences=result['sequences'],
                           texture_edges=edges, status='binary-validation-passed'))
    (output/'validation.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf8')
    print('PASS: 8 M2/SKIN/BLP sets; idle/walk/run tracks; click bounds; 8 matching client/server eDBC rows.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=MODULE/'generated/pixelmon-3d')
    parser.add_argument('--preview', action='store_true')
    args = parser.parse_args()
    validate(args.output.resolve(), args.preview)
