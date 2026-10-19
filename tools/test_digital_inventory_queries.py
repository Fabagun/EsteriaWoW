"""Exercise the actual prepared ownership queries in an isolated SQLite transaction harness.

This verifies SQL semantics and rollback only; native compilation and MySQL/gameplay
acceptance remain separate. No connection to the live character database is made.
"""

from __future__ import annotations

import ast
from pathlib import Path
import re
import sqlite3
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/server/database/Database/Implementation/CharacterDatabase.cpp"


def statements() -> dict[str, str]:
    result = {}
    pattern = r'PrepareStatement\((CHAR_\w+),\s*((?:"(?:[^"\\]|\\.)*"\s*)+),\s*CONNECTION_\w+\);'
    for match in re.finditer(pattern, SOURCE.read_text(encoding="utf-8")):
        result[match[1]] = "".join(ast.literal_eval(part) for part in re.findall(r'"(?:[^"\\]|\\.)*"', match[2]))
    return result


class OwnershipQueries(unittest.TestCase):
    def setUp(self):
        self.sql = statements()
        self.db = sqlite3.connect(":memory:")
        self.db.executescript("""
            CREATE TABLE characters (guid INTEGER PRIMARY KEY, money INTEGER, account INTEGER, name TEXT);
            CREATE TABLE item_instance (guid INTEGER PRIMARY KEY, itemEntry INTEGER, owner_guid INTEGER,
                creatorGuid INTEGER, giftCreatorGuid INTEGER, count INTEGER, duration INTEGER, charges TEXT,
                flags INTEGER, enchantments TEXT, randomPropertyId INTEGER, durability INTEGER,
                playedTime INTEGER, text TEXT);
            CREATE TABLE character_inventory (guid INTEGER, bag INTEGER, slot INTEGER, item INTEGER UNIQUE);
            CREATE TABLE character_digital_storage (guid INTEGER PRIMARY KEY, capacity INTEGER, revision INTEGER);
            CREATE TABLE character_digital_storage_item (guid INTEGER, item INTEGER PRIMARY KEY, favorite INTEGER);
            CREATE TABLE mail_items (item_guid INTEGER);
            CREATE TABLE auctionhouse (itemguid INTEGER);
            CREATE TABLE guild_bank_item (item_guid INTEGER);
            INSERT INTO characters VALUES (7, 2000000, 3, 'Tester');
            INSERT INTO character_inventory VALUES (7, 0, 23, 41);
        """)
        self.item = (123, 7, 9, 10, 5, 0, "-1 0 0 0 0", 1, "123 0 0 456 0 0", -42, 17, 543, "Inscribed text", 41)
        self.execute("CHAR_REP_ITEM_INSTANCE", self.item)
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def execute(self, name, parameters=()):
        return self.db.execute(self.sql[name], parameters)

    def deposit(self):
        self.execute("CHAR_DEL_CHAR_INVENTORY_BY_ITEM", (41,))
        self.execute("CHAR_REP_DIGITAL_ITEM", (7, 41, 1))
        self.execute("CHAR_REP_DIGITAL_STORAGE", (7, 256, 2))

    def test_deposit_preserves_instance_and_has_one_location(self):
        before = self.db.execute("SELECT * FROM item_instance").fetchall()
        with self.db:
            self.deposit()
        self.assertEqual(self.db.execute("SELECT * FROM item_instance").fetchall(), before)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM character_inventory").fetchone()[0], 0)
        row = self.execute("CHAR_SEL_DIGITAL_ITEMS", (7,)).fetchone()
        self.assertEqual(row[0:11], (9, 10, 5, 0, "-1 0 0 0 0", 1, "123 0 0 456 0 0", -42, 17, 543, "Inscribed text"))
        self.assertEqual(row[11:], (41, 123, 1, 7, 0))

    def test_transfer_failure_restores_original_location(self):
        with self.assertRaises(sqlite3.IntegrityError):
            with self.db:
                self.deposit()
                self.db.execute("INSERT INTO character_digital_storage_item VALUES (8,41,0)")
        self.assertEqual(self.db.execute("SELECT item FROM character_inventory").fetchall(), [(41,)])
        self.assertEqual(self.db.execute("SELECT * FROM character_digital_storage_item").fetchall(), [])

    def test_withdraw_preserves_guid_and_moves_mapping_atomically(self):
        with self.db:
            self.deposit()
        with self.db:
            self.execute("CHAR_DEL_DIGITAL_ITEM", (7, 41))
            self.execute("CHAR_REP_INVENTORY_ITEM", (7, 0, 38, 41))
        self.assertEqual(self.db.execute("SELECT item,slot FROM character_inventory").fetchall(), [(41, 38)])
        self.assertEqual(self.execute("CHAR_SEL_DIGITAL_ITEMS", (7,)).fetchall(), [])
        self.assertEqual(self.db.execute("SELECT durability,text FROM item_instance").fetchone(), (17, "Inscribed text"))

    def test_every_competing_location_is_detected(self):
        with self.db:
            self.deposit()
        for table, column in (("character_inventory", "item"), ("mail_items", "item_guid"),
                              ("auctionhouse", "itemguid"), ("guild_bank_item", "item_guid")):
            with self.subTest(location=table):
                self.db.execute(f"INSERT INTO {table} ({column}) VALUES (41)")
                self.assertEqual(self.execute("CHAR_SEL_DIGITAL_ITEMS", (7,)).fetchone()[15], 1)
                self.db.rollback()

    def test_missing_instance_and_wrong_owner_remain_visible_to_recovery(self):
        with self.db:
            self.deposit()
        self.db.execute("UPDATE item_instance SET owner_guid=8 WHERE guid=41")
        self.assertEqual(self.execute("CHAR_SEL_DIGITAL_ITEMS", (7,)).fetchone()[14], 8)
        self.db.execute("DELETE FROM item_instance WHERE guid=41")
        row = self.execute("CHAR_SEL_DIGITAL_ITEMS", (7,)).fetchone()
        self.assertEqual(row[11], 41)
        self.assertIsNone(row[14])

    def test_other_character_cannot_delete_mapping(self):
        with self.db:
            self.deposit()
        self.execute("CHAR_DEL_DIGITAL_ITEM", (8, 41))
        self.assertEqual(len(self.execute("CHAR_SEL_DIGITAL_ITEMS", (7,)).fetchall()), 1)

    def test_upgrade_debit_and_capacity_rollback_together(self):
        with self.db:
            self.deposit()
        with self.assertRaises(RuntimeError):
            with self.db:
                self.execute("CHAR_UDP_CHAR_MONEY", (1000000, 7))
                self.execute("CHAR_REP_DIGITAL_STORAGE", (7, 512, 3))
                raise RuntimeError("injected transaction failure")
        self.assertEqual(self.db.execute("SELECT money FROM characters").fetchone()[0], 2000000)
        self.assertEqual(self.execute("CHAR_SEL_DIGITAL_STORAGE", (7,)).fetchone(), (256, 2))

    def test_gm_queries_find_digital_stacks(self):
        with self.db:
            self.deposit()
        self.assertEqual(self.execute("CHAR_SEL_CHAR_INVENTORY_COUNT_ITEM", (123,)).fetchone()[0], 1)
        self.assertEqual(self.execute("CHAR_SEL_CHAR_INVENTORY_ITEM_BY_ENTRY_AND_OWNER", (123, 7)).fetchall(), [(41,)])
        self.assertEqual(self.execute("CHAR_SEL_CHAR_INVENTORY_STACKS_BY_ENTRY_AND_OWNER", (123, 7)).fetchall(), [(41, 5)])

    def test_item_and_character_cleanup_remove_only_their_mappings(self):
        with self.db:
            self.deposit()
        self.db.execute("INSERT INTO character_digital_storage_item VALUES (8,42,0)")
        self.execute("CHAR_DEL_DIGITAL_ITEM_BY_GUID", (41,))
        self.assertEqual(self.db.execute("SELECT item FROM character_digital_storage_item").fetchall(), [(42,)])
        self.execute("CHAR_DEL_DIGITAL_ITEMS_OWNER", (7,))
        self.execute("CHAR_DEL_DIGITAL_STORAGE_OWNER", (7,))
        self.assertEqual(self.db.execute("SELECT item FROM character_digital_storage_item").fetchall(), [(42,)])


if __name__ == "__main__":
    unittest.main()
