"""Repair the installed Gnoll cloak, running touchdown and male-only creator on isolated copies."""

import argparse
import copy
from pathlib import Path
import shutil
import struct

from luaparser import ast
from wotlkconv.m2 import parse_m2, parse_skin, write_md20
from wotlkconv.m2.skin import write_skin

import gnoll_equipment_repair as equipment
import gnoll_race_pack as g
import retroported_race_pack as p
from sethrak_equipment_repair import check_landing, packed_skin, use_running_landing

STAGE = Path('C:/Users/Zach/.codex/tmp/gnoll-cloak-landing-v3')
PREVIOUS = Path('C:/Users/Zach/.codex/tmp/gnoll-equipment-fit-v2')
GLUE = p.GLUE_ROOT + 'CharacterCreate.lua'


def prepare():
    STAGE.mkdir(parents=True, exist_ok=True)
    previous = p.load_json(PREVIOUS / 'installed.json')
    assert p.sha256(p.CLIENT_DEFAULT / g.ASSET_ARCHIVE) == previous['after'][str(g.ASSET_ARCHIVE)]
    protected = {name: p.sha256(p.CLIENT_DEFAULT / name) for name in
                 ('EsteriaAppearance.dll', 'EsteriaGnoll.bin', 'EsteriaGnollTextures.bin', 'Wow.exe')}
    before_data = g.local(PREVIOUS / 'assets', g.MODEL).read_bytes()
    before_skin = g.local(PREVIOUS / 'assets', g.MODEL[:-3] + '00.skin').read_bytes()
    with p.ClientFiles(str(p.CLIENT_DEFAULT / 'Data'), 'enUS') as files:
        assert files.find(g.MODEL)[0] == before_data
        assert files.find(g.MODEL[:-3] + '00.skin')[0] == before_skin
        glue_data, provider = files.find(GLUE)
    g.c.immutable(STAGE / 'before.m2', before_data)
    g.c.immutable(STAGE / 'before00.skin', before_skin)
    g.c.immutable(STAGE / 'before-CharacterCreate.lua', glue_data)
    shutil.copy2(PREVIOUS / 'animated.m2', STAGE / 'animated.m2')
    model, skin = parse_m2(before_data), parse_skin(before_skin)
    original = copy.deepcopy(model)
    source_skin = parse_skin((g.ROOT / 'converted/gnoll200.skin').read_bytes())
    surface = g.cape_body_surface(model, source_skin)
    donor = parse_m2((PREVIOUS / 'donors/worgen.m2').read_bytes())
    donor_skin = parse_skin((PREVIOUS / 'donors/worgen00.skin').read_bytes())
    vertices = bytearray(model.vertices)
    for geo in range(1502, 1507):
        target = sorted({v for row in skin.submeshes if g.visual.u16(row, 0) == geo
                         for tri in g.triangles(skin, row) for v in tri})
        source = sorted({v for row in donor_skin.submeshes if g.visual.u16(row, 0) == geo
                         for tri in g.triangles(donor_skin, row) for v in tri})
        heights = [struct.unpack_from('<f', donor.vertices, v * 48 + 8)[0] for v in source]
        assert len(target) == len(source)
        for target_index in target:
            previous_vertex = original.vertices[target_index * 48:(target_index + 1) * 48]
            _, old_y, old_z = struct.unpack_from('<3f', previous_vertex)
            candidates = [v for v in source if donor.vertices[v * 48 + 32:(v + 1) * 48] == previous_vertex[32:]]
            assert candidates, 'Installed cloak no longer has the pinned donor UVs'
            source_index = min(candidates, key=lambda v:
                               (struct.unpack_from('<f', donor.vertices, v * 48 + 4)[0] * .72 - old_y) ** 2
                               + (1.73 - (max(heights) - struct.unpack_from('<f', donor.vertices,
                                                                        v * 48 + 8)[0]) * .82 - old_z) ** 2)
            fitted = g.fit_cape_vertex(model, surface, donor.vertices[source_index * 48:(source_index + 1) * 48],
                                       max(heights), min(heights))
            assert fitted[32:] == vertices[target_index * 48 + 32:(target_index + 1) * 48]
            vertices[target_index * 48:(target_index + 1) * 48] = fitted
    model.vertices = bytes(vertices)
    landing = use_running_landing(model)
    meshes = [{'row': row, 'geoset': g.visual.u16(row, 0), 'triangles': g.triangles(skin, row),
               'family': 'armor' if g.visual.u16(row, 0) == 1302 or 1502 <= g.visual.u16(row, 0) <= 1506 else 'body',
               'batches': [batch for batch in skin.batches if g.visual.u16(batch, 4) == index]}
              for index, row in enumerate(skin.submeshes)]
    packed = packed_skin(model, meshes)
    encoded = write_md20(model)
    check_landing(original, parse_m2(encoded))
    path = g.local(STAGE / 'assets', g.MODEL)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(encoded)
    path.with_name(path.stem + '00.skin').write_bytes(write_skin(packed))
    glue = g.male_only_glue(glue_data.decode('utf-8-sig'))
    ast.parse(glue)
    (STAGE / 'CharacterCreate.lua').write_text(glue, encoding='utf-8', newline='\n')
    g.save(STAGE / 'changes.json', {'landing': landing, 'glue_provider': provider, 'protected': protected})
    from test_gnoll_cloak_landing import check
    check()


