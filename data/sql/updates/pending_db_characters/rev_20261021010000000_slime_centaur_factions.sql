-- Approved Slime Giant 71 -> 72 and Centaur 74 -> 73 moves. Apply with worldserver stopped.
UPDATE `characters` SET `race` = 72, `teamId` = 1, `map` = 1, `zone` = 14, `position_x` = -618.518, `position_y` = -4251.67, `position_z` = 38.718, `orientation` = 0 WHERE `guid` = 560 AND `race` = 71 AND `online` = 0;
DELETE FROM `character_skills` WHERE `guid` = 560 AND `skill` IN (98, 109);
INSERT INTO `character_skills` (`guid`, `skill`, `value`, `max`) VALUES
(560, 109, 300, 300);
DELETE FROM `character_homebind` WHERE `guid` = 560;
INSERT INTO `character_homebind` (`guid`, `mapId`, `zoneId`, `posX`, `posY`, `posZ`) VALUES
(560, 1, 14, -618.518, -4251.67, 38.718);
UPDATE `characters` SET `race` = 73, `teamId` = 0, `map` = 0, `zone` = 12, `position_x` = -8949.95, `position_y` = -132.493, `position_z` = 83.5312, `orientation` = 0 WHERE `guid` = 563 AND `race` = 74 AND `online` = 0;
DELETE FROM `character_skills` WHERE `guid` = 563 AND `skill` IN (98, 109);
INSERT INTO `character_skills` (`guid`, `skill`, `value`, `max`) VALUES
(563, 98, 300, 300);
DELETE FROM `character_homebind` WHERE `guid` = 563;
INSERT INTO `character_homebind` (`guid`, `mapId`, `zoneId`, `posX`, `posY`, `posZ`) VALUES
(563, 0, 12, -8949.95, -132.493, 83.5312);
UPDATE `characters` SET `race` = 73, `teamId` = 0, `map` = 0, `zone` = 12, `position_x` = -8949.95, `position_y` = -132.493, `position_z` = 83.5312, `orientation` = 0 WHERE `guid` = 564 AND `race` = 74 AND `online` = 0;
DELETE FROM `character_skills` WHERE `guid` = 564 AND `skill` IN (98, 109);
INSERT INTO `character_skills` (`guid`, `skill`, `value`, `max`) VALUES
(564, 98, 300, 300);
DELETE FROM `character_homebind` WHERE `guid` = 564;
INSERT INTO `character_homebind` (`guid`, `mapId`, `zoneId`, `posX`, `posY`, `posZ`) VALUES
(564, 0, 12, -8949.95, -132.493, 83.5312);
UPDATE `characters` SET `race` = 73, `teamId` = 0, `map` = 0, `zone` = 12, `position_x` = -8949.95, `position_y` = -132.493, `position_z` = 83.5312, `orientation` = 0 WHERE `guid` = 567 AND `race` = 74 AND `online` = 0;
DELETE FROM `character_skills` WHERE `guid` = 567 AND `skill` IN (98, 109);
INSERT INTO `character_skills` (`guid`, `skill`, `value`, `max`) VALUES
(567, 98, 300, 300);
DELETE FROM `character_homebind` WHERE `guid` = 567;
INSERT INTO `character_homebind` (`guid`, `mapId`, `zoneId`, `posX`, `posY`, `posZ`) VALUES
(567, 0, 12, -8949.95, -132.493, 83.5312);
UPDATE `characters` SET `race` = 73, `teamId` = 0, `map` = 0, `zone` = 12, `position_x` = -8949.95, `position_y` = -132.493, `position_z` = 83.5312, `orientation` = 0 WHERE `guid` = 568 AND `race` = 74 AND `online` = 0;
DELETE FROM `character_skills` WHERE `guid` = 568 AND `skill` IN (98, 109);
INSERT INTO `character_skills` (`guid`, `skill`, `value`, `max`) VALUES
(568, 98, 300, 300);
DELETE FROM `character_homebind` WHERE `guid` = 568;
INSERT INTO `character_homebind` (`guid`, `mapId`, `zoneId`, `posX`, `posY`, `posZ`) VALUES
(568, 0, 12, -8949.95, -132.493, 83.5312);
UPDATE `characters` SET `race` = 73, `teamId` = 0, `map` = 0, `zone` = 12, `position_x` = -8949.95, `position_y` = -132.493, `position_z` = 83.5312, `orientation` = 0 WHERE `guid` = 572 AND `race` = 74 AND `online` = 0;
DELETE FROM `character_skills` WHERE `guid` = 572 AND `skill` IN (98, 109);
INSERT INTO `character_skills` (`guid`, `skill`, `value`, `max`) VALUES
(572, 98, 300, 300);
DELETE FROM `character_homebind` WHERE `guid` = 572;
INSERT INTO `character_homebind` (`guid`, `mapId`, `zoneId`, `posX`, `posY`, `posZ`) VALUES
(572, 0, 12, -8949.95, -132.493, 83.5312);
UPDATE `characters` SET `race` = 73, `teamId` = 0, `map` = 0, `zone` = 12, `position_x` = -8949.95, `position_y` = -132.493, `position_z` = 83.5312, `orientation` = 0 WHERE `guid` = 573 AND `race` = 74 AND `online` = 0;
DELETE FROM `character_skills` WHERE `guid` = 573 AND `skill` IN (98, 109);
INSERT INTO `character_skills` (`guid`, `skill`, `value`, `max`) VALUES
(573, 98, 300, 300);
DELETE FROM `character_homebind` WHERE `guid` = 573;
INSERT INTO `character_homebind` (`guid`, `mapId`, `zoneId`, `posX`, `posY`, `posZ`) VALUES
(573, 0, 12, -8949.95, -132.493, 83.5312);
UPDATE `characters` SET `race` = 73, `teamId` = 0, `map` = 0, `zone` = 12, `position_x` = -8949.95, `position_y` = -132.493, `position_z` = 83.5312, `orientation` = 0 WHERE `guid` = 576 AND `race` = 74 AND `online` = 0;
DELETE FROM `character_skills` WHERE `guid` = 576 AND `skill` IN (98, 109);
INSERT INTO `character_skills` (`guid`, `skill`, `value`, `max`) VALUES
(576, 98, 300, 300);
DELETE FROM `character_homebind` WHERE `guid` = 576;
INSERT INTO `character_homebind` (`guid`, `mapId`, `zoneId`, `posX`, `posY`, `posZ`) VALUES
(576, 0, 12, -8949.95, -132.493, 83.5312);
UPDATE `characters` SET `race` = 73, `teamId` = 0, `map` = 0, `zone` = 12, `position_x` = -8949.95, `position_y` = -132.493, `position_z` = 83.5312, `orientation` = 0 WHERE `guid` = 577 AND `race` = 74 AND `online` = 0;
DELETE FROM `character_skills` WHERE `guid` = 577 AND `skill` IN (98, 109);
INSERT INTO `character_skills` (`guid`, `skill`, `value`, `max`) VALUES
(577, 98, 300, 300);
DELETE FROM `character_homebind` WHERE `guid` = 577;
INSERT INTO `character_homebind` (`guid`, `mapId`, `zoneId`, `posX`, `posY`, `posZ`) VALUES
(577, 0, 12, -8949.95, -132.493, 83.5312);
UPDATE `characters` SET `race` = 73, `teamId` = 0, `map` = 0, `zone` = 12, `position_x` = -8949.95, `position_y` = -132.493, `position_z` = 83.5312, `orientation` = 0 WHERE `guid` = 578 AND `race` = 74 AND `online` = 0;
DELETE FROM `character_skills` WHERE `guid` = 578 AND `skill` IN (98, 109);
INSERT INTO `character_skills` (`guid`, `skill`, `value`, `max`) VALUES
(578, 98, 300, 300);
DELETE FROM `character_homebind` WHERE `guid` = 578;
INSERT INTO `character_homebind` (`guid`, `mapId`, `zoneId`, `posX`, `posY`, `posZ`) VALUES
(578, 0, 12, -8949.95, -132.493, 83.5312);
UPDATE `characters` SET `race` = 73, `teamId` = 0, `map` = 0, `zone` = 12, `position_x` = -8949.95, `position_y` = -132.493, `position_z` = 83.5312, `orientation` = 0 WHERE `guid` = 579 AND `race` = 74 AND `online` = 0;
DELETE FROM `character_skills` WHERE `guid` = 579 AND `skill` IN (98, 109);
INSERT INTO `character_skills` (`guid`, `skill`, `value`, `max`) VALUES
(579, 98, 300, 300);
DELETE FROM `character_homebind` WHERE `guid` = 579;
INSERT INTO `character_homebind` (`guid`, `mapId`, `zoneId`, `posX`, `posY`, `posZ`) VALUES
(579, 0, 12, -8949.95, -132.493, 83.5312);
