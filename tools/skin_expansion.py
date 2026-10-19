"""Prepare additive skin art and the female Tuskarr atlas gate without packing or installing.

The existing Tarasek tool workspace supplies the pinned converter and source configuration.
All game art and receipts remain outside Git. Existing converted inputs must match on rerun.
"""

import argparse
import copy
import hashlib
import json
from pathlib import Path
import struct

import tarasek_drakkin as t
import creature_race_pack as common
import drakonid_race_pack as d
from PIL import Image
from wotlkconv.blp import Blp, convert_blp
from wotlkconv.blp.bcn import encode_bc1, encode_bc2, encode_bc3
from wotlkconv.casc.config import BuildInfo
from wotlkconv.options import Options

WORK = Path('G:/RetroPorterWork/skin-expansion')
HD = Path('G:/Downloads/HDWoWModels/Dragmarsh/DragonmashDragonkin/Models')
TUSKARR = Path('G:/RetroPorterWork/tuskarr')
PORTRAIT = Path('R:/Users/Zach/Pictures/Portraits/Charactercreate-races_tuskarr-female.png')
EXPANSIONS = (('drakonid_alliance', 69, 5, d.SKINS), ('drakonid_horde', 70, 5, d.SKINS),
              ('drakkin_alliance', 66, 6, t.SKINS))
DRAKONID = (
    ('drakonid2_white', 'Vanilla/white.blp'),
    ('drakonid2_olive', 'Vanilla/olive.blp'),
    ('drakonid2_chromatic', 'Vanilla/chromatwi.blp'),
    ('drakonid2_twilight', 'Boss/twilight.blp'),
    ('drakonid2_void', 'Nether/drakonid2_void.blp'),
    ('drakonid2_azure', 'Nether/drakonid2_blue.blp'),
    ('drakonid2_teal', 'Nether/drakonid2_green.blp'),
    ('drakonid2_indigo', 'Boss/darkblue.blp'),
    ('drakonid2_darkteal', 'Boss/darkgreen.blp'),
    ('drakonid2_umber', 'Boss/darkblack.blp'),
    ('drakonid2_charcoal', 'Nether/drakonid2_black.blp'),
    ('drakonid2_abyss', 'Varad/drakonid2_void.blp'),
)
FEMALE_SLOTS = (tuple((4039141, 4039142, *range(4039147, 4039152))),
                tuple(range(4039143, 4039147)), tuple(range(4050209, 4050213)))


def digest(blob):
    return hashlib.sha256(blob).hexdigest()


def pin(path, blob):
    common.immutable(path, blob)


