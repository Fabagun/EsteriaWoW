"""Acquire immutable Shadowguard candidates and audit source geometry and skeleton ancestry."""

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

WORK = Path('G:/RetroportWork/ethereal-shadowguard')
NATIVE = Path(__file__).resolve().parents[2] / 'wowdecomp'
PROBE = NATIVE / 'build/retail-satchel/Release/RetailAssetProbe.exe'
CONFIG = NATIVE / 'build/retail-research/RetailCasc.ini'
LISTFILE = Path('G:/ListFiles/community-listfile.csv')
MODELS = {5926159: 'ethereal_male', 6152557: 'ethereal_female', 6254042: 'dreadnaught',
          1814471: 'nightborne_male', 1810676: 'nightborne_female'}
PORTRAIT = 1711337


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8', newline='\n')


def acquire(full=False):
    config = dict(line.strip().split('=', 1) for line in CONFIG.read_text().splitlines()
                  if '=' in line and not line.lstrip().startswith(('#', ';')))
    if config.get('product') != 'wow' or config.get('build') != BUILD:
        raise ValueError('Retail source pin changed; audit the new build before acquisition')
    names = {}
    with LISTFILE.open(encoding='utf-8-sig') as source:
        for line in source:
            identifier, name = line.rstrip().split(';', 1)
            names[int(identifier)] = name
    pending = {(identifier, 'm2') for identifier in MODELS}
    if full:
        pending.add((PORTRAIT, 'blp'))
        pending.update((identifier, 'blp') for identifier, name in names.items()
                       if name.startswith(('creature/ethereal2_m/', 'creature/ethereal2_f/',
                                           'creature/shadowguardmech/')) and name.endswith('.blp'))
    completed, assets, edges = set(), {}, []
    inventory = WORK / ('inventory.json' if full else 'geometry-inventory.json')
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
            path.with_suffix('.acquire.log').write_text(result.stdout + result.stderr, encoding='utf-8')
            result.check_returncode()
        raw = path.read_bytes()
        if not raw:
            raise ValueError('Empty original: ' + str(path))
        completed.add((identifier, extension))
        assets[str(identifier)] = {'path': str(path), 'logical_name': names.get(identifier),
                                  'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
        if extension in ('m2', 'skel'):
            dependencies = references(raw)
            if not full:
                dependencies = {(child, ext) for child, ext in dependencies if ext in ('skin', 'skel')}
            pending.update(dependencies - completed)
            edges.extend({'parent': identifier, 'child': child, 'extension': ext}
                         for child, ext in sorted(dependencies))
        save(inventory, {'build': BUILD, 'product': 'wow', 'complete': not pending,
                         'scope': 'full' if full else 'geometry_and_skeletons',
                         'npc_mapping_verified': False, 'assets': assets, 'edges': edges})
        print(f'ACQUIRED {identifier}.{extension}: {len(raw)} bytes; {len(pending)} pending', flush=True)
    report = audit()
    recorded = json.loads(inventory.read_text())
    recorded['npc_mapping_verified'] = report['npc_mapping_verified']
    save(inventory, recorded)


def audit():
    report = {'build': BUILD, 'npc_ids': [247577, 246331], 'npc_mapping_verified': False, 'models': {}}
    if (WORK / 'npc-display-resolution.json').exists():
        graph = json.loads((WORK / 'npc-display-resolution.json').read_text())
        npcs = json.loads((WORK / 'npc-resolution.json').read_text())
        assert npcs['build'] == BUILD
        for npc, expected in ((247577, {5926159, 6152557}), (246331, {6254042})):
            displays = [value for value in npcs['npcs'][str(npc)]['DisplayID'] if value]
            assert {graph[str(display)]['model']['FileDataID'] for display in displays} == expected
        report['npc_mapping_verified'] = True
    for identifier, name in MODELS.items():
        raw = (WORK / 'source' / f'{identifier}.m2').read_bytes()
        model = parse_m2(raw)
        dependencies = references(raw)
        skeletons = sorted(value for value, ext in dependencies if ext == 'skel')
        chain, visited = [], set()
        while skeletons:
            skel_id = skeletons.pop()
            if skel_id in visited:
                raise ValueError('Cyclic skeleton ancestry')
            visited.add(skel_id)
            skeleton = parse_skel((WORK / 'source' / f'{skel_id}.skel').read_bytes())
            chain.append(skeleton)
            if skeleton.parent_skel_file_id:
                skeletons.append(skeleton.parent_skel_file_id)
        rig = next((entry for entry in chain if entry.bones), model)
        sequences = {sequence['id'] for entry in [model, *chain] for sequence in entry.sequences}
        skins = {}
        for skin_id, extension in sorted(dependencies):
            if extension != 'skin':
                continue
            skin = parse_skin((WORK / 'source' / f'{skin_id}.skin').read_bytes())
            skins[str(skin_id)] = dict(Counter(struct.unpack_from('<H', mesh)[0] for mesh in skin.submeshes))
        report['models'][name] = {'file_data_id': identifier, 'vertices': model.vertex_count,
            'skeleton_ancestry': sorted(visited), 'bones': len(rig.bones), 'sequence_ids': sorted(sequences),
            'socket_ids': sorted({a['id'] for entry in [model, *chain] for a in entry.attachments}),
            'texture_types': [texture['type'] for texture in model.textures], 'skins': skins,
            'bone_crc': [bone['bone_name_crc'] for bone in rig.bones]}
    for sex in ('male', 'female'):
        ethereal, donor = (report['models'][prefix + sex] for prefix in ('ethereal_', 'nightborne_'))
        donor_crcs = set(donor['bone_crc']) - {0}
        ethereal['nightborne_named_bone_matches'] = sum(crc in donor_crcs for crc in ethereal['bone_crc'])
        ethereal['missing_nightborne_actions'] = sorted(set(donor['sequence_ids']) - set(ethereal['sequence_ids']))
    save(WORK / 'source-audit.json', report)
    print('AUDITED immutable originals:', WORK / 'source-audit.json', flush=True)
    return report


def self_check():
    from slime_giant_source import self_check as check_dependencies
    check_dependencies()
    assert set(MODELS.values()) == {'ethereal_male', 'ethereal_female', 'dreadnaught',
                                  'nightborne_male', 'nightborne_female'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('geometry', 'acquire', 'audit', 'self-check'))
    args = parser.parse_args()
    self_check()
    if args.action in ('geometry', 'acquire'):
        acquire(args.action == 'acquire')
    elif args.action == 'audit':
        audit()
    else:
        print('PASS original dependency bounds and model roles')
