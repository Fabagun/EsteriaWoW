"""Deploy 3D replacements at original sprite paths; never create or edit DBC records."""
import argparse
import json
from pathlib import Path, PureWindowsPath
import shutil
import struct

from batch import DEFAULT_CLIENT, DEFAULT_OUTPUT, atomic_json, digest
from convert import Dbc, MODULE


PREFIX = 'Creature/Battlemon/'
TABLES = ['CreatureModelData', 'CreatureDisplayInfo']
LAYERS = ['.dbc9-battlemon-3d', '.dbc9-battlemon-3d-batch']


def destination(client, relative):
    parts = relative.split('/')
    if (len(parts) != 3 or '/'.join(parts[:2]) != 'Creature/Battlemon'
            or not parts[2] or any(c in parts[2] for c in ':\\')
            or Path(parts[2]).suffix not in {'.m2', '.skin', '.blp'}):
        raise ValueError('Invalid original-namespace path: ' + relative)
    root = (client/'Data/patch-z.mpq').resolve()
    result = (root/relative).resolve()
    if not result.is_relative_to(root/'Creature/Battlemon'):
        raise ValueError('Destination escapes Battlemon namespace')
    return result


def original_stem(path):
    parts = PureWindowsPath(path).parts
    if (len(parts) != 3 or tuple(p.lower() for p in parts[:2]) != ('creature', 'battlemon')
            or PureWindowsPath(parts[2]).suffix.lower() not in {'.mdx', '.m2'}):
        raise ValueError('Unexpected original model path: ' + path)
    stem = PureWindowsPath(parts[2]).stem
    stem.encode('ascii')
    return stem


def relink_model(data, stem):
    """Append strings and change only their descriptors; no geometry/track offsets move."""
    if data[:8] != b'MD20' + struct.pack('<I', 264):
        raise ValueError('Expected WotLK M2')
    count, table = struct.unpack_from('<II', data, 0x50)
    if count != 1 or table < 304 or table+16 > len(data):
        raise ValueError('Expected one valid embedded texture record')
    texture_type = struct.unpack_from('<I', data, table)[0]
    if texture_type != 0:
        raise ValueError('Replaceable texture requires separate handling')
    result = bytearray(data)
    name = stem.encode('ascii')+b'\0'
    texture = (PREFIX+stem+'.blp').replace('/', '\\').encode('ascii')+b'\0'
    struct.pack_into('<II', result, 8, len(name), len(result))
    result.extend(name)
    struct.pack_into('<II', result, table+8, len(texture), len(result))
    result.extend(texture)
    return bytes(result)


def build(output, client, report_path=None):
    report_path = Path(report_path) if report_path else output/'report.json'
    report = json.loads(report_path.read_text(encoding='utf8'))
    records = [r for r in report['records'] if r['status'] == 'passed']
    if not records:
        raise ValueError('No validated appearances')
    dbc_dir = client/'Data/patch-z.mpq/DBFilesClient'
    paths = {name: dbc_dir/(name+'.dbc1-battlemon') for name in TABLES}
    models, displays = (Dbc(paths[name]) for name in TABLES)
    package = output/'direct-package'
    files, entries, used, sources = {}, [], set(), {}
    if not (client/'Data/patch-W.mpq'/PREFIX).is_dir():
        raise ValueError('Original sprite directory is missing')
    for r in records:
        display = displays.rows[(60000 if r['shiny'] else 50000)+r['form']]
        model = models.rows[display[1]]
        stem = original_stem(models.string(model[2]))
        if stem.lower() in used:
            raise ValueError('Duplicate original model filename: '+stem)
        used.add(stem.lower())
        if model[1] != 0 or model[4] != 1065353216 or display[4] != 1065353216:
            raise ValueError('Original flags/scales require explicit review: '+stem)
        if any(display[i] for i in [6, 7, 8, 9]):
            raise ValueError('Original display has replaceable textures: '+stem)
        result = r['result']
        for ext in ['.m2', '00.skin', '.blp']:
            filename = result['asset']+ext
            source = (output/'cache/assets'/filename).resolve()
            if not source.is_relative_to((output/'cache/assets').resolve()):
                raise ValueError('Source cache path escape')
            if digest(source) != result['files'][filename]:
                raise ValueError('Source checksum mismatch: '+filename)
            original = client/'Data/patch-W.mpq'/PREFIX/(stem+ext)
            relative = PREFIX+stem+ext
            destination(client, relative)
            target = package/relative
            target.parent.mkdir(parents=True, exist_ok=True)
            data = source.read_bytes()
            target.write_bytes(relink_model(data, stem) if ext == '.m2' else data)
            files[relative] = digest(target)
            sources[relative] = dict(path=str(source), sha256=result['files'][filename],
                                     original=str(original), original_sha256=digest(original) if original.exists() else None)
        entries.append(dict(form=r['form'], name=r['name'], shiny=r['shiny'], stem=stem,
                            source_motion=result.get('source_motion', 'animated'),
                            motion_proof=result.get('motion_proof'), shell_review=result.get('shell_review'),
                            geometry_review=result.get('geometry_review'), glb_review=result.get('glb_review'),
                            skeleton_policy=result.get('skeleton_policy','baked'),
                            texture_policy=result.get('texture_policy','solid_alpha_key'),
                            alpha_source=result.get('alpha_source'),
                            alpha_source_sha256=result.get('alpha_source_sha256')))
    manifest = dict(schema=1, deployment='original-path-overrides', appearances=entries, files=files,
                    sources=sources, base_dbcs={str(p.resolve()): digest(p) for p in paths.values()},
                    report=str(report_path.resolve()), report_sha256=digest(report_path))
    atomic_json(package/'manifest.json', manifest)
    validate(output, client)
    return manifest


