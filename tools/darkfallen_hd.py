"""Acquire and convert the Retail HD Blood Elf player bodies as the Darkfallen base model.

Stage 1 only: pins the exact Retail closure (M2, SKIN, ANIM, BONE, SKEL, textures) and converts it
with the pinned wotlkconv. Nothing is renamed, integrated, packaged or installed here.
"""
import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path, PureWindowsPath

import creature_race_pack as common
from wotlkconv.casc.config import BuildInfo

ROOT = Path('G:/RetroPorterWork/darkfallen-hd')
MODELS = {'male': 1100087, 'female': 1100258}  # character/bloodelf/<sex>/bloodelf<sex>_hd.m2
SUFFIX = {'TXID': '.blp', 'SFID': '.skin', 'AFID': '.anim', 'BFID': '.bone', 'SKID': '.skel', 'SKPD': '.skel'}


def save(name, value):
    path = ROOT / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + '\n')


def acquire():
    common.STAGE = ROOT / 'stages'
    source = common.Source(asdict(BuildInfo.load(common.DEFAULT.retail_root, 'wow')))
    inventory, edges, missing = {}, [], []
    try:
        save('source-pin.json', source.pin)
        queue = [(fid, '.m2') for fid in MODELS.values()]
        seen = set()
        while queue:
            fid, hint = queue.pop(0)
            if fid in seen:
                continue
            seen.add(fid)
            name = source.listfile.path_for(fid)
            suffix = (PureWindowsPath(name).suffix if name else hint).lower()
            path = ROOT / 'raw' / (str(fid) + suffix)
            try:
                data = source.read(fid, path)
            except (OSError, ValueError) as error:
                missing.append({'file_data_id': fid, 'role': hint, 'error': str(error)})
                print('MISSING', fid, hint, str(error)[:100], flush=True)
                continue
            refs = common.references(data, suffix == '.skel') if suffix in ('.m2', '.skel') else []
            inventory[str(fid)] = {'file_data_id': fid, 'logical_name': name, 'path': str(path),
                                  'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(),
                                  'content_key': source.storage.root.ckey_for(fid).hex(),
                                  'dependencies': refs}
            for dependency, role in refs:
                edges.append({'owner': fid, 'dependency': dependency, 'role': role})
                queue.append((dependency, SUFFIX[role]))
            if len(inventory) % 20 == 0:
                print('ACQUIRED', len(inventory), 'pending', len(queue), flush=True)
        save('reports/inventory.json', {'source_pin': source.pin, 'assets': inventory, 'edges': edges,
                                        'missing': missing})
        print('CLOSURE', len(inventory), 'assets,', len(missing), 'missing', flush=True)
    finally:
        source.close()


def convert():
    from wotlkconv.listfile import Listfile
    from wotlkconv.resolve import AssetSource
    from wotlkconv.options import Options
    from wotlkconv.m2 import convert_m2, parse_m2, parse_skin

    inventory = json.loads((ROOT / 'reports/inventory.json').read_text())
    assert not inventory['missing']
    for row in inventory['assets'].values():
        assert hashlib.sha256(Path(row['path']).read_bytes()).hexdigest() == row['sha256']
    listing = Listfile.load(common.DEFAULT.listfile)
    source = AssetSource(listing, [ROOT / 'raw'])
    options = Options(path_prefix='custom\\darkfallenhd', strict_limits=True)
    report = {}
    for sex, fid in MODELS.items():
        name = inventory['assets'][str(fid)]['logical_name'].replace('\\', '/')
        output = ROOT / 'converted/patch-root/custom/darkfallenhd/character/bloodelf' / sex
        output.mkdir(parents=True, exist_ok=True)
        try:
            data, result, companions = convert_m2((ROOT / 'raw' / (str(fid) + '.m2')).read_bytes(), name,
                                                  options, listing, source)
        except Exception as error:  # report every failure; this is an acquisition-stage survey
            report[sex] = {'error': repr(error)[:600]}
            print(sex, 'FAILED', repr(error)[:400], flush=True)
            continue
        report[sex] = {'result': result.as_dict(), 'ok': bool(result.ok and data),
                       'companions': [{'name': a.filename, 'ok': a.result.ok} for a in companions]}
        if data:
            (output / Path(name).name).write_bytes(data)
            for asset in companions:
                if asset.data:
                    (output / asset.filename).write_bytes(asset.data)
            model = parse_m2(data)
            report[sex].update(vertices=model.vertex_count, bones=len(model.bones),
                               sequences=len(model.sequences), version=model.version)
        print(sex, json.dumps({k: v for k, v in report[sex].items() if k != 'result'})[:500], flush=True)
    save('reports/conversion.json', report)


