"""Regression checks for the conversion math and reversible deployment boundaries."""
import json
import math
from pathlib import Path
import shutil
import struct
import tempfile
import unittest

import numpy as np
from PIL import Image

from bmd import Reader, read_bmd
from convert import MODULE, LAYER, write_blp
from deploy import install, targets
from m2 import quaternion, compressed_quaternion, world_matrices
from validate import rotation_matrix, read_model
from texture import pad_islands, filtered_edge_alpha


class FormatTests(unittest.TestCase):
    def test_quaternion_roundtrip_known_rotations(self):
        for axis in range(3):
            for angle in [0, 0.3, math.pi/2, math.pi, -math.pi/2]:
                q = np.zeros(4)
                q[axis], q[3] = math.sin(angle/2), math.cos(angle/2)
                expected = rotation_matrix(q)
                packed = compressed_quaternion(quaternion(expected))
                values = np.array(struct.unpack('<4h', packed))
                decoded = np.where(values < 0, values+32768, values-32767)/32767
                np.testing.assert_allclose(rotation_matrix(decoded), expected, atol=0.0001)

    def test_parent_rotation_moves_child_translation(self):
        bones = [('root', -1), ('child', 0)]
        frames = np.array([[[0, 0, 0, 0, 0, math.pi/2], [2, 0, 0, 0, 0, 0]]])
        result = world_matrices(bones, frames)
        np.testing.assert_allclose(result[0, 1, :3, 3], [0, 2, 0], atol=1e-7)
        np.testing.assert_allclose(result @ np.linalg.inv(result), np.broadcast_to(np.eye(4), result.shape), atol=1e-7)

    def test_cycle_and_truncated_binary_are_rejected(self):
        with self.assertRaises(ValueError):
            world_matrices([('root', 1), ('child', 0)], np.zeros((1, 2, 6)))
        with self.assertRaises(ValueError):
            Reader(b'\0').unpack('H')

    def test_sparse_frames_carry_forward(self):
        import lzma
        # One bone, two frames; frame 1 contains no changed bones.
        raw = struct.pack('>Hhh', 1, 0, -1) + 'Root\0'.encode('utf-16be')
        raw += struct.pack('>HHH6fHHH', 2, 1, 0, 1, 2, 3, 0, 0, 0, 0, 0, 0)
        with tempfile.TemporaryDirectory(prefix='battlemon-bmd-') as directory:
            path = Path(directory)/'sparse.bmd'
            path.write_bytes(b'\2'+lzma.compress(raw))
            data = read_bmd(path)
            np.testing.assert_equal(data['frames'][0], data['frames'][1])


class TextureTests(unittest.TestCase):
    def test_padding_preserves_paint_and_does_not_wrap(self):
        pixels = np.zeros((12, 12, 4), dtype=np.uint8)
        pixels[4:8, 0:3] = [231, 142, 38, 255]
        padded = np.array(pad_islands(Image.fromarray(pixels), 2))
        np.testing.assert_equal(padded[4:8, 0:3], pixels[4:8, 0:3])
        np.testing.assert_equal(padded[5, 4], [231, 142, 38, 255])
        self.assertEqual(int(padded[5, -1, 3]), 0)
        self.assertEqual(int(padded[0, 0, 3]), 0)

    def test_exported_mips_keep_uv_edges_opaque(self):
        pixels = np.zeros((32, 32, 4), dtype=np.uint8)
        pixels[12:20, 12:20] = [230, 140, 30, 255]
        uv = np.array([[12/32, 12/32], [20/32, 12/32], [12/32, 20/32], [20/32, 20/32]])
        triangles = np.array([[0, 1, 2], [1, 3, 2]])
        with tempfile.TemporaryDirectory(prefix='battlemon-texture-') as directory:
            source, output = Path(directory)/'source.png', Path(directory)/'output.blp'
            Image.fromarray(pixels).save(source)
            write_blp(output, source)
            results = filtered_edge_alpha(output, uv, triangles)
            self.assertEqual(len(results), 6)
            self.assertTrue(all(level['nonopaque_samples'] == 0 for level in results))


class DeploymentTests(unittest.TestCase):
    def test_install_remove_preserves_baseline_and_rejects_external_changes(self):
        original = MODULE/'generated/pixelmon-3d'
        with tempfile.TemporaryDirectory(prefix='battlemon-install-') as directory:
            root = Path(directory).resolve()
            staged, client, server = root/'output', root/'client', root/'server'
            staged.mkdir()
            for side in ['client', 'server']:
                shutil.copytree(original/side, staged/side)
            shutil.copyfile(original/'manifest.json', staged/'manifest.json')
            patch = client/'Data/patch-z.mpq'
            patch.mkdir(parents=True)
            (client/'Wow.exe').write_bytes(b'test-only')
            (server/'dbc-continuations').mkdir(parents=True)
            baseline = patch/'DBFilesClient/CreatureModelData.dbc1-battlemon'
            baseline.parent.mkdir()
            baseline.write_bytes(b'original-2d-layer')
            files = install(staged, client, server)
            self.assertEqual(len(files), 28)
            victim = files[0][2]
            before = victim.read_bytes()
            victim.write_bytes(b'external-edit')
            with self.assertRaises(ValueError):
                install(staged, client, server, remove=True)
            self.assertTrue(all(p.exists() for _, _, p, _ in files))
            victim.write_bytes(before)
            install(staged, client, server, remove=True)
            self.assertTrue(all(not p.exists() for _, _, p, _ in files))
            self.assertEqual(baseline.read_bytes(), b'original-2d-layer')
            manifest = json.loads((staged/'manifest.json').read_text())
            manifest['files']['client/../outside'] = 'bad'
            (staged/'manifest.json').write_text(json.dumps(manifest))
            with self.assertRaises(ValueError):
                targets(staged, client, server)


if __name__ == '__main__':
    unittest.main()
