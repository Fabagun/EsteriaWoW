-- Esteria Skyriding: per-mount override. enabled = 1 makes a mount aura skyride (also a ground mount),
-- enabled = 0 keeps a flying mount on stock flight.
CREATE TABLE IF NOT EXISTS `esteria_skyriding_mounts` (
    `spell_id` INT UNSIGNED NOT NULL,
    `enabled` TINYINT UNSIGNED NOT NULL DEFAULT 1,
    PRIMARY KEY (`spell_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
