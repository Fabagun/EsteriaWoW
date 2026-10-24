-- Refuse to replace foreign ownership; apply as a batch without mysql --force.
CREATE TEMPORARY TABLE `_kyrian_venthyr_guard` (`ok` TINYINT NOT NULL CHECK (`ok` = 1));
DELETE FROM `_kyrian_venthyr_guard`;
INSERT INTO `_kyrian_venthyr_guard` (`ok`)
SELECT IF(
    NOT EXISTS (SELECT 1 FROM `chrraces_dbc` WHERE
        (`ID` = 75 AND `ClientFilestring` <> 'KyrianAlliance') OR
        (`ID` = 76 AND `ClientFilestring` <> 'VenthyrHorde'))
    AND NOT EXISTS (SELECT 1 FROM `creaturedisplayinfo_dbc` WHERE
        `ID` BETWEEN 60083 AND 60086 AND `ModelID` <> 121060 + `ID` - 60083)
    AND NOT EXISTS (SELECT 1 FROM `creaturemodeldata_dbc` WHERE
        `ID` BETWEEN 121060 AND 121063 AND `ModelName` <> CASE `ID`
            WHEN 121060 THEN 'custom\\kyrian\\native\\kyrianmale.m2'
            WHEN 121061 THEN 'custom\\kyrian\\native\\kyrianfemale.m2'
            WHEN 121062 THEN 'custom\\venthyr\\native\\vampire_male.m2'
            WHEN 121063 THEN 'custom\\venthyr\\native\\vampire_female.m2' END), 1, 0);
DROP TEMPORARY TABLE `_kyrian_venthyr_guard`;

START TRANSACTION;
-- Kyrian60 (Draenei start/racials) and Venthyr61 (Undead start/racials); no Death Knights.
DELETE FROM `chrraces_dbc` WHERE `ID` IN (75, 76);
INSERT INTO `chrraces_dbc` ( `ID` , `Flags` , `FactionID` , `ExplorationSoundID` , `MaleDisplayId` , `FemaleDisplayId` ,
    `ClientPrefix` , `BaseLanguage` , `CreatureType` , `ResSicknessSpellID` , `SplashSoundID` , `ClientFilestring` ,
    `CinematicSequenceID` , `Alliance` , `Name_Lang_enUS` , `Name_Lang_enGB` , `Name_Lang_koKR` , `Name_Lang_frFR` ,
    `Name_Lang_deDE` , `Name_Lang_enCN` , `Name_Lang_zhCN` , `Name_Lang_enTW` , `Name_Lang_zhTW` , `Name_Lang_esES` ,
    `Name_Lang_esMX` , `Name_Lang_ruRU` , `Name_Lang_ptPT` , `Name_Lang_ptBR` , `Name_Lang_itIT` , `Name_Lang_Unk` ,
    `Name_Lang_Mask` , `Name_Female_Lang_enUS` , `Name_Female_Lang_enGB` , `Name_Female_Lang_koKR` ,
    `Name_Female_Lang_frFR` , `Name_Female_Lang_deDE` , `Name_Female_Lang_enCN` , `Name_Female_Lang_zhCN` ,
    `Name_Female_Lang_enTW` , `Name_Female_Lang_zhTW` , `Name_Female_Lang_esES` , `Name_Female_Lang_esMX` ,
    `Name_Female_Lang_ruRU` , `Name_Female_Lang_ptPT` , `Name_Female_Lang_ptBR` , `Name_Female_Lang_itIT` ,
    `Name_Female_Lang_Unk` , `Name_Female_Lang_Mask` , `Name_Male_Lang_enUS` , `Name_Male_Lang_enGB` ,
    `Name_Male_Lang_koKR` , `Name_Male_Lang_frFR` , `Name_Male_Lang_deDE` , `Name_Male_Lang_enCN` ,
    `Name_Male_Lang_zhCN` , `Name_Male_Lang_enTW` , `Name_Male_Lang_zhTW` , `Name_Male_Lang_esES` ,
    `Name_Male_Lang_esMX` , `Name_Male_Lang_ruRU` , `Name_Male_Lang_ptPT` , `Name_Male_Lang_ptBR` ,
    `Name_Male_Lang_itIT` , `Name_Male_Lang_Unk` , `Name_Male_Lang_Mask` , `FacialHairCustomization_1` ,
    `FacialHairCustomization_2` , `HairCustomization` , `Required_Expansion` ) VALUES
