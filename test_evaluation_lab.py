"""Deterministic quality-lab tests. Controlled callers are not live-model evidence."""
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import check_submission as submission
import rrw_evaluate as ev
import rrw_model as model
import rrw_workspace as ws
from reply_safety import DraftBlocked


def inspection():
    return {'ready': True, 'state': 'installed', 'message': 'test double',
            'identity': {'name': 'gemma3:4b', 'digest': 'a' * 64}, 'version': 'fixture'}


def tags():
    return {'models': [{'name': 'gemma3:4b', 'digest': 'a' * 64, 'size': 3000000000,
                       'details': {'family': 'gemma3', 'quantization_level': 'Q4_K_M'}}]}


class ModelEvidenceTests(unittest.TestCase):
    def test_complete_response_has_typed_receipt(self):
        answer = model.checked_response({'model': model.MODEL, 'done': True,
            'response': ' A reply. ', 'eval_count': 10, 'eval_duration': 1000000000})
        self.assertEqual(answer, 'A reply.')
        self.assertEqual(answer.receipt['eval_count'], 10)

    def test_incomplete_wrong_model_empty_or_truncated_rejected(self):
        base = {'model': model.MODEL, 'done': True, 'response': 'reply'}
        for change in ({'done': False}, {'done': 'true'}, {'model': 'other'},
                       {'response': ' '}, {'done_reason': 'length'}, {'response': []}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                model.checked_response(dict(base, **change))

    def test_metrics_cannot_be_negative_boolean_nan_or_strings(self):
        for value in (-1, True, float('nan'), '12', 10**16):
            with self.subTest(value=value), self.assertRaises(ValueError):
                model.checked_response({'model': model.MODEL, 'done': True, 'response': 'ok', 'eval_count': value})

    def test_missing_receipt_cannot_be_called_complete(self):
        with self.assertRaises(ValueError):
            model.checked_response({'response': 'plausible but unverified'})

    def test_inspection_distinguishes_missing_and_unavailable(self):
        self.assertEqual(model.inspect_model(lambda p: {'models': []})['state'], 'missing')
        def unavailable(path):
            raise OSError('not running')
        self.assertEqual(model.inspect_model(unavailable)['state'], 'unavailable')

    def test_inspection_requires_digest_nonempty_model_and_correct_family(self):
        for field, value in (('digest', 'bad'), ('size', 0), ('size', True), ('details', {'family': 'other'})):
            data = tags(); data['models'][0][field] = value
            self.assertFalse(model.inspect_model(lambda p: data)['ready'])

    def test_cloud_metadata_and_duplicate_alias_are_rejected(self):
        data = tags(); data['models'][0]['remote_host'] = 'cloud.example'
        self.assertFalse(model.inspect_model(lambda p: data)['ready'])
        data = tags(); data['models'].append(copy.deepcopy(data['models'][0]))
        self.assertFalse(model.inspect_model(lambda p: data)['ready'])

    def test_inspection_preserves_identity_but_does_not_claim_network_audit(self):
        data = model.inspect_model(lambda p: tags() if p == '/api/tags' else {'version': '1.0'})
        self.assertTrue(data['ready']); self.assertEqual(data['version'], '1.0')
        self.assertFalse(data['local_execution_verified'])

    def test_missing_version_is_explicit(self):
        def request(path):
            if path == '/api/tags': return tags()
            raise OSError('not supported')
        data = model.inspect_model(request)
        self.assertTrue(data['ready']); self.assertIsNone(data['version'])


class EvaluationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.workspace = ws.Workspace(self.temp.name)
        self.lab = ev.EvaluationLab(self.workspace, inspector=inspection)

    def start(self, mode='offline', suite='smoke'):
        return self.lab.start({'mode': mode, 'suite': suite, 'confirmed': True})

    def step(self, report):
        return self.lab.step({'id': report['id'], 'revision': report['revision']})

    def finish(self, report):
        while len(report['results']) < len(report['cases']):
            report = self.step(report)
        return report

    def test_corpus_has_30_unique_fictional_cases(self):
        data = ev.corpus()
        self.assertEqual(len(data['cases']), 30)
        self.assertEqual(len({c['id'] for c in data['cases']}), 30)
        self.assertIn('fictional', data['provenance'])

    def test_offline_never_calls_model_or_inspects_service(self):
        self.workspace.caller = lambda *a: self.fail('Model called in offline mode')
        self.lab.inspect = lambda: self.fail('Network preflight in offline mode')
        report = self.finish(self.start())
        self.assertEqual(report['summary']['template'], 3)
        self.assertEqual(report['summary']['completed_api_responses'], 0)
        self.assertIsNone(report['summary']['model_median_seconds'])

    def test_evaluation_does_not_pollute_drafts_profiles_or_ledger(self):
        self.finish(self.start(suite='full'))
        self.assertEqual(list(self.workspace.drafts.iterdir()), [])
        self.assertFalse(self.workspace.profiles.exists())
        self.assertFalse(self.workspace.ledger.exists())

    def test_full_run_retains_cases_and_blocked_policy_after_quality_fixes(self):
        report = self.finish(self.start(suite='full'))
        rows = {r['case_id']: r for r in report['results']}
        self.assertEqual(rows['long-owner-policy']['status'], 'blocked')
        self.assertEqual(rows['high-stars-complaint']['rubric_findings'], [])
        self.assertEqual(rows['negation']['rubric_findings'], [])
        self.assertEqual(report['summary']['human_reviewed'], 0)

    def test_controlled_model_responses_are_not_real_evidence(self):
        baseline = self.step(self.start())['results'][0]['reply']
        self.workspace.caller = lambda *a: baseline
        report = self.step(self.start('gemma'))
        self.assertEqual(report['execution'], 'controlled-test')
        self.assertEqual(report['summary']['model'], 1)
        self.assertEqual(report['summary']['genuine_model_drafts'], 0)
        self.assertEqual(report['summary']['completed_api_responses'], 0)
        self.assertTrue(ev.live_evidence_blockers(report))

    def test_controlled_retry_records_raw_attempt_and_prompt_hash(self):
        baseline = self.step(self.start())['results'][0]['reply']
        answers = iter([baseline + '\nWe will refund you.', baseline])
        self.workspace.caller = lambda *a: next(answers)
        report = self.step(self.start('gemma'))
        row = report['results'][0]
        self.assertEqual(row['status'], 'model'); self.assertEqual(len(row['attempts']), 2)
        self.assertIn('refund', row['attempts'][0]['candidate'])
        self.assertEqual(len(row['attempts'][0]['prompt_sha256']), 64)
        self.assertTrue(row['attempts'][0]['findings'])
        self.assertFalse(self.workspace.ledger.exists())

    def test_unavailable_generation_remains_labelled_fallback(self):
        def unavailable(*a): raise OSError('Model offline')
        self.workspace.caller = unavailable
        report = self.step(self.start('gemma'))
        self.assertEqual(report['results'][0]['status'], 'fallback')
        self.assertEqual(report['summary']['genuine_model_drafts'], 0)
        self.assertIsNone(report['summary']['model_median_seconds'])

    def test_failed_preflight_is_saved_and_cannot_run(self):
        self.lab.inspect = lambda: {'ready': False, 'message': 'missing', 'state': 'missing'}
        report = self.start('gemma')
        self.assertTrue(self.lab._path(report['id']).exists())
        with self.assertRaises(ws.WorkspaceError): self.step(report)

    def test_boolean_confirmation_required_for_model_evaluation(self):
        for confirm in (False, 'true', 1, None):
            with self.subTest(confirm=confirm), self.assertRaises(ws.WorkspaceError):
                self.lab.start({'mode': 'gemma', 'confirmed': confirm})

    def test_source_change_prevents_mixed_version_resume(self):
        report = self.start()
        with patch.object(ev, 'source_snapshot', return_value={'different': 'code'}):
            with self.assertRaises(ws.WorkspaceError): self.step(report)

    def test_model_identity_change_is_recorded_as_error(self):
        report = self.start('gemma')
        self.lab.inspect = lambda: dict(inspection(), identity={'digest': 'b'*64})
        result = self.step(report)
        self.assertEqual(result['results'][0]['status'], 'error')
        self.assertTrue(result['results'][0]['model_identity_changed'])

    def test_identity_change_after_generation_does_not_count_as_model_success(self):
        baseline = self.step(self.start())['results'][0]['reply']
        self.workspace.caller = lambda *a: baseline
        report = self.start('gemma')
        checks = iter([inspection(), dict(inspection(), identity={'digest': 'changed'})])
        self.lab.inspect = lambda: next(checks)
        result = self.step(report)
        self.assertEqual(result['results'][0]['status'], 'error')
        self.assertEqual(result['summary']['model'], 0)

    def test_stale_revision_cannot_run_case_twice(self):
        report = self.start(); updated = self.step(report)
        with self.assertRaises(ws.WorkspaceError): self.step(report)
        self.assertEqual(len(ev.load_report(self.lab._path(report['id']))['results']), 1)

    def test_complete_run_cannot_overwrite_results(self):
        report = self.finish(self.start())
        before = self.lab._path(report['id']).read_bytes()
        with self.assertRaises(ws.WorkspaceError): self.step(report)
        self.assertEqual(self.lab._path(report['id']).read_bytes(), before)

    def test_generation_gate_is_shared_with_drafting(self):
        report = self.start()
        self.workspace.generation.acquire()
        try:
            with self.assertRaises(ws.WorkspaceError): self.step(report)
        finally: self.workspace.generation.release()

    def test_interruption_reserves_case_before_inference(self):
        report = self.start()
        with patch.object(self.workspace, '_generate', side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt): self.step(report)
        saved = ev.load_report(self.lab._path(report['id']))
        self.assertEqual(saved['results'][0]['status'], 'interrupted')
        self.assertFalse(self.workspace.generation.locked())
        self.assertFalse(ev.summarize(saved)['complete'])
        self.assertEqual(len(self.step(dict(saved, revision=saved['sha256']))['results']), 2)

    def test_resume_after_reopening_workspace(self):
        report = self.step(self.start())
        newlab = ev.EvaluationLab(ws.Workspace(self.temp.name))
        read = newlab.dispatch('quality-get', {'id': report['id']})
        self.assertEqual(len(newlab.step({'id': read['id'], 'revision': read['revision']})['results']), 2)

    def test_corrupt_report_remains_visible_and_is_not_overwritten(self):
        report = self.start(); path = self.lab._path(report['id'])
        path.write_text('{corrupt')
        listed = self.lab.dispatch('quality-list', {})['runs']
        self.assertIn('error', listed[0])
        with self.assertRaises(ValueError): self.step(report)
        self.assertEqual(path.read_text(), '{corrupt')

    def test_checksum_detects_modified_candidate(self):
        report = self.step(self.start()); path = self.lab._path(report['id'])
        data = json.loads(path.read_text()); data['results'][0]['reply'] += 'tampered'
        path.write_text(json.dumps(data))
        with self.assertRaises(ValueError): ev.load_report(path)

    def test_result_hash_detects_change_despite_resealed_envelope(self):
        report = self.step(self.start()); path = self.lab._path(report['id'])
        data = json.loads(path.read_text()); data['results'][0]['reply'] += 'edited'
        data['sha256'] = ev.digest({k:v for k,v in data.items() if k != 'sha256'})
        path.write_text(json.dumps(data))
        with self.assertRaises(ValueError): ev.load_report(path)

    def test_paths_and_export_formats_are_restricted(self):
        for name in ('../profiles', '/tmp/file', ['id'], 'eval-bad'):
            with self.subTest(name=name), self.assertRaises(ws.WorkspaceError):
                self.lab.dispatch('quality-get', {'id': name})
        report = self.start()
        with self.assertRaises(ws.WorkspaceError):
            self.lab.dispatch('quality-export', {'id': report['id'], 'revision': report['revision'], 'format':'html'})

    def assessment(self, report, **changes):
        row = report['results'][0]
        return dict(id=report['id'], revision=report['revision'], case_id=row['case_id'],
            result_sha256=row['result_sha256'], reviewed=True, decision='usable', **changes)

    def test_human_assessment_binds_to_result_and_never_approves_customer_draft(self):
        report = self.step(self.start())
        updated = self.lab.dispatch('quality-assess', self.assessment(report))
        self.assertEqual(updated['summary']['human_reviewed'], 1)
        self.assertEqual(updated['results'][0]['reply'], report['results'][0]['reply'])
        self.assertEqual(list(self.workspace.drafts.iterdir()), [])

    def test_assessment_needs_boolean_confirmation_and_current_result(self):
        report = self.step(self.start())
        for changes in ({'reviewed':'true'}, {'result_sha256':'wrong'}, {'decision':'approved'}, {'issues':['invented']}):
            payload = self.assessment(report); payload.update(changes)
            with self.subTest(changes=changes), self.assertRaises(ws.WorkspaceError):
                self.lab.dispatch('quality-assess', payload)

    def test_stale_assessment_does_not_overwrite(self):
        report = self.step(self.start()); self.lab.dispatch('quality-assess', self.assessment(report))
        with self.assertRaises(ws.WorkspaceError): self.lab.dispatch('quality-assess', self.assessment(report))

    def test_needed_edit_requires_description_and_records_unsafe_corrected_version(self):
        report = self.step(self.start()); payload = self.assessment(report)
        payload['decision'] = 'needs_edit'
        with self.assertRaises(ws.WorkspaceError): self.lab.dispatch('quality-assess', payload)
        payload.update(edited_reply=report['results'][0]['reply']+' We will refund you.')
        updated = self.lab.dispatch('quality-assess', payload)
        self.assertTrue(updated['results'][0]['human_review']['edited_findings'])
        self.assertNotIn('refund you', updated['results'][0]['reply'])

    def test_no_draft_cannot_be_marked_usable(self):
        report = self.start()
        with patch.object(self.workspace, '_generate', side_effect=DraftBlocked(['test'])):
            report = self.step(report)
        with self.assertRaises(ws.WorkspaceError): self.lab.dispatch('quality-assess', self.assessment(report))

    def test_export_is_verifiable_and_does_not_mislabel_templates_as_live(self):
        report = self.finish(self.start())
        payload = {'id':report['id'], 'revision':report['revision'], 'format':'json'}
        result = self.lab.dispatch('quality-export', payload)
        path = Path(self.temp.name)/'export.json'; path.write_text(result['text'])
        self.assertTrue(ev.live_evidence_blockers(ev.load_report(path)))
        result = self.lab.dispatch('quality-export', dict(payload, format='markdown'))
        self.assertIn('not real-customer validation', result['text'])
        self.assertIn('Unreviewed cases have unknown quality', result['text'])

    def test_real_transport_receipts_can_be_measured_without_counting_templates(self):
        baseline = self.step(self.start())['results'][0]['reply']
        self.workspace.caller = ws.gemma_caller
        with patch.object(ws, 'local_request', return_value={'model': model.MODEL, 'done': True,
            'response':baseline, 'eval_count':15, 'eval_duration':1000}):
            report = self.step(self.start('gemma'))
        # This is a test of production transport accounting, not a published live result.
        self.assertEqual(report['summary']['completed_api_responses'], 1)
        self.assertEqual(report['summary']['genuine_model_drafts'], 1)
        self.assertTrue(ev.live_evidence_blockers(report))  # Not complete or human-reviewed.

    def test_active_run_cannot_export_a_reserved_inflight_row(self):
        report = self.start(); self.lab.active = report['id']
        with self.assertRaises(ws.WorkspaceError):
            self.lab.dispatch('quality-export', dict(id=report['id'], revision=report['revision'], format='json'))

    def test_export_old_revision_is_refused(self):
        report = self.start(); self.step(report)
        with self.assertRaises(ws.WorkspaceError):
            self.lab.dispatch('quality-export', dict(id=report['id'], revision=report['revision'], format='markdown'))

    def test_release_requires_artifact_not_just_attestation(self):
        self.assertTrue(submission.evaluation_blockers(None))
        report = self.finish(self.start())
        self.assertTrue(submission.evaluation_blockers(self.lab._path(report['id'])))
        self.assertTrue(submission.evaluation_blockers(Path(self.temp.name)/'missing.json'))

    def test_invalid_suite_or_mode_rejected(self):
        for payload in ({'suite':'other'}, {'mode':'cloud'}):
            with self.assertRaises(ws.WorkspaceError): self.lab.start(payload)


if __name__ == '__main__':
    unittest.main()
