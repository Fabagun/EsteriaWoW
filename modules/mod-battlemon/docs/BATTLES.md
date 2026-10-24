# Battlemon Battles

Optional world pet-battle presentation and friendly trainer/playerbot duels for this AzerothCore checkout.
Included in the unified `mod-battlemon` server module. Do not also install the former standalone
Battlemon battles/overworld modules or the upstream reference modules. See `../3D-DEPLOYMENT.md` for
the current 3D catalog SQL and client/server eDBC requirements.

## Play

Install both client addons, then use `/bmb` to open the battle menu.

- **Wild Pokemon:** uses the existing Battlemon encounter, party, four equipped moves, capture, item,
  cooldown and reward rules. Existing overworld encounters also use the selected presentation.
- **Duel selected player / bot:** select a nearby player or playerbot. Humans receive an invitation;
  bots accept automatically when enabled. There is no nameplate right-click launch action; select the
  target and use the menu button or `/bmb duel`. `/bmb accept`, `/bmb decline`, `/bmb forfeit` are also available.
- **My Pokemon / moves:** opens your existing party editor. It remains the source of equipped moves.
- **Classic wild UI:** check **Use classic UI for wild battles** in `/bmb` to restore the original
  wild-battle interface; uncheck it for the new HUD. `/bmb classic` and `/bmb pet` also work.
  Player and playerbot duels always open the new team-capable HUD, regardless of this preference.
  The original `/bm` collection, shop and other screens remain available.

The new HUD shows health, ailments, weather, move details/PP, party switching, a turn clock and a battle
log. Wild battles have bag/capture controls; friendly duels deliberately have neither. Two temporary,
non-interactive world actors use the unified 3D Battlemon display catalog. They share a private
in-place battle phase with the participants, with move lunges and model-supported attack emotes.
The 3D edition includes the validated Pixelmon Extras in that catalog.

## Duel rules

Conscious owned party members and their equipped moves are copied into a temporary match. The existing
Battlemon engine resolves move priority, speed, damage, types, abilities and status effects. Switching
uses a turn; fainting requires a replacement. Both trainers choose before a normal turn resolves.
Duplicate/stale actions are rejected. A missing action times out; if neither side acts the match draws.
Leaving range, entering WoW combat, dying, teleporting, disconnecting or forfeiting ends the match.
Configuration/catalog reload cancels duels before their catalog references can become invalid.

Duels never persist match HP/PP, grant XP/items/captures, spend inventory, or alter collections.
With the default `GenerateBotTeams=1`, **every bot duel gets a fresh generated team**, ignoring any
stored bot party. Nothing is inserted into the bot collection. Human opponents retain their real teams.

| Your WoW character level | Opposing bot team |
| --- | --- |
| 1-19 | Random 1-3 basic Pokemon |
| 20-59 | Random 3-6 regular Pokemon |
| 60+ | Random 3-6; each slot has a 25% rare/strong pool chance |

Level 20 starts the larger-team bracket. The bot's WoW level does not raise Pokemon levels or team size.
The opposing Pokemon levels follow the rounded average of your conscious participating Pokemon. Below
average level 5 they match it exactly; otherwise the variation is +/-10% rounded down, minimum 1 and
maximum 3 levels, clamped to levels 1-100. Examples: average 1 -> 1; 10 -> 9-11; 30 -> 27-33; 80 -> 77-83.
Team sizes are independent of your number of Pokemon: a level-20+ character with one Pokemon can face
3-6, as specified. A lower configured `TeamSize` caps these ranges.

Beginner entries have no incoming evolution link, base-stat total at most 400, and are not rare.
Rare/strong entries are catalog legendaries/mythicals, species with base-stat total at least 550, or
catch rate at most 25. This is a difficulty classification, not a claim about canonical rarity.
Only base forms with usable catch metadata enter the generated pools; no hats, battle-state variants
or duplicate species rolls. Missing beginner metadata fails the match rather than substituting a
legendary. Setting `GenerateBotTeams=0` opts out of scaling and requires a bot's own conscious team.

Bot choices consider move power, type effectiveness, accuracy, STAB and healing; they replace fainted
team members. Normal playerbot decisions pause during the duel and resume when it ends. There is no
ranked ladder, wagering, matchmaking queue or bot collection progression.

## Server deployment (your remote server)

Push the complete unified `modules/mod-battlemon` and delete the retired standalone module paths.
The one module registers collection, overworld and battle scripts. This work does not configure or compile your core.
Copy `conf/mod_battlemon_battles.conf.dist` to the remote server's normal module configuration directory
as `mod_battlemon_battles.conf`, then include the new module in your normal remote build/deployment.
The existing Battlemon database/catalog and overworld template 60000 must already be installed.
`MOD_PLAYERBOTS` enables integration with this checkout's playerbot AI; no bot fork is bundled here.

Defaults enable wild presentation, friendly duels and bot opponents. Important switches:

