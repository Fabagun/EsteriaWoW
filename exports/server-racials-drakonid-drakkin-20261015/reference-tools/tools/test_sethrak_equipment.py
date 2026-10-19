"""Check the staged Sethrak landing graph, player garment surfaces and skinning mappings."""

import hashlib
import copy
import math
import struct

from wotlkconv.m2 import parse_m2, parse_skin

import sethrak_equipment_repair as repair
from sethrak_body_regions import collar_height, mirrored_u, waist_height


def check():
    manifest = repair.race.p.load_manifest('sethrak')
    required = {0, 402, 403, 404, 802, 803,
                1002, 1202, 1302, 1502, 1503, 1504, 1505, 1506, 1801, 1802}
    for sex, info in manifest['models'].items():
        original = parse_m2((repair.STAGE / 'before' / (sex + '.m2')).read_bytes())
        path = repair.race.animations.local(repair.STAGE / 'assets', info['model_path'])
        data = path.read_bytes()
        model = parse_m2(data)
        skin = parse_skin(path.with_name(path.stem + '00.skin').read_bytes())
        motion_before, motion_after = copy.deepcopy(original), copy.deepcopy(model)
        motion_before.attachments = motion_after.attachments = []
        motion_after.bones = motion_after.bones[:len(original.bones)]
        repair.check_landing(motion_before, motion_after)
        repair.race.animations.check_model(model, data)
        assert model.num_skin_profiles == 1
        assert sum(texture['type'] == 2 for texture in model.textures) == 1
        assert len(skin.indices) < 65536 and len(skin.vertices) < 65536
        assert required <= {repair.race.visual.u16(row, 0) for row in skin.submeshes}
        assert len(model.bones) == len(original.bones) + 4
        assert all((a['parent_bone'], a['pivot'], a['bone_name_crc']) ==
                   (b['parent_bone'], b['pivot'], b['bone_name_crc'])
                   for a, b in zip(original.bones, model.bones[:len(original.bones)], strict=True))
        for attachment in (0, 5, 6, 28):
            index = model.attachment_lookup[attachment]
            assert model.attachments[index]['id'] == attachment
            assert model.attachments[index]['animate_attached'].values == [[1]] * len(model.sequences)
        human = parse_m2((repair.STAGE / 'donors' / ('human-' + sex + '.m2')).read_bytes())
        for identifier in (5, 6):
            source = next(a for a in human.attachments if a['id'] == identifier)
            actual = model.attachments[model.attachment_lookup[identifier]]
            expected = next((slot[0] for slot in human.bones[source['bone']]['scale'].values if slot), (1, 1, 1))
            values = model.bones[actual['bone']]['scale'].values
            assert all(not slot if expected == (1, 1, 1) else
                       all(math.isclose(x, y, abs_tol=0.00001) for x, y in zip(slot[0], expected)) for slot in values)
        belt_vertices = {v for row in skin.submeshes if repair.race.visual.u16(row, 0) == 1801
                         for tri in repair.mesh_triangles(skin, row) for v in tri}
        belt_heights = sorted(struct.unpack_from('<f', model.vertices, v * 48 + 8)[0] for v in belt_vertices)
        assert abs(belt_heights[len(belt_heights) // 2] - waist_height(model)) < 0.07
        assert not {902, 903, 1102, 1104} & {repair.race.visual.u16(row, 0) for row in skin.submeshes}
        torso_vertices = {v for i, row in enumerate(skin.submeshes) if repair.race.visual.u16(row, 0) == 0
                          and any(model.textures[model.texture_combos[repair.race.visual.u16(b, 16)]]['type'] == 1
                                  for b in skin.batches if repair.race.visual.u16(b, 4) == i)
                          for tri in repair.mesh_triangles(skin, row) for v in tri}
        center = model.bones[model.bones[model.key_bone_lookup[55]]['parent_bone']]['pivot']
        checked = 0
        for v in torso_vertices:
            x, y, z = struct.unpack_from('<3f', model.vertices, v * 48)
            if abs(y) < 0.03 and waist_height(model) + 0.06 < z < 1.50:
                u = struct.unpack_from('<f', model.vertices, v * 48 + 32)[0]
                assert abs(u - mirrored_u(math.atan2(y, x - center[0]))) < 0.00001
                checked += 1
        assert checked, 'No center-front/back clothing UVs verified'
        back_collar = max(model.bones[model.key_bone_lookup[k]]['pivot'][2] for k in (0, 1)) + 0.02
        front_vertices = [v for v in torso_vertices
                          if struct.unpack_from('<f', model.vertices, v * 48)[0] > 0.05
                          and abs(struct.unpack_from('<f', model.vertices, v * 48 + 4)[0]) < 0.07]
        assert max(struct.unpack_from('<f', model.vertices, v * 48 + 8)[0] for v in front_vertices) > 1.8
        assert collar_height(model, (0.10, 0, 1.8), back_collar) > back_collar + 0.20
        rear_collar = collar_height(model, (-0.15, 0, 1.8), back_collar)
        assert rear_collar == model.bones[model.key_bone_lookup[49]]['pivot'][2] + 0.075
        assert rear_collar < model.bones[model.key_bone_lookup[50]]['pivot'][2] - 0.1
        expanded = 0
        for v in torso_vertices:
            x, y, z = struct.unpack_from('<3f', model.vertices, v * 48)
            if 1.80 < z < 1.94 and x > 0.03 and 0.025 < abs(y) < 0.12:
                u = struct.unpack_from('<f', model.vertices, v * 48 + 32)[0]
                assert u < mirrored_u(math.atan2(y, x - center[0])), 'Front neck wrap is still compressed'
                expanded += 1
        assert expanded >= 4
        base_visible = {v for row in skin.submeshes if repair.race.visual.u16(row, 0) == 0
                        for tri in repair.mesh_triangles(skin, row) for v in tri}
        hands = repair.descendants(model, model.bones[model.key_bone_lookup[8]]['parent_bone'])
        hands |= repair.descendants(model, model.bones[model.key_bone_lookup[13]]['parent_bone'])
        feet = repair.descendants(model, model.key_bone_lookup[59])
        feet |= repair.descendants(model, model.key_bone_lookup[60])
        legs = repair.descendants(model, model.key_bone_lookup[55])
        legs |= repair.descendants(model, model.key_bone_lookup[56])
        source_skin = parse_skin((repair.STAGE / 'before' / (sex + '00.skin')).read_bytes())
        original_body = {v for i, row in enumerate(source_skin.submeshes)
                         if any(original.textures[original.texture_combos[repair.race.visual.u16(b, 16)]]['type'] == 11
                                or 'snakeloa_1_body' in original.textures[
                                    original.texture_combos[repair.race.visual.u16(b, 16)]]['filename']
                                for b in source_skin.batches if repair.race.visual.u16(b, 4) == i)
                         for tri in repair.mesh_triangles(source_skin, row) for v in tri}
        shoulder_surface = {original.vertices[v * 48:v * 48 + 32] for v in original_body
                            if abs(struct.unpack_from('<f', original.vertices, v * 48)[0]) < 0.12
                            and 0.19 < abs(struct.unpack_from('<f', original.vertices, v * 48 + 4)[0]) < 0.34
                            and 1.65 < struct.unpack_from('<f', original.vertices, v * 48 + 8)[0] < 1.80}
        covered = {model.vertices[v * 48:v * 48 + 32] for v in torso_vertices}
        assert shoulder_surface and shoulder_surface <= covered, 'Chest clothing still leaves shoulder tops uncovered'
        for part in (hands, feet, legs):
            original_vertices = {original.vertices[v * 48:v * 48 + 32] for v in original_body
                                 if sum(original.vertices[v * 48 + 12 + slot] for slot in range(4)
                                        if original.vertices[v * 48 + 16 + slot] in part) > 200}
            visible_vertices = {model.vertices[v * 48:v * 48 + 32] for v in base_visible}
            assert original_vertices <= visible_vertices, 'Equipping gear can still hide hands, feet or legs'
        # Check leg triangles, not just retained vertices, with every switchable pants/boot group disabled.
        expected = {tuple(original.vertices[v * 48:v * 48 + 32] for v in tri)
                    for row in source_skin.submeshes for tri in repair.mesh_triangles(source_skin, row)
                    if all(v in original_body for v in tri)
                    and sum(original.vertices[v * 48 + 12 + slot] for v in tri for slot in range(4)
                            if original.vertices[v * 48 + 16 + slot] in legs) >= 384}
        actual = {tuple(model.vertices[v * 48:v * 48 + 32] for v in tri)
                  for row in skin.submeshes if repair.race.visual.u16(row, 0) == 0
                  for tri in repair.mesh_triangles(skin, row)}
        assert expected and expected <= actual, 'Leg triangles disappear with the equipment selectors disabled'
        old_surface = {original.vertices[i:i + 32] for i in range(0, len(original.vertices), 48)}
        new_surface = {model.vertices[i:i + 32] for i in range(0, len(model.vertices), 48)}
        assert old_surface <= new_surface, 'Authored body positions, weights or normals changed'
        for row in skin.submeshes:
            assert repair.race.visual.u16(row, 2) == 0
            assert repair.race.visual.u16(row, 12) <= 75
            start, count = repair.race.visual.u16(row, 8), repair.race.visual.u16(row, 10)
            offset = repair.race.visual.u16(row, 14)
            for index in skin.indices[start:start + count]:
                vertex = skin.vertices[index]
                for slot in range(4):
                    if model.vertices[vertex * 48 + 12 + slot]:
                        local = skin.bones[index * 4 + slot]
                        assert local < repair.race.visual.u16(row, 12)
                        assert model.bone_combos[offset + local] == model.vertices[vertex * 48 + 16 + slot]
        for at in range(0, len(model.vertices), 48):
            assert all(math.isfinite(v) for v in struct.unpack_from('<3f', model.vertices, at))
            assert sum(model.vertices[at + 12:at + 16]) == 255
        print('PASS', sex, 'run landing, retained body/rig, garment palettes and shield/shoulder attachment frames')
    bank = (repair.STAGE / 'EsteriaSethrakTextures.bin').read_bytes()
    magic, version, count, checksum = struct.unpack_from('<4I', bank)
    assert (magic, version, count) == (0x31544845, 1, 6)
    assert checksum == int.from_bytes(hashlib.sha256(bank[16:]).digest()[:4], 'little')
    print('PASS five male/one female player skin atlases and material bank integrity')
    assert mirrored_u(0) < 0.51 and mirrored_u(math.pi) > 0.99
    assert mirrored_u(-math.pi / 2) == mirrored_u(math.pi / 2)
    hip = original.bones[original.key_bone_lookup[55]]['parent_bone']
    assert waist_height(model) == original.bones[hip]['pivot'][2]
    print('PASS Human shoulders, original waist, raised neckline and complete legs with pants/boot groups disabled')


if __name__ == '__main__':
    check()
