# Pixelmon 3D pilot

This reversible test replaces only base Bulbasaur, Charmander, Squirtle, and Pikachu,
including shiny versions. Other forms keep their existing sprites. No C++ rebuild,
SQL changes, addon changes, or replacement of base DBC files is required.

The converter reads the supplied Pixelmon 9.4.0 BMD meshes and idle/walk animations,
exports WotLK M2 version 264 with SKIN files and mipmapped DXT5 BLP textures, and writes
only eight rows per table into a new tier-9 eDBC layer. The original display/model IDs
remain intact, so overworld critter morphing and right-click Battlemon encounters keep
using the existing form IDs.

## Installed layout

Client: `D:\WoW\Dark-Bro-WXL-COA\Dark-Brotherhood-wxl\Data\patch-z.mpq\`

- `Creature\Battlemon3D\`: eight M2, eight SKIN, eight BLP files.
- `DBFilesClient\CreatureModelData.dbc9-battlemon-3d`
- `DBFilesClient\CreatureDisplayInfo.dbc9-battlemon-3d`

Server repository deployment: `env/dist/bin/data/dbc-continuations/`, with the same two
continuation files, included as new repository files for the remote realm. Copy them from
`env/dist/bin/data/dbc-continuations/` to the remote server's configured
`WxlDbc.ContinuationPath`. Restart that worldserver to apply them.

The tier-1 Battlemon files, `patch-W.mpq`, and existing files in `patch-z.mpq` are preserved.
Folder patches auto-discover these continuations; no existing manifest is edited.
Generated assets and the installation receipt live under `generated/pixelmon-3d/`
(gitignored). Keep that directory for validation and removal.

## Try it in game

Fully exit and reopen the client and restart worldserver after installation. These
commands summon temporary Battlemon for five minutes:

| Pokemon | Normal | Shiny |
|---|---|---|
| Bulbasaur | `.bmo spawn 1` | `.bmo spawn 1 1` |
| Charmander | `.bmo spawn 6` | `.bmo spawn 6 1` |
| Squirtle | `.bmo spawn 11` | `.bmo spawn 11 1` |
| Pikachu | `.bmo spawn 37` | `.bmo spawn 37 1` |

Check front/back views, idle animation, moving critters, nameplate height, click
selection, and starting a battle by right-clicking. `.bmo inspect` should still show
form 1/6/11/37 and display 50001/50006/50011/50037 (70000 range for shinies here; the package shipped 60000, which Broken/Sethrak use).
Existing critters use the new look whenever their current form matches these four.

## Undo / reinstall

From the repository root in PowerShell:

```powershell
& ./modules/mod-battlemon-overworld/tools/manage-3d-test.ps1 -Action remove
& ./modules/mod-battlemon-overworld/tools/manage-3d-test.ps1 -Action install
& ./modules/mod-battlemon-overworld/tools/manage-3d-test.ps1 -Action validate
```

Then restart the client and worldserver. Removal restores the underlying 2D models
by removing this layer; it does not rewrite any original file. Removal is restricted
to the 28 exact files in the receipt and refuses files changed by another process.
For a remote realm, also remove its two `*.dbc9-battlemon-3d` files and restart it.

Optional script arguments: `-Client`, `-ServerData`, and `-Python`. `-ServerData` is the
parent of `dbc-continuations`, not the continuation directory itself.

## Regenerate

Requires Python with NumPy and Pillow 12+ (DDS DXT5 encoder). Blender is used only for
previewing; it is not required to generate or deploy the WoW assets.

```powershell
$python = "$env:USERPROFILE/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe"
& $python modules/mod-battlemon-overworld/tools/pixelmon/convert.py `
  --pixelmon 'F:/_d-bak/_other/Pixelmon-1.21.1-9.4.0-universal' `
  --client 'D:/WoW/Dark-Bro-WXL-COA/Dark-Brotherhood-wxl'
& $python modules/mod-battlemon-overworld/tools/pixelmon/validate.py --preview
& $python -m unittest discover -s modules/mod-battlemon-overworld/tools/pixelmon -p test_pipeline.py -v
```

`preview_blender.py -- --preview <generated/pixelmon-3d/preview>` can be run with Blender's
`--background --factory-startup --python` options. It saves `battlemon-3d.blend` and idle/walk
PNGs from the decoded exported M2/BLP data. The Blender scene uses sampled mesh poses for
inspection, not the source Pixelmon rig; the installed M2s contain real bone animation tracks.

## Validation and conversion limits

- Texture island borders receive eight pixels of color/opacity padding, plus two pixels
  at each mip level. This prevents WoW's alpha cutoff from making dotted holes along UV
  seams. Validation bilinearly samples triangle edges at every BLP mip and requires opaque samples.
- Binary validation covers pointers, mesh indices, bone palettes, weights, quaternion
  decoding, idle/walk/run sequences, texture decoding, animated bounds, and DBC links.
- Tests cover known rotations, hierarchy transforms, sparse BMD frames, malformed input,
  installation/removal, preservation of the baseline, and refusal of externally changed files.
- Blender renders verify the exported geometry, texture orientation, and sample poses.
  They do not establish that the WotLK renderer has loaded the files. In-game validation
  remains necessary; no local auth/world server was running during generation.
- Idle and walk are sampled at 30 fps. Run reuses the walk motion with WoW's run movement
  speed. Attack, death, swim, sound, Minecraft particles, and separate emissive materials
  are not ported in this pilot.
- WoW supports four bone influences per vertex. The strongest four are normalized;
  `manifest.json` records the maximum pose error versus the full source weights.
- Meshes are normalized to one unit of standing height, facing +X. Existing Battlemon
  species scaling and hover rules still apply. This is a test-size convention, not
  Pixelmon's original per-species world scale.
- Bulbasaur's source idle animation includes extended vines; those are retained.
- Source assets are read from the supplied local installation and are not committed.

Format references used while implementing the reader/writer:

- [Pixelmon BMD/SMD converter](https://github.com/TARNATlON/bmdsmdconvert)
- [pywowlib M2 definitions](https://github.com/wowdev/pywowlib/blob/master/file_formats/m2_format.py)

The installed files require the existing WXL extended-DBC client extension and server
module, exactly as the sprite layer does.

For resumable bulk conversion beyond the four-form pilot, see [PIXELMON-BATCH.md](PIXELMON-BATCH.md).
