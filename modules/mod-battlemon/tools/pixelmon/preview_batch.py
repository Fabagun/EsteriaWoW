"""Render decoded exported batch models as a labeled review sheet (Blender background script)."""
import argparse
import json
from pathlib import Path
import sys

import bpy
from mathutils import Vector

parser = argparse.ArgumentParser()
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
output = args.output.resolve()
report = json.loads((output/'report.json').read_text())
preview = output/'preview'
preview.mkdir(exist_ok=True)
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.samples = 8
scene.cycles.use_denoising = True
scene.render.resolution_x = scene.render.resolution_y = 256
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.world.color = (0.15, 0.15, 0.15)
scene.view_settings.view_transform = 'Standard'
bpy.ops.object.camera_add()
camera = bpy.context.object
camera.data.type = 'ORTHO'
scene.camera = camera
lamps = []
for direction, energy in [((3, -4, 6), 900), ((-4, 2, 5), 600), ((5, 5, 4), 700)]:
    bpy.ops.object.light_add(type='AREA')
    lamp = bpy.context.object
    lamp.data.energy, lamp.data.shape, lamp.data.size = energy, 'DISK', 4
    lamps.append((lamp, Vector(direction)))
for record in report['records']:
    if record['shiny'] or record['status'] != 'passed':
        continue
    asset = record['result']['asset']
    data = json.loads((preview/'data'/(asset+'.json')).read_text())
    mesh = bpy.data.meshes.new(asset)
    mesh.from_pydata(data['positions'], [], data['triangles'])
    mesh.update()
    uv = mesh.uv_layers.new()
    for polygon in mesh.polygons:
        polygon.use_smooth = True
        for loop in polygon.loop_indices:
            u, v = data['uv'][mesh.loops[loop].vertex_index]
            uv.data[loop].uv = (u, 1-v)
    obj = bpy.data.objects.new(asset, mesh)
    bpy.context.collection.objects.link(obj)
    material = bpy.data.materials.new(asset)
    material.use_nodes = True
    nodes, links = material.node_tree.nodes, material.node_tree.links
    shader = nodes.get('Principled BSDF')
    shader.inputs['Roughness'].default_value = 0.8
    texture = nodes.new('ShaderNodeTexImage')
    texture.image = bpy.data.images.load(str(preview/'data'/data['texture']))
    links.new(texture.outputs['Color'], shader.inputs['Base Color'])
    if record['result'].get('texture_policy') == 'source_alpha_blend':
        links.new(texture.outputs['Alpha'], shader.inputs['Alpha'])
    obj.data.materials.append(material)
    points = [Vector(point) for point in data['positions']]
    mn = Vector(tuple(min(p[i] for p in points) for i in range(3)))
    mx = Vector(tuple(max(p[i] for p in points) for i in range(3)))
    center, span = (mn+mx)/2, max(mx-mn)
    camera.location = center+Vector((3, -2, 1.6))*span
    camera.rotation_euler = (center-camera.location).to_track_quat('-Z', 'Y').to_euler()
    camera.data.ortho_scale = span*1.55
    for lamp, direction in lamps:
        lamp.location = center+direction
        lamp.rotation_euler = (center-lamp.location).to_track_quat('-Z', 'Y').to_euler()
    scene.render.filepath = str(preview/(str(record['form'])+'.png'))
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.meshes.remove(mesh)
    bpy.data.images.remove(texture.image)
    bpy.data.materials.remove(material)
    print('PREVIEW: '+record['name'], flush=True)
