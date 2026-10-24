"""Create the Battlemon Center source mesh and previews using Blender 4.x. No core build."""
import bpy, math, random, json, sys
from pathlib import Path
from mathutils import Vector, Matrix
random.seed(351)
OUT=Path(__file__).resolve().parents[2]/'data/center'
OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
colors={'stone':(.32,.36,.39),'stone_light':(.48,.48,.42),'wood':(.23,.115,.052),'trim':(.36,.19,.075),'plaster':(.68,.61,.45),'slate':(.095,.22,.31),'slate_light':(.14,.29,.39),'bronze':(.48,.27,.10),'dark':(.035,.047,.055),'red':(.68,.045,.04),'cream':(.90,.87,.68),'blue':(.045,.25,.50),'green':(.15,.52,.28),'glow':(.3,.95,.65),'lamp':(1,.65,.19)}
mats={}
for name,c in colors.items():
 m=bpy.data.materials.new(name);m.diffuse_color=(*c,1);m.use_nodes=True;bs=m.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(*c,1);bs.inputs['Roughness'].default_value=.8
 if name in ('glow','lamp'):bs.inputs['Emission Color'].default_value=(*c,1);bs.inputs['Emission Strength'].default_value=1
 mats[name]=m
objs=[]
def finish(o,name,mat,bevel=0):
 o.name=name;o.data.materials.append(mats[mat]);o['center_material']=mat;objs.append(o)
 if bevel:
  mod=o.modifiers.new('Hand-cut edges','BEVEL');mod.width=bevel;mod.segments=1
  bpy.context.view_layer.objects.active=o;bpy.ops.object.modifier_apply(modifier=mod.name)
 return o
def box(name,p,d,mat,bevel=.04):
 bpy.ops.mesh.primitive_cube_add(size=1,location=p);o=bpy.context.object;o.scale=d;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);return finish(o,name,mat,bevel)
def beam(name,a,b,r,mat='wood'):
 a,b=Vector(a),Vector(b);o=box(name,(a+b)/2,(r,r,(b-a).length),mat,.025);o.rotation_euler=(b-a).to_track_quat('Z','Y').to_euler();return o
def mesh(name,v,f,mat):
 d=bpy.data.meshes.new(name);d.from_pydata(v,[],f);d.update();o=bpy.data.objects.new(name,d);bpy.context.collection.objects.link(o);return finish(o,name,mat)
def ring(name,x,y,z,R,r,mat):
 bpy.ops.mesh.primitive_torus_add(major_radius=R,minor_radius=r,major_segments=48,minor_segments=8,location=(x,y,z),rotation=(math.pi/2,0,0));return finish(bpy.context.object,name,mat)
def disc(name,x,y,z,r,mat,start=0,end=2*math.pi):
 v=[(x,y,z)]+[(x+r*math.cos(t),y,z+r*math.sin(t)) for t in [start+(end-start)*i/32 for i in range(33)]]
 return mesh(name,v,[(0,i+1,i+2) for i in range(32)],mat)
def wallstones(name,xrange,yrange,zrange,front=True):
 for row in range(zrange[2]):
  for col in range(xrange[2]):
   t=(col+.5)/xrange[2];x=xrange[0]+(xrange[1]-xrange[0])*t
   box(name,(x,(yrange[0]+yrange[1])/2,zrange[0]+(row+.5)*(zrange[1]-zrange[0])/zrange[2]),((xrange[1]-xrange[0])/xrange[2]-.06,yrange[1]-yrange[0],(zrange[1]-zrange[0])/zrange[2]-.06),random.choice(['stone','stone','stone_light']),.07)
# Foundation and open entrance. Model front is -Y. Entrance threshold is local (0,-9,0).
box('Foundation',(0,0,-1.85),(24.8,17.4,3.7),'stone',.1)
box('Interior flagstone floor',(0,0,.12),(23.5,16.4,.24),'stone_light',.03)
# Solid stairs bridge the raised floor to the surveyed approach terrain.
for i in range(18):
 top=.24-i*.18;bottom=-3.7
 box('Entrance step',(0,-8.7-i*.45,(top+bottom)/2),(5.7,.47,top-bottom),'stone_light',.015)
