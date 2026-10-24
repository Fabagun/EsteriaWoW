# Battlemon overworld

Included in the unified `mod-battlemon` module; no separate overworld module is installed.
Right-click a world Pokemon to start a wild battle. Its exact form/palette comes from
`src/BattlemonModelCatalog.h`, including the 980 Extras. Display IDs are catalog lookups, not
an arithmetic assumption for every form. Overworld clicks preserve the existing Fight cooldown rules.

All `BattlemonOverworld.*` options remain in `conf/mod_battlemon_overworld.conf.dist` and existing
`mod_battlemon_overworld.conf` files continue to load. Critter morphing, reroll timing, scale/height,
hover and per-form nudges retain their behavior and defaults. `.bmo` commands are unchanged.

World SQL remains under `data/sql/world/base/`, with original filenames and contents. Applied-file
tracking uses those filenames, so moving the SQL does not require reimporting it. New deployments
also need the catalog migration and client/server eDBCs described in [3D deployment](../3D-DEPLOYMENT.md).

Legacy 2D conversion tools and historical source-conversion reports remain preserved. The active
edition uses 3D models; do not run the old plane/sprite installer against an active 3D client.
