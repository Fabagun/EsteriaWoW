"""Resolve NPC 183829 and pin its exact Retail asset closure in isolated scratch storage."""
import tarasek_drakkin as context

import argparse
import copy
from dataclasses import asdict
import hashlib
import json
import struct
from pathlib import Path, PureWindowsPath

import creature_race_pack as common
from wotlkconv.casc.config import BuildInfo
from wotlkconv.db.db2 import parse_db2
from wotlkconv.db.dbd import DbdIndex

ROOT = context.WORK
NPC = 183829


def save(name, value):
    common.immutable(ROOT / name, (json.dumps(value, indent=2) + '\n').encode())


def discover():
    definitions = DbdIndex(common.DEFAULT.dbd_dir)
    tables = {}
    for name in ('Creature', 'CreatureDisplayInfo', 'CreatureModelData', 'CreatureDisplayInfoExtra'):
        path = ROOT / 'retail-db2/dbfilesclient' / (name.lower() + '.db2')
        table = parse_db2(path.read_bytes(), str(path), definitions, name)
        assert table.named, (name, table.layout_hash)
        tables[name] = table
    npc = tables['Creature'].rows[NPC]
    displays = [tables['CreatureDisplayInfo'].rows[d] for d in npc['DisplayID'] if d]
    models = [tables['CreatureModelData'].rows[d['ModelID']] for d in displays]
    extras = [tables['CreatureDisplayInfoExtra'].rows[d['ExtendedDisplayInfoID']]
              for d in displays if d.get('ExtendedDisplayInfoID')]
    report = {'npc_id': NPC, 'creature': npc, 'displays': displays, 'models': models, 'extras': extras,
              'tables': {n: {'layout_hash': f'{t.layout_hash:08X}', 'rows': len(t.rows),
                            'skipped_records': t.skipped_records} for n, t in tables.items()},
              'source_pin': asdict(BuildInfo.load(common.DEFAULT.retail_root, 'wow'))}
    assert len(displays) == len(models) and models
    save('reports/discovery.json', report)
    print(json.dumps(report, indent=2), flush=True)


def extract():
    common.STAGE = ROOT / 'stages'
    pin = asdict(BuildInfo.load(common.DEFAULT.retail_root, 'wow'))
    source = common.Source(pin)
    try:
        for name in ('creature', 'creaturedisplayinfo', 'creaturemodeldata', 'creaturedisplayinfoextra'):
            fid = source.listfile.id_for('dbfilesclient/' + name + '.db2')
            assert fid, name
            source.read(fid, ROOT / 'retail-db2/dbfilesclient' / (name + '.db2'), database=True)
            print('DATABASE', name, fid, flush=True)
    finally:
        source.close()


def acquire():
    discovery = json.loads((ROOT / 'reports/discovery.json').read_text())
    common.STAGE = ROOT / 'stages'
    source = common.Source(discovery['source_pin'])
    try:
        save('source-pin.json', source.pin)
        queue = [(m['FileDataID'], '.m2') for m in discovery['models']]
        for display in discovery['displays']:
            queue.extend((fid, '.blp') for fid in display['TextureVariationFileDataID'] if fid)
        queue.extend((source.listfile.id_for('creature/tarasek/tarasek_' + color + '.blp'), '.blp')
                     for color in ('white', 'black', 'blue', 'bronze', 'green', 'red'))
        inventory, edges, missing = {}, [], []
        while queue:
            fid, hint = queue.pop(0)
            if str(fid) in inventory or any(row['file_data_id'] == fid for row in missing):
                continue
            name = source.listfile.path_for(fid)
            suffix = PureWindowsPath(name).suffix if name else hint
            path = ROOT / 'raw' / (str(fid) + suffix.lower())
            try:
                data = source.read(fid, path)
            except (OSError, ValueError) as error:
                missing.append({'file_data_id': fid, 'role': hint, 'error': str(error)})
                print('MISSING', fid, str(error), flush=True)
                continue
            refs = common.references(data, suffix.lower() == '.skel') if suffix.lower() in ('.m2', '.skel') else []
            inventory[str(fid)] = {'file_data_id': fid, 'logical_name': name, 'path': str(path),
                                  'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(),
                                  'content_key': source.storage.root.ckey_for(fid).hex(), 'dependencies': refs}
            for dependency, role in refs:
                edges.append({'owner': fid, 'dependency': dependency, 'role': role})
                queue.append((dependency, {'TXID': '.blp', 'SFID': '.skin', 'AFID': '.anim',
                                          'BFID': '.bone', 'SKID': '.skel', 'SKPD': '.skel'}[role]))
            common.save(ROOT / 'reports/acquisition-progress.json',
                        {'assets': inventory, 'edges': edges, 'missing': missing, 'pending': len(queue)})
            if len(inventory) % 10 == 0:
                print('ACQUIRED', len(inventory), 'pending', len(queue), flush=True)
        save('reports/inventory-palettes.json', {'source_pin': source.pin, 'assets': inventory,
                                      'edges': edges, 'missing': missing})
        assert not missing, missing
        assert all(str(e['dependency']) in inventory for e in edges)
        print('SOURCE CLOSURE COMPLETE', len(inventory), flush=True)
    finally:
        source.close()


