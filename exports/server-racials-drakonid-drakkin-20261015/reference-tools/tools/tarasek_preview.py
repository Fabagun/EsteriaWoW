"""Export actual staged Tarasek meshes with representative installed armor for offline rendering."""
import copy
import json
from pathlib import Path

import tarasek_drakkin as t
import tarasek_equipment as e
from PIL import Image
from wotlkconv.blp import Blp
from wotlkconv.m2 import parse_m2, parse_skin
import creature_animation_repair as motion

REGIONS = ('ArmUpperTexture', 'ArmLowerTexture', 'HandTexture', 'TorsoUpperTexture',
           'TorsoLowerTexture', 'LegUpperTexture', 'LegLowerTexture', 'FootTexture')
RECTS = ((0, 0, 256, 128), (0, 128, 256, 256), (0, 256, 256, 320), (256, 0, 512, 128),
         (256, 128, 512, 192), (256, 192, 512, 320), (256, 320, 512, 448), (256, 448, 512, 512))


def export():
    model_path = Path(t.p.load_json(e.WORK / 'report.json')['model'])
    model = parse_m2(model_path.read_bytes())
    skin = parse_skin(model_path.with_name('tarasek00.skin').read_bytes())
    files = t.p.ClientFiles(str(t.p.CLIENT_DEFAULT / 'Data'), 'enUS')
    table = t.p.RawWdbc(t.read_baseline('ItemDisplayInfo'))
    displays = {t.p._value(row, 0): row for row in table.records}
    scenarios = {'naked': ((), 0, 0), 'shirt': ((18924,), 0, 0),
                 'plate': ((25749, 24513, 1795, 8054), 0, 0), 'robe': ((15820,), 0, 0),
                 'run': ((25749, 24513), 5, .25), 'fishing': ((), 133, .5),
                 'cast': ((15820,), 51, .5), 'cloak': ((), 0, 0), 'cloak-run': ((), 5, .25)}
    sources = {}
    try:
        for name, (ids, action, phase) in scenarios.items():
            root = t.WORK / 'previews' / name
            root.mkdir(parents=True, exist_ok=True)
            atlas = Image.new('RGBA', (512, 512))
            selected = {0, 3301}
            if ids:
                selected.update(range(20001, 20009))
            for identifier in ids:
                row = displays[identifier]
                for region, rect in enumerate(RECTS):
                    stem = t.p._string(table.strings, t.p._value(row, (15 + region) * 4)).decode()
                    if not stem:
                        continue
                    base = 'Item\\TextureComponents\\' + REGIONS[region] + '\\' + stem
                    for suffix in ('_M.blp', '_U.blp', '.blp'):
                        try:
                            blob, provider = files.find(base + suffix)
                            break
                        except FileNotFoundError:
                            continue
                    else:
                        raise FileNotFoundError(base)
                    image = Blp.parse(blob).decode_level(0)
                    art = Image.frombytes('RGBA', (image.width, image.height), bytes(image.data))
                    atlas.alpha_composite(art.resize((rect[2] - rect[0], rect[3] - rect[1])), rect[:2])
                    sources[base + suffix] = {'provider': str(provider), 'sha256': t.sha(blob)}
                values = [t.p._value(row, (7 + k) * 4) for k in range(3)]
                has = lambda r: bool(t.p._string(table.strings, t.p._value(row, (15 + r) * 4)))
                if has(7):
                    selected.add(501 + values[0])
                if has(3):
                    selected.add(801 + values[0])
                    selected.add(1301 + values[1])
                if has(5):
                    selected.add(901 + values[0])
                    selected.add(1301 + values[1])
            atlas.save(root / 'clothing.png')
            if name in ('robe', 'cast'):
                selected.add(1302)
            cape = None
            if name.startswith('cloak'):
                selected.add(1502)
                blob, provider = files.find('Item\\ObjectComponents\\Cape\\Cape_Cloth_B_02Green.blp')
                image = Blp.parse(blob).decode_level(0)
                cape = root / 'cape.png'
                Image.frombytes('RGBA', (image.width, image.height), bytes(image.data)).save(cape)
            records = [e.equipment.vertex_record(model, i) for i in range(model.vertex_count)]
            at = round(model.sequences[motion.sequence(model, action)]['duration'] * phase)
            posed = motion.posed_vertices(model, motion.pose_matrices(model, action, at))
            for record, point in zip(records, posed, strict=True):
                record['position'] = list(map(float, point))
            parts = []
            for i, row in enumerate(skin.submeshes):
                geo = e.visual.u16(row, 0)
                if geo not in selected:
                    continue
                batch = next(b for b in skin.batches if e.visual.u16(b, 4) == i)
                slot = model.textures[model.texture_combos[e.visual.u16(batch, 16)]]['type']
                path = cape if slot == 2 else root / 'clothing.png' if slot == 14 else \
                    t.WORK / 'preview/tarasek_white.png'
                assert path is not None
                parts.append({'geoset': geo, 'triangles': e.equipment.mesh_triangles(skin, row), 'texture': str(path)})
            t.save(root / 'model.json', {'vertices': records, 'meshes': parts,
                'camera': [6, -9, 4.5], 'target': [-.45, 0, 1.25], 'scale': 3.8})
    finally:
        files.close()
    base = t.p.load_json(t.WORK / 'previews/naked/model.json')
    for i, name in enumerate(t.SKINS):
        scene = copy.deepcopy(base)
        for part in scene['meshes']:
            part['texture'] = str(t.WORK / 'preview' / ('tarasek_' + name + '.png'))
        t.save(t.WORK / 'previews' / ('skin-' + name) / 'model.json', scene)
    for i in range(5):
        scene = copy.deepcopy(base)
        scene['meshes'] = [part for part in scene['meshes'] if part['geoset'] == 0]
        row = next(row for row in skin.submeshes if e.visual.u16(row, 0) == 3301 + i)
        scene['meshes'].append({'geoset': 3301 + i, 'triangles': e.equipment.mesh_triangles(skin, row),
                               'texture': str(t.WORK / 'preview/tarasek_white.png')})
        scene.update(camera=[5, -8, 3.2], target=[.3, 0, 2.3], scale=1.8)
        t.save(t.WORK / 'previews' / ('horn-' + str(i + 1)) / 'model.json', scene)
    t.save(t.WORK / 'reports/preview-sources.json', sources)
    print('Exported', len(scenarios) + len(t.SKINS) + 5, 'scenes with actual installed armor textures')


