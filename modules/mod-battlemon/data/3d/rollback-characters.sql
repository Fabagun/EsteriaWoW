-- Restore the 2D code/addon/assets first. Stop worldserver. Preserve backup tables.
-- Existing IDs/occupied party slots are left unchanged; compare backups after restoration.
START TRANSACTION;
INSERT IGNORE INTO battlemon_owned SELECT * FROM battlemon_3d_removed_owned;
INSERT IGNORE INTO battlemon_owned_taught SELECT `b`.* FROM battlemon_3d_removed_owned_taught `b` JOIN battlemon_owned `o` ON `o`.id=`b`.owned_id JOIN battlemon_3d_removed_owned `old` ON `old`.id=`o`.id AND `old`.guid=`o`.guid AND `old`.form_id=`o`.form_id AND `old`.shiny=`o`.shiny;
INSERT IGNORE INTO battlemon_party SELECT `b`.* FROM battlemon_3d_removed_party `b` JOIN battlemon_owned `o` ON `o`.id=`b`.owned_id AND `o`.guid=`b`.guid JOIN battlemon_3d_removed_owned `old` ON `old`.id=`o`.id AND `old`.guid=`o`.guid AND `old`.form_id=`o`.form_id AND `old`.shiny=`o`.shiny;
COMMIT;
