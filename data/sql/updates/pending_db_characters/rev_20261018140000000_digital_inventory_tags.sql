-- Per-stack user tag and "keep split" mark for digital storage.
ALTER TABLE `character_digital_storage_item`
  ADD COLUMN `tag` varchar(24) NOT NULL DEFAULT '' AFTER `favorite`,
  ADD COLUMN `split` tinyint unsigned NOT NULL DEFAULT '0' AFTER `tag`;
