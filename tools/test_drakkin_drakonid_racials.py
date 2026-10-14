"""Checks for the Drakkin and Drakonid racial spell spec against the repo's server Spell.dbc."""

from collections import Counter
from pathlib import Path

from cars_mount_pack import Wdbc
import drakkin_drakonid_racials as r

SQL = r.ROOT / "modules/mod-custom-server/data/sql/db-world/updates/u_custom_server_2026_10_14_00_drakkin_drakonid_racials.sql"
CPP = r.ROOT / "modules/mod-custom-server/src"


def table_bytes() -> bytes:
    return r.DEFAULT_SPELL_DBC.read_bytes()


def test_ids_are_unique_and_unused():
    ids = [spell.spell_id for spell in r.spell_spec()]
    assert not [i for i, n in Counter(ids).items() if n > 1]
    owners = {row[0]: row for row in Wdbc(table_bytes()).rows}
    index = r.field_index()["Name_Lang_enUS"]
    table = Wdbc(table_bytes())
    names = {spell.spell_id: spell.name for spell in r.spell_spec()}
    # an id may already be present only when it is one of these same spells
    assert not [i for i in ids if i in owners and table.text(owners[i][index]) != names[i]]


def test_grants_and_bindings_point_at_real_spells():
    ids = {spell.spell_id for spell in r.spell_spec()}
    for _, spells in r.RACIAL_GRANTS:
        assert {spell_id for spell_id, _ in spells} <= ids
    assert {spell_id for spell_id, _ in r.SCRIPT_BINDINGS} <= ids
    granted = {race: {spell_id for spell_id, _ in spells} for race, spells in r.RACIAL_GRANTS}
    assert granted[66] == granted[67] == set(r.DRAKKIN_RACIALS)
    assert granted[69] == granted[70] == set(r.DRAKONID_RACIALS)


def test_script_names_exist_in_cpp():
    source = "".join(path.read_text(encoding="utf-8") for path in CPP.glob("dra*_racials.cpp"))
    for _, name in r.SCRIPT_BINDINGS:
        assert f"class {name} " in source, name
        assert f"RegisterSpellScript({name})" in source, name


def test_spec_builds_and_merge_is_idempotent():
    data = table_bytes()
    prepared = r.prepare(Wdbc(data))
    assert len(prepared) == len(r.spell_spec())
    merged = r.merge_spell_table(data)
    assert len(Wdbc(merged).rows) == len(Wdbc(data).rows) + len(prepared) - sum(
        1 for row in Wdbc(data).rows if row[0] in {p.spell.spell_id for p in prepared})
    assert r.merge_spell_table(merged) == merged


def test_sql_is_current():
    assert SQL.read_text(encoding="utf-8") == r.render_sql(table_bytes()), "rerun --sql-out"


if __name__ == "__main__":
    for name, function in sorted(globals().items()):
        if name.startswith("test_"):
            function()
            print("PASS", name)
