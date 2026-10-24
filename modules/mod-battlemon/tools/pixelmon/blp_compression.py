"""Final delivery compression. Raw source validation remains separate and unchanged."""
from pathlib import Path
from io import BytesIO
import hashlib
import shutil
import struct
import numpy as np
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'generated/source-catalog/compression-dependencies'))
import ispc_texcomp
import PIL
from PIL import Image

def raw_mips(p):
 d=p.read_bytes()
 if d[:4]!=b'BLP2' or d[8]!=3 or d[9]!=8:raise ValueError('Not raw 8-bit alpha BLP: '+str(p))
 w,h=struct.unpack_from('<2I',d,12);ofs=struct.unpack_from('<16I',d,20);sizes=struct.unpack_from('<16I',d,84)
 images=[]
 for i,o in enumerate(ofs):
  if not o:break
  size=(max(1,w>>i),max(1,h>>i))
  if sizes[i]!=size[0]*size[1]*4 or o+sizes[i]>len(d):raise ValueError('Invalid raw mip')
  images.append(Image.frombytes('RGBA',size,d[o:o+sizes[i]],'raw','BGRA'))
 if not images:raise ValueError('No mip data')
 return images

def delivery_mips(images):
 w,h=images[0].size
 limit=(1024,512) if w>h else (512,512)
 return [im for im in images if im.width<=limit[0] and im.height<=limit[1]]

def encode(images):
 offsets=[0]*16;sizes=[0]*16;chunks=[];pos=1172;metrics=[]
 for i,im in enumerate(images):
  a=np.array(im);h,w=a.shape[:2]
  padded=np.pad(a,((0,max(4,h)-h),(0,max(4,w)-w),(0,0)),mode='edge')
  surface=ispc_texcomp.RGBASurface(padded.tobytes(),padded.shape[1],padded.shape[0])
  payload=ispc_texcomp.compress_blocks_bc3(surface)
  dds=(b'DDS '+struct.pack('<7I',124,0x81007,padded.shape[0],padded.shape[1],len(payload),0,0)
       +bytes(44)+struct.pack('<4I',32,4,struct.unpack('<I',b'DXT5')[0],0)+bytes(16)
       +struct.pack('<5I',0x1000,0,0,0,0)+payload)
  if dds[84:88]!=b'DXT5':raise ValueError('Compressor did not write DXT5')
  payload=dds[128:];wanted=((w+3)//4)*((h+3)//4)*16
  if len(payload)!=wanted:raise ValueError('Incorrect block payload length')
  b=np.array(Image.open(BytesIO(dds)).convert('RGBA'))[:h,:w]
  delta=np.abs(a.astype(np.int16)-b.astype(np.int16));visible=a[:,:,3]>0
  metrics.append(dict(mip=i,size=[w,h],rgb_mae_visible=float(delta[:,:,:3][visible].mean()) if visible.any() else 0,
       alpha_mae=float(delta[:,:,3].mean()),alpha_max=int(delta[:,:,3].max()),
       transparent_became_nonzero=int(((a[:,:,3]==0)&(b[:,:,3]!=0)).sum()),
       opaque_became_translucent=int(((a[:,:,3]==255)&(b[:,:,3]!=255)).sum())))
  offsets[i]=pos;sizes[i]=len(payload);pos+=len(payload);chunks.append(payload)
 header=b'BLP2'+struct.pack('<I4B2I',1,2,8,7,1,*images[0].size)
 data=header+struct.pack('<16I',*offsets)+struct.pack('<16I',*sizes)+bytes(1024)+b''.join(chunks)
 # A separate BLP decoder must decode every stored level, including 1x1 tails.
 for i in range(len(images)):
  selected=bytearray(data);struct.pack_into('<2I',selected,12,*images[i].size)
  struct.pack_into('<I',selected,20,offsets[i]);struct.pack_into('<I',selected,84,sizes[i])
  decoded=Image.open(BytesIO(selected));decoded.load()
  if decoded.size!=images[i].size:raise ValueError('BLP decode dimensions disagree')
 return data,metrics

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def require_compressed(path):
    with Path(path).open('rb') as f: header=f.read(12)
    if header[:4]!=b'BLP2' or header[8]!=2:
        raise ValueError('New delivery texture must be compressed BLP2: '+str(path))

def prepare(source,target,backup):
    source,target,backup=map(Path,(source,target,backup))
    raw_hash=digest(source)
    data,quality=encode(delivery_mips(raw_mips(source)))
    # Lossy compression is approved only inside bounded base-level error; no alpha endpoints may change.
    if quality[0]['rgb_mae_visible']>8 or quality[0]['alpha_mae']>5:
        raise ValueError('Compression quality requires separate visual review')
    if any(x['transparent_became_nonzero'] or x['opaque_became_translucent'] for x in quality):
        raise ValueError('Compression altered transparent/opaque endpoints')
    backup.parent.mkdir(parents=True,exist_ok=True)
    if backup.exists() and digest(backup)!=raw_hash:
        raise ValueError('Raw delivery backup changed')
    if not backup.exists():shutil.copyfile(source,backup)
    if digest(backup)!=raw_hash:raise ValueError('Raw backup copy mismatch')
    target.write_bytes(data)
    require_compressed(target)
    return dict(schema=1,encoder_binary_sha256=digest(Path(ispc_texcomp.__file__).with_name('_ispc_texcomp.pyd')),encoder='ispc_texcomp-1.0.1',max_dimension=1024,sizing_policy='512-per-square-layer',encoding='DXT5',raw_sha256=raw_hash,compressed_sha256=digest(target),
                compressor_sha256=digest(Path(__file__)),pillow_version=PIL.__version__,quality=quality)

def verify(source,target,backup,proof):
    if proof.get('encoder_binary_sha256')!=digest(Path(ispc_texcomp.__file__).with_name('_ispc_texcomp.pyd')):raise ValueError('Encoder binary changed')
    if proof.get('encoder')!='ispc_texcomp-1.0.1':raise ValueError('Expected reviewed ISPC encoder')
    if proof.get('sizing_policy')!='512-per-square-layer':raise ValueError('Expected 512 pixels per square texture layer')
    if proof['compressor_sha256']!=digest(Path(__file__)) or proof['pillow_version']!=PIL.__version__:
        raise ValueError('Compression implementation/runtime changed; revalidate explicitly')
    if digest(source)!=proof['raw_sha256'] or digest(backup)!=proof['raw_sha256']:
        raise ValueError('Raw compression evidence changed')
    require_compressed(target)
    if digest(target)!=proof['compressed_sha256']:raise ValueError('Compressed delivery changed')
    data,quality=encode(delivery_mips(raw_mips(Path(source))))
    if hashlib.sha256(data).hexdigest()!=proof['compressed_sha256'] or quality!=proof['quality']:
        raise ValueError('Compression cannot be independently reproduced')
    if quality[0]['rgb_mae_visible']>8 or quality[0]['alpha_mae']>5 or any(
        x['transparent_became_nonzero'] or x['opaque_became_translucent'] for x in quality):
        raise ValueError('Compression quality gate failed')
