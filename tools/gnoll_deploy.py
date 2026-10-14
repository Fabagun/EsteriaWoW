"""Back up and install a checked Horde creature-race package; never recreate Docker services here."""

import argparse
from datetime import datetime
import hashlib
import os
from pathlib import Path
import shutil
import subprocess

import gnoll_race_pack as pack
import mechagnome_race_pack as db
import sethrak_race_pack as base
from test_gnoll_race_pack import check

NATIVE = Path('C:/g63-build/EsteriaAppearance.dll')
TABLES = {**pack.c.WORLD_TABLES, 'chrraces_dbc': 'ID'}
APPEARANCE = ('SELECT guid,race,gender,skin,face,hairStyle,hairColor,facialStyle,extraAppearance '
              'FROM characters ORDER BY guid;')


def files():
    report = pack.p.load_json(pack.STAGE / 'report.json')
    result = {str(relative): pack.STAGE / 'client' / relative for relative in report['archives']}
    result.update({name: pack.STAGE / name for name in
                   ('EsteriaAppearance.bin', 'EsteriaAppearanceGeometry.bin',
                    'Esteria' + pack.manifest()['name'] + '.bin',
                    'Esteria' + pack.manifest()['name'] + 'Textures.bin')})
    result['EsteriaAppearance.dll'] = NATIVE
    return result


def fingerprint():
    return {table: hashlib.sha256(db.sql(f'SELECT * FROM `{table}` WHERE `{field}` <> {pack.RACE} '
                                         'ORDER BY 1,2,3;').encode()).hexdigest()
            for table, field in TABLES.items()}


def preflight():
    report = pack.p.load_json(pack.STAGE / 'report.json')
    processes = subprocess.check_output(['tasklist', '/FO', 'CSV', '/NH'], text=True).lower()
    if any(name in processes for name in ('wow.exe', 'eclipse.exe', 'mpqeditor.exe')):
        raise RuntimeError('Close WoW/Eclipse/MPQEditor before the coordinated install')
    if pack.p.sha256(pack.p.CLIENT_DEFAULT / 'Wow.exe') != report['exe_sha256']:
        raise ValueError('Client executable differs from the verified stage')
    for relative, expected in report['archive_baselines'].items():
        if pack.p.sha256(pack.p.CLIENT_DEFAULT / relative) != expected:
            raise ValueError('Archive merge base changed: ' + relative)
    for name in ('EsteriaAppearance.bin', 'EsteriaAppearanceGeometry.bin'):
        if pack.p.sha256(pack.p.CLIENT_DEFAULT / name) != pack.p.sha256(pack.STAGE / 'baseline' / name):
            raise ValueError('Native catalog merge base changed: ' + name)
    for name in base.SERVER_TABLES:
        if pack.p.sha256(pack.p.SERVER_DBC_ROOT / (name + '.dbc')) != \
                pack.p.sha256(pack.STAGE / 'baseline-server' / (name + '.dbc')):
            raise ValueError('Server DBC merge base changed: ' + name)
    for table, field in TABLES.items():
        if db.sql(f'SELECT COUNT(*) FROM `{table}` WHERE `{field}`={pack.RACE};').strip() != '0':
            raise ValueError('Target race already has world rows: ' + table)
    if db.sql(f'SELECT COUNT(*) FROM characters WHERE race={pack.RACE};', 'acore_characters').strip() != '0':
        raise ValueError('Target characters require a migration policy')
    model = pack.manifest()['models']['male']
    for table, identifier in (('creaturedisplayinfo_dbc', model['display_id']),
                              ('creaturemodeldata_dbc', model['model_id'])):
        if db.sql(f'SELECT COUNT(*) FROM `{table}` WHERE `ID`={identifier};').strip() != '0':
            raise ValueError('Target model/display has a database override: ' + table)
    migration = Path(report['migration'])
    if db.sql(f"SELECT COUNT(*) FROM updates WHERE name='{migration.name}';").strip() != '0':
        raise ValueError('Dedicated migration already has a receipt')
    family = 'Esteria' + pack.manifest()['name']
    for name in (str(pack.ASSET_ARCHIVE), family + '.bin', family + 'Textures.bin'):
        if (pack.p.CLIENT_DEFAULT / name).exists():
            raise ValueError('New race file already exists: ' + name)
    build = pack.p.load_json(pack.STAGE / 'native-checks.json')
    if not build['all_passed'] or pack.p.sha256(NATIVE) != build['dll_sha256']:
        raise ValueError('Native DLL is not the tested build')
    for name, expected in build['source_files'].items():
        if pack.p.sha256(pack.p.ROOT / name) != expected:
            raise ValueError('Native/server source changed after the checked build: ' + name)
    for name, expected in build.get('catalog_hashes', {}).items():
        staged = pack.STAGE / name
        source = staged if staged.exists() else pack.p.CLIENT_DEFAULT / name
        if pack.p.sha256(source) != expected:
            raise ValueError('Native test catalog differs from deployment: ' + name)


