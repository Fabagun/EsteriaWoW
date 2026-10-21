"""Stage and install the scoped Centaur equipment, customization and form repairs."""

from collections import Counter
from datetime import datetime, timezone
import hashlib
from pathlib import Path
import re
import shutil
import subprocess
import argparse

import centaur_deploy as deploy
import centaur_race_pack as pack

WORK = pack.WORK / 'repair-v2'
TABLES = ('CharSections', 'CharHairGeosets', 'CharacterFacialHairStyles', 'BarberShopStyle')
SERVER_TABLES = ('CharSections', 'BarberShopStyle')
MIGRATION = pack.p.ROOT / 'data/sql/updates/pending_db_world/rev_20261020030000000_centaur_flight_visual.sql'
IMAGE = 'esteria-centaur:repair-v2'


def stage():
    report = {'client': {}, 'server': {}, 'installed': False}
    with pack.p.ClientFiles(str(deploy.CLIENT / 'Data'), 'enUS') as files:
        baseline = {name: files.find(pack.p.DBC_ROOT + name + '.dbc')[0] for name in TABLES}
    replacements = {}
    for name, data in baseline.items():
        original = pack.p.RawWdbc(data)
        records, pool = list(original.records), bytearray(original.strings)
        for race, faction, _ in pack.SPECS:
            bounds = pack.ranges(race)
            for sex in (0, 1):
                heads, beards = (14 if sex else 9), (1 if sex else 8)
                if name == 'CharSections':
                    used = {pack.p._value(r, 0) for r in records}
                    identifier = bounds[name][0]
                    for kind, count in ((3, heads), (2, beards)):
                        template = next(r for r in original.records if pack.p._value(r, 4) == race
                            and pack.p._value(r, 8) == sex and pack.p._value(r, 12) == kind)
                        for style in range(1, count):
                            while identifier in used:
                                identifier += 1
                            assert identifier <= bounds[name][1]
                            row = pack.p._replace(template, 0, 4, identifier)
                            row = pack.p._replace(row, 32, 4, style)
                            records.append(row)
                            used.add(identifier)
                elif name == 'CharHairGeosets':
                    used = {pack.p._value(r, 0) for r in records}
                    identifier = bounds[name][0]
                    template = next(r for r in original.records if pack.p._value(r, 4) == race
                                    and pack.p._value(r, 8) == sex)
                    for style in range(1, heads):
                        while identifier in used:
                            identifier += 1
                        assert identifier <= bounds[name][1]
                        row = pack.p._replace(template, 0, 4, identifier)
                        row = pack.p._replace(row, 12, 4, style)
                        records.append(row)
                        used.add(identifier)
                elif name == 'CharacterFacialHairStyles':
                    template = next(r for r in original.records if pack.p._value(r, 0) == race
                                    and pack.p._value(r, 4) == sex)
                    records.extend(pack.p._replace(template, 8, 4, style) for style in range(1, beards))
                else:
                    used = {pack.p._value(r, 0) for r in records}
                    identifier = bounds[name][0]
                    for kind, count in ((0, heads), (2, beards)):
                        template = next(r for r in original.records if pack.p._value(r, 148) == race
                            and pack.p._value(r, 152) == sex and pack.p._value(r, 4) == kind)
                        for style in range(1, count):
                            while identifier in used:
                                identifier += 1
                            assert identifier <= bounds[name][1]
                            row = pack.p._replace(template, 0, 4, identifier)
                            row = pack.p._replace(row, 156, 4, style)
                            records.append(row)
                            used.add(identifier)
        output = original.build(records, bytes(pool))
        if name == 'CharSections':
            output = pack.o.order_charsections_entry(pack.p.DBC_ROOT + name + '.dbc', output)
        assert not (Counter(original.records) - Counter(pack.p.RawWdbc(output).records)), name
        pack.save(WORK / 'baseline-client' / (name + '.dbc'), data)
        pack.save(WORK / 'client-dbc' / (name + '.dbc'), output)
        replacements[pack.p.DBC_ROOT + name + '.dbc'] = output
        if name in SERVER_TABLES:
            old = (deploy.SERVER / (name + '.dbc')).read_bytes()
            server = pack.p.RawWdbc(old)
            new_rows = records[len(original.records):]
            pool = bytearray(server.strings)
            rows = [pack.p._clone_strings(name, original, row, pool) for row in new_rows]
            new = server.build([*server.records, *rows], bytes(pool))
            pack.save(WORK / 'baseline-server' / (name + '.dbc'), old)
            pack.save(WORK / 'server' / (name + '.dbc'), new)
            report['server'][name] = {'before': hashlib.sha256(old).hexdigest(),
                                     'after': hashlib.sha256(new).hexdigest()}
    storm = pack.p.Storm(pack.p.DLL_DEFAULT)
    for relative in (pack.p.GLOBAL_ARCHIVE_REL, pack.p.LOCALE_ARCHIVE_REL, deploy.ASSET):
        live, target = deploy.CLIENT / relative, WORK / 'client' / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        before = pack.p.sha256(live)
        shutil.copy2(live, target)
        if relative == deploy.ASSET:
            payloads = {str(p.relative_to(pack.STAGE / 'assets')).replace('/', '\\'): p.read_bytes()
                        for p in (pack.STAGE / 'assets/custom/centaur').glob('*') if p.is_file()}
        else:
            payloads = replacements
        storm.replace_archive_entries(target, payloads)
        handle = storm.open_archive(target)
        try:
            for key, data in payloads.items():
                assert storm.read(handle, key) == data, (str(relative), key)
        finally:
            storm.dll.SFileCloseArchive(handle)
        report['client'][str(relative)] = {'before': before, 'after': pack.p.sha256(target), 'source': str(target)}
    pack.json_save(WORK / 'stage.json', report)
    print('STAGED customization tables and corrected clothing; every archive entry read back', flush=True)