def validate(output, client, deep=False):
    package = output/'direct-package'
    m = json.loads((package/'manifest.json').read_text())
    if m.get('schema') != 1 or m.get('deployment') != 'original-path-overrides':
        raise ValueError('Unknown direct package format')
    expected = {PREFIX+e['stem']+ext for e in m['appearances'] for ext in ['.m2', '00.skin', '.blp']}
    if len(expected) != 3*len(m['appearances']) or set(m['files']) != expected or set(m['sources']) != expected:
        raise ValueError('Unexpected direct package file set')
    expected_dbcs = {str((client/'Data/patch-z.mpq/DBFilesClient'/(n+'.dbc1-battlemon')).resolve())
                     for n in TABLES}
    if set(m['base_dbcs']) != expected_dbcs:
        raise ValueError('Unexpected base DBC evidence')
    for path, wanted in m['base_dbcs'].items():
        if digest(Path(path)) != wanted:
            raise ValueError('Original DBC changed')
    for relative, wanted in m['files'].items():
        destination(client, relative)
        target = package/relative
        if digest(target) != wanted:
            raise ValueError('Direct package checksum mismatch')
        evidence = m['sources'][relative]
        source = Path(evidence['path']).resolve()
        original = (client/'Data/patch-W.mpq'/relative).resolve()
        if (not source.is_relative_to((output/'cache/assets').resolve())
                or Path(evidence['original']).resolve() != original):
            raise ValueError('Source provenance path mismatch')
        original_hash = digest(original) if original.exists() else None
        if (digest(source) != evidence['sha256']
                or original_hash != evidence['original_sha256']):
            raise ValueError('Source or original sprite changed')
        expected_data = source.read_bytes()
        if relative.endswith('.m2'):
            expected_data = relink_model(expected_data, Path(relative).stem)
        if target.read_bytes() != expected_data:
            raise ValueError('Unexpected change beyond model/texture string descriptors')
    from validation_cache import check_policy, validate_asset
    for e in m['appearances']:
        check_policy(e)
    if deep:
        reused = 0
        for e in m['appearances']:
            reused += validate_asset(package/PREFIX/(e['stem']+'.m2'),e,
                                     (PREFIX+e['stem']+'.blp').replace('/', '\\'),
                                     output/'cache/deep-validation')
        print(f"Canonical deep checks: {len(m['appearances'])-reused} validated, {reused} reused", flush=True)
    return m


def retirement_plan(output, client, server_data):
    """Only exact receipt-owned test layers/assets; no directory deletion or base DBC changes."""
    plan = []
    for receipt_path in [output/'installed-batch.json', output.parent/'pixelmon-3d/installed.json']:
        if not receipt_path.exists():
            continue
        receipt = json.loads(receipt_path.read_text())
        if receipt['client'] != str(client.resolve()) or receipt['server_data'] != str(server_data.resolve()):
            raise ValueError('Legacy receipt belongs to another installation')
        for relative, hashes in receipt['files'].items():
            side, rest = relative.split('/', 1)
            owned_layer = rest in {folder+'/'+name+layer for folder in ['DBFilesClient', 'dbc-continuations']
                                  for name in TABLES for layer in LAYERS}
            owned_batch_asset = side == 'client' and rest.startswith('Creature/Battlemon3DBatch/')
            if not (owned_layer or owned_batch_asset):
                continue
            root = (client/'Data/patch-z.mpq' if side == 'client' else server_data).resolve()
            target = (root/rest).resolve()
            if not target.is_relative_to(root):
                raise ValueError('Legacy target escapes root')
            if not target.exists():
                continue
            actual = digest(target)
            if actual not in (hashes if isinstance(hashes, list) else [hashes]):
                raise ValueError('Externally changed legacy file: '+str(target))
            backup = output/'legacy-backup'/actual/target.name
            plan.append(dict(path=str(target), backup=str(backup.resolve()), sha256=actual))
    owned = {x['path'].lower() for x in plan}
    for root, folder in [(client/'Data/patch-z.mpq', 'DBFilesClient'), (server_data, 'dbc-continuations')]:
        for name in TABLES:
            for layer in LAYERS:
                p = (root/folder/(name+layer)).resolve()
                if p.exists() and str(p).lower() not in owned:
                    raise ValueError('Experimental DBC layer lacks matching ownership receipt: '+str(p))
    return plan


