"""Build transparent armor surfaces on both original Centaur bodies without changing their skin UVs."""

import copy
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import struct
import subprocess
import sys

WORK = Path('G:/RetroportWork/centaur')
BLENDER = Path('C:/Program Files/Blender Foundation/Blender 5.2/blender.exe')


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8', newline='\n')


def leg_belts(polygons):
    import numpy as np
    from saberon_equipment_fit import clip

    legs = [p for p in polygons if p[0]['part'] == 'leg']
    edges, positions = Counter(), {}
    for polygon in legs:
        keys = [tuple(round(c, 5) for c in v['position']) for v in polygon]
        positions.update((key, v['position']) for key, v in zip(keys, polygon))
        edges.update(tuple(sorted((a, b))) for a, b in zip(keys, keys[1:] + keys[:1]) if a != b)
    # Use the four actual leg sockets, excluding the separate horizontal fur cutoffs.
    boundary = [edge for edge, count in edges.items() if count == 1 and min(p[2] for p in edge) > 1]
    assert boundary and set(Counter(p for edge in boundary for p in edge).values()) == {2}
    bands = []
    for front in (False, True):
        for side in (False, True):
            segments = np.array([[positions[p] for p in edge] for edge in boundary
                                 if (edge[0][0] > .35) == front and (edge[0][1] > 0) == side])
            assert len(segments) >= 10
            starts = segments[:, 0]
            directions = segments[:, 1] - starts
            lengths_squared = np.sum(directions ** 2, axis=1)
            distances = {}

            def depth(vertex):
                key = tuple(vertex['position'])
                if key not in distances:
                    delta = np.array(key) - starts
                    t = np.clip(np.sum(delta * directions, axis=1) / lengths_squared, 0, 1)
                    distances[key] = float(np.linalg.norm(delta - directions * t[:, None], axis=1).min())
                return distances[key]

            def band(polygon):
                # Keep the original boundary edges: new skinned points can bow away from pants in motion.
                strip = clip(polygon, lambda v: .115 - depth(v))
                center_x = .85 if front else -.33
                angles = [math.atan2(v['position'][0] - center_x, abs(v['position'][1]) - .2) for v in strip]
                split = bool(angles) and max(angles) - min(angles) > math.pi
                for outward in ((True, False) if split else (None,)):
                    piece = (clip(strip, lambda v: (v['position'][0] - center_x) * (1 if outward else -1))
                             if split else strip)
                    projected = []
                    for vertex in piece:
                        x, y, _ = vertex['position']
                        angle = math.atan2(x - center_x, abs(y) - .2)
                        if split and abs(x - center_x) < 1e-6 and abs(y) < .2:
                            angle = math.pi if outward else -math.pi
                        uv = [.25 + 2 / 2048 + (.25 - 4 / 2048) * (.5 + angle / (2 * math.pi)),
                              .375 + 1 / 1024 + (.25 - 2 / 1024) * min(1, depth(vertex) / .115)]
                        projected.append(dict(vertex, uv=uv))
                    bands.extend([[projected[0], projected[i], projected[i + 1]]
                                  for i in range(1, len(projected) - 1)])

            for polygon in legs:
                if (polygon[0]['position'][0] > .35) == front and (polygon[0]['position'][1] > 0) == side:
                    band(polygon)
    return bands