(75, 14, 1629, 4141, 60083, 60084, 'Ky' , 7, 7, 15007, 1096, 'KyrianAlliance' , 0, 0, 'Kyrian' , 'Kyrian' , 'Kyrian' ,
    'Kyrian' , 'Kyrian' , 'Kyrian' , 'Kyrian' , 'Kyrian' , 'Kyrian' , 'Kyrian' , 'Kyrian' , 'Kyrian' , 'Kyrian' ,
    'Kyrian' , 'Kyrian' , 'Kyrian' , 16712191, 'Kyrian' , 'Kyrian' , 'Kyrian' , 'Kyrian' , 'Kyrian' , 'Kyrian' ,
    'Kyrian' , 'Kyrian' , 'Kyrian' , 'Kyrian' , 'Kyrian' , 'Kyrian' , 'Kyrian' , 'Kyrian' , 'Kyrian' , 'Kyrian' ,
    16712172, 'Kyrian' , 'Kyrian' , 'Kyrian' , 'Kyrian' , 'Kyrian' , 'Kyrian' , 'Kyrian' , 'Kyrian' , 'Kyrian' ,
    'Kyrian' , 'Kyrian' , 'Kyrian' , 'Kyrian' , 'Kyrian' , 'Kyrian' , 'Kyrian' , 16712172, 'NORMAL' , 'PIERCINGS' ,
    'NORMAL' , 1),
(76, 14, 5, 4141, 60085, 60086, 'Ve' , 1, 7, 15007, 1096, 'VenthyrHorde' , 0, 1, 'Venthyr' , 'Venthyr' , 'Venthyr' ,
    'Venthyr' , 'Venthyr' , 'Venthyr' , 'Venthyr' , 'Venthyr' , 'Venthyr' , 'Venthyr' , 'Venthyr' , 'Venthyr' ,
    'Venthyr' , 'Venthyr' , 'Venthyr' , 'Venthyr' , 16712191, 'Venthyr' , 'Venthyr' , 'Venthyr' , 'Venthyr' , 'Venthyr'
    , 'Venthyr' , 'Venthyr' , 'Venthyr' , 'Venthyr' , 'Venthyr' , 'Venthyr' , 'Venthyr' , 'Venthyr' , 'Venthyr' ,
    'Venthyr' , 'Venthyr' , 16712172, 'Venthyr' , 'Venthyr' , 'Venthyr' , 'Venthyr' , 'Venthyr' , 'Venthyr' , 'Venthyr'
    , 'Venthyr' , 'Venthyr' , 'Venthyr' , 'Venthyr' , 'Venthyr' , 'Venthyr' , 'Venthyr' , 'Venthyr' , 'Venthyr' ,
    16712172, 'NORMAL' , 'PIERCINGS' , 'NORMAL' , 0);
DELETE FROM `creaturemodeldata_dbc` WHERE `ID` IN (121060, 121061, 121062, 121063);
INSERT INTO `creaturemodeldata_dbc` ( `ID` , `Flags` , `ModelName` , `SizeClass` , `ModelScale` , `BloodID` ,
    `FootprintTextureID` , `FootprintTextureLength` , `FootprintTextureWidth` , `FootprintParticleScale` ,
    `FoleyMaterialID` , `FootstepShakeSize` , `DeathThudShakeSize` , `SoundID` , `CollisionWidth` , `CollisionHeight` ,
    `MountHeight` , `GeoBoxMinX` , `GeoBoxMinY` , `GeoBoxMinZ` , `GeoBoxMaxX` , `GeoBoxMaxY` , `GeoBoxMaxZ` ,
    `WorldEffectScale` , `AttachedEffectScale` , `MissileCollisionRadius` , `MissileCollisionPush` ,
    `MissileCollisionRaise` ) VALUES
