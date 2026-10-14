"""Run: rtk python tools/test_saberon_race_pack.py (requires the staged Saberon pack)."""

from collections import Counter
import hashlib
from itertools import product
import struct

from lupa.lua51 import LuaRuntime, LuaError
from wotlkconv.m2 import parse_m2, parse_skin

import saberon_race_pack as s
import retroported_race_pack as p
import sethrak_race_pack as base
import sethrak_animation_pack as animation
from gnoll_race_pack import triangles


def check_glue():
    original = {name: (s.STAGE / 'baseline' / name).read_bytes() for name in base.GLUE}
    generated = s.glue(original)
    for name, data in generated.items():
        assert data == (s.STAGE / 'glue' / name).read_bytes(), name
    # Reproduce the reported lexical error and ensure the production gate rejects it.
    broken = generated['CharacterCreate.lua'].replace(b'63 or', b'63or')
    assert broken != generated['CharacterCreate.lua']
    try:
        s.validate_glue({'CharacterCreate.lua': broken})
    except LuaError as error:
        assert "malformed number near '63or'" in str(error)
    else:
        raise AssertionError('Lua 5.1 must reject the reported malformed token')
    s.validate_glue(generated)
    text = generated['CharacterCreate.lua'].decode()
    start = text.index('function CharacterCreate_IsMaleOnlyRace(')
    lua = LuaRuntime()
    lua.execute(text[start:text.index('\nend', start) + 4])
    male_only = lua.globals().CharacterCreate_IsMaleOnlyRace
    for race in range(1, 129):
        assert bool(male_only(race)) == (race in (55, 58, 59, 63, 64)), race
    print('PASS Lua 5.1 compiles every Glue chunk and rejects 63or; all race gender policies preserved')


