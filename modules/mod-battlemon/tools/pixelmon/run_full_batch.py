"""Detached full-catalog conversion and validation; a scheduled follow-up handles final review/install."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys

from batch import DEFAULT_CLIENT, DEFAULT_OUTPUT, DEFAULT_SOURCE, atomic_json, version, preserved_records


def worker_environment():
    environment = os.environ.copy()
    # Redirected Windows stdout otherwise uses cp1252, which cannot print Nidoran's gender symbols.
    environment['PYTHONIOENCODING'] = 'utf-8'
    environment['PYTHONUTF8'] = '1'
    return environment


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def run(output, client, pixelmon, recover=False, refresh_forms=()):
    refresh_forms = set(refresh_forms)
    if refresh_forms and not recover:
        raise ValueError('Refresh forms require recovery mode')
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    # The OS releases this lock on exit/crash. A second detached launcher must not share the cache.
    import msvcrt
    lock = (output/'full-run.lock').open('a+b')
    lock.seek(0)
    if not lock.read(1):
        lock.write(b'0')
        lock.flush()
    lock.seek(0)
    try:
        msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
    except OSError:
        lock.close()
        raise RuntimeError('A full-catalog runner already owns this output directory')
    state_path = output/'full-run.json'
    state = dict(schema=1, pid=os.getpid(), started_utc=utc_now(), updated_utc=utc_now(),
                 status='running', phase='conversion', revision=version(), output=str(output))
    atomic_json(state_path, state)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    logs = output/'runs'/stamp
    logs.mkdir(parents=True)
    if (output/'report.json').exists():
        (logs/'previous-report.json').write_bytes((output/'report.json').read_bytes())
    try:
        scripts = Path(__file__).parent
        recovery_args = []
        if recover:
            previous = logs/'previous-report.json'
            if not previous.is_file():
                raise ValueError('Recovery requires a previous catalog report')
            recovery_args = ['--preserve-passed', str(previous), '--retry-failed', '--timeout', '600']
            state['recovery'] = True
            if refresh_forms:
                recovery_args += ['--refresh-forms', ','.join(str(v) for v in sorted(refresh_forms))]
                state['refresh_forms'] = sorted(refresh_forms)
        steps = [('conversion', [sys.executable, str(scripts/'batch.py'), 'run', '--all',
                                 '--output', str(output), '--client', str(client),
                                 '--pixelmon', str(pixelmon)] + recovery_args),
                 ('validation', [sys.executable, str(scripts/'batch_deploy.py'), 'validate', '--output', str(output)])]
        for phase, command in steps:
            state.update(phase=phase, log=str(logs/(phase+'.log')), updated_utc=utc_now())
            atomic_json(state_path, state)
            with (logs/(phase+'.log')).open('w', encoding='utf8') as stream:
                child = subprocess.Popen(command, stdout=stream, stderr=subprocess.STDOUT,
                                         env=worker_environment())
                state['child_pid'] = child.pid
                atomic_json(state_path, state)
                code = child.wait()
            if code:
                raise RuntimeError(f'{phase} exited with code {code}; see {state["log"]}')
            if phase == 'conversion':
                report = json.loads((output/'report.json').read_text())
                inventory = json.loads((output/'inventory.json').read_text())
                expected = {entry['form'] for entry in inventory['forms']}
                if set(report['selected_forms']) != expected or report['completed_forms'] != len(expected):
                    raise RuntimeError('Full-catalog report is incomplete; refusing completion')
                if recover:
                    previous = json.loads((logs/'previous-report.json').read_text(encoding='utf8'))
                    kept = {(r['form'], r['shiny']): r for r in report['records'] if r['status'] == 'passed'}
                    for record in previous['records']:
                        if record['status'] == 'passed':
                            current = kept.get((record['form'], record['shiny']))
                            if (current is None or (record['form'] not in refresh_forms
                                    and current['result']['files'] != record['result']['files'])):
                                raise RuntimeError('Recovery changed or lost an existing successful appearance')
                    if refresh_forms:
                        if not refresh_forms <= expected:
                            raise RuntimeError('Unknown refresh form IDs')
                        # Replacements use new asset names. Verify the old cache bytes
                        # still exist unchanged for receipts/checkpoints and rollback.
                        preserved_records(output, logs/'previous-report.json')
                state.update(counts=report['counts'], completed_forms=report['completed_forms'],
                             refreshed_appearances=report.get('refreshed_appearances', 0))
        if version() != state['revision']:
            raise RuntimeError('Converter changed during the run; review before installation')
        state.update(status='ready', phase='awaiting_review_and_install', finished_utc=utc_now())
    except BaseException as error:
        state.update(status='failed', error=type(error).__name__+': '+str(error), finished_utc=utc_now())
        raise
    finally:
        state['updated_utc'] = utc_now()
        atomic_json(state_path, state)
        lock.seek(0)
        msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
        lock.close()
    return state


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument('--client', type=Path, default=DEFAULT_CLIENT)
    parser.add_argument('--pixelmon', type=Path, default=DEFAULT_SOURCE)
    parser.add_argument('--recover', action='store_true',
                        help='Preserve previous successes and retry missing appearances')
    parser.add_argument('--refresh-forms', default='', help='Explicit reviewed orientation corrections')
    args = parser.parse_args()
    print(json.dumps(run(args.output, args.client.resolve(), args.pixelmon.resolve(), args.recover,
                         {int(v) for v in args.refresh_forms.split(',') if v}), indent=2))
