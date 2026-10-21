"""Guarded client staging and matched installation for the Centaur interaction repair."""

import argparse
from datetime import datetime, timezone
import hashlib
from pathlib import Path
import re
import shutil
import subprocess

import centaur_v4 as repair
import centaur_deploy as deploy

WORK = repair.WORK
IMAGE = 'esteria-centaur:repair-v4'
NATIVE_FILES = ('Engine/Source/Retail/Centaur.h', 'Engine/Source/Retail/CentaurAppearance.h',
                'WoW/Common/ComponentCore/RetailRace.cpp', 'WoW/Common/ComponentCore/RetailRace.h',
                'WoW/Source/Ui/GameUI_Scripts.cpp', 'Tools/RetailAssets/tests.cpp')
SERVER_FILES = ('src/server/shared/CentaurAppearance.h', 'src/server/game/Entities/Player/Player.h',
                'src/server/game/Entities/Player/Player.cpp', 'modules/mod-custom-server/src/centaur_travel.cpp')


def digest(path):
    return deploy.pack.p.sha256(path)


def archive_entries(storm, path):
    handle = storm.open_archive(path)
    try:
        return {name.replace('\\', '/').lower(): storm.read(handle, name)
                for name, *_ in storm.list_files(handle) if not name.startswith('(')}
    finally:
        storm.dll.SFileCloseArchive(handle)


def stage():
    repair.stage_ui()
    repair.verify()
    tests = deploy.NATIVE / 'build/retail-satchel/Release/RetailAssetTests.exe'
    for name, arguments in [('native-regression', []), ('native-art', ['--centaur-source',
            str(deploy.CLIENT / 'Data/Retail/RetailCasc.ini'), str(deploy.WORK)])]:
        with (WORK / (name + '.log')).open('w') as log:
            subprocess.run([str(tests), *arguments], check=True, stdout=log, stderr=subprocess.STDOUT)
    files, entries = {}, {}
    assets = deploy.pack.STAGE / 'assets/custom/centaur'
    entries[str(deploy.ASSET)] = {f'custom/centaur/{identifier}-clothing{ext}':
        (assets / f'{identifier}-clothing{ext}').read_bytes()
        for identifier in (4036647, 4081379) for ext in ('.m2', '00.skin')}
    locale = 'Data/enUS/patch-enUS-Z.MPQ'
    entries[locale] = {repair.UI_NAME: (WORK / 'client-ui/InterfaceOptionsPanels.xml').read_bytes()}
    storm = deploy.pack.p.Storm(deploy.pack.p.DLL_DEFAULT)
    for relative, payloads in entries.items():
        live, target = deploy.CLIENT / relative, WORK / 'client' / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        baseline = archive_entries(storm, live)
        shutil.copy2(live, target)
        storm.replace_archive_entries(target, payloads)
        after = archive_entries(storm, target)
        replacements = {name.replace('\\', '/').lower(): data for name, data in payloads.items()}
        assert after == {**baseline, **replacements}, 'Unrelated archive entries changed'
        files[relative] = {'source': str(target), 'before': digest(live), 'after': digest(target)}
    exe = deploy.NATIVE / 'bin/Win/WowClientRetailInventory.exe'
    metadata = deploy.pack.p.load_json(deploy.CLIENT / 'WowClientRetailVulkan.build.json')
    assert metadata['sha256'] == digest(deploy.CLIENT / 'WowClientRetailVulkan.exe')
    native = {name: digest(deploy.NATIVE / name) for name in NATIVE_FILES}
    server = {name: digest(Path(name)) for name in SERVER_FILES}
    metadata.update(sha256=digest(exe), staged_at_utc=datetime.now(timezone.utc).isoformat(),
                    centaur_repairs={'receipt': str(WORK / 'receipt.json'), 'visual_acceptance': 'pending'})
    metadata['features'].append(
        'Centaur loot motion, shared saved leg-armor toggle, gender restoration and draped cloaks')
    for name, sha in native.items():
        row = next((row for row in metadata['source_files'] if row['path'] == name), None)
        if row is None:
            metadata['source_files'].append({'path': name, 'sha256': sha})
        else:
            row['sha256'] = sha
    deploy.pack.json_save(WORK / 'WowClientRetailVulkan.build.json', metadata)
    for name, source in [('WowClientRetailVulkan.exe', exe),
                         ('WowClientRetailVulkan.build.json', WORK / 'WowClientRetailVulkan.build.json')]:
        files[name] = {'source': str(source), 'before': digest(deploy.CLIENT / name), 'after': digest(source)}
    deploy.pack.json_save(WORK / 'stage.json', {'files': files, 'native': native, 'server': server,
        'migration_sha1': hashlib.sha1(repair.MIGRATION.read_bytes()).hexdigest().upper(),
        'native_checks_passed': True, 'archive_preservation_passed': True})
    print('STAGED matched native client, four clothing entries, display checkbox and gender migration')


