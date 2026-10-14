"""Submission handoff boundaries. Test confirmations are synthetic, not user evidence."""
import base64
import contextlib
import copy
import hashlib
import http.client
import io
import json
from pathlib import Path
import shutil
import tempfile
import threading
import unittest
from unittest.mock import patch
from zipfile import ZipFile

import check_submission
import rrw_evaluate as quality
from rrw_submission import (SubmissionDesk, HERE, REFERENCE, CONFIRMATIONS, SCHEMA,
                            default_values, exhibit, make_packet, public_demo_url, main)
from rrw_web import LocalServer
from rrw_workspace import Workspace, WorkspaceError


class PublicDemoLinkTests(unittest.TestCase):
    def test_video_links_accepted_without_fetching(self):
        for url in ('https://www.youtube.com/watch?v=abc123', 'https://vimeo.com/123456',
                    'https://nolankido.com/review-reply-writer/', 'https://youtu.be/abc?t=12'):
            self.assertEqual(public_demo_url(url), url)

    def test_unsafe_local_private_and_placeholder_links_rejected(self):
        for url in ('http://youtube.com/watch', 'https://127.0.0.1/x', 'https://[::1]/x',
                    'https://127.1/x', 'https://2130706433/x', 'https://localhost/x',
                    'https://foo.local/x', 'https://a.example.com/x', 'https://foo.test/',
                    'https://user:password@youtube.com/x', 'https://youtube.com:8765/x',
                    'https://github.com/nolankido/reviewReplyWriter/actions/runs/123',
                    'https://sdmntprwestus.oaiusercontent.com/path',
                    'https://youtu.be/x?token=private', 'https://youtu.be/x?X-Amz-Signature=abc',
                    'https://youtu.be/x#token=123', ' https://youtu.be/x',
                    'https://youtu.be/x\nhello', 'https://youtu.be/%0ax',
                    'https://youtu.be/x"><script>', 'https://youtu.be/x\\evil'):
            with self.subTest(url=url), self.assertRaises(WorkspaceError): public_demo_url(url)

    def test_markdown_parentheses_encoded_and_idempotent(self):
        url=public_demo_url('https://nolankido.com/demo(a)?v=(b)')
        self.assertNotIn('(',url);self.assertEqual(public_demo_url(url),url)

    def test_blank_is_allowed_but_types_and_size_are_not(self):
        self.assertEqual(public_demo_url(''),'')
        for value in (None, True, [], 'x'*2049):
            with self.assertRaises(WorkspaceError):public_demo_url(value)


class SubmissionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.desk=SubmissionDesk(self.root)
    def tearDown(self):self.temp.cleanup()
    def save(self,view=None,**changes):
        view=view or self.desk.state();values=dict(view['values']);values.update(changes)
        return self.desk.dispatch('submission-save',{'revision':view['revision'],'values':values})
    def export(self, view=None, **changes):
        view=view or self.desk.state()
        data=dict(revision=view['revision'],format='zip',include_evaluation=False,sharing_confirmed=False,final=False)
        data.update(changes);return self.desk.dispatch('submission-export',data)
    def local_report(self, assessed=False):
        # Retained actual record is copied only inside a temporary test workspace.
        # Synthetic assessments below never modify the retained file or author state.
        report=quality.load_report(HERE/REFERENCE)
        if assessed:
            for row in report['results']:
                row['human_review']={'result_sha256':row['result_sha256'],'decision':'needs_edit',
                  'issues':['too_generic'],'notes':'Synthetic unit-test assessment, not operator feedback.'}
            report['sha256']=quality.digest({k:v for k,v in report.items() if k!='sha256'})
        folder=self.root/'.rrw'/'evaluations';folder.mkdir(parents=True,exist_ok=True)
        path=folder/(report['id']+'.json');path.write_text(json.dumps(report),encoding='utf-8')
        return report,path
    def ready_view(self):
        report,_=self.local_report(True)
        view=self.save(demo_url='https://youtu.be/unit-test-not-real',evaluation_id=report['id'])
        return self.save(view,**{key:True for key in CONFIRMATIONS})

    def test_empty_state_has_no_confirmations_and_does_not_write(self):
        view=self.desk.state()
        self.assertFalse(view['preflight_ready']);self.assertFalse(view['published'])
        self.assertTrue(all(view['values'][k] is False for k in CONFIRMATIONS))
        self.assertFalse(self.desk.path.exists());self.assertIn('TODO',view['post'])

    def test_existing_live_evidence_matches_unchanged_engine(self):
        view=self.desk.state();self.assertTrue(view['reference_sources_current'])
        self.assertEqual(view['reference_summary']['genuine_model_drafts'],3)
        self.assertEqual(view['reference_summary']['human_reviewed'],0)

    def test_state_is_private_and_repository_checklist_is_not_changed(self):
        before=(HERE/'docs/submission_evidence.json').read_bytes()
        view=self.save(demo_url='https://youtu.be/test')
        self.assertTrue(self.desk.path.is_file());self.assertEqual(self.desk.path.parent.name,'.rrw')
        self.assertEqual((HERE/'docs/submission_evidence.json').read_bytes(),before)
        self.assertFalse(view['values']['demo_accessible_to_judges'])

    def test_string_boolean_and_unknown_keys_rejected_without_write(self):
        for patch_values in ({'rules_reviewed':'true'},{'fresh_gemma_run_recorded':True},{'demo_url':None}):
            with self.subTest(values=patch_values),self.assertRaises(WorkspaceError):self.save(**patch_values)
        self.assertFalse(self.desk.path.exists())

    def test_changed_demo_invalidates_access_even_if_request_sets_true(self):
        view=self.save(demo_url='https://youtu.be/one',demo_accessible_to_judges=True)
        self.assertFalse(view['values']['demo_accessible_to_judges'])
        view=self.save(view,demo_accessible_to_judges=True)
        self.assertTrue(view['values']['demo_accessible_to_judges'])
        view=self.save(view,demo_url='https://youtu.be/two',demo_accessible_to_judges=True)
        self.assertFalse(view['values']['demo_accessible_to_judges'])

    def test_stale_save_and_export_refused(self):
        view=self.desk.state();self.save(view,rules_reviewed=True)
        with self.assertRaises(WorkspaceError) as caught:self.save(view,development_window_confirmed=True)
        self.assertEqual(caught.exception.status,409)
        with self.assertRaises(WorkspaceError):self.export(view)

    def test_corrupt_state_is_preserved(self):
        self.desk.path.parent.mkdir();self.desk.path.write_text('{broken',encoding='utf-8')
        with self.assertRaises(ValueError):self.desk.state()
        self.assertEqual(self.desk.path.read_text(),'{broken')

    def test_duplicate_or_oversized_state_rejected(self):
        self.desk.path.parent.mkdir();self.desk.path.write_text('{"schema":"a","schema":"b"}')
        with self.assertRaises(ValueError):self.desk.state()
        self.desk.path.write_text('x'*32769)
        with self.assertRaises(WorkspaceError):self.desk.state()

    def test_failed_atomic_write_keeps_previous_state(self):
        view=self.save(rules_reviewed=True);before=self.desk.path.read_bytes()
        with patch('review_reply.os.replace',side_effect=OSError('disk full')):
            with self.assertRaises(OSError):self.save(view,development_window_confirmed=True)
        self.assertEqual(self.desk.path.read_bytes(),before)

    def test_state_survives_restarting_desk(self):
        view=self.save(rules_reviewed=True)
        self.assertEqual(SubmissionDesk(self.root).state()['revision'],view['revision'])

    def test_source_change_clears_claims_confirmation_and_stale_revision(self):
        view=self.save(firsthand_claims_reviewed=True)
        with patch('rrw_submission.source_snapshot',return_value={'changed':'version'}):
            updated=self.desk.state();self.assertFalse(updated['values']['firsthand_claims_reviewed'])
            self.assertFalse(updated['reference_sources_current'])
            with self.assertRaises(WorkspaceError):self.export(view)

    def test_traversal_and_unknown_actions_rejected(self):
        for path in ('../../profiles','/etc/passwd','eval-'+'a'*32+'/x'):
            with self.assertRaises(WorkspaceError):self.save(evaluation_id=path)
        with self.assertRaises(WorkspaceError):self.desk.dispatch('submission-delete',{})
        with self.assertRaises(WorkspaceError):self.desk.dispatch('submission-save',[])

    def test_symlink_state_and_evaluation_are_rejected(self):
        self.desk.path.parent.mkdir();outside=self.root/'other.json';outside.write_text('{}')
        try:self.desk.path.symlink_to(outside)
        except OSError:self.skipTest('Symlinks unavailable to this test account')
        with self.assertRaises(WorkspaceError):self.desk.state()
        self.desk.path.unlink()
        folder=self.root/'.rrw'/'evaluations';folder.mkdir()
        name='eval-'+'a'*32;(folder/(name+'.json')).symlink_to(outside)
        with self.assertRaises(WorkspaceError):self.save(evaluation_id=name)
        self.assertEqual(outside.read_text(),'{}')

    def test_selected_unassessed_report_does_not_qualify(self):
        report,_=self.local_report();view=self.save(evaluation_id=report['id'])
        self.assertIn('Human assessment', ' '.join(view['internal_blockers']))
        self.assertEqual(view['selected_summary']['human_reviewed'],0)

    def test_changed_assessment_invalidates_export_revision(self):
        report,path=self.local_report();view=self.save(evaluation_id=report['id'])
        self.local_report(True)
        with self.assertRaises(WorkspaceError):self.export(view)

    def test_invalid_report_is_visible_without_overwriting_it(self):
        name='eval-'+'a'*32;folder=self.root/'.rrw'/'evaluations';folder.mkdir(parents=True)
        path=folder/(name+'.json');path.write_text('{broken')
        view=self.save(evaluation_id=name)
        self.assertIn('unreadable',view['evaluation_options'][0]['label'])
        self.assertIsNone(view['selected_summary']);self.assertEqual(path.read_text(),'{broken')

    def test_preflight_complete_does_not_claim_publication_or_verify_links(self):
        view=self.ready_view();self.assertTrue(view['preflight_ready']);self.assertFalse(view['published'])
        self.assertIn('Not performed',view['external_checks'])
        self.assertIn('published: false',view['post']);self.assertNotIn('TODO',view['post'])

    def test_final_export_rejects_missing_evidence_and_forged_flags(self):
        with self.assertRaises(WorkspaceError):self.export(final=True)
        with self.assertRaises(WorkspaceError):self.export(include_evaluation='true')
        view=self.ready_view()
        with self.assertRaises(WorkspaceError):self.export(view,final=True)
        exported=self.export(view,final=True,include_evaluation=True,sharing_confirmed=True)
        with ZipFile(io.BytesIO(base64.b64decode(exported['base64']))) as z:
            self.assertIn('evidence/selected-evaluation.json',z.namelist())
            self.assertFalse(json.loads(z.read('READINESS.json'))['published'])

    def test_working_packet_excludes_customer_data_profiles_and_notes(self):
        report,_=self.local_report(True);view=self.save(evaluation_id=report['id'])
        (self.root/'.env').write_text('SECRET_ENV_MARKER');(self.root/'replies').mkdir()
        (self.root/'replies'/'customer.md').write_text('PRIVATE_CUSTOMER_MARKER')
        (self.root/'.rrw'/'profiles.json').write_text('SECRET_POLICY_MARKER')
        exported=self.export(view)
        with ZipFile(io.BytesIO(base64.b64decode(exported['base64']))) as z:
            contents=b'\n'.join(z.read(n) for n in z.namelist())
            for needle in (b'SECRET_',b'PRIVATE_CUSTOMER_MARKER',b'Synthetic unit-test assessment'):
                self.assertNotIn(needle,contents)
            self.assertNotIn('evidence/selected-evaluation.json',z.namelist())
            self.assertIn(b'TODO',z.read('DEV_SUBMISSION_DRAFT.md'))

    def test_explicit_note_export_requires_per_export_consent(self):
        report,_=self.local_report(True);view=self.save(evaluation_id=report['id'])
        with self.assertRaises(WorkspaceError):self.export(view,include_evaluation=True)
        result=self.export(view,include_evaluation=True,sharing_confirmed=True)
        with ZipFile(io.BytesIO(base64.b64decode(result['base64']))) as z:
            self.assertIn(b'Synthetic unit-test assessment',z.read('evidence/selected-evaluation.json'))

    def test_manifest_covers_all_payloads_and_portable_links(self):
        result=self.export()
        with ZipFile(io.BytesIO(base64.b64decode(result['base64']))) as z:
            manifest=json.loads(z.read('MANIFEST.json'))['files']
            self.assertEqual(set(z.namelist())-{'MANIFEST.json'},set(manifest))
            for name,info in manifest.items():self.assertEqual(hashlib.sha256(z.read(name)).hexdigest(),info['sha256'])
            self.assertEqual(json.loads(z.read(REFERENCE)),json.loads(z.read('evidence/recorded-smoke.json')))
            self.assertNotIn(b'<script',z.read('START_HERE.html'))

    def test_static_guide_escapes_hostile_recorded_text(self):
        view=self.desk.state();report=quality.load_report(HERE/REFERENCE)
        report['results'][0]['reply']='<script>window.pwned=1</script>'
        rendered=exhibit(view,report)
        self.assertNotIn('<script>',rendered);self.assertIn('&lt;script&gt;',rendered)

    def test_article_markers_required_not_silently_ignored(self):
        from rrw_submission import render_post
        for template in ('published: false','<!-- RRW:NOTICE:END --><!-- RRW:NOTICE:START -->'):
            with self.assertRaises(WorkspaceError):render_post(template,default_values(),[])

    def test_packet_command_adds_only_explicit_mp4_and_never_overwrites(self):
        mp4=self.root/'demo.mp4';mp4.write_bytes(b'\0\0\0\x20ftypisom'+b'x'*30)
        output=self.root/'packet.zip'
        with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main(['--data-dir',str(self.root),'--output',str(output),'--video',str(mp4)]),0)
            before=output.read_bytes()
            self.assertEqual(main(['--data-dir',str(self.root),'--output',str(output)]),1)
        self.assertEqual(output.read_bytes(),before)
        with ZipFile(output) as z:self.assertEqual(z.read('assets/demo.mp4'),mp4.read_bytes())

    def test_wrong_video_format_rejected(self):
        view,_,reference,_=self.desk._snapshot()
        with self.assertRaises(WorkspaceError):make_packet(view,reference,video_bytes=b'Not an MP4')

    def test_generated_evidence_works_with_separate_checker_paths(self):
        view=self.ready_view();result=self.export(view,include_evaluation=True,sharing_confirmed=True)
        folder=self.root/'packet'
        with ZipFile(io.BytesIO(base64.b64decode(result['base64']))) as z:z.extractall(folder)
        with patch.object(check_submission,'suite_state',return_value=(999,True)),contextlib.redirect_stdout(io.StringIO()):
            code=check_submission.main(['--release','--evidence',str(folder/'submission_evidence.json'),
                                        '--post',str(folder/'DEV_SUBMISSION_DRAFT.md')])
        self.assertEqual(code,0)


class SubmissionHttpTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.server=LocalServer(Workspace(self.temp.name),0)
        self.thread=threading.Thread(target=self.server.serve_forever,kwargs={'poll_interval':.01},daemon=True);self.thread.start()
    def tearDown(self):
        self.server.shutdown();self.server.server_close();self.thread.join(2);self.temp.cleanup()
    def request(self,action,data,token=True,origin=None):
        conn=http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=5)
        headers={'Content-Type':'application/json','Origin':origin or self.server.origin}
        if token:headers['X-RRW-Token']=self.server.token
        try:
            conn.request('POST','/api/submission-'+action,json.dumps(data),headers)
            response=conn.getresponse();return response.status,json.loads(response.read())
        finally:conn.close()
    def test_capability_required_for_checklist_and_export(self):
        for action in ('state','save','export'):self.assertEqual(self.request(action,{},token=False)[0],401)
    def test_cross_origin_save_forbidden(self):
        self.assertEqual(self.request('save',{},origin='https://attacker.invalid')[0],403)
    def test_get_and_save_roundtrip_and_stale_conflict(self):
        status,state=self.request('state',{});self.assertEqual(status,200)
        data={'revision':state['revision'],'values':state['values']};data['values']['rules_reviewed']=True
        self.assertEqual(self.request('save',data)[0],200);self.assertEqual(self.request('save',data)[0],409)
    def test_export_missing_confirmation_is_blocked(self):
        _,state=self.request('state',{})
        code,_=self.request('export',{'revision':state['revision'],'format':'zip','include_evaluation':False,'sharing_confirmed':False,'final':True})
        self.assertEqual(code,422)


if __name__=='__main__':unittest.main()
