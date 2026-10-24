"""Retain a source emissive texture as a full-bright second draw, in one canonical BLP."""
import numpy as np
from multipart import make_atlas


def prepare_overlay(mesh, parts, destination):
    textures={p['texture'] for p in parts}
    emissions={p.get('emissive') for p in parts}
    if len(textures)!=1 or len(emissions)!=1 or None in emissions:
        raise ValueError('Emissive multipart requires reviewed shared texture pair')
    base,glow=next(iter(textures)),next(iter(emissions))
    if base==glow:
        raise ValueError('Distinct emissive source texture required')
    vertices=mesh['vertices'].copy()
    if np.any(vertices[:,6:8]<0) or np.any(vertices[:,6:8]>1):
        from repeated_atlas import create_atlas
        mapped, atlas, proof = create_atlas(vertices[:,6:8], base, glow, destination)
        vertices[:,6:8] = mapped
        return dict(mesh, vertices=vertices, emissive_overlay=True), atlas
    vertices[:,6]=(1/32+vertices[:,6]*15/16)/2
    vertices[:,7]=1/32+vertices[:,7]*15/16
    return dict(mesh,vertices=vertices,emissive_overlay=True),make_atlas([base,glow],destination)


def overlay_layout(layout):
    count=len(layout['vertices']);index_count=len(layout['triangles'])
    if max(count*2,index_count*2)>65535:
        raise ValueError('Emissive overlay exceeds 16-bit skin limits')
    overlay=layout['vertices'].copy();overlay[:,6]+=.5
    sections=[dict(s,material=0) for s in layout['sections']]
    sections += [dict(s,vertex_start=s['vertex_start']+count,index_start=s['index_start']+index_count,
                      material=1) for s in layout['sections']]
    return dict(layout,vertices=np.concatenate([layout['vertices'],overlay]),
        weights=layout['weights']*2,properties=layout['properties']*2,original=layout['original']*2,
        triangles=layout['triangles']+[v+count for v in layout['triangles']],sections=sections)
