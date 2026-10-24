"""Focused preservation, identity, catalog and Lua checks for the native race stage."""

import base64
from collections import Counter
import struct
import unittest
from unittest.mock import patch

from lupa.lua51 import LuaRuntime

import kyrian_venthyr_pack as k
import kyrian_venthyr_deploy as deploy


class NativeRaceStage(unittest.TestCase):
    def test_rollback_refuses_to_orphan_new_characters(self):
        with patch.object(deploy.k.p, 'load_json', return_value={}), \
             patch.object(deploy, 'ensure_client_closed'), \
             patch.object(deploy, 'sql', return_value='1\n'), \
             patch.object(deploy, 'command') as command:
            with self.assertRaisesRegex(RuntimeError, 'preserve/migrate'):
                deploy.rollback()
            command.assert_not_called()

    def test_packed_remap_and_preservation(self):
        k.self_check()

    def test_foreign_model_id_is_rejected(self):
        row = struct.pack('<28I', 121060, *([0] * 27))
        blob = struct.pack('<4s4I', b'WDBC', 1, 28, 112, 1) + row + b'\0'
        recipe = {'fields': 28, 'stride': 112, 'rows': [
            {'bytes': base64.b64encode(row).decode(), 'strings': {}}]}
        with self.assertRaisesRegex(ValueError, 'collision'):
            k.merge('CreatureModelData', blob, recipe, {})

    def test_unrelated_records_and_strings_preserved(self):
        for folder, output in (('baseline-client', 'client-dbc'), ('baseline-server', 'server/dbc')):
            for file in (k.STAGE / folder).glob('*.dbc'):
                before = k.p.RawWdbc(file.read_bytes())
                after = k.p.RawWdbc((k.STAGE / output / file.name).read_bytes())
                self.assertFalse(Counter(before.records) - Counter(after.records), file.name)
                self.assertTrue(after.strings.startswith(before.strings), file.name)

    def test_race_identity_and_classes(self):
        table = k.p.RawWdbc((k.STAGE / 'client-dbc/ChrRaces.dbc').read_bytes())
        for _, race, name, faction, _ in k.SPECS:
            rows = [row for row in table.records if k.p._value(row, 0) == race]
            self.assertEqual(len(rows), 1)
            self.assertEqual(k.p._value(rows[0], 52), 0 if faction == 'alliance' else 1)
            pairs = k.p.RawWdbc((k.STAGE / 'client-dbc/CharBaseInfo.dbc').read_bytes())
            self.assertEqual(sorted(row[1] for row in pairs.records if row[0] == race), k.CLASSES)
            self.assertEqual(k.p._string(table.strings, k.p._value(rows[0], 44)).decode(),
                             name.title() + faction.title())

    def test_client_server_keys_and_values_agree(self):
        for file in (k.STAGE / 'server/dbc').glob('*.dbc'):
            table = file.stem
            client = k.p.RawWdbc((k.STAGE / 'client-dbc' / file.name).read_bytes())
            server = k.p.RawWdbc(file.read_bytes())
            def selected(record):
                if table == 'CreatureModelData':
                    return 121060 <= k.p._value(record, 0) <= 121063
                if table == 'CreatureDisplayInfo':
                    return 60083 <= k.p._value(record, 0) <= 60086
                return k.race_of(table, record) in (75, 76)
            def semantic(source):
                result = []
                fields = set(k.p.STRING_FIELDS.get(table, ()))
                if table == 'CreatureDisplayInfo':
                    fields.add(9)
                for record in source.records:
                    if not selected(record):
                        continue
                    raw = bytearray(record)
                    strings = []
                    for field in sorted(fields):
                        strings.append(k.p._string(source.strings, k.p._value(record, field * 4)))
                        struct.pack_into('<I', raw, field * 4, 0)
                    result.append((bytes(raw), tuple(strings)))
                return Counter(result)
            self.assertEqual(semantic(client), semantic(server), table)

    def test_all_eight_controls_fit_frozen_encoding(self):
        for _, _, name, _, _ in k.SPECS:
            manifest = k.p.load_manifest(name)
            bank = (k.STAGE / ('client/Esteria' + name.title() + '.bin')).read_bytes()
            magic, version, count = struct.unpack_from('<3I', bank)
            self.assertEqual((magic, version, len(bank)), (0x314d4845, 1, 12 + count * 156))
            for sex, profile in manifest['appearance']['profiles'].items():
                self.assertEqual(len(profile['descriptors']), 8)
                maxima = [0] * 5
                for field, choices, factor in profile['descriptors']:
                    maxima[field] += (choices - 1) * factor
                self.assertEqual(maxima, [capacity - 1 for capacity in profile['capacities']])
                for i in range(count):
                    row = bank[12+i*156:12+(i+1)*156]
                    if struct.unpack_from('<I', row)[0] != int(sex):
                        continue
                    for selector in struct.unpack_from('<3I', row, 16):
                        if selector == 0xffffffff:
                            continue
                        option, choice = selector & 65535, selector >> 16
                        self.assertLess(option, 8)
                        self.assertLess(choice, profile['descriptors'][option][1])

    def test_lua_compiles_and_portrait_paths_are_present(self):
        lua = LuaRuntime()
        compile_lua = lua.eval('function(s) local f,e=loadstring(s); assert(f,e); return true; end')
        for file in (k.STAGE / 'glue').glob('*.lua'):
            self.assertTrue(compile_lua(file.read_text(encoding='utf-8-sig')), file.name)
        creator = (k.STAGE / 'glue/CharacterCreate.lua').read_text()
        self.assertIn('CharacterCreate.selectedRaceID == 75', creator)
        self.assertIn('CharacterCreate.selectedRaceID == 76', creator)
        self.assertIn('BodyShapePage_Active', creator)


if __name__ == '__main__':
    unittest.main()
