-- Use the verified bird bodies for Centaur's normal flight form as well as swift flight.
-- Flight speed and riding requirements remain on the existing racial/form passive spells.
DELETE FROM `player_shapeshift_model` WHERE `RaceID`=73 AND (`ShapeshiftID`,`CustomizationID`,`GenderID`)=(29,255,2);
INSERT INTO `player_shapeshift_model` (`ShapeshiftID`, `RaceID`, `CustomizationID`, `GenderID`, `ModelID`) VALUES
(29, 73, 255, 2, 21243);
DELETE FROM `player_shapeshift_model` WHERE `RaceID`=74 AND (`ShapeshiftID`,`CustomizationID`,`GenderID`)=(29,255,2);
INSERT INTO `player_shapeshift_model` (`ShapeshiftID`, `RaceID`, `CustomizationID`, `GenderID`, `ModelID`) VALUES
(29, 74, 255, 2, 21244);
