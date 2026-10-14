#!/usr/bin/env python3
"""Launch the single-owner browser workspace: python rrw_web.py.

Loopback only, per-run capability token, exact Host/Origin checks, no CORS,
no arbitrary file serving. This is not an internet-facing application server.
"""
from __future__ import annotations

import argparse
import hmac
import json
import os
import secrets
import socket
import sys
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from reply_safety import DraftBlocked
from rrw_workspace import Workspace, WorkspaceError, model_status

HERE = Path(__file__).resolve().parent
MAX_BODY = 128 * 1024
ASSETS = {'/': ('index.html', 'text/html; charset=utf-8'),
          '/app.js': ('app.js', 'text/javascript; charset=utf-8'),
          '/style.css': ('style.css', 'text/css; charset=utf-8'),
          '/review-evidence.js': ('review-evidence.js', 'text/javascript; charset=utf-8'),
          '/review-evidence.css': ('review-evidence.css', 'text/css; charset=utf-8'),
          '/inbox.js': ('inbox.js', 'text/javascript; charset=utf-8'),
          '/inbox.css': ('inbox.css', 'text/css; charset=utf-8'),
          '/inbox-sample.csv': ('inbox-sample.csv', 'text/csv; charset=utf-8'),
          '/submission.js': ('submission.js', 'text/javascript; charset=utf-8')}
ASSETS['/feedback.js'] = ('feedback.js', 'text/javascript; charset=utf-8')
ASSETS['/recovery.js'] = ('recovery.js', 'text/javascript; charset=utf-8')
ASSETS['/connection.js'] = ('connection.js', 'text/javascript; charset=utf-8')
ASSETS['/generation.js'] = ('generation.js', 'text/javascript; charset=utf-8')
ASSETS['/save-recovery.js'] = ('save-recovery.js', 'text/javascript; charset=utf-8')
ASSETS['/focus.js'] = ('focus.js', 'text/javascript; charset=utf-8')
ACTIONS = {'/api/generate': 'generate', '/api/reroll': 'reroll',
           '/api/get': 'get', '/api/profile': 'profile', '/api/edit': 'edit',
           '/api/validate': 'validate', '/api/decision': 'decision',
           '/api/approved-text': 'approved-text'}
ACTIONS.update({f'/api/quality-{action}': f'quality-{action}' for action in
    ('diagnostics', 'list', 'get', 'start', 'step', 'assess', 'export')})
ACTIONS.update({f'/api/inbox-{action}': f'inbox-{action}' for action in
    ('preview', 'create', 'list', 'get', 'step', 'skip', 'retry', 'note')})
ACTIONS.update({f'/api/feedback-{action}': f'feedback-{action}' for action in ('save', 'summary')})
ACTIONS.update({f'/api/recovery-{action}': f'recovery-{action}' for action in ('get', 'save', 'clear')})
ACTIONS['/api/generation-check'] = 'generation-check'


ACTIONS.update({f'/api/submission-{action}': f'submission-{action}'
                for action in ('state', 'save', 'export')})


def strict_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON keys are not accepted')
        result[key] = value
    return result


def reject_constant(value):
    raise ValueError('JSON constants must be finite')


class LocalServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = False

    def __init__(self, workspace, port=8765):
        self.workspace = workspace
        from rrw_submission import SubmissionDesk
        self.submission = SubmissionDesk(workspace.root, workspace.lock)
        self.token = secrets.token_urlsafe(32)
        super().__init__(('127.0.0.1', port), Handler)
        self.origin = f'http://127.0.0.1:{self.server_port}'
        self.host = f'127.0.0.1:{self.server_port}'

    @property
    def launch_url(self):
        # The fragment is not sent to the HTTP server or in a Referer header.
        return self.origin + '/#token=' + self.token