(121060, 2052, 'custom\\kyrian\\native\\kyrianmale.m2' , 1, 1.0, 1, 1, 18.0, 12.0, 1.0, 0, 0, 0, 0, 0.6111111044883728,
    2.031277894973755, 8.405317306518555, -7.2937421798706055, -7.466604232788086, -4.744598865509033,
    6.962477684020996, 6.990102291107178, 9.056293487548828, 1.0, 1.0, 0.0, 0.0, 0.0),
(121061, 2052, 'custom\\kyrian\\native\\kyrianfemale.m2' , 1, 1.0, 1, 1, 18.0, 12.0, 1.0, 0, 0, 0, 0,
    0.6111111044883728, 2.031277894973755, 8.925081253051758, -8.163848876953125, -7.466604232788086,
    -4.835848808288574, 6.962477207183838, 6.964480876922607, 9.056292533874512, 1.0, 1.0, 0.0, 0.0, 0.0),
(121062, 2052, 'custom\\venthyr\\native\\vampire_male.m2' , 1, 1.0, 1, 1, 18.0, 12.0, 1.0, 0, 0, 0, 0,
    0.6111111044883728, 2.031277894973755, 12.154294967651367, -2.9938173294067383, -2.5840964317321777,
    -2.0833332538604736, 3.6334218978881836, 3.2151646614074707, 6.976985454559326, 1.0, 1.0, 0.0, 0.0, 0.0),
(121063, 2052, 'custom\\venthyr\\native\\vampire_female.m2' , 1, 1.0, 1, 1, 18.0, 12.0, 1.0, 0, 0, 0, 0,
    0.6111111044883728, 2.031277894973755, 23.807798385620117, -3.256474733352661, -2.305504322052002,
    -2.0833332538604736, 3.616006374359131, 3.9479522705078125, 6.976985454559326, 1.0, 1.0, 0.0, 0.0, 0.0);
DELETE FROM `creaturedisplayinfo_dbc` WHERE `ID` IN (60083, 60084, 60085, 60086);
INSERT INTO `creaturedisplayinfo_dbc` ( `ID` , `ModelID` , `SoundID` , `ExtendedDisplayInfoID` , `CreatureModelScale` ,
    `CreatureModelAlpha` , `TextureVariation_1` , `TextureVariation_2` , `TextureVariation_3` , `PortraitTextureName` ,
    `BloodLevel` , `BloodID` , `NPCSoundID` , `ParticleColorID` , `CreatureGeosetData` , `ObjectEffectPackageID` )
    VALUES
(60083, 121060, 0, 0, 0.75, 255, '', '', '', '', 3, 0, 0, 0, 0, 0),
(60084, 121061, 0, 0, 0.75, 255, '', '', '', '', 3, 0, 0, 0, 0, 0),
(60085, 121062, 0, 0, 0.75, 255, '', '', '', '', 3, 0, 0, 0, 0, 0),
(60086, 121063, 0, 0, 0.75, 255, '', '', '', '', 3, 0, 0, 0, 0, 0);
DELETE FROM `playercreateinfo` WHERE `race` IN (75, 76);
INSERT INTO `playercreateinfo` ( `race` , `class` , `map` , `zone` , `position_x` , `position_y` , `position_z` ,
    `orientation` ) VALUES
