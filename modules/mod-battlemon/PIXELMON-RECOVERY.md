# Missing appearance recovery

The first installation (1,650 / 3,162 appearances) is a baseline, not completion of the catalog.
The user explicitly asked to address the missing appearances. Continue recovery after each batch;
do not mark the overall task complete merely because unsupported records retained their sprites.

## Current deployment requirement: original sprite paths

The user requires direct patch priority overrides, with no new or edited eDBC records.
`tools/manage-3d-batch.ps1` now routes install/remove/validate to `pixelmon/direct_deploy.py`.
It maps each existing display/model record to its exact original `Creature/Battlemon` filename,
including `_s` shiny names. Client payload is `Data/patch-z.mpq/Creature/Battlemon/`.
Only embedded model/texture strings change; SKIN, BLP, geometry and animation bytes are preserved.
`generated/pixelmon-batch/direct-package/manifest.json` records source hashes, canonical hashes,
original sprite hashes/absence, base DBC hashes and the report used. Internal hash-named cache
and `package/` artifacts remain conversion/validation inputs; NEVER deploy their experimental eDBCs.

The already deep-validated 2,787-appearance pass-4 baseline is migrated using the immutable
`runs/20260927T213658Z/previous-report.json`. Pass 5 subsequently completed independent deep validation, final review, and canonical installation.
The installed total is now 2,817; see the pass-6 installation evidence below.

`installed-direct.json` journals canonical ownership and exact legacy retirement/archive hashes.
Original patch-W sprite files, base `.dbc1-battlemon` records and pilot model assets stay untouched.
Receipt-owned hash-named batch assets and both experimental `.dbc9-battlemon-3d` and
`.dbc9-battlemon-3d-batch` layers are archived to `legacy-backup/` and retired from client/repo
server delivery. The four pilot eDBCs in `full-review/existing-files.json` must now be verified
against their retirement archives; all other baseline files remain at their original paths.
Keep legacy receipts and archives. No recursive directory deletion is used.

A source catalog gap exists for shiny form 510: the original DBC references
`0323_Camerupt_01_female_s`, but its three sprite files are absent. Deploy the validated 3D
appearance to that existing DBC path; record original absence instead of inventing an alias.
The adapter rejects changes to that recorded absence during package verification.

Evidence lives in `direct-migration-review/`: complete original sprite/base-DBC hash snapshot,
representative decoded equivalence (including Shadow Rider Calyrex), and installation summary.
Five direct-deployment regression tests cover binary equivalence, archival/resume/rollback,
external-file protection, missing original sprite evidence and unexpected geometry changes.

Remote realm cleanup, if experimental layers were previously deployed: remove BOTH table files
(CreatureModelData and CreatureDisplayInfo) for BOTH experimental suffixes and restart worldserver.
Keep the base `.dbc1-battlemon` layers and the `10::0` config correction. There are no replacement
3D eDBCs to deploy. No remote changes or live tests have been performed. Restart the local client.
Rollback `manage-3d-batch.ps1 -Action remove` removes owned canonical overrides and returns to
original sprites, retaining archives; it does not reactivate experimental 3D mappings.

Historical pass notes below describe earlier deployment states; this section supersedes their
instructions to install eDBCs or preserve experimental layers at active paths.

## Recovery pass 1

Implemented and regression-tested:

- BMD material labels: Pixelmon's shipped `SmdModel.load` reads the labels but discards them
  when constructing `NormalizedFace`; all faces use the JSON model definition's one texture.
  Removing the one-label restriction therefore preserves source rendering semantics.
- Incomplete XZ stream endings: decode available bytes, then require every declared BMD record,
  valid indices, finite values, and exact payload consumption. Reject trailing compressed data
  and decompression above 64 MiB. All 87 unique assets associated with the 60 original
  compression failures contain structurally complete payloads. This does not assert an absent
  XZ footer/checksum was verified. The source loader also consumes only declared records.
- Non-power-of-two textures: resample the full canvas to the next powers of two, preserving
  normalized UV coordinates; never add canvas padding that moves texture features.
- Gender ALL models are usable for females when no female-specific source model exists;
  such records explicitly carry `pixelmon_shared_gender_model`. No male-only fallback.
- Pass 1 treated explicit zero rotation as a no-op. The current renderer audit disproved
  that assumption; see pass 5 for corrected transform handling and replacement review.
- Descriptive form suffixes and color/pattern palettes are resolved explicitly.
- Default forms were reviewed against the actual addon sprites (reference sheet below).
- Numerical variants remain unresolved unless their identity can be verified.

Mapping improved from 2,114 to 2,621 appearances. Mapping is not successful conversion:
newly mapped models still pass through all export and deep-validation gates.

The recovery runner preserves the exact files of previously successful appearances across
converter revisions, verifies their hashes before reuse, and checks no prior success was lost.
It does not mislabel old outputs with new converter cache keys. It packages the union of old
successes and recovered successes, so installing a partial recovery cannot drop the baseline.

```powershell
& '<python>' -X utf8 modules/mod-battlemon-overworld/tools/pixelmon/run_full_batch.py --recover
```

Use the existing default output directory so installation receipts and rollback ownership survive.
The launcher snapshots the previous report in its timestamped `runs` directory. It runs deep
validation after conversion and stops at `ready`; the scheduled follow-up reviews and installs.
While a full run is healthy, do not edit converter files, start duplicate workers, or poll logs.

## Evidence and checks

- 25 Python regression tests passed, including truncated versus complete BMD payloads,
  non-square texture resampling, explicit mappings, section bone limits, and preservation.
- Source bytecode audit: `generated/pixelmon-recovery/smd-bytecode.txt`.
- Default sprite reference: `generated/pixelmon-recovery/default-sprites.jpg`.
- Representative conversion/review: `generated/pixelmon-recovery/smoke`. Twenty appearances
  passed conversion and independent deep validation; ten normal exports were visually reviewed
  in Blender (`smoke/review.jpg`). Butterfree normal/shiny remain held for intentional cutouts.
- Repository C++ and SQL style scans report pre-existing unrelated violations; the SQL scan
  also fails its `git fetch origin master`. No C++ or SQL was modified by this recovery pass.

## Next groups to implement after the run

1. Intentional alpha cutouts and remaining seam failures. Butterfree reaches this gate after
   the material-label fix. Preserve wing/leaf holes rather than filling them to pass seam checks.
2. Multipart definitions, attachments, and nonzero transforms. Support actual composition
   and texture bindings rather than discarding model parts.
3. Numeric variant aliases, including Alcremie sweets/colors and regional forms. Verify
   against addon sprites and source palettes; do not assume Pixelmon form-list ordering.
4. Missing/static source animations, skeleton mismatches, weight-reduction errors, extreme
   bounds, and timeouts. Keep source fidelity and validation; don't just suppress failures.
5. Distinguish genuinely absent source assets from converter limitations with a per-form audit.

Preserve the 64-bone render-section limit, seam validation, original sprite/pilot files, and
Mega Charizard Y `BattlemonOverworld.Nudge = 10::0` in all three tracked configs.
Server continuation deliverables belong in `env/dist/bin/data/dbc-continuations` in this repo.
The realm is remote. Local installation does not constitute remote deployment or live testing.

## Recovery pass 1 installed / pass 2 prepared

On 2026-09-27, recovery pass 1 installed 846 additional appearances, for 2,496 total
(1,245 normal, 1,251 shiny). Independent deep validation passed for all 2,496; installation
hash checks passed for all 7,402 active package files. The 1,650 baseline appearances and
1,158 pilot/non-batch files remain unchanged. Reviewed 23 decoded exports, including
178-bone Mega Rayquaza and three shiny variants. Receipt and server eDBC delivery paths
are unchanged. `recovery1-review/installation-summary.json` records the results.

Pass 2 adds `tools/pixelmon/variant_aliases.json`: 57 numerical forms visually compared
against both actual addon sprites and Pixelmon's declared normal-palette sprites. Each alias
pins the addon ID, name, sprite key, species dex, source form and gender. Reference sprite
SHA-256 hashes are retained as review evidence. Mismatched catalog identities are rejected.
The alias file is part of the converter revision hash. No absent shiny palette is replaced
with a normal palette. This raises mapping coverage from 2,621 to 2,721 appearances;
conversion and validation still determine which of those can be installed.

Reference sheets: `generated/pixelmon-recovery/variants/comparison0.jpg` through
`comparison2.jpg`; representative conversion output: `generated/pixelmon-recovery/variant-smoke`.
26 regression tests passed. Remaining alpha/multipart/animation problems are still active work.
Terapagos Stellar (form 1580) lacks its declared source reference sprite; its model assets
have not yet been audited, so this is not yet evidence that the 3D form is unavailable.

Pass 2 representative result: 19 appearances passed independent deep validation; 10 normal
exports were visually reviewed in `variant-smoke/review.jpg`. Pikachu Belle has no source
shiny palette; Ogerpon Wellspring still requires multipart support. Neither was substituted.
The next full `--recover` run preserves all 2,496 installed appearances before adding successes.

Prepared `generated/pixelmon-recovery/multipart-audit.json` for subsequent engineering:
40 normal forms use multiple model definitions; most share one texture and a skeleton.
Examples: Flygon body + eyes, Rotom body + translucent spectre, Furfrou body + separate fur
texture, Calyrex rider + horse, Ogerpon body + hood + mask. Preserve every part and relative
coordinates; do not normalize each part independently. Some need transparency as well as
composition. The audit is read-only evidence, not implemented multipart support.

## Recovery pass 2 installed / pass 3 prepared

Pass 2 installed 96 additional appearances, for 2,592 total (1,296 normal, 1,296 shiny).
All 7,684 active package files match installed hashes. All 2,496 prior successful exports
and 1,158 pilot/non-batch files are unchanged. Independent deep validation passed;
16 newly recovered exports were reviewed, including large rigs and shiny variants.
Full evidence: `generated/pixelmon-batch/recovery2-review`.

Pass 3 implements opaque multipart composition in `tools/pixelmon/multipart.py`:

- Prepare each part in the same unnormalized coordinate system with its own bind pose
  and animation files. Then apply one standing-height normalization and grounding to
  the assembled creature. Never move a rider, fur, mask or sweet to its own ground plane.
- Keep independent part bone transforms even when bones have identical names. Remove
  unused bones only after baking hierarchy transforms. Enforce 256 total weighted bones,
  65,535 vertex/index limits, and the existing 64-bone per-render-section limit.
- Validate matching sequence IDs, durations and timestamps across independently animated
  parts. Differing rates/scales, intentional translucency, glow and other unknown modifiers
  remain explicit failures; no parts are dropped to produce a success.
- Combine up to four distinct textures into an atlas, with duplicated borders and matching
  UV transforms. Preserve source pixel density and reject atlases above 4096 pixels or
  wrapping UVs. Shared textures use their original image. Keep interior-alpha and all-mip
  seam checks. Fingerprints include every part's model and animation content; normal/shiny
  geometry can still share a verified cache entry when layout is the same.
- Map all 63 Alcremie color/sweet combinations using exact addon/source sprite comparisons.
  Each combination selects its source normal palette and the correct sweet's shiny palette.
  The body and sweet have separate animation files with matching timings.

30 regression tests passed. New composition tests independently compare every decoded
animated vertex position, including differing part binds, rotations and common grounding;
they also check atlas identity, border texels, timing rejection and cache dependencies.

Representative evidence:

- `generated/pixelmon-recovery/multipart-smoke`: Furfrou, Ice Rider Calyrex and Ogerpon,
  normal + shiny: six appearances independently deep-validated; three assemblies visually
  reviewed. Flygon/Litwick/Cosmoem still fail seam checks. The earlier Eiscue sample ran
  before allowing distinct per-part animation files; the full pass will retry it.
- `generated/pixelmon-recovery/alcremie/comparisons.jpg`: all 63 addon/source sprite pairs.
- `generated/pixelmon-recovery/alcremie-smoke`: seven sweet types across representative
  flavors, normal + shiny: 14 appearances independently deep-validated.
- `generated/pixelmon-recovery/alcremie-review/review.jpg`: all 14 exports visually reviewed.

Mapping coverage is now 2,878 / 3,162; this is not an installation count. The next detached
recovery run must preserve the 2,592 installed appearances. Remaining alpha cutouts,
translucent parts, glow, transform modifiers, skeleton issues and genuinely absent source
variants remain active work after this pass.

## Recovery pass 3 installed

On 2026-09-27, pass 3 installed 151 additional appearances, for 2,743 total.
All 7,969 active package files match installed hashes, including both repository server eDBCs.
All 2,592 prior successes and 1,158 pilot/non-batch files remain unchanged.
Deep validation passed for the full combined package. Reviewed 24 decoded new exports,
including 142-bone Shadow Rider Calyrex, both riders, five Furfrou trims, Eiscue,
four Ogerpon masks, Alcremie flavors, and shiny variants. Evidence and previous receipt:
`generated/pixelmon-batch/recovery3-review`. The run is finalized; recovery is not complete.

419 appearances remain: 135 conversion failures and 284 unsupported mappings/modifiers.
Continue with cutout/seam handling, translucency, transforms, animation/skeleton cases,
and a source-asset audit of unresolved numerical forms. Preserve all 2,743 installed successes.
A metadata inspection found the 22 missing-idle appearances declare no animation entries
(Kakuna, both Frillish/Jellicent genders, Elgyem, Beheeyem, Shelmet, Accelgor, Diggersby,
Klefki). Determine whether their BMD models or other declared source mechanisms provide
motion before choosing an explicit static-source policy; do not invent animations or silently
weaken the static-motion gate. Morpeko and Hangry Morpeko each declare two idle entries
(`idle_hangry.bmd`, `idle_normal.bmd`); verify source loader selection semantics or exact
form identity before resolving the duplicate. These are investigations, not recovered models.

## Recovery pass 4 prepared: source motion and skeleton channels

The current shipped renderer is `client.render.entity.renderers.smd.SMDModelLoader`
plus `assimp.Scene`; the older `ValveStudioModel` QC loader is not the authority for
JSON animation selection. Bytecode evidence is saved under `generated/pixelmon-recovery`:
`current-loader-bytecode.txt`, `scene-bytecode.txt`, and `renderer-bytecode.txt`.

- `SMDModelLoader.loadAnimations` preserves declaration order. `Scene.getAnimation`
  returns the first matching name, so repeated idle entries use the first declared
  clip, including both Morpeko forms. The converter records that selection explicitly.
- An empty animation list produces no animation channels. `Scene.createBoneWorldTransform`
  retains the model nodes' local bind transforms. These sources now export an explicit
  `static_bind_pose` policy, with identity skin transforms and all original geometry.
  No walking motion is invented. Models that declare animations but lack idle still fail.
- Static policy is carried in result/manifest records with a required annotation. Independent
  decoding requires EVERY exported pose to equal the bind vertices. The default animated
  policy still rejects static walks; unknown policies are rejected. No seam, bounds,
  palette or 64-bone check is bypassed. The deployment validator is now revision-hashed.
- The current loader builds named LOCAL animation channels without animation-parent links.
  Scene traverses the MODEL hierarchy and uses local bind transforms when channels are
  absent, even for weighted bones. The converter now matches this behavior and records
  every differing parent and missing-channel fallback. Missing channels still inherit
  animated ancestors. Duplicate bone names remain ambiguous and are rejected.

35 regression tests passed, including exact static geometry with nontrivial bind transforms,
rejection of mislabeled moving/displaced static exports, default static-walk rejection,
first-declared selection, policy annotations, and independently checked inheritance of parent
motion by a weighted missing channel. Existing animation, seam and 64-bone tests pass.

Representative results (isolated packages, not installation counts):

- `source-motion-smoke`: 28 appearances independently deep-validated: all 22 no-animation
  appearances, four Morpeko appearances, and two Mega Charizard Y regression appearances.
- `binding-smoke`: 18 appearances independently deep-validated: Golduck, Starmie (01), Togepi,
  Mantine, Gardevoir, Kyogre, Gallade, Frogadier and Aegislash, normal/shiny. Basculin and
  Blue-Striped Basculin now reach the static-walk gate and remain excluded (four appearances).
- `source-motion-review/contact-sheet.jpg`: 33 reviewed decoded renders, including every
  newly recovered normal, all nine repaired animated rigs at idle and mid-walk, plus two
  shiny examples. `validation-summary.json` records counts and bytecode evidence hashes.

The next full recovery run preserves all 2,743 installed appearances and retries missing ones.
These samples demonstrate 44 new recoveries. Static-source appearances must be described
as static 3D models, not animated conversions. Alpha cutouts, translucency, transforms,
other animation failures and absent/unmapped variants remain active work after this pass.

## Recovery pass 4 installed

Pass 4 installed 44 additional appearances, for 2,787 total: 1,393 normal and 1,394 shiny.
22 are explicitly static 3D models. Independent deep validation passed; all 8,101 active
installed hashes match, including both repository server eDBCs. All 2,743 earlier successes
and 1,158 pilot/non-batch files remain unchanged. Reviewed 16 final decoded exports in
`generated/pixelmon-batch/recovery4-review`; previous receipts and finalization evidence are
retained there. 375 appearances remain (117 conversion failures, 258 unsupported).

## Recovery pass 5 prepared: source transforms and orientation corrections

`ModelData` defaults `rotate_angle` to [-pi/2, 0, 0], not zero. The current
`SMDEntityRenderer.applyModelRotations` applies translation, Y rotation, Z rotation,
X rotation, then scale. Angles are radians. `model_transform.py` converts that matrix
back from Minecraft Y-up into the converter's Z-up source space. Geometry, normals,
skinning matrices and bounds receive the same transform before common grounding and
height normalization. Positive uniform scale is supported; nonuniform/reflected scale
still requires affine animation support and is explicitly rejected. Multipart definitions
retain common coordinates and every part's transform is included in cache fingerprints.

