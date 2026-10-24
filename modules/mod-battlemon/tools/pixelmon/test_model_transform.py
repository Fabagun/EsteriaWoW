"""Source transforms preserve geometry, normals, and all animated poses together."""
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from batch import fingerprint
from m2 import prepare, build_model
from model_transform import source_matrix
from validate import read_model


class ModelTransformTests(unittest.TestCase):
    def test_source_defaults_rotation_order_units_and_offsets(self):
        np.testing.assert_allclose(source_matrix({}), np.eye(4), atol=1e-7)
        matrix = source_matrix(dict(scale=2, offsets=[1, 2, 3]))
        np.testing.assert_allclose(matrix[:3, :3], np.eye(3)*2, atol=1e-7)
        np.testing.assert_allclose(matrix[:3, 3], [1, -3, 2], atol=1e-7)
        matrix = source_matrix(dict(rotate_angle=[-math.pi/2, math.pi/2, 0]))
        np.testing.assert_allclose(matrix @ [1, 0, 0, 1], [0, 1, 0, 1], atol=1e-7)
        # Explicit zero REPLACES the source's default -90 degree X rotation.
        matrix = source_matrix(dict(rotate_angle=[0, 0, 0]))
        np.testing.assert_allclose(matrix @ [0, 1, 0, 1], [0, 0, 1, 1], atol=1e-7)
        matrix = source_matrix(dict(rotate_angle=[0, math.pi/2, math.pi/2]))
        np.testing.assert_allclose(matrix @ [1, 0, 0, 1], [0, 0, 1, 1], atol=1e-7)

    def test_invalid_and_nonrigid_transforms_are_rejected(self):
        for definition in [dict(scale=[1, 2, 1]), dict(scale=-1), dict(scale=0),
                           dict(offsets=[0, float('nan'), 0]), dict(rotate_angle=[0, 0])]:
            with self.assertRaises(ValueError):
                source_matrix(definition)

    def test_decoded_pose_and_normals_follow_same_transform(self):
        source = dict(bones=[('root', -1)], frames=np.zeros((1, 1, 6)),
                      vertices=np.array([[0., 0., 0., 1., 0., 0., 0., 0.],
                                         [1., 0., 1., 1., 0., 0., 1., 0.],
                                         [0., 1., 0., 1., 0., 0., 0., 1.]]),
                      weights=[[(0, 1.)]]*3, faces=[('body', [0, 1, 2])])
        animation = dict(bones=[('root', -1)], frames=np.zeros((2, 1, 6)))
        animation['frames'][1, 0, 0] = 1
        matrix = source_matrix(dict(scale=2, offsets=[1, 2, 3],
                                    rotate_angle=[-math.pi/2, math.pi/2, 0]))
        with patch('m2.read_bmd', side_effect=[source, animation, animation]):
            mesh = prepare(Path('source'), dict(idle=Path('idle'), walk=Path('walk')),
                           source_transform=matrix)
        np.testing.assert_allclose(mesh['vertices'][:, 3:6], [[-1, 0, 0]]*3, atol=1e-7)
        expected = [[1.5, .5, 0], [.5, .5, 1], [1.5, -.5, 0]]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'transformed.m2'
            model, skin = build_model(mesh, 'transformed', 'transformed.blp')
            path.write_bytes(model)
            path.with_name('transformed00.skin').write_bytes(skin)
            decoded = read_model(path)
            for poses in decoded['poses']:
                np.testing.assert_allclose(poses[0], expected, atol=1e-6)
                np.testing.assert_allclose(poses[1]-poses[0], [[-1, 0, 0]]*3, atol=1e-6)
            self.assertAlmostEqual(float(decoded['poses'][0][0, :, 2].min()), 0)
            self.assertAlmostEqual(float(decoded['poses'][0][0, :, 2].max()), 1)

    def test_transform_change_invalidates_geometry_cache(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'source'
            path.write_bytes(b'input')
            appearance = dict(model=str(path), texture=str(path), animations={}, fps=30)
            before = fingerprint(appearance, 'revision', texture=False)
            appearance['source_transform'] = source_matrix(dict(offsets=[1, 0, 0])).tolist()
            self.assertNotEqual(before, fingerprint(appearance, 'revision', texture=False))


if __name__ == '__main__':
    unittest.main()
