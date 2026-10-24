"""Blender preview of decoded exported M2 geometry and BLP textures, not source BMDs."""
import argparse
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Vector

parser = argparse.ArgumentParser()
parser.add_argument('--preview', type=Path, required=True)
args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
preview = args.preview.resolve()
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.samples = 16
scene.cycles.use_denoising = True
scene.render.resolution_x = 1500
scene.render.resolution_y = 900
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.render.film_transparent = False
scene.world.color = (0.15, 0.15, 0.15)
scene.view_settings.view_transform = 'Standard'
scene.render.fps = 15
scene.frame_start, scene.frame_end = 1, 12
names = ['0001_Bulbasaur', '0004_Charmander', '0007_Squirtle', '0025_Pikachu']
for row, shiny in enumerate([False, True]):
    for column, base in enumerate(names):
        stem = base + ('_shiny' if shiny else '')
        data = json.loads((preview/(stem+'.json')).read_text())
        mesh = bpy.data.meshes.new(stem)
        mesh.from_pydata(data['poses'][0][0], [], data['triangles'])
        mesh.update()
        uv = mesh.uv_layers.new()
        for polygon in mesh.polygons:
            polygon.use_smooth = True
            for loop in polygon.loop_indices:
                u, v = data['uv'][mesh.loops[loop].vertex_index]
                uv.data[loop].uv = (u, 1-v)
        obj = bpy.data.objects.new(stem, mesh)
        bpy.context.collection.objects.link(obj)
        obj.location = ((row-0.5)*2.05, (column-1.5)*1.75, 0.07)
        material = bpy.data.materials.new(stem)
        material.use_nodes = True
        nodes = material.node_tree.nodes
        links = material.node_tree.links
        principled = nodes.get('Principled BSDF')
        principled.inputs['Roughness'].default_value = 0.82
        tex = nodes.new('ShaderNodeTexImage')
        tex.image = bpy.data.images.load(str(preview/data['texture']))
        links.new(tex.outputs['Color'], principled.inputs['Base Color'])
        cutoff = nodes.new('ShaderNodeMath')
        cutoff.operation = 'GREATER_THAN'
        cutoff.inputs[1].default_value = 0.5
        links.new(tex.outputs['Alpha'], cutoff.inputs[0])
        links.new(cutoff.outputs[0], principled.inputs['Alpha'])
        obj.data.materials.append(material)
        obj.shape_key_add(name='Exported idle')
        poses = data['poses'][1][:12]
        for index, positions in enumerate(poses):
            key = obj.shape_key_add(name=f'Exported walk {index}')
            key.data.foreach_set('co', [coordinate for vertex in positions for coordinate in vertex])
            for frame in range(1, 13):
                key.value = 1.0 if frame-1 == index else 0.0
                key.keyframe_insert('value', frame=frame)
        bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=0.70, depth=0.06,
                                            location=(obj.location.x, obj.location.y, 0.025))
        platform = bpy.context.object
        mat = bpy.data.materials.get('platform') or bpy.data.materials.new('platform')
        mat.diffuse_color = (0.15, 0.19, 0.24, 1)
        platform.data.materials.append(mat)
# Ground.
bpy.ops.mesh.primitive_plane_add(size=200)
ground = bpy.context.object
mat = bpy.data.materials.new('ground')
mat.diffuse_color = (0.035, 0.045, 0.065, 1)
ground.data.materials.append(mat)
# Arrange view so +X-facing creatures are seen from their front/side.
bpy.ops.object.camera_add(location=(8.5, -3.5, 6.5))
camera = bpy.context.object
camera.rotation_euler = (Vector((0, 0, 0.5))-camera.location).to_track_quat('-Z', 'Y').to_euler()
camera.data.type = 'ORTHO'
camera.data.ortho_scale = 7.5
scene.camera = camera
for location, energy, size in [((3, -4, 8), 1800, 5), ((-4, 2, 6), 1400, 4), ((5, 5, 4), 900, 3)]:
    bpy.ops.object.light_add(type='AREA', location=location)
    lamp = bpy.context.object
    lamp.data.energy, lamp.data.shape, lamp.data.size = energy, 'DISK', size
    lamp.rotation_euler = (Vector((0, 0, 0.5))-lamp.location).to_track_quat('-Z', 'Y').to_euler()
# Frame zero shows the unmodified exported idle pose. Frames 1-12 are exported walk samples.
scene.frame_set(0)
for obj in bpy.data.objects:
    if obj.type == 'MESH' and obj.data.shape_keys:
        for key in obj.data.shape_keys.key_blocks[1:]:
            key.value = 0
            key.keyframe_insert('value', frame=0)
bpy.ops.wm.save_as_mainfile(filepath=str(preview/'battlemon-3d.blend'))
scene.render.filepath = str(preview/'battlemon-3d-idle.png')
bpy.ops.render.render(write_still=True)
scene.frame_set(6)
scene.render.filepath = str(preview/'battlemon-3d-walk.png')
bpy.ops.render.render(write_still=True)