def install():
    report = deploy.pack.p.load_json(WORK / 'stage.json')
    assert report['native_checks_passed'] and report['archive_preservation_passed']
    for root, names in [(deploy.NATIVE, report['native']), (Path('.'), report['server'])]:
        for name, sha in names.items():
            assert digest(root / name) == sha, 'Source changed after validation: ' + name
    assert hashlib.sha1(repair.MIGRATION.read_bytes()).hexdigest().upper() == report['migration_sha1']
    image = deploy.docker('image', 'inspect', IMAGE, '--format', '{{.Id}}')
    assert not deploy.sql('SELECT * FROM creature_model_info WHERE DisplayID IN (60074,60075,60076,60077);').strip()
    assert not deploy.sql(f"SELECT name FROM updates WHERE name='{repair.MIGRATION.name}';").strip()
    processes = subprocess.check_output(['tasklist', '/fo', 'csv', '/nh'], text=True).lower()
    assert not any('"' + name in processes for name in ('wowclient', 'mpqeditor', 'eclipse')), 'Close WoW first'
    backup = Path('G:/EsteriaBackups') / ('Centaur-v4-' + datetime.now().strftime('%Y%m%d-%H%M%S'))
    backup.mkdir()
    metadata_path = WORK / 'WowClientRetailVulkan.build.json'
    metadata = deploy.pack.p.load_json(metadata_path)
    metadata['backup_directory'] = str(backup)
    deploy.pack.json_save(metadata_path, metadata)
    report['files'][metadata_path.name]['after'] = digest(metadata_path)
    deploy.pack.json_save(WORK / 'stage.json', report)
    for name, row in report['files'].items():
        assert digest(deploy.CLIENT / name) == row['before'] and digest(Path(row['source'])) == row['after'], name
        saved = backup / 'client' / name
        saved.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(deploy.CLIENT / name, saved)
        assert digest(saved) == row['before']
    compose = Path('docker-compose.override.yml')
    shutil.copy2(compose, backup / compose.name)
    rollback = ('DELETE FROM creature_model_info WHERE DisplayID IN (60074,60075,60076,60077);\n'
                f"DELETE FROM updates WHERE name='{repair.MIGRATION.name}';\n")
    (backup / 'rollback.sql').write_text(rollback)
    old_image = deploy.docker('inspect', 'ac-worldserver', '--format', '{{.Image}}')
    deploy.pack.json_save(backup / 'stage.json', {**report, 'old_image': old_image})
    subprocess.run(['docker', 'compose', 'stop', 'ac-worldserver'], check=True)
    appearance = deploy.sql(deploy.APPEARANCE, 'acore_characters')
    (backup / 'character-appearance.tsv').write_bytes(appearance)
    try:
        deploy.sql('START TRANSACTION;\n' + repair.MIGRATION.read_text() +
            f"INSERT INTO updates(name,hash,state) VALUES('{repair.MIGRATION.name}',"
            f"'{report['migration_sha1']}','PENDING');\nCOMMIT;")
        for name, row in report['files'].items():
            deploy.atomic_copy(Path(row['source']), deploy.CLIENT / name, row['after'])
        text, count = re.subn(r'(  ac-worldserver:\n    image: )[^\n]+', r'\g<1>' + IMAGE, compose.read_text())
        assert count == 1
        compose.write_text(text, encoding='utf-8', newline='\n')
        assert deploy.sql(deploy.APPEARANCE, 'acore_characters') == appearance
        subprocess.run(['docker', 'compose', 'up', '-d', '--no-deps', '--no-build', '--pull', 'never',
                        '--force-recreate', 'ac-worldserver'], check=True)
    except Exception:
        for name, row in report['files'].items():
            deploy.atomic_copy(backup / 'client' / name, deploy.CLIENT / name, row['before'])
        deploy.sql('START TRANSACTION;\n' + rollback + 'COMMIT;')
        shutil.copy2(backup / compose.name, compose)
        subprocess.run(['docker', 'compose', 'up', '-d', '--no-deps', '--no-build', '--pull', 'never',
                        '--force-recreate', 'ac-worldserver'], check=True)
        raise
    for name, row in report['files'].items():
        assert digest(deploy.CLIENT / name) == row['after'], name
    receipt = {**report, 'installed': True, 'backup': str(backup), 'server_image': image, 'old_image': old_image,
               'installed_at': datetime.now(timezone.utc).isoformat(), 'live_visual_accepted': False}
    deploy.pack.json_save(WORK / 'receipt.json', receipt)
    deploy.pack.json_save(backup / 'receipt.json', receipt)
    print('INSTALLED matched Centaur v4; backup:', backup, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('stage', 'install'))
    args = parser.parse_args()
    stage() if args.action == 'stage' else install()
