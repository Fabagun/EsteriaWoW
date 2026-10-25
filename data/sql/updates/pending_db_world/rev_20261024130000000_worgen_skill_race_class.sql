-- Worgen racials were dropped at every login: skill 789 (Racial - Worgen) excluded class 2, the Hero chassis, and skill 793
-- (Two Forms / Running Wild) was valid for no Worgen at all (its race mask lacks bit 2048). Open both to every class.
REPLACE INTO `skillraceclassinfo_dbc` (`ID`, `SkillID`, `RaceMask`, `ClassMask`, `Flags`, `MinLevel`, `SkillTierID`, `SkillCostIndex`) VALUES
(971, 789, 2021623808, 2047, 1170, 0, 0, 0),
(1142, 793, 2021648384, 2047, 1170, 0, 0, 0);
