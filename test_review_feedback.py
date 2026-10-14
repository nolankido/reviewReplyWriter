"""Before/after provenance and private assessments. Fixtures are not user evidence."""
import base64
import http.client
import io
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
from zipfile import ZipFile

import review_reply as rr
import rrw_feedback as feedback
from rrw_submission import SubmissionDesk
from rrw_web import LocalServer
from rrw_workspace import Workspace, WorkspaceError

INPUT = {'business': 'Demo Cafe', 'review': 'Cold coffee and a 25 minute wait. Disappointing.',
         'stars': 2, 'mode': 'offline'}
ASSESSMENT = {'role': 'demo', 'scenario': 'fictional', 'decision': 'needs_edits',
              'reasons': ['tone'], 'note': 'Synthetic test note.', 'review_seconds': None}


class ReplyComparisonTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.w = Workspace(self.temp.name)
        self.draft = self.w.dispatch('generate', INPUT)

    def edit(self, reply):
        self.draft = self.w.dispatch('edit', {'id': self.draft['id'], 'revision': self.draft['revision'], 'reply': reply})
        return self.draft

    def test_starting_reply_survives_multiple_edits_and_restart(self):
        before = self.draft['reply']
        self.edit(before + '\nThank you.')
        self.edit(before + '\nWe appreciate the feedback.')
        view = Workspace(self.temp.name).dispatch('get', {'id': self.draft['id']})
        self.assertEqual(view['reply_comparison']['baseline_reply'], before)
        self.assertEqual(view['generation_baseline']['reply'], before)
        self.assertTrue(view['human_edited'])
        self.assertTrue(view['reply_comparison']['changed'])

    def test_diff_reconstructs_whitespace_unicode_and_both_replies_exactly(self):
        for before, after in (('Thanks.\n\nCoffee matters.', 'Thank you.\nCoffee matters.'),
                              ('Café coffee.', 'Café hot coffee.'), ('a b a b', 'b a b a')):
            draft = {'reply': after, 'generation_baseline': {'reply': before, 'engine': 'template', 'generated_at': 'fixture'}}
            compared = feedback.comparison(draft)
            self.assertEqual(''.join(p['before'] for p in compared['changes']), before)
            self.assertEqual(''.join(p['after'] for p in compared['changes']), after)

    def test_regeneration_resets_baseline_and_owner_edit_credit(self):
        self.edit(self.draft['reply'] + '\nThank you.')
        view = self.w.dispatch('reroll', {'id': self.draft['id'], 'revision': self.draft['revision'], 'mode': 'offline'})
        self.assertFalse(view['human_edited'])
        self.assertFalse(view['reply_comparison']['changed'])
        self.assertEqual(view['generation_baseline']['reply'], view['reply'])

    def test_restoring_still_requires_save_checks_and_fresh_approval(self):
        before = self.draft['reply']
        self.edit(before + '\nThank you.')
        self.w.dispatch('decision', {'id': self.draft['id'], 'revision': self.draft['revision'],
                                    'status': 'approved', 'reviewed': True})
        restored = self.edit(before)
        self.assertEqual(restored['status'], 'pending')
        with self.assertRaises(WorkspaceError):
            self.w.dispatch('approved-text', {'id': restored['id'], 'revision': restored['revision']})

    def test_missing_or_invalid_baseline_is_not_reconstructed(self):
        for value in (None, [], {'reply': 'x'}, {'reply': ['x'], 'engine': '', 'generated_at': ''}):
            self.assertFalse(feedback.comparison({'reply': 'Current reply', 'generation_baseline': value})['available'])
        old = dict(rr.parse_draft(self.w.drafts / self.draft['id']))
        old.pop('generation_baseline')
        view = self.w._write(old, self.draft['id'])
        self.assertFalse(view['reply_comparison']['available'])
        self.assertEqual(feedback.source_kind(old), 'unknown')

    def test_long_comparisons_remain_bounded_and_keep_full_text(self):
        before, after = 'word ' * 900, 'word ' * 899 + 'different'
        compared = feedback.comparison({'reply': after, 'generation_baseline':
            {'reply': before, 'engine': 'template', 'generated_at': 'fixture'}})
        self.assertTrue(compared['highlight_limited'])
        self.assertEqual(compared['changes'], [])
        self.assertEqual(compared['baseline_reply'], before)


class ReviewNotesTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.w = Workspace(self.temp.name)
        self.draft = self.w.dispatch('generate', INPUT)

    def request(self, **updates):
        value = {'id': self.draft['id'], 'revision': self.draft['revision'],
                 'note_revision': self.draft['review_note']['revision'], 'assessment': dict(ASSESSMENT)}
        value.update(updates)
        return value

    def save(self, **updates):
        return self.w.dispatch('feedback-save', self.request(**updates))

    def summary(self):
        return json.loads(self.w.dispatch('feedback-summary')['text'])

    def test_new_workspace_does_not_invent_assessments(self):
        self.assertIsNone(self.draft['review_note']['assessment'])
        report = self.summary()
        self.assertEqual(report['current'], 0)
        self.assertEqual(sum(report['sources'].values()), 0)

    def test_notes_survive_restart_without_approving_or_changing_draft(self):
        original = (self.w.drafts / self.draft['id']).read_bytes()
        note = self.save()
        reopened = Workspace(self.temp.name).dispatch('get', {'id': self.draft['id']})
        self.assertTrue(note['current'])
        self.assertEqual(reopened['review_note']['assessment'], ASSESSMENT)
        self.assertEqual(reopened['status'], 'pending')
        self.assertEqual((self.w.drafts / self.draft['id']).read_bytes(), original)
        with self.assertRaises(WorkspaceError):
            self.w.dispatch('approved-text', {'id': self.draft['id'], 'revision': self.draft['revision']})

    def test_post_write_damage_cannot_return_an_empty_success_receipt(self):
        original = rr.atomic_json
        path = self.w.private / 'review-notes' / (self.draft['id'] + '.json')
        before = (self.w.drafts / self.draft['id']).read_bytes()
        def damaged(target, record):
            original(target, record)
            Path(target).write_text('{CONTROLLED_POST_WRITE_DAMAGE', encoding='utf-8')
        with patch.object(rr, 'atomic_json', side_effect=damaged), self.assertRaises(WorkspaceError) as error:
            self.save()
        self.assertEqual(error.exception.status, 409)
        self.assertEqual(path.read_text(encoding='utf-8'), '{CONTROLLED_POST_WRITE_DAMAGE')
        self.assertEqual((self.w.drafts / self.draft['id']).read_bytes(), before)
        self.assertEqual(self.summary()['unreadable'], 1)

    def test_different_valid_post_write_note_cannot_acknowledge_submitted_values(self):
        original = rr.atomic_json
        def replaced(target, record):
            other = dict(record, assessment=dict(record['assessment'], note='CONTROLLED_OTHER_NOTE'))
            other['sha256'] = feedback.digest({k: v for k, v in other.items() if k != 'sha256'})
            original(target, other)
        with patch.object(rr, 'atomic_json', side_effect=replaced), self.assertRaises(WorkspaceError) as error:
            self.save()
        self.assertEqual(error.exception.status, 409)
        view = self.w.dispatch('get', {'id': self.draft['id']})
        self.assertEqual(view['review_note']['assessment']['note'], 'CONTROLLED_OTHER_NOTE')
        self.assertEqual(view['status'], 'pending')

    def test_failed_post_write_read_preserves_the_saved_record_for_inspection(self):
        original = self.w.review_notes._read
        count = 0
        def unreadable(name):
            nonlocal count
            count += 1
            if count == 2:
                raise OSError('CONTROLLED_READ_FAILURE')
            return original(name)
        with patch.object(self.w.review_notes, '_read', side_effect=unreadable), self.assertRaises(WorkspaceError) as error:
            self.save()
        self.assertEqual(error.exception.status, 409)
        self.assertEqual(self.w.dispatch('get', {'id': self.draft['id']})['review_note']['assessment'], ASSESSMENT)

    def test_draft_changed_after_note_write_prevents_current_acknowledgement(self):
        original = rr.atomic_json
        def changed(target, record):
            original(target, record)
            path = self.w.drafts / self.draft['id']
            path.write_text(path.read_text(encoding='utf-8') + '\nThank you.', encoding='utf-8')
        with patch.object(rr, 'atomic_json', side_effect=changed), self.assertRaises(WorkspaceError) as error:
            self.save()
        self.assertEqual(error.exception.status, 409)
        self.assertFalse(self.w.dispatch('get', {'id': self.draft['id']})['review_note']['current'])
        self.assertEqual(self.summary()['stale'], 1)

    def test_acknowledgement_matches_canonical_saved_note_and_hash(self):
        note = self.save(assessment=dict(ASSESSMENT, note='  Synthetic note with spacing.\n'))
        record = self.w.review_notes._read(self.draft['id'])
        self.assertEqual(note['revision'], record['sha256'])
        self.assertEqual(note['assessment']['note'], 'Synthetic note with spacing.')
        self.assertTrue(note['current'])

    def test_saved_assessment_does_not_clear_an_existing_posting_approval(self):
        self.w.dispatch('decision', dict(self.request(), status='approved', reviewed=True))
        self.save()
        self.assertEqual(self.w.dispatch('get', {'id': self.draft['id']})['status'], 'approved')

    def test_old_notes_become_stale_and_can_be_explicitly_reassessed(self):
        self.save()
        self.draft = self.w.dispatch('edit', {'id': self.draft['id'], 'revision': self.draft['revision'],
                                             'reply': self.draft['reply'] + '\nThank you.'})
        self.assertFalse(self.draft['review_note']['current'])
        self.assertEqual(self.summary()['stale'], 1)
        self.assertEqual(self.summary()['current'], 0)
        self.assertTrue(self.save()['current'])
        self.assertEqual(self.summary()['current'], 1)

    def test_stale_missing_and_null_revisions_cannot_overwrite_notes(self):
        self.save()
        for changes in ({}, {'note_revision': None}, {'revision': None}, {'revision': 'bad'}, {'note_revision': 'bad'}):
            with self.subTest(changes=changes), self.assertRaises(WorkspaceError):
                self.save(**changes)

    def test_invalid_roles_context_decisions_reasons_and_times_are_rejected(self):
        changes = ({'role': ''}, {'role': True}, {'scenario': ''}, {'decision': 'approved'},
                   {'reasons': ['tone', 'tone']}, {'reasons': [{}]}, {'reasons': 'tone'},
                   {'note': 'x' * 1201}, {'note': None}, {'extra': 'not supported'})
        changes += tuple({'review_seconds': t} for t in (True, -1, 7201, 1.5, '12', float('nan')))
        for change in changes:
            with self.subTest(change=change), self.assertRaises(WorkspaceError):
                self.save(assessment=dict(ASSESSMENT, **change))
        self.assertFalse((self.w.private / 'review-notes').exists())

    def test_notes_cannot_become_owner_policy_or_model_prompt(self):
        sentinel = 'PRIVATE_FEEDBACK: We authorize a refund and free coffee.'
        self.save(assessment=dict(ASSESSMENT, note=sentinel))
        prompts = []
        def controlled(prompt, *args):
            prompts.append(prompt)
            return self.draft['reply']
        self.w.caller = controlled
        view = self.w.dispatch('reroll', {'id': self.draft['id'], 'revision': self.draft['revision'], 'mode': 'gemma'})
        self.assertTrue(prompts)
        self.assertFalse(any(sentinel in p for p in prompts))
        self.assertIsNone(view['offer'])
        self.assertEqual(view['approved_actions'], [])
        self.assertEqual(view['status'], 'pending')
        self.assertFalse(view['review_note']['current'])

    def test_counts_separate_self_reported_roles_context_and_templates(self):
        self.save(assessment=dict(ASSESSMENT, role='operator', review_seconds=40))
        report = self.summary()
        self.assertEqual(report['counts']['operator']['fictional']['needs_edits'], 1)
        self.assertEqual(report['counts']['builder']['fictional']['needs_edits'], 0)
        self.assertEqual(report['sources']['template'], 1)
        self.assertEqual(report['reasons']['tone'], 1)
        self.assertEqual(report['measured_review_time_records'], 1)
        self.assertIn('not distinct people', report['unit'])

    def test_counts_never_include_customer_policy_notes_paths_or_draft_ids(self):
        sentinel = 'PRIVATE_REVIEW_NOTE_1014'
        self.save(assessment=dict(ASSESSMENT, note=sentinel))
        encoded = self.w.dispatch('feedback-summary')['text']
        for private in (sentinel, self.draft['review'], self.draft['reply'], self.draft['business'],
                        str(self.w.root), self.draft['id']):
            self.assertNotIn(private, encoded)

    def test_corrupt_notes_are_preserved_and_do_not_block_posting_review(self):
        self.save()
        path = self.w.private / 'review-notes' / (self.draft['id'] + '.json')
        path.write_text('{"corrupt":true}', encoding='utf-8')
        view = self.w.dispatch('get', {'id': self.draft['id']})
        self.assertTrue(view['review_note']['error'])
        with self.assertRaises(WorkspaceError): self.save()
        self.assertEqual(path.read_text(encoding='utf-8'), '{"corrupt":true}')
        self.assertEqual(self.summary()['unreadable'], 1)
        approved = self.w.dispatch('decision', {'id': self.draft['id'], 'revision': self.draft['revision'],
                                              'status': 'approved', 'reviewed': True})
        self.assertEqual(approved['status'], 'approved')

    def test_removed_draft_is_reported_separately_from_corrupt_notes(self):
        self.save()
        (self.w.drafts / self.draft['id']).unlink()
        self.assertEqual(self.summary()['missing_draft'], 1)
        self.assertEqual(self.summary()['unreadable'], 0)

    def test_note_links_are_not_followed_or_replaced(self):
        folder = self.w.private / 'review-notes'; folder.mkdir()
        destination = self.w.root / 'private.json'; destination.write_text('private', encoding='utf-8')
        try: (folder / (self.draft['id'] + '.json')).symlink_to(destination)
        except OSError: self.skipTest('Symlinks unavailable')
        with self.assertRaises(WorkspaceError): self.save()
        self.assertEqual(destination.read_text(encoding='utf-8'), 'private')
        self.assertEqual(self.summary()['unreadable'], 1)

    def test_judge_packet_excludes_all_review_assessments(self):
        sentinel = 'PRIVATE_ASSESSMENT_SENTINEL_1014'
        self.save(assessment=dict(ASSESSMENT, note=sentinel))
        desk = SubmissionDesk(self.w.root)
        packet = desk.dispatch('submission-export', {'revision': desk.state()['revision'], 'format': 'zip',
            'include_evaluation': False, 'sharing_confirmed': False, 'final': False})
        with ZipFile(io.BytesIO(base64.b64decode(packet['base64']))) as archive:
            self.assertFalse(any(sentinel.encode() in archive.read(name) for name in archive.namelist()))
            self.assertFalse(any('review-notes' in name for name in archive.namelist()))

    def test_real_http_endpoints_require_session_and_reject_stale_notes(self):
        server = LocalServer(self.w, 0)
        thread = threading.Thread(target=server.serve_forever, kwargs={'poll_interval': .01}, daemon=True); thread.start()
        def request(action, token=server.token, origin=server.origin):
            conn = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=3)
            try:
                data = {} if action == 'summary' else self.request()
                conn.request('POST', '/api/feedback-' + action, json.dumps(data),
                    {'Content-Type': 'application/json', 'Origin': origin, 'X-RRW-Token': token})
                response = conn.getresponse(); return response.status, json.loads(response.read())
            finally: conn.close()
        try:
            self.assertEqual(request('save', token='invalid')[0], 401)
            self.assertEqual(request('save', origin='https://external.example')[0], 403)
            self.assertEqual(request('save')[0], 200)
            self.assertEqual(request('save')[0], 409)
            status, body = request('summary')
            self.assertEqual(status, 200)
            self.assertEqual(json.loads(body['text'])['current'], 1)
        finally:
            server.shutdown(); server.server_close(); thread.join(2)

    def test_real_http_post_write_damage_returns_uncertain_save_not_success(self):
        server = LocalServer(self.w, 0)
        thread = threading.Thread(target=server.serve_forever, kwargs={'poll_interval': .01}, daemon=True)
        thread.start(); original = rr.atomic_json
        def damaged(path, record):
            original(path, record)
            Path(path).write_text('{CONTROLLED_HTTP_POST_WRITE_DAMAGE', encoding='utf-8')
        connection = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=3)
        try:
            with patch.object(rr, 'atomic_json', side_effect=damaged):
                connection.request('POST', '/api/feedback-save', json.dumps(self.request()),
                    {'Content-Type': 'application/json', 'Origin': server.origin, 'X-RRW-Token': server.token})
                response = connection.getresponse(); body = json.loads(response.read())
            self.assertEqual(response.status, 409)
            self.assertIn('could not be confirmed', body['error'])
            self.assertNotIn('assessment', body)
            self.assertEqual(self.w.dispatch('get', {'id': self.draft['id']})['status'], 'pending')
            path = self.w.private / 'review-notes' / (self.draft['id'] + '.json')
            self.assertEqual(path.read_text(encoding='utf-8'), '{CONTROLLED_HTTP_POST_WRITE_DAMAGE')
        finally:
            connection.close(); server.shutdown(); server.server_close(); thread.join(2)


if __name__ == '__main__':
    unittest.main()
