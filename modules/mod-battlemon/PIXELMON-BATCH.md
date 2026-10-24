# Pixelmon bulk conversion

The standalone converter inventories the Battlemon catalog, resolves explicit Pixelmon metadata, exports animated
WotLK M2/SKIN/BLP assets, and installs direct replacements at the original sprite paths. It does not call any model API,
contact an AI service, or require a Codex conversation to remain open. CPU time and disk usage continue locally.

The catalog currently contains 1,581 Battlemon forms, or 3,162 normal/shiny appearances. These are not 3,162 unique
meshes: geometry is cached separately from textures. The initial metadata resolver maps 2,114 appearances; the
other 1,048 are explicit exceptions. Mapping is only the first gate; conversion can reject additional appearances.
The converter does not yet guarantee complete catalog coverage.

## Run it

From a PowerShell terminal in the repository root:

```powershell
# Default: the representative 50-form / 100-appearance sample, excluding the original four-form pilot.
.\modules\mod-battlemon-overworld\tools\manage-3d-batch.ps1 -Action sample

# Full catalog, using the same cache. This stages output; it does not install anything.
.\modules\mod-battlemon-overworld\tools\manage-3d-batch.ps1 -Action all

# Re-run the same command to resume. Retry previously failed conversions explicitly:
.\modules\mod-battlemon-overworld\tools\manage-3d-batch.ps1 -Action all -RetryFailed

# Restrict a troubleshooting run to explicit Battlemon form IDs:
.\modules\mod-battlemon-overworld\tools\manage-3d-batch.ps1 -Action sample -Forms '2,7,12'
```

Only run one conversion or installation against a given output folder at a time. Keep the terminal and PC running;
the script does not schedule itself or prevent sleep. Interrupt with Ctrl+C; the next run checks existing results
and reuses completed appearances. `report.json` is checkpointed after each form and worker results after each
appearance. An unfinished appearance can be rebuilt. Cached failures are skipped unless `-RetryFailed` is used.
Changed source bytes, animation speed, or converter code invalidate affected cache keys. Successful cache hits also
verify output file hashes before reuse. Do not edit converter files during a run.

Each form runs in a separate subprocess, with a default 240-second timeout; `-TimeoutSeconds` changes that limit.
There is one worker at a time. Large animation data can still use substantial RAM; the timeout is not a RAM limit.
Failed forms do not stop the rest of the catalog. Fixing a common unsupported case can unlock many forms at once.

Parameters include `-Python`, `-Pixelmon`, `-Client`, `-ServerData`, and `-Output`. Defaults use this workstation's
paths and the repository's `env/dist/bin/data` server distribution. Python 3.10+ needs NumPy and Pillow 12.3+ with
the DDS/DXT5 encoder. Blender is only needed for optional visual previews, not batch conversion.

## Results and validation

Output is local and gitignored under `modules/mod-battlemon-overworld/generated/pixelmon-batch/`:

- `inventory.json`: every form, resolved assets, and mapping exceptions.
- `report.json`: progress, per-appearance results, source paths, timings, and validation metrics.
- `exceptions.json`: held-back appearances and reasons after a completed run.
- `cache/`: reusable mesh/appearance results, exported assets, worker jobs, and logs.
- `package/`: internal source-export validation package; its experimental eDBCs are not deployed.
- `direct-package/manifest.json`: canonical deployment allowlist, source/original hashes and mappings.
- `direct-package/Creature/Battlemon/`: original-filename client payload; contains no eDBCs.
- `installed-direct.json`: ownership and legacy archive receipt; retain for updates and rollback.
- `preview/`: decoded exported textures/geometry and optional render/contact sheet.

A package contains only successes from the selected run. Running with `-Forms` replaces the staged package selection;
run `-Action all` again before installing if you want every cached success included. It does not clear the cache.

Every successful appearance passed independent M2/SKIN parsing, bone/weight/animation checks, bounds checks,
four-weight deformation limits, and bilinear UV-edge alpha checks across every BLP mip.
Solid alpha-key models require at least 240/255 at sampled borders (16 levels above the renderer
reference cutoff of 224), with exact material/full-opacity validation. Nonopaque counts remain diagnostic. The seam fix pads texture
island colors into transparent gutters. Models with significant transparent triangle interiors are held back so
this padding does not erase intentional cutouts. These checks do not establish visual quality in the game renderer.

