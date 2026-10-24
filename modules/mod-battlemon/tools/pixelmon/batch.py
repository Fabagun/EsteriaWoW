"""Resumable, token-free Pixelmon batch conversion. No network or model API calls."""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

import numpy as np
from PIL import Image

from catalog import inventory, Unsupported
from convert import MODULE, Dbc, float_bits, write_blp, write_dbc
from m2 import prepare, build_model
from texture import filtered_edge_alpha, decode_blp
from validate import read_model

LAYER = '.dbc9-battlemon-3d-batch'
ASSETS = 'Creature/Battlemon3DBatch'
DEFAULT_SOURCE = Path('F:/_d-bak/_other/Pixelmon-1.21.1-9.4.0-universal')
DEFAULT_CLIENT = Path('D:/WoW/Dark-Bro-WXL-COA/Dark-Brotherhood-wxl')
DEFAULT_OUTPUT = MODULE/'generated/pixelmon-batch'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name+f'.{os.getpid()}.tmp')
    temporary.write_text(json.dumps(value, indent=2)+'\n', encoding='utf8', newline='\n')
    temporary.replace(path)


def version():
    names = ['batch.py', 'catalog.py', 'bmd.py', 'm2.py', 'convert.py', 'texture.py', 'validate.py', 'skin_sections.py',
             'variant_aliases.json', 'validation_cache.py', 'source_motion.py', 'source_skinning.py', 'bone_binding.py',
             'alpha_material.py', 'multipart.py', 'batch_deploy.py',
             'model_transform.py', 'emissive.py', 'repeated_atlas.py', 'reviewed_geometry.json',
             'shell_review.py', 'reviewed_alpha_shells.json', 'run_full_batch.py',
             'glb_source.py', 'glb_prepare.py', 'glb_pipeline.py', 'reviewed_glb.json']
    return hashlib.sha256(''.join(digest(Path(__file__).with_name(n)) for n in names).encode()).hexdigest()


def fingerprint(appearance, revision, texture=True):
    parts = appearance.get('parts') or [appearance]
    files = [p['model'] for p in parts]
    for p in parts:
        files.extend(p.get('animations', appearance['animations']).values())
    if texture:
        files.extend(p['texture'] for p in parts)
        files.extend(p['emissive'] for p in parts if p.get('emissive'))
    if appearance.get('model_format') == 'glb':
        files.append(appearance['metadata'])
    texture_order = list(dict.fromkeys(p['texture'] for p in parts))
    content = dict(revision=revision, fps=appearance['fps'],
                   source_motion=appearance.get('source_motion', 'animated'),
                   parts=[(p['model'], texture_order.index(p['texture']), p.get('source_transform')) for p in parts],
                   files=[(p, digest(p)) for p in files])
    return hashlib.sha256(json.dumps(content, sort_keys=True).encode()).hexdigest()


def save_mesh(path, mesh):
    meta = {k: v for k, v in mesh.items() if k not in ['vertices', 'triangles', 'sequences', 'bounds']}
    meta['bounds'] = [v.tolist() for v in mesh['bounds']]
    meta['sequences'] = [{k: v for k, v in s.items() if k not in ['times', 'translations', 'rotations', 'bounds']}
                         | {'bounds': [v.tolist() for v in s['bounds']]} for s in mesh['sequences']]
    data = dict(meta=np.array(json.dumps(meta)), vertices=mesh['vertices'], triangles=np.array(mesh['triangles']))
    for i, sequence in enumerate(mesh['sequences']):
        for key in ['times', 'translations', 'rotations']:
            data[f'{i}_{key}'] = sequence[key]
    temporary = path.with_suffix('.tmp.npz')
    np.savez_compressed(temporary, **data)
    temporary.replace(path)


def load_mesh(path):
    with np.load(path, allow_pickle=False) as data:
        mesh = json.loads(str(data['meta']))
        mesh['vertices'], mesh['triangles'] = data['vertices'], data['triangles'].tolist()
        mesh['bounds'] = tuple(np.array(v) for v in mesh['bounds'])
        for i, sequence in enumerate(mesh['sequences']):
            sequence['bounds'] = tuple(np.array(v) for v in sequence['bounds'])
            for key in ['times', 'translations', 'rotations']:
                sequence[key] = data[f'{i}_{key}']
    return mesh


