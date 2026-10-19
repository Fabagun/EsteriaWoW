"""Offline preservation and asset-closure gates for the additive skin stage (no builds)."""

from collections import Counter
import json
import struct
import unittest

import skin_expansion as s


class SkinExpansionTests(unittest.TestCase):
    def test_saved_indexes_and_profiles(self):
        self.assertEqual(s.d.SKINS[:5], ('drakonid2_blue', 'drakonid2_black', 'drakonid2_bronze',
                                        'drakonid2_green', 'drakonid2_red'))
        self.assertEqual(s.t.SKINS[:6], ('white', 'black', 'blue', 'bronze', 'green', 'red'))
        self.assertEqual(s.d.codec()['capacities'], [17, 4, 6, 76, 1])
        self.assertEqual(len(set(s.d.SKINS)), 17)
        for slug, _, _, names in s.EXPANSIONS:
            manifest = s.t.p.load_manifest(slug)
            profile = manifest['appearance']['profiles']['0']
            self.assertEqual(profile['options'][0]['choices'], list(names))
            self.assertEqual(profile['capacities'][0], len(names))
            self.assertTrue(all(0 < capacity <= 256 for capacity in profile['capacities']))
        self.assertEqual(s.t.p.load_manifest('drakkin_alliance')['appearance']['profiles']['0']
                         ['capacities'], [7, 1, 5, 7, 1])

    def test_hd_mip_chains_and_preserved_blocks(self):
        report = s.t.p.load_json(s.WORK / 'hd-skins.json')
        self.assertEqual(len(report['assets']), 13)
        for row in report['assets']:
            before = s.Blp.parse(s.Path(row['source']).read_bytes())
            blob = s.Path(row['destination']).read_bytes()
            after = s.valid_dxt(blob, tuple(row['dimensions']))
            self.assertEqual(after.mips[:before.mip_count], before.mips)
            self.assertEqual(s.digest(blob), row['sha256'])
            self.assertEqual(s.complete_dxt(blob, tuple(row['dimensions']))[0], blob)
            with self.assertRaises(AssertionError):
                s.valid_dxt(blob[:-1], tuple(row['dimensions']))

    def test_stage_table_preservation_and_skin_choices(self):
        for side in ('client/DBFilesClient', 'server'):
            for name in ('CharSections', 'BarberShopStyle'):
                relative = side + '/' + name + '.dbc'
                old = s.t.p.RawWdbc((s.WORK / 'baseline' / relative).read_bytes())
                new = s.t.p.RawWdbc((s.WORK / 'stage' / relative).read_bytes())
                self.assertFalse(Counter(old.records) - Counter(new.records))
                self.assertTrue(new.strings.startswith(old.strings))
                ids = [s.t.p._value(row, 0) for row in new.records]
                self.assertEqual(len(ids), len(set(ids)))
                for _, race, _, names in s.EXPANSIONS:
                    if name == 'CharSections':
                        skins = [s.t.p._value(row, 36) for row in new.records
                                 if tuple(s.t.p._value(row, at) for at in (4, 8, 12)) == (race, 0, 0)]
                        self.assertEqual(skins, list(range(len(names))))

    def test_catalog_preservation_and_closure(self):
        for name, stride in (('EsteriaAppearance.bin', 2316), ('EsteriaDrakonid.bin', 156),
                             ('EsteriaTarasek.bin', 156)):
            before = (s.WORK / 'baseline/catalogs' / name).read_bytes()
            after = (s.WORK / 'stage/catalogs' / name).read_bytes()
            self.assertEqual(len(after), 12 + struct.unpack_from('<I', after, 8)[0] * stride)
            if stride == 2316:
                self.assertEqual(len(before), len(after))
                expected = bytearray(before)
                for at in range(12, len(before), stride):
                    race, sex = struct.unpack_from('<2I', before, at)
                    if sex == 0 and race in (66, 69, 70):
                        struct.pack_into('<I', expected, at + 16, 7 if race == 66 else 17)
                self.assertEqual(after, expected)
            else:
                self.assertEqual(after[12:len(before)], before[12:])
                additions = [after[at:at + stride] for at in range(len(before), len(after), stride)]
                self.assertEqual(len(additions), 12 if name == 'EsteriaDrakonid.bin' else 7)
                for row in additions:
                    path = row[28:].split(b'\0')[0].decode()
                    self.assertTrue((s.WORK / 'stage/assets' / path).is_file(), path)
        report = s.t.p.load_json(s.WORK / 'stage.json')
        for path, expected in report['after'].items():
            self.assertEqual(s.t.p.sha256(s.Path(path)), expected)


if __name__ == '__main__':
    unittest.main()
