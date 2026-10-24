-- Two Forms (Worgen Wolf/Human, Dracthyr Dragon/Visage): the look of the form a character is not currently
-- showing, in the same 132-byte layout as character_retail_look (a version-2 look, see src/server/shared/RetailLookWire.h). The active
-- form's look stays in character_retail_look.
CREATE TABLE IF NOT EXISTS `character_form_look` (
  `guid` int unsigned NOT NULL,
  `data` binary(132) NOT NULL,
  PRIMARY KEY (`guid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
