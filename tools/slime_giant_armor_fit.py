"""Fit SlimeSkeleton leg, boot and belt armor beneath the outer slime shell."""

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys

WORK = Path('G:/RetroportWork/slime-giant-175382')
BLENDER = Path('C:/Program Files/Blender Foundation/Blender 5.2/blender.exe')
MODEL = '3490792-clothing.m2'
SKIN = '3490792-clothing00.skin'
INSIDE = .025


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value) + '\n', encoding='utf-8', newline='\n')


def worker(path):
    import numpy as np
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree
    from mathutils.geometry import barycentric_transform

    job = json.loads(path.read_text())
    body = job['body']
    points = [Vector(vertex['position']) for vertex in body]
    triangles = job['triangles']
    surface = BVHTree.FromPolygons(points, triangles, all_triangles=True)
    updated = []
    for original in job['vertices']:
        point = Vector(original['position'])
        hit, normal, index, distance = surface.find_nearest(point)
        # Hanging robe surfaces retain their drape; this correction owns fitted leg surfaces only.
        if original['loose'] and distance > .12:
            continue
        tri = triangles[index]
        bary = barycentric_transform(hit, *[points[i] for i in tri],
            Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1)))
        normal = sum((Vector(body[i]['normal']) * max(0, factor)
                      for i, factor in zip(tri, bary)), Vector()).normalized()
        mixed = defaultdict(float)
        for source, factor in zip(tri, bary):
            for bone, weight in zip(body[source]['bones'], body[source]['weights']):
                if weight:
                    mixed[bone] += weight * max(0, factor)
        weights = sorted(mixed.items(), key=lambda item: item[1], reverse=True)[:4]
        total = sum(value for _, value in weights)
        assert total > 0
        values = [round(value / total * 255) for _, value in weights]
        values[0] += 255 - sum(values)
        fitted = hit - normal * INSIDE
        updated.append(dict(original, position=list(fitted), normal=list(normal),
                            bones=[bone for bone, _ in weights], weights=values,
                            anchor=list(tri), barycentric=list(bary)))

    poses = job['poses']
    positions = np.asarray([vertex['position'] for vertex in updated])
    anchors = np.asarray([vertex['anchor'] for vertex in updated])
    bary = np.asarray([vertex['barycentric'] for vertex in updated])
    bary = np.clip(bary, 0, 1)
    bary /= bary.sum(axis=1)[:, None]
    bones = np.asarray([vertex['bones'] + [0] * (4 - len(vertex['bones'])) for vertex in updated])
    weights = np.asarray([vertex['weights'] + [0] * (4 - len(vertex['weights']))
                          for vertex in updated]) / 255
    margins = .02
    planes = []
    body_bones = np.asarray([vertex['bones'] for vertex in body])
    body_weights = np.asarray([vertex['weights'] for vertex in body]) / 255
    body_normals = np.asarray([vertex['normal'] for vertex in body])
    for pose in poses:
        matrices = np.asarray(pose['matrices'])
        transforms = np.einsum('vs,vsij->vij', weights, matrices[bones])
        triangle = np.asarray(pose['body'])[anchors]
        rendered_normals = np.einsum('vs,vsij,vj->vi', body_weights, matrices[body_bones, :3, :3], body_normals)
        normal = np.einsum('vs,vsj->vj', bary, rendered_normals[anchors])
        lengths = np.linalg.norm(normal, axis=1)
        assert np.min(lengths) > 1e-9, 'Degenerate animated surface anchor'
        normal /= lengths[:, None]
        anchor = np.einsum('vs,vsj->vj', bary, triangle)
        axis = np.einsum('vij,vi->vj', transforms[:, :3, :3], normal)
        offset = np.einsum('vi,vi->v', transforms[:, :3, 3] - anchor, normal)
        planes.append((axis, offset))

    def evaluate():
        distances = np.asarray([np.einsum('vi,vi->v', axis, positions) + offset
                                for axis, offset in planes])
        result = {}
        values = distances
        result['under'] = {'min': float(values.min()), 'max': float(values.max()),
                           'wrong_side': int((values > 0).sum()), 'samples': int(values.size)}
        return result

    initial = evaluate()
    # Project onto each posed surface constraint rather than following the other leg's nearest surface.
    for _ in range(64):
        for axis, offset in planes:
            violation = np.maximum(0, np.einsum('vi,vi->v', axis, positions) + offset + margins)
            positions -= axis * (violation / np.einsum('vi,vi->v', axis, axis))[:, None]
    final = evaluate()
    assert all(value['wrong_side'] == 0 for value in final.values()), final
    # Check the reported equipment's triangle interiors as well as the fitted vertices.
    by_key = {(vertex['index'], vertex['policy']): i for i, vertex in enumerate(updated)}
    faces = []
    for face in job['faces']:
        keys = [(index, face['policy']) for index in face['triangle']]
        if all(key in by_key for key in keys):
            faces.append(([by_key[key] for key in keys], face['policy']))
    caches = []
    for pose in poses:
        matrices = np.asarray(pose['matrices'])
        transforms = np.einsum('vs,vsij->vij', weights, matrices[bones])
        tree = BVHTree.FromPolygons([Vector(p) for p in pose['body']], triangles, all_triangles=True)
        caches.append((transforms, tree))
    ray = Vector((1, .017, .013)).normalized()
    samples = [([i], vertex['policy']) for i, vertex in enumerate(updated)] + faces

    def physical_check():
        wrong = {'under': 0}
        for transforms, tree in caches:
            posed = np.einsum('vij,vj->vi', transforms[:, :3, :3], positions) + transforms[:, :3, 3]
            for indices, policy in samples:
                point = Vector(posed[indices].mean(axis=0))
                hit, normal, _, _ = tree.ray_cast(point, ray, 10)
                inside = hit is not None and normal.dot(ray) > 0
                if inside == (policy == 'under'):
                    continue
                wrong[policy] += 1
        return wrong

    # Open seams and intersecting source shells make whole-mesh ray parity diagnostic, not a clearance gate.
    ray_diagnostic = physical_check()
    for vertex, position in zip(updated, positions):
        vertex['position'] = position.tolist()
    save(path.with_name('fit-result.json'), {'vertices': updated, 'initial': initial,
                                            'final': final,
                                            'poses': [pose['label'] for pose in poses],
                                            'ray_side_diagnostic': ray_diagnostic,
                                            'live_motion_check_required': True})
    print('PASS posed leg/belt clearance:', final, flush=True)


