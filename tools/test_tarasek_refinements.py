"""Validate the follow-up against the actually installed Tarasek baseline."""

import copy
from pathlib import Path
import struct

import tarasek_refinements as r
import numpy as np
from lupa.lua51 import LuaRuntime
from wotlkconv.blp import Blp
from wotlkconv.m2 import parse_m2, parse_skin

import sethrak_animation_pack as animation


def models():
    old = parse_m2((r.BASE / r.t.MODEL).read_bytes())
    blob = (r.STAGE / 'assets' / r.t.MODEL).read_bytes()
    new = parse_m2(blob)
    animation.check_model(new, blob)
    assert old.vertices == new.vertices and old.sequences == new.sequences
    assert old.key_bone_lookup == new.key_bone_lookup
    expected = copy.deepcopy(old)
    before_matrices = r.motion.pose_matrices(old, 0, 0)
    after_matrices = r.motion.pose_matrices(new, 0, 0)
    moved = []
    for a, b in zip(old.attachments, new.attachments, strict=True):
        assert a['id'] == b['id'] and a['bone'] == b['bone']
        if a['id'] in (5, 6):
            track = b['animate_attached']
            assert track.global_sequence == -1 and track.timestamps == [[0]] * 179
            assert track.values == [[1]] * 179
            next(x for x in expected.attachments if x['id'] == a['id'])['animate_attached'] = copy.deepcopy(track)
        if a['id'] in (26, 27, 28, 30, 31):
            first = before_matrices[a['bone']] @ np.array([*a['position'], 1])
            last = after_matrices[b['bone']] @ np.array([*b['position'], 1])
            assert np.allclose(last - first, (0, 0, -.3, 0), atol=1e-6)
            moved.append(a['id'])
        else:
            assert a['position'] == b['position']
    assert moved == [26, 27, 28, 30, 31]
    animation.tracks_equal(expected, new, 179)
    before = parse_skin((r.BASE / r.t.MODEL).with_name('tarasek00.skin').read_bytes())
    after = parse_skin((r.STAGE / 'assets' / r.t.MODEL).with_name('tarasek00.skin').read_bytes())
    assert before.vertices == after.vertices and before.indices == after.indices
    assert before.submeshes == after.submeshes
    changed = 0
    for a, b in zip(before.batches, after.batches, strict=True):
        combo = struct.unpack_from('<H', a, 16)[0]
        if old.textures[old.texture_combos[combo]]['type'] == 11:
            assert struct.unpack_from('<H', b, 14)[0] == 1
            material = new.materials[struct.unpack_from('<H', b, 10)[0]]
            assert material['blending_mode'] == 0 and not (material['flags'] & 1)
            changed += 1
        else:
            assert a == b
    assert changed == 7


def catalogs():
    old = (r.BASE / 'EsteriaAppearance.bin').read_bytes()
    new = (r.STAGE / 'EsteriaAppearance.bin').read_bytes()
    assert old[:12] == new[:12] and len(old) == len(new)
    changed = []
    for start in range(12, len(old), 2316):
        before, after = old[start:start + 2316], new[start:start + 2316]
        if before != after:
            assert struct.unpack_from('<2I', before) == (66, 0)
            expected = bytearray(before)
            struct.pack_into('<I', expected, 12 + 3 * 144 + 4, 7)
            assert after == bytes(expected)
            changed.append(start)
    assert len(changed) == 1
    raw = (r.STAGE / 'EsteriaTarasek.bin').read_bytes()
    count = struct.unpack_from('<I', raw, 8)[0]
    records = [raw[12 + i * 156:12 + (i + 1) * 156] for i in range(count)]
    materials = [row for row in records if struct.unpack_from('<3I', row) == (0, 1, 11)]
    assert len(materials) == 42
    for skin in range(6):
        for eye in range(7):
            rows = [row for row in materials if struct.unpack_from('<3I', row, 16) ==
                    (skin << 16, 3 | eye << 16, 0xffffffff)]
            assert len(rows) == 1
            path = rows[0][28:].split(b'\0')[0].decode()
            assert (r.STAGE / 'assets' / path).exists() if eye else (r.BASE / path).exists()
    hidden = {struct.unpack_from('<I', row, 8)[0] for row in records
              if struct.unpack_from('<I', row, 4)[0] == 4}
    assert 45684 not in hidden and 14957 in hidden
    native = r.t.p.load_json(r.STAGE / 'native-checks.json')
    assert native['all_passed']
    for name, digest in native['catalogs'].items():
        assert r.t.p.sha256(r.STAGE / name) == digest, name


