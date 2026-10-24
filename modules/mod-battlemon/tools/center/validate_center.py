"""Validate Center WMO, server collision and navigation clearance without running WoW."""
from pathlib import Path
import json,struct,numpy as np
D=Path(__file__).resolve().parents[2]/'data/center';W=D/'client/World/Wmo/Battlemon/Center'
def chunks(data,start=0):
 result={};p=start
 while p<len(data):
  assert p+8<=len(data);tag=data[p:p+4][::-1].decode();n=struct.unpack_from('<I',data,p+4)[0];assert p+8+n<=len(data)
  assert tag not in result;result[tag]=data[p+8:p+8+n];p+=8+n
 assert p==len(data);return result
from PIL import Image
review=D.parents[1]/'generated/center/decoded';review.mkdir(parents=True,exist_ok=True)
for texture in W.glob('*.blp'):Image.open(texture).convert('RGBA').save(review/(texture.stem+'.png'))
root=chunks((W/'BattlemonCenter.wmo').read_bytes());assert struct.unpack('<I',root['MVER'])[0]==17
assert list(root)==['MVER','MOHD','MOTX','MOMT','MOGN','MOGI','MOSB','MOPV','MOPT','MOPR','MOVV','MOVB','MOLT','MODS','MODN','MODD','MFOG'], 'Invalid WMO root chunk order'
nm,ng=struct.unpack_from('<2I',root['MOHD']);assert nm==ng==15 and len(root['MOMT'])==nm*64
assert struct.unpack_from('<I',root['MOHD'],24)[0]==1, 'Missing default doodad set'
assert root['MODS']==struct.pack('<20s3I',b'Set_$DefaultGlobal',0,0,0)
triangles=[];groupdata=[]
for i in range(ng):
 g=chunks((W/f'BattlemonCenter_{i:03}.wmo').read_bytes())['MOGP'];s=chunks(g,68)
 assert struct.unpack_from('<I',g,52)[0]==15, 'Dry building must use the legacy no-liquid sentinel'
 assert not (struct.unpack_from('<I',g,8)[0]&0x1000) and 'MLIQ' not in s
 v=np.frombuffer(s['MOVT'],dtype='<f4').reshape(-1,3);t=np.frombuffer(s['MOVI'],dtype='<u2').reshape(-1,3)
 assert np.isfinite(v).all() and t.max()<len(v) and len(s['MONR'])==len(s['MOVT']) and len(s['MOTV'])==len(v)*8
 assert len(s['MOPY'])==len(t)*2 and np.frombuffer(s['MOPY'],dtype='uint8')[1::2].tolist()==[i]*len(t)
 batch=struct.unpack('<6hI3H2B',s['MOBA']);assert batch[6:10]==(0,t.size,0,len(v)-1) and batch[-1]==i
 refs=np.frombuffer(s['MOBR'],dtype='<u2');nodes=s['MOBN'];seen=set()
 def visit(index):
  assert index not in seen;seen.add(index);kind,l,r,n,offset,d=struct.unpack_from('<3hHIf',nodes,index*16)
  if kind==4:assert l==r==-1 and offset+n<=len(refs)
  else:assert 0<=kind<3 and l>=0 and r>=0;visit(l);visit(r)
 visit(0);assert len(seen)*16==len(nodes) and set(refs)==set(range(len(t)))
 triangles.extend(v[t]);groupdata.append((v,t))
# Independent parser follows the core's VMAP_4.8 reader, checking every triangle and BIH leaf.
b=(D/'server/BattlemonCenter.wmo.vmo').read_bytes();p=0

def take(n):
 global p
 value=b[p:p+n];assert len(value)==n;p+=n;return value

def unpack(fmt):return struct.unpack('<'+fmt,take(struct.calcsize('<'+fmt)))
def bih(expected):
 bounds=unpack('6f');n,=unpack('I');tree=unpack(str(n)+'I');count,=unpack('I');objects=unpack(str(count)+'I');seen=set();found=[]
 assert count==expected
 def visit(at):
  assert at not in seen and at+2<n;seen.add(at);tag,left,right=tree[at:at+3];axis=tag>>30;offset=tag&0x1fffffff
  if axis==3:assert offset+left<=count;found.extend(objects[offset:offset+left])
  else:assert not(tag&(1<<29));visit(offset);visit(offset+3)
 visit(0);assert len(seen)*3==n and sorted(found)==list(range(expected))
 return bounds
