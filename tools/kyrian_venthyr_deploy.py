"""Install the checked native race stage, preserving the prior matched client/server set."""

import argparse
from datetime import datetime, timezone
from pathlib import Path
import shlex
import shutil
import subprocess

import kyrian_venthyr_pack as k


ROOT, STAGE, CLIENT = k.p.ROOT, k.STAGE, k.p.CLIENT_DEFAULT
IMAGE = 'esteria-kyrian-venthyr:20261022'
RECEIPT = STAGE / 'installation.json'
SCOPES = {
    'chrraces_dbc': '`ID` IN (75,76)',
    'creaturemodeldata_dbc': '`ID` BETWEEN 121060 AND 121063',
    'creaturedisplayinfo_dbc': '`ID` BETWEEN 60083 AND 60086',
    'creature_model_info': '`DisplayID` BETWEEN 60083 AND 60086',
    'playercreateinfo': '`race` IN (75,76)', 'player_race_stats': '`Race` IN (75,76)',
    'playercreateinfo_action': '`race` IN (75,76)', 'playercreateinfo_item': '`race` IN (75,76)',
    'player_totem_model': '`RaceID` IN (75,76)',
    'custom_race_start_spell': '`race` IN (75,76)', 'custom_race_start_skill': '`race` IN (75,76)'}


def command(*args, input=None):
    result = subprocess.run(list(args), input=input, capture_output=True, cwd=ROOT)
    if result.returncode:
        raise RuntimeError(result.stderr.decode(errors='replace')[-4000:])
    return result.stdout


def sql(text):
    return command('docker', 'exec', '-i', 'ac-database', 'sh', '-c',
        'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql -uroot --default-character-set=utf8mb4 --batch --skip-column-names',
        input=text.encode()).decode()


def ensure_client_closed():
    prefix = str(CLIENT).replace("'", "''") + '\\*'
    script = ('$ErrorActionPreference="Stop"; Get-CimInstance Win32_Process | Where-Object { $_.ExecutablePath -like '
              "'" + prefix + "' } | Select-Object -ExpandProperty ExecutablePath")
    running = command('powershell', '-NoProfile', '-Command', script).decode().strip()
    if running:
        raise RuntimeError('Close the development client before replacement: ' + running)


def preflight():
    ensure_client_closed()
    if sql('SELECT COUNT(*) FROM acore_characters.characters WHERE online=1;').strip() != '0':
        raise RuntimeError('Realm has online characters; defer the restart')
    report = k.p.load_json(STAGE / 'report.json')
    if not report.get('client_build') or not report.get('server_build'):
        raise RuntimeError('Both matched builds must have passed')
    if k.p.sha256(STAGE / 'client/WowClientRetailBodyShape.exe') != report['client_build']['sha256']:
        raise RuntimeError('Staged client binary changed')
    for relative, expected in report['loose_client_files'].items():
        if k.p.sha256(STAGE / 'client' / relative) != expected:
            raise RuntimeError('Staged loose file changed: ' + relative)
    if not k.p.load_json(STAGE / 'sql-validation.json')['foreign_ownership_rejected']:
        raise RuntimeError('SQL validation is incomplete')
    if k.MIGRATION.read_bytes() != (STAGE / 'migration.dump').read_bytes():
        raise RuntimeError('Migration differs from tested stage')
    for relative, expected in report['archives'].items():
        if k.p.sha256(CLIENT / relative) != expected['before']:
            raise RuntimeError('Client baseline changed: ' + relative)
        if k.p.sha256(STAGE / 'client' / relative) != expected['after']:
            raise RuntimeError('Staged archive changed: ' + relative)
        if not expected.get('compressed_payloads_verified'):
            raise RuntimeError('Compressed archive verification is incomplete: ' + relative)
    for name, expected in report['baseline_server_hashes'].items():
        if k.p.sha256(k.p.SERVER_DBC_ROOT / (name + '.dbc')) != expected:
            raise RuntimeError('Server baseline changed: ' + name)
    built = command('docker', 'image', 'inspect', IMAGE, '--format', '{{.Id}}').decode().strip()
    if built != report['server_build']['image_id']:
        raise RuntimeError('Server image differs from the checked build')
    return report


def rollback():
    receipt = k.p.load_json(RECEIPT)
    ensure_client_closed()
    if sql('SELECT COUNT(*) FROM acore_characters.characters WHERE race IN (75,76);').strip() != '0':
        raise RuntimeError('New-race characters exist; preserve/migrate them before rolling back')
    if receipt['status'] in ('installed-awaiting-runtime-check', 'runtime-checked'):
        for item in receipt['files']:
            if not Path(item['path']).is_file() or k.p.sha256(Path(item['path'])) != item['installed']:
                raise RuntimeError('A later change must be preserved before rollback: ' + item['path'])
    command('docker', 'compose', 'stop', 'ac-worldserver')
    sql((Path(receipt['backup']) / 'world-rows.dump').read_text())
    for item in receipt['files']:
        destination = Path(item['path'])
        if item['existed']:
            shutil.copy2(item['backup'], destination)
            if k.p.sha256(destination) != item['before']:
                raise RuntimeError('Rollback hash mismatch: ' + str(destination))
        elif destination.exists():
            destination.unlink()
    command('docker', 'compose', 'up', '-d', '--no-deps', '--no-build', '--pull', 'never',
            '--force-recreate', 'ac-worldserver')
    receipt['status'] = 'rolled-back'
    k.json_save(RECEIPT, receipt)


