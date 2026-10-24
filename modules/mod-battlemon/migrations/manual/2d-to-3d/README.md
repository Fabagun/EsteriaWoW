# Manual 2D to 3D transition (one time)

These scripts are deliberately outside the automatic database updater and module SQL folders.
Run them only when converting an existing 2D installation to the 3D edition, with worldserver stopped
and verified world/character database backups. Install the base module schema first.

Import `world.sql` into the world database, then `characters.sql` into the character database using
your SQL client. Do not use `--force`: collision and schema guards must stop the import on errors.
The world script installs the 3D catalog and removes unsupported fixed Battlemon spawns.
The character script backs up and removes only unsupported form/shiny combinations and their references.

If your server already successfully applied `rev_1790798400.sql` through the updater, this transition
is already complete. DO NOT import these scripts again, reset the databases, or edit updater history.
Moving the files does not reverse any applied changes. Preserve the `battlemon_3d_removed_*` backups.
Future normal server restarts do not run these scripts.

The corrected world script uses the runtime `creature.id` column. The former `id1` late failure and
retry were covered by the disposable MySQL regression. A failed/partial migration requires diagnosis;
it is not a reason to bypass guards. Targeted character recovery is documented in
`../../../data/3d/rollback-characters.sql`; a full rollback requires pre-transition backups.
