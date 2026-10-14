"""Check the staged Alliance race's faction, saved appearance combinations and starting contract."""

import itertools
import struct

from lupa.lua51 import LuaRuntime

import sethrak_race_pack as pack
import retroported_race_pack as p


def check_gender_switch(text):
    lua = LuaRuntime()
    lua.execute('''
        CharacterCreate={selectedRaceID=62};
        CharacterCreateFrame={};
        gender=0;
        function widget()
            local w={shown=true};
            function w:GetParent() return self; end
            function w:ClearAllPoints() end
            function w:SetPoint(...) end
            function w:SetText(...) end
            function w:IsShown() return self.shown; end
            function w:Show() self.shown=true; end
            function w:Hide() self.shown=false; end
            return w;
        end
        CharCreateOkayButton=widget();
        for i=1,29 do
            _G["CharacterCustomizationButtonFrame"..i]=widget();
            _G["CharacterCustomizationButtonFrame"..i.."Text"]=widget();
        end
        local male={5,1,4,4,1};
        function CycleCharCustomization(command,index)
            return 0,index<=5 and (gender==0 and male[index] or 1) or 0,"Choice";
        end
    ''')
    start = text.index('local function EA_ACTIVE()')
    end = text.index('function CharacterCustomization_Left(id)', start)
    lua.execute(text[start:end] + '\nRefreshTest=EA_REFRESH;')
    lua.execute('''
        RefreshTest();
        assert(CharacterCustomizationButtonFrame1:IsShown());
        assert(CharacterCustomizationButtonFrame3:IsShown());
        assert(CharacterCustomizationButtonFrame4:IsShown());
        gender=1; RefreshTest();
        for i=1,29 do assert(not _G["CharacterCustomizationButtonFrame"..i]:IsShown()); end
        gender=0; RefreshTest();
        assert(CharacterCustomizationButtonFrame1:IsShown(),"male pickers stay hidden after female");
        assert(CharacterCustomizationButtonFrame3:IsShown());
        assert(CharacterCustomizationButtonFrame4:IsShown());
        CharCreateOkayButton:Hide(); RefreshTest();
        for i=1,29 do assert(not _G["CharacterCustomizationButtonFrame"..i]:IsShown()); end
        CharCreateOkayButton:Show(); RefreshTest();
        assert(CharacterCustomizationButtonFrame1:IsShown());
    ''')


def check():
    root = pack.STAGE
    manifest = p.load_manifest('sethrak')
    lua = LuaRuntime()
    lua.execute('''
        strupper=string.upper;
        function GetLocale() return "enUS"; end
        function GetFactionForRace(id) return "Human","Alliance"; end
        ECS={Const={TEX={allianceBadge="Alliance",hordeBadge="Horde",freebornBadge="Freeborn"},
                   NEUTRAL_FACTION="Neutral"}};
    ''')
    lua.execute((root / 'glue/CharacterInfo.lua').read_text(encoding='utf-8'))
    assert lua.eval('GetExactRaceIDForFileString("SethrakAlliance")') == 62
    assert lua.eval('GetFactionForRaceID(62)') == 'Alliance'
    assert lua.eval('GetFactionForRaceID(54)') == 'Horde'
    assert lua.eval('GetExactRaceIDForFileString("ThinHuman")') == 58
    lua.execute((root / 'glue/ECS_Schema.lua').read_text(encoding='utf-8'))
    assert lua.eval('ECS.Schema.RaceOverride[62].faction') == 1
    assert lua.eval('ECS.Schema.RaceOverride[62].artKey') == 'SethrakAlliance'
    assert lua.eval('ECS.Schema.RaceByModelKey[1][1]') == 'SETHRAKALLIANCE'
    catalog = (root / 'EsteriaSethrak.bin').read_bytes()
    magic, version, count = struct.unpack_from('<3I', catalog)
    assert (magic, version) == (0x314D4845, 1) and len(catalog) == 12 + count * 156
    records = [(struct.unpack_from('<7I', catalog, offset),
                catalog[offset + 28:offset + 156].split(b'\0')[0].decode())
               for offset in range(12, len(catalog), 156)]
    checked = 0
    for gender in (0, 1):
        capacities = manifest['appearance']['profiles'][str(gender)]['capacities']
        for values in itertools.product(*(range(n) for n in capacities)):
            selected = [(r, key) for r, key in records if r[0] == gender and
                        all(s == 0xffffffff or values[s & 0xffff] == s >> 16 for s in r[4:7])]
            styles = [r[3] for r, _ in selected if r[1:3] == (0, 1)]
            assert styles == [101 + values[2] if gender == 0 else 102]
            materials = [(r[2], key) for r, key in selected if r[1] == 1]
            assert sorted(slot for slot, _ in materials) == ([11, 12] if gender == 0 else [])
            for _, key in materials:
                assert pack.animations.local(root / 'assets', key).is_file()
            checked += 1
    assert checked == 81
    for name, count, predicate in (
        ('ChrRaces', 1, lambda r: p._value(r, 0) == 62),
        ('CharBaseInfo', 10, lambda r: r[0] == 62),
        ('CharStartOutfit', 20, lambda r: r[4] == 62),
    ):
        table = p.RawWdbc((root / 'client-dbc' / (name + '.dbc')).read_bytes())
        rows = [r for r in table.records if predicate(r)]
        assert len(rows) == count
        if name == 'ChrRaces':
            r = rows[0]
            assert not p._value(r, 4) & 1 and p._value(r, 52) == 0
            assert p._value(r, 8) == 1 and p._value(r, 28) == 7
            assert (p._value(r, 16), p._value(r, 20)) == (60057, 60058)
            assert p._string(table.strings, p._value(r, 44)) == b'SethrakAlliance'
        elif name == 'CharBaseInfo':
            assert sorted(r[1] for r in rows) == manifest['classes']
        else:
            assert {(r[5], r[6], r[7]) for r in rows} == {
                (cls, gender, 0) for cls in manifest['classes'] for gender in (0, 1)}
    geometry = (root / 'EsteriaAppearanceGeometry.bin').read_bytes()
    original = (root / 'baseline/EsteriaAppearanceGeometry.bin').read_bytes()
    assert geometry[12:len(original)] == original[12:]
    assert struct.unpack_from('<I', geometry, 8)[0] == struct.unpack_from('<I', original, 8)[0] + 2
    sql = (root / 'sethrak.sql').read_text(encoding='utf-8')
    assert 'SET @RACE := 62;' in sql and 'SET @DONOR := 1;' in sql
    assert "(@RACE, 0, 668, 'Language Common')" in sql
    assert "(@RACE, 0, 98, 0, 'Language Common')" in sql
    assert '`RaceID` = 11' in sql and 'DELETE FROM `characters`' not in sql
    check_gender_switch((root / 'glue/CharacterCreate.lua').read_text(encoding='utf-8'))
    print('PASS: 81 material/armor states, Alliance faction/portraits, 10 classes, 20 outfits and Common startup')


if __name__ == '__main__':
    check()
