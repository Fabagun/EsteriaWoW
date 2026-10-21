"""Acquire and audit original Slime Giant assets through wowdecomp's pinned CASC reader.

Writes only the requested work directory and the configured CASC cache. No conversion, build,
client installation, SQL application, or race allocation is performed.
"""

import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import shutil

from wotlkconv.m2 import parse_m2, parse_skin
from wotlkconv.m2.skel import parse_skel

BUILD = '88d5e8ef05ec5a8446cdec93d142d7c6'
MODELS = {3490792: 3491636}
PALETTES = {name: (3490792, 3491663 + 2 * index, 3491664 + 2 * index)
            for index, name in enumerate(('green', 'amber', 'mauve', 'red', 'gold'))}
DONOR = (1721003, 1721013, 2175552)


def chunks(data):
    offset = 0
    while offset < len(data):
        if offset + 8 > len(data):
            raise ValueError('Truncated chunk header')
        tag, size = struct.unpack_from('<4sI', data, offset)
        offset += 8
        if size > len(data) - offset:
            raise ValueError('Truncated chunk payload')
        yield tag, data[offset:offset + size]
        offset += size


def references(data):
    result = set()
    for tag, payload in chunks(data):
        if tag in (b'SFID', b'TXID', b'SKID'):
            extension = {b'SFID': 'skin', b'TXID': 'blp', b'SKID': 'skel'}[tag]
            if len(payload) % 4:
                raise ValueError('Invalid dependency array')
            result.update((value, extension) for value, in struct.iter_unpack('<I', payload) if value)
        elif tag == b'AFID':
            if len(payload) % 8:
                raise ValueError('Invalid animation dependency array')
            result.update((value, 'anim') for _, _, value in struct.iter_unpack('<HHI', payload) if value)
        elif tag == b'SKPD' and len(payload) >= 12:
            value = struct.unpack_from('<I', payload, 8)[0]
            if value:
                result.add((value, 'skel'))
    return result


def acquire(probe, config, work):
    values = dict(line.strip().split('=', 1) for line in config.read_text().splitlines()
                  if '=' in line and not line.lstrip().startswith(('#', ';')))
    if values.get('product') != 'wow' or values.get('build') != BUILD:
        raise ValueError('Source must remain pinned to Retail ' + BUILD)
    source = work / 'correct-source'
    source.mkdir(parents=True, exist_ok=True)
    pending = {(model, 'm2') for model in MODELS}
    pending.update((value, 'blp') for palette in PALETTES.values() for value in palette[1:])
    pending.update(zip(DONOR, ('m2', 'skin', 'skel')))
    completed = set()
    while pending:
        file_id, extension = min(pending)
        pending.remove((file_id, extension))
        if (file_id, extension) in completed:
            continue
        path = source / f'{file_id}.{extension}'
        previous = work / 'source' / path.name
        if not path.exists() and previous.exists():
            shutil.copy2(previous, path)
            assert path.read_bytes() == previous.read_bytes(), 'Original copy differs'
        if not path.exists():
            command = [str(probe), str(config), f'retail/{file_id}.{extension}', '--extract', str(path)]
            result = subprocess.run(command, text=True, capture_output=True, check=True)
            (source / f'{file_id}.acquire.log').write_text(result.stdout + result.stderr, encoding='utf-8')
        data = path.read_bytes()
        if not data:
            raise ValueError('Empty source: ' + str(path))
        completed.add((file_id, extension))
        # Kul Tiran is a fitting donor: acquire its body, primary SKIN and full SKEL ancestry only.
        # Slime Giant bodies need their complete original model dependency graphs.
        if extension == 'skel' or (extension == 'm2' and file_id in MODELS):
            pending.update(references(data) - completed)
        print(f'Original {file_id}.{extension}: {len(data)} bytes', flush=True)
    return audit(work)


def audit(work):
    source = work / 'correct-source'
    report = {'source_build': BUILD, 'npc_id': 175382, 'npc_display_mapping_verified': False,
              'selection_basis': 'User-corrected reference image: SlimeSkeleton',
              'palettes': PALETTES, 'models': {}, 'originals': {}}
    donor = parse_skel((source / '2175552.skel').read_bytes())
    donor_crcs = {bone['bone_name_crc'] for bone in donor.bones if bone['bone_name_crc']}
    for model_id, skin_id in MODELS.items():
        model = parse_m2((source / f'{model_id}.m2').read_bytes())
        skin = parse_skin((source / f'{skin_id}.skin').read_bytes())
        sections = []
        for index, row in enumerate(skin.submeshes):
            geoset, _, start, count = struct.unpack_from('<4H', row)
            vertices = skin.vertices[start:start + count]
            if len(vertices) != count or not vertices or max(vertices) >= model.vertex_count:
                raise ValueError('Invalid source mesh vertex range')
            points = [struct.unpack_from('<3f', model.vertices, vertex * 48) for vertex in vertices]
            sections.append({'ordinal_zero_based': index, 'geoset_id': geoset, 'vertices': count,
                             'bounds': [[min(p[axis] for p in points), max(p[axis] for p in points)]
                                        for axis in range(3)]})
        sockets = {entry['id'] for entry in model.attachments}
        report['models'][str(model_id)] = {
            'bones': len(model.bones), 'sequences': len(model.sequences),
            'kul_tiran_crc_matches': sum(b['bone_name_crc'] in donor_crcs for b in model.bones),
            'texture_types': [texture['type'] for texture in model.textures],
            'socket_ids': sorted(sockets), 'missing_equipment_sockets': sorted({5, 6, 11, 12} - sockets),
            'sections': sections,
        }
    for path in sorted(source.iterdir()):
        if path.suffix not in ('.m2', '.skin', '.skel', '.anim', '.blp'):
            continue
        data = path.read_bytes()
        report['originals'][path.name] = {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
    path = work / 'source-audit.json'
    path.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8', newline='\n')
    print('Source audit: ' + str(path), flush=True)
    return report


def self_check():
    payload = struct.pack('<4sI2I', b'SFID', 8, 42, 0)
    assert references(payload) == {(42, 'skin')}
    for malformed in (payload[:-1], b'SFID'):
        try:
            references(malformed)
        except ValueError:
            continue
        raise AssertionError('Truncated graph accepted')
    assert not references(struct.pack('<4sI', b'TXID', 0))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('acquire', 'audit', 'self-check'))
    parser.add_argument('--work', type=Path, default=Path('G:/RetroportWork/slime-giant-175382'))
    parser.add_argument('--probe', type=Path)
    parser.add_argument('--config', type=Path)
    args = parser.parse_args()
    self_check()
    if args.action == 'acquire':
        if not args.probe or not args.config:
            parser.error('acquire requires --probe and --config')
        acquire(args.probe, args.config, args.work)
    elif args.action == 'audit':
        audit(args.work)
    else:
        print('PASS dependency parser bounds and zero-ID handling')
