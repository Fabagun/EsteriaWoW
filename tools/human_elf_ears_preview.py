"""Offline preview of the staged Human elf ears on the Retail Human head (Blender workbench).

The ear texture is painted into composed Human sheets exactly as RetailRace.cpp PaintElfEars does in the client.
Compose the sheets first with RetailComposeProbe (race 1): human<sex>-type1.png (defaults) and the TONES below.
"""

import json
from pathlib import Path
import struct
import subprocess
import sys

import numpy as np

WORK = Path('G:/RetroportWork/human-ears')
PREVIEW = WORK / 'preview'
BLENDER = Path('C:/Program Files/Blender Foundation/Blender 5.2/blender.exe')
# Default-recipe geosets (RetailRaceProbe "recipe(first choices)") without the ears.
HEAD = {0: (0, 100, 200, 300, 3202, 3400), 1: (2, 3500, 3600, 3202)}
VIEWS = {'side': ((0.32, 0.62, 0.06), 0.42), 'back': ((-0.55, 0.42, 0.10), 0.46), 'front': ((0.75, 0.0, 0.02), 0.44)}
TONES = {0: ('human0', 'live'), 1: ('human1', 'hf92')}  # default skin, then the in-game look / a darker skin
STYLES = (('human', None), ('long', 702), ('swept', 703), ('short', 704))


def paint_ears(sheet, ear):
    """Python twin of the client's PaintElfEars: detail * Human skin tone around the ear opening, blended by coverage."""
    assert ear[:4] == b'HEAR'
    x, y, w, h, n = struct.unpack_from('<5H', ear, 4)
    samples = np.frombuffer(ear, '<u2', 2 * n, 14).reshape(n, 2)
    texels = np.frombuffer(ear, np.uint8, w * h * 4, 14 + 4 * n).reshape(h, w, 4).astype(np.float64)
    tone = np.median(sheet[samples[:, 1], samples[:, 0]], axis=0)
    region = sheet[y:y + h, x:x + w]
    colour = np.clip(texels[..., :3] * tone / 128, 0, 255)
    alpha = texels[..., 3:] / 255
    sheet[y:y + h, x:x + w] = region * (1 - alpha) + colour * alpha
    return sheet


def meshes(model, skin, geosets, types):
    from sethrak_equipment_repair import mesh_triangles, vertex_record
    out = {}
    for ordinal, row in enumerate(skin.submeshes):
        geoset = struct.unpack_from('<H', row)[0]
        if geoset not in geosets:
            continue
        batches = [b for b in skin.batches if struct.unpack_from('<H', b, 4)[0] == ordinal]
        kind = {model.textures[model.texture_combos[struct.unpack_from('<H', b, 16)[0]]]['type'] for b in batches}
        texture = next(iter(kind & set(types)), None)
        if texture is None:
            continue
        tris = [[{k: vertex_record(model, i)[k] for k in ('position', 'uv', 'normal')} for i in tri]
                for tri in mesh_triangles(skin, row)]
        out.setdefault((geoset, texture), []).extend(tris)
    return out


def prepare():
    from PIL import Image
    from wotlkconv.m2 import parse_m2, parse_skin
    from human_elf_ears import MODELS, SOURCE
    job = []
    ears_root = WORK / 'stage/assets/custom/humanears'
    for sex, (human_id, skin_id, *_rest) in MODELS.items():
        human, human_skin = parse_m2((SOURCE / f'{human_id}.m2').read_bytes()), parse_skin((SOURCE / f'{skin_id}.skin').read_bytes())
        ears = parse_m2((ears_root / f'{human_id}-ears.m2').read_bytes())
        ears_skin = parse_skin((ears_root / f'{human_id}-ears00.skin').read_bytes())
        ear = (ears_root / f'{human_id}-ears.ear').read_bytes()
        head = meshes(human, human_skin, set(HEAD[sex]), (1, 6))

        for tone in TONES[sex]:
            sheet = np.asarray(Image.open(PREVIEW / f'{tone}-type1.png').convert('RGB'), dtype=np.float64)
            painted = PREVIEW / f'{tone}-type1-ears.png'
            Image.fromarray(paint_ears(sheet, ear).astype(np.uint8)).save(painted)
            textures = {1: str(painted), 6: str(PREVIEW / f'human{sex}-type6.png')}
            for name, geoset in STYLES:
                extra = meshes(human, human_skin, {702}, (1,)) if geoset is None else meshes(ears, ears_skin, {geoset}, (1,))
                parts = {**head, **{('ear',) + key: tris for key, tris in extra.items()}}
                job.append({'file': f'{sex}-{tone}-{name}', 'center': [0.0, 0.0, 1.88 if sex == 0 else 1.76],
                            'textures': textures,
                            'parts': [{'texture': key[-1], 'triangles': tris} for key, tris in parts.items()]})
    path = PREVIEW / 'render-job.json'
    path.write_text(json.dumps({'views': VIEWS, 'renders': job}))
    return path


