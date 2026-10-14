-- Drakkin is Alliance only, with the same model for both selectable genders.
UPDATE `chrraces_dbc` SET `MaleDisplayId` = `FemaleDisplayId`, `ClientPrefix` = 'Kb' WHERE `ID` IN (66, 67);
UPDATE `chrraces_dbc` SET `Flags` = `Flags` | 1 WHERE `ID` = 67;
DELETE FROM `playercreateinfo` WHERE `race` = 67;
