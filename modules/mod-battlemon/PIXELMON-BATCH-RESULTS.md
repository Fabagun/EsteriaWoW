# Pixelmon conversion result

Installed and verified 2,985 of 3,162 appearances: 1,496 normal and 1,489 shiny.
This pass added normal/shiny Mega Darkrai (form 756), Zygarde (03) (1114) and Necrozma (04) (1241).
All 2,979 previous exports remain byte-identical. Original sprite names and DBC mappings are unchanged.

## Verification

- All 8,955 installed canonical files and embedded texture references verified.
- Full internal deep validation passed: 2,985 appearances / 2,883 unique exports.
- Both eight-entry acceptance packages passed deep checks; 80 regression tests passed.
- New exports exactly match the accepted cohort; GLB source/export registry proofs pass.
- GLB oracle, 28 reviewed views, authored alpha/emissive, helper-bone tracks and 64-bone sections retained.
- All 9,490 originals, 1,154 active baseline files, four archived pilot eDBCs and 8,300 archives verified.
- Retired experimental layers remain absent; all three Nudge 10::0 entries remain intact.
- No remote deployment or live testing occurred.

## Remaining 2D fallbacks

Exact per-appearance list: [PIXELMON-2D-FALLBACKS.md](PIXELMON-2D-FALLBACKS.md).
120 missing matching models, seven missing palettes and 32 unverified size/battle identities stay 2D.
No additional model pack is requested; this follows the user's supplied-pack-only scope.
The user explicitly accepted 2D fallback for the other 18 appearances (normal/shiny Rain Castform,
Spiritomb, Fan Rotom, Lampent, Araquanid, red/blue Basculin, Joltik and Iron Leaves).
Work is complete with 2,985 installed 3D appearances and 177 accepted 2D fallbacks.
Evidence and concrete limitations: generated/pixelmon-batch/glb-review/remaining-assessment.json.

## New in-game checks

Restart the client, then test `.bmo spawn 756`, `.bmo spawn 1114`, `.bmo spawn 1241`.
Append `1` to each command for shiny. No new eDBC deployment is required.
If old experimental eDBCs were previously deployed to the remote realm, remove only
CreatureModelData and CreatureDisplayInfo `.dbc9-battlemon-3d` / `.dbc9-battlemon-3d-batch`
files from its dbc-continuations directory and restart worldserver; retain original `.dbc1-battlemon`.

## Rollback

From the repository root:

```powershell
.\modules\mod-battlemon-overworld\tools\manage-3d-batch.ps1 -Action remove
```

This removes receipt-owned canonical 3D overrides, revealing original sprites. It leaves original
sprite files, base DBCs and archives intact. It does not restore experimental 3D eDBC mappings.
Keep `generated/pixelmon-batch/installed-direct.json`, legacy receipts and `legacy-backup/`.

The full per-appearance records and failures are in `generated/pixelmon-batch/report.json` and `exceptions.json`.

Current verification: generated/pixelmon-batch/glb-review/.
Verified at 2026-09-28T16:49:32.345045+00:00.