Current deliberate limitations include ambiguous numeric variants, absent gender/shiny palettes, multipart models,
unsupported model modifiers, multiple materials, incompatible skeletons, and intentional transparent surfaces.
Emissive maps are noted but not reproduced. Idle and movement are exported; movement prefers walk, then fly/swim,
then idle, and run currently reuses that sequence. The standing height is normalized to one WoW unit before existing
server creature scaling. This is a critter conversion, not a complete port of every Pixelmon animation/effect.

## Install or undo

```powershell
# Optional repeat of binary, animation, seam and hash checks on the prepared direct package.
.\modules\mod-battlemon-overworld\tools\manage-3d-batch.ps1 -Action validate

# Install validated successes under original client filenames; retire owned experimental layers.
.\modules\mod-battlemon-overworld\tools\manage-3d-batch.ps1 -Action install

# Undo exactly the batch's installed files using its persistent receipt.
.\modules\mod-battlemon-overworld\tools\manage-3d-batch.ps1 -Action remove
```

The client assets live in `Data/patch-z.mpq/Creature/Battlemon/`, using the exact filenames referenced
by existing `.dbc1-battlemon` records. Embedded BLP references use the same names. No new or modified
DBC records are deployed. Unsupported appearances retain their original sprites. The original patch-W
files stay unchanged. Install repackages the ready report and verifies source hashes; it refuses a report
from an unfinished full run. The detached runner still deep-validates its internal source package first.

During migration, receipt-owned `Battlemon3DBatch` assets and experimental pilot/batch 3D eDBC layers
are hash-verified, archived to `legacy-backup/`, and retired. Pilot model files remain preserved.
If old layers were deployed remotely, remove `CreatureModelData` and `CreatureDisplayInfo` files with
both `.dbc9-battlemon-3d` and `.dbc9-battlemon-3d-batch` suffixes there and restart worldserver.
Keep the base Battlemon continuations and grounding config. No remote connection is made by this tool.

`installed-direct.json` journals ownership before writes for resumable installation and rollback.
Preflight rejects unowned or externally modified destinations. Retain that receipt, legacy receipts and
archives. Removal reveals the original sprites without reactivating experimental 3D DBC mappings.
Close WoW before installing/removing and reopen it afterward. No recursive deletion is used.

The historical sample/pass notes below describe earlier deployment layouts. This section supersedes
instructions below to deploy experimental eDBC files or hash-named client assets.

## Visual review

```powershell
& 'C:\data\_tools\PortableApps\BlenderCompatPortable\App\Blender64\blender.exe' --background --python `
  .\modules\mod-battlemon-overworld\tools\pixelmon\preview_batch.py -- `
  --output .\modules\mod-battlemon-overworld\generated\pixelmon-batch
& 'C:\Users\dead\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' `
  .\modules\mod-battlemon-overworld\tools\pixelmon\batch_report.py