def render(path):
    import bpy
    from mathutils import Vector
    job = json.loads(path.read_text())
    for item in job['renders']:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        scene = bpy.context.scene
        scene.render.engine = 'BLENDER_WORKBENCH'
        scene.display.shading.light = 'STUDIO'
        scene.display.shading.color_type = 'TEXTURE'
        scene.render.resolution_x = scene.render.resolution_y = 640
        materials = {}
        for texture, image in item['textures'].items():
            material = bpy.data.materials.new(texture)
            material.use_nodes = True
            node = material.node_tree.nodes.new('ShaderNodeTexImage')
            node.image = bpy.data.images.load(image)
            material.node_tree.links.new(node.outputs['Color'],
                                         material.node_tree.nodes['Principled BSDF'].inputs['Base Color'])
            materials[int(texture)] = material
        for index, part in enumerate(item['parts']):
            verts, faces, uvs = [], [], []
            for tri in part['triangles']:
                faces.append(tuple(range(len(verts), len(verts) + 3)))
                for v in tri:
                    verts.append(v['position'])
                    uvs.append((v['uv'][0], 1 - v['uv'][1]))
            mesh = bpy.data.meshes.new(f'part{index}')
            mesh.from_pydata(verts, [], faces)
            layer = mesh.uv_layers.new()
            for loop in mesh.loops:
                layer.data[loop.index].uv = uvs[loop.vertex_index]
            mesh.materials.append(materials[part['texture']])
            for polygon in mesh.polygons:
                polygon.use_smooth = True
            obj = bpy.data.objects.new(f'part{index}', mesh)
            scene.collection.objects.link(obj)
            obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.join()
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.remove_doubles(threshold=0.0001)  # weld split normals across submeshes for the preview
        bpy.ops.object.mode_set(mode='OBJECT')
        camera = bpy.data.objects.new('camera', bpy.data.cameras.new('camera'))
        scene.collection.objects.link(camera)
        scene.camera = camera
        center = Vector(item['center'])
        for view, (offset, scale) in job['views'].items():
            camera.data.type = 'ORTHO'
            camera.data.ortho_scale = scale
            camera.location = center + Vector(offset) * 3
            camera.rotation_euler = (center - camera.location).to_track_quat('-Z', 'Y').to_euler()
            scene.render.filepath = str(PREVIEW / f"{item['file']}-{view}.png")
            bpy.ops.render.render(write_still=True)


def sheet():
    from PIL import Image, ImageDraw
    rows = lambda sex: [(TONES[sex][0], view) for view in VIEWS] + [(TONES[sex][1], 'side')]
    for sex in (0, 1):
        size = Image.open(PREVIEW / f'{sex}-{TONES[sex][0]}-human-side.png').size[0]
        grid = Image.new('RGB', (size * len(STYLES), size * len(rows(sex)) + 40), 'white')
        draw = ImageDraw.Draw(grid)
        for column, (name, _) in enumerate(STYLES):
            draw.text((column * size + 10, 6), name, fill='black', font_size=28)
            for row, (tone, view) in enumerate(rows(sex)):
                grid.paste(Image.open(PREVIEW / f'{sex}-{tone}-{name}-{view}.png').convert('RGB'),
                           (column * size, 40 + row * size))
        grid.save(PREVIEW / f"sheet-{'male' if sex == 0 else 'female'}.png")


if __name__ == '__main__':
    if '--worker' in sys.argv:
        render(Path(sys.argv[sys.argv.index('--worker') + 1]))
    else:
        job = prepare()
        subprocess.run([str(BLENDER), '--background', '--factory-startup', '--python-exit-code', '1',
                        '--python', str(Path(__file__).resolve()), '--', '--worker', str(job)], check=True,
                       stdout=subprocess.DEVNULL)
        sheet()
        print('preview sheets:', *sorted(PREVIEW.glob('sheet-*.png')))
