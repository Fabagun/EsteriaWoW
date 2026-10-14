"""Use Blender's surface UV transfer and color bake on isolated Sethrak body copies."""

import json
from pathlib import Path
import sys

import bpy

ROOT = Path(sys.argv[sys.argv.index('--') + 1])


def mesh_object(name, vertices, faces, uvs=None):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([v['position'] for v in vertices], [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    layer = mesh.uv_layers.new(name='UVMap')
    for poly in mesh.polygons:
        poly.use_smooth = True
        for loop in poly.loop_indices:
            u, v = (uvs[loop] if uvs is not None else vertices[mesh.loops[loop].vertex_index]['uv'])
            layer.data[loop].uv = (u, 1 - v)
    return obj


def diffuse_material(name, image):
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    nodes = material.node_tree.nodes
    image_node = nodes.new('ShaderNodeTexImage')
    image_node.image = image
    material.node_tree.links.new(image_node.outputs['Color'], nodes.get('Principled BSDF').inputs['Base Color'])
    nodes.active = image_node
    return material, image_node


sexes = sys.argv[sys.argv.index('--') + 2:] or ('male', 'female')
for sex in sexes:
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    work = json.loads((ROOT / (sex + '-body-work.json')).read_text())
    source = mesh_object('OriginalSkin', work['target'], work['body'])
    target = mesh_object('PlayerBody', work['target'], work['body'], work['region_uvs'])
    uvs = [[item.uv[0], 1 - item.uv[1]] for item in target.data.uv_layers.active.data]
    assert len(uvs) == 3 * len(work['body'])
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 1
    scene.render.bake.use_selected_to_active = True
    scene.render.bake.cage_extrusion = 0.04
    scene.render.bake.max_ray_distance = 0.08
    scene.render.bake.margin = 8
    source_image = bpy.data.images.load(work['skin_sources'][0])
    material, image_node = diffuse_material('OriginalSkin', source_image)
    source.data.materials.append(material)
    output = bpy.data.images.new('PlayerSkinAtlas', width=512, height=512, alpha=True)
    material, output_node = diffuse_material('PlayerAtlasTarget', output)
    for link in list(material.node_tree.links):
        material.node_tree.links.remove(link)
    target.data.materials.append(material)
    for index, path in enumerate(work['skin_sources']):
        image_node.image = bpy.data.images.load(path, check_existing=True)
        bpy.ops.object.select_all(action='DESELECT')
        source.select_set(True)
        target.select_set(True)
        bpy.context.view_layer.objects.active = target
        bpy.ops.object.bake(type='DIFFUSE', pass_filter={'COLOR'})
        output.filepath_raw = str(ROOT / (sex + '-player-skin-' + str(index) + '.png'))
        output.file_format = 'PNG'
        output.save()
    (ROOT / (sex + '-body-uv.json')).write_text(json.dumps(uvs) + '\n')
    # Fit rigid garment surfaces to the accepted Sethrak body; hanging skirts/tabards/capes keep their drape.
    fitted = {}
    fit_source = mesh_object('FitAnatomy', work['target'], work['fit_surface']) if 'fit_surface' in work else source
    for part in work['equipment']:
        if part['geoset'] in (401, 1202, 1301, 1302) or part['geoset'] // 100 == 15 \
                or (part['geoset'] // 100 == 5 and not work.get('fit_boots', False)):
            continue
        obj = mesh_object('GarmentFit', work['donor'], part['triangles'])
        modifier = obj.modifiers.new('SethrakSurface', 'SHRINKWRAP')
        modifier.target = fit_source
        modifier.wrap_method = 'NEAREST_SURFACEPOINT'
        modifier.wrap_mode = 'OUTSIDE_SURFACE'
        modifier.offset = 0.015
        group = obj.vertex_groups.new(name='Used')
        used = {v for tri in part['triangles'] for v in tri}
        group.add(list(used), 1.0, 'REPLACE')
        modifier.vertex_group = group.name
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.modifier_apply(modifier=modifier.name)
        for index in used:
            fitted[str(index)] = list(obj.data.vertices[index].co)
        bpy.data.objects.remove(obj, do_unlink=True)
    (ROOT / (sex + '-equipment-fit.json')).write_text(json.dumps(fitted) + '\n')
    print('BAKED', sex, len(uvs), 'UV corners and', len(work['skin_sources']), 'skin colors', flush=True)

print('Sethrak body UV/color transfer finished', flush=True)
