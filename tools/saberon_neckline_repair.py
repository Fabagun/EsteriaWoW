"""Raise and smooth only Saberon's chest neckline on isolated copies of the currently installed assets."""

import argparse
from collections import Counter
from pathlib import Path
import shutil
import struct

import numpy as np
from PIL import Image
from wotlkconv.blp import Blp
from wotlkconv.m2 import parse_m2, parse_skin, write_md20
from wotlkconv.m2.skin import Skin, write_skin

import creature_animation_repair as motion
import gnoll_equipment_repair as installer
import gnoll_race_pack as g
import retroported_race_pack as p
import saberon_equipment_fit as fit
import saberon_race_pack as s
import sethrak_animation_pack as animation

STAGE = Path('C:/Users/Zach/.codex/tmp/saberon-neckline-20261008')
SKIN = s.MODEL[:-3] + '00.skin'


def prepare():
    STAGE.mkdir(parents=True, exist_ok=True)
    files = p.ClientFiles(str(p.CLIENT_DEFAULT / 'Data'), 'enUS')
    try:
        s.c.immutable(STAGE / 'before.m2', files.find(s.MODEL)[0])
        s.c.immutable(STAGE / 'before.skin', files.find(SKIN)[0])
    finally:
        files.close()
    model, skin = parse_m2((STAGE / 'before.m2').read_bytes()), parse_skin((STAGE / 'before.skin').read_bytes())
    original = parse_m2((fit.SOURCE / 'before.m2').read_bytes())
    original_skin = parse_skin((fit.SOURCE / 'before.skin').read_bytes())
    body = [tri for row in original_skin.submeshes if s.visual.u16(row, 0) == 0
            for tri in fit.e.mesh_triangles(original_skin, row)]
    torso = fit.torso_surface(original, body)
    normals = fit.surface_normals(original, body)
    triangles = list(dict.fromkeys([tuple(t) for t in p.load_json(fit.SOURCE / 'male-body-work.json')['body']]
                                  + [t for t in body if t[0] in torso]))
    row_index = next(i for i, row in enumerate(skin.submeshes) if s.visual.u16(row, 0) == 20004)
    chest = []
    vertices, lookup = bytearray(model.vertices), {}
    for region, polygon in fit.clothing_polygons(original, triangles, torso, normals):
        if region != 3:
            continue
        face = []
        for vertex in polygon:
            record = bytearray(48)
            struct.pack_into('<3f', record, 0, *(x + n * .018 for x, n in
                                               zip(vertex['position'], vertex['normal'], strict=True)))
            record[12:16] = bytes(vertex['weights'] + [0] * (4 - len(vertex['weights'])))
            record[16:20] = bytes(vertex['bones'] + [0] * (4 - len(vertex['bones'])))
            struct.pack_into('<3f', record, 20, *vertex['normal'])
            struct.pack_into('<2f', record, 32, *vertex['uv'])
            key = bytes(record)
            if key not in lookup:
                lookup[key] = len(vertices) // 48
                vertices.extend(record)
            face.append(lookup[key])
        chest.extend((face[0], face[i], face[i + 1]) for i in range(1, len(face) - 1))
    model.vertices, model.vertex_count = bytes(vertices), len(vertices) // 48
    raw = Skin()
    for index, row in enumerate(skin.submeshes):
        faces = chest if index == row_index else fit.e.mesh_triangles(skin, row)
        used = list(dict.fromkeys(v for tri in faces for v in tri))
        first, base = len(raw.indices), len(raw.vertices)
        remap = {v: base + i for i, v in enumerate(used)}
        raw.vertices.extend(used)
        raw.indices.extend(remap[v] for tri in faces for v in tri)
        row = bytearray(row)
        for offset, value in ((2, first >> 16), (4, base), (6, len(used)),
                              (8, first & 65535), (10, len(faces) * 3)):
            s.visual.patch16(row, offset, value)
        raw.submeshes.append(bytes(row))
        raw.batches.extend(b for b in skin.batches if s.visual.u16(b, 4) == index)
    compact = s.visual.compact_bone_palettes(model, raw)
    path = s.local(STAGE / 'assets', s.MODEL)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(write_md20(model))
    s.local(STAGE / 'assets', SKIN).write_bytes(write_skin(compact))
    protected = {str(path.relative_to(p.CLIENT_DEFAULT)): p.sha256(path)
                 for path in p.CLIENT_DEFAULT.glob('Esteria*.bin') if path.name != 'EsteriaAppearanceGeometry.bin'}
    names = ('EsteriaAppearance.dll', 'Wow.exe', p.GLOBAL_ARCHIVE_REL, p.LOCALE_ARCHIVE_REL, g.ASSET_ARCHIVE)
    protected.update({str(name): p.sha256(p.CLIENT_DEFAULT / name) for name in names})
    s.save(STAGE / 'changes.json', {'protected': protected})
    check()