The earlier assumption that explicit [0, 0, 0] was a no-op was wrong: it replaces the
-90-degree default. `zero-rotation-review/comparison.jpg` compares the installed and
corrected Cubone, Zigzagoon and Metagross exports. Zigzagoon/Metagross were standing
on end; applying the declared source transform restores their orientation. A metadata
and resolved-appearance audit identifies 70 installed appearances / 35 forms to review:
`generated/pixelmon-recovery/explicit-zero-audit.json`. These are corrections to existing
appearances, not increases in conversion coverage. Earlier files must remain recoverable.

The runner and batch now accept an explicit `--refresh-forms` list alongside `--recover`.
Only those named forms may change successful export mappings. Failed corrections retain
prior validated records. New assets get new hashed filenames; old cached and installed
files are preserved. After conversion, the runner verifies every old cached file hash,
requires every previous appearance still to pass, and rejects changes outside its allowlist.
The run snapshots its original report and records `refresh_forms` / `refreshed_appearances`.
Final review must compare changed records against that exact allowlist, distinguish new
appearances from corrected appearances, retain previous receipts, and verify original
asset bytes. Existing pilot files, seam checks, 64-bone sections, and `10::0` remain intact.

41 regression tests pass, covering known matrix order/units, explicit zero versus default,
animated positions and normals after a combined rotation/offset/scale, grounding, invalid
transforms, geometry-cache invalidation, failed-correction fallback, rejected unlisted
changes and detection of overwritten old assets.

`transform-smoke`: 30 appearances deep-validated (26 modifier samples plus four regression
controls). 16 decoded exports were reviewed in `transform-review/contact-sheet.jpg`.
Dondozo normal/shiny remain rejected for ambiguous duplicate bone names; no parts were
silently substituted. The separate zero-rotation sample stages all 35 affected forms for
review before any replacements are installed.

An additional read-only inventory for the 80 remaining unmapped form identities is saved
in `generated/pixelmon-recovery/unmapped-source-audit.json`. It records source metadata
paths/hashes and declared forms/palettes. Absence from that metadata is not yet proof that
no unreferenced model asset exists; complete the sprite/asset identity audit before claiming
those appearances cannot be recovered.

Pass 5 final representative review: all 70 orientation corrections passed independent deep
validation. Reviewed all 35 corrected normal forms and three shiny examples in
`generated/pixelmon-recovery/zero-rotation-full-review/contact-sheet.jpg` (38 renders).
The old/new comparison and exact 35-form correction allowlist remain in the evidence files.
All 41 regression tests pass. The next detached run uses `--recover --refresh-forms <allowlist>`;
its state records that allowlist. Preserve every old binary file, but permit reviewed mappings
for those forms to point to newly validated corrected exports. Count those separately from
newly recovered appearances. Failed correction attempts are explicitly included in
`exceptions.json` with disposition `retained_previous_validated_export`.

## Recovery pass 5 installed

Installed 2,814 appearances (1,406 normal / 1,408 shiny) at exact original sprite paths:
27 newly recovered, plus 70 orientation corrections on the recorded 35-form allowlist.
Reviewed 19 final decoded exports. All prior successes remain covered, and every prior cache
binary remains hash-verified. All 8,442 installed files and embedded canonical texture references
match. 9,490 original sprite/base-DBC files remain unchanged; four pilot eDBCs match archives,
and 1,154 other baseline files remain unchanged. Both experimental layers remain absent from
client and repository server delivery. No new eDBCs were deployed. `10::0` remains in all configs.

`generated/pixelmon-batch/recovery5-review/` contains comparison, selection, decoded contact sheet,
prior receipts/report, installation summary, full unresolved list and finalized state.
348 appearances remain: 160 unmapped identities, 60 model modifiers (54 legacy transparency,
two attachments, two model type, two normal map), 55 seam failures, 34 interior alpha cutouts,
12 weight errors, ten static walks, seven missing palettes, six aspect ratios, two multipart
emissive and two ambiguous duplicate-bone cases. Continue engineering these causes.

## Recovery pass 6 prepared: obsolete metadata and one verified palette

Pixelmon 9.4's actual `ModelData` record/codec has twelve fields and does not read the legacy
JSON `texture_transparency` property. `SMDModelLoader` receives the model, texture provider and
animation list; the active `AssimpRenderType.getRenderColor` reads RenderContext/shader parameters,
not that discarded JSON value. Bytecode evidence: `modeldata-bytecode.txt`,
`current-loader-bytecode.txt`, `renderer-bytecode.txt`, `assimp-render-type-bytecode.txt`.
The separate legacy SMDRenderer methods are empty and are NOT the rendering authority.

The resolver now records valid obsolete values as `legacy_texture_transparency` with a note,
matching this current loader behavior. It does not invent an opacity multiplier or discard parts.
Unknown modifiers, nonfinite/invalid values, actual PNG alpha cutouts, mip seams, multipart emissive,
source timing and geometry limits remain gated. `legacy-transparency-audit.json` records all 27
previously blocked form identities. Two now expose other explicit unsupported modifiers; the rest
reach the actual geometry/alpha checks. This metadata mapping improvement is not itself coverage.

Isolated `legacy-alpha-smoke`: 18 appearances attempted; four passed (Mega Charizard Y normal/shiny
controls and Eternatus normal/shiny), fourteen remain rejected for real seam/interior-alpha issues.
Eternatus preserves both source model parts; summed source triangle counts equal the exported 7,178,
with 75 bones partitioned into safe render sections. This is not general translucent-material support.
The genuine alpha work remains needed; do not simply remove seam checks or fill intentional holes.

Dandy Trim Furfrou form 1048 declares its normal palette as `base`, not `none`. Exact addon/source
sprites were visually compared in `dandy-palette-reference.jpg`; their hashes and explicit
normal=base/shiny=shiny mapping are recorded in `variant_aliases.json` with identity guards.
`dandy-smoke` normal/shiny both pass (shiny was already installed). Six costume Pikachu shiny
palettes are absent from their declarations; do not substitute normal colors for shiny appearances.
The four absent Furfrou trims have texture directories, but those inspected directories contain only
normal/shiny sprite PNGs, no model/animation/texture payload. This is directory evidence, not yet
proof that no unreferenced model exists elsewhere in the source tree.

49 regressions pass. All six accepted sample appearances passed independent deep validation;
reviewed normal/shiny decoded renders in `pass6-review/contact-sheet.jpg`, with all-part geometry
counts and evidence hashes in `pass6-review/validation-summary.json`. Three new appearances are
demonstrated (Eternatus normal/shiny and normal Dandy Trim); actual full-run additions may differ.
The next detached recovery preserves all 2,814 installed appearances, with no refresh allowlist.
Install only after complete deep validation and final review, using canonical direct overrides.

## Recovery pass 6 installed

Installed 2,817 appearances: 1,408 normal and 1,409 shiny. Added three appearances: Eternatus
normal/shiny and normal Dandy Trim Furfrou. All 2,814 prior successes and their cached binaries
remain unchanged. Final decoded geometry, every animation frame, UVs and bounds exactly match
reviewed sample exports; all 8,451 canonical installed files and embedded references match hashes.
All 9,490 original files remain unchanged; four pilot eDBCs match archives and the other 1,154
baseline files remain unchanged. Experimental layers remain absent. `10::0` is retained.
`generated/pixelmon-batch/recovery6-review/` contains comparison, decoded equivalence, contact
sheet, prior receipts/report, installation summary, finalized state and the full 345-case list.

The updated failure categories expose actual causes: 88 seam failures, 47 interior-alpha cases,
160 unmapped identities, twelve weight errors, ten static walks, six missing palettes, six aspect
ratios, six remaining model modifiers, four multipart emissive, four multipart timing and two
ambiguous duplicate-bone cases. No remote deployment or live testing occurred.

## Recovery pass 7 prepared: solid alpha-key threshold audit

Primary renderer reference: https://github.com/whoahq/whoa/blob/master/src/model/CM2SceneRender.cpp
`CM2SceneRender::SetupMaterial` sets alpha-key reference to element alpha times 0.87843138
(224/255), and independently controls depth writes/culling. The old solid gate required every
sample to be 255, rejecting texture samples that cannot be clipped by that cutoff.

`generated/pixelmon-recovery/alpha-key-threshold-audit.json` measures all 88 current seam failures.
Only four clear a conservative 240/255 minimum at every tested mip: normal Politoed and normal
female Politoed (253), normal Manectric (243), shiny Manectric (241.54). The other 84 stay excluded.
Keep the safety margin; do not lower acceptance to the bare renderer threshold.

The writer checks unsafe samples below 240; independent validators use a literal minimum of 240.
The prior nonopaque count remains diagnostic. The M2 decoder now requires the exact lit alpha-key
material (flags 0, blend mode 1), depth writes, and constant full texture-opacity tracks before
using this solid gate. Other material modes cannot silently reuse its acceptance rule. Tests include
253/240 passing, 239/223 failing at every mip, bilinear UV-border pinholes remaining rejected,
and rejection of changed blend modes/opacity. No pixel, UV, geometry or animation changes are
needed for the four candidates; this is an overstrict acceptance-rule correction, not general
cutout/translucent-material support. Existing interior-alpha and 64-bone checks remain intact.

52 regressions pass. An isolated representative conversion is staged under `alpha-key-smoke`
with forms 1, 10, 159, 290, 291 and 489; require its completion, deep validation, actual output
byte/decoded comparisons and visual review before another full recovery. Haunter is an expected
negative case and must remain excluded for unsafe seam alpha.

Pass 7 representative work is complete: ten appearances passed independent deep validation;
Haunter normal/shiny remain rejected. The four candidates also pass 257 samples per edge at every
mip. Dense minimum alpha is 253 for both normal Politoed forms, 243 for normal Manectric, and
241.096 for shiny Manectric, still above the 240 acceptance bound. Evidence is saved in
`alpha-key-dense-audit.json` and `pass7-review/validation-summary.json`.

Compared candidates against prior rejected cache exports: BLP and SKIN bytes are identical;
all decoded positions, triangles, UVs, bounds and every animation frame are identical. Reviewed
ten decoded renders in `pass7-review/contact-sheet.jpg`. 52 regression tests pass. Four new
appearances are demonstrated; they are not installed yet. The next detached recovery preserves
all 2,817 installed appearances and carries no refresh allowlist. The 64-bone cap, unsafe seam
rejection, original paths/DBC mappings, archives and `10::0` grounding remain enforced.

## Grouped recovery: replace tiny full-catalog cycles

The user requested a plan and execution because repeated one-to-four-appearance cycles were too slow.
The execution plan is `.agents/plans/pixelmon-grouped-recovery/pixelmon-grouped-recovery.PLAN.md`.
Work was isolated under `generated/grouped-recovery` while pass 7 remained healthy; its main scripts
were not edited. Pass 7 has converted 2,821 appearances (four more than installed 2,817) and is finishing
validation. Its ready report will feed the combined recovery; install the combined union once, rather
than scheduling another small installation cycle. Preserve its ready checkpoint under before-promotion;
do not call that checkpoint finalized until its appearances have been installed in the union.

The grouped implementation targets the remaining 341 appearances together. Actual failure grouping:
85 source-alpha cases, 46 multipart opacity cases, 157 unresolved identities/source geometry,
24 animation/rig failures, 24 other source features, three newly verified identity mappings, and two
empty-attachment cases. `unresolved-work-groups.json` enumerates every appearance with original names.
`source-asset-index.json` lists all 24,234 source assets. `unmapped-asset-audit.json` records species-folder
and global normalized-name model searches for all 80 originally unmapped identities; no extra models
were found outside those folders. This is evidence, not permission to substitute a different form.

Source-alpha support writes lossless raw BGRA BLP2 and uses an explicit blend material. The independent
reader compares all RGB and alpha pixels at every mip to the source, plus filtered UV-edge equality.
No authored alpha is filled. Solid alpha-key exports retain their 240 threshold and exact material gate.
The 64-bone cap, skinning, animation and all-part geometry checks remain enforced. Raw BLP reference:
https://github.com/Kanma/BLPConverter/blob/master/blp_internal.h (encoding 3, uncompressed BGRA).
Empty attachment arrays are accepted; nonempty attachments remain rejected. Relative multipart scales
now use each source transform before common grounding. Verified aliases add normal female cosplay
Pikachu (40) and normal/shiny Stellar Terapagos (1580); no shiny costume palette is invented.

Visual review rejected the initial permissive treatment of legacy-opacity shells: Spiritomb's face
was occluded. Newly blended multipart appearances carrying that legacy field are held explicitly as
multipart_opacity_requires_source_render_review; no parts are discarded and no opacity is guessed.
These remain engineering work, not recovered coverage. Review evidence is alpha-contact.jpg,
additional-review.jpg, verified-identities.jpg and validation-evidence.json. The final 19-form cohort
has 27 accepted appearances, ten expected opacity failures, and one missing shiny palette. All accepted
binaries match their reviewed renders byte-for-byte except embedded asset names, and pass independent
validation in both internal and original-filename packages. All 56 regression tests pass. No live
client/remote realm validation occurred. Global C++ lint reports pre-existing unrelated issues;
SQL lint could not fetch origin/master; logs are retained and no C++ or SQL was changed here.

Deep-check receipts are keyed by exact M2/SKIN/BLP hashes, source-alpha hash, motion/material policy,
expected texture path, validator/dependency contents and Python/NumPy/Pillow versions. Changed input
or rules force deep revalidation; hashes and provenance are always checked. A repeat 30-appearance
package check reused 30 receipts in 0.18 seconds. This avoids repeated full animation decoding once
those exact exports have passed these rules; the first combined validation still checks everything.

`approved.json` freezes the reviewed promotion hashes. `launch_grouped.py` waits for the current
runner and validator to exit successfully, preserves ready/report/installation checkpoints, backs
up changed scripts, promotes only matching reviewed files, runs regressions again, then starts ONE
run_full_batch.py --recover. It performs no installation and no AI calls. execution.json records the
launcher and child. While either is healthy, do not edit/restart/duplicate them. After combined ready,
review representative new exports, install canonical Creature/Battlemon files with the existing
manage-3d-batch.ps1 install action, verify originals/archives/installed hashes, and finalize that run.
Do not deploy experimental eDBCs. Preserve 10::0 in the three configs. Continue shared-cause work on
opacity, animations, actual GLB assets (Mega Darkrai), other materials, and unresolved identities;
do not stop solely because unsupported forms keep sprites. Existing rollback remains the manager's
remove action, revealing original sprites without restoring retired test layers.

## Grouped recovery installed (2026-09-28)

Installed and verified 2,913 appearances / 8,739 canonical files (1,460 normal, 1,453 shiny).
Added 96 versus the previous installation: 92 grouped recoveries plus four preceding pass-7 results.
All 2,821 previous validated records retain exact cached hashes. Full validation completed 01:04 UTC;
installation verification completed 01:28 UTC. Review/checkpoints/counts/exact 249-case unresolved list
are under generated/pixelmon-batch/grouped-review. Twenty decoded representatives were reviewed from
two angles, including large rigs, multi-part models, cutouts and shiny textures. Every installed hash
and canonical texture reference was checked; no experimental eDBCs were deployed or reactivated.

Original 9,490 files match. All 1,154 active baseline files and four archived pilot eDBCs match the
correct post-crash-fix snapshot full-review/existing-files.json. The older pre-install-existing-files
snapshot predates eight pilot SKIN repairs and must not be used as the current preservation baseline;
those differences match the current pilot receipt and post-fix snapshot. No pilot files were changed.
Both full-run.json and grouped-recovery/execution.json are finalized for this installation, while
recovery remains active. Restart WoW to test the additions; remote cleanup/config requirements and
rollback instructions remain in PIXELMON-BATCH-RESULTS.md. No remote/live testing was performed.

Next source audit: generated/grouped-next/animation-source-audit.json. Aron and Lairon source idle
and walk clips contain repeated constant channels; Skorupi's source walk is also constant, while its
idle animates. Basculin red/blue meshes have only two bones and zero weighted-name matches to their
18-bone animation rigs, so they must not be treated as valid static conversions. Dondozo has one
repeated model bone name; its animation names are unique. Keep these causes separate and preserve
actual authored static motion only with independent source proof, not by globally disabling motion checks.

## Next grouped recovery: source motion and skinning (2026-09-28)

Installed baseline remains 2,913 appearances. The isolated generated/grouped-next cohort recovered
20 appearances (normal and shiny: forms 122,217,479,480,574,693,1139,1223,1236,1512) and preserved
both Bulbasaur controls byte-for-byte except internal names. All 66 regression tests pass. Both
internal and canonical packages passed deep checks; 23 decoded idle/walk/shiny views were reviewed.
Evidence: grouped-next/validation-evidence.json, source-skinning-evidence.json, visual/contact-*.jpg.

The source loader and GPU upload prove Pixelmon keeps four strongest vertex influences. cel.vsh
preserves homogeneous W; displayed positions match normalized retained weights. The old unlimited-
influence comparison falsely rejected six forms. The corrected independent source reference differs
by less than 7e-9 model heights; unlimited-weight differences remain diagnostic. Eight-percent source
error and 64-bone section checks remain enforced. All raw influences still protect bone ancestry.
Aron/Lairon/Skorupi use a separately hash-proven constant-walk policy without freezing animated idle.
Dondozo's duplicate name is accepted only outside weighted ancestor chains; no geometry is removed.
Basculin red/blue rig mismatch remains rejected. Spiritomb opacity, Darkrai GLB and Iron Leaves
normal-map negatives remain rejected (the negative-only run correctly cannot emit an empty package).

