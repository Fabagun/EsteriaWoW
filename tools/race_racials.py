"""Racial spells for the retail ports and the custom races of Esteria.

The spec in this file is the single source for:

* ``merge_spell_table`` - clones stock donor rows into a Spell.dbc (client and server copy).
* ``render_sql``        - the matching world-DB ``spell_dbc``, ``spell_proc`` and ``spell_script_names`` rows.
* ``render_header``     - ``race_racials_generated.h`` (spell ids and the race -> racial grant table) for
  modules/mod-custom-server/src/race_racials.cpp.

Primitives and the Spell.dbc plumbing come from ``drakkin_drakonid_racials`` so both tools agree on the
column layout. The Drakkin/Drakonid spec is left untouched: its tests pin its own SQL file.

    python tools/race_racials.py --sql-out <file.sql> --header-out <file.h>
    python tools/race_racials.py --dbc-in Spell.dbc --dbc-out patched/Spell.dbc

Scope notes (what the 3.3.5a client cannot do is named in each spell description instead of faked):
Versatility, Mastery and Finesse do not exist in WotLK; they are replaced by the closest stat noted in the text.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import race_racial_visuals
from cars_mount_pack import Wdbc, build_wdbc
from drakkin_drakonid_racials import (
    ALL_MAGIC_SCHOOLS, AREA_ENEMY, ATTR_AURA_IS_DEBUFF, ATTR_IS_ABILITY, ATTR_PASSIVE, AURA_DUMMY,
    AURA_HASTE_SPELLS, AURA_MECHANIC_DURATION_MOD, AURA_MOD_BASE_RESISTANCE_PCT, AURA_MOD_DAMAGE_DONE_VERSUS,
    AURA_MOD_DAMAGE_PERCENT_DONE, AURA_MOD_DAMAGE_PERCENT_TAKEN, AURA_MOD_DECREASE_SPEED, AURA_MOD_DODGE_PERCENT,
    AURA_MOD_HEALING_DONE_PERCENT, AURA_MOD_INCREASE_SPEED, AURA_MOD_MELEE_HASTE, AURA_MOD_PERCENT_STAT,
    AURA_MOD_RANGED_HASTE, AURA_MOD_STUN, AURA_PROC_TRIGGER_SPELL, AURA_MOD_RESISTANCE, APPLY_AURA, CONE_ENEMY, DUMMY,
    DEFAULT_SPELL_DBC, DURATION_4_SEC, DURATION_6_SEC, DURATION_8_SEC, DURATION_INFINITE, GCD_CATEGORY, GCD_MS,
    MECHANIC_SNARE, MECHANIC_STUN, PASSIVE_DONOR, RADIUS_8_YD, RADIUS_15_YD, SCHOOL_ARCANE, SCHOOL_DAMAGE,
    SCHOOL_FIRE, SCHOOL_FROST, SCHOOL_NATURE, SCHOOL_PHYSICAL, SCHOOL_SHADOW, SELF, SRC_CASTER, TARGET_ENEMY,
    TEXT_COLUMNS, Prepared, Spell, _pack, _quote, _sql_value, effect, field_index, merge, spell_columns,
)

# --- races ------------------------------------------------------------------------
SETHRAK, EREDAR, NIGHTBORNE, PANDAREN_A, VOIDELF, VULPERA, LIGHTFORGED, ZANDALARI, DARKIRON = 15, 16, 17, 18, 19, 20, 21, 22, 23
PANDAREN_H, DRACTHYR = 26, 28
HIGHMOUNTAIN, MECHAGNOME, EARTHEN_A, EARTHEN_H, HARANIR_A, HARANIR_H = 46, 47, 48, 49, 50, 51
SKYBORNE_A, SKYBORNE_H, NAGA, TUSKARR, VRYKUL_A, VRYKUL_H, FORGOTTEN_A, FORGOTTEN_H = 52, 53, 54, 55, 56, 57, 58, 59
OGRE_H, OGRE_A, SETHRAK_A, GNOLL, SABERON, JINYU = 60, 61, 62, 63, 64, 65

# --- extra aura / effect numbers (SpellAuraDefines.h, SharedDefines.h) -----------------
AURA_PERIODIC_DAMAGE, AURA_PERIODIC_HEAL, AURA_MOD_ROOT, AURA_MOD_SKILL = 3, 8, 26, 30
AURA_MOD_STEALTH_DETECT, AURA_MOD_SWIM_SPEED, AURA_WATER_BREATHING, AURA_FEATHER_FALL = 17, 58, 82, 105
AURA_SAFE_FALL, AURA_REDUCE_PUSHBACK, AURA_MOD_CRIT_PCT, AURA_MOD_EXPERTISE = 144, 149, 290, 240
AURA_MOD_CRIT_DAMAGE_BONUS, AURA_DURATION_BY_DISPEL, AURA_MECHANIC_DAMAGE_TAKEN = 163, 245, 255
AURA_MOD_HEALING_PCT_TAKEN = 118
EFFECT_DISPEL_MECHANIC = 108
TARGET_ALLY, TARGET_ANY = 21, 25
MECHANIC_ROOT, MECHANIC_SILENCE, MECHANIC_FEAR, MECHANIC_KNOCKOUT, MECHANIC_BLEED, MECHANIC_INTERRUPT, MECHANIC_DAZE = 7, 9, 5, 14, 15, 26, 27
DISPEL_POISON = 4
SCHOOL_HOLY = 2
STAT_STRENGTH, STAT_AGILITY, STAT_STAMINA, STAT_INTELLECT, STAT_SPIRIT = 0, 1, 2, 3, 4
ALL_STATS = -1

SKILL_FIRST_AID, SKILL_BLACKSMITHING, SKILL_COOKING, SKILL_HERBALISM, SKILL_MINING = 129, 164, 185, 182, 186
SKILL_ENCHANTING, SKILL_FISHING, SKILL_SKINNING, SKILL_INSCRIPTION, SKILL_LOCKPICKING = 333, 356, 393, 773, 633

WEAPON_CLASS = 2
SUBCLASS_SWORDS_POLEARMS = (1 << 7) | (1 << 8) | (1 << 6)
SUBCLASS_MACES_FISTS = (1 << 4) | (1 << 5) | (1 << 13)

PROC_DONE_ANY = 0x4 | 0x10 | 0x40 | 0x100 | 0x400 | 0x1000 | 0x4000 | 0x10000
PROC_TAKEN_DAMAGE = 0x00100000

# SpellDuration / SpellCastTimes / SpellRange rows in the stock 3.3.5a tables.
DUR_1_SEC, DUR_1_5_SEC, DUR_2_SEC, DUR_3_SEC, DUR_4_SEC, DUR_5_SEC, DUR_6_SEC, DUR_8_SEC = 36, 65, 39, 27, 35, 28, 32, 31
DUR_10_SEC, DUR_12_SEC, DUR_15_SEC, DUR_20_SEC, DUR_30_SEC = 1, 29, 8, 18, 9
CAST_2_5_SEC = 19
RANGE_SELF, RANGE_MELEE, RANGE_30, RANGE_15, RANGE_40 = 1, 2, 4, 11, 5
RADIUS_5_YD, RADIUS_10_YD, RADIUS_20_YD, RADIUS_30_YD = 8, 13, 9, 10

# Further SpellDuration / SpellCastTimes rows (read from the pristine DBFilesClient tables).
DUR_1_MIN, DUR_90_SEC, DUR_2_MIN, DUR_10_MIN, DUR_1_HOUR = 3, 23, 4, 6, 42
CAST_2_SEC, CAST_3_SEC, CAST_5_SEC, CAST_10_SEC = 5, 14, 6, 7
AURA_PERIODIC_ENERGIZE, AURA_MOD_ATTACK_POWER, AURA_MOD_DAMAGE_DONE, AURA_MOD_INCREASE_HEALTH_PERCENT = 24, 99, 13, 133
FOOD_DONOR = 433   # stock "Food": seated, interrupted by moving; Quiet Contemplation borrows its flags

ICD = 1000
MIN = 60 * ICD

# --- spell id blocks ----------------------------------------------------------------
# 110300-110406 belong to Drakkin/Drakonid. Each race gets a block of 20 from 110500.
BLOCKS = {
    "NIGHTBORNE": 110500, "VOIDELF": 110520, "LIGHTFORGED": 110540, "ZANDALARI": 110560, "DARKIRON": 110580,
    "HIGHMOUNTAIN": 110600, "MECHAGNOME": 110620, "VULPERA": 110640, "PANDAREN": 110660, "DRACTHYR": 110680,
    "EARTHEN": 110700, "HARANIR": 110720, "EREDAR": 110740, "SKYBORNE": 110760, "SETHRAK": 110800,
    "NAGA": 110820, "TUSKARR": 110840, "VRYKUL": 110860, "FORGOTTEN": 110880, "OGRE": 110900,
    "GNOLL": 110920, "SABERON": 110940, "JINYU": 110960, "SHARED": 110980,
}

SPELLS: list[Spell] = []
KEYS: dict[str, int] = {}
ICONS: dict[int, int] = {}
RACE_GRANTS: dict[int, list[str]] = {}
BINDINGS: list[tuple[str, str]] = []   # (spell key, script name)
PROCS: list[tuple[str, int, int]] = []  # (spell key, chance %, cooldown ms)
DEFAULT_ICON = 20550


def _add(key: str, block: str, slot: int, name: str, fields: dict, subtext: str, description: str,
         aura_description: str, icon: int, donor: int = PASSIVE_DONOR) -> int:
    spell_id = BLOCKS[block] + slot
    if key in KEYS:
        raise ValueError(f"duplicate racial key {key}")
    KEYS[key] = spell_id
    ICONS[spell_id] = icon
    SPELLS.append(Spell(spell_id, name, fields, subtext, description, aura_description, donor))
    return spell_id


PASSIVE = {"Attributes": ATTR_IS_ABILITY | ATTR_PASSIVE}
ACTIVE = {"Attributes": ATTR_IS_ABILITY, "RangeIndex": RANGE_SELF,
          "StartRecoveryCategory": GCD_CATEGORY, "StartRecoveryTime": GCD_MS}
HIDDEN_CHILD = {"Attributes": ATTR_IS_ABILITY | 0x80, "RangeIndex": RANGE_30}   # 0x80: do not display
DEBUFF = {"Attributes": ATTR_IS_ABILITY | ATTR_AURA_IS_DEBUFF}


def passive(key, block, slot, name, description, *effects, icon=DEFAULT_ICON, extra=None, subtext="Racial Passive"):
    return _add(key, block, slot, name, merge(PASSIVE, extra or {}, *effects), subtext, description, "", icon)


def active(key, block, slot, name, description, cooldown, *effects, icon=DEFAULT_ICON, extra=None,
           range_index=RANGE_SELF, duration=None, aura_description="", cast_time=None):
    fields = merge(ACTIVE, {"RecoveryTime": cooldown, "RangeIndex": range_index}, extra or {}, *effects)
    if duration is not None:
        fields["DurationIndex"] = duration
    if cast_time is not None:
        fields["CastingTimeIndex"] = cast_time
    return _add(key, block, slot, name, fields, "Racial", description, aura_description, icon)


def child(key, block, slot, name, aura_description, *effects, duration=None, icon=DEFAULT_ICON, extra=None,
          debuff=False, hidden=False):
    fields = merge(DEBUFF if debuff else (HIDDEN_CHILD if hidden else {"Attributes": ATTR_IS_ABILITY}),
                   {"RangeIndex": RANGE_30 if debuff or hidden else RANGE_SELF}, extra or {}, *effects)
    if duration is not None:
        fields["DurationIndex"] = duration
    return _add(key, block, slot, name, fields, "", "", aura_description, icon)


HEAL_ALLY = {"Effect_1": 10, "EffectDieSides_1": 1, "EffectBasePoints_1": 0, "EffectAura_1": 0, "EffectMiscValue_1": 0,
             "ImplicitTargetA_1": 21}   # SPELL_EFFECT_HEAL on one ally; the amount comes from spell_race_scaled_heal


def damage(slot, target=TARGET_ENEMY, target_b=0, radius=0, school=None):
    """A SCHOOL_DAMAGE effect whose amount comes from ``spell_race_scaled_damage``."""
    values = {f"Effect_{slot}": SCHOOL_DAMAGE, f"EffectDieSides_{slot}": 1, f"EffectBasePoints_{slot}": 0,
              f"EffectAura_{slot}": 0, f"EffectMiscValue_{slot}": 0, f"ImplicitTargetA_{slot}": target,
              f"ImplicitTargetB_{slot}": target_b, f"EffectRadiusIndex_{slot}": radius,
              f"EffectBonusMultiplier_{slot}": 0.0}
    if school is not None:
        values["SchoolMask"] = school
    return values


def dummy(slot, target=SELF, target_b=0, radius=0):
    return {f"Effect_{slot}": DUMMY, f"EffectDieSides_{slot}": 1, f"EffectBasePoints_{slot}": 0,
            f"EffectAura_{slot}": 0, f"EffectMiscValue_{slot}": 0, f"ImplicitTargetA_{slot}": target,
            f"ImplicitTargetB_{slot}": target_b, f"EffectRadiusIndex_{slot}": radius}


def aura(slot, kind, points, misc=0, target=SELF, **extra):
    return effect(slot, kind, points, misc, target, **extra)


def area(slot, kind, points, misc=0, radius=RADIUS_8_YD, **extra):
    """An aura applied to every enemy around the caster."""
    return effect(slot, kind, points, misc, SRC_CASTER, ImplicitTargetB=AREA_ENEMY, EffectRadiusIndex=radius, **extra)


def skill(slot, skill_id, points):
    return aura(slot, AURA_MOD_SKILL, points, skill_id)


def haste(pct):
    return (aura(1, AURA_MOD_MELEE_HASTE, pct), aura(2, AURA_MOD_RANGED_HASTE, pct), aura(3, AURA_HASTE_SPELLS, pct))


def grant(race: int, *keys: str) -> None:
    RACE_GRANTS.setdefault(race, []).extend(keys)


def bind(key: str, script: str) -> None:
    BINDINGS.append((key, script))


# ---------------------------------------------------------------------------------------
# Shared building blocks
# ---------------------------------------------------------------------------------------
def haste_burst(key, block, slot, name, description, pct=10, icon=DEFAULT_ICON):
    return active(key, block, slot, name, description, 2 * MIN, *haste(pct), icon=icon, duration=DUR_10_SEC,
                  aura_description=f"Haste increased by {pct}%.")


def dodge(key, block, slot, name, pct=1, icon=DEFAULT_ICON, text=None):
    return passive(key, block, slot, name, text or f"Dodge chance increased by {pct}%.", aura(1, AURA_MOD_DODGE_PERCENT, pct), icon=icon)


def crit(key, block, slot, name, pct=1, icon=DEFAULT_ICON, text=None):
    return passive(key, block, slot, name, text or f"Critical strike chance increased by {pct}%.", aura(1, AURA_MOD_CRIT_PCT, pct), icon=icon)


def haste_passive(key, block, slot, name, pct=1, icon=DEFAULT_ICON, text=None):
    return passive(key, block, slot, name, text or f"Haste increased by {pct}%.", *haste(pct), icon=icon)


def school_bonus(key, block, slot, name, mask, label, pct=1, icon=DEFAULT_ICON):
    return passive(key, block, slot, name, f"{label} damage dealt increased by {pct}%.",
                   aura(1, AURA_MOD_DAMAGE_PERCENT_DONE, pct, mask), icon=icon)


def school_ward(key, block, slot, name, mask, label, pct=1, icon=DEFAULT_ICON):
    return passive(key, block, slot, name, f"{label} damage taken reduced by {pct}%.",
                   aura(1, AURA_MOD_DAMAGE_PERCENT_TAKEN, -pct, mask), icon=icon)


def skill_passive(key, block, slot, name, skill_id, points, label, icon=DEFAULT_ICON, text=None):
    return passive(key, block, slot, name, text or f"{label} skill increased by {points}.", skill(1, skill_id, points), icon=icon)


def armor_passive(key, block, slot, name, pct, icon=DEFAULT_ICON):
    return passive(key, block, slot, name, f"Armor from equipped items increased by {pct}%.",
                   aura(1, AURA_MOD_BASE_RESISTANCE_PCT, pct, SCHOOL_PHYSICAL), icon=icon)


def expertise(key, block, slot, name, points, subclass_mask, label, icon=DEFAULT_ICON):
    return passive(key, block, slot, name, f"Expertise with {label} increased by {points}.",
                   aura(1, AURA_MOD_EXPERTISE, points),
                   extra={"EquippedItemClass": WEAPON_CLASS, "EquippedItemSubclass": subclass_mask}, icon=icon)


def swimmer(key, block, slot, name, icon=DEFAULT_ICON):
    return passive(key, block, slot, name, "Swim speed increased by 50% and you can breathe underwater indefinitely.",
                   aura(1, AURA_MOD_SWIM_SPEED, 50), aura(2, AURA_WATER_BREATHING, 1), icon=icon)


def hunters_pace(key, block, slot, name, icon=DEFAULT_ICON):
    """Passive marker plus its out-of-combat speed child (applied/removed by race_racials.cpp)."""
    marker = passive(key, block, slot, name, "Movement speed increased by 5% while out of combat.",
                     aura(1, AURA_DUMMY, 1), icon=icon)
    child(f"{key}_SPEED", block, slot + 1, name, "Movement speed increased by 5%.",
          aura(1, AURA_MOD_INCREASE_SPEED, 5), duration=DURATION_INFINITE, icon=icon,
          extra={"Attributes": ATTR_IS_ABILITY | ATTR_PASSIVE})
    return marker


def area_pulse(key, block, slot, name, description, school, slow_pct, slow_dur, radius, icon, cooldown=3 * MIN):
    """Instant damage + slow around the caster; the damage amount is set by spell_race_scaled_damage."""
    spell = active(key, block, slot, name, description, cooldown,
                   damage(1, SRC_CASTER, AREA_ENEMY, radius, school),
                   area(2, AURA_MOD_DECREASE_SPEED, -slow_pct, 0, radius),
                   icon=icon, duration=slow_dur, aura_description=f"Movement speed reduced by {slow_pct}%.")
    bind(key, "spell_race_scaled_damage")
    return spell


# ---------------------------------------------------------------------------------------
# Retail races
# ---------------------------------------------------------------------------------------
# Nightborne (17)
B = "NIGHTBORNE"
area_pulse("ARCANE_PULSE", B, 0, "Arcane Pulse",
           "Deals Arcane damage to enemies within 8 yards and slows them by 80% for 8 sec.",
           SCHOOL_ARCANE, 80, DUR_8_SEC, RADIUS_8_YD, 1449)
school_bonus("MAGICAL_AFFINITY", B, 1, "Magical Affinity", ALL_MAGIC_SCHOOLS, "Magical", 1, 12043)
school_ward("ARCANE_RESISTANCE", B, 2, "Arcane Resistance", SCHOOL_ARCANE, "Arcane", 1, 20583)
skill_passive("ANCIENT_HISTORY", B, 3, "Ancient History", SKILL_INSCRIPTION, 5, "Inscription", 45357)
grant(NIGHTBORNE, "ARCANE_PULSE", "MAGICAL_AFFINITY", "ARCANE_RESISTANCE", "ANCIENT_HISTORY")

# Void Elf (19)
B = "VOIDELF"
entropic = passive("ENTROPIC_EMBRACE", B, 0, "Entropic Embrace",
                   "Your damaging and healing abilities have a chance to increase damage and healing done by 5% for 12 sec.",
                   aura(1, AURA_PROC_TRIGGER_SPELL, 1, 0, EffectTriggerSpell=BLOCKS[B] + 1),
                   extra={"ProcTypeMask": PROC_DONE_ANY, "ProcChance": 101}, icon=589)
child("ENTROPIC_EMBRACE_BUFF", B, 1, "Entropic Embrace", "Damage and healing done increased by 5%.",
      aura(1, AURA_MOD_DAMAGE_PERCENT_DONE, 5, 127), aura(2, AURA_MOD_HEALING_DONE_PERCENT, 5, 127),
      duration=DUR_12_SEC, icon=589)
PROCS.append(("ENTROPIC_EMBRACE", 15, 12 * ICD))
passive("PRETERNATURAL_CALM", B, 2, "Preternatural Calm", "Spellcasting is not delayed by taking damage.",
        aura(1, AURA_REDUCE_PUSHBACK, 100), icon=14751)
school_ward("CHILL_OF_NIGHT", B, 3, "Chill of Night", SCHOOL_SHADOW, "Shadow", 1, 20579)
grant(VOIDELF, "ENTROPIC_EMBRACE", "PRETERNATURAL_CALM", "CHILL_OF_NIGHT")

# Lightforged Draenei (21)
B = "LIGHTFORGED"
lj = active("LIGHTS_JUDGMENT", B, 0, "Light's Judgment",
            "Calls down Holy energy on the target after 3 sec, damaging enemies within 10 yards.", 150 * ICD,
            dummy(1, TARGET_ENEMY), icon=20271, range_index=RANGE_30)
bind("LIGHTS_JUDGMENT", "spell_race_lights_judgment")
child("LIGHTS_JUDGMENT_DAMAGE", B, 1, "Light's Judgment", "",
      damage(1, TARGET_ENEMY, 0, 0, SCHOOL_HOLY), hidden=True, icon=20271)
bind("LIGHTS_JUDGMENT_DAMAGE", "spell_race_scaled_damage")
passive("LIGHTS_RECKONING", B, 2, "Light's Reckoning",
        "On death, you erupt with Light, damaging enemies and healing allies within 15 yards.",
        aura(1, AURA_DUMMY, 1), icon=20066)
child("LIGHTS_RECKONING_DAMAGE", B, 3, "Light's Reckoning", "",
      damage(1, TARGET_ENEMY, 0, 0, SCHOOL_HOLY), hidden=True, icon=20066)
bind("LIGHTS_RECKONING_DAMAGE", "spell_race_scaled_damage")
child("LIGHTS_RECKONING_HEAL", B, 6, "Light's Reckoning", "", HEAL_ALLY, hidden=True, icon=20066)
bind("LIGHTS_RECKONING_HEAL", "spell_race_scaled_heal")
passive("HOLY_PROVIDENCE", B, 4, "Holy Providence", "Holy damage taken reduced by 1% and healing done increased by 1%.",
        aura(1, AURA_MOD_DAMAGE_PERCENT_TAKEN, -1, SCHOOL_HOLY), aura(2, AURA_MOD_HEALING_DONE_PERCENT, 1, 127), icon=635)
passive("DEMONBANE", B, 5, "Demonbane", "Experience gained from killing demons increased by 20%.",
        aura(1, AURA_DUMMY, 1), icon=1161)
grant(LIGHTFORGED, "LIGHTS_JUDGMENT", "LIGHTS_RECKONING", "HOLY_PROVIDENCE", "DEMONBANE")

# Zandalari Troll (22)
B = "ZANDALARI"
active("REGENERATIN", B, 0, "Regeneratin'",
       "Channel for 6 sec to restore 50% of your maximum health. Direct damage interrupts the channel; periodic damage does not.",
       3 * MIN, aura(1, AURA_PERIODIC_HEAL, 1, 0, EffectAuraPeriod=1000), icon=2061, duration=DUR_6_SEC,
       extra={"AttributesEx": 0x4, "ChannelInterruptFlags": 0x8 | 0x10 | 0x01000000})
bind("REGENERATIN", "spell_race_regeneratin")
passive("CITY_OF_GOLD", B, 1, "City of Gold", "Gold found on creatures increased by 2%.", aura(1, AURA_DUMMY, 1), icon=921)
active("PTERRORDAX_SWOOP", B, 2, "Pterrordax Swoop", "Spread your arms and glide, slowing your fall for 20 sec.",
       15 * MIN, aura(1, AURA_FEATHER_FALL, 1), icon=130, duration=DUR_20_SEC, aura_description="Falling slowly.")
grant(ZANDALARI, "REGENERATIN", "CITY_OF_GOLD", "PTERRORDAX_SWOOP")

# Dark Iron Dwarf (23)
B = "DARKIRON"
active("FIREBLOOD", B, 0, "Fireblood",
       "Removes all Poison, Disease, Curse, Magic and Bleed effects and increases your primary stats by 2% for 8 sec, "
       "plus 1% for each effect removed (up to 5).",
       2 * MIN, dummy(1), icon=20594)
bind("FIREBLOOD", "spell_race_fireblood")
child("FIREBLOOD_BUFF", B, 1, "Fireblood", "Primary stats increased.",
      aura(1, AURA_MOD_PERCENT_STAT, 2, ALL_STATS), duration=DUR_8_SEC, icon=20594)
school_ward("FORGED_IN_FLAMES", B, 2, "Forged in Flames", SCHOOL_PHYSICAL, "Physical", 1, 20594)
skill_passive("MASS_PRODUCTION", B, 3, "Mass Production", SKILL_BLACKSMITHING, 5, "Blacksmithing", 2018)
grant(DARKIRON, "FIREBLOOD", "FORGED_IN_FLAMES", "MASS_PRODUCTION")

# Highmountain Tauren (46)
B = "HIGHMOUNTAIN"
active("BULL_RUSH", B, 0, "Bull Rush",
       "Charge forward for 1 sec, knocking enemies in your path down for 1.5 sec.", 2 * MIN, dummy(1), icon=100)
bind("BULL_RUSH", "spell_race_bull_rush")
child("BULL_RUSH_KNOCKDOWN", B, 1, "Bull Rush", "Knocked down.",
      aura(1, AURA_MOD_STUN, 1, 0, TARGET_ENEMY, EffectMechanic=MECHANIC_STUN),
      debuff=True, duration=DUR_1_5_SEC, icon=100, extra={"Mechanic": MECHANIC_STUN})
passive("MOUNTAINEER", B, 2, "Mountaineer",
        "Damage dealt and healing done increased by 1% and damage taken reduced by 1% (Versatility has no WotLK equivalent).",
        aura(1, AURA_MOD_DAMAGE_PERCENT_DONE, 1, 127), aura(2, AURA_MOD_HEALING_DONE_PERCENT, 1, 127),
        aura(3, AURA_MOD_DAMAGE_PERCENT_TAKEN, -1, 127), icon=20550)
passive("RUGGED_TENACITY", B, 3, "Rugged Tenacity",
        "Reduces each hit you take by an amount that grows with your Stamina.", aura(1, AURA_DUMMY, 1), icon=20550)
grant(HIGHMOUNTAIN, "BULL_RUSH", "MOUNTAINEER", "RUGGED_TENACITY")

# Mechagnome (47)
B = "MECHAGNOME"
passive("COMBAT_ANALYSIS", B, 0, "Combat Analysis",
        "Every 5 sec in combat, gain 1% to all stats, stacking up to 10 times. Stacks fade soon after combat ends.",
        aura(1, AURA_DUMMY, 1), icon=28730)
child("COMBAT_ANALYSIS_STACK", B, 1, "Combat Analysis", "Stats increased by 1% per stack.",
      aura(1, AURA_MOD_PERCENT_STAT, 1, ALL_STATS), duration=DUR_15_SEC, icon=28730, extra={"CumulativeAura": 10})
passive("EMERGENCY_FAILSAFE", B, 2, "Emergency Failsafe",
        "Falling below 20% health restores 15% of your maximum health. Can occur once every 2.5 min.",
        aura(1, AURA_DUMMY, 1), icon=2061)
passive("SKELETON_PINKIE", B, 3, "Skeleton Pinkie", "You are able to pick locks.", aura(1, AURA_DUMMY, 1), icon=1804)
grant(MECHAGNOME, "COMBAT_ANALYSIS", "EMERGENCY_FAILSAFE", "SKELETON_PINKIE")

# Vulpera (20)
B = "VULPERA"
active("BAG_OF_TRICKS", B, 0, "Bag of Tricks",
       "Pull a trick from your bag. On an enemy: deals damage and slows by 80% for 4 sec. On an ally: heals and grants "
       "20% movement speed for 4 sec.", 90 * ICD, dummy(1, TARGET_ANY), icon=21343, range_index=RANGE_30)
bind("BAG_OF_TRICKS", "spell_race_bag_of_tricks")
child("BAG_OF_TRICKS_DAMAGE", B, 1, "Bag of Tricks", "", damage(1, TARGET_ENEMY, 0, 0, SCHOOL_PHYSICAL), hidden=True, icon=21343)
bind("BAG_OF_TRICKS_DAMAGE", "spell_race_scaled_damage")
child("BAG_OF_TRICKS_SLOW", B, 2, "Bag of Tricks", "Movement speed reduced by 80%.",
      aura(1, AURA_MOD_DECREASE_SPEED, -80, 0, TARGET_ENEMY, EffectMechanic=MECHANIC_SNARE), debuff=True, duration=DUR_4_SEC,
      icon=21343, extra={"Mechanic": MECHANIC_SNARE})
child("BAG_OF_TRICKS_HEAL", B, 3, "Bag of Tricks", "", HEAL_ALLY, hidden=True, icon=21343)
bind("BAG_OF_TRICKS_HEAL", "spell_race_scaled_heal")
child("BAG_OF_TRICKS_SPEED", B, 4, "Bag of Tricks", "Movement speed increased by 20%.",
      aura(1, AURA_MOD_INCREASE_SPEED, 20), duration=DUR_4_SEC, icon=21343)
passive("NOSE_FOR_TROUBLE", B, 5, "Nose for Trouble",
        "The first hit you take from an enemy is reduced by 5% of your maximum health. Rearms after 30 sec.",
        aura(1, AURA_DUMMY, 1), icon=20550)
passive("VULPERA_FIRE_RESISTANCE", B, 6, "Fire Resistance", "Fire damage taken reduced by 2%.",
        aura(1, AURA_MOD_DAMAGE_PERCENT_TAKEN, -2, SCHOOL_FIRE), icon=20572)
grant(VULPERA, "BAG_OF_TRICKS", "NOSE_FOR_TROUBLE", "VULPERA_FIRE_RESISTANCE")

# Pandaren (18 / 26)
B = "PANDAREN"
active("QUAKING_PALM", B, 0, "Quaking Palm", "Incapacitates an enemy for 4 sec. Damage may break the effect.", 2 * MIN,
       aura(1, AURA_MOD_STUN, 1, 0, TARGET_ENEMY, EffectMechanic=MECHANIC_KNOCKOUT), icon=1776, duration=DUR_4_SEC,
       range_index=RANGE_MELEE, aura_description="Incapacitated.",
       extra={"Mechanic": MECHANIC_KNOCKOUT, "AuraInterruptFlags": 0x2})
passive("EPICUREAN", B, 1, "Epicurean", "Well Fed stat bonuses are doubled.", aura(1, AURA_DUMMY, 1), icon=2639)
skill_passive("GOURMAND", B, 2, "Gourmand", SKILL_COOKING, 5, "Cooking", 818)
passive("BOUNCY", B, 4, "Bouncy", "Fall damage reduced by roughly half.", aura(1, AURA_SAFE_FALL, 12), icon=130)
for race in (PANDAREN_A, PANDAREN_H):
    grant(race, "QUAKING_PALM", "EPICUREAN", "GOURMAND", "BOUNCY")

# Dracthyr (28)
B = "DRACTHYR"
active("WING_BUFFET", B, 0, "Wing Buffet", "Knocks enemies in front of you away.", 90 * ICD,
       dummy(1, CONE_ENEMY, 0, RADIUS_15_YD), icon=45469)
bind("WING_BUFFET", "spell_race_wing_buffet")
active("DRACTHYR_GLIDE", B, 1, "Glide", "Spread your wings and glide, slowing your fall for 10 sec.", 30 * ICD,
       aura(1, AURA_FEATHER_FALL, 1), icon=130, duration=DUR_10_SEC, aura_description="Falling slowly.")
passive("AWAKENED", B, 2, "Awakened", "Damage dealt increased by 3%. (Mastery has no WotLK equivalent.)",
        aura(1, AURA_MOD_DAMAGE_PERCENT_DONE, 3, 127), icon=20550)
passive("DISCERNING_EYE", B, 3, "Discerning Eye", "Herbalism and Mining skill increased by 2.",
        skill(1, SKILL_HERBALISM, 2), skill(2, SKILL_MINING, 2), icon=2366)
grant(DRACTHYR, "WING_BUFFET", "DRACTHYR_GLIDE", "AWAKENED", "DISCERNING_EYE")

# Earthen (48 / 49)
B = "EARTHEN"
active("AZERITE_SURGE", B, 0, "Azerite Surge",
       "After 2.5 sec, unleash a surge of Fire damage on enemies within 15 yards. At level 40 the surge also heals allies, "
       "and at level 70 it additionally strikes the healthiest enemy.", 2 * MIN,
       dummy(1), icon=2120, cast_time=CAST_2_5_SEC)
bind("AZERITE_SURGE", "spell_race_azerite_surge")
child("AZERITE_SURGE_DAMAGE", B, 3, "Azerite Surge", "", damage(1, TARGET_ENEMY, 0, 0, SCHOOL_FIRE), hidden=True, icon=2120)
bind("AZERITE_SURGE_DAMAGE", "spell_race_scaled_damage")
child("AZERITE_SURGE_HEAL", B, 1, "Azerite Surge", "", HEAL_ALLY, hidden=True, icon=2120)
bind("AZERITE_SURGE_HEAL", "spell_race_scaled_heal")
child("AZERITE_SURGE_STRIKE", B, 2, "Azerite Surge", "", damage(1, TARGET_ENEMY, 0, 0, SCHOOL_FIRE), hidden=True, icon=2120)
bind("AZERITE_SURGE_STRIKE", "spell_race_scaled_damage")
armor_passive("TITAN_WROUGHT_FRAME", B, 4, "Titan-Wrought Frame", 10, 20594)
passive("WIDE_EYED_WONDER", B, 5, "Wide-Eyed Wonder", "Experience gained from exploring increased by 200%.",
        aura(1, AURA_DUMMY, 1), icon=20550)
passive("HYPER_PRODUCTIVE", B, 6, "Hyper Productive", "Herbalism, Mining and Skinning skill increased by 3.",
        skill(1, SKILL_HERBALISM, 3), skill(2, SKILL_MINING, 3), skill(3, SKILL_SKINNING, 3), icon=2580)
for race in (EARTHEN_A, EARTHEN_H):
    grant(race, "AZERITE_SURGE", "TITAN_WROUGHT_FRAME", "WIDE_EYED_WONDER", "HYPER_PRODUCTIVE")

# Haranir (50 / 51)
B = "HARANIR"
active("THORN_BLOOM", B, 0, "Thorn Bloom",
       "Thorns erupt around the target, damaging up to 8 enemies within 8 yards and healing up to 8 allies, pulsing 3 times over 4 sec.", 3 * MIN,
       dummy(1, TARGET_ANY), icon=5185, range_index=RANGE_30)
bind("THORN_BLOOM", "spell_race_thorn_bloom")
child("THORN_BLOOM_DAMAGE", B, 1, "Thorn Bloom", "", damage(1, TARGET_ENEMY, 0, 0, SCHOOL_NATURE), hidden=True, icon=5185)
bind("THORN_BLOOM_DAMAGE", "spell_race_scaled_damage")
child("THORN_BLOOM_HEAL", B, 2, "Thorn Bloom", "", HEAL_ALLY, hidden=True, icon=5185)
bind("THORN_BLOOM_HEAL", "spell_race_scaled_heal")
passive("LASH_OUT", B, 3, "Lash Out", "Critical strike damage and healing increased by 1%.",
        aura(1, AURA_MOD_CRIT_DAMAGE_BONUS, 1, 127), icon=20550)
passive("SUBTERRANEAN_PREDATOR", B, 4, "Subterranean Predator",
        "Experience from Beasts and Elementals increased by 10% and damage dealt to them increased by 1%. (WotLK has no Aberration type.)",
        aura(1, AURA_MOD_DAMAGE_DONE_VERSUS, 1, (1 << 0) | (1 << 3)), icon=1494)
skill_passive("ONE_WITH_NATURE", B, 5, "One with Nature", SKILL_HERBALISM, 5, "Herbalism", 20552)
for race in (HARANIR_A, HARANIR_H):
    grant(race, "THORN_BLOOM", "LASH_OUT", "SUBTERRANEAN_PREDATOR", "ONE_WITH_NATURE")

# ---------------------------------------------------------------------------------------
# Custom races
# ---------------------------------------------------------------------------------------
# Eredar (16)
B = "EREDAR"
haste_burst("FELBLOOD_SURGE", B, 0, "Felblood Surge", "Increases haste by 10% for 10 sec.", 10, 2825)
school_bonus("MANARI_BLOOD", B, 1, "Man'ari Blood", SCHOOL_FIRE | SCHOOL_SHADOW, "Shadow and Fire", 1, 686)
school_ward("DEMONIC_RESILIENCE", B, 2, "Demonic Resilience", SCHOOL_FIRE | SCHOOL_SHADOW, "Shadow and Fire", 1, 20579)
passive("UNBROKEN_WILL", B, 3, "Unbroken Will", "Duration of fear effects on you reduced by 10%.",
        aura(1, AURA_MECHANIC_DURATION_MOD, -10, MECHANIC_FEAR), icon=7744)
skill_passive("FORBIDDEN_KNOWLEDGE", B, 4, "Forbidden Knowledge", SKILL_ENCHANTING, 5, "Enchanting", 7411)
grant(EREDAR, "FELBLOOD_SURGE", "MANARI_BLOOD", "DEMONIC_RESILIENCE", "UNBROKEN_WILL", "FORBIDDEN_KNOWLEDGE")

# Skyborne (52 High Order / 53 Windshaper)
B = "SKYBORNE"
passive("SKYBORNE_WINGS", B, 0, "Skyborne Wings", "Fall damage greatly reduced. Use Skyborne Glide to slow a fall.",
        aura(1, AURA_SAFE_FALL, 12), icon=130)
active("SKYBORNE_GLIDE", B, 1, "Skyborne Glide", "Spread your wings and glide, slowing your fall for 10 sec.", 30 * ICD,
       aura(1, AURA_FEATHER_FALL, 1), icon=130, duration=DUR_10_SEC, aura_description="Falling slowly.")
haste_burst("EDICT_OF_THE_HIGH_ORDER", B, 2, "Edict of the High Order",
            "Increases melee, ranged and spell haste by 10% for 10 sec.", 10, 2825)
school_bonus("ORDERED_MAGIC", B, 3, "Ordered Magic", ALL_MAGIC_SCHOOLS, "Magical", 1, 12043)
passive("ORDERED_MAGIC_HEALING", B, 4, "Ordered Magic", "Healing done increased by 1%.",
        aura(1, AURA_MOD_HEALING_DONE_PERCENT, 1, 127), icon=12043)
passive("DISCIPLINED_MIND", B, 5, "Disciplined Mind", "Duration of silence and interrupt lockouts on you reduced by 10%.",
        aura(1, AURA_MECHANIC_DURATION_MOD, -10, MECHANIC_SILENCE), aura(2, AURA_MECHANIC_DURATION_MOD, -10, MECHANIC_INTERRUPT),
        icon=12043)
skill_passive("ARCANE_SCHOLARSHIP", B, 6, "Arcane Scholarship", SKILL_ENCHANTING, 5, "Enchanting", 7411)
active("GALE_STEP", B, 7, "Gale Step", "Increases movement speed by 40% for 6 sec.", 2 * MIN,
       aura(1, AURA_MOD_INCREASE_SPEED, 40), icon=2983, duration=DUR_6_SEC, aura_description="Movement speed increased by 40%.")
dodge("WINDBORNE_REFLEXES", B, 8, "Windborne Reflexes", 1, 20582)
haste_passive("SWIFT_AS_THE_GALE", B, 9, "Swift as the Gale", 1, 2983)
school_ward("STORMBORN", B, 10, "Stormborn", SCHOOL_NATURE, "Nature", 1, 20583)
grant(SKYBORNE_A, "SKYBORNE_WINGS", "SKYBORNE_GLIDE", "EDICT_OF_THE_HIGH_ORDER", "ORDERED_MAGIC", "ORDERED_MAGIC_HEALING",
      "DISCIPLINED_MIND", "ARCANE_SCHOLARSHIP")
grant(SKYBORNE_H, "SKYBORNE_WINGS", "SKYBORNE_GLIDE", "GALE_STEP", "WINDBORNE_REFLEXES", "SWIFT_AS_THE_GALE", "STORMBORN")

# Sethrak (15 / 62)
B = "SETHRAK"
area_pulse("STATIC_COIL", B, 0, "Static Coil",
           "Discharges electricity around you, dealing Nature damage to enemies within 8 yards and slowing them by 40% for 6 sec.",
           SCHOOL_NATURE, 40, DUR_6_SEC, RADIUS_8_YD, 421, cooldown=2 * MIN)
armor_passive("SCALED_HIDE", "SHARED", 0, "Scaled Hide", 2, 20594)
dodge("SERPENTINE_REFLEXES", B, 1, "Serpentine Reflexes", 1, 20582)
passive("STORMBLOOD", B, 2, "Stormblood", "Nature damage and healing done increased by 1%.",
        aura(1, AURA_MOD_DAMAGE_PERCENT_DONE, 1, SCHOOL_NATURE), aura(2, AURA_MOD_HEALING_DONE_PERCENT, 1, 127), icon=20583)
passive("VENOMOUS_CONSTITUTION", B, 3, "Venomous Constitution", "Duration of Poison effects on you reduced by 15%.",
        aura(1, AURA_DURATION_BY_DISPEL, -15, DISPEL_POISON), icon=20583)
for race in (SETHRAK, SETHRAK_A):
    grant(race, "STATIC_COIL", "SCALED_HIDE", "SERPENTINE_REFLEXES", "STORMBLOOD", "VENOMOUS_CONSTITUTION")

# Naga (54)
B = "NAGA"
active("COILING_GRASP", B, 0, "Coiling Grasp", "Immobilizes the target for 2 sec.", 2 * MIN,
       aura(1, AURA_MOD_ROOT, 1, 0, TARGET_ENEMY, EffectMechanic=MECHANIC_ROOT), icon=339, duration=DUR_2_SEC,
       range_index=RANGE_30, aura_description="Rooted.", extra={"Mechanic": MECHANIC_ROOT})
school_bonus("HIGHBORNE_LEGACY", B, 1, "Highborne Legacy", ALL_MAGIC_SCHOOLS, "Magical", 1, 12043)
swimmer("CHILDREN_OF_THE_DEPTHS", B, 2, "Children of the Depths", 20582)
expertise("SERPENTINE_WEAPONRY", B, 3, "Serpentine Weaponry", 3, SUBCLASS_SWORDS_POLEARMS, "swords and polearms", 20574)
grant(NAGA, "COILING_GRASP", "SCALED_HIDE", "HIGHBORNE_LEGACY", "CHILDREN_OF_THE_DEPTHS", "SERPENTINE_WEAPONRY")

# Tuskarr (55)
B = "TUSKARR"
active("HARPOON_TOSS", B, 0, "Harpoon Toss",
       "Hurl a harpoon up to 30 yards, dealing Physical damage and slowing the target by 50% for 6 sec.", 2 * MIN,
       damage(1, TARGET_ENEMY, 0, 0, SCHOOL_PHYSICAL),
       aura(2, AURA_MOD_DECREASE_SPEED, -50, 0, TARGET_ENEMY, EffectMechanic=MECHANIC_SNARE),
       icon=2764, range_index=RANGE_30, duration=DUR_6_SEC, aura_description="Movement speed reduced by 50%.")
bind("HARPOON_TOSS", "spell_race_scaled_damage")
passive("THICK_BLUBBER", B, 1, "Thick Blubber", "Stamina increased by 1% and Frost damage taken reduced by 1%.",
        aura(1, AURA_MOD_PERCENT_STAT, 1, STAT_STAMINA), aura(2, AURA_MOD_DAMAGE_PERCENT_TAKEN, -1, SCHOOL_FROST), icon=20592)
passive("SNOWSTRIDER", B, 2, "Snowstrider", "Duration of movement-slowing effects on you reduced by 10%.",
        aura(1, AURA_MECHANIC_DURATION_MOD, -10, MECHANIC_SNARE), icon=20592)
skill_passive("MASTER_ANGLER", "SHARED", 1, "Master Angler", SKILL_FISHING, 15, "Fishing", 7620)
passive("HEARTY_MEALS", B, 3, "Hearty Meals", "Well Fed bonuses are 10% stronger.", aura(1, AURA_DUMMY, 1), icon=2639)
grant(TUSKARR, "HARPOON_TOSS", "THICK_BLUBBER", "SNOWSTRIDER", "MASTER_ANGLER", "HEARTY_MEALS")

# Vrykul (56 / 57)
B = "VRYKUL"
haste_burst("RUNIC_WARCRY", B, 0, "Runic Warcry", "Increases melee, ranged and spell haste by 10% for 10 sec.", 10, 6673)
passive("GIANTS_BLOOD", B, 1, "Giant's Blood", "Strength and Stamina increased by 1%.",
        aura(1, AURA_MOD_PERCENT_STAT, 1, STAT_STRENGTH), aura(2, AURA_MOD_PERCENT_STAT, 1, STAT_STAMINA), icon=20550)
crit("RUNIC_HERITAGE", B, 2, "Runic Heritage", 1, 6673)
passive("IRON_WILL", B, 3, "Iron Will", "Duration of stun effects on you reduced by 10%.",
        aura(1, AURA_MECHANIC_DURATION_MOD, -10, MECHANIC_STUN), icon=20550)
skill_passive("RUNECARVER", B, 4, "Runecarver", SKILL_BLACKSMITHING, 5, "Blacksmithing", 2018)
for race in (VRYKUL_A, VRYKUL_H):
    grant(race, "RUNIC_WARCRY", "GIANTS_BLOOD", "RUNIC_HERITAGE", "IRON_WILL", "RUNECARVER")

# Forgotten (58 / 59)
B = "FORGOTTEN"
active("DESPERATE_FLIGHT", B, 0, "Desperate Flight", "Removes roots and snares and increases movement speed by 20% for 6 sec.",
       2 * MIN, aura(1, AURA_MOD_INCREASE_SPEED, 20),
       {"Effect_2": EFFECT_DISPEL_MECHANIC, "EffectDieSides_2": 1, "EffectBasePoints_2": 0, "EffectMiscValue_2": MECHANIC_ROOT,
        "ImplicitTargetA_2": SELF, "EffectAura_2": 0},
       {"Effect_3": EFFECT_DISPEL_MECHANIC, "EffectDieSides_3": 1, "EffectBasePoints_3": 0, "EffectMiscValue_3": MECHANIC_SNARE,
        "ImplicitTargetA_3": SELF, "EffectAura_3": 0},
       icon=2983, duration=DUR_6_SEC, aura_description="Movement speed increased by 20%.")
dodge("WIRY_FRAME", B, 1, "Wiry Frame", 1, 20582)
haste_passive("NERVOUS_ENERGY", B, 2, "Nervous Energy", 1, 2983)
passive("MAKE_DO", B, 3, "Make Do", "Food, drink and bandages restore 10% more health or mana.", aura(1, AURA_DUMMY, 1), icon=2639)
skill_passive("FIELD_DRESSING", B, 4, "Field Dressing", SKILL_FIRST_AID, 15, "First Aid", 3274,
              text="First Aid skill increased by 15 (bandage healing is covered by Make Do).")
for race in (FORGOTTEN_A, FORGOTTEN_H):
    grant(race, "DESPERATE_FLIGHT", "WIRY_FRAME", "NERVOUS_ENERGY", "MAKE_DO", "FIELD_DRESSING")

# Ogre (60 / 61)
B = "OGRE"
active("HEADBUTT", B, 0, "Headbutt", "Stuns a nearby enemy for 2 sec.", 2 * MIN,
       aura(1, AURA_MOD_STUN, 1, 0, TARGET_ENEMY, EffectMechanic=MECHANIC_STUN), icon=1464, duration=DUR_2_SEC,
       range_index=RANGE_MELEE, aura_description="Stunned.", extra={"Mechanic": MECHANIC_STUN})
passive("BRUTE_STRENGTH", B, 1, "Brute Strength", "Strength increased by 2%.", aura(1, AURA_MOD_PERCENT_STAT, 2, STAT_STRENGTH), icon=20550)
armor_passive("THICK_HIDE", B, 2, "Thick Hide", 2, 20594)
expertise("HEAVY_HANDS", B, 3, "Heavy Hands", 3, SUBCLASS_MACES_FISTS, "maces and fist weapons", 20574)
skill_passive("OGRE_CUISINE", B, 4, "Ogre Cuisine", SKILL_COOKING, 5, "Cooking", 818)
for race in (OGRE_H, OGRE_A):
    grant(race, "HEADBUTT", "BRUTE_STRENGTH", "THICK_HIDE", "HEAVY_HANDS", "OGRE_CUISINE")

# Gnoll (63)
B = "GNOLL"
active("SAVAGE_BITE", B, 0, "Savage Bite", "Bite the target, dealing Physical damage and causing it to bleed for 6 sec.", 2 * MIN,
       damage(1, TARGET_ENEMY, 0, 0, SCHOOL_PHYSICAL),
       aura(2, AURA_PERIODIC_DAMAGE, 1, 0, TARGET_ENEMY, EffectAuraPeriod=2000, EffectMechanic=MECHANIC_BLEED),
       icon=1079, range_index=RANGE_MELEE, duration=DUR_6_SEC, aura_description="Bleeding.", extra={"Mechanic": MECHANIC_BLEED})
bind("SAVAGE_BITE", "spell_race_scaled_damage")
bind("SAVAGE_BITE", "spell_race_scaled_bleed")
crit("PACK_HUNTER", B, 1, "Pack Hunter", 1, 20582)
passive("KEEN_NOSE", B, 2, "Keen Nose", "Stealth detection increased.", aura(1, AURA_MOD_STEALTH_DETECT, 20, 0), icon=1494)
skill_passive("SCAVENGER", B, 3, "Scavenger", SKILL_SKINNING, 5, "Skinning", 8613)
passive("SCRAPPY", B, 4, "Scrappy", "Duration of bleeds on you reduced by 10% and bleed damage taken reduced by 1%.",
        aura(1, AURA_MECHANIC_DURATION_MOD, -10, MECHANIC_BLEED), aura(2, AURA_MECHANIC_DAMAGE_TAKEN, -1, MECHANIC_BLEED),
        icon=20550)
grant(GNOLL, "SAVAGE_BITE", "PACK_HUNTER", "KEEN_NOSE", "SCAVENGER", "SCRAPPY")

# Saberon (64)
B = "SABERON"
active("POUNCE", B, 0, "Pounce", "Leap to an enemy within 15 yards and daze it for 2 sec.", 2 * MIN,
       dummy(1, TARGET_ENEMY), icon=9821, range_index=RANGE_15)
bind("POUNCE", "spell_race_pounce")
child("POUNCE_DAZE", B, 1, "Pounce", "Dazed: movement speed reduced.",
      aura(1, AURA_MOD_DECREASE_SPEED, -50, 0, TARGET_ENEMY, EffectMechanic=MECHANIC_DAZE), debuff=True, duration=DUR_2_SEC,
      icon=9821, extra={"Mechanic": MECHANIC_DAZE})
crit("PREDATORY_INSTINCTS", B, 2, "Predatory Instincts", 1, 20582)
dodge("FELINE_AGILITY", B, 3, "Feline Agility", 1, 20582)
hunters_pace("HUNTERS_PACE", B, 4, "Hunter's Pace", 2983)
school_ward("THICK_FUR", B, 6, "Thick Fur", SCHOOL_PHYSICAL, "Physical", 1, 20594)
grant(SABERON, "POUNCE", "PREDATORY_INSTINCTS", "FELINE_AGILITY", "HUNTERS_PACE", "THICK_FUR")

# Jinyu (65)
B = "JINYU"
active("TIDAL_MEND", B, 0, "Tidal Mend", "Heals you or an ally for 15% of maximum health over 6 sec.", 2 * MIN,
       aura(1, AURA_PERIODIC_HEAL, 1, 0, TARGET_ALLY, EffectAuraPeriod=2000), icon=5394, range_index=RANGE_30,
       duration=DUR_6_SEC, aura_description="Healing over time.")
bind("TIDAL_MEND", "spell_race_tidal_mend")
haste_passive("FLOW_OF_THE_RIVER", B, 1, "Flow of the River", 1, 2983)
dodge("FLUID_FOOTWORK", B, 2, "Fluid Footwork", 1, 20582)
swimmer("RIVERBORN", B, 3, "Riverborn", 20582)
grant(JINYU, "TIDAL_MEND", "FLOW_OF_THE_RIVER", "FLUID_FOOTWORK", "RIVERBORN", "MASTER_ANGLER")

# Skills shared by multiple kits
grant(SKYBORNE_A)
grant(SKYBORNE_H)



# ---------------------------------------------------------------------------------------
# Deferred racials: summons, menus and systems that need code in race_racials.cpp.
# Retail texts/cooldowns are taken from warcraft.wiki.gg; deviations are stated in each text.
# ---------------------------------------------------------------------------------------
# Nightborne: Cantrips (mail through a summoned mailbox)
B = "NIGHTBORNE"
active("CANTRIPS", B, 4, "Cantrips", "Conjure up a mailbox, allowing you mail access for 1.5 min. (Other players can use it too.)",
       10 * MIN, dummy(1), icon=8690)
bind("CANTRIPS", "spell_race_cantrips")
grant(NIGHTBORNE, "CANTRIPS")

# Void Elf: Spatial Rift (cast to open a rift, recast to step through) and Ethereal Connection
B = "VOIDELF"
active("SPATIAL_RIFT", B, 4, "Spatial Rift",
       "Tear a rift in space up to 35 yards ahead. Reactivate this ability within 8 sec to teleport through the rift. "
       "(Recharges over 3 min; the rift has no visual in WotLK.)", 0, dummy(1), icon=1953)
bind("SPATIAL_RIFT", "spell_race_spatial_rift")
passive("ETHEREAL_CONNECTION", B, 5, "Ethereal Connection", "Reduces the cost of Transmogrification by 50%.",
        aura(1, AURA_DUMMY, 1), icon=20550)
child("SPATIAL_RIFT_OPEN", B, 6, "Spatial Rift", "Reactivate Spatial Rift to teleport through the rift.",
      aura(1, AURA_DUMMY, 1), duration=DUR_8_SEC, icon=1953)
bind("SPATIAL_RIFT_OPEN", "spell_race_spatial_rift_open")
grant(VOIDELF, "SPATIAL_RIFT", "ETHEREAL_CONNECTION")

# Lightforged Draenei: Forge of Light (summons an anvil, which is what the retail Forge of Light acts as)
B = "LIGHTFORGED"
active("FORGE_OF_LIGHT", B, 7, "Forge of Light",
       "Summon a Forge of Light for 2 min, enabling Blacksmithing and Engineering, and raise your Blacksmithing skill by 5.",
       15 * MIN, dummy(1), icon=2018, cast_time=CAST_2_SEC)
bind("FORGE_OF_LIGHT", "spell_race_forge_of_light")
child("FORGE_OF_LIGHT_SKILL", B, 8, "Forge of Light", "Blacksmithing skill increased by 5.",
      skill(1, SKILL_BLACKSMITHING, 5), duration=DUR_2_MIN, icon=2018)
grant(LIGHTFORGED, "FORGE_OF_LIGHT")

# Zandalari Troll: Embrace of the Loa (menu with the six retail Loa; 5 day change cooldown)
B = "ZANDALARI"
active("EMBRACE_OF_THE_LOA", B, 3, "Embrace of the Loa",
       "Choose which Loa you embrace, gaining its boon. You can change your Loa once every 5 days.", 0, dummy(1), icon=2061)
bind("EMBRACE_OF_THE_LOA", "spell_race_embrace_of_the_loa")
passive("EMBRACE_AKUNDA", B, 4, "Embrace of Akunda",
        "Your healing spells have a chance to heal for an additional 25% of the amount healed.",
        aura(1, AURA_DUMMY, 1), icon=2061)
passive("EMBRACE_BWONSAMDI", B, 5, "Embrace of Bwonsamdi",
        "Your damaging abilities have a chance to deal additional Shadow damage and heal you for 100% of the damage dealt.",
        aura(1, AURA_DUMMY, 1), icon=2061)
passive("EMBRACE_GONK", B, 6, "Embrace of Gonk", "Movement speed increased by 5%.",
        aura(1, AURA_MOD_INCREASE_SPEED, 5), icon=2983)
passive("EMBRACE_KIMBUL", B, 7, "Embrace of Kimbul",
        "Your damaging abilities have a chance to cause the target to bleed for 6 sec. This effect stacks up to 3 times.",
        aura(1, AURA_DUMMY, 1), icon=1079)
passive("EMBRACE_KRAGWA", B, 8, "Embrace of Krag'wa",
        "Taking damage has a chance to increase your maximum health and armor by 3% for 12 sec. This effect stacks up to 3 times.",
        aura(1, AURA_DUMMY, 1), icon=20594)
passive("EMBRACE_PAKU", B, 9, "Embrace of Pa'ku",
        "Your damaging abilities have a chance to increase your critical strike chance by 4% for 12 sec.",
        aura(1, AURA_DUMMY, 1), icon=2983)
child("BWONSAMDI_SHADOW", B, 10, "Embrace of Bwonsamdi", "", damage(1, TARGET_ENEMY, 0, 0, SCHOOL_SHADOW), hidden=True, icon=2061)
bind("BWONSAMDI_SHADOW", "spell_race_bwonsamdi_shadow")
child("KIMBUL_BLEED", B, 11, "Embrace of Kimbul", "Bleeding.",
      aura(1, AURA_PERIODIC_DAMAGE, 1, 0, TARGET_ENEMY, EffectAuraPeriod=2000, EffectMechanic=MECHANIC_BLEED),
      debuff=True, duration=DUR_6_SEC, icon=1079, extra={"Mechanic": MECHANIC_BLEED, "CumulativeAura": 3})
bind("KIMBUL_BLEED", "spell_race_kimbul_bleed")
child("KRAGWA_BUFF", B, 12, "Embrace of Krag'wa", "Maximum health and armor increased by 3%.",
      aura(1, AURA_MOD_INCREASE_HEALTH_PERCENT, 3), aura(2, AURA_MOD_BASE_RESISTANCE_PCT, 3, SCHOOL_PHYSICAL),
      duration=DUR_12_SEC, icon=20594, extra={"CumulativeAura": 3})
child("PAKU_BUFF", B, 13, "Embrace of Pa'ku", "Critical strike chance increased by 4%.",
      aura(1, AURA_MOD_CRIT_PCT, 4), duration=DUR_12_SEC, icon=2983)
grant(ZANDALARI, "EMBRACE_OF_THE_LOA")
LOA_EMBRACES = ("EMBRACE_AKUNDA", "EMBRACE_BWONSAMDI", "EMBRACE_GONK", "EMBRACE_KIMBUL", "EMBRACE_KRAGWA", "EMBRACE_PAKU")

# Dark Iron Dwarf: Mole Machine (curated game_tele menu) and Dungeon Delver
B = "DARKIRON"
active("MOLE_MACHINE", B, 4, "Mole Machine",
       "Climb into a Mole Machine and burrow to a destination of your choice. (Teleports only you; usable outside combat "
       "and instances.)", 15 * MIN, dummy(1), icon=2018, cast_time=CAST_5_SEC)
bind("MOLE_MACHINE", "spell_race_mole_machine")
passive("DUNGEON_DELVER", B, 5, "Dungeon Delver", "Movement speed increased by 4% while indoors.",
        aura(1, AURA_DUMMY, 1), icon=2018)
child("DUNGEON_DELVER_SPEED", B, 6, "Dungeon Delver", "Movement speed increased by 4%.",
      aura(1, AURA_MOD_INCREASE_SPEED, 4), duration=DURATION_INFINITE, icon=2018,
      extra={"Attributes": ATTR_IS_ABILITY | ATTR_PASSIVE})
grant(DARKIRON, "MOLE_MACHINE", "DUNGEON_DELVER")

# Highmountain Tauren: Pride of Ironhorn (skill half) and Waste Not, Want Not
B = "HIGHMOUNTAIN"
skill_passive("PRIDE_OF_IRONHORN", B, 4, "Pride of Ironhorn", SKILL_MINING, 5, "Mining", 2580,
              text="Increases your Mining skill by 5. (The retail Deftness mining speed bonus is not implemented.)")
passive("WASTE_NOT_WANT_NOT", B, 5, "Waste Not, Want Not", "You have a chance to loot additional meat and fish.",
        aura(1, AURA_DUMMY, 1), icon=20550)
grant(HIGHMOUNTAIN, "PRIDE_OF_IRONHORN", "WASTE_NOT_WANT_NOT")

# Mechagnome: Mastercraft (personal anvil / forge / cooking fire) and Hyper Organic Light Originator
B = "MECHAGNOME"
passive("MASTERCRAFT", B, 4, "Mastercraft", "You function as a personal Blacksmithing Anvil, Cooking Fire, and Mining Forge.",
        aura(1, AURA_DUMMY, 1), icon=2018)
active("HOLO", B, 5, "Hyper Organic Light Originator",
       "Summon Organic Light duplicates to distract your foes for 15 sec.", 3 * MIN, dummy(1), icon=28730)
bind("HOLO", "spell_race_holo")
grant(MECHAGNOME, "MASTERCRAFT", "HOLO")

# Vulpera: camp, bag rummaging and saddlebags
B = "VULPERA"
active("MAKE_CAMP", B, 7, "Make Camp", "Make a camp at this location. Can only be used outdoors. The camp lasts 1 hour.",
       10 * MIN, dummy(1), icon=818, cast_time=CAST_5_SEC)
bind("MAKE_CAMP", "spell_race_make_camp")
active("RETURN_TO_CAMP", B, 8, "Return to Camp", "Return to your camp.", 60 * MIN, dummy(1), icon=8690,
       cast_time=CAST_10_SEC)
bind("RETURN_TO_CAMP", "spell_race_return_to_camp")
active("RUMMAGE_YOUR_BAG", B, 9, "Rummage Your Bag",
       "Change the contents of your Bag of Tricks (Physical, Fire or Frost). Now where did you put that...?", 5 * MIN,
       dummy(1), icon=21343, cast_time=CAST_3_SEC)
bind("RUMMAGE_YOUR_BAG", "spell_race_rummage_your_bag")
passive("ALPACA_SADDLEBAGS", B, 10, "Alpaca Saddlebags",
        "Grants an 8 slot Woolen Bag once. (WotLK cannot widen the backpack by 8 slots.)", aura(1, AURA_DUMMY, 1), icon=20550)
child("BAG_OF_TRICKS_FIRE", B, 11, "Bag of Tricks", "", damage(1, TARGET_ENEMY, 0, 0, SCHOOL_FIRE), hidden=True, icon=21343)
bind("BAG_OF_TRICKS_FIRE", "spell_race_scaled_damage")
child("BAG_OF_TRICKS_FROST", B, 12, "Bag of Tricks", "", damage(1, TARGET_ENEMY, 0, 0, SCHOOL_FROST), hidden=True, icon=21343)
bind("BAG_OF_TRICKS_FROST", "spell_race_scaled_damage")
grant(VULPERA, "MAKE_CAMP", "RETURN_TO_CAMP", "RUMMAGE_YOUR_BAG", "ALPACA_SADDLEBAGS")

# Pandaren: Inner Peace
B = "PANDAREN"
passive("INNER_PEACE", B, 5, "Inner Peace", "You earn twice as much rested experience.", aura(1, AURA_DUMMY, 1), icon=2639)
for race in (PANDAREN_A, PANDAREN_H):
    grant(race, "INNER_PEACE")

# Dracthyr: Soar (free flight: right-click the buff to land), Visage and Chosen Identity
B = "DRACTHYR"
AURA_FLY, AURA_MOD_INCREASE_FLIGHT_SPEED = 201, 207
active("SOAR", B, 4, "Soar",
       "Take to the air in free flight, increasing flight speed by 60%. Cancel the effect to land.",
       3 * ICD, aura(1, AURA_FLY, 0), aura(2, AURA_MOD_INCREASE_FLIGHT_SPEED, 60), icon=2983, duration=DURATION_INFINITE,
       aura_description="Flying freely. Flight speed increased by 60%.")
active("VISAGE", B, 5, "Visage", "Assume your visage, a mortal form. Use again to return to dracthyr form.", 5 * ICD,
       dummy(1), icon=20550)
bind("VISAGE", "spell_race_visage")
child("VISAGE_FORM", B, 6, "Visage", "In visage form.", aura(1, AURA_DUMMY, 1), duration=DURATION_INFINITE, icon=20550)
bind("VISAGE_FORM", "spell_race_visage_form")
active("CHOSEN_IDENTITY", B, 7, "Chosen Identity", "Choose the mortal race your Visage takes.", 0, dummy(1), icon=20550)
bind("CHOSEN_IDENTITY", "spell_race_chosen_identity")
grant(DRACTHYR, "SOAR", "VISAGE", "CHOSEN_IDENTITY")

# Earthen: Ingest Minerals (gem -> Well Fed substitute) and Quiet Contemplation
B = "EARTHEN"
active("INGEST_MINERALS", B, 7, "Ingest Minerals",
       "Consume a gem to gain an Earthen Well Fed benefit for 1 hour: Ruby (red/orange) Critical Strike, Sapphire (blue) damage "
       "and healing, Amber (yellow) Stamina, Emerald (green) Haste, Onyx (purple/prismatic) attack and spell power.",
       0, dummy(1), icon=2580)
bind("INGEST_MINERALS", "spell_race_ingest_minerals")
_add("QUIET_CONTEMPLATION", B, 8, "Quiet Contemplation",
     merge({"RecoveryTime": 1000, "DurationIndex": DUR_20_SEC, "RangeIndex": RANGE_SELF},
           aura(1, AURA_PERIODIC_HEAL, 1, 0, SELF, EffectAuraPeriod=2000),
           aura(2, AURA_PERIODIC_ENERGIZE, 1, 0, SELF, EffectAuraPeriod=2000)),
     "Racial", "Draws upon your inner energy, restoring 35% of your health and mana over 20 sec. You must remain seated.",
     "Restoring health and mana.", 2639, donor=FOOD_DONOR)
bind("QUIET_CONTEMPLATION", "spell_race_quiet_contemplation")
for slot, (key, label, effects) in enumerate((
        ("AMBER", "Stamina increased by 5%.", (aura(1, AURA_MOD_PERCENT_STAT, 5, STAT_STAMINA),)),
        ("EMERALD", "Haste increased by 3%.", haste(3)),
        ("ONYX", "Attack power increased by 60 and spell power by 30.",
         (aura(1, AURA_MOD_ATTACK_POWER, 60), aura(2, AURA_MOD_DAMAGE_DONE, 30, 126))),
        ("RUBY", "Critical strike chance increased by 2%.", (aura(1, AURA_MOD_CRIT_PCT, 2),)),
        ("SAPPHIRE", "Damage and healing done increased by 2%.",
         (aura(1, AURA_MOD_DAMAGE_PERCENT_DONE, 2, 127), aura(2, AURA_MOD_HEALING_DONE_PERCENT, 2, 127)))), start=9):
    child(f"INGEST_{key}", B, slot, "Ingest Minerals", label, *effects, duration=DUR_1_HOUR, icon=2580)
INGEST_BUFFS = ("INGEST_AMBER", "INGEST_EMERALD", "INGEST_ONYX", "INGEST_RUBY", "INGEST_SAPPHIRE")
for race in (EARTHEN_A, EARTHEN_H):
    grant(race, "INGEST_MINERALS", "QUIET_CONTEMPLATION")

# Haranir: Rootwalking (the World Tree stands in for the Cradle)
B = "HARANIR"
active("ROOTWALKING", B, 6, "Rootwalking",
       "Perform a ritualistic dance to travel through the roots to the World Tree. (Retail goes to the Cradle in Harandar and "
       "has no cooldown.)", 30 * MIN, dummy(1), icon=5185, cast_time=CAST_10_SEC)
bind("ROOTWALKING", "spell_race_rootwalking")
for race in (HARANIR_A, HARANIR_H):
    grant(race, "ROOTWALKING")

# World objects the deferred racials spawn. Stock entries are reused wherever they exist; the rest are new.
GO_MAILBOX, GO_ANVIL, GO_CAMPFIRE, GO_INVISIBLE_COOKING = 143990, 1744, 1798, 184911
CREATURE_HOLO_DECOY = 9100001
GO_INVISIBLE_ANVIL, GO_INVISIBLE_FORGE = 9100101, 9100102
# game_tele ids (verified against data/sql/base/db_world/game_tele.sql), minimum level and menu label.
MOLE_DESTINATIONS = ((507, 1, "Ironforge"), (72, 35, "The Badlands"), (1258, 40, "Uldaman"), (821, 43, "Searing Gorge"),
                     (179, 50, "Burning Steppes"), (100, 52, "Blackrock Depths"), (1398, 74, "Dalaran"),
                     (1405, 77, "The Storm Peaks"))
GAME_TELE_WORLD_TREE = 1489   # HyjalTheWorldTree
# Races Chosen Identity offers (ChrRaces ids of the stock player races; Visage uses their PlayerInfo display ids).
IDENTITY_RACES = ((1, "Human"), (2, "Orc"), (3, "Dwarf"), (4, "Night Elf"), (5, "Undead"), (6, "Tauren"), (7, "Gnome"),
                  (8, "Troll"), (10, "Blood Elf"), (11, "Draenei"))
LOA_COOLDOWN_DAYS = 5
ITEM_ALPACA_BAG = 4240
WORLD_OBJECTS_SQL = f"""
-- Racials listed here are not granted (and are removed at login); empty by default.
CREATE TABLE IF NOT EXISTS `custom_race_racial_skip` (`spell` INT UNSIGNED NOT NULL, PRIMARY KEY (`spell`));

