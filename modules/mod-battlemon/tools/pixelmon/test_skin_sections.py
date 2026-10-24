"""Regression coverage for D3D9 bone uploads and per-section skin indirection."""
from pathlib import Path
import struct
import tempfile
import unittest

import numpy as np

from m2 import build_model
from skin_sections import partition
from validate import read_model


def fixture():
    vertices, weights, triangles = [], [], []
    # Shared vertices cross the 64-bone boundary, so the exporter must duplicate them per section.
    for bone in range(80):
        for x, y in [(0, 0), (.01, 0), (0, .01)]:
            vertices.append([bone*.01+x, y, .3, 0, 0, 1, .5, .5])
            weights.append([(bone, .8), (0, .2)])
        triangles.extend([bone*3, bone*3+1, bone*3+2])
    triangles.extend([0, 237, 239])
    bounds = (np.array([-1., -1., -1.]), np.array([2., 2., 2.]))
    sequences = []
    for index in [0, 4, 5]:
        translations = np.zeros((3, 80, 3))
        translations[1, :, 0] = np.arange(80)*.001
        rotations = np.zeros((3, 80, 4))
        rotations[:, :, 3] = 1
        sequences.append(dict(id=index, duration=200, speed=0 if index==0 else 2.5,
                              times=np.array([0, 100, 200]), translations=translations,
                              rotations=rotations, bounds=bounds))
    return dict(vertices=np.array(vertices), weights=weights, triangles=triangles,
                bones=[(str(i), -1) for i in range(80)], sequences=sequences, bounds=bounds)


class SkinPartitionTests(unittest.TestCase):
    def test_preserves_triangles_uv_and_weighted_poses_across_sections(self):
        mesh = fixture()
        layout = partition(mesh)
        self.assertGreater(len(layout['sections']), 1)
        self.assertTrue(all(s['bone_count'] <= 64 for s in layout['sections']))
        np.testing.assert_array_equal(layout['vertices'][layout['triangles']], mesh['vertices'][mesh['triangles']])
        self.assertGreater(len(layout['vertices']), len(mesh['vertices']))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'test.m2'
            model, skin = build_model(mesh, 'test', 'test.blp')
            path.write_bytes(model)
            path.with_name('test00.skin').write_bytes(skin)
            decoded = read_model(path)
            for frame in range(3):
                expected = mesh['vertices'][:, :3].copy()
                for i, links in enumerate(mesh['weights']):
                    for bone, weight in links:
                        expected[i] += mesh['sequences'][0]['translations'][frame, bone]*weight
                np.testing.assert_allclose(decoded['poses'][0][frame][decoded['triangles'].ravel()],
                                           expected[mesh['triangles']], atol=1e-6)
            self.assertEqual(struct.unpack_from('<I', skin, 44)[0], 64)

    def test_rejects_unsafe_tier_oversized_palette_and_wrong_local_indices(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'test.m2'
            model, original = build_model(fixture(), 'test', 'test.blp')
            path.write_bytes(model)
            skin_path = path.with_name('test00.skin')
            for kind in ['tier', 'count', 'mapping']:
                skin = bytearray(original)
                if kind == 'tier':
                    struct.pack_into('<I', skin, 44, 256)
                elif kind == 'count':
                    section = struct.unpack_from('<I', skin, 32)[0]
                    struct.pack_into('<H', skin, section+12, 79)
                else:
                    properties = struct.unpack_from('<I', skin, 24)[0]
                    skin[properties] = 63
                skin_path.write_bytes(skin)
                with self.assertRaises(ValueError, msg=kind):
                    read_model(path)


if __name__ == '__main__':
    unittest.main()
