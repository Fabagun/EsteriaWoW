"""Completion markers must distinguish successful validation from failed or partial runs."""
import json
import subprocess
import sys
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, Mock

from batch import atomic_json
from run_full_batch import run, worker_environment


class FullRunnerTests(unittest.TestCase):
    def test_redirected_unicode_names_survive_windows_legacy_encoding(self):
        with patch.dict('os.environ', {'PYTHONIOENCODING': 'cp1252', 'PYTHONUTF8': '0'}):
            environment = worker_environment()
        result = subprocess.run([sys.executable, '-c', "print('Nidoran\\u2640 / Nidoran\\u2642')"],
                                env=environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        self.assertEqual(result.stdout.decode('utf8').strip(), 'Nidoran\u2640 / Nidoran\u2642')

    def test_ready_only_after_complete_catalog_and_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            atomic_json(output/'inventory.json', dict(forms=[dict(form=1), dict(form=2)]))
            atomic_json(output/'report.json', dict(selected_forms=[1, 2], completed_forms=2, counts=dict(passed=4)))
            child = Mock(pid=123)
            child.wait.return_value = 0
            with patch('run_full_batch.subprocess.Popen', return_value=child) as launch:
                state = run(output, output, output)
            self.assertEqual(state['status'], 'ready')
            self.assertEqual(launch.call_count, 2)
            self.assertEqual(launch.call_args.kwargs['env']['PYTHONIOENCODING'], 'utf-8')
            self.assertEqual(launch.call_args_list[1].args[0][2], 'validate')

    def test_recovery_uses_snapshot_and_preserves_existing_exports(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            atomic_json(output/'inventory.json', dict(forms=[dict(form=10)]))
            record = dict(form=10, shiny=False, status='passed', result=dict(files={'model.m2': 'hash'}))
            atomic_json(output/'report.json', dict(selected_forms=[10], completed_forms=1,
                                                  counts=dict(passed=1), records=[record]))
            child = Mock(pid=123)
            child.wait.return_value = 0
            with patch('run_full_batch.subprocess.Popen', return_value=child) as launch:
                state = run(output, output, output, recover=True)
            command = launch.call_args_list[0].args[0]
            self.assertIn('--preserve-passed', command)
            snapshot = Path(command[command.index('--preserve-passed')+1])
            self.assertEqual(json.loads(snapshot.read_text())['records'], [record])
            self.assertTrue(state['recovery'])
            self.assertEqual(state['status'], 'ready')

    def test_explicit_refresh_keeps_old_bytes_and_rejects_unlisted_changes(self):
        from batch import digest
        for allowed, corrupt in [(False, False), (True, False), (True, True)]:
            with tempfile.TemporaryDirectory() as directory:
                output = Path(directory)
                asset = output/'cache/assets/old.m2'
                asset.parent.mkdir(parents=True)
                asset.write_bytes(b'old validated bytes')
                original = dict(form=10, shiny=False, status='passed', result=dict(files={'old.m2': digest(asset)}))
                report = dict(selected_forms=[10], completed_forms=1, counts=dict(passed=1), records=[original])
                atomic_json(output/'inventory.json', dict(forms=[dict(form=10)]))
                atomic_json(output/'report.json', report)
                child = Mock(pid=123)
                child.wait.return_value = 0
                def launch(command, **kwargs):
                    if 'run' in command:
                        replacement = dict(original, result=dict(files={'new.m2': 'new-hash'}))
                        atomic_json(output/'report.json', dict(report, records=[replacement], refreshed_appearances=1))
                        if corrupt:
                            asset.write_bytes(b'overwritten')
                    return child
                with patch('run_full_batch.subprocess.Popen', side_effect=launch):
                    if allowed and not corrupt:
                        state = run(output, output, output, recover=True, refresh_forms={10})
                        self.assertEqual(state['status'], 'ready')
                        self.assertEqual(state['refreshed_appearances'], 1)
                        self.assertEqual(asset.read_bytes(), b'old validated bytes')
                    else:
                        with self.assertRaises((RuntimeError, ValueError)):
                            run(output, output, output, recover=True, refresh_forms={10} if allowed else set())
                        self.assertEqual(json.loads((output/'full-run.json').read_text())['status'], 'failed')

    def test_failed_correction_keeps_previous_record(self):
        from batch import recovery_record
        previous = dict(status='passed', result=dict(files={'old': 'hash'}))
        for candidate in [dict(status='failed', reason='bad geometry'), dict(status='unsupported', reason='missing')]:
            self.assertIs(recovery_record(previous, candidate), previous)
        replacement = dict(status='passed', result=dict(files={'new': 'hash2'}))
        self.assertIs(recovery_record(previous, replacement), replacement)

    def test_failed_validation_or_incomplete_report_never_marks_ready(self):
        for complete in [False, True]:
            with tempfile.TemporaryDirectory() as directory:
                output = Path(directory)
                atomic_json(output/'inventory.json', dict(forms=[dict(form=1), dict(form=2)]))
                atomic_json(output/'report.json', dict(selected_forms=[1, 2], completed_forms=2 if complete else 1,
                                                      counts=dict(passed=4)))
                child = Mock(pid=123)
                child.wait.side_effect = [0, 1]
                with patch('run_full_batch.subprocess.Popen', return_value=child):
                    with self.assertRaises(RuntimeError):
                        run(output, output, output)
                state = json.loads((output/'full-run.json').read_text())
                self.assertEqual(state['status'], 'failed')
                self.assertIn('error', state)


if __name__ == '__main__':
    unittest.main()
