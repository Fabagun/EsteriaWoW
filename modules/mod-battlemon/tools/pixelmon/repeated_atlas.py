"""Bounded source-repeat sampling. Affine UV mapping into pixel-exact repeated source images."""
import json
from pathlib import Path
import numpy as np
from PIL import Image

def sample(image, uv):
    h,w = image.shape[:2]
    xy=np.asarray(uv)*[w,h]-.5
    lo=np.floor(xy).astype(np.int64); f=xy-lo
    a=image[lo[:,1]%h,lo[:,0]%w].astype(float)
    b=image[lo[:,1]%h,(lo[:,0]+1)%w].astype(float)
    c=image[(lo[:,1]+1)%h,lo[:,0]%w].astype(float)
    d=image[(lo[:,1]+1)%h,(lo[:,0]+1)%w].astype(float)
    return ((a*(1-f[:,0,None])+b*f[:,0,None])*(1-f[:,1,None])+
            (c*(1-f[:,0,None])+d*f[:,0,None])*f[:,1,None])

def create_atlas(uv, base, glow, destination):
    uv=np.asarray(uv,dtype=float)
    if uv.ndim!=2 or uv.shape[1]!=2 or not len(uv) or not np.isfinite(uv).all():
        raise ValueError('Finite two-dimensional UVs required')
    if np.ptp(uv,axis=0).max()>4 or np.abs(uv).max()>8:
        raise ValueError('Bounded source wrapping bounds exceeded')
    paths=[Path(base),Path(glow)]
    if any(Path(str(p)+'.mcmeta').exists() for p in paths):
        raise ValueError('Explicit texture metadata requires separate sampler review')
    images=[np.array(Image.open(p).convert('RGBA')) for p in paths]
    if images[0].shape!=images[1].shape:
        raise ValueError('Different texture dimensions require separate sampling proof')
    h,w=images[0].shape[:2]
    origin=np.floor(uv.min(axis=0)*[w,h]).astype(int)-32
    needed=np.ceil(uv.max(axis=0)*[w,h]).astype(int)-origin+32
    tw,th=[1<<(int(n)-1).bit_length() for n in needed]
    if tw*2>4096 or th>4096:
        raise ValueError('Repeated atlas exceeds 4096 pixels')
    x=(np.arange(tw)+origin[0])%w; y=(np.arange(th)+origin[1])%h
    atlas=np.concatenate([im[y[:,None],x[None,:]] for im in images],axis=1)
    mapped=(uv*[w,h]-origin)/[tw*2,th]
    # Test original vertices and interior samples spanning every crossed repeat boundary.
    rng=np.random.default_rng(42020)
    probes=np.concatenate([uv,rng.uniform(uv.min(axis=0),uv.max(axis=0),(20000,2))])
    target=(probes*[w,h]-origin)/[tw*2,th]
    errors=[]
    for i,im in enumerate(images):
        errors.append(float(np.max(np.abs(sample(im,probes)-sample(atlas,target+[i*.5,0])))))
    if max(errors)>1e-6:
        raise ValueError('Source/atlas bilinear sampling disagreement')
    out=Path(destination);out.parent.mkdir(parents=True,exist_ok=True)
    Image.fromarray(atlas).save(out)
    proof=dict(requires_exact_export_review=True,source_size=[w,h],tile_size=[tw,th],origin=origin.tolist(),
               uv_min=uv.min(axis=0).tolist(),uv_max=uv.max(axis=0).tolist(),
               mapping='(source_uv * source_size - origin) / atlas_size; glow u += 0.5',
               base_and_glow_max_rgba_error=errors,probes_per_layer=len(probes),
               note='No source resizing, vertex modulo, clamping or geometry changes. Mip and serialized UV review still required.')
    out.with_suffix('.sampling.json').write_text(json.dumps(proof,indent=2))
    return mapped,out,proof
