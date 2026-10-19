-- Account-wide digital bank. Items keep full data in item_instance with owner_guid 0.
CREATE TABLE IF NOT EXISTS `account_bank` (
  `account` int unsigned NOT NULL,
  `capacity` int unsigned NOT NULL DEFAULT '512',
  `revision` int unsigned NOT NULL DEFAULT '1',
  `unlocked` tinyint unsigned NOT NULL DEFAULT '0',
  PRIMARY KEY (`account`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `account_bank_item` (
  `account` int unsigned NOT NULL,
  `item` int unsigned NOT NULL,
  `favorite` tinyint unsigned NOT NULL DEFAULT '0',
  `tag` varchar(24) NOT NULL DEFAULT '',
  `split` tinyint unsigned NOT NULL DEFAULT '0',
  PRIMARY KEY (`item`),
  KEY `idx_account_bank_owner` (`account`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
