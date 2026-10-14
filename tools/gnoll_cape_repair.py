"""Suspend Gnoll's cape from the upper back with the donor's animated cloth chain."""

import argparse
import copy
from pathlib import Path
import struct

import numpy as np
from wotlkconv.m2 import parse_m2, parse_skin, write_md20
from wotlkconv.m2.skin import write_skin

import creature_animation_repair as animation
import gnoll_cloak_landing_repair as archive_repair
import gnoll_equipment_repair as equipment
import gnoll_race_pack as g
import retroported_race_pack as p
from sethrak_equipment_repair import packed_skin

STAGE = Path('C:/Users/Zach/.codex/tmp/gnoll-shoulder-cape-v6')
PREVIOUS = Path('C:/Users/Zach/.codex/tmp/gnoll-shoulder-cape-v5')
DONORS = Path('C:/Users/Zach/.codex/tmp/gnoll-equipment-fit-v2/donors')


def prepare():
    STAGE.mkdir(parents=True, exist_ok=True)
    receipt = p.load_json(PREVIOUS / 'installed.json')
    assert all(p.sha256(p.CLIENT_DEFAULT / name) == digest for name, digest in receipt['after'].items())
    before_data = g.local(PREVIOUS / 'assets', g.MODEL).read_bytes()
    before_skin = g.local(PREVIOUS / 'assets', g.MODEL[:-3] + '00.skin').read_bytes()
    g.c.immutable(STAGE / 'before.m2', before_data)
    g.c.immutable(STAGE / 'before00.skin', before_skin)
    model, skin = parse_m2(before_data), parse_skin(before_skin)
    original = copy.deepcopy(model)
    previous_fit = p.load_json(PREVIOUS / 'changes.json')['suspended_cape']
    posed = animation.posed_vertices(original, animation.pose_matrices(original, 0, 0))
    donor = parse_m2((DONORS / 'worgen.m2').read_bytes())
    donor_skin = parse_skin((DONORS / 'worgen00.skin').read_bytes())
    fit, info = g.cape_rig(model, skin, donor, donor_skin)
    old_bones, new_bones = previous_fit['bones'], info['bones']
    assert old_bones == list(range(len(original.bones) - 3, len(original.bones)))
    model.bones[old_bones[0]:] = model.bones[len(original.bones):]
    remap = dict(zip(new_bones, old_bones, strict=True))
    for bone in model.bones[old_bones[0]:]:
        bone['parent_bone'] = remap.get(bone['parent_bone'], bone['parent_bone'])
    info['bones'] = old_bones
    vertices = bytearray(model.vertices)
    old_top = previous_fit['top']
    for geo in range(1502, 1507):
        target = {v for row in skin.submeshes if g.visual.u16(row, 0) == geo
                  for tri in g.triangles(skin, row) for v in tri}
        source = {v for row in donor_skin.submeshes if g.visual.u16(row, 0) == geo
                  for tri in g.triangles(donor_skin, row) for v in tri}
        high = max(struct.unpack_from('<f', donor.vertices, v * 48 + 8)[0] for v in source)
        for vertex in target:
            record = original.vertices[vertex * 48:(vertex + 1) * 48]
            _, y, z = posed[vertex]
            candidates = [v for v in source if donor.vertices[v * 48 + 32:(v + 1) * 48] == record[32:]]
            assert candidates
            source_index = min(candidates, key=lambda v:
                               (struct.unpack_from('<f', donor.vertices, v * 48 + 4)[0] * .72 - y) ** 2
                               + (old_top - (high - struct.unpack_from('<f', donor.vertices,
                                                                       v * 48 + 8)[0]) * .68 - z) ** 2)
            fitted = fit(donor.vertices[source_index * 48:(source_index + 1) * 48])
            for slot in range(4):
                if fitted[12 + slot]:
                    fitted[16 + slot] = remap.get(fitted[16 + slot], fitted[16 + slot])
            assert fitted[32:] == record[32:]
            vertices[vertex * 48:(vertex + 1) * 48] = fitted
    model.vertices = bytes(vertices)
    meshes = [{'row': row, 'geoset': g.visual.u16(row, 0), 'triangles': g.triangles(skin, row),
               'family': 'armor' if g.visual.u16(row, 0) == 1302 or 1502 <= g.visual.u16(row, 0) <= 1506 else 'body',
               'batches': [batch for batch in skin.batches if g.visual.u16(batch, 4) == index]}
              for index, row in enumerate(skin.submeshes)]
    packed = packed_skin(model, meshes)
    path = g.local(STAGE / 'assets', g.MODEL)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(write_md20(model))
    path.with_name(path.stem + '00.skin').write_bytes(write_skin(packed))
    protected = {name: p.sha256(p.CLIENT_DEFAULT / name) for name in
                 ('EsteriaAppearance.dll', 'EsteriaGnoll.bin', 'EsteriaGnollTextures.bin', 'Wow.exe',
                  str(p.GLOBAL_ARCHIVE_REL), str(p.LOCALE_ARCHIVE_REL))}
    g.save(STAGE / 'changes.json', {'suspended_cape': info, 'protected': protected})
    check()


