"""Convert skinned BMD meshes to self-contained WotLK M2 v264 + SKIN files.

Bones are baked in model space (no parent), preserving the source skinning matrices.
This avoids relying on identical bind-pose/pivot conventions in SMD and M2.
"""
import math
import struct

import numpy as np

from bmd import read_bmd


def pack(fmt, *values):
    return struct.pack('<' + fmt, *values)


class Blob:
    def __init__(self, size):
        self.data = bytearray(size)

    def add(self, data):
        self.data.extend(b'\0' * (-len(self.data) % 16))
        offset = len(self.data)
        self.data.extend(data)
        return offset

    def array(self, offset, count, data):
        address = self.add(data) if count else 0
        struct.pack_into('<II', self.data, offset, count, address)


def world_matrices(bones, frames):
    result = np.empty((len(frames), len(bones), 4, 4))
    visited = set()

    def visit(index, pending):
        if index in visited:
            return
        if index in pending:
            raise ValueError('Cyclic bone hierarchy')
        parent = bones[index][1]
        if parent >= 0:
            visit(parent, pending | {index})
        for frame_index, frame in enumerate(frames):
            x, y, z, rx, ry, rz = frame[index]
            cx, cy, cz = np.cos([rx, ry, rz])
            sx, sy, sz = np.sin([rx, ry, rz])
            local = np.array([
                [cy*cz, sx*sy*cz-cx*sz, cx*sy*cz+sx*sz, x],
                [cy*sz, sx*sy*sz+cx*cz, cx*sy*sz-sx*cz, y],
                [-sy, sx*cy, cx*cy, z],
                [0, 0, 0, 1],
            ])
            result[frame_index, index] = result[frame_index, parent] @ local if parent >= 0 else local
        visited.add(index)

    for index in range(len(bones)):
        visit(index, set())
    return result


def quaternion(matrix):
    # Stable largest-component conversion; output XYZW, as serialized by M2.
    m = matrix
    candidates = [1+m[0,0]-m[1,1]-m[2,2], 1-m[0,0]+m[1,1]-m[2,2],
                  1-m[0,0]-m[1,1]+m[2,2], 1+m[0,0]+m[1,1]+m[2,2]]
    i = int(np.argmax(candidates))
    q = np.zeros(4)
    q[i] = math.sqrt(max(0, candidates[i])) / 2
    d = 4*q[i]
    if i == 3:
        q[:3] = [(m[2,1]-m[1,2])/d, (m[0,2]-m[2,0])/d, (m[1,0]-m[0,1])/d]
    else:
        j, k = (i+1) % 3, (i+2) % 3
        q[j] = (m[j,i]+m[i,j])/d
        q[k] = (m[k,i]+m[i,k])/d
        q[3] = (m[k,j]-m[j,k])/d
    return q / np.linalg.norm(q)


def compressed_quaternion(q):
    values = np.rint(np.clip(q, -1, 1) * 32767).astype(int)
    return pack('4h', *(v - 32768 if v >= 0 else v + 32767 for v in values))


def track(blob, sequences, fmt, interpolation=1):
    timestamps, values = [], []
    for times, keys in sequences:
        timestamps.append(pack('II', len(times), blob.add(pack(f'{len(times)}I', *times))))
        raw = b''.join(compressed_quaternion(k) if fmt == 'quat' else pack(fmt, *k) for k in keys)
        values.append(pack('II', len(keys), blob.add(raw)))
    return pack('HhIIII', interpolation, -1, len(sequences), blob.add(b''.join(timestamps)),
                len(sequences), blob.add(b''.join(values)))


def empty_track():
    return pack('HhIIII', 0, -1, 0, 0, 0, 0)


def box(mn, mx):
    radius = float(np.linalg.norm((mx-mn)/2))
    return pack('7f', *mn, *mx, radius)


def skin_positions(vertices, weights, transforms):
    positions = np.c_[vertices[:, :3], np.ones(len(vertices))]
    result = np.zeros((len(transforms), len(vertices), 3))
    for bone in range(transforms.shape[1]):
        w = np.array([sum(v for b, v in links if b == bone) for links in weights])
        if np.any(w):
            result += np.einsum('fij,vj->fvi', transforms[:, bone, :3], positions) * w[None, :, None]
    return result