| Setting | Default | Purpose |
| --- | --- | --- |
| Enable | 1 | Enable the companion module |
| DefaultMode | pet | Default presentation for clients without a saved choice |
| AllowClassic | 1 | Allow the companion addon to select the old presentation |
| EnableDuels / EnableBotDuels | 1 / 1 | Human and bot duel availability |
| GenerateBotTeams | 1 | Generate fresh, level-appropriate teams for every bot duel |
| TeamSize | 6 | Maximum conscious party members, clamped to 1-6 |
| TurnSeconds / InviteSeconds | 45 / 30 | Decision and invitation timeouts |
| MaxDistance | 25 | Maximum distance from battle origin and between duelists, in yards |
| WorldActors | 1 | Show temporary world models |

All keys use the `BattlemonBattles.` prefix. Classic is a presentation option; this does not disable
or remove the original Battlemon server protocol or require other players to install the companion.
Human duel participants need the companion addon to see and submit the new match actions.

## Client installation and backup

Run `python tools/install_addon.py <Interface/AddOns>` from any working directory. It copies the bundled
`BattlemonBattles` addon and adds one optional routing hook to `Battlemon/Core/Net.lua`. It backs up the
previous Net.lua and any existing companion addon under `Interface/BattlemonBattles-Backups/<timestamp>`.
The receipt records exact before/after hashes. Unexpected routing code is rejected before changes.
The original handlers run when the companion is disabled or classic is selected. Restart the client
so it discovers the new addon. Each client needs both addons for the new mode.

For removal, disable BattlemonBattles in the addon selector; the routing hook remains harmless. To
restore files exactly, use `python tools/restore_addon.py <Interface/AddOns> <backup-directory>`.
Restoration refuses to overwrite files that have changed since that installation.

## Validation and remote smoke checks

`tests/test_addon.py <path-to-Battlemon-addon>` executes the actual companion and base Net.lua in Lua 5.1
with WoW API mocks. It covers classic routing, saved mode, forged-sender rejection, wild move/capture,
duel revisions, duplicate suppression, forced switches, invitations, forfeits and action-bar restoration.
Install test-only `lupa` and `luaparser` into `generated/test-deps` or your Python environment.
`tests/test_installer.py` checks backup, repeat installation, hash-guarded restoration and tamper refusal.
C++ is checked with the repository codestyle linter and local header/API inspection. These are not a
substitute for compiling and running on your remote realm; no live server or in-game verification has
been claimed.

After remote deployment, verify wild move/switch/item/capture/run, classic mode, a two-human invitation
and full duel, a playerbot duel with replacement, timeout, disconnect, teleport and combat cancellation.
Check that owned HP/PP/inventory/XP remain unchanged after a friendly duel and that bot AI resumes.
Check world model placement and HUD scale on the real 3.3.5a client before enabling it realm-wide.

### Private battle presentation

New-mode battles use an unused phase bit (16–30), excluding explicit database spawn masks
on the current map, current instance players and other battles in that instance. The core
ANYWHERE mask is a visibility wildcard, not a phase reservation: GM observers and all-phase
world objects do not exhaust the pool. Such observers/objects remain visible according to
normal core phase rules. If all candidate bits are explicitly reserved, the battle cancels.
Both duel participants share the phase. The original phase is restored on battle end,
logout and reload; a phase changed externally is not overwritten. The terrain stays
in place, so entering the battle does not teleport or require a loading screen.
Moving more than `MaxDistance` (default 25 yards) from the starting point ends the battle.
Actors start 14 yards apart, eight yards ahead of the trainer. Moves queue native WoW
visuals and physical lunge/return motions; models lacking attack clips use movement.
These are presentation effects, not WoW combat or new model clips.

The opaque bottom HUD covers action bars, groups moves in two rows, and opens a separate
party selector from Change Pokemon. Struggle only appears when no move has PP remaining;
the server validates that condition. Classic wild UI remains selectable.

Client changes can be loaded with `/reload`. Phasing, spacing, fleeing and move effects
require deploying the updated server modules. No local core build or live-server test
has been performed for these changes.

The Pokemon selector and Bag open opaque drawers above the command area. The bag
has paginated item rows; revive rows name their target. After a wild defeat, ball choices
open automatically in the empty right margin, with quantities and Skip capture; there
is no Capture button. The battle log uses the left margin. Narrow screens place these
panels above the commands. No cursor dropdowns are used.
The selector has its own mouse layer, and refresh only changes button enabled state
when that state actually changes, preserving clicks during frame updates.
### Native WoW battle effects (default)

`BattlemonBattles.NativeSpellVisuals = 1` selects native WoW spell presentation. Existing
configs without this key also default to native effects. The catalog has 29 verified
native spells, 104 named move overrides and fallbacks for all 18 Pokemon types.

