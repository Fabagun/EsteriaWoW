"""Check Saberon anatomy, armor selectors, palettes, native outfits and attachment frames."""

from collections import Counter
import copy
import hashlib
import math
import struct

from wotlkconv.m2 import parse_m2, parse_skin
import saberon_equipment_pack as gear
import saberon_race_pack as s
import retroported_race_pack as p
import sethrak_equipment_repair as e
import sethrak_animation_pack as a


def check():
    if (gear.STAGE / 'fit-report.json').exists():
        from test_saberon_equipment_fit import check as check_fit
        check_fit()
        return
    data = s.local(gear.STAGE / 'assets', s.MODEL).read_bytes()
    model = parse_m2(data)
    skin = parse_skin(s.local(gear.STAGE / 'assets', gear.SKIN).read_bytes())
    original = parse_m2((gear.STAGE / 'before.m2').read_bytes())
    before = parse_skin((gear.STAGE / 'before.skin').read_bytes())
    a.check_model(model, data)
    assert model.sequences == original.sequences
    assert model.global_loops == original.global_loops

    def track_equal(old, new):
        for name in ('kind', 'interpolation', 'global_sequence', 'timestamps', 'external'):
            assert getattr(old, name, None) == getattr(new, name, None), name
        if hasattr(old, 'values'):
            assert old.values == new.values

    for old, new in zip(original.bones, model.bones[:len(original.bones)], strict=True):
        for name in old:
            if name in ('rotation', 'translation', 'scale'):
                track_equal(old[name], new[name])
            else:
                assert old[name] == new[name], name
    for old, new in zip(original.events, model.events, strict=True):
        for name in old:
            if name == 'enabled':
                track_equal(old[name], new[name])
            else:
                assert old[name] == new[name], name
    assert model.materials[:len(original.materials)] == original.materials
    assert model.textures[:len(original.textures)] == original.textures
    assert model.vertex_count < 65536 and len(skin.vertices) < 65536
    assert len(skin.indices) == 79728 and len(model.bones) == 119

    def surfaces(m, k, predicate):
        return Counter(tuple(m.vertices[v * 48:v * 48 + 32] for v in tri)
                       for row in k.submeshes if predicate(s.visual.u16(row, 0))
                       for tri in e.mesh_triangles(k, row))

    native = surfaces(original, before, lambda geo: True)
    after = surfaces(model, skin, lambda geo: geo == 0 or geo >= 3000)
    assert not native - after, 'Original anatomy or native outfit surfaces were removed'
    body = surfaces(original, before, lambda geo: geo == 0)
    assert not body - surfaces(model, skin, lambda geo: geo == 0), 'Equipment can remove underlying anatomy'
    ids = {s.visual.u16(row, 0) for row in skin.submeshes}
    assert {402, 403, 404, 502, 503, 504, 505, 802, 803, 902, 903, 1002, 1102, 1104,
            1202, 1302, 1502, 1503, 1504, 1505, 1506, 1802} <= ids
    assert set(range(21001, 21010)) <= ids
    assert model.attachment_lookup[11] == 65535
    shield = model.attachments[model.attachment_lookup[0]]
    forearm = model.bones[model.bones[model.key_bone_lookup[13]]['parent_bone']]['parent_bone']
    assert model.bones[shield['bone']]['parent_bone'] == forearm
    for row in skin.submeshes:
        start = s.visual.u16(row, 8) | s.visual.u16(row, 2) << 16
        count, palette, offset = (s.visual.u16(row, n) for n in (10, 12, 14))
        assert start + count <= len(skin.indices) and palette <= 75
        for index in skin.indices[start:start + count]:
            vertex = skin.vertices[index]
            for slot in range(4):
                if model.vertices[vertex * 48 + 12 + slot]:
                    local = skin.bones[index * 4 + slot]
                    assert local < palette
                    assert model.bone_combos[offset + local] == model.vertices[vertex * 48 + 16 + slot]
    assert not s.normalize_materials(copy.deepcopy(model), copy.deepcopy(skin)), 'Dark multiply passes returned'
    for values in (struct.unpack_from('<2f', model.vertices, i * 48 + 32) for i in range(model.vertex_count)):
        assert all(math.isfinite(v) for v in values)
    bank = (gear.STAGE / 'EsteriaSaberonTextures.bin').read_bytes()
    magic, version, count, sha = struct.unpack_from('<4I', bank)
    assert (magic, version, count) == (0x31544845, 1, 4)
    assert sha == int.from_bytes(hashlib.sha256(bank[16:]).digest()[:4], 'little')
    catalog = (gear.STAGE / 'EsteriaSaberon.bin').read_bytes()
    records = [struct.unpack_from('<7I', catalog, at) for at in range(12, len(catalog), 156)]
    assert len(records) == 33
    for color in range(4):
        selected = [r for r in records if r[1] == 3 and r[4] == color << 16]
        assert len(selected) == 1 and selected[0][2] == 0
        assert struct.unpack_from('<2I', bank, selected[0][3]) == (512, 512)
    for style in range(1, 10):
        selected = [r for r in records if r[1] == 2 and r[4] == 1 | style << 16]
        assert len(selected) == 1 and selected[0][2:4] == (3100 + style, 21000 + style)
    print('PASS all original anatomy/rig/animations/lighting, 22 armor geosets, four fur atlases,')
    print('nine native outfits, bone palettes, dark-tint guard and forearm shield attachment')


if __name__ == '__main__':
    check()
