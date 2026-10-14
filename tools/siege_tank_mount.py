"""Add the Alliance Siege Tank as a hidden-passenger player-vehicle mount.

Player-as-vehicle design:
  * SPELL_AURA_TRANSFORM (56) turns the caster into the Alliance siege engine
    creature display, so the player *is* the tank (no rider body).
  * SPELL_AURA_SET_VEHICLE_ID (296) installs the multi-seat vehicle kit.
  * every VehicleSeat row sets VEHICLE_SEAT_FLAG_HIDE_PASSENGER so a boarded
    player vanishes instead of sitting on the hull.
  * SPELL_AURA_MOUNTED (78), with no separate mount model, preserves normal
    collection, dismount, pet, and map restrictions. Mounted speed is +100%.
    The vehicle kit is a linked aura removed together with the mount.

Client: WXL continuations inside PATCH-X.MPQ and matching full DBC rows in
both winning Z archives. Original siege engine model/sound data is reused.

Server: the same rows as *_dbc SQL overlays plus creature/item templates.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import cars_mount_pack as cars  # noqa: E402
import mount_pack_batch2 as batch2  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
BASELINE_DEFAULT = REPO / "DBCs" / "Latest"
CLIENT_DEFAULT = Path(r"G:\3.3.5a - Dev")
STORM_DEFAULT = cars.DLL_DEFAULT
STAGE = REPO / "var" / "siege-tank"

SLUG = "siegetank"
DISPLAY_NAME = "Alliance Siege Tank"
ICON = "ability_vehicle_siegeengineram"
SPELL_ICON_ID = 3763
SPELL_ID = 201300
VEHICLE_SPELL_ID = 201301
ITEM_ID = 901300
ITEM_DISPLAY_ID = 135100
CREATURE_ID = 3460900
VEHICLE_ID = 900305
SEAT_IDS = (900405, 900406, 900407)

DISPLAY_ID = 25292
VEHICLE_TEMPLATE_ID = 117
SEAT_TEMPLATE_ID = 1649
SPELL_TEMPLATE_ID = 61425
ITEM_TEMPLATE_ID = 18776

SPELL_AURA_TRANSFORM = 56
SPELL_AURA_SET_VEHICLE_ID = 296
SPELL_AURA_MOUNTED = 78
SPELL_AURA_MOD_INCREASE_MOUNTED_SPEED = 32
SPELL_EFFECT_APPLY_AURA = 6
TARGET_SELF = 1
HIDE_PASSENGER = 0x00000200
CAN_ENTER_OR_EXIT = 0x02000000
CAN_CONTROL = 0x00000800
CAN_CAST = 0x20000000
MOUNTED_SPEED_BASE_POINTS = 99
SEAT_ATTACHMENTS = (14, 15, 16)

CONTINUATION_TABLES = ("Spell", "Vehicle", "VehicleSeat", "SkillLineAbility")
BAKED_TABLES = ("Spell", "Vehicle", "VehicleSeat", "SkillLineAbility", "Item", "ItemDisplayInfo")


def baseline_dir(explicit: Path | None) -> Path:
    for candidate in (explicit, BASELINE_DEFAULT, REPO / "DBCs", REPO / "DBCs/.wow-toolbox-backups/.pristine"):
        if candidate and (candidate / "Spell.dbc").is_file():
            return candidate
    raise FileNotFoundError("no baseline DBC directory containing Spell.dbc")


def table(path: Path) -> cars.Wdbc:
    return cars.Wdbc(path.read_bytes())


def row(wdbc: cars.Wdbc, row_id: int, name: str) -> list[int]:
    for candidate in wdbc.rows:
        if candidate[0] == row_id:
            return list(candidate)
    raise KeyError(f"{name}.dbc has no row {row_id}")


def blank_spell_strings(spell: list[int]) -> None:
    for start, end in ((136, 152), (153, 169), (170, 186), (187, 203)):
        spell[start:end] = [0] * (end - start)


def build_rows(baseline: Path) -> dict[str, list[list[int]]]:
    spell = row(table(baseline / "Spell.dbc"), SPELL_TEMPLATE_ID, "Spell")
    spell[0] = SPELL_ID
    spell[133] = SPELL_ICON_ID
    for effect in range(3):
        spell[71 + effect] = SPELL_EFFECT_APPLY_AURA
        spell[74 + effect] = 0
        spell[77 + effect] = 0
        spell[80 + effect] = 0
        spell[83 + effect] = 0
        spell[86 + effect] = TARGET_SELF
        spell[89 + effect] = 0
        spell[92 + effect] = 0
        spell[95 + effect] = 0
        spell[98 + effect] = 0
        spell[101 + effect] = 0
        spell[104 + effect] = 0
        spell[107 + effect] = 0
        spell[110 + effect] = 0
        spell[113 + effect] = 0
        spell[116 + effect] = 0
        spell[119 + effect] = 0
    spell[95:98] = [SPELL_AURA_MOUNTED, SPELL_AURA_MOD_INCREASE_MOUNTED_SPEED, SPELL_AURA_TRANSFORM]
    spell[110:113] = [0, 0, CREATURE_ID]
    spell[81] = MOUNTED_SPEED_BASE_POINTS
    blank_spell_strings(spell)

    kit = list(spell)
    kit[0] = VEHICLE_SPELL_ID
    kit[3] = 0  # Not a second mount mechanic.
    kit[4] = 0x80  # Hidden client-side auxiliary aura.
    kit[28] = 1  # Instant; spell_linked_spell applies it as an aura.
    kit[131:133] = [0, 0]
    kit[71:74] = [SPELL_EFFECT_APPLY_AURA, 0, 0]
    kit[80:83] = [0, 0, 0]
    kit[86:89] = [TARGET_SELF, 0, 0]
    kit[95:98] = [SPELL_AURA_SET_VEHICLE_ID, 0, 0]
    kit[110:113] = [VEHICLE_ID, 0, 0]

    item = row(table(baseline / "Item.dbc"), ITEM_TEMPLATE_ID, "Item")
    item[0] = ITEM_ID
    item[5] = ITEM_DISPLAY_ID

    vehicle = row(table(baseline / "Vehicle.dbc"), VEHICLE_TEMPLATE_ID, "Vehicle")
    vehicle[0] = VEHICLE_ID
    seats = [0] * 8
    seats[1], seats[2], seats[3] = SEAT_IDS
    vehicle[6:14] = seats
    vehicle[36] = 0  # No siege weapon UI; the owner controls their own movement.

    seat_template = row(table(baseline / "VehicleSeat.dbc"), SEAT_TEMPLATE_ID, "VehicleSeat")
    vehicle_seats = []
    for seat_id, attachment in zip(SEAT_IDS, SEAT_ATTACHMENTS):
        seat = list(seat_template)
        seat[0] = seat_id
        seat[1] = (seat[1] | HIDE_PASSENGER | CAN_ENTER_OR_EXIT) & ~(CAN_CONTROL | CAN_CAST)
        seat[2] = attachment
        seat[45] |= 0x20  # Owner can eject passengers.
        vehicle_seats.append(seat)

    return {
        "Spell": [spell, kit],
        "Item": [item],
        "ItemDisplayInfo": [[ITEM_DISPLAY_ID] + [0] * 24],
        "Vehicle": [vehicle],
        "VehicleSeat": vehicle_seats,
        "SkillLineAbility": [cars.mount_skill_line_ability_row(SPELL_ID)],
    }


def build_continuations(rows: dict[str, list[list[int]]], baseline: Path) -> dict[str, bytes]:
    strings: dict[str, dict[tuple[int, int], str]] = {
        "Spell": {
            (0, 136): DISPLAY_NAME,
            (0, 170): f"Become the {DISPLAY_NAME}, carrying up to three hidden passengers at 100% increased speed.",
            (0, 187): "Movement speed increased by 100%. Party or raid members can enter the tank.",
            (1, 136): f"{DISPLAY_NAME} Passengers",
        },
        "ItemDisplayInfo": {(0, 5): ICON},
    }
    payloads: dict[str, bytes] = {}
    for name, table_rows in rows.items():
        layout = table(baseline / f"{name}.dbc")
        payloads[name] = cars.build_wdbc(table_rows, layout.fields, layout.record_size, strings.get(name, {}))
    return payloads


def continuation_entries(continuations: dict[str, bytes]) -> dict[str, bytes]:
    return {
        f"DBFilesClient/{name}.dbc1-{SLUG}": payload
        for name, payload in continuations.items()
        if name in CONTINUATION_TABLES
    }


_SPELL_FORMAT: str | None = None


def spell_format() -> str:
    global _SPELL_FORMAT
    if _SPELL_FORMAT is None:
        source = (REPO / "src/server/shared/DataStores/DBCfmt.h").read_text(encoding="utf-8")
        match = re.search(r'SpellEntryfmt\[\]\s*=\s*"([^"]+)"', source)
        if not match:
            raise ValueError("SpellEntryfmt not found in DBCfmt.h")
        _SPELL_FORMAT = match.group(1)
    return _SPELL_FORMAT


def spell_sql_values(spell: list[int], string_pool: bytes) -> list[str]:
    values: list[str] = []
    for index, kind in enumerate(spell_format()):
        raw = spell[index]
        if kind == "f":
            values.append(cars._sql_value(cars._f32_from_u32(raw)))
        elif index in cars.DBC_STRING_FIELDS["Spell"]:
            if raw == 0:
                values.append("''")
            else:
                end = string_pool.find(b"\x00", raw)
                values.append(cars._sql_value(string_pool[raw:end].decode("utf-8")))
        else:
            values.append(str(cars._i32_from_u32(raw)))
    return values

def render_sql(rows: dict[str, list[list[int]]], baseline: Path) -> str:
    layout = cars.Wdbc(build_continuations(rows, baseline)["Spell"])
    spell_values = [spell_sql_values(spell, layout.strings) for spell in layout.rows]
    spell_block = (
        "-- Full Spell.dbc row. AzerothCore replaces the whole row from `spell_dbc`,\n"
        "-- so all 234 fields are supplied in table order (one per SpellEntryfmt char).\n"
        + "\n".join(
            f"DELETE FROM `spell_dbc` WHERE `ID` = {spell[0]};\n"
            "INSERT INTO `spell_dbc` VALUES (\n" + ", ".join(values) + ");"
            for spell, values in zip(layout.rows, spell_values)
        )
    )
    linked_vehicle = cars._sql_insert(
        "spell_linked_spell", ("spell_trigger", "spell_effect", "type", "comment"),
        [(SPELL_ID, VEHICLE_SPELL_ID, 2, "Alliance Siege Tank - hidden passenger kit while mounted")],
        [SPELL_ID], "spell_trigger",
    )

    item = rows["Item"][0]
    item_block = cars._sql_insert(
        "item_dbc",
        ("ID", "ClassID", "SubclassID", "Sound_Override_Subclassid", "Material", "DisplayInfoID",
         "InventoryType", "SheatheType"),
        [(item[0], item[1], item[2], cars._i32_from_u32(item[3]), item[4], item[5], item[6], item[7])],
        [ITEM_ID],
    )
    item_display_block = cars._sql_insert(
        "itemdisplayinfo_dbc",
        ("ID", "ModelName_1", "ModelName_2", "ModelTexture_1", "ModelTexture_2", "InventoryIcon_1",
         "InventoryIcon_2", "GeosetGroup_1", "GeosetGroup_2", "GeosetGroup_3", "Flags", "SpellVisualID",
         "GroupSoundIndex", "HelmetGeosetVis_1", "HelmetGeosetVis_2", "Texture_1", "Texture_2", "Texture_3",
         "Texture_4", "Texture_5", "Texture_6", "Texture_7", "Texture_8", "ItemVisual", "ParticleColorID"),
        [(ITEM_DISPLAY_ID, "", "", "", "", ICON, "", 0, 0, 0, 0, 0, 10, 0, 0, "", "", "", "", "", "", "", "", 0, 0)],
        [ITEM_DISPLAY_ID],
    )
    vehicle = rows["Vehicle"][0]
    vehicle_block = cars._sql_insert(
        "vehicle_dbc",
        ("ID", "Flags", "TurnSpeed", "PitchSpeed", "PitchMin", "PitchMax", "SeatID_1", "SeatID_2", "SeatID_3",
         "SeatID_4", "SeatID_5", "SeatID_6", "SeatID_7", "SeatID_8", "MouseLookOffsetPitch",
         "CameraFadeDistScalarMin", "CameraFadeDistScalarMax", "CameraPitchOffset", "FacingLimitRight",
         "FacingLimitLeft", "MsslTrgtTurnLingering", "MsslTrgtPitchLingering", "MsslTrgtMouseLingering",
         "MsslTrgtEndOpacity", "MsslTrgtArcSpeed", "MsslTrgtArcRepeat", "MsslTrgtArcWidth",
         "MsslTrgtImpactRadius_1", "MsslTrgtImpactRadius_2", "MsslTrgtArcTexture", "MsslTrgtImpactTexture",
         "MsslTrgtImpactModel_1", "MsslTrgtImpactModel_2", "CameraYawOffset", "UilocomotionType",
         "MsslTrgtImpactTexRadius", "VehicleUIIndicatorID", "PowerDisplayID_1", "PowerDisplayID_2",
         "PowerDisplayID_3"),
        [cars._vehicle_sql_row(tuple(vehicle))],
        [VEHICLE_ID],
    )
    vehicle_seat_columns = (
        "ID", "Flags", "AttachmentID", "AttachmentOffsetX", "AttachmentOffsetY", "AttachmentOffsetZ",
        "EnterPreDelay", "EnterSpeed", "EnterGravity", "EnterMinDuration", "EnterMaxDuration",
        "EnterMinArcHeight", "EnterMaxArcHeight", "EnterAnimStart", "EnterAnimLoop", "RideAnimStart",
        "RideAnimLoop", "RideUpperAnimStart", "RideUpperAnimLoop", "ExitPreDelay", "ExitSpeed", "ExitGravity",
        "ExitMinDuration", "ExitMaxDuration", "ExitMinArcHeight", "ExitMaxArcHeight", "ExitAnimStart",
        "ExitAnimLoop", "ExitAnimEnd", "PassengerYaw", "PassengerPitch", "PassengerRoll",
        "PassengerAttachmentID", "VehicleEnterAnim", "VehicleExitAnim", "VehicleRideAnimLoop",
        "VehicleEnterAnimBone", "VehicleExitAnimBone", "VehicleRideAnimLoopBone", "VehicleEnterAnimDelay",
        "VehicleExitAnimDelay", "VehicleAbilityDisplay", "EnterUISoundID", "ExitUISoundID", "UiSkin", "FlagsB",
        "CameraEnteringDelay", "CameraEnteringDuration", "CameraExitingDelay", "CameraExitingDuration",
        "CameraOffsetX", "CameraOffsetY", "CameraOffsetZ", "CameraPosChaseRate", "CameraFacingChaseRate",
        "CameraEnteringZoom", "CameraSeatZoomMin", "CameraSeatZoomMax",
    )
    vehicle_seat_block = cars._sql_insert(
        "vehicleseat_dbc",
        vehicle_seat_columns,
        [cars._vehicle_seat_sql_row(tuple(seat)) for seat in rows["VehicleSeat"]],
        list(SEAT_IDS),
    )
    skill_block = cars._sql_insert(
        "skilllineability_dbc",
        ("ID", "SkillLine", "Spell", "RaceMask", "ClassMask", "ExcludeRace", "ExcludeClass", "MinSkillLineRank",
         "SupercededBySpell", "AcquireMethod", "TrivialSkillLineRankHigh", "TrivialSkillLineRankLow",
         "CharacterPoints_1", "CharacterPoints_2"),
        [tuple(cars.mount_skill_line_ability_row(SPELL_ID))],
        [SPELL_ID],
    )
    creature_template_model = cars._sql_insert(
        "creature_template_model",
        ("CreatureID", "Idx", "CreatureDisplayID", "DisplayScale", "Probability", "VerifiedBuild"),
        [(CREATURE_ID, 0, DISPLAY_ID, 1, 1, 12340)],
        [CREATURE_ID],
        "CreatureID",
    )
    creature_template = cars._sql_insert(
        "creature_template",
        ("entry", "name", "IconName", "minlevel", "maxlevel", "exp", "faction", "npcflag", "rank", "dmgschool",
         "BaseAttackTime", "RangeAttackTime", "unit_class", "unit_flags", "unit_flags2", "type", "type_flags",
         "lootid", "skinloot", "VehicleId", "AIName", "MovementType", "HoverHeight", "ExperienceModifier",
         "RacialLeader", "movementId", "RegenHealth", "flags_extra", "ScriptName"),
        [(CREATURE_ID, DISPLAY_NAME, "", 1, 1, 0, 35, 0, 0, 0, 2000, 2000, 1, 0, 2048, 1, 0, 0, 0, VEHICLE_ID,
          "", 0, 1, 1, 0, 140, 1, 0, "")],
        [CREATURE_ID],
        "entry",
        "REPLACE",
        False,
    )
    item_template = cars._sql_insert(
        "item_template",
        ("entry", "class", "subclass", "SoundOverrideSubclass", "name", "displayid", "Quality", "Flags",
         "FlagsExtra", "BuyCount", "BuyPrice", "SellPrice", "InventoryType", "AllowableClass", "AllowableRace",
         "ItemLevel", "RequiredLevel", "RequiredSkill", "RequiredSkillRank", "maxcount", "stackable",
         "ContainerSlots", "bonding", "description", "Material", "sheath", "RandomProperty", "RandomSuffix",
         "block", "itemset", "MaxDurability", "area", "Map", "BagFamily", "TotemCategory", "duration",
         "ItemLimitCategory", "HolidayId", "ScriptName", "DisenchantID", "FoodType", "minMoneyLoot",
         "maxMoneyLoot", "flagsCustom", "VerifiedBuild", "spellid_1", "spelltrigger_1", "spellcharges_1",
         "spellppmRate_1", "spellcooldown_1", "spellcategory_1", "spellcategorycooldown_1", "spellid_2",
         "spelltrigger_2", "spellcharges_2", "spellppmRate_2", "spellcooldown_2", "spellcategory_2",
         "spellcategorycooldown_2"),
        [(ITEM_ID, 15, 5, -1, f"Reins of the {DISPLAY_NAME}", ITEM_DISPLAY_ID, 4, 0, 0, 1, 0, 0, 0, 262143, -1,
          80, 40, 762, 150, 1, 1, 0, 1, f"Teaches you how to ride the {DISPLAY_NAME}.", 4, 0, 0, 0, 0, 0, 0, 0,
          0, 128, 0, 0, 0, 0, "", 0, 0, 0, 0, 0, 12340, 483, 0, -1, 0, -1, 330, 3000, SPELL_ID, 6, 0, 0, -1, 0,
          -1)],
        [ITEM_ID],
        "entry",
        "REPLACE",
        False,
    )
    sql = "\n\n".join((
        "-- Alliance Siege Tank (see tools/siege_tank_mount.py).\n"
        "-- Player-as-vehicle: transform display + multi-seat kit, passengers hidden.",
        creature_template_model,
        creature_template,
        item_template,
        spell_block,
        linked_vehicle,
        item_block,
        item_display_block,
        vehicle_block,
        vehicle_seat_block,
        skill_block,
    )) + "\n"
    # Break only at commas outside SQL string literals.
    lines = []
    for line in sql.splitlines():
        current = ""
        for token in re.split(r",(?=(?:[^']*'[^']*')*[^']*$)", line):
            if current and len(current) + len(token) + 2 > 120:
                lines.append(current + ",")
                current = "    " + token.lstrip()
            else:
                current += ("," if current else "") + token
        lines.append(current)
    return "\n".join(lines) + "\n"


def stage(baseline: Path) -> dict[str, Path]:
    rows = build_rows(baseline)
    continuations = build_continuations(rows, baseline)
    STAGE.mkdir(parents=True, exist_ok=True)
    written: dict[str, Path] = {}
    for name, payload in continuations.items():
        path = STAGE / f"{name}.dbc1-{SLUG}"
        path.write_bytes(payload)
        written[name] = path
    sql_path = STAGE / "alliance_siege_tank_mount.sql"
    sql_path.write_text(render_sql(rows, baseline), encoding="utf-8", newline="\n")
    written["sql"] = sql_path
    manifest = {
        "slug": SLUG,
        "name": DISPLAY_NAME,
        "baseline": str(baseline),
        "spell": SPELL_ID,
        "vehicle_spell": VEHICLE_SPELL_ID,
        "spell_icon": SPELL_ICON_ID,
        "item": ITEM_ID,
        "item_display": ITEM_DISPLAY_ID,
        "creature": CREATURE_ID,
        "display": DISPLAY_ID,
        "vehicle": VEHICLE_ID,
        "seats": list(SEAT_IDS),
        "continuations": sorted(f"DBFilesClient/{n}.dbc1-{SLUG}" for n in CONTINUATION_TABLES),
        "baked": sorted(BAKED_TABLES),
    }
    manifest_path = STAGE / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    written["manifest"] = manifest_path
    return written


def deploy_client(client_root: Path, stormlib: Path, baseline: Path) -> Path:
    storm = cars.Storm(stormlib)
    data = client_root / "Data"
    patch_x = batch2._case_insensitive_file(data, "PATCH-X.MPQ")
    root_z = batch2._case_insensitive_file(data, "patch-Z.MPQ")
    locale_z = batch2._case_insensitive_file(data / "enUS", "patch-enUS-Z.MPQ")
    if patch_x is None or root_z is None or locale_z is None:
        raise FileNotFoundError("PATCH-X and both Z archives are required")

    rows = build_rows(baseline)
    continuations = build_continuations(rows, baseline)
    baked: dict[str, bytes] = {}
    for name in BAKED_TABLES:
        base, _source = batch2.read_winning_client_dbc(storm, data, name, "enUS")
        merged = batch2.merge_wdbc_replace_rows(base, continuations[name], name)
        cars.Wdbc(merged)
        baked[f"DBFilesClient\\{name}.dbc"] = merged

    backup = client_root / "Backups" / f"siege-tank-{datetime.now():%Y%m%dT%H%M%S}"
    backup.mkdir(parents=True, exist_ok=False)
    hashes = {}
    for archive in (patch_x, root_z, locale_z):
        shutil.copy2(archive, backup / archive.name)
        with archive.open("rb") as source, (backup / archive.name).open("rb") as saved:
            digest = hashlib.file_digest(source, "sha256").hexdigest()
            assert digest == hashlib.file_digest(saved, "sha256").hexdigest(), f"backup mismatch: {archive}"
            hashes[archive.name] = digest
    (backup / "sha256.json").write_text(json.dumps(hashes, indent=2) + "\n", encoding="utf-8")

    entries = continuation_entries(continuations)
    additions = ("\n".join(sorted(entries)) + "\n").encode("utf-8")
    existing = b""
    try:
        existing = cars.read_archive_entry(storm, patch_x, "wxl-dbc.manifest")
    except OSError:
        pass
    entries["wxl-dbc.manifest"] = cars.merge_wxl_manifest(existing, additions)
    try:
        storm.replace_archive_entries(patch_x, entries)
        for archive in (root_z, locale_z):
            storm.replace_archive_entries(archive, baked)
        verify(baseline, client_root, stormlib)
    except Exception:
        for archive in (patch_x, root_z, locale_z):
            shutil.copy2(backup / archive.name, archive)
        raise
    return backup


def verify(baseline: Path, client_root: Path | None = None, stormlib: Path | None = None) -> None:
    rows = build_rows(baseline)
    spell = rows["Spell"][0]
    assert spell[0] == SPELL_ID
    assert spell[95:98] == [SPELL_AURA_MOUNTED, SPELL_AURA_MOD_INCREASE_MOUNTED_SPEED, SPELL_AURA_TRANSFORM]
    assert spell[110:113] == [0, 0, CREATURE_ID]
    assert spell[81] == MOUNTED_SPEED_BASE_POINTS
    assert rows["Spell"][1][95] == SPELL_AURA_SET_VEHICLE_ID
    assert rows["Spell"][1][110] == VEHICLE_ID
    assert rows["Vehicle"][0][0] == VEHICLE_ID
    assert rows["Vehicle"][0][7:10] == list(SEAT_IDS)
    assert rows["Vehicle"][0][6] == 0, "the driver is the vehicle base, not a passenger seat"
    for seat in rows["VehicleSeat"]:
        assert seat[1] & HIDE_PASSENGER, "every seat must hide its passenger"
        assert seat[1] & CAN_ENTER_OR_EXIT, "passengers must be able to leave"
        assert not seat[1] & (CAN_CONTROL | CAN_CAST), "passengers cannot take driver or weapon controls"
    icon_table = table(baseline / "SpellIcon.dbc")
    assert icon_table.text(row(icon_table, SPELL_ICON_ID, "SpellIcon")[1]).lower() == (
        f"interface\\icons\\{ICON}"
    )
    sql = render_sql(rows, baseline)
    assert DISPLAY_NAME in sql and "Alliance Siege Tank Passengers" in sql
    assert f"({SPELL_ID}, {VEHICLE_SPELL_ID}, 2," in sql
    assert all(len(line) <= 120 for line in sql.splitlines())
    if client_root and stormlib:
        storm = cars.Storm(stormlib)
        expected = build_continuations(rows, baseline)
        for name in BAKED_TABLES:
            payload, _ = batch2.read_winning_client_dbc(storm, client_root / "Data", name, "enUS")
            actual = cars.Wdbc(payload)
            wanted = cars.Wdbc(expected[name])
            for entry in wanted.rows:
                existing = row(actual, entry[0], name)
                for field, value in enumerate(entry):
                    if field in cars.DBC_STRING_FIELDS.get(name, ()):
                        assert actual.text(existing[field]) == wanted.text(value), (name, field)
                    else:
                        assert existing[field] == value, (name, field)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--client", type=Path, default=CLIENT_DEFAULT)
    parser.add_argument("--stormlib", type=Path, default=STORM_DEFAULT)
    parser.add_argument("--stage", action="store_true")
    parser.add_argument("--deploy-client", action="store_true")
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--verify-client", action="store_true")
    args = parser.parse_args()
    if not (args.stage or args.deploy_client or args.verify or args.verify_client):
        parser.error("choose --stage, --deploy-client, or --verify")
    baseline = baseline_dir(args.baseline)
    print(f"baseline: {baseline}")
    if args.stage:
        for name, path in sorted(stage(baseline).items()):
            print(f"staged {name}: {path}")
    if args.deploy_client:
        print(f"client deployed; backups: {deploy_client(args.client, args.stormlib, baseline)}")
    if args.verify or args.verify_client:
        live = args.deploy_client or args.verify_client
        verify(baseline, args.client if live else None, args.stormlib if live else None)
        print("verify: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