def surfaces(model, skin, chest):
    return Counter((s.visual.u16(row, 0), tuple(model.vertices[v * 48:(v + 1) * 48] for v in tri))
                   for row in skin.submeshes if (s.visual.u16(row, 0) == 20004) == chest
                   for tri in fit.e.mesh_triangles(skin, row))


def neckline(model, skin, raised=False):
    posed = motion.posed_vertices(model, motion.pose_matrices(model, 0, 0))
    area, edges = 0, []
    for row in skin.submeshes:
        if s.visual.u16(row, 0) != 20004:
            continue
        for tri in fit.e.mesh_triangles(skin, row):
            points = posed[list(tri)]
            if points[:, 0].mean() < .15:
                area += np.linalg.norm(np.cross(points[1] - points[0], points[2] - points[0])) / 2
            for a, b in zip(tri, tri[1:] + tri[:1]):
                uv = [struct.unpack_from('<2f', model.vertices, v * 48 + 32) for v in (a, b)]
                if all(abs(v - (fit.collar_texture_v(u, .004) if raised else .004)) < 1e-6 for u, v in uv):
                    edges.append(float(np.linalg.norm(posed[a] - posed[b])))
    return float(area), max(edges)


def check():
    before, old_skin = parse_m2((STAGE / 'before.m2').read_bytes()), parse_skin((STAGE / 'before.skin').read_bytes())
    data = s.local(STAGE / 'assets', s.MODEL).read_bytes()
    model, skin = parse_m2(data), parse_skin(s.local(STAGE / 'assets', SKIN).read_bytes())
    animation.check_model(model, data)
    assert surfaces(before, old_skin, False) == surfaces(model, skin, False), 'Other anatomy or equipment changed'
    assert model.textures == before.textures and model.materials == before.materials
    assert model.replacable_texture_lookup == before.replacable_texture_lookup
    assert model.sequences == before.sequences
    assert model.key_bone_lookup == before.key_bone_lookup
    assert [{k: v for k, v in a.items() if k != 'animate_attached'} for a in model.attachments] == [
        {k: v for k, v in a.items() if k != 'animate_attached'} for a in before.attachments]
    animation.tracks_equal(before, model, len(before.sequences))
    old_area, old_edge = neckline(before, old_skin)
    area, edge = neckline(model, skin, raised=True)
    assert area > old_area * 1.02, 'Rear chest coverage did not increase'
    assert edge < old_edge * .6, 'Neckline retains coarse polygon edges'
    assert model.vertex_count < 65536 and len(skin.vertices) < 65536
    for row in skin.submeshes:
        assert s.visual.u16(row, 12) <= 75
        offset = s.visual.u16(row, 14)
        start = s.visual.u16(row, 8) | s.visual.u16(row, 2) << 16
        for index in skin.indices[start:start + s.visual.u16(row, 10)]:
            vertex = skin.vertices[index]
            for slot in range(4):
                if model.vertices[vertex * 48 + 12 + slot]:
                    local = skin.bones[index * 4 + slot]
                    assert local < s.visual.u16(row, 12)
                    assert model.bone_combos[offset + local] == model.vertices[vertex * 48 + 16 + slot]
        if s.visual.u16(row, 0) == 20004:
            for tri in fit.e.mesh_triangles(skin, row):
                for vertex in tri:
                    assert sum(model.vertices[vertex * 48 + 12:vertex * 48 + 16]) == 255
                    assert struct.unpack_from('<f', model.vertices, vertex * 48 + 36)[0] >= .00399
    for action, clock in ((0, 0), (5, 100), (17, 100), (51, 100)):
        assert np.isfinite(motion.posed_vertices(model, motion.pose_matrices(model, action, clock))).all()
    s.save(STAGE / 'neckline-check.json', {'rear_area_before': old_area, 'rear_area_after': area,
                                         'edge_before': old_edge, 'edge_after': edge})
    print(f'PASS rear chest area {old_area:.3f} -> {area:.3f}; max neckline edge {old_edge:.3f} -> {edge:.3f}; '
          'fur, other armor, materials and animation retained')


