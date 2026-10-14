"""Check Gnoll anatomy with equipment selectors disabled, cloth fit and semantic wrist attachment."""

import math
import struct

from wotlkconv.m2 import parse_m2, parse_skin

import gnoll_equipment_repair as repair
import gnoll_race_pack as g
import sethrak_animation_pack as animation
from sethrak_equipment_repair import descendants


def check():
    root = repair.STAGE
    model_path = g.local(root / 'assets', g.MODEL)
    data = model_path.read_bytes()
    model = parse_m2(data)
    skin = parse_skin(model_path.with_name(model_path.stem + '00.skin').read_bytes())
    original = parse_m2((root / 'animated.m2').read_bytes())
    source = parse_skin((g.ROOT / 'converted/gnoll200.skin').read_bytes())
    animation.check_model(model, data)
    assert model.vertex_count < 65536 and len(skin.vertices) < 65536
    assert all(g.visual.u16(r, 12) <= 75 for r in skin.submeshes)

    def surface(m, k, predicate):
        return {tuple(m.vertices[v * 48:v * 48 + 32] for v in tri)
                for row in k.submeshes if predicate(g.visual.u16(row, 0)) for tri in g.triangles(k, row)}

    assert surface(original, source, lambda geo: True) <= surface(model, skin, lambda geo: True)
    hands = descendants(original, original.bones[original.key_bone_lookup[8]]['parent_bone'])
    hands |= descendants(original, original.bones[original.key_bone_lookup[13]]['parent_bone'])
    legs = descendants(original, original.key_bone_lookup[55]) | descendants(original, original.key_bone_lookup[56])
    expected = set()
    for row in source.submeshes:
        geo = g.visual.u16(row, 0)
        for tri in g.triangles(source, row):
            body = geo in (701, 801, 1001)
            body |= geo == 0 and sum(original.vertices[v * 48 + 12 + s] for v in tri for s in range(4)
                                    if original.vertices[v * 48 + 16 + s] in hands | legs) >= 300
            if body:
                expected.add(tuple(original.vertices[v * 48:v * 48 + 32] for v in tri))
    assert expected <= surface(model, skin, lambda geo: geo == 0), 'Gloves, pants or boots can still remove anatomy'
    ids = {g.visual.u16(row, 0) for row in skin.submeshes}
    assert {1302, 1502, 1503, 1504, 1505, 1506} <= ids
    assert not {401, 402, 403, 404, 502, 503, 504, 505, 1301, 902, 903, 1102, 1104, 1801, 1802} & ids
    for geo in (1302, 1502, 1503, 1504, 1505, 1506):
        used = {v for row in skin.submeshes if g.visual.u16(row, 0) == geo
                for tri in g.triangles(skin, row) for v in tri}
        points = [struct.unpack_from('<3f', model.vertices, v * 48) for v in used]
        zlow, zhigh = min(p[2] for p in points), max(p[2] for p in points)
        if geo == 1302:
            assert len(used) >= 100 and abs(zhigh - 1.01) < .001 and zlow < .2
        else:
            top = max(model.bones[model.key_bone_lookup[k]]['pivot'][2] for k in (2, 3)) + .075
            assert len(used) > 40 and abs(zhigh - top) < .001 and zhigh - zlow > .45
    arms = descendants(original, original.key_bone_lookup[0]) | descendants(original, original.key_bone_lookup[1])
    player_rows = [r for i, r in enumerate(skin.submeshes) if any(
        model.textures[model.texture_combos[g.visual.u16(b, 16)]]['type'] in (1, 14)
        for b in skin.batches if g.visual.u16(b, 4) == i)]
    for row in player_rows:
        for tri in g.triangles(skin, row):
            arm = sum(model.vertices[v * 48 + 12 + s] for v in tri for s in range(4)
                      if model.vertices[v * 48 + 16 + s] in arms) >= 300
            if arm:
                assert all(struct.unpack_from('<f', model.vertices, v * 48 + 32)[0] <= .5 for v in tri)
    for identifier in (5, 6):
        anchor = model.attachments[model.attachment_lookup[identifier]]
        assert all(not values or all(abs(value - 1.05) < .00001 for value in values[0])
                   for values in model.bones[anchor['bone']]['scale'].values)
    shield = model.attachments[model.attachment_lookup[0]]
    forearm = model.bones[model.bones[model.key_bone_lookup[13]]['parent_bone']]['parent_bone']
    assert model.bones[shield['bone']]['parent_bone'] == forearm, 'Shield is still following a shoulder'
    assert math.dist(shield['position'], model.bones[model.key_bone_lookup[13]]['pivot']) < .16
    for row in skin.submeshes:
        start = g.visual.u16(row, 8) | g.visual.u16(row, 2) << 16
        count, offset = g.visual.u16(row, 10), g.visual.u16(row, 14)
        for i in skin.indices[start:start + count]:
            vertex = skin.vertices[i]
            for slot in range(4):
                if model.vertices[vertex * 48 + 12 + slot]:
                    local = skin.bones[i * 4 + slot]
                    assert local < g.visual.u16(row, 12)
                    assert model.bone_combos[offset + local] == model.vertices[vertex * 48 + 16 + slot]
    if (root / 'before.m2').exists():
        from sethrak_equipment_repair import check_landing
        check_landing(parse_m2((root / 'before.m2').read_bytes()), model)
    else:
        assert model.sequences == original.sequences
    print('PASS Gnoll anatomy, arm/leg atlas separation, no loose donor pieces or floating belt ring, '
          'close cape fit, 30-percent shoulder reduction and forearm shield anchor', flush=True)


if __name__ == '__main__':
    check()
