"""Racial spells for Drakkin (races 66/67) and Drakonid (races 69/70).

One spec drives both halves, the same way the Darkfallen pack does it:

* ``merge_spell_table`` clones donor rows into the client Spell.dbc.
* ``render_sql`` emits the matching world-DB ``spell_dbc`` rows, ``spell_proc`` and
  ``spell_script_names`` bindings for modules/mod-custom-server/src/drakkin_racials.cpp
  and drakonid_racials.cpp.

Every row is cloned from a stock donor, so only the fields named in the spec differ
from a spell the client already understands. Columns are addressed by their
``spell_dbc`` name, which keeps the spec readable and ties it to the world schema.

    python tools/drakkin_drakonid_racials.py --sql-out <file.sql>
    python tools/drakkin_drakonid_racials.py --dbc-in Spell.dbc --dbc-out patched/Spell.dbc

Both spell sets are always added together: the two race packs each ship a whole
Spell.dbc, so a pack that carried only its own spells would erase the other's.
"""

from __future__ import annotations

import argparse
import re
import struct
from dataclasses import dataclass, field
from pathlib import Path

from cars_mount_pack import Wdbc, build_wdbc

ROOT = Path(__file__).resolve().parents[1]
SPELL_DBC_DDL = ROOT / "data" / "sql" / "base" / "db_world" / "spell_dbc.sql"
DEFAULT_SPELL_DBC = ROOT / "modules" / "mod-custom-server" / "data" / "dbc" / "retroported-races" / "Spell.dbc"

DRAKKIN_RACES = (66, 67)
DRAKONID_RACES = (69, 70)

# --- spell ids -----------------------------------------------------------------
# 110040-110044 belong to Darkfallen, 110100-110103 to the Mag'har racials, 13990001-5 to Arakkoa.
CHROMATIC_ANCESTRY = 110300
RUBY_BLOOD, AZURE_BLOOD, EMERALD_BLOOD, BRONZE_BLOOD = 110301, 110302, 110303, 110304
OBSIDIAN_BLOOD, TWILIGHT_BLOOD, INFINITE_BLOOD, FROSTBROOD_BLOOD = 110305, 110306, 110307, 110308
BLOODS = (RUBY_BLOOD, AZURE_BLOOD, EMERALD_BLOOD, BRONZE_BLOOD,
          OBSIDIAN_BLOOD, TWILIGHT_BLOOD, INFINITE_BLOOD, FROSTBROOD_BLOOD)
LESSER_DRAGONBREATH = 110309
DRACONIC_EXPOSURE = 110310
BREATH_FIRE, BREATH_ARCANE, BREATH_NATURE, BREATH_SHADOW, BREATH_FROST = 110311, 110312, 110313, 110314, 110315
BREATHS = (BREATH_FIRE, BREATH_ARCANE, BREATH_NATURE, BREATH_SHADOW, BREATH_FROST)
TOGETHER_STRONG = 110316
TOGETHER_STRONG_AURA = 110317
ANCIENT_BROODBLOOD = 110318
ANCIENT_BROODBLOOD_AURA = 110319

DRACONIC_CHARGE = 110400
CHARGE_IMPACT = 110401
CHARGE_STUN = 110402
CHARGE_STOMP = 110403
DRACONIC_HIDE = 110404
DRAGONKIN = 110405
TREASURE_HOARDER = 110406

DRAKKIN_RACIALS = (CHROMATIC_ANCESTRY,) + BLOODS + (LESSER_DRAGONBREATH, TOGETHER_STRONG, ANCIENT_BROODBLOOD)
DRAKONID_RACIALS = (DRACONIC_CHARGE, DRACONIC_HIDE, DRAGONKIN, TREASURE_HOARDER)

# --- constants -------------------------------------------------------------------
APPLY_AURA, SCHOOL_DAMAGE, DUMMY = 6, 2, 3
SELF, TARGET_ENEMY, SRC_CASTER, CONE_ENEMY = 1, 6, 22, 104
# An area spell centred on the caster needs both: SRC_CASTER for the origin and AREA_ENEMY as the
# filter. With the origin alone it hits friendlies and the caster too.
AREA_ENEMY = 15

