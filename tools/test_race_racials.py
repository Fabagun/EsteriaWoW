"""Checks for the race racial spec against the repo's server Spell.dbc and C++ sources."""

import re
from collections import Counter

from cars_mount_pack import Wdbc
import drakkin_drakonid_racials as base
import race_racial_visuals as v
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


def test_retail_visual_specs_point_at_real_racials_and_ids_are_disjoint():
    for key in v.RETAIL_VISUALS:
        assert key in r.KEYS and key in r.VISUAL_DONORS, key   # the stock donor stays as the fallback
    ids = [v.visual_id(key) for key in v.RETAIL_VISUALS]
    assert len(set(ids)) == len(ids) and min(ids) == v.VISUAL_BASE
    assert v.VISUAL_BASE > 30112 and v.KIT_BASE > 22076 and v.ATTACH_BASE > 6076 and v.EFFECT_BASE > 8676, "must clear the client maxima"


def test_event_slot_rules():
    assert v.slot_for(1, 1) == "precast" and v.slot_for(3, 1) == "cast" and v.slot_for(3, 3) == "impact"
    assert v.slot_for(7, 2) == "state" and v.slot_for(6, 2) == "impact" and v.slot_for(5, 1) == "caster_impact"
    assert v.slot_for(99, 1) is None


def _tables(tmp_path):
    def write(name, header, *rows):
        (tmp_path / f"{name}.csv").write_text(chr(10).join([header, *rows]) + chr(10), encoding="utf-8")
    write("SpellXSpellVisual", "ID,SpellVisualID,SpellID", "1,10,900")
    write("SpellVisual", "ID,StateKit", "10,7")
    write("SpellVisualEvent", "ID,StartEvent,TargetType,SpellVisualKitID,SpellVisualID", "1,3,1,8,10", "2,6,2,9,10")
    write("SpellVisualKitEffect", "ID,EffectType,Effect,ParentSpellVisualKitID", "1,2,100,7", "2,2,101,8", "3,5,102,9", "4,2,103,9")
    write("SpellVisualKitModelAttach", "ID,AttachmentID,SpellVisualEffectNameID,ParentSpellVisualKitID,Offset_0,Offset_1,Offset_2,Yaw,Pitch,Roll,Scale",
          "100,19,1,7,0,0,0,0,0,0,1", "101,22,2,8,0,0,0,0,0,0,2", "103,34,0,9,0,0,0,0,0,0,1")
    write("SpellVisualEffectName", "ID,ModelFileDataID,Scale", "1,5000,1", "2,5001,0.5")
    return v.Tables(tmp_path)


def test_trace_maps_events_to_slots_and_ignores_non_model_effects(tmp_path):
    found = v.trace(_tables(tmp_path), v.Retail(900))
    assert {slot: [a.model for a in items] for slot, items in found.items()} == {"state": [5000], "cast": [5001]}
    assert found["cast"][0].scale == 1.0 and found["cast"][0].attachment == 22   # attach scale 2 x effect name scale 0.5
    assert v.trace(_tables(tmp_path), v.Retail(900, remap={"cast": "state"}, skip=("state",))) == {}
    assert v.trace(_tables(tmp_path), v.Retail(901)) == {}


def test_built_rows_use_fresh_ids_and_keep_the_donor_cast_pose(tmp_path):
    key = next(iter(v.RETAIL_VISUALS))
    found = {key: v.trace(_tables(tmp_path), v.Retail(900))}
    built = v.build_rows(found, {5000: "Spells/Racials/a.mdx", 5001: "Spells/Racials/b.mdx"},
                         lambda k, slot: (1, 2) if slot == "precast" else None)
    visual, = built["rows"]["SpellVisual"]
    assert visual[0] == v.visual_id(key) and len(visual) == 32
    kits = {row[0]: row for row in built["rows"]["SpellVisualKit"]}
    assert all(len(row) == 38 for row in kits.values())
    assert visual[v.SLOTS["state"]] in kits and visual[v.SLOTS["cast"]] in kits
    assert kits[visual[v.SLOTS["precast"]]][1:3] == [1, 2], "anim-only kit keeps the stock cast pose"
    attaches = built["rows"]["SpellVisualKitModelAttach"]
    assert {row[1] for row in attaches} <= set(kits) and all(len(row) == 10 for row in attaches)
    assert built["effect_strings"] == {0: "Spells/Racials/a.mdx", 1: "Spells/Racials/b.mdx"}


def test_usable_drops_models_that_did_not_convert():
    a, b = v.Attach(1, 19, (0, 0, 0), 0, 0, 0, 1), v.Attach(2, 19, (0, 0, 0), 0, 0, 0, 1)
    assert v.usable({"X": {"cast": [a, b], "state": [b]}, "Y": {"cast": [b]}}, {1}) == {"X": {"cast": [a]}}


def test_ported_racials_take_the_new_visual_id_only_on_the_client():
    table = Wdbc(table_bytes())
    index = r.field_index()
    key = "ARCANE_PULSE"
    server = next(i for i in r.prepare(table) if i.spell.spell_id == r.KEYS[key])
    client = next(i for i in r.prepare(table, True, frozenset({key})) if i.spell.spell_id == r.KEYS[key])
    assert client.row[index["SpellVisualID_1"]] == v.visual_id(key) and client.row[index["SpellVisualID_2"]] == 0
    assert server.row[index["SpellVisualID_1"]] != v.visual_id(key)


def test_client_stage_never_writes_patch_z_and_keeps_archives_under_the_limit():
    import race_racials_update as u
    assert u.p.GLOBAL_ARCHIVE_REL not in u.ARCHIVES, "patch-Z is within ~67 MB of the 2 GiB read limit"
    assert u.ASSET_ARCHIVE_REL.name.lower() not in {"patch-z.mpq", "patch-r.mpq"} and u.MAX_ARCHIVE_BYTES < 2 * 1024 ** 3

if __name__ == "__main__":
    for name, function in sorted(globals().items()):
        if name.startswith("test_"):
            if "tmp_path" in function.__code__.co_varnames[:function.__code__.co_argcount]:
                import tempfile
                from pathlib import Path
                with tempfile.TemporaryDirectory() as folder:
                    function(Path(folder))
            else:
                function()
            print("PASS", name)