def prepare(model_path, animation_paths, height=1.0, fps=30, static_bind_pose=False, source_transform=None):
    model = read_bmd(model_path)
    if not len(model['vertices']) or len(model['bones']) > 256:
        raise ValueError('Empty model or too many bones for one skin section')
    # Pixelmon SmdModel reads material labels but renders every face with the
    # enclosing JSON model definition's single texture. Labels are not texture bindings.
    raw_source_weights = model['weights']
    weights, source_weights = [], []
    max_dropped_weight = 0.0
    for links in model['weights']:
        links = sorted(((b, w) for b, w in links if w > 0), key=lambda v: -v[1])
        if not links:
            raise ValueError('Vertex has no positive weights')
        # WotLK vertices permit four influences. Keep the strongest and renormalize.
        source_total = sum(w for _, w in links)
        source_weights.append([(b, w/source_total) for b, w in links])
        max_dropped_weight = max(max_dropped_weight, sum(w for _, w in links[4:])/source_total)
        links = links[:4]
        total = sum(w for _, w in links)
        weights.append([(b, w/total) for b, w in links])
    model['weights'] = weights
    bind = world_matrices(model['bones'], model['frames'][:1])[0]
    inverse_bind = np.linalg.inv(bind)
    animations = {}
    binding_notes = []
    if static_bind_pose:
        if animation_paths:
            raise ValueError('Static source policy cannot discard declared animations')
        # Scene uses model node bind transforms when no animation exists. After
        # inverse-bind multiplication the skin matrices are exactly identity.
        identity = np.broadcast_to(np.eye(4), (1, len(model['bones']), 4, 4)).copy()
        animations = dict(idle=identity, walk=identity.copy())
        fps = 1
    for name, path in animation_paths.items():
        animation = read_bmd(path)
        animation_names = {bone[0]: i for i, bone in enumerate(animation['bones'])}
        from bone_binding import check_duplicate_names
        binding_notes.extend(name+':'+note for note in check_duplicate_names(
            model['bones'], animation['bones'], source_weights))
        frames = np.repeat(model['frames'][:1], len(animation['frames']), axis=0)
        for index, (bone_name, parent) in enumerate(model['bones']):
            if bone_name not in animation_names:
                # Scene.createBoneWorldTransform retains the model node's LOCAL
                # bind transform if no named channel exists, including weighted bones.
                # It still inherits animated ancestors; never freeze it in world space.
                binding_notes.append(f'{name}:bind_local_fallback:{bone_name}')
                continue
            other = animation_names[bone_name]
            other_parent = animation['bones'][other][1]
            parent_name = model['bones'][parent][0] if parent >= 0 else None
            other_parent_name = animation['bones'][other_parent][0] if other_parent >= 0 else None
            if parent_name != other_parent_name:
                # SMDModelLoader creates named LOCAL channels without animation
                # hierarchy links; Scene traverses the original model hierarchy.
                binding_notes.append(f'{name}:model_parent_used:{bone_name}')
            frames[:, index] = animation['frames'][:, other]
        animations[name] = world_matrices(model['bones'], frames) @ inverse_bind
    if 'idle' not in animations or 'walk' not in animations:
        raise ValueError('Pilot requires idle and walk animations')
    idle_positions = skin_positions(model['vertices'], weights, animations['idle'][:1])[0]
    source_transform = np.eye(4) if source_transform is None else np.asarray(source_transform, dtype=float)
    if source_transform.shape != (4, 4) or not np.isfinite(source_transform).all():
        raise ValueError('Invalid source transform matrix')
    source_scale = np.linalg.norm(source_transform[:3, 0])
    if (source_scale <= 0 or np.linalg.det(source_transform[:3, :3]) <= 0
            or not np.allclose(source_transform[3], [0, 0, 0, 1])
            or not np.allclose(source_transform[:3, :3].T @ source_transform[:3, :3],
                               np.eye(3)*source_scale**2, atol=1e-8, rtol=1e-7)):
        raise ValueError('Source transform must be a positive uniform-scale rigid transform')
    idle_positions = (np.c_[idle_positions, np.ones(len(idle_positions))] @ source_transform.T)[:, :3]
    if height is not None and np.ptp(idle_positions[:, 2]) <= 1e-8:
        raise ValueError('Source transform produces zero standing height')
    scale = height / np.ptp(idle_positions[:, 2]) if height is not None else 1.0
    # Source is Z-up, facing -Y. WoW creatures face +X.
    conversion = np.array([[0, -scale, 0, 0], [scale, 0, 0, 0], [0, 0, scale, 0], [0, 0, 0, 1]])
    conversion[2, 3] = -idle_positions[:, 2].min() * scale if height is not None else 0.0
    conversion = conversion @ source_transform
    inv_conversion = np.linalg.inv(conversion)
    vertices = model['vertices'].copy()
    vertices[:, :3] = (np.c_[vertices[:, :3], np.ones(len(vertices))] @ conversion.T)[:, :3]
    vertices[:, 3:6] = vertices[:, 3:6] @ (conversion[:3, :3] / (scale*source_scale)).T
    vertices[:, 7] = 1 - vertices[:, 7]
    source_error = 0.0
    unlimited_error = 0.0
    from source_skinning import source_positions
    for matrices in animations.values():
        original = source_positions(model['vertices'], raw_source_weights, matrices)
        unlimited = skin_positions(model['vertices'], source_weights, matrices)
        reduced = skin_positions(model['vertices'], weights, matrices)
        source_error = max(source_error, float(np.linalg.norm(original-reduced, axis=2).max()) * scale * source_scale)
        unlimited_error = max(unlimited_error, float(np.linalg.norm(unlimited-reduced, axis=2).max()) * scale * source_scale)
    sequences = []
    all_positions = []
    for sequence_id, name, speed in [(0, 'idle', 0), (4, 'walk', 2.5), (5, 'walk', 7.0)]:
        matrices = conversion @ animations[name] @ inv_conversion
        times = np.rint(np.arange(len(matrices)) * 1000/fps).astype(int)
        # Explicit final key closes the loop without referencing another sequence.
        duration = round(len(matrices) * 1000/fps)
        matrices = np.concatenate([matrices, matrices[:1]])
        times = np.append(times, duration)
        quats = np.array([[quaternion(m[:3, :3]) for m in frame] for frame in matrices])
        for f in range(1, len(quats)):
            signs = np.sum(quats[f-1] * quats[f], axis=1) < 0
            quats[f, signs] *= -1
        posed = skin_positions(vertices, weights, matrices)
        all_positions.append(posed)
        sequences.append(dict(id=sequence_id, name=name, speed=speed, duration=duration,
                              times=times, translations=matrices[:, :, :3, 3], rotations=quats,
                              bounds=(posed.min(axis=(0, 1)), posed.max(axis=(0, 1)))))
    # Deduplicate exact position/normal/UV/weights combinations (preserving seams).
    unique, unique_weights, lookup, triangles = [], [], {}, []
    for _, tri in model['faces']:
        for index in tri:
            key = (tuple(vertices[index]), tuple(weights[index]))
            if key not in lookup:
                lookup[key] = len(unique)
                unique.append(vertices[index])
                unique_weights.append(weights[index])
            triangles.append(lookup[key])
    if len(unique) > 65535 or len(triangles) > 65535:
        raise ValueError('Pilot mesh exceeds a single SKIN section')
    posed = np.concatenate(all_positions)
    return dict(vertices=np.array(unique), weights=unique_weights, triangles=triangles,
                bones=model['bones'], sequences=sequences,
                standing_bounds=[idle_positions.min(axis=0).tolist(), idle_positions.max(axis=0).tolist()],
                skinning_error=source_error, max_dropped_weight=max_dropped_weight,
                unlimited_weight_difference=unlimited_error, skinning_reference='pixelmon_smd_four_weights',
                binding_notes=binding_notes,
                bounds=(posed.min(axis=(0, 1)), posed.max(axis=(0, 1))))