ATTR_IS_ABILITY = 0x00000010
ATTR_PASSIVE = 0x00000040
ATTR_DO_NOT_DISPLAY = 0x00000080
ATTR_AURA_IS_DEBUFF = 0x04000000
ATTR_NOT_IN_COMBAT = 0x10000000
ATTR3_DEATH_PERSISTENT = 0x00100000
PROC_TAKEN_DAMAGE = 0x00100000

# DBC lookup rows (SpellCastTimes, SpellDuration, SpellRange, SpellRadius).
CAST_3_SEC = 14
DURATION_4_SEC, DURATION_6_SEC, DURATION_8_SEC, DURATION_INFINITE = 35, 32, 31, 21
RADIUS_8_YD, RADIUS_15_YD = 14, 18
GCD_CATEGORY, GCD_MS = 133, 1500
SCHOOL_PHYSICAL, SCHOOL_FIRE, SCHOOL_NATURE, SCHOOL_FROST, SCHOOL_SHADOW, SCHOOL_ARCANE = 1, 4, 8, 16, 32, 64
ALL_MAGIC_SCHOOLS = 126

AURA_DUMMY = 4
AURA_MOD_RESISTANCE = 22
AURA_MOD_INCREASE_SPEED = 31
AURA_MOD_DECREASE_SPEED = 33
AURA_MOD_STUN = 12
AURA_MOD_DODGE_PERCENT = 49
AURA_MOD_DAMAGE_PERCENT_DONE = 79
AURA_MOD_PERCENT_STAT = 80
AURA_MOD_DAMAGE_PERCENT_TAKEN = 87
AURA_MOD_RESISTANCE_PCT = 101
AURA_MOD_HEALING_PCT = 118
AURA_MOD_INCREASE_ENERGY_PERCENT = 132
AURA_MOD_MANA_REGEN_INTERRUPT = 134
AURA_MOD_HEALING_DONE_PERCENT = 136
AURA_MOD_MELEE_HASTE = 138
AURA_MOD_RANGED_HASTE = 140
AURA_MOD_BASE_RESISTANCE_PCT = 142
AURA_MOD_DAMAGE_DONE_VERSUS = 168
AURA_MOD_ATTACKER_MELEE_CRIT_DAMAGE = 203
AURA_HASTE_SPELLS = 216
AURA_PERIODIC_DUMMY = 226
AURA_MECHANIC_DURATION_MOD = 232
AURA_PROC_TRIGGER_SPELL = 42

STAT_STAMINA = 2
MECHANIC_SNARE, MECHANIC_STUN = 11, 12
CREATURE_TYPE_DRAGONKIN_MASK = 1 << (2 - 1)

PASSIVE_DONOR = 20550  # Endurance: instant passive aura, no visuals, no class flags

# Stock spells whose icon each racial borrows.
ICONS = {
    CHROMATIC_ANCESTRY: 31661, RUBY_BLOOD: 133, AZURE_BLOOD: 5143, EMERALD_BLOOD: 5185,
    BRONZE_BLOOD: 12043, OBSIDIAN_BLOOD: 8071, TWILIGHT_BLOOD: 686, INFINITE_BLOOD: 1953,
    FROSTBROOD_BLOOD: 168, LESSER_DRAGONBREATH: 31661, DRACONIC_EXPOSURE: 31661,
    TOGETHER_STRONG: 1243, TOGETHER_STRONG_AURA: 1243, ANCIENT_BROODBLOOD: 12975, ANCIENT_BROODBLOOD_AURA: 12975,
    DRACONIC_CHARGE: 100, CHARGE_IMPACT: 100, CHARGE_STUN: 100, CHARGE_STOMP: 6343,
    DRACONIC_HIDE: 12299, DRAGONKIN: 22888, TREASURE_HOARDER: 921,
    **{breath_id: 31661 for breath_id in BREATHS},
}
# Cast visuals: Dragon's Breath for the breath, Thunder Clap for the stomp (the stock stomp animation).
VISUALS = {LESSER_DRAGONBREATH: 31661, CHARGE_STOMP: 6343}


@dataclass(frozen=True)
class Spell:
    spell_id: int
    name: str
    fields: dict[str, int | float]
    subtext: str = ""
    description: str = ""
    aura_description: str = ""
    donor: int = PASSIVE_DONOR


