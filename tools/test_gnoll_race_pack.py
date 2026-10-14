"""Check Gnoll's staged appearance, retained anatomy/animations and additive Horde package."""

from collections import Counter
import hashlib
import math
import struct

from lupa.lua51 import LuaRuntime
from wotlkconv.m2 import parse_m2, parse_skin

import gnoll_race_pack as g
import retroported_race_pack as p
import sethrak_animation_pack as animations
import sethrak_race_pack as base


def check_codec():
    profile = g.codec()
    assert len(profile['options']) == 15 and profile['capacities'] == [120, 54, 60, 48, 3]
    for field, indices in enumerate(g.FIELDS):
        for encoded in range(profile['capacities'][field]):
            choices = {i: encoded // profile['descriptors'][i][2] % len(g.CHOICES[i]) for i in indices}
            assert encoded == sum(choices[i] * profile['descriptors'][i][2] for i in indices)
            for index in indices:
                for new in range(len(g.CHOICES[index])):
                    changed = encoded + (new - choices[index]) * profile['descriptors'][index][2]
                    assert 0 <= changed < profile['capacities'][field]
                    for other in indices:
                        if other != index:
                            assert changed // profile['descriptors'][other][2] % len(g.CHOICES[other]) == choices[other]
    catalog = (g.STAGE / 'EsteriaGnoll.bin').read_bytes()
    magic, version, count = struct.unpack_from('<3I', catalog)
    assert (magic, version) == (0x314D4845, 1) and len(catalog) == 12 + count * 156
    records = [(struct.unpack_from('<7I', catalog, at), catalog[at + 28:at + 156].split(b'\0')[0].decode())
               for at in range(12, len(catalog), 156)]
    for index, choices in enumerate(g.CHOICES):
        for choice, value in enumerate(choices):
            selected = [r for r, key in records if r[4] == index | choice << 16]
            if index == 0:
                assert {(r[1], r[2]) for r in selected} == {(1, 11)}
            elif index == 5:
                assert [(r[1], r[2]) for r in selected] == [(1, 12)]
            else:
                assert [(r[1], r[2], r[3]) for r in selected] == [(0, 30 + value // 100, 3000 + value)]
    for row, key in records:
        if row[1] == 1:
            assert g.local(g.STAGE / 'assets', key).is_file()
    print('PASS all 15 controls: independent byte round-trips, mesh choices and skin/palette mappings')


def check_geometry():
    data = g.local(g.STAGE / 'assets', g.MODEL).read_bytes()
    model = parse_m2(data)
    skin = parse_skin(g.local(g.STAGE / 'assets', g.MODEL[:-3] + '00.skin').read_bytes())
    animations.check_model(model, data)
    assert model.vertex_count < 65536 and len(skin.vertices) < 65536
    assert all(g.visual.u16(mesh, 12) <= 75 for mesh in skin.submeshes)
    source = parse_m2(g.raw(3886641))
    source_skin = parse_skin(g.raw(3886655))

    def surfaces(m, k):
        return Counter(tuple(m.vertices[v * 48:v * 48 + 32] for v in tri)
                       for row in k.submeshes for tri in g.triangles(k, row))

    # The shared packer removes duplicate draws of an identical triangle, retaining its actual surface.
    assert not set(surfaces(source, source_skin)) - set(surfaces(model, skin)), 'An authored surface was removed'
    required = {3000 + g.visual.u16(row, 0) for row in source_skin.submeshes if g.visual.u16(row, 0)}
    present = {g.visual.u16(row, 0) for row in skin.submeshes}
    assert required <= present
    assert {401, 402, 403, 404, 502, 503, 504, 505, 802, 803, 902, 903,
            1002, 1102, 1104, 1202, 1301, 1302, 1502, 1503, 1504, 1505, 1506, 1802} <= present
    assert {0, 1, 2, 5, 6, 28} <= {a['id'] for a in model.attachments}
    assert 11 not in {a['id'] for a in model.attachments}, 'Helmets are not fitted for this port'
    for row in skin.submeshes:
        offset = g.visual.u16(row, 14)
        start = g.visual.u16(row, 8) | g.visual.u16(row, 2) << 16
        count = g.visual.u16(row, 10)
        for index in skin.indices[start:start + count]:
            vertex = skin.vertices[index]
            for slot in range(4):
                if model.vertices[vertex * 48 + 12 + slot]:
                    local_bone = skin.bones[index * 4 + slot]
                    assert local_bone < g.visual.u16(row, 12)
                    assert model.bone_combos[offset + local_bone] == model.vertices[vertex * 48 + 16 + slot]
    for texture in model.textures:
        if texture['type'] == 0:
            assert g.local(g.STAGE / 'assets', texture['filename']).exists()
    assert {s['id'] for s in source.sequences} <= {s['id'] for s in model.sequences}
    assert {e['identifier'] for e in source.events} <= {e['identifier'] for e in model.events}
    print('PASS retained source triangles/geosets, player garments, sockets, animation closure and native limits')


def check():
    check_codec()
    check_geometry()
    root = g.STAGE
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
    row = next(r for r in races.records if p._value(r, 0) == 63)
    assert p._value(row, 8) == 2 and p._value(row, 52) == 1 and p._value(row, 28) == 1
    assert (p._value(row, 16), p._value(row, 20)) == (60059, 0)
    assert p._string(races.strings, p._value(row, 44)) == b'GnollHorde'
    models = p.RawWdbc((root / 'client-dbc/CreatureModelData.dbc').read_bytes())
    row = next(r for r in models.records if p._value(r, 0) == 120068)
    assert p._value(row, 4) & 4, 'The live client requires PLAYER_MODEL to create the appearance component'
    assert struct.unpack_from('<f', row, 16)[0] == 1.0
    assert math.isclose(struct.unpack_from('<f', row, 56)[0], .6111111044883728)
    assert math.isclose(struct.unpack_from('<f', row, 60)[0], 2.031277894973755)
    outfits = p.RawWdbc((root / 'client-dbc/CharStartOutfit.dbc').read_bytes())
    rows = [r for r in outfits.records if r[4] == 63]
    assert len(rows) == 10 and {r[5] for r in rows} == set(g.manifest()['classes'])
    assert all(r[6] == 0 and r[7] == 0 for r in rows)
    lua = LuaRuntime()
    lua.execute('strupper=string.upper; function GetLocale() return "enUS" end; '
                'function GetFactionForRace() return "Human","Alliance" end; '
                'ECS={Const={TEX={},NEUTRAL_FACTION="Neutral"}};')
    lua.execute((root / 'glue/CharacterInfo.lua').read_text())
    assert lua.eval('GetExactRaceIDForFileString("GnollHorde")') == 63
    assert lua.eval('GetFactionForRaceID(63)') == 'Horde'
    assert lua.eval('GetFactionForRaceID(62)') == 'Alliance'
    lua.execute((root / 'glue/ECS_Schema.lua').read_text())
    assert lua.eval('ECS.Schema.RaceOverride[63].faction') == 2
    text = (root / 'glue/CharacterCreate.lua').read_text()
    assert 'or race == 63' in text and 'or CharacterCreate.selectedRaceID == 63' in text
    bank = (root / 'EsteriaGnollTextures.bin').read_bytes()
    magic, version, count, checksum = struct.unpack_from('<4I', bank)
    assert (magic, version, count) == (0x31544845, 1, 20)
    assert checksum == int.from_bytes(hashlib.sha256(bank[16:]).digest()[:4], 'little')
    report = p.load_json(root / 'report.json')
    storm = p.Storm(p.DLL_DEFAULT)
    for relative, expected in report['archives'].items():
        path = root / 'client' / relative
        assert p.sha256(path) == expected
        handle = storm.open_archive(path)
        try:
            if relative == str(g.ASSET_ARCHIVE):
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
    sql = (root / 'gnoll.sql').read_text()
    assert 'SET @RACE := 63;' in sql and 'SET @DONOR := 2;' in sql
    assert "(@RACE, 0, 669, 'Language Orcish')" in sql
    assert "(@RACE, 0, 109, 0, 'Language Orcish')" in sql
    assert 'DELETE FROM `characters`' not in sql
    if report['live_install_performed']:
        installed = p.load_json(root / 'last-install.json')
        assert all(p.sha256(p.CLIENT_DEFAULT / name) == sha for name, sha in installed['installed_hashes'].items())
    assert p.sha256(p.CLIENT_DEFAULT / 'Wow.exe') == report['exe_sha256']
    print('PASS Horde identity, male-only starts, Orcish, additive tables, archive readbacks and executable integrity')


if __name__ == '__main__':
    check()
