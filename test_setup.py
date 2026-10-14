"""Setup failure recovery and evidence labels. No real model success is claimed."""
import contextlib
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import review_reply as rr
import rrw_evaluate as ev
import rrw_model as model
import rrw_setup as setup
import rrw_web as web
import rrw_workspace as ws


def installed():
    return {'ready': True, 'state': 'installed', 'message': 'private-server-message',
            'identity': {'name': 'gemma3:4b', 'digest': 'a' * 64, 'size': 3000000000,
                         'family': 'gemma3', 'parameter_size': 'private-metadata'},
            'version': 'private-version'}


def missing():
    return {'ready': False, 'state': 'missing', 'identity': None}


class SetupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def check(self, inspector=installed):
        return setup.check_setup(self.root, inspector)

    def test_default_check_never_generates_or_reads_customer_files(self):
        (self.root / 'gap_ledger.json').write_text('private-business-secret', encoding='utf-8')
        before = {p.name: p.read_bytes() for p in self.root.iterdir()}
        with patch.object(ws, 'gemma_caller', side_effect=AssertionError('Generated')), \
             patch.object(rr, 'load_ledger', side_effect=AssertionError('Read customer ledger')):
            report = self.check()
        self.assertTrue(report['templates_ready'])
        self.assertTrue(report['gemma_installed'])
        self.assertFalse(report['gemma_test']['requested'])
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.root.iterdir()})
        encoded = json.dumps(report)
        for private in (str(self.root), 'private-business-secret', 'private-server-message',
                        'private-metadata', 'private-version'):
            self.assertNotIn(private, encoded)

    def test_missing_model_does_not_prevent_template_launch(self):
        with patch.object(model, 'inspect_model', side_effect=missing), \
             patch.object(web, 'main', return_value=0) as launch, \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(setup.main(['--launch', '--data-dir', str(self.root), '--no-browser']), 0)
        launch.assert_called_once_with(['--port', '0', '--data-dir', str(self.root), '--no-browser'])

    def test_storage_failure_blocks_launch_and_excludes_error_details(self):
        with patch.object(setup, 'writable_directory', side_effect=OSError('private-folder-name')):
            report = self.check()
        self.assertFalse(report['templates_ready'])
        self.assertNotIn('private-folder-name', json.dumps(report))
        with patch.object(setup, 'check_setup', return_value=report), \
             patch.object(web, 'main') as launch, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(setup.main(['--launch']), 1)
        launch.assert_not_called()

    def test_incomplete_copy_has_clear_failure_and_no_model_inspection(self):
        with patch.object(setup, 'HERE', self.root):
            report = self.check(lambda: self.fail('Inspected missing installation'))
        self.assertFalse(report['templates_ready'])
        self.assertEqual(report['model']['state'], 'not_checked')
        self.assertFalse(next(c['passed'] for c in report['checks'] if c['id'] == 'installation'))

    def test_unsupported_python_does_not_import_or_probe_app(self):
        with patch.object(setup.sys, 'version_info', (3, 9, 7)), \
             patch.object(setup, 'template_check', side_effect=AssertionError('Imported app')):
            report = self.check(lambda: self.fail('Inspected model'))
        self.assertFalse(report['templates_ready'])
        self.assertEqual(len(report['checks']), 1)

    def test_loopback_permission_failure_is_actionable(self):
        with patch.object(setup, 'loopback_check', side_effect=OSError('blocked')):
            report = self.check()
        check = next(c for c in report['checks'] if c['id'] == 'loopback')
        self.assertFalse(check['passed'])
        self.assertIn('127.0.0.1', check['message'])
        self.assertFalse(report['templates_ready'])

    def test_template_regression_blocks_launch(self):
        with patch.object(rr, 'validate_reply', return_value=False):
            self.assertFalse(self.check()['templates_ready'])

    def test_existing_private_folder_is_probed_without_changing_contents(self):
        private = self.root / '.rrw'; private.mkdir()
        (private / 'profiles.json').write_text('owner-private', encoding='utf-8')
        with patch.object(setup.tempfile, 'TemporaryFile', wraps=tempfile.TemporaryFile) as probe:
            self.check()
        self.assertEqual([call.kwargs['dir'] for call in probe.call_args_list], [self.root, private])
        self.assertEqual((private / 'profiles.json').read_text(encoding='utf-8'), 'owner-private')

    def test_folder_files_and_links_are_rejected(self):
        (self.root / 'replies').write_text('not a directory', encoding='utf-8')
        self.assertFalse(self.check()['templates_ready'])
        (self.root / 'replies').unlink()
        try:
            (self.root / '.rrw').symlink_to(self.root, target_is_directory=True)
        except OSError:
            self.skipTest('Symlinks unavailable')
        self.assertFalse(self.check()['templates_ready'])

    def test_missing_model_verification_creates_diagnostics_without_fake_run(self):
        with patch.object(model, 'inspect_model', side_effect=missing), \
             contextlib.redirect_stdout(io.StringIO()):
            code = setup.main(['--verify-gemma', '--data-dir', str(self.root)])
        self.assertEqual(code, 2)
        report = json.loads((self.root / '.rrw/setup-check.json').read_text(encoding='utf-8'))
        self.assertEqual(report['gemma_test']['state'], 'prerequisites_failed')
        self.assertFalse(report['gemma_test']['passed'])
        self.assertFalse((self.root / '.rrw/evaluations').exists())

    def test_diagnostic_save_failure_is_not_reported_as_success(self):
        with patch.object(model, 'inspect_model', side_effect=missing), \
             patch.object(setup, 'save_report', side_effect=OSError('private error')), \
             contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(setup.main(['--report', str(self.root / 'report.json')]), 1)
        self.assertIn('Could not save', output.getvalue())
        self.assertNotIn('private error', output.getvalue())

    def test_doctor_uses_identity_check_and_does_not_claim_inference(self):
        with patch.object(model, 'inspect_model', side_effect=installed), \
             patch.object(rr, 'load_ledger', return_value={}), \
             patch.object(rr.urllib.request, 'urlopen', side_effect=AssertionError('Old transport')), \
             contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(rr.doctor(model.MODEL), 0)
        self.assertIn('generation not tested', output.getvalue())
        self.assertNotIn('Gemma will write', output.getvalue())

    def test_nested_remote_model_metadata_fails_all_installation_checks(self):
        tags = {'models': [{'name': model.MODEL, 'digest': 'a' * 64, 'size': 100,
                           'details': {'family': 'gemma3', 'remote_model': 'cloud-alias'}}]}
        with patch.object(ws, 'local_request', return_value=tags):
            self.assertFalse(ws.model_status()['ready'])
            self.assertFalse(setup.check_setup(self.root)['gemma_installed'])


class SmokeEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def fixture(self):
        lab = ev.EvaluationLab(ws.Workspace(self.root), inspector=installed)
        run = lab.start({'mode': 'offline', 'suite': 'smoke'})
        while len(run['results']) < len(run['cases']):
            run = lab.step({'id': run['id'], 'revision': run['revision']})
        # Construct a protocol fixture in memory; never store it as live evidence.
        run = copy.deepcopy(run)
        run.update(mode='gemma', execution='ollama', preflight=installed())
        for row in run['results']:
            row.update(status='model', attempts=[{'receipt': {'done': True}}])
        return run

    def test_pass_means_complete_current_api_protocol_and_no_human_assessment(self):
        summary = setup.smoke_summary(self.fixture())
        self.assertTrue(summary['passed'])
        self.assertEqual(summary['model_drafts'], 3)
        self.assertEqual(summary['human_reviewed'], 0)
        self.assertNotIn(str(self.root), json.dumps(summary))

    def test_fallback_stale_controlled_flagged_and_missing_receipts_cannot_pass(self):
        base = self.fixture()
        for change in ('fallback', 'stale', 'controlled', 'receipt', 'incomplete', 'identity', 'rubric', 'preflight'):
            run = copy.deepcopy(base)
            if change == 'fallback': run['results'][0]['status'] = 'fallback'
            if change == 'stale': run['sources']['review_reply.py'] = 'old'
            if change == 'controlled': run['execution'] = 'controlled-test'
            if change == 'receipt': run['results'][0]['attempts'] = []
            if change == 'incomplete': run['results'].pop()
            if change == 'identity': run['results'][0]['model_identity_changed'] = True
            if change == 'rubric': run['results'][0]['rubric_findings'] = ['Tier mismatch']
            if change == 'preflight': run['preflight']['ready'] = False
            with self.subTest(change=change):
                self.assertFalse(setup.smoke_summary(run)['passed'])

    def test_controlled_failing_caller_records_fallbacks_without_customer_drafts(self):
        def unavailable(*a):
            raise OSError('offline')
        workspace = ws.Workspace(self.root, caller=unavailable)
        report = setup.check_setup(self.root, installed)
        with patch.object(ws, 'Workspace', return_value=workspace), \
             patch.object(model, 'inspect_model', side_effect=installed), \
             patch.object(ev, 'inspect_model', side_effect=installed):
            setup.verify_gemma(report, self.root, emit=lambda s: None)
        self.assertFalse(report['gemma_test']['passed'])
        self.assertEqual(report['gemma_test']['fallbacks'], 3)
        self.assertEqual(report['gemma_test']['model_drafts'], 0)
        self.assertEqual(list((self.root / 'replies').iterdir()), [])
        self.assertFalse((self.root / 'gap_ledger.json').exists())
        self.assertEqual(len(list((self.root / '.rrw/evaluations').glob('*.json'))), 1)

    def test_interrupted_run_is_saved_and_cannot_pass(self):
        def stop(*a): raise KeyboardInterrupt()
        workspace = ws.Workspace(self.root, caller=stop)
        with patch.object(ws, 'Workspace', return_value=workspace), \
             patch.object(model, 'inspect_model', side_effect=installed), \
             patch.object(ev, 'inspect_model', side_effect=installed), \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(setup.main(['--verify-gemma', '--data-dir', str(self.root)]), 130)
        report = json.loads((self.root / '.rrw/setup-check.json').read_text(encoding='utf-8'))
        self.assertFalse(report['gemma_test']['passed'])
        self.assertEqual(report['gemma_test']['interrupted'], 1)
        self.assertEqual(report['gemma_test']['state'], 'interrupted')
        path = next((self.root / '.rrw/evaluations').glob('*.json'))
        self.assertEqual(ev.load_report(path)['results'][0]['status'], 'interrupted')

    def test_active_app_prevents_model_test_without_touching_drafts(self):
        report = setup.check_setup(self.root, installed)
        with web.InstanceLock(self.root), self.assertRaises(ws.WorkspaceError):
            setup.verify_gemma(report, self.root, emit=lambda s: None)
        self.assertFalse(report['gemma_test']['passed'])
        self.assertFalse((self.root / 'replies').exists())


if __name__ == '__main__':
    unittest.main()
