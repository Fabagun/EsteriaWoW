"""Source-motion policies must preserve bind geometry without hiding broken animation."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from catalog import select_animations, Unsupported
from m2 import prepare, build_model
from test_skin_sections import fixture
from validate import read_model


class SourceMotionTests(unittest.TestCase):
    def test_first_declared_animation_and_only_empty_lists_are_static(self):
        entries = [dict(type='idle', animation='first'), dict(type='walk', animation='walk'),
                   dict(type='idle', animation='second')]
        self.assertEqual(select_animations(dict(animations=entries)),
                         ({'idle': 'first', 'walk': 'walk'}, True))
        self.assertEqual(select_animations({}), ({}, False))
        self.assertEqual(select_animations(dict(animations=[])), ({}, False))
        with self.assertRaisesRegex(Unsupported, 'missing_idle'):
            select_animations(dict(animations=[dict(type='walk', animation='walk')]))

    def test_static_source_preserves_all_geometry_and_nontrivial_bind_pose(self):
        source = dict(bones=[('root', -1), ('child', 0)],
                      frames=np.array([[[2., 3., 4., .1, .2, .3], [1., 0., 0., 0., .3, 0.]]]),
                      vertices=np.array([[0., 0., 0., 0., 0., 1., 0., 0.],
                                         [1., 0., 1., 0., 0., 1., 1., 0.],
                                         [0., 1., 0., 0., 0., 1., 0., 1.]]),
                      weights=[[(0, .6), (1, .4)]]*3, faces=[('body', [0, 1, 2])])
        with patch('m2.read_bmd', return_value=source):
            mesh = prepare(Path('source.bmd'), {}, static_bind_pose=True)
            with self.assertRaisesRegex(ValueError, 'cannot discard'):
                prepare(Path('source.bmd'), {'idle': Path('idle.bmd')}, static_bind_pose=True)
        with tempfile.TemporaryDirectory() as directory:
            model, skin = build_model(mesh, 'static', 'static.blp')
            path = Path(directory)/'static.m2'
            path.write_bytes(model)
            path.with_name('static00.skin').write_bytes(skin)
            # The usual animation gate is still strict.
            with self.assertRaisesRegex(ValueError, 'Walk sequence is static'):
                read_model(path)
            decoded = read_model(path, source_motion='static_bind_pose')
            expected = source['vertices'][:, [1, 0, 2]].copy()
            expected[:, 0] *= -1
            for poses in decoded['poses']:
                for pose in poses:
                    np.testing.assert_allclose(pose[decoded['triangles'].ravel()], expected, atol=1e-6)
            self.assertEqual(len(decoded['triangles']), 1)
            with self.assertRaisesRegex(ValueError, 'Unknown source motion'):
                read_model(path, source_motion='anything')

    def test_named_local_channels_use_model_parents_and_missing_bones_inherit_motion(self):
        source = dict(bones=[('root', -1), ('child', 0), ('missing', 0)],
                      frames=np.array([[[2., 0., 0., 0., 0., 0.],
                                        [0., 0., 1., 0., 0., 0.],
                                        [0., 1., 0., 0., 0., 0.]]]),
                      vertices=np.array([[2., 0., 1., 0., 0., 1., 0., 0.],
                                         [3., 0., 0., 0., 0., 1., 1., 0.],
                                         [2., 1., 0., 0., 0., 1., 0., 1.]]),
                      weights=[[(1, 1.)], [(0, 1.)], [(2, 1.)]], faces=[('body', [0, 1, 2])])
        animation = dict(bones=[('root', -1), ('child', -1)],
                         frames=np.array([[[2., 0., 0., 0., 0., 0.], [0., 0., 1., 0., 0., 0.]],
                                          [[3., 0., 0., 0., 0., 0.], [0., 0., 1., 0., 0., 0.]]]))
        with patch('m2.read_bmd', side_effect=[source, animation, animation]):
            mesh = prepare(Path('source'), dict(idle=Path('idle'), walk=Path('walk')))
        self.assertIn('walk:model_parent_used:child', mesh['binding_notes'])
        self.assertIn('walk:bind_local_fallback:missing', mesh['binding_notes'])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'bound.m2'
            model, skin = build_model(mesh, 'bound', 'bound.blp')
            path.write_bytes(model)
            path.with_name('bound00.skin').write_bytes(skin)
            decoded = read_model(path)
            # Root +1 source X must move ALL vertices +1 WoW Y, including the
            # weighted bone absent from the animation and the reparented channel.
            for poses in decoded['poses']:
                np.testing.assert_allclose(poses[1]-poses[0], [[0., 1., 0.]]*3, atol=1e-6)

    def test_static_policy_rejects_moving_or_displaced_geometry(self):
        for displaced in [False, True]:
            mesh = fixture()
            if displaced:
                for sequence in mesh['sequences']:
                    sequence['translations'][:] = [.1, 0, 0]
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory)/'invalid.m2'
                model, skin = build_model(mesh, 'invalid', 'invalid.blp')
                path.write_bytes(model)
                path.with_name('invalid00.skin').write_bytes(skin)
                with self.assertRaisesRegex(ValueError, 'does not preserve the bind pose'):
                    read_model(path, source_motion='static_bind_pose')


if __name__ == '__main__':
    unittest.main()