def build_model(mesh, name, texture, texture_policy='solid_alpha_key'):
    from skin_sections import MAX_SECTION_BONES, partition
    layout = partition(mesh)
    if mesh.get('emissive_overlay'):
        from emissive import overlay_layout
        layout = overlay_layout(layout)
    mesh = dict(mesh, **{key: layout[key] for key in ['vertices', 'weights', 'triangles']})
    b = Blob(304)
    b.data[:8] = b'MD20' + pack('I', 264)
    encoded_name = name.encode('ascii') + b'\0'
    b.array(8, len(encoded_name), encoded_name)
    sequence_bytes = []
    for seq in mesh['sequences']:
        sequence_bytes.append(pack('HHIfIhHIII', seq['id'], 0, seq['duration'], seq['speed'],
                                   0x20, 32767, 0, 0, 0, 150) + box(*seq['bounds']) + pack('hH', -1, 0))
    b.array(0x1c, len(sequence_bytes), b''.join(sequence_bytes))
    b.array(0x24, 6, pack('6h', 0, -1, -1, -1, 1, 2))
    bones = []
    for index in range(len(mesh['bones'])):
        translations = [(s['times'], s['translations'][:, index]) for s in mesh['sequences']]
        rotations = [(s['times'], s['rotations'][:, index]) for s in mesh['sequences']]
        hierarchical = mesh.get('skeleton_policy') == 'glb_hierarchical_trs'
        parent = mesh['bones'][index][1] if hierarchical else -1
        if parent >= index or parent < -1:
            raise ValueError('Non-topological bone hierarchy')
        translation_interpolation = mesh.get('translation_interpolation', {}).get(index, 1)
        scales = track(b, [(s['times'], s['scales'][:, index]) for s in mesh['sequences']], '3f') \
            if hierarchical else empty_track()
        bones.append(pack('iIhHI', -1, 0x200, parent, 0, 0)
                     + track(b, translations, '3f', translation_interpolation)
                     + track(b, rotations, 'quat') + scales + pack('3f', 0, 0, 0))
    b.array(0x2c, len(bones), b''.join(bones))
    b.array(0x34, 26, pack('26h', *([-1]*26)))
    vertices = []
    for vertex, links in zip(mesh['vertices'], mesh['weights']):
        quantized = [round(w*255) for _, w in links]
        quantized[0] += 255 - sum(quantized)
        indices = [index for index, _ in links] + [0]*(4-len(links))
        quantized += [0]*(4-len(links))
        vertices.append(pack('3f4B4B3f2f2f', *vertex[:3], *quantized, *indices,
                             *vertex[3:6], *vertex[6:8], 0, 0))
    b.array(0x3c, len(vertices), b''.join(vertices))
    struct.pack_into('<I', b.data, 0x44, 1)
    path = texture.encode('ascii') + b'\0'
    texture_offset = b.add(path)
    b.array(0x50, 1, pack('IIII', 0, 0, len(path), texture_offset))
    weight = track(b, [([0], [(32767,)]) for _ in mesh['sequences']], 'H')
    b.array(0x58, 1, weight)
    # Lit and alpha-tested. The flame and silhouette retain the source PNG alpha.
    if texture_policy not in {'solid_alpha_key', 'source_alpha_blend', 'source_alpha_emissive', 'source_alpha_emissive_twosided'}:
        raise ValueError('Unknown texture policy')
    if texture_policy in {'source_alpha_emissive', 'source_alpha_emissive_twosided'}:
        if not mesh.get('emissive_overlay'):
            raise ValueError('Emissive material requires separate overlay sections')
        two_sided = 4 if texture_policy.endswith('_twosided') else 0
        b.array(0x70, 2, pack('4H', two_sided, 2, two_sided | 1, 2))
    else:
        b.array(0x70, 1, pack('HH', 0, 2 if texture_policy == 'source_alpha_blend' else 1))
    b.array(0x78, len(layout['combos']), pack(f"{len(layout['combos'])}H", *layout['combos']))
    for offset, value in [(0x80, 0), (0x88, 0), (0x90, 0), (0x98, -1)]:
        b.array(offset, 1, pack('h', value))
    mn, mx = mesh['bounds']
    b.data[0xa0:0xbc] = box(mn, mx)
    b.data[0xbc:0xd8] = box(mn, mx)
    corners = np.array([[x, y, z] for z in [mn[2], mx[2]] for y in [mn[1], mx[1]] for x in [mn[0], mx[0]]])
    faces = [0,2,3, 0,3,1, 4,5,7, 4,7,6, 0,1,5, 0,5,4, 2,6,7, 2,7,3, 0,4,6, 0,6,2, 1,3,7, 1,7,5]
    normals = []
    for a, c, d in np.array(faces).reshape(-1, 3):
        normal = np.cross(corners[c]-corners[a], corners[d]-corners[a])
        normals.extend(normal/np.linalg.norm(normal))
    b.array(0xd8, len(faces), pack(f'{len(faces)}H', *faces))
    b.array(0xe0, 8, pack('24f', *corners.ravel()))
    b.array(0xe8, 12, pack('36f', *normals))
    skin = Blob(48)
    skin.data[:4] = b'SKIN'
    skin.array(4, len(vertices), pack(f'{len(vertices)}H', *range(len(vertices))))
    skin.array(12, len(mesh['triangles']), pack(f'{len(mesh["triangles"])}H', *mesh['triangles']))
    skin.array(20, len(vertices), b''.join(bytes(p) for p in layout['properties']))
    center = (mn+mx)/2
    section_bytes, batches = [], []
    for index, section in enumerate(layout['sections']):
        section_bytes.append(pack('10H7f', 0, 0, section['vertex_start'], section['vertex_count'],
                                  section['index_start'], section['index_count'], section['bone_count'],
                                  section['bone_start'], section['influences'], 0, *center, *center,
                                  float(np.linalg.norm((mx-mn)/2))))
        material = section.get('material', 0)
        batches.append(pack('BB11H', 0, 0, 0, index, index, 65535, material, material, 1, 0, 0, 0, 0))
    skin.array(28, len(section_bytes), b''.join(section_bytes))
    skin.array(36, len(batches), b''.join(batches))
    struct.pack_into('<I', skin.data, 44, MAX_SECTION_BONES)
    return bytes(b.data), bytes(skin.data)