def check_texture_interior(texture, mesh):
    # Solid-mesh padding must not erase intentional holes in wings, smoke, or foliage cards.
    alpha = np.array(Image.open(texture).convert('RGBA'))[:, :, 3]
    uv = mesh['vertices'][np.array(mesh['triangles']).reshape(-1, 3), 6:8]
    samples = np.concatenate([np.einsum('i,tij->tj', bary, uv)
                              for bary in [(1/3, 1/3, 1/3), (.6, .2, .2), (.2, .6, .2), (.2, .2, .6)]])
    xy = np.floor(samples*np.array([alpha.shape[1], alpha.shape[0]])).astype(int)
    values = alpha[np.clip(xy[:, 1], 0, alpha.shape[0]-1), np.clip(xy[:, 0], 0, alpha.shape[1]-1)]
    if np.count_nonzero(values < 128) > max(3, len(values)*0.005):
        raise Unsupported('interior_transparency_requires_material_review')


def cached_result(output, key, retry_failed=False):
    path = output/'cache/results'/(key+'.json')
    if not path.exists():
        return None
    try:
        result = json.loads(path.read_text())
        if result['status'] != 'passed':
            return None if retry_failed else result
        if all((output/'cache/assets'/p).is_file() and digest(output/'cache/assets'/p) == h
               for p, h in result['files'].items()):
            return result
    except (ValueError, KeyError, OSError):
        pass
    return None


