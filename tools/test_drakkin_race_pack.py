"""Check the actual staged Drakkin package, preserving current races and source assets."""

from collections import Counter
import hashlib
import struct

from lupa.lua51 import LuaRuntime
from wotlkconv.m2 import parse_m2, parse_skin

import drakkin_race_pack as k
import sethrak_animation_pack as animations
import creature_animation_repair as motion


def check_creator_gender():
    source = (k.STAGE / 'glue/CharacterCreate.lua').read_text()
    source = source[source.index('-- This supplied Drakkin pack has one authored female body.'):]
    lua = LuaRuntime()
    lua.execute('''
        SEX_MALE=2; SEX_FEMALE=3; selectedSex=SEX_MALE;
        CharacterCreate={selectedRaceID=1};
        CharacterCreateRaceButton1={raceID=66};
        CharacterCreateRaceButton2={raceID=67};
        CharacterCreateRaceButton3={raceID=1};
        function SetSelectedSex(sex) selectedSex=sex; end
        function GetSelectedSex() return selectedSex; end
        function SetCharacterGender(sex) SetSelectedSex(sex); end
        function SetCharacterRace(id)
            local race=_G['CharacterCreateRaceButton'..id].raceID;
            assert((race~=66 and race~=67) or selectedSex==SEX_FEMALE);
            CharacterCreate.selectedRaceID=race;
            CharacterCreateGenderButtonMale.hidden=false;
            CharacterCreateGenderButtonFemale.hidden=false;
        end
        function hide(self) self.hidden=true; end
        CharacterCreateGenderButtonMale={Hide=hide};
        CharacterCreateGenderButtonFemale={Hide=hide};
    ''')
    lua.execute(source)
    lua.execute('''
        for _,id in ipairs({1,2,1,2}) do
            SetCharacterRace(id);
            assert(selectedSex==SEX_FEMALE and CharacterCreateGenderButtonMale.hidden);
            SetCharacterGender(SEX_MALE);
            assert(selectedSex==SEX_FEMALE);
        end
        SetCharacterRace(3); SetCharacterGender(SEX_MALE);
        assert(selectedSex==SEX_MALE and not CharacterCreateGenderButtonMale.hidden);
    ''')


