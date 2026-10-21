-- Restore the original player gender after a gender-neutral bird transformation.
DELETE FROM `creature_model_info` WHERE `DisplayID` IN (60074, 60075, 60076, 60077);
INSERT INTO `creature_model_info`
(`DisplayID`, `BoundingRadius`, `CombatReach`, `Gender`, `DisplayID_Other_Gender`) VALUES
(60074, 0.5, 1.5, 0, 60075),
(60075, 0.5, 1.5, 1, 60074),
(60076, 0.5, 1.5, 0, 60077),
(60077, 0.5, 1.5, 1, 60076);
