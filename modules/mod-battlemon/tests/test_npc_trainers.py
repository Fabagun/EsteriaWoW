"""Check NPC roster assets, themes, SQL schema names and repeatable template installation."""
import csv
import json
import re
import sqlite3
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
DATA = json.loads((ROOT / 'data/npc-trainers.json').read_text(encoding='utf-8'))['trainers']
SQL = (REPO / 'data/sql/updates/pending_db_world/rev_1790969531700983800.sql').read_text(encoding='utf-8')


class NpcTrainerTests(unittest.TestCase):
    def test_all_models_have_one_template(self):
        appearances = json.loads((REPO / 'modules/mod-pokemon-trainer/data/gym-trainers/manifest.json')
                                 .read_text(encoding='utf-8'))['appearances']
        self.assertEqual({r['display'] for r in DATA}, {r['display'] for r in appearances})
        self.assertEqual(len(DATA), len({r['entry'] for r in DATA}))
        self.assertEqual(len(DATA), 21)

    def test_roster_species_have_usable_base_models(self):
        species = {int(r['id']): r for r in csv.DictReader(
            (ROOT / 'addon/Battlemon/Data/csv/species.csv').read_text(encoding='utf-8-sig').splitlines())}
        forms = list(csv.DictReader((ROOT / 'addon/Battlemon/Data/csv/forms.csv').read_text(encoding='utf-8-sig').splitlines()))
        displays = json.loads((ROOT / 'data/3d/catalog.json').read_text(encoding='utf-8'))['appearances']
        installed = {r['form'] for r in displays}
        for trainer in DATA:
            for identifier in trainer['species']:
                self.assertIn(identifier, species)
                candidates = [int(f['id']) for f in forms
                              if int(f['species_id']) == identifier and not f['variant']]
                self.assertTrue(candidates, (trainer['name'], identifier))
                self.assertIn(min(candidates), installed, (trainer['name'], identifier))
                if trainer['theme'] in ('WATER', 'FIGHTING'):
                    self.assertIn(trainer['theme'], [species[identifier]['type1'], species[identifier]['type2']])
            if trainer['random']:
                self.assertLessEqual(trainer['max_size'], len(set(trainer['species'])))
                self.assertEqual(len(trainer['species']), len(set(trainer['species'])))
                self.assertTrue(1 <= trainer['min_size'] <= trainer['max_size'] <= 6)

    def test_service_npcs_are_not_battle_trainers(self):
        by_role = {r['role']: r for r in DATA if r['role'] in ('guard', 'healer', 'teacher')}
        self.assertEqual(by_role['teacher']['entry'], 950117)
        self.assertEqual(by_role['healer']['entry'], 950104)
        self.assertEqual(by_role['guard']['entry'], 950116)
        self.assertTrue(all(not r['species'] for r in by_role.values()))

    def test_kanto_signature_teams(self):
        expected = {950100: [74, 95], 950101: [120, 121], 950115: [100, 25, 26],
                    950112: [109, 89, 109, 110], 950118: [64, 122, 49, 65],
                    950114: [87, 91, 80, 124, 131]}
        for row in DATA:
            if row['entry'] in expected:
                self.assertFalse(row['random'])
                self.assertEqual(row['species'], expected[row['entry']])

    def test_no_spawn_or_existing_center_changes(self):
        mutations = re.findall(r'(?:INSERT INTO|DELETE FROM|UPDATE)\s+`([^`]+)`', SQL)
        self.assertEqual(set(mutations), {'creature_template', 'creature_template_model', 'creature_model_info'})
        self.assertNotRegex(SQL, r'\b90050[01]\b|\b900511\b')

    def test_schema_and_idempotency(self):
        db = sqlite3.connect(':memory:')
        self.addCleanup(db.close)
        for table, keys in [('creature_template', 'entry'), ('creature_template_model', 'CreatureID,Idx'),
                            ('creature_model_info', 'DisplayID')]:
            ddl = (REPO / f'data/sql/base/db_world/{table}.sql').read_text(encoding='utf-8')
            block = ddl.split(f'CREATE TABLE `{table}` (', 1)[1].split(') ENGINE=', 1)[0]
            columns = re.findall(r'^  `([^`]+)`', block, re.M)
            db.execute(f'CREATE TABLE `{table}` (' + ','.join('`'+c+'`' for c in columns)
                       + f', PRIMARY KEY ({keys}))')
        db.execute("INSERT INTO creature_model_info (DisplayID, BoundingRadius, CombatReach) VALUES (950100, 0.5, 2)")
        db.execute("INSERT INTO creature_template (entry, name) VALUES (12345, 'Unrelated')")
        body = SQL.split('    START TRANSACTION;', 1)[1].split('    COMMIT;', 1)[0]
        db.executescript(body)
        snapshot = db.execute('SELECT entry,name,ScriptName,npcflag FROM creature_template ORDER BY entry').fetchall()
        db.executescript(body)
        self.assertEqual(snapshot, db.execute(
            'SELECT entry,name,ScriptName,npcflag FROM creature_template ORDER BY entry').fetchall())
        self.assertEqual(len(snapshot), 22)
        self.assertEqual(db.execute('SELECT COUNT(*) FROM creature_model_info').fetchone()[0], 21)
        self.assertEqual(db.execute('SELECT BoundingRadius, CombatReach FROM creature_model_info WHERE DisplayID=950100').fetchone(), (0.5, 2))
        self.assertEqual(db.execute('SELECT COUNT(*) FROM creature_template_model').fetchone()[0], 21)
        self.assertEqual(db.execute('SELECT ScriptName,npcflag FROM creature_template WHERE entry=950116')
                         .fetchone(), ('', 0))
        self.assertEqual(db.execute('SELECT ScriptName FROM creature_template WHERE entry=950117')
                         .fetchone()[0], 'pokemon_trainer_teacher')
        self.assertEqual(db.execute('SELECT ScriptName FROM creature_template WHERE entry=950104')
                         .fetchone()[0], 'pokemon_trainer_nurse')


if __name__ == '__main__':
    unittest.main()
