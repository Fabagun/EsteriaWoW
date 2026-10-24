"""Blender render of independently decoded effect meshes."""
import json,sys
from pathlib import Path
import bpy
from mathutils import Vector
out=Path(sys.argv[sys.argv.index('--')+1]).resolve()
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=8
scene.render.resolution_x=480;scene.render.resolution_y=270;scene.render.resolution_percentage=100
scene.world.color=(.025,.03,.045);scene.view_settings.view_transform='Standard'
bpy.ops.object.camera_add();camera=bpy.context.object;camera.data.type='ORTHO';scene.camera=camera
for p in sorted(out.glob('fx_*.json')):
 d=json.loads(p.read_text());mesh=bpy.data.meshes.new(d['name']);mesh.from_pydata(d['positions'],[],d['triangles']);mesh.update()
 uv=mesh.uv_layers.new()
 for poly in mesh.polygons:
  for loop in poly.loop_indices:
   u,v=d['uv'][mesh.loops[loop].vertex_index];uv.data[loop].uv=(u,1-v)
 obj=bpy.data.objects.new(d['name'],mesh);bpy.context.collection.objects.link(obj)
 mat=bpy.data.materials.new(d['name']);mat.use_nodes=True;n=mat.node_tree.nodes;l=mat.node_tree.links;n.clear()
 tex=n.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(out/d['texture']))
 emit=n.new('ShaderNodeEmission');transparent=n.new('ShaderNodeBsdfTransparent');mix=n.new('ShaderNodeMixShader');output=n.new('ShaderNodeOutputMaterial')
 l.new(tex.outputs['Color'],emit.inputs['Color']);l.new(tex.outputs['Alpha'],mix.inputs[0]);l.new(transparent.outputs[0],mix.inputs[1]);l.new(emit.outputs[0],mix.inputs[2]);l.new(mix.outputs[0],output.inputs['Surface'])
 obj.data.materials.append(mat)
 mn,mx=map(Vector,d['bounds']);center=(mn+mx)/2;span=max(mx-mn)
 camera.location=center+Vector((.5,-2,1))*span;camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.ortho_scale=span*1.2
 scene.render.filepath=str(out/(d['name']+'-render.png'));bpy.ops.render.render(write_still=True)
 bpy.data.objects.remove(obj,do_unlink=True)
