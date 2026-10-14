#!/usr/bin/env python3
"""Explicit local development verification. No CI, installs, inference or uploads.

python rrw_verify.py [--browser] [--output NEW_FILE.json]
Receipts omit subprocess output, private state, tokens and machine paths.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import shutil
import signal
import subprocess
import sys
import time
import uuid

HERE = Path(__file__).resolve().parent
MANIFEST = 'verification_sources.json'
NODE_CHECKS = ('input_state_checks', 'connection_state_checks', 'save_recovery_checks',
               'focus_checks', 'generation_status_checks', 'quality_recovery_checks',
               'inbox_input_checks')
BROWSER_CHECKS = ('browser_smoke', 'quality_browser_smoke', 'submission_browser_smoke',
                  'inbox_browser_smoke')


def source_snapshot(project):
    """Fingerprint the explicit public source inventory, never scan owner state."""
    from rrw_submission import read_packet_file
    project = Path(project)
    def read(name):
        relative = PurePosixPath(name)
        if (relative.is_absolute() or str(relative) != name or '..' in relative.parts
                or any(part.startswith('.') for part in relative.parts)):
            raise ValueError('Invalid public source inventory')
        path = project / relative
        if any(project.joinpath(*relative.parts[:i]).is_symlink()
               for i in range(1, len(relative.parts) + 1)):
            raise ValueError('Source links are not supported')
        return read_packet_file(path, 4 * 1024 * 1024, 'Verification source', 'Incomplete source copy')
    manifest = read(MANIFEST)
    names = json.loads(manifest)
    if (not isinstance(names, list) or not 1 <= len(names) <= 200
            or any(not isinstance(name, str) or not name for name in names)
            or len(names) != len(set(names))):
        raise ValueError('Invalid public source inventory')
    # A newly added test must be inventoried before its results can be source-bound.
    if not {path.name for path in project.glob('test_*.py')}.issubset(names):
        raise ValueError('Test inventory is incomplete')
    allowed_examples = {'examples/02-angry-cafe.txt', 'examples/batch-sample.csv',
                        'examples/evaluation_cases.json'}
    files = {MANIFEST: hashlib.sha256(manifest).hexdigest()}
    for name in names:
        path = PurePosixPath(name)
        allowed = (len(path.parts) == 1 and path.suffix == '.py' or name == 'start_windows.bat'
                   or path.parts[0] == 'scripts' and len(path.parts) == 2 and path.suffix in ('.py', '.cjs')
                   or path.parts[0] == 'web' and len(path.parts) == 2 and path.suffix in ('.js', '.css', '.html', '.csv')
                   or name in allowed_examples
                   or name.startswith('examples/safety/') and len(path.parts) == 3 and path.suffix in ('.md', '.txt'))
        if not allowed:
            raise ValueError('Inventory must exclude private state and owner policies')
        files[name] = hashlib.sha256(read(name)).hexdigest()
    return files


def execute(command, project, timeout):
    """Run fixed local commands with private output discarded and bounded lifetime."""
    process = None
    try:
        options = {'start_new_session': True} if os.name != 'nt' else {
            'creationflags': subprocess.CREATE_NEW_PROCESS_GROUP}
        process = subprocess.Popen(command, cwd=project, stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL, **options)
        code = process.wait(timeout=timeout)
        return ('passed' if code == 0 else 'failed', code)
    except subprocess.TimeoutExpired:
        return 'timed_out', None
    except OSError:
        return 'unavailable', None
    except KeyboardInterrupt:
        raise
    finally:
        if process is not None and process.poll() is None:
            if os.name == 'nt':
                subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10, check=False)
            else:
                try: os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError: pass
            process.wait(timeout=10)


def verify(project=HERE, browser=False, runner=None, node=None, emit=print):
    runner = runner or execute
    node = shutil.which('node') if node is None else node
    before = source_snapshot(project)
    report = {'schema': 'rrw-local-verification-v1',
              'checked_at': datetime.now(timezone.utc).isoformat(),
              'environment': {'python': platform.python_version(), 'os': platform.system(),
                              'architecture': platform.machine()},
              'sources': before, 'sources_current': False, 'checks': [],
              'source_scope': 'Fixed application, web assets, test scripts and fictional fixtures in verification_sources.json. Owner policies, private state, documentation and external runtimes are excluded.',
              'development_verified': False, 'model_inference': 'not_requested',
              'operator_feedback': 'not_collected', 'contest_readiness': 'not_verified',
              'limits': 'Local execution on this machine only. State/browser fixtures use controlled data and model stand-ins. Source hashes are not signatures; private data and raw logs are excluded.'}
    commands = [('development', [sys.executable, 'check_submission.py'], 300),
                ('launcher', [sys.executable, 'scripts/launcher_smoke.py'], 90),
                ('backup', [sys.executable, 'scripts/backup_smoke.py'], 90)]
    commands += [(name, [node, 'scripts/' + name + '.cjs'] if node else None, 30)
                 for name in NODE_CHECKS]
    commands += [(name, [sys.executable, 'scripts/' + name + '.py'] if browser else None, 300)
                 for name in BROWSER_CHECKS]
    for name, command, timeout in commands:
        emit('Checking ' + name + '...')
        start = time.monotonic()
        if command is None:
            state, code = ('not_requested' if name in BROWSER_CHECKS else 'unavailable'), None
        else:
            state, code = runner(command, project, timeout)
        report['checks'].append({'id': name, 'state': state, 'exit_code': code,
                                 'elapsed_seconds': round(time.monotonic() - start, 3)})
        emit(name + ': ' + state)
    try: report['sources_current'] = before == source_snapshot(project)
    except (OSError, ValueError, ImportError): pass
    required = [row for row in report['checks'] if row['id'] not in BROWSER_CHECKS or browser]
    report['development_verified'] = report['sources_current'] and all(row['state'] == 'passed' for row in required)
    report['browser_navigation'] = 'passed' if browser and all(
        row['state'] == 'passed' for row in report['checks'] if row['id'] in BROWSER_CHECKS) else (
            'not_requested' if not browser else 'not_passed')
    if not report['sources_current'] or any(row['state'] in ('failed', 'timed_out') for row in required):
        return report, 1
    return report, 0 if report['development_verified'] else 2


def save_receipt(report, path):
    path = Path(os.path.abspath(path))
    if any(part.is_symlink() for part in (path, *path.parents)):
        raise ValueError('Receipt links are not supported')
    if path.exists():
        raise ValueError('Receipt already exists; choose a new filename')
    content = json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + '\n'
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as stream:
        stream.write(content)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--browser', action='store_true', help='Explicitly run already-installed Playwright/Chromium checks; never install')
    parser.add_argument('--output', type=Path, help='New local JSON receipt filename; never overwrite')
    args = parser.parse_args(argv)
    output = args.output or HERE / '.rrw' / 'verification' / ('verify-' + uuid.uuid4().hex + '.json')
    try:
        if output.exists() or output.is_symlink():
            raise ValueError('Receipt already exists; choose a new filename')
        if sys.version_info < (3, 10):
            raise ValueError('Python 3.10 or newer is required')
        report, code = verify(browser=args.browser)
        save_receipt(report, output)
        print('Receipt saved locally. Nothing was uploaded. Inspect before sharing.')
        print('Development verification: ' + ('passed' if report['development_verified'] else 'not passed'))
        print('Browser navigation: ' + report['browser_navigation'] + '. Gemma and operator evidence remain separate.')
        print('For any failed check, run its named script directly to inspect local diagnostics.')
        return code
    except KeyboardInterrupt:
        print('Interrupted. No completed verification or new receipt is claimed.', file=sys.stderr)
        return 130
    except (OSError, ValueError, ImportError):
        print('Verification or receipt saving failed. Use a complete source copy and a new writable receipt path; existing files were kept.', file=sys.stderr)
        return 1


if __name__ == '__main__': raise SystemExit(main())
