"""Regression tests for missing-appearance recovery and preserving installed exports."""
import json
import lzma
from pathlib import Path
import struct
import tempfile
import unittest

from PIL import Image

from batch import digest, preserved_records
from bmd import read_bmd
from catalog import choose_form, Unsupported
from convert import write_blp


class RecoveryTests(unittest.TestCase):
    def test_complete_payload_without_xz_footer_and_truncated_payload(self):
        raw = struct.pack('>Hhh', 1, 0, -1) + 'Root\0'.encode('utf-16be')
        raw += struct.pack('>HHH6fHH', 1, 1, 0, 1, 2, 3, 0, 0, 0, 0, 0)
        compressed = lzma.compress(raw)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'model.bmd'
            # Remove only the XZ footer. Full geometry still parses exactly.
            path.write_bytes(b'\2'+compressed[:-12])
            self.assertEqual(read_bmd(path)['bones'], [('Root', -1)])
            # Compression can be readable while the BMD records are incomplete.
            path.write_bytes(b'\2'+lzma.compress(raw[:-2])[:-12])
            with self.assertRaisesRegex(ValueError, 'Truncated BMD'):
                read_bmd(path)
            path.write_bytes(b'\2'+compressed+b'extra')
            with self.assertRaisesRegex(ValueError, 'after BMD'):
                read_bmd(path)

    def test_npot_full_canvas_is_resampled_without_uv_padding(self):
        with tempfile.TemporaryDirectory() as directory:
            source, target = Path(directory)/'texture.png', Path(directory)/'texture.blp'
            image = Image.new('RGBA', (30, 18), (245, 20, 10, 255))
            for x in range(15, 30):
                for y in range(18):
                    image.putpixel((x, y), (10, 20, 245, 255))
            image.save(source)
            write_blp(target, source)
            decoded = Image.open(target).convert('RGBA')
            self.assertEqual(decoded.size, (32, 32))
            self.assertGreater(decoded.getpixel((8, 16))[0], 230)
            self.assertGreater(decoded.getpixel((24, 16))[2], 230)
            self.assertEqual(decoded.getpixel((31, 31))[3], 255)

    def test_named_aliases_and_defaults_do_not_guess_numbers(self):
        form, _ = choose_form(dict(name='Fighting Type Arceus', variant='01'),
                              dict(name='Arceus', forms=[dict(name='base'), dict(name='fighting')]))
        self.assertEqual(form['name'], 'fighting')
        form, _ = choose_form(dict(name='Shellos', variant=''),
                              dict(dex=422, name='Shellos', forms=[dict(name='east'), dict(name='west')]))
        self.assertEqual(form['name'], 'west')
        form, _ = choose_form(dict(name='Indeedee (Female)', variant='female'),
                              dict(dex=876, name='Indeedee', forms=[dict(name='male'), dict(name='female')]))
        self.assertEqual(form['name'], 'female')

        with self.assertRaisesRegex(Unsupported, 'unmapped_variant'):
            choose_form(dict(name='Sneasel (01 Female)', variant='01_female'),
                        dict(name='Sneasel', forms=[dict(name='base'), dict(name='hisuian')]))

    def test_verified_numeric_alias_requires_exact_catalog_identity(self):
        form = dict(id='106', name='Growlithe (01)', sprite='0058_Growlithe_01', variant='01')
        species = dict(dex=58, name='Growlithe', forms=[dict(name='base'), dict(name='hisuian')])
        picked, gender = choose_form(form, species)
        self.assertEqual((picked['name'], gender), ('hisuian', 'ALL'))
        for field in ['name', 'sprite']:
            with self.assertRaisesRegex(Unsupported, 'identity_changed'):
                choose_form(form | {field: 'different'}, species)
        with self.assertRaisesRegex(Unsupported, 'identity_changed'):
            choose_form(form, species | {'dex': 59})

    def test_preservation_verifies_content_and_excludes_failures(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            asset = root/'cache/assets/a.m2'
            asset.parent.mkdir(parents=True)
            asset.write_bytes(b'known export')
            report = root/'old.json'
            report.write_text(json.dumps(dict(records=[
                dict(form=10, shiny=False, status='passed', result=dict(files={'a.m2': digest(asset)})),
                dict(form=11, shiny=True, status='failed')])) )
            self.assertEqual(set(preserved_records(root, report)), {(10, False)})
            asset.write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError, 'checksum'):
                preserved_records(root, report)


if __name__ == '__main__':
    unittest.main()
