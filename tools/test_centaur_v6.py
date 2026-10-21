"""Check Centaur anatomical UV regions, restored fingers and shared-pose arm coverage."""

from collections import defaultdict
import json
from pathlib import Path
import struct

import numpy as np
from wotlkconv.m2 import parse_m2, parse_skin
from wotlkconv.m2.skel import parse_skel

import centaur_deploy as deploy
import creature_animation_repair as motion
from sethrak_equipment_repair import mesh_triangles

WORK = deploy.WORK / 'repair-v6'


def points(model, skin, geoset):
    return {i: model.vertices[i * 48:(i + 1) * 48] for row in skin.submeshes
            if struct.unpack_from('<H', row)[0] == geoset for tri in mesh_triangles(skin, row) for i in tri}


def pose_point(record, matrices):
    position = np.array([*struct.unpack_from('<3f', record), 1])
    return sum((matrices[bone] @ position)[:3] * weight / 255
               for bone, weight in zip(record[16:20], record[12:16]) if weight)


def main(output_root=None):
    output_root = output_root or WORK
    import test_centaur_refine
    test_centaur_refine.main()
    reports = {}
    for sex, identifier in enumerate((4036647, 4081379)):
        root = deploy.pack.STAGE / 'assets/custom/centaur'
        model = parse_m2((root / f'{identifier}-clothing.m2').read_bytes())
        skin = parse_skin((root / f'{identifier}-clothing00.skin').read_bytes())
        report = json.loads((deploy.WORK / 'clothing' / str(sex) / 'transfer-result.json').read_text())
        for polygon in report['polygons']:
            region, part = polygon[0]['region'], polygon[0]['part']
            assert all(v['region'] == region and v['part'] == part for v in polygon)
            if region in (5, 6):
                assert part == 'leg', 'Pants cannot wrap hands, claws or the horse torso'
            if part == 'arm':
                assert region in (0, 1, 2), 'Arm/claw geometry cannot sample torso or pants textures'
            for vertex in polygon:
                u, v = vertex['uv']
                assert 0 < u < .25 if part == 'arm' else .25 <= u <= .5
                if region == 2:
                    assert .5 < v < 1
        hand = [v for p in report['polygons'] for v in p if v['region'] == 2]
        assert min(v['position'][2] for v in hand) < 1.71, 'Gloves must reach the original finger/claw tips'
        assert {v['position'][1] > 0 for v in hand} == {False, True}
        torso = [v for p in report['polygons'] for v in p if v['part'] == 'torso']
        assert max(v['position'][2] for v in torso) > 2.77, 'Collar must reach the original neck base'
        for vertex in torso:
            expected = max(1 / 8192, min(.375 - 1 / 8192, (2.79 - vertex['position'][2]) / .97 * .375))
            assert abs(vertex['uv'][1] - expected) < 1e-6, 'Torso UV must be continuous through the chest split'
        geosets = {struct.unpack_from('<H', row)[0] for row in skin.submeshes}
        assert 401 not in geosets, 'Naked donor cuff duplicates the fitted arm'
        base_by_tail = defaultdict(list)
        for record in points(model, skin, 1).values():
            base_by_tail[record[12:]].append(record)
        pairs = []
        for geoset in (402, 403, 404, 802, 803):
            for record in points(model, skin, geoset).values():
                normal = np.array(struct.unpack_from('<3f', record, 20))
                p = np.array(struct.unpack_from('<3f', record))
                candidates = base_by_tail[record[12:]]
                assert candidates, 'Cuffs must use the exact body UVs, normals and skin weights'
                base = min(candidates, key=lambda b: np.linalg.norm(
                    p - np.array(struct.unpack_from('<3f', b)) - normal * .018))
                assert np.linalg.norm(p - np.array(struct.unpack_from('<3f', base)) - normal * .018) < 1e-5
                pairs.append((base, record))
        skeleton = parse_skel((deploy.WORK / 'source' / ('4226281.skel' if sex else '4224620.skel')).read_bytes())
        body = parse_m2((deploy.WORK / 'source' / f'{identifier}.m2').read_bytes())
        if sex:
            original_skin = parse_skin((deploy.WORK / 'source/4081384.skin').read_bytes())
            covered = {(*np.round(np.array(struct.unpack_from('<3f', r)) -
                        np.array(struct.unpack_from('<3f', r, 20)) * .006, 4), r[12:20])
                       for r in points(model, skin, 1).values()}
            for row in original_skin.submeshes:
                if struct.unpack_from('<H', row)[0] != 201:
                    continue
                for index in {i for tri in mesh_triangles(original_skin, row) for i in tri}:
                    at = index * 48
                    record = body.vertices[at:at + 48]
                    position = np.array(struct.unpack_from('<3f', record))
                    assert (*np.round(position, 4), record[12:20]) in covered, \
                        'Female breast/bra anatomy must have a complete armor overlay'
        body.bones, body.sequences, body.global_loops = skeleton.bones, skeleton.sequences, skeleton.global_loops
        minimum = 100
        for action in (0, 4, 5):
            index = motion.sequence(body, action)
            assert body.sequences[index]['flags'] & 0x20
            for phase in (0, .25, .5, .75):
                matrices = motion.pose_matrices(body, action, round(body.sequences[index]['duration'] * phase))
                for base, cuff in pairs:
                    delta = pose_point(cuff, matrices) - pose_point(base, matrices)
                    normal = np.array(struct.unpack_from('<3f', base, 20))
                    posed_normal = sum(matrices[b][:3, :3] @ normal * w / 255
                                       for b, w in zip(base[16:20], base[12:16]) if w)
                    assert np.dot(delta, posed_normal) > 0, 'Cuff crossed its body overlay in an authored pose'
                    minimum = min(minimum, np.linalg.norm(delta))
        assert minimum > .005, 'Cuff clearance collapsed in an authored pose'
        reports[str(identifier)] = {'anatomical_regions_passed': True, 'full_finger_coverage': True,
            'continuous_torso_uv': True, 'cuff_vertex_pairs': len(pairs), 'poses': 12,
            'minimum_cuff_overlay_separation': float(minimum)}
    deploy.pack.json_save(output_root / 'geometry-validation.json', reports)
    print('PASS anatomical UVs, complete gloves, continuous chest mapping and cuff separation in 24 source poses')


if __name__ == '__main__':
    main()