def repair():
    """Player-body repairs proven on Tarasek: embed external tracks, separate bone track arrays, audit."""
    import shutil
    import struct
    import highmountain_complete_tracks as tracks
    import sethrak_animation_pack as animations
    import skyborne_visual_pack as visual
    import vrykul_female_pack as arrays
    from wotlkconv.m2 import parse_m2, parse_skin, write_md20

    report = {}
    for sex in MODELS:
        source = ROOT / 'converted/patch-root/custom/darkfallenhd/character/bloodelf' / sex
        output = ROOT / 'repaired' / sex
        if output.exists():
            shutil.rmtree(output)
        shutil.copytree(source, output)
        stem = 'bloodelf%s_hd' % sex
        model = visual.read_player_model(output / (stem + '.m2'))
        tracks.embed(model, output, stem)
        payload, separated = arrays.separate_bone_track_arrays(write_md20(model))
        (output / (stem + '.m2')).write_bytes(payload)
        rebuilt = parse_m2(payload)
        assert rebuilt.vertices == model.vertices and rebuilt.version == 264
        assert all(not t.external for t in rebuilt.tracks())
        actions = sorted({q['id'] for q in rebuilt.sequences})
        required = animations.ACTIONS
        missing = sorted(set(required) - set(actions))
        animations.ACTIONS = tuple(a for a in required if a in actions)
        try:
            animations.check_model(rebuilt, payload)
        finally:
            animations.ACTIONS = required
        skin = parse_skin((output / (stem + '00.skin')).read_bytes())
        assert all(v < rebuilt.vertex_count for v in skin.vertices)
        geosets = sorted({struct.unpack_from('<H', row)[0] for row in skin.submeshes})
        report[sex] = {'model_sha256': hashlib.sha256(payload).hexdigest(), 'bytes': len(payload),
                       'vertices': rebuilt.vertex_count, 'bones': len(rebuilt.bones),
                       'sequences': len(rebuilt.sequences), 'missing_player_actions': missing,
                       'geosets': geosets, 'attachments': [a['id'] for a in rebuilt.attachments],
                       'textures': len(rebuilt.textures) if hasattr(rebuilt, 'textures') else None}
        print(sex, json.dumps({k: v for k, v in report[sex].items() if k != 'geosets'}), flush=True)
        print('  geosets', geosets, flush=True)
    save('reports/repair.json', report)


def extract_db2():
    common.STAGE = ROOT / 'stages'
    source = common.Source(asdict(BuildInfo.load(common.DEFAULT.retail_root, 'wow')))
    try:
        for name in ('ChrModel', 'ChrRaces', 'ChrCustomizationOption', 'ChrCustomizationChoice',
                     'ChrCustomizationElement', 'ChrCustomizationMaterial', 'ChrCustomizationGeoset',
                     'ChrCustomizationSkinnedModel', 'ChrCustomizationDisplayInfo', 'ChrCustomizationReq',
                     'ChrCustomizationReqChoice', 'ChrCustomizationBone', 'ChrCustomizationElementCondition',
                     'TextureFileData', 'CreatureDisplayInfo', 'CreatureModelData'):
            fid = source.listfile.id_for('dbfilesclient/' + name.lower() + '.db2')
            if not fid:
                print('NOLISTFILE', name)
                continue
            try:
                source.read(fid, ROOT / 'db2' / (name.lower() + '.db2'), database=True)
                print('DATABASE', name, fid, flush=True)
            except (OSError, ValueError) as error:
                print('FAILED', name, str(error)[:100])
    finally:
        source.close()


HAIR_COLORS = 10  # v1: first ten retail hair colours per style
CHR_MODELS = {'male': 19, 'female': 20}


