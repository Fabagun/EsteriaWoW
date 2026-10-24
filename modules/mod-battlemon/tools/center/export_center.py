"""Export the authored Center triangles to WotLK WMO v17, textures and raw collision."""
from pathlib import Path
import json,struct,math,sys,hashlib,importlib.util
import numpy as np
from PIL import Image
MODULE=Path(__file__).resolve().parents[2];D=MODULE/'data/center';OUT=D/'client/World/Wmo/Battlemon/Center';OUT.mkdir(parents=True,exist_ok=True)
P=lambda fmt,*x:struct.pack('<'+fmt,*x)
def chunk(tag,data=b''):return tag[::-1].encode()+P('I',len(data))+data
source=json.loads((D/'geometry.json').read_text());materials=list(source['materials']);groups=source['groups']
sys.path.insert(0,str(MODULE/'generated/source-catalog/compression-dependencies'))
import texture_delivery as bc
rawdir=D/'texture-sources';rawdir.mkdir(exist_ok=True);tex=b'';materialbytes=b'';proofs={}
for name in materials:
 color=np.array(source['materials'][name]);color=np.where(color<=.0031308,12.92*color,1.055*color**(1/2.4)-.055)
 yy,xx=np.mgrid[:512,:512];variation=(np.sin(xx*.081+np.sin(yy*.032)*2)*np.sin(yy*.12))*.022
 rgb=np.clip((color[None,None,:]+variation[:,:,None])*255,0,255).astype('uint8');a=np.concatenate([rgb,np.full((512,512,1),255,dtype='uint8')],2)
 im=Image.fromarray(a);im.save(rawdir/(name+'.png'));mips=[im]
 while mips[-1].size!=(1,1):mips.append(mips[-1].resize((max(1,mips[-1].width//2),max(1,mips[-1].height//2)),Image.Resampling.BOX))
 data,quality=bc.encode(mips);assert data==bc.encode(mips)[0];(OUT/(name+'.blp')).write_bytes(data)
 assert all(q['alpha_max']==0 and q['rgb_mae_visible']<8 for q in quality)
 proofs[name]={'sha256':hashlib.sha256(data).hexdigest(),'source_sha256':bc.digest(rawdir/(name+'.png')),'quality':quality,'encoder':'ispc_texcomp-1.0.1'}
 offset=len(tex);tex+=('World\\Wmo\\Battlemon\\Center\\'+name+'.blp').encode()+b'\0';tex+=b'\0'*((-len(tex))%4)
 # Unlit emissive glass/lamps; ordinary materials retain WoW lighting.
 flags=1 if name in ('lamp','glow') else 0
 materialbytes+=P('16I',flags,0,0,offset,0,0,0,0,0,0,0,0,0,0,0,0)
allv=np.array([v for g in groups.values() for t in g for v in t['v']]);lo=allv.min(0);hi=allv.max(0)
namebuf=b'\0\0';infos=b'';rawgroups=[];counts=[]
for gi,name in enumerate(materials):
 triangles=groups[name];verts=[];normals=[];indices=[];lookup={}
 for t in triangles:
  for v in t['v']:
   key=tuple(round(x,6) for x in v+t['n'])
   if key not in lookup:lookup[key]=len(verts);verts.append(v);normals.append(t['n'])
   indices.append(lookup[key])
 v=np.array(verts);glo=v.min(0);ghi=v.max(0);nf=len(triangles);assert len(verts)<65536 and len(indices)<65536
 no=len(namebuf);namebuf+=name.encode()+b'\0';flags=0x1|0x8|0x200
 infos+=P('I6fI',flags,*glo,*ghi,no)
 # Spatial collision tree; crossing faces included on both sides.
 nodes=[];refs=[];tv=np.array([t['v'] for t in triangles]);tlo=tv.min(1);thi=tv.max(1)
 def bsp(ids,bmin,bmax,depth=0):
  node=len(nodes);nodes.append(None);axis=int(np.argmax(bmax-bmin));mid=float((bmin[axis]+bmax[axis])/2)
  left=[i for i in ids if tlo[i,axis]<=mid];right=[i for i in ids if thi[i,axis]>=mid]
  if len(ids)<=64 or depth>=12 or len(left)==len(ids) or len(right)==len(ids):
   nodes[node]=P('3hHIf',4,-1,-1,len(ids),len(refs),0);refs.extend(ids)
  else:
   b=bmax.copy();b[axis]=mid;l=bsp(left,bmin,b,depth+1);b=bmin.copy();b[axis]=mid;r=bsp(right,b,bmax,depth+1)
   nodes[node]=P('3hHIf',axis,l,r,0,0,mid)
  return node
 bsp(list(range(nf)),glo,ghi)
 # Legacy liquid index 15 means no liquid; zero means water, not none.
 head=P('3I6f6H4B4I',no,no,flags,*glo,*ghi,0,0,0,0,1,0,0,0,0,0,15,gi,0,0)
 assert len(head)==68
 uv=[(p[0]*.12+p[1]*.06,p[2]*.15+p[1]*.12) for p in verts]
 batch=P('6hI3H2B',*(math.floor(x) for x in glo),*(math.ceil(x) for x in ghi),0,len(indices),0,len(verts)-1,0,gi)
 child=chunk('MOPY',bytes([0x28,gi])*nf)+chunk('MOVI',P(str(len(indices))+'H',*indices))+chunk('MOVT',v.astype('<f4').tobytes())+chunk('MONR',np.array(normals,dtype='<f4').tobytes())+chunk('MOTV',np.array(uv,dtype='<f4').tobytes())+chunk('MOBA',batch)+chunk('MOLR',P('4H',0,1,2,3))+chunk('MOBN',b''.join(nodes))+chunk('MOBR',P(str(len(refs))+'H',*refs))
 (OUT/f'BattlemonCenter_{gi:03}.wmo').write_bytes(chunk('MVER',P('I',17))+chunk('MOGP',head+child))
 counts.append({'group':name,'vertices':len(verts),'faces':nf,'bsp_nodes':len(nodes)})
 # Raw vmap input follows this core's vmap4_extractor serialization.
 rawgroups.append((flags,gi,glo,ghi,v,indices))
roothead=P('9I6fI',len(materials),len(materials),0,4,0,0,1,0,0,*lo,*hi,0)
root=chunk('MVER',P('I',17))+chunk('MOHD',roothead)+chunk('MOTX',tex)+chunk('MOMT',materialbytes)+chunk('MOGN',namebuf)+chunk('MOGI',infos)+chunk('MOSB',b'\0'*4)
for tag in ['MOPV','MOPT','MOPR','MOVV','MOVB']:root+=chunk(tag)
root+=chunk('MOLT',b''.join(P('8B10f',0,1,1,0,128,199,255,255,pos[0],pos[1],pos[2]-.6,1.5,1,15,0,0,0,0) for pos in source['lights']))
# Gameobject instances select set zero, even when there are no separate doodads.
root+=chunk('MODS',P('20s3I',b'Set_$DefaultGlobal',0,0,0))
for tag in ['MODN','MODD']:root+=chunk(tag)
root+=chunk('MFOG',bytes(48));(OUT/'BattlemonCenter.wmo').write_bytes(root)
(D/'export-proof.json').write_text(json.dumps({'format':'WMO 17','bounds':[lo.tolist(),hi.tolist()],'groups':counts,'texture_proofs':proofs,'live_verified':False},indent=2)+'\n')
print('WMO exported:',len(materials),'groups;',sum(c['faces'] for c in counts),'faces; all mipmaps decoded and compression reproduced.')

# Server collision BIH uses the exact VMAP_4.8 schema in this core.
def bih(bounds):
    lows=np.array([x[0] for x in bounds]);highs=np.array([x[1] for x in bounds]);nodes=[0,0,0];objects=[]
    def node(at,ids):
        if len(ids)<=8:
            nodes[at:at+3]=[0xC0000000|len(objects),len(ids),0];objects.extend(ids);return
        axis=int(np.argmax(highs[ids].max(0)-lows[ids].min(0)))
        ids=sorted(ids,key=lambda i:float(lows[i,axis]+highs[i,axis]));mid=len(ids)//2;l,r=ids[:mid],ids[mid:]
        offset=len(nodes);nodes.extend([0]*6)
        fl=lambda x:struct.unpack('<I',P('f',float(x)))[0]
        nodes[at:at+3]=[(axis<<30)|offset,fl(highs[l,axis].max()),fl(lows[r,axis].min())]
        node(offset,l);node(offset+3,r)
    node(0,list(range(len(bounds))))
    return P('6fI',*lows.min(0),*highs.max(0),len(nodes))+P(str(len(nodes))+'I',*nodes)+P('I',len(objects))+P(str(len(objects))+'I',*objects)
server=D/'server';server.mkdir(exist_ok=True)
vmo=b'VMAP_4.8WMOD'+P('II',8,0)+b'GMOD'+P('I',len(rawgroups));gb=[]
for flags,gi,glo,ghi,v,indices in rawgroups:
    vv=v.astype('<f4');ii=np.array(indices,dtype='<u4').reshape(-1,3);tv=vv[ii];tb=list(zip(tv.min(1),tv.max(1)))
    vmo+=P('6fII',*glo,*ghi,flags,gi)+b'VERT'+P('II',4+vv.nbytes,len(vv))+vv.tobytes()
    vmo+=b'TRIM'+P('II',4+ii.nbytes,len(ii))+ii.tobytes()+b'MBIH'+bih(tb)+b'LIQU'+P('I',0);gb.append((glo,ghi))
vmo+=b'GBIH'+bih(gb);(server/'BattlemonCenter.wmo.vmo').write_bytes(vmo)
# Paired client/server display layer. Keep its custom ID separate from Pokemon IDs.
display=900500;path='World\\Wmo\\Battlemon\\Center\\BattlemonCenter.wmo'
row=P('12I6fI',display,1,*([0]*10),*lo,*hi,0);strings=b'\0'+path.encode()+b'\0';dbc=b'WDBC'+P('4I',1,19,76,len(strings))+row+strings
(server/'GameObjectDisplayInfo.dbc9-battlemon-center').write_bytes(dbc)
name=b'BattlemonCenter.wmo';(server/'GameObjectModels.center-record').write_bytes(P('IBI',display,1,len(name))+name+P('6f',*lo,*hi))
angle=2.3489094+math.pi/2
# Keep the surveyed world origin and raised floor fixed as the room is resized.
x=-9062.506-9*math.sin(angle);y=352.9509+9*math.cos(angle);z=96.1162
previous=json.loads((D/'placement.json').read_text()) if (D/'placement.json').exists() else {}
placement={'map':0,'phase':1,'entrance_gps':[-9062.506,352.9509,93.1162],'floor_world_z':z+.24,'entrance_facing':2.3489094,'origin':[x,y,z],'orientation':angle,'display_id':display,'gameobject_entry':900500,'npc_entry':900501,'services':{}}
for label,pos in source['service_points'].items():
    a,b,c=pos;placement['services'][label]=[x+a*math.cos(angle)-b*math.sin(angle),y+a*math.sin(angle)+b*math.cos(angle),z+c,2.3489094]
if 'world_update' in previous:placement['world_update']=previous['world_update']
placement['world_followup_updates']=previous.get('world_followup_updates',[])
placement['gameobject_type']=14
placement['room_scale']=source.get('room_scale',1)
a,b,c=source['entrance']
placement['door_threshold_world']=[x+a*math.cos(angle)-b*math.sin(angle),y+a*math.sin(angle)+b*math.cos(angle),z+c]
(D/'placement.json').write_text(json.dumps(placement,indent=2)+'\n')
print('Server collision and paired display layer written; origin',placement['origin'])