def effect(slot: int, aura: int, points: int, misc: int = 0, target: int = SELF, **extra) -> dict[str, int]:
    """One APPLY_AURA effect; ``points`` is the shown value (die sides 1 add 1 to base points)."""
    return {f"Effect_{slot}": APPLY_AURA, f"EffectDieSides_{slot}": 1, f"EffectBasePoints_{slot}": points - 1,
            f"ImplicitTargetA_{slot}": target, f"EffectAura_{slot}": aura, f"EffectMiscValue_{slot}": misc,
            **{f"{key}_{slot}": value for key, value in extra.items()}}


def merge(*parts: dict) -> dict:
    result: dict = {}
    for part in parts:
        result.update(part)
    return result


PASSIVE = {"Attributes": ATTR_IS_ABILITY | ATTR_PASSIVE}
# A selectable Blood: out of combat only, survives death, and stays until swapped or cancelled.
BLOOD = {"Attributes": ATTR_IS_ABILITY | ATTR_NOT_IN_COMBAT, "AttributesEx3": ATTR3_DEATH_PERSISTENT,
         "CastingTimeIndex": CAST_3_SEC, "DurationIndex": DURATION_INFINITE, "RangeIndex": 1}
DEBUFF = {"Attributes": ATTR_IS_ABILITY | ATTR_AURA_IS_DEBUFF, "RangeIndex": 4}


def blood(spell_id: int, name: str, description: str, aura_description: str, *effects: dict) -> Spell:
    return Spell(spell_id, name, merge(BLOOD, *effects), "Chromatic Ancestry", description, aura_description)


def breath_damage(spell_id: int, school: int) -> Spell:
    return Spell(spell_id, "Lesser Dragonbreath", {
        "Attributes": ATTR_IS_ABILITY | ATTR_DO_NOT_DISPLAY, "RangeIndex": 4, "SchoolMask": school,
        "DefenseType": 1, "Effect_1": SCHOOL_DAMAGE, "EffectDieSides_1": 1, "EffectBasePoints_1": 0, "EffectAura_1": 0,
        "ImplicitTargetA_1": TARGET_ENEMY, "EffectBonusMultiplier_1": 0.0})