# A continuous, level landing joins the top stair to the interior slab.
box('Door threshold landing',(0,-8.3,.12),(3.7,1.3,.24),'stone_light',0)
# Continuous wall slabs except the 3.6 yard doorway.
for x in [-7,7]:box('Front plaster',(x,-8,3.6),(10,.5,7.2),'plaster')
box('Door lintel plaster',(0,-8,5.7),(4,.5,3),'plaster')
for x in [-12,12]:box('Side plaster',(x,0,3.6),(.5,16,7.2),'plaster')
box('Rear plaster',(0,8,3.6),(24,.5,7.2),'plaster')
for a,b in [(-12,-2),(2,12)]:wallstones('Front masonry',(a,b,9),(-8.45,-7.65),(0,2.4,4))
wallstones('Rear masonry',(-12,12,20),(7.7,8.4),(0,2.4,4))
for x in [-12.1,12.1]:
 for row in range(4):
  for col in range(13):box('Side masonry',(x,-7.5+col*1.25,.3+row*.6),(.9,1.18,.53),random.choice(['stone','stone_light']),.06)
# Structural timber.
for x in [-11.8,-7.6,-3,3,7.6,11.8]:
 for y in [-8.4,8.35]:
  box('Timber post',(x,y,4.5),(.42,.48,5.4),'wood');box('Copper post shoe',(x,y,2.5),(.58,.60,.43),'bronze')
for z in [2.55,5.4,7.2]:
 for y in [-8.45,8.45]:
  if y<0 and z<4.5:
   for x in [-7.325,7.325]:box('Cross timber',(x,y,z),(10.05,.46,.38),'wood')
  else:box('Cross timber',(0,y,z),(24.7,.46,.38),'wood')
 for x in [-12.35,12.35]:box('Side cross timber',(x,0,z),(.45,17.2,.38),'wood')
for x in [-12.3,12.3]:
 for y in [-4,0,4]:box('Side post',(x,y,4.5),(.4,.4,5.4),'wood')
for x in [-10,-5.3,5.3,10]:
 beam('Diagonal brace',(x-1.3,-8.47,5.65),(x+1.3,-8.47,6.96),.22)
# Main pitched roof ridge along X, slate tiles individually modeled.
angle=math.atan2(4.1,9)
for side in [-1,1]:
 for row in range(10):
  y=side*(row+.5)*.9;z=11.6-abs(y)*4.1/9
  for col in range(25):
   x=-12.6+col*1.03+(row%2)*.25
   o=box('Blue slate shingle',(x,y,z),(1.07,1.12,.10),random.choice(['slate','slate','slate_light']),.025);o.rotation_euler.x=-side*angle
for x in [-13,13]:
 beam('Roof fascia',(x,-9.25,7.38),(x,0,11.72),.42,'trim');beam('Roof fascia',(x,0,11.72),(x,9.25,7.38),.42,'trim')
beam('Roof ridge',(-13.3,0,11.76),(13.3,0,11.76),.4,'trim')
# Close both roof-end gables; face both inside and outside.
for x in [-12,12]:
 mesh('Side roof gable',[(x+d,y,z) for d in [-.16,.16] for y,z in [(-8,7.2),(8,7.2),(0,11.45)]],[(2,1,0),(3,4,5),(0,1,4,3),(1,2,5,4),(2,0,3,5)],'plaster')
 beam('Side gable upright',(x,0,7.2),(x,0,11.45),.26)
# Front center gable, sign and sheltered entry.
mesh('Front gable',[(-4.2,-8.6,7),(4.2,-8.6,7),(0,-8.6,11.7)],[(0,1,2)],'plaster')
for x in [-1,1]:
 beam('Gable timber',(x*4.3,-8.72,7),(0,-8.72,11.85),.43,'trim')
 for row in range(6):
  xx=x*(row+.5)*.7;zz=11.8-abs(xx)*4.7/4.2
  for col in range(4):
   o=box('Gable slate',(xx,-8.1+col*.9,zz),(.95,.97,.12),'slate',.025);o.rotation_euler.y=x*math.atan2(4.7,4.2)
