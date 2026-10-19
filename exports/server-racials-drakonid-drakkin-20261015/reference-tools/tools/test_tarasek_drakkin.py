"""Focused preservation, codec, model, Lua and migration checks for the staged male Drakkin port."""
from collections import Counter
import copy
from pathlib import Path
import sqlite3
import struct

import tarasek_drakkin as t
import tarasek_equipment as e
import sethrak_animation_pack as animations
from lupa.lua51 import LuaRuntime
from wotlkconv.m2 import parse_m2, parse_skin


def allowed_change(name, row):
    if name == 'ChrRaces':
        return t.p._value(row, 0) == 66
    if name in ('CreatureModelData', 'CreatureDisplayInfo'):
        return False
    offsets = {'CharSections': (4, 8), 'CharHairGeosets': (4, 8),
               'CharacterFacialHairStyles': (0, 4), 'BarberShopStyle': (148, 152)}
    race, gender = offsets[name]
    return t.p._value(row, race) == 66 and t.p._value(row, gender) == 0


def tables():
    checked = 0
    for folder, base in (('client-dbc', t.WORK / 'baseline/DBFilesClient'),
                         ('server-dbc', t.STAGE / 'baseline-server')):
        for path in (t.STAGE / folder).glob('*.dbc'):
            old = t.p.RawWdbc((base / path.name).read_bytes())
            new = t.p.RawWdbc(path.read_bytes())
            unchanged = [row for row in old.records if not allowed_change(path.stem, row)]
            assert not Counter(unchanged) - Counter(new.records), (folder, path.stem)
            assert new.strings.startswith(old.strings), (folder, path.stem)
            if path.stem == 'ChrRaces':
                before = next(r for r in old.records if t.p._value(r, 0) == 66)
                after = next(r for r in new.records if t.p._value(r, 0) == 66)
                assert t.p._replace(after, 16, 4, t.p._value(before, 16)) == before
                assert t.p._value(after, 16) == t.DISPLAY_ID
            elif path.stem == 'CharSections':
                keys = [tuple(t.p._value(r, at) for at in (4, 8, 12, 32, 36)) for r in new.records]
                assert keys == sorted(keys)
                skins = [r for r in new.records if t.p._value(r, 4) == 66 and t.p._value(r, 8) == 0
                         and t.p._value(r, 12) == 0]
                assert [t.p._value(r, 36) for r in skins] == list(range(6))
            checked += 1
    return checked


def models():
    original = parse_m2(t.MODEL_SOURCE.read_bytes())
    path = Path(t.p.load_json(e.WORK / 'report.json')['model'])
    blob = path.read_bytes()
    model = parse_m2(blob)
    skin = parse_skin(path.with_name('tarasek00.skin').read_bytes())
    animations.check_model(model, blob)
    trimmed = copy.copy(model)
    trimmed.bones = model.bones[:len(original.bones)]
    animations.tracks_equal(original, trimmed, len(original.sequences))
    assert model.vertices[:len(original.vertices)] == original.vertices
    assert len(model.sequences) == 179 and len(original.sequences) == 165
    assert model.vertex_count < 65536 and max(skin.vertices) < model.vertex_count
    assert max(e.visual.u16(row, 12) for row in skin.submeshes) <= 75
    geosets = {e.visual.u16(row, 0) for row in skin.submeshes}
    assert set(range(3301, 3306)) <= geosets
    assert set(range(20001, 20009)) <= geosets
    assert not geosets & {102, 103, 104, 202}
    for batch in skin.batches:
        count, combo = struct.unpack_from('<HH', batch, 14)
        assert all(model.textures[model.texture_combos[combo + j]]['type'] != 12 for j in range(count))
    for vertex in set(skin.vertices):
        record = e.equipment.vertex_record(model, vertex)
        assert sum(record['weights']) == 255
        assert all(b < len(model.bones) for b, w in zip(record['bones'], record['weights']) if w)
    report = t.p.load_json(t.WORK / 'reports/animation-repair.json')
    assert all(row['moving_matched_bones'] for row in report['added_actions'])