def convert_one(output, appearance, revision):
    if appearance.get('model_format') == 'glb':
        from glb_pipeline import convert_one as convert_glb
        return convert_glb(output, appearance, revision)
    start = time.monotonic()
    key = appearance['key']
    asset = 'a_'+key[:20]
    geometry_key = fingerprint(appearance, revision, texture=False)
    mesh_path = output/'cache/meshes'/(geometry_key+'.npz')
    mesh_path.parent.mkdir(parents=True, exist_ok=True)
    mesh_reused = mesh_path.exists()
    if mesh_reused:
        mesh = load_mesh(mesh_path)
    else:
        animations = {k: Path(v) for k, v in appearance['animations'].items()}
        if appearance.get('parts'):
            from multipart import compose
            meshes = [prepare(Path(p['model']),
                              {k: Path(v) for k, v in p.get('animations', appearance['animations']).items()},
                              height=None, fps=appearance['fps'], source_transform=p.get('source_transform'))
                      for p in appearance['parts']]
            mesh = compose(meshes, [p['texture'] for p in appearance['parts']])
        else:
            mesh = prepare(Path(appearance['model']), animations, fps=appearance['fps'],
                           static_bind_pose=appearance.get('source_motion') == 'static_bind_pose',
                           source_transform=appearance.get('source_transform'))
        if mesh['skinning_error'] > 0.08:
            raise Unsupported('four_weight_deformation_exceeds_8_percent_height')
        save_mesh(mesh_path, mesh)
    texture = appearance['texture']
    if appearance.get('parts'):
        from multipart import make_atlas
        texture = make_atlas([p['texture'] for p in appearance['parts']], output/'cache/atlases'/(key+'.png'))
    emissive = any(p.get('emissive') for p in (appearance.get('parts') or [appearance]))
    if emissive:
        from emissive import prepare_overlay
        mesh, texture = prepare_overlay(mesh, appearance.get('parts') or [appearance], output/'cache/emissive'/(key+'.png'))
    policy = 'solid_alpha_key'
    try:
        check_texture_interior(texture, mesh)
    except Unsupported:
        policy = 'source_alpha_blend'
    if emissive:
        policy = 'source_alpha_emissive'
    assets = output/'cache/assets'
    assets.mkdir(parents=True, exist_ok=True)
    from alpha_material import write_alpha_blp, validate_alpha_texture, source_digest
    source_motion = appearance.get('source_motion', 'animated')
    model = assets/(asset+'.m2')
    if policy == 'solid_alpha_key':
        write_blp(model.with_suffix('.blp'), texture)
        preliminary = filtered_edge_alpha(model.with_suffix('.blp'), mesh['vertices'][:,6:8],
                                           np.array(mesh['triangles']).reshape(-1,3))
        if any(level['unsafe_alpha_key_samples'] for level in preliminary):
            policy = 'source_alpha_blend'
    m2, skin = build_model(mesh, asset, (ASSETS+'/'+asset+'.blp').replace('/', '\\'), texture_policy=policy)
    model.write_bytes(m2)
    model.with_name(asset+'00.skin').write_bytes(skin)
    if policy in {'source_alpha_blend', 'source_alpha_emissive'}:
        write_alpha_blp(model.with_suffix('.blp'), texture)
    motion_proof = None
    try:
        decoded = read_model(model, source_motion=source_motion, texture_policy=policy)
    except ValueError as error:
        if str(error) != 'Walk sequence is static' or source_motion != 'animated':
            raise
        from source_motion import constant_walk_proof
        motion_proof = constant_walk_proof(appearance)
        source_motion = 'source_constant_walk'
        decoded = read_model(model, source_motion=source_motion, texture_policy=policy)

    geometry_proof = None
    if np.max(mesh['bounds'][1]-mesh['bounds'][0]) > 6 or emissive:
        from shell_review import approve_export
        try:
            geometry_proof = approve_export(appearance, model, Path(__file__).with_name('reviewed_geometry.json'))
        except ValueError as error:
            raise Unsupported('geometry_or_source_timing_requires_review') from error

    shell_proof = None
    if (policy in {'source_alpha_blend', 'source_alpha_emissive'} and appearance.get('legacy_texture_transparency')
            and appearance.get('parts') and not geometry_proof):
        from shell_review import approve_export
        try:
            shell_proof = approve_export(appearance, model)
        except ValueError as error:
            raise Unsupported('multipart_opacity_requires_source_render_review') from error

    alpha_proof = None
    if policy in {'source_alpha_blend', 'source_alpha_emissive'}:
        alpha_proof = validate_alpha_texture(model.with_suffix('.blp'), texture, source_digest(texture),
                                            decoded['uv'], decoded['triangles'])
    edges = filtered_edge_alpha(model.with_suffix('.blp'), decoded['uv'], decoded['triangles'])
    if policy == 'solid_alpha_key' and any(level['unsafe_alpha_key_samples'] for level in edges):
        raise Unsupported('texture_seam_validation_failed')
    # Small, decoded output previews; full animations remain in the M2.
    preview = output/'preview/data'
    preview.mkdir(parents=True, exist_ok=True)
    decode_blp(model.with_suffix('.blp')).save(preview/(asset+'.png'))
    atomic_json(preview/(asset+'.json'), dict(triangles=decoded['triangles'].tolist(), uv=decoded['uv'].tolist(),
                positions=decoded['poses'][0][0].tolist(), texture=asset+'.png'))
    return dict(status='passed', asset=asset, files={asset+ext: digest(assets/(asset+ext))
                for ext in ['.m2', '00.skin', '.blp']}, bounds=[v.tolist() for v in mesh['bounds']],
                vertices=len(mesh['vertices']), triangles=len(mesh['triangles'])//3, bones=len(mesh['bones']),
                skinning_error=mesh['skinning_error'], binding_notes=mesh.get('binding_notes', []),
                skinning_reference=mesh.get('skinning_reference'),
                unlimited_weight_difference=mesh.get('unlimited_weight_difference'),
                mesh_reused=mesh_reused,
                seconds=round(time.monotonic()-start, 3), source=appearance,
                texture_policy=policy, alpha_source=str(Path(texture).resolve()) if alpha_proof else None,
                alpha_source_sha256=source_digest(texture) if alpha_proof else None, alpha_validation=alpha_proof,
                notes=appearance['notes']+(['source_walk_channels_constant'] if motion_proof else []),
                source_motion=source_motion, motion_proof=motion_proof, shell_review=shell_proof,
                geometry_review=geometry_proof,
                min_edge_alpha=min(r['minimum_alpha'] for r in edges))


def worker(job_path):
    job = json.loads(job_path.read_text())
    output = Path(job['output'])
    for appearance in job['appearances']:
        try:
            result = convert_one(output, appearance, job['revision'])
        except Exception as error:
            result = dict(status='failed', reason=type(error).__name__+': '+str(error))
        atomic_json(output/'cache/results'/(appearance['key']+'.json'), result)


