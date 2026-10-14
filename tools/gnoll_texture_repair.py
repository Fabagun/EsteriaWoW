"""Restore authored Gnoll fur beneath transparent player clothing; retain the installed cape and rig."""

import argparse
from collections import Counter
import hashlib
from pathlib import Path
import struct

from PIL import Image
from wotlkconv.m2 import parse_m2, parse_skin, write_md20
from wotlkconv.m2.skin import Skin, write_skin

import gnoll_cloak_landing_repair as archives
import gnoll_equipment_repair as installer
import gnoll_race_pack as g
import retroported_race_pack as p
import sethrak_animation_pack as animation

STAGE = Path('C:/Users/Zach/.codex/tmp/gnoll-texture-repair-20261008')
SKIN = g.MODEL[:-3] + '00.skin'


def restore_fur(model, skin, source, source_skin):
    """Resolve remapped body triangles against source geometry, retaining exact authored UVs."""
    authored = {}
    for row in source_skin.submeshes:
        if g.visual.u16(row, 0) in (0, 701, 801, 1001):
            for tri in g.triangles(source_skin, row):
                key = tuple(source.vertices[v * 48:v * 48 + 32] for v in tri)
                authored[key] = [source.vertices[v * 48:(v + 1) * 48] for v in tri]
    fur_batch = next(b for b in skin.batches
                     if model.textures[model.texture_combos[g.visual.u16(b, 16)]]['type'] == 11)
    vertices, meshes = bytearray(model.vertices), []
    player_vertices = {v for i, row in enumerate(skin.submeshes)
                       if any(model.textures[model.texture_combos[g.visual.u16(b, 16)]]['type'] == 1
                              for b in skin.batches if g.visual.u16(b, 4) == i)
                       for tri in g.triangles(skin, row) for v in tri}
    native_vertices = {model.vertices[v * 48:(v + 1) * 48]: v for v in range(model.vertex_count)
                       if v not in player_vertices}
    restored = 0
    for index, row in enumerate(skin.submeshes):
        batches = [b for b in skin.batches if g.visual.u16(b, 4) == index]
        player = any(model.textures[model.texture_combos[g.visual.u16(b, 16)]]['type'] == 1 for b in batches)
        geo = g.visual.u16(row, 0)
        tris = g.triangles(skin, row)
        if player:
            for batch in batches:
                model.materials[g.visual.u16(batch, 10)] = {'flags': 16, 'blending_mode': 2}
        if player and geo == 0:
            native = []
            for tri in tris:
                key = tuple(model.vertices[v * 48:v * 48 + 32] for v in tri)
                records = authored[key]
                indices = []
                for record in records:
                    if record not in native_vertices:
                        native_vertices[record] = len(vertices) // 48
                        vertices.extend(record)
                    indices.append(native_vertices[record])
                native.append(tuple(indices))
            meshes.append({'row': row, 'batches': [fur_batch], 'geoset': 0,
                           'triangles': native, 'family': 'body'})
            restored += len(native)
            for vertex in {v for tri in tris for v in tri}:
                point = struct.unpack_from('<3f', model.vertices, vertex * 48)
                normal = struct.unpack_from('<3f', model.vertices, vertex * 48 + 20)
                struct.pack_into('<3f', vertices, vertex * 48,
                                 *(x + n * .002 for x, n in zip(point, normal, strict=True)))
        meshes.append({'row': row, 'batches': batches, 'geoset': geo, 'triangles': tris,
                       'family': 'armor' if 1502 <= geo <= 1506 or geo == 1302 else 'body'})
    model.vertices, model.vertex_count = bytes(vertices), len(vertices) // 48
    raw = Skin()
    for index, mesh in enumerate(meshes):
        row = bytearray(mesh['row'])
        used = list(dict.fromkeys(v for tri in mesh['triangles'] for v in tri))
        first, lookup = len(raw.indices), len(raw.vertices)
        mapping = {v: lookup + i for i, v in enumerate(used)}
        raw.vertices.extend(used)
        raw.indices.extend(mapping[v] for tri in mesh['triangles'] for v in tri)
        for offset, value in ((0, mesh['geoset']), (2, first >> 16), (4, lookup), (6, len(used)),
                              (8, first & 65535), (10, 3 * len(mesh['triangles']))):
            g.visual.patch16(row, offset, value)
        raw.submeshes.append(bytes(row))
        for batch in mesh['batches']:
            value = bytearray(batch)
            g.visual.patch16(value, 4, index)
            g.visual.patch16(value, 6, index)
            raw.batches.append(bytes(value))
    return g.visual.compact_bone_palettes(model, raw), restored