Grouped-next/approved.json freezes promotion hashes. Its launch_grouped.py backs up the finalized
baseline and changed scripts, promotes reviewed files, runs regressions, then starts one --recover
run. Read grouped-next/execution.json as well as pixelmon-batch/full-run.json. Do not modify scripts
while these processes are healthy. After ready, verify source-cache preservation, compare new records
with the reviewed cohort (allowing internal asset names), review any additional new cases, then install
and verify canonical files. Finalize BOTH states only after installation. The older grouped-recovery
execution is already finalized. Do not stop work with unresolved appearances solely because sprites remain.

Next audits: aspect-timing-audit.json found large walking bounds in Ekans/Joltik, a flat Stunfisk,
and 40-versus-41-frame Rain Castform walk parts. Do not loosen the global aspect gate or stretch
one part's time. Continue grouped material/opacity (46), GLB, normal/emissive, timing and source-identity
work. Keep all 163 identity/palette cases explicit; do not substitute unrelated forms. The correct
preservation baseline is pixelmon-batch/full-review/existing-files.json (1,154 active + 4 archived
pilot eDBCs), not the pre-crash pilot snapshot. Original sprites remain 9,490 unchanged files.

## Source-motion group installed (2026-09-28T03:30:59.193028+00:00)

2,933/3,162 appearances are installed and verified (8,799 canonical files); 229 remain.
All 20 additions match reviewed cohort bytes except internal names; all 2,913 prior cache assets
are preserved. 9,490 originals, 1,154 active baseline files, four archived pilot eDBCs and 8,300
legacy archives match. The three Nudge 10::0 entries remain intact. Both grouped-next execution
and full-run states are finalized. Evidence: generated/pixelmon-batch/skeleton-review.
Remote cleanup/rollback/test commands are in PIXELMON-BATCH-RESULTS.md. No remote or live testing.

The next bounded audit is generated/grouped-materials. Source AssimpRenderType explicitly enables
backface culling; the earlier Blender preview did not. Corrected culled previews improve some shells,
but Spiritomb remains unclear; do not assume culling resolves every case. The 46-case legacy-opacity
hold may be broader than necessary. Audit all 23 affected forms using unchanged authored source alpha,
all original parts and matching culling. Never apply invented opacity or deploy unreviewed audit results.
The audit converter is separate from production; its removal of the hold is ONLY for visual analysis.
Any production allowance must match explicitly reviewed source/export hashes, keeping failed cases held.

The detached grouped-materials/run_audit.py now converts all 46 held appearances in an isolated
output, deep-validates them, and renders front/back normals plus shiny fronts with source-matching
backface culling. Read generated/grouped-materials/execution.json FIRST on follow-up; while its
recorded Python processes are healthy, end promptly without duplicate workers or script edits.
After ready, inspect visual/contact-*.jpg and individual uncertain models. The provisional audit
converter has an unconditional hold bypass and MUST NOT be promoted or used for installation.
Culled previews of five old exports still showed Spiritomb's face poorly; treat it separately.

If a case visually matches the actual source render/material behavior, production can allow only
explicitly reviewed source/export hashes (normalize internal asset names when comparing). Preserve
all parts and every authored alpha pixel; no guessed legacy opacity. Keep incorrect/unclear cases held.
Review the whole group before implementing one bounded policy and combined recovery; don't launch
full-catalog cycles for one or two appearances. Production code and installed files remain unchanged
by this audit. A review can conclude that some cases are source defects or need per-part materials;
record exact identities and evidence rather than claiming them recovered.

Additional evidence: grouped-materials/glb-source-audit.json. Mega Darkrai's real 2.47 MB GLB has
118 nodes, one skin, a single textured primitive, 348-channel idle/walk clips, embedded normal PNG,
external shiny texture, a double-sided material and a separately declared emissive texture. It is
not missing source data. Supporting this requires explicit GLB animation/material handling, not a
BMD filename alias or discarded channels/maps. Current source-alpha audit does not touch that gate.

## Reviewed source-alpha group queued (2026-09-28)

The complete 46-appearance audit passed independent decoding and authored-alpha checks. Reviewed
all 69 normal-front/back/shiny-front views and 24 cardinal detail views. Accepted 38 appearances;
held normal/shiny Spiritomb (675), Fan Rotom (738), Lampent (918) for obscured details, and Araquanid
(1160) for the face pointing opposite the standard forward axis. Exact review: grouped-materials/
visual-review.json. The source maintainer confirms legacy texture_transparency is unused:
https://pixelmonmod.com/tracker.php?p=2&t=22840. No opacity multipliers were invented or applied.

Production candidate is grouped-materials/tools/pixelmon, copied from the gated production code.
Do NOT promote audit-tools. shell_review.py plus reviewed_alpha_shells.json implement a closed
allowance matching exact original source/animation/texture hashes, transforms, FPS, and normalized
exported M2/SKIN/BLP hashes. Only internal cache names may differ. Changed or unreviewed source,
geometry, skin, texture or policy stays held. Proofs propagate through internal/canonical manifests
and validation receipts; actual source hashes are rechecked, including when reusing receipts.
No geometry, parts, materials, RGB, alpha or animation data were changed by the allowance itself.

71 regression tests pass. Representative candidate cohort: 16 passed (14 new plus two Bulbasaur
controls), eight expected holds. Both filename packages passed deep validation and every accepted
cohort export matches the reviewed audit bytes apart from cache names. All 38 registry entries were
individually rechecked against reviewed files. Line wrapping after conversion has identical AST;
format-only-proof.json records this. Evidence: validation-evidence.json, material-source-evidence.json,
visual/contact-*.jpg, detail-review/contact-*.jpg. The original audit completion is archived as
audit-execution.json; execution.json now tracks the guarded promotion/full recovery launcher.

approved.json freezes candidate hashes. launch_grouped.py backs up installed/report/state files
and modified production scripts, promotes only those hashes, runs regressions, then starts ONE
run_full_batch.py --recover. While execution/full-run recorded processes are healthy, end quietly;
no edits/restarts/duplicate jobs. When ready, expect 38 new / 2,971 total if all approved cases pass.
Verify exact previous asset preservation and use shell_review.approve_export on every new export;
compare against alpha-audit, never install that provisional audit report. Review unexpected additions
separately. Install the production validated union through the canonical manager, verify all original/
base/archive/config/installed hashes, and finalize both states. Counts are expectations, not installed
results: installed baseline remains 2,933 until successful verification. Continue remaining shared-
cause recovery afterward; do not stop at retained sprites. All earlier preservation rules still apply.

## Material group installed and verified (2026-09-28 05:33 UTC)

Installed 2,971/3,162 appearances, adding all 38 reviewed shells; 191 remain. No corrected replacements.
All 2,933 previous exports are unchanged. Verified all 8,913 canonical hashes and texture references,
9,490 originals, 1,154 active baseline files, four archived pilot eDBCs, 8,300 legacy archives,
retired-layer absence and all three grounding configs. Both material execution and full-run states
are finalized. Evidence: generated/pixelmon-batch/material-review/, including exact unresolved.json.
Production install only; isolated alpha-audit was never installed. No remote deployment/live test.
Rollback and one-time remote experimental-layer cleanup remain in PIXELMON-BATCH-RESULTS.md.

Next group: generated/grouped-diagnostics. Diagnose all ten still-failing BMD forms together with
full movement samples, centroid/extent measurements, rig/channel correspondence and separate-part
views for obscured shells. These are source diagnostics, not approved exports or grounds to drop
parts. Also retain actual unsupported material/GLB definitions for the following implementation.
Do not loosen aspect gates or stretch differing loops without source playback evidence.

## Grouped shape and emissive recovery reviewed (2026-09-28 06:26 follow-up)

Reviewed all 86 grouped-diagnostics source views and all ten failing BMD forms. Ekans legitimately
uncoils into a long body, and Stunfisk is naturally flat: their extreme bounds are retained exactly,
not rescaled or globally exempted. The new closed reviewed_geometry.json approves exact original
source files/transforms/FPS and normalized exported M2/SKIN/BLP hashes for these four appearances.

Implemented real multipart emissive overlays for normal/shiny Crocalor (1437) and Glimmora (1504).
All parts, RGB/alpha, texture references and animations are retained. One atlas holds the original
base and emissive maps; separate lit and unlit alpha-blended sections use identical animated geometry,
weights, faces and 64-bone palettes. Independent decoding checks both layers and UV assignment; the
same canonical three-file naming is preserved. No maps are dropped or baked into fake base lighting.
The source's AbstractPokemonRenderer performs the same second full-bright texture draw; bytecode
and reference links are saved in generated/grouped-motion. These four exports are also hash-reviewed.

Candidate: grouped-motion/tools/pixelmon. 74 production-bound regressions pass. Acceptance cohort:
10 passed (eight additions and two unchanged Bulbasaur controls), eight expected failed appearances,
two expected unsupported normal maps. Both internal/canonical deep checks pass. Every addition is
byte-identical to its reviewed audit export except internal cache names. Reviewed 24 idle/walk/shiny/
low-light views plus four Glimmora reverse details. Registry/source rechecks and equality evidence are
in validation-evidence.json; approved.json freezes twelve production-bound files. launch_grouped.py
promotes only those files, rechecks regressions and starts one --recover. Expected union 2,979;
installed baseline remains 2,971 until installation verification. Do not promote either audit-tools tree.

Held timing experiment: current SMDModelLoader uses 25 ticks per second and duration frame_count-1;
Animation.calculateAnimationTime independently wraps each part. Older diagnostic and normal converter
sampling used 30 FPS/full-frame-count loops. A source-faithful 40-versus-39-period Rain Castform trial
runs on a 62.4-second common timeline, but long playback exposes its head piercing the shell as the
supplied source clips drift apart. Do NOT install that trial or stretch clips to hide the source problem.
Its code is retained under experiments; source_loops.py/test_source_loops.py in the lab are excluded
from promotion. All 24 decoded timing/bounds trial views were inspected. Existing successful assets
remain byte-preserved; no blanket timing refresh was done.

Joltik's provided walk has large vertical displacement and an abrupt terminal pose; Basculin red/blue
model rigs have no matching weighted-bone channels in the supplied clips. Spiritomb/Fan Rotom/Lampent
faces remain obscured; Araquanid still needs an evidenced orientation correction. These remain held.
Next engineering should combine actual Mega Darkrai GLB support (with emissive/double-sided material),
normal-map handling and remaining source rig/material/identity problems. Do not classify assets as
missing without the earlier full source audit, and do not silently substitute a different appearance.

On current run readiness, compare every old cache hash, recheck every new geometry_review with
shell_review.approve_export(..., reviewed_geometry.json), and compare with material-audit bytes.
Install production validated union only through manage-3d-batch.ps1 -Action install, then recheck
all canonical/original/base/archive/config evidence and finalize both grouped-motion and full-run states.
Preserve original filenames, base DBC mappings, all receipts and remote-cleanup instructions as before.

## Shape/emissive group installed and verified (2026-09-28 13:19 UTC)

Installed 2,979/3,162 appearances: eight additions, zero replacements, 183 unresolved.
All 2,971 previous cache exports remained unchanged. Verified all 8,937 canonical files/references,
9,490 originals, 1,154 active baseline files, four archived pilot eDBCs, 8,300 retired-file archives,
retired-layer absence and three grounding configs. Both grouped-motion/full-run states are finalized.
Exact unresolved identities and preservation evidence: generated/pixelmon-batch/motion-review/.
No remote deployment or live testing. Rollback and remote cleanup remain in PIXELMON-BATCH-RESULTS.md.

Next isolated implementation: generated/grouped-glb/tools/pixelmon. The actual Mega Darkrai GLB
has 118 nodes, 116 skin joints, 2,563 vertices, idle/walk animations, embedded normal-palette PNG,
external shiny/emissive maps and double-sided material. Animated scale includes genuine non-uniform
changes (roughly 0.11 to 2.57); flat rotation/translation baking would lose them. Test hierarchical
local TRS with inverse-bind helper bones against independent Blender glTF import before any promotion.
Current reader is experimental, not installed or production-approved. Keep all earlier holds intact.

GLB candidate checkpoint: generated/grouped-glb. All 80 candidate regressions passed (the legacy
pilot fixture lookup is explicitly redirected to the existing module fixture; writes remain temporary).
Independent Blender 4.3 glTF import agrees across 94 source poses. Provisional normal/shiny M2s use
235 bones, topological TRS hierarchy, inverse-bind helpers, and a separate STEP translation bone to
preserve mixed per-animation interpolation without smoothing the authored discontinuity. Both decode
with 64-bone sections, double-sided lit/emissive draws, retained maps and authored alpha. Binary poses
were compared against Blender at 188 samples including off-key times: maximum height-relative error
0.00041646 idle / 0.00016784 walk. Full texture mip checks passed. These are isolated review assets,
NOT approved/installed; source facing, visual fidelity, catalog integration and production validation
still remain. run_review.py prepares 28 decoded views in a guarded detached worker; read execution.json.
Do not promote the isolated tools merely because these numerical checks pass. Combine accepted work
with other meaningful fixes before another full-catalog recovery. Installed baseline remains 2,979.

## Grouped identity priority (2026-09-28 13:48 UTC)

User noted diminishing returns; priority is now all 156 unresolved numerical/variant appearances
(78 forms), before another small full-catalog cycle. Reviewed both original unresolved sprite sheets.
Many visibly differ from the provided source's declared forms and geometry; do not treat them as
simple filename aliases. Size variants are candidates for further investigation, not accepted shared
geometry: preserve real proportions and size behavior before claiming recovery.

One detached worker generated/grouped-identities/run_audit.py performs a fresh full asset inventory,
species/global-name geometry search, geometry/metadata/source/original sprite hashes, exact cropped
RGBA source/peer matches and ranked visual comparison sheets for every unresolved form. Ranking is
only a review aid, not identity proof; a source sprite can exist without its matching 3D model.
Read grouped-identities/execution.json first; while healthy, do not duplicate or modify the job.
On ready review identity-audit.json and comparison sheets, verify source definitions before any alias,
and group real missing assets separately from recoverable mappings. No installed files are touched.

Darkrai's 28 views were reviewed and recorded in grouped-glb/visual-review.json; state is reviewed,
held_for_grouped_integration. No obvious torn mesh/missing overlay was seen, but source-facing evidence,
catalog integration and production acceptance remain required. Do not launch a two-appearance full
recovery while this identity group is being investigated. Installed count remains 2,979/3,162.

Grouped identity audit complete: fresh source inventory still contains 24,234 assets and 4,411
geometry/animation files, with no changes from the prior inventory. Reviewed original target sheets
and comparisons 07-12 for the ambiguous identities. Of 156 appearances, four are verified duplicate
identities: normal/shiny Zygarde (03), form 1114, equals Complete Forme 1113; Necrozma (04), form 1241,
equals Ultra 1240. Both normal/shiny cropped RGBA match their supported peers exactly. Isolated
variant_aliases.json entries resolve to identical model/texture/animation/transform definitions for
all four; two changed-identity negative controls reject correctly. Evidence: alias-acceptance.json.
Nothing promoted/installed yet; combine with GLB and other accepted work.

The other groups are 120 appearances with no matching variant model found in the supplied pack,
12 size appearances requiring proportions/scale review, and 20 battle-state appearances requiring
source pose/geometry review (Ogerpon 04-11 and Zacian/Zamazenta 02). Exact identities, full source
paths and SHA-256 evidence: grouped-identities/IDENTITY-RESULTS.md and identity-audit.json. Source
sprite presence does not prove a matching model exists (e.g. some hats and Dada sprites lack their
variant geometry). Do not replace those with ordinary base models. Do not call all 156 recoverable.
Next: inspect actual source growth/render behavior for the 32 uncertain appearances, then combine
valid recoveries with four aliases and GLB production integration. Continue other material/rig holds.
Installed baseline remains 2,979; this audit adds zero installed appearances.

## Combined GLB/identity acceptance running (2026-09-28 14:53 UTC)

Current guarded detached worker: grouped-glb/run_integration.py, PID 18268. Read
integration-execution.json before any code changes. No production files or installed assets changed.
The isolated candidate now combines two verified identity aliases with an explicit GLB resolver,
converter adapter, skeleton/material proof, manifest propagation and validation-cache dependencies.
The worker first requires the empty GLB registry to reject exports, then compares generated vertex
positions/normals/UVs/weights, every sequence and bone track/interpolation, materials, bounds, full
SKIN bytes and BLP bytes against the reviewed candidate. Both palettes matched; it wrote only an
isolated exact source/export reviewed_glb.json registry including species metadata hashes.

Actual shiny metadata points to none/emissive.png, not shiny/emissive.png; both files have identical
SHA-256 CD7976B005D0AD1C819E8A3F5B07D3C56CB93DEE98CAF5F5BC4E482DA1590440, so visuals are unchanged.
Resolver now follows the actual declaration. GLB Assimp import flags 266826 do not introduce a
coordinate flip; evidence is grouped-identities/behavior/AssimpSceneLoader.txt. Source render-scale
and GrowthData disassemblies show scalar growth, not variant-specific proportion deformation.
AbstractPokemonRenderer renders generic tera hats/effects, not evidence of the required alternate
battle-state meshes. The 32 uncertain source-state/size cases remain held; do not substitute base forms.

Worker next runs all regressions, then forms 1,756,1114,1241,840,1553,675 as one acceptance cohort:
expected eight passed appearances (six additions plus two Bulbasaur controls), four failed held
rig/shell appearances and two unsupported Iron Leaves normal-map controls. Then independently
validates internal and canonical packages. It never promotes or installs. On ready review counts,
logs, registry/source proof, decoded new canonical references and old alias/source equivalence,
then assess grouped promotion. Keep full recovery/installation preservation requirements unchanged.

