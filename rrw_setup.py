#!/usr/bin/env python3
"""Check this computer, launch the app, or explicitly test Gemma on fictional reviews.

No package installation, model downloads, configuration changes or uploads.
Diagnostics exclude customer files, full paths and raw server/error messages.
"""
import argparse
from datetime import datetime, timezone
from pathlib import Path
import platform
import random
import socket
import sys
import tempfile

HERE = Path(__file__).resolve().parent
REQUIRED_FILES = ('review_reply.py', 'review_quality.py', 'reply_safety.py', 'rrw_risk.py',
                  'rrw_model.py', 'rrw_workspace.py', 'rrw_web.py', 'rrw_inbox.py',
                  'rrw_evaluate.py', 'rrw_submission.py', 'rrw_feedback.py', 'rrw_recovery.py', 'rrw_requests.py', 'examples/evaluation_cases.json',
                  'web/index.html', 'web/app.js', 'web/style.css', 'web/inbox.js',
                  'web/inbox.css', 'web/inbox-sample.csv', 'web/submission.js',
                  'web/review-evidence.js', 'web/review-evidence.css', 'web/feedback.js', 'web/recovery.js',
                  'web/connection.js', 'web/generation.js', 'web/save-recovery.js')
MODEL_MESSAGES = {
    'installed': 'Gemma 3 is installed. Generation has not been tested by this check.',
    'missing': 'Ollama is running. Download gemma3:4b, then check again.',
    'unavailable': 'Start Ollama, then check again. Templates still work.',
    'unverified': 'The model identity check failed. Open Quality Lab for details.',
}


