"""Real CLI backup/recovery and a recovered launcher over HTTP. Fictional fixtures only."""
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
sys.path.insert(0, str(HERE))
from rrw_workspace import Workspace
from rrw_backup import inventory


def main():
    with tempfile.TemporaryDirectory(prefix='rrw private backup smoke ') as directory:
        base = Path(directory); source = base / 'source work'; restored = base / 'recovered work'
        archive = base / 'private.rrw-backup.zip'
        workspace = Workspace(source)
        view = workspace.dispatch('generate', {'business': 'Demo Cafe', 'review': 'Cold coffee and a 25 minute wait.',
                                              'stars': 2, 'mode': 'offline'})
        ref = {'id': view['id'], 'revision': view['revision']}
        workspace.dispatch('decision', dict(ref, status='approved', reviewed=True))
        original_work = {name: (source / name).read_bytes() for name in inventory(source)}
        for arguments in (['create', '--data-dir', str(source), '--output', str(archive), '--confirm-private'],
                          ['inspect', '--archive', str(archive)],
                          ['recover', '--archive', str(archive), '--destination', str(restored), '--confirm-private']):
            result = subprocess.run([sys.executable, str(HERE / 'rrw_backup.py'), *arguments],
                                    capture_output=True, text=True, timeout=15)
            if result.returncode != 0 or not json.loads(result.stdout)['private']:
                raise RuntimeError('Controlled backup CLI failed')
        command = (['cmd.exe', '/d', '/c', 'start_windows.bat'] if os.name == 'nt'
                   else [sys.executable, '-u', 'rrw_setup.py', '--launch'])
        command += ['--no-browser', '--data-dir', str(restored)]
        lines = queue.Queue()
        process = subprocess.Popen(command, cwd=HERE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                   text=True, encoding='utf-8')
        def read_output():
            for line in process.stdout: lines.put(line.strip())
            lines.put(None)
        reader = threading.Thread(target=read_output, daemon=True); reader.start()
        try:
            origin = None; deadline = time.monotonic() + 20
            while time.monotonic() < deadline:
                try: line = lines.get(timeout=max(.01, deadline - time.monotonic()))
                except queue.Empty: break
                if line is None: break
                if line.startswith('http://127.0.0.1:') and '/#token=' in line:
                    origin = urlsplit(line); break
            if origin is None: raise RuntimeError('Recovered launcher did not serve within 20 seconds')
            token = parse_qs(origin.fragment)['token'][0]
            def request(action, data):
                connection = http.client.HTTPConnection(origin.hostname, origin.port, timeout=5)
                try:
                    connection.request('POST', '/api/' + action, json.dumps(data),
                        {'Content-Type': 'application/json', 'Origin': origin.scheme + '://' + origin.netloc,
                         'X-RRW-Token': token})
                    response = connection.getresponse()
                    return response.status, json.loads(response.read())
                finally: connection.close()
            status, recovered = request('get', {'id': view['id']})
            if status != 200 or recovered['status'] != 'pending' or recovered['reply'] != view['reply']:
                raise RuntimeError('Recovered reply changed or regained approval')
            if request('approved-text', ref)[0] != 409:
                raise RuntimeError('Recovered copy bypassed approval')
            if request('decision', dict(ref, status='approved', reviewed=False))[0] != 400:
                raise RuntimeError('Recovered approval did not require explicit human-review confirmation')
            if request('decision', dict(ref, status='approved', reviewed=True))[0] != 200:
                raise RuntimeError('Controlled reviewed approval failed')
            status, copied = request('approved-text', ref)
            if status != 200 or copied['text'] != view['reply']:
                raise RuntimeError('Controlled approved export did not match')
            if workspace.dispatch('get', {'id': view['id']})['status'] != 'approved':
                raise RuntimeError('Original workspace was changed')
            if any((source / name).read_bytes() != data for name, data in original_work.items()):
                raise RuntimeError('Original saved review-work bytes changed')
            print(json.dumps({'private_backup_cli': True, 'recovered_launcher_http': True,
                'original_workspace_preserved': True, 'restored_approval_reset': True,
                'explicit_review_approval_export': True, 'paths_with_spaces': True,
                'launcher': 'windows-batch' if os.name == 'nt' else 'python-setup',
                'browser_navigation': False, 'model_calls': 0}))
        finally:
            if process.poll() is None:
                if os.name == 'nt':
                    subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10, check=False)
                else: process.terminate()
                try: process.wait(timeout=10)
                except subprocess.TimeoutExpired: process.kill(); process.wait(timeout=5)
            reader.join(timeout=2); process.stdout.close()


if __name__ == '__main__':
    main()
