-- Existing male Drakkin becomes Awakening Tarasek; female appearance is unchanged.
UPDATE `characters` SET `skin` = 0,
    `face` = 0,
    `hairStyle` = 0,
    `hairColor` = 0,
    `facialStyle` = 0,
    `extraAppearance` = 0
WHERE `guid` = 546
  AND `race` = 66
  AND `gender` = 0
  AND `skin` = 7
  AND `face` = 0
  AND `hairStyle` = 0
  AND `hairColor` = 6
  AND `facialStyle` = 0
  AND `extraAppearance` = 0;
