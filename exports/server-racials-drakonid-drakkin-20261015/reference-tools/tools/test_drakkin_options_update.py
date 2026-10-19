"""Check the staged Drakkin update against current data and executable Lua behavior."""

from collections import Counter
import re
import struct

from lupa.lua51 import LuaRuntime

import drakkin_options_update as u


def check():
    sections = u.p.RawWdbc((u.STAGE / 'client-dbc/CharSections.dbc').read_bytes())
    for name in u.TABLES:
        before = (u.STAGE / 'baseline' / (name + '.dbc')).read_bytes()
        after = (u.STAGE / 'client-dbc' / (name + '.dbc')).read_bytes()
        old, new = u.p.RawWdbc(before), u.p.RawWdbc(after)
        owned = {row for race in (66, 67) for row in u.p._table_rows_for_race(before, name, race)}
        assert not (Counter(row for row in old.records if row not in owned) - Counter(new.records)), name
        assert new.strings.startswith(old.strings), name
    for path in (u.STAGE / 'baseline-server').glob('*.dbc'):
        before = path.read_bytes()
        old = u.p.RawWdbc(before)
        new = u.p.RawWdbc((u.STAGE / 'server-dbc' / path.name).read_bytes())
        owned = {row for race in (66, 67) for row in u.p._table_rows_for_race(before, path.stem, race)}
        assert not (Counter(row for row in old.records if row not in owned) - Counter(new.records)), path.name
    for race in (66, 67):
        manifest = u.p.load_manifest('drakkin_' + ('alliance' if race == 66 else 'horde'))
        assert manifest['models']['male'] == manifest['models']['female']
        assert manifest['appearance']['profiles']['0'] == manifest['appearance']['profiles']['1']
        for gender in (0, 1):
            rows = [row for row in sections.records if u.p._value(row, 4) == race
                    and u.p._value(row, 8) == gender]
            skins = sorted((u.p._value(row, 36), u.p._string(sections.strings, u.p._value(row, 16)))
                           for row in rows if u.p._value(row, 12) == 0)
            assert [index for index, _ in skins] == list(range(16))
            assert [path.decode() for _, path in skins] == [
                f'custom\\kobold\\body-{index}.blp' for index in u.skin_order(race)]
            eyes = sorted(u.p._value(row, 36) for row in rows if u.p._value(row, 12) == 3)
            assert eyes == list(range(25))
            outfits = u.p.RawWdbc((u.STAGE / 'client-dbc/CharStartOutfit.dbc').read_bytes())
            assert len([row for row in outfits.records if row[4] == race and row[6] == gender]) == 10
        # Original saved female skin indexes still point at the original textures.
        baseline = u.p.RawWdbc((u.STAGE / 'baseline/CharSections.dbc').read_bytes())
        for row in baseline.records:
            if u.p._value(row, 4) == race and u.p._value(row, 12) == 0:
                color = u.p._value(row, 36)
                new = next(v for v in sections.records if u.p._value(v, 4) == race
                           and u.p._value(v, 8) == 1 and u.p._value(v, 12) == 0
                           and u.p._value(v, 36) == color)
                for offset in (16, 20):
                    assert u.p._string(baseline.strings, u.p._value(row, offset)) == \
                        u.p._string(sections.strings, u.p._value(new, offset))
    for folder in ('client-dbc', 'server-dbc'):
        races = u.p.RawWdbc((u.STAGE / folder / 'ChrRaces.dbc').read_bytes())
        assert u.p._value(next(row for row in races.records if u.p._value(row, 0) == 67), 4) & 1
        assert not u.p._value(next(row for row in races.records if u.p._value(row, 0) == 66), 4) & 1
    base = u.p.RawWdbc((u.STAGE / 'client-dbc/CharBaseInfo.dbc').read_bytes())
    assert not any(row[0] == 67 for row in base.records)
    assert len([row for row in base.records if row[0] == 66]) == 10
    text = (u.STAGE / 'CharacterCreate.lua').read_text()
    assert 'local hiddenRace = strupper(fileString) == "DRAKKINHORDE"' in text
    lua = LuaRuntime()
    icon_table = text[text.index('RACE_ICON_TEXTURES = {'):]
    icon_table = icon_table[:icon_table.index('\n}') + 2]
    lua.execute(icon_table)
    icons = lua.globals().RACE_ICON_TEXTURES
    for token in ('DRAKKINALLIANCE', 'DRAKKINHORDE', 'GNOLLHORDE', 'SABERONHORDE'):
        assert icons[token + '_MALE'] and icons[token + '_FEMALE']
    for token in ('GNOLLHORDE', 'SABERONHORDE'):
        assert icons[token + '_FEMALE'] == icons[token + '_MALE']
    creator = text[text.index('-- Only Naga has an authored second playable body type'):]
    lua.execute('''
        SEX_MALE=2; SEX_FEMALE=3; selectedSex=SEX_MALE;
        CharacterCreate={selectedRaceID=1};
        function SetCharacterRace(id) CharacterCreate.selectedRaceID=id; end
        function SetCharacterGender(sex) selectedSex=sex; end
        function GetSelectedSex() return selectedSex; end
        function CharacterCreate_IsMaleOnlyRace(race) return race==63 or race==64; end
        function CharacterCreate_UpdateModel() end
        function CharacterCreate_UpdateButtonCheckedStates() end
        function CharacterCreate_ResetState() end
        function GetNameForRace() return '', 'DRAKKINALLIANCE'; end
        function strupper(value) return string.upper(value); end
        function show(self) self.hidden=false; end
        function hide(self) self.hidden=true; end
        function enable(self) self.disabled=false; end
        function disable(self) self.disabled=true; end
        CharacterCreateGenderButtonMale={Show=show,Hide=hide};
        CharacterCreateGenderButtonFemale={Show=show,Hide=hide,Enable=enable,Disable=disable};
    ''')
    lua.execute(creator)
    lua.execute('''
        for _,race in ipairs({66,67,1}) do
            SetCharacterRace(race);
            assert(not CharacterCreateGenderButtonMale.hidden);
            assert(not CharacterCreateGenderButtonFemale.hidden);
            for _,sex in ipairs({SEX_MALE,SEX_FEMALE}) do
                SetCharacterGender(sex); assert(GetSelectedSex()==sex);
                CharacterCreate_UpdateButtonCheckedStates(); assert(GetSelectedSex()==sex);
            end
        end
    ''')
    assert u.update_glue(text.encode()) == text.encode(), 'Glue update is not idempotent'
    storm = u.p.Storm(u.p.DLL_DEFAULT)
    handle = storm.open_archive(u.STAGE / 'client' / u.k.ASSET)
    try:
        model = u.k.parse_m2(storm.read(handle, u.k.MODEL))
        skin = u.k.parse_skin(storm.read(handle, u.k.MODEL[:-3] + '00.skin'))
        used = {model.texture_combos[u.k.visual.u16(batch, 16)] for batch in skin.batches}
        assert 9 in used and model.textures[9]['type'] == 6
        assert model.replacable_texture_lookup[6] == 9
        for eye in range(25):
            blob = storm.read(handle, f'custom\\kobold\\koboldeyes00_{eye:02d}.blp')
            assert u.Blp.parse(blob).decode_level(0).width > 0
        names = [name for name, *_ in storm.list_files(handle)]
        male_helmets = [name for name in names if re.search(r'KbM\.m2$', name, re.I)]
        assert male_helmets, 'No isolated male Drakkin helmet aliases'
        for name in male_helmets:
            assert storm.read(handle, name) == storm.read(handle, re.sub(r'KbM\.', 'KbF.', name, flags=re.I))
            helmet = u.k.parse_m2(storm.read(handle, name))
            for lod in range(helmet.num_skin_profiles):
                assert storm.read(handle, name[:-3] + f'{lod:02d}.skin')
    finally:
        storm.dll.SFileCloseArchive(handle)
    catalog = (u.STAGE / 'EsteriaAppearance.bin').read_bytes()
    count = struct.unpack_from('<I', catalog, 8)[0]
    profiles = [catalog[12 + i * 2316:12 + (i + 1) * 2316] for i in range(count)]
    assert {(u.p._value(row, 0), u.p._value(row, 4)) for row in profiles
            if u.p._value(row, 0) in (66, 67)} == {(66, 0), (66, 1), (67, 0), (67, 1)}
    original = (u.STAGE / 'EsteriaAppearance-before.bin').read_bytes()
    old_count = struct.unpack_from('<I', original, 8)[0]
    for i in range(old_count):
        row = original[12 + i * 2316:12 + (i + 1) * 2316]
        if u.p._value(row, 0) not in (66, 67):
            assert row in profiles, 'Unrelated appearance profile changed'
    print('PASS: skin preservation, both genders, all eyes, Lua gender switching, portrait mappings, helmet aliases')


if __name__ == '__main__':
    check()
