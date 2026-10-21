"""Check belts against the actual pants boundary and mirrored cape UVs in source poses."""

from collections import Counter
import json
import struct

import numpy as np
from wotlkconv.m2 import parse_m2, parse_skin
from wotlkconv.m2.skel import parse_skel

import centaur_deploy as deploy
import creature_animation_repair as motion
import test_centaur_v6 as geometry
import test_centaur_v7 as previous

WORK = deploy.WORK / 'repair-v8'


def main():
    previous.main(WORK)
    report = {}
    for sex, identifier in enumerate((4036647, 4081379)):
        root = deploy.pack.STAGE / 'assets/custom/centaur'
        model = parse_m2((root / f'{identifier}-clothing.m2').read_bytes())
        skin = parse_skin((root / f'{identifier}-clothing00.skin').read_bytes())
        polygons = json.loads((deploy.WORK / 'clothing' / str(sex) / 'transfer-result.json').read_text())['polygons']
        edges, vertices = Counter(), {}
        for polygon in polygons:
            if polygon[0]['part'] != 'leg':
                continue
            keys = [tuple(round(c, 5) for c in v['position']) for v in polygon]
            vertices.update(zip(keys, polygon))
            edges.update(tuple(sorted((a, b))) for a, b in zip(keys, keys[1:] + keys[:1]) if a != b)
        boundary = [edge for edge, count in edges.items() if count == 1 and min(v[2] for v in edge) > 1]
        belt = geometry.points(model, skin, 1805)
        top = [r for r in belt.values() if abs(struct.unpack_from('<f', r, 36)[0] - (.375 + 1 / 1024)) < 1e-6]
        raw_top = np.array([np.array(struct.unpack_from('<3f', r)) -
                            np.array(struct.unpack_from('<3f', r, 20)) * .018 for r in top])
        assert len(top) > 64
        pairs = []
        for key in {v for edge in boundary for v in edge}:
            vertex = vertices[key]
            index = np.linalg.norm(raw_top - vertex['position'], axis=1).argmin()
            assert np.linalg.norm(raw_top[index] - vertex['position']) < 1e-5, 'Belt misses a pants boundary corner'
            actual = top[index]
            expected_weights = {b: w for b, w in zip(vertex['bones'], vertex['weights']) if w}
            assert {b: w for b, w in zip(actual[16:20], actual[12:16]) if w} == expected_weights
            pairs.append((vertex, actual))
        starts = np.array([vertices[a]['position'] for a, _ in boundary])
        directions = np.array([vertices[b]['position'] for _, b in boundary]) - starts
        edge_samples = []
        for point, actual in zip(raw_top, top):
            delta = point - starts
            t = np.clip(np.sum(delta * directions, axis=1) / np.sum(directions ** 2, axis=1), 0, 1)
            distances = np.linalg.norm(delta - directions * t[:, None], axis=1)
            index = distances.argmin()
            assert distances[index] < 1e-5
            a, b = boundary[index]
            edge_samples.append((vertices[a], vertices[b], t[index], actual))
        cape = list(geometry.points(model, skin, 1502).values())
        cape.sort(key=lambda r: (struct.unpack_from('<f', r, 36)[0], struct.unpack_from('<f', r, 4)[0]))
        for row in range(25):
            left, center, right = [np.array(struct.unpack_from('<3f', cape[row * 17 + col]))
                                   for col in (0, 8, 16)]
            assert abs(center[1]) < .002
            assert abs(np.linalg.norm(left - center) - np.linalg.norm(right - center)) < .002
            for col in range(17):
                record = cape[row * 17 + col]
                u, v = struct.unpack_from('<2f', record, 32)
                assert abs(u - (.992 - .7426 * abs(2 * col / 16 - 1))) < 1e-6
                assert abs(v - (.004 + .989 * row / 24)) < 1e-6
        skeleton = parse_skel((deploy.WORK / 'source' / ('4226281.skel' if sex else '4224620.skel')).read_bytes())
        rig = parse_m2((deploy.WORK / 'source' / f'{identifier}.m2').read_bytes())
        rig.bones, rig.sequences, rig.global_loops = skeleton.bones, skeleton.sequences, skeleton.global_loops
        poses, maximum_gap, maximum_edge_gap = 0, 0, 0
        for action in (0, 4, 5):
            duration = rig.sequences[motion.sequence(rig, action)]['duration']
            for phase in (0, .25, .5, .75):
                matrices = motion.pose_matrices(rig, action, round(duration * phase))
                for vertex, actual in pairs:
                    expected = sum((matrices[b] @ np.array([*vertex['position'], 1]))[:3] * w / 255
                                   for b, w in zip(vertex['bones'], vertex['weights']) if w)
                    normal = sum(matrices[b][:3, :3] @ np.array(vertex['normal']) * w / 255
                                 for b, w in zip(vertex['bones'], vertex['weights']) if w)
                    gap = np.linalg.norm(geometry.pose_point(actual, matrices) - expected - normal * .018)
                    maximum_gap = max(maximum_gap, float(gap))
                for a, b, t, actual in edge_samples:
                    def posed(vertex):
                        return sum((matrices[bone] @ np.array([*vertex['position'], 1]))[:3] * w / 255
                                   for bone, w in zip(vertex['bones'], vertex['weights']) if w)
                    expected = posed(a) * (1 - t) + posed(b) * t
                    normal = np.array(struct.unpack_from('<3f', actual, 20))
                    normal = sum(matrices[bone][:3, :3] @ normal * w / 255
                                 for bone, w in zip(actual[16:20], actual[12:16]) if w)
                    gap = np.linalg.norm(geometry.pose_point(actual, matrices) - normal * .018 - expected)
                    if gap > maximum_edge_gap:
                        maximum_edge_gap = float(gap)
                        worst_edge = (action, phase, a['position'], b['position'], float(t))
                # Walk/run move the source flanks asymmetrically; idle checks the visible centered drape.
                if action == 0:
                    for row in range(25):
                        left, center, right = [geometry.pose_point(cape[row * 17 + col], matrices)
                                               for col in (0, 8, 16)]
                        assert abs(np.linalg.norm(left - center) - np.linalg.norm(right - center)) < .03
                poses += 1
        assert maximum_gap < 1e-5, 'Belt boundary weights drift from pants in motion'
        assert maximum_edge_gap < .01, f'Subdivided belt edge drifts: {maximum_edge_gap}, {worst_edge}'
        report[str(identifier)] = {'exact_pants_boundary_corners': len(pairs), 'boundary_vertices': len(top),
            'posed_boundary_max_error': maximum_gap, 'posed_edge_max_error': maximum_edge_gap,
            'poses': poses, 'mirrored_half_cape_atlas': True}
    deploy.pack.json_save(WORK / 'boundary-validation.json', report)
    print('PASS exact pants socket boundaries and mirrored cape panels in 24 source poses')


if __name__ == '__main__':
    main()
