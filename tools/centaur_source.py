"""Acquire the exact requested Retail Centaur bodies and audit their immutable dependency graph."""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import struct
import subprocess

from wotlkconv.m2 import parse_m2, parse_skin
from wotlkconv.m2.skel import parse_skel

from slime_giant_source import BUILD, references

WORK = Path('G:/RetroportWork/centaur')
MODELS = {0: 4036647, 1: 4081379}
PROBE = Path('R:/Users/Zach/Documents/GitHub/wowdecomp/build/retail-satchel/Release/RetailAssetProbe.exe')
CONFIG = Path('R:/Users/Zach/Documents/GitHub/wowdecomp/build/retail-research/RetailCasc.ini')
LISTFILE = Path('G:/ListFiles/community-listfile.csv')


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8', newline='\n')


def acquire():
    config = dict(line.split('=', 1) for line in CONFIG.read_text().splitlines() if '=' in line)
    if config.get('product') != 'wow' or config.get('build') != BUILD:
        raise ValueError('Retail source pin changed; audit the new build before acquisition')
    names = {}
    for line in LISTFILE.read_text(encoding='utf-8-sig').splitlines():
        identifier, name = line.split(';', 1)
        if name.lower().startswith(('creature/centaur2_male/', 'creature/centaur2_female/')):
            names[int(identifier)] = name
    for sex, identifier in MODELS.items():
        expected = 'creature/centaur2_' + ('female' if sex else 'male')
        if names.get(identifier) != expected + '/' + expected.split('/')[-1] + '.m2':
            raise ValueError('Requested source model identity changed')
    pending = {(identifier, 'm2') for identifier in MODELS.values()}
    # Replaceable textures are supplied by CreatureDisplayInfo, rather than the model TXID array.
    pending.update((identifier, 'blp') for identifier, name in names.items() if name.endswith('.blp'))
    completed, assets, edges = set(), {}, []
    while pending:
        identifier, extension = min(pending)
        pending.remove((identifier, extension))
        if (identifier, extension) in completed:
            continue
        path = WORK / 'source' / f'{identifier}.{extension}'
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            result = subprocess.run([str(PROBE), str(CONFIG), f'retail/{identifier}.{extension}',
                                     '--extract', str(path)], capture_output=True, text=True)
            (path.with_suffix('.acquire.log')).write_text(result.stdout + result.stderr, encoding='utf-8')
            result.check_returncode()
        data = path.read_bytes()
        if not data:
            raise ValueError('Empty source: ' + str(path))
        assets[str(identifier)] = {'path': str(path), 'logical_name': names.get(identifier),
                                  'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
        completed.add((identifier, extension))
        if extension in ('m2', 'skel'):
            deps = references(data)
            pending.update(deps - completed)
            edges.extend({'parent': identifier, 'child': child, 'extension': ext} for child, ext in sorted(deps))
        save(WORK / 'inventory.json', {'build': BUILD, 'product': 'wow', 'complete': not pending,
                                     'assets': assets, 'edges': edges})
        print(f'ACQUIRED {identifier}.{extension}: {len(data)} bytes; {len(pending)} pending', flush=True)
    audit()


def audit():
    inventory = json.loads((WORK / 'inventory.json').read_text())
    report = {'build': BUILD, 'dependency_closure_complete': inventory['complete'], 'models': {}}
    for sex, identifier in MODELS.items():
        model = parse_m2((WORK / 'source' / f'{identifier}.m2').read_bytes())
        deps = references((WORK / 'source' / f'{identifier}.m2').read_bytes())
        skeletons = [value for value, ext in deps if ext == 'skel']
        skeleton = parse_skel((WORK / 'source' / f'{skeletons[0]}.skel').read_bytes()) if skeletons else model
        chain = [skeleton]
        while getattr(chain[-1], 'parent_skel_file_id', 0):
            parent = chain[-1].parent_skel_file_id
            assert parent not in [getattr(entry, 'parent_skel_file_id', 0) for entry in chain[:-1]]
            chain.append(parse_skel((WORK / 'source' / f'{parent}.skel').read_bytes()))
        skin_ids = sorted(value for value, ext in deps if ext == 'skin')
        skin = parse_skin((WORK / 'source' / f'{skin_ids[0]}.skin').read_bytes())
        socket_ids = sorted({a['id'] for entry in [model, *chain] for a in entry.attachments})
        report['models'][str(sex)] = {'file_data_id': identifier, 'vertices': model.vertex_count,
            'bones': len(skeleton.bones), 'sequence_ids': sorted({s['id'] for entry in chain for s in entry.sequences}),
            'socket_ids': socket_ids, 'missing_equipment_sockets': sorted({1, 2, 5, 6, 11, 12} - set(socket_ids)),
            'texture_types': [t['type'] for t in model.textures],
            'geosets': dict(Counter(struct.unpack_from('<H', mesh)[0] for mesh in skin.submeshes))}
    save(WORK / 'source-audit.json', report)
    print(json.dumps(report, indent=2), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('acquire', 'audit'))
    args = parser.parse_args()
    acquire() if args.action == 'acquire' else audit()