def transfer(path):
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree
    from mathutils.geometry import barycentric_transform

    job = json.loads(path.read_text())
    donor = job['donor']
    points = [Vector(v['position']) for v in donor]
    by_region = {}
    for tri in job['donor_body']:
        u, v = [sum(donor[i]['uv'][axis] for i in tri) / 3 for axis in (0, 1)]
        region = (0 if v < .25 else 1 if v < .5 else 2) if u < .25 else (
            3 if v < .25 else 4 if v < .375 else 5 if v < .625 else 6 if v < .875 else 7)
        by_region.setdefault(region, []).append(tri)
    assert set(by_region) == set(range(8))
    trees = {r: BVHTree.FromPolygons(points, tris, all_triangles=True) for r, tris in by_region.items()}

    def project(vertex, selected):
        point = Vector(vertex['position'])
        epsilon = 1 / 8192
        if selected in (3, 4):
            angle = math.atan2(abs(point.y), point.x - .86)
            inset = 6 / 2048  # Skip the legacy atlas border gutter as well as bilinear/mip bleed.
            return dict(vertex, uv=[.25 + inset + (.25 - 2 * inset) * angle / math.pi,
                                    max(epsilon, min(.375 - epsilon, (2.79 - point.z) / .97 * .375))],
                        region=selected)
        if selected >= 5:
            center_x = .85 if point.x > .35 else -.65
            if selected == 7:
                angle = math.atan2(point.y - math.copysign(.2, point.y), point.x - center_x)
                return dict(vertex, uv=[.25 + .25 * abs(angle / math.pi),
                                        .875 + .125 * (1 - min(1, max(0, point.z / .21)))], region=selected)
            if selected != 7:
                center_x = (.856 + (.892 - .856) * min(1, max(0, (1.57 - point.z) / .82))
                            if center_x > 0 else -.344 - .315 * min(1, max(0, (1.66 - point.z) / .86)))
            angle = math.atan2(point.y - math.copysign(.2, point.y), point.x - center_x)
            u = .25 + epsilon + (.25 - 2 * epsilon) * abs(angle / math.pi)
            low, high, v0, v1 = (.0, .21, .875, 1) if selected == 7 else (
                (1.2, 1.87 if center_x > 0 else 1.73, .375, .625) if selected == 5 else
                (.76 if center_x > 0 else .855, 1.2, .625, .875))
            v = v0 + epsilon + (v1 - v0 - 2 * epsilon) * (
                1 - min(1, max(0, (point.z - low) / (high - low))))
            return dict(vertex, uv=[u, v], region=selected)
        hit, _, index, _ = trees[selected].find_nearest(point)
        tri = by_region[selected][index]
        uv = barycentric_transform(hit, *[points[i] for i in tri],
                                   *[Vector((*donor[i]['uv'], 0)) for i in tri])
        low, high = ((0, .25), (.25, .5), (.5, 1))[selected]
        uv.x, uv.y = max(epsilon, min(.25 - epsilon, uv.x)), max(low + epsilon, min(high - epsilon, uv.y))
        return dict(vertex, uv=[uv.x, uv.y], region=selected)

    polygons = []
    for polygon in job['polygons']:
        selected = polygon[0]['region']
        polygons.append([project(vertex, selected) for vertex in polygon])
    target_points = [Vector(v['position']) for v in job['target']]
    target_tree = BVHTree.FromPolygons(target_points, job['target_body'], all_triangles=True)
    back_triangles = job['horse_body']
    back_tree = BVHTree.FromPolygons(target_points, back_triangles, all_triangles=True)
    cape_vertices, capes, cape_cache = [], [], {}

    def cape_vertex(vertex):
        key = tuple(round(v, 6) for v in (*vertex['position'], *vertex['uv']))
        if key not in cape_cache:
            angle = max(-1, min(1, vertex['position'][1] / .44)) * math.pi * .30
            origin = Vector((vertex['position'][0], math.sin(angle) * 3, 1.5 + math.cos(angle) * 3))
            direction = Vector((0, -math.sin(angle), -math.cos(angle)))
            hit, _, triangle, _ = back_tree.ray_cast(origin, direction)
            if hit is None:
                hit, _, triangle, _ = back_tree.find_nearest(origin + direction * 2.7)
            tri = back_triangles[triangle]
            assert hit is not None, 'Cloak must stay over the horse back'
            factors = barycentric_transform(hit, *[target_points[i] for i in tri],
                                            Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1)))
            normal, weights = Vector(), {}
            for index, factor in zip(tri, factors):
                normal += Vector(job['target'][index]['normal']) * factor
                for bone, weight in zip(job['target'][index]['bones'], job['target'][index]['weights']):
                    weights[bone] = weights.get(bone, 0) + max(0, factor) * weight
            normal.normalize()
            strongest = sorted(weights.items(), key=lambda pair: pair[1], reverse=True)[:4]
            total = sum(weight for _, weight in strongest)
            normalized = [round(weight / total * 255) for _, weight in strongest]
            normalized[0] += 255 - sum(normalized)
            cape_cache[key] = len(cape_vertices)
            cape_vertices.append(dict(vertex, position=list(hit + normal * .018), normal=list(normal),
                                      bones=[bone for bone, _ in strongest], weights=normalized))
        return cape_cache[key]

    for cape in job['capes']:
        # A single regular cloth surface has a clean hem; projecting the donor's folded double layers did not.
        columns, rows = 16, 24
        grid = [[cape_vertex({'position': [.70 - 1.18 * row / rows, .44 * (2 * col / columns - 1), 0],
                              # The native cape atlas stores a mirrored half-panel, with its center at U=.992.
                              'uv': [.992 - .7426 * abs(2 * col / columns - 1), .004 + .989 * row / rows]})
                 for col in range(columns + 1)] for row in range(rows + 1)]
        faces = [tri for row in range(rows) for col in range(columns)
                 for tri in ([grid[row][col], grid[row][col + 1], grid[row + 1][col]],
                             [grid[row][col + 1], grid[row + 1][col + 1], grid[row + 1][col]])]
        capes.append({'geoset': cape['geoset'], 'triangles': faces})
    fitted = {}
    for index in job['equipment_vertices']:
        point = points[index]
        if index in job['rigid_vertices']:
            hit, normal, _, _ = target_tree.find_nearest(point)
            fitted[str(index)] = dict(position=list(hit + normal * .012))
        else:
            fitted[str(index)] = dict(position=list(point))
    save(path.with_name('transfer-result.json'), {'polygons': polygons, 'equipment_positions': fitted,
                                                'cape_vertices': cape_vertices, 'capes': capes,
                                                'regions': sorted({v['region'] for p in polygons for v in p})})