def package(output, client, records):
    dbc_dir = client/'Data/patch-z.mpq/DBFilesClient'
    models = Dbc(dbc_dir/'CreatureModelData.dbc1-battlemon')
    displays = Dbc(dbc_dir/'CreatureDisplayInfo.dbc1-battlemon')
    if (models.fields, displays.fields) != (28, 16):
        raise ValueError('Unexpected WotLK DBC layout')
    package_dir = output/'package'
    (package_dir/'client'/ASSETS).mkdir(parents=True, exist_ok=True)
    model_rows, display_rows, delivered, files = [], [], [], {}
    for record in records:
        if record['status'] != 'passed':
            continue
        result = record['result']
        asset = result['asset']
        display_id = (60000 if record['shiny'] else 50000)+record['form']
        dr = displays.rows[display_id].copy()
        mr = models.rows[dr[1]].copy()
        if not models.string(mr[2]).lower().startswith('creature\\battlemon\\'):
            raise ValueError('Refusing to override a non-Battlemon model')
        mn, mx = np.array(result['bounds'])
        mr[1], mr[4] = 0, float_bits(1)
        mr[14], mr[15] = float_bits(max(mx[0]-mn[0], mx[1]-mn[1])), float_bits(mx[2]-mn[2])
        mr[17:23] = [float_bits(v) for v in [*mn, *mx]]
        dr[4] = float_bits(1)
        model_rows.append((mr, {2: (ASSETS+'/'+asset+'.mdx').replace('/', '\\')}))
        display_rows.append((dr, {i: '' for i in [6, 7, 8, 9]}))
        for filename, hash_value in result['files'].items():
            relative = 'client/'+ASSETS+'/'+filename
            shutil.copyfile(output/'cache/assets'/filename, package_dir/relative)
            files[relative] = hash_value
        delivered.append(dict(form=record['form'], name=record['name'], shiny=record['shiny'],
                              display=display_id, model=mr[0], asset=asset, notes=result['notes'],
                              source_motion=result.get('source_motion', 'animated'),
                              motion_proof=result.get('motion_proof'), shell_review=result.get('shell_review'),
                              geometry_review=result.get('geometry_review'), glb_review=result.get('glb_review'),
                              skeleton_policy=result.get('skeleton_policy','baked'),
                              texture_policy=result.get('texture_policy','solid_alpha_key'),
                              alpha_source=result.get('alpha_source'),
                              alpha_source_sha256=result.get('alpha_source_sha256')))
    if not delivered:
        raise ValueError('No validated appearances to package')
    for name, rows, fields, columns in [('CreatureModelData', model_rows, 28, [2]),
                                       ('CreatureDisplayInfo', display_rows, 16, [6, 7, 8, 9])]:
        if len({r[0][0] for r in rows}) != len(rows):
            raise ValueError('Duplicate model/display IDs in batch')
        for folder in ['client/DBFilesClient', 'server/dbc-continuations']:
            path = package_dir/folder/(name+LAYER)
            path.parent.mkdir(parents=True, exist_ok=True)
            write_dbc(path, rows, fields, columns)
            files[path.relative_to(package_dir).as_posix()] = digest(path)
    atomic_json(package_dir/'manifest.json', dict(schema=1, layer=LAYER, files=files, appearances=delivered))


def preserved_records(output, report_path):
    """Pin previously validated exports across converter revisions; never forge cache keys."""
    if not report_path:
        return {}
    report = json.loads(Path(report_path).read_text(encoding='utf8'))
    result = {}
    for record in report['records']:
        if record['status'] != 'passed':
            continue
        key = (record['form'], record['shiny'])
        if key in result:
            raise ValueError('Duplicate preserved appearance')
        if not record['result'].get('files'):
            raise ValueError('Preserved appearance has no checksums')
        for name, wanted in record['result']['files'].items():
            path = (output/'cache/assets'/name).resolve()
            if not path.is_relative_to((output/'cache/assets').resolve()) or digest(path) != wanted:
                raise ValueError('Preserved asset checksum/path mismatch: ' + name)
        result[key] = record
    return result


def recovery_record(previous, candidate):
    """A failed correction must retain the prior validated appearance."""
    if candidate['status'] == 'passed':
        return candidate
    return previous