def install():
    report = preflight()
    print('PASS install preflight; backing up matched files and scoped world rows', flush=True)
    if RECEIPT.exists():
        raise FileExistsError('Installation receipt already exists; inspect it before retrying')
    backup = STAGE / 'rollback'
    backup.mkdir()
    old_image = command('docker', 'inspect', 'ac-worldserver', '--format', '{{.Image}}').decode().strip()
    receipt = {'status': 'backing-up', 'backup': str(backup), 'prior_image_id': old_image,
               'new_image_id': report['server_build']['image_id'], 'files': [],
               'installed_utc': datetime.now(timezone.utc).isoformat(), 'live_accepted': False}
    receipt['protected_services'] = {
        name: command('docker', 'inspect', name, '--format', '{{.Id}}').decode().strip()
        for name in ('ac-authserver', 'ac-database')}
    transfers = [(file, CLIENT / file.relative_to(STAGE / 'client'))
                 for file in (STAGE / 'client').rglob('*') if file.is_file()]
    transfers += [(file, k.p.SERVER_DBC_ROOT / file.name) for file in (STAGE / 'server/dbc').glob('*.dbc')]
    override = ROOT / 'docker-compose.override.yml'
    transfers.append((None, override))
    for index, (source, destination) in enumerate(transfers):
        item = {'path': str(destination), 'existed': destination.exists(), 'backup': str(backup / str(index))}
        if destination.exists():
            item['before'] = k.p.sha256(destination)
            shutil.copy2(destination, item['backup'])
            if k.p.sha256(Path(item['backup'])) != item['before']:
                raise RuntimeError('Backup mismatch: ' + str(destination))
        if source:
            item['after'] = k.p.sha256(source)
        receipt['files'].append(item)
    # Dump only scoped world rows; accounts and saved characters are never changed.
    dump = 'USE `acore_world`;\n'
    for table, condition in SCOPES.items():
        shell = ('MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysqldump -uroot --default-character-set=utf8mb4 --set-gtid-purged=OFF --no-create-info --skip-triggers '
                 '--skip-add-locks --complete-insert acore_world ' + shlex.quote(table) +
                 ' --where=' + shlex.quote(condition))
        rows = command('docker', 'exec', 'ac-database', 'sh', '-c', shell).decode()
        dump += f'DELETE FROM `{table}` WHERE {condition};\n' + rows + '\n'
    k.save(backup / 'world-rows.dump', dump.encode())
    k.json_save(RECEIPT, receipt)
    print('Backups hash verified; stopping worldserver for matched replacement', flush=True)
    command('docker', 'compose', 'stop', 'ac-worldserver')
    try:
        sql('USE acore_world;\n' + k.MIGRATION.read_text())
        for source, destination in transfers:
            if source is None:
                text = destination.read_text()
                # Scope the image edit to the worldserver block; leave every other service untouched.
                start = text.index('  ac-worldserver:')
                end = text.index('\n  #', start) if '\n  #' in text[start:] else len(text)
                block = text[start:end]
                import re
                block, changed = re.subn(r'(?m)^    image: .+$', '    image: ' + IMAGE, block, count=1)
                if changed != 1:
                    raise RuntimeError('Worldserver image declaration changed')
                destination.write_text(text[:start] + block + text[end:], encoding='utf-8', newline='\n')
            else:
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, destination)
        for item in receipt['files']:
            item['installed'] = k.p.sha256(Path(item['path']))
            if 'after' in item and item['after'] != item['installed']:
                raise RuntimeError('Installed hash mismatch: ' + item['path'])
        k.json_save(RECEIPT, receipt)
        print('Migration and installed hashes verified; recreating worldserver', flush=True)
        command('docker', 'compose', 'up', '-d', '--no-deps', '--no-build', '--pull', 'never',
                '--force-recreate', 'ac-worldserver')
        receipt['status'] = 'installed-awaiting-runtime-check'
        k.json_save(RECEIPT, receipt)
        print('Installed matched native race package:', RECEIPT)
    except Exception:
        rollback()
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('preflight', 'install', 'rollback'))
    action = parser.parse_args().action
    if action == 'preflight':
        preflight()
        print('PASS install preflight')
    elif action == 'install':
        install()
    else:
        rollback()