def backup():
    check()
    preflight()
    root = Path('C:/Users/Zach/.codex/backups') / (
        pack.manifest()['slug'] + '-' + datetime.now().strftime('%Y%m%d-%H%M%S'))
    root.mkdir(parents=True)
    report = {'backup': str(root), 'files': {name: str(path) for name, path in files().items()},
              'before': {}, 'install_hashes': {}, 'server_before': {}, 'server_after': {},
              'world_fingerprints': fingerprint(),
              'prior_worldserver': pack.p.load_json(pack.STAGE / 'prior-worldserver.json')}
    for name, source in files().items():
        live = pack.p.CLIENT_DEFAULT / name
        report['before'][name] = pack.p.sha256(live) if live.exists() else None
        report['install_hashes'][name] = pack.p.sha256(source)
        if live.exists():
            target = root / 'client' / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(live, target)
            assert pack.p.sha256(target) == report['before'][name]
    for name in base.SERVER_TABLES:
        live = pack.p.SERVER_DBC_ROOT / (name + '.dbc')
        target = root / 'server-dbc' / live.name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(live, target)
        report['server_before'][name] = pack.p.sha256(live)
        report['server_after'][name] = pack.p.sha256(pack.STAGE / 'server/dbc' / live.name)
        assert pack.p.sha256(target) == report['server_before'][name]
    migration = Path(pack.p.load_json(pack.STAGE / 'report.json')['migration'])
    report['migration'] = str(migration)
    report['migration_sha256'] = pack.p.sha256(migration)
    shutil.copy2(migration, root / migration.name)
    rollback = '\n'.join(f'DELETE FROM `{table}` WHERE `{field}`={pack.RACE};' for table, field in TABLES.items())
    rollback += f"\nDELETE FROM `updates` WHERE `name`='{migration.name}';\n"
    (root / 'rollback-world.sql').write_text(rollback, encoding='utf-8', newline='\n')
    before = db.sql(APPEARANCE, 'acore_characters')
    (root / 'characters-appearance.tsv').write_text(before, encoding='utf-8', newline='\n')
    report['backup_checksums'] = {str(path.relative_to(root)): pack.p.sha256(path)
                                for path in root.rglob('*') if path.is_file()}
    pack.save(root / 'install-plan.json', report)
    pack.save(pack.STAGE / 'install-plan.json', report)
    print('HASH-VERIFIED', pack.manifest()['name'], 'BACKUP', root, flush=True)


def install():
    preflight()
    if subprocess.check_output(['docker', 'inspect', 'ac-worldserver', '--format',
                                '{{.State.Running}}'], text=True).strip() != 'false':
        raise ValueError('Stop only ac-worldserver before coordinated installation')
    report = pack.p.load_json(pack.STAGE / 'install-plan.json')
    root = Path(report['backup'])
    for name, expected in report['backup_checksums'].items():
        if pack.p.sha256(root / name) != expected:
            raise ValueError('Verified rollback backup changed: ' + name)
    for name, expected in report['before'].items():
        live = pack.p.CLIENT_DEFAULT / name
        if (pack.p.sha256(live) if live.exists() else None) != expected:
            raise ValueError('Client file changed since backup: ' + name)
        if pack.p.sha256(Path(report['files'][name])) != report['install_hashes'][name]:
            raise ValueError('Staged file changed since backup: ' + name)
    for name, expected in report['server_before'].items():
        if pack.p.sha256(pack.p.SERVER_DBC_ROOT / (name + '.dbc')) != expected:
            raise ValueError('Server DBC changed since backup: ' + name)
    if fingerprint() != report['world_fingerprints']:
        raise ValueError('Unrelated startup data changed since backup')
    migration = Path(report['migration'])
    if pack.p.sha256(migration) != report['migration_sha256']:
        raise ValueError('Migration changed since backup')
    characters = db.sql(APPEARANCE, 'acore_characters')
    (root / 'characters-at-install.tsv').write_text(characters, encoding='utf-8', newline='\n')
    receipt = hashlib.sha1(migration.read_bytes()).hexdigest().upper()
    try:
        db.sql('START TRANSACTION;\n' + migration.read_text() +
               f"\nINSERT INTO updates (name,hash,state) VALUES ('{migration.name}','{receipt}','PENDING');\nCOMMIT;")
        for name, source in report['files'].items():
            target = pack.p.CLIENT_DEFAULT / name
            temporary = target.with_suffix(target.suffix + '.race-next')
            shutil.copy2(source, temporary)
            assert pack.p.sha256(temporary) == report['install_hashes'][name]
            os.replace(temporary, target)
            print('INSTALLED', name, flush=True)
        for name in base.SERVER_TABLES:
            source = pack.STAGE / 'server/dbc' / (name + '.dbc')
            target = pack.p.SERVER_DBC_ROOT / source.name
            shutil.copy2(source, target)
            assert pack.p.sha256(target) == report['server_after'][name]
        assert fingerprint() == report['world_fingerprints']
        assert db.sql(APPEARANCE, 'acore_characters') == characters
    except Exception:
        for name, expected in report['before'].items():
            target = pack.p.CLIENT_DEFAULT / name
            if expected is not None:
                shutil.copy2(root / 'client' / name, target)
            elif target.exists():
                assert pack.p.CLIENT_DEFAULT.resolve() in target.resolve().parents
                target.unlink()
        for name in base.SERVER_TABLES:
            shutil.copy2(root / 'server-dbc' / (name + '.dbc'), pack.p.SERVER_DBC_ROOT / (name + '.dbc'))
        db.sql('START TRANSACTION;\n' + (root / 'rollback-world.sql').read_text() + '\nCOMMIT;')
        raise
    report.update(status='installed_awaiting_worldserver_recreation', receipt=receipt,
                  installed_hashes={name: pack.p.sha256(pack.p.CLIENT_DEFAULT / name) for name in report['files']},
                  character_appearance_sha256=hashlib.sha256(characters.encode()).hexdigest())
    pack.save(root / 'install-report.json', report)
    pack.save(pack.STAGE / 'last-install.json', report)
    print('MATCHED', pack.manifest()['name'], 'PACKAGE INSTALLED', root, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('preflight', 'backup', 'install'))
    parser.add_argument('--race', choices=('gnoll', 'saberon'), default='gnoll')
    args = parser.parse_args()
    if args.race == 'saberon':
        import saberon_race_pack as pack
        from test_saberon_race_pack import check
        NATIVE = Path('C:/s64-build/EsteriaAppearance.dll')
    globals()[args.action]()