def run(args):
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    revision = version()
    preserved = preserved_records(output, getattr(args, 'preserve_passed', None))
    entries, sample = inventory(args.pixelmon.resolve(), args.client.resolve())
    atomic_json(output/'inventory.json', dict(forms=entries, sample=sample))
    if args.command == 'inventory':
        print('Mapped appearances:', sum(a['status']=='mapped' for e in entries for a in e['appearances']))
        return
    selected = set(sample if not args.all else [e['form'] for e in entries])
    if args.forms:
        selected = {int(v) for v in args.forms.split(',')}
        if not selected <= {e['form'] for e in entries}:
            raise ValueError('Unknown form ID')
    refresh_forms = {int(v) for v in getattr(args, 'refresh_forms', '').split(',') if v}
    if refresh_forms and (not preserved or not refresh_forms <= selected):
        raise ValueError('Refresh forms require a preserved report and selected known IDs')
    records, refresh_results = [], []
    completed = reused = 0
    for entry in entries:
        if entry['form'] not in selected:
            continue
        pending = []
        for a in entry['appearances']:
            if (entry['form'], a['shiny']) in preserved and entry['form'] not in refresh_forms:
                reused += 1
                continue
            if a['status'] == 'mapped':
                a['key'] = fingerprint(a, revision)
                old = cached_result(output, a['key'], args.retry_failed)
                if old:
                    reused += 1
                else:
                    pending.append(a)
        if pending:
            job_path = output/'cache/jobs'/(str(entry['form'])+'.json')
            atomic_json(job_path, dict(output=str(output), revision=revision, appearances=pending))
            log = output/'cache/jobs'/(str(entry['form'])+'.log')
            with log.open('w', encoding='utf8') as stream:
                try:
                    process = subprocess.run([sys.executable, str(Path(__file__).resolve()), 'worker',
                                              '--job', str(job_path)], stdout=stream, stderr=stream,
                                             timeout=max(args.timeout, 900) if any(x.get('model_format')=='glb' for x in pending) else args.timeout, check=False)
                    failure = 'worker_exit:'+str(process.returncode)
                except subprocess.TimeoutExpired:
                    failure = 'worker_timeout:'+str(args.timeout)
            for a in pending:
                if not cached_result(output, a['key']):
                    atomic_json(output/'cache/results'/(a['key']+'.json'), dict(status='failed', reason=failure))
        for a in entry['appearances']:
            old_record = preserved.get((entry['form'], a['shiny']))
            if old_record is not None and entry['form'] not in refresh_forms:
                records.append(old_record)
                continue
            record = dict(form=entry['form'], name=entry['name'], shiny=a['shiny'])
            if a['status'] != 'mapped':
                record.update(status='unsupported', reason=a['reason'])
            else:
                result = cached_result(output, a['key'])
                record.update(status=result['status'], result=result)
                if result['status'] != 'passed':
                    record['reason'] = result['reason']
            if old_record is not None:
                refresh_results.append(dict(form=entry['form'], name=entry['name'], shiny=a['shiny'],
                                            status=record['status'], reason=record.get('reason'),
                                            changed=record['status'] == 'passed'
                                            and record['result']['files'] != old_record['result']['files']))
                record = recovery_record(old_record, record)
            records.append(record)
        completed += 1
        counts = Counter(r['status'] for r in records)
        report = dict(selected_forms=sorted(selected), completed_forms=completed, records=records,
                      counts=dict(counts), reused_appearances=reused,
                      elapsed_seconds=round(time.monotonic()-started, 2), revision=revision,
                      preserved_appearances=len(preserved)-sum(x['changed'] for x in refresh_results),
                      refreshed_appearances=sum(x['changed'] for x in refresh_results),
                      refresh_results=refresh_results,
                      preserved_from=str(args.preserve_passed) if getattr(args, 'preserve_passed', None) else None)
        atomic_json(output/'report.json', report)
        print(f'[{completed}/{len(selected)}] {entry["name"]}: '
              + ', '.join(r['status'] for r in records[-2:]), flush=True)
    package(output, args.client.resolve(), records)
    exceptions = [dict(form=r['form'], name=r['name'], shiny=r['shiny'], reason=r['reason'])
                  for r in records if r['status'] != 'passed']
    exceptions.extend(dict(form=x['form'], name=x['name'], shiny=x['shiny'], reason=x['reason'],
                           correction=True, disposition='retained_previous_validated_export')
                      for x in refresh_results if x['status'] != 'passed')
    atomic_json(output/'exceptions.json', exceptions)
    print(json.dumps({k: v for k, v in report.items() if k not in ['records', 'selected_forms', 'revision']}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['inventory', 'run', 'worker'])
    parser.add_argument('--pixelmon', type=Path, default=DEFAULT_SOURCE)
    parser.add_argument('--client', type=Path, default=DEFAULT_CLIENT)
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument('--job', type=Path)
    parser.add_argument('--all', action='store_true', help='Process the full catalog instead of the 50-form sample')
    parser.add_argument('--forms', help='Explicit comma-separated form IDs')
    parser.add_argument('--preserve-passed', type=Path, help='Keep checksum-verified successes from this report')
    parser.add_argument('--refresh-forms', default='', help='Revalidate named corrections; keep prior if unsuccessful')
    parser.add_argument('--retry-failed', action='store_true')
    parser.add_argument('--timeout', type=int, default=240, help='Maximum seconds per form worker')
    args = parser.parse_args()
    if args.command == 'worker':
        worker(args.job)
    else:
        run(args)
