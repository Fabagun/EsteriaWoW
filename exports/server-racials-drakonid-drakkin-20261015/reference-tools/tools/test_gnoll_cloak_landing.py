"""Check Gnoll cloak attachment through authored poses, touchdown aliases and creator refreshes."""

import struct

from lupa import LuaRuntime
import numpy as np
from wotlkconv.m2 import parse_m2, parse_skin

import creature_animation_repair as animation
import gnoll_cloak_landing_repair as repair
import gnoll_equipment_repair as equipment
import gnoll_race_pack as g
from sethrak_equipment_repair import check_landing


def pose(model, action, time):
    return animation.posed_vertices(model, animation.pose_matrices(model, action, time))


def surface_distance(point, triangles):
    a, b, c = (triangles[:, i] for i in range(3))
    ab, ac, ap = b - a, c - a, point - a
    dot = lambda x, y: np.einsum('ij,ij->i', x, y)
    aa, bb, cc, d, e = dot(ab, ab), dot(ab, ac), dot(ac, ac), dot(ab, ap), dot(ac, ap)
    determinant = aa * cc - bb * bb
    valid = determinant > 1e-12
    u = np.divide(cc * d - bb * e, determinant, out=np.zeros_like(d), where=valid)
    v = np.divide(aa * e - bb * d, determinant, out=np.zeros_like(e), where=valid)
    inside = valid & (u >= 0) & (v >= 0) & (u + v <= 1)
    distances = [np.linalg.norm((a + u[:, None] * ab + v[:, None] * ac)[inside] - point, axis=1)]
    for start, end in ((a, b), (b, c), (c, a)):
        edge = end - start
        amount = np.clip(np.divide(dot(point - start, edge), dot(edge, edge),
                                   out=np.zeros(len(start)), where=dot(edge, edge) > 1e-12), 0, 1)
        distances.append(np.linalg.norm(start + amount[:, None] * edge - point, axis=1))
    return min(float(values.min()) for values in distances if len(values))


def check():
    root = repair.STAGE
    model = parse_m2(g.local(root / 'assets', g.MODEL).read_bytes())
    skin = parse_skin(g.local(root / 'assets', g.MODEL[:-3] + '00.skin').read_bytes())
    before = parse_m2((root / 'before.m2').read_bytes())
    check_landing(before, model)
    cape = {v for row in skin.submeshes if 1502 <= g.visual.u16(row, 0) <= 1506
            for tri in g.triangles(skin, row) for v in tri}
    assert model.vertex_count == before.vertex_count
    for vertex in range(model.vertex_count):
        old, new = before.vertices[vertex * 48:(vertex + 1) * 48], model.vertices[vertex * 48:(vertex + 1) * 48]
        assert (old[32:] == new[32:] if vertex in cape else old == new)
    for vertex in cape:
        record = model.vertices[vertex * 48:(vertex + 1) * 48]
        assert sum(record[12:16]) == 255
        if struct.unpack_from('<f', record, 8)[0] < 1.0:
            assert record[12:17] == bytes((255, 0, 0, 0, model.key_bone_lookup[51]))
    source_skin = parse_skin((g.ROOT / 'converted/gnoll200.skin').read_bytes())
    torso = {model.key_bone_lookup[k] for k in (4, 48, 51, 53)}
    rear = []
    for row in source_skin.submeshes:
        if g.visual.u16(row, 0) not in (0, 701, 801):
            continue
        for tri in g.triangles(source_skin, row):
            records = [model.vertices[v * 48:(v + 1) * 48] for v in tri]
            if sum(r[12 + s] for r in records for s in range(4) if r[16 + s] in torso) >= 540:
                rear.append(tri)
    upper = [v for v in cape if struct.unpack_from('<f', model.vertices, v * 48 + 8)[0] > 1.08
             and abs(struct.unpack_from('<f', model.vertices, v * 48 + 4)[0]) < .18]
    assert len(upper) >= 40
    maximum = 0
    for action in (0, 5, 37, 38, 39):
        duration = model.sequences[animation.sequence(model, action)]['duration']
        for fraction in (0, .25, .5, .75):
            points = pose(model, action, duration * fraction)
            distances = [surface_distance(points[v], points[np.array(rear)]) for v in upper]
            maximum = max(maximum, max(distances))
            assert max(distances) < .095, (action, fraction, max(distances))
    lua = LuaRuntime()
    lua.execute('''
SEX_MALE=0; SEX_FEMALE=1; strupper=string.upper; sex=1; token="GnollHorde";
CharacterCreate={selectedRaceID=2};
CharacterCreateGenderButtonFemale={shown=true, enabled=true};
function CharacterCreateGenderButtonFemale:Show() self.shown=true; end
function CharacterCreateGenderButtonFemale:Hide() self.shown=false; end
function CharacterCreateGenderButtonFemale:Enable() self.enabled=true; end
function CharacterCreateGenderButtonFemale:Disable() self.enabled=false; end
function GetSelectedSex() return sex; end
function GetNameForRace() return "Gnoll",token; end
function SetCharacterGender(value) sex=value; CharacterCreate_UpdateButtonCheckedStates(); end
function CharacterCreate_UpdateButtonCheckedStates() CharacterCreateGenderButtonFemale:Show(); end
function CharacterCreate_ResetState() CharacterCreateGenderButtonFemale:Show(); end
''')
    text = (root / 'CharacterCreate.lua').read_text()
    assert 'or target.raceID == 63) then' in text
    lua.execute(text[text.index('-- Gnoll has one authored playable body;'):])
    for refresh in ('CharacterCreate_UpdateButtonCheckedStates()', 'CharacterCreate_ResetState()'):
        lua.execute('sex=1; token="GnollHorde"; ' + refresh)
        assert lua.eval('sex==SEX_MALE and not CharacterCreateGenderButtonFemale.shown '
                        'and not CharacterCreateGenderButtonFemale.enabled')
        lua.execute('sex=1; token="SethrakAlliance"; ' + refresh)
        assert lua.eval('sex==SEX_FEMALE and CharacterCreateGenderButtonFemale.shown '
                        'and CharacterCreateGenderButtonFemale.enabled')
    equipment.STAGE = root
    from test_gnoll_equipment import check as check_equipment
    check_equipment()
    print(f'PASS cape upper clearance through 20 stand/run/jump poses (max {maximum:.4f}); '
          'run landing, unchanged other equipment and male-only creator refreshes')


if __name__ == '__main__':
    check()
