"""Loopback API boundaries also cover all evaluation data and mutations."""
import http.client
import json
import tempfile
import threading
import unittest

from rrw_workspace import Workspace
from rrw_web import LocalServer


class EvaluationHttpTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.server = LocalServer(Workspace(self.temp.name), 0)
        self.thread = threading.Thread(target=self.server.serve_forever,
            kwargs={'poll_interval':.01}, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown(); self.server.server_close(); self.thread.join(2)
        self.temp.cleanup()

    def request(self, action, payload, token=True, origin=None):
        conn = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=5)
        headers={'Content-Type':'application/json', 'Origin':origin or self.server.origin}
        if token: headers['X-RRW-Token']=self.server.token
        try:
            conn.request('POST', '/api/quality-'+action, json.dumps(payload), headers)
            response=conn.getresponse()
            return response.status, json.loads(response.read())
        finally: conn.close()

    def test_evidence_reads_require_session_capability(self):
        for action in ('list','get','export','diagnostics'):
            self.assertEqual(self.request(action, {}, token=False)[0], 401)

    def test_cross_origin_cannot_start_evaluation(self):
        self.assertEqual(self.request('start', {'mode':'offline'}, origin='https://attacker.test')[0], 403)

    def test_run_result_export_roundtrip(self):
        status, report=self.request('start', {'mode':'offline'})
        self.assertEqual(status,200)
        status, report=self.request('step', {'id':report['id'], 'revision':report['revision']})
        self.assertEqual(status,200); self.assertEqual(report['summary']['template'],1)
        status, exported=self.request('export', {'id':report['id'], 'revision':report['revision'], 'format':'json'})
        self.assertEqual(status,200); self.assertEqual(json.loads(exported['text'])['execution'],'templates')

    def test_stale_mutation_gets_conflict(self):
        _, report=self.request('start', {'mode':'offline'})
        ref={'id':report['id'], 'revision':report['revision']}
        self.assertEqual(self.request('step', ref)[0],200)
        self.assertEqual(self.request('step', ref)[0],409)

    def test_api_does_not_accept_custom_fixture_or_endpoint(self):
        _, report=self.request('start', {'mode':'offline', 'endpoint':'https://evil.test',
            'cases':[{'review':'private customer data'}]})
        self.assertEqual(len(report['cases']),3)
        self.assertNotIn('private customer data', json.dumps(report))
        self.assertEqual(self.request('get', {'id':'../../profiles'})[0],400)


if __name__=='__main__': unittest.main()
