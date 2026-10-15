"""Checks for the race racial spec against the repo's server Spell.dbc and C++ sources."""

import re
from collections import Counter

from cars_mount_pack import Wdbc
import drakkin_drakonid_racials as base
import race_racials as r

MODULE = base.ROOT / "modules/mod-custom-server"
SQL = MODULE / "data/sql/db-world/updates/u_custom_server_2026_10_14_01_race_racials.sql"
HEADER = MODULE / "src/race_racials_generated.h"
CPP = MODULE / "src/race_racials.cpp"


def table_bytes() -> bytes:
    return r.DEFAULT_SPELL_DBC.read_bytes()


def test_ids_are_unique_and_do_not_overlap_drakkin():
    ids = [spell.spell_id for spell in r.spell_spec()]
    assert not [i for i, n in Counter(ids).items() if n > 1]
    assert not set(ids) & {spell.spell_id for spell in base.spell_spec()}


def test_every_grant_and_binding_resolves():
    for race, keys in r.RACE_GRANTS.items():
        for key in keys:
            assert key in r.KEYS, (race, key)
    for key, _ in r.BINDINGS:
        assert key in r.KEYS, key


def test_script_names_exist_in_cpp():
    source = CPP.read_text(encoding="utf-8")
    for _, name in r.BINDINGS:
        assert re.search(rf"class {name}\b", source), name
        assert f"RegisterSpellScript({name})" in source, name


def test_cpp_only_uses_generated_spell_names():
    names = set(re.findall(r"SPELL_[A-Z0-9_]+", HEADER.read_text(encoding="utf-8")))
    used = set(re.findall(r"\bSPELL_[A-Z0-9_]+\b", CPP.read_text(encoding="utf-8")))
    stock = {name for name in used if name.startswith(("SPELL_FAILED_", "SPELL_AURA_", "SPELL_EFFECT_", "SPELL_SCHOOL_MASK_",
                                                        "SPELL_ATTR"))} | {"SPELL_CAST_OK", "SPELL_DIRECT_DAMAGE"}
    assert not used - names - stock


def test_spec_merges_idempotently():
    data = table_bytes()
    assert r.merge_spell_table(data) == data, "run race_racials.py --dbc-out on the module Spell.dbc"
    assert len(r.prepare(Wdbc(data))) == len(r.spell_spec())


def test_generated_files_are_current():
    assert SQL.read_text(encoding="utf-8") == r.render_sql(table_bytes()), "rerun --sql-out"
    assert HEADER.read_text(encoding="utf-8") == r.render_header(), "rerun --header-out"


BASE = base.ROOT / "data/sql/base/db_world"
LUA = base.ROOT / "modules/mod-worgoblin-high-elf/lua_scripts/transmog.lua"


def base_has(table: str, entry_id: int) -> bool:
    return re.search(rf"^\({entry_id},", (BASE / f"{table}.sql").read_text(encoding="utf-8"), re.M) is not None


def test_stock_world_data_the_deferred_racials_use_exists():
    for entry in (r.GO_MAILBOX, r.GO_ANVIL, r.GO_CAMPFIRE, r.GO_INVISIBLE_COOKING):
        assert base_has("gameobject_template", entry), entry
    assert base_has("item_template", r.ITEM_ALPACA_BAG)
    for tele, _, label in r.MOLE_DESTINATIONS:
        assert base_has("game_tele", tele), label
    assert base_has("game_tele", r.GAME_TELE_WORLD_TREE)
    assert len({tele for tele, _, _ in r.MOLE_DESTINATIONS}) == len(r.MOLE_DESTINATIONS)


def test_new_world_objects_are_free_and_created_by_the_sql():
    for table, entry in (("creature_template", r.CREATURE_HOLO_DECOY), ("gameobject_template", r.GO_INVISIBLE_ANVIL),
                         ("gameobject_template", r.GO_INVISIBLE_FORGE)):
        assert not base_has(table, entry), f"{table} {entry} is taken"
        assert f"({entry}," in r.WORLD_OBJECTS_SQL
    assert f"`creature_template_model` WHERE `CreatureID` = {r.CREATURE_HOLO_DECOY}" in r.WORLD_OBJECTS_SQL


def test_every_deferred_racial_is_wired():
    cpp = CPP.read_text(encoding="utf-8")
    lua = LUA.read_text(encoding="utf-8")
    markers = ("CANTRIPS", "SPATIAL_RIFT", "FORGE_OF_LIGHT", "EMBRACE_OF_THE_LOA", "MOLE_MACHINE", "DUNGEON_DELVER", "MASTERCRAFT",
               "HOLO", "MAKE_CAMP", "RETURN_TO_CAMP", "RUMMAGE_YOUR_BAG", "ALPACA_SADDLEBAGS", "INNER_PEACE", "VISAGE",
               "CHOSEN_IDENTITY", "INGEST_MINERALS", "QUIET_CONTEMPLATION", "ROOTWALKING", "WASTE_NOT_WANT_NOT", "EMBRACE_AKUNDA")
    for key in markers:
        assert f"SPELL_{key}" in cpp or key in {bound for bound, _ in r.BINDINGS}, key
    assert str(r.KEYS["ETHEREAL_CONNECTION"]) in lua, "transmog.lua must apply the Ethereal Connection discount"
    for key in r.LOA_EMBRACES + r.INGEST_BUFFS:
        assert key in r.KEYS
    for race in (r.NIGHTBORNE, r.VOIDELF, r.LIGHTFORGED, r.ZANDALARI, r.DARKIRON, r.MECHAGNOME, r.VULPERA, r.DRACTHYR,
                 r.EARTHEN_A, r.HARANIR_A):
        assert race in r.RACE_GRANTS


def test_loa_embraces_are_not_granted_directly():
    granted = {key for keys in r.RACE_GRANTS.values() for key in keys}
    assert not granted & set(r.LOA_EMBRACES), "Loa are learned through the menu"


if __name__ == "__main__":
    for name, function in sorted(globals().items()):
        if name.startswith("test_"):
            function()
            print("PASS", name)
