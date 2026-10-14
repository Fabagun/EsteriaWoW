# Additional login scenes

The existing login screen selector now includes **Retail Midnight** (`mi`) and **Sirus WoW** (`si`).
`LoginScenes.lua` contains the scene data inserted into the current winning `AccountLogin.lua`; the
existing preview, Apply, Cancel and saved-choice behavior handles both entries.

Midnight uses the two full scene layers from Retail `wow` build `12.1.0.69933`, content build
`dcfc90fffd79ba00406ae46f5f657592`, converted using the pinned WoW retroport skill tools. Its 110 source
dependencies have verified CASC content identities. Wrath uses approximations for newer shaders,
particle blending and animated camera FOV; the conversion report records the exact losses.

Sirus comes from `D:/Sirus/_client/World of Warcraft Sirus`. All 73 enabled foreground placements and
the background are retained, including Human camera inheritance, lighting, transforms and sequences.
The 337 assets are already Wrath format. Only embedded dependency filename spans are relocated;
geometry, animation tracks and their offsets remain unchanged.

All assets use `custom/esteria_login/{midnight,sirus}/` paths. The packer merges assets into the existing
`Data/Patch-Zzz.mpq`, retaining its previous files, and changes only `Interface/GlueXML/AccountLogin.lua`
in `Data/patch-Z.MPQ` and `Data/enUS/patch-enUS-Z.MPQ`. It does not edit the executable or saved settings.

Local source inventories, conversion report, reviewable Lua, staged archives and installation receipt
are under `G:/RetroPorterWork/login-screens/`. Raw assets remain outside Git. The acquisition recipe and
skill configuration are in `.agents/plans/login-screen-midnight-sirus/`.

With those local inputs available:

```powershell
rtk proxy python tools/login_screen_pack.py stage
rtk proxy python -m unittest discover -s tools -p test_login_screen_pack.py -v
rtk proxy python tools/login_screen_pack.py install
rtk proxy python tools/test_login_persistence_contract.py
```

Staging refuses an already patched login baseline. Installation requires closed clients/editors and
unchanged baseline/stage hashes, creates verified backups outside `Data`, and restores archives if
replacement fails. `installed.json` records the precise backup directory and archive hashes.

Live acceptance remains separate: fresh launch, preview both new screens, switch to an existing screen,
Cancel, Apply, restart to check persistence, and exit. Confirm visuals and animations on that client;
parser checks and the Lua harness do not establish that Midnight's shader approximations look correct.

The shared model loader waits for `GetModel()` to report the requested file before applying camera,
position, scale and sequence. Sirus first waits for the Human camera donor, then for the foreground
model. Unfinished models stay transparent, and switching scenes cancels callbacks on hidden frames.
The regression harness simulates delayed loads that reset transforms on completion.

To apply only this Lua repair to an existing installation, use `repair-stage` and `repair-install`
instead of `stage` and `install`. These actions preserve the asset archive and record their receipt
under `G:/RetroPorterWork/login-screens/initialization-fix/`.