assert take(12)==b'VMAP_4.8WMOD';assert unpack('II')==(8,0);assert take(4)==b'GMOD';assert unpack('I')==(ng,)
for expected_v,expected_t in groupdata:
 bounds=unpack('6f');flags,gid=unpack('II');assert flags&1
 assert take(4)==b'VERT';size,n=unpack('II');assert size==4+n*12
 v=np.frombuffer(take(n*12),dtype='<f4').reshape(-1,3);assert np.array_equal(v,expected_v)
 assert take(4)==b'TRIM';size,n=unpack('II');assert size==4+n*12
 t=np.frombuffer(take(n*12),dtype='<u4').reshape(-1,3);assert np.array_equal(t,expected_t)
 assert take(4)==b'MBIH';bih(n);assert take(4)==b'LIQU';assert unpack('I')==(0,)
assert take(4)==b'GBIH';bih(ng);assert p==len(b)
# Ray checks against exported geometry, including entrance and floor.
T=np.array(triangles);a=T[:,0];e1=T[:,1]-a;e2=T[:,2]-a

def ray(origin,direction):
 origin=np.array(origin);d=np.array(direction);h=np.cross(d,e2);det=np.einsum('ij,ij->i',e1,h);valid=np.abs(det)>1e-8
 inv=np.zeros_like(det);inv[valid]=1/det[valid];s=origin-a;u=inv*np.einsum('ij,ij->i',s,h);q=np.cross(s,e1);v=inv*q.dot(d);distance=inv*np.einsum('ij,ij->i',e2,q)
 good=valid&(u>=0)&(v>=0)&(u+v<=1)&(distance>1e-5)
 return float(distance[good].min()) if good.any() else float('inf')
source=json.loads((D/'geometry.json').read_text())
scale=source['room_scale'];floor=source['floor_z']
for x in [-.9,-.5,0,.5,.9]:
 for z in [.5,1,1.5,2,2.5]:
  assert ray([x,-11*scale,z],[0,1,0])>4*scale, 'Doorway blocked at '+str((x,z))
assert ray([5*scale,-11*scale,1.5],[0,1,0])<4*scale,'Facade collision missing'
assert abs(ray([0,0,3],[0,0,-1])-2.76)<.01,'Interior floor height'
assert ray([0,0,3],[1,0,0])<8,'Side wall collision missing'
assert 4.2 < 1+ray([0,0,1],[0,0,1])-floor < 4.5,'Human-scale ceiling height'
for i in range(18):
 y=(-8.7-i*.45)*scale;expected=.24-i*.18
 assert abs((2-ray([0,y,2],[0,0,-1]))-expected)<.02, 'Stair tread collision'
# Sample the entire walking path, including the join missed by tread-center tests.
for x in [-.8,0,.8]:
 for y in np.linspace(-8.9*scale,-7.0*scale,80):
  assert abs((2-ray([x,y,2],[0,0,-1]))-floor)<.01, 'Threshold lip or gap'
for x,y in [(-4*scale,3.4*scale),(6*scale,3.6*scale)]:
 top=3-ray([x,y,3],[0,0,-1])
 assert 1.0<top-floor<1.12,'Counter must be waist height, not above NPC heads'
placement=json.loads((D/'placement.json').read_text())
terrain=json.loads((D/'terrain-fit.json').read_text())
assert placement['origin'][2]+floor==terrain['new_floor_z']
assert terrain['new_floor_z']-terrain['terrain_vertex_max_z']>1.5
for label,(x,y,z) in source['service_points'].items():
 hit=3-ray([x,y,3],[0,0,-1])
 assert abs(hit-floor)<.01,'Attendant floor collision'
 assert .02<z-hit<.04,'Attendant feet clearance'
 assert abs(placement['services'][label][2]-(terrain['new_floor_z']+.03))<.001
result={'wmo_groups':ng,'triangles':len(T),'server_geometry_equals_client':True,'collision_tree_coverage':True,'entrance_clearance_tested':True,'live_verified':False}
(D/'validation.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS',result)