def convert():
    from wotlkconv.listfile import Listfile
    from wotlkconv.resolve import AssetSource
    from wotlkconv.options import Options
    from wotlkconv.m2 import convert_m2, parse_m2, parse_skin, write_md20
    from wotlkconv.blp import convert_blp
    import highmountain_complete_tracks as tracks
    import vrykul_female_pack as arrays
    import sethrak_animation_pack as animations
    import skyborne_visual_pack as visual

    inventory = json.loads((ROOT / 'reports/inventory-palettes.json').read_text())
    assert not inventory['missing']
    for row in inventory['assets'].values():
        assert hashlib.sha256(Path(row['path']).read_bytes()).hexdigest() == row['sha256']
    listing = Listfile.load(common.DEFAULT.listfile)
    source = AssetSource(listing, [ROOT / 'raw'])
    options = Options(path_prefix='custom\\tarasek', strict_limits=True)
    output = ROOT / 'converted/patch-root/custom/tarasek/creature/tarasek'
    output.mkdir(parents=True, exist_ok=True)
    data, result, companions = convert_m2((ROOT / 'raw/4485357.m2').read_bytes(),
        'creature/tarasek/tarasek.m2', options, listing, source)
    common.save(ROOT / 'reports/conversion.json', {'model': result.as_dict(),
        'companions': [a.result.as_dict() for a in companions]})
    assert result.ok and data and all(a.result.ok and a.data for a in companions)
    (output / 'tarasek.m2').write_bytes(data)
    for asset in companions:
        (output / asset.filename).write_bytes(asset.data)
    model = visual.read_player_model(output / 'tarasek.m2')
    tracks.embed(model, output, 'tarasek')
    payload, separated = arrays.separate_bone_track_arrays(write_md20(model))
    (output / 'tarasek.m2').write_bytes(payload)
    rebuilt = parse_m2(payload)
    assert rebuilt.vertices == model.vertices and rebuilt.version == 264
    assert all(not t.external for t in rebuilt.tracks())
    required = animations.ACTIONS
    animations.ACTIONS = tuple(a for a in required if a in {s['id'] for s in rebuilt.sequences})
    try:
        animations.check_model(rebuilt, payload)
    finally:
        animations.ACTIONS = required
    textures = []
    for row in inventory['assets'].values():
        if not row['path'].lower().endswith('.blp'):
            continue
        blob, report = convert_blp(Path(row['path']).read_bytes(), row['logical_name'], options)
        assert blob and report.ok, report
        logical = PureWindowsPath(row['logical_name'])
        path = ROOT / 'converted/patch-root/custom/tarasek' / Path(*logical.parts)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(blob)
        textures.append({'file_data_id': row['file_data_id'], 'path': str(path),
                         'sha256': hashlib.sha256(blob).hexdigest()})
    skin = parse_skin((output / 'tarasek00.skin').read_bytes())
    assert all(v < rebuilt.vertex_count for v in skin.vertices)
    assert all(i < len(skin.vertices) for i in skin.indices)
    actions = sorted({q['id'] for q in rebuilt.sequences})
    geosets = sorted({struct.unpack_from('<H', row)[0] for row in skin.submeshes})
    report = {'state': 'art_converted_awaiting_player_repairs', 'model': str(output / 'tarasek.m2'),
              'model_sha256': hashlib.sha256(payload).hexdigest(), 'vertices': rebuilt.vertex_count,
              'bones': len(rebuilt.bones), 'sequences': len(rebuilt.sequences), 'actions': actions,
              'missing_player_actions': sorted(set(animations.ACTIONS) - set(actions)),
              'geosets': geosets, 'attachments': [a['id'] for a in rebuilt.attachments],
              'textures': textures, 'shared_bone_track_arrays_separated': separated,
              'armor_support_complete': False, 'installed': False}
    common.save(ROOT / 'reports/model-audit.json', report)
    print(json.dumps(report, indent=2), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('extract', 'discover', 'acquire', 'convert'))
    args = parser.parse_args()
    globals()[args.action]()
