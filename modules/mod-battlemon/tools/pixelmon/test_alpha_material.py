"""Authored holes/translucency survive, while corruption and policy substitutions fail."""
import tempfile
from pathlib import Path
import struct
import unittest
import numpy as np
from PIL import Image
from alpha_material import write_alpha_blp, validate_alpha_texture, source_digest
from texture import decode_blp
from m2 import build_model
from validate import read_model
from test_skin_sections import fixture
from validation_cache import validate_asset


class AlphaMaterialTests(unittest.TestCase):
    def test_all_mips_preserve_holes_and_fractional_alpha_and_reject_corruption(self):
        uv=np.array([[0,0],[1,0],[0,1]]); triangles=np.array([[0,1,2]])
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); pixels=np.full((16,16,4),255,dtype=np.uint8)
            pixels[:,:,:3]=[20,140,220]; pixels[4:12,4:12,3]=0; pixels[:4,:4,3]=127
            Image.fromarray(pixels).save(p/'source.png')
            write_alpha_blp(p/'a.blp',p/'source.png'); original=(p/'a.blp').read_bytes()
            proof=source_digest(p/'source.png')
            levels=validate_alpha_texture(p/'a.blp',p/'source.png',proof,uv,triangles)
            self.assertEqual(len(levels),5)
            self.assertEqual(levels[0]['transparent_pixels'],64)
            self.assertEqual(levels[0]['fractional_pixels'],16)
            np.testing.assert_array_equal(np.array(decode_blp(p/'a.blp')),pixels)
            for mip in [0,2,4]:
                for channel in [0,3]:
                    data=bytearray(original); offset=struct.unpack_from('<I',data,20+4*mip)[0]
                    data[offset+channel] ^= 127; (p/'a.blp').write_bytes(data)
                    with self.assertRaises(ValueError):
                        validate_alpha_texture(p/'a.blp',p/'source.png',proof,uv,triangles)
            (p/'a.blp').write_bytes(original)
            with self.assertRaisesRegex(ValueError,'checksum'):
                validate_alpha_texture(p/'a.blp',p/'source.png','wrong',uv,triangles)

    def test_policy_is_explicit_and_cache_rechecks_content_and_policy(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); model,skin=build_model(fixture(),'model','model.blp',texture_policy='source_alpha_blend')
            (p/'model.m2').write_bytes(model); (p/'model00.skin').write_bytes(skin)
            Image.new('RGBA',(16,16),(50,120,210,127)).save(p/'source.png')
            write_alpha_blp(p/'model.blp',p/'source.png')
            entry=dict(texture_policy='source_alpha_blend',alpha_source=str(p/'source.png'),
                       alpha_source_sha256=source_digest(p/'source.png'))
            with self.assertRaises(ValueError): read_model(p/'model.m2')
            read_model(p/'model.m2',texture_policy='source_alpha_blend')
            self.assertFalse(validate_asset(p/'model.m2',entry,'model.blp',p/'receipts'))
            self.assertTrue(validate_asset(p/'model.m2',entry,'model.blp',p/'receipts'))
            with self.assertRaises(ValueError): validate_asset(p/'model.m2',entry,'wrong.blp',p/'receipts')
            with self.assertRaises(ValueError): validate_asset(p/'model.m2',{},'model.blp',p/'receipts')
            data=bytearray((p/'model.blp').read_bytes()); data[-1]=255; (p/'model.blp').write_bytes(data)
            with self.assertRaises(ValueError): validate_asset(p/'model.m2',entry,'model.blp',p/'receipts')

if __name__ == '__main__': unittest.main()