def install():
    deploy.closed()
    report = pack.p.load_json(WORK / 'stage.json')
    assert not report['installed']
    validation = pack.p.load_json(WORK / 'validation.json')
    assert validation['passed']
    assert deploy.docker('image', 'inspect', IMAGE, '--format', '{{.Id}}') == validation['server_image']
    exe = deploy.NATIVE / 'bin/Win/WowClientRetailInventory.exe'
    assert pack.p.sha256(exe) == validation['client_sha256']
    assert pack.p.sha256(MIGRATION) == validation['flight_sql_sha256']
    assert pack.p.sha256(pack.p.ROOT / 'src/server/shared/CreatureAppearance.h') == validation['server_header_sha256']
    for name, expected in validation['native_source'].items():
        assert pack.p.sha256(deploy.NATIVE / name) == expected, name
    root = Path('G:/EsteriaBackups') / ('Centaur-repair-' + datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S'))
    root.mkdir(parents=True, exist_ok=False)
    files = report['client']
    metadata_path = deploy.CLIENT / 'WowClientRetailVulkan.build.json'
    metadata = pack.p.load_json(metadata_path)
    assert metadata['sha256'] == pack.p.sha256(deploy.CLIENT / 'WowClientRetailVulkan.exe')
    metadata.update(sha256=validation['client_sha256'], backup_directory=str(root),
                    centaur_repairs={'receipt': str(WORK / 'receipt.json'), 'visual_acceptance': 'pending'})
    metadata['features'].append('Centaur facial choices, fitted armor/hooves and restoration after flight')
    for name, expected in validation['native_source'].items():
        row = next((row for row in metadata['source_files'] if row['path'] == name), None)
        if row is None:
            metadata['source_files'].append({'path': name, 'sha256': expected})
        else:
            row['sha256'] = expected
    pack.json_save(WORK / metadata_path.name, metadata)
    for name, source in (('WowClientRetailVulkan.exe', exe), (metadata_path.name, WORK / metadata_path.name)):
        files[name] = {'source': str(source), 'before': pack.p.sha256(deploy.CLIENT / name),
                       'after': pack.p.sha256(source)}
    for name, row in files.items():
        live, saved = deploy.CLIENT / name, root / 'client' / name
        assert pack.p.sha256(live) == row['before'], name
        assert pack.p.sha256(Path(row['source'])) == row['after'], name
        saved.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(live, saved)
        assert pack.p.sha256(saved) == row['before']
    for name, row in report['server'].items():
        assert pack.p.sha256(deploy.SERVER / (name + '.dbc')) == row['before']
        pack.save(root / 'server' / (name + '.dbc'), (deploy.SERVER / (name + '.dbc')).read_bytes())
    compose = pack.p.ROOT / 'docker-compose.override.yml'
    shutil.copy2(compose, root / compose.name)
    old_image = deploy.docker('inspect', 'ac-worldserver', '--format', '{{.Image}}')
    subprocess.run(['docker', 'image', 'tag', old_image, 'esteria-centaur-rollback:repair-v2'], check=True)
    where = 'ShapeshiftID=29 AND RaceID IN (73,74) AND CustomizationID=255 AND GenderID=2'
    assert not deploy.sql('SELECT * FROM player_shapeshift_model WHERE ' + where + ';').strip()
    rollback = 'DELETE FROM player_shapeshift_model WHERE ' + where + ';\n'
    rollback += f"DELETE FROM updates WHERE name='{MIGRATION.name}';\n"
    pack.save(root / 'rollback.sql', rollback.encode())
    pack.json_save(root / 'plan.json', report)
    subprocess.run(['docker', 'compose', 'stop', 'ac-worldserver'], cwd=pack.p.ROOT, check=True)
    appearance = deploy.sql(deploy.APPEARANCE, 'acore_characters')
    pack.save(root / 'character-appearance.tsv', appearance)
    try:
        sha1 = hashlib.sha1(MIGRATION.read_bytes()).hexdigest().upper()
        deploy.sql('START TRANSACTION;\n' + MIGRATION.read_text() +
            f"\nINSERT INTO updates(name,hash,state) VALUES('{MIGRATION.name}','{sha1}','PENDING');\nCOMMIT;")
        for name, row in files.items():
            deploy.atomic_copy(Path(row['source']), deploy.CLIENT / name, row['after'])
        for name, row in report['server'].items():
            deploy.atomic_copy(WORK / 'server' / (name + '.dbc'), deploy.SERVER / (name + '.dbc'), row['after'])
        text, count = re.subn(r'(  ac-worldserver:\n    image: )[^\n]+', r'\g<1>' + IMAGE, compose.read_text())
        assert count == 1
        compose.write_text(text, encoding='utf-8', newline='\n')
        assert deploy.sql(deploy.APPEARANCE, 'acore_characters') == appearance
        subprocess.run(['docker', 'compose', 'up', '-d', '--no-deps', '--no-build', '--pull', 'never',
                        '--force-recreate', 'ac-worldserver'], cwd=pack.p.ROOT, check=True)
    except Exception:
        for name, row in files.items():
            deploy.atomic_copy(root / 'client' / name, deploy.CLIENT / name, row['before'])
        for name, row in report['server'].items():
            deploy.atomic_copy(root / 'server' / (name + '.dbc'), deploy.SERVER / (name + '.dbc'), row['before'])
        deploy.sql('START TRANSACTION;\n' + rollback + '\nCOMMIT;')
        shutil.copy2(root / compose.name, compose)
        subprocess.run(['docker', 'compose', 'up', '-d', '--no-deps', '--no-build', '--pull', 'never',
                        '--force-recreate', 'ac-worldserver'], cwd=pack.p.ROOT, check=True)
        raise
    report.update(installed=True, backup=str(root), server_image=validation['server_image'], visual_accepted=False)
    pack.json_save(WORK / 'receipt.json', report)
    pack.json_save(root / 'receipt.json', report)
    print('INSTALLED Centaur repair; existing saved appearances unchanged; backup:', root, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('stage', 'install'))
    globals()[parser.parse_args().action]()