def spell_spec() -> tuple[Spell, ...]:
    return (
        Spell(CHROMATIC_ANCESTRY, "Chromatic Ancestry",
              merge(PASSIVE, effect(1, AURA_DUMMY, 1)), "Racial Passive",
              "Every Drakkin carries the blood of an ancient draconic lineage. Choose a Blood while out "
              "of combat; only one can be active at a time, and it also sets the school of your Lesser Dragonbreath."),
        blood(RUBY_BLOOD, "Ruby Blood",
              "Your physical damage is increased by 2%. Lesser Dragonbreath deals Fire damage.",
              "Physical damage increased by 2%.",
              effect(1, AURA_MOD_DAMAGE_PERCENT_DONE, 2, SCHOOL_PHYSICAL)),
        blood(AZURE_BLOOD, "Azure Blood",
              "Your maximum mana is increased by 4% and mana regeneration while casting by 5%. "
              "Lesser Dragonbreath deals Arcane damage.",
              "Maximum mana increased by 4%; mana regeneration while casting increased by 5%.",
              effect(1, AURA_MOD_INCREASE_ENERGY_PERCENT, 4, 0), effect(2, AURA_MOD_MANA_REGEN_INTERRUPT, 5)),
        blood(EMERALD_BLOOD, "Emerald Blood",
              "Your healing done is increased by 3% and healing received by 2%. "
              "Lesser Dragonbreath deals Nature damage.",
              "Healing done increased by 3%; healing received increased by 2%.",
              effect(1, AURA_MOD_HEALING_DONE_PERCENT, 3, 127), effect(2, AURA_MOD_HEALING_PCT, 2, 127)),
        blood(BRONZE_BLOOD, "Bronze Blood",
              "Your melee, ranged and spell haste are increased by 2%. Lesser Dragonbreath deals Arcane damage.",
              "Haste increased by 2%.",
              effect(1, AURA_MOD_MELEE_HASTE, 2), effect(2, AURA_MOD_RANGED_HASTE, 2), effect(3, AURA_HASTE_SPELLS, 2)),
        blood(OBSIDIAN_BLOOD, "Obsidian Blood",
              "Your armor is increased by 2%, physical damage taken is reduced by 2% and melee critical strike "
              "damage taken by 5%. Lesser Dragonbreath deals Fire damage.",
              "Armor increased by 2%; physical damage taken reduced by 2%; melee critical damage taken reduced by 5%.",
              effect(1, AURA_MOD_BASE_RESISTANCE_PCT, 2, SCHOOL_PHYSICAL),
              effect(2, AURA_MOD_DAMAGE_PERCENT_TAKEN, -2, SCHOOL_PHYSICAL),
              effect(3, AURA_MOD_ATTACKER_MELEE_CRIT_DAMAGE, -5)),
        blood(TWILIGHT_BLOOD, "Twilight Blood",
              "Your spell damage is increased by 2%. Lesser Dragonbreath deals Shadow damage.",
              "Spell damage increased by 2%.",
              effect(1, AURA_MOD_DAMAGE_PERCENT_DONE, 2, ALL_MAGIC_SCHOOLS)),
        blood(INFINITE_BLOOD, "Infinite Blood",
              "Your movement speed is increased by 2% and dodge chance by 1%. Lesser Dragonbreath deals Arcane damage.",
              "Movement speed increased by 2%; dodge chance increased by 1%.",
              effect(1, AURA_MOD_INCREASE_SPEED, 2), effect(2, AURA_MOD_DODGE_PERCENT, 1)),
        blood(FROSTBROOD_BLOOD, "Frostbrood Blood",
              "The duration of snares on you is reduced by 15% and your Frost resistance is increased by 30. "
              "Lesser Dragonbreath deals Frost damage.",
              "Snare duration reduced by 15%; Frost resistance increased by 30.",
              effect(1, AURA_MECHANIC_DURATION_MOD, -15, MECHANIC_SNARE), effect(2, AURA_MOD_RESISTANCE, 30, SCHOOL_FROST)),
        Spell(LESSER_DRAGONBREATH, "Lesser Dragonbreath", {
            "Attributes": ATTR_IS_ABILITY, "RecoveryTime": 120000, "RangeIndex": 1,
            "StartRecoveryCategory": GCD_CATEGORY, "StartRecoveryTime": GCD_MS,
            "Effect_1": DUMMY, "EffectDieSides_1": 1, "EffectBasePoints_1": 0, "EffectAura_1": 0,
            "ImplicitTargetA_1": CONE_ENEMY,
            "EffectRadiusIndex_1": RADIUS_15_YD}, "Racial",
              "Exhale draconic energy in a cone, dealing damage in the school of your active Blood and exposing "
              "enemies for 6 sec, reducing their armor by 5% and their magic resistances by 20.",
              donor=PASSIVE_DONOR),
        Spell(DRACONIC_EXPOSURE, "Draconic Exposure", merge(
            DEBUFF, {"DurationIndex": DURATION_6_SEC},
            effect(1, AURA_MOD_RESISTANCE_PCT, -5, SCHOOL_PHYSICAL, TARGET_ENEMY),
            effect(2, AURA_MOD_RESISTANCE, -20, ALL_MAGIC_SCHOOLS, TARGET_ENEMY)), "",
              aura_description="Armor reduced by 5% and magic resistances reduced by 20."),
        *(breath_damage(spell_id, school) for spell_id, school in zip(
            BREATHS, (SCHOOL_FIRE, SCHOOL_ARCANE, SCHOOL_NATURE, SCHOOL_SHADOW, SCHOOL_FROST))),
        Spell(TOGETHER_STRONG, "Drakkin Together Strong", merge(
            PASSIVE, effect(1, AURA_PERIODIC_DUMMY, 1, EffectAuraPeriod=2000)), "Racial Passive",
              "Party members within 30 yards gain 1% Stamina for each other Drakkin in your party, up to 4%."),
        Spell(TOGETHER_STRONG_AURA, "Drakkin Together Strong", merge(
            {"Attributes": ATTR_IS_ABILITY, "DurationIndex": DURATION_4_SEC},
            effect(1, AURA_MOD_PERCENT_STAT, 1, STAT_STAMINA)),
              aura_description="Stamina increased by the Drakkin around you."),
        Spell(ANCIENT_BROODBLOOD, "Ancient Broodblood", merge(
            PASSIVE, {"ProcTypeMask": PROC_TAKEN_DAMAGE, "ProcChance": 101}, effect(1, AURA_PROC_TRIGGER_SPELL, 1)),
              "Racial Passive",
              "When struck below 30% health, your draconic instincts awaken, increasing movement speed and healing "
              "received by 10% for 8 sec. Can occur once every 60 sec."),
        Spell(ANCIENT_BROODBLOOD_AURA, "Ancient Broodblood", merge(
            {"Attributes": ATTR_IS_ABILITY, "DurationIndex": DURATION_8_SEC},
            effect(1, AURA_MOD_INCREASE_SPEED, 10), effect(2, AURA_MOD_HEALING_PCT, 10, 127)),
              aura_description="Movement speed and healing received increased by 10%."),

        Spell(DRACONIC_CHARGE, "Draconic Charge", {
            "Attributes": ATTR_IS_ABILITY, "RecoveryTime": 120000, "RangeIndex": 1,
            "StartRecoveryCategory": GCD_CATEGORY, "StartRecoveryTime": GCD_MS,
            "Effect_1": DUMMY, "EffectDieSides_1": 1, "EffectBasePoints_1": 0, "EffectAura_1": 0,
            "ImplicitTargetA_1": SELF}, "Racial",
              "Charge forward, knocking enemies aside and stunning the first enemy struck for 1 sec. "
              "On landing you slam the ground, damaging enemies within 8 yards and slowing them by 50% for 4 sec."),
        Spell(CHARGE_IMPACT, "Draconic Charge", {
            "Attributes": ATTR_IS_ABILITY | ATTR_DO_NOT_DISPLAY, "RangeIndex": 4, "SchoolMask": SCHOOL_PHYSICAL,
            "DefenseType": 2, "Effect_1": SCHOOL_DAMAGE, "EffectDieSides_1": 1, "EffectBasePoints_1": 0, "EffectAura_1": 0,
            "ImplicitTargetA_1": TARGET_ENEMY, "EffectBonusMultiplier_1": 0.0}),
        Spell(CHARGE_STUN, "Draconic Charge", merge(
            DEBUFF, {"DurationIndex": 36, "Mechanic": MECHANIC_STUN},
            effect(1, AURA_MOD_STUN, 1, 0, TARGET_ENEMY, EffectMechanic=MECHANIC_STUN)),
              aura_description="Stunned."),
        Spell(CHARGE_STOMP, "Draconic Stomp", merge(
            {"Attributes": ATTR_IS_ABILITY | ATTR_DO_NOT_DISPLAY, "RangeIndex": 1, "SchoolMask": SCHOOL_PHYSICAL,
             "DefenseType": 2, "DurationIndex": DURATION_4_SEC,
             "Effect_1": SCHOOL_DAMAGE, "EffectDieSides_1": 1, "EffectBasePoints_1": 0, "EffectAura_1": 0,
             "ImplicitTargetA_1": SRC_CASTER, "ImplicitTargetB_1": AREA_ENEMY, "EffectRadiusIndex_1": RADIUS_8_YD, "EffectBonusMultiplier_1": 0.0},
            effect(2, AURA_MOD_DECREASE_SPEED, -50, 0, SRC_CASTER, EffectRadiusIndex=RADIUS_8_YD, ImplicitTargetB=AREA_ENEMY)),
              aura_description="Movement speed reduced by 50%."),
        Spell(DRACONIC_HIDE, "Draconic Hide", merge(
            PASSIVE, effect(1, AURA_MOD_BASE_RESISTANCE_PCT, 3, SCHOOL_PHYSICAL),
            effect(2, AURA_MOD_DAMAGE_PERCENT_TAKEN, -2, SCHOOL_PHYSICAL)), "Racial Passive",
              "Increases armor from items by 3% and reduces physical damage taken by 2%."),
        Spell(DRAGONKIN, "Dragonkin", merge(
            PASSIVE, effect(1, AURA_MOD_DAMAGE_DONE_VERSUS, 3, CREATURE_TYPE_DRAGONKIN_MASK)), "Racial Passive",
              "Increases damage dealt to Dragonkin by 3%."),
        Spell(TREASURE_HOARDER, "Treasure Hoarder", merge(PASSIVE, effect(1, AURA_DUMMY, 1)), "Racial Passive",
              "Increases gold found on creatures by 5%."),
    )


