"""Validate and reversibly install only the dedicated batch namespace and continuation layer."""
import argparse
import json
from pathlib import Path
import re
import shutil

from batch import ASSETS, DEFAULT_CLIENT, DEFAULT_OUTPUT, LAYER, atomic_json, digest
from convert import Dbc, MODULE
from texture import filtered_edge_alpha
from validate import read_model

TABLES = ['CreatureModelData', 'CreatureDisplayInfo']


def allowed(relative):
    dbcs = {side + '/' + folder + '/' + table + LAYER
            for side, folder in [('client', 'DBFilesClient'), ('server', 'dbc-continuations')]
            for table in TABLES}
    return relative in dbcs or bool(re.fullmatch(
        r'client/' + ASSETS + r'/a_[0-9a-f]{20}(?:\.m2|00\.skin|\.blp)', relative))


def target(relative, client, server_data):
    if not allowed(relative):
        raise ValueError('File outside batch namespace: ' + relative)
    side, rest = relative.split('/', 1)
    root = (client/'Data/patch-z.mpq' if side == 'client' else server_data).resolve()
    destination = (root/rest).resolve()
    if not destination.is_relative_to(root):
        raise ValueError('Destination escapes deployment root')
    return destination


def validate_package(package, deep=False):
    package = package.resolve()
    manifest = json.loads((package/'manifest.json').read_text())
    if manifest.get('schema') != 1 or manifest.get('layer') != LAYER:
        raise ValueError('Unexpected batch manifest')
    appearances = manifest['appearances']
    if not appearances:
        raise ValueError('Empty batch')
    expected = {side + '/' + folder + '/' + table + LAYER
                for side, folder in [('client', 'DBFilesClient'), ('server', 'dbc-continuations')]
                for table in TABLES}
    for entry in appearances:
        for extension in ['.m2', '00.skin', '.blp']:
            expected.add('client/' + ASSETS + '/' + entry['asset'] + extension)
    if set(manifest['files']) != expected:
        raise ValueError('Manifest file set does not match its appearances')
    for relative, wanted in manifest['files'].items():
        if not allowed(relative):
            raise ValueError('Invalid package path: ' + relative)
        path = (package/relative).resolve()
        if not path.is_relative_to(package) or not path.is_file() or digest(path) != wanted:
            raise ValueError('Package checksum/path mismatch: ' + relative)
    tables = {}
    for name in TABLES:
        client_path = package/'client/DBFilesClient'/(name+LAYER)
        server_path = package/'server/dbc-continuations'/(name+LAYER)
        if digest(client_path) != digest(server_path):
            raise ValueError('Client/server continuation mismatch')
        tables[name] = Dbc(client_path)
    models, displays = (tables[name] for name in TABLES)
    if (models.fields, displays.fields) != (28, 16):
        raise ValueError('Unexpected DBC layout')
    for table, key in [(models, 'model'), (displays, 'display')]:
        ids = [entry[key] for entry in appearances]
        if len(set(ids)) != len(ids) or set(table.rows) != set(ids):
            raise ValueError('Duplicate or unexpected DBC rows')
    for entry in appearances:
        display = displays.rows[entry['display']]
        model = models.rows[entry['model']]
        expected_id = (60000 if entry['shiny'] else 50000) + entry['form']
        model_path = (ASSETS+'/'+entry['asset']+'.mdx').replace('/', '\\')
        if entry['display'] != expected_id or display[1] != entry['model'] or models.string(model[2]) != model_path:
            raise ValueError('Appearance/DBC mapping mismatch')
        if any(display[i] != 0 for i in [6, 7, 8, 9]):
            raise ValueError('Unexpected replaceable texture fields')
    motion_by_asset = {}
    for entry in appearances:
        policy = entry.get('source_motion', 'animated')
        if policy not in {'animated', 'static_bind_pose', 'source_constant_walk'}:
            raise ValueError('Unknown source motion policy')
        if motion_by_asset.setdefault(entry['asset'], policy) != policy:
            raise ValueError('Conflicting source motion policies for one asset')
        if policy == 'source_constant_walk' and 'source_walk_channels_constant' not in entry.get('notes', []):
            raise ValueError('Missing source constant-walk annotation')
        if policy == 'static_bind_pose' and 'source_has_no_animations_static_bind_pose' not in entry.get('notes', []):
            raise ValueError('Missing explicit static source annotation')
    from validation_cache import check_policy, validate_asset
    entries_by_asset = {}
    for e in appearances:
        check_policy(e)
        signature = tuple(e.get(k) for k in ['source_motion', 'motion_proof', 'shell_review',
                                                       'geometry_review', 'glb_review', 'skeleton_policy',
                                               'texture_policy', 'alpha_source_sha256'])
        if e['asset'] in entries_by_asset:
            old = entries_by_asset[e['asset']]
            if signature != tuple(old.get(k) for k in ['source_motion', 'motion_proof', 'shell_review',
                                                       'geometry_review', 'glb_review', 'skeleton_policy',
                                               'texture_policy', 'alpha_source_sha256']):
                raise ValueError('Conflicting validation policies for one asset')
        entries_by_asset[e['asset']] = e
    if deep:
        reused = 0
        for asset, entry in sorted(entries_by_asset.items()):
            path = package/'client'/ASSETS/(asset+'.m2')
            expected_texture = (ASSETS+'/'+asset+'.blp').replace('/', '\\')
            reused += validate_asset(path,entry,expected_texture,package.parent/'cache/deep-validation')
        print(f'Deep checks: {len(entries_by_asset)-reused} validated, {reused} unchanged receipts reused', flush=True)
    return manifest