def check():
    report = k.p.load_json(k.STAGE / 'report.json')
    for path, expected in report['source']['source_hashes'].items():
        assert k.p.sha256(k.Path(path)) == expected, 'Supplied source changed: ' + path
    for name, expected in report['catalog_baselines'].items():
        assert k.p.sha256(k.p.CLIENT_DEFAULT / name) == expected, 'Live runtime changed: ' + name
    assert k.p.sha256(k.p.CLIENT_DEFAULT / 'Wow.exe') == report['exe_sha256']
    for name in k.tables_lib.TABLES:
        old = k.p.RawWdbc((k.STAGE / 'baseline' / (name + '.dbc')).read_bytes())
        new = k.p.RawWdbc((k.STAGE / 'client-dbc' / (name + '.dbc')).read_bytes())
        assert not (Counter(old.records) - Counter(new.records)), name + ' lost unrelated rows'
        assert new.strings.startswith(old.strings), name + ' changed unrelated strings'
    for race, _, donor, _, display, count in k.SPECS:
        table = k.p.RawWdbc((k.STAGE / 'client-dbc/ChrRaces.dbc').read_bytes())
        row = next(row for row in table.records if k.p._value(row, 0) == race)
        assert [k.p._value(row, field * 4) for field in (2, 4, 5, 7, 13)] == [
            donor, 0, display, 7 if race == 66 else 1, 0 if race == 66 else 1]
        sections = k.p.RawWdbc((k.STAGE / 'client-dbc/CharSections.dbc').read_bytes())
        owned = [row for row in sections.records if k.p._value(row, 4) == race]
        assert all(k.p._value(row, 8) == 1 for row in owned), 'Advertised an unauthored male body'
        assert sorted(k.p._value(row, 36) for row in owned if k.p._value(row, 12) == 0) == list(range(count))
        for row in owned:
            for field in (4, 5, 6):
                key = k.p._string(sections.strings, k.p._value(row, field * 4)).decode()
                assert not key or key in report['assets'], 'Missing CharSections texture: ' + key
        table = k.p.RawWdbc((k.STAGE / 'client-dbc/CharStartOutfit.dbc').read_bytes())
        assert len([row for row in table.records if row[4] == race and row[6] == 1]) == 10
    blob = k.local(k.STAGE / 'assets', k.MODEL).read_bytes()
    model = parse_m2(blob)
    animations.check_model(model, blob)
    original = parse_m2((k.ROOT / 'converted/koboldfemale.m2').read_bytes())
    assert model.vertices.startswith(original.vertices), 'Drakkin source geometry was replaced'
    assert model.sequences == original.sequences
    for before, after in zip(original.tracks(), model.tracks(), strict=True):
        assert before.timestamps == after.timestamps
        if hasattr(before, 'values'):
            assert before.values == after.values, 'Authored animation changed'
    skin = parse_skin(k.local(k.STAGE / 'assets', k.MODEL[:-3] + '00.skin').read_bytes())
    assert model.version == 264 and model.num_skin_profiles == 1 and model.vertex_count < 65536
    # 3.3.5a player models carry a texture-coordinate lookup; an empty table leaves every
    # batch without a UV set and the client never draws the model.
    assert model.texture_coord_combos and all(
        k.visual.u16(batch, 18) < len(model.texture_coord_combos) for batch in skin.batches)
    assert {model.textures[model.texture_combos[k.visual.u16(batch, 16)]]['type']
            for batch in skin.batches} <= {0, 1, 2, 8}
    assert all(i < model.vertex_count for i in skin.vertices)
    assert all(i < len(skin.vertices) for i in skin.indices)
    assert all(k.visual.u16(row, 12) <= 75 for row in skin.submeshes)
    assert {403, 503, 903, 1104, 1302, 1502} <= {k.visual.u16(row, 0) for row in skin.submeshes}
    for row in skin.submeshes:
        start = k.visual.u16(row, 8) | k.visual.u16(row, 2) << 16
        assert start + k.visual.u16(row, 10) <= len(skin.indices)
    for action in (0, 4, 5, 13, 17, 18, 37, 38, 39, 41, 42, 50, 60, 119, 120, 133, 134):
        index = motion.sequence(model, action)
        while model.sequences[index]['flags'] & 0x40:
            index = model.sequences[index]['alias_next']
        assert any(t.timestamps[index] for t in model.tracks() if t.global_sequence < 0
                   and index < len(t.timestamps)), 'Missing authored action: ' + str(action)
    for name, expected in report['catalogs'].items():
        assert k.p.sha256(k.STAGE / name) == expected
    catalog = (k.STAGE / 'EsteriaAppearance.bin').read_bytes()
    assert struct.unpack_from('<3I', catalog, len(catalog) - 2 * 2316) == (66, 1, 5)
    assert struct.unpack_from('<3I', catalog, len(catalog) - 2316) == (67, 1, 5)
    check_creator_gender()
    storm = k.p.Storm(k.p.DLL_DEFAULT)
    for relative, expected in report['archives'].items():
        archive = k.STAGE / 'client' / relative
        assert k.p.sha256(archive) == expected and archive.stat().st_size < 0x80000000
        handle = storm.open_archive(archive)
        try:
            entries = report['assets'] if relative == str(k.ASSET) else {
                k.p.DBC_ROOT + name + '.dbc': k.p.sha256(k.STAGE / 'client-dbc' / (name + '.dbc'))
                for name in k.tables_lib.TABLES}
            for key, digest in entries.items():
                assert hashlib.sha256(storm.read(handle, key)).hexdigest() == digest, key
            if relative != str(k.ASSET):
                assert k.p.sha256(k.p.CLIENT_DEFAULT / relative) == report['archive_baselines'][relative]
                source = storm.open_archive(k.STAGE / 'baseline-archives' / relative)
                try:
                    old = {name.casefold(): size for name, size, _, _ in storm.list_files(source)
                           if name.casefold() not in ('(listfile)', '(attributes)')}
                    new = {name.casefold(): size for name, size, _, _ in storm.list_files(handle)}
                    assert old.keys() <= new.keys(), 'Unrelated archive entries were lost'
                    changed = {name.casefold() for name in entries}
                    changed.update((k.p.GLUE_ROOT + name).casefold() for name in k.tables_lib.GLUE)
                    assert all(new[name] == size for name, size in old.items() if name not in changed)
                    for name in k.tables_lib.GLUE:
                        assert storm.read(handle, k.p.GLUE_ROOT + name) == (k.STAGE / 'glue' / name).read_bytes()
                finally:
                    storm.dll.SFileCloseArchive(source)
        finally:
            storm.dll.SFileCloseArchive(handle)
    k.save(k.STAGE / 'checks.json', {'passed': True, 'races': [66, 67], 'assets': len(report['assets']),
           'native_build_checked': False, 'live_client_checked': False})
    print('PASS Drakkin source preservation, model/armor/action bounds, female creator guards, DBC and MPQ readback')


if __name__ == '__main__':
    check()
