Arakkoa playable race (Alliance, race id 45)

Built from the HD Outland Arakkoa. Male display 977475, female display 977476.
Needs a core that already allows race ids above 32 (the same kind of core this
CoA repack uses). Race 45 shares the 32-bit race-mask slot of race 13, the same
way the racial notes in the build describe. The proficiency SQL uses that mask
(4096). Do not import it if race 13 on your server must keep different weapons.

Client
  Copy client\patch-ZR.MPQ into the WoW client's Data folder.
  It has to load after the other patch archives. On this client the name
  patch-ZR.MPQ already does that.

Server data files
  Copy server\dbc\*.dbc over the worldserver Data\dbc folder, then restart
  the worldserver.
  Spell.dbc is a full file from this repack with Arakkoa spells 13990001
  through 13990005 added. Replacing a different server's Spell.dbc will drop
  that server's own spell edits.
  CharBaseInfo.dbc is also inside the MPQ. The server copy is the same file.

Database (worldserver stopped)
  1. sql\arakkoa.sql                  world: create info, copied from race 50
  2. sql\arakkoa_racials.sql          characters: grants the five racials
  3. sql\arakkoa_proficiency_world.sql
  4. sql\arakkoa_proficiency_characters.sql

Racials: Outcast's Curse, Feathered Descent, Lore of Skettis, Flight of the
Raven, Skyward Glide.