def stage(validate=None, include_creator=True):
    if validate is None:
        from test_gnoll_cloak_landing import check
        validate = check
    validate()
    storm = p.Storm(p.DLL_DEFAULT)
    files = {}
    archives = (g.ASSET_ARCHIVE, p.GLOBAL_ARCHIVE_REL, p.LOCALE_ARCHIVE_REL) if include_creator else (g.ASSET_ARCHIVE,)
    relatives = (*archives, Path('EsteriaAppearanceGeometry.bin'))
    before = {str(relative): p.sha256(p.CLIENT_DEFAULT / relative) for relative in relatives}
    for relative in archives:
        target = STAGE / 'client' / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p.CLIENT_DEFAULT / relative, target)
        updates = ({g.MODEL: g.local(STAGE / 'assets', g.MODEL).read_bytes(),
                    g.MODEL[:-3] + '00.skin': g.local(STAGE / 'assets', g.MODEL[:-3] + '00.skin').read_bytes()}
                   if relative == g.ASSET_ARCHIVE else {GLUE: (STAGE / 'CharacterCreate.lua').read_bytes()})
        storm.replace_archive_entries(target, updates)
        handle = storm.open_archive(target)
        try:
            assert all(storm.read(handle, key) == value for key, value in updates.items())
        finally:
            storm.dll.SFileCloseArchive(handle)
        files[str(relative)] = str(target)
    catalog = (p.CLIENT_DEFAULT / 'EsteriaAppearanceGeometry.bin').read_bytes()
    magic, version, count = struct.unpack_from('<3I', catalog)
    at, rows, changed = 12, [], 0
    for _ in range(count):
        path = catalog[at:at + 128].split(b'\0')[0].decode()
        size = struct.unpack_from('<I', catalog, at + 128)[0]
        row = catalog[at:at + 132 + size]
        if path.lower() == g.MODEL.lower():
            skin = g.local(STAGE / 'assets', g.MODEL[:-3] + '00.skin').read_bytes()
            row = catalog[at:at + 128] + struct.pack('<I', len(skin)) + skin
            changed += 1
        rows.append(row)
        at += 132 + size
    assert changed == 1 and at == len(catalog) and (magic, version) == (0x4D474145, 1)
    target = STAGE / 'EsteriaAppearanceGeometry.bin'
    target.write_bytes(catalog[:12] + b''.join(rows))
    files[target.name] = str(target)
    assert all(p.sha256(p.CLIENT_DEFAULT / name) == digest for name, digest in before.items())
    protected = p.load_json(STAGE / 'changes.json')['protected']
    assert all(p.sha256(p.CLIENT_DEFAULT / name) == digest for name, digest in protected.items())
    report = {'files': files, 'before': before,
              'after': {name: p.sha256(Path(path)) for name, path in files.items()},
              'exe_sha256': p.sha256(p.CLIENT_DEFAULT / 'Wow.exe'),
              'protected': protected}
    g.save(STAGE / 'stage.json', report)
    print(f'PASS {len(files)} staged client files and archive readbacks; other geometry retained')


def install():
    from test_gnoll_cloak_landing import check
    check()
    equipment.STAGE = STAGE
    equipment.install()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare', 'stage', 'install'))
    globals()[parser.parse_args().action]()
