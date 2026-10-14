"""Launch a real server, complete a template reply and stop it. No model evidence.

Uses the Windows batch launcher on Windows; the Python setup launcher elsewhere.
No browser engine is involved. Session links and private paths are not printed.
"""
import http.client
import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import tempfile
import threading
import time
from urllib.parse import parse_qs, urlsplit

HERE = Path(__file__).resolve().parents[1]


def request(origin, token, action, data):
    conn = http.client.HTTPConnection(origin.hostname, origin.port, timeout=5)
    try:
        conn.request('POST', '/api/' + action, json.dumps(data),
                     {'Content-Type': 'application/json', 'Origin': origin.scheme + '://' + origin.netloc,
                      'X-RRW-Token': token})
        response = conn.getresponse()
        body = response.read()
        if response.status != 200:
            raise RuntimeError('Launcher smoke HTTP status: ' + str(response.status))
        return json.loads(body)
    finally:
        conn.close()


def main():
    with tempfile.TemporaryDirectory(prefix='rrw launch test ') as directory:
        command = (['cmd.exe', '/d', '/c', 'start_windows.bat'] if os.name == 'nt'
                   else [sys.executable, '-u', 'rrw_setup.py', '--launch'])
        command += ['--no-browser', '--data-dir', directory]
        lines = queue.Queue()
        process = subprocess.Popen(command, cwd=HERE, stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT, text=True, encoding='utf-8')

        def read_output():
            for line in process.stdout:
                lines.put(line.strip())
            lines.put(None)

        reader = threading.Thread(target=read_output, daemon=True)
        reader.start()
        try:
            deadline = time.monotonic() + 20
            origin = None
            while time.monotonic() < deadline:
                try:
                    line = lines.get(timeout=max(.01, deadline - time.monotonic()))
                except queue.Empty:
                    break
                if line is None:
                    raise RuntimeError('Launcher exited before serving a session')
                if line.startswith('http://127.0.0.1:') and '/#token=' in line:
                    origin = urlsplit(line)
                    break
            if origin is None:
                raise RuntimeError('Launcher did not serve a session within 20 seconds')
            token = parse_qs(origin.fragment)['token'][0]
            draft = request(origin, token, 'generate', {
                'business': 'Demo Cafe', 'review': 'Cold coffee and a 25 minute wait. Disappointing.',
                'stars': 2, 'mode': 'offline'})
            if draft['status'] != 'pending' or not draft['engine'].startswith('template'):
                raise RuntimeError('Expected a pending template draft')
            baseline = draft['reply']
            draft = request(origin, token, 'edit', {'id': draft['id'], 'revision': draft['revision'],
                                                  'reply': baseline + '\nThank you.'})
            if draft['reply_comparison']['baseline_reply'] != baseline or not draft['reply_comparison']['changed']:
                raise RuntimeError('Starting reply was not preserved across the edit')
            request(origin, token, 'feedback-save', {'id': draft['id'], 'revision': draft['revision'],
                'note_revision': 'new', 'assessment': {'role': 'demo', 'scenario': 'fictional',
                'decision': 'needs_edits', 'reasons': ['tone'], 'note': 'SYNTHETIC_LAUNCHER_NOTE', 'review_seconds': None}})
            counts = request(origin, token, 'feedback-summary', {})['text']
            if (json.loads(counts)['counts']['demo']['fictional']['needs_edits'] != 1
                    or 'SYNTHETIC_LAUNCHER_NOTE' in counts or baseline in counts):
                raise RuntimeError('Expected anonymous draft counts without notes or reply text')
            draft = request(origin, token, 'decision', {'id': draft['id'], 'revision': draft['revision'],
                                                      'status': 'approved', 'reviewed': True})
            exported = request(origin, token, 'approved-text', {'id': draft['id'], 'revision': draft['revision']})
            if exported['text'] != draft['reply']:
                raise RuntimeError('Approved export differs from the reviewed draft')
            pending_edit = draft['reply'] + '\nPending private edit.'
            copy_state = request(origin, token, 'recovery-get', {})
            saved_copy = request(origin, token, 'recovery-save', {'revision': copy_state['revision'], 'payload': {
                'inputs': {'business': 'Demo Cafe', 'kind': 'cafe', 'tone': 'professional', 'platform': 'google',
                           'offer': '', 'signoff': '', 'approved_actions': [], 'review': 'Cold coffee.',
                           'stars': 2, 'followup': False, 'original': '', 'previous': '', 'mode': 'gemma'},
                'editor': {'id': draft['id'], 'revision': draft['revision'], 'reply': pending_edit}}})
            recovered = request(origin, token, 'recovery-get', {})
            if (recovered['payload']['editor']['reply'] != pending_edit or recovered['editor_state'] != 'current'
                    or recovered['payload']['inputs']['mode'] != 'offline'
                    or 'policy_confirmed' in recovered['payload']['inputs']):
                raise RuntimeError('Working copy recovery changed text or retained authorization')
            still_approved = request(origin, token, 'approved-text', {'id': draft['id'], 'revision': draft['revision']})
            if still_approved['text'] != draft['reply']:
                raise RuntimeError('Saving a recovery copy modified the approved draft')
            cleared = request(origin, token, 'recovery-clear', {'revision': saved_copy['revision']})
            if cleared['available'] or cleared['revision'] == 'new':
                raise RuntimeError('Clearing a working copy did not retain its revision tombstone')
            print(json.dumps({'launcher': 'windows-batch' if os.name == 'nt' else 'python-setup',
                              'storage_path_with_spaces': True, 'free_port': True,
                              'template_draft_approval_export': True, 'comparison_and_private_notes': True,
                              'private_working_copy': True, 'model_calls': 0}))
        finally:
            if process.poll() is None:
                if os.name == 'nt':
                    subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                   timeout=10, check=False)
                else:
                    process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
            reader.join(timeout=2)
            process.stdout.close()


if __name__ == '__main__':
    main()