def clothing_catalog(catalog):
    """Use one transparent base layer; fur colors continue through the existing type-11 selections."""
    from haranir_race_pack import lznt1
    pixels = bytearray(512 * 512 * 4)
    pixels[0] = 1  # Keep RtlCompressBuffer's all-zero sparse-block special case out of this bank.
    packed = lznt1(bytes(pixels))
    bank = bytearray(struct.pack('<4I', 0x31544845, 1, 1, 0)
                     + struct.pack('<3I', 512, 512, len(packed)) + packed)
    struct.pack_into('<I', bank, 12, int.from_bytes(hashlib.sha256(bank[16:]).digest()[:4], 'little'))
    rows = [catalog[at:at + 156] for at in range(12, len(catalog), 156)
            if struct.unpack_from('<I', catalog, at + 4)[0] != 3]
    rows.append(struct.pack('<7I', 0, 3, 0, 16, 0xffffffff, 0xffffffff, 0xffffffff)
                + b'1:0'.ljust(128, b'\0'))
    return struct.pack('<3I', 0x314D4845, 1, len(rows)) + b''.join(rows), bytes(bank)


def prepare():
    STAGE.mkdir(parents=True, exist_ok=True)
    files = p.ClientFiles(str(p.CLIENT_DEFAULT / 'Data'), 'enUS')
    try:
        data, provider = files.find(g.MODEL)
        skin_data, skin_provider = files.find(SKIN)
    finally:
        files.close()
    g.c.immutable(STAGE / 'before.m2', data)
    g.c.immutable(STAGE / 'before00.skin', skin_data)
    model, skin = parse_m2(data), parse_skin(skin_data)
    source = parse_m2((g.ROOT / 'converted/gnoll2.m2').read_bytes())
    source_skin = parse_skin((g.ROOT / 'converted/gnoll200.skin').read_bytes())
    compact, count = restore_fur(model, skin, source, source_skin)
    path = g.local(STAGE / 'assets', g.MODEL)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(write_md20(model))
    g.local(STAGE / 'assets', SKIN).write_bytes(write_skin(compact))
    catalog = (p.CLIENT_DEFAULT / 'EsteriaGnoll.bin').read_bytes()
    g.c.immutable(STAGE / 'before-EsteriaGnoll.bin', catalog)
    records, bank = clothing_catalog(catalog)
    (STAGE / 'EsteriaGnoll.bin').write_bytes(records)
    (STAGE / 'EsteriaGnollTextures.bin').write_bytes(bank)
    Image.new('RGBA', (512, 512)).save(STAGE / 'male-player-skin-0.png')
    protected = {name: p.sha256(p.CLIENT_DEFAULT / name) for name in
                 ('EsteriaAppearance.dll', 'Wow.exe', str(p.GLOBAL_ARCHIVE_REL), str(p.LOCALE_ARCHIVE_REL))}
    baseline = {name: p.sha256(p.CLIENT_DEFAULT / name) for name in
                (str(g.ASSET_ARCHIVE), 'EsteriaAppearanceGeometry.bin', 'EsteriaGnoll.bin', 'EsteriaGnollTextures.bin')}
    g.save(STAGE / 'changes.json', {'restored_fur_triangles': count, 'protected': protected,
                                  'baseline': baseline, 'model_provider': provider, 'skin_provider': skin_provider})
    check()