# --- script and proc bindings ----------------------------------------------------
SCRIPT_BINDINGS: tuple[tuple[int, str], ...] = (
    *((blood_id, "spell_drakkin_chromatic_blood") for blood_id in BLOODS),
    (LESSER_DRAGONBREATH, "spell_drakkin_lesser_dragonbreath"),
    *((breath_id, "spell_drakkin_breath_damage") for breath_id in BREATHS),
    (TOGETHER_STRONG, "spell_drakkin_together_strong"),
    (ANCIENT_BROODBLOOD, "spell_drakkin_ancient_broodblood"),
    (DRACONIC_CHARGE, "spell_drakonid_draconic_charge"),
    (CHARGE_IMPACT, "spell_drakonid_charge_damage"),
    (CHARGE_STOMP, "spell_drakonid_charge_damage"),
)
BROODBLOOD_INTERNAL_COOLDOWN_MS = 60000

RACIAL_GRANTS: tuple[tuple[int, tuple[tuple[int, str], ...]], ...] = tuple(
    (race, tuple((spell.spell_id, spell.name) for spell in spell_spec() if spell.spell_id in ids))
    for races, ids in ((DRAKKIN_RACES, DRAKKIN_RACIALS), (DRAKONID_RACES, DRAKONID_RACIALS)) for race in races)