def behind(points, triangles):
    """Signed rear-surface clearance; an interior/front point fails rather than looking 'close'."""
    a, b, c = (triangles[:, i] for i in range(3))
    determinant = (b[:, 2] - c[:, 2]) * (a[:, 1] - c[:, 1]) + (c[:, 1] - b[:, 1]) * (a[:, 2] - c[:, 2])
    valid = abs(determinant) > 1e-8
    minimum, checked = float('inf'), 0
    for point in points:
        u = np.divide((b[:, 2] - c[:, 2]) * (point[1] - c[:, 1])
                      + (c[:, 1] - b[:, 1]) * (point[2] - c[:, 2]), determinant,
                      out=np.zeros(len(a)), where=valid)
        v = np.divide((c[:, 2] - a[:, 2]) * (point[1] - c[:, 1])
                      + (a[:, 1] - c[:, 1]) * (point[2] - c[:, 2]), determinant,
                      out=np.zeros(len(a)), where=valid)
        hits = valid & (u >= 0) & (v >= 0) & (u + v <= 1)
        if hits.any():
            rear = (u * a[:, 0] + v * b[:, 0] + (1 - u - v) * c[:, 0])[hits].min()
            minimum = min(minimum, rear - point[0])
            checked += 1
    return minimum, checked


def check():
    from collections import Counter
    import sethrak_animation_pack as checks
    data = g.local(STAGE / 'assets', g.MODEL).read_bytes()
    model, skin = parse_m2(data), parse_skin(g.local(STAGE / 'assets', g.MODEL[:-3] + '00.skin').read_bytes())
    before, old_skin = parse_m2((STAGE / 'before.m2').read_bytes()), parse_skin((STAGE / 'before00.skin').read_bytes())
    info = p.load_json(STAGE / 'changes.json')['suspended_cape']
    checks.check_model(model, data)
    assert model.sequences == before.sequences
    assert [{k: v for k, v in a.items() if k != 'animate_attached'} for a in model.attachments] == [
        {k: v for k, v in a.items() if k != 'animate_attached'} for a in before.attachments]
    existing = info['bones'][0]
    assert [{k: v for k, v in b.items() if k not in ('rotation', 'translation', 'scale')}
            for b in model.bones[:existing]] == [
        {k: v for k, v in b.items() if k not in ('rotation', 'translation', 'scale')}
        for b in before.bones[:existing]]
    for index in info['bones']:
        old_bone, new_bone = before.bones[index], model.bones[index]
        assert {k: v for k, v in old_bone.items() if k not in ('rotation', 'translation', 'scale')} == {
            k: v for k, v in new_bone.items() if k not in ('rotation', 'translation', 'scale')}
        for name in ('rotation', 'translation', 'scale'):
            old, new = old_bone[name], new_bone[name]
            assert old.timestamps == new.timestamps and old.values == new.values, 'Cloth motion changed'
            assert old.interpolation == new.interpolation and old.global_sequence == new.global_sequence
    retained = copy.deepcopy(model)
    retained.bones = model.bones[:existing] + before.bones[existing:]
    checks.tracks_equal(before, retained, len(before.sequences))
    assert all(g.visual.u16(row, 12) <= 75 for row in skin.submeshes)

    def surfaces(m, k, cape=False):
        return Counter((g.visual.u16(row, 0), tuple(m.vertices[v * 48:(v + 1) * 48] for v in tri))
                       for row in k.submeshes if (1502 <= g.visual.u16(row, 0) <= 1506) == cape
                       for tri in g.triangles(k, row))
    assert surfaces(model, skin) == surfaces(before, old_skin), 'Other equipment or anatomy changed'
    cape_faces = [tri for row in skin.submeshes if 1502 <= g.visual.u16(row, 0) <= 1506
                  for tri in g.triangles(skin, row)]
    cape = sorted({v for tri in cape_faces for v in tri})
    def cape_uvs(m, k):
        return Counter((g.visual.u16(row, 0), tuple(m.vertices[v * 48 + 32:(v + 1) * 48] for v in tri))
                       for row in k.submeshes if 1502 <= g.visual.u16(row, 0) <= 1506
                       for tri in g.triangles(k, row))
    assert cape_uvs(model, skin) == cape_uvs(before, old_skin)
    assert len(model.bones) == len(before.bones)
    for vertex in cape:
        record = model.vertices[vertex * 48:(vertex + 1) * 48]
        assert sum(record[12:16]) == 255
        assert {record[16 + s] for s in range(4) if record[12 + s]} <= {info['parent'], *info['bones']}
    body = np.array(g.cape_body_triangles(model, skin))
    minimum = float('inf')
    reference = animation.posed_vertices(model, animation.pose_matrices(model, 0, 0))
    upper = np.concatenate((reference[cape, 2], reference[np.array(cape_faces), 2].mean(axis=1))) > info['top'] - .40
    actions = [(action, animation.sequence(model, action)) for action in (0, 5, 37, 38, 39, 185, 186, 187)]
    actions += [(0, index) for index, q in enumerate(model.sequences) if q['id'] == 0 and q['variation_index']]
    for action, sequence_index in actions:
        duration = model.sequences[sequence_index]['duration']
        for fraction in (0, .25, .5, .75):
            posed = animation.posed_vertices(model, animation.pose_matrices(
                model, action, duration * fraction, sequence_index))
            samples = np.concatenate((posed[cape], posed[np.array(cape_faces)].mean(axis=1)))
            clearance, count = behind(samples, posed[body])
            upper_clearance, _ = behind(samples[upper], posed[body])
            lower_clearance, _ = behind(samples[~upper], posed[body])
            assert count > 50 and upper_clearance > .008 and lower_clearance > .015, (
                action, sequence_index, fraction, upper_clearance, lower_clearance, count)
            minimum = min(minimum, clearance)
    for index in info['bones']:
        bone = model.bones[index]
        assert any(len(set(slot)) > 1 for slot in bone['rotation'].values), 'Cape has no independent flutter'
    for row in skin.submeshes:
        start, count, offset = g.visual.u16(row, 8), g.visual.u16(row, 10), g.visual.u16(row, 14)
        for index in skin.indices[start:start + count]:
            vertex = skin.vertices[index]
            for slot in range(4):
                if model.vertices[vertex * 48 + 12 + slot]:
                    local = skin.bones[index * 4 + slot]
                    assert local < g.visual.u16(row, 12)
                    assert model.bone_combos[offset + local] == model.vertices[vertex * 48 + 16 + slot]
    print(f'PASS all cape lengths outside the body in {len(actions) * 4} idle/run/jump poses '
          f'(min clearance {minimum:.4f}); '
          'three animated shoulder-rooted cloth bones; other equipment, creator and landing retained')


def stage():
    archive_repair.STAGE = STAGE
    archive_repair.stage(validate=check, include_creator=False)


def install():
    equipment.STAGE = STAGE
    equipment.install(validate=check)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare', 'check', 'stage', 'install'))
    globals()[parser.parse_args().action]()
