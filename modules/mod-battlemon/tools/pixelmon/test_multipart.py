"""Verify multipart geometry, animated placement, texture identity and cache dependencies."""
import copy
from pathlib import Path
import tempfile
import unittest

import numpy as np
from PIL import Image

from batch import fingerprint
from m2 import build_model
from multipart import compose, make_atlas
from validate import read_model, rotation_matrix


def mesh(z, movement):
    vertices = np.array([[0., 0., z, 0, 0, 1, 0, 0], [1., 0., z, 0, 0, 1, 1, 0],
                         [0., 0., z+1, 0, 0, 1, 0, 1]])
    sequences = []
    for sid in [0, 4, 5]:
        t = np.zeros((3, 3, 3)); t[1, 2, 0] = movement
        q = np.zeros((3, 3, 4)); q[..., 3] = 1
        q[1, 2] = [0, np.sin(.4), 0, np.cos(.4)]
        sequences.append(dict(id=sid, name='test', duration=200, speed=0 if sid==0 else 2.5,
                              times=np.array([0, 100, 200]), translations=t, rotations=q,
                              bounds=(np.array([-20., -20., -20.]), np.array([20., 20., 20.]))))
    return dict(vertices=vertices, weights=[[(2, 1.)]]*3, triangles=[0, 1, 2],
                bones=[('unused', -1), ('control', -1), ('shared-name', -1)],
                sequences=sequences, bounds=sequences[0]['bounds'],
                standing_bounds=[vertices[:, :3].min(axis=0), vertices[:, :3].max(axis=0)],
                skinning_error=0., max_dropped_weight=0.)


class MultipartTests(unittest.TestCase):
    def test_independent_rigs_keep_all_parts_and_every_animated_position(self):
        parts = [mesh(2, .6), mesh(4, 1.2)]
        merged = compose(parts, ['red.png', 'blue.png'])
        self.assertEqual(len(merged['bones']), 2)  # Same bone names are distinct binds; unused bones are removed.
        self.assertEqual(len(merged['triangles']), 6)
        np.testing.assert_allclose(merged['vertices'][[0, 3], 2], [0, 2/3])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'test.m2'
            m2, skin = build_model(merged, 'test', 'test.blp')
            path.write_bytes(m2); path.with_name('test00.skin').write_bytes(skin)
            decoded = read_model(path)
            for sequence in range(3):
                for frame in range(3):
                    expected = []
                    for part in parts:
                        s = part['sequences'][sequence]
                        posed = part['vertices'][:, :3] @ rotation_matrix(s['rotations'][frame, 2]).T
                        posed += s['translations'][frame, 2]
                        expected.extend(posed/3+np.array([0, 0, -2/3]))
                    np.testing.assert_allclose(decoded['poses'][sequence][frame][decoded['triangles'].ravel()],
                                               expected, atol=1e-4)

    def test_atlas_keeps_texture_assignment_and_clamped_borders(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); paths = [root/'red.png', root/'blue.png']
            for p, color in zip(paths, [(255, 0, 0, 255), (0, 0, 255, 255)]):
                Image.new('RGBA', (32, 24), color).save(p)
            combined = compose([mesh(2, .1), mesh(4, .2)], paths)
            atlas = Image.open(make_atlas(paths, root/'atlas.png'))
            for i, uv in enumerate(combined['vertices'][:, 6:8]):
                xy = np.floor(uv*np.array(atlas.size)).astype(int)
                self.assertEqual(atlas.getpixel(tuple(xy)), (255, 0, 0, 255) if i < 3 else (0, 0, 255, 255))
            self.assertEqual(make_atlas([paths[0], paths[0]], root/'unused.png'), paths[0])

    def test_mismatched_timing_and_wrapping_uvs_are_rejected(self):
        a, b = mesh(2, .1), mesh(4, .2)
        b['sequences'][0]['duration'] = 300
        with self.assertRaisesRegex(ValueError, 'timing'):
            compose([a, b], ['a.png', 'b.png'])
        b = mesh(4, .2); b['vertices'][0, 6] = 1.5
        with self.assertRaisesRegex(ValueError, 'non-wrapping'):
            compose([a, b], ['a.png', 'b.png'])

    def test_every_part_invalidates_cache_but_shiny_geometry_can_reuse(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ['a', 'b', 'red', 'blue', 'shinyred', 'shinyblue', 'animation']:
                (root/name).write_bytes(name.encode())
            appearance = dict(model=str(root/'a'), texture=str(root/'red'), fps=30,
                              animations=dict(idle=str(root/'animation')),
                              parts=[dict(model=str(root/'a'), texture=str(root/'red')),
                                     dict(model=str(root/'b'), texture=str(root/'blue'))])
            before = fingerprint(appearance, 'v')
            (root/'b').write_bytes(b'changed part')
            self.assertNotEqual(before, fingerprint(appearance, 'v'))
            shiny = copy.deepcopy(appearance)
            shiny['parts'][0]['texture'] = str(root/'shinyred')
            shiny['parts'][1]['texture'] = str(root/'shinyblue')
            self.assertEqual(fingerprint(appearance, 'v', texture=False), fingerprint(shiny, 'v', texture=False))
            self.assertNotEqual(fingerprint(appearance, 'v'), fingerprint(shiny, 'v'))
            before = fingerprint(appearance, 'v', texture=False)
            appearance['parts'][1]['animations'] = dict(idle=str(root/'blue'))
            self.assertNotEqual(before, fingerprint(appearance, 'v', texture=False))


if __name__ == '__main__':
    unittest.main()
