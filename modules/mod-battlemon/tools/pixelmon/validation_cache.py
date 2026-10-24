"""Content-addressed deep checks; any asset, policy or validator change invalidates reuse."""
import hashlib
import json
import os
from pathlib import Path
import platform
import numpy as np
import PIL


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def signature(model, entry, expected_texture):
    dependencies = ['validation_cache.py', 'validate.py', 'texture.py', 'alpha_material.py', 'convert.py',
                    'source_motion.py', 'bmd.py', 'emissive.py', 'repeated_atlas.py', 'reviewed_geometry.json',
                    'shell_review.py', 'reviewed_alpha_shells.json', 'glb_source.py', 'glb_prepare.py',
                    'glb_pipeline.py', 'reviewed_glb.json']
    return dict(schema=1, validators={n:sha(Path(__file__).with_name(n)) for n in dependencies},
                runtime=[platform.python_version(), np.__version__, PIL.__version__],
                files={ext:sha(model.with_name(model.stem+ext)) for ext in ['.m2','00.skin','.blp']},
                shell_review=entry.get('shell_review'), geometry_review=entry.get('geometry_review'),
                glb_review=entry.get('glb_review'), skeleton_policy=entry.get('skeleton_policy','baked'),
                motion=entry.get('source_motion','animated'),
                motion_proof=entry.get('motion_proof'),
                texture_policy=entry.get('texture_policy','solid_alpha_key'),
                alpha_source_sha256=entry.get('alpha_source_sha256'), expected_texture=expected_texture)


def check_policy(entry):
    skeleton = entry.get('skeleton_policy', 'baked')
    if skeleton == 'glb_hierarchical_trs':
        from shell_review import verify_proof
        if not entry.get('glb_review') or entry.get('texture_policy') != 'source_alpha_emissive_twosided':
            raise ValueError('Missing reviewed GLB skeleton/material proof')
        verify_proof(entry['glb_review'], Path(__file__).with_name('reviewed_glb.json'))
    elif skeleton != 'baked' or entry.get('glb_review'):
        raise ValueError('Unknown or mismatched skeleton proof')
    if entry.get('texture_policy') == 'source_alpha_emissive_twosided' and skeleton != 'glb_hierarchical_trs':
        raise ValueError('Two-sided GLB policy requires hierarchical skeleton')
    if entry.get('geometry_review') is not None:
        from shell_review import verify_proof
        verify_proof(entry['geometry_review'], Path(__file__).with_name('reviewed_geometry.json'))
    if entry.get('shell_review') is not None:
        from shell_review import verify_proof
        if entry.get('texture_policy') != 'source_alpha_blend':
            raise ValueError('Reviewed source-alpha shell cannot use another material policy')
        verify_proof(entry['shell_review'])
    if entry.get('source_motion') == 'source_constant_walk':
        from source_motion import validate_constant_walk
        if not entry.get('motion_proof'):
            raise ValueError('Missing constant-walk source proof')
        validate_constant_walk(entry['motion_proof'])
    policy = entry.get('texture_policy','solid_alpha_key')
    if policy == 'source_alpha_emissive' and not entry.get('geometry_review'):
        raise ValueError('Missing reviewed emissive source/export proof')
    if policy not in {'solid_alpha_key','source_alpha_blend','source_alpha_emissive','source_alpha_emissive_twosided'}:
        raise ValueError('Unknown texture policy')
    if policy in {'source_alpha_blend','source_alpha_emissive','source_alpha_emissive_twosided'}:
        if not entry.get('alpha_source') or not entry.get('alpha_source_sha256'):
            raise ValueError('Missing authored alpha proof')
        if sha(entry['alpha_source']) != entry['alpha_source_sha256']:
            raise ValueError('Authored alpha source changed')
    return policy


def validate_asset(model, entry, expected_texture, cache):
    from validate import read_model
    from texture import filtered_edge_alpha
    from alpha_material import validate_alpha_texture
    model = Path(model)
    policy = check_policy(entry)
    evidence = signature(model,entry,expected_texture)
    key = hashlib.sha256(json.dumps(evidence,sort_keys=True).encode()).hexdigest()
    receipt = Path(cache)/(key+'.json')
    if receipt.exists():
        try:
            old = json.loads(receipt.read_text())
            if old == dict(status='passed',evidence=evidence):
                return True
        except (ValueError,OSError):
            pass
    decoded = read_model(model, source_motion=entry.get('source_motion','animated'), texture_policy=policy,
                         skeleton_policy=entry.get('skeleton_policy','baked'))
    if np.max(decoded['bounds'][1]-decoded['bounds'][0]) > 6 and not entry.get('geometry_review'):
        raise ValueError('Missing reviewed extreme-bounds source/export proof')
    if decoded['texture'] != expected_texture:
        raise ValueError('M2 texture reference mismatch')
    if policy in {'source_alpha_blend','source_alpha_emissive','source_alpha_emissive_twosided'}:
        validate_alpha_texture(model.with_suffix('.blp'),entry['alpha_source'],entry['alpha_source_sha256'],
                               decoded['uv'],decoded['triangles'])
    elif any(x['minimum_alpha'] < 240 for x in filtered_edge_alpha(
            model.with_suffix('.blp'),decoded['uv'],decoded['triangles'])):
        raise ValueError('Texture seam validation failed')
    receipt.parent.mkdir(parents=True,exist_ok=True)
    temporary = receipt.with_suffix('.'+str(os.getpid())+'.tmp')
    temporary.write_text(json.dumps(dict(status='passed',evidence=evidence),sort_keys=True)+'\n')
    temporary.replace(receipt)
    return False
