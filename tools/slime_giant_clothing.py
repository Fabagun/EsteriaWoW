"""Transfer authored Kul Tiran equipment UVs/geosets to the original SlimeSkeleton body.

Source inputs remain unchanged. An identical rig drives transparent layout-141 clothing in texture14,
with texture2 for the cape. Animation and socket transforms come from the original parent model.
"""

import argparse
from collections import Counter
import copy
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys

WORK = Path('G:/RetroportWork/slime-giant-175382')
BLENDER = Path('C:/Program Files/Blender Foundation/Blender 5.2/blender.exe')
MODEL, SKIN = 3490792, 3491636
NAKED = {0, 401, 501, 1301, 1801, 2001, 2201}


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8', newline='\n')


def blender_transfer(path):
    """Use the donor's triangle UVs, separating atlas components at transfer seams."""
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree
    from mathutils.geometry import barycentric_transform

    work = json.loads(path.read_text())
    donor, target, body = work['donor'], work['target'], work['donor_body']
    points = [Vector(v['position']) for v in donor]
    target_points = [Vector(v['position']) for v in target]
    donor_bvh = BVHTree.FromPolygons(points, body, all_triangles=True)
    target_bvh = BVHTree.FromPolygons(target_points, work['target_body'], all_triangles=True)

    def region(tri):
        u, v = [sum(donor[i]['uv'][axis] for i in tri) / 3 for axis in (0, 1)]
        if u < .25:
            return 0 if v < .25 else 1 if v < .5 else 2
        return 3 if v < .375 else 4 if v < .4375 else 5 if v < .6875 else 6 if v < .875 else 7

    by_region = {}
    for tri in body:
        by_region.setdefault(region(tri), []).append(tri)
    assert set(by_region) == set(range(8)), set(by_region)
    region_bvhs = {r: BVHTree.FromPolygons(points, tris, all_triangles=True) for r, tris in by_region.items()}

    def projected_uv(point, selected):
        hit, _, index, distance = region_bvhs[selected].find_nearest(Vector(point))
        tri = by_region[selected][index]
        uv = barycentric_transform(hit, *[points[i] for i in tri],
                                   *[Vector((*donor[i]['uv'], 0)) for i in tri])
        return [uv.x, uv.y], distance

    def nearest_region(point):
        _, _, index, _ = donor_bvh.find_nearest(Vector(point))
        return region(body[index])

    def midpoint(a, b):
        weights = {}
        for vertex in (a, b):
            for bone, weight in zip(vertex['bones'], vertex['weights']):
                if weight:
                    weights[bone] = weights.get(bone, 0) + weight / 2
        weights = sorted(weights.items(), key=lambda item: item[1], reverse=True)[:4]
        total = sum(weight for _, weight in weights)
        normalized = [round(weight / total * 255) for _, weight in weights]
        normalized[0] += 255 - sum(normalized)
        return {'position': [(a['position'][i] + b['position'][i]) / 2 for i in range(3)],
                'normal': list((Vector(a['normal']) + Vector(b['normal'])).normalized()),
                'bones': [bone for bone, _ in weights], 'weights': normalized,
                'inner_surface': a['inner_surface']}

    polygons, distances, coverage = [], [], Counter()

    def transfer(vertices, depth=0):
        center = [sum(v['position'][i] for v in vertices) / 3 for i in range(3)]
        selected = nearest_region(center)
        regions = [nearest_region(v['position']) for v in vertices]
        if depth < 1 and len(set(regions + [selected])) > 1:
            a, b, c = vertices
            ab, bc, ca = midpoint(a, b), midpoint(b, c), midpoint(c, a)
            for face in ((a, ab, ca), (ab, b, bc), (ca, bc, c), (ab, bc, ca)):
                transfer(face, depth + 1)
            return
        center_uv, _ = projected_uv(center, selected)
        # The opaque hands and wrists need coverage through the cuff; other regions duplicate the outer shell.
        if vertices[0]['inner_surface'] and selected not in (1, 2):
            return
        result = []
        for original in vertices:
            vertex = dict(original)
            uv, distance = projected_uv(vertex['position'], selected)
            # Prevent interpolation across the quarter-width mirrored arm/torso atlas seams.
            if abs(uv[0] - center_uv[0]) > .125:
                low, high = (0, .25) if selected < 3 else (.25, .5)
                uv[0] += .25 if uv[0] < center_uv[0] else -.25
                uv[0] = min(high, max(low, uv[0]))
            vertex['uv'] = uv
            result.append(vertex)
            distances.append(distance)
            coverage[selected] += 1
        polygons.append(result)

    for triangle in work['clothing_polygons']:
        transfer(triangle)

    # Transfer nearby body displacement, preserving the authored clearance/drape of loose garments.
    fitted, fit_distances = {}, []
    for index in work['equipment_vertices']:
        original = Vector(donor[index]['position'])
        anchor, _, _, _ = donor_bvh.find_nearest(original)
        destination, _, _, distance = target_bvh.find_nearest(anchor)
        fitted[str(index)] = list(original + destination - anchor)
        fit_distances.append(distance)
    sorted_distances = sorted(distances)
    save(path.with_name('transfer-result.json'), {
        'polygons': polygons, 'equipment_positions': fitted,
        'coverage_corners': dict(sorted(coverage.items())),
        'uv_projection_distance': {'median': sorted_distances[len(distances) // 2],
                                   'p95': sorted_distances[int(len(distances) * .95)],
                                   'max': max(distances)},
        'equipment_body_displacement_max': max(fit_distances),
    })
    print('Transferred authored Kul Tiran UVs:', len(polygons), 'body triangles;', len(fitted), 'gear vertices')


def remap_rig(donor, model):
    """Map CRCs then named ancestors; donor and source indices are never interchangeable."""
    by_crc = {bone['bone_name_crc']: i for i, bone in enumerate(model.bones) if bone['bone_name_crc']}
    mapping, fallback = {}, {}
    for index in range(len(donor.bones)):
        ancestor, seen = index, set()
        while ancestor >= 0 and ancestor not in seen:
            seen.add(ancestor)
            crc = donor.bones[ancestor]['bone_name_crc']
            if crc and crc in by_crc:
                mapping[index] = by_crc[crc]
                if ancestor != index:
                    fallback[index] = ancestor
                break
            ancestor = donor.bones[ancestor]['parent_bone']
        # Unnamed independent helper roots can be unused by the selected equipment surfaces.
    return mapping, fallback


def prepare(work, blender):
    import numpy as np
    from wotlkconv.m2 import parse_m2, parse_skin, write_md20
    from wotlkconv.m2.skel import parse_skel
    from wotlkconv.m2.skin import write_skin
    from wotlkconv.m2.types import Track
    from saberon_equipment_fit import clip, surface_normals
    from sethrak_equipment_repair import mesh_triangles, packed_skin, vertex_record

    paths = [work / 'correct-source' / f'{MODEL}.m2', work / 'correct-source' / f'{SKIN}.skin',
             work / 'source/1721003.m2', work / 'source/1721013.skin', work / 'source/2175552.skel']
    original = {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
    model = parse_m2(paths[0].read_bytes())
    skin = parse_skin(paths[1].read_bytes())
    donor = parse_m2(paths[2].read_bytes())
    donor_skin = parse_skin(paths[3].read_bytes())
    donor.bones = parse_skel(paths[4].read_bytes()).bones
    assert (model.vertex_count, len(model.bones), len(model.sequences), len(skin.submeshes)) == (7490, 208, 320, 4)
    assert len(donor.bones) == 197
    original_bones = copy.deepcopy(model.bones)
    mapping, fallback = remap_rig(donor, model)
    fitted_donor = []
    for index in range(max(donor_skin.vertices) + 1):
        vertex = vertex_record(donor, index)
        point = np.array(vertex['position'])
        for slot, weight in enumerate(vertex['weights']):
            if weight:
                bone = vertex['bones'][slot]
                if bone not in mapping:
                    continue
                target = mapping[bone]
                point += weight / 255 * (np.array(model.bones[target]['pivot']) - donor.bones[bone]['pivot'])
                vertex['bones'][slot] = target
        vertex['position'] = point.tolist()
        fitted_donor.append(vertex)

    source_body = [triangle for index in (1, 2) for triangle in mesh_triangles(skin, skin.submeshes[index])]
    normals = surface_normals(model, source_body)
    target = [vertex_record(model, i) for i in range(model.vertex_count)]
    for index, normal in normals.items():
        target[index]['normal'] = normal
    head = next(i for i, bone in enumerate(model.bones) if bone['key_bone_id'] == 6)
    neck = model.bones[head]['pivot'][2] - .035
    clothing_polygons = []
    for section in (1, 2):
        for triangle in mesh_triangles(skin, skin.submeshes[section]):
            polygon = clip([target[i] for i in triangle], lambda vertex: neck - vertex['position'][2])
            for at in range(1, len(polygon) - 1):
                clothing_polygons.append([dict(vertex, inner_surface=section == 2)
                                          for vertex in (polygon[0], polygon[at], polygon[at + 1])])
    donor_body, equipment, equipment_vertices = [], [], set()
    for index, row in enumerate(donor_skin.submeshes):
        geoset = struct.unpack_from('<H', row)[0]
        batches = [b for b in donor_skin.batches if struct.unpack_from('<H', b, 4)[0] == index]
        types = {donor.textures[donor.texture_combos[struct.unpack_from('<H', b, 16)[0]]]['type'] for b in batches}
        triangles = mesh_triangles(donor_skin, row)
        if geoset in NAKED:
            assert types == {1}
            donor_body.extend(triangles)
        if (400 <= geoset < 700 or 800 <= geoset < 1600 or 1800 <= geoset < 1900) and types in ({1}, {2}):
            equipment.append({'geoset': geoset, 'row': row, 'triangles': triangles, 'texture': next(iter(types))})
            equipment_vertices.update(i for tri in triangles for i in tri)
    derived = work / 'correct-fit'
    used_vertices = equipment_vertices | {i for triangle in donor_body for i in triangle}
    assert all(bone in mapping for i in used_vertices
               for bone, weight in zip(vertex_record(donor, i)['bones'], vertex_record(donor, i)['weights']) if weight)
    job = derived / 'transfer-work.json'
    save(job, {'donor': fitted_donor, 'donor_body': donor_body, 'target': target, 'target_body': source_body,
               'clothing_polygons': clothing_polygons, 'equipment_vertices': sorted(equipment_vertices)})
    subprocess.run([str(blender), '--background', '--factory-startup', '--python-exit-code', '1',
                    '--python', str(Path(__file__).resolve()),
                    '--', '--blender-worker', str(job)], check=True)
    transferred = json.loads(job.with_name('transfer-result.json').read_text())
    vertices, faces = bytearray(), []

    def emit(vertex, clearance=0):
        weights = list(vertex['weights']) + [0] * (4 - len(vertex['weights']))
        bones = [bone if weight else 0 for bone, weight in zip(vertex['bones'], vertex['weights'])]
        bones += [0] * (4 - len(bones))
        assert sum(weights) == 255 and all(0 <= bone < len(model.bones) for bone in bones)
        point = np.array(vertex['position']) + np.array(vertex['normal']) * clearance
        assert np.isfinite([*point, *vertex['uv'], *vertex['normal']]).all()
        at = len(vertices) // 48
        vertices.extend(struct.pack('<3f4B4B3f2f2f', *point, *weights, *bones,
                                    *vertex['normal'], *vertex['uv'], 0, 0))
        return at

    for polygon in transferred['polygons']:
        clearance = .004 if polygon[0]['inner_surface'] else -.006
        faces.append(tuple(emit(vertex, clearance) for vertex in polygon))
    batch = struct.pack('<12H', 0, 0, 0, 0, 65535, 0, 0, 1, 0, 0, 0, 0)
    meshes = [{'family': 'body', 'geoset': 1, 'row': skin.submeshes[1], 'batches': [batch], 'triangles': faces}]
    donor_indices = {}
    for entry in equipment:
        for triangle in entry['triangles']:
            for index in triangle:
                if index not in donor_indices:
                    vertex = dict(fitted_donor[index], position=transferred['equipment_positions'][str(index)])
                    donor_indices[index] = emit(vertex)
        gear_batch = bytearray(batch)
        struct.pack_into('<H', gear_batch, 16, int(entry['texture'] == 2))
        meshes.append({'family': 'body', 'geoset': entry['geoset'], 'row': entry['row'],
                       'batches': [bytes(gear_batch)],
                       'triangles': [tuple(donor_indices[i] for i in tri) for tri in entry['triangles']]})
    model.vertices, model.vertex_count = bytes(vertices), len(vertices) // 48
    model.textures = [{'type': 14, 'flags': 0, 'filename': ''}, {'type': 2, 'flags': 0, 'filename': ''}]
    model.replacable_texture_lookup = [65535] * 15
    model.replacable_texture_lookup[14], model.replacable_texture_lookup[2] = 0, 1
    model.texture_combos = [0, 1]
    model.texture_coord_combos = [0]
    model.texture_weight_combos = [0]
    model.texture_transform_combos = [65535]
    # Cutout armor writes depth before the translucent slime; blended collections sort over it.
    model.materials = [{'flags': 0, 'blending_mode': 1}]
    idle = copy.deepcopy(next(sequence for sequence in model.sequences
                              if sequence['id'] == 0 and sequence['variation_index'] == 0))
    idle.update(flags=(idle['flags'] & ~0x40) | 0x20, variation_next=-1, alias_next=0)
    # CreateModel starts idle before the parent-pose binding is ready; an empty sequence table crashes there.
    model.sequences, model.sequence_lookups, model.global_loops = [idle], [0], []
    model.anim_file_ids, model.bone_file_ids, model.skin_file_ids, model.texture_file_ids = [], [], [], []
    model.attachments, model.attachment_lookup = [], []
    model.events, model.lights, model.cameras, model.ribbons, model.particles = [], [], [], [], []
    model.colors, model.texture_transforms = [], []
    # Loose MD20 collections bypass CASC normalization; native alpha evaluation needs a real opacity track.
    model.texture_weights = [{'weight': Track(kind='fixed16', timestamps=[[0]], values=[[32767]])}]
    model.camera_lookup = []
    for bone in model.bones:
        for key, kind in (('translation', 'vec3'), ('rotation', 'quat16'), ('scale', 'vec3')):
            bone[key] = Track(kind=kind)
    # All 61 used bones fit one native palette; shared triangle windows must use the same bone map.
    for mesh in meshes:
        mesh['family'] = 'armor'
        row = bytearray(mesh['row'])
        struct.pack_into('<H', row, 16, 4)
        mesh['row'] = bytes(row)
    output_skin = packed_skin(model, meshes)
    # SetIndices copies every section sequentially; shared input ranges would overrun its GPU allocation.
    expanded = []
    rows = []
    for source_row in output_skin.submeshes:
        row = bytearray(source_row)
        first = struct.unpack_from('<H', row, 8)[0] | (struct.unpack_from('<H', row, 2)[0] << 16)
        count = struct.unpack_from('<H', row, 10)[0]
        assert first + count <= len(output_skin.indices)
        start = len(expanded)
        struct.pack_into('<H', row, 2, start >> 16)
        struct.pack_into('<H', row, 8, start & 65535)
        expanded.extend(output_skin.indices[first:first + count])
        rows.append(bytes(row))
    output_skin.indices = expanded
    output_skin.submeshes = rows
    model.num_skin_profiles = 1
    output, encoded_skin = write_md20(model), write_skin(output_skin)
    restored, restored_skin = parse_m2(output), parse_skin(encoded_skin)
    assert restored.vertex_count < 65536 and len(restored_skin.indices) < 65536
    assert len(restored_skin.vertices) < 65536 and max(restored_skin.vertices) < restored.vertex_count
    assert restored_skin.indices and max(restored_skin.indices) < len(restored_skin.vertices)
    assert sum(struct.unpack_from('<H', row, 10)[0] for row in restored_skin.submeshes) == \
        len(restored_skin.indices), 'Native sequential index upload must fit the allocated index count'
    assert restored.num_skin_profiles == 1 and len(restored.bones) == 208
    assert len(restored.sequences) == 1 and restored.sequences[0]['id'] == 0
    assert restored.sequence_lookups == [0], 'Native CreateModel must find an idle before parent-pose binding'
    assert all(index < len(restored.texture_weights) for index in restored.texture_weight_combos)
    assert restored.texture_weights[0]['weight'].values == [[32767]], 'Native batch alpha must have a real opaque key'
    assert restored.materials == [{'flags': 0, 'blending_mode': 1}]
    assert not restored.texture_transforms, 'Equipment must not inherit the animated slime UV transform'
    for before, after in zip(original_bones, restored.bones, strict=True):
        for key in ('key_bone_id', 'flags', 'parent_bone', 'submesh_id', 'bone_name_crc', 'pivot'):
            if key in before:
                assert before[key] == after[key], (key, before[key], after[key])
    assert all(struct.unpack_from('<H', row, 12)[0] <= 75 for row in restored_skin.submeshes)
    assert set(transferred['coverage_corners']) == {str(i) for i in range(8)}
    assert {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths} == original
    destination = work / 'stage/assets/custom/slimegiant'
    baseline = work / 'armor-layering-v2/baseline'
    baseline.mkdir(parents=True, exist_ok=True)
    (baseline / f'{MODEL}-clothing.m2').write_bytes(output)
    (baseline / f'{MODEL}-clothing00.skin').write_bytes(encoded_skin)
    report = {'status': 'correct-model-authored-kul-tiran-uv-and-equipment-staged',
              'source_model': MODEL, 'source_skin': SKIN, 'source_sha256': original,
              'vertices': restored.vertex_count, 'skin_vertices': len(restored_skin.vertices),
              'indices': len(restored_skin.indices), 'triangles': len(restored_skin.indices) // 3,
              'body_clothing_triangles': len(faces), 'bone_count': len(restored.bones),
              'bone_crc_exact_matches': len(mapping) - len(fallback), 'bone_ancestry_fallback': fallback,
              'equipment_geosets': [entry['geoset'] for entry in equipment],
              'equipment_triangles': sum(len(entry['triangles']) for entry in equipment),
              'uv_layout': 'original Kul Tiran HD; native layout 141, type14; cape type2',
              'body_surface_policy': 'single outer shell; opaque inner shell only for hands and wrists',
              'armor_material': 'alpha cutout with depth writes; no animated slime UV transform',
              'uv_projection_distance': transferred['uv_projection_distance'],
              'region_coverage_corners': transferred['coverage_corners'],
              'equipment_body_displacement_max': transferred['equipment_body_displacement_max'],
              'model_sha256': hashlib.sha256(output).hexdigest(),
              'skin_sha256': hashlib.sha256(encoded_skin).hexdigest(), 'live_acceptance': False}
    from slime_giant_armor_fit import fit_assets
    clearance = fit_assets(work, baseline, destination)
    report.update(model_sha256=clearance['model_sha256'], skin_sha256=clearance['skin_sha256'],
                  vertices=report['vertices'] + clearance['split_shared_belt_vertices'],
                  skin_vertices=report['skin_vertices'] + clearance['split_shared_belt_vertices'],
                  armor_clearance_report=str(work / 'armor-layering-v2/fit-report.json'))
    save(derived / 'clothing-report.json', report)
    save(work / 'clothing-report.json', {str(MODEL): report})
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    if '--blender-worker' in sys.argv:
        blender_transfer(Path(sys.argv[sys.argv.index('--blender-worker') + 1]))
    else:
        parser = argparse.ArgumentParser(description=__doc__)
        parser.add_argument('--work', type=Path, default=WORK)
        parser.add_argument('--blender', type=Path, default=BLENDER)
        args = parser.parse_args()
        prepare(args.work, args.blender)