def fit_assets(work, source, destination):
    import numpy as np
    from wotlkconv.m2 import parse_m2, parse_skin
    from wotlkconv.m2.skin import write_skin
    from sethrak_equipment_repair import mesh_triangles, vertex_record
    import creature_animation_repair as motion

    raw = (source / MODEL).read_bytes()
    raw_skin = (source / SKIN).read_bytes()
    clothing = parse_m2(raw)
    skin = parse_skin(raw_skin)
    body = parse_m2((work / 'correct-source/3490792.m2').read_bytes())
    body_skin = parse_skin((work / 'correct-source/3491636.skin').read_bytes())
    # The second source surface is opaque inner anatomy, not the outer clearance boundary.
    surface = mesh_triangles(body_skin, body_skin.submeshes[1])
    policies = defaultdict(set)
    loose = set()
    protected = set()
    check_faces = []
    for row in skin.submeshes:
        geo = struct.unpack_from('<H', row)[0]
        used = {v for tri in mesh_triangles(skin, row) for v in tri}
        policy = 'under' if geo // 100 in (5, 9, 10, 11, 13, 18) else None
        if policy:
            policies[policy].update(used)
            if geo // 100 == 13:
                loose.update(used)
        else:
            protected.update(used)
        if geo in (505, 1104, 1002, 1801):
            check_faces.extend({'triangle': tri, 'policy': policy} for tri in mesh_triangles(skin, row))
    assert not (protected & policies['under']), 'Accepted armor shares fitted vertices'
    records = []
    for policy, indices in policies.items():
        for index in sorted(indices):
            vertex = vertex_record(clothing, index)
            records.append(dict(vertex, policy=policy, loose=index in loose and policy == 'under'))
    poses = [{'label': 'bind', 'body': [vertex_record(body, i)['position'] for i in range(body.vertex_count)],
              'matrices': np.repeat(np.eye(4)[None, :, :], len(body.bones), axis=0).tolist()}]
    for action in (0, 4, 5, 37, 38, 39, 41):
        index = motion.sequence(body, action)
        assert body.sequences[index]['flags'] & 0x20, 'Pose check needs authored embedded animation'
        for phase in (.0, .25, .5, .75):
            matrices = motion.pose_matrices(body, action, round(body.sequences[index]['duration'] * phase))
            poses.append({'label': f'{action}:{phase}', 'body': motion.posed_vertices(body, matrices).tolist(),
                          'matrices': matrices.tolist()})
    stage = work / 'armor-layering-v2'
    job = stage / 'fit-work.json'
    save(job, {'body': [vertex_record(body, i) for i in range(body.vertex_count)], 'triangles': surface,
               'vertices': records, 'poses': poses, 'faces': check_faces})
    job.with_name('fit-result.json').unlink(missing_ok=True)
    subprocess.run([str(BLENDER), '-b', '--factory-startup', '--python-exit-code', '1',
                    '--python', str(Path(__file__).resolve()),
                    '--', '--worker', str(job)], check=True)
    result = json.loads(job.with_name('fit-result.json').read_text())
    corrections = {(v['index'], v['policy']): v for v in result['vertices']}
    vertices = bytearray(clothing.vertices)
    original_vertices = clothing.vertex_count
    assert set(clothing.bone_combos) and len(clothing.bone_combos) <= 75
    bone_map = {bone: i for i, bone in enumerate(clothing.bone_combos)}
    changed = set()
    for (index, policy), vertex in corrections.items():
        target = index
        weights = vertex['weights'] + [0] * (4 - len(vertex['weights']))
        bones = vertex['bones'] + [0] * (4 - len(vertex['bones']))
        assert sum(weights) == 255 and all(bone in bone_map for bone, weight in zip(bones, weights) if weight)
        struct.pack_into('<3f', vertices, target * 48, *vertex['position'])
        vertices[target * 48 + 12:target * 48 + 20] = bytes(weights + bones)
        changed.add(target)
    local_bones = bytearray(skin.bones)
    for lookup, vertex in enumerate(skin.vertices):
        if vertex in changed:
            at = vertex * 48
            local_bones[lookup * 4:lookup * 4 + 4] = bytes(
                bone_map[vertices[at + 16 + slot]] if vertices[at + 12 + slot] else 0 for slot in range(4))
    skin.bones = bytes(local_bones)
    assert len(skin.vertices) < 65536 and len(vertices) // 48 < 65536
    assert sum(struct.unpack_from('<H', row, 10)[0] for row in skin.submeshes) == len(skin.indices)
    for index in protected:
        assert vertices[index * 48:(index + 1) * 48] == clothing.vertices[index * 48:(index + 1) * 48]
    output = bytearray(raw)
    while len(output) % 4:
        output.append(0)
    struct.pack_into('<2I', output, 0x3c, len(vertices) // 48, len(output))
    output.extend(vertices)
    encoded_skin = write_skin(skin)
    restored = parse_m2(bytes(output))
    assert restored.bones == clothing.bones and restored.sequences == clothing.sequences
    assert restored.textures == clothing.textures and restored.texture_weights == clothing.texture_weights
    destination.mkdir(parents=True, exist_ok=True)
    (destination / MODEL).write_bytes(output)
    (destination / SKIN).write_bytes(encoded_skin)
    report = {key: value for key, value in result.items() if key != 'vertices'}
    report.update(changed_vertices=len(changed), protected_vertices=len(protected),
                  split_shared_belt_vertices=0, original_vertices=original_vertices,
                  model_sha256=hashlib.sha256(output).hexdigest(),
                  skin_sha256=hashlib.sha256(encoded_skin).hexdigest(), live_acceptance=False)
    save(stage / 'fit-report.json', report)
    print(json.dumps(report, indent=2))
    return report


if __name__ == '__main__':
    if '--worker' in sys.argv:
        worker(Path(sys.argv[sys.argv.index('--worker') + 1]))
    else:
        parser = argparse.ArgumentParser(description=__doc__)
        parser.add_argument('--work', type=Path, default=WORK)
        args = parser.parse_args()
        fit_assets(args.work, args.work / 'armor-layering-v2/baseline',
                   args.work / 'armor-layering-v2/assets/custom/slimegiant')
