"""Render a head-and-shoulders Drakonid portrait from a preview scene (model.json) in headless Blender."""
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Vector

root = Path(sys.argv[sys.argv.index('--') + 1])
work = json.loads((root / 'model.json').read_text())
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
materials = {}
for part in work['meshes']:
    mesh = bpy.data.meshes.new(str(part['geoset']))
    mesh.from_pydata([v['position'] for v in work['vertices']], [], part['triangles'])
    mesh.update()
    obj = bpy.data.objects.new(mesh.name, mesh)
    bpy.context.collection.objects.link(obj)
    uv = mesh.uv_layers.new()
    for poly in mesh.polygons:
        poly.use_smooth = True
        for loop in poly.loop_indices:
            u, v = work['vertices'][mesh.loops[loop].vertex_index]['uv']
            uv.data[loop].uv = (u, 1 - v)
    mesh.normals_split_custom_set_from_vertices([v['normal'] for v in work['vertices']])
    path = part['texture']
    if path not in materials:
        material = bpy.data.materials.new(path)
        material.use_nodes = True
        node = material.node_tree.nodes.new('ShaderNodeTexImage')
        node.image = bpy.data.images.load(path, check_existing=True)
        tree = material.node_tree
        tree.links.new(node.outputs['Color'], tree.nodes.get('Principled BSDF').inputs['Base Color'])
        tree.links.new(node.outputs['Alpha'], tree.nodes.get('Principled BSDF').inputs['Alpha'])
        materials[path] = material
    obj.data.materials.append(materials[path])
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.samples = 24
scene.world.color = (.18, .18, .18)
scene.view_settings.view_transform = 'Standard'
for position, power, size in (((4, -5, 6), 650, 5), ((-3, 3, 4), 500, 4), ((5, 5, 5), 350, 5)):
    bpy.ops.object.light_add(type='AREA', location=position)
    lamp = bpy.context.object
    lamp.data.energy, lamp.data.shape, lamp.data.size = power, 'DISK', size
    lamp.rotation_euler = (Vector((0, 0, 1)) - lamp.location).to_track_quat('-Z', 'Y').to_euler()
bpy.ops.object.camera_add(location=(0, 0, 0))
camera = bpy.context.object
camera.data.type = 'ORTHO'
camera.data.ortho_scale = 1.55
scene.camera = camera
scene.render.resolution_x = scene.render.resolution_y = 512
target = Vector((0.85, -0.2, 4.1))
cx, cy, _ = work['camera']
angle = math.atan2(cy, cx) + math.radians(20)
camera.location = (target.x + 14 * math.cos(angle), target.y + 14 * math.sin(angle), 4.6)
camera.rotation_euler = (target - camera.location).to_track_quat('-Z', 'Y').to_euler()
scene.render.filepath = str(root / 'portrait.png')
bpy.ops.render.render(write_still=True)
