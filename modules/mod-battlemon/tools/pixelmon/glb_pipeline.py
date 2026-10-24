"""Closed GLB adapter; production acceptance requires an exact reviewed source/export proof."""
from pathlib import Path
import time
import numpy as np
from catalog import Unsupported,resource_path
from glb_source import GLB


def resolve(source,species,source_form,group,palette,definition):
    if set(definition)!={'model_type','model','texture','emissive'}:
        raise Unsupported('glb_model_definition_requires_review')
    model=resource_path(source,definition['model'])
    if model.suffix.lower()!='.glb':raise Unsupported('assimp_model_format_requires_review')
    embedded=definition['texture']=='minecraft:textures/none'
    texture=model if embedded else resource_path(source,definition['texture'])
    paths=list((source/'data/pixelmon/species').glob(f"{species['dex']:03}_*.json"))
    if len(paths)!=1:raise Unsupported('ambiguous_glb_metadata')
    return dict(model=str(model),texture=str(texture),emissive=str(resource_path(source,definition['emissive'])),
        metadata=str(paths[0]),embedded_texture=embedded,model_format='glb',animations={},fps=24,
        source_form=source_form['name'],source_palette=palette['name'],gender=group['gender'],parts=[],
        source_motion='animated',source_transform=None,legacy_texture_transparency=[],
        notes=['embedded_glb_animations','source_emissive_retained','source_double_sided_material_retained'])


def convert_one(output,appearance,revision):
    from batch import atomic_json,digest
    from glb_prepare import prepare_glb
    from m2 import build_model
    from emissive import prepare_overlay
    from alpha_material import write_alpha_blp,validate_alpha_texture,source_digest
    from texture import decode_blp,filtered_edge_alpha
    from validate import read_model
    from shell_review import approve_export
    start=time.monotonic();asset='a_'+appearance['key'][:20]
    mesh=prepare_glb(Path(appearance['model']))
    glb=mesh['glb_source'];geo=mesh['glb_geometry']
    material=geo['material']
    if (not material.get('doubleSided') or material.get('alphaMode','OPAQUE')!='OPAQUE'
            or material.get('extensions') or material.get('normalTexture')
            or material.get('occlusionTexture') or material.get('emissiveTexture')
            or material['pbrMetallicRoughness'].get('baseColorFactor',[1,1,1,1])!=[1,1,1,1]):
        raise Unsupported('glb_material_requires_review')
    texture=Path(appearance['texture'])
    folder=output/'cache/glb';folder.mkdir(parents=True,exist_ok=True)
    if appearance['embedded_texture']:
        texture_index=material['pbrMetallicRoughness']['baseColorTexture']['index']
        image_index=glb.data['textures'][texture_index]['source'];image=glb.data['images'][image_index]
        if image.get('mimeType')!='image/png' or 'uri' in image:raise Unsupported('glb_embedded_texture_format')
        view=glb.data['bufferViews'][image['bufferView']]
        texture=folder/(appearance['key']+'-embedded.png')
        texture.write_bytes(glb.binary[view.get('byteOffset',0):view.get('byteOffset',0)+view['byteLength']])
    mesh,atlas=prepare_overlay(mesh,[{'texture':str(texture),'emissive':appearance['emissive']}],folder/(appearance['key']+'-atlas.png'))
    assets=output/'cache/assets';assets.mkdir(parents=True,exist_ok=True);model=assets/(asset+'.m2')
    policy='source_alpha_emissive_twosided';skeleton='glb_hierarchical_trs'
    raw,skin=build_model(mesh,asset,'Creature\\Battlemon3DBatch\\'+asset+'.blp',texture_policy=policy)
    model.write_bytes(raw);model.with_name(asset+'00.skin').write_bytes(skin)
    write_alpha_blp(model.with_suffix('.blp'),atlas)
    decoded=read_model(model,texture_policy=policy,skeleton_policy=skeleton)
    alpha=validate_alpha_texture(model.with_suffix('.blp'),atlas,source_digest(atlas),decoded['uv'],decoded['triangles'])
    try:proof=approve_export(appearance,model,Path(__file__).with_name('reviewed_glb.json'))
    except ValueError as error:raise Unsupported('glb_source_export_requires_closed_review') from error
    preview=output/'preview/data';preview.mkdir(parents=True,exist_ok=True)
    decode_blp(model.with_suffix('.blp')).save(preview/(asset+'.png'))
    atomic_json(preview/(asset+'.json'),dict(positions=decoded['poses'][0][0].tolist(),triangles=decoded['triangles'].tolist(),uv=decoded['uv'].tolist(),texture=asset+'.png'))
    edges=filtered_edge_alpha(model.with_suffix('.blp'),decoded['uv'],decoded['triangles'])
    return dict(status='passed',asset=asset,files={asset+ext:digest(assets/(asset+ext)) for ext in ['.m2','00.skin','.blp']},
        bounds=[b.tolist() for b in mesh['bounds']],vertices=len(mesh['vertices']),triangles=len(mesh['triangles'])//3,
        bones=len(mesh['bones']),source=appearance,notes=appearance['notes'],source_motion='animated',
        skeleton_policy=skeleton,glb_review=proof,texture_policy=policy,alpha_source=str(atlas.resolve()),
        alpha_source_sha256=source_digest(atlas),alpha_validation=alpha,mesh_reused=False,
        seconds=round(time.monotonic()-start,3),skinning_reference='glb_reviewed_independent_blender_oracle',
        min_edge_alpha=min(r['minimum_alpha'] for r in edges))
