"""Offline preservation and asset-closure gates for the female Tuskarr stage (no builds, no install)."""

from collections import Counter
import json
import struct
import unittest

import tuskarr_female_pack as f

p = f.s.t.p


def table(kind, name, stage=False):
    root = f.STAGE / ('client-dbc' if kind == 'client' else 'server-dbc') if stage else f.BASELINE / kind
    return p.RawWdbc((root / (name + '.dbc')).read_bytes())


class FemaleTuskarrTests(unittest.TestCase):
    def test_profile_and_registry(self):
        manifest = p.load_manifest('tuskarr')
        self.assertEqual(manifest['appearance']['supported_genders'], [0, 1])
        self.assertEqual(manifest['appearance']['profiles']['1']['capacities'], [7, 1, 1, 1, 1])
        self.assertEqual(manifest['appearance']['profiles']['0']['capacities'], [7, 1, 7, 7, 7])
        self.assertEqual(manifest['models']['female']['model_path'], f.MODEL)
        header = (f.s.t.REPO / 'src/server/shared/CreatureAppearance.h').read_text()
        self.assertIn('TuskarrFemale', header)
        self.assertIn('return gender ? TuskarrFemale : TuskarrMale;', header)

    def test_all_player_actions_and_sockets(self):
        report = json.loads((f.WORK / 'model.json').read_text())
        self.assertEqual(report['missing_player_actions'], [])
        animation = json.loads((f.WORK / 'animation-repair.json').read_text())
        self.assertTrue(animation['authored_tracks_preserved'] and animation['vertices_preserved'])
        model = f.parse_m2((f.STAGE / 'assets' / f.MODEL.replace('\\', '/')).read_bytes())
        male = f.parse_m2(f.PLAYER.read_bytes())
        self.assertEqual({a['id'] for a in male.attachments} - {a['id'] for a in model.attachments}, set())
        self.assertLessEqual(len(model.bones), 256)

    def test_tables_only_append_female_rows(self):
        for kind in ('client', 'server'):
            for name in f.TABLES:
                if not (f.BASELINE / kind / (name + '.dbc')).exists():
                    continue
                old, new = table(kind, name), table(kind, name, stage=True)
                if name == 'ChrRaces':
                    changed = [(a, b) for a, b in zip(old.records, new.records) if a != b]
                    self.assertEqual(len(changed), 1)
                    self.assertEqual(p._value(changed[0][1], 0), 55)
                    self.assertEqual(p._value(changed[0][1], 20), f.DISPLAY_ID)
                    continue
                self.assertFalse(Counter(old.records) - Counter(new.records))
                self.assertTrue(new.strings.startswith(old.strings))
                ids = [p._value(r, 0) for r in new.records if name not in ('CharacterFacialHairStyles',)]
                if name != 'CharacterFacialHairStyles':
                    self.assertEqual(len(ids), len(set(ids)), name)
            sections = table(kind, 'CharSections', stage=True)
            female = [r for r in sections.records if p._value(r, 4) == 55 and p._value(r, 8) == 1]
            self.assertEqual(len(female), 7 * 3 + 2)
            skins = [p._string(sections.strings, p._value(r, 16)).decode() for r in female if p._value(r, 12) == 0]
            self.assertEqual(skins, [f.texture_path(fid) for fid in f.SKINS])

    def test_creature_rows(self):
        models = table('client', 'CreatureModelData', stage=True)
        row = next(r for r in models.records if p._value(r, 0) == f.MODEL_ID)
        self.assertEqual(p._string(models.strings, p._value(row, 8)).decode(), f.MODEL)
        displays = table('client', 'CreatureDisplayInfo', stage=True)
        row = next(r for r in displays.records if p._value(r, 0) == f.DISPLAY_ID)
        self.assertEqual(p._value(row, 4), f.MODEL_ID)

    def test_selections_keep_male_records_and_bank_offsets(self):
        old = (f.BASELINE / 'EsteriaTuskarr.bin').read_bytes()
        new = (f.STAGE / 'EsteriaTuskarr.bin').read_bytes()
        count = struct.unpack_from('<I', old, 8)[0]
        self.assertEqual(new[12:12 + count * 156], old[12:])
        records = [new[at:at + 156] for at in range(12 + count * 156, len(new), 156)]
        self.assertEqual(len(records), 7 + 8 + 1)
        self.assertTrue(all(struct.unpack_from('<I', r)[0] == 1 for r in records))
        old_bank = (f.BASELINE / 'EsteriaTuskarrTextures.bin').read_bytes()
        bank = (f.STAGE / 'EsteriaTuskarrTextures.bin').read_bytes()
        self.assertEqual(bank[16:len(old_bank)], old_bank[16:])
        self.assertEqual(struct.unpack_from('<I', bank, 8)[0], struct.unpack_from('<I', old_bank, 8)[0] + 1)
        base = records[-1]
        self.assertEqual(struct.unpack_from('<4I', base)[:3], (1, 3, 0))
        offset = struct.unpack_from('<I', base, 12)[0]
        self.assertEqual(offset, len(old_bank))
        width, height, size = struct.unpack_from('<3I', bank, offset)
        self.assertEqual((width, height, offset + 12 + size), (512, 512, len(bank)))
        for fid, record in zip(f.SKINS, records):
            self.assertEqual(struct.unpack_from('<4I', record)[:3], (1, 1, 11))
            self.assertEqual(record[28:].split(b'\0')[0].decode(), f.texture_path(fid))

    def test_appearance_and_glue(self):
        old = (f.BASELINE / 'EsteriaAppearance.bin').read_bytes()
        new = (f.STAGE / 'EsteriaAppearance.bin').read_bytes()
        self.assertEqual(len(new), len(old) + 2316)
        self.assertEqual(new[12:len(old)], old[12:])
        self.assertEqual(struct.unpack_from('<3I', new, len(old)), (55, 1, 5))
        text = (f.STAGE / 'CharacterCreate.lua').read_text(encoding='utf-8')
        self.assertNotIn('race == 55 or', text)
        self.assertIn('UI-CharacterCreate-TuskarrFemale', text)

    def test_skin_textures_and_portraits(self):
        for fid in f.SKINS:
            blob = (f.STAGE / 'assets' / f.texture_path(fid).replace('\\', '/')).read_bytes()
            texture = f.s.Blp.parse(blob)
            for level in range(texture.mip_count):
                texture.decode_level(level)
        for key in ('Interface/Glues/CharacterCreate/UI-CharacterCreate-TuskarrFemale.blp',
                    'Interface/Glues/CharacterSelect/ECS-Portrait-TuskarrFemale.blp'):
            self.assertTrue((f.STAGE / 'assets' / key).is_file(), key)

    def test_receipt_is_unbuilt_and_uninstalled(self):
        receipt = json.loads((f.WORK / 'stage.json').read_text())
        self.assertFalse(receipt['installed'] or receipt['packaged'] or receipt['live_accepted'])


if __name__ == '__main__':
    unittest.main()
