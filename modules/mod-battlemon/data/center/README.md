# Battlemon Center - Elwynn Forest

Custom walk-in building inspired by the supplied reference: stone base, timber framing,
blue slate roof, stained-glass windows, Pokeball medallion, pendant lighting, healing
counter, collection terminal and shop shelving. The source Blender file is included.
The terminal mesh is decoration; party management is available through either attendant.

Entrance: map 0, phase 1, X -9062.506, Y 352.9509, Z 93.1162, facing 2.3489094.
The building origin differs from the entrance; see placement.json. Footprint is about
27 by 20 yards including roof overhangs, benches and steps. Terrain fit needs an in-game check.

## Remote deployment

The local client patch is installed separately by the agent. Fully restart WoW after delivery.
Push/pull the repository and build the server using your normal workflow. With worldserver
stopped, run from /root/dark-brotherhood/core:

```sh
python3 modules/mod-battlemon/tools/center/install_center.py --server-data env/dist/bin/data --apply
```

This installs the paired GameObjectDisplayInfo continuation, Center collision model and one
entry in the existing GameObjectModels.dtree, preserving all existing records and saving a
backup. It checks display ID collisions and refuses to replace independently changed files.
Repeating the same installation is safe. Do not regenerate the collision index without
reinstalling this Center entry afterward.

Start the rebuilt server with the normal world updater enabled. The pending update named
in placement.json places the building and two stationary attendants. It runs once through
the updater and guards custom entry collisions. It supports both creature.id and creature.id1.
No character-data migration or manual SQL import is required for this building.

Both attendants offer party healing, the existing Battlemon shop and existing party/move
management. Healing restores the current six-slot party, preserves equipped moves, and is
unavailable during combat, battles, duels or a Pocketmon session. Existing shop prices and
purchase rules are unchanged. No new remote healing addon command is exposed.

## Verification and limits

- Client WMO v17 geometry and VMAP_4.8 server geometry match exactly.
- Collision trees cover all triangles; doorway, floor and walls have offline ray checks.
- All texture mipmaps decode; ISPC BC3 output reproduces exactly from retained PNG sources.
- The final exported WMO and decoded BLP textures were rendered for exterior/interior review.
- Lua 5.1 packet tests cover capture banners, final escape, close timing and center panels.
- Installer fixtures cover repeat installation, collision-index preservation and changed-file rejection.
- Module C++ style checks pass. No core compilation or live server test was performed.
- Root C++ lint has existing failures outside this change. Root SQL lint requires an absent
  origin/master branch; targeted checks flag the valid SIGNAL MESSAGE_TEXT routine syntax.
- In-game lighting, terrain fit and server collision still require verification after deployment.
  This is a dynamic gameobject with stationary attendants; map navmeshes were not rebuilt.

Tools are under ../../tools/center.
Rebuild dependencies: Blender 4.x, Python, numpy, Pillow and ispc_texcomp==1.0.1.
Run build_center.py in Blender, then export_center.py and validate_center.py in Python.
The validator also prepares decoded review textures for render_delivery.py in Blender.
Runtime loading does not require Blender, Python, or a native-render extension on the client.

Format references used for export: this core's src/common/Collision/Models/WorldModel.cpp,
BoundingIntervalHierarchy.cpp and the upstream WowDevTools WMO format definitions at
https://github.com/WowDevTools/Blender-WMO-import-export-scripts/tree/master/io_scene_wmo/wmo.

## Missing-building correction

The original spawn used generic type 5, which instantiated an M2 error fallback instead of
loading this WMO. World update `rev_1790830984.sql` changes only the Center template to native
map-object type 14. Pull this update and restart worldserver with the normal updater enabled;
no core rebuild or asset reinstallation is needed for this correction. Reconnect the client
afterward and verify `.gobject info guid 5714478` reports Type 14 on the existing deployment.
The original already-applied placement update remains unchanged.

## Doorway, dry interior and slope correction

The dry WMO now writes legacy liquid index 15 (none); index 0 incorrectly marked the
building as water. The lower front timber is split around the doorway. The floor is raised
three yards to world Z 96.3562, above terrain vertices measured up to Z 94.79 in the client
Elwynn tile, with a deep stone foundation and 18 entrance steps. Both attendants stand at
Z 96.3562. Terrain-fit.json records the survey; live terrain/collision checks remain required.

Fully exit WoW for the client asset replacement. On the server, pull these changes, stop
worldserver, and rerun the installer command above before starting worldserver. The new
world update moves only the existing Center and its two attendants; it preserves their GUIDs.
No core rebuild is required. The installer now accepts exact known previous Center releases,
backs up replaced files, and still refuses independently modified assets or ID collisions.

## Human-scale interior correction

The room footprint is now 65% of the original, approximately 15.3 by 10.7 yards inside.
Counters stand approximately 1.06 yards above the floor; a timber ceiling closes the attic
at approximately 4.34 yards above the floor. Shelves, windows, lamps and exterior details
follow the resized building. The foundation depth and floor elevation stay unchanged so
terrain cannot re-enter the room. Attendant spawn points now follow the smaller counters,
with 0.03 yards of clearance above the exact collision floor. Install the paired assets and
restart with the new pending world migration before checking this revision in game.

## Continuous doorway landing

A level landing now connects the top stair directly to the interior floor. Previously,
the gap between these meshes exposed the lower foundation and created a threshold lip.
Validation samples the complete walking path at three lateral positions, including the
join. This asset-only change needs paired client/server assets and restart, without a new
SQL update. The reported NPC clipping remains under investigation: live NPC Z 96.3862
is already above server FloorZ 96.3562; an independent player-height reading is required.