# Racials of the donor race that the legacy race-mask rows would otherwise hand to these races.
HUMAN_RACIALS = ((20597, "Sword Specialization"), (20598, "The Human Spirit"), (20599, "Diplomacy"),
                 (20600, "Perception"), (58985, "Perception"), (20864, "Mace Specialization"), (59752, "Every Man for Himself"))
ORC_RACIALS = ((20572, "Blood Fury"), (20573, "Hardiness"), (20574, "Axe Specialization"), (20575, "Command"),
               (20576, "Command"), (21563, "Command"), (33697, "Blood Fury"), (33702, "Blood Fury"),
               (54562, "Command"), (65222, "Command"))
DONOR_RACIALS = {66: HUMAN_RACIALS, 67: ORC_RACIALS, 69: HUMAN_RACIALS, 70: ORC_RACIALS}
# The racial skill lines re-teach those spells at every login through their SkillLineAbility rows,
# so the skill itself has to be withheld as well.
DONOR_RACIAL_SKILLS = {66: (754, "Human Racial"), 67: (125, "Orc Racial"), 69: (754, "Human Racial"), 70: (125, "Orc Racial")}


def racial_exclusion_sql(race: int) -> str:
    """``custom_race_start_spell_exclude`` rows that keep the donor race's racials off this race."""
    donor = DONOR_RACIALS[race]
    label = "Human" if donor is HUMAN_RACIALS else "Orc"
    ids = ", ".join(str(spell_id) for spell_id, _ in donor)
    rows = ",\n".join(f"(@RACE, {spell_id}, '{label} {name}')" for spell_id, name in donor)
    skill, skill_name = DONOR_RACIAL_SKILLS[race]
    return (f"DELETE FROM `custom_race_start_spell_exclude` WHERE `race` = @RACE AND `spell` IN ({ids});\n"
            "INSERT INTO `custom_race_start_spell_exclude` (`race`, `spell`, `comment`) VALUES\n" + rows + ";\n"
            f"DELETE FROM `custom_race_start_skill_exclude` WHERE `race` = @RACE AND `skill` = {skill};\n"
            "INSERT INTO `custom_race_start_skill_exclude` (`race`, `skill`, `comment`) VALUES\n"
            f"(@RACE, {skill}, '{skill_name}');\n")


