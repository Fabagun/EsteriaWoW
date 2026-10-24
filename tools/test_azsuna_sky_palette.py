"""Regression against the exact model captured by the guarded camera crash."""
import struct
import unittest

import repair_azsuna_sky_palette as sky


class SkyPalette(unittest.TestCase):
    def setUp(self):
        self.model = (sky.WORK / 'azsuna_sky01.m2').read_bytes()
        self.skin = (sky.WORK / 'azsuna_sky0100.skin').read_bytes()

    def test_captured_bad_spans_are_bounded_without_changing_vertices(self):
        count = struct.unpack_from('<I', self.model, 120)[0]
        sections, offset = struct.unpack_from('<2I', self.skin, 28)
        spans = [struct.unpack_from('<2H', self.skin, offset + i * 48 + 12) for i in range(sections)]
        self.assertTrue(any(start + length > count for length, start in spans))
        fixed, _ = sky.repair(self.model, self.skin)
        changed = {i for i, (old, new) in enumerate(zip(self.skin, fixed)) if old != new}
        allowed = {offset + i * 48 + byte for i in range(sections) for byte in range(12, 16)}
        self.assertTrue(changed <= allowed)
        bones = struct.unpack_from('<I', self.model, 44)[0]
        palette_offset = struct.unpack_from('<I', self.model, 124)[0]
        palette = struct.unpack_from('<' + str(count) + 'H', self.model, palette_offset)
        properties, properties_offset = struct.unpack_from('<2I', fixed, 20)
        for i in range(sections):
            start, vertices = struct.unpack_from('<2H', fixed, offset + i * 48 + 4)
            length, first = struct.unpack_from('<2H', fixed, offset + i * 48 + 12)
            self.assertLessEqual(first + length, count)
            for local in fixed[properties_offset + start * 4:properties_offset + (start + vertices) * 4]:
                self.assertLess(local, length)
                self.assertLess(palette[first + local], bones)

    def test_invalid_shared_palette_is_rejected(self):
        bad = bytearray(self.model)
        at = struct.unpack_from('<I', bad, 124)[0]
        struct.pack_into('<H', bad, at, 65535)
        with self.assertRaisesRegex(ValueError, 'invalid rig bone'):
            sky.repair(bad, self.skin)


if __name__ == '__main__':
    unittest.main()