def surfaces(model, skin, predicate):
    return Counter((g.visual.u16(row, 0), tuple(model.vertices[v * 48:(v + 1) * 48] for v in tri))
                   for index, row in enumerate(skin.submeshes)
                   if predicate(g.visual.u16(row, 0), {model.textures[model.texture_combos[g.visual.u16(b, 16)]]['type']
                                                      for b in skin.batches if g.visual.u16(b, 4) == index})
                   for tri in g.triangles(skin, row))


def check():
    import ctypes
    data = g.local(STAGE / 'assets', g.MODEL).read_bytes()
    model, skin = parse_m2(data), parse_skin(g.local(STAGE / 'assets', SKIN).read_bytes())
    before, old_skin = parse_m2((STAGE / 'before.m2').read_bytes()), parse_skin((STAGE / 'before00.skin').read_bytes())
    animation.check_model(model, data)
    assert model.sequences == before.sequences
    assert [{k: v for k, v in a.items() if k != 'animate_attached'} for a in model.attachments] == [
        {k: v for k, v in a.items() if k != 'animate_attached'} for a in before.attachments]
    animation.tracks_equal(before, model, len(before.sequences))
    retained = lambda geo, types: types not in ({1}, {14})
    assert surfaces(before, old_skin, retained) <= surfaces(model, skin, retained)
    source = parse_m2((g.ROOT / 'converted/gnoll2.m2').read_bytes())
    source_skin = parse_skin((g.ROOT / 'converted/gnoll200.skin').read_bytes())
    expected = {tri for (_, tri) in surfaces(source, source_skin, lambda geo, types: geo in (0, 701, 801, 1001))}
    actual = {tri for (_, tri) in surfaces(model, skin, lambda geo, types: geo == 0 and types == {11})}
    assert expected <= actual, 'Authored body or neck UVs differ from the donor'
    for index, row in enumerate(skin.submeshes):
        assert g.visual.u16(row, 12) <= 75
        for batch in (b for b in skin.batches if g.visual.u16(b, 4) == index):
            if model.textures[model.texture_combos[g.visual.u16(batch, 16)]]['type'] in (1, 14):
                assert model.materials[g.visual.u16(batch, 10)] == {'flags': 16, 'blending_mode': 2}
        offset = g.visual.u16(row, 14)
        for tri in g.triangles(skin, row):
            for vertex in tri:
                assert sum(model.vertices[vertex * 48 + 12:vertex * 48 + 16]) == 255
        start = g.visual.u16(row, 8) | g.visual.u16(row, 2) << 16
        count = g.visual.u16(row, 10)
        for index in skin.indices[start:start + count]:
            vertex = skin.vertices[index]
            for slot in range(4):
                if model.vertices[vertex * 48 + 12 + slot]:
                    local = skin.bones[index * 4 + slot]
                    assert local < g.visual.u16(row, 12)
                    assert model.bone_combos[offset + local] == model.vertices[vertex * 48 + 16 + slot]
    catalog = (STAGE / 'EsteriaGnoll.bin').read_bytes()
    old = (STAGE / 'before-EsteriaGnoll.bin').read_bytes()
    non_bake = lambda value: [value[at:at + 156] for at in range(12, len(value), 156)
                              if struct.unpack_from('<I', value, at + 4)[0] != 3]
    assert non_bake(catalog) == non_bake(old), 'Fur, outfit or feature controls changed'
    bank = (STAGE / 'EsteriaGnollTextures.bin').read_bytes()
    width, height, size = struct.unpack_from('<3I', bank, 16)
    target, written = ctypes.create_string_buffer(width * height * 4), ctypes.c_ulong()
    assert ctypes.windll.ntdll.RtlDecompressBuffer(2, target, len(target), bank[28:], size,
                                                  ctypes.byref(written)) == 0
    assert written.value == len(target) and not any(target.raw[3::4]), 'Clothing base is not transparent'
    assert model.vertex_count < 65536 and len(skin.vertices) < 65536
    print(f'PASS exact donor body/neck fur, transparent clothing, all controls and cape/rig retained; '
          f'{len(skin.indices)} indices', flush=True)