User did not understand the additional-model-folder question. Explained that addon sprite variants
outnumber matching supplied 3D variants (e.g. cap Pikachu). Do not ask again now or require the user
to locate assets while recoverable work remains. Finish available conversions and provide a clear
missing-model list. The request for a newer folder is unanswered; no source asset was provided.


## 2026-09-28 15:52 UTC: reviewed GLB/identity group running

User clarified scope: use what the supplied Pixelmon mod has. If a matching appearance does not
exist there, leave its original 2D sprite in the earlier patch. Do not request another pack or
invent substitutions. Missing source appearances are accepted fallbacks, not a request for new models.

Installed baseline remains 2,979/3,162. Combined acceptance verified six additions (normal/shiny
Mega Darkrai form 756, duplicate Zygarde 1114 and Necrozma 1241), two unchanged Bulbasaur controls,
four expected rig/shell failures and two unsupported normal-map controls. All 80 regressions pass.
Both eight-entry packages passed deep validation; file hashes, canonical references and GLB policy
propagation verified. Each alias export equals its installed peer after cache-name normalization;
both GLB exports match the closed source/export registry and previously reviewed 28 views/oracle.
Evidence and exact 14-file promotion receipt: generated/grouped-glb/approved.json and
validation-evidence.json. Fixed test fixture resolution for both isolated and production locations.

One guarded launcher PID 51876 promoted reviewed files and started recovery PID 5716 at 15:51 UTC.
Check generated/grouped-glb/recovery-execution.json and generated/pixelmon-batch/full-run.json.
Revision 0192e3872383925edf83f8d6762cbf0995f67a71b83700703a70ad799d11baa9.
Run directory: generated/pixelmon-batch/runs/20260928T155145Z. No new installation yet.
Expected union 2,985 only if six additions pass. Do not modify active converter files or duplicate jobs.
On ready preserve every previous cache hash, compare new normalized exports against
combined-acceptance, verify GLB proofs, install canonical names using the manager and adapt the
existing preservation verifier deliberately. Finalize recovery-execution, integration-execution and
full-run only after installation verification. Missing variants keep 2D; remaining actual supplied
models with rendering/rig issues still need a bounded assessment, without another absent-asset audit.


## 2026-09-28 16:49 UTC: GLB/identity installation verified

Installed 2,985/3,162, six additions; 8,955 canonical files verified. Every previous 2,979 export
unchanged. All original/baseline/archive checks passed. Full-run, GLB recovery and integration states
are finalized. Evidence generated/pixelmon-batch/glb-review, exact remaining list PIXELMON-2D-FALLBACKS.md.
Remaining 177: 120 absent matching models, seven missing palettes, 32 unproved size/battle identities,
18 conversion-limited appearances. User accepts absent-source 2D fallback; do not repeat inventory
or request another pack. Actual normal_mapping shader inspected: screen derivatives and second
texture cause view-dependent lighting, so a fixed texture bake/drop is not faithful. Rechecked existing
source shell views: opaque surfaces obscure details; Araquanid also needs orientation review. Existing
rig/timing/motion evidence remains held, not silently corrected. Remaining assessment records exact
limitations and source evidence. Need user preference on retaining those 18 as 2D versus allowing
source repairs/material approximations beyond current fidelity constraints. No further full cycle
should run just to repeat these known failures. Rollback and remote cleanup recorded in results.


## Final user decision

User explicitly chose "Keep these 18 as 2D and finish". Work is complete: 2,985 installed
3D appearances and 177 accepted original 2D fallbacks. Recovery automation remains paused.
Do not resume repairs or re-audit missing identities unless requested. Installation and preservation
verification is in generated/pixelmon-batch/glb-review/installation-summary.json.


## Expanded user scope: ALL supplied Pixelmon, 2026-09-28

User explicitly requests ALL Pokemon in supplied folder converted, no redoing completed exports,
and extras wired with extended DBC. This replaces the completed Battlemon-only scope. Keep 2,985
installed appearances and all original assets intact. New plan .agents/plans/pixelmon-full-source/
pixelmon-full-source.PLAN.md; isolated implementation/evidence generated/source-catalog.

source_index.py enumerates every declared species/form/gender/palette/conditional model/style.
It reuses the production resolver body without editing production, records its hash and all unsupported
features, and verifies old export hashes before reuse. Inventory:3,782 definitions;2,802 exact reused,
785 pending definitions (692 unique content jobs),195 unsupported definitions. Unsupported grouped:
162 single-part emissive,26 attachments,2 normal maps,2 attachments+normal maps,2 missing idle,
1 model_type. MissingNo is the model_type hold, not an absent asset. This is source definition coverage,
not the old Battlemon appearance count. Still audit inherited/unreferenced source assets before claiming ALL.

run_cohort.py PID15668 active at17:12UTC, execution.json checkpoint. Nine new-only examples:
Browt normal/shiny,Pombon normal,Gecqua normal,Gmax Venusaur normal/shiny,Venusaur zombie,
Pidgey pink conditional state,Mareep shorn. Earlier two preflight launches failed on selecting emissive-held
Charizard/Blastoise Gmax; no conversion occurred then. All current identities preflight checked.
Worker converts checkpoints, independently deep-validates, renders idle/walk decoded views. It never
installs, promotes or modifies existing converter. On ready inspect logs, exceptions and all visual views.
If healthy do not duplicate workers or edit scripts. Existing production revision unchanged.

id-registry.json reserves980 not-yet-covered definitions, stable IDs200000-200979, readable stems,
Creature/Battlemon/PixelmonExtras and .dbc9-pixelmon-extras.28 local client/server DBC tables/layers
including real base tables scanned. The first provisional max-ID allocation was discarded BEFORE any
installation because old custom outliers produce huge sparse ranges; compact200000+ allocation is final.
Do not regenerate/renumber registry. Recheck collisions and scanned hashes before eventual installation.

stage_extras.py implemented (syntax checked only), accepting --report and --output; rewrites name/texture
strings, deep-validates canonical models, creates paired additive eDBCs with bounds and fixed registry IDs.
Must exercise on accepted cohort, verify canonical geometry/track equivalence and collision rules before
any deployment. No new eDBCs/assets installed yet. Need reversible extras installer and manifest receipts;
server eDBCs belong env/dist/bin/data/dbc-continuations, remote realm deployment not claimed.

Next: review cohort, test stager, implement durable new-only runner over unique pending identities
(reuse cohort outputs and all previous accepted exports). Add shared support for single-part emissive
and attachments through isolated acceptance, not by dropping maps/parts or autoapproving registry holds.
Model predicates are explicit separate display states; textures/attachments/palettes must remain distinct.
Continue all-source conversion and extra wiring; previous accepted18 fallbacks now included in assessment
under ALL request, but do not silently degrade source fidelity. No server/client builds authorized.


## 2026-09-28 17:30 follow-up: source cohort accepted, new-only bulk launched

Nine new examples passed independent deep validation. All36 decoded normal/shiny idle/walk views
reviewed in source-catalog/cohort-contact.jpg. Fixed normal-only preview helper omission by rendering
8 missing shiny views with isolated render_missing.py; production unchanged. Gmax Venusaur canopy
hides body from elevated view; geometry retained. cohort-review.json freezes reports/manifest/contact.
Exercised stage_extras.py: nine readable canonical exports deep-validated; only name/texture descriptors
and appended strings differ from reviewed M2, SKIN/BLP identical. Paired eDBCs and IDs verified against
all28 scanned layers; no installation. Existing2,985 remain installed untouched.

ONE new source-catalog/run_bulk.py PID28108 launched after acceptance. Current state bulk-execution.json.
It processes692 unique pending content keys (785 identities), reuses nine cohort results, checkpoints
per job, independently deep-validates exports and never installs. It does not re-convert old successes.
While healthy do not change production converter/catalog or duplicate workers. Per-job logs in bulk/logs;
failed conversion results remain explicit; process or validation failures stop for diagnosis.
On ready group exceptions, review representative additional outputs (especially conditional/Gmax/special
palettes), stage full accepted union and implement reversible extras installer with receipts. Need preserve
validation proofs in final extra manifest (current staging entries have policy but omit full proof fields;
extend before installer); recheck canonical hashes/bounds/collisions and all original preservation snapshots.
Continue shared195 unsupported definitions after this job; no feature code edits during active revision.
Audit inherited/unreferenced source coverage before declaring ALL. No new client/server assets installed yet.


## 2026-09-28 19:23 follow-up: bulk complete; full extra staging/review active

New-only run completed692 unique jobs:764 passed identities,21 failed, no new installation.
Failures:6 geometry/source motion (Swellow/Joltik/Braviary normal+shiny),3 Rain Castform timing
(normal/shiny/christmas),8 existing multipart shell holds,4 red/blue Basculin rig mismatches.
The195 unsupported definitions remain a separate shared-feature engineering workload.

stage_extras.py now carries source snapshots, bounds and all non-null material/motion/GLB/geometry/shell
validation proofs. Enforces original-vs-relinked M2 equivalence except name descriptors and appended strings,
and rechecks all28 scanned DBC hashes/ID collisions. Strengthened version passed the9-entry cohort again
into cohort-proof-package. Existing reviewed9-entry package unchanged.

ONE prepare_bulk_review.py PID36036 now runs: check source-catalog/review-execution.json FIRST.
It stages764 accepted exports, deep-validates canonical files, writes paired additive eDBCs and creates
bounded representative decoded front/back/walk views covering alpha species, every predicate type,
largest rigs, new species, Gmax and special palettes. Output extras-package and bulk-visual/contact-*.jpg;
review-selection.json records selection reasons. No install. While healthy do not duplicate or edit scripts.
On ready review every contact sheet/uncertain image, inspect manifest source/proof propagation and all
file hashes, then implement reversible extras installer with receipt/rollback and preservation tests.
Existing2985 client models, original sprites and baseDBCs remain untouched. Recheck installed hashes,
9490 originals,1154 baseline files,4 pilot archives,8300 retired archives and Nudge10::0 before/after deploy.
New server eDBCs must go to env/dist/bin/data/dbc-continuations; realm remote. Continue195 shared support
and21 conversion failures afterward, plus inherited/unreferenced coverage audit. Do not claim all done.

## 2026-09-28 19:54: 764 extras installed; grouped emissive audit active

Reviewed all 12 bulk contact sheets / 144 views / 48 representative models; frozen in
source-catalog/bulk-visual-review.json. deploy_extras.py validates all source snapshots, cache hashes,
proof propagation, exact M2 relinking equivalence, SKIN/BLP equality, paired DBC IDs/paths/bounds,
28 original layer hashes and fresh local DBC collision scan. Temporary-fixture tests passed traversal,
unowned overwrite, changed-file rollback refusal, install, rollback and repeated rollback checks.

764 extras installed and verified: 2,292 model/skin/texture files plus four matching client/server eDBC
files, 2,296 total. Original 2,985 / 8,955 canonical files, 9,490 originals, 1,154 active baseline files,
four archived pilot DBCs, 8,300 legacy archives and three Nudge10::0 configs all preserved before/after.
Receipts: installed-extras.json and extras-installation-verification.json under source-catalog.
Bulk/review checkpoints finalized; whole ALL-source task remains active. Read INSTALLED-EXTRAS.md and
installed-display-lookup.json for exact IDs, remote deployment and rollback. Extras require the two
.dbc9-pixelmon-extras files copied from repository env/dist/bin/data/dbc-continuations to remote realm,
then worldserver/client restart. No remote deployment or live tests performed. Existing wild spawn
catalogue is not automatically expanded by eDBC rows. Future extra additions need deliberate union
staging/receipt-aware installer extension; current installer intentionally refuses existing receipts.

ONE run_emissive_audit.py PID28564 started19:54UTC. FIRST check source-catalog/emissive-execution.json.
It audits all162 single-part emissive definitions with exact-content deduplication and checkpoints.
Adapter isolated in emissive-audit-tools: preserves single mesh path/normalization, adds actual declared
emissive texture, invokes existing paired fullbright draw/atlas encoder. Geometry review gate is bypassed
ONLY for diagnostic output: NEVER promote this audit adapter or install emissive-audit/report.json.
Production unchanged. Audit outputs must get independent layer/texture checks, decoded day/night and
front/back/walk review, exact approved source/export registry, positive/negative regression coverage
before any production integration. All source parts/maps/alpha/transforms retained. While this worker
is healthy end quietly; do not duplicate/restart or edit its adapter/driver.

Remaining before audit:195 unsupported definitions (162 emissive,26 attachments,2 normal maps,
2 attachments+normal maps,2 missing idle,1 actual MissingNo model_type), plus21 known bulk failures
in bulk-failures.json. Continue shared categories and inherited/unreferenced model coverage audit;
no repeated original-catalog conversion, no missing-pack requests or unsupported-as-absent claims.

## 2026-09-28 20:49: emissive audit complete; independent validation/rendering active

All162 emissive definitions processed:142 passed initial diagnostic conversion,20 failed with the SAME
cause: Emissive atlas requires non-wrapping source UVs. These are conversion limitations, not absent
source models. Exact identities in source-catalog/emissive-failures.json. No emissive assets installed.

ONE prepare_emissive_review.py PID12192 started20:48:52UTC. FIRST read
source-catalog/emissive-review-execution.json. Production decoder checks both material flags, paired
positions/weights/faces, UV offset, palettes and animations. Rebuilds atlases from actual base/glow maps,
checks every BLP mip RGB/alpha/edge against that source, verifies fingerprints/file hashes and constant
walk proofs. Renders ALL142 identities with idle front/back/night and mid-walk views (568 views) using
previously reviewed paired-layer shader. Outputs emissive-visual/independent-checks.json,selection.json,
report.json,contact-*.jpg. On ready visually review all sheets and uncertain detail views before exact
source/export registry approval, production acceptance and union installation. This job does NOT approve,
promote or install anything. Audit-only converter still bypasses geometry registry; never promote it.
While recorded Python/Blender process is healthy end promptly and quietly; do not duplicate or edit.
Continue after review with shared wrapping-UV support and other source feature holds; preserve all maps,
alpha, parts and source motion. Existing764extras+2985original appearances remain unchanged.

## 2026-09-28 21:12: all emissive visuals reviewed; guarded candidate acceptance active

Reviewed all48 contact sheets /568 views.134 identities visually accepted. Eight source-facing holds:
GmaxBlastoise normal/shiny/zombie (indices14-16),strikeRalts71,Spectrier normal/shiny119-120,
IronBundle normal/shiny138-139. Front/back views suggest reversed facing; require actual source-axis
proof before correcting or approving, no blind rotations. Exact IDs in emissive-visual-review.json.

Candidate isolated in source-catalog/emissive-candidate/tools/pixelmon, copied from PRODUCTION (not
bypass audit). Changes only: catalog retains actual single-part emissive path and removes false note;
batch uses single appearance for overlay when parts absent; reviewed_geometry registry adds exact134
reviewed source/export hashes. Existing geometry/shell gates remain. No production promotion/install.

ONE run_emissive_acceptance.py PID31928 started21:11UTC. FIRST read emissive-acceptance-execution.json.
All80 regressions passed after restoring missing original pilot fixtures under isolated candidate/generated;
first failed attempt was fixture path only, no production change. Current cohort tests12representative
positives (including Gmax,sourcealpha,normal/shiny/palettes),four negatives(two facing holds,two wrapped
UVs),normalized reviewed-byte equality,closed source/export registry proofs,internal+canonical deep checks,
and2proof-mutation negatives. Results emissive-candidate/acceptance/report.json. Worker never promotes
or installs. While healthy do not duplicate/restart or change scripts. Stage_extras imported only for
relink helper, candidate validation modules loaded first. Confirm candidate dependency paths before reuse.

On ready inspect acceptance evidence/logs, add unchanged-control checks before promotion, and ensure
all134 accepted audit exports can acquire real reviewed proofs/deep validation without regenerating old
installed assets. Promote only minimal reviewed production changes, never audit bypass. Need validated
union report/staging plus receipt-aware extras installer update (currently refuses existing receipt).
Keep current764extra files/DBCs and2985original exports preserved, stableIDregistry unchanged. No newly
accepted emissive assets installed yet. Continue20wrappingUV failures,eightfacing holds,otherfeatures,
and full-source coverage audit; ALL task not complete.

## 2026-09-28 21:30: emissive acceptance passed; guarded union staging active

Candidate acceptance ready:80regressions,12positive reviewed-byte matches with internal+canonical deep
checks,4expected rejections(2facing,2wrapping),2mutated-proof rejections. Revision
c705ec6297bc3fe5699a51160c18226a8e7dcb884dbdddb6e35446c09f5bb4ac.

ONE prepare_emissive_union.py PID35240 started21:30:23UTC. FIRST check emissive-union-execution.json.
Its first preflight exited on legacy texture_policy field absence; repaired selection to use established
solid_alpha_key default before any conversions/promotion. Current healthy worker compares three unchanged
controls (Bulbasaur,Crocalor and first source-alpha entry), independently deep-validates all134 exact
reviewed audit exports with closed registry proof, preserves/copies prior764cache bytes into new union,
verifies every old2985cache export hash, then promotes ONLY batch.py,catalog.py,reviewed_geometry.json
from clean candidate after verifying other files unchanged. Backs original3files in
emissive-candidate/before-promotion and records promotion.json. Never promotes audit bypass.
Then stages898appearance union at emissive-union-package with canonical deep validation; preserves
all2292existingextraasset hashes. This worker does NOT install. While healthy do not edit scripts or
start duplicates. Outputs emissive-union/report.json and package manifest; counts expected898passed,
21previous failures,134additions. Existing764extras remain installed until verified receipt-aware update.

