-- Alliance Siege Tank (see tools/siege_tank_mount.py).
-- Player-as-vehicle: transform display + multi-seat kit, passengers hidden.

DELETE FROM `creature_template_model` WHERE `CreatureID` IN (3460900);
INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`,
    `VerifiedBuild`) VALUES
(3460900, 0, 25292, 1, 1, 12340);

REPLACE INTO `creature_template` (`entry`, `name`, `IconName`, `minlevel`, `maxlevel`, `exp`, `faction`, `npcflag`,
    `rank`, `dmgschool`, `BaseAttackTime`, `RangeAttackTime`, `unit_class`, `unit_flags`, `unit_flags2`, `type`,
    `type_flags`, `lootid`, `skinloot`, `VehicleId`, `AIName`, `MovementType`, `HoverHeight`, `ExperienceModifier`,
    `RacialLeader`, `movementId`, `RegenHealth`, `flags_extra`, `ScriptName`) VALUES
(3460900, 'Alliance Siege Tank', '', 1, 1, 0, 35, 0, 0, 0, 2000, 2000, 1, 0, 2048, 1, 0, 0, 0, 900305, '', 0, 1, 1, 0,
    140, 1, 0, '');

REPLACE INTO `item_template` (`entry`, `class`, `subclass`, `SoundOverrideSubclass`, `name`, `displayid`, `Quality`,
    `Flags`, `FlagsExtra`, `BuyCount`, `BuyPrice`, `SellPrice`, `InventoryType`, `AllowableClass`, `AllowableRace`,
    `ItemLevel`, `RequiredLevel`, `RequiredSkill`, `RequiredSkillRank`, `maxcount`, `stackable`, `ContainerSlots`,
    `bonding`, `description`, `Material`, `sheath`, `RandomProperty`, `RandomSuffix`, `block`, `itemset`,
    `MaxDurability`, `area`, `Map`, `BagFamily`, `TotemCategory`, `duration`, `ItemLimitCategory`, `HolidayId`,
    `ScriptName`, `DisenchantID`, `FoodType`, `minMoneyLoot`, `maxMoneyLoot`, `flagsCustom`, `VerifiedBuild`,
    `spellid_1`, `spelltrigger_1`, `spellcharges_1`, `spellppmRate_1`, `spellcooldown_1`, `spellcategory_1`,
    `spellcategorycooldown_1`, `spellid_2`, `spelltrigger_2`, `spellcharges_2`, `spellppmRate_2`, `spellcooldown_2`,
    `spellcategory_2`, `spellcategorycooldown_2`) VALUES
(901300, 15, 5, -1, 'Reins of the Alliance Siege Tank', 135100, 4, 0, 0, 1, 0, 0, 0, 262143, -1, 80, 40, 762, 150, 1, 1,
    0, 1, 'Teaches you how to ride the Alliance Siege Tank.', 4, 0, 0, 0, 0, 0, 0, 0, 0, 128, 0, 0, 0, 0, '', 0, 0, 0,
    0, 0, 12340, 483, 0, -1, 0, -1, 330, 3000, 201300, 6, 0, 0, -1, 0, -1);

-- Full Spell.dbc row. AzerothCore replaces the whole row from `spell_dbc`,
-- so all 234 fields are supplied in table order (one per SpellEntryfmt char).
DELETE FROM `spell_dbc` WHERE `ID` = 201300;
INSERT INTO `spell_dbc` VALUES (
201300, 0, 0, 21, 269582608, 0, 0, 0, 0, 0, 131072, 512, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 16, 0, 0, 31,
    0, 0, 0, 101, 0, 0, 0, 1, 21, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, -1,
    0, 0, 6, 6, 6, 0, 0, 0, 0, 0, 0, 0, 99, 0, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 78, 32, 56, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 3460900, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 12813, 0, 3763, 0, 0,
    'Alliance Siege Tank', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', 16712190, '', '', '', '', '', '',
    '', '', '', '', '', '', '', '', '', '', 16712172,
    'Become the Alliance Siege Tank, carrying up to three hidden passengers at 100% increased speed.', '', '', '', '',
    '', '', '', '', '', '', '', '', '', '', '', 16712190,
    'Movement speed increased by 100%. Party or raid members can enter the tank.', '', '', '', '', '', '', '', '', '',
    '', '', '', '', '', '', 16712190, 0, 330, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0,
    0, 0, 0);
DELETE FROM `spell_dbc` WHERE `ID` = 201301;
INSERT INTO `spell_dbc` VALUES (
201301, 0, 0, 0, 128, 0, 0, 0, 0, 0, 131072, 512, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 31, 0, 0, 0,
    101, 0, 0, 0, 1, 21, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, -1, 0, 0, 6,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 296, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    900305, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 3763, 0, 0,
    'Alliance Siege Tank Passengers', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', 16712190, '', '', '',
    '', '', '', '', '', '', '', '', '', '', '', '', '', 16712172, '', '', '', '', '', '', '', '', '', '', '', '', '',
    '', '', '', 16712190, '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', 16712190, 0, 330, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0);

DELETE FROM `spell_linked_spell` WHERE `spell_trigger` IN (201300);
INSERT INTO `spell_linked_spell` (`spell_trigger`, `spell_effect`, `type`, `comment`) VALUES
(201300, 201301, 2, 'Alliance Siege Tank - hidden passenger kit while mounted');

DELETE FROM `item_dbc` WHERE `ID` IN (901300);
INSERT INTO `item_dbc` (`ID`, `ClassID`, `SubclassID`, `Sound_Override_Subclassid`, `Material`, `DisplayInfoID`,
    `InventoryType`, `SheatheType`) VALUES
(901300, 15, 5, -1, 4, 135100, 0, 0);

DELETE FROM `itemdisplayinfo_dbc` WHERE `ID` IN (135100);
INSERT INTO `itemdisplayinfo_dbc` (`ID`, `ModelName_1`, `ModelName_2`, `ModelTexture_1`, `ModelTexture_2`,
    `InventoryIcon_1`, `InventoryIcon_2`, `GeosetGroup_1`, `GeosetGroup_2`, `GeosetGroup_3`, `Flags`, `SpellVisualID`,
    `GroupSoundIndex`, `HelmetGeosetVis_1`, `HelmetGeosetVis_2`, `Texture_1`, `Texture_2`, `Texture_3`, `Texture_4`,
    `Texture_5`, `Texture_6`, `Texture_7`, `Texture_8`, `ItemVisual`, `ParticleColorID`) VALUES
(135100, '', '', '', '', 'ability_vehicle_siegeengineram', '', 0, 0, 0, 0, 0, 10, 0, 0, '', '', '', '', '', '', '', '',
    0, 0);

DELETE FROM `vehicle_dbc` WHERE `ID` IN (900305);
INSERT INTO `vehicle_dbc` (`ID`, `Flags`, `TurnSpeed`, `PitchSpeed`, `PitchMin`, `PitchMax`, `SeatID_1`, `SeatID_2`,
    `SeatID_3`, `SeatID_4`, `SeatID_5`, `SeatID_6`, `SeatID_7`, `SeatID_8`, `MouseLookOffsetPitch`,
    `CameraFadeDistScalarMin`, `CameraFadeDistScalarMax`, `CameraPitchOffset`, `FacingLimitRight`, `FacingLimitLeft`,
    `MsslTrgtTurnLingering`, `MsslTrgtPitchLingering`, `MsslTrgtMouseLingering`, `MsslTrgtEndOpacity`,
    `MsslTrgtArcSpeed`, `MsslTrgtArcRepeat`, `MsslTrgtArcWidth`, `MsslTrgtImpactRadius_1`, `MsslTrgtImpactRadius_2`,
    `MsslTrgtArcTexture`, `MsslTrgtImpactTexture`, `MsslTrgtImpactModel_1`, `MsslTrgtImpactModel_2`, `CameraYawOffset`,
    `UilocomotionType`, `MsslTrgtImpactTexRadius`, `VehicleUIIndicatorID`, `PowerDisplayID_1`, `PowerDisplayID_2`,
    `PowerDisplayID_3`) VALUES
(900305, 1343811623, 1.04700005, 1.04700005, 0, 0, 0, 900405, 900406, 900407, 0, 0, 0, 0, 0, 1, 1.5, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, '', '', '', '', 0, 0, 0, 0, 61, 0, 0);

DELETE FROM `vehicleseat_dbc` WHERE `ID` IN (900405, 900406, 900407);
INSERT INTO `vehicleseat_dbc` (`ID`, `Flags`, `AttachmentID`, `AttachmentOffsetX`, `AttachmentOffsetY`,
    `AttachmentOffsetZ`, `EnterPreDelay`, `EnterSpeed`, `EnterGravity`, `EnterMinDuration`, `EnterMaxDuration`,
    `EnterMinArcHeight`, `EnterMaxArcHeight`, `EnterAnimStart`, `EnterAnimLoop`, `RideAnimStart`, `RideAnimLoop`,
    `RideUpperAnimStart`, `RideUpperAnimLoop`, `ExitPreDelay`, `ExitSpeed`, `ExitGravity`, `ExitMinDuration`,
    `ExitMaxDuration`, `ExitMinArcHeight`, `ExitMaxArcHeight`, `ExitAnimStart`, `ExitAnimLoop`, `ExitAnimEnd`,
    `PassengerYaw`, `PassengerPitch`, `PassengerRoll`, `PassengerAttachmentID`, `VehicleEnterAnim`, `VehicleExitAnim`,
    `VehicleRideAnimLoop`, `VehicleEnterAnimBone`, `VehicleExitAnimBone`, `VehicleRideAnimLoopBone`,
    `VehicleEnterAnimDelay`, `VehicleExitAnimDelay`, `VehicleAbilityDisplay`, `EnterUISoundID`, `ExitUISoundID`,
    `UiSkin`, `FlagsB`, `CameraEnteringDelay`, `CameraEnteringDuration`, `CameraExitingDelay`, `CameraExitingDuration`,
    `CameraOffsetX`, `CameraOffsetY`, `CameraOffsetZ`, `CameraPosChaseRate`, `CameraFacingChaseRate`,
    `CameraEnteringZoom`, `CameraSeatZoomMin`, `CameraSeatZoomMax`) VALUES
(900405, 1192264203, 14, 0, 0, 0, 0, 7, 19.2900009, 0.5, 1.5, 1, 4, 37, 38, -1, 91, 128, 123, 0, 7, 19.2900009, 0, 1, 1,
    4, 37, 38, 39, 0, 0, 0, -1, -1, -1, -1, -1, -1, -1, 0, 0, 1, 0, 0, 0, 48, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
(900406, 1192264203, 15, 0, 0, 0, 0, 7, 19.2900009, 0.5, 1.5, 1, 4, 37, 38, -1, 91, 128, 123, 0, 7, 19.2900009, 0, 1, 1,
    4, 37, 38, 39, 0, 0, 0, -1, -1, -1, -1, -1, -1, -1, 0, 0, 1, 0, 0, 0, 48, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
(900407, 1192264203, 16, 0, 0, 0, 0, 7, 19.2900009, 0.5, 1.5, 1, 4, 37, 38, -1, 91, 128, 123, 0, 7, 19.2900009, 0, 1, 1,
    4, 37, 38, 39, 0, 0, 0, -1, -1, -1, -1, -1, -1, -1, 0, 0, 1, 0, 0, 0, 48, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0);

DELETE FROM `skilllineability_dbc` WHERE `ID` IN (201300);
INSERT INTO `skilllineability_dbc` (`ID`, `SkillLine`, `Spell`, `RaceMask`, `ClassMask`, `ExcludeRace`, `ExcludeClass`,
    `MinSkillLineRank`, `SupercededBySpell`, `AcquireMethod`, `TrivialSkillLineRankHigh`, `TrivialSkillLineRankLow`,
    `CharacterPoints_1`, `CharacterPoints_2`) VALUES
(201300, 777, 201300, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0);
