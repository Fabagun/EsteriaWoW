-- Natures Ally (21927) was handed to every race as a starting spell and does nothing useful; it is
-- also listed in ClasslessWildcard.ExcludedSpells so the module never rolls it.
DELETE FROM `playercreateinfo_spell_custom` WHERE `Spell` = 21927;