On ready review logs/manifest/closedproofs and all preserved hashes; extend installer with tested
receipt-owned union update and rollback (current deploy_extras.py refuses existingreceipt). Keep original
installed-extras.json/manifest/DBCs backed up, reject unowned overwrite and changedowned files, preserve
stableIDregistry and old assets, update only owned additiveDBC rows plus new files. Verify canonical,
sourceproofs,baselines,archives,Nudge before/after. Then finalize relevant states/report actual898extra
count only after installed verification. Continue20wrappedUV,8facingholds,otherfeatures/fullsourceaudit.

## 2026-09-28 21:57: 134 emissive additions installed; source coverage audit active

INSTALLED VERIFIED:898 extras /2698files (2694assets+4pairedDBCs),134 additions. Previous764extras'
2292asset bytes unchanged; original2985/8955canonical files,9490sprites,1154activebaselinefiles,
4pilotarchives,8300legacyarchives,Nudge10::0 all preserved. Verification timestamp21:54:45UTC;
evidence emissive-installation-verification.json. Union/acceptance/review states finalized.

update_extras.py check/install/verify/rollback validates exact closed proofs,canonical/source/reference
hashes,IDs,bounds and preservation. Reuses strict deploy_extras.validate with optional package/report/review
arguments. Owned union updates only fourDBCs,adds402assetfiles; immutable previousreceipt/DBCbackup and
journal in extras-updates/emissive-134. Fixtures passed unowned-overwrite,changedpriorfile,atomicupdate,
changedfile rollback refusal,repeatedrollback and interruptedupdate recovery. Atomic hard-link publication
for new files prevents overwrite races; owned DBC replace verifies priorhash. Existingreceipt now points
union package/report/review. Old default deploy_extras verify still targets firstpackage; use update_extras
verify for currentunion. Full remove remains deploy_extras remove; lastupdate rollback update_extras rollback.
Lookup/docs refreshed. Remote needs BOTH updated.dbc9-pixelmon-extras files copied from repo distribution
and realm/client restart. No remote deployment/live testing claimed.

ONE audit_source_coverage.py PID38620 started21:56:39UTC. FIRST read source-catalog/coverage-execution.json.
Reuses existing complete grouped-recovery/source-asset-index.json rather than rebuilding inventory. Audits
all species metadata resource references/inheritance gaps,decodes only UNREFERENCED BMDs to distinguish
meshes from animation-only files. Outputs source-coverage-audit/assets.json,inheritance-gaps.json,summary.json.
While healthy end quietly,do not duplicate/edit. On ready review actual unreferenced meshes/otherformats
and inheritance semantics; don't treat animationclips as Pokémon or invent identity/texture mappings.

Next remaining groups:20wrappedUV,8facingholds,33otherunsupported plus21initialbulkfailures=82 declared
definitions, before coverageaudit findings. wrapping-uv-diagnostics.json measures all20 cached UVranges:
real out-of-range authored UVs (-.102213 to1.002591),not mere floating error. No clamp/modulo shortcut.
Need source sampler evidence then faithful wrapping atlas/material support. javap available at
C:/data/_tools/PortableApps/CommonFiles/OpenJDK64/bin/javap.exe; Pixelmon OBJTextureLoader is old path,
actual current SMD/Assimp renderer evidence in grouped-motion/abstract-renderer-bytecode.txt. Source pack
has only MissingNo Pokémon texture.mcmeta; do not assume absent mapping assets. Otherfeatures include
attachments,normalmaps,MissingNo,motion/rig holds. Production revision remainsc705ec6297bc3fe5699a51160c18226a8e7dcb884dbdddb6e35446c09f5bb4ac.


## 2026-09-28 22:24: Coverage corrected; 20 wrapped-UV diagnostics running

Coverage audit is complete, not active. Fixed resource resolution using catalog.resource_path (textures/models
prefix), reusing all prior classifications without rerunning the inventory or conversions. Actual results:
4171 metadata-referenced assets,19 unreferenced BMD meshes,22 animation-only files,7 Servine OBJ parts,
one Greninja battle_bond inheritance gap. Zero unresolved metadata resource paths. Review hashes/loader
semantics before treating orphan/legacy/duplicate meshes as extra identities. Existing audit files corrected.

ONE run_wrapping_audit.py PID24216 started22:23:58UTC; checkpoint wrapping-execution.json. While healthy
end quietly, no duplicate/restart/active-script edits. Isolated wrapping-audit-tools copies the diagnostic
adapter with its intentional registry bypass: NEVER promote or install this adapter/report. It reuses all20
existing cached geometry files by hash and only tests a repeated texture atlas. No installed assets changed.

Official Mojang1.21.1 client and mappings downloaded with verified officialSHA1 to sampler-evidence.
SimpleTexture gqe defaults blur/clamp false; metadata serializer gsj defaults clamp false; NativeImage faj
sets CLAMP_TO_EDGE only for clamp true. Pixelmon AssimpRenderType gets the normal TextureManager texture
and binds it to Sampler0. Bytecode evidence saved; no .mcmeta accepted by candidate. Fresh GL texture default
REPEAT supports periodic source samples. Candidate makes exact pixel repeats with integer origin and affine
UV transform; no texture resizing or per-vertex modulo/clamp. Equal power-of-two source dimensions required;
4096 atlas cap. Fixtures:3000 triangle interior samples agree with source bilinear sampling, three invalid
input/metadata negatives reject, modulo counterexample detected. Per-export .sampling.json tests20000random
UV samples plus every vertex for both base/glow RGBA. All original parts/weights/geometry retained.

On ready inspect20results, independently validate serialized M2UVs and ALL mip-level/source sampling,
paired materials/weights/faces,64bone sections,seams and decoded front/back/day/night/walk views. Audit
base-level sampling proof alone is NOT production approval: mip/filter behavior and source facing still
need review. Only then integrate into clean production candidate with closed source/export policy proofs,
positive/negative regressions, canonical acceptance and strict receipt-owned union update. Do not redo old
exports. Installed count remains898extras+2985originals. Other62 declared holds and source coverage followup
remain. Prior preservation and remote deployment instructions unchanged.


## 2026-09-28 22:45: Wrapped-UV diagnostic union review launched

Initial20audit finished:11 passed,9 rejected only the diagnostic power-of-two source-size restriction.
Preserved all11 exports. New isolated wrapping-npot-audit-tools removes only that restriction; repeated
texel addressing already supports arbitrary source dimensions. Equal base/glow dimensions, finite/bounded
UVs, no explicit sampler metadata and4096atlas cap remain. Fixture90x75RGBA source samples passed; an
existing Butterfree decoded export independently matched all source positions/triangle indices/float32UVs
and reconstructed atlas bytes. Evidence wrapping-npot-fixture-results.json. No production edits/install.

ONE run_wrapping_review_pipeline.py PID30424 launched after22:40UTC; FIRST read
source-catalog/wrapping-pipeline-execution.json. It runs nine-only recovery with reused geometry, then
merges untouched11 and newresults into wrapping-union/report.json, preserving per-record original audit
revision/cache location. Then prepare_wrapping_review.py independently reconstructs repeated atlas from
actual source RGBA, checks serialized mesh positions/triangles/UV affine transform and quantization,
checks both layers/64bone palettes/constant-walk proofs and every BLP mip via production decoder and
alpha verifier. Renders front/back/night/walk for every passed appearance to wrapping-visual, contact sheets.
Candidate reports remain AUDIT ONLY. All audit-tools include unconditional review bypass and MUST NEVER
be promoted/installed. Existing production/898extras+2985originals unchanged.

While healthy recorded pipeline/child/Blender workers run,end quietly and promptly; no duplicate/restart
or active-script edits. On ready read all sheets and uncertain individual views,inspect per-mip checks
and texture-filter implications (base source-repeat proof alone does not prove every mip matches source
rendering). Decide explicit bounded policy/proofs and clean production candidate/regressions/canonical
acceptance before any union install. Retain source maps/geometry/transforms. Other62 declared cases plus
completed coverage findings still require work; no old installed reconversion. Preserve all prior rollback,
original hashes,stableIDs and remote deployment requirements.


## User-requested compressed texture test kit

Separate from production conversion, user authorized DXT5 compressed COPIES of every raw BLP currently
under client patch-z.mpq/Creature/Battlemon, including PixelmonExtras, with reversible .bat workflows.
Client/Battlemon-Texture-Tools/texture_batch.py generates303copies under Creature/Battlemon-Compressed
and original raw backups under client/Battlemon-Raw-Backup. Original active files are NOT automatically
replaced. manifest.json holds original/compressed hashes, sizes, every-mip compression metrics. Batch
files generate/backup/install/restore/verify; install and restore require unchanged known hashes and
retain backups. No models/DBCs changed. Compression is lossy; no in-game quality claim. Fixture tested
DXT5RGB/alpha,smallmips,install/restore,tampered-active rejection.

If the user later runs Install Compressed, production receipts still describe raw textures. Check this
kit's last-action.json and hashes when diagnosing preservation differences; do not label intentional
verified test copies corrupt or silently overwrite their test. Restore Raw returns production baseline.
The full-source conversion goal remains independent and unfinished.


## User-required compressed delivery for all NEW textures

User requires future additions avoid raw BLP viewer incompatibility. Added tools/pixelmon/blp_compression.py:
DXT5 encodes original mip levels, decodes every mip via DDS and BLP, records errors, preserves all fully
transparent/opaque endpoints. Base RGB MAE<=8 and alpha MAE<=5 required; failures need explicit review.
Retains exact raw backup and runtime/compressor/source/compressed hashes. verify independently reproduces
compressed bytes and quality. Raw audit/source validation remains unchanged; do not replace its proof with
lossy comparisons. New stage_extras entries compress AFTER raw canonical deep validation, save raw backups
under package/raw-texture-backups and texture_compression proof on entry. Existing receipt entries retain
exact old texture bytes; prior compressed entries regenerate the same compression proof when restaged.
deploy_extras validates proof, source/raw backup and reproducible delivery. Initial install and update_extras
new-file paths reject raw BLP. direct_deploy also rejects new/changed raw deliveries (unchanged receipt-owned
raw files allowed); direct build needs explicit final compression/proof integration if future original-name
additions use raw audit files. Do NOT bypass this gate or claim those raw additions installed.

Real Ivysaur Halloween isolated stage test passed: original source/geometry/alpha validation retained,
compressed DXT5 staged, allmips decode, exact raw backup, reproducible proof. Raw delivery/tampered proof
negatives reject. Evidence generated/source-catalog/compression-policy-test. No installed assets changed.
Production source code has changed, no active conversion workers; do not assume earlier c705 revision still
applies. Preserve existing cache bytes and closed raw source/export approval registries. New final compressed
textures require visual review too, separate from source-lossless audits.

User noted large compressed Talonflame ashen and Volcarona alter flying: 4096x2048/10.67MiB and
2048x1024/2.67MiB. Source pairs1024x512 and512x512 were over-expanded by padded square atlas layout.
Asked optional test-copy resolution cap1024 or2048; no downscale yet at this checkpoint. Existing 303-copy
test kit remains separate, originals and production receipts unchanged.


## User selected Ivysaur-sized textures:512pixel maximum

User explicitly requested compressed copies the size of0002_Ivysaur.blp(512x512,350724bytes). All303test
copies regenerated from original RAW mip levels with maximum dimension512,proportions retained. Total
81804092bytes;largest350724. Talonflame andVolcarona examples now512x256/175972bytes each. Raw backups
and every active original hash unchanged. Test kitmanifest/README/bats updated;before512manifest retained.
blp_compression.py finaldelivery now also caps512and records max_dimension proof. Existing raw/source
validation unchanged. Positive realVenusaur prepare/reproduce passed. Talonflame512fails conservative
production quality gate (seecompression-policy-test/size-512/validation.json); DO NOT loosen automatically
or installheld productionmodels just because user allowed lossy testcopies. User cantry303copies through
client/Battlemon-Texture-Tools/03-Install-Compressed.bat andrestore04-Restore-Raw.bat. Production approval
still requires finalcompressed visual/qualityreview. No useranswerpending now:512capexplicitlyselected.


## CORRECTION: User requires512per layer, NOT512across paired atlases

User rejected half-resolution paired textures. Rebuilt all140wide testcopies from untouched RAWbackups
at1024x512, not upscaled degradedcopies.163square512x512copies remain byte-identical. All active originals
and backups verifiedunchanged. Example shiny flyingCharizard now1024x512; manifest/installhashes updated.
Future blp_compression.delivery_mips uses1024x512boundingbox forwideatlases and512x512forsquare, retaining
aspectratio. Single512overallcap superseded. Per-layer dimensions and compressed visualquality remain
requiredchecks; don't optimize purely byfilebytes. Newcompressionruntimehash proofs must be regenerated
forfuturestaging, without redoing oldsourceexports. Testkit summary/README updated.


## Compression encoder corrected after actual Charmander mesh review

User's0004_Charmander_base_ALL_none_always_0_default edge report was REAL: oldPillowDXT5 exported bright
speckles onhead/back. Equal-resolution raw mip renderedclean, proving compression rather than resolution
caused it. DXT3trial wasworse/rejected. Independent ispc_texcomp1.0.1 BC3/DXT5 removed bright speckles
in decodedfront/back comparison atsame1024x512. Evidence source-catalog/charmander-edge-review,including
rawfull/rawsameLOD/oldcompressed/newISPC renders and metrics. ActualWoW rendering notclaimed.
All303testcopies REBUILT fromRAWbackups withISPC, preserving163square512x512+140paired1024x512.
CurrentCharmanderfile hash exactlymatches cleanreview. Total155204412bytes unchanged;allmipsdecoded,
allactiveoriginal/backups unchanged;maximum basealphaMAE across303now0.606. Testkitmanifest/bats updated.
Previousmanifest-before-ispc.json retained. Dependencies isolated atclient/Battlemon-Texture-Tools/dependencies
and repo generated/source-catalog/compression-dependencies. MITispc_texcomp1.0.1 wheel. Future
blp_compression.py also usesISPC, withbinary/compressor/runtime/hashqualityproofs; realCharmander
prepare/reproduce passes. DON'T returntoPillowBC3encoder oroverall512atlascap. Existingraw/sourceproofs
remain unchanged. Finalcompressed views stillrequired fornewmodels; do not treat filedecode alone as
proof of visualquality (this incident demonstrateswhy).

## Wrapping delivery reviewed; clean acceptance running (2026-09-29 00:20 UTC)

All 20 wrapped-UV identities passed final ISPC compression prepare/reproduce checks. All seven sheets /
80 final compressed front/back/night/walk views were reviewed and accepted; no visible tears, missing
parts, facing errors or bright compression speckles. Frozen evidence: wrapping-visual-review.json and
wrapping-delivery-review/checks.json. Raw audit exports remain isolated; not installed or promoted.

ONE run_wrapping_acceptance.py PID26616 is now running, checkpoint wrapping-acceptance-execution.json.
80 regressions passed; four representative wrapping conversions/internal+canonical checks, three unchanged
controls and all twenty exact registry/deep approvals follow. Closed source/export mutation and empty
registry negatives are included. Stop quietly while healthy; do not edit candidate/worker or duplicate.
Initial regression setup failures were isolated missing dependency/fixture paths and old delivery fixture;
fixed with subprocess PYTHONPATH to compression-dependencies, copied preserved pilot fixture, and synthetic
DXT5 fixture in candidate test_direct_deploy.py. No production gate was weakened. Initial logs retained.

Clean candidate: wrapping-candidate/tools/pixelmon copied from current production, only conditional
out-of-range branch in emissive.py, bounded repeated_atlas.py, revision/dependency hashes in batch.py and
validation_cache.py, and twenty exact reviewed_geometry registry entries. Nonwrapping path unchanged.
Candidate test_direct_deploy fixture differs deliberately; handle this explicitly during promotion diff.
All audit adapters still bypass review and MUST NOT be promoted. Worker does not promote or install.

On ready inspect acceptance evidence, promote only reviewed runtime files with backups after positives,
negatives and unchanged controls pass. Build 918 union from existing emissive-union 898 plus twenty
wrapping-union rows, using each row's audit_output/cache/assets (no unified wrapping cache). Attach genuine
geometry_review proof, remove AUDIT_ONLY labels only after approval, preserve all old asset hashes.
Stage with updated stage_extras.py, retaining final compression/runtime/source proofs and raw backups.
New canonical compressed BLP hashes must equal reviewed delivery hashes; all 2694 old extra assets unchanged.
Adapt strict update_extras transaction/paths deliberately, preserve old receipt and paired eDBCs, verify
originals/archives/Nudge and canonical hashes after installation. Expected 918 extras/62 declared holds
ONLY after verified install. Current actual install remains898 extras +2985 original replacements.
Continue remaining feature/coverage work afterward. No remote deployment or live test was performed.

## USER OVERRIDE: Extras disabled entirely and preserved (2026-09-29)

User explicitly selected: Disable extras entirely for now; preserve them for later, because module/addon
sprite catalog integration is absent. This supersedes all automatic extras install/union instructions.
898 extras /2698 files archived with exact hashes at client/Battlemon-Deferred/Installed-Extras, including
prior installed receipt and all four client/repository-server eDBC files. Receipt-owned removal completed;
all target files absent, all archives verified, full original preservation check unchanged. Active original
2985 replacements remain. Extras receipt status is removed; extras-disabled.json records evidence.
170 compressed extra test copies moved outside patch to client/Battlemon-Deferred/Compressed/PixelmonExtras.
Texture batch manifest now133 original-model textures; generation/install/restore excludes PixelmonExtras.
Raw backups unchanged; old303 manifest preserved in manifest-before-extras-excluded.json. Verify passed.
Follow-up automation PAUSED; do not reactivate or reinstall extras without new user authorization.
If extra eDBCs were copied to remote realm, user must remove both .dbc9-pixelmon-extras files there and restart.
No remote action/live test performed. Restart client to unload any cached extra rows.

