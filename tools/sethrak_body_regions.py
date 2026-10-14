"""Map Sethrak anatomy explicitly to Wrath's sleeve, torso, hand and trouser atlas regions."""

import math
import struct

import numpy as np


def children(model, root):
    result = {root}
    for _ in model.bones:
        expanded = result | {i for i, b in enumerate(model.bones) if b['parent_bone'] in result}
        if expanded == result:
            return result
        result = expanded
    raise ValueError('Cyclic skeleton')


def cylinder(point, first, last):
    axis = np.asarray(last) - first
    length = np.linalg.norm(axis)
    axis /= length
    reference = np.array([1.0, 0.0, 0.0])
    reference -= axis * np.dot(reference, axis)
    reference /= np.linalg.norm(reference)
    side = np.cross(axis, reference)
    delta = np.asarray(point) - first
    t = np.clip(np.dot(delta, axis) / length, 0, 1)
    angle = math.atan2(np.dot(delta, side), np.dot(delta, reference))
    return (angle / (2 * math.pi) + 0.5) % 1, float(t)


def waist_height(model):
    hip = model.bones[model.key_bone_lookup[55]]['parent_bone']
    return model.bones[hip]['pivot'][2]


def old_collar_height(model, point, back):
    neck = model.bones[model.key_bone_lookup[49]]['pivot']
    front = model.bones[model.key_bone_lookup[50]]['pivot'][2] - 0.06
    dx, dy = point[0] - neck[0], point[1] - neck[1]
    facing = max(0, dx / max(math.hypot(dx, dy), 0.00001))
    return back + facing * (front - back)


def collar_height(model, point, back):
    neck = model.bones[model.key_bone_lookup[49]]['pivot']
    shoulder_top = neck[2] + 0.075
    return old_collar_height(model, point, shoulder_top)


def mirrored_u(angle):
    # Player torso/leg components store one side: front at the left, back at the right.
    return 0.5035 + abs(angle) / math.pi * 0.491


def body_uvs(model, triangles, collar):
    positions = [struct.unpack_from('<3f', model.vertices, i * 48) for i in range(model.vertex_count)]
    bones = model.bones
    hip = bones[model.key_bone_lookup[55]]['parent_bone']
    waist = waist_height(model)
    arms = []
    legs = []
    for finger in (8, 13):
        palm = bones[model.key_bone_lookup[finger]]['parent_bone']
        forearm = bones[palm]['parent_bone']
        upper = bones[forearm]['parent_bone']
        arms.append((children(model, upper), children(model, forearm), children(model, palm), upper, forearm, palm))
    for thigh_key, knee_key, ankle_key in ((55, 57, 60), (56, 58, 59)):
        thigh, knee, ankle = (model.key_bone_lookup[k] for k in (thigh_key, knee_key, ankle_key))
        legs.append((children(model, thigh), thigh, knee, ankle))

    def weight(tri, group):
        return sum(model.vertices[v * 48 + 12 + i] for v in tri for i in range(4)
                   if model.vertices[v * 48 + 16 + i] in group)

    result = []
    for tri in triangles:
        arm = max(arms, key=lambda a: weight(tri, a[0]))
        leg = max(legs, key=lambda a: weight(tri, a[0]))
        uvs = []
        shoulder_cap = all(p[2] >= 1.55 and abs(p[1]) <= 0.36 for p in (positions[v] for v in tri))
        if weight(tri, arm[0]) >= 300 and not shoulder_cap:
            if weight(tri, arm[2]) >= 300:
                first = bones[arm[5]]['pivot']
                last = tuple(first[i] + 0.14 * (first[i] - bones[arm[4]]['pivot'][i])
                             / math.dist(first, bones[arm[4]]['pivot']) for i in range(3))
                bounds = (0.5, 0.625)
            elif weight(tri, arm[1]) >= 300:
                first, last, bounds = bones[arm[4]]['pivot'], bones[arm[5]]['pivot'], (0.25, 0.5)
            else:
                first, last, bounds = bones[arm[3]]['pivot'], bones[arm[4]]['pivot'], (0.0, 0.25)
            for v in tri:
                u, t = cylinder(positions[v], first, last)
                uvs.append([u * 0.5, bounds[0] + t * (bounds[1] - bounds[0])])
        else:
            center = bones[hip]['pivot']
            for v in tri:
                x, y, z = positions[v]
                neck = bones[model.key_bone_lookup[49]]['pivot']
                blend = min(1, max(0, (z - 1.50) / 0.30))
                origin = center[0] + blend * (neck[0] - center[0])
                angle = math.atan2(y, x - origin)
                u = mirrored_u(angle)
                old_top = old_collar_height(model, positions[v], collar)
                top = old_top + blend * (collar_height(model, positions[v], collar) - old_top)
                torso_split = waist + (top - waist) * 0.33
                if z >= torso_split:
                    height = (top - z) / (top - torso_split) * 0.25
                elif z >= waist:
                    height = 0.25 + (torso_split - z) / (torso_split - waist) * 0.125
                else:
                    first, knee, last = (bones[i]['pivot'] for i in leg[1:])
                    if z >= knee[2]:
                        height = 0.375 + (waist - z) / (waist - knee[2]) * 0.25
                    else:
                        height = 0.625 + (knee[2] - z) / (knee[2] - last[2]) * 0.25
                    # Center each leg on its thigh/knee/ankle axis, preserving the sagittal mirror.
                    upper, lower = (first, knee) if z >= knee[2] else (knee, last)
                    t = min(1, max(0, (upper[2] - z) / (upper[2] - lower[2])))
                    cx, cy = (upper[i] + t * (lower[i] - upper[i]) for i in (0, 1))
                    u = mirrored_u(math.atan2(y - cy, x - cx))
                uvs.append([u, min(0.875, max(0.0, height))])
        result.extend(uvs)
    return result
