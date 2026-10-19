"""Render staged Tarasek scenes in a fresh headless Blender process."""
from pathlib import Path
import sys

def render(root):
    """Render the staged Tarasek meshes and a portrait without opening or modifying either game client."""

    import json
    from pathlib import Path
    import sys

    import bpy
    from mathutils import Vector


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
            material.node_tree.links.new(node.outputs['Color'],
                                         material.node_tree.nodes.get('Principled BSDF').inputs['Base Color'])
            material.node_tree.links.new(node.outputs['Alpha'],
                                         material.node_tree.nodes.get('Principled BSDF').inputs['Alpha'])
            if part.get('unlit'):
                emission = material.node_tree.nodes.new('ShaderNodeEmission')
                transparent = material.node_tree.nodes.new('ShaderNodeBsdfTransparent')
                mixed = material.node_tree.nodes.new('ShaderNodeMixShader')
                material.node_tree.links.new(node.outputs['Color'], emission.inputs['Color'])
                material.node_tree.links.new(node.outputs['Alpha'], mixed.inputs[0])
                material.node_tree.links.new(transparent.outputs[0], mixed.inputs[1])
                material.node_tree.links.new(emission.outputs[0], mixed.inputs[2])
                material.node_tree.links.new(mixed.outputs[0],
                                             material.node_tree.nodes.get('Material Output').inputs[0])
            materials[path] = material
        obj.data.materials.append(materials[path])
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 16
    scene.render.resolution_percentage = 100
    scene.world.color = (.18, .18, .18)
    scene.view_settings.view_transform = 'Standard'
    for position, power, size in (((4, -5, 6), 650, 5), ((-3, 3, 4), 500, 4)):
        bpy.ops.object.light_add(type='AREA', location=position)
        lamp = bpy.context.object
        lamp.data.energy, lamp.data.shape, lamp.data.size = power, 'DISK', size
        lamp.rotation_euler = (Vector((0, 0, 1)) - lamp.location).to_track_quat('-Z', 'Y').to_euler()
    bpy.ops.object.camera_add(location=(5, -7, 3.2))
    camera = bpy.context.object
    camera.data.type, camera.data.ortho_scale = 'ORTHO', 3.4
    camera.rotation_euler = (Vector((0, 0, 1.2)) - camera.location).to_track_quat('-Z', 'Y').to_euler()
    if 'camera' in work:
        camera.location = work['camera']
        camera.rotation_euler = (Vector(work['target']) - camera.location).to_track_quat('-Z', 'Y').to_euler()
        camera.data.ortho_scale = work['scale']
    scene.camera = camera
    scene.render.resolution_x, scene.render.resolution_y = 640, 800
    scene.render.filepath = str(root / 'native-outfit.png')
    bpy.ops.render.render(write_still=True)

root = Path(sys.argv[sys.argv.index('--') + 1])
names = sys.argv[sys.argv.index('--') + 2:]
for folder in sorted(root.iterdir()):
    if (folder / 'model.json').is_file() and (not names or folder.name in names):
        render(folder)