def valid_dxt(blob, dimensions):
    """Check actual spans: the converter parser tolerates truncated source mip chains."""
    texture = Blp.parse(blob)
    assert (texture.width, texture.height) == dimensions
    assert texture.compression == 2 and texture.alpha_type in (0, 1, 7)
    count = max(dimensions).bit_length()
    assert texture.has_mips and texture.mip_count == count
    offsets = struct.unpack_from('<16I', blob, 20)
    sizes = struct.unpack_from('<16I', blob, 84)
    end = 1172
    for level in range(count):
        width, height = max(1, texture.width >> level), max(1, texture.height >> level)
        size = ((width + 3) // 4) * ((height + 3) // 4) * (8 if texture.alpha_type == 0 else 16)
        assert offsets[level] == end and sizes[level] == size
        end += size
        assert end <= len(blob)
        texture.decode_level(level)
    assert not any(offsets[count:]) and not any(sizes[count:]) and end == len(blob)
    return texture


def complete_dxt(blob, dimensions):
    """Preserve authored blocks and generate only missing terminal mip levels."""
    source = Blp.parse(blob)
    assert (source.width, source.height) == dimensions
    assert source.compression == 2 and source.alpha_type in (0, 1, 7)
    count = max(dimensions).bit_length()
    assert 1 < source.mip_count <= count
    result = copy.deepcopy(source)
    image = source.decode_level(source.mip_count - 1)
    encoder = {0: encode_bc1, 1: encode_bc2, 7: encode_bc3}[source.alpha_type]
    while len(result.mips) < count:
        image = image.halve()
        result.mips.append(encoder(image.data, image.width, image.height))
    output = result.serialize()
    checked = valid_dxt(output, dimensions)
    assert checked.mips[:source.mip_count] == source.mips
    return output, count - source.mip_count


def prepare():
    rows = []
    entries = [(HD / 'Drakonid' / source,
                d.WORK / 'converted/patch-root/custom/drakonid/creature/drakonid2' / (name + '.blp'),
                (1024, 512)) for name, source in DRAKONID]
    entries.append((HD / 'Tarasek/Textures/purple_felorcwarrioraxe.blp',
                    t.MODEL_SOURCE.parent / 'tarasek_purple.blp', (512, 512)))
    # Validate the entire input set before writing any converted inputs.
    prepared = []
    for source, destination, dimensions in entries:
        original = source.read_bytes()
        output, repaired = complete_dxt(original, dimensions)
        if destination.exists():
            assert destination.read_bytes() == output, 'Converted input occupied: ' + str(destination)
        prepared.append((destination, output))
        rows.append({'source': str(source), 'source_sha256': digest(original),
                     'destination': str(destination), 'sha256': digest(output), 'bytes': len(output),
                     'dimensions': dimensions, 'missing_mips_generated': repaired,
                     'authored_mips_preserved': True})
    for destination, output in prepared:
        pin(destination, output)
    t.save(WORK / 'hd-skins.json', {'assets': rows, 'installed': False, 'packaged': False})
    print('Prepared', len(rows), 'validated DXT skins; existing indexes and authored blocks preserved')


def config():
    """Update only skin options; retain later Tarasek eyes and every other race/profile."""
    for slug, names in (('drakonid_alliance', d.SKINS), ('drakonid_horde', d.SKINS),
                        ('drakkin_alliance', t.SKINS)):
        path = t.p.manifest_path(slug)
        manifest = t.p.load_json(path)
        profile = manifest['appearance']['profiles']['0']
        old = profile['options'][0]['choices']
        assert list(names[:len(old)]) == old, 'Installed skin indexes changed: ' + slug
        profile['options'][0]['choices'] = list(names)
        profile['capacities'][0] = len(names)
        if 'descriptors' in profile:
            assert profile['descriptors'][0][0::2] == [0, 1]
            profile['descriptors'][0][1] = len(names)
        t.save(path, manifest)
    common.header()
    print('Updated skin manifests and generated header; no allocation or saved-character migration')


def grow_table(blob, name, allocation):
    """Append skin rows in owned free IDs, preserving all existing rows and string offsets."""
    from ogre_furbolg_race_pack import order_charsections_entry

    table = t.p.RawWdbc(blob)
    rows, pool = list(table.records), bytearray(table.strings)
    used = {t.p._value(row, 0) for row in rows}
    for slug, race, old_count, skins in EXPANSIONS:
        race_at, sex_at = (4, 8) if name == 'CharSections' else (148, 152)
        own = [r for r in table.records if t.p._value(r, race_at) == race and t.p._value(r, sex_at) == 0]
        assert own, (name, race)
        low, high = allocation['race_allocations'][slug][name]
        free = iter(i for i in range(low, high + 1) if i not in used)
        if name == 'CharSections':
            templates = [r for r in own if t.p._value(r, 36) == 0 and t.p._value(r, 12) in (0, 1, 4)]
            assert templates
        else:
            templates = [r for r in own if t.p._value(r, 4) == 3 and t.p._value(r, 156) == 0]
            assert len(templates) == 1
        for color in range(old_count, len(skins)):
            for template in templates:
                variation = t.p._value(template, 32) if name == 'CharSections' else 0
                kind = t.p._value(template, 12) if name == 'CharSections' else 3
                assert not any((t.p._value(r, 12), t.p._value(r, 32), t.p._value(r, 36)) ==
                               (kind, variation, color) for r in own) if name == 'CharSections' else not any(
                                   t.p._value(r, 4) == 3 and t.p._value(r, 156) == color for r in own)
                identifier = next(free, None)
                assert identifier is not None, (slug, name, 'allocation exhausted')
                row = t.p._replace(template, 0, 4, identifier)
                row = t.p._replace(row, 36 if name == 'CharSections' else 156, 4, color)
                if race == 66 and name == 'CharSections' and kind == 0:
                    row = t.p._set_string(row, 4, pool,
                        'custom\\tarasek\\creature\\tarasek\\tarasek_' + skins[color] + '.blp')
                rows.append(row)
                used.add(identifier)
    result = table.build(rows, bytes(pool))
    if name == 'CharSections':
        result = order_charsections_entry(t.p.DBC_ROOT + name + '.dbc', result)
    return result


def grow_appearance(blob):
    magic, version, count = struct.unpack_from('<3I', blob)
    assert (magic, version) == (0x50504145, 2) and len(blob) == 12 + count * 2316
    result, changed = bytearray(blob), set()
    for at in range(12, len(blob), 2316):
        race, gender = struct.unpack_from('<2I', blob, at)
        if gender == 0 and race in (66, 69, 70):
            expected, total = (6, len(t.SKINS)) if race == 66 else (5, len(d.SKINS))
            assert struct.unpack_from('<3I', blob, at + 12) == (0x28, expected, 1)
            struct.pack_into('<I', result, at + 16, total)
            changed.add(race)
    assert changed == {66, 69, 70}
    return bytes(result)


def grow_selections(blob, tarasek=False):
    magic, version, count = struct.unpack_from('<3I', blob)
    assert (magic, version) == (0x314D4845, 1) and len(blob) == 12 + count * 156
    rows = [blob[at:at + 156] for at in range(12, len(blob), 156)]
    originals = [r for r in rows if struct.unpack_from('<3I', r) == (0, 1, 11)
                 and struct.unpack_from('<I', r, 16)[0] == 0]
    assert len(originals) == (7 if tarasek else 1), 'Unexpected installed skin/eye selectors'
    names = ('purple',) if tarasek else tuple(name for name, _ in DRAKONID)
    for index, name in enumerate(names, 6 if tarasek else 5):
        for original in originals:
            row = bytearray(original)
            struct.pack_into('<I', row, 16, index << 16)
            path = original[28:].split(b'\0')[0].decode()
            prefix = 'tarasek_white' if tarasek else 'drakonid2_blue'
            replacement = 'tarasek_' + name if tarasek else name
            assert prefix in path
            path = path.replace(prefix, replacement).encode()
            assert len(path) < 128
            row[28:] = path.ljust(128, b'\0')
            rows.append(bytes(row))
    return struct.pack('<3I', magic, version, len(rows)) + b''.join(rows)


def stage():
    """Incremental loose stage from current winning data, retaining Tarasek refinements and later races."""
    import tarasek_refinements as refinements

    target = WORK / 'stage'
    baseline = WORK / 'baseline'
    receipt = {'state': 'loose_integration_staged', 'installed': False, 'packaged': False,
               'native_built': False, 'server_built': False, 'live_accepted': False,
               'client': str(t.p.CLIENT_DEFAULT), 'before': {}, 'after': {}, 'providers': {}}

    def write(relative, before, after, destination=target):
        pin(baseline / relative, before)
        path = destination / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(after)
        receipt['before'][relative] = digest(before)
        receipt['after'][str(path)] = digest(after)

    allocation = t.p.load_json(t.p.ALLOCATION_PATH)
    files = t.p.ClientFiles(str(t.p.CLIENT_DEFAULT / 'Data'), 'enUS')
    try:
        for name in ('CharSections', 'BarberShopStyle'):
            key = t.p.DBC_ROOT + name + '.dbc'
            blob, provider = files.find(key)
            write('client/' + key.replace('\\', '/'), blob, grow_table(blob, name, allocation))
            receipt['providers'][key] = str(provider)
            blob = (t.p.SERVER_DBC_ROOT / (name + '.dbc')).read_bytes()
            write('server/' + name + '.dbc', blob, grow_table(blob, name, allocation))
        # The existing iris-only generator owns the eye masks; use an isolated work/stage for purple.
        for key in (t.MODEL, t.MODEL[:-3] + '00.skin'):
            pin(baseline / 'purple-eyes' / key, files.find(key)[0])
        previous = refinements.BASE, refinements.STAGE, refinements.WORK
        try:
            refinements.BASE = baseline / 'purple-eyes'
            refinements.STAGE, refinements.WORK = target, WORK / 'purple-eyes'
            refinements.eyes(('purple',))
        finally:
            refinements.BASE, refinements.STAGE, refinements.WORK = previous
    finally:
        files.close()
    for name, transform in (('EsteriaAppearance.bin', grow_appearance),
                            ('EsteriaDrakonid.bin', grow_selections),
                            ('EsteriaTarasek.bin', lambda blob: grow_selections(blob, True))):
        blob = (t.p.CLIENT_DEFAULT / name).read_bytes()
        write('catalogs/' + name, blob, transform(blob))
    for row in t.p.load_json(WORK / 'hd-skins.json')['assets']:
        source = Path(row['destination'])
        assert t.p.sha256(source) == row['sha256']
        key = d.texture_path(source.stem) if source.stem.startswith('drakonid') else str(
            t.PureWindowsPath(t.MODEL).parent / source.name)
        pin(target / 'assets' / key, source.read_bytes())
    for path in (target / 'assets').rglob('*'):
        if path.is_file():
            receipt['after'][str(path)] = t.p.sha256(path)
    receipt['source_files'] = {name: t.p.sha256(t.REPO / name) for name in (
        'tools/skin_expansion.py', 'tools/drakonid_race_pack.py', 'tools/tarasek_drakkin.py',
        'src/server/shared/CreatureAppearance.h')}
    t.save(WORK / 'stage.json', receipt)
    print('Staged incremental DBCs, catalogs, 13 skins and six purple eye variants; no MPQ/build/install')


def acquire_tuskarr():
    common.STAGE = WORK / 'source-stage'
    expected = json.loads((TUSKARR / 'reports/source-pin.json').read_text())
    assert expected['version'] == '12.1.0.69933'
    current = BuildInfo.load(common.DEFAULT.retail_root, 'wow')
    assert all(getattr(current, key) == expected[key] for key in ('product', 'version', 'build_key'))
    # Distribution metadata can refresh while the pinned content build remains identical.
    source = common.Source({**expected, 'cdn_key': current.cdn_key})
    assets = []
    try:
        pin(WORK / 'tuskarr/source-pin.json', (json.dumps(source.pin, indent=2) + '\n').encode())
        for slot, ids in enumerate(FEMALE_SLOTS, 1):
            for fid in ids:
                raw = WORK / 'tuskarr/raw' / (str(fid) + '.blp')
                blob = source.read(fid, raw)
                name = source.listfile.path_for(fid)
                output, result = convert_blp(blob, name or str(fid) + '.blp', Options())
                assert output and result.ok, result.as_dict()
                destination = WORK / 'tuskarr/converted' / (str(fid) + '.blp')
                pin(destination, output)
                texture = Blp.parse(output)
                for level in range(texture.mip_count):
                    texture.decode_level(level)
                decoded = texture.decode_level()
                preview = WORK / 'tuskarr/atlases' / (str(fid) + '.png')
                preview.parent.mkdir(parents=True, exist_ok=True)
                Image.frombytes('RGBA', (decoded.width, decoded.height), bytes(decoded.data)).save(preview)
                assets.append({'file_data_id': fid, 'slot': slot, 'logical_name': name,
                    'content_key': source.storage.root.ckey_for(fid).hex(),
                    'raw': str(raw), 'raw_sha256': digest(blob), 'converted': str(destination),
                    'sha256': digest(output), 'dimensions': [texture.width, texture.height],
                    'encoding': texture.encoding_name, 'mips': texture.mip_count, 'preview': str(preview),
                    'conversion': result.as_dict()})
                t.save(WORK / 'tuskarr/acquisition.json', {'source_pin': source.pin, 'assets': assets,
                    'original_source_pin': expected,
                    'portrait': str(PORTRAIT), 'atlas_fit': 'unverified', 'installed': False})
                print('ACQUIRED female Tuskarr', fid, texture.width, texture.height, flush=True)
    finally:
        source.close()


def preview_tuskarr():
    """Export each acquired atlas on the actual player UVs, with the male skin as control."""
    import sethrak_equipment_repair as equipment
    from wotlkconv.m2 import parse_m2, parse_skin

    report = t.p.load_json(WORK / 'tuskarr/acquisition.json')
    model_path = TUSKARR / 'integration/patch-root/custom/tuskarr/native/male/tuskarrmale.m2'
    model = parse_m2(model_path.read_bytes())
    skin_path = model_path.with_name('tuskarrmale00.skin')
    skin = parse_skin(skin_path.read_bytes())
    vertices = [equipment.vertex_record(model, i) for i in range(model.vertex_count)]
    meshes = []
    for row in skin.submeshes:
        geo = struct.unpack_from('<H', row)[0]
        if geo in (10000, 101, 401, 501):
            meshes.append({'geoset': geo, 'triangles': equipment.mesh_triangles(skin, row)})
    used = {i for mesh in meshes for face in mesh['triangles'] for i in face}
    low = [min(vertices[i]['position'][axis] for i in used) for axis in range(3)]
    high = [max(vertices[i]['position'][axis] for i in used) for axis in range(3)]
    center = [(a + b) / 2 for a, b in zip(low, high)]
    size = max(b - a for a, b in zip(low, high))
    textures = [(str(a['file_data_id']), Path(a['preview'])) for a in report['assets']]
    male = TUSKARR / 'output/patch-root/custom/tuskarr/character/tuskarr/male/tuskarrmaleskin00_00.blp'
    image = Blp.parse(male.read_bytes()).decode_level()
    control = WORK / 'tuskarr/atlases/male-control.png'
    Image.frombytes('RGBA', (image.width, image.height), bytes(image.data)).save(control)
    textures.insert(0, ('male-control', control))
    for name, texture in textures:
        parts = [dict(mesh, texture=str(texture)) for mesh in meshes]
        scene = {'vertices': vertices, 'meshes': parts,
                 'camera': [center[0] + size * 1.5, center[1] - size * 2, center[2] + size * .3],
                 'target': center, 'scale': size * 1.3}
        t.save(WORK / 'tuskarr/previews' / name / 'model.json', scene)
    t.save(WORK / 'tuskarr/preview-sources.json', {'model': str(model_path),
        'model_sha256': t.p.sha256(model_path), 'skin_sha256': t.p.sha256(skin_path),
        'control': str(male), 'control_sha256': t.p.sha256(male),
        'geosets': [mesh['geoset'] for mesh in meshes], 'portrait': str(PORTRAIT),
        'note': 'Bare player mesh in bind pose, same UVs/material for every candidate; offline gate only.'})
    print('Exported', len(textures), 'player-UV scenes including the male control')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare', 'config', 'stage', 'acquire-tuskarr', 'preview-tuskarr'))
    args = parser.parse_args()
    globals()[args.action.replace('-', '_')]()