def check():
    check_glue()
    root = s.STAGE
    source = parse_m2((s.ROOT / 'converted/saberon.m2').read_bytes())
    source_skin = parse_skin((s.ROOT / 'converted/saberon00.skin').read_bytes())
    model_data = s.local(root / 'assets', s.MODEL).read_bytes()
    model = parse_m2(model_data)
    skin = parse_skin(s.local(root / 'assets', s.MODEL[:-3] + '00.skin').read_bytes())
    equipped = any(t['type'] == 1 for t in model.textures)
    source_fur = any(s.visual.u16(row, 0) == 20001 for row in skin.submeshes)
    if equipped:
        from test_saberon_equipment import check as check_equipment
        check_equipment()
    animation.check_model(model, model_data)
    assert equipped or model.vertices == source.vertices
    assert model.materials[:len(source.materials)] == source.materials, 'Authored lighting flags must remain unchanged'
    assert equipped or Counter((s.visual.u16(row, 0), tri) for row in source_skin.submeshes
                   for tri in triangles(source_skin, row)) == Counter(
        (s.visual.u16(row, 0) - 3000 if s.visual.u16(row, 0) else 0, tri)
        for row in skin.submeshes for tri in triangles(skin, row))
    assert {q['id'] for q in source.sequences} <= {q['id'] for q in model.sequences}
    assert {e['identifier'] for e in source.events} <= {e['identifier'] for e in model.events}
    assert {0, 1, 2, 5, 6, 26, 27, 28} <= {a['id'] for a in model.attachments}
    assert model.attachment_lookup[11] == 65535
    assert len(skin.vertices) < 65536
    assert len(skin.indices) == (76488 if source_fur else 79728 if equipped else 69426)
    assert any(s.visual.u16(r, 2) for r in skin.submeshes), 'Large-mesh coverage was lost'
    for batch in skin.batches:
        first = model.textures[model.texture_combos[s.visual.u16(batch, 16)]]['type']
        if first in (11, 12, 13) and s.visual.u16(batch, 2) == 0:
            assert s.visual.u16(batch, 14) == 1 and not batch[0] & 0x80
            assert s.visual.u16(batch, 2) == 0
            if first == 11:
                assert model.materials[s.visual.u16(batch, 10)]['flags'] & 1 == 0, 'Fur must retain normal lighting'
    assert not s.normalize_materials(model, skin), 'Material repair must be idempotent'
    for row in skin.submeshes:
        start = s.visual.u16(row, 8) | s.visual.u16(row, 2) << 16
        count, palette, offset = (s.visual.u16(row, n) for n in (10, 12, 14))
        assert start + count <= len(skin.indices) and palette <= 75
        for index in skin.indices[start:start + count]:
            vertex = skin.vertices[index]
            for slot in range(4):
                if model.vertices[vertex * 48 + 12 + slot]:
                    bone = skin.bones[index * 4 + slot]
                    assert bone < palette
                    assert model.bone_combos[offset + bone] == model.vertices[vertex * 48 + 16 + slot]
    for texture in model.textures:
        if texture['type'] == 0:
            assert s.local(root / 'assets', texture['filename']).is_file()
    catalog = (root / 'EsteriaSaberon.bin').read_bytes()
    magic, version, count = struct.unpack_from('<3I', catalog)
    assert (magic, version, count) == (0x314D4845, 1, 41 if source_fur else 33 if equipped else 20)
    assert len(catalog) == 12 + count * 156
    records = [(struct.unpack_from('<7I', catalog, at), catalog[at + 28:at + 156].split(b'\0')[0].decode())
               for at in range(12, len(catalog), 156)]
    for fields in product(*[range(n) for n in s.profile()['capacities']]):
        selected = [(r, path) for r, path in records if r[1] != 5 and not (20001 <= r[3] <= 20009)
                    and all(selector == 0xffffffff or fields[selector & 65535] == selector >> 16
                            for selector in r[4:7])]
        expected = {(0, 31), (1, 11), (1, 12), (1, 13)}
        if equipped:
            expected.add((3, 0))
            if fields[1]:
                expected.add((2, 3100 + fields[1]))
        assert len(selected) == len(expected)
        assert {(r[1], r[2]) for r, path in selected} == expected
        assert next(r[3] for r, path in selected if r[1] == 0) == 3100 + fields[1]
        for r, path in selected:
            if r[1] == 1:
                assert s.local(root / 'assets', path).is_file()
    references = p.load_json(s.ROOT / 'reports/references.json')
    assert {r['ID'] for r in references['creatures']} == set(s.REFERENCES)
    assert {r['FileDataID'] for r in references['models']} == {s.MODEL_FID}
    assert {100 + r['GeosetValue'] for r in references['display_geosets']} <= set(s.CHOICES[1])
    for name in base.TABLES:
        before = p.RawWdbc((root / 'baseline' / (name + '.dbc')).read_bytes())
        after = p.RawWdbc((root / 'client-dbc' / (name + '.dbc')).read_bytes())
        assert not Counter(before.records) - Counter(after.records), name
        assert after.strings.startswith(before.strings), name
    for name in base.SERVER_TABLES:
        before = p.RawWdbc((root / 'baseline-server' / (name + '.dbc')).read_bytes())
        after = p.RawWdbc((root / 'server/dbc' / (name + '.dbc')).read_bytes())
        assert after.records[:before.count] == before.records and after.strings.startswith(before.strings), name
    races = p.RawWdbc((root / 'client-dbc/ChrRaces.dbc').read_bytes())
    row = next(r for r in races.records if p._value(r, 0) == s.RACE)
    assert p._value(row, 8) == 2 and p._value(row, 52) == 1 and p._value(row, 28) == 1
    assert (p._value(row, 16), p._value(row, 20)) == (60061, 0)
    assert p._string(races.strings, p._value(row, 44)) == b'SaberonHorde'
    models = p.RawWdbc((root / 'client-dbc/CreatureModelData.dbc').read_bytes())
    row = next(r for r in models.records if p._value(r, 0) == 120070)
    assert p._value(row, 4) & 0x804 == 0x804
    assert p._string(models.strings, p._value(row, 8)).decode() == s.MODEL
    outfits = p.RawWdbc((root / 'client-dbc/CharStartOutfit.dbc').read_bytes())
    rows = [r for r in outfits.records if r[4] == s.RACE]
    assert len(rows) == 10 and {r[5] for r in rows} == set(s.manifest()['classes'])
    assert all(r[6] == 0 and r[7] == 0 for r in rows)
    before = (root / 'baseline/EsteriaAppearance.bin').read_bytes()
    after = (root / 'EsteriaAppearance.bin').read_bytes()
    assert after[12:len(before)] == before[12:]
    assert struct.unpack_from('<3I', after, len(before)) == (s.RACE, 0, 5)
    for i, n in enumerate(s.profile()['capacities']):
        assert struct.unpack_from('<3I', after, len(before) + 12 + i * 144) == ((0x28, 0x2C, 0x34, 0x24, 0x30)[i], n, 1)
    before = (root / 'baseline/EsteriaAppearanceGeometry.bin').read_bytes()
    after = (root / 'EsteriaAppearanceGeometry.bin').read_bytes()
    assert after[12:len(before)] == before[12:]
    assert after[len(before):len(before) + 128].split(b'\0')[0].decode() == s.MODEL
    assert after[len(before) + 132:] == s.local(root / 'assets', s.MODEL[:-3] + '00.skin').read_bytes()
    lua = LuaRuntime()
    lua.execute('strupper=string.upper; function GetLocale() return "enUS" end; '
                'function GetFactionForRace() return "Human","Alliance" end; '
                'ECS={Const={TEX={},NEUTRAL_FACTION="Neutral"}};')
    lua.execute((root / 'glue/CharacterInfo.lua').read_text())
    assert lua.eval('GetExactRaceIDForFileString("SaberonHorde")') == 64
    assert lua.eval('GetFactionForRaceID(64)') == 'Horde'
    assert lua.eval('GetFactionForRaceID(63)') == 'Horde'
    assert lua.eval('GetFactionForRaceID(62)') == 'Alliance'
    lua.execute((root / 'glue/ECS_Schema.lua').read_text())
    assert lua.eval('ECS.Schema.RaceOverride[64].faction') == 2
    text = (root / 'glue/CharacterCreate.lua').read_text()
    assert 'MAX_RACES = 129;' in text and 'or race == 64' in text
    assert 'or CharacterCreate.selectedRaceID == 64' in text and 'strupper(fileString) == "SABERONHORDE"' in text
    report = p.load_json(root / 'report.json')
    storm = p.Storm(p.DLL_DEFAULT)
    for relative, expected in report['archives'].items():
        path = root / 'client' / relative
        assert p.sha256(path) == expected
        handle = storm.open_archive(path)
        try:
            if relative == str(s.ASSET_ARCHIVE):
                for key, expected in report['assets'].items():
                    assert hashlib.sha256(storm.read(handle, key)).hexdigest() == expected
            else:
                for name in base.TABLES:
                    assert storm.read(handle, p.DBC_ROOT + name + '.dbc') == (root / 'client-dbc' /
                                                                           (name + '.dbc')).read_bytes()
                for name in base.GLUE:
                    assert storm.read(handle, p.GLUE_ROOT + name) == (root / 'glue' / name).read_bytes()
        finally:
            storm.dll.SFileCloseArchive(handle)
    sql = (root / 'saberon.sql').read_text()
    assert 'SET @RACE := 64;' in sql and 'SET @DONOR := 2;' in sql
    assert "(@RACE, 0, 669, 'Language Orcish')" in sql
    assert 'DELETE FROM `characters`' not in sql
    if report['live_install_performed']:
        installed = p.load_json(root / 'last-install.json')
        assert all(p.sha256(p.CLIENT_DEFAULT / name) == sha for name, sha in installed['installed_hashes'].items())
    assert p.sha256(p.CLIENT_DEFAULT / 'Wow.exe') == report['exe_sha256']
    print('PASS Saberon: 360 appearance combinations, all source surfaces/animations, large-mesh closure,')
    print('Horde identity, starter rows, unrelated data, root/enUS/asset archive readbacks, executable integrity')


if __name__ == '__main__':
    check()
