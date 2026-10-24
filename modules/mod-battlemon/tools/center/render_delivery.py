import bpy,struct,sys,json
from pathlib import Path
from mathutils import Vector
D=Path(__file__).resolve().parents[2]/'data/center';W=D/'client/World/Wmo/Battlemon/Center';T=D.parents[1]/'generated/center/decoded'
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
def chunks(b,start=0):
 d={};p=start
 while p<len(b):
  name=b[p:p+4][::-1].decode();n=struct.unpack_from('<I',b,p+4)[0];d[name]=b[p+8:p+8+n];p+=8+n
 return d
names=list(json.loads((D/'geometry.json').read_text())['materials'])
for i,name in enumerate(names):
 b=chunks((W/f'BattlemonCenter_{i:03}.wmo').read_bytes())['MOGP'];c=chunks(b,68)
 v=list(struct.iter_unpack('<3f',c['MOVT']));t=list(struct.iter_unpack('<3H',c['MOVI']));uv=list(struct.iter_unpack('<2f',c['MOTV']))
 mesh=bpy.data.meshes.new(name);mesh.from_pydata(v,[],t);mesh.update();layer=mesh.uv_layers.new()
 for loop in mesh.loops:layer.data[loop.index].uv=uv[loop.vertex_index]
 obj=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(obj)
 mat=bpy.data.materials.new(name);mat.use_nodes=True;bs=mat.node_tree.nodes.get('Principled BSDF');bs.inputs['Roughness'].default_value=.8
 tex=mat.node_tree.nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(T/(name+'.png')));mat.node_tree.links.new(tex.outputs['Color'],bs.inputs['Base Color'])
 if name in ['glow','lamp']:mat.node_tree.links.new(tex.outputs['Color'],bs.inputs['Emission Color']);bs.inputs['Emission Strength'].default_value=1
 mesh.materials.append(mat)
scene=bpy.context.scene;scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.19,.24,.32,1);scene.world.node_tree.nodes['Background'].inputs[1].default_value=.6
bpy.ops.object.light_add(type='AREA',location=(-10,-18,24));bpy.context.object.data.energy=4500;bpy.context.object.data.size=14
bpy.ops.object.light_add(type='SUN',location=(0,0,25));bpy.context.object.rotation_euler=(.35,-.5,-.5);bpy.context.object.data.energy=2.4
root=chunks((W/'BattlemonCenter.wmo').read_bytes())
for light in struct.iter_unpack('<8B10f',root['MOLT']):
 bpy.ops.object.light_add(type='POINT',location=light[8:11]);bpy.context.object.data.energy=950;bpy.context.object.data.color=(light[6]/255,light[5]/255,light[4]/255);bpy.context.object.data.shadow_soft_size=.5
scene.render.engine='CYCLES';scene.cycles.samples=20;scene.render.resolution_x=1200;scene.render.resolution_y=850;scene.render.resolution_percentage=100
for name,pos,target in [('delivery-exterior',(22,-29,15),(0,0,2.5)),('delivery-interior',(0,-4,2.0),(0,3.3,1.7))]:
 bpy.ops.object.camera_add(location=pos);o=bpy.context.object;o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler();o.data.lens=38;scene.camera=o;scene.render.filepath=str(D/(name+'.png'));bpy.ops.render.render(write_still=True)
