# Cosmetic Wings on Character Select Complete Reference

Prepared for EsteriaWoW on October 21 2026

We made cosmetic wings visible on Character Select by sending the saved wing aura with the character roster and attaching the corresponding model to the character preview through `EsteriaAppearance.dll`.

This document includes the full explanation, the complete contents of all five source files linked in the preceding explanation, supporting build and test files, and the original deployment record. The source appendices are current checkout snapshots taken during document creation. The deployment record describes the October 5 implementation and is historical evidence, not a statement of current deployment status. Full source files include unrelated and later features; they are not a minimal standalone patch.

## Contents

- [How it works](#how-it-works)
- [Server selection and packet layout](#server-selection-and-packet-layout)
- [Client catalog format](#client-catalog-format)
- [Native rendering and cleanup](#native-rendering-and-cleanup)
- [Preparation and deployment](#preparation-and-deployment)
- [Verification and historical results](#verification-and-historical-results)
- [Source inventory](#source-inventory)
- [Focused source extracts](#focused-source-extracts)
- [Complete source appendices](#complete-source-appendices)
- [Original deployment record](#original-deployment-record)

## How it works

The normal WotLK `SMSG_CHAR_ENUM` packet supplies the character list, appearance, and equipment data. It does not supply the character's active aura state. Our wing cosmetics are persistent self-applied aura spells, so displaying the equipped wing before login required an additional path from saved aura state to the preview renderer.

The complete flow is:

```text
Saved character_aura row
    -> account-scoped permanent aura query
    -> filter by exclusive wing group 9100
    -> SMSG_CHAR_ENUM custom CWG1 trailer
    -> native roster hook stores GUID -> wing spell
    -> selected character GUID resolves its wing
    -> EsteriaCosmeticWings.bin resolves model and scale
    -> child scene model attaches to the preview at back attachment 16
```

Knowing a wing spell does not equip it. The saved active aura determines the selection. Spell group 9100 identifies the equipped wing independently of Cosmetics skill ownership; the server source notes that the Cosmetics skill mapping is intentionally absent for classless characters.

The client feature reused the existing native roster, preview, geometry refresh, and component teardown hooks. The wing implementation needed an updated native helper, a generated wing catalog, and the server roster change. It did not require an additional executable patch, database schema migration, or replacement MPQ. A fresh installation elsewhere still needs the preexisting native appearance hook foundation and the wing assets and DBC data that this feature consumes.

## Server selection and packet layout

`CHAR_SEL_ENUM_PERMANENT_AURAS` reads the account's non-deleted characters and their saved auras. It requires `a.casterGuid = a.guid` and `a.remainTime = -1`, giving permanent self-applied auras. `HandleCharEnum()` then retains spells that belong to `SpellGroup(9100)`.

The existing character serialization remains responsible for ordinary appearance and equipment. For characters successfully added to the roster, the server writes the selected wing's raw player GUID and spell ID to an extra block. The wire layout is:

| Field | Size | Meaning |
| --- | --- | --- |
| Character GUID | 8 bytes per record | Raw player GUID |
| Wing spell ID | 4 bytes per record | Saved equipped wing aura |
| Record count | 4 bytes after all records | Number of GUID and spell pairs |
| Magic | 4 bytes at the end | ASCII `CWG1`, integer `0x31475743` |

The fields use the client's little-endian representation. The block is `12 * count + 8` bytes. It is appended only when at least one roster character has a matching saved wing. In the original implementation, it followed the HXE1 and HXE2 appearance extensions. The current server snapshot also contains subsequent body shape and Retail look extensions; its complete packet construction is preserved below.

`EsteriaEnumExtra()` clears the earlier wing roster, recognizes the CWG1 trailer, validates its count and bounds, caches each GUID and spell pair, and reduces the packet length before the stock parser runs. Its wing-aware parser also recognizes HXE1 and HXE2 and uses record strides of 12, 9, and 16 bytes respectively. An empty fresh wing roster therefore clears an earlier equipped selection rather than leaving stale wings attached.

`EsteriaSelectExtra()` finds the preview's roster row, reads its GUID, sets the preview's wing selection from that map, and calls `UpdateCosmeticWing()`. That wing handling precedes the extended-race-specific branch, so it is not restricted to a particular custom race.

## Client catalog format

`tools/cosmetic_wings_character_select.py` resolves Cosmetics skill line **779** through the installed client data:

```text
SkillLineAbility -> Spell -> SpellVisual state kit
    -> SpellVisualKitModelAttach with attachment 16
    -> SpellVisualEffectName model path and scale
```

The tool reads the effective data from the configured root and enUS creator archives and applicable WXL manifest entries. The source deliberately keeps the baked `SpellVisualEffectName` and `SpellVisualKitModelAttach` tables out of the WXL overlay merge. It checks model availability, rejects unsupported attachment transforms, validates paths and scales, checks that server group 9100 has client catalog coverage, and checks returned server spell visual identities against the client values.

The generated `EsteriaCosmeticWings.bin` has this little-endian layout:

| Field | Size | Meaning |
| --- | --- | --- |
| Magic | 4 bytes | `0x31475743`, ASCII CWG1 |
| Version | 4 bytes | 1 |
| Record count | 4 bytes | Number of wing definitions |
| Spell ID | 4 bytes per record | Catalog lookup key |
| Attachment ID | 4 bytes per record | 16 |
| Scale | 4 bytes per record | Floating point scale |
| Model path | 260 bytes per record | NUL-terminated ASCII path |

The header is 12 bytes and each definition is 272 bytes. The Python writer uses `<3I` for the header and `<IIf260s` for records. The C++ reader checks the magic, version, count limit of 4096, nonzero spell ID, attachment 16, a finite positive scale no greater than 100, a nonempty terminated path, and exact end of file. A missing or invalid catalog yields no definitions.

The historical preparation resolved **205 client wing visuals** and verified **201 server wing spells**. Four ribbon-only Alas Wings records were intentionally excluded from the server exclusive wing group. These are historical preparation counts, not a regenerated catalog inventory for today.

## Native rendering and cleanup

`CosmeticWings.inl` maintains three maps: the roster GUID to spell map, the preview character component to selected spell map, and the preview component to bound child model map.

`UpdateCosmeticWing()` looks up the selected spell in the catalog and obtains the preview parent model from the character component. If the correct wing is already attached to that same parent, it returns without creating a duplicate. If the spell or parent changed, it forgets the old child first. When no catalog entry exists, the parent is not ready, the attachment is unavailable, or no scene exists, it returns without attaching a wing.

For a valid ready preview, it creates the child model in the parent's scene, initializes its animation, applies zero origin and the catalog scale, then attaches it to **back attachment 16**. It checks that attachment succeeded before retaining the child. `EsteriaGeometry()` calls this updater on subsequent preview refreshes, allowing the wing to recover when loading or stock model refresh changes the parent.

The helper retains its own child reference because a stock component refresh may already have detached that child. `ForgetCosmeticWing()` checks whether it is still attached, detaches that specific child if needed, releases its retained reference, and removes the binding. `EsteriaForgetCharacter()` also removes the selected spell state. This lifecycle handles wing replacement, aura removal, character switching and component teardown without detaching normal equipment.

The current implementation uses the following native addresses through its existing address resolver. These addresses are specific to the supported client ABI and require verification when porting to another executable.

| Address | Use in this implementation |
| --- | --- |
| `0x008273D0` | Check that the parent supports the attachment |
| `0x0081F8F0` | Create the child scene model |
| `0x00832AB0` | Initialize the child animation |
| `0x008251D0` | Set origin rotation and scale |
| `0x00831630` | Attach the child to the parent |
| `0x008274F0` | Detach this child if still attached |
| `0x00824ED0` | Release the retained child reference |

The preparation script fingerprints the create, attach, detach and release entry points and requires the existing `ESTERIA_APPEARANCE_NATIVE_V1` marker in the executable. It is not a universal hook installer.

## Preparation and deployment

The repository README describes this sequence. Commands are included as reference only and were not executed while preparing this document.

1. Prepare the catalog with `python tools/cosmetic_wings_character_select.py prepare`.
2. Build the native helper with `client-customization/build-native.bat`, using a short staging directory such as `C:\Users\Zach\.codex\tmp\wings-select` and satisfying the current build script's arguments and prerequisites. Its full current contents are included below.
3. Keep neighboring appearance catalogs beside the staged test executables. The preparation tool copies those catalogs and verifies their hashes.
4. Close WoW and Eclipse before using the preparation tool's `install` command. Installation writes the helper and catalog and keeps verified rollback copies.
5. Install the compatible client helper before switching to the server build that sends the custom roster extension.
6. After an explicitly authorized server build, recreate only the rebuilt worldserver service as appropriate for the deployment.

The documented worldserver recreate command is:

```powershell
docker compose up -d --no-deps --no-build --pull never --force-recreate ac-worldserver
```

Original rollout details, including its backup directory, image hash, rollback tag, migration setting, and protocol SDK fixture fix, are retained verbatim in the deployment-record appendix. They describe that rollout and must not be treated as current installed artifact identities.

## Verification and historical results

The source includes three complementary checks:

- Python catalog tests: `python -m unittest discover -s tools -p test_cosmetic_wings_character_select.py`.
- Native helper tests in `TestCosmeticWings.cpp`, covering mixed appearance trailers, character isolation, repeat renders, parent refresh, removal, delayed loading and teardown.
- The protocol test `TestSession_CosmeticWingCharacterSelect`, which follows real casts, replacement and cancellation through logout and the returned character roster.

The original deployment record reports passing native checks and this live protocol progression:

```text
No wing -> spell 970340 -> spell 970388 -> no wing after cancellation and logout
```

That protocol result verifies saved selection and roster state. The original record explicitly left fresh graphical-client acceptance outstanding for wing placement and scale, custom races and genders, repeated character switches, logout, and clean client exit or restart. No build, test, installation, or graphical client check was performed to create this document.

## Source inventory

The following files are embedded in full. SHA256 values cover the original bytes read from the checkout. Code blocks preserve source text with line endings normalized to LF. Line counts refer to the source files, not this combined document.

| Appendix | Source | Lines | SHA256 |
| --- | --- | ---: | --- |
| 1 | `src/server/database/Database/Implementation/CharacterDatabase.cpp` | 760 | `e946933b156c9b3f84094d29bff4f178912d8b3cde1cf94e4f03476672dd2667` |
| 2 | `src/server/game/Handlers/CharacterHandler.cpp` | 3063 | `87e64a388b83e27c36d5593de56e92b1bfa04bdb1c042a2331c1e7555288e0d4` |
| 3 | `client-customization/NativeAppearance.cpp` | 1803 | `fff71c5632369aceb4d183c809339645e162c48437274cb6bfb3b354ce0f4c22` |
| 4 | `tools/cosmetic_wings_character_select.py` | 198 | `e4e79d1cec59a192e7f5f41abbce02e3795ccb58bb55711d8d01a1cd77436fe6` |
| 5 | `client-customization/CosmeticWings.inl` | 104 | `5e7807b1d659d129588fbf41bc2ca55184bd2e3fcfb45406accda0ff87bb556f` |
| 6 | `client-customization/TestCosmeticWings.cpp` | 232 | `459e02cda01e54efe0121b96867e2e17731c380bc2fe2b258e421c8e9b42b7ae` |
| 7 | `tools/test_cosmetic_wings_character_select.py` | 45 | `6ea95b162ef43380be644620654dc2652c8cef953b87bcdc49b81ebb7293f7f0` |
| 8 | `e2e/suites/protocol/session/cosmetic_wings_e2e_test.go` | 85 | `d415d00c7f836e32cf6b15be4f1acc94d3c0e6a72a7c6fd00af03018532a1515` |
| 9 | `client-customization/build-native.bat` | 33 | `21fff47bf277b00cba40a18c94a2885bf2c64c4e8ed0a1a3f067b86f0591005e` |
| 10 | `client-customization/NativeAppearance.def` | 22 | `5f8cbf53f06d944b29950dde1008ab0c9fc13fcf55328ad87503240f497de6a8` |

## Focused source extracts

These numbered extracts locate the central implementation within the full source appendices. The numbers are original source line numbers.

### src/server/database/Database/Implementation/CharacterDatabase.cpp lines 58 through 61

```text
  58      PrepareStatement(CHAR_SEL_ENUM_PERMANENT_AURAS, "SELECT a.guid, a.spell FROM character_aura AS a "
  59                       "JOIN characters AS c ON c.guid = a.guid WHERE c.account = ? "
  60                       "AND c.deleteInfos_Name IS NULL AND a.casterGuid = a.guid AND a.remainTime = -1 "
  61                       "ORDER BY a.guid, a.spell", CONNECTION_ASYNC);
```

### src/server/game/Handlers/CharacterHandler.cpp lines 272 through 284

```text
 272      }
 273      // Cosmetics' server skill mapping is intentionally absent for classless characters.
 274      // The existing exclusive wing group identifies equipped wings without changing spell ownership.
 275      std::unordered_map<uint32, uint32> wings;
 276      if (permanentAuras)
 277      {
 278          do
 279          {
 280              uint32 spell = (*permanentAuras)[1].Get<uint32>();
 281              if (sSpellMgr->IsSpellMemberOfSpellGroup(spell, SpellGroup(9100)))
 282                  wings[(*permanentAuras)[0].Get<uint32>()] = spell;
 283          } while (permanentAuras->NextRow());
 284      }
```

### src/server/game/Handlers/CharacterHandler.cpp lines 309 through 317

```text
 309              if (Player::BuildEnumData(result, &data))
 310              {
 311                  _legitCharacters.insert(guid);
 312                  ++num;
 313                  if (auto wing = wings.find((*result)[0].Get<uint32>()); wing != wings.end())
 314                  {
 315                      cosmeticWings << guid.GetRawValue() << wing->second;
 316                      ++wingCount;
 317                  }
```

### src/server/game/Handlers/CharacterHandler.cpp lines 358 through 362

```text
 358      if (wingCount)
 359      {
 360          data.append(cosmeticWings);
 361          data << wingCount << uint32(0x31475743); // CWG1: GUID + active wing spell, stripped before stock parsing.
 362      }
```

### client-customization/NativeAppearance.cpp lines 1489 through 1542

```text
1489  extern "C" __declspec(dllexport) void __cdecl EsteriaEnumExtra(void* packet)
1490  {
1491      highmountainRoster.clear();
1492      cosmeticWingRoster.clear();
1493      if (!packet)
1494          return;
1495      unsigned length = Field<unsigned>(packet, 0x10);
1496      unsigned base = Field<unsigned>(packet, 8);
1497      if (length < base || length - base < 8 || length - base > Field<unsigned>(packet, 0x0C))
1498          return;
1499      auto* bytes = Field<unsigned char*>(packet, 4);
1500      unsigned size = length - base;
1501      if (!bytes)
1502          return;
1503      for (unsigned tail = 0; tail < 3 && size >= 8; ++tail)
1504      {
1505          unsigned magic = Field<unsigned>(bytes, size - 4);
1506          unsigned stride = magic == 0x31455848 ? 9 : magic == 0x32455848 ? 16 : magic == 0x31475743 ? 12 : 0;
1507          if (!stride)
1508              break;
1509          unsigned count = Field<unsigned>(bytes, size - 8);
1510          if (count > 100 || count > (size - 8) / stride)
1511              break;
1512          unsigned start = size - 8 - count * stride;
1513          for (unsigned i = 0; i < count; ++i)
1514          {
1515              auto guid = Field<std::uint64_t>(bytes, start + i * stride);
1516              if (stride == 12)
1517                  cosmeticWingRoster[guid] = Field<unsigned>(bytes, start + i * stride + 8);
1518              else
1519                  highmountainRoster[guid] = stride == 9
1520                      ? bytes[start + i * stride + 8] : Field<std::uint64_t>(bytes, start + i * stride + 8);
1521          }
1522          size = start;
1523          Field<unsigned>(packet, 0x10) = base + size;
1524      }
1525  }
1526  
1527  extern "C" __declspec(dllexport) void __cdecl EsteriaSelectExtra(void* character)
1528  {
1529      if (!character)
1530          return;
1531      unsigned count = *reinterpret_cast<unsigned*>(Address(0x00B6B23C));
1532      auto* rows = *reinterpret_cast<unsigned char**>(Address(0x00B6B240));
1533      if (!rows || count > 100)
1534          return;
1535      for (unsigned i = 0; i < count; ++i)
1536      {
1537          auto* row = rows + i * 0x198;
1538          if (Field<void*>(row, 0x188) != character)
1539              continue;
1540          auto wing = cosmeticWingRoster.find(Field<std::uint64_t>(row, 0));
1541          cosmeticWingSelections[character] = wing == cosmeticWingRoster.end() ? 0 : wing->second;
1542          UpdateCosmeticWing(character);
```

### client-customization/CosmeticWings.inl lines 51 through 103

```text
  51      void ForgetCosmeticWing(void* character)
  52      {
  53          auto it = boundCosmeticWings.find(character);
  54          if (it == boundCosmeticWings.end())
  55              return;
  56          void* wing = it->second.instance;
  57          // Retain our own reference: a stock component refresh may already have detached the child.
  58          if (Field<void*>(wing, 0x48))
  59              Native<void(__thiscall*)(void*)>(0x008274F0)(wing);
  60          Native<void(__thiscall*)(void*)>(0x00824ED0)(wing);
  61          boundCosmeticWings.erase(it);
  62      }
  63  
  64      void UpdateCosmeticWing(void* character)
  65      {
  66          auto selected = cosmeticWingSelections.find(character);
  67          unsigned spell = selected == cosmeticWingSelections.end() ? 0 : selected->second;
  68          auto const& catalog = CosmeticWings();
  69          auto definition = std::find_if(catalog.begin(), catalog.end(),
  70              [spell](CosmeticWing const& wing) { return wing.spell == spell; });
  71          void* parent = Field<void*>(character, 0x38);
  72          auto bound = boundCosmeticWings.find(character);
  73          if (bound != boundCosmeticWings.end())
  74          {
  75              if (definition != catalog.end() && bound->second.spell == spell
  76                  && parent && Field<void*>(bound->second.instance, 0x48) == parent)
  77                  return;
  78              ForgetCosmeticWing(character);
  79          }
  80          if (definition == catalog.end() || !parent || !(Field<unsigned>(parent, 0x10) & 1)
  81              || !Native<int(__thiscall*)(void*, unsigned)>(0x008273D0)(parent, definition->attachment))
  82              return;
  83          void* scene = Field<void*>(parent, 0x28);
  84          if (!scene)
  85              return;
  86          void* child = Native<void*(__thiscall*)(void*, char const*, unsigned)>(0x0081F8F0)(
  87              scene, definition->model, 0);
  88          if (!child)
  89              return;
  90          Native<void(__thiscall*)(void*, int, int, int, int, float, int, int)>(0x00832AB0)(
  91              child, -1, 0, -1, 0, 1.0f, 1, 1);
  92          float origin[3]{};
  93          Native<void(__thiscall*)(void*, float const*, float, float)>(0x008251D0)(
  94              child, origin, 0, definition->scale);
  95          Native<void(__thiscall*)(void*, void*, unsigned, void*, int)>(0x00831630)(
  96              child, parent, definition->attachment, nullptr, 0);
  97          if (Field<void*>(child, 0x48) != parent)
  98          {
  99              Native<void(__thiscall*)(void*)>(0x00824ED0)(child);
 100              return;
 101          }
 102          boundCosmeticWings[character] = {child, spell};
 103      }
```

### Repository operational notes

Source: `client-customization/README.md`, section Cosmetic wings on Character Select.

#### Cosmetic wings on Character Select

`CosmeticWings.inl` reuses the installed native roster, preview and component teardown hooks.
Worldserver reads saved infinite self-applied auras and sends only members of wing group 9100 in a
`CWG1` trailer (GUID plus spell ID). The native helper strips it before stock parsing, alongside
`HXE1` and `HXE2`. Knowing a wing spell without its aura does not equip it.

`tools/cosmetic_wings_character_select.py prepare` resolves Cosmetics skill line 779 through the
installed Spell/SpellVisual state kit and back attachment 16 into `EsteriaCosmeticWings.bin`. It
checks server visual agreement, model presence, scales and native attachment fingerprints.
The helper retains an independent child reference across stock preview refreshes, detaches only
its own wing, and releases that reference when the character component is destroyed.
No schema migration, executable patch or MPQ replacement is required.

After explicit build authorization, prepare the catalog, then use `client-customization/build-native.bat`
with `C:\Users\Zach\.codex\tmp\wings-select` as its output directory.
The build runs the existing native checks and the new `TestCosmeticWings.exe` when the catalog exists.
Close WoW/Eclipse and run the preparation tool with `install` to install the DLL and catalog with
hash-verified rollback copies. Install the client helper before recreating the rebuilt
`ac-worldserver` with `docker compose up -d --no-deps --no-build --pull never --force-recreate ac-worldserver`.

Verification: `python -m unittest discover -s tools -p test_cosmetic_wings_character_select.py`;
`TestCosmeticWings.exe` checks mixed trailers, character isolation, repeat renders, parent refresh,
removal, delayed loading and teardown. The live protocol case is
`TestSession_CosmeticWingCharacterSelect` in `e2e/suites/protocol/session/`.
Its oracle follows real casts and cancellation through logout and the returned roster trailer.
Live visual acceptance still requires a fresh client: wing/no-wing characters, changing wings,
removing an aura, repeated character switches, custom races of both genders, and logout/client exit.


## Complete source appendices

### Appendix 1 CharacterDatabase.cpp

Originally linked database query source.

Source: `src/server/database/Database/Implementation/CharacterDatabase.cpp`  
Absolute path: `R:\Users\Zach\Documents\GitHub\EsteriaWoW\src\server\database\Database\Implementation\CharacterDatabase.cpp`  
Source lines: 1 through 760  
SHA256: `e946933b156c9b3f84094d29bff4f178912d8b3cde1cf94e4f03476672dd2667`

<!-- BEGIN FULL SOURCE 1 -->
````cpp
/*
 * This file is part of the AzerothCore Project. See AUTHORS file for Copyright information
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful, but WITHOUT
 * ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
 * FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for
 * more details.
 *
 * You should have received a copy of the GNU General Public License along
 * with this program. If not, see <http://www.gnu.org/licenses/>.
 */

#include "CharacterDatabase.h"
#include "MySQLPreparedStatement.h"

void CharacterDatabaseConnection::DoPrepareStatements()
{
    if (!m_reconnecting)
        m_stmts.resize(MAX_CHARACTERDATABASE_STATEMENTS);

    PrepareStatement(CHAR_DEL_QUEST_POOL_SAVE, "DELETE FROM pool_quest_save WHERE pool_id = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_INS_QUEST_POOL_SAVE, "INSERT INTO pool_quest_save (pool_id, quest_id) VALUES (?, ?)", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_NONEXISTENT_GUILD_BANK_ITEM, "DELETE FROM guild_bank_item WHERE guildid = ? AND TabId = ? AND SlotId = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_EXPIRED_BANS, "UPDATE character_banned SET active = 0 WHERE unbandate <= UNIX_TIMESTAMP() AND unbandate <> bandate", CONNECTION_ASYNC);
    PrepareStatement(CHAR_SEL_DATA_BY_NAME, "SELECT guid, account, name, gender, race, class, level FROM characters WHERE deleteDate IS NULL AND name = ?", CONNECTION_BOTH);
    PrepareStatement(CHAR_SEL_DATA_BY_GUID, "SELECT guid, account, name, gender, race, class, level FROM characters WHERE deleteDate IS NULL AND guid = ?", CONNECTION_BOTH);
    PrepareStatement(CHAR_SEL_CHECK_NAME, "SELECT 1 FROM characters WHERE name = ?", CONNECTION_BOTH);
    PrepareStatement(CHAR_SEL_CHECK_GUID, "SELECT 1 FROM characters WHERE guid = ?", CONNECTION_SYNCH);
    PrepareStatement(CHAR_SEL_SUM_CHARS, "SELECT COUNT(guid) FROM characters WHERE account = ?", CONNECTION_BOTH);
    PrepareStatement(CHAR_SEL_CHAR_CREATE_INFO, "SELECT level, race, class FROM characters WHERE account = ? LIMIT 0, ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_INS_CHARACTER_BAN, "INSERT INTO character_banned VALUES (?, UNIX_TIMESTAMP(), UNIX_TIMESTAMP()+?, ?, ?, 1)", CONNECTION_ASYNC);
    PrepareStatement(CHAR_UPD_CHARACTER_BAN, "UPDATE character_banned SET active = 0 WHERE guid = ? AND active != 0", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_CHARACTER_BAN, "DELETE cb FROM character_banned cb INNER JOIN characters c ON c.guid = cb.guid WHERE c.account = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_SEL_BANINFO, "SELECT FROM_UNIXTIME(bandate, '%Y-%m-%d %H:%i:%s'), unbandate-bandate, active, unbandate, banreason, bannedby FROM character_banned WHERE guid = ? ORDER BY bandate ASC", CONNECTION_SYNCH);
    PrepareStatement(CHAR_SEL_GUID_BY_NAME_FILTER, "SELECT guid, name FROM characters WHERE name LIKE CONCAT('%%', ?, '%%')", CONNECTION_SYNCH);
    PrepareStatement(CHAR_SEL_BANINFO_LIST, "SELECT bandate, unbandate, bannedby, banreason FROM character_banned WHERE guid = ? ORDER BY unbandate", CONNECTION_SYNCH);
    PrepareStatement(CHAR_SEL_BANNED_NAME, "SELECT characters.name FROM characters, character_banned WHERE character_banned.guid = ? AND character_banned.guid = characters.guid", CONNECTION_SYNCH);
    PrepareStatement(CHAR_SEL_ENUM, "SELECT c.guid, c.name, c.race, c.class, c.gender, c.skin, c.face, c.hairStyle, c.hairColor, c.facialStyle, c.level, c.zone, c.map, c.position_x, c.position_y, c.position_z, "
                     "gm.guildid, c.playerFlags, c.at_login, cp.entry, cp.modelid, cp.level, "
                     "c.equipmentCache, cb.guid, c.extra_flags, c.extraAppearance, c.teamId "
                     "FROM characters AS c LEFT JOIN character_pet AS cp ON c.guid = cp.owner "
                     "AND cp.slot = ? "
                     "LEFT JOIN guild_member AS gm ON c.guid = gm.guid "
                     "LEFT JOIN character_banned AS cb ON c.guid = cb.guid AND cb.active = 1 WHERE c.account = ? AND c.deleteInfos_Name IS NULL ORDER BY COALESCE(c.order, c.guid)", CONNECTION_ASYNC);
    PrepareStatement(CHAR_SEL_ENUM_DECLINED_NAME, "SELECT c.guid, c.name, c.race, c.class, c.gender, c.skin, c.face, c.hairStyle, c.hairColor, c.facialStyle, c.level, c.zone, c.map, "
                     "c.position_x, c.position_y, c.position_z, gm.guildid, c.playerFlags, c.at_login, cp.entry, cp.modelid, cp.level, c.equipmentCache, "
                     "cb.guid, c.extra_flags, cd.genitive, c.extraAppearance, c.teamId "
                     "FROM characters AS c LEFT JOIN character_pet AS cp ON c.guid = cp.owner "
                     "AND cp.slot = ? "
                     "LEFT JOIN character_declinedname AS cd ON c.guid = cd.guid LEFT JOIN guild_member AS gm ON c.guid = gm.guid "
                     "LEFT JOIN character_banned AS cb ON c.guid = cb.guid AND cb.active = 1 WHERE c.account = ? AND c.deleteInfos_Name IS NULL ORDER BY COALESCE(c.order, c.guid)", CONNECTION_ASYNC);
    PrepareStatement(CHAR_SEL_FREE_NAME, "SELECT guid, name, at_login FROM characters WHERE guid = ? AND account = ? AND NOT EXISTS (SELECT NULL FROM characters WHERE name = ?)", CONNECTION_ASYNC);
    PrepareStatement(CHAR_SEL_ENUM_PERMANENT_AURAS, "SELECT a.guid, a.spell FROM character_aura AS a "
                     "JOIN characters AS c ON c.guid = a.guid WHERE c.account = ? "
                     "AND c.deleteInfos_Name IS NULL AND a.casterGuid = a.guid AND a.remainTime = -1 "
                     "ORDER BY a.guid, a.spell", CONNECTION_ASYNC);
    PrepareStatement(CHAR_SEL_CHAR_ZONE, "SELECT zone FROM characters WHERE guid = ?", CONNECTION_SYNCH);
    PrepareStatement(CHAR_SEL_CHARACTER_NAME_DATA,
                     "SELECT race, class, gender, level, teamId FROM characters WHERE guid = ?", CONNECTION_SYNCH);
    PrepareStatement(CHAR_SEL_CHAR_POSITION_XYZ, "SELECT map, position_x, position_y, position_z FROM characters WHERE guid = ?", CONNECTION_SYNCH);
    PrepareStatement(CHAR_SEL_CHAR_POSITION, "SELECT position_x, position_y, position_z, orientation, map, taxi_path FROM characters WHERE guid = ?", CONNECTION_SYNCH);
    PrepareStatement(CHAR_DEL_QUEST_STATUS_DAILY, "DELETE FROM character_queststatus_daily", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_QUEST_STATUS_WEEKLY, "DELETE FROM character_queststatus_weekly", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_QUEST_STATUS_MONTHLY, "DELETE FROM character_queststatus_monthly", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_QUEST_STATUS_SEASONAL, "DELETE FROM character_queststatus_seasonal WHERE event = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_QUEST_STATUS_DAILY_CHAR, "DELETE FROM character_queststatus_daily WHERE guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_QUEST_STATUS_WEEKLY_CHAR, "DELETE FROM character_queststatus_weekly WHERE guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_QUEST_STATUS_MONTHLY_CHAR, "DELETE FROM character_queststatus_monthly WHERE guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_QUEST_STATUS_SEASONAL_CHAR, "DELETE FROM character_queststatus_seasonal WHERE guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_BATTLEGROUND_RANDOM, "DELETE FROM character_battleground_random", CONNECTION_ASYNC);
    PrepareStatement(CHAR_INS_BATTLEGROUND_RANDOM, "INSERT INTO character_battleground_random (guid) VALUES (?)", CONNECTION_ASYNC);

    // Start LoginQueryHolder content
    PrepareStatement(CHAR_SEL_CHARACTER, "SELECT guid, account, name, race, class, gender, level, xp, money, skin, face, hairStyle, hairColor, facialStyle, bankSlots, restState, playerFlags, "
                     "position_x, position_y, position_z, map, orientation, taximask, cinematic, totaltime, leveltime, rest_bonus, logout_time, is_logout_resting, resettalents_cost, "
                     "resettalents_time, trans_x, trans_y, trans_z, trans_o, transguid, extra_flags, stable_slots, at_login, zone, online, death_expire_time, taxi_path, instance_mode_mask, "
                     "arenaPoints, totalHonorPoints, todayHonorPoints, yesterdayHonorPoints, totalKills, todayKills, yesterdayKills, chosenTitle, knownCurrencies, watchedFaction, drunk, "
                     "health, power1, power2, power3, power4, power5, power6, power7, instance_id, talentGroupsCount, activeTalentGroup, exploredZones, equipmentCache, ammoId, "
                     "knownTitles, actionBars, grantableLevels, innTriggerId, extraBonusTalentCount, "
                     "UNIX_TIMESTAMP(creation_date), "
                     "teamId, extraAppearance FROM characters WHERE guid = ?", CONNECTION_ASYNC);

    PrepareStatement(CHAR_UPD_EXTENDED_APPEARANCE,
        "UPDATE characters SET extraAppearance = ? WHERE guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_SEL_ENUM_BODY_SHAPE,
        "SELECT b.guid, b.data FROM character_body_shape AS b JOIN characters AS c ON c.guid = b.guid "
        "WHERE c.account = ? AND c.deleteInfos_Name IS NULL", CONNECTION_ASYNC);
    PrepareStatement(CHAR_SEL_ENUM_RETAIL_LOOK,
        "SELECT l.guid, l.data FROM character_retail_look AS l JOIN characters AS c ON c.guid = l.guid "
        "WHERE c.account = ? AND c.deleteInfos_Name IS NULL", CONNECTION_ASYNC);
    PrepareStatement(CHAR_SEL_RETAIL_LOOK,
        "SELECT data FROM character_retail_look WHERE guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_REP_RETAIL_LOOK,
        "REPLACE INTO character_retail_look (guid, data) VALUES (?, ?)", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_RETAIL_LOOK,
        "DELETE FROM character_retail_look WHERE guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_SEL_BODY_SHAPE,
        "SELECT data FROM character_body_shape WHERE guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_REP_BODY_SHAPE,
        "REPLACE INTO character_body_shape (guid, data) VALUES (?, ?)", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_BODY_SHAPE,
        "DELETE FROM character_body_shape WHERE guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_UPD_EYE_LIGHTNING,
        "UPDATE characters SET extraAppearance = (extraAppearance & 9223372036854775807) | ? WHERE guid = ?",
        CONNECTION_ASYNC);

    PrepareStatement(CHAR_SEL_CHARACTER_AURAS, "SELECT casterGuid, itemGuid, spell, effectMask, recalculateMask, stackCount, amount0, amount1, amount2, "
                     "base_amount0, base_amount1, base_amount2, maxDuration, remainTime, remainCharges FROM character_aura WHERE guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_SEL_CHARACTER_SPELL, "SELECT spell, specMask FROM character_spell WHERE guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_SEL_CHARACTER_QUESTSTATUS, "SELECT quest, status, explored, timer, mobcount1, mobcount2, mobcount3, mobcount4, "
                     "itemcount1, itemcount2, itemcount3, itemcount4, itemcount5, itemcount6, playercount FROM character_queststatus WHERE guid = ? AND status <> 0", CONNECTION_ASYNC);
    PrepareStatement(CHAR_SEL_CHARACTER_DAILYQUESTSTATUS, "SELECT quest, time FROM character_queststatus_daily WHERE guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_SEL_CHARACTER_WEEKLYQUESTSTATUS, "SELECT quest FROM character_queststatus_weekly WHERE guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_SEL_CHARACTER_MONTHLYQUESTSTATUS, "SELECT quest FROM character_queststatus_monthly WHERE guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_SEL_CHARACTER_SEASONALQUESTSTATUS, "SELECT quest, event FROM character_queststatus_seasonal WHERE guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_INS_CHARACTER_DAILYQUESTSTATUS, "INSERT INTO character_queststatus_daily (guid, quest, time) VALUES (?, ?, ?)", CONNECTION_ASYNC);
    PrepareStatement(CHAR_INS_CHARACTER_WEEKLYQUESTSTATUS, "INSERT INTO character_queststatus_weekly (guid, quest) VALUES (?, ?)", CONNECTION_ASYNC);
    PrepareStatement(CHAR_INS_CHARACTER_MONTHLYQUESTSTATUS, "INSERT INTO character_queststatus_monthly (guid, quest) VALUES (?, ?)", CONNECTION_ASYNC);
    PrepareStatement(CHAR_INS_CHARACTER_SEASONALQUESTSTATUS, "INSERT IGNORE INTO character_queststatus_seasonal (guid, quest, event) VALUES (?, ?, ?)", CONNECTION_ASYNC);
    PrepareStatement(CHAR_SEL_CHARACTER_REPUTATION, "SELECT faction, standing, flags FROM character_reputation WHERE guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_SEL_CHARACTER_INVENTORY, "SELECT creatorGuid, giftCreatorGuid, count, duration, charges, flags, enchantments, randomPropertyId, durability, playedTime, text, bag, slot, "
                     "item, itemEntry FROM character_inventory ci JOIN item_instance ii ON ci.item = ii.guid WHERE ci.guid = ? ORDER BY bag, slot", CONNECTION_ASYNC);
    PrepareStatement(CHAR_SEL_CHARACTER_ACTIONS, "SELECT a.button, a.action, a.type FROM character_action as a, characters as c WHERE a.guid = c.guid AND a.spec = c.activeTalentGroup AND a.guid = ? ORDER BY button", CONNECTION_ASYNC);
    PrepareStatement(CHAR_SEL_CHARACTER_MAILCOUNT_UNREAD, "SELECT COUNT(id) FROM mail WHERE receiver = ? AND (checked & 1) = 0 AND deliver_time <= ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_SEL_CHARACTER_MAILCOUNT_UNREAD_SYNCH, "SELECT COUNT(id) FROM mail WHERE receiver = ? AND (checked & 1) = 0 AND deliver_time <= ?", CONNECTION_SYNCH);
    PrepareStatement(CHAR_SEL_MAIL_SERVER_CHARACTER, "SELECT mailId from mail_server_character WHERE guid = ? and mailId = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_REP_MAIL_SERVER_CHARACTER, "REPLACE INTO mail_server_character (guid, mailId) values (?, ?)", CONNECTION_ASYNC);
    PrepareStatement(CHAR_SEL_CHARACTER_SOCIALLIST, "SELECT friend, flags, note FROM character_social JOIN characters ON characters.guid = character_social.friend WHERE character_social.guid = ? AND deleteinfos_name IS NULL LIMIT 255", CONNECTION_ASYNC);
    PrepareStatement(CHAR_SEL_CHARACTER_HOMEBIND, "SELECT mapId, zoneId, posX, posY, posZ FROM character_homebind WHERE guid = ?", CONNECTION_BOTH);
    PrepareStatement(CHAR_SEL_CHARACTER_SPELLCOOLDOWNS, "SELECT spell, category, item, time, needSend FROM character_spell_cooldown WHERE guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_SEL_CHARACTER_DECLINEDNAMES, "SELECT genitive, dative, accusative, instrumental, prepositional FROM character_declinedname WHERE guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_SEL_CHARACTER_ACHIEVEMENTS, "SELECT achievement, date FROM character_achievement WHERE guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_SEL_CHARACTER_CRITERIAPROGRESS, "SELECT criteria, counter, date FROM character_achievement_progress WHERE guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_SEL_CHARACTER_EQUIPMENTSETS, "SELECT setguid, setindex, name, iconname, ignore_mask, item0, item1, item2, item3, item4, item5, item6, item7, item8, "
                     "item9, item10, item11, item12, item13, item14, item15, item16, item17, item18 FROM character_equipmentsets WHERE guid = ? ORDER BY setindex", CONNECTION_ASYNC);
    PrepareStatement(CHAR_SEL_CHARACTER_ENTRY_POINT, "SELECT joinX, joinY, joinZ, joinO, joinMapId, taxiPath0, taxiPath1, mountSpell FROM character_entry_point WHERE guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_SEL_CHARACTER_GLYPHS, "SELECT talentGroup, glyph1, glyph2, glyph3, glyph4, glyph5, glyph6 FROM character_glyphs WHERE guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_SEL_CHARACTER_TALENTS, "SELECT spell, specMask FROM character_talent WHERE guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_SEL_CHARACTER_SKILLS, "SELECT skill, value, max FROM character_skills WHERE guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_SEL_CHARACTER_RANDOMBG, "SELECT guid FROM character_battleground_random WHERE guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_SEL_CHARACTER_BANNED, "SELECT guid FROM character_banned WHERE guid = ? AND active = 1", CONNECTION_ASYNC);
    PrepareStatement(CHAR_SEL_CHARACTER_QUESTSTATUSREW, "SELECT quest FROM character_queststatus_rewarded WHERE guid = ? AND active = 1", CONNECTION_ASYNC);
    PrepareStatement(CHAR_SEL_ACCOUNT_INSTANCELOCKTIMES, "SELECT instanceId, releaseTime FROM account_instance_times WHERE accountId = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_SEL_BREW_OF_THE_MONTH, "SELECT lastEventId FROM character_brew_of_the_month WHERE guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_REP_BREW_OF_THE_MONTH, "REPLACE INTO character_brew_of_the_month (guid, lastEventId) VALUES (?, ?)", CONNECTION_ASYNC);
    // End LoginQueryHolder content

    PrepareStatement(CHAR_SEL_CHARACTER_ACTIONS_SPEC, "SELECT button, action, type FROM character_action WHERE guid = ? AND spec = ? ORDER BY button", CONNECTION_ASYNC);
    PrepareStatement(CHAR_SEL_MAILITEMS, "SELECT creatorGuid, giftCreatorGuid, count, duration, charges, flags, enchantments, randomPropertyId, durability, playedTime, text, item_guid, itemEntry, ii.owner_guid, m.id FROM mail_items mi INNER JOIN mail m ON mi.mail_id = m.id LEFT JOIN item_instance ii ON mi.item_guid = ii.guid WHERE m.receiver = ?", CONNECTION_BOTH);
    PrepareStatement(CHAR_SEL_AUCTION_ITEMS, "SELECT creatorGuid, giftCreatorGuid, count, duration, charges, flags, enchantments, randomPropertyId, durability, playedTime, text, itemguid, itemEntry FROM auctionhouse ah JOIN item_instance ii ON ah.itemguid = ii.guid", CONNECTION_SYNCH);
    PrepareStatement(CHAR_SEL_AUCTIONS, "SELECT id, houseid, itemguid, itemEntry, count, itemowner, buyoutprice, time, buyguid, lastbid, startbid, deposit FROM auctionhouse ah INNER JOIN item_instance ii ON ii.guid = ah.itemguid", CONNECTION_SYNCH);
    PrepareStatement(CHAR_INS_AUCTION, "INSERT INTO auctionhouse (id, houseid, itemguid, itemowner, buyoutprice, time, buyguid, lastbid, startbid, deposit) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_AUCTION, "DELETE FROM auctionhouse WHERE id = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_UPD_AUCTION_BID, "UPDATE auctionhouse SET buyguid = ?, lastbid = ? WHERE id = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_INS_MAIL, "INSERT INTO mail(id, messageType, stationery, mailTemplateId, sender, receiver, subject, body, has_items, expire_time, deliver_time, money, cod, checked) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_MAIL_BY_ID, "DELETE FROM mail WHERE id = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_INS_MAIL_ITEM, "INSERT INTO mail_items(mail_id, item_guid, receiver) VALUES (?, ?, ?)", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_MAIL_ITEM, "DELETE FROM mail_items WHERE item_guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_INVALID_MAIL_ITEM, "DELETE FROM mail_items WHERE item_guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_SEL_EXPIRED_MAIL, "SELECT id, messageType, sender, receiver, has_items, expire_time, stationery, checked, mailTemplateId FROM mail WHERE expire_time < ?", CONNECTION_SYNCH);
    PrepareStatement(CHAR_SEL_EXPIRED_MAIL_ITEMS, "SELECT item_guid, itemEntry, mail_id FROM mail_items mi INNER JOIN item_instance ii ON ii.guid = mi.item_guid LEFT JOIN mail mm ON mi.mail_id = mm.id WHERE mm.id IS NOT NULL AND mm.expire_time < ?", CONNECTION_SYNCH);
    PrepareStatement(CHAR_UPD_MAIL_RETURNED, "UPDATE mail SET sender = ?, receiver = ?, expire_time = ?, deliver_time = ?, cod = 0, checked = ? WHERE id = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_UPD_MAIL_ITEM_RECEIVER, "UPDATE mail_items SET receiver = ? WHERE item_guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_UPD_ITEM_OWNER, "UPDATE item_instance SET owner_guid = ? WHERE guid = ?", CONNECTION_ASYNC);

    PrepareStatement(CHAR_SEL_ITEM_REFUNDS, "SELECT player_guid, paidMoney, paidExtendedCost FROM item_refund_instance WHERE item_guid = ? AND player_guid = ? LIMIT 1", CONNECTION_SYNCH);
    PrepareStatement(CHAR_SEL_ITEM_BOP_TRADE, "SELECT allowedPlayers FROM item_soulbound_trade_data WHERE itemGuid = ? LIMIT 1", CONNECTION_SYNCH);
    PrepareStatement(CHAR_DEL_ITEM_BOP_TRADE, "DELETE FROM item_soulbound_trade_data WHERE itemGuid = ? LIMIT 1", CONNECTION_ASYNC);
    PrepareStatement(CHAR_INS_ITEM_BOP_TRADE, "INSERT INTO item_soulbound_trade_data VALUES (?, ?)", CONNECTION_ASYNC);
    PrepareStatement(CHAR_REP_INVENTORY_ITEM, "REPLACE INTO character_inventory (guid, bag, slot, item) VALUES (?, ?, ?, ?)", CONNECTION_ASYNC);
    PrepareStatement(CHAR_REP_ITEM_INSTANCE, "REPLACE INTO item_instance (itemEntry, owner_guid, creatorGuid, giftCreatorGuid, count, duration, charges, flags, enchantments, randomPropertyId, durability, playedTime, text, guid) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", CONNECTION_ASYNC);
    PrepareStatement(CHAR_UPD_ITEM_INSTANCE, "UPDATE item_instance SET itemEntry = ?, owner_guid = ?, creatorGuid = ?, giftCreatorGuid = ?, count = ?, duration = ?, charges = ?, flags = ?, enchantments = ?, randomPropertyId = ?, durability = ?, playedTime = ?, text = ? WHERE guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_UPD_ITEM_INSTANCE_ON_LOAD, "UPDATE item_instance SET duration = ?, flags = ?, durability = ? WHERE guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_UPD_ITEM_COUNT, "UPDATE item_instance SET count = ? WHERE guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_ITEM_INSTANCE, "DELETE FROM item_instance WHERE guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_ITEM_INSTANCE_BY_OWNER, "DELETE FROM item_instance WHERE owner_guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_UPD_GIFT_OWNER, "UPDATE character_gifts SET guid = ? WHERE item_guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_GIFT, "DELETE FROM character_gifts WHERE item_guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_SEL_CHARACTER_GIFT_BY_ITEM, "SELECT entry, flags FROM character_gifts WHERE item_guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_SEL_ACCOUNT_BY_NAME, "SELECT account FROM characters WHERE name = ?", CONNECTION_SYNCH);
    PrepareStatement(CHAR_DEL_ACCOUNT_INSTANCE_LOCK_TIMES, "DELETE FROM account_instance_times WHERE accountId = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_INS_ACCOUNT_INSTANCE_LOCK_TIMES, "INSERT INTO account_instance_times (accountId, instanceId, releaseTime) VALUES (?, ?, ?)", CONNECTION_ASYNC);
    PrepareStatement(CHAR_SEL_MATCH_MAKER_RATING, "SELECT matchMakerRating, maxMMR  FROM character_arena_stats WHERE guid = ? AND slot = ?", CONNECTION_SYNCH);
    PrepareStatement(CHAR_SEL_CHARACTER_COUNT, "SELECT account, COUNT(guid) FROM characters WHERE account = ? GROUP BY account", CONNECTION_ASYNC);
    PrepareStatement(CHAR_UPD_NAME_BY_GUID, "UPDATE characters SET name = ? WHERE guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_DECLINED_NAME, "DELETE FROM character_declinedname WHERE guid = ?", CONNECTION_ASYNC);

    // Guild handling
    // 0: uint32, 1: string, 2: uint32, 3: string, 4: string, 5: uint64, 6-10: uint32, 11: uint64
    PrepareStatement(CHAR_INS_GUILD, "INSERT INTO guild (guildid, name, leaderguid, info, motd, createdate, EmblemStyle, EmblemColor, BorderStyle, BorderColor, BackgroundColor, BankMoney) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_GUILD, "DELETE FROM guild WHERE guildid = ?", CONNECTION_ASYNC); // 0: uint32
    // 0: string, 1: uint32
    PrepareStatement(CHAR_UPD_GUILD_NAME, "UPDATE guild SET name = ? WHERE guildid = ?", CONNECTION_ASYNC);
    // 0: uint32, 1: uint32, 2: uint8, 4: string, 5: string
    PrepareStatement(CHAR_INS_GUILD_MEMBER, "INSERT INTO guild_member (guildid, guid, `rank`, pnote, offnote) VALUES (?, ?, ?, ?, ?)", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_GUILD_MEMBER, "DELETE FROM guild_member WHERE guid = ?", CONNECTION_ASYNC); // 0: uint32
    PrepareStatement(CHAR_DEL_GUILD_MEMBERS, "DELETE FROM guild_member WHERE guildid = ?", CONNECTION_ASYNC); // 0: uint32
    PrepareStatement(CHAR_SEL_GUILD_MEMBER_EXTENDED, "SELECT g.guildid, g.name, gr.rname, gm.pnote, gm.offnote "
                     "FROM guild g JOIN guild_member gm ON g.guildid = gm.guildid "
                     "JOIN guild_rank gr ON g.guildid = gr.guildid AND gm.`rank` = gr.rid WHERE gm.guid = ?", CONNECTION_BOTH);
    // 0: uint32, 1: uint8, 3: string, 4: uint32, 5: uint32
    PrepareStatement(CHAR_INS_GUILD_RANK, "INSERT INTO guild_rank (guildid, rid, rname, rights, BankMoneyPerDay) VALUES (?, ?, ?, ?, ?)", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_GUILD_RANKS, "DELETE FROM guild_rank WHERE guildid = ?", CONNECTION_ASYNC); // 0: uint32
    PrepareStatement(CHAR_DEL_GUILD_LOWEST_RANK, "DELETE FROM guild_rank WHERE guildid = ? AND rid >= ?", CONNECTION_ASYNC); // 0: uint32, 1: uint8
    PrepareStatement(CHAR_INS_GUILD_BANK_TAB, "INSERT INTO guild_bank_tab (guildid, TabId) VALUES (?, ?)", CONNECTION_ASYNC); // 0: uint32, 1: uint8
    PrepareStatement(CHAR_DEL_GUILD_BANK_TAB, "DELETE FROM guild_bank_tab WHERE guildid = ? AND TabId = ?", CONNECTION_ASYNC); // 0: uint32, 1: uint8
    PrepareStatement(CHAR_DEL_GUILD_BANK_TABS, "DELETE FROM guild_bank_tab WHERE guildid = ?", CONNECTION_ASYNC); // 0: uint32
    // 0: uint32, 1: uint8, 2: uint8, 3: uint32, 4: uint32
    PrepareStatement(CHAR_INS_GUILD_BANK_ITEM, "INSERT INTO guild_bank_item (guildid, TabId, SlotId, item_guid) VALUES (?, ?, ?, ?)", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_GUILD_BANK_ITEM, "DELETE FROM guild_bank_item WHERE guildid = ? AND TabId = ? AND SlotId = ?", CONNECTION_ASYNC); // 0: uint32, 1: uint8, 2: uint8
    PrepareStatement(CHAR_DEL_GUILD_BANK_ITEMS, "DELETE FROM guild_bank_item WHERE guildid = ?", CONNECTION_ASYNC); // 0: uint32
    // 0: uint32, 1: uint8, 2: uint8, 3: uint8, 4: uint32
    PrepareStatement(CHAR_INS_GUILD_BANK_RIGHT, "INSERT INTO guild_bank_right (guildid, TabId, rid, gbright, SlotPerDay) VALUES (?, ?, ?, ?, ?) "
                     "ON DUPLICATE KEY UPDATE gbright = VALUES(gbright), SlotPerDay = VALUES(SlotPerDay)", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_GUILD_BANK_RIGHTS, "DELETE FROM guild_bank_right WHERE guildid = ?", CONNECTION_ASYNC); // 0: uint32
    PrepareStatement(CHAR_DEL_GUILD_BANK_RIGHTS_FOR_RANK, "DELETE FROM guild_bank_right WHERE guildid = ? AND rid = ?", CONNECTION_ASYNC); // 0: uint32, 1: uint8
    // 0-1: uint32, 2-3: uint8, 4-5: uint32, 6: uint16, 7: uint8, 8: uint64
    PrepareStatement(CHAR_INS_GUILD_BANK_EVENTLOG, "INSERT INTO guild_bank_eventlog (guildid, LogGuid, TabId, EventType, PlayerGuid, ItemOrMoney, ItemStackCount, DestTabId, TimeStamp) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_GUILD_BANK_EVENTLOG, "DELETE FROM guild_bank_eventlog WHERE guildid = ? AND LogGuid = ? AND TabId = ?", CONNECTION_ASYNC); // 0: uint32, 1: uint32, 2: uint8
    PrepareStatement(CHAR_DEL_GUILD_BANK_EVENTLOGS, "DELETE FROM guild_bank_eventlog WHERE guildid = ?", CONNECTION_ASYNC); // 0: uint32
    // 0-1: uint32, 2: uint8, 3-4: uint32, 5: uint8, 6: uint64
    PrepareStatement(CHAR_INS_GUILD_EVENTLOG, "INSERT INTO guild_eventlog (guildid, LogGuid, EventType, PlayerGuid1, PlayerGuid2, NewRank, TimeStamp) VALUES (?, ?, ?, ?, ?, ?, ?)", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_GUILD_EVENTLOG, "DELETE FROM guild_eventlog WHERE guildid = ? AND LogGuid = ?", CONNECTION_ASYNC); // 0: uint32, 1: uint32
    PrepareStatement(CHAR_DEL_GUILD_EVENTLOGS, "DELETE FROM guild_eventlog WHERE guildid = ?", CONNECTION_ASYNC); // 0: uint32
    PrepareStatement(CHAR_UPD_GUILD_MEMBER_PNOTE, "UPDATE guild_member SET pnote = ? WHERE guid = ?", CONNECTION_ASYNC); // 0: string, 1: uint32
    PrepareStatement(CHAR_UPD_GUILD_MEMBER_OFFNOTE, "UPDATE guild_member SET offnote = ? WHERE guid = ?", CONNECTION_ASYNC); // 0: string, 1: uint32
    PrepareStatement(CHAR_UPD_GUILD_MEMBER_RANK, "UPDATE guild_member SET `rank` = ? WHERE guid = ?", CONNECTION_ASYNC); // 0: uint8, 1: uint32
    PrepareStatement(CHAR_UPD_GUILD_MOTD, "UPDATE guild SET motd = ? WHERE guildid = ?", CONNECTION_ASYNC); // 0: string, 1: uint32
    PrepareStatement(CHAR_UPD_GUILD_INFO, "UPDATE guild SET info = ? WHERE guildid = ?", CONNECTION_ASYNC); // 0: string, 1: uint32
    PrepareStatement(CHAR_UPD_GUILD_LEADER, "UPDATE guild SET leaderguid = ? WHERE guildid = ?", CONNECTION_ASYNC); // 0: uint32, 1: uint32
    PrepareStatement(CHAR_UPD_GUILD_RANK_NAME, "UPDATE guild_rank SET rname = ? WHERE rid = ? AND guildid = ?", CONNECTION_ASYNC); // 0: string, 1: uint8, 2: uint32
    PrepareStatement(CHAR_UPD_GUILD_RANK_RIGHTS, "UPDATE guild_rank SET rights = ? WHERE rid = ? AND guildid = ?", CONNECTION_ASYNC); // 0: uint32, 1: uint8, 2: uint32
    // 0-5: uint32
    PrepareStatement(CHAR_UPD_GUILD_EMBLEM_INFO, "UPDATE guild SET EmblemStyle = ?, EmblemColor = ?, BorderStyle = ?, BorderColor = ?, BackgroundColor = ? WHERE guildid = ?", CONNECTION_ASYNC);
    // 0: string, 1: string, 2: uint32, 3: uint8
    PrepareStatement(CHAR_UPD_GUILD_BANK_TAB_INFO, "UPDATE guild_bank_tab SET TabName = ?, TabIcon = ? WHERE guildid = ? AND TabId = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_UPD_GUILD_BANK_MONEY, "UPDATE guild SET BankMoney = ? WHERE guildid = ?", CONNECTION_ASYNC); // 0: uint64, 1: uint32
    // 0: uint8, 1: uint32, 2: uint8, 3: uint32
    PrepareStatement(CHAR_UPD_GUILD_BANK_EVENTLOG_TAB, "UPDATE guild_bank_eventlog SET TabId = ? WHERE guildid = ? AND TabId = ? AND LogGuid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_UPD_GUILD_RANK_BANK_MONEY, "UPDATE guild_rank SET BankMoneyPerDay = ? WHERE rid = ? AND guildid = ?", CONNECTION_ASYNC); // 0: uint32, 1: uint8, 2: uint32
    PrepareStatement(CHAR_UPD_GUILD_BANK_TAB_TEXT, "UPDATE guild_bank_tab SET TabText = ? WHERE guildid = ? AND TabId = ?", CONNECTION_ASYNC); // 0: string, 1: uint32, 2: uint8

    PrepareStatement(CHAR_INS_GUILD_MEMBER_WITHDRAW,
                     "INSERT INTO guild_member_withdraw (guid, tab0, tab1, tab2, tab3, tab4, tab5, money) VALUES (?, ?, ?, ?, ?, ?, ?, ?) "
                     "ON DUPLICATE KEY UPDATE tab0 = VALUES (tab0), tab1 = VALUES (tab1), tab2 = VALUES (tab2), tab3 = VALUES (tab3), tab4 = VALUES (tab4), tab5 = VALUES (tab5)", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_GUILD_MEMBER_WITHDRAW, "TRUNCATE guild_member_withdraw", CONNECTION_ASYNC);

    // 0: uint32, 1: uint32, 2: uint32
    PrepareStatement(CHAR_SEL_CHAR_DATA_FOR_GUILD, "SELECT name, level, class, gender, zone, account FROM characters WHERE guid = ?", CONNECTION_SYNCH);

    // Chat channel handling
    PrepareStatement(CHAR_INS_CHANNEL, "INSERT INTO channels(channelId, name, team, announce, lastUsed) VALUES (?, ?, ?, ?, UNIX_TIMESTAMP())", CONNECTION_ASYNC);
    PrepareStatement(CHAR_UPD_CHANNEL, "UPDATE channels SET announce = ?, password = ?, lastUsed = UNIX_TIMESTAMP() WHERE channelId = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_CHANNEL, "DELETE FROM channels WHERE name = ? AND team = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_UPD_CHANNEL_USAGE, "UPDATE channels SET lastUsed = UNIX_TIMESTAMP() WHERE channelId = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_OLD_CHANNELS, "DELETE FROM channels WHERE lastUsed + ? < UNIX_TIMESTAMP()", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_OLD_CHANNELS_BANS, "DELETE cb.* FROM channels_bans cb LEFT JOIN channels cn ON cb.channelId=cn.channelId WHERE cn.channelId IS NULL OR cb.banTime <= UNIX_TIMESTAMP()", CONNECTION_ASYNC);
    PrepareStatement(CHAR_INS_CHANNEL_BAN, "REPLACE INTO channels_bans VALUES (?, ?, ?)", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_CHANNEL_BAN, "DELETE FROM channels_bans WHERE channelId = ? AND playerGUID = ?", CONNECTION_ASYNC);

    // Equipmentsets
    PrepareStatement(CHAR_UPD_EQUIP_SET, "UPDATE character_equipmentsets SET name=?, iconname=?, ignore_mask=?, item0=?, item1=?, item2=?, item3=?, "
                     "item4=?, item5=?, item6=?, item7=?, item8=?, item9=?, item10=?, item11=?, item12=?, item13=?, item14=?, item15=?, item16=?, "
                     "item17=?, item18=? WHERE guid=? AND setguid=? AND setindex=?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_INS_EQUIP_SET, "INSERT INTO character_equipmentsets (guid, setguid, setindex, name, iconname, ignore_mask, item0, item1, item2, item3, "
                     "item4, item5, item6, item7, item8, item9, item10, item11, item12, item13, item14, item15, item16, item17, item18) "
                     "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_EQUIP_SET, "DELETE FROM character_equipmentsets WHERE setguid=?", CONNECTION_ASYNC);

    // Auras
    PrepareStatement(CHAR_INS_AURA, "INSERT INTO character_aura (guid, casterGuid, itemGuid, spell, effectMask, recalculateMask, stackcount, amount0, amount1, amount2, base_amount0, base_amount1, base_amount2, maxDuration, remainTime, remainCharges) "
                     "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", CONNECTION_ASYNC);

    // Account data
    PrepareStatement(CHAR_SEL_ACCOUNT_DATA, "SELECT type, time, data FROM account_data WHERE accountId = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_REP_ACCOUNT_DATA, "REPLACE INTO account_data (accountId, type, time, data) VALUES (?, ?, ?, ?)", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_ACCOUNT_DATA, "DELETE FROM account_data WHERE accountId = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_SEL_PLAYER_ACCOUNT_DATA, "SELECT type, time, data FROM character_account_data WHERE guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_REP_PLAYER_ACCOUNT_DATA, "REPLACE INTO character_account_data(guid, type, time, data) VALUES (?, ?, ?, ?)", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_PLAYER_ACCOUNT_DATA, "DELETE FROM character_account_data WHERE guid = ?", CONNECTION_ASYNC);

    // Tutorials
    PrepareStatement(CHAR_SEL_TUTORIALS, "SELECT tut0, tut1, tut2, tut3, tut4, tut5, tut6, tut7 FROM account_tutorial WHERE accountId = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_SEL_HAS_TUTORIALS, "SELECT 1 FROM account_tutorial WHERE accountId = ?", CONNECTION_SYNCH);
    PrepareStatement(CHAR_INS_TUTORIALS, "INSERT INTO account_tutorial(tut0, tut1, tut2, tut3, tut4, tut5, tut6, tut7, accountId) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", CONNECTION_ASYNC);
    PrepareStatement(CHAR_UPD_TUTORIALS, "UPDATE account_tutorial SET tut0 = ?, tut1 = ?, tut2 = ?, tut3 = ?, tut4 = ?, tut5 = ?, tut6 = ?, tut7 = ? WHERE accountId = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_TUTORIALS, "DELETE FROM account_tutorial WHERE accountId = ?", CONNECTION_ASYNC);

    // Instance saves
    PrepareStatement(CHAR_INS_INSTANCE_SAVE, "INSERT INTO instance (id, map, resettime, difficulty, completedEncounters, data) VALUES (?, ?, ?, ?, ?, ?)", CONNECTION_ASYNC);
    PrepareStatement(CHAR_UPD_INSTANCE_SAVE_DATA, "UPDATE instance SET data=? WHERE id=?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_UPD_INSTANCE_SAVE_ENCOUNTERMASK, "UPDATE instance SET completedEncounters=? WHERE id=?", CONNECTION_ASYNC);

    // Game event saves
    PrepareStatement(CHAR_DEL_GAME_EVENT_SAVE, "DELETE FROM game_event_save WHERE eventEntry = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_INS_GAME_EVENT_SAVE, "INSERT INTO game_event_save (eventEntry, state, next_start) VALUES (?, ?, ?)", CONNECTION_ASYNC);

    // Game event condition saves
    PrepareStatement(CHAR_DEL_ALL_GAME_EVENT_CONDITION_SAVE, "DELETE FROM game_event_condition_save WHERE eventEntry = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_GAME_EVENT_CONDITION_SAVE, "DELETE FROM game_event_condition_save WHERE eventEntry = ? AND condition_id = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_INS_GAME_EVENT_CONDITION_SAVE, "INSERT INTO game_event_condition_save (eventEntry, condition_id, done) VALUES (?, ?, ?)", CONNECTION_ASYNC);
    PrepareStatement(CHAR_SEL_GAME_EVENT_CONDITION_SAVE_DATA, "SELECT eventEntry, condition_id, done FROM game_event_condition_save", CONNECTION_SYNCH);
    PrepareStatement(CHAR_SEL_GAME_EVENT_SAVE_DATA, "SELECT eventEntry, state, next_start FROM game_event_save", CONNECTION_SYNCH);

    // Petitions
    PrepareStatement(CHAR_DEL_ALL_PETITION_SIGNATURES, "DELETE FROM petition_sign WHERE playerguid = ?", CONNECTION_ASYNC);
    // petition_sign.type is not written by the sign insert (petition_id schema), join petition for the type filter
    PrepareStatement(CHAR_DEL_PETITION_SIGNATURE, "DELETE ps FROM petition_sign ps INNER JOIN petition p ON p.petition_id = ps.petition_id WHERE ps.playerguid = ? AND p.type = ?", CONNECTION_ASYNC);

    // Arena teams
    PrepareStatement(CHAR_INS_ARENA_TEAM, "INSERT INTO arena_team (arenaTeamId, name, captainGuid, type, rating, backgroundColor, emblemStyle, emblemColor, borderStyle, borderColor) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", CONNECTION_ASYNC);
    PrepareStatement(CHAR_INS_ARENA_TEAM_MEMBER, "INSERT INTO arena_team_member (arenaTeamId, guid, personalRating) VALUES (?, ?, ?)", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_ARENA_TEAM, "DELETE FROM arena_team WHERE arenaTeamId = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_ARENA_TEAM_MEMBERS, "DELETE FROM arena_team_member WHERE arenaTeamId = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_UPD_ARENA_TEAM_CAPTAIN, "UPDATE arena_team SET captainGuid = ? WHERE arenaTeamId = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_ARENA_TEAM_MEMBER, "DELETE FROM arena_team_member WHERE arenaTeamId = ? AND guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_UPD_ARENA_TEAM_STATS, "UPDATE arena_team SET rating = ?, weekGames = ?, weekWins = ?, seasonGames = ?, seasonWins = ?, `rank` = ? WHERE arenaTeamId = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_UPD_ARENA_TEAM_MEMBER, "UPDATE arena_team_member SET personalRating = ?, weekGames = ?, weekWins = ?, seasonGames = ?, seasonWins = ? WHERE arenaTeamId = ? AND guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_REP_CHARACTER_ARENA_STATS, "REPLACE INTO character_arena_stats (guid, slot, matchMakerRating, maxMMR) VALUES (?, ?, ?, ?)", CONNECTION_ASYNC);
    PrepareStatement(CHAR_SEL_PLAYER_ARENA_TEAMS, "SELECT arena_team_member.arenaTeamId FROM arena_team_member JOIN arena_team ON arena_team_member.arenaTeamId = arena_team.arenaTeamId WHERE guid = ?", CONNECTION_SYNCH);
    PrepareStatement(CHAR_UPD_ARENA_TEAM_NAME, "UPDATE arena_team SET name = ? WHERE arenaTeamId = ?", CONNECTION_ASYNC);

    // Character battleground data
    PrepareStatement(CHAR_INS_PLAYER_ENTRY_POINT, "INSERT INTO character_entry_point (guid, joinX, joinY, joinZ, joinO, joinMapId, taxiPath0, taxiPath1, mountSpell) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_PLAYER_ENTRY_POINT, "DELETE FROM character_entry_point WHERE guid = ?", CONNECTION_ASYNC);

    // Character homebind
    PrepareStatement(CHAR_INS_PLAYER_HOMEBIND, "INSERT INTO character_homebind (guid, mapId, zoneId, posX, posY, posZ) VALUES (?, ?, ?, ?, ?, ?)", CONNECTION_ASYNC);
    PrepareStatement(CHAR_UPD_PLAYER_HOMEBIND, "UPDATE character_homebind SET mapId = ?, zoneId = ?, posX = ?, posY = ?, posZ = ? WHERE guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_PLAYER_HOMEBIND, "DELETE FROM character_homebind WHERE guid = ?", CONNECTION_ASYNC);

    // Corpse
    PrepareStatement(CHAR_SEL_CORPSES, "SELECT posX, posY, posZ, orientation, mapId, displayId, itemCache, bytes1, bytes2, guildId, flags, dynFlags, time, corpseType, instanceId, phaseMask, guid FROM corpse WHERE mapId = ? AND instanceId = ?", CONNECTION_SYNCH);
    PrepareStatement(CHAR_INS_CORPSE, "INSERT INTO corpse (guid, posX, posY, posZ, orientation, mapId, displayId, itemCache, bytes1, bytes2, guildId, flags, dynFlags, time, corpseType, instanceId, phaseMask) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_CORPSE, "DELETE FROM corpse WHERE guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_CORPSES_FROM_MAP, "DELETE FROM corpse WHERE mapId = ? AND instanceId = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_SEL_CORPSE_LOCATION, "SELECT mapId, posX, posY, posZ, orientation FROM corpse WHERE guid = ?", CONNECTION_ASYNC);

    // Creature respawn
    PrepareStatement(CHAR_SEL_CREATURE_RESPAWNS, "SELECT guid, respawnTime FROM creature_respawn WHERE mapId = ? AND instanceId = ?", CONNECTION_SYNCH);
    PrepareStatement(CHAR_REP_CREATURE_RESPAWN, "REPLACE INTO creature_respawn (guid, respawnTime, mapId, instanceId) VALUES (?, ?, ?, ?)", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_CREATURE_RESPAWN, "DELETE FROM creature_respawn WHERE guid = ? AND mapId = ? AND instanceId = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_CREATURE_RESPAWN_BY_INSTANCE, "DELETE FROM creature_respawn WHERE mapId = ? AND instanceId = ?", CONNECTION_ASYNC);

    // Gameobject respawn
    PrepareStatement(CHAR_SEL_GO_RESPAWNS, "SELECT guid, respawnTime FROM gameobject_respawn WHERE mapId = ? AND instanceId = ?", CONNECTION_SYNCH);
    PrepareStatement(CHAR_REP_GO_RESPAWN, "REPLACE INTO gameobject_respawn (guid, respawnTime, mapId, instanceId) VALUES (?, ?, ?, ?)", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_GO_RESPAWN, "DELETE FROM gameobject_respawn WHERE guid = ? AND mapId = ? AND instanceId = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_GO_RESPAWN_BY_INSTANCE, "DELETE FROM gameobject_respawn WHERE mapId = ? AND instanceId = ?", CONNECTION_ASYNC);

    // GM Tickets
    PrepareStatement(CHAR_SEL_GM_TICKETS, "SELECT id, type, playerGuid, name, description, createTime, mapId, posX, posY, posZ, lastModifiedTime, closedBy, assignedTo, comment, response, completed, escalated, viewed, needMoreHelp, resolvedBy FROM gm_ticket", CONNECTION_SYNCH);
    PrepareStatement(CHAR_REP_GM_TICKET, "REPLACE INTO gm_ticket (id, type, playerGuid, name, description, createTime, mapId, posX, posY, posZ, lastModifiedTime, closedBy, assignedTo, comment, response, completed, escalated, viewed, needMoreHelp, resolvedBy) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_GM_TICKET, "DELETE FROM gm_ticket WHERE id = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_PLAYER_GM_TICKETS, "DELETE FROM gm_ticket WHERE playerGuid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_UPD_PLAYER_GM_TICKETS_ON_CHAR_DELETION, "UPDATE gm_ticket SET type = 2 WHERE playerGuid = ?", CONNECTION_ASYNC);

    // GM Survey/subsurvey/lag report
    PrepareStatement(CHAR_INS_GM_SURVEY, "INSERT INTO gm_survey (guid, surveyId, mainSurvey, comment, createTime) VALUES (?, ?, ?, ?, UNIX_TIMESTAMP(NOW()))", CONNECTION_ASYNC);
    PrepareStatement(CHAR_INS_GM_SUBSURVEY, "INSERT INTO gm_subsurvey (surveyId, questionId, answer, answerComment) VALUES (?, ?, ?, ?)", CONNECTION_ASYNC);
    PrepareStatement(CHAR_INS_LAG_REPORT, "INSERT INTO lag_reports (guid, lagType, mapId, posX, posY, posZ, latency, createTime) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", CONNECTION_ASYNC);

    // LFG Data
    PrepareStatement(CHAR_REP_LFG_DATA, "REPLACE INTO lfg_data (guid, dungeon, state) VALUES (?, ?, ?)", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_LFG_DATA, "DELETE FROM lfg_data WHERE guid = ?", CONNECTION_ASYNC);

    // Player saving
    PrepareStatement(CHAR_INS_CHARACTER, "INSERT INTO characters (guid, account, name, race, class, gender, level, xp, money, skin, face, hairStyle, hairColor, facialStyle, bankSlots, restState, playerFlags, "
                     "map, instance_id, instance_mode_mask, position_x, position_y, position_z, orientation, trans_x, trans_y, trans_z, trans_o, transguid, "
                     "taximask, cinematic, "
                     "totaltime, leveltime, rest_bonus, logout_time, is_logout_resting, resettalents_cost, resettalents_time, "
                     "extra_flags, stable_slots, at_login, zone, "
                     "death_expire_time, taxi_path, arenaPoints, totalHonorPoints, todayHonorPoints, yesterdayHonorPoints, totalKills, "
                     "todayKills, yesterdayKills, chosenTitle, knownCurrencies, watchedFaction, drunk, health, power1, power2, power3, "
                     "power4, power5, power6, power7, latency, talentGroupsCount, activeTalentGroup, exploredZones, equipmentCache, "
                     "ammoId, knownTitles, actionBars, grantableLevels, innTriggerId, "
                     "extraBonusTalentCount, teamId) VALUES "
                     "(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,"
                     "?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", CONNECTION_ASYNC);
    PrepareStatement(CHAR_UPD_CHARACTER, "UPDATE characters SET name=?,race=?,class=?,gender=?,level=?,xp=?,money=?,skin=?,face=?,hairStyle=?,hairColor=?,facialStyle=?,bankSlots=?,restState=?,playerFlags=?,"
                     "map=?,instance_id=?,instance_mode_mask=?,position_x=?,position_y=?,position_z=?,orientation=?,trans_x=?,trans_y=?,trans_z=?,trans_o=?,transguid=?,taximask=?,cinematic=?,totaltime=?,leveltime=?,rest_bonus=?,"
                     "logout_time=?,is_logout_resting=?,resettalents_cost=?,resettalents_time=?,extra_flags=?,stable_slots=?,at_login=?,zone=?,death_expire_time=?,taxi_path=?,"
                     "arenaPoints=?,totalHonorPoints=?,todayHonorPoints=?,yesterdayHonorPoints=?,totalKills=?,todayKills=?,yesterdayKills=?,chosenTitle=?,knownCurrencies=?,"
                     "watchedFaction=?,drunk=?,health=?,power1=?,power2=?,power3=?,power4=?,power5=?,power6=?,power7=?,latency=?,talentGroupsCount=?,activeTalentGroup=?,exploredZones=?,"
                     "equipmentCache=?,ammoId=?,knownTitles=?,actionBars=?,grantableLevels=?,innTriggerId=?,"
                     "extraBonusTalentCount=?,teamId=?,online=? WHERE guid=?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_UPD_CHARACTER_TEAM, "UPDATE characters SET teamId = ? WHERE guid = ?", CONNECTION_ASYNC);

    PrepareStatement(CHAR_UPD_ADD_AT_LOGIN_FLAG, "UPDATE characters SET at_login = at_login | ? WHERE guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_UPD_REM_AT_LOGIN_FLAG, "UPDATE characters set at_login = at_login & ~ ? WHERE guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_UPD_ALL_AT_LOGIN_FLAGS, "UPDATE characters SET at_login = at_login | ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_INS_BUG_REPORT, "INSERT INTO bugreport (type, content) VALUES(?, ?)", CONNECTION_ASYNC);
    PrepareStatement(CHAR_INS_SPAM_REPORT, "INSERT INTO spam_reports (SpamType, SpammerGuid, Unk1, MailIdOrMessageType, ChannelId, SecondsSinceMessage, Description, Time) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", CONNECTION_ASYNC);
    PrepareStatement(CHAR_UPD_PETITION_NAME, "UPDATE petition SET name = ? WHERE petition_id = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_INS_PETITION_SIGNATURE, "INSERT INTO petition_sign (ownerguid, petition_id, playerguid, player_account) VALUES (?, ?, ?, ?)", CONNECTION_ASYNC);
    PrepareStatement(CHAR_UPD_ACCOUNT_ONLINE, "UPDATE characters SET online = 0 WHERE account = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_UPD_CHAR_OFFLINE, "UPDATE characters SET online = 0 WHERE guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_INS_GROUP, "INSERT INTO `groups` (guid, leaderGuid, lootMethod, looterGuid, lootThreshold, icon1, icon2, icon3, icon4, icon5, icon6, icon7, icon8, groupType, difficulty, raidDifficulty, masterLooterGuid) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", CONNECTION_ASYNC);
    PrepareStatement(CHAR_REP_GROUP_MEMBER, "REPLACE INTO group_member (guid, memberGuid, memberFlags, subgroup, roles) VALUES(?, ?, ?, ?, ?)", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_GROUP_MEMBER, "DELETE FROM group_member WHERE memberGuid = ? AND guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_UPD_GROUP_LEADER, "UPDATE `groups` SET leaderGuid = ? WHERE guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_UPD_GROUP_TYPE, "UPDATE `groups` SET groupType = ? WHERE guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_UPD_GROUP_MEMBER_SUBGROUP, "UPDATE group_member SET subgroup = ? WHERE memberGuid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_UPD_GROUP_MEMBER_FLAG, "UPDATE group_member SET memberFlags = ? WHERE memberGuid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_UPD_GROUP_DIFFICULTY, "UPDATE `groups` SET difficulty = ? WHERE guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_UPD_GROUP_RAID_DIFFICULTY, "UPDATE `groups` SET raidDifficulty = ? WHERE guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_ALL_GM_TICKETS, "TRUNCATE TABLE gm_ticket", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_INVALID_SPELL_TALENTS, "DELETE FROM character_talent WHERE spell = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_INVALID_SPELL_SPELLS, "DELETE FROM character_spell WHERE spell = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_UPD_DELETE_INFO, "UPDATE characters SET deleteInfos_Name = name, deleteInfos_Account = account, deleteDate = UNIX_TIMESTAMP(), name = '', account = 0 WHERE guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_UDP_RESTORE_DELETE_INFO, "UPDATE characters SET name = ?, account = ?, deleteDate = NULL, deleteInfos_Name = NULL, deleteInfos_Account = NULL WHERE deleteDate IS NOT NULL AND guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_UPD_ZONE, "UPDATE characters SET zone = ? WHERE guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_UPD_LEVEL, "UPDATE characters SET level = ?, xp = 0 WHERE guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_UPD_XP_ACCUMULATIVE, "UPDATE characters SET  xp = xp + ? WHERE guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_INVALID_ACHIEV_PROGRESS_CRITERIA, "DELETE FROM character_achievement_progress WHERE criteria = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_INVALID_ACHIEVMENT, "DELETE FROM character_achievement WHERE achievement = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_INS_ADDON, "INSERT INTO addons (name, crc) VALUES (?, ?)", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_INVALID_PET_SPELL, "DELETE FROM pet_spell WHERE spell = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_UPD_GLOBAL_INSTANCE_RESETTIME, "UPDATE instance_reset SET resettime = ? WHERE mapid = ? AND difficulty = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_UPD_CHAR_ONLINE, "UPDATE characters SET online = 1 WHERE guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_UPD_CHAR_NAME_AT_LOGIN, "UPDATE characters set name = ?, at_login = ? WHERE guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_UPD_WORLDSTATE, "UPDATE worldstates SET value = ? WHERE entry = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_INS_WORLDSTATE, "INSERT INTO worldstates (entry, value) VALUES (?, ?)", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_CHAR_INSTANCE_BY_INSTANCE, "DELETE FROM character_instance WHERE instance = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_CHAR_INSTANCE_BY_INSTANCE_NOT_EXTENDED, "DELETE FROM character_instance WHERE instance = ? AND extended = 0", CONNECTION_ASYNC);
    PrepareStatement(CHAR_UPD_CHAR_INSTANCE_SET_NOT_EXTENDED, "UPDATE character_instance SET extended = 0 WHERE instance = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_CHAR_INSTANCE_BY_INSTANCE_GUID, "DELETE FROM character_instance WHERE guid = ? AND instance = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_UPD_CHAR_INSTANCE, "UPDATE character_instance SET instance = ?, permanent = ?, extended = 0 WHERE guid = ? AND instance = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_UPD_CHAR_INSTANCE_EXTENDED, "UPDATE character_instance SET extended = ? WHERE guid = ? AND instance = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_INS_CHAR_INSTANCE, "INSERT INTO character_instance (guid, instance, permanent, extended) VALUES (?, ?, ?, 0)", CONNECTION_ASYNC);
    PrepareStatement(CHAR_INS_ARENA_LOG_FIGHT, "INSERT INTO log_arena_fights VALUES (?, NOW(), ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", CONNECTION_ASYNC);
    PrepareStatement(CHAR_INS_ARENA_LOG_MEMBERSTATS, "INSERT INTO log_arena_memberstats VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", CONNECTION_ASYNC);
    PrepareStatement(CHAR_UPD_GENDER_AND_APPEARANCE, "UPDATE characters SET gender = ?, skin = ?, face = ?, hairStyle = ?, hairColor = ?, facialStyle = ? WHERE guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_CHARACTER_SKILL, "DELETE FROM character_skills WHERE guid = ? AND skill = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_UPD_ADD_CHARACTER_SOCIAL_FLAGS, "UPDATE character_social SET flags = flags | ? WHERE guid = ? AND friend = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_UPD_REM_CHARACTER_SOCIAL_FLAGS, "UPDATE character_social SET flags = flags & ~ ? WHERE guid = ? AND friend = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_INS_CHARACTER_SOCIAL, "REPLACE INTO character_social (guid, friend, flags) VALUES (?, ?, ?)", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_CHARACTER_SOCIAL, "DELETE FROM character_social WHERE guid = ? AND friend = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_UPD_CHARACTER_SOCIAL_NOTE, "UPDATE character_social SET note = ? WHERE guid = ? AND friend = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_UPD_CHARACTER_POSITION, "UPDATE characters SET position_x = ?, position_y = ?, position_z = ?, orientation = ?, map = ?, zone = ?, trans_x = 0, trans_y = 0, trans_z = 0, transguid = 0, taxi_path = '', cinematic = 1 WHERE guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_SEL_CHARACTER_AURA_FROZEN, "SELECT characters.name FROM characters LEFT JOIN character_aura ON (characters.guid = character_aura.guid) WHERE character_aura.spell = 9454", CONNECTION_ASYNC);
    PrepareStatement(CHAR_SEL_CHARACTER_ONLINE, "SELECT name, account, map, zone FROM characters WHERE online > 0", CONNECTION_SYNCH);
    PrepareStatement(CHAR_SEL_CHAR_DEL_INFO_BY_GUID, "SELECT guid, deleteInfos_Name, deleteInfos_Account, deleteDate, level FROM characters WHERE deleteDate IS NOT NULL AND guid = ?", CONNECTION_SYNCH);
    PrepareStatement(CHAR_SEL_CHAR_DEL_INFO_BY_NAME, "SELECT guid, deleteInfos_Name, deleteInfos_Account, deleteDate, level FROM characters WHERE deleteDate IS NOT NULL AND deleteInfos_Name LIKE CONCAT('%%', ?, '%%') ORDER BY deleteDate DESC", CONNECTION_SYNCH);
    PrepareStatement(CHAR_SEL_CHAR_DEL_INFO_BY_NAME_LIMIT, "SELECT guid, deleteInfos_Name, deleteInfos_Account, deleteDate, level FROM characters WHERE deleteDate IS NOT NULL AND deleteInfos_Name LIKE CONCAT('%%', ?, '%%') ORDER BY deleteDate DESC LIMIT 51", CONNECTION_SYNCH);
    PrepareStatement(CHAR_SEL_CHAR_DEL_INFO, "SELECT guid, deleteInfos_Name, deleteInfos_Account, deleteDate, level FROM characters WHERE deleteDate IS NOT NULL ORDER BY deleteDate DESC LIMIT 51", CONNECTION_SYNCH);
    PrepareStatement(CHAR_SEL_CHARS_BY_ACCOUNT_ID, "SELECT guid, class, race FROM characters WHERE account = ?", CONNECTION_SYNCH);
    PrepareStatement(CHAR_SEL_ACCOUNT_INFO_CHARS, "SELECT guid, name, level, race, class, online FROM characters WHERE account = ? AND deleteDate IS NULL ORDER BY level DESC, name ASC", CONNECTION_SYNCH);
    PrepareStatement(CHAR_SEL_CHAR_PINFO, "SELECT totaltime, level, money, account, race, class, map, zone, gender, health, playerFlags FROM characters WHERE guid = ?", CONNECTION_SYNCH);
    PrepareStatement(CHAR_SEL_PINFO_BANS, "SELECT unbandate, bandate = unbandate, bannedby, banreason FROM character_banned WHERE guid = ? AND active ORDER BY bandate ASC LIMIT 1", CONNECTION_SYNCH);
    PrepareStatement(CHAR_SEL_PINFO_MAILS, "SELECT SUM(CASE WHEN (checked & 1) THEN 1 ELSE 0 END) AS 'readmail', COUNT(*) AS 'totalmail' FROM mail WHERE `receiver` = ?", CONNECTION_SYNCH);
    PrepareStatement(CHAR_SEL_PINFO_XP, "SELECT a.xp, b.guid FROM characters a LEFT JOIN guild_member b ON a.guid = b.guid WHERE a.guid = ?", CONNECTION_SYNCH);
    PrepareStatement(CHAR_SEL_CHAR_HOMEBIND, "SELECT mapId, zoneId, posX, posY, posZ FROM character_homebind WHERE guid = ?", CONNECTION_SYNCH);
    PrepareStatement(CHAR_SEL_CHAR_GUID_NAME_BY_ACC, "SELECT guid, name FROM characters WHERE account = ?", CONNECTION_SYNCH);
    PrepareStatement(CHAR_SEL_POOL_QUEST_SAVE, "SELECT quest_id FROM pool_quest_save WHERE pool_id = ?", CONNECTION_SYNCH);
    PrepareStatement(CHAR_SEL_CHARACTER_AT_LOGIN, "SELECT at_login FROM characters WHERE guid = ?", CONNECTION_SYNCH);
    PrepareStatement(CHAR_SEL_CHAR_CLASS_LVL_AT_LOGIN, "SELECT class, level, at_login, knownTitles FROM characters WHERE guid = ?", CONNECTION_SYNCH);
    PrepareStatement(CHAR_SEL_CHAR_CUSTOMIZE_INFO, "SELECT name, race, class, gender, at_login FROM characters WHERE guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_SEL_CHAR_RACE_OR_FACTION_CHANGE_INFOS,
                     "SELECT at_login, knownTitles, money, teamId FROM characters WHERE guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_SEL_CHAR_AT_LOGIN_TITLES_MONEY, "SELECT at_login, knownTitles, money FROM characters WHERE guid = ?", CONNECTION_SYNCH);
    PrepareStatement(CHAR_SEL_CHAR_COD_ITEM_MAIL, "SELECT id, messageType, mailTemplateId, sender, subject, body, money, has_items FROM mail WHERE receiver = ? AND has_items <> 0 AND cod <> 0", CONNECTION_SYNCH);
    PrepareStatement(CHAR_SEL_CHAR_SOCIAL, "SELECT DISTINCT guid FROM character_social WHERE friend = ?", CONNECTION_SYNCH);
    PrepareStatement(CHAR_SEL_CHAR_OLD_CHARS, "SELECT guid, deleteInfos_Account FROM characters WHERE deleteDate IS NOT NULL AND deleteDate < ?", CONNECTION_SYNCH);
    PrepareStatement(CHAR_SEL_ARENA_TEAM_ID_BY_PLAYER_GUID, "SELECT arena_team_member.arenateamid FROM arena_team_member JOIN arena_team ON arena_team_member.arenateamid = arena_team.arenateamid WHERE guid = ? AND type = ? LIMIT 1", CONNECTION_SYNCH);
    PrepareStatement(CHAR_SEL_MAIL, "SELECT id, messageType, sender, receiver, subject, body, expire_time, deliver_time, money, cod, checked, stationery, mailTemplateId, has_items FROM mail WHERE receiver = ? ORDER BY id DESC", CONNECTION_ASYNC);
    PrepareStatement(CHAR_SEL_NEXT_MAIL_DELIVERYTIME, "SELECT MIN(deliver_time) FROM mail WHERE receiver = ? AND deliver_time > ? AND (checked & 1) = 0 LIMIT 1", CONNECTION_SYNCH);
    PrepareStatement(CHAR_DEL_CHAR_AURA_FROZEN, "DELETE FROM character_aura WHERE spell = 9454 AND guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_SEL_CHAR_INVENTORY_COUNT_ITEM, "SELECT COUNT(itemEntry) FROM item_instance ii "
        "WHERE itemEntry = ? AND (EXISTS(SELECT 1 FROM character_inventory ci WHERE ci.item = ii.guid) "
        "OR EXISTS(SELECT 1 FROM character_digital_storage_item ds WHERE ds.item = ii.guid))", CONNECTION_SYNCH);
    PrepareStatement(CHAR_SEL_MAIL_COUNT_ITEM, "SELECT COUNT(itemEntry) FROM mail_items mi INNER JOIN item_instance ii ON ii.guid = mi.item_guid WHERE itemEntry = ?", CONNECTION_SYNCH);
    PrepareStatement(CHAR_SEL_AUCTIONHOUSE_COUNT_ITEM, "SELECT COUNT(itemEntry) FROM auctionhouse ah INNER JOIN item_instance ii ON ii.guid = ah.itemguid WHERE itemEntry = ?", CONNECTION_SYNCH);
    PrepareStatement(CHAR_SEL_GUILD_BANK_COUNT_ITEM, "SELECT COUNT(itemEntry) FROM guild_bank_item gbi INNER JOIN item_instance ii ON ii.guid = gbi.item_guid WHERE itemEntry = ?", CONNECTION_SYNCH);
    PrepareStatement(CHAR_SEL_CHAR_INVENTORY_ITEM_BY_ENTRY, "SELECT ci.item, cb.slot AS bag, ci.slot, ci.guid, c.account, c.name FROM characters c "
                     "INNER JOIN (SELECT guid, item, bag, slot FROM character_inventory UNION ALL "
                     "SELECT guid, item, 0, 255 FROM character_digital_storage_item) ci ON ci.guid = c.guid "
                     "INNER JOIN item_instance ii ON ii.guid = ci.item "
                     "LEFT JOIN character_inventory cb ON cb.item = ci.bag WHERE ii.itemEntry = ? LIMIT ?", CONNECTION_SYNCH);
    PrepareStatement(CHAR_SEL_CHAR_INVENTORY_ITEM_BY_ENTRY_AND_OWNER, "SELECT ii.guid FROM item_instance ii "
        "WHERE ii.itemEntry = ? AND ii.owner_guid = ? "
        "AND (EXISTS(SELECT 1 FROM character_inventory ci WHERE ci.item = ii.guid) "
        "OR EXISTS(SELECT 1 FROM character_digital_storage_item ds WHERE ds.item = ii.guid))", CONNECTION_SYNCH);
    PrepareStatement(CHAR_SEL_CHAR_INVENTORY_STACKS_BY_ENTRY_AND_OWNER, "SELECT ii.guid, ii.count FROM item_instance ii "
        "LEFT JOIN character_inventory cb ON cb.bag = ii.guid "
        "WHERE ii.itemEntry = ? AND ii.owner_guid = ? AND cb.item IS NULL "
        "AND (EXISTS(SELECT 1 FROM character_inventory ci WHERE ci.item = ii.guid) "
        "OR EXISTS(SELECT 1 FROM character_digital_storage_item ds WHERE ds.item = ii.guid))", CONNECTION_SYNCH);
    PrepareStatement(CHAR_SEL_MAIL_ITEMS_BY_ENTRY, "SELECT mi.item_guid, m.sender, m.receiver, cs.account, cs.name, cr.account, cr.name "
                     "FROM mail m INNER JOIN mail_items mi ON mi.mail_id = m.id INNER JOIN item_instance ii ON ii.guid = mi.item_guid "
                     "INNER JOIN characters cs ON cs.guid = m.sender INNER JOIN characters cr ON cr.guid = m.receiver WHERE ii.itemEntry = ? LIMIT ?", CONNECTION_SYNCH);
    PrepareStatement(CHAR_SEL_AUCTIONHOUSE_ITEM_BY_ENTRY, "SELECT  ah.itemguid, ah.itemowner, c.account, c.name FROM auctionhouse ah INNER JOIN characters c ON c.guid = ah.itemowner INNER JOIN item_instance ii ON ii.guid = ah.itemguid WHERE ii.itemEntry = ? LIMIT ?", CONNECTION_SYNCH);
    PrepareStatement(CHAR_SEL_GUILD_BANK_ITEM_BY_ENTRY, "SELECT gi.item_guid, gi.guildid, g.name FROM guild_bank_item gi INNER JOIN guild g ON g.guildid = gi.guildid INNER JOIN item_instance ii ON ii.guid = gi.item_guid WHERE ii.itemEntry = ? LIMIT ?", CONNECTION_SYNCH);
    PrepareStatement(CHAR_DEL_CHAR_ACHIEVEMENT, "DELETE FROM character_achievement WHERE guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_CHAR_ACHIEVEMENT_PROGRESS, "DELETE FROM character_achievement_progress WHERE guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_INS_CHAR_ACHIEVEMENT, "INSERT INTO character_achievement (guid, achievement, date) VALUES (?, ?, ?)", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_CHAR_ACHIEVEMENT_PROGRESS_BY_CRITERIA, "DELETE FROM character_achievement_progress WHERE guid = ? AND criteria = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_INS_CHAR_ACHIEVEMENT_PROGRESS, "INSERT INTO character_achievement_progress (guid, criteria, counter, date) VALUES (?, ?, ?, ?)", CONNECTION_ASYNC);
    PrepareStatement(CHAR_INS_CHAR_ACHIEVEMENT_OFFLINE_UPDATES, "INSERT INTO character_achievement_offline_updates (guid, update_type, arg1, arg2, arg3) VALUES (?, ?, ?, ?, ?)", CONNECTION_ASYNC);
    PrepareStatement(CHAR_SEL_CHAR_ACHIEVEMENT_OFFLINE_UPDATES, "SELECT update_type, arg1, arg2, arg3 FROM character_achievement_offline_updates WHERE guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_CHAR_ACHIEVEMENT_OFFLINE_UPDATES, "DELETE FROM character_achievement_offline_updates WHERE guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_CHAR_REPUTATION_BY_FACTION, "DELETE FROM character_reputation WHERE guid = ? AND faction = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_INS_CHAR_REPUTATION_BY_FACTION, "INSERT INTO character_reputation (guid, faction, standing, flags) VALUES (?, ?, ? , ?)", CONNECTION_ASYNC);
    PrepareStatement(CHAR_UPD_CHAR_ARENA_POINTS, "UPDATE characters SET arenaPoints = (arenaPoints + ?) WHERE guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_ITEM_REFUND_INSTANCE, "DELETE FROM item_refund_instance WHERE item_guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_INS_ITEM_REFUND_INSTANCE, "INSERT INTO item_refund_instance (item_guid, player_guid, paidMoney, paidExtendedCost) VALUES (?, ?, ?, ?)", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_GROUP, "DELETE FROM `groups` WHERE guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_GROUP_MEMBER_ALL, "DELETE FROM group_member WHERE guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_INS_CHAR_GIFT, "INSERT INTO character_gifts (guid, item_guid, entry, flags) VALUES (?, ?, ?, ?)", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_INSTANCE_BY_INSTANCE, "DELETE FROM instance WHERE id = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_MAIL_ITEM_BY_ID, "DELETE FROM mail_items WHERE mail_id = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_INS_PETITION, "INSERT INTO petition (petition_id, ownerguid, petitionguid, name, type) VALUES (?, ?, ?, ?, ?)", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_PETITION_BY_ID, "DELETE FROM petition WHERE petition_id = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_PETITION_SIGNATURE_BY_ID, "DELETE FROM petition_sign WHERE petition_id = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_CHAR_DECLINED_NAME, "DELETE FROM character_declinedname WHERE guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_INS_CHAR_DECLINED_NAME, "INSERT INTO character_declinedname (guid, genitive, dative, accusative, instrumental, prepositional) VALUES (?, ?, ?, ?, ?, ?)", CONNECTION_ASYNC);
    PrepareStatement(CHAR_UPD_CHAR_RACE, "UPDATE characters SET race = ?, teamId = ? WHERE guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_CHAR_SKILL_LANGUAGES, "DELETE FROM character_skills WHERE skill IN (98, 113, 759, 111, 313, 109, 115, 315, 673, 137) AND guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_INS_CHAR_SKILL_LANGUAGE, "INSERT INTO `character_skills` (guid, skill, value, max) VALUES (?, ?, 300, 300)", CONNECTION_ASYNC);
    PrepareStatement(CHAR_UPD_CHAR_TAXI_PATH, "UPDATE characters SET taxi_path = '' WHERE guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_UPD_CHAR_TAXIMASK, "UPDATE characters SET taximask = ? WHERE guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_CHAR_QUESTSTATUS, "DELETE FROM character_queststatus WHERE guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_CHAR_SOCIAL_BY_GUID, "DELETE FROM character_social WHERE guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_CHAR_SOCIAL_BY_FRIEND, "DELETE FROM character_social WHERE friend = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_CHAR_ACHIEVEMENT_BY_ACHIEVEMENT, "DELETE FROM character_achievement WHERE achievement = ? AND guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_UPD_CHAR_ACHIEVEMENT, "UPDATE character_achievement SET achievement = ? WHERE achievement = ? AND guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_UPD_CHAR_INVENTORY_FACTION_CHANGE, "UPDATE item_instance ii SET ii.itemEntry = ? "
        "WHERE ii.itemEntry = ? AND ii.owner_guid = ? "
        "AND (EXISTS(SELECT 1 FROM character_inventory ci WHERE ci.item = ii.guid) "
        "OR EXISTS(SELECT 1 FROM character_digital_storage_item ds WHERE ds.item = ii.guid))", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_CHAR_SPELL_BY_SPELL, "DELETE FROM character_spell WHERE guid = ? AND spell = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_UPD_CHAR_SPELL_FACTION_CHANGE, "UPDATE character_spell SET spell = ? WHERE spell = ? AND guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_SEL_CHAR_REP_BY_FACTION, "SELECT standing FROM character_reputation WHERE faction = ? AND guid = ?", CONNECTION_SYNCH);
    PrepareStatement(CHAR_DEL_CHAR_REP_BY_FACTION, "DELETE FROM character_reputation WHERE faction = ? AND guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_UPD_CHAR_REP_FACTION_CHANGE, "UPDATE character_reputation SET faction = ?, standing = ? WHERE faction = ? AND guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_UPD_CHAR_TITLES_FACTION_CHANGE, "UPDATE characters SET knownTitles = ? WHERE guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_RES_CHAR_TITLES_FACTION_CHANGE, "UPDATE characters SET chosenTitle = 0 WHERE guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_CHAR_SPELL_COOLDOWN, "DELETE FROM character_spell_cooldown WHERE guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_CHARACTER, "DELETE FROM characters WHERE guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_CHAR_ACTION, "DELETE FROM character_action WHERE guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_CHAR_AURA, "DELETE FROM character_aura WHERE guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_CHAR_GIFT, "DELETE FROM character_gifts WHERE guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_CHAR_INSTANCE, "DELETE FROM character_instance WHERE guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_CHAR_INVENTORY, "DELETE FROM character_inventory WHERE guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_CHAR_QUESTSTATUS_REWARDED, "DELETE FROM character_queststatus_rewarded WHERE guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_CHAR_REPUTATION, "DELETE FROM character_reputation WHERE guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_CHAR_SPELL, "DELETE FROM character_spell WHERE guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_MAIL, "DELETE FROM mail WHERE receiver = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_MAIL_ITEMS, "DELETE FROM mail_items WHERE receiver = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_CHAR_ACHIEVEMENTS, "DELETE FROM character_achievement WHERE guid = ? AND achievement NOT BETWEEN '456' AND '467' AND achievement NOT BETWEEN '1400' AND '1427' AND achievement NOT IN(1463, 3117, 3259)", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_CHAR_EQUIPMENTSETS, "DELETE FROM character_equipmentsets WHERE guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_GUILD_EVENTLOG_BY_PLAYER, "DELETE FROM guild_eventlog WHERE PlayerGuid1 = ? OR PlayerGuid2 = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_GUILD_BANK_EVENTLOG_BY_PLAYER, "DELETE FROM guild_bank_eventlog WHERE PlayerGuid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_CHAR_GLYPHS, "DELETE FROM character_glyphs WHERE guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_CHAR_TALENT, "DELETE FROM character_talent WHERE guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_CHAR_SKILLS, "DELETE FROM character_skills WHERE guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_UDP_CHAR_HONOR_POINTS, "UPDATE characters SET totalHonorPoints = ? WHERE guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_UDP_CHAR_HONOR_POINTS_ACCUMULATIVE, "UPDATE characters SET totalHonorPoints = totalHonorPoints + ? WHERE guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_UDP_CHAR_ARENA_POINTS, "UPDATE characters SET arenaPoints = ? WHERE guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_UDP_CHAR_ARENA_POINTS_ACCUMULATIVE, "UPDATE characters SET arenaPoints = arenaPoints + ? WHERE guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_UPD_ALL_HONOR_POINTS, "UPDATE characters SET totalHonorPoints = 0", CONNECTION_SYNCH);
    PrepareStatement(CHAR_UPD_ALL_ARENA_POINTS, "UPDATE characters SET arenaPoints = 0", CONNECTION_SYNCH);
    PrepareStatement(CHAR_UDP_CHAR_MONEY, "UPDATE characters SET money = ? WHERE guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_UDP_CHAR_MONEY_ACCUMULATIVE, "UPDATE characters SET money = money + ? WHERE guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_UPD_CHAR_REMOVE_GHOST, "UPDATE characters SET playerFlags = (playerFlags & (~16)) WHERE guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_INS_CHAR_ACTION, "INSERT INTO character_action (guid, spec, button, action, type) VALUES (?, ?, ?, ?, ?)"
                     "ON DUPLICATE KEY UPDATE action = VALUES(action), type = VALUES(type)", CONNECTION_ASYNC);
    PrepareStatement(CHAR_UPD_CHAR_ACTION, "UPDATE character_action SET action = ?, type = ? WHERE guid = ? AND button = ? AND spec = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_CHAR_ACTION_BY_BUTTON_SPEC, "DELETE FROM character_action WHERE guid = ? AND button = ? AND spec = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_CHAR_INVENTORY_BY_ITEM, "DELETE FROM character_inventory WHERE item = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_CHAR_INVENTORY_BY_BAG_SLOT, "DELETE FROM character_inventory WHERE bag = ? AND slot = ? AND guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_UPD_MAIL, "UPDATE mail SET has_items = ?, expire_time = ?, deliver_time = ?, money = ?, cod = ?, checked = ? WHERE id = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_REP_CHAR_QUESTSTATUS, "REPLACE INTO character_queststatus (guid, quest, status, explored, timer, mobcount1, mobcount2, mobcount3, mobcount4, itemcount1, itemcount2, itemcount3, itemcount4, itemcount5, itemcount6, playercount) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_CHAR_QUESTSTATUS_BY_QUEST, "DELETE FROM character_queststatus WHERE guid = ? AND quest = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_INS_CHAR_QUESTSTATUS_REWARDED, "INSERT IGNORE INTO character_queststatus_rewarded (guid, quest, active) VALUES (?, ?, 1)", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_CHAR_QUESTSTATUS_REWARDED_BY_QUEST, "DELETE FROM character_queststatus_rewarded WHERE guid = ? AND quest = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_UPD_CHAR_QUESTSTATUS_REWARDED_FACTION_CHANGE, "UPDATE character_queststatus_rewarded SET quest = ? WHERE quest = ? AND guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_UPD_CHAR_QUESTSTATUS_REWARDED_ACTIVE, "UPDATE character_queststatus_rewarded SET active = 1 WHERE guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_UPD_CHAR_QUESTSTATUS_REWARDED_ACTIVE_BY_QUEST, "UPDATE character_queststatus_rewarded SET active = 0 WHERE quest = ? AND guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_SEL_CHAR_QUESTSTATUS_BY_QUEST, "SELECT status FROM character_queststatus WHERE guid = ? AND quest = ?", CONNECTION_SYNCH);
    PrepareStatement(CHAR_SEL_CHAR_QUESTSTATUS_SEASONAL_BY_QUEST, "SELECT 1 FROM character_queststatus_seasonal WHERE guid = ? AND quest = ? AND event = ?", CONNECTION_SYNCH);
    PrepareStatement(CHAR_SEL_CHAR_QUESTSTATUS_REWARDED_BY_QUEST, "SELECT 1 FROM character_queststatus_rewarded WHERE guid = ? AND quest = ? AND active = 1", CONNECTION_SYNCH);
    PrepareStatement(CHAR_DEL_CHAR_SKILL_BY_SKILL, "DELETE FROM character_skills WHERE guid = ? AND skill = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_INS_CHAR_SKILLS, "INSERT INTO character_skills (guid, skill, value, max) VALUES (?, ?, ?, ?)"
                     "ON DUPLICATE KEY UPDATE value = VALUES(value), max = VALUES(max)", CONNECTION_ASYNC);
    PrepareStatement(CHAR_UDP_CHAR_SKILLS, "UPDATE character_skills SET value = ?, max = ? WHERE guid = ? AND skill = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_INS_CHAR_SPELL, "INSERT INTO character_spell (guid, spell, specMask) VALUES (?, ?, ?)"
                     "ON DUPLICATE KEY UPDATE specMask = VALUES(specMask)", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_CHAR_STATS, "DELETE FROM character_stats WHERE guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_INS_CHAR_STATS, "INSERT INTO character_stats (guid, maxhealth, maxpower1, maxpower2, maxpower3, maxpower4, maxpower5, maxpower6, maxpower7, strength, agility, stamina, intellect, spirit, "
                     "armor, resHoly, resFire, resNature, resFrost, resShadow, resArcane, blockPct, dodgePct, parryPct, critPct, rangedCritPct, spellCritPct, attackPower, rangedAttackPower, "
                     "spellPower, resilience) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", CONNECTION_ASYNC);
    PrepareStatement(CHAR_SEL_CHAR_STATS, "SELECT maxhealth, strength, agility, stamina, intellect, spirit, armor, attackPower, spellPower, resilience FROM character_stats WHERE guid = ?", CONNECTION_SYNCH);
    PrepareStatement(CHAR_DEL_PETITION_BY_OWNER, "DELETE FROM petition WHERE ownerguid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_PETITION_SIGNATURE_BY_OWNER, "DELETE FROM petition_sign WHERE ownerguid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_PETITION_BY_OWNER_AND_TYPE, "DELETE FROM petition WHERE ownerguid = ? AND type = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_PETITION_SIGNATURE_BY_OWNER_AND_TYPE, "DELETE ps FROM petition_sign ps INNER JOIN petition p ON p.petition_id = ps.petition_id WHERE ps.ownerguid = ? AND p.type = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_INS_CHAR_GLYPHS, "INSERT INTO character_glyphs VALUES(?, ?, ?, ?, ?, ?, ?, ?)", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_CHAR_TALENT_BY_SPELL, "DELETE FROM character_talent WHERE guid = ? AND spell = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_INS_CHAR_TALENT, "INSERT INTO character_talent (guid, spell, specMask) VALUES (?, ?, ?)"
                     "ON DUPLICATE KEY UPDATE specMask = VALUES(specMask)", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_CHAR_ACTION_EXCEPT_SPEC, "DELETE FROM character_action WHERE spec<>? AND guid = ?", CONNECTION_ASYNC);

    // Items that hold loot or money
    PrepareStatement(CHAR_SEL_ITEMCONTAINER_ITEMS, "SELECT containerGUID, itemid, item_index, count, randomPropertyId, randomSuffix, follow_loot_rules, freeforall, is_blocked, is_counted, is_underthreshold, needs_quest, conditionLootId FROM item_loot_storage", CONNECTION_SYNCH);
    PrepareStatement(CHAR_DEL_ITEMCONTAINER_SINGLE_ITEM, "DELETE FROM item_loot_storage WHERE containerGUID = ? AND itemid = ? AND count = ? AND item_index = ? LIMIT 1", CONNECTION_ASYNC);
    PrepareStatement(CHAR_INS_ITEMCONTAINER_SINGLE_ITEM, "INSERT INTO item_loot_storage (containerGUID, itemid, item_index, count, randomPropertyId, randomSuffix, follow_loot_rules, freeforall, is_blocked, is_counted, is_underthreshold, needs_quest, conditionLootId) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_ITEMCONTAINER_CONTAINER, "DELETE FROM item_loot_storage WHERE containerGUID = ?", CONNECTION_ASYNC);

    // Calendar
    PrepareStatement(CHAR_REP_CALENDAR_EVENT, "REPLACE INTO calendar_events (id, creator, title, description, type, dungeon, eventtime, flags, time2) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_CALENDAR_EVENT, "DELETE FROM calendar_events WHERE id = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_REP_CALENDAR_INVITE, "REPLACE INTO calendar_invites (id, event, invitee, sender, status, statustime, `rank`, text) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_CALENDAR_INVITE, "DELETE FROM calendar_invites WHERE id = ?", CONNECTION_ASYNC);

    // Pet
    PrepareStatement(CHAR_SEL_CHAR_PET_IDS, "SELECT id FROM character_pet WHERE owner = ?", CONNECTION_SYNCH);
    PrepareStatement(CHAR_DEL_CHAR_PET_DECLINEDNAME_BY_OWNER, "DELETE FROM character_pet_declinedname WHERE owner = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_CHAR_PET_DECLINEDNAME, "DELETE FROM character_pet_declinedname WHERE id = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_ADD_CHAR_PET_DECLINEDNAME, "INSERT INTO character_pet_declinedname (id, owner, genitive, dative, accusative, instrumental, prepositional) VALUES (?, ?, ?, ?, ?, ?, ?)", CONNECTION_ASYNC);
    PrepareStatement(CHAR_SEL_PET_DECLINED_NAME, "SELECT genitive, dative, accusative, instrumental, prepositional FROM character_pet_declinedname WHERE owner = ? AND id = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_SEL_PET_AURA, "SELECT casterGuid, spell, effectMask, recalculateMask, stackCount, amount0, amount1, amount2, base_amount0, base_amount1, base_amount2, maxDuration, remainTime, remainCharges FROM pet_aura WHERE guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_SEL_PET_SPELL, "SELECT spell, active FROM pet_spell WHERE guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_SEL_PET_SPELL_COOLDOWN, "SELECT spell, category, time FROM pet_spell_cooldown WHERE guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_PET_AURAS, "DELETE FROM pet_aura WHERE guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_PET_SPELLS, "DELETE FROM pet_spell WHERE guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_PET_SPELL_COOLDOWNS, "DELETE FROM pet_spell_cooldown WHERE guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_INS_PET_SPELL_COOLDOWN, "INSERT INTO pet_spell_cooldown (guid, spell, category, time) VALUES (?, ?, ?, ?)", CONNECTION_ASYNC);
    PrepareStatement(CHAR_INS_PET_SPELL, "INSERT INTO pet_spell (guid, spell, active) VALUES (?, ?, ?)", CONNECTION_ASYNC);
    PrepareStatement(CHAR_INS_PET_AURA, "INSERT INTO pet_aura (guid, casterGuid, spell, effectMask, recalculateMask, stackCount, amount0, amount1, amount2, "
                     "base_amount0, base_amount1, base_amount2, maxDuration, remainTime, remainCharges) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", CONNECTION_ASYNC);
    PrepareStatement(CHAR_SEL_CHAR_PETS, "SELECT id, entry, modelid, level, exp, Reactstate, slot, name, renamed, curhealth, curmana, curhappiness, abdata, savetime, CreatedBySpell, PetType FROM character_pet WHERE owner = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_CHAR_PET_BY_OWNER, "DELETE FROM character_pet WHERE owner = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_UPD_CHAR_PET_NAME, "UPDATE character_pet SET name = ?, renamed = 1 WHERE owner = ? AND id = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_UPD_CHAR_PET_SLOT_BY_ID, "UPDATE character_pet SET slot = ? WHERE owner = ? AND id = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_CHAR_PET_BY_ID, "DELETE FROM character_pet WHERE id = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_CHAR_PET_BY_SLOT, "DELETE FROM character_pet WHERE owner = ? AND (slot = ? OR slot > ?)", CONNECTION_ASYNC);
    PrepareStatement(CHAR_REP_CHAR_PET, "REPLACE INTO character_pet (id, entry, owner, modelid, CreatedBySpell, PetType, level, exp, Reactstate, name, renamed, slot, curhealth, curmana, curhappiness, savetime, abdata) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", CONNECTION_ASYNC);

    // PvPstats
    PrepareStatement(CHAR_SEL_PVPSTATS_MAXID, "SELECT MAX(id) FROM pvpstats_battlegrounds", CONNECTION_SYNCH);
    PrepareStatement(CHAR_INS_PVPSTATS_BATTLEGROUND, "INSERT INTO pvpstats_battlegrounds (id, winner_faction, bracket_id, type, date) VALUES (?, ?, ?, ?, NOW())", CONNECTION_ASYNC);
    PrepareStatement(CHAR_INS_PVPSTATS_PLAYER, "INSERT INTO pvpstats_players (battleground_id, character_guid, winner, score_killing_blows, score_deaths, score_honorable_kills, score_bonus_honor, score_damage_done, score_healing_done, attr_1, attr_2, attr_3, attr_4, attr_5) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", CONNECTION_ASYNC);
    PrepareStatement(CHAR_SEL_PVPSTATS_FACTIONS_OVERALL, "SELECT winner_faction, COUNT(*) AS count FROM pvpstats_battlegrounds WHERE DATEDIFF(NOW(), date) < 7 GROUP BY winner_faction ORDER BY winner_faction ASC", CONNECTION_SYNCH);
    PrepareStatement(CHAR_SEL_PVPSTATS_BRACKET_MONTH, "SELECT character_guid, COUNT(character_guid) AS count, characters.name as character_name FROM pvpstats_players INNER JOIN pvpstats_battlegrounds ON pvpstats_players.battleground_id = pvpstats_battlegrounds.id AND bracket_id = ? AND MONTH(date) = MONTH(NOW()) AND YEAR(date) = YEAR(NOW()) INNER JOIN characters ON pvpstats_players.character_guid = characters.guid AND characters.deleteDate IS NULL WHERE pvpstats_players.winner = 1 GROUP BY character_guid ORDER BY count(character_guid) DESC LIMIT 0, ?", CONNECTION_SYNCH);

    // Deserter tracker
    PrepareStatement(CHAR_INS_DESERTER_TRACK, "INSERT INTO battleground_deserters (guid, type, datetime) VALUES (?, ?, NOW())", CONNECTION_ASYNC);

    // QuestTracker
    PrepareStatement(CHAR_INS_QUEST_TRACK, "INSERT INTO quest_tracker (id, character_guid, quest_accept_time, core_hash, core_revision) VALUES (?, ?, NOW(), ?, ?)", CONNECTION_ASYNC);
    PrepareStatement(CHAR_UPD_QUEST_TRACK_GM_COMPLETE, "UPDATE quest_tracker SET completed_by_gm = 1 WHERE id = ? AND character_guid = ? ORDER BY quest_accept_time DESC LIMIT 1", CONNECTION_ASYNC);
    PrepareStatement(CHAR_UPD_QUEST_TRACK_COMPLETE_TIME, "UPDATE quest_tracker SET quest_complete_time = NOW() WHERE id = ? AND character_guid = ? ORDER BY quest_accept_time DESC LIMIT 1", CONNECTION_ASYNC);
    PrepareStatement(CHAR_UPD_QUEST_TRACK_ABANDON_TIME, "UPDATE quest_tracker SET quest_abandon_time = NOW() WHERE id = ? AND character_guid = ? ORDER BY quest_accept_time DESC LIMIT 1", CONNECTION_ASYNC);

    // Recovery Item
    PrepareStatement(CHAR_INS_RECOVERY_ITEM, "INSERT INTO recovery_item (Guid, ItemEntry, Count, DeleteDate) VALUES (?, ?, ?, UNIX_TIMESTAMP())", CONNECTION_SYNCH);
    PrepareStatement(CHAR_SEL_RECOVERY_ITEM, "SELECT id, itemEntry, Count, Guid FROM recovery_item WHERE id = ?", CONNECTION_SYNCH);
    PrepareStatement(CHAR_SEL_RECOVERY_ITEM_LIST, "SELECT id, itemEntry, Count FROM recovery_item WHERE Guid = ? ORDER BY id DESC", CONNECTION_SYNCH);
    PrepareStatement(CHAR_DEL_RECOVERY_ITEM, "DELETE FROM recovery_item WHERE Guid = ? AND ItemEntry = ? AND Count = ? ORDER BY Id DESC LIMIT 1", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_RECOVERY_ITEM_BY_RECOVERY_ID, "DELETE FROM recovery_item WHERE id = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_SEL_RECOVERY_ITEM_OLD_ITEMS, "SELECT Guid, ItemEntry FROM recovery_item WHERE DeleteDate IS NOT NULL AND DeleteDate < ?", CONNECTION_SYNCH);
    PrepareStatement(CHAR_DEL_RECOVERY_ITEM_BY_GUID, "DELETE FROM recovery_item WHERE Guid = ?", CONNECTION_ASYNC);

    PrepareStatement(CHAR_SEL_HONORPOINTS, "SELECT totalHonorPoints FROM characters WHERE guid = ?", CONNECTION_SYNCH);
    PrepareStatement(CHAR_SEL_ARENAPOINTS, "SELECT arenaPoints FROM characters WHERE guid = ?", CONNECTION_SYNCH);

    // Character names
    PrepareStatement(CHAR_INS_RESERVED_PLAYER_NAME, "INSERT IGNORE INTO reserved_name (name) VALUES (?)", CONNECTION_ASYNC);
    PrepareStatement(CHAR_INS_PROFANITY_PLAYER_NAME, "INSERT IGNORE INTO profanity_name (name) VALUES (?)", CONNECTION_ASYNC);

    // Chat filter
    PrepareStatement(CHAR_SEL_CHAT_FILTER, "SELECT ID, Word FROM chat_filter ORDER BY ID", CONNECTION_SYNCH);
    PrepareStatement(CHAR_SEL_CHAT_FILTER_WORD, "SELECT ID FROM chat_filter WHERE Word = ?", CONNECTION_SYNCH);
    PrepareStatement(CHAR_INS_CHAT_FILTER_WORD, "INSERT INTO chat_filter (Word) VALUES (?)", CONNECTION_SYNCH);
    PrepareStatement(CHAR_DEL_CHAT_FILTER_WORD, "DELETE FROM chat_filter WHERE Word = ?", CONNECTION_SYNCH);

    // Character settings
    PrepareStatement(CHAR_SEL_CHAR_SETTINGS, "SELECT source, data FROM character_settings WHERE guid = ?", CONNECTION_BOTH);
    PrepareStatement(CHAR_REP_CHAR_SETTINGS, "REPLACE INTO character_settings (guid, source, data) VALUES (?, ?, ?)", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_CHAR_SETTINGS, "DELETE FROM character_settings WHERE guid = ?", CONNECTION_ASYNC);

    // Instance saved data. Stores the states of gameobjects in instances to be loaded on server start
    PrepareStatement(CHAR_SELECT_INSTANCE_SAVED_DATA, "SELECT guid, state FROM instance_saved_go_state_data WHERE id = ?", CONNECTION_SYNCH);
    PrepareStatement(CHAR_INSERT_INSTANCE_SAVED_DATA, "INSERT INTO instance_saved_go_state_data (id, guid, state) VALUES (?, ?, ?)"
        "ON DUPLICATE KEY UPDATE state = VALUES(state)", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DELETE_INSTANCE_SAVED_DATA, "DELETE FROM instance_saved_go_state_data WHERE id = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_SANITIZE_INSTANCE_SAVED_DATA, "DELETE FROM instance_saved_go_state_data WHERE id NOT IN (SELECT instance.id FROM instance)", CONNECTION_ASYNC);

    // world_state
    PrepareStatement(CHAR_SEL_WORLD_STATE, "SELECT Id, Data FROM world_state", CONNECTION_SYNCH);
    PrepareStatement(CHAR_REP_WORLD_STATE, "REPLACE INTO world_state (Id, Data) VALUES(?, ?)", CONNECTION_ASYNC);

    PrepareStatement(CHAR_SEL_DIGITAL_STORAGE,
        "SELECT capacity, revision FROM character_digital_storage WHERE guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_SEL_DIGITAL_ITEMS,
        "SELECT ii.creatorGuid, ii.giftCreatorGuid, ii.count, ii.duration, ii.charges, ii.flags, ii.enchantments, "
        "ii.randomPropertyId, ii.durability, ii.playedTime, ii.text, ds.item, ii.itemEntry, ds.favorite, ii.owner_guid, "
        "(EXISTS(SELECT 1 FROM character_inventory ci WHERE ci.item = ds.item) "
        "OR EXISTS(SELECT 1 FROM mail_items mi WHERE mi.item_guid = ds.item) "
        "OR EXISTS(SELECT 1 FROM auctionhouse ah WHERE ah.itemguid = ds.item) "
        "OR EXISTS(SELECT 1 FROM guild_bank_item gb WHERE gb.item_guid = ds.item)), ds.tag, ds.split "
        "FROM character_digital_storage_item ds LEFT JOIN item_instance ii ON ii.guid = ds.item WHERE ds.guid = ?",
        CONNECTION_ASYNC);
    PrepareStatement(CHAR_REP_DIGITAL_STORAGE,
        "REPLACE INTO character_digital_storage (guid, capacity, revision) VALUES (?, ?, ?)", CONNECTION_ASYNC);
    PrepareStatement(CHAR_REP_DIGITAL_ITEM,
        "REPLACE INTO character_digital_storage_item (guid, item, favorite, tag, split) VALUES (?, ?, ?, ?, ?)", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_DIGITAL_ITEM,
        "DELETE FROM character_digital_storage_item WHERE guid = ? AND item = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_DIGITAL_STORAGE_OWNER,
        "DELETE FROM character_digital_storage WHERE guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_DIGITAL_ITEMS_OWNER,
        "DELETE FROM character_digital_storage_item WHERE guid = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_DIGITAL_ITEM_BY_GUID,
        "DELETE FROM character_digital_storage_item WHERE item = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_UPD_GUILD_BANK_TAB_SLOTS, "UPDATE guild_bank_tab SET slots = ? WHERE guildid = ? AND TabId = ?", CONNECTION_ASYNC);
    PrepareStatement(CHAR_SEL_ACCOUNT_BANK,
        "SELECT capacity, revision, unlocked FROM account_bank WHERE account = ?", CONNECTION_SYNCH);
    PrepareStatement(CHAR_SEL_ACCOUNT_BANK_ITEMS,
        "SELECT ii.creatorGuid, ii.giftCreatorGuid, ii.count, ii.duration, ii.charges, ii.flags, ii.enchantments, "
        "ii.randomPropertyId, ii.durability, ii.playedTime, ii.text, ab.item, ii.itemEntry, ab.favorite, ii.owner_guid, "
        "(EXISTS(SELECT 1 FROM character_inventory ci WHERE ci.item = ab.item) "
        "OR EXISTS(SELECT 1 FROM mail_items mi WHERE mi.item_guid = ab.item) "
        "OR EXISTS(SELECT 1 FROM auctionhouse ah WHERE ah.itemguid = ab.item) "
        "OR EXISTS(SELECT 1 FROM guild_bank_item gb WHERE gb.item_guid = ab.item) "
        "OR EXISTS(SELECT 1 FROM character_digital_storage_item ds WHERE ds.item = ab.item)), ab.tag, ab.split "
        "FROM account_bank_item ab LEFT JOIN item_instance ii ON ii.guid = ab.item WHERE ab.account = ?",
        CONNECTION_SYNCH);
    PrepareStatement(CHAR_REP_ACCOUNT_BANK,
        "REPLACE INTO account_bank (account, capacity, revision, unlocked) VALUES (?, ?, ?, ?)", CONNECTION_ASYNC);
    PrepareStatement(CHAR_REP_ACCOUNT_BANK_ITEM,
        "REPLACE INTO account_bank_item (account, item, favorite, tag, split) VALUES (?, ?, ?, ?, ?)", CONNECTION_ASYNC);
    PrepareStatement(CHAR_DEL_ACCOUNT_BANK_ITEM,
        "DELETE FROM account_bank_item WHERE account = ? AND item = ?", CONNECTION_ASYNC);

    // CHAR_NO_OP_PROVIDE_REALM_CONTEXT is a no-op query that accepts a single parameter: the realm ID.
    // This query is used specifically in cross-realm scenarios when the database transaction
    // lacks sufficient context to determine which realm's database the query should target.
    // By providing the realm ID explicitly, this ensures that mysql reverse proxy will use
    // correct realm database for the transaction.
    PrepareStatement(CHAR_NO_OP_PROVIDE_REALM_CONTEXT, "SELECT ? AS no_op", CONNECTION_ASYNC);
}

CharacterDatabaseConnection::CharacterDatabaseConnection(MySQLConnectionInfo& connInfo) : MySQLConnection(connInfo)
{
}

CharacterDatabaseConnection::CharacterDatabaseConnection(ProducerConsumerQueue<SQLOperation*>* q, MySQLConnectionInfo& connInfo) : MySQLConnection(q, connInfo)
{
}

CharacterDatabaseConnection::~CharacterDatabaseConnection()
{
}
````
<!-- END FULL SOURCE 1 -->

### Appendix 2 CharacterHandler.cpp

Originally linked server roster source.

Source: `src/server/game/Handlers/CharacterHandler.cpp`  
Absolute path: `R:\Users\Zach\Documents\GitHub\EsteriaWoW\src\server\game\Handlers\CharacterHandler.cpp`  
Source lines: 1 through 3063  
SHA256: `87e64a388b83e27c36d5593de56e92b1bfa04bdb1c042a2331c1e7555288e0d4`

<!-- BEGIN FULL SOURCE 2 -->
````cpp
/*
 * This file is part of the AzerothCore Project. See AUTHORS file for Copyright information
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful, but WITHOUT
 * ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
 * FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for
 * more details.
 *
 * You should have received a copy of the GNU General Public License along
 * with this program. If not, see <http://www.gnu.org/licenses/>.
 */

#include "AccountMgr.h"
#include "AreaDefines.h"
#include "RBAC.h"
#include "ArenaTeamMgr.h"
#include "AuctionHouseMgr.h"
#include "Battleground.h"
#include "CalendarMgr.h"
#include "CharacterCache.h"
#include "CharacterPackets.h"
#include "Chat.h"
#include "Common.h"
#include "DatabaseEnv.h"
#include "GameTime.h"
#include "GitRevision.h"
#include "Group.h"
#include "HighmountainAppearance.h"
#include "EarthenAppearance.h"
#include "HaranirAppearance.h"
#include "BodyShapeWire.h"
#include "RetailLookWire.h"
#include "EyeEffects.h"
#include "Guild.h"
#include "GuildMgr.h"
#include "InstanceSaveMgr.h"
#include "Language.h"
#include "Log.h"
#include "MapMgr.h"
#include "Metric.h"
#include "MotdMgr.h"
#include "ObjectAccessor.h"
#include "ObjectMgr.h"
#include "Opcodes.h"
#include "Pet.h"
#include "Player.h"
#include "PlayerDump.h"
#include "QueryHolder.h"
#include "RaceMgr.h"
#include "Realm.h"
#include "ReputationMgr.h"
#include "ScriptMgr.h"
#include "SharedDefines.h"
#include "SocialMgr.h"
#include "SpellAuraEffects.h"
#include "SpellAuras.h"
#include "SpellMgr.h"
#include "StringConvert.h"
#include "TC9Sidecar.h"
#include "Tokenize.h"
#include "Transport.h"
#include "Util.h"
#include "VulperaAppearance.h"
#include "World.h"
#include "WorldPacket.h"
#include "WorldSession.h"
#include "WorldSessionMgr.h"

#include <unordered_map>

LoginQueryHolder::LoginQueryHolder(uint32 accountId, ObjectGuid guid) : m_accountId(accountId), m_guid(guid)
{
}

bool LoginQueryHolder::Initialize()
{
    SetSize(MAX_PLAYER_LOGIN_QUERY);

    bool res = true;
    uint64 rawGUID = m_guid.GetRawValue();

    CharacterDatabasePreparedStatement* stmt = CharacterDatabase.GetPreparedStatement(CHAR_SEL_CHARACTER);
    stmt->SetData(0, rawGUID);
    res &= SetPreparedQuery(PLAYER_LOGIN_QUERY_LOAD_FROM, stmt);

    stmt = CharacterDatabase.GetPreparedStatement(CHAR_SEL_CHARACTER_AURAS);
    stmt->SetData(0, rawGUID);
    res &= SetPreparedQuery(PLAYER_LOGIN_QUERY_LOAD_AURAS, stmt);

    stmt = CharacterDatabase.GetPreparedStatement(CHAR_SEL_CHARACTER_SPELL);
    stmt->SetData(0, rawGUID);
    res &= SetPreparedQuery(PLAYER_LOGIN_QUERY_LOAD_SPELLS, stmt);

    stmt = CharacterDatabase.GetPreparedStatement(CHAR_SEL_CHARACTER_QUESTSTATUS);
    stmt->SetData(0, rawGUID);
    res &= SetPreparedQuery(PLAYER_LOGIN_QUERY_LOAD_QUEST_STATUS, stmt);

    stmt = CharacterDatabase.GetPreparedStatement(CHAR_SEL_CHARACTER_DAILYQUESTSTATUS);
    stmt->SetData(0, rawGUID);
    res &= SetPreparedQuery(PLAYER_LOGIN_QUERY_LOAD_DAILY_QUEST_STATUS, stmt);

    stmt = CharacterDatabase.GetPreparedStatement(CHAR_SEL_CHARACTER_WEEKLYQUESTSTATUS);
    stmt->SetData(0, rawGUID);
    res &= SetPreparedQuery(PLAYER_LOGIN_QUERY_LOAD_WEEKLY_QUEST_STATUS, stmt);

    stmt = CharacterDatabase.GetPreparedStatement(CHAR_SEL_CHARACTER_MONTHLYQUESTSTATUS);
    stmt->SetData(0, rawGUID);
    res &= SetPreparedQuery(PLAYER_LOGIN_QUERY_LOAD_MONTHLY_QUEST_STATUS, stmt);

    stmt = CharacterDatabase.GetPreparedStatement(CHAR_SEL_CHARACTER_SEASONALQUESTSTATUS);
    stmt->SetData(0, rawGUID);
    res &= SetPreparedQuery(PLAYER_LOGIN_QUERY_LOAD_SEASONAL_QUEST_STATUS, stmt);

    stmt = CharacterDatabase.GetPreparedStatement(CHAR_SEL_CHARACTER_REPUTATION);
    stmt->SetData(0, rawGUID);
    res &= SetPreparedQuery(PLAYER_LOGIN_QUERY_LOAD_REPUTATION, stmt);

    stmt = CharacterDatabase.GetPreparedStatement(CHAR_SEL_CHARACTER_INVENTORY);
    stmt->SetData(0, rawGUID);
    res &= SetPreparedQuery(PLAYER_LOGIN_QUERY_LOAD_INVENTORY, stmt);

    stmt = CharacterDatabase.GetPreparedStatement(CHAR_SEL_DIGITAL_STORAGE);
    stmt->SetData(0, rawGUID);
    res &= SetPreparedQuery(PLAYER_LOGIN_QUERY_LOAD_DIGITAL_STORAGE, stmt);

    stmt = CharacterDatabase.GetPreparedStatement(CHAR_SEL_DIGITAL_ITEMS);
    stmt->SetData(0, rawGUID);
    res &= SetPreparedQuery(PLAYER_LOGIN_QUERY_LOAD_DIGITAL_ITEMS, stmt);

    stmt = CharacterDatabase.GetPreparedStatement(CHAR_SEL_CHARACTER_ACTIONS);
    stmt->SetData(0, rawGUID);
    res &= SetPreparedQuery(PLAYER_LOGIN_QUERY_LOAD_ACTIONS, stmt);

    stmt = CharacterDatabase.GetPreparedStatement(CHAR_SEL_MAIL);
    stmt->SetData(0, rawGUID);

    res &= SetPreparedQuery(PLAYER_LOGIN_QUERY_LOAD_MAILS, stmt);

    stmt = CharacterDatabase.GetPreparedStatement(CHAR_SEL_MAILITEMS);
    stmt->SetData(0, rawGUID);
    res &= SetPreparedQuery(PLAYER_LOGIN_QUERY_LOAD_MAIL_ITEMS, stmt);

    stmt = CharacterDatabase.GetPreparedStatement(CHAR_SEL_CHARACTER_SOCIALLIST);
    stmt->SetData(0, rawGUID);
    res &= SetPreparedQuery(PLAYER_LOGIN_QUERY_LOAD_SOCIAL_LIST, stmt);

    stmt = CharacterDatabase.GetPreparedStatement(CHAR_SEL_CHARACTER_HOMEBIND);
    stmt->SetData(0, rawGUID);
    res &= SetPreparedQuery(PLAYER_LOGIN_QUERY_LOAD_HOME_BIND, stmt);

    stmt = CharacterDatabase.GetPreparedStatement(CHAR_SEL_CHARACTER_SPELLCOOLDOWNS);
    stmt->SetData(0, rawGUID);
    res &= SetPreparedQuery(PLAYER_LOGIN_QUERY_LOAD_SPELL_COOLDOWNS, stmt);

    if (sWorld->getBoolConfig(CONFIG_DECLINED_NAMES_USED))
    {
        stmt = CharacterDatabase.GetPreparedStatement(CHAR_SEL_CHARACTER_DECLINEDNAMES);
        stmt->SetData(0, rawGUID);
        res &= SetPreparedQuery(PLAYER_LOGIN_QUERY_LOAD_DECLINED_NAMES, stmt);
    }

    stmt = CharacterDatabase.GetPreparedStatement(CHAR_SEL_CHARACTER_ACHIEVEMENTS);
    stmt->SetData(0, rawGUID);
    res &= SetPreparedQuery(PLAYER_LOGIN_QUERY_LOAD_ACHIEVEMENTS, stmt);

    stmt = CharacterDatabase.GetPreparedStatement(CHAR_SEL_CHARACTER_CRITERIAPROGRESS);
    stmt->SetData(0, rawGUID);
    res &= SetPreparedQuery(PLAYER_LOGIN_QUERY_LOAD_CRITERIA_PROGRESS, stmt);

    stmt = CharacterDatabase.GetPreparedStatement(CHAR_SEL_CHARACTER_EQUIPMENTSETS);
    stmt->SetData(0, rawGUID);
    res &= SetPreparedQuery(PLAYER_LOGIN_QUERY_LOAD_EQUIPMENT_SETS, stmt);

    stmt = CharacterDatabase.GetPreparedStatement(CHAR_SEL_CHARACTER_ENTRY_POINT);
    stmt->SetData(0, rawGUID);
    res &= SetPreparedQuery(PLAYER_LOGIN_QUERY_LOAD_ENTRY_POINT, stmt);

    stmt = CharacterDatabase.GetPreparedStatement(CHAR_SEL_CHARACTER_GLYPHS);
    stmt->SetData(0, rawGUID);
    res &= SetPreparedQuery(PLAYER_LOGIN_QUERY_LOAD_GLYPHS, stmt);

    stmt = CharacterDatabase.GetPreparedStatement(CHAR_SEL_CHARACTER_TALENTS);
    stmt->SetData(0, rawGUID);
    res &= SetPreparedQuery(PLAYER_LOGIN_QUERY_LOAD_TALENTS, stmt);

    stmt = CharacterDatabase.GetPreparedStatement(CHAR_SEL_PLAYER_ACCOUNT_DATA);
    stmt->SetData(0, rawGUID);
    res &= SetPreparedQuery(PLAYER_LOGIN_QUERY_LOAD_ACCOUNT_DATA, stmt);

    stmt = CharacterDatabase.GetPreparedStatement(CHAR_SEL_CHARACTER_SKILLS);
    stmt->SetData(0, rawGUID);
    res &= SetPreparedQuery(PLAYER_LOGIN_QUERY_LOAD_SKILLS, stmt);

    stmt = CharacterDatabase.GetPreparedStatement(CHAR_SEL_CHARACTER_RANDOMBG);
    stmt->SetData(0, rawGUID);
    res &= SetPreparedQuery(PLAYER_LOGIN_QUERY_LOAD_RANDOM_BG, stmt);

    stmt = CharacterDatabase.GetPreparedStatement(CHAR_SEL_CHARACTER_BANNED);
    stmt->SetData(0, rawGUID);
    res &= SetPreparedQuery(PLAYER_LOGIN_QUERY_LOAD_BANNED, stmt);

    stmt = CharacterDatabase.GetPreparedStatement(CHAR_SEL_CHARACTER_QUESTSTATUSREW);
    stmt->SetData(0, rawGUID);
    res &= SetPreparedQuery(PLAYER_LOGIN_QUERY_LOAD_QUEST_STATUS_REW, stmt);

    stmt = CharacterDatabase.GetPreparedStatement(CHAR_SEL_BREW_OF_THE_MONTH);
    stmt->SetData(0, rawGUID);
    res &= SetPreparedQuery(PLAYER_LOGIN_QUERY_LOAD_BREW_OF_THE_MONTH, stmt);

    stmt = CharacterDatabase.GetPreparedStatement(CHAR_SEL_ACCOUNT_INSTANCELOCKTIMES);
    stmt->SetData(0, m_accountId);
    res &= SetPreparedQuery(PLAYER_LOGIN_QUERY_LOAD_INSTANCE_LOCK_TIMES, stmt);

    stmt = CharacterDatabase.GetPreparedStatement(CHAR_SEL_CORPSE_LOCATION);
    stmt->SetData(0, rawGUID);
    res &= SetPreparedQuery(PLAYER_LOGIN_QUERY_LOAD_CORPSE_LOCATION, stmt);

    stmt = CharacterDatabase.GetPreparedStatement(CHAR_SEL_CHAR_SETTINGS);
    stmt->SetData(0, rawGUID);
    res &= SetPreparedQuery(PLAYER_LOGIN_QUERY_LOAD_CHARACTER_SETTINGS, stmt);

    stmt = CharacterDatabase.GetPreparedStatement(CHAR_SEL_CHAR_PETS);
    stmt->SetData(0, rawGUID);
    res &= SetPreparedQuery(PLAYER_LOGIN_QUERY_LOAD_PET_SLOTS, stmt);

    stmt = CharacterDatabase.GetPreparedStatement(CHAR_SEL_CHAR_ACHIEVEMENT_OFFLINE_UPDATES);
    stmt->SetData(0, rawGUID);
    res &= SetPreparedQuery(PLAYER_LOGIN_QUERY_LOAD_OFFLINE_ACHIEVEMENTS_UPDATES, stmt);

    stmt = CharacterDatabase.GetPreparedStatement(CHAR_SEL_BODY_SHAPE);
    stmt->SetData(0, rawGUID);
    res &= SetPreparedQuery(PLAYER_LOGIN_QUERY_LOAD_BODY_SHAPE, stmt);

    stmt = CharacterDatabase.GetPreparedStatement(CHAR_SEL_RETAIL_LOOK);
    stmt->SetData(0, rawGUID);
    res &= SetPreparedQuery(PLAYER_LOGIN_QUERY_LOAD_RETAIL_LOOK, stmt);

    return res;
}

void WorldSession::HandleCharEnum(PreparedQueryResult result, PreparedQueryResult permanentAuras, PreparedQueryResult bodyShape, PreparedQueryResult retailLook)
{
    // Saved full Retail looks, by character (opaque to the server; only structurally checked).
    std::unordered_map<uint32, std::array<uint8, CharacterRetailLook::PayloadSize>> retailLooks;
    if (retailLook)
    {
        do
        {
            auto const payload = (*retailLook)[1].Get<Binary, CharacterRetailLook::PayloadSize>();
            CharacterRetailLook::Look look;
            if (CharacterRetailLook::ReadPayload(payload.data(), payload.size(), look))
                retailLooks[(*retailLook)[0].Get<uint32>()] = payload;
        } while (retailLook->NextRow());
    }

    // Saved body sliders, by character. Rows that are not a valid payload are ignored.
    std::unordered_map<uint32, std::array<uint8, CharacterBodyShape::PayloadSize>> bodyShapes;
    if (bodyShape)
    {
        do
        {
            auto const payload = (*bodyShape)[1].Get<Binary, CharacterBodyShape::PayloadSize>();
            CharacterBodyShape::Values values{};
            if (CharacterBodyShape::ReadPayload(payload.data(), payload.size(), values) && !CharacterBodyShape::AllDefault(values))
                bodyShapes[(*bodyShape)[0].Get<uint32>()] = payload;
        } while (bodyShape->NextRow());
    }
    // Cosmetics' server skill mapping is intentionally absent for classless characters.
    // The existing exclusive wing group identifies equipped wings without changing spell ownership.
    std::unordered_map<uint32, uint32> wings;
    if (permanentAuras)
    {
        do
        {
            uint32 spell = (*permanentAuras)[1].Get<uint32>();
            if (sSpellMgr->IsSpellMemberOfSpellGroup(spell, SpellGroup(9100)))
                wings[(*permanentAuras)[0].Get<uint32>()] = spell;
        } while (permanentAuras->NextRow());
    }

    WorldPacket data(SMSG_CHAR_ENUM, 100);                  // we guess size

    uint8 num = 0;
    ByteBuffer extraAppearances;
    uint32 extraCount = 0;
    ByteBuffer haranirAppearances;
    uint32 haranirCount = 0;
    ByteBuffer cosmeticWings;
    uint32 wingCount = 0;
    ByteBuffer bodyShapeBlock;
    uint32 bodyShapeCount = 0;
    ByteBuffer retailLookBlock;
    uint32 retailLookCount = 0;

    data << num;

    _legitCharacters.clear();
    if (result)
    {
        do
        {
            ObjectGuid guid = ObjectGuid::Create<HighGuid::Player>((*result)[0].Get<uint32>());
            LOG_DEBUG("network.opcode", "Loading char {} from account {}.", guid.ToString(), GetAccountId());
            if (Player::BuildEnumData(result, &data))
            {
                _legitCharacters.insert(guid);
                ++num;
                if (auto wing = wings.find((*result)[0].Get<uint32>()); wing != wings.end())
                {
                    cosmeticWings << guid.GetRawValue() << wing->second;
                    ++wingCount;
                }
                if (auto const look = retailLooks.find((*result)[0].Get<uint32>()); look != retailLooks.end())
                {
                    retailLookBlock << guid.GetRawValue();
                    retailLookBlock.append(look->second.data(), look->second.size());
                    ++retailLookCount;
                }
                if (auto const shape = bodyShapes.find((*result)[0].Get<uint32>()); shape != bodyShapes.end())
                {
                    bodyShapeBlock << guid.GetRawValue();
                    bodyShapeBlock.append(shape->second.data(), shape->second.size());
                    ++bodyShapeCount;
                }
                uint64 const extra = (*result)[result->GetFieldCount() - 2].Get<uint64>();
                if (UsesHaranirAppearance((*result)[2].Get<uint8>()) || CharacterEyeEffects::Lightning(extra))
                {
                    haranirAppearances << guid.GetRawValue() << extra;
                    ++haranirCount;
                }
                else if (UsesExtendedAppearance((*result)[2].Get<uint8>()))
                {
                    extraAppearances << guid.GetRawValue()
                        << uint8((*result)[result->GetFieldCount() - 2].Get<uint64>());
                    ++extraCount;
                }
            }
        } while (result->NextRow());
    }

    data.put<uint8>(0, num);
    if (extraCount)
    {
        data.append(extraAppearances);
        data << extraCount << uint32(0x31455848); // HXE1, consumed by the native client before stock parsing.
    }
    if (haranirCount)
    {
        data.append(haranirAppearances);
        data << haranirCount << uint32(0x32455848); // HXE2: GUID + uint64 extension.
    }

    if (wingCount)
    {
        data.append(cosmeticWings);
        data << wingCount << uint32(0x31475743); // CWG1: GUID + active wing spell, stripped before stock parsing.
    }

    if (bodyShapeCount)
    {
        data.append(bodyShapeBlock);
        data << bodyShapeCount << CharacterBodyShape::EnumMagic; // BSE1: GUID + body-slider payload, stripped by the native client.
    }

    if (retailLookCount)
    {
        data.append(retailLookBlock);
        data << retailLookCount << CharacterRetailLook::EnumMagic; // RLE1: GUID + full Retail look, stripped by the native client.
    }

    SendPacket(&data);
}

void WorldSession::HandleCharEnumOpcode(WorldPacket& /*recvData*/)
{
    CharacterDatabasePreparedStatement* stmt = nullptr;

    /// get all the data necessary for loading all characters (along with their pets) on the account

    if (sWorld->getBoolConfig(CONFIG_DECLINED_NAMES_USED))
        stmt = CharacterDatabase.GetPreparedStatement(CHAR_SEL_ENUM_DECLINED_NAME);
    else
        stmt = CharacterDatabase.GetPreparedStatement(CHAR_SEL_ENUM);

    stmt->SetData(0, PET_SAVE_AS_CURRENT);
    stmt->SetData(1, GetAccountId());

    _queryProcessor.AddCallback(CharacterDatabase.AsyncQuery(stmt).WithChainingPreparedCallback(
        [this](QueryCallback& callback, PreparedQueryResult result)
        {
            auto* auraStmt = CharacterDatabase.GetPreparedStatement(CHAR_SEL_ENUM_PERMANENT_AURAS);
            auraStmt->SetData(0, GetAccountId());
            callback.WithChainingPreparedCallback(
                [this, result](QueryCallback& nextCallback, PreparedQueryResult permanentAuras)
                {
                    auto* bodyShapeStmt = CharacterDatabase.GetPreparedStatement(CHAR_SEL_ENUM_BODY_SHAPE);
                    bodyShapeStmt->SetData(0, GetAccountId());
                    nextCallback.WithChainingPreparedCallback(
                        [this, result, permanentAuras](QueryCallback& lastCallback, PreparedQueryResult bodyShape)
                        {
                            auto* lookStmt = CharacterDatabase.GetPreparedStatement(CHAR_SEL_ENUM_RETAIL_LOOK);
                            lookStmt->SetData(0, GetAccountId());
                            lastCallback.WithPreparedCallback(
                                [this, result, permanentAuras, bodyShape](PreparedQueryResult retailLook)
                                {
                                    HandleCharEnum(result, permanentAuras, bodyShape, retailLook);
                                });
                            lastCallback.SetNextQuery(CharacterDatabase.AsyncQuery(lookStmt));
                        });
                    nextCallback.SetNextQuery(CharacterDatabase.AsyncQuery(bodyShapeStmt));
                });
            callback.SetNextQuery(CharacterDatabase.AsyncQuery(auraStmt));
        }));
}

void WorldSession::HandleCharCreateOpcode(WorldPacket& recvData)
{
    std::shared_ptr<CharacterCreateInfo> createInfo = std::make_shared<CharacterCreateInfo>();

    recvData >> createInfo->Name
        >> createInfo->Race
        >> createInfo->Class
        >> createInfo->Gender
        >> createInfo->Skin
        >> createInfo->Face
        >> createInfo->HairStyle
        >> createInfo->HairColor
        >> createInfo->FacialHair
        >> createInfo->OutfitId;

    if (createInfo->Race == RACE_SLIME_GIANT_ALLIANCE || createInfo->Race == RACE_CENTAUR_HORDE)
    {
        SendCharCreate(CHAR_CREATE_DISABLED);
        return;
    }

    if (!CharacterRetailLook::ReadTail(recvData, createInfo->HasRetailLook, createInfo->RetailLook)
        || (createInfo->HasRetailLook && (createInfo->RetailLook.race != createInfo->Race || createInfo->RetailLook.sex != createInfo->Gender)))
    {
        SendCharCreate(CHAR_CREATE_FAILED);
        return;
    }

    if (!CharacterBodyShape::ReadTail(recvData, createInfo->HasBodyShape, createInfo->BodyShape))
    {
        SendCharCreate(CHAR_CREATE_FAILED);
        return;
    }

    bool hasEyeLightning = false;
    if (!CharacterEyeEffects::ReadTail(recvData, UsesHaranirAppearance(createInfo->Race) ? 12 : 0,
        hasEyeLightning, createInfo->EyeLightning))
    {
        SendCharCreate(CHAR_CREATE_FAILED);
        return;
    }

    if (CreatureAppearance::Uses(createInfo->Race) && (createInfo->OutfitId != 0
        || recvData.rpos() != recvData.size() || !CreatureAppearance::Validate(createInfo->Race,
            createInfo->Gender, {createInfo->Skin, createInfo->Face, createInfo->HairStyle,
                createInfo->HairColor, createInfo->FacialHair})))
    {
        SendCharCreate(CHAR_CREATE_FAILED);
        return;
    }

    if (createInfo->Race == RACE_VULPERA && (createInfo->OutfitId != 0
        || recvData.rpos() != recvData.size() || !VulperaAppearance::ValidateClass(createInfo->Gender,
            createInfo->Class, VulperaAppearance::Fields(createInfo->Skin, createInfo->Face,
                createInfo->HairStyle, createInfo->HairColor, createInfo->FacialHair))))
    {
        SendCharCreate(CHAR_CREATE_FAILED);
        return;
    }

    if (UsesHaranirAppearance(createInfo->Race))
    {
        if (recvData.size() - recvData.rpos() != 12)
        {
            SendCharCreate(CHAR_CREATE_FAILED);
            return;
        }
        uint32 magic = 0;
        recvData >> createInfo->HaranirExtra >> magic;
        if (magic != 0x31435248 || !HaranirAppearance::Validate(createInfo->Gender,
            HaranirAppearance::Fields(createInfo->Skin, createInfo->Face, createInfo->HairStyle,
                createInfo->HairColor, createInfo->FacialHair, createInfo->HaranirExtra)))
        {
            SendCharCreate(CHAR_CREATE_FAILED);
            return;
        }
    }

    // The stock outfit byte is unused by this core; extended profiles use it as their sixth appearance byte.
    std::array<uint8, 6> const appearance = {createInfo->Skin, createInfo->Face, createInfo->HairStyle,
        createInfo->HairColor, createInfo->FacialHair, createInfo->OutfitId};
    if (UsesExtendedAppearance(createInfo->Race)
        && !(createInfo->Race == RACE_HIGHMOUNTAIN_TAUREN
            ? HighmountainAppearance::Validate(createInfo->Gender, appearance)
            : EarthenAppearance::Validate(createInfo->Gender, appearance)))
    {
        SendCharCreate(CHAR_CREATE_FAILED);
        return;
    }

    // A character is always created on its race-origin team. Freeborn is deliberately NOT carried
    // by this packet: the only field Lua can influence here is the name, and a Freeborn name has to
    // follow exactly the same rules as an Alliance or Horde one. The creation screen records the
    // choice and FreebornClaim.h applies it once the character exists.

    if (!HasPermission(rbac::RBAC_PERM_SKIP_CHECK_CHARACTER_CREATION_TEAMMASK))
    {
        if (uint32 mask = sWorld->getIntConfig(CONFIG_CHARACTER_CREATING_DISABLED))
        {
            // The mask disables a persistent team by race origin, which is the only team a create
            // can ask for now: bits 0/1 disable Alliance and Horde. Bit 3 (8) would disable
            // Freeborn, which is chosen after creation, not here.
            if (mask & (1 << Player::TeamIdForRace(createInfo->Race)))
            {
                SendCharCreate(CHAR_CREATE_DISABLED);
                return;
            }
        }
    }

    ChrClassesEntry const* classEntry = sChrClassesStore.LookupEntry(createInfo->Class);
    if (!classEntry)
    {
        SendCharCreate(CHAR_CREATE_FAILED);
        LOG_ERROR("network.opcode", "Class ({}) not found in DBC while creating new char for account (ID: {}): wrong DBC files or cheater?", createInfo->Class, GetAccountId());
        return;
    }

    ChrRacesEntry const* raceEntry = sChrRacesStore.LookupEntry(createInfo->Race);
    if (!raceEntry)
    {
        SendCharCreate(CHAR_CREATE_FAILED);
        LOG_ERROR("network.opcode", "Race ({}) not found in DBC while creating new char for account (ID: {}): wrong DBC files or cheater?", createInfo->Race, GetAccountId());
        return;
    }

    // prevent character creating Expansion race without Expansion account
    if (raceEntry->expansion > Expansion())
    {
        SendCharCreate(CHAR_CREATE_EXPANSION);
        LOG_ERROR("network.opcode", "Expansion {} account:[{}] tried to Create character with expansion {} race ({})", Expansion(), GetAccountId(), raceEntry->expansion, createInfo->Race);
        return;
    }

    // prevent character creating Expansion class without Expansion account
    if (classEntry->expansion > Expansion())
    {
        SendCharCreate(CHAR_CREATE_EXPANSION_CLASS);
        LOG_ERROR("network.opcode", "Expansion {} account:[{}] tried to Create character with expansion {} class ({})", Expansion(), GetAccountId(), classEntry->expansion, createInfo->Class);
        return;
    }

    if (!HasPermission(rbac::RBAC_PERM_SKIP_CHECK_CHARACTER_CREATION_RACEMASK))
    {
        uint32 raceMaskDisabled = sWorld->getIntConfig(CONFIG_CHARACTER_CREATING_DISABLED_RACEMASK);
        if (GetRaceMaskForRace(createInfo->Race) & raceMaskDisabled)
        {
            SendCharCreate(CHAR_CREATE_DISABLED);
            return;
        }
    }

    if (!HasPermission(rbac::RBAC_PERM_SKIP_CHECK_CHARACTER_CREATION_CLASSMASK))
    {
        uint32 classMaskDisabled = sWorld->getIntConfig(CONFIG_CHARACTER_CREATING_DISABLED_CLASSMASK);
        if ((1 << (createInfo->Class - 1)) & classMaskDisabled)
        {
            SendCharCreate(CHAR_CREATE_DISABLED);
            return;
        }
    }

    // prevent character creating with invalid name
    if (!normalizePlayerName(createInfo->Name))
    {
        SendCharCreate(CHAR_NAME_NO_NAME);
        LOG_ERROR("network.opcode", "Account:[{}] but tried to Create character with empty [name] ", GetAccountId());
        return;
    }

    // check name limitations
    uint8 res = ObjectMgr::CheckPlayerName(createInfo->Name, true);
    if (res != CHAR_NAME_SUCCESS)
    {
        if (res != CHAR_NAME_RESERVED || !HasPermission(rbac::RBAC_PERM_SKIP_CHECK_CHARACTER_CREATION_RESERVEDNAME))
        {
            SendCharCreate(ResponseCodes(res));
            return;
        }
    }

    // speedup check for heroic class disabled case
    uint32 heroic_free_slots = sWorld->getIntConfig(CONFIG_HEROIC_CHARACTERS_PER_REALM);
    if (heroic_free_slots == 0 && !HasPermission(rbac::RBAC_PERM_SKIP_CHECK_CHARACTER_CREATION_DEATH_KNIGHT) && createInfo->Class == CLASS_DEATH_KNIGHT)
    {
        SendCharCreate(CHAR_CREATE_UNIQUE_CLASS_LIMIT);
        return;
    }

    // speedup check for heroic class disabled case
    uint32 req_level_for_heroic = sWorld->getIntConfig(CONFIG_CHARACTER_CREATING_MIN_LEVEL_FOR_HEROIC_CHARACTER);
    if (!HasPermission(rbac::RBAC_PERM_SKIP_CHECK_CHARACTER_CREATION_DEATH_KNIGHT) && createInfo->Class == CLASS_DEATH_KNIGHT
        && req_level_for_heroic > sWorld->getIntConfig(CONFIG_MAX_PLAYER_LEVEL) && !HasAccountFlag(ACCOUNT_FLAG_DEATH_KNIGHT_OK))
    {
        SendCharCreate(CHAR_CREATE_LEVEL_REQUIREMENT);
        return;
    }

    CharacterDatabasePreparedStatement* stmt = CharacterDatabase.GetPreparedStatement(CHAR_SEL_CHECK_NAME);
    stmt->SetData(0, createInfo->Name);

    _queryProcessor.AddCallback(CharacterDatabase.AsyncQuery(stmt)
        .WithChainingPreparedCallback([this](QueryCallback& queryCallback, PreparedQueryResult result)
            {
                if (result)
                {
                    SendCharCreate(CHAR_CREATE_NAME_IN_USE);
                    return;
                }

                LoginDatabasePreparedStatement* stmt = LoginDatabase.GetPreparedStatement(LOGIN_SEL_SUM_REALM_CHARACTERS);
                stmt->SetData(0, GetAccountId());
                queryCallback.SetNextQuery(LoginDatabase.AsyncQuery(stmt));
            })
        .WithChainingPreparedCallback([this](QueryCallback& queryCallback, PreparedQueryResult result)
            {
                uint64 acctCharCount = 0;
                if (result)
                {
                    Field* fields = result->Fetch();
                    acctCharCount = uint64(fields[0].Get<double>());
                }

                if (acctCharCount >= static_cast<uint64>(sWorld->getIntConfig(CONFIG_CHARACTERS_PER_ACCOUNT)))
                {
                    SendCharCreate(CHAR_CREATE_ACCOUNT_LIMIT);
                    return;
                }

                CharacterDatabasePreparedStatement* stmt = CharacterDatabase.GetPreparedStatement(CHAR_SEL_SUM_CHARS);
                stmt->SetData(0, GetAccountId());
                queryCallback.SetNextQuery(CharacterDatabase.AsyncQuery(stmt));
            })
        .WithChainingPreparedCallback([this, createInfo](QueryCallback& queryCallback, PreparedQueryResult result)
            {
                if (result)
                {
                    Field* fields = result->Fetch();
                    createInfo->CharCount = uint8(fields[0].Get<uint64>()); // SQL's COUNT() returns uint64 but it will always be less than uint8.Max

                    if (createInfo->CharCount >= sWorld->getIntConfig(CONFIG_CHARACTERS_PER_REALM))
                    {
                        SendCharCreate(CHAR_CREATE_SERVER_LIMIT);
                        return;
                    }
                }

                bool allowTwoSideAccounts = !sWorld->IsPvPRealm() || sWorld->getBoolConfig(CONFIG_ALLOW_TWO_SIDE_ACCOUNTS) || HasPermission(rbac::RBAC_PERM_TWO_SIDE_CHARACTER_CREATION);
                uint32 skipCinematics = sWorld->getIntConfig(CONFIG_SKIP_CINEMATICS);

                std::function<void(PreparedQueryResult)> finalizeCharacterCreation = [this, createInfo](PreparedQueryResult result)
                    {
                        if (!sScriptMgr->CanAccountCreateCharacter(GetAccountId(), createInfo->Race, createInfo->Class))
                        {
                            SendCharCreate(CHAR_CREATE_DISABLED);
                            return;
                        }
                        bool haveSameRace = false;
                        uint32 heroicReqLevel = sWorld->getIntConfig(CONFIG_CHARACTER_CREATING_MIN_LEVEL_FOR_HEROIC_CHARACTER);
                        bool const deathKnightFlagAlreadySet = HasAccountFlag(ACCOUNT_FLAG_DEATH_KNIGHT_OK); // Account flag is superior to level requirement.
                        bool hasHeroicReqLevel = (heroicReqLevel == 0) || deathKnightFlagAlreadySet;
                        bool allowTwoSideAccounts = !sWorld->IsPvPRealm() || sWorld->getBoolConfig(CONFIG_ALLOW_TWO_SIDE_ACCOUNTS) || HasPermission(rbac::RBAC_PERM_TWO_SIDE_CHARACTER_CREATION);
                        uint32 skipCinematics = sWorld->getIntConfig(CONFIG_SKIP_CINEMATICS);
                        bool checkDeathKnightReqs = !HasPermission(rbac::RBAC_PERM_SKIP_CHECK_CHARACTER_CREATION_DEATH_KNIGHT) && createInfo->Class == CLASS_DEATH_KNIGHT;

                        if (result)
                        {
                            // One-account-one-side limits are origin-based on purpose: a Freeborn
                            // character is hostile to every side, so letting it skip this rule
                            // grants no cross-side advantage, and treating it as its race origin
                            // keeps native creation behaviour byte-for-byte unchanged.
                            TeamId teamId = Player::TeamIdForRace(createInfo->Race);
                            uint32 freeDeathKnightSlots = sWorld->getIntConfig(CONFIG_HEROIC_CHARACTERS_PER_REALM);

                            Field* field = result->Fetch();
                            uint8 accRace = field[1].Get<uint8>();

                            if (checkDeathKnightReqs)
                            {
                                uint8 accClass = field[2].Get<uint8>();
                                if (accClass == CLASS_DEATH_KNIGHT)
                                {
                                    if (freeDeathKnightSlots > 0)
                                        --freeDeathKnightSlots;

                                    if (freeDeathKnightSlots == 0)
                                    {
                                        SendCharCreate(CHAR_CREATE_UNIQUE_CLASS_LIMIT);
                                        return;
                                    }
                                }

                                if (!hasHeroicReqLevel)
                                {
                                    uint8 accLevel = field[0].Get<uint8>();
                                    if (accLevel >= heroicReqLevel)
                                        hasHeroicReqLevel = true;
                                }
                            }

                            // need to check team only for first character
                            /// @todo what to if account already has characters of both races?
                            if (!allowTwoSideAccounts)
                            {
                                uint32 accTeam = 0;
                                if (accRace > 0)
                                    accTeam = Player::TeamIdForRace(accRace);

                                if (accTeam != teamId)
                                {
                                    SendCharCreate(CHAR_CREATE_PVP_TEAMS_VIOLATION);
                                    return;
                                }
                            }

                            // search same race for cinematic or same class if need
                            /// @todo check if cinematic already shown? (already logged in?; cinematic field)
                            while ((skipCinematics == 1 && !haveSameRace) || createInfo->Class == CLASS_DEATH_KNIGHT)
                            {
                                if (!result->NextRow())
                                    break;

                                field = result->Fetch();
                                accRace = field[1].Get<uint8>();

                                if (!haveSameRace)
                                    haveSameRace = createInfo->Race == accRace;

                                if (checkDeathKnightReqs)
                                {
                                    uint8 acc_class = field[2].Get<uint8>();
                                    if (acc_class == CLASS_DEATH_KNIGHT)
                                    {
                                        if (freeDeathKnightSlots > 0)
                                            --freeDeathKnightSlots;

                                        if (freeDeathKnightSlots == 0)
                                        {
                                            SendCharCreate(CHAR_CREATE_UNIQUE_CLASS_LIMIT);
                                            return;
                                        }
                                    }

                                    if (!hasHeroicReqLevel)
                                    {
                                        uint8 acc_level = field[0].Get<uint8>();
                                        if (acc_level >= heroicReqLevel)
                                            hasHeroicReqLevel = true;
                                    }
                                }
                            }
                        }

                        if (checkDeathKnightReqs)
                        {
                            if (!deathKnightFlagAlreadySet && hasHeroicReqLevel)
                                UpdateAccountFlag(ACCOUNT_FLAG_DEATH_KNIGHT_OK);

                            if (!hasHeroicReqLevel)
                            {
                                SendCharCreate(CHAR_CREATE_LEVEL_REQUIREMENT);
                                return;
                            }
                        }

                        // Check name uniqueness in the same step as saving to database
                        if (sCharacterCache->GetCharacterGuidByName(createInfo->Name))
                        {
                            SendCharCreate(CHAR_CREATE_NAME_IN_USE);
                            return;
                        }

                        std::shared_ptr<Player> newChar(new Player(this), [](Player* ptr)
                            {
                                // Only when player is created correctly do clean
                                if (ptr->HasAtLoginFlag(AT_LOGIN_FIRST))
                                {
                                    ptr->CleanupsBeforeDelete();
                                }
                                delete ptr;
                            });

                        newChar->GetMotionMaster()->Initialize();
                        if (!newChar->Create(sObjectMgr->GetGenerator<HighGuid::Player>().Generate(), createInfo.get()))
                        {
                            // Player not create (race/class/etc problem?)
                            SendCharCreate(CHAR_CREATE_ERROR);
                            return;
                        }

                        if ((haveSameRace && skipCinematics == 1) || skipCinematics == 2)
                            newChar->setCinematic(1);                         // not show intro

                        newChar->SetAtLoginFlag(AT_LOGIN_FIRST);              // First login

                        CharacterDatabaseTransaction characterTransaction = CharacterDatabase.BeginTransaction();
                        LoginDatabaseTransaction trans = LoginDatabase.BeginTransaction();

                        // Player created, save it now
                        newChar->SaveToDB(characterTransaction, true, false);
                        createInfo->CharCount++;

                        if (createInfo->HasBodyShape && !CharacterBodyShape::AllDefault(createInfo->BodyShape))
                        {
                            std::vector<uint8> payload(CharacterBodyShape::PayloadSize);
                            CharacterBodyShape::WritePayload(payload.data(), createInfo->BodyShape);
                            CharacterDatabasePreparedStatement* shapeStmt = CharacterDatabase.GetPreparedStatement(CHAR_REP_BODY_SHAPE);
                            shapeStmt->SetData(0, newChar->GetGUID().GetCounter());
                            shapeStmt->SetData(1, payload);
                            characterTransaction->Append(shapeStmt);
                        }

                        if (createInfo->HasRetailLook)
                        {
                            std::vector<uint8> payload(CharacterRetailLook::PayloadSize);
                            CharacterRetailLook::WritePayload(payload.data(), createInfo->RetailLook);
                            CharacterDatabasePreparedStatement* lookStmt = CharacterDatabase.GetPreparedStatement(CHAR_REP_RETAIL_LOOK);
                            lookStmt->SetData(0, newChar->GetGUID().GetCounter());
                            lookStmt->SetData(1, payload);
                            characterTransaction->Append(lookStmt);
                        }

                        LoginDatabasePreparedStatement* stmt = LoginDatabase.GetPreparedStatement(LOGIN_DEL_REALM_CHARACTERS_BY_REALM);
                        stmt->SetData(0, GetAccountId());
                        stmt->SetData(1, realm.Id.Realm);
                        trans->Append(stmt);

                        stmt = LoginDatabase.GetPreparedStatement(LOGIN_REP_REALM_CHARACTERS);
                        stmt->SetData(0, createInfo->CharCount);
                        stmt->SetData(1, GetAccountId());
                        stmt->SetData(2, realm.Id.Realm);
                        trans->Append(stmt);

                        LoginDatabase.CommitTransaction(trans);

                        AddTransactionCallback(CharacterDatabase.AsyncCommitTransaction(characterTransaction)).AfterComplete([this, newChar = std::move(newChar)](bool success)
                            {
                                if (success)
                                {
                                    LOG_INFO("entities.player.character",
                                        "Account: {} (IP: {}) Create Character: {} {} (persistent team {})",
                                        GetAccountId(), GetRemoteAddress(), newChar->GetName(),
                                        newChar->GetGUID().ToString(), uint32(newChar->GetTeamId()));
                                    sScriptMgr->OnPlayerCreate(newChar.get());
                                    sCharacterCache->AddCharacterCacheEntry(
                                        newChar->GetGUID(), GetAccountId(), newChar->GetName(),
                                        newChar->getGender(), newChar->getRace(), newChar->getClass(),
                                        newChar->GetLevel(), newChar->GetTeamId());
                                    SendCharCreate(CHAR_CREATE_SUCCESS);
                                }
                                else
                                    SendCharCreate(CHAR_CREATE_ERROR);
                            });
                    };

                if (allowTwoSideAccounts && !skipCinematics && createInfo->Class != CLASS_DEATH_KNIGHT)
                {
                    finalizeCharacterCreation(PreparedQueryResult(nullptr));
                    return;
                }

                CharacterDatabasePreparedStatement* stmt = CharacterDatabase.GetPreparedStatement(CHAR_SEL_CHAR_CREATE_INFO);
                stmt->SetData(0, GetAccountId());
                stmt->SetData(1, (skipCinematics == 1 || createInfo->Class == CLASS_DEATH_KNIGHT) ? 10 : 1);
                queryCallback.WithPreparedCallback(std::move(finalizeCharacterCreation)).SetNextQuery(CharacterDatabase.AsyncQuery(stmt));
            }));
}

void WorldSession::HandleCharDeleteOpcode(WorldPacket& recvData)
{
    ObjectGuid guid;
    recvData >> guid;

    // Initiating
    uint32 initAccountId = GetAccountId();

    // can't delete loaded character
    if (ObjectAccessor::FindConnectedPlayer(guid) || sWorldSessionMgr->FindOfflineSessionForCharacterGUID(guid.GetCounter()))
    {
        sScriptMgr->OnPlayerFailedDelete(guid, initAccountId);
        return;
    }

    uint32 accountId = 0;
    uint8 level = 0;
    std::string name;

    // is guild leader
    if (sGuildMgr->GetGuildByLeader(guid))
    {
        sScriptMgr->OnPlayerFailedDelete(guid, initAccountId);
        SendCharDelete(CHAR_DELETE_FAILED_GUILD_LEADER);
        return;
    }

    // is arena team captain
    if (sArenaTeamMgr->GetArenaTeamByCaptain(guid))
    {
        sScriptMgr->OnPlayerFailedDelete(guid, initAccountId);
        SendCharDelete(CHAR_DELETE_FAILED_ARENA_CAPTAIN);
        return;
    }

    if (CharacterCacheEntry const* playerData = sCharacterCache->GetCharacterCacheByGuid(guid))
    {
        accountId = playerData->AccountId;
        name = playerData->Name;
        level = playerData->Level;
    }

    // prevent deleting other players' characters using cheating tools
    if (accountId != initAccountId)
    {
        sScriptMgr->OnPlayerFailedDelete(guid, initAccountId);
        return;
    }

    LOG_INFO("entities.player.character", "Account: {}, IP: {} deleted character: {}, {}, Level: {}", accountId, GetRemoteAddress(), name, guid.ToString(), level);

    // To prevent hook failure, place hook before removing reference from DB
    sScriptMgr->OnPlayerDelete(guid, initAccountId); // To prevent race conditioning, but as it also makes sense, we hand the accountId over for successful delete.
    sCalendarMgr->RemoveAllPlayerEventsAndInvites(guid);
    Player::DeleteFromDB(guid.GetCounter(), GetAccountId(), true, false);

    sWorld->UpdateRealmCharCount(GetAccountId());

    SendCharDelete(CHAR_DELETE_SUCCESS);
}

void WorldSession::HandlePlayerLoginOpcode(WorldPacket& recvData)
{
    if (!sWorld->getBoolConfig(CONFIG_REALM_LOGIN_ENABLED))
    {
        SendCharLoginFailed(LoginFailureReason::NoWorld);
        return;
    }

    if (PlayerLoading() || GetPlayer() != nullptr)
    {
        LOG_ERROR("network", "Player tried to login again, AccountId = {}", GetAccountId());
        KickPlayer("WorldSession::HandlePlayerLoginOpcode Another client logging in");
        return;
    }

    ObjectGuid playerGuid;
    recvData >> playerGuid;

    // The ownership check is delegated to the gateway in cluster mode, but a
    // non-player GUID is invalid regardless of who authenticated the session.
    if (!playerGuid.IsPlayer() || (!sToCloud9Sidecar->ClusterModeEnabled() && !IsLegitCharacterForAccount(playerGuid)))
    {
        LOG_ERROR("network", "Account ({}) can't login with that character ({}).", GetAccountId(), playerGuid.ToString());
        KickPlayer("Account can't login with this character");
        return;
    }

    // pussywizard:
    if (WorldSession* sess = sWorldSessionMgr->FindOfflineSessionForCharacterGUID(playerGuid.GetCounter()))
    {
        if (sess->GetAccountId() != GetAccountId())
        {
            SendCharLoginFailed(LoginFailureReason::DuplicateCharacter);
            return;
        }
    }

    // pussywizard:
    if (WorldSession* sess = sWorldSessionMgr->FindOfflineSession(GetAccountId()))
    {
        Player* p = sess->GetPlayer();
        if (!p || sess->IsKicked())
        {
            SendCharLoginFailed(LoginFailureReason::DuplicateCharacter);
            return;
        }

        if (p->GetGUID() != playerGuid)
            sess->KickPlayer("No return, go to normal loading"); // no return, go to normal loading
        else
        {
            // pussywizard: players stay ingame no matter what (prevent abuse), but allow to turn it off to stop crashing
            if (!sWorld->getBoolConfig(CONFIG_ENABLE_LOGIN_AFTER_DC))
            {
                SendCharLoginFailed(LoginFailureReason::DuplicateCharacter);
                return;
            }

            uint8 limitA = 10, limitB = 10, limitC = 10; // pussywizard: this somehow froze (probably, ahh crash logs ...), and while (far) have never frozen in LogoutPlayer o_O maybe it's the combination of while(far); while(near);
            while (sess->GetPlayer() && (sess->GetPlayer()->IsBeingTeleportedFar() || (sess->GetPlayer()->IsInWorld() && sess->GetPlayer()->IsBeingTeleportedNear())))
            {
                if (limitA == 0 || --limitA == 0)
                {
                    LOG_INFO("misc", "HandlePlayerLoginOpcode A");
                    break;
                }
                while (sess->GetPlayer() && sess->GetPlayer()->IsBeingTeleportedFar())
                {
                    if (limitB == 0 || --limitB == 0)
                    {
                        LOG_INFO("misc", "HandlePlayerLoginOpcode B");
                        break;
                    }
                    sess->HandleMoveWorldportAck();
                }
                while (sess->GetPlayer() && sess->GetPlayer()->IsInWorld() && sess->GetPlayer()->IsBeingTeleportedNear())
                {
                    if (limitC == 0 || --limitC == 0)
                    {
                        LOG_INFO("misc", "HandlePlayerLoginOpcode C");
                        break;
                    }

                    Player* plMover = sess->GetPlayer()->m_mover->ToPlayer();
                    if (!plMover)
                        break;

                    WorldPacket pkt(MSG_MOVE_TELEPORT_ACK, 20);
                    pkt << plMover->GetPackGUID();
                    pkt << uint32(0); // flags
                    pkt << uint32(0); // time
                    sess->HandleMoveTeleportAck(pkt);
                }
            }
            if (!p->FindMap() || !p->IsInWorld() || sess->IsKicked())
            {
                SendCharLoginFailed(LoginFailureReason::DuplicateCharacter);
                return;
            }

            sess->SetPlayer(nullptr);
            SetPlayer(p);
            p->SetSession(this);
            delete p->PlayerTalkClass;
            p->PlayerTalkClass = new PlayerMenu(p->GetSession());
            HandlePlayerLoginToCharInWorld(p);
            return;
        }
    }

    std::shared_ptr<LoginQueryHolder> holder = std::make_shared<LoginQueryHolder>(GetAccountId(), playerGuid);
    if (!holder->Initialize())
        return;

    m_playerLoading = true;
    AddQueryHolderCallback(CharacterDatabase.DelayQueryHolder(holder)).AfterComplete([this](SQLQueryHolderBase const& holder)
        {
            HandlePlayerLoginFromDB(static_cast<LoginQueryHolder const&>(holder));
        });
}

void WorldSession::HandlePlayerLoginFromDB(LoginQueryHolder const& holder)
{
    m_playerLoading = true;
    ObjectGuid playerGuid = holder.GetGuid();

    Player* pCurrChar = new Player(this);
    // for send server info and strings (config)
    ChatHandler chH = ChatHandler(pCurrChar->GetSession());

    // "GetAccountId() == db stored account id" checked in LoadFromDB (prevent login not own character using cheating tools)
    if (!pCurrChar->LoadFromDB(playerGuid, holder))
    {
        SetPlayer(nullptr);
        KickPlayer("WorldSession::HandlePlayerLogin Player::LoadFromDB failed"); // disconnect client, player no set to session and it will not deleted or saved at kick
        delete pCurrChar; // delete it manually
        m_playerLoading = false;
        return;
    }

    pCurrChar->GetMotionMaster()->Initialize();
    pCurrChar->SendDungeonDifficulty(false);

    WorldPacket data(SMSG_LOGIN_VERIFY_WORLD, 20);
    data << pCurrChar->GetMapId();
    data << pCurrChar->GetPositionX();
    data << pCurrChar->GetPositionY();
    data << pCurrChar->GetPositionZ();
    data << pCurrChar->GetOrientation();
    SendPacket(&data);

    // load player specific part before send times
    LoadAccountData(holder.GetPreparedResult(PLAYER_LOGIN_QUERY_LOAD_ACCOUNT_DATA), PER_CHARACTER_CACHE_MASK);
    SendAccountDataTimes(PER_CHARACTER_CACHE_MASK);

    data.Initialize(SMSG_FEATURE_SYSTEM_STATUS, 2);         // added in 2.2.0
    data << uint8(2);                                       // 2 - COMPLAINT_ENABLED_WITH_AUTO_IGNORE
    data << uint8(0);                                       // enable(1)/disable(0) voice chat interface in client
    SendPacket(&data);

    // Send MOTD
    {
        SendPacket(sMotdMgr->GetMotdPacket(pCurrChar->GetSession()->GetSessionDbLocaleIndex()));

        // send server info
        if (sWorld->getIntConfig(CONFIG_ENABLE_SINFO_LOGIN) == 1)
            chH.PSendSysMessage("{}", GitRevision::GetFullVersion());
    }

    if (!sToCloud9Sidecar->ClusterModeEnabled())
    {
        if (uint32 guildId = sCharacterCache->GetCharacterGuildIdByGuid(pCurrChar->GetGUID()))
        {
            Guild* guild = sGuildMgr->GetGuildById(guildId);
            Guild::Member const* member = guild ? guild->GetMember(pCurrChar->GetGUID()) : nullptr;
            if (member)
            {
                pCurrChar->SetInGuild(guildId);
                pCurrChar->SetRank(member->GetRankId());
                guild->SendLoginInfo(this);
            }
            else
            {
                LOG_ERROR("network.opcode", "Player {} ({}) marked as member of not existing guild (id: {}), removing guild membership for player.",
                    pCurrChar->GetName(), pCurrChar->GetGUID().ToString(), guildId);
                pCurrChar->SetInGuild(0);
                pCurrChar->SetRank(0);
            }
        }
        else
        {
            pCurrChar->SetInGuild(0);
            pCurrChar->SetRank(0);
        }
    }
    else
    {
        pCurrChar->SetInGuild(0);
        pCurrChar->SetRank(0);
    }

    data.Initialize(SMSG_LEARNED_DANCE_MOVES, 4 + 4);
    data << uint32(0);
    data << uint32(0);
    SendPacket(&data);

    pCurrChar->SendInitialPacketsBeforeAddToMap();

    //Show cinematic at the first time that player login
    if (!pCurrChar->getCinematic())
    {
        pCurrChar->setCinematic(1);

        if (ChrClassesEntry const* cEntry = sChrClassesStore.LookupEntry(pCurrChar->getClass()))
        {
            if (cEntry->CinematicSequence)
                pCurrChar->GetCinematicMgr().StartCinematic(cEntry->CinematicSequence);
            else if (ChrRacesEntry const* rEntry = sChrRacesStore.LookupEntry(pCurrChar->getRace()))
                pCurrChar->GetCinematicMgr().StartCinematic(rEntry->CinematicSequence);

            // send new char string if not empty
            std::string_view newCharString = sWorld->getStringConfig(CONFIG_NEW_CHAR_STRING);
            if (!newCharString.empty())
                chH.PSendSysMessage("{}", newCharString);
        }
    }

    // Xinef: moved this from below
    ObjectAccessor::AddObject(pCurrChar);

    if (!pCurrChar->GetMap()->AddPlayerToMap(pCurrChar) || !pCurrChar->CheckInstanceLoginValid())
    {
        AreaTriggerTeleport const* at = sObjectMgr->GetGoBackTrigger(pCurrChar->GetMapId());
        if (at)
            pCurrChar->TeleportTo(at->target_mapId, at->target_X, at->target_Y, at->target_Z, pCurrChar->GetOrientation());
        else
            pCurrChar->TeleportTo(pCurrChar->m_homebindMapId, pCurrChar->m_homebindX, pCurrChar->m_homebindY, pCurrChar->m_homebindZ, pCurrChar->GetOrientation());

        // Probably a hackfix, but currently the best workaround to prevent character names showing as Unknown after teleport out from instances at login.
        pCurrChar->GetSession()->SendNameQueryOpcode(pCurrChar->GetGUID());
    }

    pCurrChar->SendInitialPacketsAfterAddToMap();

    if (!sToCloud9Sidecar->ClusterModeEnabled())
    {
        CharacterDatabasePreparedStatement* stmt = CharacterDatabase.GetPreparedStatement(CHAR_UPD_CHAR_ONLINE);
        stmt->SetData(0, pCurrChar->GetGUID().GetCounter());
        CharacterDatabase.Execute(stmt);
    }

    LoginDatabasePreparedStatement* loginStmt = LoginDatabase.GetPreparedStatement(LOGIN_UPD_ACCOUNT_ONLINE);
    loginStmt->SetData(0, GetAccountId());
    LoginDatabase.Execute(loginStmt);

    pCurrChar->SetInGameTime(GameTime::GetGameTimeMS().count());

    // announce group about member online (must be after add to player list to receive announce to self)
    if (Group* group = pCurrChar->GetGroup())
    {
        group->SendUpdate();
        group->ResetMaxEnchantingLevel();
    }

    // pussywizard: send instance welcome message as when entering the instance through a portal
    if (MapDifficulty const* mapDiff = GetMapDifficultyData(pCurrChar->GetMap()->GetId(), pCurrChar->GetMap()->GetDifficulty()))
        if (mapDiff->resetTime)
            if (time_t timeReset = sInstanceSaveMgr->GetResetTimeFor(pCurrChar->GetMap()->GetId(), pCurrChar->GetMap()->GetDifficulty()))
            {
                uint32 timeleft = uint32(timeReset - GameTime::GetGameTime().count());
                pCurrChar->SendInstanceResetWarning(pCurrChar->GetMap()->GetId(), pCurrChar->GetMap()->GetDifficulty(), timeleft, true);
            }

    // pussywizard: ensure that we end up on map with our loaded transport:
    if (Transport* t = pCurrChar->GetTransport())
        if (!t->IsInMap(pCurrChar))
        {
            t->RemovePassenger(pCurrChar);
            pCurrChar->m_transport = nullptr;
            pCurrChar->m_movementInfo.transport.Reset();
            pCurrChar->m_movementInfo.RemoveMovementFlag(MOVEMENTFLAG_ONTRANSPORT);
        }

    // friend status
    sSocialMgr->SendFriendStatus(pCurrChar, FRIEND_ONLINE, pCurrChar->GetGUID(), true);

    // Place character in world (and load zone) before some object loading
    pCurrChar->LoadCorpse(holder.GetPreparedResult(PLAYER_LOGIN_QUERY_LOAD_CORPSE_LOCATION));

    // Set FFA PvP for non GM in non-rest mode
    if (sWorld->IsFFAPvPRealm() && !pCurrChar->IsGameMaster() && !pCurrChar->HasPlayerFlag(PLAYER_FLAGS_RESTING))
        if (!pCurrChar->HasByteFlag(UNIT_FIELD_BYTES_2, 1, UNIT_BYTE2_FLAG_FFA_PVP))
        {
            sScriptMgr->OnPlayerFfaPvpStateUpdate(pCurrChar, true);
            pCurrChar->SetByteFlag(UNIT_FIELD_BYTES_2, 1, UNIT_BYTE2_FLAG_FFA_PVP);
        }

    if (pCurrChar->HasPlayerFlag(PLAYER_FLAGS_CONTESTED_PVP))
    {
        pCurrChar->SetContestedPvP(nullptr, false);
    }

    // Apply at_login requests
    if (pCurrChar->HasAtLoginFlag(AT_LOGIN_RESET_SPELLS))
    {
        pCurrChar->resetSpells();
        ChatHandler(this).SendNotification(LANG_RESET_SPELLS);
    }

    if (pCurrChar->HasAtLoginFlag(AT_LOGIN_RESET_TALENTS))
    {
        pCurrChar->resetTalents(true);
        pCurrChar->SendTalentsInfoData(false);              // original talents send already in to SendInitialPacketsBeforeAddToMap, resend reset state
        ChatHandler(this).SendNotification(LANG_RESET_TALENTS);
    }

    if (pCurrChar->HasAtLoginFlag(AT_LOGIN_CHECK_ACHIEVS))
    {
        // If we process the check while players are loading they won't be notified of the changes.
        pCurrChar->m_Events.AddEventAtOffset([pCurrChar]
            {
                pCurrChar->RemoveAtLoginFlag(AT_LOGIN_CHECK_ACHIEVS, true);
                pCurrChar->CheckAllAchievementCriteria();
            }, 1s);
    }

    bool firstLogin = pCurrChar->HasAtLoginFlag(AT_LOGIN_FIRST);
    if (firstLogin)
    {
        PlayerInfo const* info = sObjectMgr->GetPlayerInfo(pCurrChar->getRace(), pCurrChar->getClass());
        for (uint32 spellId : info->castSpells)
        {
            pCurrChar->CastSpell(pCurrChar, spellId, true);
        }

        // start with every map explored
        if (sWorld->getBoolConfig(CONFIG_START_ALL_EXPLORED))
        {
            for (uint8 i = 0; i < PLAYER_EXPLORED_ZONES_SIZE; i++)
            {
                pCurrChar->SetFlag(PLAYER_EXPLORED_ZONES_1 + i, 0xFFFFFFFF);
            }
        }

        // Reputations if "StartAllReputation" is enabled, -- TODO: Fix this in a better way
        if (sWorld->getBoolConfig(CONFIG_START_ALL_REP))
        {
            ReputationMgr& repMgr = pCurrChar->GetReputationMgr();

            auto SendFullReputation = [&repMgr](std::initializer_list<uint32> factionsList)
                {
                    for (auto const& itr : factionsList)
                    {
                        repMgr.SetOneFactionReputation(sFactionStore.LookupEntry(itr), 42999.f, false);
                    }
                };

            SendFullReputation({ 942, 935, 936, 1011, 970, 967, 989, 932, 934, 1038, 1077, 1106, 1104, 1090, 1098, 1156, 1073, 1105, 1119, 1091 });

            switch (pCurrChar->GetFaction())
            {
            case ALLIANCE:
                SendFullReputation({ 72, 47, 69, 930, 730, 978, 54, 946, 1037, 1068, 1126, 1094, 1050 });
                break;
            case HORDE:
                SendFullReputation({ 76, 68, 81, 911, 729, 941, 530, 947, 1052, 1067, 1124, 1064, 1085 });
                break;
            default:
                break;
            }

            repMgr.SendStates();
        }
    }

    // show time before shutdown if shutdown planned.
    if (sWorld->IsShuttingDown())
        sWorld->ShutdownMsg(true, pCurrChar);

    if (sWorld->getBoolConfig(CONFIG_ALL_TAXI_PATHS))
        pCurrChar->SetTaxiCheater(true);

    if (pCurrChar->IsGameMaster())
        ChatHandler(this).SendNotification(LANG_GM_ON);

    std::string IP_str = GetRemoteAddress();
    LOG_INFO("entities.player", "Account: {} (IP: {}) Login Character:[{}] ({}) Level: {}",
        GetAccountId(), IP_str, pCurrChar->GetName(), pCurrChar->GetGUID().ToString(), pCurrChar->GetLevel());

    if (!pCurrChar->IsStandState() && !pCurrChar->HasUnitState(UNIT_STATE_STUNNED))
        pCurrChar->SetStandState(UNIT_STAND_STATE_STAND);

    m_playerLoading = false;

    // Handle Login-Achievements (should be handled after loading)
    _player->UpdateAchievementCriteria(ACHIEVEMENT_CRITERIA_TYPE_ON_LOGIN, 1);

    // Xinef: fix vendors falling of player vehicle, due to isBeingLoaded checks
    if (pCurrChar->IsInWorld())
    {
        if (pCurrChar->GetMountBlockId() && !pCurrChar->HasMountedAura())
        {
            pCurrChar->CastSpell(pCurrChar, pCurrChar->GetMountBlockId(), true);
            pCurrChar->SetMountBlockId(0);

            // Xinef: refresh this in case mount aura changes anything (eg no fly zone)
            pCurrChar->UpdateAreaDependentAuras(pCurrChar->GetAreaId());
            pCurrChar->UpdateZoneDependentAuras(pCurrChar->GetZoneId());
        }
    }

    // pussywizard: pvp mode
    pCurrChar->RemovePlayerFlag(PLAYER_FLAGS_PVP_TIMER);
    if (pCurrChar->HasPlayerFlag(PLAYER_FLAGS_IN_PVP))
        pCurrChar->UpdatePvP(true, true);

    // pussywizard: on login it's not possible to go back to arena as a spectator, HandleMoveWorldportAckOpcode is not sent, so call it here
    pCurrChar->SetIsSpectator(false);

    // xinef: do this after everything is loaded
    pCurrChar->ContinueTaxiFlight();

    // reset for all pets before pet loading
    if (pCurrChar->HasAtLoginFlag(AT_LOGIN_RESET_PET_TALENTS))
        Pet::resetTalentsForAllPetsOf(pCurrChar);

    // Load pet if any (if player not alive and in taxi flight or another then pet will remember as temporary unsummoned)
    pCurrChar->LoadPet();

    if (pCurrChar->GetSession()->GetRecruiterId() != 0 || pCurrChar->GetSession()->IsARecruiter())
    {
        bool isReferrer = pCurrChar->GetSession()->IsARecruiter();

        for (auto const& [accID, session] : sWorldSessionMgr->GetAllSessions())
        {
            if (!session->GetRecruiterId() && !session->IsARecruiter())
                continue;

            if ((isReferrer && pCurrChar->GetSession()->GetAccountId() == session->GetRecruiterId()) || (!isReferrer && pCurrChar->GetSession()->GetRecruiterId() == session->GetAccountId()))
            {
                Player* rf = session->GetPlayer();
                if (rf)
                {
                    pCurrChar->SendUpdateToPlayer(rf);
                    rf->SendUpdateToPlayer(pCurrChar);
                }
            }
        }
    }

    sScriptMgr->OnPlayerLogin(pCurrChar);

    if (pCurrChar->HasAtLoginFlag(AT_LOGIN_FIRST))
    {
        pCurrChar->RemoveAtLoginFlag(AT_LOGIN_FIRST);
        sScriptMgr->OnPlayerFirstLogin(pCurrChar);
    }

    METRIC_EVENT("player_events", "Login", pCurrChar->GetName());
}

void WorldSession::HandlePlayerLoginToCharInWorld(Player* pCurrChar)
{
    ChatHandler chH = ChatHandler(this);
    m_playerLoading = true;

    // Exit vehicle on reconnect - the client has fully reset so
    // the player can no longer control the vehicle. Without this
    // the player is stuck: server-side still seated, but the
    // client has no vehicle UI or movement control.
    if (pCurrChar->GetVehicle())
        pCurrChar->ExitVehicle();

    pCurrChar->SendDungeonDifficulty(false);

    WorldPacket data(SMSG_LOGIN_VERIFY_WORLD, 20);
    data << pCurrChar->GetMapId();
    data << pCurrChar->GetPositionX();
    data << pCurrChar->GetPositionY();
    data << pCurrChar->GetPositionZ();
    data << pCurrChar->GetOrientation();
    SendPacket(&data);

    SendAccountDataTimes(PER_CHARACTER_CACHE_MASK);

    data.Initialize(SMSG_FEATURE_SYSTEM_STATUS, 2);         // added in 2.2.0
    data << uint8(2);                                       // unknown value
    data << uint8(0);                                       // enable(1)/disable(0) voice chat interface in client
    SendPacket(&data);

    // Send MOTD
    {
        SendPacket(sMotdMgr->GetMotdPacket(pCurrChar->GetSession()->GetSessionDbLocaleIndex()));

        // send server info
        if (sWorld->getIntConfig(CONFIG_ENABLE_SINFO_LOGIN) == 1)
            chH.PSendSysMessage("{}", GitRevision::GetFullVersion());

        LOG_DEBUG("network.opcode", "WORLD: Sent server info");
    }

    data.Initialize(SMSG_LEARNED_DANCE_MOVES, 4 + 4);
    data << uint32(0);
    data << uint32(0);
    SendPacket(&data);

    // Xinef: fix possible problem with flag UNIT_FLAG_STUNNED added during logout
    if (pCurrChar->HasUnitState(UNIT_STATE_LOGOUT_TIMER))
    {
        pCurrChar->SetRooted(false, true, true);
        pCurrChar->RemoveUnitFlag(UNIT_FLAG_STUNNED);
    }

    if (pCurrChar->GetPendingFlightChange() <= pCurrChar->GetMapChangeOrderCounter())
    {
        if (!pCurrChar->HasIncreaseMountedFlightSpeedAura() && !pCurrChar->HasFlyAura())
            pCurrChar->m_movementInfo.RemoveMovementFlag(MOVEMENTFLAG_CAN_FLY);
    }

    pCurrChar->SendInitialPacketsBeforeAddToMap();

    // necessary actions from AddPlayerToMap:
    pCurrChar->GetMap()->SendInitTransports(pCurrChar);
    pCurrChar->GetMap()->SendInitSelf(pCurrChar);

    // If we are logging into an existing player, simply clear visibility references
    // so player will receive a fresh list of new objects on the next vis update.
    pCurrChar->GetObjectVisibilityContainer().CleanVisibilityReferences();
    pCurrChar->UpdateObjectVisibility(false);

    pCurrChar->CleanupChannels();
    pCurrChar->SendInitialPacketsAfterAddToMap();
    uint32 currZone, currArea;
    pCurrChar->GetZoneAndAreaId(currZone, currArea);
    pCurrChar->SendInitWorldStates(currZone, currArea);
    pCurrChar->SetInGameTime(GameTime::GetGameTimeMS().count());

    // Xinef: we need to resend all spell mods
    for (uint16 Opcode = SMSG_SET_FLAT_SPELL_MODIFIER; Opcode <= SMSG_SET_PCT_SPELL_MODIFIER; ++Opcode) // PCT = FLAT+1
    {
        uint32 modType = (Opcode == SMSG_SET_FLAT_SPELL_MODIFIER) ? SPELLMOD_FLAT : SPELLMOD_PCT;
        for (uint32 opType = SPELLMOD_DAMAGE; opType < MAX_SPELLMOD; ++opType)
        {
            int32 i = 0;
            flag96 _mask = 0;
            SpellModContainer const& spellMods = pCurrChar->GetSpellModList(opType);
            if (spellMods.empty())
                continue;

            for (int32 eff = 0; eff < 96; ++eff)
            {
                if (eff != 0 && eff % 32 == 0)
                    _mask[i++] = 0;

                _mask[i] = uint32(1) << (eff - (32 * i));
                int32 val = 0;
                for (auto const& spellMod : spellMods)
                    if (spellMod->type == modType && spellMod->mask & _mask)
                        val += spellMod->value;

                if (val == 0)
                    continue;

                WorldPacket data(Opcode, (1 + 1 + 4));
                data << uint8(eff);
                data << uint8(opType);
                data << int32(val);
                SendPacket(&data);
            }
        }
    }

    if (Group* group = pCurrChar->GetGroup())
        group->SendUpdate();

    // pussywizard: send instance welcome message as when entering the instance through a portal
    if (MapDifficulty const* mapDiff = GetMapDifficultyData(pCurrChar->GetMap()->GetId(), pCurrChar->GetMap()->GetDifficulty()))
        if (mapDiff->resetTime)
            if (time_t timeReset = sInstanceSaveMgr->GetResetTimeFor(pCurrChar->GetMap()->GetId(), pCurrChar->GetMap()->GetDifficulty()))
            {
                uint32 timeleft = uint32(timeReset - GameTime::GetGameTime().count());
                GetPlayer()->SendInstanceResetWarning(pCurrChar->GetMap()->GetId(), pCurrChar->GetMap()->GetDifficulty(), timeleft, true);
            }

    // this shouldn't do anything, becaues offline can't be on taxi, but just in case
    pCurrChar->ContinueTaxiFlight();

    // send pet data, action bar, talents, etc.
    pCurrChar->PetSpellInitialize();
    pCurrChar->SendTalentsInfoData(true);

    // show time before shutdown if shutdown planned.
    if (sWorld->IsShuttingDown())
        sWorld->ShutdownMsg(true, pCurrChar);

    if (pCurrChar->IsGameMaster())
        ChatHandler(pCurrChar->GetSession()).SendNotification(LANG_GM_ON);

    m_playerLoading = false;
}

void WorldSession::HandlePlayerLoginToCharOutOfWorld(Player* /*pCurrChar*/)
{
    ABORT();
}

void WorldSession::HandleSetFactionAtWar(WorldPacket& recvData)
{
    uint32 repListID;
    uint8  flag;

    recvData >> repListID;
    recvData >> flag;

    GetPlayer()->GetReputationMgr().SetAtWar(repListID, flag);
}

//I think this function is never used :/ I dunno, but i guess this opcode not exists
void WorldSession::HandleSetFactionCheat(WorldPacket& /*recvData*/)
{
    LOG_ERROR("network.opcode", "WORLD SESSION: HandleSetFactionCheat, not expected call, please report.");
    GetPlayer()->GetReputationMgr().SendStates();
}

void WorldSession::HandleTutorialFlag(WorldPacket& recvData)
{
    uint32 data;
    recvData >> data;

    uint8 index = uint8(data / 32);
    if (index >= MAX_ACCOUNT_TUTORIAL_VALUES)
        return;

    uint32 value = (data % 32);

    uint32 flag = GetTutorialInt(index);
    flag |= (1 << value);
    SetTutorialInt(index, flag);
}

void WorldSession::HandleTutorialClear(WorldPacket& /*recvData*/)
{
    for (uint8 i = 0; i < MAX_ACCOUNT_TUTORIAL_VALUES; ++i)
        SetTutorialInt(i, 0xFFFFFFFF);
}

void WorldSession::HandleTutorialReset(WorldPacket& /*recvData*/)
{
    for (uint8 i = 0; i < MAX_ACCOUNT_TUTORIAL_VALUES; ++i)
        SetTutorialInt(i, 0x00000000);
}

void WorldSession::HandleSetWatchedFactionOpcode(WorldPacket& recvData)
{
    uint32 fact;
    recvData >> fact;
    GetPlayer()->SetUInt32Value(PLAYER_FIELD_WATCHED_FACTION_INDEX, fact);
}

void WorldSession::HandleSetFactionInactiveOpcode(WorldPacket& recvData)
{
    uint32 replistid;
    uint8 inactive;
    recvData >> replistid >> inactive;

    _player->GetReputationMgr().SetInactive(replistid, inactive);
}

void WorldSession::HandleShowingHelmOpcode(WorldPackets::Character::ShowingHelm& packet)
{
    if (packet.ShowHelm)
        _player->RemovePlayerFlag(PLAYER_FLAGS_HIDE_HELM);
    else
        _player->SetPlayerFlag(PLAYER_FLAGS_HIDE_HELM);
}

void WorldSession::HandleShowingCloakOpcode(WorldPackets::Character::ShowingCloak& packet)
{
    if (packet.ShowCloak)
        _player->RemovePlayerFlag(PLAYER_FLAGS_HIDE_CLOAK);
    else
        _player->SetPlayerFlag(PLAYER_FLAGS_HIDE_CLOAK);
}

void WorldSession::HandleCharRenameOpcode(WorldPacket& recvData)
{
    std::shared_ptr<CharacterRenameInfo> renameInfo = std::make_shared<CharacterRenameInfo>();

    recvData >> renameInfo->Guid
        >> renameInfo->Name;

    // prevent character rename to invalid name
    if (!normalizePlayerName(renameInfo->Name))
    {
        SendCharRename(CHAR_NAME_NO_NAME, renameInfo.get());
        return;
    }

    uint8 res = ObjectMgr::CheckPlayerName(renameInfo->Name, true);
    if (res != CHAR_NAME_SUCCESS)
    {
        if (res != CHAR_NAME_RESERVED || !HasPermission(rbac::RBAC_PERM_SKIP_CHECK_CHARACTER_CREATION_RESERVEDNAME))
        {
            SendCharRename(ResponseCodes(res), renameInfo.get());
            return;
        }
    }

    // Ensure that the character belongs to the current account, that rename at login is enabled
    // and that there is no character with the desired new name
    CharacterDatabasePreparedStatement* stmt = CharacterDatabase.GetPreparedStatement(CHAR_SEL_FREE_NAME);

    stmt->SetData(0, renameInfo->Guid.GetCounter());
    stmt->SetData(1, GetAccountId());
    stmt->SetData(2, renameInfo->Name);

    _queryProcessor.AddCallback(CharacterDatabase.AsyncQuery(stmt)
        .WithPreparedCallback(std::bind(&WorldSession::HandleCharRenameCallBack, this, renameInfo, std::placeholders::_1)));
}

void WorldSession::HandleCharRenameCallBack(std::shared_ptr<CharacterRenameInfo> renameInfo, PreparedQueryResult result)
{
    if (!result)
    {
        SendCharRename(CHAR_CREATE_ERROR, renameInfo.get());
        return;
    }

    Field* fields = result->Fetch();

    ObjectGuid::LowType guidLow = fields[0].Get<uint32>();
    std::string oldName = fields[1].Get<std::string>();
    uint16 atLoginFlags = fields[2].Get<uint16>();

    if (!(atLoginFlags & AT_LOGIN_RENAME))
    {
        SendCharRename(CHAR_CREATE_ERROR, renameInfo.get());
        return;
    }

    atLoginFlags &= ~AT_LOGIN_RENAME;

    // pussywizard:
    if (ObjectAccessor::FindConnectedPlayer(ObjectGuid::Create<HighGuid::Player>(guidLow)) || sWorldSessionMgr->FindOfflineSessionForCharacterGUID(guidLow))
    {
        SendCharRename(CHAR_CREATE_ERROR, renameInfo.get());
        return;
    }

    // Update name and at_login flag in the db
    CharacterDatabasePreparedStatement* stmt = CharacterDatabase.GetPreparedStatement(CHAR_UPD_CHAR_NAME_AT_LOGIN);
    stmt->SetData(0, renameInfo->Name);
    stmt->SetData(1, atLoginFlags);
    stmt->SetData(2, guidLow);
    CharacterDatabase.Execute(stmt);

    // Removed declined name from db
    if (sWorld->getBoolConfig(CONFIG_DECLINED_NAMES_USED))
    {
        stmt = CharacterDatabase.GetPreparedStatement(CHAR_DEL_DECLINED_NAME);
        stmt->SetData(0, guidLow);
        CharacterDatabase.Execute(stmt);
    }

    LOG_INFO("entities.player.character", "Account: {} (IP: {}), Character [{}] (guid: {}) Changed name to: {}", GetAccountId(), GetRemoteAddress(), oldName, guidLow, renameInfo->Name);

    SendCharRename(RESPONSE_SUCCESS, renameInfo.get());

    // xinef: update global data
    sCharacterCache->UpdateCharacterData(renameInfo->Guid, renameInfo->Name);
}

void WorldSession::HandleSetPlayerDeclinedNames(WorldPacket& recvData)
{
    // pussywizard:
    if (!sWorld->getBoolConfig(CONFIG_DECLINED_NAMES_USED))
        return;

    ObjectGuid guid;
    recvData >> guid;

    // not accept declined names for unsupported languages
    std::string name;
    if (!sCharacterCache->GetCharacterNameByGuid(guid, name))
    {
        SendSetPlayerDeclinedNamesResult(DECLINED_NAMES_RESULT_ERROR, guid);
        return;
    }

    std::wstring wname;
    if (!Utf8toWStr(name, wname))
    {
        SendSetPlayerDeclinedNamesResult(DECLINED_NAMES_RESULT_ERROR, guid);
        return;
    }

    if (!isCyrillicCharacter(wname[0]))                      // name already stored as only single alphabet using
    {
        SendSetPlayerDeclinedNamesResult(DECLINED_NAMES_RESULT_ERROR, guid);
        return;
    }

    std::string name2;
    DeclinedName declinedname;

    recvData >> name2;

    if (name2 != name)                                       // character have different name
    {
        SendSetPlayerDeclinedNamesResult(DECLINED_NAMES_RESULT_ERROR, guid);
        return;
    }

    for (int i = 0; i < MAX_DECLINED_NAME_CASES; ++i)
    {
        recvData >> declinedname.name[i];
        if (!normalizePlayerName(declinedname.name[i]))
        {
            SendSetPlayerDeclinedNamesResult(DECLINED_NAMES_RESULT_ERROR, guid);
            return;
        }
    }

    if (!ObjectMgr::CheckDeclinedNames(wname, declinedname))
    {
        SendSetPlayerDeclinedNamesResult(DECLINED_NAMES_RESULT_ERROR, guid);
        return;
    }

    for (int i = 0; i < MAX_DECLINED_NAME_CASES; ++i)
        CharacterDatabase.EscapeString(declinedname.name[i]);

    CharacterDatabaseTransaction trans = CharacterDatabase.BeginTransaction();

    CharacterDatabasePreparedStatement* stmt = CharacterDatabase.GetPreparedStatement(CHAR_DEL_CHAR_DECLINED_NAME);
    stmt->SetData(0, guid.GetCounter());
    trans->Append(stmt);

    stmt = CharacterDatabase.GetPreparedStatement(CHAR_INS_CHAR_DECLINED_NAME);
    stmt->SetData(0, guid.GetCounter());

    for (uint8 i = 0; i < 5; i++)
        stmt->SetData(i + 1, declinedname.name[i]);

    trans->Append(stmt);

    CharacterDatabase.CommitTransaction(trans);

    SendSetPlayerDeclinedNamesResult(DECLINED_NAMES_RESULT_SUCCESS, guid);
}

void WorldSession::HandleAlterAppearance(WorldPacket& recvData)
{
    LOG_DEBUG("network", "CMSG_ALTER_APPEARANCE");

    uint32 Hair, Color, FacialHair, SkinColor;
    recvData >> Hair >> Color >> FacialHair >> SkinColor;

    BarberShopStyleEntry const* bs_hair = sBarberShopStyleStore.LookupEntry(Hair);

    if (!bs_hair || bs_hair->type != 0 || bs_hair->race != _player->getRace() || bs_hair->gender != _player->getGender())
        return;

    BarberShopStyleEntry const* bs_facialHair = sBarberShopStyleStore.LookupEntry(FacialHair);

    if (!bs_facialHair || bs_facialHair->type != 2 || bs_facialHair->race != _player->getRace() || bs_facialHair->gender != _player->getGender())
        return;

    BarberShopStyleEntry const* bs_skinColor = sBarberShopStyleStore.LookupEntry(SkinColor);

    if (bs_skinColor && (bs_skinColor->type != 3 || bs_skinColor->race != _player->getRace() || bs_skinColor->gender != _player->getGender()))
        return;

    if (_player->getRace() == RACE_VULPERA && (Color > 255 || bs_hair->hair_id > 255
        || bs_facialHair->hair_id > 255 || (bs_skinColor && bs_skinColor->hair_id > 255)
        || !VulperaAppearance::ValidateClass(_player->getGender(), _player->getClass(), VulperaAppearance::Fields(
            bs_skinColor ? uint8(bs_skinColor->hair_id) : _player->GetByteValue(PLAYER_BYTES, 0),
            _player->GetByteValue(PLAYER_BYTES, 1), uint8(bs_hair->hair_id), uint8(Color),
            uint8(bs_facialHair->hair_id)))))
        return;

    if (UsesHaranirAppearance(_player->getRace()))
    {
        uint64 const extra = CharacterEyeEffects::Appearance(uint64(_player->GetUInt32Value(UNIT_FIELD_PADDING))
            | (uint64(_player->GetUInt32Value(OBJECT_FIELD_PADDING)) << 32));
        if (Color > 255 || !HaranirAppearance::Validate(_player->getGender(), HaranirAppearance::Fields(
            bs_skinColor ? uint8(bs_skinColor->hair_id) : _player->GetByteValue(PLAYER_BYTES, 0),
            _player->GetByteValue(PLAYER_BYTES, 1), uint8(bs_hair->hair_id), uint8(Color),
            uint8(bs_facialHair->hair_id), extra)))
            return;
    }

    GameObject* go = _player->FindNearestGameObjectOfType(GAMEOBJECT_TYPE_BARBER_CHAIR, 5.0f);
    if (!go)
    {
        WorldPacket data(SMSG_BARBER_SHOP_RESULT, 4);
        data << uint32(2);
        SendPacket(&data);
        return;
    }

    if (_player->getStandState() != UNIT_STAND_STATE_SIT_LOW_CHAIR + go->GetGOInfo()->barberChair.chairheight)
    {
        WorldPacket data(SMSG_BARBER_SHOP_RESULT, 4);
        data << uint32(2);
        SendPacket(&data);
        return;
    }

    uint32 cost = _player->GetBarberShopCost(bs_hair->hair_id, Color, bs_facialHair->hair_id, bs_skinColor);

    // 0 - ok
    // 1, 3 - not enough money
    // 2 - you have to seat on barber chair
    if (!_player->HasEnoughMoney(cost))
    {
        WorldPacket data(SMSG_BARBER_SHOP_RESULT, 4);
        data << uint32(1);                                  // no money
        SendPacket(&data);
        return;
    }
    else
    {
        WorldPacket data(SMSG_BARBER_SHOP_RESULT, 4);
        data << uint32(0);                                  // ok
        SendPacket(&data);
    }

    _player->ModifyMoney(-int32(cost));                     // it isn't free
    _player->UpdateAchievementCriteria(ACHIEVEMENT_CRITERIA_TYPE_GOLD_SPENT_AT_BARBER, cost);

    _player->SetByteValue(PLAYER_BYTES, 2, uint8(bs_hair->hair_id));
    _player->SetByteValue(PLAYER_BYTES, 3, uint8(Color));
    _player->SetByteValue(PLAYER_BYTES_2, 0, uint8(bs_facialHair->hair_id));
    if (bs_skinColor)
        _player->SetByteValue(PLAYER_BYTES, 0, uint8(bs_skinColor->hair_id));

    _player->UpdateAchievementCriteria(ACHIEVEMENT_CRITERIA_TYPE_VISIT_BARBER_SHOP, 1);

    _player->SetStandState(0);                              // stand up
}

void WorldSession::HandleRemoveGlyph(WorldPacket& recvData)
{
    uint32 slot;
    recvData >> slot;

    if (slot >= MAX_GLYPH_SLOT_INDEX)
    {
        LOG_DEBUG("network", "Client sent wrong glyph slot number in opcode CMSG_REMOVE_GLYPH {}", slot);
        return;
    }

    if (uint32 glyph = _player->GetGlyph(slot))
    {
        if (GlyphPropertiesEntry const* glyphEntry = sGlyphPropertiesStore.LookupEntry(glyph))
        {
            _player->RemoveAurasDueToSpell(glyphEntry->SpellId);

            // Removed any triggered auras
            Unit::AuraMap& ownedAuras = _player->GetOwnedAuras();
            for (Unit::AuraMap::iterator iter = ownedAuras.begin(); iter != ownedAuras.end();)
            {
                Aura* aura = iter->second;
                if (SpellInfo const* triggeredByAuraSpellInfo = aura->GetTriggeredByAuraSpellInfo())
                {
                    if (triggeredByAuraSpellInfo->Id == glyphEntry->SpellId)
                    {
                        _player->RemoveOwnedAura(iter);
                        continue;
                    }
                }
                ++iter;
            }

            _player->SendLearnPacket(glyphEntry->SpellId, false); // Send packet to properly handle client-side spell tooltips
            _player->SetGlyph(slot, 0, true);
            _player->SendTalentsInfoData(false);
        }
    }
}

void WorldSession::HandleCharCustomize(WorldPacket& recvData)
{
    std::shared_ptr<CharacterCustomizeInfo> customizeInfo = std::make_shared<CharacterCustomizeInfo>();

    recvData >> customizeInfo->Guid;

    if (!IsLegitCharacterForAccount(customizeInfo->Guid))
    {
        LOG_ERROR("entities.player.cheat", "Account {}, IP: {} tried to customise {}, but it does not belong to their account!",
            GetAccountId(), GetRemoteAddress(), customizeInfo->Guid.ToString());
        recvData.rfinish();
        KickPlayer("WorldSession::HandleCharCustomize Trying to customise character of another account");
        return;
    }

    // pussywizard:
    if (ObjectAccessor::FindConnectedPlayer(customizeInfo->Guid) || sWorldSessionMgr->FindOfflineSessionForCharacterGUID(customizeInfo->Guid.GetCounter()))
    {
        recvData.rfinish();
        WorldPacket data(SMSG_CHAR_CUSTOMIZE, 1);
        data << uint8(CHAR_CREATE_ERROR);
        SendPacket(&data);
        return;
    }

    recvData >> customizeInfo->Name
        >> customizeInfo->Gender
        >> customizeInfo->Skin
        >> customizeInfo->HairColor
        >> customizeInfo->HairStyle
        >> customizeInfo->FacialHair
        >> customizeInfo->Face;

    if (!CharacterRetailLook::ReadTail(recvData, customizeInfo->HasRetailLook, customizeInfo->RetailLook))
    {
        SendCharCustomize(CHAR_CREATE_ERROR, customizeInfo.get());
        return;
    }

    if (!CharacterBodyShape::ReadTail(recvData, customizeInfo->HasBodyShape, customizeInfo->BodyShape))
    {
        SendCharCustomize(CHAR_CREATE_ERROR, customizeInfo.get());
        return;
    }

    if (!CharacterEyeEffects::ReadTail(recvData, 0, customizeInfo->HasEyeLightning, customizeInfo->EyeLightning))
    {
        SendCharCustomize(CHAR_CREATE_ERROR, customizeInfo.get());
        return;
    }

    CharacterDatabasePreparedStatement* stmt = CharacterDatabase.GetPreparedStatement(CHAR_SEL_CHAR_CUSTOMIZE_INFO);
    stmt->SetData(0, customizeInfo->Guid.GetCounter());

    _queryProcessor.AddCallback(CharacterDatabase.AsyncQuery(stmt)
        .WithPreparedCallback(std::bind(&WorldSession::HandleCharCustomizeCallback, this, customizeInfo, std::placeholders::_1)));
}

void WorldSession::HandleCharCustomizeCallback(std::shared_ptr<CharacterCustomizeInfo> customizeInfo, PreparedQueryResult result)
{
    if (!result)
    {
        SendCharCustomize(CHAR_CREATE_ERROR, customizeInfo.get());
        return;
    }

    // get the players old (at this moment current) race
    CharacterCacheEntry const* playerData = sCharacterCache->GetCharacterCacheByGuid(customizeInfo->Guid);
    if (!playerData)
    {
        SendCharCustomize(CHAR_CREATE_ERROR, customizeInfo.get());
        return;
    }

    Field* fields = result->Fetch();
    std::string oldName = fields[0].Get<std::string>();
    //uint8 plrRace = fields[1].Get<uint8>();
    //uint8 plrClass = fields[2].Get<uint8>();
    //uint8 plrGender = fields[3].Get<uint8>();
    uint32 atLoginFlags = fields[4].Get<uint16>();

    if (CreatureAppearance::Uses(fields[1].Get<uint8>()) && !CreatureAppearance::Validate(fields[1].Get<uint8>(),
        customizeInfo->Gender, {customizeInfo->Skin, customizeInfo->Face, customizeInfo->HairStyle,
            customizeInfo->HairColor, customizeInfo->FacialHair}))
    {
        SendCharCustomize(CHAR_CREATE_ERROR, customizeInfo.get());
        return;
    }

    if (fields[1].Get<uint8>() == RACE_VULPERA && !VulperaAppearance::ValidateClass(customizeInfo->Gender,
        fields[2].Get<uint8>(), VulperaAppearance::Fields(customizeInfo->Skin, customizeInfo->Face,
            customizeInfo->HairStyle, customizeInfo->HairColor, customizeInfo->FacialHair)))
    {
        SendCharCustomize(CHAR_CREATE_ERROR, customizeInfo.get());
        return;
    }

    if (!(atLoginFlags & AT_LOGIN_CUSTOMIZE))
    {
        SendCharCustomize(CHAR_CREATE_ERROR, customizeInfo.get());
        return;
    }

    atLoginFlags &= ~AT_LOGIN_CUSTOMIZE;

    // prevent character rename to invalid name
    if (!normalizePlayerName(customizeInfo->Name))
    {
        SendCharCustomize(CHAR_NAME_NO_NAME, customizeInfo.get());
        return;
    }

    ResponseCodes res = static_cast<ResponseCodes>(ObjectMgr::CheckPlayerName(customizeInfo->Name, true));
    if (res != CHAR_NAME_SUCCESS)
    {
        if (res != CHAR_NAME_RESERVED || !HasPermission(rbac::RBAC_PERM_SKIP_CHECK_CHARACTER_CREATION_RESERVEDNAME))
        {
            SendCharCustomize(res, customizeInfo.get());
            return;
        }
    }

    // character with this name already exist
    if (ObjectGuid newguid = sCharacterCache->GetCharacterGuidByName(customizeInfo->Name))
    {
        if (newguid != customizeInfo->Guid)
        {
            SendCharCustomize(CHAR_CREATE_NAME_IN_USE, customizeInfo.get());
            return;
        }
    }

    CharacterDatabasePreparedStatement* stmt = nullptr;
    CharacterDatabaseTransaction trans = CharacterDatabase.BeginTransaction();

    ObjectGuid::LowType lowGuid = customizeInfo->Guid.GetCounter();

    /// Customize
    Player::Customize(customizeInfo.get(), trans);

    /// Name Change and update atLogin flags
    {
        stmt = CharacterDatabase.GetPreparedStatement(CHAR_UPD_CHAR_NAME_AT_LOGIN);
        stmt->SetData(0, customizeInfo->Name);
        stmt->SetData(1, atLoginFlags);
        stmt->SetData(2, lowGuid);

        trans->Append(stmt);

        if (sWorld->getBoolConfig(CONFIG_DECLINED_NAMES_USED))
        {
            stmt = CharacterDatabase.GetPreparedStatement(CHAR_DEL_DECLINED_NAME);
            stmt->SetData(0, lowGuid);

            trans->Append(stmt);
        }
    }

    CharacterDatabase.CommitTransaction(trans);

    sCharacterCache->UpdateCharacterData(customizeInfo->Guid, customizeInfo->Name, customizeInfo->Gender);

    SendCharCustomize(RESPONSE_SUCCESS, customizeInfo.get());

    LOG_INFO("entities.player.character", "Account: {} (IP: {}), Character[{}] ({}) Customized to: {}",
        GetAccountId(), GetRemoteAddress(), oldName, customizeInfo->Guid.ToString(), customizeInfo->Name);
}

void WorldSession::HandleEquipmentSetSave(WorldPacket& recvData)
{
    LOG_DEBUG("network", "CMSG_EQUIPMENT_SET_SAVE");

    uint64 setGuid;
    recvData.readPackGUID(setGuid);

    uint32 index;
    recvData >> index;
    if (index >= MAX_EQUIPMENT_SET_INDEX)                    // client set slots amount
        return;

    std::string name;
    recvData >> name;

    if (name.length() > 16) // Client limitation
    {
        LOG_ERROR("entities.player.cheat", "Character GUID {} tried to create equipment set {} with too long a name!", _player->GetGUID().ToString(), setGuid);
        return;
    }

    std::string iconName;
    recvData >> iconName;

    if (iconName.length() > 100) // DB limitation
    {
        LOG_ERROR("entities.player.cheat", "Character GUID {} tried to create equipment set {} with too long an icon name!", _player->GetGUID().ToString(), setGuid);
        return;
    }

    EquipmentSet eqSet;

    eqSet.Guid = setGuid;
    eqSet.Name = name;
    eqSet.IconName = iconName;
    eqSet.state = EQUIPMENT_SET_NEW;

    for (uint32 i = 0; i < EQUIPMENT_SLOT_END; ++i)
    {
        ObjectGuid itemGuid;
        recvData >> itemGuid.ReadAsPacked();

        // xinef: if client sends 0, it means empty slot
        if (!itemGuid)
        {
            eqSet.Items[i].Clear();
            continue;
        }

        // equipment manager sends "1" (as raw GUID) for slots set to "ignore" (don't touch slot at equip set)
        if (itemGuid.GetRawValue() == 1)
        {
            // ignored slots saved as bit mask because we have no free special values for Items[i]
            eqSet.IgnoreMask |= 1 << i;
            continue;
        }

        // xinef: some cheating checks
        Item* item = _player->GetItemByPos(INVENTORY_SLOT_BAG_0, i);
        if (!item || item->GetGUID() != itemGuid)
        {
            eqSet.Items[i].Clear();
            continue;
        }

        eqSet.Items[i] = itemGuid;
    }

    _player->SetEquipmentSet(index, eqSet);
}

void WorldSession::HandleEquipmentSetDelete(WorldPacket& recvData)
{
    LOG_DEBUG("network", "CMSG_EQUIPMENT_SET_DELETE");

    uint64 setGuid;
    recvData.readPackGUID(setGuid);

    _player->DeleteEquipmentSet(setGuid);
}

void WorldSession::HandleEquipmentSetUse(WorldPacket& recvData)
{
    LOG_DEBUG("network", "CMSG_EQUIPMENT_SET_USE");

    std::vector<std::unique_ptr<SavedItem>> savedItems;
    uint8 errorId = 0;
    for (uint32 i = 0; i < EQUIPMENT_SLOT_END; ++i)
    {
        ObjectGuid itemGuid;
        recvData >> itemGuid.ReadAsPacked();

        uint8 srcbag, srcslot;
        recvData >> srcbag >> srcslot;

        LOG_DEBUG("entities.player.items", "Item {}: srcbag {}, srcslot {}", itemGuid.ToString(), srcbag, srcslot);

        // check if item slot is set to "ignored" (raw value == 1), must not be unequipped then
        if (itemGuid.GetRawValue() == 1)
            continue;

        // Only equip weapons in combat
        if (_player->IsInCombat() && i != EQUIPMENT_SLOT_MAINHAND && i != EQUIPMENT_SLOT_OFFHAND && i != EQUIPMENT_SLOT_RANGED)
            continue;

        Item* item = nullptr;
        if (itemGuid)
            item = _player->GetItemByGuid(itemGuid);

        uint16 dstpos = i | (INVENTORY_SLOT_BAG_0 << 8);

        InventoryResult msg;
        Item* uItem = _player->GetItemByPos(INVENTORY_SLOT_BAG_0, i);
        if (uItem)
        {
            if (uItem->IsEquipped())
            {
                msg = _player->CanUnequipItem(dstpos, true);
                if (msg != EQUIP_ERR_OK)
                {
                    _player->SendEquipError(msg, uItem, nullptr);
                    continue;
                }
            }

            if (!item)
            {
                ItemPosCountVec sDest;
                msg = _player->CanStoreItem(NULL_BAG, NULL_SLOT, sDest, uItem, false);
                if (msg == EQUIP_ERR_OK)
                {
                    savedItems.emplace_back(std::make_unique<SavedItem>(uItem, dstpos));
                    _player->RemoveItem(INVENTORY_SLOT_BAG_0, i, true);
                    _player->StoreItem(sDest, uItem, true);
                }
                else
                {
                    errorId = 4;
                    for (uint8_t j = 0; j < savedItems.size(); ++j)
                    {
                        _player->SwapItem(savedItems[j].get()->item->GetPos(), savedItems[j].get()->dstpos);
                    }
                    break;
                }

                continue;
            }
        }

        if (item)
        {
            if (item->GetPos() == dstpos)
                continue;

            if (!item->IsEquipped())
            {
                uint16 _candidatePos;
                msg = _player->CanEquipItem(NULL_SLOT, _candidatePos, item, true);
                if (msg != EQUIP_ERR_OK)
                {
                    _player->SendEquipError(msg, item, nullptr);
                    continue;
                }
            }

            _player->SwapItem(item->GetPos(), dstpos);
        }
    }

    WorldPacket data(SMSG_EQUIPMENT_SET_USE_RESULT, 1);
    data << uint8(errorId);                                       // 4 - equipment swap failed - inventory is full
    SendPacket(&data);
}

void WorldSession::HandleCharFactionOrRaceChange(WorldPacket& recvData)
{
    std::shared_ptr<CharacterFactionChangeInfo> factionChangeInfo = std::make_shared<CharacterFactionChangeInfo>();

    recvData >> factionChangeInfo->Guid;

    if (!IsLegitCharacterForAccount(factionChangeInfo->Guid))
    {
        LOG_ERROR("entities.player.cheat", "Account {}, IP: {} tried to factionchange character {}, but it does not belong to their account!",
            GetAccountId(), GetRemoteAddress(), factionChangeInfo->Guid.ToString());
        recvData.rfinish();
        KickPlayer("WorldSession::HandleCharFactionOrRaceChange Trying to change faction of character of another account");
        return;
    }

    recvData >> factionChangeInfo->Name
        >> factionChangeInfo->Gender
        >> factionChangeInfo->Skin
        >> factionChangeInfo->HairColor
        >> factionChangeInfo->HairStyle
        >> factionChangeInfo->FacialHair
        >> factionChangeInfo->Face
        >> factionChangeInfo->Race;

    if (!CharacterRetailLook::ReadTail(recvData, factionChangeInfo->HasRetailLook, factionChangeInfo->RetailLook))
    {
        SendCharFactionChange(CHAR_CREATE_ERROR, factionChangeInfo.get());
        return;
    }

    if (!CharacterBodyShape::ReadTail(recvData, factionChangeInfo->HasBodyShape, factionChangeInfo->BodyShape))
    {
        SendCharFactionChange(CHAR_CREATE_ERROR, factionChangeInfo.get());
        return;
    }

    if (!CharacterEyeEffects::ReadTail(recvData, 0, factionChangeInfo->HasEyeLightning, factionChangeInfo->EyeLightning))
    {
        SendCharFactionChange(CHAR_CREATE_ERROR, factionChangeInfo.get());
        return;
    }

    // pussywizard:
    if (ObjectAccessor::FindConnectedPlayer(factionChangeInfo->Guid) || sWorldSessionMgr->FindOfflineSessionForCharacterGUID(factionChangeInfo->Guid.GetCounter()))
    {
        SendCharFactionChange(CHAR_CREATE_ERROR, factionChangeInfo.get());
        return;
    }

    factionChangeInfo->FactionChange = (recvData.GetOpcode() == CMSG_CHAR_FACTION_CHANGE);

    CharacterDatabasePreparedStatement* stmt = CharacterDatabase.GetPreparedStatement(CHAR_SEL_CHAR_RACE_OR_FACTION_CHANGE_INFOS);
    stmt->SetData(0, factionChangeInfo->Guid.GetCounter());

    _queryProcessor.AddCallback(CharacterDatabase.AsyncQuery(stmt)
        .WithPreparedCallback(std::bind(&WorldSession::HandleCharFactionOrRaceChangeCallback, this, factionChangeInfo, std::placeholders::_1)));
}

void WorldSession::HandleCharFactionOrRaceChangeCallback(std::shared_ptr<CharacterFactionChangeInfo> factionChangeInfo, PreparedQueryResult result)
{
    if (factionChangeInfo->Race == RACE_SLIME_GIANT_ALLIANCE || factionChangeInfo->Race == RACE_CENTAUR_HORDE)
    {
        SendCharFactionChange(CHAR_CREATE_DISABLED, factionChangeInfo.get());
        return;
    }
    if (!result)
    {
        SendCharFactionChange(CHAR_CREATE_ERROR, factionChangeInfo.get());
        return;
    }

    ObjectGuid::LowType lowGuid = factionChangeInfo->Guid.GetCounter();

    // get the players old (at this moment current) race
    CharacterCacheEntry const* playerData = sCharacterCache->GetCharacterCacheByGuid(factionChangeInfo->Guid);
    if (!playerData)
    {
        SendCharFactionChange(CHAR_CREATE_ERROR, factionChangeInfo.get());
        return;
    }

    uint8 oldRace = playerData->Race;
    uint8 playerClass = playerData->Class;
    uint8 level = playerData->Level;

    if (CreatureAppearance::Uses(factionChangeInfo->Race) && !CreatureAppearance::Validate(factionChangeInfo->Race,
        factionChangeInfo->Gender, {factionChangeInfo->Skin, factionChangeInfo->Face, factionChangeInfo->HairStyle,
            factionChangeInfo->HairColor, factionChangeInfo->FacialHair}))
    {
        SendCharFactionChange(CHAR_CREATE_ERROR, factionChangeInfo.get());
        return;
    }

    if (factionChangeInfo->Race == RACE_VULPERA && !VulperaAppearance::ValidateClass(factionChangeInfo->Gender,
        playerClass, VulperaAppearance::Fields(factionChangeInfo->Skin, factionChangeInfo->Face,
            factionChangeInfo->HairStyle, factionChangeInfo->HairColor, factionChangeInfo->FacialHair)))
    {
        SendCharFactionChange(CHAR_CREATE_ERROR, factionChangeInfo.get());
        return;
    }

    if (!sObjectMgr->GetPlayerInfo(factionChangeInfo->Race, playerClass))
    {
        SendCharFactionChange(CHAR_CREATE_ERROR, factionChangeInfo.get());
        return;
    }

    Field* fields = result->Fetch();
    uint32 atLoginFlags = fields[0].Get<uint16>();
    std::string knownTitlesStr = fields[1].Get<std::string>();
    uint32 money = fields[2].Get<uint32>();
    if (fields[3].IsNull())
    {
        SendCharFactionChange(CHAR_CREATE_ERROR, factionChangeInfo.get());
        return;
    }

    // TINYINT UNSIGNED: read as uint8. See the note in Player::BuildEnumData.
    uint32 const oldPersistentTeamValue = fields[3].Get<uint8>();
    if (!IsValidPlayerTeamId(oldPersistentTeamValue))
    {
        SendCharFactionChange(CHAR_CREATE_ERROR, factionChangeInfo.get());
        return;
    }
    TeamId const oldPersistentTeamId = static_cast<TeamId>(oldPersistentTeamValue);

    uint32 usedLoginFlag = (factionChangeInfo->FactionChange ? AT_LOGIN_CHANGE_FACTION : AT_LOGIN_CHANGE_RACE);
    if (!(atLoginFlags & usedLoginFlag))
    {
        SendCharFactionChange(CHAR_CREATE_ERROR, factionChangeInfo.get());
        return;
    }

    // xinef: add some safety checks
    if (factionChangeInfo->FactionChange)
    {
        // if player is in a guild
        if (playerData->GuildId && !sWorld->getBoolConfig(CONFIG_ALLOW_TWO_SIDE_INTERACTION_GUILD))
        {
            SendCharFactionChange(CHAR_CREATE_CHARACTER_IN_GUILD, factionChangeInfo.get());
            return;
        }

        // is arena team captain
        if (sArenaTeamMgr->GetArenaTeamByCaptain(factionChangeInfo->Guid))
        {
            SendCharFactionChange(CHAR_CREATE_CHARACTER_ARENA_LEADER, factionChangeInfo.get());
            return;
        }

        // check mailbox
        if (playerData->MailCount)
        {
            SendCharFactionChange(CHAR_CREATE_CHARACTER_DELETE_MAIL, factionChangeInfo.get());
            return;
        }

        // check auctions, current packet is processed single-threaded way, so not a problem
        bool has_auctions = false;

        for (uint8 i = 0; i < 2; ++i) // check both neutral and faction-specific AH
        {
            AuctionHouseObject* auctionHouse = sAuctionMgr->GetAuctionsMap(
                i == 0 ? 0 : (Player::TeamIdForRace(playerData->Race) == TEAM_ALLIANCE ? 12 : 29));

            for (auto const& [auID, Aentry] : auctionHouse->GetAuctions())
            {
                if (Aentry && (Aentry->owner == factionChangeInfo->Guid || Aentry->bidder == factionChangeInfo->Guid))
                {
                    has_auctions = true;
                    break;
                }
            }

            if (has_auctions)
                break;
        }

        if (has_auctions)
        {
            SendCharFactionChange(CHAR_CREATE_ERROR, factionChangeInfo.get());
            return;
        }
    }

    TeamId newTeam = Player::TeamIdForRace(factionChangeInfo->Race);
    TeamId const newPersistentTeamId = oldPersistentTeamId == TEAM_FREEBORN ? TEAM_FREEBORN : newTeam;
    if (factionChangeInfo->FactionChange == (Player::TeamIdForRace(oldRace) == newTeam))
    {
        SendCharFactionChange(factionChangeInfo->FactionChange ? CHAR_CREATE_CHARACTER_SWAP_FACTION : CHAR_CREATE_CHARACTER_RACE_ONLY, factionChangeInfo.get());
        return;
    }

    uint32 maxMoney = sWorld->getIntConfig(CONFIG_CHANGE_FACTION_MAX_MONEY);
    if (maxMoney && money > maxMoney)
    {
        SendCharFactionChange(CHAR_CREATE_CHARACTER_GOLD_LIMIT, factionChangeInfo.get());
        return;
    }

    // pussywizard: check titles here to prevent return while building queries
    const uint32 ktcount = KNOWN_TITLES_SIZE * 2;
    std::vector<std::string_view> tokens = Acore::Tokenize(knownTitlesStr, ' ', false);

    if (factionChangeInfo->FactionChange && tokens.size() != ktcount)
    {
        SendCharFactionChange(CHAR_CREATE_ERROR, factionChangeInfo.get());
        return;
    }

    if (!HasPermission(rbac::RBAC_PERM_SKIP_CHECK_CHARACTER_CREATION_RACEMASK))
    {
        uint32 raceMaskDisabled = sWorld->getIntConfig(CONFIG_CHARACTER_CREATING_DISABLED_RACEMASK);
        if (GetRaceMaskForRace(factionChangeInfo->Race) & raceMaskDisabled)
        {
            SendCharFactionChange(CHAR_CREATE_ERROR, factionChangeInfo.get());
            return;
        }
    }

    // prevent character rename to invalid name
    if (!normalizePlayerName(factionChangeInfo->Name))
    {
        SendCharFactionChange(CHAR_NAME_NO_NAME, factionChangeInfo.get());
        return;
    }

    ResponseCodes res = static_cast<ResponseCodes>(ObjectMgr::CheckPlayerName(factionChangeInfo->Name, true));
    if (res != CHAR_NAME_SUCCESS)
    {
        if (res != CHAR_NAME_RESERVED || !HasPermission(rbac::RBAC_PERM_SKIP_CHECK_CHARACTER_CREATION_RESERVEDNAME))
        {
            SendCharFactionChange(res, factionChangeInfo.get());
            return;
        }
    }

    // character with this name already exist
    if (ObjectGuid newguid = sCharacterCache->GetCharacterGuidByName(factionChangeInfo->Name))
    {
        if (newguid != factionChangeInfo->Guid)
        {
            SendCharFactionChange(CHAR_CREATE_NAME_IN_USE, factionChangeInfo.get());
            return;
        }
    }

    CharacterDatabasePreparedStatement* stmt = nullptr;
    CharacterDatabaseTransaction trans = CharacterDatabase.BeginTransaction();

    // resurrect the character in case he's dead
    Player::OfflineResurrect(factionChangeInfo->Guid, trans);

    // Name Change and update atLogin flags
    {
        CharacterDatabase.EscapeString(factionChangeInfo->Name);

        stmt = CharacterDatabase.GetPreparedStatement(CHAR_UPD_CHAR_NAME_AT_LOGIN);
        stmt->SetData(0, factionChangeInfo->Name);
        stmt->SetData(1, uint16((atLoginFlags | AT_LOGIN_RESURRECT) & ~usedLoginFlag));
        stmt->SetData(2, lowGuid);
        trans->Append(stmt);

        stmt = CharacterDatabase.GetPreparedStatement(CHAR_DEL_CHAR_DECLINED_NAME);
        stmt->SetData(0, lowGuid);
        trans->Append(stmt);
    }

    // Customize
    Player::Customize(factionChangeInfo.get(), trans);

    // Race Change
    {
        stmt = CharacterDatabase.GetPreparedStatement(CHAR_UPD_CHAR_RACE);
        stmt->SetData(0, factionChangeInfo->Race);
        stmt->SetData(1, static_cast<uint8>(newPersistentTeamId));
        stmt->SetData(2, lowGuid);
        trans->Append(stmt);
    }

    LOG_INFO("entities.player.character", "Account: {} (IP: {}), Character [{}] (guid: {}) Changed Race/Faction to: {}",
        GetAccountId(), GetRemoteAddress(), playerData->Name, lowGuid, factionChangeInfo->Name);

    // xinef: update global data
    sCharacterCache->UpdateCharacterData(factionChangeInfo->Guid, factionChangeInfo->Name, factionChangeInfo->Gender, factionChangeInfo->Race);
    sCharacterCache->UpdateCharacterTeamId(factionChangeInfo->Guid, newPersistentTeamId);

    if (oldRace != factionChangeInfo->Race)
    {
        // Switch Languages
        // delete all languages first
        stmt = CharacterDatabase.GetPreparedStatement(CHAR_DEL_CHAR_SKILL_LANGUAGES);
        stmt->SetData(0, lowGuid);
        trans->Append(stmt);

        // Now add them back
        stmt = CharacterDatabase.GetPreparedStatement(CHAR_INS_CHAR_SKILL_LANGUAGE);
        stmt->SetData(0, lowGuid);

        // Faction specific languages
        if (newTeam == TEAM_HORDE)
            stmt->SetData(1, 109);
        else
            stmt->SetData(1, 98);

        trans->Append(stmt);

        // Race specific languages
        if (factionChangeInfo->Race != RACE_ORC && factionChangeInfo->Race != RACE_HUMAN)
        {
            stmt = CharacterDatabase.GetPreparedStatement(CHAR_INS_CHAR_SKILL_LANGUAGE);
            stmt->SetData(0, lowGuid);

            switch (factionChangeInfo->Race)
            {
            case RACE_DWARF:
                stmt->SetData(1, 111);
                break;
            case RACE_DRAENEI:
                stmt->SetData(1, 759);
                break;
            case RACE_GNOME:
                stmt->SetData(1, 313);
                break;
            case RACE_NIGHTELF:
                stmt->SetData(1, 113);
                break;
            case RACE_UNDEAD_PLAYER:
                stmt->SetData(1, 673);
                break;
            case RACE_TAUREN:
                stmt->SetData(1, 115);
                break;
            case RACE_TROLL:
                stmt->SetData(1, 315);
                break;
            case RACE_BLOODELF:
                stmt->SetData(1, 137);
                break;
            }

            trans->Append(stmt);
        }

        if (factionChangeInfo->FactionChange)
        {
            {
                // Delete all Flypaths
                stmt = CharacterDatabase.GetPreparedStatement(CHAR_UPD_CHAR_TAXI_PATH);
                stmt->SetData(0, lowGuid);
                trans->Append(stmt);

                // Update Taxi path
                TaxiMask newTaxiMask;
                newTaxiMask.fill(0);

                TaxiMask const& factionMask = newTeam == TEAM_HORDE ? sHordeTaxiNodesMask : sAllianceTaxiNodesMask;
                for (auto const& itr : sTaxiPathSetBySource)
                {
                    auto FillTaxiMask = [&](uint8 field, uint32 mask)
                        {
                            if (playerClass == CLASS_DEATH_KNIGHT)
                            {
                                newTaxiMask[field] |= uint32(mask | (sDeathKnightTaxiNodesMask[field] & mask));
                            }
                            else
                            {
                                newTaxiMask[field] |= mask;
                            }
                        };

                    uint32 nodeId = itr.first;
                    uint8 field = (uint8)((nodeId - 1) / 32);
                    uint32 submask = 1 << ((nodeId - 1) % 32);

                    if ((factionMask[field] & submask) == 0)
                    {
                        FillTaxiMask(field, 0);
                        continue;
                    }

                    TaxiPathSetForSource const& taxiPaths = itr.second;
                    if (taxiPaths.empty())
                    {
                        FillTaxiMask(field, 0);
                        continue;
                    }

                    TaxiPathEntry const* taxiPath = taxiPaths.begin()->second;
                    if (!taxiPath)
                    {
                        FillTaxiMask(field, 0);
                        continue;
                    }

                    TaxiPathNodeList const& taxiNodePaths = sTaxiPathNodesByPath[taxiPath->ID];
                    if (taxiNodePaths.empty())
                    {
                        FillTaxiMask(field, 0);
                        continue;
                    }

                    TaxiPathNodeEntry const* pathNode = taxiNodePaths.front();
                    if (!pathNode)
                    {
                        FillTaxiMask(field, 0);
                        continue;
                    }

                    AreaTableEntry const* zone = sAreaTableStore.LookupEntry(sMapMgr->GetZoneId(PHASEMASK_NORMAL, pathNode->mapid, pathNode->x, pathNode->y, pathNode->z));
                    if (!zone)
                    {
                        FillTaxiMask(field, 0);
                        continue;
                    }

                    LFGDungeonEntry const* lfgDungeon = GetZoneLFGDungeonEntry(zone->area_name[GetSessionDbLocaleIndex()], GetSessionDbLocaleIndex());
                    if (!lfgDungeon)
                    {
                        FillTaxiMask(field, 0);
                        continue;
                    }

                    // Get level from LFGDungeonEntry because the one from AreaTableEntry is not valid
                    // If area level is too big, do not add new taxi
                    if (lfgDungeon->MinLevel > level)
                    {
                        FillTaxiMask(field, 0);
                        continue;
                    }

                    FillTaxiMask(field, submask);
                }

                std::ostringstream taximaskstream;
                for (uint8 i = 0; i < TaxiMaskSize; ++i)
                    taximaskstream << uint32(newTaxiMask[i]) << ' ';

                stmt = CharacterDatabase.GetPreparedStatement(CHAR_UPD_CHAR_TAXIMASK);
                stmt->SetData(0, taximaskstream.str());
                stmt->SetData(1, lowGuid);
                trans->Append(stmt);
            }

            // Reset guild
            if (!sWorld->getBoolConfig(CONFIG_ALLOW_TWO_SIDE_INTERACTION_GUILD))
            {
                if (uint32 guildId = playerData->GuildId)
                    if (Guild* guild = sGuildMgr->GetGuildById(guildId))
                        guild->DeleteMember(factionChangeInfo->Guid, false, false, true);
            }

            if (!HasPermission(rbac::RBAC_PERM_TWO_SIDE_ADD_FRIEND))
            {
                // Delete Friend List
                stmt = CharacterDatabase.GetPreparedStatement(CHAR_DEL_CHAR_SOCIAL_BY_GUID);
                stmt->SetData(0, lowGuid);
                trans->Append(stmt);

                stmt = CharacterDatabase.GetPreparedStatement(CHAR_DEL_CHAR_SOCIAL_BY_FRIEND);
                stmt->SetData(0, lowGuid);
                trans->Append(stmt);
            }

            // Leave Arena Teams
            Player::LeaveAllArenaTeams(factionChangeInfo->Guid);

            // Reset homebind and position
            stmt = CharacterDatabase.GetPreparedStatement(CHAR_DEL_PLAYER_HOMEBIND);
            stmt->SetData(0, lowGuid);
            trans->Append(stmt);

            stmt = CharacterDatabase.GetPreparedStatement(CHAR_INS_PLAYER_HOMEBIND);
            stmt->SetData(0, lowGuid);

            WorldLocation loc;
            uint16 zoneId = 0;

            if (newTeam == TEAM_ALLIANCE)
            {
                loc.WorldRelocate(MAP_EASTERN_KINGDOMS, -8867.68f, 673.373f, 97.9034f, 0.0f);
                zoneId = AREA_STORMWIND_CITY;
            }
            else
            {
                loc.WorldRelocate(MAP_KALIMDOR, 1633.33f, -4439.11f, 15.7588f, 0.0f);
                zoneId = AREA_ORGRIMMAR;
            }

            stmt->SetData(1, loc.GetMapId());
            stmt->SetData(2, zoneId);
            stmt->SetData(3, loc.GetPositionX());
            stmt->SetData(4, loc.GetPositionY());
            stmt->SetData(5, loc.GetPositionZ());
            trans->Append(stmt);

            Player::SavePositionInDB(loc, zoneId, factionChangeInfo->Guid, trans);

            // Achievement conversion
            for (auto const& [achiev_alliance, achiev_horde] : sObjectMgr->FactionChangeAchievements)
            {
                stmt = CharacterDatabase.GetPreparedStatement(CHAR_DEL_CHAR_ACHIEVEMENT_BY_ACHIEVEMENT);
                stmt->SetData(0, uint16(newTeam == TEAM_ALLIANCE ? achiev_alliance : achiev_horde));
                stmt->SetData(1, lowGuid);
                trans->Append(stmt);

                stmt = CharacterDatabase.GetPreparedStatement(CHAR_UPD_CHAR_ACHIEVEMENT);
                stmt->SetData(0, uint16(newTeam == TEAM_ALLIANCE ? achiev_alliance : achiev_horde));
                stmt->SetData(1, uint16(newTeam == TEAM_ALLIANCE ? achiev_horde : achiev_alliance));
                stmt->SetData(2, lowGuid);
                trans->Append(stmt);
            }

            // Item conversion
            for (auto const& [item_alliance, item_horde] : sObjectMgr->FactionChangeItems)
            {
                uint32 new_entry = (newTeam == TEAM_ALLIANCE ? item_alliance : item_horde);
                uint32 old_entry = (newTeam == TEAM_ALLIANCE ? item_horde : item_alliance);

                if (old_entry == 45978 /*Solid Gold Coin*/ || old_entry == 2589 /*Linen Cloth*/ || old_entry == 5976 /*Guild Tabard*/)
                    continue;

                stmt = CharacterDatabase.GetPreparedStatement(CHAR_UPD_CHAR_INVENTORY_FACTION_CHANGE);
                stmt->SetData(0, new_entry);
                stmt->SetData(1, old_entry);
                stmt->SetData(2, lowGuid);
                trans->Append(stmt);
            }

            // Delete all current quests
            stmt = CharacterDatabase.GetPreparedStatement(CHAR_DEL_CHAR_QUESTSTATUS);
            stmt->SetData(0, lowGuid);
            trans->Append(stmt);

            // Quest conversion
            for (auto const& [quest_alliance, quest_horde] : sObjectMgr->FactionChangeQuests)
            {
                stmt = CharacterDatabase.GetPreparedStatement(CHAR_DEL_CHAR_QUESTSTATUS_REWARDED_BY_QUEST);
                stmt->SetData(0, lowGuid);
                stmt->SetData(1, (newTeam == TEAM_ALLIANCE ? quest_alliance : quest_horde));
                trans->Append(stmt);

                stmt = CharacterDatabase.GetPreparedStatement(CHAR_UPD_CHAR_QUESTSTATUS_REWARDED_FACTION_CHANGE);
                stmt->SetData(0, (newTeam == TEAM_ALLIANCE ? quest_alliance : quest_horde));
                stmt->SetData(1, (newTeam == TEAM_ALLIANCE ? quest_horde : quest_alliance));
                stmt->SetData(2, lowGuid);
                trans->Append(stmt);
            }

            // Mark all rewarded quests as "active" (will count for completed quests achievements)
            stmt = CharacterDatabase.GetPreparedStatement(CHAR_UPD_CHAR_QUESTSTATUS_REWARDED_ACTIVE);
            stmt->SetData(0, lowGuid);
            trans->Append(stmt);

            // Disable all old-faction specific quests
            for (auto const& [questID, quest] : sObjectMgr->GetQuestTemplates())
            {
                uint32 newRaceMask = (newTeam == TEAM_ALLIANCE) ? sRaceMgr->GetAllianceRaceMask() : sRaceMgr->GetHordeRaceMask();

                if (quest->GetAllowableRaces() && !(quest->GetAllowableRaces() & newRaceMask))
                {
                    stmt = CharacterDatabase.GetPreparedStatement(CHAR_UPD_CHAR_QUESTSTATUS_REWARDED_ACTIVE_BY_QUEST);
                    stmt->SetData(0, quest->GetQuestId());
                    stmt->SetData(1, lowGuid);
                    trans->Append(stmt);
                }
            }

            // Spell conversion
            for (auto const& [spell_alliance, spell_horde] : sObjectMgr->FactionChangeSpells)
            {
                stmt = CharacterDatabase.GetPreparedStatement(CHAR_DEL_CHAR_SPELL_BY_SPELL);
                stmt->SetData(0, lowGuid);
                stmt->SetData(1, (newTeam == TEAM_ALLIANCE ? spell_alliance : spell_horde));
                trans->Append(stmt);

                stmt = CharacterDatabase.GetPreparedStatement(CHAR_UPD_CHAR_SPELL_FACTION_CHANGE);
                stmt->SetData(0, (newTeam == TEAM_ALLIANCE ? spell_alliance : spell_horde));
                stmt->SetData(1, (newTeam == TEAM_ALLIANCE ? spell_horde : spell_alliance));
                stmt->SetData(2, lowGuid);
                trans->Append(stmt);
            }

            // Reputation conversion
            for (auto const& [reputation_alliance, reputation_horde] : sObjectMgr->FactionChangeReputation)
            {
                uint32 newReputation = (newTeam == TEAM_ALLIANCE) ? reputation_alliance : reputation_horde;
                uint32 oldReputation = (newTeam == TEAM_ALLIANCE) ? reputation_horde : reputation_alliance;

                // select old standing set in db
                stmt = CharacterDatabase.GetPreparedStatement(CHAR_SEL_CHAR_REP_BY_FACTION);
                stmt->SetData(0, oldReputation);
                stmt->SetData(1, lowGuid);

                PreparedQueryResult result = CharacterDatabase.Query(stmt);
                if (!result)
                    continue;

                fields = result->Fetch();
                int32 oldDBRep = fields[0].Get<int32>();
                FactionEntry const* factionEntry = sFactionStore.LookupEntry(oldReputation);

                // old base reputation
                int32 oldBaseRep = sObjectMgr->GetBaseReputationOf(factionEntry, oldRace, playerClass);

                // new base reputation
                int32 newBaseRep = sObjectMgr->GetBaseReputationOf(sFactionStore.LookupEntry(newReputation), factionChangeInfo->Race, playerClass);

                // final reputation shouldnt change
                int32 FinalRep = oldDBRep + oldBaseRep;
                int32 newDBRep = FinalRep - newBaseRep;

                stmt = CharacterDatabase.GetPreparedStatement(CHAR_DEL_CHAR_REP_BY_FACTION);
                stmt->SetData(0, newReputation);
                stmt->SetData(1, lowGuid);
                trans->Append(stmt);

                stmt = CharacterDatabase.GetPreparedStatement(CHAR_UPD_CHAR_REP_FACTION_CHANGE);
                stmt->SetData(0, uint16(newReputation));
                stmt->SetData(1, newDBRep);
                stmt->SetData(2, uint16(oldReputation));
                stmt->SetData(3, lowGuid);
                trans->Append(stmt);
            }

            // Title conversion
            if (!knownTitlesStr.empty())
            {
                std::array<uint32, KNOWN_TITLES_SIZE * 2> knownTitles;

                for (uint32 index = 0; index < knownTitles.size(); ++index)
                {
                    Optional<uint32> thisMask;
                    if (index < tokens.size())
                        thisMask = Acore::StringTo<uint32>(tokens[index]);

                    if (thisMask)
                        knownTitles[index] = *thisMask;
                    else
                    {
                        LOG_WARN("entities.player", "{} has invalid title data '{}' at index {} - skipped, this may result in titles being lost",
                            GetPlayerInfo(), (index < tokens.size()) ? std::string(tokens[index]) : "<none>", index);

                        knownTitles[index] = 0;
                    }
                }

                for (auto const& [title_alliance, title_horde] : sObjectMgr->FactionChangeTitles)
                {
                    CharTitlesEntry const* atitleInfo = sCharTitlesStore.LookupEntry(title_alliance);
                    CharTitlesEntry const* htitleInfo = sCharTitlesStore.LookupEntry(title_horde);

                    // new team
                    if (newTeam == TEAM_ALLIANCE)
                    {
                        uint32 bitIndex = htitleInfo->bit_index;
                        uint32 index = bitIndex / 32;
                        uint32 old_flag = 1 << (bitIndex % 32);
                        uint32 new_flag = 1 << (atitleInfo->bit_index % 32);

                        if (knownTitles[index] & old_flag)
                        {
                            knownTitles[index] &= ~old_flag;
                            // use index of the new title
                            knownTitles[atitleInfo->bit_index / 32] |= new_flag;
                        }
                    }
                    else
                    {
                        uint32 bitIndex = atitleInfo->bit_index;
                        uint32 index = bitIndex / 32;
                        uint32 old_flag = 1 << (bitIndex % 32);
                        uint32 new_flag = 1 << (htitleInfo->bit_index % 32);

                        if (knownTitles[index] & old_flag)
                        {
                            knownTitles[index] &= ~old_flag;
                            // use index of the new title
                            knownTitles[htitleInfo->bit_index / 32] |= new_flag;
                        }
                    }

                    std::ostringstream ss;
                    for (uint32 mask : knownTitles)
                        ss << mask << ' ';

                    stmt = CharacterDatabase.GetPreparedStatement(CHAR_UPD_CHAR_TITLES_FACTION_CHANGE);
                    stmt->SetData(0, ss.str().c_str());
                    stmt->SetData(1, lowGuid);
                    trans->Append(stmt);

                    // unset any currently chosen title
                    stmt = CharacterDatabase.GetPreparedStatement(CHAR_RES_CHAR_TITLES_FACTION_CHANGE);
                    stmt->SetData(0, lowGuid);
                    trans->Append(stmt);
                }
            }
        }
    }

    // Re-check all achievement criterias
    stmt = CharacterDatabase.GetPreparedStatement(CHAR_UPD_ADD_AT_LOGIN_FLAG);
    stmt->SetData(0, uint16(AT_LOGIN_CHECK_ACHIEVS));
    stmt->SetData(1, lowGuid);
    trans->Append(stmt);

    CharacterDatabase.CommitTransaction(trans);

    LOG_DEBUG("entities.player", "{} (IP: {}) changed race from {} to {}", GetPlayerInfo(), GetRemoteAddress(), oldRace, factionChangeInfo->Race);

    SendCharFactionChange(RESPONSE_SUCCESS, factionChangeInfo.get());
}

void WorldSession::SendCharCreate(ResponseCodes result)
{
    WorldPacket data(SMSG_CHAR_CREATE, 1);
    data << uint8(result);
    SendPacket(&data);
}

void WorldSession::SendCharDelete(ResponseCodes result)
{
    WorldPacket data(SMSG_CHAR_DELETE, 1);
    data << uint8(result);
    SendPacket(&data);
}

void WorldSession::SendCharLoginFailed(LoginFailureReason reason)
{
    WorldPacket data(SMSG_CHARACTER_LOGIN_FAILED, 1);
    data << uint8(reason);
    SendPacket(&data);
};

void WorldSession::SendCharRename(ResponseCodes result, CharacterRenameInfo const* renameInfo)
{
    WorldPacket data(SMSG_CHAR_RENAME, 1 + 8 + renameInfo->Name.size() + 1);
    data << uint8(result);
    if (result == RESPONSE_SUCCESS)
    {
        data << renameInfo->Guid;
        data << renameInfo->Name;
    }
    SendPacket(&data);
}

void WorldSession::SendCharFactionChange(ResponseCodes result, CharacterFactionChangeInfo const* factionChangeInfo)
{
    WorldPacket data(SMSG_CHAR_FACTION_CHANGE, 1 + 8 + factionChangeInfo->Name.size() + 1 + 7);
    data << uint8(result);
    if (result == RESPONSE_SUCCESS)
    {
        data << factionChangeInfo->Guid;
        data << factionChangeInfo->Name;
        data << uint8(factionChangeInfo->Gender);
        data << uint8(factionChangeInfo->Skin);
        data << uint8(factionChangeInfo->Face);
        data << uint8(factionChangeInfo->HairStyle);
        data << uint8(factionChangeInfo->HairColor);
        data << uint8(factionChangeInfo->FacialHair);
        data << uint8(factionChangeInfo->Race);
    }
    SendPacket(&data);
}

void WorldSession::SendCharCustomize(ResponseCodes result, CharacterCustomizeInfo const* customizeInfo)
{
    WorldPacket data(SMSG_CHAR_CUSTOMIZE, 1 + 8 + customizeInfo->Name.size() + 1 + 6);
    data << uint8(result);
    if (result == RESPONSE_SUCCESS)
    {
        data << customizeInfo->Guid;
        data << customizeInfo->Name;
        data << uint8(customizeInfo->Gender);
        data << uint8(customizeInfo->Skin);
        data << uint8(customizeInfo->Face);
        data << uint8(customizeInfo->HairStyle);
        data << uint8(customizeInfo->HairColor);
        data << uint8(customizeInfo->FacialHair);
    }
    SendPacket(&data);
}

void WorldSession::SendSetPlayerDeclinedNamesResult(DeclinedNameResult result, ObjectGuid guid)
{
    WorldPacket data(SMSG_SET_PLAYER_DECLINED_NAMES_RESULT, 4 + 8);
    data << uint32(result);
    data << guid;
    SendPacket(&data);
}
````
<!-- END FULL SOURCE 2 -->

### Appendix 3 NativeAppearance.cpp

Originally linked native appearance source.

Source: `client-customization/NativeAppearance.cpp`  
Absolute path: `R:\Users\Zach\Documents\GitHub\EsteriaWoW\client-customization\NativeAppearance.cpp`  
Source lines: 1 through 1803  
SHA256: `fff71c5632369aceb4d183c809339645e162c48437274cb6bfb3b354ce0f4c22`

<!-- BEGIN FULL SOURCE 3 -->
````cpp
// Esteria native appearance helpers. Loaded by Wow.exe's permanent import table.
// No WarcraftXL API, loader, events, or runtime patching is used.
#include <windows.h>

#include <cmath>
#include <cstdarg>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <vector>
#include <array>
#include <unordered_map>
#include <random>
#include <algorithm>
#include <string>
#include <memory>
#include <wincodec.h>
#include <wrl/client.h>
#pragma comment(lib, "windowscodecs.lib")
#pragma comment(lib, "ole32.lib")
#include "../src/server/shared/HighmountainAppearance.h"
#include "../src/server/shared/EarthenAppearance.h"
#include "../src/server/shared/HaranirAppearance.h"
#include "../src/server/shared/VulperaAppearance.h"
#include "../src/server/shared/CreatureAppearance.h"

namespace
{
    bool HighmountainGeometry(void* character);
    bool HighmountainCycle(void* state, char const* command);
    bool PreviewAppearance(void* character, char const* command);
    bool dropdownWheelBlocked = false;
}

namespace
{
    constexpr unsigned RaceCount = 129;
    constexpr unsigned AppearanceProfileCount = RaceCount * 2;

    FILE* CatalogFile(wchar_t const* name)
    {
        wchar_t path[MAX_PATH] = {};
        if (!GetModuleFileNameW(nullptr, path, MAX_PATH))
            return nullptr;
        wchar_t* slash = std::wcsrchr(path, L'\\');
        if (!slash || slash - path + 1 + std::wcslen(name) >= MAX_PATH)
            return nullptr;
        std::wcscpy(slash + 1, name);
        FILE* file = nullptr;
        return _wfopen_s(&file, path, L"rb") ? nullptr : file;
    }

    struct Option
    {
        std::uint32_t offset;
        std::uint32_t count;
        std::uint32_t factor;
        std::uint32_t geometryOffset;
        std::uint32_t geometryChoices[32];
    };

    struct Profile
    {
        std::uint32_t race;
        std::uint32_t gender;
        std::uint32_t optionCount;
        Option options[16];
    };

    std::vector<Profile> const& Profiles()
    {
        static std::vector<Profile> const profiles = []
        {
            std::vector<Profile> result;
            FILE* file = CatalogFile(L"EsteriaAppearance.bin");
            if (!file)
                return result;
            std::uint32_t header[3] = {};
            if (std::fread(header, sizeof(header), 1, file) != 1 || header[0] != 0x50504145
                || header[1] != 2 || header[2] > AppearanceProfileCount)
            {
                std::fclose(file);
                return result;
            }
            for (std::uint32_t i = 0; i < header[2]; ++i)
            {
                Profile profile{};
                if (std::fread(&profile, sizeof(profile), 1, file) != 1)
                    break;
                bool valid = profile.race < RaceCount && profile.gender < 2
                    && profile.optionCount > 0 && profile.optionCount <= 16;
                for (std::uint32_t j = 0; valid && j < profile.optionCount; ++j)
                {
                    auto const& option = profile.options[j];
                    valid = (option.offset == 0x24 || option.offset == 0x28 || option.offset == 0x2C
                        || option.offset == 0x30 || option.offset == 0x34)
                        && option.count && option.factor && option.count <= 256
                        && option.factor <= 256 / option.count
                        && (!option.geometryOffset || (option.count <= 32
                            && option.geometryOffset >= 0x144 && option.geometryOffset < 0x190
                            && option.geometryOffset % 4 == 0));
                }
                if (valid)
                    result.push_back(profile);
            }
            std::fclose(file);
            return result;
        }();
        return profiles;
    }

    template<class T>
    T& Field(void* object, std::size_t offset)
    {
        return *reinterpret_cast<T*>(static_cast<unsigned char*>(object) + offset);
    }

    struct Geometry
    {
        char model[128];
        std::vector<unsigned char> skin;
    };

    struct MaterialSelector
    {
        unsigned offset;
        unsigned factor;
        unsigned count;
        unsigned value;
    };

    struct AppearanceMaterial
    {
        unsigned race;
        unsigned gender;
        unsigned slot;
        MaterialSelector selectors[3];
        char path[128];
    };

    std::vector<AppearanceMaterial> const& AppearanceMaterials()
    {
        static std::vector<AppearanceMaterial> const materials = []
        {
            std::vector<AppearanceMaterial> result;
            FILE* file = CatalogFile(L"EsteriaAppearanceMaterials.bin");
            if (!file)
                return result;
            unsigned header[3] = {};
            if (std::fread(header, sizeof(header), 1, file) == 1 && header[0] == 0x544D4145
                && header[1] == 1 && header[2] <= 4096)
                for (unsigned i = 0; i < header[2]; ++i)
                {
                    AppearanceMaterial material{};
                    if (std::fread(&material, sizeof(material), 1, file) != 1)
                        break;
                    bool valid = material.race == 47 && material.gender < 2
                        && material.slot == 5 && material.path[0]
                        && std::memchr(material.path, 0, sizeof(material.path));
                    for (auto const& selector : material.selectors)
                        valid = valid && (selector.offset == 0x24 || selector.offset == 0x28
                            || selector.offset == 0x30) && selector.factor && selector.count
                            && selector.count <= 256 && selector.factor <= 256 / selector.count
                            && selector.value < selector.count;
                    if (valid)
                        result.push_back(material);
                }
            std::fclose(file);
            return result;
        }();
        return materials;
    }

    bool ValidGeometry(std::vector<unsigned char>& skin)
    {
        if (skin.size() < 48 || Field<unsigned>(skin.data(), 0) != 0x4E494B53)
            return false;
        unsigned const strides[] = {2, 2, 4, 48, 24};
        for (unsigned i = 0; i < 5; ++i)
        {
            unsigned count = Field<unsigned>(skin.data(), 4 + i * 8);
            unsigned offset = Field<unsigned>(skin.data(), 8 + i * 8);
            if (offset > skin.size() || count > (skin.size() - offset) / strides[i])
                return false;
        }
        unsigned vertices = Field<unsigned>(skin.data(), 4);
        unsigned indices = Field<unsigned>(skin.data(), 12);
        unsigned meshes = Field<unsigned>(skin.data(), 28);
        if (!vertices || vertices > 65535 || !indices || !meshes || meshes > 4096)
            return false;
        auto* sections = skin.data() + Field<unsigned>(skin.data(), 32);
        for (unsigned i = 0; i < meshes; ++i)
        {
            auto* section = sections + i * 48;
            unsigned start = Field<std::uint16_t>(section, 8)
                | (Field<std::uint16_t>(section, 2) << 16);
            if (start > indices || Field<std::uint16_t>(section, 10) > indices - start
                || unsigned(Field<std::uint16_t>(section, 4)) + Field<std::uint16_t>(section, 6) > vertices
                || Field<std::uint16_t>(section, 12) > 75)
                return false;
        }
        return true;
    }

    std::vector<Geometry>& Geometries()
    {
        static std::vector<Geometry> geometries = []
        {
            std::vector<Geometry> result;
            FILE* file = CatalogFile(L"EsteriaAppearanceGeometry.bin");
            if (!file)
                return result;
            unsigned header[3] = {};
            if (std::fread(header, sizeof(header), 1, file) == 1 && header[0] == 0x4D474145
                && header[1] == 1 && header[2] <= AppearanceProfileCount)
                for (unsigned i = 0; i < header[2]; ++i)
                {
                    Geometry geometry{};
                    unsigned length = 0;
                    if (std::fread(geometry.model, sizeof(geometry.model), 1, file) != 1
                        || !std::memchr(geometry.model, 0, sizeof(geometry.model))
                        || std::fread(&length, sizeof(length), 1, file) != 1 || length > 16 * 1024 * 1024)
                        break;
                    geometry.skin.resize(length);
                    if (std::fread(geometry.skin.data(), length, 1, file) != 1 || !ValidGeometry(geometry.skin))
                        break;
                    result.push_back(std::move(geometry));
                }
            std::fclose(file);
            return result;
        }();
        return geometries;
    }

    std::uintptr_t Address(std::uintptr_t preferred)
    {
        return reinterpret_cast<std::uintptr_t>(GetModuleHandleW(nullptr)) + preferred - 0x00400000;
    }

    template<class T>
    T Native(std::uintptr_t preferred)
    {
        return reinterpret_cast<T>(Address(preferred));
    }

    void Refresh(void* character)
    {
        // These are the setters the stock component initializer itself calls.
        Native<void(__thiscall*)(void*, unsigned, int, int)>(0x004EA2F0)(
            character, Field<unsigned>(character, 0x24), 0, 0);
        Native<void(__thiscall*)(void*, unsigned, int, int, int)>(0x004EA6B0)(
            character, Field<unsigned>(character, 0x28), 0, 1, 0);
        Native<void(__thiscall*)(void*, unsigned, int, int)>(0x004EA490)(
            character, Field<unsigned>(character, 0x2C), 0, 0);
        Native<void(__thiscall*)(void*, unsigned, int)>(0x004EA3E0)(
            character, Field<unsigned>(character, 0x34), 0);
        Native<void(__thiscall*)(void*, unsigned, int, int)>(0x004EA590)(
            character, Field<unsigned>(character, 0x30), 0, 0);
        *reinterpret_cast<unsigned*>(Address(0x00B6B18C)) = Field<unsigned>(character, 0x28);
        Native<void(__cdecl*)(void*, int)>(0x004E6AE0)(character, 1);
    }
}

#include "CosmeticWings.inl"
#include "RunningWild.inl"

extern "C" __declspec(dllexport) void __cdecl EsteriaSkin(void* model)
{
    if (!model)
        return;
    void* skin = Field<void*>(model, 0x170);
    if (!skin)
        return;
    for (auto& geometry : Geometries())
    {
        if (_stricmp(static_cast<char*>(model) + 0x3C, geometry.model))
            continue;
        // Restore the prepared Wrath arrays if another asset reader parked wide-index meshes.
        // The engine still owns and frees its original profile block. Catalog arrays live until exit.
        for (unsigned i = 0; i < 5; ++i)
        {
            Field<unsigned>(skin, 4 + i * 8) = Field<unsigned>(geometry.skin.data(), 4 + i * 8);
            Field<void*>(skin, 8 + i * 8) = geometry.skin.data()
                + Field<unsigned>(geometry.skin.data(), 8 + i * 8);
        }
        Field<unsigned>(skin, 44) = 75;
        return;
    }
}

extern "C" __declspec(dllexport) void __cdecl EsteriaGeometry(void* character)
{
    if (!character)
        return;
    UpdateCosmeticWing(character);
    if (HighmountainGeometry(character))
        return;
    for (auto const& profile : Profiles())
    {
        if (profile.race != Field<unsigned>(character, 0x18)
            || profile.gender != Field<unsigned>(character, 0x1C))
            continue;
        for (unsigned i = 0; i < profile.optionCount; ++i)
        {
            auto const& option = profile.options[i];
            if (option.geometryOffset)
            {
                unsigned choice = (Field<unsigned>(character, option.offset) / option.factor) % option.count;
                Field<unsigned>(character, option.geometryOffset) = option.geometryChoices[choice];
            }
        }
        if (profile.race == 47 && profile.optionCount == 12)
        {
            auto choice = [&](unsigned index)
            {
                auto const& option = profile.options[index];
                return (Field<unsigned>(character, option.offset) / option.factor) % option.count;
            };
            unsigned modification = choice(7);
            unsigned visor = modification / 4;
            Field<unsigned>(character, 0x148) = choice(4) ? 101 + choice(4) : 100;
            Field<unsigned>(character, 0x150) = 301 + choice(5);
            Field<unsigned>(character, 0x158) = 501 + choice(6);
            Field<unsigned>(character, 0x16C) = 1001 + choice(6);
            Field<unsigned>(character, 0x160) = 702 + modification % 4;
            Field<unsigned>(character, 0x184) = visor ? 1601 + (visor == 4 ? 2 : visor) : 1600;
            Field<unsigned>(character, 0x18C) = visor == 2 ? 1803 : 1800;
            unsigned eye = choice(8);
            unsigned primal = profile.options[8].count - 4;
            Field<unsigned>(character, 0x188) = eye >= primal ? 1702 + eye - primal : eye == 14 ? 1701 : 1700;
            void* instance = Field<void*>(character, 0x38);
            if (instance)
            {
                unsigned boundSlots = 0;
                for (auto const& material : AppearanceMaterials())
                {
                    if (material.gender != profile.gender || (boundSlots & (1u << material.slot)))
                        continue;
                    bool selected = true;
                    for (auto const& selector : material.selectors)
                        selected = selected && (Field<unsigned>(character, selector.offset)
                            / selector.factor) % selector.count == selector.value;
                    if (!selected)
                        continue;
                    // Same load/set/release sequence used by the native extra-head setter.
                    void* texture = Native<void*(__cdecl*)(char const*, void*)>(0x004E8D30)(
                        material.path, reinterpret_cast<void*>(Address(0x00AC46D0)));
                    if (texture)
                    {
                        Native<void(__thiscall*)(void*, unsigned, void*)>(0x00825260)(
                            instance, material.slot, texture);
                        Native<void(__cdecl*)(void*)>(0x0047BF30)(texture);
                    }
                    boundSlots |= 1u << material.slot;
                }
            }
        }
        if (profile.optionCount > 7 && profile.options[2].geometryOffset == 0x184)
        {
            auto const& enabled = profile.options[6];
            auto const& color = profile.options[7];
            unsigned feather = Field<unsigned>(character, 0x184);
            unsigned toggle = (Field<unsigned>(character, enabled.offset) / enabled.factor) % enabled.count;
            unsigned palette = (Field<unsigned>(character, color.offset) / color.factor) % color.count;
            Field<unsigned>(character, 0x184) = feather && toggle ? feather + palette * 100 : 1600;
            void* instance = Field<void*>(character, 0x38);
            if (instance)
                Native<void(__thiscall*)(void*, unsigned, unsigned, int)>(0x0082C7C0)(instance, 4000, 4799, 0);
        }
        break;
    }
}

extern "C" __declspec(dllexport) bool __cdecl EsteriaDropdownWheelBlocked()
{
    return dropdownWheelBlocked;
}

namespace
{
    void ScaleVrykulPreview(void* character)
    {
        if (!character || (Field<unsigned>(character, 0x18) != 56 && Field<unsigned>(character, 0x18) != 57))
            return;
        void* instance = Field<void*>(character, 0x38);
        void* model = instance ? Field<void*>(instance, 0x2C) : nullptr;
        if (!model || _strnicmp(static_cast<char*>(model) + 0x3C, "custom\\vrykul\\", 14))
            return;
        auto const* matrix = reinterpret_cast<float const*>(static_cast<unsigned char*>(instance) + 0xB4);
        float current = std::hypot(matrix[0], matrix[1]);
        float position[] = {matrix[12], matrix[13], matrix[14]};
        if (!std::isfinite(current) || current < .001f
            || !std::all_of(std::begin(position), std::end(position), [](float v) { return std::isfinite(v); })
            || std::abs(current - .55f) < .0001f)
            return;
        // Verified 12340 UI placement ABI: position, yaw, uniform scale. Preserve facing and pedestal position.
        Native<void(__thiscall*)(void*, float const*, float, float)>(0x008251D0)(
            instance, position, std::atan2(matrix[1], matrix[0]), .55f);
    }
}

extern "C" __declspec(dllexport) int __cdecl EsteriaCycle(void* state)
{
    auto const isNumber = Native<int(__cdecl*)(void*, int)>(0x0084DF20);
    if (isNumber(state, 1))
        return Native<int(__cdecl*)(void*)>(0x004E0B50)(state);
    auto const getTop = Native<int(__cdecl*)(void*)>(0x0084DBD0);
    auto const number = Native<double(__cdecl*)(void*, int)>(0x0084E030);
    auto const string = Native<char const*(__cdecl*)(void*, int, std::size_t*)>(0x0084E0E0);
    auto const pushNumber = Native<void(__cdecl*)(void*, double)>(0x0084E2A0);
    char const* command = string(state, 1, nullptr);
    if (!command || getTop(state) < 2 || !isNumber(state, 2))
        return 0;
    if (std::strcmp(command, "EA_WHEEL_BLOCK") == 0)
    {
        double active = number(state, 2);
        if (active == 0 || active == 1)
            dropdownWheelBlocked = active == 1;
        return 0;
    }
    if (std::strcmp(command, "EA_SELECT") == 0)
    {
        double index = number(state, 2);
        unsigned count = *reinterpret_cast<unsigned*>(Address(0x00B6B23C));
        auto* rows = *reinterpret_cast<unsigned char**>(Address(0x00B6B240));
        if (!rows || count > 100 || !std::isfinite(index) || index < 1 || index > count
            || index != std::floor(index))
            return 0;
        auto* row = rows + (static_cast<unsigned>(index) - 1) * 0x198;
        pushNumber(state, row[0x178]);
        pushNumber(state, row[0x17A]);
        return 2;
    }
    if (std::strcmp(command, "EA_PREVIEW_SCALE") == 0)
    {
        double index = number(state, 2);
        if (!std::isfinite(index) || index < 0 || index > 100 || index != std::floor(index))
            return 0;
        if (index == 0)
            ScaleVrykulPreview(*reinterpret_cast<void**>(Address(0x00B6B1A0)));
        else
        {
            unsigned count = *reinterpret_cast<unsigned*>(Address(0x00B6B23C));
            auto* rows = *reinterpret_cast<unsigned char**>(Address(0x00B6B240));
            if (rows && count <= 100 && index <= count)
                ScaleVrykulPreview(Field<void*>(rows + (static_cast<unsigned>(index) - 1) * 0x198, 0x188));
        }
        return 0;
    }
    void* character = *reinterpret_cast<void**>(Address(0x00B6B1A0));
    if (!character)
        return 0;
    if (std::strcmp(command, "EA_PREVIEW_SAVE") == 0 || std::strcmp(command, "EA_PREVIEW_RESTORE") == 0
        || std::strcmp(command, "EA_PREVIEW_END") == 0)
    {
        pushNumber(state, PreviewAppearance(character, command) ? 1 : 0);
        return 1;
    }
    if (std::strcmp(command, "EA_SET") == 0 && (getTop(state) != 3 || !isNumber(state, 3)))
        return 0;
    if (std::strcmp(command, "EA_STOCK_GET") == 0 || std::strcmp(command, "EA_STOCK_CHOICES") == 0)
    {
        double requested = number(state, 2);
        unsigned race = Field<unsigned>(character, 0x18);
        unsigned gender = Field<unsigned>(character, 0x1C);
        if (!std::isfinite(requested) || requested < 1 || requested > 5
            || requested != std::floor(requested) || race >= RaceCount || gender > 1)
            return 0;
        unsigned index = static_cast<unsigned>(requested) - 1;
        constexpr unsigned offsets[] = {0x28, 0x2C, 0x34, 0x24, 0x30};
        constexpr unsigned categories[] = {0, 1, 3, 3, 2};
        void* table = *reinterpret_cast<void**>(Address(0x00B6B864));
        if (!table)
            return 0;
        auto variations = Native<unsigned(__cdecl*)(void*, unsigned, unsigned, unsigned)>(0x004F3AE0);
        auto colors = Native<unsigned(__cdecl*)(void*, unsigned, unsigned, unsigned, unsigned)>(0x004F3B10);
        auto section = Native<unsigned const*(__cdecl*)(void*, unsigned, unsigned, unsigned,
            unsigned, unsigned, bool*)>(0x004F3BA0);
        unsigned flags = Native<unsigned(__cdecl*)(unsigned, unsigned)>(0x004F3A40)(
            0, Field<unsigned>(character, 0x20));
        auto allowed = [&](unsigned category, unsigned variation, unsigned color)
        {
            auto row = section(table, race, gender, category, variation, color, nullptr);
            return row && Native<bool(__cdecl*)(unsigned, unsigned)>(0x004F39A0)(row[7], flags);
        };
        unsigned category = categories[index];
        unsigned style = Field<unsigned>(character, 0x34);
        bool texturedFeature = false;
        if (index == 4)
            section(table, race, gender, 2, Field<unsigned>(character, 0x30),
                Field<unsigned>(character, 0x24), &texturedFeature);
        auto featureCounts = *reinterpret_cast<unsigned**>(Address(0x00B6B860));
        unsigned count = index == 0 ? colors(table, race, gender, 0, 0)
            : index == 3 ? colors(table, race, gender, 3, style)
            : index == 4 && !texturedFeature ? (featureCounts ? featureCounts[race * 2 + gender] : 0)
            : variations(table, race, gender, category);
        if (count > 256)
            return 0;
        if (std::strcmp(command, "EA_STOCK_GET") == 0)
        {
            pushNumber(state, Field<unsigned>(character, offsets[index]));
            pushNumber(state, count);
            return 2;
        }
        std::string choices;
        for (unsigned value = 0; value < count; ++value)
        {
            bool valid = index == 4 && !texturedFeature;
            if (index == 0)
                valid = allowed(0, 0, value) && allowed(1, Field<unsigned>(character, 0x2C), value);
            else if (index == 3)
                valid = allowed(3, style, value);
            else if (!valid)
                for (unsigned color = 0, total = (std::min)(colors(table, race, gender, category, value), 256u);
                    color < total && !valid; ++color)
                    valid = allowed(category, value, color);
            if (valid)
                choices += std::to_string(value) + ",";
        }
        Native<void(__cdecl*)(void*, char const*)>(0x0084E350)(state, choices.c_str());
        return 1;
    }
    if (HighmountainCycle(state, command))
        return std::strcmp(command, "EA_GET") == 0 ? 3 : std::strcmp(command, "EA_CHOICES") == 0 ? 1 : 0;
    Profile const* profile = nullptr;
    for (auto const& candidate : Profiles())
        if (candidate.race == Field<unsigned>(character, 0x18)
            && candidate.gender == Field<unsigned>(character, 0x1C))
        {
            profile = &candidate;
            break;
        }
    double requested = number(state, 2);
    if (!profile || !std::isfinite(requested) || requested < 1 || requested > profile->optionCount
        || requested != std::floor(requested))
        return 0;
    auto const& option = profile->options[static_cast<unsigned>(requested) - 1];
    unsigned& encoded = Field<unsigned>(character, option.offset);
    unsigned const value = (encoded / option.factor) % option.count;
    if (std::strcmp(command, "EA_GET") == 0)
    {
        pushNumber(state, value);
        pushNumber(state, option.count);
        return 2;
    }
    if (std::strcmp(command, "EA_CHOICES") == 0)
    {
        std::string choices;
        for (unsigned i = 0; i < option.count; ++i)
            choices += std::to_string(i) + ",";
        Native<void(__cdecl*)(void*, char const*)>(0x0084E350)(state, choices.c_str());
        return 1;
    }
    bool direct = std::strcmp(command, "EA_SET") == 0;
    if ((!direct && std::strcmp(command, "EA_CYCLE") != 0) || getTop(state) != 3 || !isNumber(state, 3))
        return 0;
    double delta = number(state, 3);
    if (direct ? (!std::isfinite(delta) || delta < 0 || delta >= option.count || delta != std::floor(delta))
        : (delta != 1 && delta != -1))
        return 0;
    unsigned const next = direct ? static_cast<unsigned>(delta)
        : (value + option.count + static_cast<int>(delta)) % option.count;
    unsigned const replacement = encoded - value * option.factor + next * option.factor;
    if (replacement > 255)
        return 0;
    encoded = replacement;
    Refresh(character);
    return 0;
}

extern "C" __declspec(dllexport) unsigned __cdecl EsteriaSkillRace(unsigned race)
{
    // Match the server's legacy eligibility masks without changing character identity.
    switch (race)
    {
        case 45: return 2;
        case 46: return 6;
        case 47: return 7;
        case 48: return 3;
        case 49: return 2;
        case 50: return 4;
        case 51: return 8;
        case 52: return 13;
        case 53: return 10;
        case 54: return 10;
        case 55: return 3;
        case 56:
        case 58: return 1;
        case 57:
        case 59: return 2;
        case 60: return 2;
        case 61: return 1;
        case 62: return 1;
        case 63: return 2;
        case 64: return 2;
        case 65: return 1;
        case 66: return 1;
        case 67: return 2;
        case 68: return 2;
        case 69: return 1;
        case 70: return 2;
        default: return race;
    }
}

extern "C" __declspec(dllexport) std::uint32_t __cdecl EsteriaWideSource(void const* section, void const* skin)
{
    if (!section)
        return 0;
    auto const* data = static_cast<unsigned char const*>(section);
    std::uint32_t const low = *reinterpret_cast<std::uint16_t const*>(data + 8);
    std::uint32_t const high = *reinterpret_cast<std::uint16_t const*>(data + 2);
    std::uint32_t const count = *reinterpret_cast<std::uint16_t const*>(data + 10);
    std::uint32_t const wide = (high << 16) | low;
    if (skin)
    {
        std::uint32_t const total = *reinterpret_cast<std::uint32_t const*>(
            static_cast<unsigned char const*>(skin) + 0x0C);
        if (wide <= total && count <= total - wide)
            return wide;
    }
    return low;
}

extern "C" __declspec(dllexport) std::uint32_t __cdecl EsteriaDrawStart(void const* section, void* context)
{
    void* instance = context ? Field<void*>(context, 0x60) : nullptr;
    void* model = instance ? Field<void*>(instance, 0x2C) : nullptr;
    void* skin = model ? Field<void*>(model, 0x170) : nullptr;
    return EsteriaWideSource(section, skin);
}

namespace
{
    bool ExtendedRace(unsigned race)
    {
        return race == 20 || race == 46 || race == 48 || race == 49 || race == 50 || race == 51
            || CreatureAppearance::Uses(race);
    }

    bool ValidateExtended(unsigned race, unsigned gender, std::array<std::uint8_t, 13> const& fields)
    {
        if (CreatureAppearance::Uses(race))
        {
            std::array<std::uint8_t, 5> appearance{};
            std::copy_n(fields.begin(), appearance.size(), appearance.begin());
            return std::all_of(fields.begin() + 5, fields.end(), [](std::uint8_t value) { return value == 0; })
                && CreatureAppearance::Validate(race, gender, appearance);
        }
        if (race == 20)
        {
            std::array<std::uint8_t, 5> vulpera{};
            std::copy_n(fields.begin(), vulpera.size(), vulpera.begin());
            return std::all_of(fields.begin() + 5, fields.end(), [](std::uint8_t value) { return value == 0; })
                && VulperaAppearance::Validate(gender, vulpera);
        }
        if (race == 50 || race == 51)
            return HaranirAppearance::Validate(gender, fields);
        std::array<std::uint8_t, 6> legacy{};
        std::copy_n(fields.begin(), legacy.size(), legacy.begin());
        return std::all_of(fields.begin() + 6, fields.end(), [](std::uint8_t value) { return value == 0; })
            && (race == 46 ? HighmountainAppearance::Validate(gender, legacy)
                : EarthenAppearance::Validate(gender, legacy));
    }

    std::unordered_map<void*, std::array<std::uint8_t, 13>> earthenNetworkAppearance;

    void CaptureEarthenAppearance(void* character, unsigned char const* network, std::uint64_t extra)
    {
        unsigned race = Field<unsigned>(character, 0x18);
        if ((race != 20 && race != 48 && race != 49 && race != 50 && race != 51
            && !CreatureAppearance::Uses(race)) || !network)
            return;
        std::array<std::uint8_t, 13> values{};
        std::memcpy(values.data(), network, 5);
        for (unsigned i = 0; i < 8; ++i)
            values[5 + i] = race == 20 || CreatureAppearance::Uses(race) ? 0
                : static_cast<std::uint8_t>(extra >> (i * 8));
        if (!ValidateExtended(race, Field<unsigned>(character, 0x1C), values))
            return;
        earthenNetworkAppearance[character] = values;
    }

    std::uint64_t UnitAppearanceExtra(void* unit)
    {
        auto* fields = Field<unsigned char*>(unit, 0xD0);
        if (!fields)
            return 0;
        std::uint64_t extra = Field<unsigned>(fields, 0x8D * 4);
        void* character = Field<void*>(unit, 0xB4C);
        if (Field<unsigned>(unit, 0x14) == 4 && character
            && (Field<unsigned>(character, 0x18) == 50 || Field<unsigned>(character, 0x18) == 51))
        {
            auto* objectFields = Field<unsigned char*>(unit, 8);
            if (objectFields)
                extra |= std::uint64_t{Field<unsigned>(objectFields, 5 * 4)} << 32;
        }
        return extra;
    }

    void CaptureEarthenOwner(void* character)
    {
        auto* connection = *reinterpret_cast<unsigned char**>(Address(0x00C79CE0));
        if (!connection)
            return;
        auto* manager = Field<unsigned char*>(connection, 0x2ED0);
        if (!manager)
            return;
        auto* unit = Field<unsigned char*>(manager, 0xAC);
        // ponytail: bounded owner lookup during dirty component rebuilds; index by GUID if profiling warrants it.
        for (unsigned i = 0; unit && !(reinterpret_cast<std::uintptr_t>(unit) & 1) && i < 4096; ++i)
        {
            if (Field<unsigned>(unit, 0x14) == 4 && Field<void*>(unit, 0xB4C) == character)
            {
                auto* playerData = Field<unsigned char*>(unit, 0x1008);
                auto* fields = Field<unsigned char*>(unit, 0xD0);
                if (playerData && fields)
                    CaptureEarthenAppearance(character, playerData + 0x14, UnitAppearanceExtra(unit));
                return;
            }
            unit = Field<unsigned char*>(unit, 0x3C);
        }
    }

    std::unordered_map<void*, std::uint64_t> highmountainExtra;
    std::unordered_map<std::uint64_t, std::uint64_t> highmountainRoster;
    thread_local void* highmountainContext = nullptr;
    constexpr unsigned appearanceOffsets[] = {0x28, 0x2C, 0x34, 0x24, 0x30};

    std::array<std::uint8_t, 13> HighmountainFields(void* character)
    {
        std::array<std::uint8_t, 13> result{};
        for (unsigned i = 0; i < 5; ++i)
            result[i] = static_cast<std::uint8_t>(Field<unsigned>(character, appearanceOffsets[i]));
        auto it = highmountainExtra.find(character);
        std::uint64_t extra = it == highmountainExtra.end() ? 0 : it->second;
        for (unsigned i = 0; i < 8; ++i)
            result[5 + i] = Field<unsigned>(character, 0x18) == 20
                || CreatureAppearance::Uses(Field<unsigned>(character, 0x18)) ? 0
                : static_cast<std::uint8_t>(extra >> (i * 8));
        return result;
    }

    void SetHighmountainFields(void* character, std::array<std::uint8_t, 13> const& values)
    {
        for (unsigned i = 0; i < 5; ++i)
            Field<unsigned>(character, appearanceOffsets[i]) = values[i];
        highmountainExtra[character] = HaranirAppearance::Extra(values);
    }

    bool PreviewAppearance(void* character, char const* command)
    {
        // Character Create owns one model; keep its complete packed appearance for transient hovers.
        static void* owner = nullptr;
        static unsigned race = 0, gender = 0, characterClass = 0;
        static std::array<std::uint8_t, 13> saved{};
        if (std::strcmp(command, "EA_PREVIEW_END") == 0)
        {
            owner = nullptr;
            return true;
        }
        if (std::strcmp(command, "EA_PREVIEW_SAVE") == 0)
        {
            owner = character;
            race = Field<unsigned>(character, 0x18);
            gender = Field<unsigned>(character, 0x1C);
            characterClass = Field<unsigned>(character, 0x20);
            saved = HighmountainFields(character);
            return true;
        }
        if (owner != character || race != Field<unsigned>(character, 0x18)
            || gender != Field<unsigned>(character, 0x1C) || characterClass != Field<unsigned>(character, 0x20))
            return false;
        SetHighmountainFields(character, saved);
        Refresh(character);
        return true;
    }

    // Explicit descriptor/rule tables come from the pinned Retail choices; version-2 profiles stay intact.
    template<class Options, class Labels, class Requirements>
    bool HighmountainControl(void* state, char const* command, void* character, Options const& options,
        Labels const& labels, Requirements const& requirements)
    {
        auto const number = Native<double(__cdecl*)(void*, int)>(0x0084E030);
        auto const pushNumber = Native<void(__cdecl*)(void*, double)>(0x0084E2A0);
        auto const pushString = Native<void(__cdecl*)(void*, char const*)>(0x0084E350);
        double requested = number(state, 2);
        if (!std::isfinite(requested) || requested < 1 || requested > options.size()
            || requested != std::floor(requested))
        {
            if (std::strcmp(command, "EA_GET") == 0)
            {
                pushNumber(state, 0);
                pushNumber(state, 1);
                pushString(state, "");
            }
            else if (std::strcmp(command, "EA_CHOICES") == 0)
                pushString(state, "");
            return true;
        }
        unsigned index = static_cast<unsigned>(requested) - 1;
        auto fields = HighmountainFields(character);
        unsigned race = Field<unsigned>(character, 0x18);
        unsigned gender = Field<unsigned>(character, 0x1C);
        unsigned characterClass = Field<unsigned>(character, 0x20);
        auto normalize = [&](std::array<std::uint8_t, 13>& values)
        {
            if (race != 20)
                return;
            std::array<std::uint8_t, 5> vulpera{};
            std::copy_n(values.begin(), vulpera.size(), vulpera.begin());
            vulpera = VulperaAppearance::Normalize(gender, characterClass, vulpera);
            std::copy(vulpera.begin(), vulpera.end(), values.begin());
        };
        auto allowed = [&](std::array<std::uint8_t, 13> const& values)
        {
            if (!ValidateExtended(race, gender, values))
                return false;
            if (race != 20)
                return true;
            std::array<std::uint8_t, 5> vulpera{};
            std::copy_n(values.begin(), vulpera.size(), vulpera.begin());
            return VulperaAppearance::ValidateClass(gender, characterClass, vulpera);
        };
        auto original = fields;
        normalize(fields);
        if (fields != original)
        {
            SetHighmountainFields(character, fields);
            Refresh(character);
        }
        if (std::strcmp(command, "EA_RANDOM") == 0)
        {
            static std::mt19937 random(GetTickCount());
            fields = {};
            normalize(fields);
            for (unsigned i = 0; i < options.size(); ++i)
            {
                auto const& descriptor = options[i];
                unsigned first = std::uniform_int_distribution<unsigned>(0, descriptor.count - 1)(random);
                for (unsigned attempt = 0; attempt < descriptor.count; ++attempt)
                {
                    auto candidate = fields;
                    unsigned value = (first + attempt) % descriptor.count;
                    unsigned prior = candidate[descriptor.field] / descriptor.factor % descriptor.count;
                    candidate[descriptor.field] = static_cast<std::uint8_t>(
                        candidate[descriptor.field] - prior * descriptor.factor + value * descriptor.factor);
                    if (allowed(candidate))
                    {
                        fields = candidate;
                        break;
                    }
                }
            }
            SetHighmountainFields(character, fields);
            Refresh(character);
            return true;
        }
        auto const& option = options[index];
        unsigned value = (fields[option.field] / option.factor) % option.count;
        if (std::strcmp(command, "EA_GET") == 0)
        {
            pushNumber(state, value);
            unsigned count = option.count;
            if (race == 20 && index == 9)
            {
                auto candidate = fields;
                candidate[option.field] = static_cast<std::uint8_t>(candidate[option.field] - value * option.factor
                    + option.factor);
                if (!allowed(candidate))
                    count = 1;
            }
            pushNumber(state, count);
            pushString(state, labels[index]);
            return true;
        }
        bool choices = std::strcmp(command, "EA_CHOICES") == 0;
        bool direct = std::strcmp(command, "EA_SET") == 0;
        if (!choices && !direct && std::strcmp(command, "EA_CYCLE") != 0)
            return true;
        double direction = choices ? 1 : number(state, 3);
        if (direct ? (!std::isfinite(direction) || direction < 0 || direction >= option.count
            || direction != std::floor(direction)) : (direction != 1 && direction != -1))
            return true;
        std::string available;
        for (unsigned step = 1; step <= (direct ? 1u : option.count); ++step)
        {
            unsigned next = choices ? step - 1 : direct ? static_cast<unsigned>(direction)
                : static_cast<unsigned>((static_cast<int>(value) + static_cast<int>(option.count) * 2
                    + static_cast<int>(step) * static_cast<int>(direction)) % static_cast<int>(option.count));
            auto candidate = fields;
            candidate[option.field] = static_cast<std::uint8_t>(
                candidate[option.field] - value * option.factor + next * option.factor);
            // Changing a prerequisite resets incompatible dependent accessories to their authored default.
            for (unsigned pass = 0; pass < options.size(); ++pass)
                for (auto const& rule : requirements)
                {
                    auto const& selected = options[rule.option];
                    auto const& required = options[rule.required];
                    unsigned dependent = (candidate[selected.field] / selected.factor) % selected.count;
                    unsigned prerequisite = (candidate[required.field] / required.factor) % required.count;
                    if (rule.option != index && dependent == rule.value
                        && !(rule.mask & (std::uint64_t{1} << prerequisite)))
                        candidate[selected.field] -= static_cast<std::uint8_t>(dependent * selected.factor);
                }
            if (!allowed(candidate))
                continue;
            if (choices)
            {
                available += std::to_string(next) + ",";
                continue;
            }
            SetHighmountainFields(character, candidate);
            Refresh(character);
            break;
        }
        if (choices)
            pushString(state, available.c_str());
        return true;
    }

    bool HighmountainCycle(void* state, char const* command)
    {
        void* character = *reinterpret_cast<void**>(Address(0x00B6B1A0));
        if (!character || !ExtendedRace(Field<unsigned>(character, 0x18)))
            return false;
        if (Field<unsigned>(character, 0x18) == 54)
        {
            constexpr std::array<char const*, 5> maleLabels =
                {"Skin Color", "Face", "Crest Style", "Eye Color", "Facial Features"};
            constexpr std::array<char const*, 5> femaleLabels =
                {"Skin Color", "Face", "Hair Style", "Hair Color", "Facial Features"};
            constexpr std::array<VulperaAppearance::Requirement, 0> requirements{};
            unsigned gender = Field<unsigned>(character, 0x1C);
            return HighmountainControl(state, command, character, CreatureAppearance::Options(54, gender),
                gender ? femaleLabels : maleLabels, requirements);
        }
        if (Field<unsigned>(character, 0x18) == 62)
        {
            constexpr std::array<char const*, 5> labels =
                {"Skin Color", "Face", "Armor Style", "Armor Color", "Facial Features"};
            constexpr std::array<VulperaAppearance::Requirement, 0> requirements{};
            return HighmountainControl(state, command, character,
                CreatureAppearance::Options(62, Field<unsigned>(character, 0x1C)), labels, requirements);
        }
        if (Field<unsigned>(character, 0x18) == 63)
        {
            constexpr std::array<VulperaAppearance::Requirement, 0> requirements{};
            return HighmountainControl(state, command, character, CreatureAppearance::GnollControls,
                CreatureAppearance::GnollLabels, requirements);
        }
        if (Field<unsigned>(character, 0x18) == 69 || Field<unsigned>(character, 0x18) == 70)
        {
            constexpr std::array<VulperaAppearance::Requirement, 0> requirements{};
            return HighmountainControl(state, command, character, CreatureAppearance::DrakonidControls,
                CreatureAppearance::DrakonidLabels, requirements);
        }
        if (Field<unsigned>(character, 0x18) == 64)
        {
            constexpr std::array<char const*, 5> labels =
                {"Fur Color", "Outfit Style", "Armor Color", "Cloth Color", "Facial Features"};
            constexpr std::array<VulperaAppearance::Requirement, 0> requirements{};
            return HighmountainControl(state, command, character, CreatureAppearance::Options(64, 0),
                labels, requirements);
        }
        if (CreatureAppearance::Uses(Field<unsigned>(character, 0x18)))
            return false;
        if (Field<unsigned>(character, 0x18) == 20)
        {
            if (Field<unsigned>(character, 0x1C) == 0)
                return HighmountainControl(state, command, character, VulperaAppearance::MaleOptions,
                    VulperaAppearance::MaleLabels, VulperaAppearance::MaleRequirements);
            return HighmountainControl(state, command, character, VulperaAppearance::FemaleOptions,
                VulperaAppearance::FemaleLabels, VulperaAppearance::FemaleRequirements);
        }
        if (Field<unsigned>(character, 0x18) == 50 || Field<unsigned>(character, 0x18) == 51)
        {
            if (Field<unsigned>(character, 0x1C) == 0)
                return HighmountainControl(state, command, character, HaranirAppearance::MaleOptions,
                    HaranirAppearance::MaleLabels, HaranirAppearance::MaleRequirements);
            return HighmountainControl(state, command, character, HaranirAppearance::FemaleOptions,
                HaranirAppearance::FemaleLabels, HaranirAppearance::FemaleRequirements);
        }
        if (Field<unsigned>(character, 0x18) != 46)
        {
            if (Field<unsigned>(character, 0x1C) == 0)
                return HighmountainControl(state, command, character, EarthenAppearance::MaleOptions,
                    EarthenAppearance::MaleLabels, EarthenAppearance::MaleRequirements);
            return HighmountainControl(state, command, character, EarthenAppearance::FemaleOptions,
                EarthenAppearance::FemaleLabels, EarthenAppearance::FemaleRequirements);
        }
        if (Field<unsigned>(character, 0x1C) == 0)
            return HighmountainControl(state, command, character, HighmountainAppearance::MaleOptions,
                HighmountainAppearance::MaleLabels, HighmountainAppearance::MaleRequirements);
        return HighmountainControl(state, command, character, HighmountainAppearance::FemaleOptions,
            HighmountainAppearance::FemaleLabels, HighmountainAppearance::FemaleRequirements);
    }

    struct HighmountainSelection
    {
        unsigned gender;
        unsigned kind; // 0: geometry group, 1: replaceable material
        unsigned target;
        unsigned value;
        unsigned choices[3]; // {option, value} packed as two uint16s; 0xffffffff means unconditional
        char path[128];
    };

    std::vector<HighmountainSelection> ReadSelections(wchar_t const* name)
    {
        return [name]
        {
            std::vector<HighmountainSelection> result;
            FILE* file = CatalogFile(name);
            if (!file)
                return result;
            unsigned header[3] = {};
            if (std::fread(header, sizeof(header), 1, file) == 1 && header[0] == 0x314D4845
                && header[1] == 1 && header[2] <= 16384)
                for (unsigned i = 0; i < header[2]; ++i)
                {
                    HighmountainSelection record{};
                    if (std::fread(&record, sizeof(record), 1, file) != 1)
                        break;
                    bool valid = record.gender < 2 && record.kind <= 5
                        && (record.kind == 5 ? record.target < 16 && record.value && record.path[0]
                            && std::memchr(record.path, 0, sizeof(record.path))
                            : record.kind == 4 ? record.target && record.value < 52
                            : record.kind == 3 ? record.target < 9 && record.value >= 16
                            && std::memchr(record.path, 0, sizeof(record.path))
                            : record.kind == 2 ? record.target < 5200 && record.value >= 10000
                            && record.value < 30000 : record.kind ? record.target < 16 && record.path[0]
                            && std::memchr(record.path, 0, sizeof(record.path)) : record.target < 52
                            && record.value >= record.target * 100 && record.value < record.target * 100 + 100);
                    for (unsigned selector : record.choices)
                        valid = valid && (selector == 0xffffffff || (selector & 0xffff) < 32
                            && (selector >> 16) < 256);
                    if (valid)
                        result.push_back(record);
                }
            std::fclose(file);
            return result;
        }();
    }

    std::vector<HighmountainSelection> const& HighmountainSelections()
    {
        static auto const records = ReadSelections(L"EsteriaHighmountain.bin");
        return records;
    }

    std::vector<HighmountainSelection> const& EarthenSelections()
    {
        static auto const records = ReadSelections(L"EsteriaEarthen.bin");
        return records;
    }

    std::vector<HighmountainSelection> const& HaranirSelections()
    {
        static auto const records = ReadSelections(L"EsteriaHaranir.bin");
        return records;
    }

    std::vector<HighmountainSelection> const& VulperaSelections()
    {
        static auto const records = ReadSelections(L"EsteriaVulpera.bin");
        return records;
    }

    std::vector<HighmountainSelection> const& RetailSelections(unsigned race)
    {
        static auto const naga = ReadSelections(L"EsteriaNaga.bin");
        static auto const tuskarr = ReadSelections(L"EsteriaTuskarr.bin");
        static auto const vrykul = ReadSelections(L"EsteriaVrykul.bin");
        static auto const human = ReadSelections(L"EsteriaThinHuman.bin");
        static auto const sethrak = ReadSelections(L"EsteriaSethrak.bin");
        static auto const gnoll = ReadSelections(L"EsteriaGnoll.bin");
        static auto const saberon = ReadSelections(L"EsteriaSaberon.bin");
        static auto const tarasek = ReadSelections(L"EsteriaTarasek.bin");
        static auto const drakonid = ReadSelections(L"EsteriaDrakonid.bin");
        static auto const darkfallen = ReadSelections(L"EsteriaDarkfallen.bin");
        switch (race)
        {
            case 54: return naga;
            case 55: return tuskarr;
            case 56:
            case 57: return vrykul;
            case 58:
            case 59: return human;
            case 62: return sethrak;
            case 63: return gnoll;
            case 64: return saberon;
            case 66: return tarasek;
            case 43:
            case 44: return darkfallen;
            case 69:
            case 70: return drakonid;
            case 20: return VulperaSelections();
            default: return HaranirSelections();
        }
    }

    wchar_t const* RetailTextureBank(unsigned race)
    {
        switch (race)
        {
            case 54: return L"EsteriaNagaTextures.bin";
            case 55: return L"EsteriaTuskarrTextures.bin";
            case 56:
            case 57: return L"EsteriaVrykulTextures.bin";
            case 58:
            case 59: return L"EsteriaThinHumanTextures.bin";
            case 62: return L"EsteriaSethrakTextures.bin";
            case 63: return L"EsteriaGnollTextures.bin";
            case 64: return L"EsteriaSaberonTextures.bin";
            case 66: return L"EsteriaTarasekTextures.bin";
            case 43:
            case 44: return L"EsteriaDarkfallenTextures.bin";
            case 69:
            case 70: return L"EsteriaDrakonidTextures.bin";
            case 20: return L"EsteriaVulperaTextures.bin";
            default: return L"EsteriaHaranirTextures.bin";
        }
    }

    char const* RetailCacheFamily(unsigned race)
    {
        switch (race)
        {
            case 54: return "Naga";
            case 55: return "Tuskarr";
            case 56:
            case 57: return "Vrykul";
            case 58:
            case 59: return "ThinHuman";
            case 62: return "Sethrak";
            case 63: return "Gnoll";
            case 64: return "Saberon";
            case 66: return "Tarasek";
            case 43:
            case 44: return "Darkfallen";
            case 69:
            case 70: return "Drakonid";
            case 20: return "Vulpera";
            default: return "Haranir";
        }
    }

    unsigned SaberonTextureCoverage(void* character)
    {
        static auto const masks = []
        {
            std::unordered_map<unsigned, unsigned> result;
            FILE* file = CatalogFile(L"EsteriaSaberonCoverage.bin");
            if (!file)
                return result;
            unsigned header[3]{};
            if (std::fread(header, sizeof(header), 1, file) == 1 && header[0] == 0x56434253
                && header[1] == 1 && header[2] <= 65536)
                for (unsigned i = 0; i < header[2]; ++i)
                {
                    unsigned row[2]{};
                    if (std::fread(row, sizeof(row), 1, file) != 1 || !row[0] || !row[1] || row[1] >= 128)
                    {
                        result.clear();
                        break;
                    }
                    result.emplace(row[0], row[1]);
                }
            std::fclose(file);
            return result;
        }();
        unsigned result = 0;
        for (unsigned slot = 2; slot <= 9; ++slot)
        {
            if (slot == 4)
                continue; // Belts have a separate raised waist surface.
            auto found = masks.find(Field<unsigned>(character, 0x428 + slot * 4));
            if (found != masks.end())
                result |= found->second;
        }
        return result;
    }

    // Bounded diagnostic trace for the Drakonid pipeline (EsteriaDrakonid.log beside Wow.exe).
    void DrakonidTrace(char const* format, ...)
    {
        static unsigned lines = 0;
        if (lines >= 1500)
            return;
        char executable[MAX_PATH]{};
        if (!GetModuleFileNameA(nullptr, executable, MAX_PATH))
            return;
        char* slash = std::strrchr(executable, '\\');
        if (!slash)
            return;
        std::strcpy(slash + 1, "EsteriaDrakonid.log");
        FILE* file = nullptr;
        if (fopen_s(&file, executable, "a") || !file)
            return;
        va_list arguments;
        va_start(arguments, format);
        std::vfprintf(file, format, arguments);
        va_end(arguments);
        std::fputc('\n', file);
        std::fclose(file);
        ++lines;
    }

    // Body regions painted by the equipped items' texture components (bit n = Wrath region n, 0..7).
    unsigned DrakonidTextureCoverage(void* character)
    {
        static auto const masks = []
        {
            std::unordered_map<unsigned, unsigned> result;
            FILE* file = CatalogFile(L"EsteriaDrakonidCoverage.bin");
            if (!file)
                return result;
            unsigned header[3]{};
            if (std::fread(header, sizeof(header), 1, file) == 1 && header[0] == 0x56434253
                && header[1] == 1 && header[2] <= 65536)
                for (unsigned i = 0; i < header[2]; ++i)
                {
                    unsigned row[2]{};
                    if (std::fread(row, sizeof(row), 1, file) != 1 || !row[0] || !row[1] || row[1] >= 256)
                    {
                        result.clear();
                        break;
                    }
                    result.emplace(row[0], row[1]);
                }
            std::fclose(file);
            return result;
        }();
        unsigned result = 0;
        for (unsigned slot = 2; slot <= 9; ++slot)
        {
            auto found = masks.find(Field<unsigned>(character, 0x428 + slot * 4));
            if (found != masks.end())
                result |= found->second;
        }
        return result;
    }

#include "HaranirMaterials.inl"

    template<class Options>
    bool ExtendedGeometry(void* character, Options const& options,
        std::vector<HighmountainSelection> const& records)
    {
        unsigned gender = Field<unsigned>(character, 0x1C);
        auto const network = earthenNetworkAppearance.find(character);
        if (network != earthenNetworkAppearance.end())
            SetHighmountainFields(character, network->second);
        auto fields = HighmountainFields(character);
        if (!ValidateExtended(Field<unsigned>(character, 0x18), gender, fields))
        {
            fields = {};
            SetHighmountainFields(character, fields);
        }
        void* instance = Field<void*>(character, 0x38);
        if (!instance)
            return true;
        bool nativeClothingCovered = false;
        if (Field<unsigned>(character, 0x18) == 62 || Field<unsigned>(character, 0x18) == 64)
            for (unsigned slot = 2; slot <= 9; ++slot)
                nativeClothingCovered = nativeClothingCovered || Field<unsigned>(character, 0x428 + slot * 4) != 0;
        if (Field<unsigned>(character, 0x18) == 69 || Field<unsigned>(character, 0x18) == 70)
            DrakonidTrace("refresh character=%p race=%u gender=%u records=%u slots=[%u %u %u %u %u %u %u %u %u %u] "
                          "robe=%u coverage=%x", character, Field<unsigned>(character, 0x18), gender,
                          static_cast<unsigned>(records.size()),
                          Field<unsigned>(character, 0x428), Field<unsigned>(character, 0x42C),
                          Field<unsigned>(character, 0x430), Field<unsigned>(character, 0x434),
                          Field<unsigned>(character, 0x438), Field<unsigned>(character, 0x43C),
                          Field<unsigned>(character, 0x440), Field<unsigned>(character, 0x444),
                          Field<unsigned>(character, 0x448), Field<unsigned>(character, 0x44C),
                          Field<unsigned>(character, 0x178), DrakonidTextureCoverage(character));
        unsigned materials = 0;
        std::uint64_t helmetGroups = 0;
        if (Field<unsigned>(character, 0x18) == 20 || Field<unsigned>(character, 0x18) == 54
            || (Field<unsigned>(character, 0x18) == 66 && gender == 0)
            || Field<unsigned>(character, 0x18) == 69 || Field<unsigned>(character, 0x18) == 70)
            for (auto const& record : records)
                if (record.kind == 4 && record.gender == gender && record.value < 52
                    && record.target == Field<unsigned>(character, 0x428))
                    helmetGroups |= std::uint64_t{1} << record.value;
        std::uint64_t geometryGroups = 0;
        unsigned selectedGeosets[52] = {};
        Native<void(__thiscall*)(void*, unsigned, unsigned, int)>(0x0082C7C0)(instance, 10000, 29999, 0);
        for (auto const& record : records)
        {
            bool equipmentTexture = record.kind == 5 && Field<unsigned>(character, 0x18) == 64
                && ((record.target == 9 && record.value == Field<unsigned>(character, 0x438))
                    || (record.target == 10 && record.value == Field<unsigned>(character, 0x43C)));
            if (record.gender != gender || (record.kind >= 3 && !equipmentTexture))
                continue;
            bool selected = true;
            for (unsigned selector : record.choices)
            {
                if (selector == 0xffffffff)
                    continue;
                unsigned index = selector & 0xffff;
                if (index >= options.size())
                {
                    selected = false;
                    break;
                }
                auto const& option = options[index];
                selected = selected && (fields[option.field] / option.factor) % option.count == selector >> 16;
            }
            if (!selected)
                continue;
            if (record.kind == 2)
            {
                if (nativeClothingCovered && record.value >= 21000 && record.value < 22000)
                    continue;
                if (Field<unsigned>(character, 0x18) == 64 && record.value >= 20001 && record.value <= 20009)
                {
                    unsigned coverage = SaberonTextureCoverage(character);
                    unsigned beltDisplay = Field<unsigned>(character, 0x438);
                    bool belt = std::any_of(records.begin(), records.end(), [beltDisplay](auto const& item)
                    {
                        return item.kind == 5 && item.target == 9 && item.value == beltDisplay;
                    });
                    unsigned pantsDisplay = Field<unsigned>(character, 0x43C);
                    bool separatePants = belt && std::any_of(records.begin(), records.end(),
                        [pantsDisplay](auto const& item)
                    {
                        return item.kind == 5 && item.target == 10 && item.value == pantsDisplay;
                    });
                    unsigned region = record.value == 20009 ? 5 : record.value - 20001;
                    bool covered = record.value == 20008 ? belt : (coverage & (1u << region)) != 0;
                    if (record.value == 20006 && separatePants)
                        covered = false;
                    if (record.value == 20009 && !separatePants)
                        covered = false;
                    if (!covered)
                        continue;
                }
                if ((Field<unsigned>(character, 0x18) == 69 || Field<unsigned>(character, 0x18) == 70)
                    && record.value >= 20001 && record.value <= 20028 && (record.value - 20001) % 10 < 8
                    && !(DrakonidTextureCoverage(character) & (1u << ((record.value - 20001) % 10))))
                    continue; // 2000x body shells, 2001x / 2002x dorsal shells of tail 0 / 1
                unsigned group = record.target / 100;
                unsigned source = group < 19 ? Field<unsigned>(character, 0x144 + group * 4)
                    : selectedGeosets[group];
                if (record.target == 0 || source == record.target)
                    Native<void(__thiscall*)(void*, unsigned, unsigned, int)>(0x0082C7C0)(
                        instance, record.value, record.value, 1);
                continue;
            }
            if (!record.kind)
            {
                if (geometryGroups & (std::uint64_t{1} << record.target))
                    continue;
                geometryGroups |= std::uint64_t{1} << record.target;
                unsigned selectedValue = record.value;
                if (helmetGroups & (std::uint64_t{1} << record.target))
                    selectedValue = record.target * 100;
                unsigned race = Field<unsigned>(character, 0x18);
                if (race == 63)
                {
                    // Native Gnoll outfits yield only to equipment covering the same body region.
                    auto equipped = [&](unsigned slot)
                    {
                        return Field<unsigned>(character, 0x428 + slot * 4) != 0;
                    };
                    unsigned group = record.target;
                    bool covered = (group == 35 && (equipped(2) || equipped(3) || equipped(9)))
                        || (group == 36 && (equipped(7) || equipped(8)))
                        || ((group == 37 || group == 42) && equipped(4))
                        || ((group == 38 || group == 43) && (equipped(5)
                            || Field<unsigned>(character, 0x178) == 1302))
                        || (group == 40 && (equipped(5) || equipped(6))) || (group == 41 && equipped(1));
                    if (covered)
                        // These defaults are authored body surfaces, not removable outfit decorations.
                        selectedValue = group == 37 ? 3701 : group == 38 ? 3801 : group * 100;
                }
                if (record.target == 20 && (race == 48 || race == 49 || race == 50 || race == 51
                    || race == 56 || race == 57))
                    // Native equipment slot7 (Feet) maps to component visual slot6 at 0x428 + 6*4.
                    selectedValue = Field<unsigned>(character, 0x440) ? 2002
                        : (race == 50 || race == 51 ? record.value : 2001);
                selectedGeosets[record.target] = selectedValue;
                if (record.target < 19)
                    Field<unsigned>(character, 0x144 + record.target * 4) = selectedValue;
                else
                {
                    Native<void(__thiscall*)(void*, unsigned, unsigned, int)>(0x0082C7C0)(
                        instance, record.target * 100, record.target * 100 + 99, 0);
                    Native<void(__thiscall*)(void*, unsigned, unsigned, int)>(0x0082C7C0)(
                        instance, selectedValue, selectedValue, 1);
                }
            }
            else if (!(materials & (1u << record.target)))
            {
                void* texture = Native<void*(__cdecl*)(char const*, void*)>(0x004E8D30)(
                    record.path, reinterpret_cast<void*>(Address(0x00AC46D0)));
                if (texture)
                {
                    Native<void(__thiscall*)(void*, unsigned, void*)>(0x00825260)(instance, record.target, texture);
                    Native<void(__cdecl*)(void*)>(0x0047BF30)(texture);
                }
                materials |= 1u << record.target;
            }
        }
        // Some source-hidden groups have no customization selector. Apply their hide after all selections.
        for (unsigned group = 0; group < 52; ++group)
            if (helmetGroups & (std::uint64_t{1} << group))
            {
                if (group < 19)
                    Field<unsigned>(character, 0x144 + group * 4) = group * 100;
                Native<void(__thiscall*)(void*, unsigned, unsigned, int)>(0x0082C7C0)(
                    instance, group * 100, group * 100 + 99, 0);
            }
        return true;
    }

    bool HighmountainGeometry(void* character)
    {
        unsigned race = Field<unsigned>(character, 0x18);
        if (!ExtendedRace(race))
            return false;
        // The authored female player model uses ordinary DBC materials and equipment geosets.
        if (CreatureAppearance::UsesStockMaterials(race, Field<unsigned>(character, 0x1C)))
            return false;
        if (race != 46 && Field<void*>(character, 0x38))
            CaptureEarthenOwner(character);
        if (CreatureAppearance::Uses(race))
        {
            SetHaranirMaterials(character);
            if (race == 63)
                return ExtendedGeometry(character, CreatureAppearance::GnollControls, RetailSelections(race));
            if (race == 69 || race == 70)
                return ExtendedGeometry(character, CreatureAppearance::DrakonidControls, RetailSelections(race));
            return ExtendedGeometry(character, CreatureAppearance::Options(race, Field<unsigned>(character, 0x1C)),
                RetailSelections(race));
        }
        if (race == 20)
        {
            SetHaranirMaterials(character);
            if (Field<unsigned>(character, 0x1C) == 0)
                return ExtendedGeometry(character, VulperaAppearance::MaleOptions, VulperaSelections());
            return ExtendedGeometry(character, VulperaAppearance::FemaleOptions, VulperaSelections());
        }
        if (race == 50 || race == 51)
        {
            SetHaranirMaterials(character);
            if (Field<unsigned>(character, 0x1C) == 0)
                return ExtendedGeometry(character, HaranirAppearance::MaleOptions, HaranirSelections());
            return ExtendedGeometry(character, HaranirAppearance::FemaleOptions, HaranirSelections());
        }
        if (race == 46)
        {
            if (Field<unsigned>(character, 0x1C) == 0)
                return ExtendedGeometry(character, HighmountainAppearance::MaleOptions, HighmountainSelections());
            return ExtendedGeometry(character, HighmountainAppearance::FemaleOptions, HighmountainSelections());
        }
        if (Field<unsigned>(character, 0x1C) == 0)
            return ExtendedGeometry(character, EarthenAppearance::MaleOptions, EarthenSelections());
        return ExtendedGeometry(character, EarthenAppearance::FemaleOptions, EarthenSelections());
    }
}

extern "C" __declspec(dllexport) void __cdecl EsteriaCreateExtra(void* packet)
{
    void* character = *reinterpret_cast<void**>(Address(0x00B6B1A0));
    if (!packet || !character || !ExtendedRace(Field<unsigned>(character, 0x18))
        || Field<unsigned>(character, 0x18) == 20 || CreatureAppearance::Uses(Field<unsigned>(character, 0x18)))
        return;
    unsigned size = Field<unsigned>(packet, 0x10);
    unsigned base = Field<unsigned>(packet, 8);
    if (!size || size < base || size - base > Field<unsigned>(packet, 0x0C))
        return;
    auto* bytes = Field<unsigned char*>(packet, 4);
    auto fields = HighmountainFields(character);
    unsigned race = Field<unsigned>(character, 0x18);
    bytes[size - base - 1] = race == 50 || race == 51 ? 0 : fields[5];
    if (race == 50 || race == 51)
    {
        auto const append = Native<void(__thiscall*)(void*, unsigned)>(0x0047AFE0);
        for (unsigned i = 5; i < fields.size(); ++i)
            append(packet, fields[i]);
        for (unsigned i = 0; i < 4; ++i)
            append(packet, (0x31435248 >> (i * 8)) & 255);
    }
}

extern "C" __declspec(dllexport) void __cdecl EsteriaEnumExtra(void* packet)
{
    highmountainRoster.clear();
    cosmeticWingRoster.clear();
    if (!packet)
        return;
    unsigned length = Field<unsigned>(packet, 0x10);
    unsigned base = Field<unsigned>(packet, 8);
    if (length < base || length - base < 8 || length - base > Field<unsigned>(packet, 0x0C))
        return;
    auto* bytes = Field<unsigned char*>(packet, 4);
    unsigned size = length - base;
    if (!bytes)
        return;
    for (unsigned tail = 0; tail < 3 && size >= 8; ++tail)
    {
        unsigned magic = Field<unsigned>(bytes, size - 4);
        unsigned stride = magic == 0x31455848 ? 9 : magic == 0x32455848 ? 16 : magic == 0x31475743 ? 12 : 0;
        if (!stride)
            break;
        unsigned count = Field<unsigned>(bytes, size - 8);
        if (count > 100 || count > (size - 8) / stride)
            break;
        unsigned start = size - 8 - count * stride;
        for (unsigned i = 0; i < count; ++i)
        {
            auto guid = Field<std::uint64_t>(bytes, start + i * stride);
            if (stride == 12)
                cosmeticWingRoster[guid] = Field<unsigned>(bytes, start + i * stride + 8);
            else
                highmountainRoster[guid] = stride == 9
                    ? bytes[start + i * stride + 8] : Field<std::uint64_t>(bytes, start + i * stride + 8);
        }
        size = start;
        Field<unsigned>(packet, 0x10) = base + size;
    }
}

extern "C" __declspec(dllexport) void __cdecl EsteriaSelectExtra(void* character)
{
    if (!character)
        return;
    unsigned count = *reinterpret_cast<unsigned*>(Address(0x00B6B23C));
    auto* rows = *reinterpret_cast<unsigned char**>(Address(0x00B6B240));
    if (!rows || count > 100)
        return;
    for (unsigned i = 0; i < count; ++i)
    {
        auto* row = rows + i * 0x198;
        if (Field<void*>(row, 0x188) != character)
            continue;
        auto wing = cosmeticWingRoster.find(Field<std::uint64_t>(row, 0));
        cosmeticWingSelections[character] = wing == cosmeticWingRoster.end() ? 0 : wing->second;
        UpdateCosmeticWing(character);
        unsigned race = row[0x178];
        if (!ExtendedRace(race))
            return;
        auto it = highmountainRoster.find(Field<std::uint64_t>(row, 0));
        highmountainExtra[character] = race == 20 || CreatureAppearance::Uses(race)
            || it == highmountainRoster.end() ? 0 : it->second;
        if (race == 20 || race == 48 || race == 49 || race == 50 || race == 51 || CreatureAppearance::Uses(race))
        {
            // The preview's first base-section validation precedes the stock setters that establish
            // resolver context. Seed the authenticated roster identity/bytes before that validation.
            Field<unsigned>(character, 0x18) = race;
            Field<unsigned>(character, 0x1C) = row[0x17A];
            CaptureEarthenAppearance(character, row + 0x17B, highmountainExtra[character]);
            auto const appearance = earthenNetworkAppearance.find(character);
            if (appearance != earthenNetworkAppearance.end())
                SetHighmountainFields(character, appearance->second);
            highmountainContext = character;
        }
        return;
    }
}

extern "C" __declspec(dllexport) void __cdecl EsteriaUnitExtra(void* unit)
{
    if (!unit || (Field<unsigned>(unit, 0x14) != 3 && Field<unsigned>(unit, 0x14) != 4))
        return;
    void* character = Field<void*>(unit, 0xB4C);
    void* fields = Field<void*>(unit, 0xD0); // Native UnitFields starts after the six ObjectFields.
    if (!character || !fields || !ExtendedRace(Field<unsigned>(character, 0x18)))
        return;
    unsigned race = Field<unsigned>(character, 0x18);
    highmountainExtra[character] = race == 20 || CreatureAppearance::Uses(race) ? 0 : race == 50 || race == 51
        ? UnitAppearanceExtra(unit) : Field<unsigned>(fields, 0x8D * 4) & 255;
    // Stock player initialization clamps packed choices against sparse ordinary DBC counts.
    // Preserve the authenticated player bytes before the native compositor and accessory selectors run.
    if (Field<unsigned>(unit, 0x14) == 4)
    {
        auto* playerData = Field<unsigned char*>(unit, 0x1008);
        if (playerData)
            CaptureEarthenAppearance(character, playerData + 0x14, highmountainExtra[character]);
    }
    HighmountainGeometry(character);
    RefreshTarasekSelfMount(unit, character);
}

extern "C" __declspec(dllexport) void __cdecl EsteriaRegisterExtra()
{
    // UNIT_FIELD_PADDING has no stock old-value cache slot. Registering it makes the client copy
    // to the lookup's out-of-range fallback, corrupting adjacent objects. Read it after unit updates.
}

extern "C" __declspec(dllexport) void __cdecl EsteriaForgetCharacter(void* character)
{
    tarasekMountState.erase(character);
    ForgetCosmeticWing(character);
    cosmeticWingSelections.erase(character);
    haranirImages.erase(character);
    earthenNetworkAppearance.erase(character);
    highmountainExtra.erase(character);
    if (highmountainContext == character)
        highmountainContext = nullptr;
}

extern "C" __declspec(dllexport) void __cdecl EsteriaAppearanceContext(void* character)
{
    highmountainContext = character;
}

extern "C" __declspec(dllexport) void __cdecl EsteriaSectionArguments(unsigned* arguments)
{
    if (!arguments || !ExtendedRace(arguments[1]) || arguments[2] > 1 || !highmountainContext
        || Field<unsigned>(highmountainContext, 0x18) != arguments[1]
        || Field<unsigned>(highmountainContext, 0x1C) != arguments[2])
        return;
    auto fields = HighmountainFields(highmountainContext);
    unsigned gender = arguments[2];
    if (CreatureAppearance::Uses(arguments[1]))
        return;
    if (arguments[1] == 20 || arguments[1] == 50 || arguments[1] == 51)
    {
        arguments[4] = 0;
        arguments[5] = 0;
        return;
    }
    if (arguments[1] != 46)
    {
        arguments[4] = arguments[3] == 1 ? fields[1] % 10 : 0;
        arguments[5] = arguments[3] == 3 ? fields[3] % 14 : arguments[3] == 2 ? 0 : fields[0] % 14;
        return;
    }
    // Resolve actual logical choices before the native compositor indexes CharSections.
    unsigned skin = fields[0] % 9;
    unsigned face = fields[1] % (gender ? 4 : 5);
    unsigned paint = gender ? (fields[1] / 4) % 4 : fields[3] / 64;
    unsigned paintColor = gender ? fields[2] / 81 : fields[5] % 3;
    if (arguments[3] == 0 || arguments[3] == 1 || arguments[3] == 4)
    {
        arguments[4] = arguments[3] == 1 ? face : 0;
        arguments[5] = skin + 9 * (paint + 4 * paintColor);
    }
    else
    {
        arguments[4] = 0;
        arguments[5] = 0;
    }
}

extern "C" __declspec(dllexport) bool __cdecl EsteriaDirectSection(
    void* character, unsigned operation, unsigned const* arguments)
{
    if (!character || !ExtendedRace(Field<unsigned>(character, 0x18)) || !arguments || operation > 2)
        return false;
    highmountainContext = character;
    unsigned kind = operation == 0 ? 0 : operation == 1 ? 3 : arguments[0];
    unsigned slot = operation == 0 ? 1 : operation == 1 ? 0 : arguments[1];
    if (kind > 4 || slot > 2)
        return true;
    unsigned style = operation == 2 ? arguments[2] : 0;
    unsigned color = operation == 2 ? arguments[3] : Field<unsigned>(character, 0x28);
    if (operation == 1 && CreatureAppearance::UsesStockMaterials(
        Field<unsigned>(character, 0x18), Field<unsigned>(character, 0x1C)))
    {
        style = Field<unsigned>(character, 0x34);
        color = Field<unsigned>(character, 0x24);
    }
    unsigned race = Field<unsigned>(character, 0x18);
    bool tarasekEyes = race == 66 && Field<unsigned>(character, 0x1C) == 0;
    if (operation == 1 && (race == 69 || race == 70 || tarasekEyes))
    {
        // Eye Color uses the stock hair-color setter; refresh the selected eye/body texture there too.
        void* instance = Field<void*>(character, 0x38);
        if (!instance)
            return true;
        auto fields = HighmountainFields(character);
        unsigned gender = Field<unsigned>(character, 0x1C);
        unsigned target = tarasekEyes ? 11 : 6;
        auto const& options = tarasekEyes ? CreatureAppearance::Options(race, gender)
                                         : CreatureAppearance::DrakonidControls;
        for (auto const& record : RetailSelections(race))
        {
            if (record.kind != 1 || record.target != target || record.gender != gender)
                continue;
            bool selected = true;
            for (unsigned selector : record.choices)
            {
                if (selector == 0xffffffff)
                    continue;
                unsigned index = selector & 0xffff;
                if (index >= options.size())
                {
                    selected = false;
                    break;
                }
                auto const& option = options[index];
                selected = selected && (fields[option.field] / option.factor) % option.count == selector >> 16;
            }
            if (!selected)
                continue;
            void* texture = Native<void*(__cdecl*)(char const*, void*)>(0x004E8D30)(
                record.path, reinterpret_cast<void*>(Address(0x00AC46D0)));
            if (texture)
            {
                Native<void(__thiscall*)(void*, unsigned, void*)>(0x00825260)(instance, target, texture);
                Native<void(__cdecl*)(void*)>(0x0047BF30)(texture);
            }
            break;
        }
        return true;
    }
    char const* path = HaranirLayerPath(character, kind, slot);
    if (!path)
    {
        auto* table = *reinterpret_cast<void**>(Address(0x00B6B864));
        auto* row = Native<unsigned*(__cdecl*)(void*, unsigned, unsigned, unsigned, unsigned, unsigned, void*)>(
            0x004F3BA0)(table, Field<unsigned>(character, 0x18), Field<unsigned>(character, 0x1C),
                kind, style, color, nullptr);
        if (!row)
            return true;
        path = reinterpret_cast<char const*>(row[4 + slot]);
    }
    if (!path)
        return true;
    if (operation < 2)
    {
        unsigned race = Field<unsigned>(character, 0x18);
        if (race == 20 || (CreatureAppearance::Uses(race)
            && !CreatureAppearance::UsesStockMaterials(race, Field<unsigned>(character, 0x1C))))
        {
            SetHaranirMaterials(character);
            return true;
        }
        void* instance = Field<void*>(character, 0x38);
        if (instance && path[0])
        {
            void* texture = Native<void*(__cdecl*)(char const*, void*)>(0x004E8D30)(
                path, reinterpret_cast<void*>(Address(0x00AC46D0)));
            if (texture)
            {
                Native<void(__thiscall*)(void*, unsigned, void*)>(0x00825260)(
                    instance, operation == 0 ? 8 : 6, texture);
                Native<void(__cdecl*)(void*)>(0x0047BF30)(texture);
            }
        }
        return true;
    }
    // The stock layer setter validates, then bypasses the resolver and reindexes encoded bytes.
    // Keep its cache/refcount/dirty-bit lifecycle, with the resolved row as the only material source.
    void*& layer = Field<void*>(character, 0x194 + (kind * 3 + slot) * 4);
    if (layer)
        Native<void(__cdecl*)(void*)>(0x004F31A0)(layer);
    layer = nullptr;
    bool nativeMaterials = race == 20 || race == 50 || race == 51 || (CreatureAppearance::Uses(race)
        && !CreatureAppearance::UsesStockMaterials(race, Field<unsigned>(character, 0x1C)));
    layer = path[0] ? (nativeMaterials ? HaranirLoadLayer(path)
        : Native<void*(__cdecl*)(char const*)>(0x004F3930)(path)) : nullptr;
    if (arguments[4] < 32)
        Field<unsigned>(character, 0x0C) |= 1u << arguments[4];
    void* pending = Field<void*>(character, 0x52C);
    if (pending)
    {
        Field<unsigned>(pending, 0) &= ~1u;
        Field<void*>(character, 0x52C) = nullptr;
    }
    Field<unsigned>(character, 8) &= ~8u;
    return true;
}

extern "C" __declspec(dllexport) unsigned __cdecl EsteriaSectionCount(unsigned const* arguments)
{
    // Race46 stores encoded bytes. Its material getters normalize every access into the sparse source table.
    if (!arguments || !ExtendedRace(arguments[1]) || arguments[2] > 1 || arguments[3] > 4)
        return 0xffffffff;
    if (CreatureAppearance::Uses(arguments[1]))
    {
        if (!CreatureAppearance::GenderAllowed(arguments[1], arguments[2]))
            return 0;
        auto const& options = CreatureAppearance::Options(arguments[1], arguments[2]);
        return arguments[3] == 2 || arguments[3] == 3 ? options[3].count : options[0].count;
    }
    if (arguments[1] == 20)
    {
        auto const& capacities = arguments[2] ? VulperaAppearance::FemaleCapacities
            : VulperaAppearance::MaleCapacities;
        return arguments[3] == 2 || arguments[3] == 3 ? capacities[3] : capacities[0];
    }
    if (arguments[1] == 50 || arguments[1] == 51)
    {
        auto const& capacities = arguments[2] ? HaranirAppearance::FemaleCapacities
            : HaranirAppearance::MaleCapacities;
        return arguments[3] == 2 || arguments[3] == 3 ? capacities[3] : capacities[0];
    }
    if (arguments[1] != 46)
    {
        auto const& capacities = arguments[2] ? EarthenAppearance::FemaleCapacities
            : EarthenAppearance::MaleCapacities;
        return arguments[3] == 2 || arguments[3] == 3 ? capacities[3] : capacities[0];
    }
    auto const& capacities = arguments[2] ? HighmountainAppearance::FemaleCapacities
        : HighmountainAppearance::MaleCapacities;
    return arguments[3] == 2 || arguments[3] == 3 ? capacities[3] : capacities[0];
}
````
<!-- END FULL SOURCE 3 -->

### Appendix 4 cosmetic_wings_character_select.py

Originally linked catalog preparation and installation source.

Source: `tools/cosmetic_wings_character_select.py`  
Absolute path: `R:\Users\Zach\Documents\GitHub\EsteriaWoW\tools\cosmetic_wings_character_select.py`  
Source lines: 1 through 198  
SHA256: `e4e79d1cec59a192e7f5f41abbce02e3795ccb58bb55711d8d01a1cd77436fe6`

<!-- BEGIN FULL SOURCE 4 -->
````python
"""Stage the native Character Select wing catalog from the installed Cosmetics visual graph."""

import argparse
import ctypes
import hashlib
import json
import math
import os
import shutil
import struct
import subprocess
from datetime import datetime
from pathlib import Path

from cars_mount_pack import DLL_DEFAULT, H, Storm, Wdbc
from wow_xref import Pe

CLIENT = Path(r"G:\3.3.5a - Dev")
STAGE = Path(r"C:\Users\Zach\.codex\tmp\wings-select")
CATALOG = "EsteriaCosmeticWings.bin"
TABLES = ("Spell", "SkillLineAbility", "SpellVisual", "SpellVisualEffectName", "SpellVisualKitModelAttach")
BAKED = {"SpellVisualEffectName", "SpellVisualKitModelAttach"}


def sha256(path):
    with Path(path).open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def open_readonly(storm, path):
    handle = H()
    if not storm.dll.SFileOpenArchive(str(path), 0, 0x100, ctypes.byref(handle)):
        raise OSError(f"Cannot read client archive: {path} ({ctypes.get_last_error()})")
    return handle


def catalog_records(tables):
    """Resolve only wing state-kit attachments, preserving the effective effect scale."""
    spells = sorted({r[2] for r in tables["SkillLineAbility"].values() if r[1] == 779})
    records = []
    for spell in spells:
        row = tables["Spell"][spell]
        visual = tables["SpellVisual"].get(row[131])
        attachments = [r for r in tables["SpellVisualKitModelAttach"].values()
                       if visual and r[1] == visual[4] and r[3] == 16]
        if not attachments:
            continue
        if len(attachments) != 1 or any(attachments[0][4:]):
            raise ValueError(f"Wing {spell} has an unsupported attachment transform")
        effect, strings = tables["SpellVisualEffectName"][attachments[0][2]]
        end = strings.find(b"\0", effect[2])
        if end < effect[2]:
            raise ValueError(f"Wing {spell} has an invalid effect path")
        model = strings[effect[2]:end].decode("ascii")
        scale = struct.unpack("<f", struct.pack("<I", effect[4]))[0]
        if not model or len(model) >= 260 or not math.isfinite(scale) or not 0 < scale <= 100:
            raise ValueError(f"Wing {spell} has an invalid path or scale")
        records.append(dict(spell=spell, visual=row[131], kit=visual[4], model=model, scale=scale))
    if not records:
        raise ValueError("No Cosmetics wing attachments found")
    return records


def prepare(client=CLIENT, stage=STAGE):
    import mechagnome_race_pack as db

    stage.mkdir(parents=True, exist_ok=True)
    storm = Storm(DLL_DEFAULT)
    tables = {name: {} for name in TABLES}
    sources = {}
    archives = (client / "Data/patch-Z.MPQ", client / "Data/enUS/patch-enUS-Z.MPQ")
    for path in archives:
        handle = open_readonly(storm, path)
        try:
            for name in TABLES:
                blob = storm.read(handle, f"DBFilesClient\\{name}.dbc")
                sources[f"{path.name}:{name}"] = hashlib.sha256(blob).hexdigest()
                dbc = Wdbc(blob)
                tables[name].update({r[0]: (r, dbc.strings) if name == "SpellVisualEffectName" else r
                                     for r in dbc.rows})
        finally:
            storm.dll.SFileCloseArchive(handle)
    path = client / "Data/PATCH-X.MPQ"
    handle = open_readonly(storm, path)
    try:
        manifest = storm.read(handle, "wxl-dbc.manifest").decode("utf-8")
        for entry in manifest.splitlines():
            entry = entry.strip()
            if not entry or entry.startswith("#"):
                continue
            name = entry.replace("\\", "/").rsplit("/", 1)[-1].split(".dbc1-", 1)[0]
            # The installed WXL merger does not merge these baked visual tables.
            if name not in tables or name in BAKED:
                continue
            blob = storm.read(handle, entry.replace("/", "\\"))
            sources[entry] = hashlib.sha256(blob).hexdigest()
            dbc = Wdbc(blob)
            tables[name].update({r[0]: r for r in dbc.rows})
        records = catalog_records(tables)
        for record in records:
            model = record["model"]
            if model.lower().endswith(".mdx"):
                model = model[:-4] + ".m2"
            storm.read(handle, model)  # Fail before staging a catalog with missing wing assets.
    finally:
        storm.dll.SFileCloseArchive(handle)
    group = {int(value) for value in db.sql("SELECT spell_id FROM spell_group WHERE id=9100;").split()}
    by_spell = {r["spell"]: r for r in records}
    if not group or not group <= by_spell.keys():
        raise ValueError(f"Exclusive wing group lacks client visuals: {sorted(group - by_spell.keys())}")
    for line in db.sql("SELECT ID,SpellVisualID_1 FROM spell_dbc WHERE ID IN ("
                       + ",".join(map(str, sorted(group))) + ");").splitlines():
        spell, visual = map(int, line.split())
        if by_spell[spell]["visual"] != visual:
            raise ValueError(f"Server/client wing visual mismatch: {spell}")
    pe = Pe(client / "Wow.exe")
    expected = {
        0x0081F8F0: "558bec8b450885c0", 0x00831630: "558bec81ec8c000000",
        0x008274F0: "568bf18b465c33c9", 0x00824ED0: "568bf18306ff8b06",
    }
    for address, fingerprint in expected.items():
        if pe.read_va(address, len(bytes.fromhex(fingerprint))) != bytes.fromhex(fingerprint):
            raise ValueError(f"Native attachment ABI changed at {address:x}")
    if b"ESTERIA_APPEARANCE_NATIVE_V1\0" not in pe.data:
        raise ValueError("Existing native roster/preview hooks are required")
    blob = struct.pack("<3I", 0x31475743, 1, len(records)) + b"".join(
        struct.pack("<IIf260s", r["spell"], 16, r["scale"], r["model"].encode("ascii")) for r in records)
    (stage / CATALOG).write_bytes(blob)
    # Existing native harnesses resolve appearance catalogs beside their executable.
    for catalog in client.glob("Esteria*.bin"):
        if catalog.name == CATALOG:
            continue
        shutil.copy2(catalog, stage / catalog.name)
        digest = sha256(catalog)
        if sha256(stage / catalog.name) != digest:
            raise ValueError(f"Native test catalog copy mismatch: {catalog.name}")
        sources["native-test:" + catalog.name] = digest
    report = dict(records=records, server_wings=len(group), sources=sources,
                  exe_sha256=sha256(client / "Wow.exe"),
                  helper_before_sha256=sha256(client / "EsteriaAppearance.dll"),
                  catalog_sha256=sha256(stage / CATALOG))
    (stage / "catalog-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Staged {len(records)} wing visuals; {len(group)} server wing spells verified: {stage / CATALOG}")


def install(client=CLIENT, stage=STAGE):
    processes = subprocess.check_output(["tasklist", "/FO", "CSV", "/NH"], text=True).lower()
    if "wow.exe" in processes or "eclipse.exe" in processes:
        raise RuntimeError("Close WoW/Eclipse before installing the native helper")
    report = json.loads((stage / "catalog-report.json").read_text(encoding="utf-8"))
    if sha256(client / "Wow.exe") != report["exe_sha256"]:
        raise ValueError("Client executable changed after staging")
    if sha256(client / "EsteriaAppearance.dll") != report["helper_before_sha256"]:
        raise ValueError("Client helper changed after staging")
    if sha256(stage / CATALOG) != report["catalog_sha256"]:
        raise ValueError("Catalog changed after staging")
    for test in ("TestNativeAppearance.exe", "TestHighmountainMaterials.exe", "TestCustomizationChoices.exe",
                 "TestCosmeticWings.exe"):
        subprocess.run([str(stage / test), str(stage / "EsteriaAppearance.dll")], check=True)
    backup = Path(r"C:\Users\Zach\.codex\backups") / (
        "cosmetic-wings-select-" + datetime.now().strftime("%Y%m%d-%H%M%S"))
    backup.mkdir(parents=True)
    report["backup"] = str(backup)
    report["before"] = {}
    for name in ("EsteriaAppearance.dll", CATALOG):
        live = client / name
        report["before"][name] = sha256(live) if live.exists() else None
        if live.exists():
            shutil.copy2(live, backup / name)
            if sha256(backup / name) != report["before"][name]:
                raise ValueError(f"Rollback copy mismatch: {name}")
    (backup / "install-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    try:
        for name in (CATALOG, "EsteriaAppearance.dll"):
            temporary = client / (name + ".wings-next")
            shutil.copy2(stage / name, temporary)
            if sha256(temporary) != sha256(stage / name):
                raise ValueError(f"Install copy mismatch: {name}")
            os.replace(temporary, client / name)
    except Exception:
        for name, previous in report["before"].items():
            if previous is not None:
                shutil.copy2(backup / name, client / name)
            elif (client / name).exists():
                (client / name).unlink()
        raise
    report["installed"] = {name: sha256(client / name) for name in ("EsteriaAppearance.dll", CATALOG)}
    (backup / "install-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Installed native helper and wing catalog; verified rollback: {backup}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "install"))
    parser.add_argument("--client", type=Path, default=CLIENT)
    parser.add_argument("--stage", type=Path, default=STAGE)
    args = parser.parse_args()
    globals()[args.action](args.client, args.stage)
````
<!-- END FULL SOURCE 4 -->

### Appendix 5 CosmeticWings.inl

Originally linked catalog reader and model lifecycle source.

Source: `client-customization/CosmeticWings.inl`  
Absolute path: `R:\Users\Zach\Documents\GitHub\EsteriaWoW\client-customization\CosmeticWings.inl`  
Source lines: 1 through 104  
SHA256: `5e7807b1d659d129588fbf41bc2ca55184bd2e3fcfb45406accda0ff87bb556f`

<!-- BEGIN FULL SOURCE 5 -->
````cpp
// Character Select only. The catalog is derived from installed Cosmetics state-kit attachments.
namespace
{
    struct CosmeticWing
    {
        unsigned spell;
        unsigned attachment;
        float scale;
        char model[260];
    };
    static_assert(sizeof(CosmeticWing) == 272);

    std::vector<CosmeticWing> const& CosmeticWings()
    {
        static std::vector<CosmeticWing> const wings = []
        {
            std::vector<CosmeticWing> result;
            FILE* file = CatalogFile(L"EsteriaCosmeticWings.bin");
            if (!file)
                return result;
            unsigned header[3]{};
            bool valid = std::fread(header, sizeof(header), 1, file) == 1
                && header[0] == 0x31475743 && header[1] == 1 && header[2] <= 4096;
            for (unsigned i = 0; valid && i < header[2]; ++i)
            {
                CosmeticWing wing{};
                valid = std::fread(&wing, sizeof(wing), 1, file) == 1 && wing.spell
                    && wing.attachment == 16 && std::isfinite(wing.scale) && wing.scale > 0
                    && wing.scale <= 100 && wing.model[0] && std::memchr(wing.model, 0, sizeof(wing.model));
                if (valid)
                    result.push_back(wing);
            }
            valid = valid && std::fgetc(file) == EOF;
            std::fclose(file);
            if (!valid)
                result.clear();
            return result;
        }();
        return wings;
    }

    std::unordered_map<std::uint64_t, unsigned> cosmeticWingRoster;
    std::unordered_map<void*, unsigned> cosmeticWingSelections;
    struct BoundCosmeticWing
    {
        void* instance;
        unsigned spell;
    };
    std::unordered_map<void*, BoundCosmeticWing> boundCosmeticWings;

    void ForgetCosmeticWing(void* character)
    {
        auto it = boundCosmeticWings.find(character);
        if (it == boundCosmeticWings.end())
            return;
        void* wing = it->second.instance;
        // Retain our own reference: a stock component refresh may already have detached the child.
        if (Field<void*>(wing, 0x48))
            Native<void(__thiscall*)(void*)>(0x008274F0)(wing);
        Native<void(__thiscall*)(void*)>(0x00824ED0)(wing);
        boundCosmeticWings.erase(it);
    }

    void UpdateCosmeticWing(void* character)
    {
        auto selected = cosmeticWingSelections.find(character);
        unsigned spell = selected == cosmeticWingSelections.end() ? 0 : selected->second;
        auto const& catalog = CosmeticWings();
        auto definition = std::find_if(catalog.begin(), catalog.end(),
            [spell](CosmeticWing const& wing) { return wing.spell == spell; });
        void* parent = Field<void*>(character, 0x38);
        auto bound = boundCosmeticWings.find(character);
        if (bound != boundCosmeticWings.end())
        {
            if (definition != catalog.end() && bound->second.spell == spell
                && parent && Field<void*>(bound->second.instance, 0x48) == parent)
                return;
            ForgetCosmeticWing(character);
        }
        if (definition == catalog.end() || !parent || !(Field<unsigned>(parent, 0x10) & 1)
            || !Native<int(__thiscall*)(void*, unsigned)>(0x008273D0)(parent, definition->attachment))
            return;
        void* scene = Field<void*>(parent, 0x28);
        if (!scene)
            return;
        void* child = Native<void*(__thiscall*)(void*, char const*, unsigned)>(0x0081F8F0)(
            scene, definition->model, 0);
        if (!child)
            return;
        Native<void(__thiscall*)(void*, int, int, int, int, float, int, int)>(0x00832AB0)(
            child, -1, 0, -1, 0, 1.0f, 1, 1);
        float origin[3]{};
        Native<void(__thiscall*)(void*, float const*, float, float)>(0x008251D0)(
            child, origin, 0, definition->scale);
        Native<void(__thiscall*)(void*, void*, unsigned, void*, int)>(0x00831630)(
            child, parent, definition->attachment, nullptr, 0);
        if (Field<void*>(child, 0x48) != parent)
        {
            Native<void(__thiscall*)(void*)>(0x00824ED0)(child);
            return;
        }
        boundCosmeticWings[character] = {child, spell};
    }
}
````
<!-- END FULL SOURCE 5 -->

### Appendix 6 TestCosmeticWings.cpp

Supporting native lifecycle tests.

Source: `client-customization/TestCosmeticWings.cpp`  
Absolute path: `R:\Users\Zach\Documents\GitHub\EsteriaWoW\client-customization\TestCosmeticWings.cpp`  
Source lines: 1 through 232  
SHA256: `459e02cda01e54efe0121b96867e2e17731c380bc2fe2b258e421c8e9b42b7ae`

<!-- BEGIN FULL SOURCE 6 -->
````cpp
#include <windows.h>
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <vector>
#include <array>
#include <string>
#include <initializer_list>

namespace
{
    template<class T>
    T& Field(void* p, unsigned offset)
    {
        return *reinterpret_cast<T*>(static_cast<unsigned char*>(p) + offset);
    }

    std::uintptr_t Address(std::uintptr_t preferred)
    {
        return reinterpret_cast<std::uintptr_t>(GetModuleHandleW(nullptr)) + preferred - 0x00400000;
    }

    void Hook(std::uintptr_t preferred, void* function)
    {
        auto* code = reinterpret_cast<unsigned char*>(Address(preferred));
        code[0] = 0xE9;
        *reinterpret_cast<int*>(code + 1) = static_cast<int>(
            reinterpret_cast<std::uintptr_t>(function) - reinterpret_cast<std::uintptr_t>(code) - 5);
    }

    std::vector<void*> children;
    unsigned created, released, detached;
    float scale;
    bool attachmentAvailable = true;
    std::string modelPath;

    void* __fastcall Create(void* scene, void*, char const* path, unsigned flags)
    {
        assert(scene && !flags);
        modelPath = path;
        auto* child = new unsigned char[0x200]{};
        Field<unsigned>(child, 0) = 1;
        children.push_back(child);
        ++created;
        return child;
    }

    int __fastcall HasAttachment(void*, void*, unsigned attachment)
    {
        assert(attachment == 16);
        return attachmentAvailable;
    }

    void __fastcall Attach(void* child, void*, void* parent, unsigned attachment, void* transform, int force)
    {
        assert(attachment == 16 && !transform && !force);
        Field<void*>(child, 0x48) = parent;
        ++Field<unsigned>(child, 0);
    }

    void __fastcall Detach(void* child, void*)
    {
        assert(Field<void*>(child, 0x48) && Field<unsigned>(child, 0) == 2);
        Field<void*>(child, 0x48) = nullptr;
        --Field<unsigned>(child, 0);
        ++detached;
    }

    void __fastcall Release(void* child, void*)
    {
        assert(!Field<void*>(child, 0x48) && Field<unsigned>(child, 0) == 1);
        Field<unsigned>(child, 0) = 0;
        ++released;
    }

    void __fastcall Sequence(void*, void*, int bone, int animation, int variation,
        int time, float speed, int blend, int enabled)
    {
        assert(bone == -1 && animation == 0 && variation == -1 && time == 0
            && speed == 1 && blend == 1 && enabled == 1);
    }

    void __fastcall Placement(void*, void*, float const* origin, float facing, float value)
    {
        assert(!origin[0] && !origin[1] && !origin[2] && !facing);
        scale = value;
    }
}

int main(int argc, char** argv)
{
    assert(argc == 2);
    for (unsigned address : {0x00810000u, 0x00820000u, 0x00830000u, 0x00B60000u})
        assert(VirtualAlloc(reinterpret_cast<void*>(Address(address)), 65536,
            MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE) == reinterpret_cast<void*>(Address(address)));
    Hook(0x0081F8F0, reinterpret_cast<void*>(Create));
    Hook(0x008273D0, reinterpret_cast<void*>(HasAttachment));
    Hook(0x00831630, reinterpret_cast<void*>(Attach));
    Hook(0x008274F0, reinterpret_cast<void*>(Detach));
    Hook(0x00824ED0, reinterpret_cast<void*>(Release));
    Hook(0x00832AB0, reinterpret_cast<void*>(Sequence));
    Hook(0x008251D0, reinterpret_cast<void*>(Placement));

    // Use actual staged catalog records; do not substitute a fixture over the deployment catalog.
    std::string catalog = argv[1];
    catalog = catalog.substr(0, catalog.find_last_of("\\/")) + "\\EsteriaCosmeticWings.bin";
    FILE* file = nullptr;
    assert(!fopen_s(&file, catalog.c_str(), "rb"));
    struct Record
    {
        unsigned spell, attachment;
        float scale;
        char path[260];
    };
    unsigned header[3]{};
    Record definition{};
    assert(std::fread(header, sizeof(header), 1, file) == 1 && header[0] == 0x31475743
        && header[1] == 1 && header[2] > 0);
    assert(std::fread(&definition, sizeof(definition), 1, file) == 1);
    std::fclose(file);

    HMODULE module = LoadLibraryA(argv[1]);
    assert(module);
    using Invoke = void(__cdecl*)(void*);
    auto enumExtra = reinterpret_cast<Invoke>(GetProcAddress(module, "EsteriaEnumExtra"));
    auto selectExtra = reinterpret_cast<Invoke>(GetProcAddress(module, "EsteriaSelectExtra"));
    auto geometry = reinterpret_cast<Invoke>(GetProcAddress(module, "EsteriaGeometry"));
    auto forget = reinterpret_cast<Invoke>(GetProcAddress(module, "EsteriaForgetCharacter"));
    assert(enumExtra && selectExtra && geometry && forget);

    std::array<unsigned char, 128> bytes{};
    unsigned packet[6]{};
    Field<void*>(packet, 4) = bytes.data();
    Field<unsigned>(packet, 8) = 37; // Reader bases need not be zero.
    Field<unsigned>(packet, 12) = static_cast<unsigned>(bytes.size());
    unsigned cursor = 1;
    auto append = [&](auto value)
    {
        std::memcpy(bytes.data() + cursor, &value, sizeof(value));
        cursor += sizeof(value);
    };
    append(std::uint64_t{11}); append(std::uint8_t{81}); append(1u); append(0x31455848u);
    append(std::uint64_t{22}); append(std::uint64_t{0x123456789ABC}); append(1u); append(0x32455848u);
    append(std::uint64_t{11}); append(definition.spell);
    append(std::uint64_t{22}); append(12345u); // A non-wing spell must never spawn a preview attachment.
    append(2u); append(0x31475743u);
    Field<unsigned>(packet, 16) = 37 + cursor;
    enumExtra(packet);
    assert(Field<unsigned>(packet, 16) == 38); // All three trailers stripped, stock roster untouched.

    unsigned char rows[3 * 0x198]{};
    unsigned char first[0x200]{}, second[0x200]{}, creator[0x200]{};
    unsigned char parent[0x200]{}, replacement[0x200]{};
    unsigned scene{};
    for (void* value : {static_cast<void*>(parent), static_cast<void*>(replacement)})
    {
        Field<unsigned>(value, 0x10) = 1;
        Field<void*>(value, 0x28) = &scene;
    }
    Field<unsigned>(first, 0x18) = Field<unsigned>(second, 0x18) = Field<unsigned>(creator, 0x18) = 1;
    Field<void*>(first, 0x38) = parent;
    Field<void*>(second, 0x38) = replacement;
    Field<void*>(creator, 0x38) = replacement;
    Field<std::uint64_t>(rows, 0) = 11;
    Field<void*>(rows, 0x188) = first;
    rows[0x178] = 1;
    Field<std::uint64_t>(rows, 0x198) = 22;
    Field<void*>(rows, 0x198 + 0x188) = second;
    rows[0x198 + 0x178] = 1;
    *reinterpret_cast<void**>(Address(0x00B6B240)) = rows;
    *reinterpret_cast<unsigned*>(Address(0x00B6B23C)) = 2;
    selectExtra(first);
    assert(created == 1 && modelPath == definition.path && scale == definition.scale);
    geometry(first); geometry(first); selectExtra(first);
    assert(created == 1 && !released); // Repeated renders must not stack copies.
    selectExtra(second); geometry(second); geometry(creator);
    assert(created == 1); // Other characters and the creator inherit no wings.

    Field<void*>(first, 0x38) = replacement;
    geometry(first);
    assert(created == 2 && detached == 1 && released == 1); // Parent replaced by stock preview refresh.
    auto* child = children.back();
    Detach(child, nullptr); // Stock teardown may remove the parent-owned reference before our hook.
    geometry(first);
    assert(created == 3 && released == 2);
    forget(first); forget(first);
    assert(detached == 3 && released == 3); // Cleanup and address reuse are safe.
    geometry(first);
    assert(created == 3);

    selectExtra(first);
    assert(created == 4);
    Field<unsigned>(packet, 16) = 38;
    enumExtra(packet); // Fresh no-wing roster clears an earlier equipped aura.
    selectExtra(first);
    assert(released == 4 && detached == 4);
    geometry(first);
    assert(created == 4);

    // Invalid counts, truncated tails and null buffers cannot create wing state.
    cursor = 1;
    append(std::uint64_t{11}); append(definition.spell); append(101u); append(0x31475743u);
    Field<unsigned>(packet, 16) = 37 + cursor;
    enumExtra(packet);
    assert(Field<unsigned>(packet, 16) == 37 + cursor);
    selectExtra(first);
    assert(created == 4);
    cursor = 1;
    append(std::uint64_t{11}); append(definition.spell); append(1u); append(0x31475743u);
    Field<unsigned>(packet, 16) = 37 + cursor;
    enumExtra(packet);
    attachmentAvailable = false;
    selectExtra(first);
    assert(created == 4);
    attachmentAvailable = true;
    Field<unsigned>(replacement, 0x10) = 0;
    geometry(first);
    assert(created == 4); // Delayed parent loading retries without creating a dangling wing.
    Field<unsigned>(replacement, 0x10) = 1;
    geometry(first);
    assert(created == 5);
    forget(first);
    assert(released == 5 && detached == 5);
    Field<void*>(packet, 4) = nullptr;
    enumExtra(packet);
    enumExtra(nullptr);
    for (auto* value : children)
        delete[] static_cast<unsigned char*>(value);
    FreeLibrary(module);
    std::puts("Cosmetic wings: PASS (mixed trailers, isolation, repeats, parent refresh, removal, cleanup)");
}
````
<!-- END FULL SOURCE 6 -->

### Appendix 7 test_cosmetic_wings_character_select.py

Supporting catalog preparation tests.

Source: `tools/test_cosmetic_wings_character_select.py`  
Absolute path: `R:\Users\Zach\Documents\GitHub\EsteriaWoW\tools\test_cosmetic_wings_character_select.py`  
Source lines: 1 through 45  
SHA256: `6ea95b162ef43380be644620654dc2652c8cef953b87bcdc49b81ebb7293f7f0`

<!-- BEGIN FULL SOURCE 7 -->
````python
"""Small resolver checks; the native harness exercises the actual packet parser and ownership."""

import copy
import struct
import unittest

from cosmetic_wings_character_select import catalog_records


class WingCatalogTests(unittest.TestCase):
    def test_state_attachment_resolution_and_rejection(self):
        spell = [0] * 234
        spell[0], spell[131] = 970340, 30240
        visual = [0] * 32
        visual[0], visual[4] = 30240, 21040
        tables = {
            "Spell": {970340: spell},
            "SkillLineAbility": {1: [1, 779, 970340], 2: [2, 777, 123]},
            "SpellVisual": {30240: visual},
            "SpellVisualKitModelAttach": {1: [1, 21040, 8300, 16, 0, 0, 0, 0, 0, 0]},
            "SpellVisualEffectName": {8300: ([8300, 0, 1, 0, 0x3F800000, 0, 0], b"\0wings.mdx\0")},
        }
        record, = catalog_records(tables)
        self.assertEqual((record["spell"], record["model"], record["scale"]), (970340, "wings.mdx", 1))
        for value in (float("nan"), float("inf"), 0.0, -1.0, 101.0):
            changed = copy.deepcopy(tables)
            changed["SpellVisualEffectName"][8300][0][4] = struct.unpack("<I", struct.pack("<f", value))[0]
            with self.assertRaises(ValueError):
                catalog_records(changed)
        changed = copy.deepcopy(tables)
        changed["SpellVisualKitModelAttach"][1][4] = 1
        with self.assertRaises(ValueError):
            catalog_records(changed)
        changed = copy.deepcopy(tables)
        changed["SpellVisualKitModelAttach"][1][3] = 57
        with self.assertRaises(ValueError):
            catalog_records(changed)
        changed = copy.deepcopy(tables)
        changed["SpellVisualKitModelAttach"][2] = changed["SpellVisualKitModelAttach"][1].copy()
        with self.assertRaises(ValueError):
            catalog_records(changed)


if __name__ == "__main__":
    unittest.main()
````
<!-- END FULL SOURCE 7 -->

### Appendix 8 cosmetic_wings_e2e_test.go

Supporting live protocol test.

Source: `e2e/suites/protocol/session/cosmetic_wings_e2e_test.go`  
Absolute path: `R:\Users\Zach\Documents\GitHub\EsteriaWoW\e2e\suites\protocol\session\cosmetic_wings_e2e_test.go`  
Source lines: 1 through 85  
SHA256: `d415d00c7f836e32cf6b15be4f1acc94d3c0e6a72a7c6fd00af03018532a1515`

<!-- BEGIN FULL SOURCE 8 -->
````go
//go:build e2e

package session_test

import (
	"encoding/binary"
	"testing"
	"time"

	"github.com/azerothcore/AzerothGhost/client"
	"github.com/azerothcore/AzerothGhost/e2e/e2eharness"
	"github.com/azerothcore/azerothcore-wotlk/e2e/internal/meta"
)

// Esteria Cosmetics: a real cast, wing replacement and aura cancellation must reach Character Select.
// Requires the custom wing spells; rendering itself is covered by the native harness and manual client gate.
func TestSession_CosmeticWingCharacterSelect(t *testing.T) {
	meta.Begin(t, meta.TestMeta{Tags: []string{"short", "protocol", "cosmetics"}, Runtime: "short", Category: "protocol/session"})
	bot := e2eharness.NewSolo(t, e2eharness.ScenarioOpts{Prefix: "WingSel", Level: 80})
	bot.TeleportPad(t, e2eharness.PackagePad(t))
	const firstWing, secondWing uint32 = 970340, 970388
	for _, spell := range []uint32{firstWing, secondWing} {
		if !bot.World.KnowsSpell(spell) {
			e2eharness.Preconditionf(t, "Esteria cosmetic wing %d was not granted to this character", spell)
		}
	}

	assertRoster := func(want uint32) {
		t.Helper()
		bot.Save(t)
		// The pinned harness closes its socket on logout. Reconnect through its normal lifecycle,
		// then request the same account-scoped roster to inspect the state saved by that logout.
		bot.Relog(t)
		packets := make(chan []byte, 1)
		cancel := bot.World.AddPacketHook(func(op uint16, payload []byte) {
			if op == client.SmsgCharEnum {
				select {
				case packets <- append([]byte(nil), payload...):
				default:
				}
			}
		})
		defer cancel()
		if err := bot.World.RequestCharList(); err != nil {
			e2eharness.HarnessFailf(t, "character list request: %v", err)
		}
		var payload []byte
		select {
		case payload = <-packets:
		case <-time.After(15 * time.Second):
			e2eharness.HarnessFailf(t, "character list response timed out")
		}
		var got uint32
		if len(payload) >= 8 && binary.LittleEndian.Uint32(payload[len(payload)-4:]) == 0x31475743 {
			count := int(binary.LittleEndian.Uint32(payload[len(payload)-8:]))
			if count > 100 || count > (len(payload)-8)/12 {
				e2eharness.Assertf(t, "invalid CWG1 wing count %d", count)
			}
			start := len(payload) - 8 - count*12
			for offset := start; offset < len(payload)-8; offset += 12 {
				if binary.LittleEndian.Uint64(payload[offset:]) == bot.GUID {
					got = binary.LittleEndian.Uint32(payload[offset+8:])
				}
			}
		}
		if got != want {
			e2eharness.Assertf(t, "guid=0x%X Character Select wing=%d want=%d", bot.GUID, got, want)
		}
	}

	assertRoster(0) // Knowing every wing does not equip one.
	bot.CastMust(t, firstWing, bot.GUID, 10*time.Second)
	e2eharness.WaitUnitAura(t, bot.World, bot.GUID, firstWing, 10*time.Second)
	assertRoster(firstWing)
	bot.CastMust(t, secondWing, bot.GUID, 10*time.Second)
	e2eharness.WaitUnitAura(t, bot.World, bot.GUID, secondWing, 10*time.Second)
	bot.AssertAuraConsumed(t, firstWing, 10*time.Second, 0)
	assertRoster(secondWing)
	if err := bot.World.CancelAura(secondWing); err != nil {
		e2eharness.HarnessFailf(t, "cancel wing aura: %v", err)
	}
	bot.AssertAuraConsumed(t, secondWing, 10*time.Second, 0)
	assertRoster(0)
	t.Logf("PASS guid=0x%X Character Select follows no wing -> %d -> %d -> no wing", bot.GUID, firstWing, secondWing)
}
````
<!-- END FULL SOURCE 8 -->

### Appendix 9 build-native.bat

Supporting native build and test commands.

Source: `client-customization/build-native.bat`  
Absolute path: `R:\Users\Zach\Documents\GitHub\EsteriaWoW\client-customization\build-native.bat`  
Source lines: 1 through 33  
SHA256: `21fff47bf277b00cba40a18c94a2885bf2c64c4e8ed0a1a3f067b86f0591005e`

<!-- BEGIN FULL SOURCE 9 -->
````bat
@echo off
setlocal
call "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvarsall.bat" x86
if not "%errorlevel%"=="0" exit /b %errorlevel%
if "%~1"=="" exit /b 2
if not exist "%~1" mkdir "%~1"
cl.exe /nologo /std:c++20 /O2 /EHsc /MT /LD "%~dp0NativeAppearance.cpp" /Fo"%~1\NativeAppearance.obj" /link /DEF:"%~dp0NativeAppearance.def" /OUT:"%~1\EsteriaAppearance.dll" /IMPLIB:"%~1\EsteriaAppearance.lib"
if not "%errorlevel%"=="0" exit /b %errorlevel%
cl.exe /nologo /std:c++20 /O2 /EHsc /MT "%~dp0TestNativeAppearance.cpp" /Fo"%~1\TestNativeAppearance.obj" /link /OUT:"%~1\TestNativeAppearance.exe"
if not "%errorlevel%"=="0" exit /b %errorlevel%
"%~1\TestNativeAppearance.exe" "%~1\EsteriaAppearance.dll"
if not "%errorlevel%"=="0" exit /b %errorlevel%
cl.exe /nologo /std:c++20 /O2 /EHsc /MT "%~dp0TestHighmountainMaterials.cpp" /Fo"%~1\TestHighmountainMaterials.obj" /link /DYNAMICBASE:NO /BASE:0x04000000 /OUT:"%~1\TestHighmountainMaterials.exe"
if not "%errorlevel%"=="0" exit /b %errorlevel%
"%~1\TestHighmountainMaterials.exe" "%~1\EsteriaAppearance.dll"
if not "%errorlevel%"=="0" exit /b %errorlevel%
cl.exe /nologo /std:c++20 /O2 /EHsc /MT "%~dp0TestCustomizationChoices.cpp" /Fo"%~1\TestCustomizationChoices.obj" /link /DYNAMICBASE:NO /BASE:0x04000000 /OUT:"%~1\TestCustomizationChoices.exe"
if not "%errorlevel%"=="0" exit /b %errorlevel%
"%~1\TestCustomizationChoices.exe" "%~1\EsteriaAppearance.dll"
if not "%errorlevel%"=="0" exit /b %errorlevel%
cl.exe /nologo /std:c++20 /O2 /EHsc /MT "%~dp0TestCosmeticWings.cpp" /Fo"%~1\TestCosmeticWings.obj" /link /DYNAMICBASE:NO /BASE:0x04000000 /OUT:"%~1\TestCosmeticWings.exe"
if not "%errorlevel%"=="0" exit /b %errorlevel%
if exist "%~1\EsteriaCosmeticWings.bin" "%~1\TestCosmeticWings.exe" "%~1\EsteriaAppearance.dll"
if not "%errorlevel%"=="0" exit /b %errorlevel%
cl.exe /nologo /std:c++20 /O2 /EHsc /MT "%~dp0TestRunningWild.cpp" /Fo"%~1\TestRunningWild.obj" /link /OUT:"%~1\TestRunningWild.exe"
if not "%errorlevel%"=="0" exit /b %errorlevel%
"%~1\TestRunningWild.exe" "%~1\EsteriaAppearance.dll"
if not "%errorlevel%"=="0" exit /b %errorlevel%
if "%~2"=="" exit /b 0
cl.exe /nologo /std:c++20 /O2 /EHsc /MT "%~dp0TestRunningWildThunks.cpp" /Fo"%~1\TestRunningWildThunks.obj" /link /DYNAMICBASE:NO /BASE:0x04000000 /OUT:"%~1\TestRunningWildThunks.exe"
if not "%errorlevel%"=="0" exit /b %errorlevel%
"%~1\TestRunningWildThunks.exe" "%~1\EsteriaAppearance.dll" "%~2"
exit /b %errorlevel%
````
<!-- END FULL SOURCE 9 -->

### Appendix 10 NativeAppearance.def

Supporting DLL export definitions.

Source: `client-customization/NativeAppearance.def`  
Absolute path: `R:\Users\Zach\Documents\GitHub\EsteriaWoW\client-customization\NativeAppearance.def`  
Source lines: 1 through 22  
SHA256: `5f8cbf53f06d944b29950dde1008ab0c9fc13fcf55328ad87503240f497de6a8`

<!-- BEGIN FULL SOURCE 10 -->
````text
LIBRARY EsteriaAppearance
EXPORTS
    EsteriaCycle
    EsteriaDropdownWheelBlocked
    EsteriaWideSource
    EsteriaDrawStart
    EsteriaGeometry
    EsteriaSkin
    EsteriaSkillRace
    EsteriaCreateExtra
    EsteriaEnumExtra
    EsteriaSelectExtra
    EsteriaUnitExtra
    EsteriaRegisterExtra
    EsteriaAppearanceContext
    EsteriaSectionArguments
    EsteriaDirectSection
    EsteriaSectionCount
    EsteriaForgetCharacter
    EsteriaSelfMounted
    EsteriaSelfAnimation
    EsteriaSelfMotion
````
<!-- END FULL SOURCE 10 -->

## Original deployment record

Historical record for chat `01a10ea6-84c3-75d2-9d2f-15f64bf1a8f3`, last updated October 6 2026 at 01:38:56 UTC. Original stored summary reproduced in full below; its results have not been rerun for this document. The current native detach call shown in Appendix 5 is authoritative for the exported code.

Source: `C:\Users\Zach\.codex\memories\rollout_summaries\2026-10-06T00-39-16-e73J-cosmetic_wings_character_select_deployment.md`

````text
thread_id: 01a10ea6-84c3-75d2-9d2f-15f64bf1a8f3
updated_at: 2026-10-06T01:38:56+00:00
rollout_path: C:\Users\Zach\.codex\sessions\2026\10\05\rollout-2026-10-05T19-39-16-01a10ea6-84c3-75d2-9d2f-15f64bf1a8f3.jsonl
cwd: \\?\R:\Users\Zach\Documents\GitHub\EsteriaWoW
git_branch: main

# Implemented saved cosmetic-wing rendering on Character Select and deployed it

Rollout context: In `R:\Users\Zach\Documents\GitHub\EsteriaWoW`, the user asked whether wings from the Cosmetics SkillLine could appear on Character Select when the character has a cosmetic wing aura active, then authorized implementation and deployment.

## Task 1: Investigate feasibility and implementation path

Outcome: success

Key steps:

- Confirmed the existing wing system uses persistent self-applied aura spells in Cosmetics skill line 779, with an exclusive spell group 9100.
- Confirmed normal `SMSG_CHAR_ENUM` data contains appearance/equipment but not active aura state.
- Traced the server path through `WorldSession::HandleCharEnum`, `Player::BuildEnumData`, and the character database aura tables.
- Traced existing native client hooks and Warcraft client model attachment functions. The implementation uses the existing native appearance DLL rather than modifying `Wow.exe` or adding a WXL extension.
- Designed a server-to-client `CWG1` roster trailer containing GUID/spell pairs, appended after existing HXE1/HXE2 appearance extensions.
- Implemented client-side catalog loading from `EsteriaCosmeticWings.bin`, attachment at model attachment point 16, parent-refresh handling, replacement/removal, and cleanup on character teardown.

Reusable implementation facts:

- The catalog resolved 205 client wing visuals; 201 server wing spells in group 9100 had matching client/server visual identities.
- Four ribbon-only Alas Wings records were intentionally excluded from the server exclusive wing group.
- Existing native model functions used by the client path include `CreateSceneModel` at `0x0081F8F0`, `AttachToScene` at `0x00831630`, `DetachSlot` at `0x00827560`, and `ReleaseRenderCtx` at `0x00824ED0`.
- The client keeps a reference to the attached wing child, detaches/releases it on replacement, parent refresh, or teardown, and does not alter normal equipment attachments.

## Task 2: Build, deploy, and verify

Outcome: success

Key steps:

- Prepared the catalog with `python tools/cosmetic_wings_character_select.py prepare`.
- Initial native test attempts failed because the staging directory lacked existing appearance catalogs and then because the staging path exceeded an existing 128-byte cache path limit. The catalogs were copied with hash verification and staging was shortened to `C:\Users\Zach\.codex\tmp\wings-select`; all four native checks then passed:
  - `Native appearance helpers: PASS`
  - `Highmountain materials/lifetime: PASS`
  - `Customization choices: PASS`
  - `Cosmetic wings: PASS (mixed trailers, isolation, repeats, parent refresh, removal, cleanup)`
- Built the worldserver image successfully and recreated only `ac-worldserver`; authserver and MySQL remained running.
- Installed the native helper and wing catalog with verified rollback backup at `C:\Users\Zach\.codex\backups\cosmetic-wings-select-20261005-200742`.
- `Wow.exe` remained unchanged. The deployed worldserver image was `sha256:c540f6dcaf34eb4b8b03375f832fcdbeeae1afa05cb69dcadd0b552fce674f98`; the prior image was saved under rollback tag `acore/ac-wotlk-worldserver:cosmetic-wings-rollback-7567af86d8bc`.
- Automatic database migrations remained disabled via `AC_UPDATES_ENABLE_DATABASES=0`; `characters.extraAppearance` remained `bigint unsigned`.
- The live protocol test passed after fixing a task-local copy of the pinned AzerothGhost SDK. The SDK encoded the NUL byte at the start of the Win/OS/platform FourCC fields, producing an empty client OS and Warden rejection; the task-local copy corrected the wire encoding to trailing NUL bytes without changing server security checks.
- Live test result: `no wing -> 970340 -> 970388 -> no wing after cancellation and logout`, including real casts, exclusive replacement, aura cancellation, logout/relog, and Character Select roster-state verification.
- Temporary test accounts and character were deleted through the worldserver console and verified absent. Worldserver remained running with zero restarts.

Failures and how to do differently:

- Do not infer live success from source/static checks alone. The first native build failed due to missing neighboring appearance catalogs; stage all catalogs consumed by existing harnesses.
- Keep staging paths short because the existing native appearance cache enforces a path-length limit.
- The first live protocol attempt failed before wing code because the pinned SDK sent malformed OS bytes. Check the server log for authentication rejection causes before changing server logic; correct protocol fixtures in a task-local copy and preserve server authentication/Warden behavior.
- The final rollout verified packet/state behavior but did not verify actual 3D placement in a freshly restarted graphical WoW client. A manual client check remains required for visual position, scale, custom races/genders, switching characters, and client exit/restart behavior.

References:

- `src/server/game/Handlers/CharacterHandler.cpp` — Character Select packet construction and `CWG1` trailer.
- `src/server/database/Database/Implementation/CharacterDatabase.cpp` — account-scoped character/aura query support.
- `src/server/database/Database/Implementation/CharacterDatabase.h` and `src/server/game/Server/WorldSession.h` — declarations and session state.
- `client-customization/NativeAppearance.cpp` — roster parsing, wing selection, model attachment, refresh, and cleanup.
- `client-customization/CosmeticWings.inl` — binary catalog parser and attachment lifecycle.
- `client-customization/TestCosmeticWings.cpp` — native isolation/replacement/cleanup harness.
- `tools/cosmetic_wings_character_select.py` — catalog preparation and verified installation.
- `.agents/plans/cosmetic-wings-character-select/run_protocol_check.py` — task-local protocol build/run wrapper.
- `e2e/suites/protocol/session/cosmetic_wings_e2e_test.go` — live no-wing/replacement/cancellation/logout test.
- Verification command: `python -m unittest discover -s tools -p test_cosmetic_wings_character_select.py` passed.

## Task 3: Cleanup and final state

Outcome: success

- Both generated temporary accounts were deleted through the native worldserver console.
- Database verification reported zero remaining temporary accounts and zero test character rows.
- `git diff --check` passed for the focused changed files.
- Final user-facing status correctly stated that deployment and automated/live protocol checks passed, while fresh-client 3D visual acceptance remains outstanding.
````
