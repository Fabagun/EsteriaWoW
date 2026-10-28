CREATE TABLE IF NOT EXISTS `custom_transmogrification_outfit_slots` (
  `Owner` int(10) unsigned NOT NULL COMMENT 'Player guidlow',
  `Bought` int(10) unsigned NOT NULL DEFAULT '0' COMMENT 'Outfit slots bought in the transmog window',
  PRIMARY KEY (`Owner`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