for x in [-2.15,2.15]:box('Door jamb',(x,-8.64,2.2),(.35,.7,4.4),'trim')
beam('Entry lintel',(-2.3,-8.7,4.5),(2.3,-8.7,4.5),.45,'trim')
box('Entry canopy',(0,-9.1,4.9),(5.5,2.4,.27),'wood')
for x in [-2.35,2.35]:beam('Canopy brace',(x,-8.6,3.7),(x,-9.85,4.8),.20,'trim')
# Pokeball medallion: modeled, not a flat billboard.
ring('Medallion bronze rim',0,-8.93,8.8,1.57,.17,'bronze');ring('Healing emerald halo',0,-8.88,8.8,1.83,.07,'glow')
disc('Pokeball dark backing',0,-9.01,8.8,1.46,'dark')
disc('Pokeball upper enamel',0,-9.05,8.8,1.36,'red',0,math.pi)
disc('Pokeball lower enamel',0,-9.05,8.8,1.36,'cream',math.pi,2*math.pi)
box('Pokeball belt',(0,-9.10,8.8),(2.75,.06,.18),'dark',0)
ring('Pokeball button rim',0,-9.15,8.8,.35,.10,'dark');disc('Pokeball button',0,-9.18,8.8,.30,'cream')
# Paired lancet windows with jewel glass and lead tracery.
for x in [-9.6,-6.7,6.7,9.6]:
 box('Window recess',(x,-8.34,3.75),(1.9,.2,2.6),'dark')
 for row in range(4):
  for col in range(2):
   xx=x+(col-.5)*.72;zz=2.9+row*.55
   mesh('Stained glass diamond',[(xx,-8.48,zz-.32),(xx+.34,-8.48,zz),(xx,-8.48,zz+.32),(xx-.34,-8.48,zz)],[(0,1,2),(0,2,3)],['green','blue','cream'][(row+col)%3])
 for dx in [-.99,.99]:beam('Window casing',(x+dx,-8.6,2.45),(x+dx,-8.6,4.8),.16,'trim')
 beam('Window arch',(x-.99,-8.6,4.8),(x,-8.6,5.25),.19,'trim');beam('Window arch',(x,-8.6,5.25),(x+.99,-8.6,4.8),.19,'trim')
 box('Window sill',(x,-8.7,2.4),(2.3,.65,.16),'stone_light')
# Lanterns and side benches.
for x in [-3.25,3.25]:
 beam('Lantern hanger',(x,-8.5,4.7),(x,-9.15,4.7),.11,'dark')
 box('Lantern glow',(x,-9.1,3.75),(.4,.4,.7),'lamp')
 for z in [3.35,4.15]:box('Lantern caps',(x,-9.1,z),(.65,.65,.15),'bronze')
 for dx in [-.23,.23]:beam('Lantern frame',(x+dx,-9.34,3.4),(x+dx,-9.34,4.1),.06,'dark')
 beam('Lantern chain',(x,-9.1,4.2),(x,-9.1,4.7),.07,'dark')
for x in [-8.3,8.3]:
 box('Bench seat',(x,-9.3,.9),(3.5,.85,.2),'trim');box('Bench back',(x,-8.95,1.65),(3.5,.16,.65),'wood')
 for dx in [-1.25,1.25]:box('Bench leg',(x+dx,-9.3,.4),(.22,.66,.8),'wood')