def racial_grant_sql(race: int) -> str:
    """The racial rows a race pack appends to its own migration: donor exclusions, then grants."""
    spells = dict(RACIAL_GRANTS)[race]
    rows = ",\n".join("(@RACE, 0, {}, '{}')".format(spell_id, f"Racial: {name}".replace("'", "''"))
                      for spell_id, name in spells)
    ids = ", ".join(str(spell_id) for spell_id, _ in spells)
    return (racial_exclusion_sql(race)
            + f"DELETE FROM `custom_race_start_spell` WHERE `race` = @RACE AND `spell` IN ({ids});\n"
            "INSERT INTO `custom_race_start_spell` (`race`, `classMask`, `spell`, `comment`) VALUES\n"
            + rows + ";\n")


# --- Spell.dbc plumbing --------------------------------------------------------
SPELL_FIELD_COUNT = 234


def spell_columns() -> tuple[tuple[str, str], ...]:
    """(column, kind) pairs in Spell.dbc field order, read from the world schema."""
    schema = SPELL_DBC_DDL.read_text(encoding="utf-8")
    start = schema.index("CREATE TABLE `spell_dbc` (")
    end = schema.index(") ENGINE=", start)
    columns = []
    for name, type_text in re.findall(r"\n\s*`([^`]+)`\s+([^\n,]+),", schema[start:end]):
        kind = ("float" if type_text.startswith("float") else "string" if "char" in type_text
                else "unsigned" if "unsigned" in type_text else "signed")
        columns.append((name, kind))
    if len(columns) != SPELL_FIELD_COUNT:
        raise ValueError(f"unexpected spell_dbc column count: {len(columns)}")
    return tuple(columns)


def field_index() -> dict[str, int]:
    return {name: index for index, (name, _) in enumerate(spell_columns())}


def _pack(value: int | float, kind: str) -> int:
    if isinstance(value, float) or kind == "float":
        return struct.unpack("<I", struct.pack("<f", float(value)))[0]
    return value & 0xFFFFFFFF


@dataclass
class Prepared:
    spell: Spell
    row: list[int]
    icon: int = 0
    notes: list[str] = field(default_factory=list)


def prepare(table: Wdbc) -> list[Prepared]:
    """Clone donor rows and apply the spec; the table is only read."""
    index, columns = field_index(), spell_columns()
    rows = {row[0]: row for row in table.rows}

    def donor(spell_id: int) -> list[int]:
        if spell_id not in rows:
            raise ValueError(f"Spell.dbc donor {spell_id} is missing")
        return list(rows[spell_id])

    prepared = []
    for spell in spell_spec():
        row = donor(spell.donor)
        row[0] = spell.spell_id
        for name, value in spell.fields.items():
            if name not in index:
                raise ValueError(f"{spell.name}: unknown spell_dbc column {name}")
            row[index[name]] = _pack(value, columns[index[name]][1])
        row[index["SpellIconID"]] = donor(ICONS[spell.spell_id])[index["SpellIconID"]]
        if spell.spell_id in VISUALS:
            row[index["SpellVisualID_1"]] = donor(VISUALS[spell.spell_id])[index["SpellVisualID_1"]]
        for name in ("Name_Lang_enUS", "NameSubtext_Lang_enUS", "Description_Lang_enUS", "AuraDescription_Lang_enUS"):
            row[index[name]] = 0
        prepared.append(Prepared(spell, row))
    return prepared


TEXT_COLUMNS = (("Name_Lang_enUS", "name"), ("NameSubtext_Lang_enUS", "subtext"),
                ("Description_Lang_enUS", "description"), ("AuraDescription_Lang_enUS", "aura_description"))


def merge_spell_table(data: bytes) -> bytes:
    """Append every Drakkin/Drakonid racial that the table does not already carry."""
    table = Wdbc(data)
    index = field_index()
    existing = {row[0] for row in table.rows}
    records = [list(row) for row in table.rows]
    strings: dict[tuple[int, int], str] = {}
    for row_index, row in enumerate(records):
        for column, _ in TEXT_COLUMNS:
            if row[index[column]]:
                value = table.text(row[index[column]])
                if value:
                    strings[(row_index, index[column])] = value
    for item in prepare(table):
        if item.spell.spell_id in existing:
            # Re-running over an already patched table is fine; a different spell on the id is not.
            owner = next(row for row in table.rows if row[0] == item.spell.spell_id)
            if table.text(owner[index["Name_Lang_enUS"]]) != item.spell.name:
                raise ValueError(f"spell id {item.spell.spell_id} already belongs to another spell")
            continue
        for column, attribute in TEXT_COLUMNS:
            value = getattr(item.spell, attribute)
            if value:
                strings[(len(records), index[column])] = value
        records.append(item.row)
    return build_wdbc(records, table.fields, table.record_size, strings)


