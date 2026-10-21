"""Focused staged-data, portrait, Lua policy, and reversible character-migration checks."""

from collections import Counter
import json
import re
import sqlite3
import struct
import unittest

from PIL import Image
from lupa.lua51 import LuaRuntime

import slime_centaur_racials as r
import slime_centaur_factions as f


class RacialStageTests(unittest.TestCase):
    def table(self, name, folder='client-dbc'):
        return r.p.RawWdbc((r.STAGE / folder / (name + '.dbc')).read_bytes())

    def test_spell_contract(self):
        table = self.table('Spell')
        index = r.d.field_index()
        rows = {r.p._value(row, 0): row for row in table.records}

        def value(identifier, name, signed=False):
            return struct.unpack_from('<i' if signed else '<I', rows[identifier], index[name] * 4)[0]

        self.assertEqual(value(111011, 'EffectAura_1'), 245)
        self.assertEqual(value(111011, 'EffectMiscValue_1'), 4)
        self.assertEqual(value(111011, 'EffectBasePoints_1', True) + 1, -10)
        self.assertEqual(value(111012, 'EffectAuraPeriod_1'), 5000)
        self.assertEqual(value(111013, 'RecoveryTime'), 120000)
        self.assertEqual(value(111013, 'DurationIndex'), 32)
        self.assertEqual(value(111014, 'EffectBasePoints_1', True) + 1, -30)
        self.assertEqual(value(111020, 'EffectBasePoints_1') + 1, 5)
        self.assertEqual(value(111020, 'EquippedItemClass'), 2)
        self.assertEqual(value(111020, 'EquippedItemSubclass'), 1 << 6)
        self.assertEqual(value(111023, 'EffectAura_1'), 4)
        self.assertEqual(value(111024, 'RecoveryTime'), 120000)
        self.assertEqual(value(111025, 'DurationIndex'), 1)
        self.assertEqual(value(111025, 'EffectMiscValue_1'), 127)
        self.assertEqual(value(111027, 'EffectAura_2'), 206)
        for identifier in (111002, 111003):
            self.assertTrue(value(identifier, 'AttributesEx4') & 0x20000000)
        with r.p.ClientFiles(str(r.p.CLIENT_DEFAULT / 'Data'), 'enUS') as files:
            duration = r.p.RawWdbc(files.find(r.p.DBC_ROOT + 'SpellDuration.dbc')[0])
        durations = {r.p._value(row, 0): struct.unpack_from('<i', row, 4)[0] for row in duration.records}
        self.assertEqual(durations[32], 6000)
        self.assertEqual(durations[1], 10000)
        self.assertLessEqual(durations[39], 2000)

    def test_unrelated_records_preserved(self):
        owned = {s[0] for s in r.SPECS} | set(range(111000, 111004))
        for path in (r.STAGE / 'baseline-client').glob('*.dbc'):
            before = r.p.RawWdbc(path.read_bytes())
            after = self.table(path.stem)
            if path.stem == 'CharBaseInfo':
                expected = Counter(row for row in before.records if row[0] not in (71, 74))
                self.assertEqual(expected, Counter(after.records))
            else:
                excluded = owned if path.stem == 'Spell' else {71, 74} if path.stem == 'ChrRaces' else set()
                self.assertFalse(Counter(row for row in before.records if r.p._value(row, 0) not in excluded)
                                 - Counter(after.records), path.stem)
        flags = {r.p._value(row, 0): r.p._value(row, 4) for row in self.table('ChrRaces').records}
        self.assertTrue(flags[71] & 1 and flags[74] & 1)
        self.assertFalse(flags[72] & 1 or flags[73] & 1)

    def test_passenger_seats_and_flight_identity(self):
        vehicles = {r.p._value(row, 0): row for row in self.table('Vehicle').records}
        seats = {r.p._value(row, 0): row for row in self.table('VehicleSeat').records}
        for offset, attachment in ((0, 39), (1, 0)):
            self.assertEqual(r.p._value(vehicles[r.VEHICLE + offset], 24), r.SEAT + offset)
            seat = seats[r.SEAT + offset]
            self.assertEqual(r.p._value(seat, 8), attachment)
            self.assertTrue(r.p._value(seat, 4) & 0x02000000)
            self.assertFalse(r.p._value(seat, 4) & (0x200 | 0x800 | 0x20000000))
        table = self.table('CreatureModelData')
        model = next(row for row in table.records if r.p._value(row, 0) == r.FLIGHT_MODEL)
        self.assertEqual(r.p._string(table.strings, r.p._value(model, 8)), b'retail\\4077816.m2')
        inventory = json.loads((r.WORK / 'ohnahra/inventory.json').read_text())
        self.assertEqual((inventory['npc'], inventory['display']), (194796, 106285))
        self.assertTrue(inventory['complete'])
        self.assertIn(0, inventory['attachments'])
        for entry in inventory['assets'].values():
            self.assertEqual(r.p.sha256(r.Path(entry['path'])), entry['sha256'])

    def test_portraits_and_creator_policy(self):
        storm = r.p.Storm(r.p.DLL_DEFAULT)
        handle = storm.open_archive(r.STAGE / 'slime-centaur-racials-overlay.MPQ')
        try:
            lua = storm.read(handle, r.p.GLUE_ROOT + 'CharacterCreate.lua').decode()
            expression = re.search(r'local hiddenRace = ([^\n]+)', lua).group(1)
            check = LuaRuntime().eval('function(fileString) local strupper=string.upper; return ' + expression + ' end')
            self.assertTrue(check('SlimeGiantAlliance'))
            self.assertTrue(check('CentaurHorde'))
            self.assertFalse(check('SlimeGiantHorde'))
            self.assertFalse(check('CentaurAlliance'))
            for faction in ('Alliance', 'Horde'):
                for sex in ('Male', 'Female'):
                    source = r.Path('R:/Users/Zach/Pictures/Portraits') / faction / (
                        f'Charactercreate-races_centaur-{sex.lower()}_{faction.lower()}.png')
                    entry = f'Interface\\Glues\\CharacterCreate\\UI-CharacterCreate-Centaur{faction}{sex}.blp'
                    data = storm.read(handle, entry)
                    offset = struct.unpack_from('<I', data, 20)[0]
                    pixels = Image.frombytes('RGBA', (64, 64), data[offset:offset + 64 * 64 * 4], 'raw', 'BGRA')
                    expected = Image.open(source).convert('RGBA').resize((64, 64), Image.Resampling.LANCZOS)
                    self.assertEqual(pixels.tobytes(), expected.tobytes())
        finally:
            storm.dll.SFileCloseArchive(handle)

    def test_character_migration_round_trip(self):
        db = sqlite3.connect(':memory:')
        db.executescript('CREATE TABLE characters (guid INTEGER PRIMARY KEY,race,teamId,map,zone,position_x REAL,'
                         'position_y REAL,position_z REAL,orientation REAL,class,online,appearance TEXT);'
                         'CREATE TABLE character_skills (guid INTEGER,skill INTEGER,value INTEGER,max INTEGER);'
                         'CREATE TABLE character_homebind (guid INTEGER,mapId INTEGER,zoneId INTEGER,'
                         'posX REAL,posY REAL,posZ REAL);')
        root = r.WORK / 'migration'
        for line in (root / 'characters-before.tsv').read_text().splitlines():
            values = [float(v) if '.' in v else int(v) for v in line.split('\t')]
            db.execute('INSERT INTO characters VALUES (?,?,?,?,?,?,?,?,?,?,?,?)', [*values, 'preserve-exactly'])
        db.execute("INSERT INTO characters VALUES (999999,1,0,0,12,1,2,3,0,1,0,'unrelated')")
        for table, filename, marks in (('character_skills', 'languages-before.tsv', '?,?,?,?'),
                                        ('character_homebind', 'homebind-before.tsv', '?,?,?,?,?,?')):
            for line in (root / filename).read_text().splitlines():
                db.execute('INSERT INTO ' + table + ' VALUES (' + marks + ')', line.split('\t'))
        def snapshot():
            return {table: db.execute('SELECT * FROM ' + table + ' ORDER BY 1,2').fetchall()
                    for table in ('characters', 'character_skills', 'character_homebind')}
        before = snapshot()
        db.executescript(f.MIGRATION.read_text())
        self.assertEqual(db.execute('SELECT COUNT(*) FROM characters WHERE race IN (71,74)').fetchone()[0], 0)
        self.assertEqual(db.execute('SELECT appearance FROM characters WHERE guid=999999').fetchone()[0], 'unrelated')
        self.assertTrue(all(row[-1] == 'preserve-exactly' for row in snapshot()['characters'] if row[0] != 999999))
        db.executescript((root / 'rollback-characters.sql').read_text())
        self.assertEqual(snapshot(), before)

    def test_world_sql_matches_client_spells(self):
        text = r.MIGRATION.read_text()
        db = sqlite3.connect(':memory:')
        columns = {}
        for table, fields in re.findall(r'INSERT INTO `([^`]+)`\s*\(([^)]+)\)\s*VALUES', text):
            columns.setdefault(table, set()).update(re.findall(r'`([^`]+)`', fields))
        for table, fields in columns.items():
            db.execute('CREATE TABLE `' + table + '` (' + ','.join('`' + field + '`' for field in sorted(fields)) + ')')
        db.executescript('CREATE TABLE chrraces_dbc (ID INTEGER,Flags INTEGER);'
                         'INSERT INTO chrraces_dbc VALUES (71,14),(72,14),(73,14),(74,14);')
        db.executescript(text)
        db.executescript(text)
        table = self.table('Spell')
        by_id = {r.p._value(row, 0): row for row in table.records}
        names = r.d.spell_columns()
        for identifier in {spec[0] for spec in r.SPECS} | set(range(111000, 111004)):
            row = by_id[identifier]
            actual = db.execute('SELECT ' + ','.join('`' + name + '`' for name, _ in names)
                                + ' FROM spell_dbc WHERE ID=?', (identifier,)).fetchall()
            expected = []
            for i, (_, kind) in enumerate(names):
                value = r.p._value(row, i * 4)
                expected.append(r.p._string(table.strings, value).decode() if kind == 'string' else
                                float(r.d._sql_value(value, kind)) if kind == 'float' else
                                int(r.d._sql_value(value, kind)))
            self.assertEqual(actual, [tuple(expected)], identifier)


if __name__ == '__main__':
    unittest.main()