Last wrapping acceptance was NOT complete:80 regressions passed, first positive failed nonwrapping guard
(ValueError: Emissive atlas requires non-wrapping source UVs). No worker remains, no promotion/install.
Likely candidate/production import contamination via stage_extras import path should be investigated on
future authorized resumption. Preserve all acceptance logs, reviewed20 exports and compressed80views.

## RESUMED: Finish conversion, keep extras disabled (user request)

User said "I want you to finish this" after the exact remaining82 explanation. Resume conversion,
validation and staged deliverables; their explicit extras-disabled decision remains in force.
Do NOT reinstall extras, their eDBC layers, or restore compressed extras to active patch paths.
Completed extras belong in deferred/repository packages until later user authorization to enable.

Confirmed acceptance error was import contamination: stage_extras prepended production tools, so lazy
emissive import selected old production code. run_wrapping_acceptance.py now restores candidate precedence
and asserts emissive/repeated_atlas module origins. Failure logs/script preserved. One worker PID51036
restarted for acceptance; read wrapping-acceptance-execution.json. No installed assets changed.
After passing, finalize this20 converted set into a validated DEFERRED union, keeping prior898 bytes.
Continue remaining62 declared cases by shared cause (attachments, normal maps, missing idle/model type,
facing, motion/rig/loops/materials), plus unresolved coverage cases. Do not stop after wrapping.
Use durable guarded jobs for expensive conversion; preserve checkpoints and exact source fidelity.
Automatic follow-up resumed for finishing conversion/staging, explicitly forbidden from live install.

## Wrapping acceptance complete; deferred union worker (2026-09-29 01:28 UTC)

Corrected candidate acceptance completed at01:11UTC:80 regressions,4 representative internal/canonical
positives,3 unchanged controls,3 closed-registry negatives and all20 deep approvals passed. Revision
59f79fee07976e2028affe15b27eab646758904516c3588ee734d49e1e9e9915. Evidence wrapping-candidate/acceptance/report.json.
Runtime diff reviewed: wrapping branch only, bounded repeated_atlas helper, dependency/version hashes,
exact20 source/export registry. Test fixture differs only in candidate and is not promoted.

ONE prepare_wrapping_deferred.py PID48808 launched01:27:42UTC. Check wrapping-deferred-execution.json FIRST.
Worker verifies disabled archive/receipt, reuses898 old raw cache sets plus20 exact reviewed audit sets,
attaches genuine proofs, promotes five reviewed runtime files with backups, deep-stages918 into
wrapping-deferred-package. No active install paths written. All2694old extras asset hashes must stay
identical; new compressed hashes must match wrapping-delivery-review/checks.json. Receipt/archive and
active extras absence checked before/after. Candidate/source old outputs not redone. While healthy end
promptly, no duplicate/restart/edit. On failure bounded logs and fix concrete cause. On ready verify
manifest/package/pairedDBC/proofs and original baseline preservation, finalize deferred state and continue
remaining62/coverage work. All new extras remain disabled per user. Do not run update/install commands.

## Deferred918 finalized; accessory source reference running (2026-09-29 01:54 UTC)

wrapping-deferred-verification.json confirms918appearances/2758packagefiles. deploy_extras.validate checked
canonical references/geometry relinks/source+material+compression proofs, paired eDBC IDs/paths/bounds and
fresh collision scan. Original preservation8955canonical,9490sprites,1154baseline,4archivedpilotDBCs,
8300archives,3groundingconfigs passed. All2698archived extra files verified, active extras absent, removed
receipt unchanged. wrapping-deferred-execution is finalized, installed=false. Keep extras disabled.

attachments source-audit COMPLETED all28attachment definitions (26attachments plus2IronLeaves normal-map
cases),50uniqueBMDmodel/clipassets. Every Hat node exists, though none is vertex-weighted. SMDModelLoader
buildMesh includes ALL nodes in bones, so Scene.createBoneWorldTransform uses animated Hat world matrix;
do not mistake unweighted for absent. Source bytecode in attachments: entity-renderer,Scene,SMDModelLoader,
Animation,AbstractClientEntity. Recursive parent draw applies model T*RY*RZ*RX*S(-sx,-sy,sz); accessory then
parent bone world transform, attachmentScale/abs(parent ModelData scale), and child ModelData transform.
Actual AbstractClientEntity.attachmentScale is max(.01,form.dimensions.height), NOT default1 (tera multiplies1.5).
Animation.calculateAnimationTime uses entityticks*25/20 modulo(frame_count-1); child/parent periods differ.

ONE prepare_attachment_reference.py PID35280 started01:53:46UTC (attachments-reference-execution.json).
Diagnostic source-pose reference, no conversion/install/promotion: all28normal/elf/Christmas definitions,
idle0tick/walk8tick/walk160tick=84views. All samples land exactly on source keys; no guessed interpolation,
no clip stretch. Retains every part/source RGBA and four-weight reference. Derives actual height correction,
parent Hat motion and child pose independently. Blender renders at384px12samples into attachments/reference;
contact sheets follow. IronLeaves NORMALMAP IS NOT RENDERED in diagnostic images (explicitly labeled);
do not count it converted or discard map. While worker healthy end promptly, no duplicate/restart/edit.
On ready review source-transform images/assumptions, inspect uncertain views and source bytecode before
engineering isolated attachment composition with independent source/output oracle and closed acceptance.
These are diagnostic, not approved conversion assets. Need verify orientation/default child transform,
loop boundaries/source-clock behavior and frame interpolation before export. Continue shared groups.
Remaining declared62 plus coveragecases; do not stop after source audit or claim allsource completion.

## Actual accessory exporter implemented; independent review running (2026-09-29 02:20 UTC)

User rejected another missing-file list and explicitly requested finishing actual conversion. Remain on
unfinished source work; do not re-audit original filename gaps. Extras still disabled. All84attachment
source-reference views (7sheets) actually reviewed. Most hats follow heads; Mew/Pawmi/SlitherWing source
orientations need careful source/decoded comparison, not invented rotation fixes. IronLeaves map still held.

New isolated attachment_export.py implements combined skinned body+accessory exports, all source parts,
animated Hat bone world transform, authored ModelData transforms and dimensions.height correction.
Uses least-common-multiple of independent(frame_count-1) periods at25fps, no clip stretching/freezing.
Normalizes combined posed height, deduplicates exact vertices/weights/UVs, retains4source influences,
uses64bone partitioner and source-alpha atlas. No production changes or bypass, no extras installation.
Dratini and Pikachu Christmas representative exports finished in attachments/candidate/assets; exporter
state attachment-candidate-execution.json ready. Two-candidate testing is adapter acceptance, NOT another
full-catalog conversion or claim these are approved. Need apply proven support across26accessory-only
cases after complete acceptance. IronLeaves normal maps require separate support (do not drop maps).

ONE review_attachment_candidate.py PID46832 active, childBlender44004 rendering12decoded front/back
idle/walk/late views. Check attachment-candidate-review-execution.json FIRST. Independent full read_model
passed both candidates (all sequence keys, bounds, bones, SKIN/materials), all alpha mip checks passed.
Separate pre-existing source pose meshes compared face-by-face at entityticks0,8,160 against decoded
exports with height-relative error<=.01. Metrics in attachments/candidate-review/checks.json.
Output contact.jpg after renderer. This is NOT final approval: fractional/inter-key source agreement,
loop boundaries, compression/finalviews, closed source/export registry and production integration remain.
Exporter currently sets placeholder skinning_error=0; must replace with measured errors before approval.
source_snapshot must cover attachment metadata/model/clips/textures/transforms, not only body; validation
cache dependencies must include adapter/oracle/runtime. Do not promote temporary candidate_only reports.
Large LCM tracks need memory-aware bounded validation; reuse completed source/export bytes.
While recorded worker/Blender healthy endquietly, no duplicate/restart/active scriptedit. Onready review
contact then implement fractional/loop-boundary oracle and negatives, extend shared support in one grouped
run once accepted. Continue other62 holds and coverage (918deferredremain finalbaseline until additions
fullyvalidated). Preserve disabledarchives/receipts and originalactiveassets. Follow-up ACTIVE.

## Active raw corruption fixed:133original textures APPLIED (user Nincada report)

User showed Nincada corrupt inWoW/blackviewer. Active0290_Nincada.blp was still rawBGRA1399272bytes;
corrected compressed350724byte512x512DXT5copy had never been installed (last-action absent). Root explicitly
applied all133original-model testkit replacements via texture_batch.py install then verify. Both normal
and shinyNincada nowDXT5,512x512,350724bytes (~343KiB). Independently decoded normalNincada and visually
inspected sourcepaint; no liveWoWtest claimed. User must fullyrestartclient to reload cached textures.
ALL133activehashes andrawbackuphashes verified; zero rawBLPs remain at activeBattlemonroot. Extras folder
andDBC layer remainabsent. Evidence active-compression-overrides.json andclienttestkitlast-action.json.

CRITICAL PRESERVATION UPDATE: Original installed-direct receipt intentionally stillrecords RAWbaseline.
These133knownhash substitutions are nowAUTHORIZED ACTIVE, notcorruption. Future original preservation
checks must accept exact raw->compressed mappings from active-compression-overrides.json after verifying
manifest andrawbackups; allother8955baselinefiles exactoldhash. DoNOTsilentlyrestoreRAW oroverwritefixes,
and don't modifyreceipt to loseoriginal evidence. Original2Dsprites/baseDBCs/models/SKINunchanged. Existing
preservation helper mod.installed(old) needs deliberate overlay-aware adaptation before nextfullcheck.
Rawrollback remainsclient/Battlemon-Texture-Tools/04-Restore-Raw.bat butshouldnotbeautomaticallyrun.
Accessoryconversioncontinuesseparately; noextrasactivationauthorized.

## Fractional accessory validation in progress (2026-09-29 02:58 UTC)

Reviewed all12 decoded Dratini/Pikachu front/back idle/walk/late views in candidate-review/contact.jpg.
Hats/geometry/textures appear intact in those sampled poses; this is NOT final compressed approval.
Authoritative NodeAnimation.txt now records source local translation lerp and quaternion slerp.
ONE check_attachment_fractional.py PID24008 runs independently against serialized M2 tracks, source
local hierarchical interpolation and independent parent/child frame_count-1 periods. Samples quarter
frames plus immediately before/after independent and combined loop boundaries; tests both normalized
linear and spherical output quaternion interpolation. It retains the terminal source frame, unlike the
candidate's wrapped integer table: any boundary discrepancy must be diagnosed, not silently tolerated.
Results attachments/candidate-review/fractional-checks.json; state attachment-fractional-execution.json.
While healthy do not duplicate/edit/restart. On ready inspect measured errors and repair the candidate
before production approval. Candidate placeholder skinning_error=0 still must become real measured proof.
Next: negatives, complete child/source/metadata proof snapshots, compressed delivery visual review,
closed registry, shared26 accessory acceptance. No conversion count increase yet.918deferred/62unfinished.
No live extras or eDBCs.133active compressed original overrides remain authorized and must be honored.

## Accessory fractional failure diagnosed and isolated correction running (03:16 UTC)

First fractional oracle completed0/2accepted: Dratini walk error~0.02082height, concentrated at child
loop boundary. Integer-only candidate dropped terminal source keys and interpolated directly to restart;
local hierarchical quaternion motion also needs more samples. Rejected files/metrics/exporter preserved
in attachments/candidate-before-fractional-fix. No production/installed changes.
Corrected isolated exporter uses local quaternion slerp at quarterframes and retains source terminal plus
restart as duplicate-timestamp keys at each independent loop boundary. This is a CANDIDATE, not approved:
verify actual WoW interpolation semantics for duplicate timestamps before production acceptance; if
unsupported use an evidenced alternative rather than smoothing away source discontinuities.
ONE run_attachment_candidate.py PID49252 started03:16UTC; ONE dependent waiter PID27784
run_attachment_fractional_retry.py runs the independent oracle when exports complete. While either
healthy do not duplicate/edit/restart. Oracle now samples eighth-frame midpoints (between new keys),
plus near loop boundaries, to avoid validating only emitted samples. Check attachment-candidate-execution
and attachment-fractional-execution plus bounded retry logs if failed. Preserve terminal frame semantics.
All later steps still pending: measured skinning proof (placeholder0 NOT approval), complete source
snapshots, negatives, full decoder including duplicate times/bounds, actual client interpolation evidence,
final ISPC compressed mesh visuals, closedregistry and26group acceptance. Baseline918deferred remains.
Extras disabled and133active original compression overrides remain intact.

## Corrected fractional acceptance passed; final delivery review running (03:35 UTC)

Both corrected candidates pass independent eighth-frame/loop-boundary source comparisons. Worst height
relative errors: Dratini idle.0001951/walk.0003442; Pikachu idle.0005593/walk.0005082. All1028sampled
poses compare both output slerp/nlerp. This does not yet prove actual WoW duplicate-key behavior.
ONE review_attachment_final.py PID11776 now runs full read_model on corrected exports (all keys,
bounds/materials/64bones), rawalpha allmips, ISPC compressed delivery1024x512 with backup/reproduction,
three compressionproof mutation negatives and12finalcompressed decoded views. State
attachment-final-review-execution.json; output attachments/final-review. No live writes or promotion.
It records full source-audit row hash and every absolute source/metadata/clip/texture file found in row,
measured skinning_error with exact exported file hashes, dependencies/runtime. Future exporter placeholder
zero replaced byNone (not approved until independent proof); no asset regeneration required for this
non-serialized metadata change. Verify snapshot includes resolved parent texture path before approval.
While worker healthy endquietly/no duplicate/restart/edit. On ready review compressed contact and all
proofs/negatives. Still require actual client duplicate-timestamp semantics evidence or an evidenced
alternative, source/registry integration and grouped26. No countincrease:918deferred/62unfinished.
All extras disabled,133active original texture overrides preserved.

## Distinct-millisecond boundary acceptance (2026-09-29 03:54 UTC)

All12 finalcompressed Dratini/Pikachu views visually reviewed intact. Full decoder/rawalpha/ISPC
reproduction/three mutation negatives passed each. Duplicate-key version archived in
attachments/duplicate-key-candidate with assets/scripts/finalreview. Not promoted.
To remove dependence on unproved duplicate timestamp behavior, isolated exporter now emits strictly
increasing uint32 millisecond times:10ms interior spacing plus source sample at boundary-1ms and exact
restart atboundary, original integer40ms frame periods unchanged. No clip stretching/freezing. This
represents source at timestamp resolution; submillisecond discontinuity behavior is NOT claimed exact.
Oracle now asserts strictlyincreasing timestamps, samples offkeys and EVERYinteger millisecond from
boundary-40ms through+10ms at parent/child/repeated/combined boundaries, unchanged.01height threshold.
Source snapshots now explicitly add resolved parenttexture resource. Fullvalidation reruns sequentially.
ONE run_attachment_distinct_acceptance.py PID10872 starts corrected candidate export, fractionaloracle,
then fullfinalreview/compression/render. State attachment-distinct-execution.json recordschildpid/phase.
While healthy endquietly/no duplicates/edits/restarts. Onready review newfinalcontact/proofs then establish
closedregistry/sourcecache/integration andgrouped26; no more fullcatalogcycles for these2acceptancecases.
Current918deferred/62unfinished unchanged. All extrasdisabled;133activeoriginalcompressed mappingsintact.

## Full26 accessory candidate cohort launched (2026-09-29 04:12 UTC)

Distinct-timestamp representative acceptance finished:1608 independent source comparison samples passed
(worst.0005593height), full decoder/allalpha mips/compression/reproduction passed. All12 NEW compressed
views reviewed intact. No duplicate timestamps; source sampled at integer millisecond resolution.
ONE run_attachment_group.py PID5596 now processes all26 accessory-only identities in isolated subprocesses,
checkpoints eachrecord/log, reuses2 reviewed candidates, checks independent offkey/boundary sourceposes,
measuredskinning_error, fullmetadata/body/child/clip/texture snapshots, ISPC compression/rawbackup/reproduction.
State attachment-group-execution.json, outputs attachments/group. TwoIronLeaves normalmapaccessories
excluded. This is candidate generation, NOT production approval or installation; report labels diagnostic.
Onready classify failures, independently fullvalidate geometry/materials/allmips (memorybounded for long
LCMs), review ALL finalcompressed cohort models incl source Mew/Pawmi/SlitherWing facing, establish closed
source/export registry and dependency/runtime proofs + negative controls, canonicalacceptance/deferredunion.
No production gate bypass; no completed918redo. Final group snapshot helper includes resolvedparenttexture.
Group check reuses existing independentoracle with optional asset_dir only; previous testedmath unchanged.
Group resume currently trusts checkpoint presence: verify source/export/dependency hashes before any retry
reuse or acceptance. Failedrecords remain failures; fix explicitly and preserve evidence, don'tsilentlyskip.
918verifieddeferred/62unfinished unchanged until group fullyapproved. Extrasremain disabled;133active
original texture overrides intact. Continue nextsharedgroups afterthis, not just accessories.

## Accessory cohort finished24/26; group deep/visual review launched

