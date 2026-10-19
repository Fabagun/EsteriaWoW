-- Full item data stays in item_instance. These tables describe virtual carried ownership only.
CREATE TABLE IF NOT EXISTS `character_digital_storage` (
  `guid` int unsigned NOT NULL,
  `capacity` int unsigned NOT NULL DEFAULT '256',
  `revision` int unsigned NOT NULL DEFAULT '1',
  PRIMARY KEY (`guid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `character_digital_storage_item` (
  `guid` int unsigned NOT NULL,
  `item` int unsigned NOT NULL,
  `favorite` tinyint unsigned NOT NULL DEFAULT '0',
  PRIMARY KEY (`item`),
  KEY `idx_digital_owner` (`guid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