def _sql_value(value: int, kind: str) -> str:
    if kind == "float":
        return repr(struct.unpack("<f", struct.pack("<I", value))[0])
    if kind == "signed":
        return str(struct.unpack("<i", struct.pack("<I", value))[0])
    return str(value)


def _quote(value: str) -> str:
    return "'" + value.replace("\\", "\\\\").replace("'", "''") + "'"


def render_sql(data: bytes) -> str:
    """World-DB half: `spell_dbc` rows, the Broodblood proc cooldown and the script bindings."""
    table = Wdbc(data)
    columns = spell_columns()
    string_columns = {name for name, kind in columns if kind == "string"}
    statements = []
    for item in prepare(table):
        names, values = ["ID"], [str(item.spell.spell_id)]
        for position, (column, kind) in enumerate(columns):
            if column == "ID" or kind == "string" or not item.row[position]:
                continue
            names.append(column)
            values.append(_sql_value(item.row[position], kind))
        for column, attribute in TEXT_COLUMNS:
            text = getattr(item.spell, attribute)
            if text and column in string_columns:
                names.append(column)
                values.append(_quote(text))
        statements.append("INSERT INTO `spell_dbc` ({}) VALUES\n({});".format(
            ", ".join(f"`{name}`" for name in names), ", ".join(values)))

    spell_ids = ", ".join(str(spell.spell_id) for spell in spell_spec())
    script_ids = ", ".join(str(spell_id) for spell_id, _ in SCRIPT_BINDINGS)
    scripts = ",\n".join(f"({spell_id}, {_quote(name)})" for spell_id, name in SCRIPT_BINDINGS)
    return (
        "-- GENERATED by `python tools/drakkin_drakonid_racials.py --sql-out <path>`; do not hand edit.\n"
        "-- The rows mirror the client Spell.dbc entries the Drakkin and Drakonid packs write.\n"
        "-- `spell_dbc` overrides the whole row, so every non-default field of the cloned stock\n"
        "-- spell is listed here; anything omitted is 0/empty in the DBC row too.\n"
        "\n"
        f"DELETE FROM `spell_dbc` WHERE `ID` IN ({spell_ids});\n"
        + "\n".join(statements) + "\n"
        "\n"
        "-- Ancient Broodblood: ProcFlags come from Spell.dbc; the internal cooldown is the only addition.\n"
        f"DELETE FROM `spell_proc` WHERE `SpellId` = {ANCIENT_BROODBLOOD};\n"
        f"INSERT INTO `spell_proc` (`SpellId`, `Cooldown`) VALUES ({ANCIENT_BROODBLOOD}, "
        f"{BROODBLOOD_INTERNAL_COOLDOWN_MS});\n"
        "\n"
        "-- drakkin_racials.cpp and drakonid_racials.cpp are inert without these bindings.\n"
        f"DELETE FROM `spell_script_names` WHERE `spell_id` IN ({script_ids});\n"
        "INSERT INTO `spell_script_names` (`spell_id`, `ScriptName`) VALUES\n" + scripts + ";\n"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dbc-in", type=Path, default=DEFAULT_SPELL_DBC, help="Spell.dbc used as the donor source")
    parser.add_argument("--sql-out", type=Path)
    parser.add_argument("--dbc-out", type=Path, help="write a Spell.dbc with the racials appended")
    args = parser.parse_args()
    data = args.dbc_in.read_bytes()
    if args.sql_out:
        args.sql_out.write_text(render_sql(data), encoding="utf-8", newline="\n")
    if args.dbc_out:
        args.dbc_out.parent.mkdir(parents=True, exist_ok=True)
        args.dbc_out.write_bytes(merge_spell_table(data))


if __name__ == "__main__":
    main()
