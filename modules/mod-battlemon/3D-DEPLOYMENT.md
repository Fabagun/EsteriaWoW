# Battlemon 3D deployment

This checkout is now the 3D edition. The 2D snapshot is at `C:/data/pokemon-mod/2d-version`; the self-contained 3D module/client package is at `C:/data/pokemon-mod/3d-version`.

The catalog has 3,965 available form/palette appearances across 2,345 forms, including all 980 validated Pixelmon extras. Sixteen old appearances are rescued by those extras. Existing form IDs are retained. New form IDs use the reserved 2000-2978 range; original extra display IDs 200000-200979 are retained. MissingNo uses species ID 1033 (source dex 0) because 0 is a runtime sentinel. Four new species use supplied-source base stats and level-up moves. Existing species retain this battle system's moves and form overrides. Source appearance predicates are selectable named model states, not newly implemented Minecraft transformation mechanics.

## Remote deployment (worldserver stopped)

1. Back up world and character databases. Pull the updated module through Git. Battlemon now ships as one module, `modules/mod-battlemon`; include all new/moved files and the deletions of the former overworld/battles module paths. Keep the Playerbots dependency and all three existing `.conf` files. Regenerate the remote build source list as part of your normal build.
   Check `/root/dark-brotherhood/core/env/dist/etc/modules/mod_battlemon_battles.conf` against
   `modules/mod-battlemon/conf/mod_battlemon_battles.conf.dist`. If the active file is absent, copy
   the template there without the `.dist` suffix. For an existing file, retain your custom values
   and add missing options, including `BattlemonBattles.NativeSpellVisuals = 1` under `[worldserver]`.
   Installing a new `.dist` template does not merge new options into an existing `.conf`.
2. Copy the client package's contents into the WoW client. The local development client has already been updated by the migration receipt when `3d-activation.json` reports success.
3. From the remote core checkout, run `python3 modules/mod-battlemon/tools/install_3d_dbcs.py --server-data env/dist/bin/data`. This uses the checkout's existing `env/dist/bin/data` layout (`DataDir = "data"` in `env/dist/etc/worldserver.conf`) and verifies/installs six paired eDBC layers into its `dbc-continuations` subdirectory. Existing conflicting layers cause a refusal.
4. **Only for a 2D to 3D transition that has not already been applied:** with worldserver stopped and database backups verified, manually import `modules/mod-battlemon/migrations/manual/2d-to-3d/world.sql` into the world database and `characters.sql` from that folder into the character database. Read the folder's README first. Base module SQL must already be installed. Do not use `--force`. These files are outside the automatic updater. **If your server already successfully applied `rev_1790798400.sql`, skip this step; do not rerun it or edit updater history.**
5. Build on your remote server using your normal process, then restart the server and fully restart WoW. No core compilation, remote deployment or production SQL execution was performed here.

Both existing battle UI modes, wild battles, human duels and Playerbot duels remain available. All encounter selection uses the supported 3D catalog. Shiny selection only chooses authored available variants. Existing saved addon teams prune removed owned IDs after a complete server ownership snapshot.

## Rollback

Stop the server and restore the 2D modules/addons/client files as a unit. Restore your pre-migration databases for a complete rollback. For targeted recovery of only removed owned Pokemon, review `data/3d/rollback-characters.sql`: persistent `battlemon_3d_removed_*` tables retain the old ownership IDs, parties and taught moves. Occupied IDs/party slots are not overwritten. The world migration also preserves removed unsupported fixed spawns in `battlemon_3d_removed_spawns`. Disable the extra eDBC layer when reverting to 2D. Raw texture backups and all historical deferred packages remain intact.

## Validation limits

Catalog consistency, exact file hashes, eDBC references, Lua 5.1 runtime mocks, existing battle UI regression and compressed model renders are checked. The repository-wide linters have pre-existing findings; the SQL linter additionally cannot fetch this checkout's origin/master. Backup INSERT IGNORE statements deliberately preserve history instead of deleting backups. A live client/server test and remote build still belong to deployment: verify collection previews, a rescued original form, an extra palette, a shiny, switching/capture, and a Playerbot duel.

## Migration history

The one-time transition previously shipped as `rev_1790798400.sql` in the pending updater folders.
It is now manual-only under `migrations/manual/2d-to-3d`. Already-applied database changes remain valid;
normal restarts must not repeat the transition. The corrected script uses runtime `creature.id` and
was tested against fresh, repeated and partially committed migrations in disposable MySQL databases.

## Living 3D distribution

`C:/data/pokemon-mod/3d-version` is the living distribution. Module, addon, migration and client asset
changes must be copied there and its SHA-256 manifest updated together. The `2d-version` snapshot is frozen.

After module/client edits, run `python modules/mod-battlemon/tools/sync_3d_distribution.py --apply`
from the development checkout. It rejects independently edited package files, verifies source and
copy hashes, and updates the manifest. Without `--apply` it only checks and reports changes.

## Elwynn Battlemon Center

The new Center needs its paired display and collision files installed on the stopped server before restart.
See [Center deployment](data/center/README.md). Its placement uses the supplied Elwynn GPS.


## Optional Pokemon Trainer profession

The living 3D package also contains mod-pokemon-trainer. See
server/modules/mod-pokemon-trainer/README.md for deployment and manual rollback SQL.
It uses one Ditto companion, owner-level combat scaling and your existing captured forms/moves.
Client additions are in patch-z.mpq; server DBCs and both config files are installed with
modules/mod-pokemon-trainer/tools/install.py. A worldserver build including the new module
is required. The frozen 2D snapshot is unchanged.
