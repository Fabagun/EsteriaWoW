"""Regression checks for exact source fur, no floating glove pieces and regional armor UVs."""

from collections import Counter
import ctypes
import math
from pathlib import Path
import struct

import numpy as np
from wotlkconv.m2 import parse_m2, parse_skin
import saberon_equipment_fit as f
import saberon_race_pack as s
import sethrak_equipment_repair as e
import creature_animation_repair as motion


def check():
    old = parse_m2((f.SOURCE / 'before.m2').read_bytes())
    old_skin = parse_skin((f.SOURCE / 'before.skin').read_bytes())
    model = parse_m2(s.local(f.STAGE / 'assets', s.MODEL).read_bytes())
    skin = parse_skin(s.local(f.STAGE / 'assets', s.MODEL[:-3] + '00.skin').read_bytes())

    def fur_surface(m, k):
        return Counter(tuple(m.vertices[v * 48:(v + 1) * 48] for v in tri)
                       for index, row in enumerate(k.submeshes) if s.visual.u16(row, 0) == 0
                       and all(m.textures[m.texture_combos[s.visual.u16(b, 16)]]['type'] == 11
                               for b in k.batches if s.visual.u16(b, 4) == index)
                       for tri in e.mesh_triangles(k, row))

    assert fur_surface(old, old_skin) == fur_surface(model, skin), 'Original visible fur or UVs changed'
    assert model.materials[:len(old.materials)] == old.materials
    assert model.sequences == old.sequences
    source_triangles = e.mesh_triangles(old_skin, old_skin.submeshes[0])
    normals = f.surface_normals(old, source_triangles)
    chest_vertices = {v for row in skin.submeshes if s.visual.u16(row, 0) == 20004
                      for tri in e.mesh_triangles(skin, row) for v in tri}
    for original_vertex in (74, 76, 1447):
        point = np.array(struct.unpack_from('<3f', old.vertices, original_vertex * 48))
        normal = np.array(normals[original_vertex])
        assert any(np.allclose(struct.unpack_from('<3f', model.vertices, v * 48), point + normal * .018,
                               atol=1e-6) for v in chest_vertices), 'Chest clearance uses inward shading normals'
    torso = f.torso_surface(old, source_triangles)
    work = s.p.load_json(f.SOURCE / 'male-body-work.json')
    triangles = list(dict.fromkeys([tuple(t) for t in work['body']]
                                  + [t for t in source_triangles if t[0] in torso]))
    boundaries = {}
    for tri, (region, uvs) in zip(triangles, f.armor_uvs(old, triangles, torso), strict=True):
        used = {v for row in skin.submeshes if s.visual.u16(row, 0) == 20001 + region
                for face in e.mesh_triangles(skin, row) for v in face}
        for source in tri:
            point = np.array(struct.unpack_from('<3f', old.vertices, source * 48))
            expected = point + np.array(normals[source]) * .018
            candidates = [v for v in used if np.allclose(
                struct.unpack_from('<3f', model.vertices, v * 48), expected, atol=1e-6)]
            if region in (3, 4) and not candidates:
                continue  # The neckline clips only the torso polygons.
            assert candidates, 'Clothing moved inward or uses a different clearance at a region join'
            key = tuple(np.round(point, 5))
            boundaries.setdefault(key, {}).setdefault(region, set()).update(candidates)
    for action, clock in ((0, 0), (5, 100), (17, 100), (51, 100)):
        posed = motion.posed_vertices(model, motion.pose_matrices(model, action, clock))
        for regions in boundaries.values():
            if len(regions) < 2:
                continue
            points = posed[list(set().union(*regions.values()))]
            assert np.max(np.ptp(points, axis=0)) < 1e-4, 'Clothing region join opens during animation'
    ids = {s.visual.u16(row, 0) for row in skin.submeshes}
    for row in skin.submeshes:
        if s.visual.u16(row, 0) == 20005:
            for tri in e.mesh_triangles(skin, row):
                assert any(struct.unpack_from('<f', model.vertices, v * 48 + 36)[0] < .37499 for v in tri), \
                    'Lower torso collapses onto the belt texture row'
    assert not any(400 <= geo < 1200 or 1800 <= geo < 1900 for geo in ids), 'Borrowed limb/belt meshes remain'
    assert set(range(20001, 20010)) <= ids
    assert {1202, 1302, 1502, 1503, 1504, 1505, 1506} <= ids
    assert len(skin.indices) > len(old_skin.indices) and len(skin.vertices) < 65536 and model.vertex_count < 65536
    for row in skin.submeshes:
        geo = s.visual.u16(row, 0)
        assert s.visual.u16(row, 12) <= 75
        if 20001 <= geo <= 20007:
            for tri in e.mesh_triangles(skin, row):
                for vertex in tri:
                    u, v = struct.unpack_from('<2f', model.vertices, vertex * 48 + 32)
                    assert 0 <= u <= 1 and 0 <= v <= .875
                    assert u < .5 if geo <= 20003 else u > .5
                    if geo in (20004, 20005):
                        assert v >= .00399, 'Chest overlay crosses its neckline'
            batches = [b for b in skin.batches if s.visual.u16(b, 4) == skin.submeshes.index(row)]
            assert all(model.materials[s.visual.u16(b, 10)] == {'flags': 16, 'blending_mode': 2} for b in batches)
    for action, clock in ((0, 0), (5, 100), (17, 100), (51, 100)):
        points = motion.posed_vertices(model, motion.pose_matrices(model, action, clock))
        for geo in (20002, 20003):
            used = {v for row in skin.submeshes if s.visual.u16(row, 0) == geo
                    for tri in e.mesh_triangles(skin, row) for v in tri}
            if action == 0:
                assert points[list(used), 2].min() > .2, 'Glove surface reaches the ground in standing pose'
            assert np.isfinite(points[list(used)]).all()
    bank = (f.STAGE / 'EsteriaSaberonTextures.bin').read_bytes()
    assert struct.unpack_from('<3I', bank) == (0x31544845, 1, 1)
    width, height, length = struct.unpack_from('<3I', bank, 16)
    assert (width, height) == (512, 512)
    target, written = ctypes.create_string_buffer(width * height * 4), ctypes.c_ulong()
    status = ctypes.windll.ntdll.RtlDecompressBuffer(2, target, len(target), bank[28:28 + length], length,
                                                   ctypes.byref(written))
    assert status == 0 and written.value == len(target)
    assert not any(target.raw[3::4]), 'Overlay base contains opaque rebaked fur'
    coverage = (f.STAGE / 'EsteriaSaberonCoverage.bin').read_bytes()
    magic, version, count = struct.unpack_from('<3I', coverage)
    assert (magic, version) == (0x56434253, 1) and len(coverage) == 12 + count * 8
    masks = dict(struct.iter_unpack('<2I', coverage[12:]))
    assert masks[64585] == 6 and masks[64588] == 96
    belt = [row for row in skin.submeshes if s.visual.u16(row, 0) == 20008]
    points = [struct.unpack_from('<3f', model.vertices, v * 48) for row in belt
              for tri in e.mesh_triangles(skin, row) for v in tri]
    assert min(p[2] for p in points) > 1.38 and max(p[2] for p in points) < 1.69
    arms = e.descendants(model, 17) | e.descendants(model, 18)
    for row in belt:
        for tri in e.mesh_triangles(skin, row):
            for v in tri:
                assert not any(model.vertices[v * 48 + 12 + i] and model.vertices[v * 48 + 16 + i] in arms
                               for i in range(4)), 'Belt includes arm geometry'
    assert model.textures[model.replacable_texture_lookup[9]]['type'] == 9
    assert model.textures[model.replacable_texture_lookup[10]]['type'] == 10
    original_pants = [tri for row in skin.submeshes if s.visual.u16(row, 0) == 20006
                      for tri in e.mesh_triangles(skin, row)]
    separate_pants = [tri for row in skin.submeshes if s.visual.u16(row, 0) == 20009
                      for tri in e.mesh_triangles(skin, row)]
    assert len(original_pants) == len(separate_pants)
    for original_tri, separate_tri in zip(original_pants, separate_pants, strict=True):
        for a, b in zip(original_tri, separate_tri, strict=True):
            assert model.vertices[a * 48:a * 48 + 32] == model.vertices[b * 48:b * 48 + 32]
            u, v = struct.unpack_from('<2f', model.vertices, a * 48 + 32)
            actual = struct.unpack_from('<2f', model.vertices, b * 48 + 32)
            assert np.allclose(actual, ((u - .5) * 2, (v - .375) * 4), atol=1e-6), 'Leggings pixels cropped'
    previous_root = Path('C:/Users/Zach/.codex/tmp/saberon-equipment-fit-v5')
    previous_model = parse_m2(s.local(previous_root / 'assets', s.MODEL).read_bytes())
    previous_skin = parse_skin(s.local(previous_root / 'assets', s.MODEL[:-3] + '00.skin').read_bytes())
    for geo in (20002, 20003, 20006, 20007):
        def pieces(m, k):
            return Counter(tuple(m.vertices[v * 48:(v + 1) * 48] for v in tri)
                           for row in k.submeshes if s.visual.u16(row, 0) == geo
                           for tri in e.mesh_triangles(k, row))
        before, after = pieces(previous_model, previous_skin), pieces(model, skin)
        assert not before - after, 'Repaired glove/leg surfaces changed'
        assert geo == 20006 or before == after, 'Unexpected new glove/lower-leg geometry'
    print('PASS exact original fur/UVs, transparent clothing base, no donor limb meshes,')
    print('outward limb clearance, welded joins in standing/run/attack/cast, preserved limbs, no belt-row stretching')


if __name__ == '__main__':
    check()
