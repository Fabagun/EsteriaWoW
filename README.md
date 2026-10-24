# EsteriaWoW

A self-hosted World of Warcraft 3.3.5a (WotLK, client build `12340`) server built on
AzerothCore with the PlayerBots fork, standard Eluna, Docker Compose and MySQL. Esteria
extends the stock game with dozens of new playable races, a third player faction, a
rebuilt client interface and a stack of progression and quality-of-life modules.

It is the server half of a matched pair. The client half is the
[wowdecomp Esteria fork](https://github.com/STRHercules/wowdecomp), which supplies the
native extensions (64-slot race table, Retail-style appearance, digital inventory) that
this server's packets and data assume.

Most of this is opt-in per module or needs the matching client. Status words follow
[Modules.md](Modules.md): **enabled**, **installed**, **staged** (data present, not
validated in game) and **manual** (not a normal CMake module). A feature listed here is
not proof that it passed a live test; each section says what is known.

---

## What Esteria adds

### Playable races

Esteria widens the race table from 10 to 64 slots and ships a registry-driven set of
playable races. The registry is
[`race_registry.json`](modules/mod-custom-server/data/races/race_registry.json). Each row
records faction, start zone, asset owner, and the stock race it borrows for legacy
eligibility masks (there are no free 32-bit mask bits left).

| Family | Race IDs | Notes |
| --- | --- | --- |
| Original ten | 1-8, 10, 11 | Plus 435 skin, 56 face and 220 hair-color additions from the Ascension customization pack |
| Worgoblin baseline | 9 Goblin, 12 Worgen, 13 High Elf | Worgen and Dracthyr use saved alternate forms |
| Custom races | 14/24/27 Broken, 15/62 Sethrak, 25 Forsaken | Broken has its own racial runtime effects |
| Imported player models | 16 Eredar, 17 Nightborne, 18/26 Pandaren, 19 Void Elf, 21 Lightforged, 22 Zandalari, 23 Dark Iron, 28 Dracthyr, 29 Kul Tiran, 30/31 Illidari | |
| Darkfallen | 43 Alliance, 44 Horde | Own identity; shares the high mask bit |
| Retail ports | 20 Vulpera, 45 Mag'har, 46 Highmountain, 47 Mechagnome, 48/49 Earthen, 50/51 Haranir, 52/53 Skyborne | Expanded creator controls for six families |
| Creature and Wrath ports | 54 Naga, 55 Tuskarr, 56/57 Vrykul, 58/59 Forgotten, 60/61 Ogre | Female Vrykul and Alliance Ogre included |
| Newer additions | 63 Gnoll, 64 Saberon, 65 Jinyu, 66 Drakkin, 68 Arakkoa, 69/70 Drakonid, 72 Slime Giant, 73 Centaur, 75 Kyrian, 76 Venthyr | Several are hidden in the creator |
| NPC-only | 32-42, 67, 71, 74 | Reserved so NPC race rows never collide with players |

Server-side support for this lives in:

| Piece | What it does |
| --- | --- |
| `RaceMgr` and `SharedDefines.h` | Bounded race helpers; masks come from `GetRaceMaskForRace`, never an unchecked shift |
| Appearance codecs | `Highmountain`, `Earthen`, `Haranir`, `Vulpera` and `CreatureAppearance` headers validate and carry extra appearance bytes through create, save, enumerate and login |
| Character wire extensions | Extra appearance bytes ride in `HXE1` / `HXE2` roster trailers and `HRC1` create trailers that the client strips before stock parsing |
| `mod-custom-server` racials | Racial spells and cast visuals per race: `race_racials`, `drakkin`, `drakonid`, `darkfallen`, `slime_centaur` and `donor` racials, plus Centaur travel |
| Retail look save and broadcast | Body sliders and the full Retail look are stored per character and sent to nearby players |
| Playable-bot policy | PlayerBots follow the same race, visibility and appearance rules |

The developer handoff in [RaceGuide/](RaceGuide/) covers the pipeline, per-race recipes,
runtime DLLs, server changes and the validation checklist. Start at
[RaceGuide/README.md](RaceGuide/README.md). Race racial design is in
[RACIALS.md](RACIALS.md).

### Freeborn: a third faction

`TEAM_FREEBORN` is a persistent third `TeamId`, not an alignment layer on top of
Alliance and Horde. It is specified in
[Freeborn_Third_TeamId_Implementation_Specification.md](Freeborn_Third_TeamId_Implementation_Specification.md),
with core hooks, a classless wildcard path and unit tests in
`src/test/server/game/Combat/FreebornTeamTest.cpp`.

### Client interface and customization

| Feature | What it does |
| --- | --- |
| Esteria Character Select (ECS) | Virtualised roster with race portraits, search, drag reorder, notes and a detail tooltip. See [docs/CHARACTER_SELECT.md](docs/CHARACTER_SELECT.md) |
| Retail-style Glue | Login screen, race creator, 64-race buttons and portraits from [UI.md](UI.md) and [tools/](tools/) |
| Digital inventory | Carried inventory window with server-side search and pagination, negotiated by an `ESTERIADI` handshake so older cores keep normal bags. See [client-customization/EsteriaInventory/](client-customization/EsteriaInventory/README.md) |
| Grand Satchel | 237-slot bag support. See [client-customization/EsteriaSatchel/](client-customization/EsteriaSatchel/README.md) |
| Native appearance | Hair, skin, geoset, cosmetic wing and material handling in [client-customization/](client-customization/README.md) |
| Barber and creator limits | Race-capacity and archive-capacity patches, with tests under `client-customization/Test*.cpp` |

All barbers still use the legacy combined-value interface. Expanded creator controls do
not imply an expanded barber.

### Content and gameplay modules

| System | Status | Summary |
| --- | --- | --- |
| Battlemon (`mod-battlemon`) | Enabled | Pokemon-style collection, wild encounters, world pet battles, human and bot duels. 980 converted 3D models. See [Battlemon.md](Battlemon.md) and [modules/mod-battlemon/README.md](modules/mod-battlemon/README.md) |
| `mod-wxl-dbc` | Enabled | Server DBC continuation files, so large custom tables (Battlemon, Freeborn) load without replacing base DBCs |
| Echoes of the Worldsoul | Staged | Permanent attunement and stat bridge, in `mod-custom-server/src/mod_attunement_plus.cpp` |
| Prestige and Draft | Staged | Character replay, ranks and draft choices through Eluna |
| Dream Path (`mod-seasonpass`) | Staged | Seasonal tiers, weekly goals, chests, Dream Renown. Reward tables are in [Season.md](Season.md) |
| Mythic+ (`mod-mythic-plus`) | Staged | Keystones, timers, affixes and rankings |
| Dungeon Master (`mod-dungeon-master`) | Staged | Procedural dungeons with six tiers, nine themes and Roguelike mode |
| Instance ownership | Enabled | `InstanceMode` keeps Mythic+, Dungeon Master and Roguelike scaling from stacking with AutoBalance |
| Nemesis (`mod-nemesis-system`) | Staged | Persistent revenge targets with ranks, affixes and the `NemesisTracker` addon |
| Loyal Steed (`mod-loyal-steed`) | Staged | Persistent companion with saddlebags and fast travel |
| Transmog (`mod-transmog`) | Enabled | Rewritten service, collection UI and protocol bridge |
| Mounts | Staged | About 111 novelty and car mounts, packed by `tools/cars_mount_pack.py` and `mount_pack_batch2.py` |
| Faction-Free (`mod-Faction-Free`) | Manual | Cross-faction player-to-NPC behavior with replacement faction DBCs |
| Fly Anywhere (`mod-fly-anywhere`) | Enabled | Flying in Eastern Kingdoms and Kalimdor, with a matching `AreaTable.dbc` |

The full list, including the stock quality-of-life modules (AH bot, account-wide
achievements and mounts, AOE loot, random enchants, item upgrade, corpse respawn and
others), is in [Modules.md](Modules.md) and [ModuleStatus.md](ModuleStatus.md).

### Core changes

Esteria prefers module hooks. Some things need the core:

| Area | Change |
| --- | --- |
| Eluna | Standard Eluna integrated as core callbacks, with spell and aura hooks and quest-reward prevention |
| Races | 64-slot race handling, legacy-mask aliasing and race/faction compatibility in `Player` and `Unit` |
| Persistence | `extraAppearance BIGINT UNSIGNED` on characters, plus per-character Retail look and slider storage |
| Handlers | `CharacterHandler` create and enumerate extensions, digital inventory packets |
| DBC | `DBCStore` continuation support used by `mod-wxl-dbc` |
| Teams | Third `TeamId` and the code paths that read it |

The exact core delta since the September 2 import is captured in
[RaceGuide/05-SERVER.md](RaceGuide/05-SERVER.md).

### Planned and design-stage work

These are documents, not shipped features:

| Document | Scope |
| --- | --- |
| [ConquestOfEsteria.md](ConquestOfEsteria.md) | Audit and transport plan for the Ascension custom classes. The current core still has class IDs 1-11 |
| [ESTERIA_LIVING_WORLD_IMPLEMENTATION.md](ESTERIA_LIVING_WORLD_IMPLEMENTATION.md) | Persistent simulation of towns, businesses, crime, trade and government |
| [EsteriaGameplayExpansion.md](EsteriaGameplayExpansion.md) | Expanded hunter taming (drake, dragonkin, elemental, undead, mechanical), animal companion, custom Hearthstone |
| [FORSAKEN_TAUNKA.md](FORSAKEN_TAUNKA.md), [HALFELVES.md](HALFELVES.md) | Race implementation plans |
| [WODMODELS.md](WODMODELS.md) | Analysis of Warlords of Draenor character models |
| [IDEAS.md](IDEAS.md) | Backlog |

---

## Requirements

- Docker Desktop with Compose.
- A separately obtained 3.3.5a build `12340` client. The repository does not ship or
  redistribute it.
- The matching wowdecomp Esteria client build, for the native race, appearance and
  inventory extensions.
- Blizzard-derived converted assets (MPQs, DBCs, textures) are not in Git. The
  repository stores manifests, generators, tests, SQL and docs.

## Running

Docker Desktop must be running. From the repository root in PowerShell:

```powershell
docker compose up -d
docker compose ps
```

Rebuild after a core or C++ module change:

```powershell
docker compose up -d --build
```

| Service | Purpose |
| --- | --- |
| `ac-database` | MySQL 8.4 and persistent database volume |
| `ac-db-import` | Applies AzerothCore and module database updates |
| `ac-client-data-init` | Initializes the persistent extracted client-data volume |
| `ac-authserver` | Login service |
| `ac-worldserver` | Worldserver, Eluna, PlayerBots and gameplay modules |
| `ac-tools` | Optional client-data extraction profile |

`docker-compose.override.yml` publishes auth (`3724`) and world (`8085`) and keeps
MySQL on loopback (`127.0.0.1:3306`). For remote players, the realm address, firewall
and client `realmlist.wtf` must all use the same reachable host. Do not expose MySQL.

```powershell
docker compose logs --tail 100 ac-worldserver
docker compose restart ac-worldserver ac-authserver
docker compose down
```

`docker compose down` keeps the database volume; `down -v` discards it. Attach to the
worldserver console with `docker attach ac-worldserver` and detach with `Ctrl+P`,
`Ctrl+Q`. Create an administrator interactively:

```text
account create <username> <password>
account set gmlevel <username> 3 -1
```

Never commit or print database or account passwords. More commands are in
[COMMANDS.md](COMMANDS.md).

### SQL rules

Put new local SQL in `data/sql/updates/pending_db_*` or the owning module's database
directory. Do not edit `data/sql/base/`, `data/sql/archive/` or merged
`data/sql/updates/db_*/`. Back up the database before changing live data.

## Layout

| Path | Contents |
| --- | --- |
| `src/` | AzerothCore core with Esteria changes |
| `modules/` | 57 module directories, including `mod-custom-server` (Esteria's own C++, SQL and race registry) |
| `lua_scripts/` | Eluna scripts bind-mounted into the worldserver |
| `data/sql/` | Base, merged and pending database updates |
| `conf/dist/` | Configuration templates |
| `RaceGuide/` | Race and custom-content developer guide, with evidence and reference indexes |
| `client-customization/` | Native appearance, digital inventory and satchel sources and tests |
| `tools/` | Race packers, deploy scripts, UI patchers and their tests |
| `docs/` | Character select, retroported race plan and design specs |
| `e2e/` | Protocol-level live-stack tests built on AzerothGhost |
| `Arakkoa-race/`, `SlimeSkeleton/`, `VulperaDBC/`, `Vehicles/` | Staged race and asset packages |
| `wxl-races-patcher/`, `BinaryWork/` | Client patch inspection and race-select DLL work |
| `Harvested/`, `NewModels/` | Extracted source models and race material |
| `azerothcore-wotlk-coa/` | Class donor tree used for the Conquest audit |

## Status

Server build, database import and worldserver readiness are recorded. Several races,
the creator, the digital inventory and the Vrykul and Ogre ports have been checked in
game by the developer. Live validation of the progression modules, PlayerBots with
every race, restart recovery and multiplayer is not complete. See
[PROGRESSION.md](PROGRESSION.md) and [RaceGuide/10-VALIDATION.md](RaceGuide/10-VALIDATION.md).

## License

Server and module licensing follows the repository and each upstream module's license.
AzerothCore is AGPL-licensed; see [LICENSE](LICENSE). World of Warcraft client files,
MPQs, DBCs and extracted data are not distributed here.
