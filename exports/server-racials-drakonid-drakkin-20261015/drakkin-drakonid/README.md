# Drakkin / Drakonid server subset

- Drakkin Alliance: race 66; female display 60064, male Tarasek display 60070.
- Horde Drakkin: retired race 67; retained existing rows and source, disabled in effective ChrRaces.
- Drakonid Alliance/Horde: races 69/70; displays 60068/60069.
- Drakkin racial spell block: 110300-110319, including hidden effects.
- Drakonid racial spell block: 110400-110406.
- Male Drakkin Running Wild: 110050/110051; conditional on gender and trained riding tier.

`database/` contains live rows scoped to these races, models, displays, appearance, spells,
procs and script bindings. The corresponding schema is provided separately. Empty tables are
retained to record that no matching live rows existed.

Required source lives at `../source/` using repository paths:

- `modules/mod-custom-server/src/{drakkin_racials,drakonid_racials,donor_racials}.cpp`
- `modules/mod-custom-server/src/MP_loader.cpp` and the rest of that module's sources/build hook.
- `modules/mod-worgoblin-high-elf/src/Worgoblin.cpp` (male Drakkin Running Wild).
- `src/server/shared/{SharedDefines,CreatureAppearance}.h`.
- Core creation, storage, ObjectMgr, RaceMgr and DBC loading files included in the source snapshot.

Use the common tables and full effective DBCs in `../database/` and `../server-data/` together
with these rows. Human/Orc legacy eligibility masks are shared dependencies; race IDs remain
66/67/69/70. No new client art or racial implementation was generated.