Batch ended2026-09-29 07:44UTC.24candidate_checked,2failed: Mewchristmas/elf have out-of-range sourceUVs
and were correctly rejected by accessory exporter's nonwrapping atlas. Logs attachments/group/14.log,15.log.
Need genuine source repeat support for both; do not clamp or drop sourceparts. Allother24 awaitapproval.
ONE run_attachment_group_review.py PID14244 now tests isolated bounded validator equivalence against full
productiondecoder on BOTH reviewedrepresentatives, exact selectedposes/geometry/bounds comparison. Then
review_attachment_group.py runs full groupstructural/allkeybounds/allalphamips/sourcehash/compressionproof
and3proofnegatives permodel, generates144compressed front/back idle/walk/lateviews plus12contactsheets.
State attachment-review-launcher.json then attachment-group-review-execution.json; output
attachments/group-review. Isolated attachment_stream_validate.py retains allgeometry/material/64bone
checks and EVERYkeyfinite/bounds/motiongate, but computesposedvertices in32framechunks and saves only
renderframes to avoid memoryexplosion onlongLCMtracks. NOT productionpromoted. No gate omissions intended;
equivalence mustpass beforegroupreview. Existing24compressed bytes reused/reproduced, not regenerated.
Onready review ALLsheets/uncertaindetails, closedsource/exportregistry/dependencyproofs/negativecontrols
andcanonicalintegration beforedeferredunion. Continue Mewwrap andother36cases, not tinyfullcatalogredo.
Extrasdisabled,133activecompressionoverrides remainauthorized. Baseline918deferred unchangeduntilapproval.

## User explicitly resumed ALL conversion; follow-up ACTIVE (2026-09-29)

User: 'why is it paused. finish this shit'. Prior paused automation text was stale; root resumed ACTIVE.
ExtrasremainDISABLED; this is conversion/validation/deferredpackage authorization, not installation.
Reviewed ALL12sheets/144compressedviews.20accessories visuallyaccepted. Four Pawmi/SlitherWing Christmas/
elf held for facing/hatplacement matching questionable source references; exactreview in
attachments/group-review/visual-review.json. Mew2 UVfailures real rangevmax1.00159895, body512square,
hat1024square. Need periodic sampling not clamp. Do not edit attachment_export dependencies while staging.
ONE stage_reviewed_accessories.py PID29296 active at15:30UTC canonicaldeepvalidation. Creates standalone
attachment-deferred-package for20 only; no livewrites. Closed20registry matches exactsource/metadata/
child/assets/transforms,dependencies,rawexporthashes,visual/deepmetrics;60proofmutationnegatives beforestage.
Uses existing stage_extras canonicalrelink/pairedDBCs/collisionscan and existingvalidation_cache with
isolated boundeddecoder already equivalence-tested, signatureexplicitly includesaccessoryproof anddecoderhash.
No productiongate bypass/promotion. All20canonicalcompressedhashes mustequalreviewedgroupbytes.
Registry/report in attachments/accepted. State attachment-package-execution.json. Onready inspect proof,
manifest/pairings; preservationandunion with918 stillPENDING. Do not claim942completeduntilverified.
Next adapt preservationfor133activeoverrides, verifyarchives/originals, mergevalidateddeferredunion without
redoing918, then keepengineering4orientation+2Mew+36othercases. SourcePawmi/SlitherWing definitionshave
noexplicitrotate_angle; investigateactualrenderer/modeldefaults, no inventedrotation. Groupednewcasesonly.
KeepACTIVEscheduledfollowup; don'tpausejustbecauseextrasdisabled. All133activecompressedfixesremain.

##20accessory canonical package READY;938union verification running

stage_reviewed_accessories completed20 canonical appearances/60proofnegatives at15:39UTC. All reviewed
compressed hashes matched. ONE merge_accessory_union.py PID39916 now verifies preservation, merges918+20
exactassetbytes andpairedDBCrows, validates28collisionbaselines, preservesrawbackups andallsourceproofs.
State attachment-union-execution.json; output accessory-union-package; evidence accessory-union-verification.json.
IMPORTANT arithmetic correction:918+20=938, NOT942.42declared remain after this20, not38 (four additional
orientationholds in24candidate group). Older942 references were arithmetic errors, not converted assets.
Full canonical package copiesonlyvalidated bytes, combinedDBC numericfields/stringvalues checked exactly.
No source reconversion oractiveclient/serverwrites. Finalized onlyafterpreservation before/after.
Updated grouped-glb/install_review.py installedhelper nowstrictly verifies133 authorizedoverrides against
manifestSHA,lastaction,rawbackups,originalreceipt membership andcompressedactivehash; allotherfiles unchanged.
If fails inspectconcrete mismatch; neverrestoreRAW orweakenhashes. Worker checks8955canonical/9490sprites/
1154baseline/4pilotarchives/8300legacy and2698disabledextras. Extrasremain disabled.
Onready inspectevidence then continue42cases (4Pawmi/SlitherWing,2Mewwrap,other36), actualengineering.
Whilehealthy endquietly, no duplicate/restart/edit. FollowupACTIVE; no stale pauseinstruction applies.


## 938 deferred appearances finalized; isolated Mew wrapping worker (2026-09-29 22:47 UTC)

attachment-union-execution.json is finalized: 938 appearances, 2814 canonical asset files and four paired
DBC files in accessory-union-package. All prior918 asset hashes preserved. Full preservation passed for
8955 active originals (133 authorized compressed overrides),9490 sprites,1154 baseline files,four pilot
archives,8300 legacy archives,three Nudge10::0 configs,and2698 disabled extra archive files. Extras absent
from active client/server. accessory-union-verification.json retains evidence. 42 declared cases remain.
The earlier942 count was incorrect;918+20=938. The combined manifest records validated_source_packages;
it does not fabricate source_report_sha256. Future consumers must validate these constituent proofs.

ONE run_attachment_wrapping.py PID46424 started22:47UTC; state attachment-wrapping-execution.json.
Creates two Mew Christmas/elf candidates under attachments/wrapping, then invokes
review_attachment_wrapping.py. New isolated attachment_wrapping_export.py leaves the frozen accepted
attachment_export.py untouched. attachment_periodic_atlas.py retains the existing15/16 affine mapping
and per-part density, but builds periodic RGBA source halos BEFORE Lanczos resizing, then crops center
and gutter. UVs are never clamped/moduloed; bounded gutter rejects unsupported ranges. This is the existing
resampling policy with periodic borders, NOT lossless original-resolution bilinear equivalence.
Fixture checks independently compare a5x5 periodic source field to the3x3 implementation, detect the old
clamped border, demonstrate vertex modulo changes triangle interpolation, and reject3 invalid UV cases.
Fixtures passed in attachments/wrapping/fixtures/checks.json. Actual final source-filter error/mips and
compressed views still need acceptance; do not approve just because the isolated conversion succeeds.

Worker validates independent fractional source motion, exact source and dependency hashes, raw backups,
ISPC reproduction; subsequent review checks all keys/bounds/materials/64bones, all raw alpha/RGB mips,
every serialized face UV against source affine mapping, periodic source pixels and12 finalcompressed views.
Review outputs attachments/wrapping/review. On ready inspect all contact sheets/uncertain details, source
sampling evidence, closed registry and canonical acceptance, then deferred union. No new Mew count yet.
Do not edit active scripts or restart healthy worker. Stale/failed inspect bounded recorded logs first.

Source ModelData.class codec and ModelData$Builder.class both freshly inspected with javap: default
rotate_angle is(-1.5707964,0,0), consistent with existing model_matrix. Therefore changing that default
is not a justified fix for Pawmi/SlitherWing orientation. Investigate remaining actual loader semantics.
The42 remaining cases and coverage findings remain as documented above. Continue after current worker.
Automation checkpoint successfully updated ACTIVE at this turn, hourly unchanged schedule, quiet checks.
Extras must remain disabled; no active client/server changes were made in this turn.

## Mew review status/provenance repair (2026-09-30 00:41 UTC)

Both candidate exports completed, but the prior review failed at its texture-source hash gate. The
parent incorrectly reported ready because the review caught its exception and exited zero. Old scripts,
states and log preserved under attachments/wrapping/review-before-provenance-fix. Both review and parent
now return failure and require child state ready before reporting ready. No failed review was approved.

Concrete atlas metadata defect: attachment_periodic_atlas.build records str(path) from the prior image
loading loop for both layers, although source_sha256 uses paths[j] correctly. Pixel construction uses
images[j] correctly. The review now resolves each texture independently from original model declarations,
requires the original layer hash and size, independently rebuilds all periodic RGBA pixels and checks UVs.
It retains explicit source_bindings corrections alongside the original records; no source/export bytes
were changed and the frozen atlas/exporter was not edited. Historical converter metadata must never be
used as an authoritative source path without these independently validated bindings. New approval
registry must cover this correction and new review dependency, retaining the old dependency evidence.

ONE resume_attachment_wrapping_review.py PID11868, child review PID50456 launched00:41:28UTC. State remains
attachment-wrapping-execution.json with child attachment-wrapping-review-execution.json. Reuses both
completed exports; no reconversion. On ready review all12 compressed views, closed source/export proof
acceptance and canonical staging before deferred union. Still938 deferred/42 unfinished. Extras disabled,
active originals and new unrelated mod-battlemon-battles work untouched. No production promotion.

## Mew compressed review passed; canonical package running (2026-09-30 01:06 UTC)

Corrected review completed two passes at00:45:50UTC. Reviewed all12 final compressed contact-00 views
and independent source14-idle.png. Mew's upside-down pose is also present in source reference; explicit
parent rotate_angle zero preserved. Body/tail/ears/hats intact in idle/walk/late front/back. Decisions
frozen attachments/wrapping/review/visual-review.json with sheet/check/source-reference hashes.
Independent checks retain source_bindings corrections, periodic RGBA and serialized UV proofs, every
raw mip, compression reproduction and negatives; source pose maxerror approximately.000205 height.

ONE stage_reviewed_mew_wrapping.py PID49384 started01:06:26UTC. State mew-wrapping-package-execution.json;
log attachments/wrapping/stage-error.log/stage.log. Closed two-source/export registry includes independent
periodic review, corrected bindings and historical generation dependencies. Historical reviewer digest
verified via archived pre-repair script; all other generation dependencies current exact match. Twelve
proof-mutation negatives; same canonical relink/deep/DBC/collision workflow as accepted20 accessories.
Output mew-wrapping-deferred-package; no runtime promotion or active installation. Still938deferred until
this package and preservation/union verified. Next merge938+2 into940 deferred only, preserve all938 bytes,
paired DBC fields/collision baselines and original/archive overlays. Then continue other40declared cases.
While worker healthy leave it running. Extras disabled; separate pet-battle work preserved.

## 950 assembly and SMD renderer correction (2026-09-30 03:50 UTC)

User explicitly requested Mew union plus resolving all remaining40. Mew merged into940 with full
preservation and fresh collision scan: mew-union-verification.json. Ten additional candidates now
passed independent fractional/offkey/boundary source comparisons, every-key structural checks, all
raw alpha mips, ISPC reproduction, sixty compressed views (all reviewed), sixty closed-proof negatives,
and canonical staging. MissingNo1, Pecharunt shell2, Rain Castform3, Basculin red/blue4. Their standalone
remaining10-deferred-package is accepted; remaining10-union-package assembles950/2854files including
four paired eDBCs. Prior940 bytes and original/archive/133compressed-overlay preservation passed.

NEW CONCRETE SOURCE BUG: prior attachment reference used AssimpEntityRenderer's local x/y negation,
but ModelData defaults to SMD and SMDEntityRenderer.applyModelRotations uses positive declared scales.
Fresh bytecode at remaining40/smd-entity.txt and model-data.txt confirms this. Frozen old dependencies
and exports retained. smd-renderer-correction.json records22 deferred accessories requiring corrected
proofs (20earlier plus2Mew), so950 is assembly-verified but MUST NOT be declared wholly source-approved.
The new10 are unaffected: old/new normalized parent transforms differ <1e-12, exact per-row addendum
recorded. No original898 bytes or active original models/textures changed. No live extras installed.

Stopped ONLY own new uncorrected run_remaining22.py parent27500/child14248 after discovering source
oracle mismatch; old partial evidence retained remaining40/cohort22. Corrected worker
run_remaining22_smd.py PID34672; read remaining40-cohort22-smd-execution.json for actual PID/child.
Uses isolated remaining40_smd_export/check and smd_source_transform.py. All22 remaining non-accessory,
non-normalmap facing/motion/shell cases; checkpoints/hash proofs. No production promotion.

Second worker run_accessory_smd.py (read accessory-smd-execution.json for PID) repairs all26accessory-only
cases, priority indices20,21,26,27 Pawmi/SlitherWing, followed remaining22 includingMew. Uses NEW isolated
attachment_smd_export, attachment_smd_wrapping_export and check_attachment_smd_fractional. Reuses source
metadata only, not incorrect exports. Previous archives/frozen dependencies untouched. Corrected source4
references12views reviewed: remaining40/source-smd4/contact-00.jpg. Pawmi body now upright in source;
retain authored hat placement, no invented rotation. Need full compressed review, independent periodic
Mew bindings/mips/UV proof, strict closed registry and canonical acceptance for repaired26 before replacing
ONLY the22 affected deferred entries and adding4new. Old898 archive bytes must remain unchanged.

Four IronLeaves normal-map cases still require material support. Actual normal map512square has256
RGB values (not constant/empty); source shader uses Sampler6 and derivative tangent basis, and is enabled
whenever declared normal map exists. Never drop/bake away dynamic map effects or claim missing assets.
Evidence remaining40/renderer.txt and source assets/pixelmon/shaders/core/normal_mapping.fsh.

Continue actual engineering and validation; extras DISABLED and user conversion request ACTIVE. The
remaining22 worker and accessory26 worker are independent. Do not edit their active dependencies.
When ready inspect per-row failures, review final compressed views and stage/merge exact corrected proofs.
No core build. Preserve unrelated battle module/effect work. Coverage findings still need identity closure.

### Dependent reviews and coverage closure (2026-09-30 04:02 UTC)

Queued ONE review_accessory_smd.py PID9188, waiting on accessory-smd-execution.json, then full bounded
structural/alpha/compression checks and156compressedviews for26candidates. State accessory-smd-review-execution.json.
It uses corrected source references under remaining40/source-smd-all (84views rendered, diagnostic-only
IronLeaves maps still not rendered). Source-to-WoW comparison rotation is corrected RZ(+90), not oldRZ(-90).
Mew periodic source bindings/independent atlas reconstruction remain additional approval requirements.

Queued ONE wait_review_remaining22_smd.py PID26732; state remaining22-review-launcher.json. Waits for
single22producer, then review_remaining22_smd.py writes remaining40/review22-smd and state
remaining40-review22-smd-execution.json. Explicit subprocess return and ready-state checks prevent false success.
Both review workers do NOT approve/install. Do not duplicate/restart healthy producers or dependent reviews.

Coverage progress: remaining40/coverage-resolved.json independently verifies8orphan mesh files are exact
byte duplicates of declared resources (current hashes checked). Greninja battle_bond inheritance resolved:
SpeciesTypeAdapter resets DataCopier; StatsTypeAdapter clones first form and overwrites only present fields;
DataCopier.setForm keeps first form; absent genderProperties therefore inherits all5base visual mappings.
No geometry IDs allocated for duplicates/inherited visuals. Eleven other orphan meshes and7ServineOBJparts
still need loader/identity resolution. Do not rerun source inventory or count22animation-only files as models.

## Fan Rotom fixed, twelve more packaged, accessories resumed (2026-09-30 15:44 UTC)

User explicitly says do ALL remaining fixes and accessory correction approval. Extras remain disabled.
Resumed stopped run_accessory_smd.py after proving old workers absent: parent41524/child47264. All25
previous completed rows rechecked exact source/export/dependency hashes. Last Pawmot elf regenerates
only incomplete output, now in independent fractional comparison after writing99MB M2. CPU active.
ONE review_accessory_smd.py PID11236 waits then runs full structural/alpha/source checks and156views.
Read accessory-smd-execution.json and accessory-smd-review-execution.json. No duplicate/restart/edit
while healthy. Corrected26 comprise22 replacements to previously deferred accessories plus4new cases.

BOTH Fan Rotom normal/shiny now fully accepted and deferred. Exact-key diagnostics proved source/local
quaternion matrices agree3e-16 and serialized keys agree3e-5height; error3.28% was between10ms keys due
to rapidly rotating fan pivot translations. New isolated fanrotom_export/channels/check use2ms keys;
original25fps/79frame periods unchanged, every intervening odd millisecond checked. Each3324samples,
worst.001342403height. Robust quaternion experiment alone did NOT fix it. All12finalcompressedviews
reviewed, structural/allalpha/ISPCproofs and12closed-proof mutation negatives/canonical relinks passed.
fanrotom-deferred-package2; fanrotom-union-package952 with full preservation/freshDBCs/old950hashes.
No production converter changes or live installation.

All120cohort22 final compressed views actually reviewed. Twelve accepted: Swellow2/Joltik2/Braviary2,
Spiritomb2/Lampent2/Araquanid2. Eight facing cases remain HELD for actual world-heading/source context:
GmaxBlastoise3,strikeRalts1,Spectrier2,IronBundle2. Do not approve those from numerical matches alone.
remaining40/review22-smd/visual-review.json freezes decisions/sheet hashes. stage_remaining12_smd.py
passed72proof negatives and12canonical deep approvals; remaining12-deferred-package accepted.
merge_remaining12_union.py finalized remaining12-union-package964/2892assets+4pairedDBCs. Evidence
remaining12-union-verification.json: old952bytes,8955originals with exact133compressedoverrides,9490
sprites,1154baseline,4pilotarchives,8300archives,3Nudgeconfigs,2698disabledarchivedextras preserved.
IMPORTANT964 is assembly verified, still includes22 old accessories awaiting corrected replacement.
Declared16unfinished =8facing +4newaccessories(current26batch) +4IronLeaves normalmaps. Don't double
count22repairs. Source coverage identity closure remains as earlier; no source substitution.

