# Esteria server racials and Drakkin / Drakonid export

Extracted from the working EsteriaWoW repository and the running server on October 15, 2026
(America/Chicago). This is a copy of the existing implementation and data. No server files,
databases, characters, or installed client files were changed; no build was run.

## Contents

- `races/`: per-race JSON indexes, `index.json`, and full effective racial/triggered spell records.
  Covers **59 race entries: 56 enabled in effective server race data, plus disabled Sethrak 15,
  disabled Pandaren 26, and retired Horde Drakkin 67**. Kul Tiran 29 and Illidari 30/31 are included
  despite being absent from the current 55-entry registry.
- `server-data/dbc/`: the complete effective DBC directory copied from the running worldserver,
  including mounted overrides. Whole tables preserve stock spell/model/skill dependencies and
  unrelated custom rows that share those files. These are server DBCs, not a client patch.
- `server-data/dbc-continuations/`: the active continuation files, including Freeborn faction data.
- `database/shared-world-schema.sql` and `shared-world-data.sql`: a live snapshot of 61 shared
  race, creation, skill/model/faction DBC override, and spell tables. Includes `spell_dbc`, proc
  definitions, bindings, start spells/skills, exclusions, outfits, actions, stats and totems.
  The data dump uses a single consistent MySQL transaction. Each additional scoped dump has its
  own transaction; this is not a global database-plus-files atomic backup.
- `database/racial-support/`: current templates for racial summons, gameobjects, created items,
  teleport destinations, spell conditions and disables. Existing stock database content remains
  a prerequisite.
- `database/characters-schema-reference.sql`: character table structure only, including appearance
  persistence fields. No character/account database contents were dumped.
- `drakkin-drakonid/`: focused current database rows and race indexes for IDs **66, 67, 69, 70**.
  Male Drakkin Running Wild spells **110050/110051** are included alongside the dragon racials.
- `source/`: current C++/Lua implementations and integration files at their repository paths.
  Includes the racial module and loader, Worgoblin/Broken/Running Wild logic, donor removal,
  SharedDefines, RaceMgr, creation/load/save handlers, appearance headers, DBC loaders and bot
  integration. Source includes existing uncommitted work; capture metadata records the Git state.
- `historical-sql/`: verbatim original migrations, separated from current live data. Includes the
  race installations, later options, racial definitions and Tarasek male Drakkin migrations.
- `reference-tools/`: existing racial/race generator scripts with their local Python import
  dependencies and the Spell SQL schema used by their field parser. Some tools also do client
  work and require external tools/assets and workstation paths; they were copied, not executed.
- `metadata/`: provenance, source revision, mounted paths, table counts, race coverage, relevant
  runtime settings, extraction findings, integrity receipt and SHA-256 inventory.

## Using this export

Keep this folder as the server-side source/data handoff. It is based on Esteria's custom
AzerothCore 3.3.5a core and a matching stock world database. It is not an automatic standalone
installer for an arbitrary stock core. Follow the existing file paths when reviewing or merging
the implementation into another checkout; custom race identity, legacy masks, scripts and SQL
must stay aligned. Client models, textures, MPQs, GlueXML and native client DLLs are outside this
server export and remain necessary for clients to display these races correctly.

The shared world dump contains **whole tables**, including ordinary class starting spells and
other existing overrides. Review and merge it into a compatible target. Do not blindly import
it over another populated server. The focused Drakkin/Drakonid dumps narrow the race-ID rows;
shared Human/Orc mask grants, languages, skills and common dependencies stay in the shared data.
Original migrations in `historical-sql/` are historical evidence, not a replay order. In particular,
GUID-specific character appearance migrations belong to this installation and must not be replayed
against unrelated characters. The character schema is reference material, not a character migration.

The per-race indexes distinguish explicit script grants, additional source racials and candidates
from starting spells/racial skill lines. Candidates may be class-dependent, later stripped by a
script or stale in existing data; the actual copied scripts and full tables govern runtime behavior.
`racial-spell-records.json` contains 314 existing racial and triggered spell records, including
shared/hidden effects. For DBC-backed records, field types are decoded from the matching schema;
SQL override records take precedence. Existing invalid localized string offsets are preserved as
`invalid_string_offset` values in the JSON and listed in metadata; original DBC bytes are untouched.
References to missing old spells/templates are preserved rather than invented or repaired.

## Integrity

Run `python verify.py` in this folder. The manifest covers every delivered file except itself
and its receipt. The extraction also compares copied DBC hashes against the running container
and counts dumped INSERT rows against the captured table counts. These checks validate the
extraction; they do not certify racial gameplay or install this package anywhere.
