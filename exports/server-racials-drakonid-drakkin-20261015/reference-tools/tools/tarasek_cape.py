"""Tarasek cloak: Worgen donor cape topology on an animated cloth chain, scaled to the Tarasek back.

Adapted from gnoll_race_pack.cape_rig / cape_surfaces (proven on Gnoll); only the donor-to-target scale is new.
"""
import copy
import math
import struct

import skyborne_visual_pack as visual
from gnoll_race_pack import triangles

SCALE = 1.0   # height / depth multiplier for donor-derived cloak dimensions
WIDTH = 1.0   # width multiplier
CLEARANCE = .04  # gap between the body's rear surface and the cloak


def cape_body_triangles(model, skin):
    from sethrak_equipment_repair import descendants
    excluded = descendants(model, model.key_bone_lookup[0]) | descendants(model, model.key_bone_lookup[1])
    excluded |= descendants(model, model.key_bone_lookup[41])
    return [tri for row in skin.submeshes if visual.u16(row, 0) in (0, 701, 801, 1001)
            for tri in triangles(skin, row) if sum(
                model.vertices[v * 48 + 12 + s] for v in tri for s in range(4)
                if model.vertices[v * 48 + 16 + s] in excluded) < 384]


def cape_rig(model, skin, donor, donor_skin):
    """Fit in the actual standing pose; append only three cloth bones, rooted at the upper spine."""
    import numpy as np
    import creature_animation_repair as animation
    CAPE_BONES = (18, 28, 37)
    parent = model.key_bone_lookup[53]
    authored = copy.deepcopy(model)
    authored.bones = authored.bones[:parent + 1]
    reference = animation.pose_matrices(model, 0, 0)
    points = animation.posed_vertices(model, reference)
    shoulders = [(reference[model.key_bone_lookup[k]] @ np.array(
        (*model.bones[model.key_bone_lookup[k]]['pivot'], 1)))[:3] for k in (0, 1)]
    center_y = sum(point[1] for point in shoulders) / 2
    top = sum(point[2] for point in shoulders) / 2 + .08
    used = {v for tri in cape_body_triangles(model, skin) for v in tri}
    rear = [points[v, 0] for v in used if abs(points[v, 2] - top) < .14
            and abs(points[v, 1] - center_y) < .24]
    assert rear
    back = min(rear)
    anchor_triangles = []
    for tri in cape_body_triangles(model, skin):
        a, b, c = points[list(tri)]
        determinant = (b[2] - c[2]) * (a[1] - c[1]) + (c[1] - b[1]) * (a[2] - c[2])
        if abs(determinant) < .000001:
            continue
        u = ((b[2] - c[2]) * (center_y - c[1]) + (c[1] - b[1]) * (top - c[2])) / determinant
        v = ((c[2] - a[2]) * (center_y - c[1]) + (a[1] - c[1]) * (top - c[2])) / determinant
        barycentric = np.array((u, v, 1 - u - v))
        if min(barycentric) >= 0:
            anchor_triangles.append((float(barycentric @ points[list(tri), 0]), tri, barycentric))
    assert anchor_triangles
    back, anchor_tri, anchor_weights = min(anchor_triangles, key=lambda item: item[0])
    anchor_bind = np.column_stack((np.ndarray((model.vertex_count, 3), '<f4', model.vertices, strides=(48, 4)),
                                   np.ones(model.vertex_count)))[list(anchor_tri)]
    anchor_skin = np.ndarray((model.vertex_count, 4), 'u1', model.vertices, offset=12,
                             strides=(48, 1))[list(anchor_tri)] / 255
    anchor_bones = np.ndarray((model.vertex_count, 4), 'u1', model.vertices, offset=16,
                              strides=(48, 1))[list(anchor_tri)]
    authored.bones = model.bones[:max(parent, int(anchor_bones.max())) + 1]
    inverse = np.linalg.inv(reference[parent])
    cape = {v for row in donor_skin.submeshes if 1502 <= visual.u16(row, 0) <= 1506
            for tri in triangles(donor_skin, row) for v in tri}
    heights = [struct.unpack_from("<f", donor.vertices, v * 48 + 8)[0] for v in cape]
    high, low = max(heights), min(heights)
    body_faces = points[np.array(cape_body_triangles(model, skin))]

    def positioned(source):
        _, y, z = source
        depth = max(0, min(1, (high - z) / (high - low)))
        x = back - .03 * SCALE - .28 * SCALE * depth + .02 * SCALE * (abs(y) / .48) ** 2
        y, height = center_y + y * .72 * WIDTH, top - (high - z) * .68 * SCALE
        # Keep the whole cloak behind the body: sample the rear surface around this point and clear the furthest.
        rear = None
        for dy, dz in ((0, 0), (0, .15), (0, -.15), (.12, 0), (-.12, 0), (.12, -.12), (-.12, -.12)):
            for scale in (1, .75, .5, .25):
                qy, qz = center_y + (y - center_y) * scale + dy, height + dz
                a, b, c = (body_faces[:, i] for i in range(3))
                determinant = (b[:, 2] - c[:, 2]) * (a[:, 1] - c[:, 1]) + (c[:, 1] - b[:, 1]) * (a[:, 2] - c[:, 2])
                valid = abs(determinant) > .000001
                u = np.divide((b[:, 2] - c[:, 2]) * (qy - c[:, 1]) + (c[:, 1] - b[:, 1]) * (qz - c[:, 2]),
                              determinant, out=np.zeros(len(a)), where=valid)
                v = np.divide((c[:, 2] - a[:, 2]) * (qy - c[:, 1]) + (a[:, 1] - c[:, 1]) * (qz - c[:, 2]),
                              determinant, out=np.zeros(len(a)), where=valid)
                hits = valid & (u >= 0) & (v >= 0) & (u + v <= 1)
                if hits.any():
                    found = (u * a[:, 0] + v * b[:, 0] + (1 - u - v) * c[:, 0])[hits].min()
                    rear = found if rear is None else min(rear, found)
                    break
        if rear is not None:
            x = min(x, rear - CLEARANCE)
        x += .025 * max(0, 1 - depth / .32)
        reference_point = (x, y, height, 1)
        return (inverse @ np.array(reference_point))[:3]

    mapping = {}
    for index in CAPE_BONES:
        source = donor.bones[index]
        assert source['parent_bone'] == (10 if index == 18 else CAPE_BONES[CAPE_BONES.index(index) - 1])
        bone = copy.deepcopy(source)
        pivot = (inverse @ np.array((back - .03, center_y, top, 1)))[:3] if index == 18 \
            else positioned(source['pivot'])
        bone.update(parent_bone=parent if index == 18 else mapping[source['parent_bone']],
                    key_bone_id=-1, bone_name_crc=0, pivot=tuple(pivot))
        for name in ('rotation', 'translation', 'scale'):
            track = bone[name]
            track.global_sequence = -1
            track.external.clear()
            track.timestamps, track.values = [], []
            for sequence_index, q in enumerate(model.sequences):
                resolved = model.sequences[animation.sequence(model, q['id'])]
                action = resolved['id']
                if action not in {seq['id'] for seq in donor.sequences}:
                    action = 0
                source_index = animation.sequence(donor, action)
                times, values = animation.keys(source[name], source_index)
                times, values = copy.deepcopy(times), copy.deepcopy(values)
                if name == 'rotation' and values:
                    _, initial = animation.keys(source[name], animation.sequence(donor, 0))
                    a = animation.quat(initial[0])
                    initial_inverse = (-a[0], -a[1], -a[2], a[3])
                    remapped = []
                    for value in values:
                        delta = np.array(animation.multiply(animation.quat(value), initial_inverse))
                        if delta[3] < 0:
                            delta = -delta
                        # Retain the authored flutter with a smaller swing on this shorter cape.
                        delta = np.array((0, 0, 0, 1)) * .55 + delta * .45
                        remapped.append(animation.packed(delta))
                    values = remapped
                if name == 'rotation' and index == 18:
                    # Cloth is held at the shoulder but hangs under gravity as the torso pitches.
                    source_duration = donor.sequences[source_index]['duration']
                    key_times = sorted(set([round(q['duration'] * i / 16) for i in range(17)]
                                           + [round(t * q['duration'] / max(1, source_duration)) for t in times]))
                    def donor_delta(clock):
                        if not values:
                            return (0, 0, 0, 1)
                        at = min(range(len(times)), key=lambda i: abs(times[i] - clock))
                        return animation.quat(values[at])
                    corrected = []
                    for clock in key_times:
                        current = animation.pose_matrices(authored, q['id'], clock, sequence_index)[parent]
                        rotation = np.linalg.inv(current[:3, :3]) @ reference[parent, :3, :3]
                        # Keep the hanging frame upright while the shoulder attachment moves with the torso.
                        pitch = (math.copysign(math.sqrt(max(0, 1 + rotation[0, 0]
                                     - rotation[1, 1] - rotation[2, 2])) / 2, rotation[2, 1] - rotation[1, 2]),
                                 math.copysign(math.sqrt(max(0, 1 - rotation[0, 0]
                                     + rotation[1, 1] - rotation[2, 2])) / 2, rotation[0, 2] - rotation[2, 0]),
                                 math.copysign(math.sqrt(max(0, 1 - rotation[0, 0]
                                     - rotation[1, 1] + rotation[2, 2])) / 2, rotation[1, 0] - rotation[0, 1]),
                                 math.sqrt(max(0, 1 + np.trace(rotation))) / 2)
                        lean = max(0, -math.atan2(rotation[0, 2], rotation[2, 2]))
                        flare = (0, math.sin(lean / 2), 0, math.cos(lean / 2))
                        pitch = animation.multiply(pitch, flare)
                        corrected.append(animation.packed(animation.multiply(
                            pitch, donor_delta(clock * source_duration / max(1, q['duration'])))))
                    times, values = key_times, corrected
                    duration = q['duration']
                else:
                    duration = donor.sequences[source_index]['duration']
                track.timestamps.append([min(q['duration'], round(t * q['duration'] / max(1, duration)))
                                         for t in times])
                track.values.append(values)
            track.timestamp_spans = track.value_spans = [(0, 0)] * len(model.sequences)
        if index == 18:
            track = bone['translation']
            track.interpolation = 1
            for sequence_index, q in enumerate(model.sequences):
                times = bone['rotation'].timestamps[sequence_index]
                values = []
                for clock in times:
                    matrices = animation.pose_matrices(authored, q['id'], clock, sequence_index)
                    anchor_points = np.einsum('vs,vsij,vj->vi', anchor_skin, matrices[anchor_bones], anchor_bind)[:, :3]
                    normal = np.cross(anchor_points[1] - anchor_points[0], anchor_points[2] - anchor_points[0])
                    normal /= np.linalg.norm(normal)
                    if normal[0] > 0:
                        normal = -normal
                    anchor = anchor_weights @ anchor_points + normal * .03
                    local = np.linalg.inv(matrices[parent]) @ np.array((*anchor, 1))
                    values.append(tuple(local[:3] - np.array(bone['pivot'])))
                track.timestamps[sequence_index], track.values[sequence_index] = times, values
        mapping[index] = len(model.bones)
        model.bones.append(bone)
    assert len(model.bones) <= 256

    def fit(record):
        data = bytearray(record)
        struct.pack_into('<3f', data, 0, *positioned(struct.unpack_from('<3f', data)))
        normal = inverse[:3, :3] @ np.array((-1, 0, 0))
        struct.pack_into('<3f', data, 20, *(normal / np.linalg.norm(normal)))
        z = struct.unpack_from('<f', record, 8)[0]
        depth = max(0, min(1, (high - z) / (high - low)))
        stops = ((0, parent), (.15, mapping[18]), (.58, mapping[28]), (1, mapping[37]))
        at = min(2, next((i for i in range(3) if depth <= stops[i + 1][0]), 2))
        fraction = (depth - stops[at][0]) / (stops[at + 1][0] - stops[at][0])
        weight = round(max(0, min(1, fraction)) * 255)
        ordered = [(stops[at][1], 255 - weight), (stops[at + 1][1], weight)]
        data[12:20] = bytes([weight for _, weight in ordered] + [0] * (4 - len(ordered))
                            + [bone for bone, _ in ordered] + [0] * (4 - len(ordered)))
        return data

    return fit, {'parent': parent, 'bones': list(mapping.values()), 'top': top, 'back': back}


def cape_surfaces(model, vertices, meshes, skin, donor, donor_skin, batch):
    """Retain authored cape topology and UVs on an animated chain suspended from the upper back."""
    spine = model.key_bone_lookup[4]
    fit, _ = cape_rig(model, skin, donor, donor_skin)
    for geoset in range(1502, 1507):
        source = [r for r in donor_skin.submeshes if visual.u16(r, 0) == geoset]
        used = {v for row in source for tri in triangles(donor_skin, row) for v in tri}
        mapping = {}
        for vertex in sorted(used):
            data = fit(donor.vertices[vertex * 48:(vertex + 1) * 48])
            mapping[vertex] = len(vertices) // 48
            vertices.extend(data)
        row = bytearray(source[0])
        visual.patch16(row, 18, spine)
        faces = [tuple(mapping[v] for v in tri) for mesh in source for tri in triangles(donor_skin, mesh)]
        meshes.append({'row': bytes(row), 'batches': [batch], 'geoset': geoset, 'triangles': faces,
                       'family': 'armor'})
