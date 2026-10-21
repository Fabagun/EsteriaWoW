"""Back up, apply, verify or roll back only the matched Slime Giant server data (races 71/72)."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

import creature_race_pack as creature
import slime_giant_race_pack as pack

RACES = (71, 72)
IDS = '71,72'
SERVER = pack.p.SERVER_DBC_ROOT
TABLES = pack.SERVER_TABLES
BACKUPS = Path('G:/EsteriaBackups')
PLAN = pack.STAGE / 'server-install-plan.json'
VALIDATION = pack.STAGE / 'server-build-validation.json'
AUDIT = pack.WORK / 'source-audit.json'
ROLLBACK_IMAGE = 'esteria-slimegiant-rollback:pre-20261020'
SCOPES = {name: (field, IDS) for name, field in {
    **creature.WORLD_TABLES, 'custom_race_start_spell_exclude': 'race',
    'custom_race_start_skill_exclude': 'race', 'chrraces_dbc': 'ID'}.items()}
SCOPES.update(creaturemodeldata_dbc=('ID', '120081,120082'),
              creaturedisplayinfo_dbc=('ID', '60072,60073'))
APPEARANCE = ('SELECT guid,race,gender,skin,face,hairStyle,hairColor,facialStyle,extraAppearance,teamId '
              'FROM characters ORDER BY guid;')


def save_json(path, value):
    pack.save(path, (json.dumps(value, indent=2) + '\n').encode())


def sql(query, database='acore_world'):
    command = ['docker', 'exec', '-i', 'ac-database', 'sh', '-c',
               'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql -uroot --batch --skip-column-names ' + database]
    result = subprocess.run(command, input=query.encode(), capture_output=True, check=False)
    if result.returncode:
        raise RuntimeError('Scoped SQL failed: ' + result.stderr.decode('utf-8', errors='replace'))
    return result.stdout


def docker(*arguments):
    return subprocess.check_output(['docker', *arguments], text=True).strip()


def stopped():
    assert docker('inspect', 'ac-worldserver', '--format', '{{.State.Running}}') == 'false', \
        'Stop only ac-worldserver before applying or rolling back server data'


def fingerprint():
    return {table: hashlib.sha256(b'\n'.join(sorted(sql(
        f'SELECT * FROM `{table}` WHERE `{field}` NOT IN ({ids});').splitlines()))).hexdigest()
        for table, (field, ids) in SCOPES.items()}


def vacant():
    for table, (field, ids) in SCOPES.items():
        assert sql(f'SELECT COUNT(*) FROM `{table}` WHERE `{field}` IN ({ids});').strip() == b'0', \
            'Reserved SQL rows are occupied: ' + table
    assert sql(f"SELECT COUNT(*) FROM `updates` WHERE `name`='{pack.MIGRATION.name}';").strip() == b'0', \
        'The dedicated migration already has a receipt'
    assert sql(f'SELECT COUNT(*) FROM characters WHERE race IN ({IDS});', 'acore_characters').strip() == b'0', \
        'Existing Slime Giant characters require an explicit preservation plan'


def validate_build():
    audit = pack.p.load_json(AUDIT)
    assert audit['npc_id'] == 175382 and set(audit['models']) == {'3490792'}, 'Wrong source model'
    model = audit['models']['3490792']
    assert (model['bones'], model['sequences']) == (208, 320), 'Wrong source skeleton'
    expected = {color.lower(): [3490792, 3491663 + i * 2, 3491664 + i * 2]
                for i, color in enumerate(pack.SOURCE_COLORS)}
    assert audit['palettes'] == expected, 'Wrong source palettes'
    validation = pack.p.load_json(VALIDATION)
    assert validation['all_passed'] is True and validation['source_model'] == 3490792, 'Build validation failed'
    assert validation['server_image'].startswith('sha256:'), 'Record the immutable built image ID'
    assert docker('image', 'inspect', validation['server_image'], '--format', '{{.Id}}') == \
        validation['server_image'], 'Built server image is absent'
    assert validation['migration_sha256'] == pack.p.sha256(pack.MIGRATION), 'Validated SQL changed'
    assert pack.MIGRATION.read_bytes() == pack.migration_sql().encode(), 'Unexpected migration content'
    assert (pack.STAGE / 'slime_giant.sql').read_bytes() == pack.MIGRATION.read_bytes(), 'Staged SQL differs'
    required = {'src/server/shared/SharedDefines.h', 'src/server/shared/CreatureAppearance.h'}
    assert required <= set(validation['source_files']), 'Server source fingerprints are incomplete'
    for name, expected_hash in validation['source_files'].items():
        assert pack.p.sha256(pack.p.ROOT / name) == expected_hash, 'Validated build source changed: ' + name
    assert set(validation['server_dbc_hashes']) == set(TABLES), 'Six validated server DBCs are required'
    for name, expected_hash in validation['server_dbc_hashes'].items():
        assert pack.p.sha256(pack.STAGE / 'server/dbc' / (name + '.dbc')) == expected_hash, \
            'Validated staged DBC changed: ' + name
    pack.self_check()
    return validation


def unchanged_characters(root):
    original = (root / 'characters-appearance.tsv').read_bytes().splitlines()
    current = set(sql(APPEARANCE, 'acore_characters').splitlines())
    assert all(row in current for row in original), 'A saved character appearance changed'


def load_plan():
    plan = pack.p.load_json(PLAN)
    root = Path(plan['backup'])
    assert root.resolve().parent == BACKUPS.resolve() and root.name.startswith('SlimeGiant-server-'), \
        'Unexpected rollback directory'
    assert PLAN.read_bytes() == (root / 'server-install-plan.json').read_bytes(), 'Install plans differ'
    for name, expected in plan['backup_hashes'].items():
        assert pack.p.sha256(root / name) == expected, 'Rollback backup changed: ' + name
    return plan, root


def prepare():
    validation = validate_build()
    vacant()
    names = ','.join("'" + name + "'" for name in (*SCOPES, 'updates'))
    engines = sql('SELECT TABLE_NAME,ENGINE FROM information_schema.TABLES '
                  f"WHERE TABLE_SCHEMA='acore_world' AND TABLE_NAME IN ({names});").splitlines()
    assert len(engines) == len(SCOPES) + 1 and all(row.endswith(b'\tInnoDB') for row in engines), \
        'Every scoped SQL table must support transactions'
    root = BACKUPS / ('SlimeGiant-server-' + datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S-%f'))
    root.mkdir(parents=True, exist_ok=False)
    before = {}
    for name in TABLES:
        live = SERVER / (name + '.dbc')
        assert pack.p.sha256(live) == pack.p.sha256(pack.STAGE / 'baseline-server' / live.name), \
            'Mounted DBC differs from the staged baseline: ' + name
        before[name] = pack.p.sha256(live)
        pack.save(root / 'server-dbc' / live.name, live.read_bytes())
        assert pack.p.sha256(root / 'server-dbc' / live.name) == before[name], 'DBC backup failed'
    for source in (pack.MIGRATION, AUDIT, VALIDATION):
        pack.save(root / source.name, source.read_bytes())
    scoped = {table: sql(f'SELECT * FROM `{table}` WHERE `{field}` IN ({ids});').hex()
              for table, (field, ids) in SCOPES.items()}
    scoped['updates'] = sql(f"SELECT * FROM `updates` WHERE `name`='{pack.MIGRATION.name}';").hex()
    assert not any(scoped.values()), 'Scoped rows changed during preparation'
    save_json(root / 'scoped-world-before.json', scoped)
    pack.save(root / 'characters-appearance.tsv', sql(APPEARANCE, 'acore_characters'))
    rollback = '\n'.join(f'DELETE FROM `{table}` WHERE `{field}` IN ({ids});'
                         for table, (field, ids) in SCOPES.items())
    rollback += f"\nDELETE FROM `updates` WHERE `name`='{pack.MIGRATION.name}';\n"
    pack.save(root / 'rollback-world.sql', rollback.encode())
    plan = {'status': 'prepared', 'backup': str(root), 'before': before,
            'after': validation['server_dbc_hashes'], 'world_fingerprints': fingerprint(),
            'server_image': validation['server_image'], 'rollback_image_tag': ROLLBACK_IMAGE,
            'rollback_image': docker('image', 'inspect', ROLLBACK_IMAGE, '--format', '{{.Id}}'),
            'migration_sha256': pack.p.sha256(pack.MIGRATION),
            'migration_sha1': hashlib.sha1(pack.MIGRATION.read_bytes()).hexdigest().upper(),
            'source_audit_sha256': pack.p.sha256(AUDIT), 'validation_sha256': pack.p.sha256(VALIDATION),
            'character_appearance_sha256': pack.p.sha256(root / 'characters-appearance.tsv'),
            'backup_hashes': {str(path.relative_to(root)): pack.p.sha256(path)
                              for path in root.rglob('*') if path.is_file()}}
    save_json(root / 'server-install-plan.json', plan)
    save_json(PLAN, plan)
    print('PREPARED hash-verified server rollback:', root, flush=True)


def atomic_copy(source, target, expected):
    temporary = target.with_suffix(target.suffix + '.slimegiant-next')
    output = temporary.open('xb')
    try:
        with output, source.open('rb') as incoming:
            shutil.copyfileobj(incoming, output)
        assert pack.p.sha256(temporary) == expected, 'Temporary DBC hash differs: ' + target.name
        os.replace(temporary, target)
        assert pack.p.sha256(target) == expected, 'Installed DBC hash differs: ' + target.name
    finally:
        temporary.unlink(missing_ok=True)


def db_semantics():
    for race, _, donor, _, display in pack.SPECS:
        classes = sql(f'SELECT class FROM playercreateinfo WHERE race={race} ORDER BY class;')
        assert [int(row) for row in classes.splitlines()] == list(pack.CLASSES), 'Wrong creation classes'
        actual = sql('SELECT class,map,zone,position_x,position_y,position_z,orientation '
                     f'FROM playercreateinfo WHERE race={race} ORDER BY class;')
        expected = sql('SELECT class,map,zone,position_x,position_y,position_z,orientation '
                       f'FROM playercreateinfo WHERE race={donor} ORDER BY class;')
        assert actual == expected, 'Wrong donor starts'
        spell, skill, language, alliance = (668, 98, 7, 0) if donor == 1 else (669, 109, 1, 1)
        assert sql(f'SELECT classMask,spell FROM custom_race_start_spell WHERE race={race};').strip() == \
            f'0\t{spell}'.encode(), 'Wrong starting language spell'
        assert sql(f'SELECT classMask,skill,`rank` FROM custom_race_start_skill WHERE race={race};').strip() == \
            f'0\t{skill}\t0'.encode(), 'Wrong starting language skill'
        actual = sql('SELECT FactionID,MaleDisplayId,FemaleDisplayId,ClientPrefix,BaseLanguage,Alliance '
                     f'FROM chrraces_dbc WHERE ID={race};').strip()
        assert actual == f'{donor}\t{display}\t0\tKt\t{language}\t{alliance}'.encode(), 'Wrong race identity'


def restore(plan, root):
    for name in TABLES:
        atomic_copy(root / 'server-dbc' / (name + '.dbc'), SERVER / (name + '.dbc'), plan['before'][name])
    sql('START TRANSACTION;\n' + (root / 'rollback-world.sql').read_text() + '\nCOMMIT;')
    assert fingerprint() == plan['world_fingerprints'], 'Unrelated world data changed'
    unchanged_characters(root)
    vacant()


def apply():
    stopped()
    plan, root = load_plan()
    assert not (root / 'server-applied.json').exists(), 'Server package was already applied'
    validate_build()
    assert pack.p.sha256(AUDIT) == plan['source_audit_sha256'], 'Source audit changed since preparation'
    assert pack.p.sha256(VALIDATION) == plan['validation_sha256'], 'Build validation changed since preparation'
    assert pack.p.sha256(pack.MIGRATION) == plan['migration_sha256'], 'Migration changed since preparation'
    for name in TABLES:
        assert pack.p.sha256(SERVER / (name + '.dbc')) == plan['before'][name], 'Mounted DBC changed: ' + name
        assert pack.p.sha256(pack.STAGE / 'server/dbc' / (name + '.dbc')) == plan['after'][name], \
            'Staged DBC changed: ' + name
    vacant()
    assert fingerprint() == plan['world_fingerprints'], 'Unrelated world data changed since preparation'
    unchanged_characters(root)
    try:
        receipt = (f"\nINSERT INTO `updates` (`name`,`hash`,`state`) VALUES "
                   f"('{pack.MIGRATION.name}','{plan['migration_sha1']}','PENDING');\nCOMMIT;")
        sql('START TRANSACTION;\n' + pack.MIGRATION.read_text() + receipt)
        for name in TABLES:
            atomic_copy(pack.STAGE / 'server/dbc' / (name + '.dbc'), SERVER / (name + '.dbc'), plan['after'][name])
        db_semantics()
        assert fingerprint() == plan['world_fingerprints'], 'Unrelated world data changed during installation'
        unchanged_characters(root)
    except Exception:
        restore(plan, root)
        raise
    save_json(root / 'server-applied.json', {'status': 'applied_awaiting_recreation',
                                           'migration_sha1': plan['migration_sha1'], 'after': plan['after']})
    print('APPLIED scoped server SQL and six DBCs:', root, flush=True)


def verify():
    plan, root = load_plan()
    assert (root / 'server-applied.json').is_file(), 'No successful server apply record'
    assert docker('inspect', 'ac-worldserver', '--format', '{{.Image}} {{.State.Running}}') == \
        plan['server_image'] + ' true', 'Runtime server image differs from the validated build'
    for name in TABLES:
        assert pack.p.sha256(SERVER / (name + '.dbc')) == plan['after'][name], 'Installed DBC differs: ' + name
        path = '/azerothcore/env/dist/data/dbc/' + name + '.dbc'
        assert docker('exec', 'ac-worldserver', 'sha256sum', path).split()[0] == plan['after'][name], \
            'Mounted runtime DBC differs: ' + name
    db_semantics()
    receipt = sql(f"SELECT hash,state FROM updates WHERE name='{pack.MIGRATION.name}';").strip()
    assert receipt == f"{plan['migration_sha1']}\tPENDING".encode(), 'Migration receipt differs'
    assert fingerprint() == plan['world_fingerprints'], 'Unrelated world data changed'
    unchanged_characters(root)
    save_json(root / 'server-verified.json', {'status': 'server_data_verified_live_client_pending',
                                            'image': plan['server_image'], 'server_dbc_hashes': plan['after'],
                                            'original_characters_preserved': True, 'live_client_checked': False})
    print('VERIFIED server image, six mounted DBCs, classes, starts, languages and preserved data:', root, flush=True)


def rollback():
    stopped()
    plan, root = load_plan()
    assert sql(f'SELECT COUNT(*) FROM characters WHERE race IN ({IDS});', 'acore_characters').strip() == b'0', \
        'Preserve new Slime Giant characters before rolling back their server support'
    for name in TABLES:
        assert pack.p.sha256(SERVER / (name + '.dbc')) in (plan['before'][name], plan['after'][name]), \
            'A server DBC has unrelated later changes: ' + name
    assert fingerprint() == plan['world_fingerprints'], 'Unrelated world data changed; inspect before rollback'
    restore(plan, root)
    save_json(root / 'server-rolled-back.json', {'status': 'data_restored_old_image_recreation_required',
                                               'rollback_image_tag': plan['rollback_image_tag'],
                                               'rollback_image': plan['rollback_image']})
    print('ROLLED BACK scoped server data; recreate the saved image separately:', plan['rollback_image_tag'],
          flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare', 'apply', 'verify', 'rollback'))
    args = parser.parse_args()
    {'prepare': prepare, 'apply': apply, 'verify': verify, 'rollback': rollback}[args.action]()