- Thunder Shock uses Lightning Bolt; Thunder/Thunderbolt use repeated Chain Lightning.
- Flamethrower uses a short fire volley; Fire Blast uses a larger Pyroblast projectile.
- Hydro Pump uses a Waterbolt volley; Ice Beam and Blizzard use frost projectiles.
- Confusion/Psychic use Mind Blast. Shadow Ball, poison and grass have distinct visuals.
- Physical moves lunge, play the mapped impact and return; recipients get a hit reaction.
- Healing and protective moves play on the user's Pokemon rather than the opponent.

These are deliberate WoW visual interpretations. Recognizable native missile/impact
models and their DBC sound cues replace the crossed sprites. Not every Pokemon move
has a unique WoW model; unmapped moves use their type/category. Converted models can
still lack specific cast/attack/wound clips. Persistent status auras/icons are separate
and are not added here. HP and battle logs still resolve under the existing turn engine;
visual timing does not delay damage, and switching cancels stale actor animations.

The service sends `SMSG_SPELL_START`/`SMSG_SPELL_GO` presentation packets using the core's
one-unit target layout. It never calls `CastSpell`, creates a `Spell`, adds an aura or
changes WoW health/power/threat. Phased creature GUIDs are re-resolved for every delayed
step; scene/actor changes cancel playback. Normal finishing attacks drain before scene
cleanup; disconnects and invalid scenes still clean up.

Deploy the updated `mod-battlemon` through your normal remote build and restart
worldserver. No new client assets, new eDBCs or SQL are needed for native playback.
The local client/server spell and visual rows were checked for equality and all chosen
visual kits were checked for presence. The supplied client's Renew impact kit is missing;
healing profiles therefore use the verified Flash Heal visual. Missing runtime spell
rows fall back to the prior renderer. Set `NativeSpellVisuals = 0` to explicitly use it.

Mappings live in `data/native-visuals.json`. Regenerate and validate them with:

```sh
python tools/native_visuals.py --client-dbcs /path/to/client/DBFilesClient --server-data /path/to/server/data
```

`tests/test_native_visuals.py` checks missing impact kits, client/server mismatches,
channeled-spell rejection and generated-catalog consistency. Core packet serialization
and APIs were checked against this repository; no core build or remote/in-game visual
test was performed. On the realm, check lightning/fire/water/Confusion, physical contact,
self-healing, a finishing attack, switching and leaving during playback.

### Previous Pixelmon attack-effect adaptation (optional fallback)

With native visuals disabled, the supplied Pixelmon 9.4.1 definitions select 894 move plans: 203 particle
models across beam, ball, buff, rain, tube, explosion, radial and lightning families,
plus source-selected leap/run/stomp motions. Thunder Shock selects lightning;
Flamethrower and Water Gun select their particle beams. Confusion uses a leap in this
source pack; persistent confusion/status icons and sounds are not added by this pack.

These are deterministic WotLK crossed-sprite adaptations using supplied textures,
colors and action mappings, not exact replays of Java particle simulation. Particle
counts, sizes and durations are bounded; density and timing differ from Minecraft.
The manifest retains original parameters and source hashes. Combat damage and status
rules are unchanged. Effects are noncombat, unselectable phased scene actors and are
removed on cleanup. Finishing effects drain before normal phase restoration;
disconnects and invalid scenes still clean up. Effects are decorative: HP/log updates
are not delayed to synchronize with them, and switching can cancel an old actor's
queued animation. Models without authored attack clips use supported movement.

Delivery lives in `assets/battle-effects`: client M2/skin/BC3 BLP files, raw RGBA PNG
backups, paired CreatureModelData/CreatureDisplayInfo eDBCs, and hash manifest.
IDs 310000–310202 are reserved by this package; installation checks collisions.
No Pokemon replacements or Pokemon Extras are installed by this tool.

After your git deployment, stage the server display files with Python 3.9+:

```sh
python3 modules/mod-battlemon/tools/install_effects.py --server-data /path/to/server/data
```

This writes `dbc-continuations/*.dbc9-battlemon-effects`. Deploy the updated modules
through your normal remote build and restart worldserver to load both code and rows.
For another client, run the same tool with `--client-patch /path/to/data/patch-z.mpq`.
It refuses unowned overwrites and modified receipts/files. Fully quit and restart WoW
after client asset installation; `/reload` alone does not load new models and eDBCs.
No local core build or live realm verification has been performed.

Validation: `tools/validate_effects.py` independently decodes all 203 models, bone
sections, animation bounds and texture paths; reproduces ISPC 1.0.1 BC3 bytes and
checks every mip, source hashes and paired display rows. Corrupt bone, bounds and
material fixtures must fail. `tests/test_effect_installer.py` covers ownership,
tampering, cross-patch ID collision and interrupted-copy rollback. Thirty decoded
pose renders cover all eight families; actual 3.3.5a playback remains a remote test.
Source textures and definitions come from the user's supplied Pixelmon archive;
no new redistribution license is asserted.
