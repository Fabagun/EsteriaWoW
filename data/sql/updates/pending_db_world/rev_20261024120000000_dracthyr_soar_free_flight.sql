-- Dracthyr Soar (110684): free flight (aura 201) with +60% flight speed (aura 207) until cancelled, instead of the
-- ground-bound speed burst. The core already refuses flying auras in no-fly areas (Spell::CheckCast).
UPDATE `spell_dbc` SET
    `EffectAura_1` = 201, `EffectBasePoints_1` = 0,
    `EffectAura_2` = 207, `EffectBasePoints_2` = 59,
    `DurationIndex` = 21, `RecoveryTime` = 3000,
    `Description_Lang_enUS` = 'Take to the air in free flight, increasing flight speed by 60%. Cancel the effect to land.',
    `AuraDescription_Lang_enUS` = 'Flying freely. Flight speed increased by 60%.'
WHERE `ID` = 110684;
