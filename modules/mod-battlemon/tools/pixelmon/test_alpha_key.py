"""Solid alpha-key acceptance keeps margin above the actual renderer cutoff."""
from pathlib import Path
import struct
import tempfile
import unittest

import numpy as np
from PIL import Image

from convert import write_blp
from texture import filtered_edge_alpha
from m2 import build_model
from validate import read_model
from test_skin_sections import fixture


class AlphaKeyTests(unittest.TestCase):
    def test_safe_nonopaque_pixels_and_unsafe_pixels_at_every_mip(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            uv = np.array([[0., 0.], [1., 0.], [0., 1.]])
            triangles = np.array([[0, 1, 2]])
            for alpha, safe in [(253, True), (240, True), (239, False), (223, False)]:
                Image.new('RGBA', (16, 16), (50, 120, 210, alpha)).save(root/'source.png')
                write_blp(root/'output.blp', root/'source.png')
                levels = filtered_edge_alpha(root/'output.blp', uv, triangles)
                self.assertEqual(len(levels), 5)
                self.assertTrue(all(x['nonopaque_samples'] > 0 for x in levels))
                self.assertEqual(all(x['unsafe_alpha_key_samples'] == 0 for x in levels), safe)
                self.assertEqual(all(x['minimum_alpha'] >= 240 for x in levels), safe)

    def test_bilinear_border_pinholes_remain_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            image = Image.new('RGBA', (16, 16), (50, 120, 210, 253))
            for y in range(16):
                image.putpixel((8, y), (50, 120, 210, 0))
            image.save(root/'source.png'); write_blp(root/'output.blp', root/'source.png')
            uv = np.array([[8.5/16, 0.], [8.5/16, 1.], [1., 0.]])
            levels = filtered_edge_alpha(root/'output.blp', uv, np.array([[0, 1, 2]]))
            self.assertGreater(levels[0]['unsafe_alpha_key_samples'], 0)
            self.assertLess(levels[0]['minimum_alpha'], 224)

    def test_other_blending_and_opacity_cannot_use_the_solid_gate(self):
        model, skin = build_model(fixture(), 'model', 'model.blp')
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); p = root/'model.m2'
            (root/'model00.skin').write_bytes(skin)
            data = bytearray(model); material = struct.unpack_from('<I', data, 0x74)[0]
            struct.pack_into('<H', data, material+2, 2); p.write_bytes(data)
            with self.assertRaisesRegex(ValueError, 'alpha-key material'):
                read_model(p)
            data = bytearray(model); opacity = struct.unpack_from('<I', data, 0x5c)[0]
            sequences = struct.unpack_from('<I', data, opacity+16)[0]
            values = struct.unpack_from('<I', data, sequences+4)[0]
            struct.pack_into('<H', data, values, 16000); p.write_bytes(data)
            with self.assertRaisesRegex(ValueError, 'full texture opacity'):
                read_model(p)


if __name__ == '__main__':
    unittest.main()
