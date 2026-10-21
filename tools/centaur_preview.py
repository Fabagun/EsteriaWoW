"""Render isolated Centaur bare-body and real plate-overlay previews; never launch a client."""

import json
from pathlib import Path
import struct
import subprocess

from PIL import Image
from wotlkconv.blp import Blp
from wotlkconv.m2 import parse_m2, parse_skin
from sethrak_equipment_repair import mesh_triangles, vertex_record
from centaur_clothing import WORK, BLENDER


def export():
    renderer = WORK / 'preview/render.py'
    renderer.parent.mkdir(parents=True, exist_ok=True)
    code = Path('tools/gnoll_preview_blender.py').read_text()
    code = code.replace('camera.location = (5, -7, 2.7)', 'camera.location = (5, -7, 3.7)')
    code = code.replace('Vector((.6, 0, 1.62))', 'Vector((.92, 0, 2.85))')
    renderer.write_text(code, encoding='utf-8', newline='\n')
    plate = Path('G:/RetroportWork/slime-giant-175382/correct-fit/preview/armor-hd.png')
    if (WORK / 'repair-v2/lightbringer-armor.png').exists():
        plate = WORK / 'repair-v2/lightbringer-armor.png'
    assert Image.open(plate).size == (2048, 1024), 'Preview must use the actual layout-141 equipment sheet'
    for sex, model_id, skin_id, body_id in ((0, 4036647, 4036674, 4036659), (1, 4081379, 4081384, 4081391)):
        root = WORK / 'preview' / str(sex)
        root.mkdir(parents=True, exist_ok=True)
        image = Blp.parse((WORK / 'source' / f'{body_id}.blp').read_bytes()).decode_level(0)
        texture = root / 'body.png'
        Image.frombytes('RGBA', (image.width, image.height), bytes(image.data)).save(texture)
        image = Blp.parse((WORK / 'source' / f'{4081389 if sex else 4036660}.blp').read_bytes()).decode_level(0)
        native_top = root / 'outfit.png'
        Image.frombytes('RGBA', (image.width, image.height), bytes(image.data)).save(native_top)
        for equipped in (False, True):
            output = root / ('plate' if equipped else 'bare')
            output.mkdir(exist_ok=True)
            vertices, meshes = [], []
            for model_path, skin_path, clothing in (
                    (WORK / 'source' / f'{model_id}.m2', WORK / 'source' / f'{skin_id}.skin', False),
                    (WORK / 'stage/assets/custom/centaur' / f'{model_id}-clothing.m2',
                     WORK / 'stage/assets/custom/centaur' / f'{model_id}-clothing00.skin', True)):
                if clothing and not equipped:
                    continue
                model, skin = parse_m2(model_path.read_bytes()), parse_skin(skin_path.read_bytes())
                choices = {1, 401, 802, 1801, 2002} if clothing else ({0, 101, 201, 701} if sex else {0, 701})
                mapping = {}
                for ordinal, row in enumerate(skin.submeshes):
                    geoset = struct.unpack_from('<H', row)[0]
                    if geoset not in choices:
                        continue
                    types = {model.textures[model.texture_combos[struct.unpack_from('<H', b, 16)[0]]]['type']
                             for b in skin.batches if struct.unpack_from('<H', b, 4)[0] == ordinal}
                    triangles = mesh_triangles(skin, row)
                    for tri in triangles:
                        for index in tri:
                            if index not in mapping:
                                mapping[index] = len(vertices)
                                vertices.append(vertex_record(model, index))
                    meshes.append({'geoset': geoset, 'triangles': [[mapping[i] for i in tri] for tri in triangles],
                                   'texture': str(plate if clothing else native_top if types == {12} else texture)})
            data = {'vertices': vertices, 'meshes': meshes, 'camera': [5, -7, 3.5], 'target': [.1, 0, 1.6], 'scale': 3.9}
            (output / 'model.json').write_text(json.dumps(data), encoding='utf-8')
            subprocess.run([str(BLENDER), '--background', '--factory-startup', '--python-exit-code', '1',
                            '--python', str(renderer), '--', str(output)], check=True,
                           stdout=(output / 'render.log').open('w'), stderr=subprocess.STDOUT)


if __name__ == '__main__':
    export()
