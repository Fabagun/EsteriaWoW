"""Run the compiled Centaur protocol tests using temporary Docker process environment credentials."""

import os
import json
from pathlib import Path
import subprocess

import centaur_race_pack as pack
from slime_giant_deploy import sql


def main(output_root=None, test_pattern='^TestSession_CentaurCreationAndTravel$'):
    output_root = output_root or pack.WORK
    output_root.mkdir(parents=True, exist_ok=True)
    binary = pack.WORK / 'test-tools/centaur-e2e.test'
    assert binary.is_file(), 'Compile the pinned consumer test first'
    password = subprocess.check_output(['docker', 'exec', 'ac-database',
                                        'printenv', 'MYSQL_ROOT_PASSWORD'], text=True).strip()
    assert password and '\n' not in password
    networks = {name: json.loads(subprocess.check_output(['docker', 'inspect', name, '--format',
                '{{json .NetworkSettings.Networks}}'], text=True))
                for name in ('ac-worldserver', 'ac-authserver', 'ac-database')}
    shared = set.intersection(*(set(value) for value in networks.values()))
    assert len(shared) == 1, 'Choose the realm shared Docker network explicitly'
    network = shared.pop()
    database_address = networks['ac-database'][network]['IPAddress']
    auth_address = networks['ac-authserver'][network]['IPAddress']
    assert database_address and auth_address
    env = os.environ.copy()
    env['E2E_AUTH_ADDR'] = auth_address + ':3724'
    env['E2E_WORLD_LOG'] = 'info'
    for variable, database in (('AUTH', 'acore_auth'), ('CHAR', 'acore_characters'), ('WORLD', 'acore_world')):
        env['E2E_' + variable + '_DSN'] = f'root:{password}@tcp({database_address}:3306)/{database}'
    log = output_root / 'live-protocol-tests.log'
    command = ['docker', 'run', '--rm', '--network', 'container:ac-worldserver',
               '--mount', f'type=bind,source={binary.parent},target=/task,readonly',
               *[value for name in ('E2E_AUTH_ADDR', 'E2E_WORLD_LOG', 'E2E_AUTH_DSN',
                                    'E2E_CHAR_DSN', 'E2E_WORLD_DSN') for value in ('-e', name)],
               'golang:1.26', '/task/centaur-e2e.test', '-test.v=true',
               '-test.run=' + test_pattern, '-test.parallel=1', '-test.timeout=12m']
    before = sql("SELECT id FROM account WHERE username LIKE 'CNTAUR%';", 'acore_auth').splitlines()
    exit_code = 124
    try:
        with log.open('w', encoding='utf-8') as output:
            result = subprocess.run(command, env=env, stdout=output, stderr=subprocess.STDOUT, timeout=780)
            exit_code = result.returncode
    except subprocess.TimeoutExpired:
        print('Centaur protocol test timed out; disabling its test accounts')
    accounts = sql("SELECT id,username FROM account WHERE username LIKE 'CNTAUR%';", 'acore_auth').splitlines()
    output = log.read_text(encoding='utf-8', errors='replace').upper()
    added = [row.decode().split('\t') for row in accounts if row.split(b'\t')[0] not in before
             and row.decode().split('\t')[1].upper() in output]
    if added:
        ids = ','.join(str(int(row[0])) for row in added)
        # These fixtures use the harness's public password; never leave usable GM accounts on the realm.
        sql(f'UPDATE account SET salt=RANDOM_BYTES(32),verifier=RANDOM_BYTES(32),session_key=NULL '
            f'WHERE id IN ({ids});\nDELETE FROM account_access WHERE id IN ({ids});', 'acore_auth')
    pack.json_save(output_root / 'live-protocol-result.json', {'passed': exit_code == 0,
        'exit_code': exit_code, 'log': str(log), 'test_accounts': added, 'test_credentials_disabled': True,
        'rendered_client_acceptance': False})
    print('Centaur protocol test exit:', exit_code, 'log:', log)
    raise SystemExit(exit_code)


if __name__ == '__main__':
    main()
