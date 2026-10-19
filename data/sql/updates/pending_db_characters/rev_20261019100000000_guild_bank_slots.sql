-- Guild bank tabs start at 128 slots and can grow up to 250 (stays below the 255 'no slot' sentinel).
ALTER TABLE `guild_bank_tab`
  ADD COLUMN `slots` smallint unsigned NOT NULL DEFAULT '128' AFTER `TabText`;
