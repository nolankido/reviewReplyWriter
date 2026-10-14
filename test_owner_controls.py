"""Owner editorial choices and private manual-handling boundaries."""
import base64
import io
import http.client
import json
import random
import tempfile
import threading
import unittest
from pathlib import Path
from zipfile import ZipFile

import review_reply as rr
from rrw_workspace import Workspace, WorkspaceError
from rrw_submission import SubmissionDesk
from rrw_web import LocalServer
from test_review_inbox import SETTINGS


class EditorialChoiceTests(unittest.TestCase):
    def test_complete_short_positive_reply_needs_no_invitation(self):
        reply = 'Thank you for your kind words about the coffee at Demo Cafe.\n\n- The Demo Cafe team'
        for platform in rr.PLATFORMS:
            self.assertEqual(rr.reply_gaps(reply, 'Great coffee.', 'Demo Cafe', 5, platform=platform), [])

    def test_short_negative_reply_keeps_its_essential_details(self):
        reply = 'Thank you for reviewing Demo Cafe. We are sorry about the cold coffee you described.\n\n- The Demo Cafe team'
        self.assertEqual(rr.reply_gaps(reply, 'Cold coffee.', 'Demo Cafe', 1, platform='airbnb'), [])
        self.assertIn('an apology', rr.reply_gaps(reply.replace('We are sorry about', 'We noticed'), 'Cold coffee.', 'Demo Cafe', 1))

    def test_unapproved_refund_still_fails_in_a_short_reply(self):
        reply = 'Thank you for reviewing Demo Cafe. Sorry about cold coffee. We will refund you.'
        self.assertTrue(any('policy:' in f for f in rr.reply_gaps(reply, 'Cold coffee.', 'Demo Cafe', 1)))

    def test_specificity_and_exact_wait_are_still_required(self):
        reply = 'Thank you for reviewing Demo Cafe. We are sorry about your experience.'
        gaps = rr.reply_gaps(reply, 'Cold coffee and a 25 minute wait.', 'Demo Cafe', 1)
        self.assertTrue(any('specific detail' in f for f in gaps))
        self.assertTrue(any('25 minute' in f for f in gaps))

    def test_followup_does_not_require_an_invitation_or_filler(self):
        reply = 'Thank you for the update about Demo Cafe. We are sorry the coffee was still cold.\n\n- The Demo Cafe team'
        self.assertEqual(rr.followup_gaps(reply, 'Cold coffee.', 'We are sorry about coffee.',
            'Update: the coffee was still cold.', 'Demo Cafe', platform='airbnb'), [])

    def test_templates_have_no_forced_closing_or_padding(self):
        reply = rr.template_reply('Great coffee.', 'Demo Cafe', 'professional', 5,
                                  'cafe', random.Random(0), platform='airbnb')
        self.assertNotIn('hope', reply.lower())
        self.assertNotIn('perspective', reply.lower())
        self.assertLess(len(reply.split()), 35)
        self.assertEqual(rr.reply_gaps(reply, 'Great coffee.', 'Demo Cafe', 5, platform='airbnb'), [])

    def test_warm_does_not_impose_a_regional_greeting(self):
        reply = rr.template_reply('Great coffee.', 'Demo Cafe', 'warm', 5, 'cafe', random.Random(0))
        self.assertTrue(reply.startswith('Thanks'))
        self.assertNotIn('Mahalo', reply)

    def test_prompts_keep_caps_and_make_invitation_optional(self):
        first = rr.build_prompt('Cold coffee.', 'Demo Cafe', 'professional', 1, 'cafe', platform='airbnb')
        followup = rr.build_followup_prompt('Cold coffee.', 'Sorry about coffee.',
            'Update: coffee was still cold.', 'Demo Cafe', 'professional', 'cafe', platform='airbnb')
        for prompt in (first, followup):
            self.assertIn('at most 220 words', prompt)
            self.assertIn('No minimum length', prompt)
            self.assertIn('invitation is optional', prompt)
            self.assertNotIn('50 to 220 words', prompt)

    def test_retired_style_ledger_rules_do_not_come_back_in_coaching(self):
        with tempfile.TemporaryDirectory() as root:
            path = str(Path(root) / 'ledger.json')
            rr.atomic_json(path, {'Demo Cafe': {'a closing invitation': 20, 'enough substance': 18, 'an apology': 2}})
            self.assertEqual(rr.top_gaps('Demo Cafe', path), ['an apology'])
            self.assertIn('a closing invitation', rr.load_ledger(path)['Demo Cafe'])


class PrivateHandlingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.w = Workspace(self.temp.name)
        data = {'csv': 'review,stars\n"The cafe exposed my private information.",5\nGreat coffee.,5\n', 'settings': SETTINGS}
        preview = self.w.dispatch('inbox-preview', data)
        self.inbox = self.w.dispatch('inbox-create', dict(data, preview_revision=preview['revision'], confirmed=True))

    def tearDown(self):
        self.temp.cleanup()

    def note(self, **changes):
        data = {'id': self.inbox['id'], 'revision': self.inbox['revision'],
                'row_id': self.inbox['rows'][0]['id'], 'note': 'Synthetic private test note.', 'handled': True}
        data.update(changes)
        return self.w.dispatch('inbox-note', data)

    def test_handled_is_private_tracking_not_generation_or_approval(self):
        saved = self.note()
        self.assertEqual(saved['counts']['manual_handled'], 1)
        self.assertEqual(saved['counts']['manual_open'], 0)
        self.assertEqual(saved['rows'][0]['status'], 'manual')
        self.assertNotIn('draft_id', saved['rows'][0])
        self.assertEqual(self.w.dispatch('state')['drafts'], [])
        with self.assertRaises(WorkspaceError):
            self.w.dispatch('inbox-retry', {'id': saved['id'], 'revision': saved['revision'], 'row_id': saved['rows'][0]['id']})

    def test_note_can_be_reopened_and_handling_reopened_explicitly(self):
        saved = self.note(note='Synthetic note: reviewed personally.')
        reopened = Workspace(self.temp.name).dispatch('inbox-get', {'id': saved['id']})
        self.assertEqual(reopened['rows'][0]['handling_note'], 'Synthetic note: reviewed personally.')
        self.inbox = reopened
        revised = self.note(handled=False, note='Further personal work remains.')
        self.assertEqual(revised['counts']['manual_open'], 1)

    def test_missing_note_or_non_boolean_handled_is_rejected(self):
        for values in ({'note': ''}, {'handled': 'yes'}, {'handled': None}, {'note': 'x' * 1201}):
            with self.assertRaises(WorkspaceError):
                self.note(**values)

    def test_notes_require_a_current_revision_and_a_manual_row(self):
        self.note()
        with self.assertRaises(WorkspaceError): self.note()
        with self.assertRaises(WorkspaceError): self.note(revision=None)
        current = self.w.dispatch('inbox-get', {'id': self.inbox['id']})
        with self.assertRaises(WorkspaceError):
            self.note(revision=current['revision'], row_id=current['rows'][1]['id'])

    def test_note_promises_do_not_become_owner_policy_or_other_draft_context(self):
        saved = self.note(note='PRIVATE_NOTE: We authorize a refund and free coffee.')
        result = self.w.dispatch('inbox-step', {'id': saved['id'], 'revision': saved['revision'], 'mode': 'offline'})
        row = next(r for r in result['rows'] if r.get('draft_id'))
        draft = self.w.dispatch('get', {'id': row['draft_id']})
        self.assertIsNone(draft['offer'])
        self.assertEqual(draft['approved_actions'], [])
        self.assertNotIn('PRIVATE_NOTE', draft['reply'])
        self.assertNotIn('refund', draft['reply'].lower())

    def test_judge_export_excludes_private_handling_notes(self):
        sentinel = 'PRIVATE_HANDLING_SENTINEL_1014'
        self.note(note=sentinel)
        desk = SubmissionDesk(Path(self.temp.name))
        state = desk.state()
        result = desk.dispatch('submission-export', {'revision': state['revision'], 'format': 'zip',
            'include_evaluation': False, 'sharing_confirmed': False, 'final': False})
        with ZipFile(io.BytesIO(base64.b64decode(result['base64']))) as archive:
            self.assertFalse(any(sentinel.encode() in archive.read(name) for name in archive.namelist()))

    def test_real_http_note_endpoint_keeps_the_row_manual_and_blocks_stale_updates(self):
        server = LocalServer(self.w, 0)
        thread = threading.Thread(target=server.serve_forever, kwargs={'poll_interval': .01}, daemon=True)
        thread.start()
        data = {'id': self.inbox['id'], 'revision': self.inbox['revision'],
                'row_id': self.inbox['rows'][0]['id'], 'note': 'Synthetic HTTP test note.', 'handled': True}
        def request():
            conn = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=3)
            try:
                conn.request('POST', '/api/inbox-note', json.dumps(data),
                    {'Content-Type': 'application/json', 'Origin': server.origin, 'X-RRW-Token': server.token})
                response = conn.getresponse()
                return response.status, json.loads(response.read())
            finally:
                conn.close()
        try:
            code, result = request()
            self.assertEqual(code, 200)
            self.assertEqual(result['rows'][0]['status'], 'manual')
            self.assertNotIn('draft_id', result['rows'][0])
            self.assertEqual(request()[0], 409)
        finally:
            server.shutdown(); server.server_close(); thread.join(2)


if __name__ == '__main__':
    unittest.main()