(75, 1, 530, 3526, -3961.64, -13931.2, 100.615, 2.08364),
(75, 2, 530, 3526, -3961.64, -13931.2, 100.615, 2.08364),
(75, 3, 530, 3526, -3961.64, -13931.2, 100.615, 2.08364),
(75, 4, 530, 3526, -3961.64, -13931.2, 100.615, 2.08364),
(75, 5, 530, 3526, -3961.64, -13931.2, 100.615, 2.08364),
(75, 7, 530, 3526, -3961.64, -13931.2, 100.615, 2.08364),
(75, 8, 530, 3526, -3961.64, -13931.2, 100.615, 2.08364),
(75, 9, 530, 3526, -3961.64, -13931.2, 100.615, 2.08364),
(75, 11, 530, 3526, -3961.64, -13931.2, 100.615, 2.08364),
(76, 1, 0, 85, 1676.71, 1678.31, 121.67, 2.70526),
(76, 2, 0, 85, 1676.71, 1678.31, 121.67, 2.70526),
(76, 3, 0, 85, 1676.71, 1678.31, 121.67, 2.70526),
(76, 4, 0, 85, 1676.71, 1678.31, 121.67, 2.70526),
(76, 5, 0, 85, 1676.71, 1678.31, 121.67, 2.70526),
(76, 7, 0, 85, 1676.71, 1678.31, 121.67, 2.70526),
(76, 8, 0, 85, 1676.71, 1678.31, 121.67, 2.70526),
(76, 9, 0, 85, 1676.71, 1678.31, 121.67, 2.70526),
(76, 11, 0, 85, 1676.71, 1678.31, 121.67, 2.70526);
DELETE FROM `player_race_stats` WHERE `Race` IN (75, 76);
INSERT INTO `player_race_stats` (`Race`, `Strength`, `Agility`, `Stamina`, `Intellect`, `Spirit`) VALUES
(75, 1, -3, 0, 0, 2),
(76, -1, -2, 0, -2, 5);
DELETE FROM `playercreateinfo_action` WHERE `race` IN (75, 76);
INSERT INTO `playercreateinfo_action` (`race`, `class`, `button`, `action`, `type`) VALUES
(75, 1, 72, 6603, 0),
(75, 1, 73, 78, 0),
(75, 1, 74, 28880, 0),
(75, 1, 83, 4540, 128),
(75, 2, 0, 6603, 0),
(75, 2, 1, 21084, 0),
(75, 2, 2, 635, 0),
(75, 2, 3, 28880, 0),
(75, 2, 10, 159, 128),
(75, 2, 11, 4540, 128),
(75, 3, 0, 6603, 0),
(75, 3, 1, 2973, 0),
(75, 3, 2, 75, 0),
(75, 3, 3, 28880, 0),
(75, 3, 10, 159, 128),
(75, 3, 11, 4540, 128),
(75, 4, 0, 6603, 0),
(75, 4, 1, 1752, 0),
(75, 4, 2, 2098, 0),
(75, 4, 3, 2764, 0),
(75, 4, 11, 2070, 128),
(75, 5, 0, 6603, 0),
(75, 5, 1, 585, 0),
(75, 5, 2, 2050, 0),
(75, 5, 3, 28880, 0),
(75, 5, 10, 159, 128),
(75, 5, 11, 4540, 128),
(75, 7, 0, 6603, 0),
(75, 7, 1, 403, 0),
(75, 7, 2, 331, 0),
(75, 7, 3, 28880, 0),
(75, 7, 10, 159, 128),
(75, 7, 11, 4540, 128),
(75, 8, 0, 6603, 0),
(75, 8, 1, 133, 0),
(75, 8, 2, 168, 0),
(75, 8, 3, 28880, 0),
(75, 8, 10, 159, 128),
(75, 8, 11, 4540, 128),
(75, 9, 0, 6603, 0),
(75, 9, 1, 686, 0),
(75, 9, 2, 687, 0),
(75, 9, 10, 159, 128),
(75, 9, 11, 4604, 128),
(75, 11, 0, 6603, 0),
(75, 11, 1, 5176, 0),
(75, 11, 2, 5185, 0),
(75, 11, 10, 159, 128),
(75, 11, 11, 4536, 128),
(76, 1, 72, 6603, 0),
(76, 1, 73, 78, 0),
(76, 1, 74, 20577, 0),
(76, 1, 83, 4604, 128),
(76, 2, 0, 6603, 0),
(76, 2, 1, 21084, 0),
(76, 2, 2, 635, 0),
(76, 2, 10, 159, 128),
(76, 2, 11, 20857, 128),
(76, 3, 0, 6603, 0),
(76, 3, 1, 2973, 0),
(76, 3, 2, 75, 0),
(76, 3, 10, 159, 128),
(76, 3, 11, 117, 128),
(76, 4, 0, 6603, 0),
(76, 4, 1, 1752, 0),
(76, 4, 2, 2098, 0),
(76, 4, 3, 2764, 0),
(76, 4, 4, 20577, 0),
(76, 4, 11, 4604, 128),
(76, 5, 0, 6603, 0),
(76, 5, 1, 585, 0),
(76, 5, 2, 2050, 0),
(76, 5, 3, 20577, 0),
(76, 5, 10, 159, 128),
(76, 5, 11, 4604, 128),
(76, 7, 0, 6603, 0),
(76, 7, 1, 403, 0),
(76, 7, 2, 331, 0),
(76, 7, 10, 159, 128),
(76, 7, 11, 117, 128),
(76, 8, 0, 6603, 0),
(76, 8, 1, 133, 0),
(76, 8, 2, 168, 0),
(76, 8, 3, 20577, 0),
(76, 8, 10, 159, 128),
(76, 8, 11, 4604, 128),
(76, 9, 0, 6603, 0),
(76, 9, 1, 686, 0),
(76, 9, 2, 687, 0),
(76, 9, 3, 20577, 0),
(76, 9, 10, 159, 128),
(76, 9, 11, 4604, 128),
(76, 11, 0, 6603, 0),
(76, 11, 1, 5176, 0),
(76, 11, 2, 5185, 0),
(76, 11, 10, 159, 128),
(76, 11, 11, 4536, 128);
DELETE FROM `playercreateinfo_item` WHERE `race` IN (75, 76);
DELETE FROM `player_totem_model` WHERE `RaceID` IN (75, 76);
INSERT INTO `player_totem_model` (`TotemID`, `RaceID`, `ModelID`) VALUES
(1, 75, 19074),
(2, 75, 19073),
(3, 75, 19075),
(4, 75, 19071),
(1, 76, 30758),
(2, 76, 30757),
(3, 76, 30759),
(4, 76, 30756);

