"""Read the bounded glTF 2.0 subset used by the provided skinned Pixelmon GLB."""
import json
from pathlib import Path
import struct
import numpy as np
from m2 import quaternion


class GLB:
    def __init__(self, path):
        self.path=Path(path);raw=self.path.read_bytes();self._accessors={}
        if len(raw)<20 or struct.unpack_from('<4sII',raw)!=(b'glTF',2,len(raw)):
            raise ValueError('Invalid GLB 2 header')
        chunks={};offset=12
        while offset<len(raw):
            size,kind=struct.unpack_from('<II',raw,offset);offset+=8
            if size%4 or offset+size>len(raw) or kind in chunks:
                raise ValueError('Invalid or duplicate GLB chunk')
            chunks[kind]=raw[offset:offset+size];offset+=size
        self.data=json.loads(chunks[0x4e4f534a]);self.binary=chunks[0x004e4942]
        if self.data['asset']['version']!='2.0' or self.data.get('extensionsRequired'):
            raise ValueError('Unsupported glTF version/extensions')
        buffers=self.data['buffers']
        if len(buffers)!=1 or 'uri' in buffers[0] or buffers[0]['byteLength']>len(self.binary):
            raise ValueError('External or truncated GLB buffer')
        self.parents=[-1]*len(self.data['nodes']);self.order=[]
        for i,node in enumerate(self.data['nodes']):
            for child in node.get('children',[]):
                if not 0<=child<len(self.parents) or self.parents[child]!=-1:
                    raise ValueError('Invalid glTF node parent')
                self.parents[child]=i
        def visit(i,pending):
            if i in pending:raise ValueError('Cyclic glTF node hierarchy')
            if i in self.order:return
            if self.parents[i]>=0:visit(self.parents[i],pending|{i})
            self.order.append(i)
        for i in range(len(self.parents)):visit(i,set())

    def accessor(self,index):
        if index in self._accessors:return self._accessors[index]
        a=self.data['accessors'][index]
        if a.get('sparse'):raise ValueError('Sparse glTF accessor requires explicit support')
        view=self.data['bufferViews'][a['bufferView']]
        if view.get('buffer',0)!=0:raise ValueError('Unexpected glTF buffer index')
        types={5120:'i1',5121:'u1',5122:'<i2',5123:'<u2',5125:'<u4',5126:'<f4'}
        widths={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4,'MAT4':16}
        dt=np.dtype(types[a['componentType']]);width=widths[a['type']]
        count=a['count'];start=view.get('byteOffset',0)+a.get('byteOffset',0)
        stride=view.get('byteStride',width*dt.itemsize)
        end=start+(count-1)*stride+width*dt.itemsize
        if count<1 or stride<width*dt.itemsize or end>view.get('byteOffset',0)+view['byteLength']:
            raise ValueError('glTF accessor outside buffer view')
        result=np.ndarray((count,width),dtype=dt,buffer=self.binary,offset=start,strides=(stride,dt.itemsize)).copy()
        if a.get('normalized'):
            if dt.kind not in 'iu':raise ValueError('Unexpected normalized accessor type')
            info=np.iinfo(dt);result=np.maximum(result.astype(float)/info.max,-1)
        if not np.isfinite(result).all():raise ValueError('Nonfinite glTF accessor')
        result.setflags(write=False);self._accessors[index]=result
        return result

    def geometry(self):
        nodes=[i for i,n in enumerate(self.data['nodes']) if 'mesh' in n]
        if len(nodes)!=1:raise ValueError('GLB requires explicitly supported single skinned mesh')
        node=self.data['nodes'][nodes[0]]
        if 'skin' not in node:raise ValueError('GLB mesh is not skinned')
        primitives=self.data['meshes'][node['mesh']]['primitives']
        if len(primitives)!=1 or primitives[0].get('mode',4)!=4 or primitives[0].get('targets'):
            raise ValueError('Unsupported GLB primitive or morph targets')
        primitive=primitives[0];attrs=primitive['attributes']
        if set(attrs)!={'POSITION','NORMAL','TEXCOORD_0','JOINTS_0','WEIGHTS_0'}:
            raise ValueError('Unsupported GLB vertex attributes')
        result={k:self.accessor(v) for k,v in attrs.items()}
        result['indices']=self.accessor(primitive['indices']).ravel().astype(int)
        if len(result['indices'])%3 or result['indices'].max()>=len(result['POSITION']):
            raise ValueError('Invalid GLB triangles')
        result['skin']=self.data['skins'][node['skin']]
        result['inverse_bind']=self.accessor(result['skin']['inverseBindMatrices']).reshape(-1,4,4).transpose(0,2,1)
        result['material']=self.data['materials'][primitive.get('material',0)]
        return result

    def local_trs(self,animation,seconds):
        nodes=self.data['nodes'];count=len(nodes)
        t=np.array([n.get('translation',[0,0,0]) for n in nodes],dtype=float)
        q=np.array([n.get('rotation',[0,0,0,1]) for n in nodes],dtype=float)
        scale=np.array([n.get('scale',[1,1,1]) for n in nodes],dtype=float)
        for i,node in enumerate(nodes):
            if 'matrix' in node:t[i],q[i],scale[i]=decompose(np.array(node['matrix']).reshape(4,4).T)
        seen=set()
        for channel in animation['channels']:
            target=channel['target'];key=(target['node'],target['path'])
            if key in seen:raise ValueError('Duplicate glTF channel')
            seen.add(key)
            sampler=animation['samplers'][channel['sampler']]
            times=self.accessor(sampler['input']).ravel();values=self.accessor(sampler['output'])
            if len(times)!=len(values) or np.any(np.diff(times)<=0):raise ValueError('Invalid glTF sample times')
            i=max(0,min(int(np.searchsorted(times,seconds,side='right'))-1,len(times)-1))
            j=min(i+1,len(times)-1)
            fraction=0 if i==j else float(np.clip((seconds-times[i])/(times[j]-times[i]),0,1))
            interp=sampler.get('interpolation','LINEAR')
            if interp=='STEP':value=values[i]
            elif interp=='LINEAR':
                value=slerp(values[i],values[j],fraction) if key[1]=='rotation' else values[i]*(1-fraction)+values[j]*fraction
            else:raise ValueError('Unsupported glTF interpolation')
            array={'translation':t,'rotation':q,'scale':scale}.get(key[1])
            if array is None:raise ValueError('Unsupported glTF animated property')
            array[key[0]]=value
        return t,q,scale


