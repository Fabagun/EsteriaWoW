-- Darkfallen HD (native appearance): supplied skins/hair, one face, retail hair styles, no facial hair.
UPDATE `characters` SET `skin` = LEAST(`skin`, IF(`gender` = 0, 4, 3)), `face` = 0, `facialStyle` = 0,
    `hairStyle` = LEAST(`hairStyle`, IF(`gender` = 0, 20, 24)),
    `hairColor` = LEAST(`hairColor`, IF(`gender` = 0, 3, 4))
WHERE `race` IN (43, 44);