```

The sheet renders normal appearances from the exported M2 idle pose and decoded BLP, not the original Minecraft mesh.
It is a useful gross-error check; inspect idle, movement, scale, shading, and seams in-game before broader deployment.

## Initial sample result (2026-09-27)

The 50-form sample attempted 100 appearances: 65 passed, 25 failed conversion gates, and 10 were unmapped/unsupported.
That covers both appearances of 32 forms plus shiny Tentacool. The other 35 appearances keep their existing sprites.
The first run took 762.66 seconds (12 minutes 43 seconds); a cached rerun took 1.91 seconds, reusing all 90 mapped
appearance results including cached failures. The package is 44.7 MiB and contains 199 files: 195 assets and four DBC
copies. It was installed to the local client and repository server distribution; 1,158 pre-existing files were
fingerprinted and verified unchanged. This is the sample deployment, not a completed full-catalog conversion.

Independent deep validation passed for all 65 appearances, including every texture mip seam and paired DBC rows.
All 15 focused conversion/deployment tests passed. Blender previews were inspected from decoded exports. The
remote realm has not been tested with this batch. Restart/deploy through the normal server workflow before in-game
verification. Repository-wide C++ lint reports existing style errors; SQL lint reports existing SQL issues and
cannot finish its required `origin/master` fetch. No C++ or SQL files were changed by this batch work.

Held-back categories: 10 appearances need multiple materials; six hit compressed-source read errors; five need
transparent-material review; four need non-power-of-two texture handling; four use multipart models; two have an
ambiguous numbered variant; two need a rotation modifier; and two have ambiguous default forms. These are the next
shared converter improvements, rather than 35 independent manual conversions.

## Client crash repair: render bone palettes (2026-09-27)

The in-game `.bmo spawn 10` test crashed build 12340 at `0x0068453D`. Offline validation had missed a render limit:
Mega Charizard Y was exported with all 79 bones in one section, and every skin advertised the 256-bone tier.
The client's shader path uploads three constant registers per section bone, starting at register 31. A 79-bone
section overruns a 256-register buffer. The crash dump shows a corrupted vertex-format index at the subsequent
binding operation, consistent with that overflow. Lugia's 80-bone section had the same defect.

The exporter now partitions triangles into compact section palettes of at most 64 bones, duplicates shared vertices
at section boundaries, and emits one material batch per section. Each SKIN property resolves through its section's
palette back to the original skeleton bone. Every skin advertises the 64-bone tier, also limiting instanced draws.
The independent validator checks section coverage, local/global bone mapping, material references, and that limit.

The installed sample repair retains asset names, textures, DBC rows, and animations. Mega Charizard Y now has four
sections (64/64/64/51 bones); Lugia has three (64/64/47). Normal and shiny variants are repaired. The other sample and
pilot skins receive only the corrected tier. Per-triangle UVs and all decoded animation frames were compared before
and after partitioning and were identical within 1e-7. Regression tests include an 80-bone mesh, vertices shared
between sections, unsafe tiers, oversized palettes, and incorrect local bone indices.

Close and reopen the client, then retry `.bmo spawn 10` and `.bmo spawn 10 1` before broader testing. No server DBC
redeployment is needed for this repair. The full-catalog run remains on hold until in-game verification succeeds.
Offline checks alone are not an in-game crash-fix confirmation. Existing build caches are invalidated by the
exporter/validator change; the repaired sample remains staged and installed at its existing paths.

Render-path reference: [whoa CM2SceneRender::DrawBatch](https://github.com/whoahq/whoa/blob/master/src/model/CM2SceneRender.cpp).
Local crash analysis, original assets, and the repair verification report are under `generated/crash-form10/`.

## Approved full-catalog run and grounding correction (2026-09-27)

The user confirmed the repaired Mega Charizard Y renders and the other in-game sample tests look good. Its remaining
height offset came from the server's Flying-type heuristic, not the model mesh. The tracked module config template
and both env/dist module config files now set `BattlemonOverworld.Nudge = 10::0`. This preserves automatic scale and
sets hover to zero for normal and shiny Mega Charizard Y. Other species, including Zubat, retain their hover rules.
Deploy the updated server config and reload configuration (or restart worldserver); respawn the test creature or use
`.bmo remorph` on the existing target. Client model replacement cannot change this server-owned hover flag.

`tools/pixelmon/run_full_batch.py` is a detached runner for conversion of the entire catalog followed by independent
deep validation. It writes `generated/pixelmon-batch/full-run.json` with its PID, child PID, phase, log path, and final
status. A Windows file lock prevents a second detached runner from using the same output concurrently. Detailed logs
and the previous report are saved under `generated/pixelmon-batch/runs/<UTC timestamp>/`. A completed conversion
must cover the entire inventory; validation failure or incomplete output cannot produce a ready status.

An hourly follow-up in this task checks that state and stays quiet while the job is healthy. When ready, it reviews
representative exports, installs validated successes, prepares the repository server continuations, reports remaining
exceptions, and disables itself. The script runs without AI calls; scheduled checks and final review consume normal
agent usage. Keep the computer awake and Codex running for follow-ups. The current sample stays installed during
conversion. Conversion success is separate from in-game verification of the additional species.

The full run is complete and installed locally. See [full-catalog results](PIXELMON-BATCH-RESULTS.md) for counts,
exceptions, remote-server deployment, and rollback instructions.