def stage():
    baseline = p.load_json(STAGE / 'changes.json')['baseline']
    assert all(p.sha256(p.CLIENT_DEFAULT / name) == digest for name, digest in baseline.items())
    archives.STAGE = STAGE
    archives.stage(validate=check, include_creator=False)
    report = p.load_json(STAGE / 'stage.json')
    for name in ('EsteriaGnoll.bin', 'EsteriaGnollTextures.bin'):
        report['files'][name] = str(STAGE / name)
        report['before'][name] = p.sha256(p.CLIENT_DEFAULT / name)
        report['after'][name] = p.sha256(STAGE / name)
    g.save(STAGE / 'stage.json', report)


def install():
    report = p.load_json(STAGE / 'stage.json')
    dll = STAGE / 'native/EsteriaAppearance.dll'
    name = 'EsteriaAppearance.dll'
    baseline = report['protected'].get(name, report['before'].get(name))
    if not dll.exists() or p.sha256(dll) == baseline:
        raise RuntimeError('Build and verify the Gnoll alpha fix before installation')
    report['files'][name] = str(dll)
    report['before'][name] = baseline
    report['protected'].pop(name, None)
    report['after'][name] = p.sha256(dll)
    g.save(STAGE / 'stage.json', report)
    installer.STAGE = STAGE
    installer.install(validate=check)


def preview():
    """Render the same idle pose and palette before/after, using the existing Blender viewer."""
    import creature_animation_repair as motion
    from sethrak_equipment_repair import vertex_record
    from wotlkconv.blp import Blp
    color = 9
    textures = {}
    for fid in (g.BODY_IDS[color], g.ARMOR_IDS[0], 3886653):
        image = Blp.parse(g.raw(fid)).decode_level(0)
        path = STAGE / (str(fid) + '.png')
        Image.frombytes('RGBA', (image.width, image.height), bytes(image.data)).save(path)
        textures[fid] = str(path)
    selected = {0, 401, 501, 1301}
    selected.update(3000 + choices[0] for i, choices in enumerate(g.CHOICES) if i not in (0, 5))
    selected.difference_update((3701, 3801))
    selected.update((3702, 3802))
    for name in ('before', 'after'):
        root = STAGE / ('preview-' + name)
        root.mkdir(exist_ok=True)
        model = parse_m2((STAGE / 'before.m2').read_bytes() if name == 'before'
                         else g.local(STAGE / 'assets', g.MODEL).read_bytes())
        skin = parse_skin((STAGE / 'before00.skin').read_bytes() if name == 'before'
                          else g.local(STAGE / 'assets', SKIN).read_bytes())
        atlas = (Path('C:/Users/Zach/.codex/tmp/gnoll-equipment-fit-v2') / f'male-player-skin-{color}.png'
                 if name == 'before' else STAGE / 'male-player-skin-0.png')
        materials = {0: textures[3886653], 11: textures[g.BODY_IDS[color]],
                     12: textures[g.ARMOR_IDS[0]], 1: str(atlas), 14: str(atlas)}
        posed = motion.posed_vertices(model, motion.pose_matrices(model, 0, 0))
        vertices = [dict(vertex_record(model, i), position=posed[i].tolist()) for i in range(model.vertex_count)]
        parts = []
        for i, row in enumerate(skin.submeshes):
            if g.visual.u16(row, 0) not in selected:
                continue
            batch = next(b for b in skin.batches if g.visual.u16(b, 4) == i)
            kind = model.textures[model.texture_combos[g.visual.u16(batch, 16)]]['type']
            parts.append({'geoset': g.visual.u16(row, 0), 'triangles': g.triangles(skin, row),
                          'texture': materials[kind]})
        g.save(root / 'model.json', {'vertices': vertices, 'meshes': parts})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare', 'check', 'stage', 'install', 'preview'))
    globals()[parser.parse_args().action]()
