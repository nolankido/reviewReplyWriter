#!/usr/bin/env python3
"""Checkpointed quality evaluations of fictional reviews. No publishing or uploads.

python rrw_evaluate.py --mode offline --suite full
python rrw_evaluate.py --mode gemma --suite smoke
python rrw_evaluate.py --report .rrw/evaluations/eval-....json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import re
import statistics
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import review_reply as rr
from reply_safety import DraftBlocked, SAFETY_VERSION
from rrw_model import inspect_model

HERE = Path(__file__).resolve().parent
CORPUS = HERE / 'examples' / 'evaluation_cases.json'
VERSION = 'rrw-evaluation-v1'
SOURCES = ('review_reply.py', 'reply_safety.py', 'rrw_risk.py', 'review_quality.py', 'rrw_workspace.py',
           'rrw_model.py', 'rrw_inbox.py', 'rrw_evaluate.py', 'examples/evaluation_cases.json')
ISSUES = ('unapproved_promise', 'invented_fact', 'missed_complaint',
          'wrong_tone', 'too_generic', 'other')
STATUSES = ('model', 'template', 'fallback', 'blocked', 'error', 'interrupted')


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
        separators=(',', ':'), allow_nan=False).encode('utf-8')).hexdigest()


def source_snapshot():
    return {name: hashlib.sha256((HERE / name).read_bytes()).hexdigest() for name in SOURCES}


def corpus():
    data = json.loads(CORPUS.read_text(encoding='utf-8'))
    ids = [case['id'] for case in data['cases']]
    if len(ids) != len(set(ids)) or not set(data['smoke']).issubset(ids):
        raise ValueError('Invalid evaluation corpus')
    return data


def result_digest(result):
    return digest({k: v for k, v in result.items() if k not in ('human_review', 'result_sha256')})


def _no_duplicates(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate evidence key')
        result[key] = value
    return result


def load_report(path):
    path = Path(path)
    if path.is_symlink() or path.stat().st_size > 4 * 1024 * 1024:
        raise ValueError('Evaluation file cannot be read safely')
    report = json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=_no_duplicates)
    if not isinstance(report, dict) or report.get('schema') != VERSION:
        raise ValueError('Unsupported evaluation report')
    expected = report.get('sha256')
    if digest({k: v for k, v in report.items() if k != 'sha256'}) != expected:
        raise ValueError('Evaluation integrity check failed; preserve the file for recovery')
    cases, results = report.get('cases'), report.get('results')
    if not isinstance(cases, list) or not 1 <= len(cases) <= 30 or not isinstance(results, list):
        raise ValueError('Invalid evaluation case list')
    if len(results) > len(cases):
        raise ValueError('Evaluation has more results than cases')
    for case, row in zip(cases, results):
        if not isinstance(row, dict) or row.get('case_id') != case.get('id') or row.get('status') not in STATUSES:
            raise ValueError('Evaluation results do not match the selected cases')
        if row.get('result_sha256') != result_digest(row):
            raise ValueError('Evaluation result fingerprint mismatch')
        review = row.get('human_review')
        if review and (not isinstance(review, dict) or review.get('result_sha256') != row['result_sha256']):
            raise ValueError('Human assessment belongs to a different result')
    return report


def summarize(report):
    rows = report['results']
    counts = {key: sum(row['status'] == key for row in rows) for key in STATUSES}
    assessments = [r['human_review'] for r in rows if r.get('human_review')]
    timings = [r['elapsed_ms'] / 1000 for r in rows if r['status'] == 'model']
    actual = report['execution'] == 'ollama'
    return dict(total=len(report['cases']), attempted=len(rows), **counts,
        complete=len(rows) == len(report['cases']) and not counts['interrupted'],
        model_calls=sum(len(r.get('attempts', [])) for r in rows),
        completed_api_responses=sum(bool(t.get('receipt', {}).get('done')) for r in rows for t in r.get('attempts', [])) if actual else 0,
        first_try_model=sum(r['status'] == 'model' and len(r.get('attempts', [])) == 1 for r in rows),
        retried_cases=sum(len(r.get('attempts', [])) > 1 for r in rows),
        rubric_flagged=sum(bool(r.get('rubric_findings')) for r in rows),
        model_median_seconds=round(statistics.median(timings), 3) if timings else None,
        human_reviewed=len(assessments), usable=sum(r['decision'] == 'usable' for r in assessments),
        needs_edit=sum(r['decision'] == 'needs_edit' for r in assessments),
        unusable=sum(r['decision'] == 'unusable' for r in assessments),
        human_risk_flags=sum(bool(r['issues']) for r in assessments),
        genuine_model_drafts=counts['model'] if actual else 0)


def live_evidence_blockers(report):
    """Checks evidence structure, not authenticity of a local server or its claims."""
    findings = []
    if report.get('execution') != 'ollama' or report.get('mode') != 'gemma':
        findings.append('This is not a real Ollama evaluation; templates and controlled callers do not qualify.')
    if report.get('sources') != source_snapshot():
        findings.append('Evaluation was recorded against different source files; record a fresh run.')
    summary = summarize(report)
    if not summary['complete'] or summary['total'] < 3:
        findings.append('Finish at least the three-case smoke run; incomplete runs do not qualify.')
    if not summary['genuine_model_drafts'] or not summary['completed_api_responses']:
        findings.append('No accepted model draft with a completed API receipt was recorded.')
    if not report.get('preflight', {}).get('ready'):
        findings.append('The model identity preflight did not pass.')
    if any(r.get('model_identity_changed') for r in report['results']):
        findings.append('Model identity changed during this run.')
    if summary['human_reviewed'] < summary['total']:
        findings.append('Human assessment is missing for one or more cases.')
    return findings


def markdown_report(report):
    s = summarize(report)
    lines = ['# Review Reply Writer: quality evidence', '',
        '**Fictional regression fixtures, not real-customer validation.**', '',
        f"Run: `{report['id']}`. Mode: **{report['mode']}**. Execution: **{report['execution']}**.",
        f"Started: {report['created_at']}. Source fingerprint: `{digest(report['sources'])}`.", '',
        '## Results', '',
        f"Attempted {s['attempted']} of {s['total']}; model drafts {s['model']}; templates {s['template']}; fallbacks {s['fallback']}; blocked {s['blocked']}; errors {s['error']}; interrupted {s['interrupted']}.",
        f"First-attempt model drafts: {s['first_try_model']}. Retried cases: {s['retried_cases']}. Completed API responses: {s['completed_api_responses']}.",
        f"Median elapsed seconds for model-drafted cases only (including their retries): {s['model_median_seconds'] if s['model_median_seconds'] is not None else 'not measured'}.",
        f"Rubric flags: {s['rubric_flagged']}. These are limited text/tier probes, not a semantic quality score.", '',
        '## Human assessment', '',
        f"Reviewed {s['human_reviewed']} of {s['total']}: usable as draft {s['usable']}, needs editing {s['needs_edit']}, unusable {s['unusable']}.",
        f"Cases with human-reported risks: {s['human_risk_flags']} among reviewed cases only. Unreviewed cases have unknown quality.", '',
        'Assessments do not approve replies for publication. Self-checks and hashes do not prove factuality, local execution, or external verification.', '',
        '## Case records', '']
    for case, row in zip(report['cases'], report['results']):
        lines.extend([f"### {case['label']}", '', f"Outcome: {row['status']}. Rubric: {'; '.join(row.get('rubric_findings', [])) or 'no probe flagged'}.",
                      '', 'Review:', '', json.dumps(case['input']['review'], ensure_ascii=False), '', 'Reply:', '',
                      json.dumps(row.get('reply'), ensure_ascii=False), '',
                      'Findings: ' + json.dumps(row.get('findings', []), ensure_ascii=False), '',
                      'Human assessment: ' + json.dumps(row.get('human_review'), ensure_ascii=False), ''])
    lines.extend(['## Reproduction and limits', '',
        'JSON export contains the source hashes, complete fixture snapshots, model digest, attempt texts and available server timing receipts. Keep it with this report.',
        'No prompts, reports or reviews are uploaded by the application. Server metadata is trusted, not independently attested. Local hashes detect accidental edits, not deliberate forgery.', ''])
    return '\n'.join(lines)


class EvaluationLab:
    def __init__(self, workspace, inspector=None):
        self.workspace = workspace
        self.folder = workspace.private / 'evaluations'
        if self.folder.is_symlink():
            raise ValueError('Evaluation folder cannot be a symlink')
        self.folder.mkdir(exist_ok=True)
        self.inspect = inspector or inspect_model
        self.active = None

    def _path(self, name):
        from rrw_workspace import WorkspaceError
        if not isinstance(name, str) or not re.fullmatch(r'eval-[0-9a-f]{32}', name):
            raise WorkspaceError('Invalid evaluation identifier')
        path = self.folder / (name + '.json')
        if path.is_symlink():
            raise WorkspaceError('Evaluation links are not supported')
        return path

    def _read(self, data):
        from rrw_workspace import WorkspaceError
        path = self._path(data.get('id'))
        if not path.exists():
            raise WorkspaceError('Evaluation not found', 404)
        report = load_report(path)
        if data.get('revision') != report['sha256']:
            raise WorkspaceError('Evaluation changed elsewhere. Reopen it before continuing.', 409)
        return report

    def _save(self, report):
        report['updated_at'] = now()
        for row in report['results']:
            row['result_sha256'] = result_digest(row)
        report['sha256'] = digest({k: v for k, v in report.items() if k != 'sha256'})
        rr.atomic_json(str(self._path(report['id'])), report)
        return self._view(report)

    def _view(self, report):
        return dict(report, revision=report['sha256'], summary=summarize(report),
                    sources_current=report['sources'] == source_snapshot(),
                    active=self.active == report['id'],
                    evidence_blockers=live_evidence_blockers(report))

    def start(self, data):
        from rrw_workspace import gemma_caller, WorkspaceError
        mode, suite = data.get('mode', 'offline'), data.get('suite', 'smoke')
        if mode not in ('offline', 'gemma') or suite not in ('smoke', 'full'):
            raise WorkspaceError('Select a supported evaluation mode and suite')
        if mode == 'gemma' and data.get('confirmed') is not True:
            raise WorkspaceError('Confirm that this will run the installed Gemma model on fictional reviews')
        fixtures = corpus()
        cases = fixtures['cases'] if suite == 'full' else [c for c in fixtures['cases'] if c['id'] in fixtures['smoke']]
        execution = 'templates' if mode == 'offline' else ('ollama' if self.workspace.caller is gemma_caller else 'controlled-test')
        preflight = self.inspect() if mode == 'gemma' else {'ready': False, 'state': 'not_requested', 'message': 'No model calls in template mode.'}
        report = dict(schema=VERSION, id='eval-' + uuid.uuid4().hex, created_at=now(),
            mode=mode, suite=suite, execution=execution, cases=cases, results=[],
            provenance=fixtures['provenance'], corpus_version=fixtures['version'],
            sources=source_snapshot(), safety_version=SAFETY_VERSION, preflight=preflight,
            environment={'python': platform.python_version(), 'os': platform.system(),
                         'architecture': platform.machine()},
            parameters={'model': rr.DEFAULT_MODEL, 'temperature_initial': .8,
                        'temperature_retry': .3, 'num_predict': 500,
                        'context': 'Ollama server default; not independently inspected',
                        'seed': 'Ollama default; repeatable protocol, not guaranteed identical text'})
        with self.workspace.lock:
            return self._save(report)

    def step(self, data):
        from rrw_workspace import WorkspaceError
        if not self.workspace.generation.acquire(blocking=False):
            raise WorkspaceError('A generation is already in progress. Finish it first.', 409)
        try:
            with self.workspace.lock:
                report = self._read(data)
                if report['sources'] != source_snapshot():
                    raise WorkspaceError('The code changed. Start a new evaluation rather than mixing versions.', 409)
                if len(report['results']) >= len(report['cases']):
                    raise WorkspaceError('This run has no remaining cases. Start a new run to repeat it.', 409)
                if report['mode'] == 'gemma' and not report['preflight']['ready']:
                    raise WorkspaceError('Model setup did not pass. Resolve it and start a fresh run.', 409)
                case = report['cases'][len(report['results'])]
                self.active = report['id']
                # Reserve before inference. A process crash leaves an honest interruption,
                # never a silently repeated or missing case.
                row = dict(case_id=case['id'], status='interrupted', started_at=now(),
                           reply=None, attempts=[], findings=['Execution did not finish.'],
                           rubric_findings=[], elapsed_ms=0)
                report['results'].append(row)
                reserved = self._save(report)['revision']
            import time
            started = time.monotonic()
            try:
                if report['mode'] == 'gemma':
                    current = self.inspect()
                    if not current['ready'] or current.get('identity') != report['preflight'].get('identity'):
                        row['model_identity_changed'] = True
                        raise ValueError('Model identity changed or became unavailable; start a fresh run')
                draft = self.workspace._new_draft(case['input'])
                result = self.workspace._generate(draft, report['mode'],
                    observe=row['attempts'].append, record_ledger=False)
                row.update(reply=result['reply'], engine=result['engine'], tier=result['tier'], findings=[],
                           status='template' if report['mode'] == 'offline' else
                           ('fallback' if result['engine'].startswith('template') else 'model'))
                if result['tier'] != case['expected_tier']:
                    row['rubric_findings'].append('Tier mismatch: expected ' + case['expected_tier'] + ', got ' + result['tier'])
                body = rr._body(result['reply'], result.get('signoff')).lower()
                import review_quality as quality
                row['review_evidence'] = quality.coverage(body, draft['review'],
                    None if 'original' in draft else draft.get('stars'))
                if case['topics_any'] and not any(t.lower() in body for t in case['topics_any']):
                    row['rubric_findings'].append('No target issue/topic mentioned: ' + ', '.join(case['topics_any']))
                if report['mode'] == 'gemma':
                    current = self.inspect()
                    if not current['ready'] or current.get('identity') != report['preflight'].get('identity'):
                        row.update(status='error', model_identity_changed=True,
                                   findings=['Model identity changed during generation; result is not qualified evidence.'])
            except DraftBlocked as exc:
                row.update(status='blocked', findings=exc.findings)
            except (OSError, ValueError, TypeError, KeyError) as exc:
                row.update(status='error', findings=[str(exc)[:600]])
            finally:
                row['elapsed_ms'] = round((time.monotonic() - started) * 1000)
                row['finished_at'] = now()
            with self.workspace.lock:
                self._read(dict(id=report['id'], revision=reserved))
                return self._save(report)
        finally:
            self.active = None
            self.workspace.generation.release()

    def assess(self, data):
        from rrw_workspace import WorkspaceError, text
        report = self._read(data)
        if self.active == report['id']:
            raise WorkspaceError('Finish the active case before assessing it.', 409)
        if report['sources'] != source_snapshot():
            raise WorkspaceError('Source changed. Export this historical run or start a fresh evaluation.', 409)
        row = next((r for r in report['results'] if r['case_id'] == data.get('case_id')), None)
        if row is None or row['result_sha256'] != data.get('result_sha256'):
            raise WorkspaceError('The result changed. Reopen the case before assessing it.', 409)
        if data.get('reviewed') is not True or data.get('decision') not in ('usable', 'needs_edit', 'unusable'):
            raise WorkspaceError('Read the case and choose an explicit human assessment')
        if row['reply'] is None and data['decision'] != 'unusable':
            raise WorkspaceError('A case with no draft cannot be assessed as usable')
        issues = data.get('issues', [])
        if not isinstance(issues, list) or any(not isinstance(x, str) or x not in ISSUES for x in issues):
            raise WorkspaceError('Choose a supported issue label')
        if len(issues) != len(set(issues)) or len(issues) > len(ISSUES):
            raise WorkspaceError('Duplicate issue labels')
        edited = text(data.get('edited_reply', ''), 'Edited reply', 20000)
        notes = text(data.get('notes', ''), 'Assessment notes', 2000)
        if data['decision'] == 'needs_edit' and not (edited or notes):
            raise WorkspaceError('Describe the needed edit or enter a corrected draft')
        case = next(c for c in report['cases'] if c['id'] == row['case_id'])
        row['human_review'] = dict(result_sha256=row['result_sha256'], reviewed_at=now(),
            decision=data['decision'], issues=issues, notes=notes, edited_reply=edited,
            edited_findings=rr.draft_findings(dict(self.workspace._new_draft(case['input']), reply=edited)) if edited else [])
        return self._save(report)

    def dispatch(self, action, data):
        from rrw_workspace import WorkspaceError
        if action == 'quality-start':
            return self.start(data)
        if action == 'quality-step':
            return self.step(data)
        if action == 'quality-diagnostics':
            return self.inspect()
        with self.workspace.lock:
            if action == 'quality-list':
                runs = []
                for path in sorted(self.folder.glob('eval-*.json'), key=lambda p: p.name):
                    try:
                        report = load_report(path)
                        runs.append(dict(id=report['id'], created_at=report['created_at'],
                            mode=report['mode'], execution=report['execution'], summary=summarize(report)))
                    except (OSError, ValueError, TypeError, KeyError):
                        runs.append(dict(id=path.stem, error='Unreadable evidence; original file preserved.'))
                runs.sort(key=lambda r: r.get('created_at', ''), reverse=True)
                return {'runs': runs, 'suites': {'smoke': 3, 'full': len(corpus()['cases'])}}
            if action == 'quality-get':
                return self._view(load_report(self._path(data.get('id'))))
            if action == 'quality-assess':
                return self.assess(data)
            if action == 'quality-export':
                report = self._read(data)
                if self.active == report['id']:
                    raise WorkspaceError('Finish the active case before exporting.', 409)
                if data.get('format') == 'json':
                    return {'filename': report['id'] + '.json', 'mime': 'application/json',
                            'text': json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + '\n'}
                if data.get('format') == 'markdown':
                    return {'filename': report['id'] + '.md', 'mime': 'text/markdown',
                            'text': markdown_report(report)}
                raise WorkspaceError('Export as JSON or Markdown')
            raise WorkspaceError('Unknown quality action', 404)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=('offline', 'gemma'), default='offline')
    parser.add_argument('--suite', choices=('smoke', 'full'), default='smoke')
    parser.add_argument('--data-dir', type=Path, default=HERE)
    parser.add_argument('--report', type=Path, help='Read an existing JSON evidence file; no model calls')
    parser.add_argument('--resume', help='Continue remaining cases of an existing evaluation id')
    args = parser.parse_args(argv)
    try:
        if args.report:
            print(markdown_report(load_report(args.report)))
            return 0
        from rrw_workspace import Workspace
        from rrw_web import InstanceLock
        with InstanceLock(args.data_dir):
            workspace = Workspace(args.data_dir)
            lab = EvaluationLab(workspace)
            report = lab.dispatch('quality-get', {'id': args.resume}) if args.resume else lab.start(
                {'mode': args.mode, 'suite': args.suite, 'confirmed': True})
            print(f"Evaluation {report['id']}: {report['execution']}; fictional fixtures only.", flush=True)
            if report['mode'] == 'gemma' and not report['preflight']['ready']:
                print(report['preflight']['message'])
                print('No generation performed. Resolve setup and start a fresh run.')
                return 2
            while len(report['results']) < len(report['cases']):
                print(f"Case {len(report['results']) + 1}/{len(report['cases'])}", flush=True)
                report = lab.step({'id': report['id'], 'revision': report['revision']})
                row = report['results'][-1]
                print(row['case_id'] + ': ' + row['status'], flush=True)
            print(markdown_report(report))
            print('JSON saved locally: ' + str(lab._path(report['id'])))
            print('Open Quality Lab in the browser to record human assessments.')
            return 1 if any(r['status'] in ('error', 'interrupted') for r in report['results']) else 0
    except (OSError, ValueError) as exc:
        print('Evaluation could not complete: ' + str(exc), file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print('Stopped. Completed cases are saved; an in-flight case remains marked interrupted.', file=sys.stderr)
        return 130


if __name__ == '__main__':
    sys.exit(main())