def deploy(output, client, server_data, remove=False):
    output, client, server_data = output.resolve(), client.resolve(), server_data.resolve()
    if not (client/'Wow.exe').is_file() or not (client/'Data/patch-z.mpq').is_dir():
        raise ValueError('Expected existing WXL client and loose patch-z.mpq directory')
    if not (server_data/'dbc-continuations').is_dir():
        raise ValueError('Expected existing server data/dbc-continuations directory')
    receipt_path = output/'installed-batch.json'
    receipt = json.loads(receipt_path.read_text()) if receipt_path.exists() else {}
    if receipt and (receipt['client'] != str(client) or receipt['server_data'] != str(server_data)):
        raise ValueError('Receipt belongs to a different installation')
    owned = receipt.get('files', {})
    if remove and not receipt:
        raise ValueError('No installation receipt; refusing to delete unowned files')
    manifest = None if remove else validate_package(output/'package')
    incoming = {} if remove else manifest['files']
    # A journal records both old and desired hashes before any copies. Interrupted installs can resume or undo.
    journal = {relative: list(hashes) for relative, hashes in owned.items()}
    for relative, wanted in incoming.items():
        journal[relative] = list(dict.fromkeys(journal.get(relative, []) + [wanted]))
    for relative in journal:
        destination = target(relative, client, server_data)
        if destination.exists() and (relative not in owned or digest(destination) not in owned[relative]):
            raise ValueError('Unowned or externally changed file: ' + str(destination))
    if remove:
        for relative in owned:
            destination = target(relative, client, server_data)
            if destination.is_file():
                destination.unlink()
        receipt_path.unlink()
        print('Removed the batch layer and its owned assets; pilot and original sprites remain.')
        return
    receipt = dict(client=str(client), server_data=str(server_data), files=journal)
    atomic_json(receipt_path, receipt)
    for relative, wanted in incoming.items():
        destination = target(relative, client, server_data)
        destination.parent.mkdir(parents=True, exist_ok=True)
        # Atomic replacement avoids leaving a partial file if the process is interrupted.
        temporary = destination.with_name(destination.name+'.batch-install.tmp')
        shutil.copyfile(output/'package'/relative, temporary)
        if digest(temporary) != wanted:
            raise ValueError('Deployment checksum mismatch: ' + relative)
        temporary.replace(destination)
        receipt['files'][relative] = [wanted]
    atomic_json(receipt_path, receipt)
    print(f"Installed {len(incoming)} verified files / {len(manifest['appearances'])} appearances. "
          'Restart client and deploy/restart the remote server to load the continuation layer.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['validate', 'install', 'remove'])
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument('--client', type=Path, default=DEFAULT_CLIENT)
    parser.add_argument('--server-data', type=Path, default=MODULE.parents[1]/'env/dist/bin/data')
    args = parser.parse_args()
    if args.action == 'validate':
        result = validate_package(args.output/'package', deep=True)
        print(f"Validated {len(result['appearances'])} appearances, all mip seams, and paired eDBC files.")
    else:
        deploy(args.output, args.client, args.server_data, remove=args.action == 'remove')
