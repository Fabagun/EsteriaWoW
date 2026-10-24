"""Install/remove only the files owned by the reversible four-Pokemon test layer."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

from convert import MODULE, LAYER, PILOT
from validate import validate


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def targets(output, client, server_data):
    manifest = json.loads((output/'manifest.json').read_text())
    expected = set()
    for _, dex, name in PILOT:
        stem = f'{dex:04}_{name.title()}'
        for suffix in ['', '_shiny']:
            for extension in ['.m2', '00.skin', '.blp']:
                expected.add(f'client/Creature/Battlemon3D/{stem}{suffix}{extension}')
    for table in ['CreatureModelData', 'CreatureDisplayInfo']:
        expected.add('client/DBFilesClient/'+table+LAYER)
        expected.add('server/dbc-continuations/'+table+LAYER)
    if set(manifest['files']) != expected:
        raise ValueError('Manifest does not describe exactly the four-species pilot')
    roots = {'client': (client/'Data/patch-z.mpq').resolve(), 'server': server_data.resolve()}
    result = []
    for relative in sorted(expected):
        side, rest = relative.split('/', 1)
        destination = (roots[side]/rest).resolve()
        if not destination.is_relative_to(roots[side]):
            raise ValueError('Destination escapes deployment root')
        result.append((relative, output/relative, destination, manifest['files'][relative]))
    return result


def install(output, client, server_data, remove=False):
    output, client, server_data = output.resolve(), client.resolve(), server_data.resolve()
    if not (client/'Wow.exe').is_file() or not (client/'Data/patch-z.mpq').is_dir():
        raise ValueError('Expected existing WXL client and loose patch-z.mpq directory')
    if not (server_data/'dbc-continuations').is_dir():
        raise ValueError('Expected existing server data/dbc-continuations directory')
    files = targets(output, client, server_data)
    receipt_file = output/'installed.json'
    receipt = json.loads(receipt_file.read_text()) if receipt_file.exists() else {}
    if receipt and (receipt['client'] != str(client) or receipt['server_data'] != str(server_data)):
        raise ValueError('Receipt belongs to a different installation')
    owned = receipt.get('files', {})
    if remove and not receipt:
        raise ValueError('No installation receipt; refusing to delete unowned files')
    if not remove:
        validate(output)
    # Preflight every destination before making any changes.
    for relative, source, destination, wanted in files:
        if destination.exists():
            actual = digest(destination)
            if actual != owned.get(relative) and (remove or actual != wanted):
                raise ValueError(f'File was changed externally; refusing to overwrite/delete: {destination}')
    if remove:
        for _, _, destination, _ in files:
            if destination.is_file():
                destination.unlink()  # Exact allow-listed files only; never recursive deletion.
        receipt_file.unlink()
        print('Removed 3D test assets and eDBC layer. Restart client/server to restore sprite rows.')
    else:
        receipt = dict(client=str(client), server_data=str(server_data), files={})
        for relative, source, destination, wanted in files:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
            if digest(destination) != wanted:
                raise ValueError(f'Deployment checksum mismatch: {destination}')
            receipt['files'][relative] = wanted
        receipt_file.write_text(json.dumps(receipt, indent=2)+'\n', encoding='utf8')
        print(f'Installed and hash-verified {len(files)} files. Restart client/server to load tier 9.')
    return files


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['install', 'remove'])
    parser.add_argument('--output', type=Path, default=MODULE/'generated/pixelmon-3d')
    parser.add_argument('--client', type=Path, required=True)
    parser.add_argument('--server-data', type=Path, required=True)
    args = parser.parse_args()
    install(args.output, args.client, args.server_data, args.action == 'remove')