Prepared but NOT RUN stage_accessory_smd.py for all26 after actual156view decisions. It requires frozen
visual-review.json, current checkedsource/exports/reviewer records, complete new dependency hashes,
156mutation negatives, canonical validation and reviewed compressed equality. Its Mew cases additionally
call verify_accessory_smd_periodic.py: independent source bindings, larger periodicRGBA reconstruction,
all serialized faceUVs; retains historical atlas metadata path correction. No bypass promotion. Inspect
and run only after visual review. Merge must replace exactly22 known keys in964 and add4, preserving
remaining942 existing entries and old898 archived bytes; pairedDBC rows need exact replacements, IDs
stable. Do not use naive additive union with duplicatekeys. Expected968 after this verified correction.

Four IronLeaves are genuine unresolved material engineering. remaining40/ironleaves-material-contract.json
has exact4 identities/maps/metadata and source shader hash; normal vectors deviate up to54.4828degrees.
Source normal_mapping.fsh samplesSampler6 and derives TBN from screen dFdx/dFdy(worldPosition), then
applies dynamic light0/light1. Static diffuse baking, discarding map or ordinary UV-tangent assumptions
are not equivalent. Current v264 writer emits one diffuse texture/no normal binding. Public WarcraftXL
v1.1 M2DrawApi supports an interceptor but does NOT prove installed wxl-native-render supports this map.
Public wxl-m2/wxl-native-render repository lookups404; do not declare impossible solely from that.
Evidence API headers and exact installed binary hashes under remaining40/normalmap-client-evidence.
Need supported material path or independently validated clientextension; keep map source untouched.
Source ModelData full codec also proves legacy texture_transparency field absent/ignored; do not invent
opacity from it. Existing PNG alpha remains preserved. Other battle-module/addon/effects work untouched.

## Standard-client Iron Leaves constraint and accessory progress (2026-09-30)

User explicitly rejected wxl-native-render as a requirement. Iron Leaves must run on the standard client. No extension source or installation is required or requested. No production converter or active asset was changed for this experiment.

- All 26 corrected accessory exports passed. ONE review_accessory_smd.py PID11236 continues full decoded/compressed review; read accessory-smd-review-execution.json first. Both corrected Mew periodic proofs passed in remaining40/accessory-smd-periodic-checks.json. Still requires all156 visual views, closed staging and 22-replacement/4-addition merge. stage_accessory_smd.py is prepared but NOT run. Existing964 package still contains22 superseded accessory entries.
- Initial normalmap_vertex_candidate changed Iron Leaves walk geometry by .01536 height; REJECTED. Preserve its evidence; do not use for acceptance.
- normalmap_exact_skin_candidate restricts subdivision to identical bone-weight faces; idle/walk source errors <6e-11 height. Its edge-sampled lighting was insufficient.
- normalmap_fitted_candidate fits the interior normal field on the same exact-skinning restriction. Independent19000triangle probes/26 light directions: mean absolute Lambert error .01488393 vs .03890078 for omission, area-weighted angular error3.42726deg, worst51.36976deg. Geometry remains <6e-11 height. This is a standard UV-tangent-field approximation, NOT exact Minecraft screen-derivative shader equivalence. Evidence ironleaves-fitted-quality-execution.json and remaining40/ironleaves-fitted-quality.json. No approval yet; inspect outlier area and final appearance.
- ONE run_ironleaves_standard.py PID47644 is generating base normal/shiny ordinary M2 candidates in remaining40/ironleaves-standard, read ironleaves-standard-execution.json. No native extension required. Maps and provenance retained, diffuse RGBA unchanged. Needs serialized normals/skinning/source proof, final ISPC compression and normal-aware visual review. Existing renderer recomputes smooth normals and is NOT sufficient for this material validation. The two accessory Iron Leaves variants remain pending and must use the same material handling after validation.
- Most recent assembled deferred package remains remaining12-union-package964. FanRotom2 and additional12 motion/shell models are fully validated/merged; prior952 hashes preserved. No live installation; extras disabled;133 authorized compressed originals untouched.
- Automation update returned 'Automation does not exist in the app ... may have been deleted manually'. No replacement automation was created and no recurring follow-up was updated. Do not claim it is active. Existing worker processes are independent of that missing automation.

Follow-up to standard-client prototype: both normal/shiny ordinary M2 exports completed (ironleaves-standard-execution.json ready,count2). ONE review_ironleaves_standard.py PID36488 now decodes all keys/sections, validates serialized unit normals, compresses with ISPC/raw backups/reproduction, and renders12 views with the actual skinned exported normals through render_ironleaves_normals.py. Diagnostic only; NOT source-equivalence approval. Read ironleaves-standard-review-execution.json. Accessory review PID11236 still healthy and processing Pawmo at this checkpoint. No duplicate workers. Standard-client candidates have not been merged, installed or counted complete.

## Verified970 and remaining source-facing work (2026-09-30 18:10 UTC)

LATEST PACKAGE ironleaves-base-union-package:970 appearances/2910 assets+4pairedDBCs, verified ironleaves-base-union-verification.json. ALL26 corrected accessories accepted after156 compressed views,156 mutation negatives/canonical checks; exactly22 old entries replaced with stableIDs and4added,942 unaffected preserved. accessory-corrected-union-package968 intermediate. Base normal/shiny IronLeaves2 accepted after12 normal-aware compressed views and independent serialized barycentric source-motion checks,14negatives. Ordinary client vertex-normal approximation retains original maps/provenance and unchanged diffuseRGBA; explicitly NOT exact Minecraft screen-derivative normal shader. User rejected extension dependency; none required. Full preservation passed8955originals including133 exact compressed overrides,9490sprites,1154baseline,4pilot,8300archives,3configs,2698disabled extras. No install; extras remain disabled.

ONE run_ironleaves_attachments.py PID48828 /child51020 remains healthy generating Christmas thenelf refined-body+hat candidates. First state ironleaves-attachments-execution.json. Long independent authored LCM timelines; do not restart/edit frozen exporter/checker. Requires normal-aware final structural/alpha/visualreview, strict canonical staging thenunion. No count increase yet.

Facing source diagnostic complete48 paired views reviewed: remaining40/facing8-source. record_facing_landmarks.py creates heading-landmarks.json with source hashes. Blastoise andSpectrier bind semantichead/tail landmarks face+X; idleturn/rearing is authored and matches source, not grounds for invented fixedrotation. StrikeRalts SAME model/clips/transforms asnormalRalts keyb3275ca5983db7bbac46a30718faa61d05100f992fd6a4bd2f0f1eb97b3e6a7e. Six source-faithful cases accepted for staging in new facing6-review; old frozenreview unchanged. ONE stage_facing6.py PID43656 started18:10UTC, read facing6-package-execution.json/log. Retains strictfullcanonical checks,36mutationnegatives,source/dependency/headingproofs,reviewedcompressedhash equality. No merged count increase until verified union970+6.

IronBundle2 stillheld. Sourcebind yellowbeak centroid[-.017277,-2.187524,12.308301], bindbounds[-6.704416,-2.795740,-.628452]..[6.704416,16.181130,16.816117], inferredbindfaces-Y vs target+X; idlebeak reversesY fromauthoredrootturn. Do NOT guessed180rotate. Need landmark-derived targetbasis/source-world semantics and preserve authoredmotion. No correction applied.

Declared source3782=2802oldreuse+970deferred+10unmerged (6currentstaging+2IronBundle+2IronLeavesaccessories). Additional coverage identity closure still pending11orphanBMD+7ServineOBJ; reuse existingaudit. Automation absent; no recurringfollow-up created/updated. Existingworkers independent. Preserve unrelated battle-module/addon work; no corebuild.

FOLLOW-UP18:11UTC: Six-case stager first failed an unchanged hardcoded twelve-count assertion. Corrected cohort assertion to6; no quality gate changed. RetryPID30596 passed strict canonical acceptance/36negatives. merge_facing6_union.py PID45792 finalized: facing6-union-package976,2928assets+4pairedDBCs; facing6-union-verification.json verifies970prior hashes andfullpreservation. Latest source3782=2802oldreuse+976deferred+4declaredremaining (IronBundle2,IronLeavesaccessories2), plusoutstandingorphan/Servinecoverage. No liveinstall. IronLeavesworker48828/51020 remainshealthy. Sixformerfacingholds closedwithpairedsourceandbindlandmarks, noanimationrotationchanges. Nextread ironleaves-attachments-execution.json; finalnormalaware review/staging/unionneeded afterready. Noautomation active.

LATEST: IronLeaves accessory export worker48828 finishedready2/failed0 at2026-09-30T18:35:31Z. Both source fractional proofs pass; NOTapproved ormerged. ONE review_ironleaves_attachments.py PID16524 launched on user status/resume. State ironleaves-attachments-review-execution.json. Bounded fullallkeys/sections decoder, unitserialized/skinnednormal checks, allrawalphamips, reuse exactISPCcompressedbytes/rawbackups/reproduction,3compressionmutationnegatives percase,12normal-awarefinalviews. Onready inspect remaining40/ironleaves-attachments-review/contact.jpg pluschecks and thenstrictclosedsource/materialregistry/canonicalstaging/union. Noextensiondependency. Current976verified unchanged. IronBundle2 andorphan/Servinecoverage stillpending. Noactiveinstall orautomation claim.

USER correctly challenged leaving independent work pending. Started both now. run_ironbundle_facing.py PID47072 finished2passed/0failed18:46:58UTC. Isolated +90Z calibration maps measured sourcebind beak-Y toWoW+X, retainsallauthoredmotion/materials. Independent ironbundle_facing_check expresses coordinate mapping separately, alloffkeys/loopproofs/fullstructural/alpha/ISPCpass. NOTvisualapproved ormerged. ONE review_ironbundle_facing.py launched immediately, read ironbundle-facing-review-execution.json; inspect allfinalviews beforeclosedregistry/staging. Candidate exporter/checker/runner frozen whileproofsused.

resolve_coverage_identities.py PID49292 completed:11unreferencedBMD/7ServineOBJ analyzed, zero exactsemantic geometry+skin+bind duplicates amongsame-species declaredmeshes. remaining40/coverage-loader-identities.json retainscounts/hash/candidate literalreferences. Literalbasename matches in4speciesJSON are NOT fullpath matches; do notcallthem resolved. No literalclass/json/java refs to7ServineOBJ orother7BMD. Actual loaderbytecode dumped coverage-model-loaders.txt andcoverage-cached-loader.txt: registeredSMD+Assimp, need finish interpretation/dynamicpath evidence. No absence-only claim, no dropping assets/newIDs. IronLeaves finalreview16524 stillrunning. Latest verifiedunion976, extrasdisabled.

LATEST19:28UTC: User flagged40min idle; completed review outputs had waitedforassistant. No automation exists. Do notleavecompletedstepspending. Both originalreviews finished. ALL12IronLeavesaccessory normal-awareviews inspectedaccepted: christmas/elf hats/body/sourcecolors intact. stage_ironleaves_attachments.py PID51396 runningstrictcanonicaldeep (firstcase done,secondinprogress),14proofnegatives inclnormalmapmaterialadaptation;complete sourcefilesguard hashesnormalmaps,sourcefittedapprox unchanged. Currentreviewfrozen visual-review.json.

IronBundle FIRST bind-based+90Z candidate visuallyREJECTED: authoredidle/walk facebackwards despitebindaxis. Preserved ironbundle-facing artifacts. Isolated ironbundle_animated_facing_export/check usesconstant-90Z mapping animatedsource+Y toWoW+X without alteringtiming/rig/sourcegeometry. Bothpassedindependentoffkey/boundaryoracle andstructural/alpha/compression. ALL12newrenders reviewedfrontcorrect; visual-review.json frozen. stage_ironbundle.py PID27200 finishedready2,12proofnegatives/canonicalexactcompressedbytes. Noactiveinstallation.

ONE finish_final_declared.py PID27900 waitsonaccessoryacceptanceready (failsifworkerdisappears orstatusfailed), thenruns merge_ironleaves_attachments_union.py976+2=978 andmerge_final_declared_union.py978+2=980,fullpreservation/freshcollisionchecks/exactpriorhashes/pairedDBCverification. FIRSTread final-declared-execution.json andironleaves-attachments-package-execution.json. Neverduplicateworkers. Expectedlatest final-declared-union-package980 ONLYafterverification. Userdoesnotwant another40minutecompletedstageleftidle.

Coveragebindingconclusions saved remaining40/coverage-binding-conclusions.json withexactresourcechecks acrossspeciesmetadata andactualbytecode. BothSMD/AssimploaderstakeModelDataresource+explicitclips;Assimpimportsrequestedbytesfrommemory;ResourceWithFallbackusesexplicitresource/fallback, notneighborfilediscovery. Servinesourceusesone servine.bmd +idle/walk, no7OBJassemblybinding.11orphanBMD+7OBJhaveNOexactdeclaredbinding andnotexactsemanticduplicates. Remainexplicitgenuinesourcebindinglimitations; doNOTinventtexture/clip/assemblyidentity orcountconverted. Noallsourcecompleteclaim. Allsourceassets retained. Fullsourcecatalogdeclaredcompletion distinctfromlooselegacyresources.

FINAL DECLARED CATALOG VERIFIED2026-09-30T19:30UTC: finish_final_declared.py ready980. Latest final-declared-union-package contains980appearances/2940canonicalassets+4pairedDBCs. final-declared-union-verification.json provesremaining_declared0,prior978bytehashespreserved,freshcollisionchecks,fulloriginal/archivepreservation,extras_activefalse. Source3782=2802exactreuse+980converteddeferred. BOTH IronBundlevariants andALL4IronLeavescases,ALL26accessorycorrections closed. Noextensionrequired; measurednormalfieldapproximation remainsexplicit. Allfinal24views inspected,IronBundle12mutationnegatives andIronLeavesaccessory14passed,exactreviewedcompressedhashes canonicalmatched. Noactiveinstallation. NOworkersremainingforthese cases; noautomationclaimed.

Do NOT callallloose-source conversion complete: remaining40/coverage-binding-conclusions.json retains11BMD+7ServineOBJwithnoauthoredappearance/clip/assemblybindings, hashes andloaderbytecodeevidence. Thosegenuinesourcebindinglimitations remain explicit andsourcepreserved; noinventedidentities/substitutions/droppedparts. No needtoaskforanotherpack. Declaredcatalog isfullyconverted; optionallegacylooseassetreconstruction isseparatelyunresolved.

Loose-source investigation completed usingBOTH supplied9.4.0/9.4.1: remaining40/loose-source-resolution.json. Four files are represented geometry/components: Mewtwoloose2592faces matchbasepositions/UV/winding/namedweights;Burmy950bodyfacesincludedallthreecloaks;Litwickbig/small96eachincludedboth-flame192. Fourteenfiles are unselectedvariants/layers/authoringparts:Flygoncombined2 (1318base+108eyes overlap,68unprovenunusedfaces),Servine7OBJ(localcoordinates/externalmissingMTL;declaredriggedBMDused),Charizard1,Heracross1,CofagrigusAura1,NihilegoExtra1,StarVaroom1. Exactresourcepaths unreferenced inbothpacks; remaining renderingclassspeciesnamehits wereplayer cosmeticCharizardwings, notPokemonmeshloaders. Normal loaderconsumesdeclaredresource+clips, no directoryassembly. Noadditionalactiveappearanceidentified. DoNOTclaim18filesconverted; no new IDs/install. Theyarepreservedunusedsources, not18missingPokemon. Historicalauthorintentforunusedvariants unknown;customreconstructionoutsidefaithfulcurrentappearanceconversion. Previous '18remainingconversioncases' wordingtoo broad. Evidenceincludesgeometrycomparisons,sourcehashes,perversionclass/resource scan,OBJ provenance andloaderbytecode. Declared980deferred remainsverified/unchanged;noextension/extrasactivation.

## 3D edition transition: extras activation authorized

User explicitly requested preserving the complete 2D edition, then activating the full 3D catalog including Extras. This supersedes prior deferred-only/disabled instructions. The immutable 2D distribution is C:/data/pokemon-mod/2d-version (28,204 files). The 3D distribution is C:/data/pokemon-mod/3d-version. Runtime catalog: 3,965 available appearances across 2,345 forms, including all 980 Extras; 16 original appearances rescued. The actual local client addon and 2,940 Extra model assets plus four paired eDBC files are installed and hash-verified by generated/version-migration/3d-activation.json. Historical disabled/archive receipts remain unchanged; generated/source-catalog/3d-catalog-active.json supersedes them. All 2,985 original replacements and the 133 authorized compressed textures are preserved. New delivery compression retains raw backups; 340 compressed texture views were reviewed. No core build or remote database execution was performed. Remote deployment instructions: modules/mod-battlemon/3D-DEPLOYMENT.md. Pending world/character rev_1790798400.sql installs the catalog and backs up/removes only 161 unsupported owned form/shiny pairs and their party/taught-move references; do not treat that as 161 known owned Pokemon. Actual removed row count depends on the remote database. Prior loose-source investigation remains authoritative: no additional active appearance was identified.

## Module consolidation

All Battlemon runtime code, addons, configuration templates, SQL, assets and tools now reside in modules/mod-battlemon. Former mod-battlemon-overworld and mod-battlemon-battles roots are removed. Their generated evidence trees were moved byte-for-byte into mod-battlemon/generated; historical absolute paths retain original spelling and resolve by replacing either former module root with mod-battlemon. The exact mapping and configuration preservation receipt is generated/module-consolidation/receipt.json. No model bytes, display IDs, config keys/defaults, live client files or SQL contents changed as part of consolidation. Keep all three existing config filenames on deployment. The frozen 2D edition stays unchanged; only the 3D distribution follows the unified module layout.