class Handler(BaseHTTPRequestHandler):
    server_version = 'ReviewReplyWriter'
    sys_version = ''

    def setup(self):
        super().setup()
        self.connection.settimeout(10)

    def log_message(self, format, *args):
        pass  # Do not log reviews, capability tokens or request bodies.

    def _send(self, status, payload, mime='application/json; charset=utf-8'):
        body = payload if isinstance(payload, bytes) else json.dumps(payload, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', mime)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('X-Frame-Options', 'DENY')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('Cross-Origin-Resource-Policy', 'same-origin')
        self.send_header('Content-Security-Policy', "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'")
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError, socket.timeout):
            pass

    def _boundary(self, api=False, mutation=False):
        hosts = self.headers.get_all('Host', [])
        if hosts != [self.server.host]:
            raise WorkspaceError('Open the exact 127.0.0.1 address printed by the launcher.', 403)
        origin = self.headers.get('Origin')
        if (origin is not None and origin != self.server.origin) or (mutation and origin != self.server.origin):
            raise WorkspaceError('Cross-origin requests are not allowed.', 403)
        if self.headers.get('Sec-Fetch-Site') == 'cross-site':
            raise WorkspaceError('Cross-site requests are not allowed.', 403)
        if api:
            values = self.headers.get_all('X-RRW-Token', [])
            if len(values) != 1 or not hmac.compare_digest(values[0], self.server.token):
                raise WorkspaceError('Workspace session expired. Reopen the link printed by the launcher.', 401)

    def _error(self, exc):
        if isinstance(exc, DraftBlocked):
            self._send(422, {'error': 'Draft blocked by the checks. No approval was recorded.',
                             'findings': exc.findings})
        elif isinstance(exc, WorkspaceError):
            self._send(exc.status, {'error': str(exc)})
        elif isinstance(exc, (ValueError, TypeError, KeyError)):
            self._send(400, {'error': 'Invalid input or local data: ' + str(exc)[:300]})
        elif isinstance(exc, OSError):
            self._send(500, {'error': 'Local file or connection error. Check file permissions and preserve your existing data.'})
        else:
            self._send(500, {'error': 'Unexpected workspace error. Your current editor text has been kept in the browser.'})

    def do_GET(self):
        try:
            self._boundary(api=self.path.startswith('/api/'))
            parsed = urlsplit(self.path)
            if parsed.query or parsed.fragment or parsed.path != self.path:
                raise WorkspaceError('Unknown route.', 404)
            if self.path in ASSETS:
                name, mime = ASSETS[self.path]
                self._send(200, (HERE / 'web' / name).read_bytes(), mime)
            elif self.path == '/api/state':
                self._send(200, self.server.workspace.dispatch('state'))
            elif self.path == '/api/model':
                self._send(200, model_status())
            elif self.path == '/favicon.ico':
                self._send(204, b'', 'image/x-icon')
            else:
                raise WorkspaceError('Unknown route.', 404)
        except Exception as exc:
            self._error(exc)

    def do_POST(self):
        try:
            self._boundary(api=True, mutation=True)
            if self.path not in ACTIONS:
                raise WorkspaceError('Unknown route.', 404)
            if self.headers.get('Content-Type', '').split(';')[0].strip().lower() != 'application/json':
                raise WorkspaceError('Only application/json requests are accepted.', 415)
            if self.headers.get('Transfer-Encoding'):
                raise WorkspaceError('Chunked request bodies are not supported.', 400)
            lengths = self.headers.get_all('Content-Length', [])
            if len(lengths) != 1 or not lengths[0].isascii() or not lengths[0].isdigit():
                raise WorkspaceError('A single Content-Length is required.', 411)
            length = int(lengths[0])
            if length > MAX_BODY:
                raise WorkspaceError('Request is too large.', 413)
            raw = self.rfile.read(length)
            if len(raw) != length:
                raise WorkspaceError('Request body is incomplete.')
            data = json.loads(raw.decode('utf-8'), object_pairs_hook=strict_object,
                              parse_constant=reject_constant)
            action = ACTIONS[self.path]
            target = self.server.submission if action.startswith('submission-') else self.server.workspace
            self._send(200, target.dispatch(action, data))
        except Exception as exc:
            self._error(exc)

    def do_OPTIONS(self):
        self._send(405, {'error': 'Cross-origin access is not enabled.'})


class InstanceLock:
    """Prevent two browser servers from writing the same workspace."""
    def __init__(self, directory):
        self.path = Path(directory) / '.rrw' / 'web.lock'
        self.handle = None

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self.handle = self.path.open('a+b')
            self.handle.seek(0)
            # Windows can deny even reading the byte held by another process.
            # Keep initialization inside the error boundary and always close it.
            if not self.handle.read(1):
                self.handle.write(b'0')
                self.handle.flush()
            self.handle.seek(0)
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(self.handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            if self.handle is not None:
                self.handle.close()
                self.handle = None
            raise WorkspaceError('Cannot lock this workspace. Close another browser instance '
                                 'or check permissions for the data directory.') from exc
        return self

    def __exit__(self, *args):
        if self.handle is not None:
            try:
                self.handle.seek(0)
                if os.name == 'nt':
                    import msvcrt
                    msvcrt.locking(self.handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(self.handle.fileno(), fcntl.LOCK_UN)
            finally:
                self.handle.close()
                self.handle = None


def main(argv=None):
    parser = argparse.ArgumentParser(description='Open Review Reply Writer on this computer only.')
    parser.add_argument('--port', type=int, default=8765, help='Loopback port; 0 chooses a free port')
    parser.add_argument('--no-browser', action='store_true', help='Print the session link without opening a tab')
    parser.add_argument('--data-dir', type=Path, default=HERE, help='Directory containing replies/ and .rrw/')
    args = parser.parse_args(argv)
    if not 0 <= args.port <= 65535:
        parser.error('port must be between 0 and 65535')
    try:
        with InstanceLock(args.data_dir):
            with LocalServer(Workspace(args.data_dir), args.port) as server:
                print('Review Reply Writer | local browser workspace', flush=True)
                print(server.launch_url, flush=True)
                print('Keep this terminal open. Press Ctrl+C to stop. Do not share the session link.', flush=True)
                if not args.no_browser:
                    webbrowser.open(server.launch_url)
                server.serve_forever(poll_interval=0.2)
    except KeyboardInterrupt:
        return 0
    except (OSError, WorkspaceError) as exc:
        print(f'Could not start workspace: {exc}', file=sys.stderr)
        print('Close the other instance or choose --port 0 for a free port.', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