def tables(*names):
    from wotlkconv.db.db2 import parse_db2
    from wotlkconv.db.dbd import DbdIndex
    definitions = DbdIndex(common.DEFAULT.dbd_dir)
    result = {}
    for name in names:
        path = ROOT / 'db2' / (name.lower() + '.db2')
        result[name] = parse_db2(path.read_bytes(), str(path), definitions, name)
    return result


def hair_plan():
    """{sex: {'styles': [(name, geoset)], 'colors': [name], 'files': {(style, color): fileDataID}}}"""
    t = tables('ChrCustomizationOption', 'ChrCustomizationChoice', 'ChrCustomizationElement',
               'ChrCustomizationMaterial', 'ChrCustomizationGeoset', 'TextureFileData')
    files = {}
    for row in t['TextureFileData'].rows.values():
        files.setdefault(row['MaterialResourcesID'], []).append(row)
    plan = {}
    for sex, model in CHR_MODELS.items():
        options = {o['Name_lang']: o for o in t['ChrCustomizationOption'].rows.values() if o['ChrModelID'] == model}
        def choices(option):
            return sorted((c for c in t['ChrCustomizationChoice'].rows.values()
                           if c['ChrCustomizationOptionID'] == option['ID']), key=lambda c: c['OrderIndex'])
        styles, colors = choices(options['Hair Style']), choices(options['Hair Color'])[:HAIR_COLORS]
        color_index = {c['ID']: i for i, c in enumerate(colors)}
        elements = {}
        for element in t['ChrCustomizationElement'].rows.values():
            elements.setdefault(element['ChrCustomizationChoiceID'], []).append(element)
        out = {'styles': [], 'colors': [c.get('Name_lang') for c in colors], 'files': {}}
        # The hair mesh texture (texture target 10) comes from the Hair Color choice and is style independent;
        # the per-style target-12 material is only a scalp overlay for the body atlas, which v1 omits.
        color_file = {}
        for color, choice in enumerate(colors):
            for element in elements.get(choice['ID'], []):
                if element['ChrCustomizationMaterialID']:
                    resource = t['ChrCustomizationMaterial'].rows[element['ChrCustomizationMaterialID']]
                    assert resource['ChrModelTextureTargetID'] == 10, resource
                    candidates = files[resource['MaterialResourcesID']]
                    assert len(candidates) == 1, candidates
                    color_file[color] = candidates[0]['FileDataID']
        assert sorted(color_file) == list(range(len(colors))), color_file
        for style_index, style in enumerate(styles):
            geoset = None
            for element in elements.get(style['ID'], []):
                if element['ChrCustomizationGeosetID']:
                    geoset = t['ChrCustomizationGeoset'].rows[element['ChrCustomizationGeosetID']]['GeosetID']
            out['styles'].append((style.get('Name_lang'), geoset))
            for color, fid in color_file.items():
                out['files'][(style_index, color)] = fid
        plan[sex] = out
    return plan


def hair():
    plan = hair_plan()
    common.STAGE = ROOT / 'stages'
    source = common.Source(asdict(BuildInfo.load(common.DEFAULT.retail_root, 'wow')))
    inventory = {}
    try:
        for sex, data in plan.items():
            for (style, color), fid in sorted(data['files'].items()):
                path = ROOT / 'raw-hair' / (str(fid) + '.blp')
                blob = source.read(fid, path)
                inventory['%s-%d-%d' % (sex, color, fid)] = {'file_data_id': fid, 'sex': sex, 'style': style, 'color': color,
                                       'logical_name': source.listfile.path_for(fid), 'path': str(path),
                                       'bytes': len(blob), 'sha256': hashlib.sha256(blob).hexdigest()}
        save('reports/hair.json', {'plan': {s: {'styles': d['styles'], 'colors': d['colors'],
                                               'files': {'%d,%d' % k: v for k, v in d['files'].items()}}
                                            for s, d in plan.items()}, 'assets': inventory})
        sizes = sorted({v['bytes'] for v in inventory.values()})
        print('HAIR', len(inventory), 'files; sizes', sizes[:3], sizes[-3:], 'total', sum(v['bytes'] for v in inventory.values()))
    finally:
        source.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('acquire', 'convert', 'repair', 'extract_db2', 'hair'))
    globals()[parser.parse_args().action]()