def stage():
    import gnoll_cloak_landing_repair as archives
    archives.STAGE = STAGE
    old_model, old_archive = g.MODEL, g.ASSET_ARCHIVE
    try:
        g.MODEL, g.ASSET_ARCHIVE = s.MODEL, s.ASSET_ARCHIVE
        archives.stage(validate=check, include_creator=False)
    finally:
        g.MODEL, g.ASSET_ARCHIVE = old_model, old_archive


def install():
    installer.STAGE = STAGE
    installer.install(validate=check)


def preview():
    files = p.ClientFiles(str(p.CLIENT_DEFAULT / 'Data'), 'enUS')
    try:
        table = p.RawWdbc(files.find(p.DBC_ROOT + 'ItemDisplayInfo.dbc')[0])
        item = next(row for row in table.records if p._value(row, 0) == 64695)
        atlas = Image.new('RGBA', (512, 512))
        for region, rect in ((0, (0, 0, 256, 128)), (3, (256, 0, 512, 128)), (4, (256, 128, 512, 192))):
            directory = ('ArmUpperTexture', '', '', 'TorsoUpperTexture', 'TorsoLowerTexture')[region]
            stem = p._string(table.strings, p._value(item, (15 + region) * 4)).decode()
            if not stem:
                continue
            for suffix in ('_U', '_M', '', '_F'):
                try:
                    data = files.find('Item\\TextureComponents\\' + directory + '\\' + stem + suffix + '.blp')[0]
                    break
                except FileNotFoundError:
                    continue
            else:
                raise FileNotFoundError(stem)
            image = Blp.parse(data).decode_level(0)
            image = Image.frombytes('RGBA', (image.width, image.height), bytes(image.data))
            atlas.alpha_composite(image.resize((rect[2] - rect[0], rect[3] - rect[1]),
                                              Image.Resampling.NEAREST), (rect[0], rect[1]))
        atlas.save(STAGE / 'battleplate.png')
        image = Blp.parse(files.find(s.PREFIX + 'textures\\' + str(s.BODY_IDS[3]) + '.blp')[0]).decode_level(0)
        Image.frombytes('RGBA', (image.width, image.height), bytes(image.data)).save(STAGE / 'fur.png')
    finally:
        files.close()
    for name in ('before', 'after'):
        root = STAGE / ('preview-' + name)
        root.mkdir(exist_ok=True)
        model = parse_m2((STAGE / 'before.m2').read_bytes() if name == 'before'
                         else s.local(STAGE / 'assets', s.MODEL).read_bytes())
        skin = parse_skin((STAGE / 'before.skin').read_bytes() if name == 'before'
                          else s.local(STAGE / 'assets', SKIN).read_bytes())
        posed = motion.posed_vertices(model, motion.pose_matrices(model, 0, 0))
        parts = []
        for index, row in enumerate(skin.submeshes):
            if s.visual.u16(row, 0) not in (0, 20004, 20005):
                continue
            batch = next(b for b in skin.batches if s.visual.u16(b, 4) == index)
            kind = model.textures[model.texture_combos[s.visual.u16(batch, 16)]]['type']
            if kind not in (11, 14):
                continue
            parts.append({'geoset': s.visual.u16(row, 0), 'triangles': fit.e.mesh_triangles(skin, row),
                          'texture': str(STAGE / ('fur.png' if kind == 11 else 'battleplate.png')),
                          'unlit': kind == 14})
        s.save(root / 'model.json', {'vertices': [dict(fit.e.vertex_record(model, i), position=posed[i].tolist())
                                                for i in range(model.vertex_count)], 'meshes': parts,
                                   'camera': [-3, -5, 8], 'target': [0, 0, 1.9], 'scale': 1.45})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare', 'check', 'stage', 'install', 'preview'))
    globals()[parser.parse_args().action]()
