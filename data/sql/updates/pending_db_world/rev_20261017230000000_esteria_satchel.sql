-- Requires Esteria's matched 254-slot client/server container layout.
-- New custom entry only; the installer must reject an existing unrelated allocation.
DELETE FROM `item_dbc` WHERE `ID` = 910237;
INSERT INTO `item_dbc`
(`ID`, `ClassID`, `SubclassID`, `Sound_Override_Subclassid`, `Material`, `DisplayInfoID`, `InventoryType`, `SheatheType`)
VALUES
(910237, 1, 0, -1, 8, 64151, 18, 0);
DELETE FROM `item_template` WHERE `entry` = 910237;
INSERT INTO `item_template`
(`entry`, `class`, `subclass`, `SoundOverrideSubclass`, `name`, `displayid`, `Quality`, `BuyCount`, `InventoryType`,
 `AllowableClass`, `AllowableRace`, `ItemLevel`, `RequiredLevel`, `stackable`, `ContainerSlots`,
 `bonding`, `description`, `Material`, `BagFamily`, `VerifiedBuild`)
VALUES
(910237, 1, 0, -1, 'Esteria Grand Satchel', 64151, 4, 1, 18,
 -1, -1, 80, 0, 1, 237, 2, 'A place for every adventure.', 8, 0, 12340);