def catalogs():
    old = (t.WORK / 'baseline/EsteriaAppearance.bin').read_bytes()
    new = (t.STAGE / 'EsteriaAppearance.bin').read_bytes()
    assert old[:12] == new[:12]
    for at in range(12, len(old), 2316):
        before, after = old[at:at + 2316], new[at:at + 2316]
        if struct.unpack_from('<2I', before) != (66, 0):
            assert before == after, 'Female/unrelated EAPP profile changed'
        else:
            assert [t.p._value(after, 12 + 144 * i + 4) for i in range(5)] == list(t.CAPACITIES)
    old = (t.WORK / 'baseline/EsteriaAppearanceGeometry.bin').read_bytes()
    new = (t.STAGE / 'EsteriaAppearanceGeometry.bin').read_bytes()
    assert new[12:len(old)] == old[12:]
    assert t.p._value(new, 8) == t.p._value(old, 8) + 1
    catalog = (t.STAGE / 'EsteriaTarasek.bin').read_bytes()
    rows = [catalog[at:at + 156] for at in range(12, len(catalog), 156)]
    assert len(rows) == t.p._value(catalog, 8)
    assert all(t.p._value(row, 0) == 0 for row in rows)
    assert len([r for r in rows if t.p._value(r, 4) == 1 and t.p._value(r, 8) == 11]) == 6
    assert len([r for r in rows if t.p._value(r, 4) == 0 and t.p._value(r, 8) == 33]) == 5


def helmets():
    report = t.p.load_json(t.WORK / 'reports/helmets.json')
    assert report['per_model_deformation'] is False
    for key, info in report['sources'].items():
        source = t.PureWindowsPath(key)
        stem = source.stem.rsplit('_', 1)[0]
        raw = (t.WORK / 'helmet-sources' / (info.get('cache_stem', stem) + '.m2')).read_bytes()
        path = t.STAGE / 'assets/Item/ObjectComponents/Head' / (stem + '_KbM.m2')
        target = path.read_bytes()
        assert t.sha(raw) == info['m2_sha256']
        assert t.sha(path.with_name(path.stem + '00.skin').read_bytes()) == info['skin_sha256']
        delta = info.get('translation', [0, 0, 0])
        if not any(delta):
            assert raw == target, 'Unnecessary donor helmet rewrite: ' + key
        else:
            old, new = parse_m2(raw), parse_m2(target)
            assert old.vertex_count == new.vertex_count
            for index in range(old.vertex_count):
                assert old.vertices[index * 48 + 12:(index + 1) * 48] == \
                    new.vertices[index * 48 + 12:(index + 1) * 48], 'Normals/UVs/weights changed'
                a = struct.unpack_from('<3f', old.vertices, index * 48)
                b = struct.unpack_from('<3f', new.vertices, index * 48)
                assert all(abs(b[i] - a[i] - delta[i]) < 1e-5 for i in range(3)), 'Helmet was stretched'
    print('Verified unchanged donor helmet shapes:', len(report['sources']))


