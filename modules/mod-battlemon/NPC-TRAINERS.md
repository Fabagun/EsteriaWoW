# Pokemon NPCs: placement and rosters

All 21 trainer models have dedicated NPC templates. **No NPC is spawned, moved, or replaced by this update.**
Place Professor Oak and Nurse Joy inside the Center manually. The old 900501 attendants and 900511
profession teacher remain unchanged until you choose to remove them in-game.

## Deployment

Deploy and rebuild mod-battlemon and mod-pokemon-trainer. Install the matching model DBCs with worldserver stopped:

```sh
python3 modules/mod-pokemon-trainer/tools/install_gym_models.py --server-data env/dist/bin/data --apply
```

The normal world updater applies `data/sql/updates/pending_db_world/rev_1790969531700983800.sql`.
The follow-up `rev_1790972077274103100.sql` binds Nurse Joy to the same `npc_battlemon_center`
script as the working attendant and clears obsolete per-spawn nurse script overrides. Its three
menu options work with the existing Center script; the rebuilt profession module adds Ditto healing
through the shared Center service. Restart worldserver. The models are already in the user's loose patch-z.mpq folder; this change requires
no new client assets. The normal Battlemon and BattlemonBattles addons handle the battle and supplies UI.

## Placement

Stand where an NPC should appear, face the desired direction, and run `.npc add ENTRY`.
The **NPC entry happens to match its display ID** for these templates. `.morph` only changes appearance;
use `.npc add` to get the behavior listed below. Select an unwanted old NPC and use `.npc delete` to remove it.

| NPC | Entry / command | Role or roster |
| --- | --- | --- |
| Brock | `.npc add 950100` | Geodude, Onix |
| Misty | `.npc add 950101` | Staryu, Starmie |
| Lillie | `.npc add 950102` | Clefairy, Cleffa, Comfey |
| Lillie (Z-Powered) | `.npc add 950103` | Clefable, Cutiefly, Comfey |
| Nurse Joy | `.npc add 950104` | Heals Battlemon party and Ditto; supplies shop and party management |
| Beauty | `.npc add 950107` | Random 2-4 from Elegant companions pool |
| Black Belt | `.npc add 950108` | Random 2-4 from FIGHTING pool |
| Fisherman | `.npc add 950109` | Random 2-4 from WATER pool |
| James | `.npc add 950110` | Weezing, Victreebel, Meowth |
| Jessie | `.npc add 950111` | Arbok, Wobbuffet, Meowth |
| Koga | `.npc add 950112` | Koffing, Muk, Koffing, Weezing |
| Lass | `.npc add 950113` | Random 2-4 from Route companions pool |
| Lorelei | `.npc add 950114` | Dewgong, Cloyster, Slowbro, Jynx, Lapras |
| Lt. Surge | `.npc add 950115` | Voltorb, Pikachu, Raichu |
| Officer Jenny | `.npc add 950116` | Friendly non-battling guard; no trainer or vendor gossip |
| Professor Oak | `.npc add 950117` | Teaches Pokemon Trainer and profession rank upgrades; opens PKMN |
| Sabrina | `.npc add 950118` | Kadabra, Mr. Mime, Venomoth, Alakazam |
| Shrek | `.npc add 950119` | Random 3-4 from Swamp companions pool |
| Swimmer | `.npc add 950120` | Random 2-4 from WATER pool |
| Team Rocket Grunt (Female) | `.npc add 950121` | Random 2-4 from Team Rocket pool |
| Team Rocket Grunt (Male) | `.npc add 950122` | Random 2-4 from Team Rocket pool |

## Battles and supplies

Trainer gossip offers **Challenge this Pokemon Trainer** and **Browse Pokemon supplies**. Supplies use
the existing Battlemon shop and currency, including its existing item/price checks. Oak teaches the
secondary profession; he is not a battle opponent. Jenny is not a battle opponent or vendor.

Generic teams roll independently for each challenge, without duplicate species. Fisherman and Swimmer
pools are entirely Water; Black Belt's pool is entirely Fighting. Named teams retain their listed species,
including Koga's two Koffing. Trainer Pokemon use the rounded average level of the player's eligible party,
clamped to 1-100; they use the catalog's level-appropriate moves. The configured BattlemonBattles.TeamSize
can shorten teams (default six preserves every named roster).

The Kanto leader and Lorelei species are based on their [Red/Blue teams](https://pokemondb.net/red-blue/gymleaders-elitefour).
Jessie/James use signature-themed teams. Lillie's Fairy-oriented teams and Shrek's swamp pool are custom
interpretations, not claims of exact canonical game parties.

These challenges reuse the existing nonlethal duel engine: conscious party members enter at full battle HP/PP;
results do not persist HP loss, award Pokemon XP/items/badges, or allow capturing the trainer's Pokemon.
A trainer victory grants one Pokemon Trainer profession skill point, up to the trained rank cap.
Your profession's Pokemon level limit governs which owned Pokemon can join. Normal WoW pet/class bars remain independent.

Each player has a separate battle instance; two players can challenge the same stationary trainer.
The trainer is not moved into a player's private battle phase. Leaving range, combat, logout, map changes,
trainer removal and forfeiting terminate the encounter and restore the player's original phase.
`BattlemonBattles.Enable` and `BattlemonBattles.EnableDuels` must be enabled. Playerbot-duel settings do not
control these NPC opponents.

Edit `data/npc-trainers.json` and run `python modules/mod-battlemon/tools/build_npc_trainers.py` to regenerate
the roster header and pending template SQL. After that migration ships, subsequent DB changes should get a new pending update.

## Undo

Manual rollback: `modules/mod-pokemon-trainer/rollback/npc-trainers.sql`.
It refuses to remove templates while any manually placed spawn uses them. Delete those NPCs first,
stop worldserver, back up the world DB, then apply the rollback manually. It preserves the older Center
NPCs, skills, captures and model assets. Model collision metadata is retained for existing manual morphs. Disable/roll back the code separately if desired.

## Validation and remaining live checks

Automated checks cover all 21 display links, base Pokemon model availability, type-themed pools,
canonical rosters, no spawn SQL, actual repository schema column names and repeat-install behavior.
The migration and manual rollback were also exercised in an isolated local MySQL database, including
an entry collision and the rollback's manually placed spawn guard. No production tables were modified.

C++ was not built (repository rule requires an explicit build request). No updated auth/world stack was
available, so live gossip/battle behavior is not yet verified. After deployment, verify on a test character:

1. Add Oak/Joy; learn the profession, open PKMN, train a capped rank, and heal a fainted party and Ditto.
2. Challenge Brock: Geodude then Onix; complete a battle and verify one profession skill gain.
3. Force both sides to switch, exhaust PP, forfeit, leave range, and relog; verify the battle closes and phase restores.
4. Challenge Water/Fighting trainers repeatedly and verify only the matching types appear.
5. Have two players challenge the same trainer; confirm independent rosters/turns and phase cleanup.
6. Repeat an existing player/playerbot duel to check the shared action submission path.
7. Browse supplies and purchase an item through the normal Battlemon shop; Jenny must have no challenge option.