def slerp(a,b,f):
    a=a/np.linalg.norm(a);b=b/np.linalg.norm(b);dot=float(a@b)
    if dot<0:b=-b;dot=-dot
    if dot>.9995:q=a*(1-f)+b*f
    else:
        angle=np.arccos(np.clip(dot,-1,1));q=(np.sin((1-f)*angle)*a+np.sin(f*angle)*b)/np.sin(angle)
    return q/np.linalg.norm(q)


def rotation(q):
    x,y,z,w=q/np.linalg.norm(q)
    return np.array([[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],
                     [2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],
                     [2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]])


def decompose(matrix):
    scale=np.linalg.norm(matrix[:3,:3],axis=0)
    if np.any(scale<=0):raise ValueError('Singular glTF transform')
    rot=matrix[:3,:3]/scale
    if np.linalg.det(rot)<0:scale[0]*=-1;rot[:,0]*=-1
    if not np.allclose(rot.T@rot,np.eye(3),atol=1e-5,rtol=0):
        raise ValueError('Inverse-bind shear exceeds numerical export tolerance')
    u,_,v=np.linalg.svd(rot);rot=u@v
    return matrix[:3,3],quaternion(rot),scale


def worlds(glb,trs):
    t,q,s=trs;result=np.empty((len(t),4,4))
    for i in glb.order:
        local=np.eye(4);local[:3,:3]=rotation(q[i])*s[i];local[:3,3]=t[i]
        result[i]=local if glb.parents[i]<0 else result[glb.parents[i]]@local
    return result


def source_positions(glb,geo,trs):
    global_matrices=worlds(glb,trs)[geo['skin']['joints']]@geo['inverse_bind']
    p=np.c_[geo['POSITION'],np.ones(len(geo['POSITION']))]
    w=geo['WEIGHTS_0'].astype(float);w/=w.sum(axis=1,keepdims=True)
    result=np.zeros((len(p),3))
    for slot in range(4):
        result+=np.einsum('vij,vj->vi',global_matrices[geo['JOINTS_0'][:,slot].astype(int),:3],p)*w[:,slot,None]
    return result