-- Hyper Organic Light Originator decoy: a passive humanoid that Clone Me! dresses as the caster.
DELETE FROM `creature_template` WHERE `entry` = {CREATURE_HOLO_DECOY};
INSERT INTO `creature_template` (`entry`, `name`, `subname`, `minlevel`, `maxlevel`, `faction`, `speed_walk`, `speed_run`, `BaseAttackTime`, `RangeAttackTime`, `unit_class`, `type`, `DamageModifier`, `flags_extra`) VALUES
({CREATURE_HOLO_DECOY}, 'Organic Light', 'Hyper Organic Light Originator', 1, 1, 35, 1, 1.14286, 2000, 2000, 1, 7, 0, 64);
DELETE FROM `creature_template_model` WHERE `CreatureID` = {CREATURE_HOLO_DECOY};
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`) VALUES
({CREATURE_HOLO_DECOY}, 0, 11686, 1, 1);

-- Mastercraft: invisible spell-focus objects (Data0 = SpellFocusObject id: 1 anvil, 3 forge; Data1 = radius).
DELETE FROM `gameobject_template` WHERE `entry` IN ({GO_INVISIBLE_ANVIL}, {GO_INVISIBLE_FORGE});
INSERT INTO `gameobject_template` (`entry`, `type`, `displayId`, `name`, `size`, `Data0`, `Data1`) VALUES
({GO_INVISIBLE_ANVIL}, 8, 0, 'Invisible Anvil Object', 1, 1, 10),
({GO_INVISIBLE_FORGE}, 8, 0, 'Invisible Forge Object', 1, 3, 10);
"""


# Retail icons (FileDataIDs of Retail 12.1.0.69933), keyed by racial. Light's Judgment (1717022) and Lash Out
# (7491035) are listed in retail but not stored in the local CASC install, so they keep stock icons.
# Each entry below was read back from the local install. The client stage extracts them from the
# retail CASC install and gives each its own SpellIcon.dbc row; the server rows keep stock donor icons.
RETAIL_ICONS: dict[str, int] = {
    "ARCANE_PULSE": 1851463, "MAGICAL_AFFINITY": 1723986, "ARCANE_RESISTANCE": 1723997, "ANCIENT_HISTORY": 1723985,
    "ENTROPIC_EMBRACE": 1723992, "ENTROPIC_EMBRACE_BUFF": 1723992, "PRETERNATURAL_CALM": 1724001, "CHILL_OF_NIGHT": 1723989,
    "LIGHTS_RECKONING": 1723994,
    "LIGHTS_RECKONING_DAMAGE": 1723994, "LIGHTS_RECKONING_HEAL": 1723994, "HOLY_PROVIDENCE": 1723996, "DEMONBANE": 1723990,
    "REGENERATIN": 1850550, "CITY_OF_GOLD": 1850547, "PTERRORDAX_SWOOP": 1850549,
    "FIREBLOOD": 1786406, "FIREBLOOD_BUFF": 1786406, "FORGED_IN_FLAMES": 1786407, "MASS_PRODUCTION": 1786408,
    "BULL_RUSH": 1723987, "BULL_RUSH_KNOCKDOWN": 1723987, "MOUNTAINEER": 1723999, "RUGGED_TENACITY": 1724003,
    "COMBAT_ANALYSIS": 3192685, "COMBAT_ANALYSIS_STACK": 3192685, "EMERGENCY_FAILSAFE": 3192688, "SKELETON_PINKIE": 3192689,
    "BAG_OF_TRICKS": 3193416, "BAG_OF_TRICKS_DAMAGE": 3193416, "BAG_OF_TRICKS_SLOW": 3193416, "BAG_OF_TRICKS_HEAL": 3193416,
    "BAG_OF_TRICKS_SPEED": 3193416, "NOSE_FOR_TROUBLE": 3193419, "VULPERA_FIRE_RESISTANCE": 3193417,
    "QUAKING_PALM": 572035, "EPICUREAN": 571692, "GOURMAND": 571693, "BOUNCY": 572033,
    "WING_BUFFET": 4622488, "DRACTHYR_GLIDE": 4622484, "AWAKENED": 4622481, "DISCERNING_EYE": 4630415,
    "AZERITE_SURGE": 5788297, "AZERITE_SURGE_DAMAGE": 5788297, "AZERITE_SURGE_HEAL": 5788297, "AZERITE_SURGE_STRIKE": 5788297,
    "TITAN_WROUGHT_FRAME": 5788302, "WIDE_EYED_WONDER": 5788303, "HYPER_PRODUCTIVE": 5788298,
    "THORN_BLOOM": 7491039, "THORN_BLOOM_DAMAGE": 7491039, "THORN_BLOOM_HEAL": 7491039,
    "SUBTERRANEAN_PREDATOR": 7491038, "ONE_WITH_NATURE": 7491036,
}
# Stock WotLK spells whose cast animation and effect (SpellVisualID) each racial borrows until a retail effect is
# ported. Without a visual the client plays no cast animation and shows nothing.
VISUAL_DONORS: dict[str, int] = {
    "ARCANE_PULSE": 1449, "ENTROPIC_EMBRACE_BUFF": 976, "LIGHTS_JUDGMENT": 879, "LIGHTS_JUDGMENT_DAMAGE": 15237,
    "LIGHTS_RECKONING_DAMAGE": 15237, "LIGHTS_RECKONING_HEAL": 23455, "REGENERATIN": 740, "PTERRORDAX_SWOOP": 130,
    "FIREBLOOD": 2825, "FIREBLOOD_BUFF": 2825, "BULL_RUSH": 100, "BULL_RUSH_KNOCKDOWN": 853,
    "BAG_OF_TRICKS": 30455, "BAG_OF_TRICKS_DAMAGE": 30455, "BAG_OF_TRICKS_SLOW": 1715, "BAG_OF_TRICKS_HEAL": 2050,
    "BAG_OF_TRICKS_SPEED": 2983, "BAG_OF_TRICKS_FIRE": 2136, "BAG_OF_TRICKS_FROST": 116,
    "QUAKING_PALM": 1776, "WING_BUFFET": 18500, "DRACTHYR_GLIDE": 130, "SKYBORNE_GLIDE": 130,
    "AZERITE_SURGE": 2120, "AZERITE_SURGE_DAMAGE": 2136, "AZERITE_SURGE_HEAL": 23455, "AZERITE_SURGE_STRIKE": 133,
    "THORN_BLOOM": 339, "THORN_BLOOM_DAMAGE": 8921, "THORN_BLOOM_HEAL": 774,
    "FELBLOOD_SURGE": 2825, "EDICT_OF_THE_HIGH_ORDER": 6673, "RUNIC_WARCRY": 6673, "GALE_STEP": 2983,
    "DESPERATE_FLIGHT": 2983, "STATIC_COIL": 6343, "COILING_GRASP": 339, "HARPOON_TOSS": 30455,
    "HEADBUTT": 6552, "SAVAGE_BITE": 1822, "POUNCE": 9005, "POUNCE_DAZE": 1715, "TIDAL_MEND": 139,
    "CANTRIPS": 587, "SPATIAL_RIFT": 1953, "SPATIAL_RIFT_OPEN": 1953, "FORGE_OF_LIGHT": 587, "MOLE_MACHINE": 8690,
    "HOLO": 1856, "MAKE_CAMP": 587, "RETURN_TO_CAMP": 8690, "RUMMAGE_YOUR_BAG": 587, "SOAR": 130,
    "VISAGE": 783, "ROOTWALKING": 8690,
}
# Spells with a cast time must be interrupted by movement and pushback or the client keeps "casting" while walking.
CAST_INTERRUPT_FLAGS = 0x0F
INSTANT_CAST = 1

SPELL_ICON_BASE = 92000   # SpellIcon.dbc ids for the retail icons; the stage asserts they are free


def retail_icon_ids() -> dict[int, int]:
    """FileDataID -> SpellIcon.dbc id, in a stable order."""
    return {fdid: SPELL_ICON_BASE + index for index, fdid in enumerate(sorted(set(RETAIL_ICONS.values())))}


# ---------------------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------------------
def spell_spec() -> tuple[Spell, ...]:
    return tuple(SPELLS)


def prepare(table: Wdbc, retail_icons: bool = False, ported: frozenset = frozenset()) -> list[Prepared]:
    index, columns = field_index(), spell_columns()
    rows = {row[0]: row for row in table.rows}

    def donor(spell_id: int) -> list[int]:
        if spell_id not in rows:
            raise ValueError(f"Spell.dbc donor {spell_id} is missing")
        return list(rows[spell_id])

    prepared = []
    for spell in SPELLS:
        row = donor(spell.donor)
        row[0] = spell.spell_id
        for name, value in spell.fields.items():
            if name not in index:
                raise ValueError(f"{spell.name}: unknown spell_dbc column {name}")
            row[index[name]] = _pack(value, columns[index[name]][1])
        row[index["SpellIconID"]] = donor(ICONS[spell.spell_id])[index["SpellIconID"]]
        key = next(k for k, v in KEYS.items() if v == spell.spell_id)
        if retail_icons and key in RETAIL_ICONS:
            row[index["SpellIconID"]] = retail_icon_ids()[RETAIL_ICONS[key]]
        if key in VISUAL_DONORS:
            source = donor(VISUAL_DONORS[key])
            for column in ("SpellVisualID_1", "SpellVisualID_2"):
                row[index[column]] = source[index[column]]
            if key in ported:    # a retail visual was ported for this racial (race_racial_visuals); it replaces the donor's
                row[index["SpellVisualID_1"]], row[index["SpellVisualID_2"]] = race_racial_visuals.visual_id(key), 0
        passive = row[index["Attributes"]] & ATTR_PASSIVE
        if (not passive and row[index["CastingTimeIndex"]] != INSTANT_CAST and not row[index["InterruptFlags"]]
                and not row[index["ChannelInterruptFlags"]]):
            row[index["InterruptFlags"]] = CAST_INTERRUPT_FLAGS
        for name in ("Name_Lang_enUS", "NameSubtext_Lang_enUS", "Description_Lang_enUS", "AuraDescription_Lang_enUS"):
            row[index[name]] = 0
        prepared.append(Prepared(spell, row))
    return prepared


def merge_spell_table(data: bytes, retail_icons: bool = False, ported: frozenset = frozenset()) -> bytes:
    """Append every racial the table does not already carry (client stage: ``retail_icons=True``, ``ported`` = keys with a retail visual)."""
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
    position = {row[0]: i for i, row in enumerate(table.rows)}
    for item in prepare(table, retail_icons, ported):
        spell_id = item.spell.spell_id
        if spell_id in existing:
            owner = table.rows[position[spell_id]]
            if table.text(owner[index["Name_Lang_enUS"]]) != item.spell.name:
                raise ValueError(f"spell id {spell_id} already belongs to another spell")
            slot = position[spell_id]
            records[slot] = item.row     # the spec is the source of truth, so a re-run refreshes the row
        else:
            slot = len(records)
            records.append(item.row)
        for column, attribute in TEXT_COLUMNS:
            value = getattr(item.spell, attribute)
            if value:
                strings[(slot, index[column])] = value
            else:
                strings.pop((slot, index[column]), None)
    return build_wdbc(records, table.fields, table.record_size, strings)


def render_sql(data: bytes) -> str:
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

    spell_ids = ", ".join(str(spell.spell_id) for spell in SPELLS)
    script_ids = ", ".join(sorted({str(KEYS[key]) for key, _ in BINDINGS}, key=int))
    scripts = ",\n".join(f"({KEYS[key]}, {_quote(name)})" for key, name in BINDINGS)
    proc_ids = ", ".join(str(KEYS[key]) for key, _, _ in PROCS)
    procs = ",\n".join(f"({KEYS[key]}, 2, {chance}, {cooldown})" for key, chance, cooldown in PROCS)
    return (
        "-- GENERATED by `python tools/race_racials.py --sql-out <path>`; do not hand edit.\n"
        "-- Racial spells for the retail ports and custom races; mirrors the client Spell.dbc rows.\n"
        "\n"
        f"DELETE FROM `spell_dbc` WHERE `ID` IN ({spell_ids});\n"
        + "\n".join(statements) + "\n"
        "\n"
        f"DELETE FROM `spell_proc` WHERE `SpellId` IN ({proc_ids});\n"
        "INSERT INTO `spell_proc` (`SpellId`, `SpellPhaseMask`, `Chance`, `Cooldown`) VALUES\n" + procs + ";\n"
        "\n"
        + WORLD_OBJECTS_SQL +
        "\n"
        "-- race_racials.cpp is inert without these bindings.\n"
        f"DELETE FROM `spell_script_names` WHERE `spell_id` IN ({script_ids});\n"
        "INSERT INTO `spell_script_names` (`spell_id`, `ScriptName`) VALUES\n" + scripts + ";\n"
    )


def render_header() -> str:
    lines = ["// GENERATED by tools/race_racials.py --header-out; do not hand edit.", "#pragma once", "",
             "#include \"Define.h\"", "", "#include <array>", "#include <vector>", "", "namespace RaceRacials", "{",
             "    enum RacialSpell : uint32", "    {"]
    lines += [f"        SPELL_{key} = {spell_id}," for key, spell_id in KEYS.items()]
    lines += ["    };", "", "    struct RaceGrant", "    {", "        uint8 race;", "        std::vector<uint32> spells;", "    };", "",
              "    inline std::vector<RaceGrant> const& Grants()", "    {", "        static std::vector<RaceGrant> const grants =", "        {"]
    for race in sorted(RACE_GRANTS):
        keys = ", ".join(f"SPELL_{key}" for key in RACE_GRANTS[race])
        lines.append(f"            {{ {race}, {{ {keys} }} }},")
    lines += ["        };", "        return grants;", "    }", ""]
    lines += ["    enum RacialObject : uint32", "    {",
              f"        RACIAL_GO_MAILBOX = {GO_MAILBOX},", f"        RACIAL_GO_ANVIL = {GO_ANVIL},",
              f"        RACIAL_GO_CAMPFIRE = {GO_CAMPFIRE},", f"        RACIAL_GO_INVISIBLE_COOKING = {GO_INVISIBLE_COOKING},",
              f"        RACIAL_GO_INVISIBLE_ANVIL = {GO_INVISIBLE_ANVIL},", f"        RACIAL_GO_INVISIBLE_FORGE = {GO_INVISIBLE_FORGE},",
              f"        RACIAL_CREATURE_HOLO_DECOY = {CREATURE_HOLO_DECOY},", f"        RACIAL_ITEM_ALPACA_BAG = {ITEM_ALPACA_BAG},",
              f"        RACIAL_TELE_WORLD_TREE = {GAME_TELE_WORLD_TREE},", f"        RACIAL_LOA_COOLDOWN_DAYS = {LOA_COOLDOWN_DAYS},",
              "    };", "",
              "    struct MenuEntry", "    {", "        uint32 id;", "        uint8 minLevel;", "        char const* label;", "    };", "",
              "    inline std::vector<MenuEntry> const& MoleDestinations()", "    {", "        static std::vector<MenuEntry> const entries =",
              "        {"]
    lines += [f'            {{ {tele}, {level}, "{label}" }},' for tele, level, label in MOLE_DESTINATIONS]
    lines += ["        };", "        return entries;", "    }", "",
              "    inline std::vector<MenuEntry> const& IdentityRaces()", "    {", "        static std::vector<MenuEntry> const entries =",
              "        {"]
    lines += [f'            {{ {race}, 0, "{label}" }},' for race, label in IDENTITY_RACES]
    lines += ["        };", "        return entries;", "    }", "",
              "    inline std::vector<uint32> const& LoaEmbraces()", "    {", "        static std::vector<uint32> const spells =",
              "        {"]
    lines += [f"            SPELL_{key}," for key in LOA_EMBRACES]
    lines += ["        };", "        return spells;", "    }", "}", ""]
    return "\n".join(lines)


def check() -> None:
    ids = [spell.spell_id for spell in SPELLS]
    assert len(ids) == len(set(ids)), "duplicate spell ids"
    for race, keys in RACE_GRANTS.items():
        for key in keys:
            assert key in KEYS, (race, key)
    for key in VISUAL_DONORS:
        assert key in KEYS, key


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dbc-in", type=Path, default=DEFAULT_SPELL_DBC)
    parser.add_argument("--sql-out", type=Path)
    parser.add_argument("--header-out", type=Path)
    parser.add_argument("--dbc-out", type=Path)
    args = parser.parse_args()
    check()
    data = args.dbc_in.read_bytes()
    if args.sql_out:
        args.sql_out.write_text(render_sql(data), encoding="utf-8", newline="\n")
    if args.header_out:
        args.header_out.write_text(render_header(), encoding="utf-8", newline="\n")
    if args.dbc_out:
        args.dbc_out.parent.mkdir(parents=True, exist_ok=True)
        args.dbc_out.write_bytes(merge_spell_table(data))


if __name__ == "__main__":
    main()
