# Esteria Grand Satchel

Item **910237**, 237 general-purpose slots. GM command: `.additem 910237`.

This addon requires the matched Esteria custom client/server container ceiling of 254 slots.
It does not raise quest capacity, widen class masks, or resize existing bags/backpack.

The supplied 1122x1402 artwork is preserved as nine 512x512 RGBA TGA tiles. The window starts
at 561x701 UI units, fits within the current screen, and can be dragged. `/satchel` toggles the
satchel windows; `/satchel 0.8` sets a preferred scale. Standard bag toggles, all-bags bindings,
ConsolePort, and Escape are supported. Equipped bank satchels are available while at the bank.

Item buttons inherit the installed 3.3.5 `ContainerFrameItemButtonTemplate`: click, use/equip,
drag/drop, modified links, stack splitting, merchants, socketing and tooltips use native handlers.

DragonUI integration requires the staged session-index stride fixes in `bagster_data.lua` and
`bagster_classes.lua` (100 to 1000), preventing collisions between large-bag and adjacent-bag slots.
The separate window excludes 237-slot bags from Bagster's combined item view. SavedVariables
and the user's existing bag categories are preserved.

Packaging (no native build or installation):

```powershell
python tools/esteria_satchel.py --source path/to/source.png --out path/to/new-stage
```

The stage includes a compressed namespaced MPQ, loose addon and DragonUI compatibility files,
one pending SQL migration, exact baseline/entry hashes, and a pixel round-trip report. Item.dbc
is extended from the current winning client table, preserving all other rows and strings.

Live acceptance after installing the matched build:

1. Obtain/equip the bag in an ordinary bag slot, then open it through keyboard and controller.
2. Drag, use and split items at slots 1, 100, 101, 127, 128, 129 and 237; check adjacent bags.
3. Check tooltips, cooldowns, locks, quest marks, merchant selling and bank movement.
4. Relog and verify the last-slot item persists. Test swapping/unequipping empty satchels.
5. Check multiple satchels, Escape, all-bags toggling, dragging, and different UI scales.

The ordinary stock Wow.exe does not support the expanded container layout. Installation alone
and mocked/offline checks do not prove live gameplay acceptance.
