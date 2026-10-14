"""Render staged Sethrak equipment in Blender without touching the installed client."""

import json
from pathlib import Path
import sys

import bpy
from mathutils import Vector

ROOT = Path(sys.argv[sys.argv.index('--') + 1])


def material(path, transparent=False):
    result = bpy.data.materials.new(Path(path).stem)
    result.use_nodes = True
    nodes = result.node_tree.nodes
    image = nodes.new('ShaderNodeTexImage')
    image.image = bpy.data.images.load(path, check_existing=True)
    shader = nodes.get('Principled BSDF')
    shader.inputs['Roughness'].default_value = 0.7
    result.node_tree.links.new(image.outputs['Color'], shader.inputs['Base Color'])
    if transparent:
        result.node_tree.links.new(image.outputs['Alpha'], shader.inputs['Alpha'])
    return result


sexes = sys.argv[sys.argv.index('--') + 2:] or ('male', 'female')
for sex in sexes:
    work = json.loads((ROOT / (sex + '-preview.json')).read_text())
    for mode in work.get('preview_modes', ('base', 'shirt', 'plate', 'robe')):
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.delete(use_global=False)
        groups = {0, 401, 501, 1301, 1801, 20102}
        if mode == 'plate':
            # Reproduce bulk leggings hiding the default pants and boot surfaces.
            groups = {0, 401, 903, 1104, 1801, 20102}
        elif mode == 'robe':
            groups = {0, 401, 1302, 1801, 20102}
        groups = set(work.get('preview_groups', {}).get(mode, groups))
        objects = []
        for index, part in enumerate(work['meshes']):
            if part['geoset'] not in groups or part['texture_type'] == 2:
                continue
            if mode == 'robe' and part.get('native_group') in (38, 43):
                continue
            mesh = bpy.data.meshes.new('Piece')
            mesh.from_pydata([v['position'] for v in work['vertices']], [], part['triangles'])
            mesh.update()
            layer = mesh.uv_layers.new(name='UVMap')
            for poly in mesh.polygons:
                poly.use_smooth = True
                for loop in poly.loop_indices:
                    u, v = work['vertices'][mesh.loops[loop].vertex_index]['uv']
                    layer.data[loop].uv = (u, 1 - v)
            obj = bpy.data.objects.new('Piece', mesh)
            bpy.context.collection.objects.link(obj)
            path = (work['base_atlas'] if mode == 'base' else work['gear_textures'][mode])
            if part['texture_type'] != 1:
                path = work['textures'][str(part['texture'])]
            mesh.materials.append(material(path, part.get('transparent', False)))
            objects.append(obj)
        bpy.ops.object.camera_add(location=(5, -7, 3.2))
        camera = bpy.context.object
        direction = Vector((-0.25, 0, 1.25)) - camera.location
        camera.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
        camera.data.type = 'ORTHO'
        camera.data.ortho_scale = 3.9
        scene = bpy.context.scene
        scene.camera = camera
        scene.render.engine = 'CYCLES'
        scene.cycles.samples = 16
        scene.world.color = (0.15, 0.15, 0.15)
        for location, power in (((3, -4, 5), 700), ((-3, 2, 4), 550)):
            bpy.ops.object.light_add(type='AREA', location=location)
            lamp = bpy.context.object
            lamp.data.energy = power
            lamp.data.shape = 'DISK'
            lamp.data.size = 5
        scene.render.resolution_x = 512
        scene.render.resolution_y = 640
        scene.render.resolution_percentage = 100
        scene.view_settings.view_transform = 'Standard'
        scene.render.filepath = str(ROOT / (sex + '-render-' + mode + '.png'))
        bpy.ops.render.render(write_still=True)
        print('RENDERED', sex, mode, flush=True)