def lua():
    text = (t.STAGE / 'CharacterCreate.lua').read_text()
    runtime = LuaRuntime()
    runtime.eval('function(s) local f,e=loadstring(s); assert(f,e); end')(text)
    runtime.execute('''
        SEX_MALE=2; SEX_FEMALE=3; selectedSex=SEX_MALE;
        CharacterCreate={selectedRaceID=66};
        function GetSelectedSex() return selectedSex; end
        local function show(self) self.hidden=false; end
        local function hide(self) self.hidden=true; end
        local function enable(self) self.disabled=false; end
        CharacterCreateGenderButtonMale={Show=show,Hide=hide,Enable=enable};
        CharacterCreateGenderButtonFemale={Show=show,Hide=hide,Enable=enable};
        function SetCharacterRace(id)
            CharacterCreate.selectedRaceID=id;
            CharacterCreateGenderButtonMale:Hide();
            CharacterCreateGenderButtonFemale:Hide();
            CharacterCreateGenderButtonMale.disabled=true;
            CharacterCreateGenderButtonFemale.disabled=true;
        end
    ''')
    runtime.execute(text[text.index('-- Drakkin: Tarasek male'):])
    runtime.execute('''
        SetCharacterRace(66);
        assert(not CharacterCreateGenderButtonMale.hidden and not CharacterCreateGenderButtonMale.disabled);
        assert(not CharacterCreateGenderButtonFemale.hidden and not CharacterCreateGenderButtonFemale.disabled);
        SetCharacterRace(63);
        assert(CharacterCreateGenderButtonFemale.hidden);
    ''')
    block = text[text.index('        if CharacterCreate.selectedRaceID == 66 and GetSelectedSex()'):]
    block = block[:block.index('        if CharacterCreate.selectedRaceID == 65')]
    runtime.execute('''
        for i=1,5 do
            _G['CharacterCustomizationButtonFrame'..i]={hidden=false,Hide=function(s) s.hidden=true; end,
                Show=function(s) s.hidden=false; end};
            _G['CharacterCustomizationButtonFrame'..i..'Text']={SetText=function(s,v) s.text=v; end};
        end
        function reset()
            for i=1,5 do _G['CharacterCustomizationButtonFrame'..i].hidden=false; end
        end
    ''')
    runtime.execute('function layout() ' + block + ' end')
    runtime.execute('''
        CharacterCreate.selectedRaceID=66; selectedSex=SEX_MALE; layout();
        assert(not CharacterCustomizationButtonFrame3.hidden);
        assert(CharacterCustomizationButtonFrame3Text.text=='Horns');
        assert(CharacterCustomizationButtonFrame4.hidden);
        reset(); selectedSex=SEX_FEMALE; layout();
        assert(CharacterCustomizationButtonFrame3.hidden and not CharacterCustomizationButtonFrame4.hidden);
        assert(CharacterCustomizationButtonFrame4Text.text=='Eye Color');
        reset(); CharacterCreate.selectedRaceID=1; layout();
        assert(not CharacterCustomizationButtonFrame3.hidden and not CharacterCustomizationButtonFrame4.hidden);
    ''')


def migrations():
    rows = t.p.load_json(t.WORK / 'baseline/population.json')['rows']
    database = sqlite3.connect(':memory:')
    database.execute('CREATE TABLE characters '
                     '(guid,race,gender,skin,face,hairStyle,hairColor,facialStyle,extraAppearance)')
    database.executemany('INSERT INTO characters VALUES (?,?,?,?,?,?,?,?,?)', rows)
    forward = (t.STAGE / 'pending_db_characters.sql').read_text()
    rollback = (t.STAGE / 'rollback-characters.sql').read_text()
    database.executescript(forward)
    database.executescript(forward)
    current = [list(r) for r in database.execute('SELECT * FROM characters ORDER BY guid')]
    assert current == [r[:3] + [0] * 6 if r[1:3] == [66, 0] else r for r in rows]
    database.executescript(rollback)
    assert [list(r) for r in database.execute('SELECT * FROM characters ORDER BY guid')] == rows
    database.close()


def check():
    report = t.p.load_json(t.STAGE / 'report.json')
    assert report['state'] in ('integration_staged_requires_builds_and_install',
                               'installed_and_server_ready_live_client_pending')
    count = tables()
    models()
    catalogs()
    helmets()
    lua()
    migrations()
    for relative, record in report['archives'].items():
        path = t.STAGE / 'client' / relative
        assert t.p.sha256(path) == record['sha256']
        assert path.stat().st_size < 0x80000000 and record['readback_verified']
    for name, expected in report['runtime_baselines'].items():
        if report['installed'] and name == 'EsteriaAppearance.dll':
            expected = t.p.load_json(t.STAGE / 'native-checks.json')['dll_sha256']
        assert t.p.sha256(t.p.CLIENT_DEFAULT / name) == expected
    print('PASS:', count, 'client/server tables preserve female and unrelated rows; source tracks/UVs;'
          ' catalogs; male/female Lua switching; reversible migration; archive readback receipts')
    t.save(t.WORK / 'reports/validation.json', {'passed': True, 'tables': count,
        'checks': ['female-and-unrelated-row-preservation', 'authored-animation-and-vertex-preservation',
                   'model-skin-palettes-weights', 'catalog-isolation', 'lua-controls-and-gender-switching',
                   'idempotent-reversible-migration', 'archive-stage-hashes'],
        'native_build_run': report['native_built'], 'server_build_run': report['server_built'],
        'installed': report['installed'], 'runtime_readback_passed': report.get('runtime_readback_passed', False),
        'live_accepted': False})


if __name__ == '__main__':
    check()
