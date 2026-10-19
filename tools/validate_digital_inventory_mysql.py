"""Validate prepared inventory SQL and rollback in an explicitly isolated disposable MySQL container."""

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess

from test_digital_inventory_queries import ROOT, statements


def literal(value):
    if isinstance(value, int):
        return str(value)
    return "0x" + value.encode("utf-8").hex() if value else "''"


def main(container: str):
    if not container.startswith("esteria-inventory-db-"):
        raise ValueError("Use an isolated esteria-inventory-db-* validation container, never the live database")
    queries = statements()

    def run(sql, expect_failure=False):
        result = subprocess.run(["docker", "exec", "-i", container, "mysql", "-uroot", "--batch",
                                 "--skip-column-names"], input=sql, capture_output=True, text=True)
        if expect_failure:
            if result.returncode == 0 or "Duplicate entry" not in result.stderr:
                raise AssertionError("Expected an injected duplicate-key failure: " + result.stderr)
        elif result.returncode:
            raise RuntimeError(result.stderr)
        return result.stdout.strip()

    def query(name, *params):
        pieces = queries[name].split("?")
        if len(pieces) != len(params) + 1:
            raise ValueError("Parameter count: " + name)
        return "".join(p + literal(v) for p, v in zip(pieces, params)) + pieces[-1] + ";\n"

    prefix = "USE esteria_inventory_validation;\n"
    run("CREATE DATABASE esteria_inventory_validation;\n" + prefix + """
        CREATE TABLE characters (guid INT UNSIGNED PRIMARY KEY, money INT UNSIGNED, account INT, name TEXT);
        CREATE TABLE item_instance (guid INT UNSIGNED PRIMARY KEY, itemEntry INT UNSIGNED, owner_guid INT UNSIGNED,
            creatorGuid INT UNSIGNED, giftCreatorGuid INT UNSIGNED, count INT UNSIGNED, duration INT UNSIGNED,
            charges TEXT, flags INT UNSIGNED, enchantments TEXT, randomPropertyId INT, durability INT UNSIGNED,
            playedTime INT UNSIGNED, text TEXT) ENGINE=InnoDB;
        CREATE TABLE character_inventory (guid INT UNSIGNED, bag INT UNSIGNED, slot INT UNSIGNED,
            item INT UNSIGNED UNIQUE) ENGINE=InnoDB;
        CREATE TABLE mail_items (item_guid INT UNSIGNED);
        CREATE TABLE auctionhouse (itemguid INT UNSIGNED);
        CREATE TABLE guild_bank_item (item_guid INT UNSIGNED);
    """ + (ROOT / "data/sql/updates/pending_db_characters/rev_20261018030000000_digital_inventory.sql").read_text())
    names = [name for name in queries if "DIGITAL" in name] + [
        "CHAR_SEL_CHAR_INVENTORY_COUNT_ITEM", "CHAR_SEL_CHAR_INVENTORY_ITEM_BY_ENTRY",
        "CHAR_SEL_CHAR_INVENTORY_ITEM_BY_ENTRY_AND_OWNER", "CHAR_SEL_CHAR_INVENTORY_STACKS_BY_ENTRY_AND_OWNER",
        "CHAR_UPD_CHAR_INVENTORY_FACTION_CHANGE", "CHAR_REP_ITEM_INSTANCE", "CHAR_UPD_ITEM_INSTANCE",
        "CHAR_REP_INVENTORY_ITEM", "CHAR_UDP_CHAR_MONEY", "CHAR_DEL_CHAR_INVENTORY_BY_ITEM"]
    for name in names:
        run(prefix + "SET @source = " + literal(queries[name]) + "; PREPARE inventory_check FROM @source; "
            "DEALLOCATE PREPARE inventory_check;")
    item = (123, 7, 9, 10, 5, 0, "-1 0 0 0 0", 1, "123 0 0 456 0 0", -42, 17, 543, "Inscribed text", 41)
    run(prefix + "INSERT INTO characters VALUES (7,2000000,3,'Tester');\n"
        + query("CHAR_REP_ITEM_INSTANCE", *item) + query("CHAR_REP_INVENTORY_ITEM", 7, 0, 23, 41))
    deposit = query("CHAR_DEL_CHAR_INVENTORY_BY_ITEM", 41) + query("CHAR_REP_DIGITAL_ITEM", 7, 41, 1)
    run(prefix + "START TRANSACTION;\n" + deposit
        + "INSERT INTO character_digital_storage_item VALUES (8,41,0); COMMIT;", expect_failure=True)
    if run(prefix + "SELECT item FROM character_inventory;") != "41":
        raise AssertionError("Failed transfer did not preserve original physical ownership")
    if run(prefix + "SELECT COUNT(*) FROM character_digital_storage_item;") != "0":
        raise AssertionError("Failed transfer left a virtual mapping")
    run(prefix + "START TRANSACTION;\n" + deposit + query("CHAR_REP_DIGITAL_STORAGE", 7, 256, 2) + "COMMIT;")
    saved = run(prefix + query("CHAR_SEL_DIGITAL_ITEMS", 7)).split("\t")
    if saved[2] != "5" or saved[7:11] != ["-42", "17", "543", "Inscribed text"] or saved[11:] != ["41", "123", "1", "7", "0"]:
        raise AssertionError("Deposit changed instance metadata: " + repr(saved))
    run(prefix + query("CHAR_REP_INVENTORY_ITEM", 7, 0, 23, 41))
    if run(prefix + query("CHAR_SEL_DIGITAL_ITEMS", 7)).split("\t")[15] != "1":
        raise AssertionError("Duplicate location was not detected")
    run(prefix + query("CHAR_DEL_CHAR_INVENTORY_BY_ITEM", 41))
    run(prefix + "START TRANSACTION;\n" + query("CHAR_UDP_CHAR_MONEY", 1000000, 7)
        + query("CHAR_REP_DIGITAL_STORAGE", 7, 512, 3) + "ROLLBACK;")
    if run(prefix + "SELECT money FROM characters WHERE guid=7;") != "2000000":
        raise AssertionError("Rolled-back upgrade charged gold")
    if run(prefix + query("CHAR_SEL_DIGITAL_STORAGE", 7)) != "256\t2":
        raise AssertionError("Rolled-back upgrade changed capacity")
    run(prefix + query("CHAR_UPD_CHAR_INVENTORY_FACTION_CHANGE", 124, 123, 7))
    if run(prefix + "SELECT itemEntry FROM item_instance WHERE guid=41;") != "124":
        raise AssertionError("Faction conversion omitted digital item")
    run(prefix + "START TRANSACTION;\n" + query("CHAR_DEL_DIGITAL_ITEM", 7, 41)
        + query("CHAR_REP_INVENTORY_ITEM", 7, 0, 38, 41) + "COMMIT;")
    if run(prefix + "SELECT item,slot FROM character_inventory WHERE guid=7;") != "41\t38":
        raise AssertionError("Withdrawal did not preserve GUID and target slot")
    print(f"PASS: MySQL 8.4 prepared {len(names)} actual queries; migration, rollback, ownership, instance state, "
          "upgrade debit, conflict detection, faction conversion and withdrawal")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--container", required=True)
    main(parser.parse_args().container)