def prepare():
    import numpy as np
    from wotlkconv.m2 import parse_m2, parse_skin, write_md20
    from wotlkconv.m2.skel import parse_skel
    from wotlkconv.m2.skin import write_skin
    from wotlkconv.m2.types import Track
    from sethrak_equipment_repair import mesh_triangles, packed_skin, vertex_record
    from saberon_equipment_fit import clip, surface_normals
    from slime_giant_clothing import remap_rig, NAKED

    donor_root = Path('G:/RetroportWork/slime-giant-175382/source')
    donor = parse_m2((donor_root / '1721003.m2').read_bytes())
    donor.bones = parse_skel((donor_root / '2175552.skel').read_bytes()).bones
    donor_skin = parse_skin((donor_root / '1721013.skin').read_bytes())
    report = {'live_accepted': False, 'models': {}}
    for sex, identifier, skin_id, skel_id in ((0, 4036647, 4036674, 4224620), (1, 4081379, 4081384, 4226281)):
        source = WORK / 'source' / f'{identifier}.m2'
        original = hashlib.sha256(source.read_bytes()).hexdigest()
        model = parse_m2(source.read_bytes())
        skel = parse_skel((WORK / 'source' / f'{skel_id}.skel').read_bytes())
        parent = parse_skel((WORK / 'source/4224620.skel').read_bytes())
        model.bones = copy.deepcopy(skel.bones)
        model.key_bone_lookup = list(skel.key_bone_lookup)
        skin = parse_skin((WORK / 'source' / f'{skin_id}.skin').read_bytes())
        base = next(row for row in skin.submeshes if struct.unpack_from('<H', row)[0] == 0)
        anatomy = []
        for ordinal, row in enumerate(skin.submeshes):
            types = {model.textures[model.texture_combos[struct.unpack_from('<H', b, 16)[0]]]['type']
                     for b in skin.batches if struct.unpack_from('<H', b, 4)[0] == ordinal}
            geoset = struct.unpack_from('<H', row)[0]
            if (geoset in ({0, 101} if sex else {0}) and types == {11}
                    or sex and geoset == 201 and types in ({11}, {12})):
                anatomy.append(row)
        body_triangles = [tri for row in anatomy for tri in mesh_triangles(skin, row)]
        target = [vertex_record(model, i) for i in range(max(i for tri in body_triangles for i in tri) + 1)]
        normals = surface_normals(model, body_triangles)
        for index, normal in normals.items():
            if np.isfinite(normal).all():
                target[index]['normal'] = normal
        polygons = []
        neckline = model.bones[model.key_bone_lookup[6]]['pivot'][2] - .01
        adjacency = {}
        for tri in body_triangles:
            for index in tri:
                adjacency.setdefault(index, set()).update(tri)
        pending, component = set(adjacency), {}
        while pending:
            todo = [pending.pop()]
            group = set(todo)
            while todo:
                added = adjacency[todo.pop()] - group
                todo.extend(added)
                group.update(added)
                pending.difference_update(added)
            max_z = max(target[i]['position'][2] for i in group)
            positions = [target[i]['position'] for i in group]
            minimum_x = min(p[0] for p in positions)
            maximum_x = max(p[0] for p in positions)
            minimum_z = min(p[2] for p in positions)
            part = ('hoof' if max_z <= .21 else 'arm' if max(abs(p[1]) for p in positions) > 1.05
                    and max_z < 2.71 else 'skip' if max_z < 1 or minimum_z > 2.69
                    or
                    max(abs(p[1]) for p in positions) < .1 and max_z < 2 else
                    'back' if minimum_x < 0 and maximum_x > .5 else
                    'torso' if minimum_x > .6 and max_z > 2.1
                    else 'leg')
            for index in group:
                component[index] = part
        for tri in body_triangles:
            part = component[tri[0]]
            hoof = part == 'hoof'
            if part in ('skip', 'back'):
                continue
            polygon = [target[i] for i in tri]
            if part == 'torso':
                polygon = clip(polygon, lambda v: neckline - v['position'][2])
                polygon = clip(polygon, lambda v: v['position'][2] - 1.82)
            if not hoof:
                front = sum(target[i]['position'][0] for i in tri) / 3 > .35
                polygon = clip(polygon, lambda v: v['position'][2] - (.76 if front else .855))
            pieces = []
            if part == 'arm':
                side = 0 if sum(v['position'][1] for v in polygon) > 0 else 1
                elbow = np.array(model.bones[model.key_bone_lookup[61 if side else 62]]['pivot'])
                wrist = np.array(model.bones[111 if side else 108]['pivot'])
                axis = wrist - elbow
                axis /= np.linalg.norm(axis)
                upper = clip(polygon, lambda v: -np.dot(np.array(v['position']) - elbow, axis))
                lower = clip(polygon, lambda v: np.dot(np.array(v['position']) - elbow, axis))
                fore = clip(lower, lambda v: -np.dot(np.array(v['position']) - wrist, axis))
                hand = clip(lower, lambda v: np.dot(np.array(v['position']) - wrist, axis))
                pieces = [(upper, 0), (fore, 1), (hand, 2)]
            elif part == 'leg':
                pieces = [(clip(polygon, lambda v: v['position'][2] - 1.2), 5),
                          (clip(polygon, lambda v: 1.2 - v['position'][2]), 6)]
            else:
                pieces = [(polygon, 7 if hoof else 3 if sum(v['position'][2] for v in polygon) >
                           2.14 * len(polygon) else 4)]
            for piece, region in pieces:
                piece = [dict(v, region=region, hoof=hoof, part=part) for v in piece]
                polygons.extend([[piece[0], piece[i], piece[i + 1]] for i in range(1, len(piece) - 1)])
        mapping, fallback = remap_rig(donor, model)
        fitted_donor = []
        for i in range(max(donor_skin.vertices) + 1):
            vertex = vertex_record(donor, i)
            point = np.array(vertex['position'])
            for slot, weight in enumerate(vertex['weights']):
                if weight:
                    bone = vertex['bones'][slot]
                    assert bone in mapping, 'Equipment donor has an unmapped weighted bone'
                    point += weight / 255 * (np.array(model.bones[mapping[bone]]['pivot']) - donor.bones[bone]['pivot'])
                    vertex['bones'][slot] = mapping[bone]
            fitted_donor.append(dict(vertex, position=point.tolist()))
        donor_body, equipment, used, rigid, capes = [], [], set(), set(), []
        for ordinal, row in enumerate(donor_skin.submeshes):
            geoset = struct.unpack_from('<H', row)[0]
            batches = [b for b in donor_skin.batches if struct.unpack_from('<H', b, 4)[0] == ordinal]
            types = {donor.textures[donor.texture_combos[struct.unpack_from('<H', b, 16)[0]]]['type'] for b in batches}
            triangles = mesh_triangles(donor_skin, row)
            if geoset in NAKED and types == {1}:
                donor_body.extend(triangles)
            if geoset // 100 == 15 and types == {2}:
                capes.append({'geoset': geoset, 'triangles': triangles, 'row': row})
            # The fitted body replaces the donor's bare waist (1801), which otherwise spans the horse back.
            if geoset != 401 and geoset // 100 in (4, 8, 10, 12) and types in ({1}, {2}):
                if geoset // 100 in (4, 8):
                    # Donor double-sided cuffs fold onto themselves when shrinkwrapped to another arm.
                    equipment.append({'geoset': geoset, 'triangles': [], 'row': row, 'texture': 1,
                                      'surface_region': 1 if geoset // 100 == 4 else 0})
                    continue
                equipment.append({'geoset': geoset, 'triangles': triangles, 'row': row,
                                  'texture': next(iter(types))})
                used.update(i for tri in triangles for i in tri)
                if geoset // 100 in (4, 5, 8, 9, 11, 18):
                    rigid.update(i for tri in triangles for i in tri)
        work = WORK / 'clothing' / str(sex)
        job = work / 'transfer-work.json'
        save(job, {'donor': fitted_donor, 'donor_body': donor_body, 'target': target,
                   'target_body': body_triangles, 'polygons': polygons, 'equipment_vertices': sorted(used),
                   'horse_body': [tri for tri in body_triangles if component[tri[0]] == 'back'],
                   'rigid_vertices': sorted(rigid),
                   'capes': [{k: v for k, v in cape.items() if k != 'row'} for cape in capes]})
        subprocess.run([str(BLENDER), '--background', '--factory-startup', '--python-exit-code', '1',
                        '--python', str(Path(__file__).resolve()), '--', '--worker', str(job)], check=True)
        result = json.loads(job.with_name('transfer-result.json').read_text())
        assert result['regions'] == list(range(8)), 'Every gender must support arms, hands, torso and four legs'
        vertices, faces, hooves = bytearray(), [], []

        def emit(vertex, clearance=0):
            weights = list(vertex['weights']) + [0] * (4 - len(vertex['weights']))
            bones = [bone if weight else 0 for bone, weight in zip(vertex['bones'], vertex['weights'])]
            bones += [0] * (4 - len(bones))
            assert sum(weights) == 255 and all(0 <= bone < len(model.bones) for bone in bones)
            point = np.array(vertex['position']) + np.array(vertex['normal']) * clearance
            assert np.isfinite([*point, *vertex['uv']]).all()
            index = len(vertices) // 48
            vertices.extend(struct.pack('<3f4B4B3f2f2f', *point, *weights, *bones,
                                        *vertex['normal'], *vertex['uv'], 0, 0))
            return index

        for polygon in result['polygons']:
            (hooves if polygon[0].get('hoof') else faces).append(tuple(emit(vertex, .006) for vertex in polygon))
        batch = struct.pack('<12H', 0, 0, 0, 0, 65535, 0, 0, 1, 0, 0, 0, 0)
        meshes = [{'family': 'body', 'geoset': 1, 'row': base, 'batches': [batch], 'triangles': faces}]
        meshes.append({'family': 'body', 'geoset': 2002, 'row': base, 'batches': [batch], 'triangles': hooves})
        bands = leg_belts(result['polygons'])
        belt_batch = bytearray(batch)
        struct.pack_into('<H', belt_batch, 16, 2)
        meshes.append({'family': 'body', 'geoset': 1805, 'row': base, 'batches': [bytes(belt_batch)],
                       'triangles': [tuple(emit(v, .018) for v in tri) for tri in bands]})
        donor_indices = {}
        for entry in equipment:
            if 'surface_region' in entry:
                triangles = [tuple(emit(v, .024) for v in polygon) for polygon in result['polygons']
                             if polygon[0]['region'] == entry['surface_region']]
                meshes.append({'family': 'body', 'geoset': entry['geoset'], 'row': entry['row'],
                               'batches': [batch], 'triangles': triangles})
                continue
            for tri in entry['triangles']:
                for i in tri:
                    if i not in donor_indices:
                        donor_indices[i] = emit(dict(fitted_donor[i], **result['equipment_positions'][str(i)]))
            gear_batch = bytearray(batch)
            struct.pack_into('<H', gear_batch, 16, int(entry['texture'] == 2))
            meshes.append({'family': 'body', 'geoset': entry['geoset'], 'row': entry['row'],
                           'batches': [bytes(gear_batch)],
                           'triangles': [tuple(donor_indices[i] for i in tri) for tri in entry['triangles']]})
        cape_indices = [emit(vertex) for vertex in result['cape_vertices']]
        for original_cape, cape in zip(capes, result['capes'], strict=True):
            cape_batch = bytearray(batch)
            struct.pack_into('<H', cape_batch, 16, 1)
            cape_row = bytearray(original_cape['row'])
            points = np.array([result['cape_vertices'][i]['position'] for tri in cape['triangles'] for i in tri])
            center = (points.min(axis=0) + points.max(axis=0)) / 2
            radius = np.linalg.norm(points - center, axis=1).max()
            struct.pack_into('<3f3ff', cape_row, 20, *center, *center, radius)
            meshes.append({'family': 'body', 'geoset': cape['geoset'], 'row': bytes(cape_row),
                           'batches': [bytes(cape_batch)],
                           'triangles': [tuple(cape_indices[i] for i in tri) for tri in cape['triangles']]})
        model.vertices, model.vertex_count = bytes(vertices), len(vertices) // 48
        model.textures = [{'type': t, 'flags': 0, 'filename': ''} for t in (14, 2, 15)]
        model.replacable_texture_lookup = [65535] * 16
        model.replacable_texture_lookup[14], model.replacable_texture_lookup[2] = 0, 1
        model.replacable_texture_lookup[15] = 2
        model.texture_combos, model.texture_coord_combos = [0, 1, 2], [0]
        model.texture_weight_combos, model.texture_transform_combos = [0], [65535]
        model.materials = [{'flags': 0, 'blending_mode': 1}]
        idle = copy.deepcopy(next(s for s in parent.sequences if s['id'] == 0 and s['variation_index'] == 0))
        idle.update(flags=0x20, variation_next=-1, alias_next=0)
        model.sequences, model.sequence_lookups, model.global_loops = [idle], [0], []
        model.anim_file_ids, model.bone_file_ids, model.skin_file_ids, model.texture_file_ids = [], [], [], []
        model.attachments, model.attachment_lookup = [], []
        model.events, model.lights, model.cameras, model.ribbons, model.particles = [], [], [], [], []
        model.colors, model.texture_transforms, model.camera_lookup = [], [], []
        model.texture_weights = [{'weight': Track(kind='fixed16', timestamps=[[0]], values=[[32767]])}]
        for bone in model.bones:
            for key, kind in (('translation', 'vec3'), ('rotation', 'quat16'), ('scale', 'vec3')):
                bone[key] = Track(kind=kind)
        for mesh in meshes:
            row = bytearray(mesh['row'])
            struct.pack_into('<H', row, 16, 4)  # UV seam interpolation can add a fourth bone influence.
            points = np.array([struct.unpack_from('<3f', model.vertices, i * 48)
                               for tri in mesh['triangles'] for i in tri])
            center = (points.min(axis=0) + points.max(axis=0)) / 2
            radius = np.linalg.norm(points - center, axis=1).max()
            struct.pack_into('<3f3ff', row, 20, *center, *center, radius)
            mesh['row'] = bytes(row)
        output_skin = packed_skin(model, meshes)
        expanded, submeshes, lookups, local_bones = [], [], [], bytearray()
        for original_row in output_skin.submeshes:
            row = bytearray(original_row)
            first, count = struct.unpack_from('<2H', row, 8)
            first |= struct.unpack_from('<H', row, 2)[0] << 16
            used = output_skin.indices[first:first + count]
            unique = list(dict.fromkeys(used))
            remap = {value: len(lookups) + index for index, value in enumerate(unique)}
            palette_count, palette_start = struct.unpack_from('<2H', row, 12)
            palette = {bone: index for index, bone in enumerate(
                model.bone_combos[palette_start:palette_start + palette_count])}
            struct.pack_into('<2H', row, 4, len(lookups), len(unique))
            # Each section needs a private contiguous lookup window with its own local bone palette.
            for index in unique:
                vertex = output_skin.vertices[index]
                lookups.append(vertex)
                at = vertex * 48
                local_bones.extend(palette[model.vertices[at + 16 + slot]]
                                   if model.vertices[at + 12 + slot] else 0 for slot in range(4))
            start = len(expanded)
            struct.pack_into('<H', row, 2, start >> 16)
            struct.pack_into('<H', row, 8, start & 65535)
            expanded.extend(remap[index] for index in used)
            submeshes.append(bytes(row))
        output_skin.indices, output_skin.submeshes = expanded, submeshes
        output_skin.vertices, output_skin.bones = lookups, bytes(local_bones)
        model.num_skin_profiles = 1
        output, companion = write_md20(model), write_skin(output_skin)
        restored, restored_skin = parse_m2(output), parse_skin(companion)
        assert restored.vertex_count < 65536 and len(restored_skin.vertices) < 65536
        assert max(restored_skin.vertices) < restored.vertex_count
        assert max(restored_skin.indices) < len(restored_skin.vertices)
        assert sum(struct.unpack_from('<H', r, 10)[0] for r in restored_skin.submeshes) == len(restored_skin.indices)
        assert all(struct.unpack_from('<H', row, 12)[0] <= 75 for row in restored_skin.submeshes)
        for before, after in zip(skel.bones, restored.bones, strict=True):
            assert all(before[key] == after[key] for key in ('parent_bone', 'bone_name_crc', 'pivot'))
        assert hashlib.sha256(source.read_bytes()).hexdigest() == original
        destination = WORK / 'stage/assets/custom/centaur'
        destination.mkdir(parents=True, exist_ok=True)
        (destination / f'{identifier}-clothing.m2').write_bytes(output)
        (destination / f'{identifier}-clothing00.skin').write_bytes(companion)
        report['models'][str(sex)] = {'source': identifier, 'source_sha256': original,
            'vertices': restored.vertex_count, 'indices': len(restored_skin.indices), 'regions': result['regions'],
            'garment_geosets': sorted({e['geoset'] for e in [*equipment, *capes]} | {1805}),
            'rig_bones': len(restored.bones),
            'source_bones_preserved': True, 'model_sha256': hashlib.sha256(output).hexdigest(),
            'skin_sha256': hashlib.sha256(companion).hexdigest(),
            'remaining': ['posed garment clearance', 'helm and shoulder scale calibration', 'live equipment fit']}
    save(WORK / 'clothing-report.json', report)
    print('STAGED both Centaur clothing collections; visual acceptance remains pending', flush=True)


if __name__ == '__main__':
    if '--worker' in sys.argv:
        transfer(Path(sys.argv[sys.argv.index('--worker') + 1]))
    else:
        prepare()