# Stone chimney with cap.
for z in range(7):box('Chimney course',(8.8,3.2,9+z*.52),(1.55,1.4,.48),'stone',.06)
box('Chimney cap',(8.8,3.2,12.65),(1.9,1.75,.25),'stone_light')
# Interior service counters, healing machine and shelving. No door/loading boundary.
box('Healing counter',(-4,4,1.1),(7.4,1.5,2.2),'wood');box('Healing countertop',(-4,4,2.25),(7.65,1.72,.16),'cream')
box('Healing machine',(-4,4.05,2.62),(3.3,1.05,.6),'red');box('Healing tray',(-4,3.95,2.95),(3.1,.93,.10),'dark')
for i in range(6):
 x=-5.25+(i%3)*1.25;y=3.68+(i//3)*.55
 bpy.ops.mesh.primitive_uv_sphere_add(segments=12,ring_count=6,radius=.19,location=(x,y,3.16));finish(bpy.context.object,'Healing ball','cream')
box('Shop counter',(6,3.6,1.1),(5.7,1.6,2.2),'wood');box('Shop countertop',(6,3.6,2.25),(5.9,1.8,.17),'trim')
for x in [4.2,7.8]:
 for z in [1,2.6,4.2]:
  box('Shop shelf',(x,7.1,z),(3.1,.9,.15),'trim')
  for i in range(5):box('Shop supplies',(x-1.1+i*.55,7.05,z+.38),(.35,.5,.6),['red','green','blue','cream'][i%4],.06)
 for dx in [-1.5,1.5]:box('Shelf upright',(x+dx,7.1,2.6),(.14,.8,5),'wood')
box('Collection terminal',(-9.8,4,1.4),(1.5,1.3,2.8),'wood');box('Terminal screen',(-9.8,3.32,2.35),(1.14,.12,.8),'glow')
for x in [-7,0,7]:
 beam('Interior ceiling tie',(x,-7.7,6.9),(x,7.7,6.9),.25)
# Interior pendant lights above the public floor and both service counters.
light_positions=[(-6,-2,5.4),(6,-2,5.4),(-6,5,5.4),(6,5,5.4)]
for x,y,z in light_positions:
 beam('Pendant chain',(x,y,z+.4),(x,y,6.8),.07,'dark')
 box('Pendant glow',(x,y,z),(.5,.5,.7),'lamp')
 for dz in [-.42,.42]:box('Pendant bronze cap',(x,y,z+dz),(.8,.8,.12),'bronze')
 for dx in [-.3,.3]:
  for dy in [-.3,.3]:beam('Pendant frame',(x+dx,y+dy,z-.35),(x+dx,y+dy,z+.35),.055,'dark')
# Human-scale room: keep the raised floor/foundation elevation, reduce the footprint.
# A flat timber ceiling closes the unused roof void above the occupied room.
box('Interior ceiling',(0,0,7.0),(23.5,16.0,.16),'wood',0)
ROOM_SCALE=.65
FLOOR=.24
COUNTER_SCALE=.78
for o in objs:
 furniture=o.name.startswith(('Healing counter','Shop counter'))
 machine=o.name.startswith(('Healing machine','Healing tray','Healing ball'))
 world=o.matrix_world.copy()
 for vertex in o.data.vertices:
  v=world@vertex.co
  if furniture:v.z=FLOOR+(v.z-FLOOR)*COUNTER_SCALE
  if machine:v.z-=(2.25-FLOOR)*(1-COUNTER_SCALE)
  v.x*=ROOM_SCALE;v.y*=ROOM_SCALE
  if v.z>FLOOR:v.z=FLOOR+(v.z-FLOOR)*ROOM_SCALE
  vertex.co=v
 o.matrix_world=Matrix.Identity(4);o.data.update()
light_positions=[(x*ROOM_SCALE,y*ROOM_SCALE,FLOOR+(z-FLOOR)*ROOM_SCALE) for x,y,z in light_positions]
service_points={'healer':[-4*ROOM_SCALE,5.7*ROOM_SCALE,FLOOR+.03],
                'shop':[6*ROOM_SCALE,5.3*ROOM_SCALE,FLOOR+.03],
                'collection':[-9.8*ROOM_SCALE,3*ROOM_SCALE,FLOOR+.03]}
# Export evaluated triangles grouped by material, preserve separate solid objects.
deps=bpy.context.evaluated_depsgraph_get();groups={name:[] for name in colors}
for o in objs:
 e=o.evaluated_get(deps);me=e.to_mesh();me.calc_loop_triangles();mat=o['center_material']
 for t in me.loop_triangles:
  verts=[list(o.matrix_world@me.vertices[i].co) for i in t.vertices]
  n=list((o.matrix_world.to_3x3()@t.normal).normalized());groups[mat].append({'v':verts,'n':n})
 e.to_mesh_clear()
(OUT/'geometry.json').write_text(json.dumps({'lights':light_positions,'materials':colors,'groups':groups,'entrance':[0,-9*ROOM_SCALE,FLOOR],'room_scale':ROOM_SCALE,'floor_z':FLOOR,'service_points':service_points}),encoding='utf-8')
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'battlemon-center.blend'))
if '--no-render' in sys.argv:
 print('CENTER_SOURCE_COMPLETE',sum(len(x) for x in groups.values()),flush=True);sys.exit(0)
# Review views only: ground and lighting are not exported as building geometry.
box('Preview ground',(0,0,-.83),(200,200,.2),'green',0)
world=bpy.context.scene.world;world.color=(.22,.22,.22)
bpy.ops.object.light_add(type='AREA',location=(-10,-18,24));bpy.context.object.data.energy=4500;bpy.context.object.data.shape='DISK';bpy.context.object.data.size=14
bpy.ops.object.light_add(type='SUN',location=(0,0,25));bpy.context.object.rotation_euler=(.35,-.5,-.5);bpy.context.object.data.energy=2.4
for pos in light_positions:
 bpy.ops.object.light_add(type='POINT',location=(pos[0],pos[1],pos[2]-.6));bpy.context.object.data.energy=950;bpy.context.object.data.color=(1,.78,.5);bpy.context.object.data.shadow_soft_size=.5
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=24;scene.render.resolution_x=1400;scene.render.resolution_y=1000;scene.render.resolution_percentage=100
scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.19,.24,.32,1);scene.world.node_tree.nodes['Background'].inputs[1].default_value=.6
for name,pos,target in [('exterior',(30,-40,22),(0,0,4.5)),('entrance',(0,-29,8),(0,-2,4.5)),('interior',(0,-6,4.2),(0,5,2.8))]:
 bpy.ops.object.camera_add(location=pos);camera=bpy.context.object;camera.rotation_euler=(Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.lens=38;scene.camera=camera;scene.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True)
print('CENTER_SOURCE_COMPLETE',sum(len(x) for x in groups.values()),flush=True)