def writable_directory(directory):
    """Probe storage without opening customer files. Temporary files are removed."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    targets = [directory]
    for name in ('.rrw', 'replies'):
        child = directory / name
        if child.is_symlink():
            raise ValueError('Workspace folders must not be links')
        if child.exists():
            if not child.is_dir():
                raise ValueError('Workspace folder is not a directory')
            targets.append(child)
    for target in targets:
        with tempfile.TemporaryFile(dir=target) as probe:
            probe.write(b'rrw-setup-check')
            probe.flush()
            probe.seek(0)
            if probe.read() != b'rrw-setup-check':
                raise OSError('Storage probe did not round-trip')


def loopback_check():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(('127.0.0.1', 0))


def installation_check():
    if any(not (HERE / name).is_file() or (HERE / name).stat().st_size == 0
           for name in REQUIRED_FILES):
        raise ValueError('Incomplete application copy')


def template_check():
    import review_reply as rr
    review = 'Cold coffee and a 25 minute wait. Disappointing.'
    reply = rr.template_reply(review, 'Demo Cafe', 'professional', 2, 'cafe',
                              random.Random(7))
    if not rr.validate_reply(reply, review, 'Demo Cafe', 2):
        raise ValueError('Template self-check failed')


def check_setup(directory, inspector=None):
    supported = sys.version_info >= (3, 10)
    report = {
        'schema': 'rrw-setup-v1',
        'checked_at': datetime.now(timezone.utc).isoformat(),
        'environment': {'python': platform.python_version(), 'os': platform.system(),
                        'architecture': platform.machine()},
        'checks': [{'id': 'python', 'passed': supported,
                    'message': 'Python 3.10 or newer is required.'}],
        'templates_ready': False, 'gemma_installed': False,
        'model': {'state': 'not_checked', 'identity': None},
        'gemma_test': {'requested': False, 'passed': False, 'state': 'not_requested'},
        'limits': 'Setup checks are not human quality assessment or a network privacy audit.',
    }
    if not supported:
        return report  # Avoid importing the app on unsupported runtimes.
    for name, check, message in (
        ('installation', installation_check, 'Extract a complete copy of the app, including its web folder.'),
        ('storage', lambda: writable_directory(directory),
         'Local storage must be writable. Extract the ZIP into a writable folder or use --data-dir PATH.'),
        ('loopback', loopback_check, 'The browser needs permission to listen on 127.0.0.1.'),
        ('template', template_check,
         'The template and validator self-check must pass. Re-extract a complete copy if it fails.'),
    ):
        try:
            check()
            passed = True
        except (OSError, ValueError, ImportError):
            passed = False
        report['checks'].append({'id': name, 'passed': passed, 'message': message})
    report['templates_ready'] = all(item['passed'] for item in report['checks'])
    if not next(item['passed'] for item in report['checks'] if item['id'] == 'installation'):
        return report
    if inspector is None:
        from rrw_model import inspect_model
        inspector = inspect_model
    inspected = inspector()
    state = inspected['state']
    report['gemma_installed'] = inspected['ready'] is True and state == 'installed'
    # Exclude free-form server metadata and exception messages from diagnostics.
    identity = inspected.get('identity') or {}
    report['model'] = {'state': state, 'message': MODEL_MESSAGES[state],
                       'identity': {key: identity[key] for key in ('name', 'digest', 'size', 'family')
                                    if key in identity} if report['gemma_installed'] else None}
    return report


def smoke_summary(run):
    from rrw_evaluate import source_snapshot, summarize
    summary = summarize(run)
    passed = (run['execution'] == 'ollama' and run['preflight']['ready'] is True
              and summary['complete'] and summary['total'] == 3
              and summary['model'] == 3 and summary['completed_api_responses'] >= 3
              and not summary['rubric_flagged']
              and all(any(attempt.get('receipt', {}).get('done') is True
                          for attempt in row.get('attempts', [])) for row in run['results'])
              and not any(row.get('model_identity_changed') for row in run['results'])
              and run['sources'] == source_snapshot())
    return {
        'requested': True, 'passed': passed,
        'state': 'completed' if summary['complete'] else 'incomplete',
        'evaluation_id': run['id'], 'execution': run['execution'],
        'sources': run['sources'],
        'total': summary['total'], 'attempted': summary['attempted'],
        'model_drafts': summary['genuine_model_drafts'],
        'completed_api_responses': summary['completed_api_responses'],
        'fallbacks': summary['fallback'], 'errors': summary['error'],
        'blocked': summary['blocked'], 'interrupted': summary['interrupted'],
        'rubric_flagged': summary['rubric_flagged'],
        'human_reviewed': summary['human_reviewed'],
    }


def verify_gemma(report, directory, emit=print):
    report['gemma_test'] = {'requested': True, 'passed': False, 'state': 'prerequisites_failed'}
    if not report['templates_ready'] or not report['gemma_installed']:
        emit('Gemma test skipped. Fix the failed setup checks first; no generation was performed.')
        return
    from rrw_evaluate import EvaluationLab
    from rrw_web import InstanceLock
    from rrw_workspace import Workspace
    with InstanceLock(directory):
        lab = EvaluationLab(Workspace(directory))
        run = lab.start({'mode': 'gemma', 'suite': 'smoke', 'confirmed': True})
        report['gemma_test'] = smoke_summary(run)
        if not run['preflight']['ready']:
            emit('The model became unavailable. No generation was performed.')
            return
        emit('Running three fictional reviews. Each completed case is saved; nothing is posted.')
        try:
            while len(run['results']) < len(run['cases']):
                emit('Case {}/3'.format(len(run['results']) + 1))
                run = lab.step({'id': run['id'], 'revision': run['revision']})
                report['gemma_test'] = smoke_summary(run)
                emit(run['results'][-1]['case_id'] + ': ' + run['results'][-1]['status'])
        except KeyboardInterrupt:
            run = lab.dispatch('quality-get', {'id': run['id']})
            report['gemma_test'] = dict(smoke_summary(run), passed=False, state='interrupted')
            raise
        emit('Evaluation saved: ' + str(lab._path(run['id'])))
        emit('Open Quality Lab to read the results and record human assessments.')


def save_report(report, path):
    import review_reply as rr
    path = Path(path)
    if path.is_symlink() or path.parent.is_symlink():
        raise ValueError('Diagnostic report links are not supported')
    path.parent.mkdir(parents=True, exist_ok=True)
    rr.atomic_json(str(path), report)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument('--launch', action='store_true', help='Check setup, then open the local app')
    actions.add_argument('--verify-gemma', action='store_true', help='Run the three fictional Gemma smoke cases')
    parser.add_argument('--data-dir', type=Path, default=HERE)
    parser.add_argument('--report', type=Path, help='Save diagnostics without customer data or full paths')
    parser.add_argument('--port', type=int, default=0, help='Launch port; 0 selects a free port (default)')
    parser.add_argument('--no-browser', action='store_true')
    args = parser.parse_args(argv)
    if not 0 <= args.port <= 65535:
        parser.error('port must be between 0 and 65535')
    report = check_setup(args.data_dir)
    for item in report['checks']:
        print('{}: {}{}'.format(item['id'], 'OK' if item['passed'] else 'FAILED',
                               '' if item['passed'] else '. ' + item['message']))
    if report['model']['state'] != 'not_checked':
        print(report['model']['message'])
    code = 0 if report['templates_ready'] else 1
    try:
        if args.verify_gemma:
            verify_gemma(report, args.data_dir)
            code = 0 if report['gemma_test']['passed'] else 2
    except (OSError, ValueError):
        report['gemma_test'].update(passed=False, state='could_not_complete')
        print('Test could not complete. Close the app, check folder permissions, then try again.')
        code = 2
    except KeyboardInterrupt:
        print('Stopped. Completed cases remain saved; no human assessment was recorded.')
        code = 130
    report_path = args.report or (args.data_dir / '.rrw' / 'setup-check.json' if args.verify_gemma else None)
    if report_path and sys.version_info >= (3, 10):
        try:
            save_report(report, report_path)
            print('Diagnostics saved: ' + str(report_path))
        except (OSError, ValueError):
            print('Could not save diagnostics. Check the report folder permissions.')
            return 1
    if args.verify_gemma:
        print('Gemma smoke: ' + ('PASSED. Human assessment still required.' if report['gemma_test']['passed']
                                else 'NOT VERIFIED. Review setup and any saved case results.'))
    if args.launch and report['templates_ready']:
        from rrw_web import main as launch
        options = ['--port', str(args.port), '--data-dir', str(args.data_dir)]
        if args.no_browser:
            options.append('--no-browser')
        return launch(options)
    return code


if __name__ == '__main__':
    sys.exit(main())