DELETE FROM `custom_race_start_spell` WHERE `race` = 75;
INSERT INTO `custom_race_start_spell` (`race`, `classMask`, `spell`, `comment`) VALUES
(75, 0, 668, 'Kyrian faction language'),
(75, 0, 20579, 'Shadow Resistance'),
(75, 0, 28875, 'Gemcutting'),
(75, 0, 28880, 'Gift of the Naaru'),
(75, 0, 29932, 'Language Draenei'),
(75, 7, 6562, 'Heroic Presence'),
(75, 1496, 28878, 'Inspiring Presence');
DELETE FROM `custom_race_start_skill` WHERE `race` = 75;
INSERT INTO `custom_race_start_skill` (`race`, `classMask`, `skill`, `rank`, `comment`) VALUES
(75, 0, 98, 0, 'Kyrian faction language');

DELETE FROM `custom_race_start_spell` WHERE `race` = 76;
INSERT INTO `custom_race_start_spell` (`race`, `classMask`, `spell`, `comment`) VALUES
(76, 0, 669, 'Venthyr faction language');
DELETE FROM `custom_race_start_skill` WHERE `race` = 76;
INSERT INTO `custom_race_start_skill` (`race`, `classMask`, `skill`, `rank`, `comment`) VALUES
(76, 0, 109, 0, 'Venthyr faction language');

DELETE FROM `creature_model_info` WHERE `DisplayID` IN (60083, 60084, 60085, 60086);
INSERT INTO `creature_model_info` ( `DisplayID` , `BoundingRadius` , `CombatReach` , `Gender` , `DisplayID_Other_Gender`
    ) VALUES
(60083, 0.5, 1.5, 0, 60084),
(60084, 0.5, 1.5, 1, 60083),
(60085, 0.5, 1.5, 0, 60086),
(60086, 0.5, 1.5, 1, 60085);

DELETE FROM `playercreateinfo_action` WHERE `race` = 75 AND `class` IN (4,9,11) AND `button` = 4;
INSERT INTO `playercreateinfo_action` (`race`, `class`, `button`, `action`, `type`) VALUES
(75, 4, 4, 28880, 0),
(75, 9, 4, 28880, 0),
(75, 11, 4, 28880, 0);

COMMIT;