def textures():
    report = r.t.p.load_json(r.WORK / 'eyes.json')
    assert tuple(report['options']) == r.EYES and len(report['textures']) == 36
    for path, info in report['textures'].items():
        target = r.STAGE / 'assets' / path
        assert r.t.p.sha256(target) == info['sha256']
        original_path = path.split('_eyes_')[0] + '.blp'
        before = Blp.parse((r.BASE / original_path).read_bytes())
        after = Blp.parse(target.read_bytes())
        assert len(before.mips) == len(after.mips) == 10
        first, last = before.decode_level(), after.decode_level()
        a = np.frombuffer(first.data, dtype='u1').reshape((512, 512, 4))
        b = np.frombuffer(last.data, dtype='u1').reshape((512, 512, 4))
        assert np.array_equal(a[:, :, 3], b[:, :, 3])
        ys, xs = np.where(np.any(a[:, :, :3] != b[:, :, :3], axis=2))
        assert 50 <= len(xs) <= 500 and xs.min() >= 10 and xs.max() <= 25
        assert ys.min() >= 169 and ys.max() <= 197
        for level in range(4, 10):
            assert before.decode_level(level).data == after.decode_level(level).data


def lua():
    text = (r.STAGE / 'assets/Interface/GlueXML/CharacterCreate.lua').read_text()
    runtime = LuaRuntime()
    runtime.eval('function(s) assert(loadstring(s)); end')(text)
    start = text.index('        if CharacterCreate.selectedRaceID == 66 and GetSelectedSex()')
    block = text[start:text.index('        if CharacterCreate.selectedRaceID == 65', start)]
    runtime.execute('''
        SEX_MALE=2; SEX_FEMALE=3; selectedSex=2; CharacterCreate={selectedRaceID=66};
        function GetSelectedSex() return selectedSex; end
        for i=1,5 do
            _G['CharacterCustomizationButtonFrame'..i]={Hide=function(s) s.hidden=true; end,
                Show=function(s) s.hidden=false; end};
            _G['CharacterCustomizationButtonFrame'..i..'Text']={SetText=function(s,v) s.text=v; end};
        end
    ''')
    runtime.execute('function layout() ' + block + ' end')
    runtime.execute('''
        layout(); assert(not CharacterCustomizationButtonFrame3.hidden);
        assert(not CharacterCustomizationButtonFrame4.hidden);
        assert(CharacterCustomizationButtonFrame3Text.text=='Horns');
        assert(CharacterCustomizationButtonFrame4Text.text=='Eye Color');
        selectedSex=SEX_FEMALE; layout();
        assert(CharacterCustomizationButtonFrame3.hidden);
        assert(not CharacterCustomizationButtonFrame4.hidden);
    ''')
    begin = text.index('local function ChoiceText(')
    end = text.index('local function PickerSignature()', begin)
    runtime.execute(text[begin:end] + '\nchoice=ChoiceText;')
    runtime.execute('selectedSex=SEX_MALE;')
    assert [runtime.globals().choice(4, i, 'Eye Color') for i in range(7)] == [x.title() for x in r.EYES]
    runtime.execute('selectedSex=SEX_FEMALE;')
    assert runtime.globals().choice(4, 0, 'Eye Color') == 'Eye Color 1'


if __name__ == '__main__':
    models()
    catalogs()
    textures()
    lua()
    r.t.save(r.STAGE / 'validation.json', {'passed': True,
        'source_files': {str(path): r.t.p.sha256(path) for path in (
            Path(__file__), Path('tools/tarasek_refinements.py'),
            Path('src/server/shared/CreatureAppearance.h'), Path('data/retroported-races/drakkin_alliance.json'))},
        'checks': ['all-179-authored-sequences-and-bone-tracks', 'shoulder-visibility-all-actions',
                   'five-back-sockets-common-offset', 'seven-lit-diffuse-batches',
                   '42-eye-combinations-and-iris-only-pixels', 'female-and-unrelated-profile-preservation',
                   'Lightbringer-closed-helm-removal', 'creator-layout-and-eye-names'],
        'live_accepted': False})
    print('PASS: authored motion, permanent shoulders, all back sockets, diffuse skin, 42 eye combinations, '
          'iris-only pixels, female/unrelated profiles, helmet hides and male/female creator controls')
