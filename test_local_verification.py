"""Verification orchestration fixtures do not represent model or owner evidence."""
import contextlib
import io
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

import rrw_verify as verify


class LocalVerificationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        names = json.loads((verify.HERE / verify.MANIFEST).read_text())
        for name in (verify.MANIFEST, *names):
            target = self.root / name; target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(verify.HERE / name, target)

    def run_fixture(self, **kwargs):
        return verify.verify(self.root, runner=lambda *args: ('passed', 0), node='node',
                             emit=lambda *args: None, **kwargs)

    def test_source_bound_results_do_not_claim_browser_model_operator_or_contest(self):
        report, code = self.run_fixture()
        self.assertEqual(code, 0); self.assertTrue(report['development_verified'])
        self.assertTrue(report['sources_current']); self.assertEqual(len(report['checks']), 15)
        for name in ('browser_navigation', 'model_inference'):
            self.assertEqual(report[name], 'not_requested')
        self.assertEqual(report['operator_feedback'], 'not_collected')
        self.assertEqual(report['contest_readiness'], 'not_verified')

    def test_missing_node_cannot_be_a_complete_pass(self):
        report, code = verify.verify(self.root, runner=lambda *args: ('passed', 0),
                                    node=False, emit=lambda *args: None)
        self.assertEqual(code, 2); self.assertFalse(report['development_verified'])
        self.assertEqual(sum(row['state'] == 'unavailable' for row in report['checks']), 8)

    def test_failure_timeout_and_unavailable_are_distinct_and_never_pass(self):
        for state, expected in (('failed', 1), ('timed_out', 1), ('unavailable', 2)):
            with self.subTest(state=state):
                report, code = verify.verify(self.root, runner=lambda *args: (state, None),
                                            node='node', emit=lambda *args: None)
                self.assertEqual(code, expected); self.assertFalse(report['development_verified'])
                self.assertEqual(report['checks'][0]['state'], state)

    def test_changed_source_refuses_current_evidence_even_when_commands_pass(self):
        path = self.root / 'web/app.js'
        def changed(*args):
            path.write_bytes(path.read_bytes() + b'\n// controlled change\n')
            return 'passed', 0
        report, code = verify.verify(self.root, runner=changed, node='node', emit=lambda *args: None)
        self.assertEqual(code, 1); self.assertFalse(report['sources_current'])
        self.assertFalse(report['development_verified'])

    def test_browser_is_explicit_and_only_runs_existing_scripts(self):
        calls = []
        def recorded(command, *args): calls.append(command); return 'passed', 0
        report, code = verify.verify(self.root, browser=True, runner=recorded,
                                    node='node', emit=lambda *args: None)
        self.assertEqual(code, 0); self.assertEqual(report['browser_navigation'], 'passed')
        self.assertEqual(len(calls), 15)
        self.assertTrue(all(command[-1].endswith('_smoke.py') for command in calls[-4:]))
        self.assertNotIn('install', json.dumps(calls)); self.assertNotIn('ollama', json.dumps(calls))

    def test_private_state_never_read_fingerprinted_or_copied(self):
        marker = 'PRIVATE_CONTROLLED_OWNER_DATA'
        for name in ('.rrw/profiles.json', 'replies/private.md', 'profiles.json', '.env'):
            path = self.root / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_text(marker)
        report, _ = self.run_fixture()
        rendered = json.dumps(report)
        self.assertNotIn(marker, rendered); self.assertNotIn(self.temp.name, rendered)
        self.assertNotIn('profiles.json', rendered); self.assertNotIn('replies/', rendered)
        self.assertNotIn('.env', rendered); self.assertNotIn('stdout', rendered)

    def test_missing_linked_unlisted_or_private_inventory_is_refused(self):
        source = self.root / 'web/app.js'; before = source.read_bytes(); source.unlink()
        with self.assertRaises(ValueError): verify.source_snapshot(self.root)
        source.write_bytes(before)
        (self.root / 'test_new_unlisted.py').write_text('pass\n')
        with self.assertRaises(ValueError): verify.source_snapshot(self.root)
        (self.root / 'test_new_unlisted.py').unlink()
        manifest = self.root / verify.MANIFEST
        names = json.loads(manifest.read_text()); manifest.write_text(json.dumps(names + ['.rrw/profiles.json']))
        with self.assertRaises(ValueError): verify.source_snapshot(self.root)

    def test_source_link_is_refused(self):
        source = self.root / 'web/app.js'; target = self.root / 'target.js'; source.rename(target)
        try: source.symlink_to(target)
        except OSError: self.skipTest('Symlinks unavailable to this test account')
        with self.assertRaises(ValueError): verify.source_snapshot(self.root)

    def test_receipt_never_overwrites_and_contains_no_subprocess_output(self):
        report, _ = self.run_fixture(); path = self.root / 'receipt.json'
        verify.save_receipt(report, path); before = path.read_bytes()
        with self.assertRaises(ValueError): verify.save_receipt({}, path)
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(json.loads(before), report)

    def test_main_existing_output_refuses_before_running_checks(self):
        path = self.root / 'receipt.json'; path.write_text('KEEP_EXISTING')
        with patch.object(verify, 'verify', side_effect=AssertionError('Do not run')), \
             contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(verify.main(['--output', str(path)]), 1)
        self.assertEqual(path.read_text(), 'KEEP_EXISTING')

    def test_real_subprocess_success_failure_timeout_and_missing_executable(self):
        self.assertEqual(verify.execute([sys.executable, '-c', 'print("PRIVATE_FIXTURE")'], self.root, 5), ('passed', 0))
        self.assertEqual(verify.execute([sys.executable, '-c', 'raise SystemExit(7)'], self.root, 5), ('failed', 7))
        self.assertEqual(verify.execute([sys.executable, '-c', 'import time; time.sleep(10)'], self.root, .05), ('timed_out', None))
        self.assertEqual(verify.execute([str(self.root / 'missing-command')], self.root, 5), ('unavailable', None))


if __name__ == '__main__': unittest.main()