def refresh():
    path = Path(t.p.load_json(e.WORK / 'report.json')['model'])
    model = parse_m2(path.read_bytes())
    skin = parse_skin(path.with_name('tarasek00.skin').read_bytes())
    for root in (t.WORK / 'previews').iterdir():
        if root.name.startswith('helmet-'):
            continue
        source = root / 'model.json'
        if not source.exists():
            continue
        scene = t.p.load_json(source)
        if root.name in ('robe', 'cast') and not any(part['geoset'] == 1302 for part in scene['meshes']):
            for row in skin.submeshes:
                if e.visual.u16(row, 0) == 1302:
                    scene['meshes'].append({'geoset': 1302, 'triangles': e.equipment.mesh_triangles(skin, row),
                                           'texture': str(root / 'clothing.png')})
        action, phase = (5, .25) if root.name in ('run', 'cloak-run') else (133, .5) \
            if root.name == 'fishing' else (51, .5) if root.name == 'cast' else (0, 0)
        at = round(model.sequences[motion.sequence(model, action)]['duration'] * phase)
        points = motion.posed_vertices(model, motion.pose_matrices(model, action, at))
        records = [e.equipment.vertex_record(model, i) for i in range(model.vertex_count)]
        for record, point in zip(records, points, strict=True):
            record['position'] = list(map(float, point))
        scene['vertices'] = records
        t.save(source, scene)


if __name__ == '__main__':
    import sys
    refresh() if sys.argv[1:] == ['refresh'] else export()
