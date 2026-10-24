-- Worgen Two Forms (68994, 68995, 68996, 110020): swap Wolf and Human through the saved looks instead of transforming into a
-- costume NPC (spell_race_two_forms, race_racials.cpp). Dracthyr Visage (110685) already has its script.
DELETE FROM `spell_script_names` WHERE `spell_id` IN (68994, 68995, 68996, 110020);
INSERT INTO `spell_script_names` (`spell_id`, `ScriptName`) VALUES
(68994, 'spell_race_two_forms'),
(68995, 'spell_race_two_forms'),
(68996, 'spell_race_two_forms'),
(110020, 'spell_race_two_forms');
