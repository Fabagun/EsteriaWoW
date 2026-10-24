"""Emissive overlays retain both source textures and every animated, bone-limited draw."""
import copy
from pathlib import Path
import struct
import tempfile
import unittest
import numpy as np
from PIL import Image
from alpha_material import write_alpha_blp,validate_alpha_texture,source_digest
from batch import fingerprint
from emissive import prepare_overlay
from m2 import build_model
from test_multipart import mesh
from validate import read_model


class EmissiveTests(unittest.TestCase):
    def test_animated_overlay_faces_and_authored_alpha_are_preserved(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);base=root/'base.png';glow=root/'glow.png'
            Image.new('RGBA',(32,32),(20,40,80,192)).save(base)
            Image.new('RGBA',(32,32),(220,60,30,96)).save(glow)
            original=mesh(0,.2)
            result,atlas=prepare_overlay(original,[dict(texture=str(base),emissive=str(glow))],root/'atlas.png')
            m2,skin=build_model(result,'test','test.blp',texture_policy='source_alpha_emissive')
            path=root/'test.m2';path.write_bytes(m2);path.with_name('test00.skin').write_bytes(skin)
            write_alpha_blp(path.with_suffix('.blp'),atlas)
            decoded=read_model(path,texture_policy='source_alpha_emissive')
            half=len(decoded['positions'])//2
            for pose in decoded['poses']:
                np.testing.assert_array_equal(pose[:,:half],pose[:,half:])
            validate_alpha_texture(path.with_suffix('.blp'),atlas,source_digest(atlas),decoded['uv'],decoded['triangles'])
            self.assertEqual(len(decoded['triangles']),2)
            changed=bytearray(m2);_,at=struct.unpack_from('<II',changed,0x70)
            struct.pack_into('<H',changed,at+4,0)
            path.write_bytes(changed)
            with self.assertRaisesRegex(ValueError,'unlit'):
                read_model(path,texture_policy='source_alpha_emissive')

    def test_different_part_maps_cannot_be_silently_dropped(self):
        with self.assertRaisesRegex(ValueError,'shared'):
            prepare_overlay(mesh(0,.1),[dict(texture='a',emissive='x'),dict(texture='b',emissive='y')],'unused')
        with self.assertRaisesRegex(ValueError,'shared'):
            prepare_overlay(mesh(0,.1),[dict(texture='a',emissive=None)],'unused')

    def test_source_emissive_content_invalidates_texture_cache(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            for name in ['model','base','glow','walk']:(root/name).write_bytes(name.encode())
            part=dict(model=str(root/'model'),texture=str(root/'base'),emissive=str(root/'glow'))
            appearance=dict(part,parts=[part],fps=30,animations=dict(walk=str(root/'walk')))
            before=fingerprint(appearance,'v');geometry=fingerprint(appearance,'v',False)
            (root/'glow').write_bytes(b'new glow')
            self.assertNotEqual(before,fingerprint(appearance,'v'))
            self.assertEqual(geometry,fingerprint(appearance,'v',False))

if __name__=='__main__':unittest.main()