def install(output, client, server_data, remove=False):
    output, client, server_data = output.resolve(), client.resolve(), server_data.resolve()
    receipt_path = output/'installed-direct.json'
    receipt = json.loads(receipt_path.read_text()) if receipt_path.exists() else {}
    if receipt and (receipt['client'] != str(client) or receipt['server_data'] != str(server_data)):
        raise ValueError('Direct receipt belongs to another installation')
    if not (client/'Wow.exe').is_file() or not (server_data/'dbc-continuations').is_dir():
        raise ValueError('Expected existing client and repository server data')
    for item in receipt.get('retired', []):
        if not Path(item['path']).exists() and digest(Path(item['backup'])) != item['sha256']:
            raise ValueError('Retired file backup missing or changed')
    owned = receipt.get('files', {})
    if remove and not receipt:
        raise ValueError('No direct-install receipt')
    m = None if remove else validate(output, client)
    incoming = {} if remove else m['files']
    from blp_compression import require_compressed
    for relative,wanted in incoming.items():
        if relative.lower().endswith('.blp') and wanted not in owned.get(relative,[]):
            require_compressed(output/'direct-package'/relative)
    journal = {r: list(h) for r, h in owned.items()}
    for relative, wanted in incoming.items():
        journal[relative] = list(dict.fromkeys(journal.get(relative, [])+[wanted]))
    for relative in journal:
        p = destination(client, relative)
        if p.exists() and (relative not in owned or digest(p) not in owned[relative]):
            raise ValueError('Unowned or externally modified canonical file: '+str(p))
    if remove:
        for relative in owned:
            p = destination(client, relative)
            if p.exists():
                p.unlink()
        receipt['files'] = {}
        receipt['active'] = False
        atomic_json(receipt_path, receipt)
        print('Removed direct 3D overrides; original sprites and DBCs remain. Legacy archives retained.')
        return
    plan = retirement_plan(output, client, server_data)
    # Persist intent before the first copy: interrupted copies/retirements can resume safely.
    retired = {x['path']: x for x in receipt.get('retired', [])}
    retired.update({x['path']: x for x in plan})
    receipt = dict(client=str(client), server_data=str(server_data), active=True,
                   files=journal, retired=list(retired.values()), appearances=m['appearances'])
    atomic_json(receipt_path, receipt)
    for relative, wanted in incoming.items():
        target = destination(client, relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        temp = target.with_name(target.name+'.direct-install.tmp')
        shutil.copyfile(output/'direct-package'/relative, temp)
        if digest(temp) != wanted:
            raise ValueError('Direct copy verification failed')
        temp.replace(target)
        receipt['files'][relative] = [wanted]
    atomic_json(receipt_path, receipt)
    for item in plan:
        path, backup = Path(item['path']), Path(item['backup'])
        backup.parent.mkdir(parents=True, exist_ok=True)
        if not backup.exists():
            shutil.copyfile(path, backup)
        if digest(backup) != item['sha256'] or digest(path) != item['sha256']:
            raise ValueError('Legacy archive verification failed')
        path.unlink()
    for relative, wanted in incoming.items():
        if digest(destination(client, relative)) != wanted:
            raise ValueError('Installed canonical checksum mismatch')
    print(f"Installed {len(m['appearances'])} appearances / {len(incoming)} files at original sprite paths. "
          f"Archived {len(plan)} receipt-owned experimental files; no DBC records edited.")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['build', 'validate', 'install', 'remove'])
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument('--client', type=Path, default=DEFAULT_CLIENT)
    parser.add_argument('--server-data', type=Path, default=MODULE.parents[1]/'env/dist/bin/data')
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    if args.action in {'build', 'install'}:
        state_path = args.output/'full-run.json'
        if state_path.exists() and not args.report:
            state = json.loads(state_path.read_text())
            if state['status'] not in {'ready', 'finalized'}:
                raise ValueError('Wait for the full run validation before repackaging its report')
        build(args.output, args.client, args.report)
    if args.action == 'validate':
        manifest = validate(args.output, args.client, deep=True)
        print('Deep-validated', len(manifest['appearances']), 'direct overrides')
    elif args.action in {'install', 'remove'}:
        install(args.output, args.client, args.server_data, args.action == 'remove')
