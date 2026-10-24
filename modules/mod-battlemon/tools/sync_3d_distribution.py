"""Synchronize the living 3D package using its owned-file manifest; never touch the 2D snapshot."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil

MODULE = Path(__file__).resolve().parents[1]
RETIRED = {f'server/core-updates/pending_db_{db}/rev_1790798400.sql' for db in ('world', 'characters')}

def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest()

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--package', type=Path, default=Path('C:/data/pokemon-mod/3d-version'))
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    root = args.package.resolve()
    if root.name != '3d-version':
        raise ValueError('Expected the living 3d-version directory')
    manifest_path = root/'manifest.json'
    manifest = json.loads(manifest_path.read_text())
    if manifest['edition'] != '3d':
        raise ValueError('Not a 3D distribution')
    snapshot = root.parent/'2d-version/manifest.json'
    if sha(snapshot) != manifest['2d_snapshot_manifest_sha256']:
        raise ValueError('Frozen 2D manifest changed')
    old = {row['path']: row for row in manifest['files']}
    if len(old) != len(manifest['files']):
        raise ValueError('Duplicate manifest paths')
    def target(name):
        p = (root/name).resolve()
        if not p.is_relative_to(root):
            raise ValueError('Path escapes package: '+name)
        return p
    # Preflight all owned destinations before making any change.
    for name, row in old.items():
        if sha(target(name)) != row['sha256']:
            raise ValueError('Package was edited independently: '+name)
    sources = {name: Path(row['source']) for name, row in old.items() if name not in RETIRED}
    for p in MODULE.rglob('*'):
        rel = p.relative_to(MODULE)
        if any(part in {'generated', '__pycache__', '.git', '.agents', '.codex'} for part in rel.parts):
            continue
        if p.is_file() and p.suffix != '.pyc':
            sources['server/modules/mod-battlemon/'+rel.as_posix()] = p
    trainer = MODULE.parent/'mod-pokemon-trainer'
    if trainer.is_dir():
        for p in trainer.rglob('*'):
            rel = p.relative_to(trainer)
            if any(part in {'generated', '__pycache__', 'validation', '.git', '.agents', '.codex'} for part in rel.parts):
                continue
            if p.is_file() and p.suffix != '.pyc':
                sources['server/modules/mod-pokemon-trainer/'+rel.as_posix()] = p
        update = MODULE.parents[1]/'data/sql/updates/pending_db_world/rev_1790889000.sql'
        sources['server/core-updates/pending_db_world/'+update.name] = update
        addon = old['client/Interface/AddOns/BattlemonBattles/BattlemonBattles.lua']
        trainer_client = Path(addon['source']).parents[3]
        for source in (trainer/'client').rglob('*'):
            if source.is_file():
                rel = source.relative_to(trainer/'client')
                sources['client/Data/patch-z.mpq/'+rel.as_posix()] = trainer_client/'Data/patch-z.mpq'/rel
        for source in (trainer/'data/dbc-continuations').iterdir():
            sources['client/Data/patch-z.mpq/DBFilesClient/'+source.name] = (
                trainer_client/'Data/patch-z.mpq/DBFilesClient'/source.name)
        gym_manifest = trainer/'data/gym-trainers/manifest.json'
        if gym_manifest.exists():
            for relative in json.loads(gym_manifest.read_text(encoding='utf-8'))['files']:
                sources['client/Data/patch-z.mpq/'+relative] = trainer_client/'Data/patch-z.mpq'/relative
        hook = 'Interface/FrameXML/WorldStateFrame.xml'
        sources['client/Data/patch-z.mpq/'+hook] = trainer_client/'Data/patch-z.mpq'/hook

    sources['README.md'] = MODULE/'3D-DEPLOYMENT.md'
    center_placement = MODULE/'data/center/placement.json'
    if center_placement.exists():
        placement = json.loads(center_placement.read_text())
        updates = [placement.get('world_update')] + placement.get('world_followup_updates', [])
        for update in filter(None, updates):
            source = (MODULE.parents[1]/update).resolve()
            pending = (MODULE.parents[1]/'data/sql/updates/pending_db_world').resolve()
            if source.parent != pending or not source.name.startswith('rev_'):
                raise ValueError('Unexpected Center world-update path')
            sources['server/core-updates/pending_db_world/'+source.name] = source
        addon_row = old['client/Interface/AddOns/BattlemonBattles/BattlemonBattles.lua']
        client = Path(addon_row['source']).parents[3]
        for source in (MODULE/'data/center/client').rglob('*'):
            if source.is_file():
                relative = source.relative_to(MODULE/'data/center/client')
                name = 'client/Data/patch-z.mpq/'+relative.as_posix()
                sources[name] = client/'Data/patch-z.mpq'/relative
        layer = 'GameObjectDisplayInfo.dbc9-battlemon-center'
        sources['client/Data/patch-z.mpq/DBFilesClient/'+layer] = client/'Data/patch-z.mpq/DBFilesClient'/layer


    rows, changes = [], []
    for name, source in sorted(sources.items()):
        digest = sha(source)
        row = dict(path=name, source=str(source.resolve()), sha256=digest, bytes=source.stat().st_size)
        rows.append(row)
        if name not in old or old[name]['sha256'] != digest:
            if name not in old and target(name).exists():
                raise ValueError('Unowned destination exists: '+name)
            changes.append(row)
    removed = sorted(RETIRED.intersection(old))
    print(json.dumps(dict(changed=len(changes), removed=removed, files=len(rows)), indent=2), flush=True)
    if not args.apply:
        return
    for row in changes:
        dest = target(row['path'])
        dest.parent.mkdir(parents=True, exist_ok=True)
        temporary = dest.with_name(dest.name+'.sync-tmp')
        if temporary.exists():
            raise ValueError('Unexpected sync temporary: '+str(temporary))
        shutil.copyfile(row['source'], temporary)
        if sha(temporary) != row['sha256']:
            raise ValueError('Source changed during copy')
        temporary.replace(dest)
    for name in removed:
        target(name).unlink()
    for row in rows:
        if sha(target(row['path'])) != row['sha256']:
            raise ValueError('Final package verification failed: '+row['path'])
    manifest.update(files=rows, bytes=sum(r['bytes'] for r in rows),
                    final_sync_utc=datetime.now(timezone.utc).isoformat())
    temporary = manifest_path.with_suffix('.json.sync-tmp')
    temporary.write_text(json.dumps(manifest, indent=2)+'\n', encoding='utf-8')
    temporary.replace(manifest_path)
    print('PASS: living copy synchronized and all file hashes verified; 2D snapshot untouched.')

if __name__ == '__main__':
    main()
