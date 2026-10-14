"""Small runnable checks for the native atlas and indexed texture contract."""

import struct
from types import SimpleNamespace

import numpy as np
from PIL import Image
from wotlkconv.blp import Blp
from wotlkconv.m2.skin import Skin

import human_native_retroport as h


def main():
    art = Image.new('RGBA', (32, 16), (120, 50, 75, 255))
    art.putpixel((0, 0), (120, 50, 75, 0))
    for alpha in (False, True):
        blp = Blp.parse(h.indexed(art, alpha))
        assert blp.compression == 1 and blp.alpha_type == 8
        assert blp.alpha_size == (8 if alpha else 0)
        assert blp.mip_count == 5  # Stop at the short axis.
        assert blp.decode_level(0).data[3] == (0 if alpha else 255)
    mask = np.zeros((512, 512), dtype=np.uint8)
    tiles = [h.reserve(mask, *size) for size in ((128, 64), (128, 128), (128, 128), (128, 128))]
    for i, (x, y, width, height) in enumerate(tiles):
        for left, top, w, ht in tiles[:i]:
            assert x + width <= left or left + w <= x or y + height <= top or top + ht <= y
    try:
        h.reserve(np.ones((512, 512), dtype=np.uint8), 128, 64)
        raise AssertionError('An occupied atlas must be rejected')
    except ValueError:
        pass
    raw = bytearray(48)
    struct.pack_into('<2f', raw, 32, .25, .75)
    uv = struct.unpack_from('<2f', h.tile_uv(raw, (128, 0, 128, 64)), 32)
    assert uv == (.3125, .09375)
    struct.pack_into('<f', raw, 32, float('nan'))
    try:
        h.tile_uv(raw, tiles[0])
        raise AssertionError('Nonfinite source UVs must be rejected')
    except ValueError:
        pass
    face = Image.new('RGBA', (256, 192), (0, 0, 255, 255))
    face.paste((255, 0, 0, 255), (0, 0, 256, 64))
    lower, upper = h.face_fragments(face)
    assert lower[0] == 4 and lower[2].size == (256, 128) and lower[2].getpixel((0, 0))[:3] == (0, 0, 255)
    assert upper[0] == 5 and upper[2].size == (256, 64) and upper[2].getpixel((0, 0))[:3] == (255, 0, 0)
    skin = Skin(bone_count_max=1)
    skin.vertices = [0, 1, 2, 0, 1, 2]
    skin.bones = bytes(24)
    skin.indices = [0, 1, 2] * 10000 + [3, 4, 5] * 12000
    for start, count, first in ((0, 30000, 0), (30000, 36000, 3)):
        mesh = bytearray(48)
        struct.pack_into('<6H', mesh, 0, 0, 0, first, 3, start, count)
        skin.submeshes.append(bytes(mesh))
    rebuilt = h.native_indices(skin, SimpleNamespace(vertex_count=3))
    assert len(rebuilt.indices) == 66000 and all(h.v.u16(r, 2) == 0 for r in rebuilt.submeshes)
    assert max(rebuilt.indices) < len(rebuilt.vertices)
    print('Human native atlas, alpha, mip, UV and triangle-offset checks passed')


if __name__ == '__main__':
    main()
