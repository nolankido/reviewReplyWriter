"""Saved reply comparisons and private, self-reported review assessments.

Notes never enter prompts, owner policy, approvals or the submission packet.
Exports count assessed drafts, not people, revenue or time saved.
"""
from __future__ import annotations

from datetime import datetime, timezone
from difflib import SequenceMatcher
import hashlib
import json
import re

import review_reply as rr
from rrw_workspace import WorkspaceError, text, MAX_REPLY_CHARS

SCHEMA = 'rrw-review-note-v1'
ROLES = ('operator', 'builder', 'demo')
SCENARIOS = ('fictional', 'authorized_review', 'unspecified')
DECISIONS = ('as_is', 'needs_edits', 'not_useful')
REASONS = ('missed_detail', 'invented_fact', 'unapproved_promise', 'tone', 'too_generic', 'other')
FIELDS = {'role', 'scenario', 'decision', 'reasons', 'note', 'review_seconds'}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
        separators=(',', ':'), allow_nan=False).encode('utf-8')).hexdigest()


def comparison(draft):
    baseline = draft.get('generation_baseline')
    if baseline is None:
        return {'available': False, 'message': 'No starting reply was recorded for this older or imported draft.'}
    if (not isinstance(baseline, dict) or set(baseline) != {'reply', 'engine', 'generated_at'}
            or not all(isinstance(baseline.get(k), str) for k in baseline)
            or not 0 < len(baseline['reply']) <= MAX_REPLY_CHARS
            or len(baseline['engine']) > 2000 or len(baseline['generated_at']) > 80):
        return {'available': False, 'message': 'Starting reply metadata needs recovery; comparison is unavailable.'}
    before, after = baseline['reply'], draft['reply']
    left, right = re.findall(r'\s+|\S+', before), re.findall(r'\s+|\S+', after)
    limited = max(len(left), len(right)) > 1000
    changes = [] if limited else [
        {'kind': kind, 'before': ''.join(left[a:b]), 'after': ''.join(right[c:d])}
        for kind, a, b, c, d in SequenceMatcher(None, left, right).get_opcodes()]
    return {'available': True, 'changed': before != after, 'baseline_reply': before,
            'baseline_engine': baseline['engine'], 'generated_at': baseline['generated_at'],
            'baseline_words': len(before.split()), 'saved_words': len(after.split()),
            'changes': changes, 'highlight_limited': limited}


def values(data):
    if not isinstance(data, dict) or set(data) != FIELDS:
        raise WorkspaceError('Review assessment fields are missing or unsupported.')
    result = dict(data)
    for field, choices in (('role', ROLES), ('scenario', SCENARIOS), ('decision', DECISIONS)):
        if data[field] not in choices:
            raise WorkspaceError('Choose a supported assessment ' + field + '.')
    reasons = data['reasons']
    if (not isinstance(reasons, list) or len(reasons) > len(REASONS)
            or any(not isinstance(item, str) or item not in REASONS for item in reasons)
            or len(reasons) != len(set(reasons))):
        raise WorkspaceError('Choose distinct supported reasons.')
    result['note'] = text(data['note'], 'Private review note', 1200)
    seconds = data['review_seconds']
    if seconds is not None and (type(seconds) is not int or not 0 <= seconds <= 7200):
        raise WorkspaceError('Observed review time must be blank or 0-7200 whole seconds.')
    return result


def source_kind(draft):
    compared = comparison(draft)
    if not compared['available']:
        return 'unknown'
    engine = compared['baseline_engine']
    if engine.startswith('template'):
        return 'fallback' if 'fallback' in engine else 'template'
    return 'model_labelled' if engine.startswith(rr.DEFAULT_MODEL + ' via Ollama') else 'unknown'


class ReviewNotes:
    def __init__(self, workspace):
        self.workspace = workspace
        self.folder = workspace.private / 'review-notes'

    def _check_folder(self):
        if self.workspace.private.is_symlink() or self.folder.is_symlink():
            raise WorkspaceError('Review note folders cannot be links.')

    def _path(self, name):
        self._check_folder()
        if not isinstance(name, str) or not re.fullmatch(r'reply-[a-z0-9-]+\.md', name):
            raise WorkspaceError('Invalid draft identifier.')
        path = self.folder / (name + '.json')
        if path.is_symlink():
            raise WorkspaceError('Review note links are not supported.')
        return path

    def _read(self, name):
        path = self._path(name)
        if not path.exists():
            return None
        if path.stat().st_size > 16384:
            raise WorkspaceError('Review note is too large; preserve it for recovery.')
        from rrw_web import strict_object, reject_constant
        record = json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=strict_object,
                            parse_constant=reject_constant)
        if (not isinstance(record, dict) or set(record) != {'schema', 'draft_id', 'draft_revision',
                'recorded_at', 'target', 'source_kind', 'assessment', 'sha256'}
                or record.get('schema') != SCHEMA
                or record.get('draft_id') != name
                or record.get('sha256') != digest({k: v for k, v in record.items() if k != 'sha256'})
                or not isinstance(record.get('draft_revision'), str)
                or not re.fullmatch(r'[0-9a-f]{64}', record['draft_revision'])
                or not isinstance(record.get('recorded_at'), str) or len(record['recorded_at']) > 80
                or record.get('target') not in ('starting_reply', 'saved_reply')
                or record.get('source_kind') not in ('template', 'fallback', 'model_labelled', 'unknown')):
            raise WorkspaceError('Review note integrity failed; preserve it for recovery.')
        values(record.get('assessment'))
        return record

    def view(self, name, revision):
        try:
            record = self._read(name)
        except (OSError, ValueError, TypeError, KeyError):
            return {'revision': None, 'assessment': None, 'current': False,
                    'error': 'Saved notes need recovery. The file was preserved; draft approval is separate.'}
        if record is None:
            return {'revision': 'new', 'assessment': None, 'current': False}
        return {'revision': record['sha256'], 'assessment': record['assessment'],
                'current': record['draft_revision'] == revision,
                'recorded_at': record['recorded_at'], 'target': record['target']}

    def save(self, data):
        name = data.get('id')
        draft = self.workspace._revision(name, data.get('revision'))
        old = self._read(name)
        expected = old['sha256'] if old else 'new'
        if data.get('note_revision') != expected:
            raise WorkspaceError('Review notes changed elsewhere. Reload the saved notes before replacing them.', 409)
        assessment = values(data.get('assessment'))
        compared = comparison(draft)
        record = {'schema': SCHEMA, 'draft_id': name, 'draft_revision': data['revision'],
                  'recorded_at': datetime.now(timezone.utc).isoformat(),
                  'target': 'starting_reply' if compared['available'] else 'saved_reply',
                  'source_kind': source_kind(draft), 'assessment': assessment}
        record['sha256'] = digest(record)
        path = self._path(name)
        self.folder.mkdir(exist_ok=True)
        self.workspace._revision(name, data['revision'])
        rr.atomic_json(str(path), record)
        return self.view(name, data['revision'])

    def summary(self):
        report = {
            'schema': 'rrw-review-counts-v1', 'created_at': datetime.now(timezone.utc).isoformat(),
            'unit': 'One latest saved assessment per draft, not distinct people.',
            'interpretation': 'Self-reported judgments. No customer adoption, revenue, time saved or independent verification is implied.',
            'current': 0, 'stale': 0, 'missing_draft': 0, 'unreadable': 0,
            'counts': {role: {scenario: {choice: 0 for choice in DECISIONS} for scenario in SCENARIOS}
                       for role in ROLES},
            'sources': {key: 0 for key in ('template', 'fallback', 'model_labelled', 'unknown')},
            'reasons': {key: 0 for key in REASONS}, 'measured_review_time_records': 0,
        }
        self._check_folder()
        for path in sorted(self.folder.glob('reply-*.md.json')):
            name = path.name.removesuffix('.json')
            try:
                record = self._read(name)
                try:
                    _, revision = self.workspace._read(name)
                except WorkspaceError as exc:
                    if exc.status == 404 and not (self.workspace.drafts / name).exists():
                        report['missing_draft'] += 1
                        continue
                    raise
                if record['draft_revision'] != revision:
                    report['stale'] += 1
                    continue
                assessment = record['assessment']
                report['current'] += 1
                report['counts'][assessment['role']][assessment['scenario']][assessment['decision']] += 1
                report['sources'][record['source_kind']] += 1
                for reason in assessment['reasons']:
                    report['reasons'][reason] += 1
                report['measured_review_time_records'] += assessment['review_seconds'] is not None
            except (OSError, ValueError, TypeError, KeyError):
                report['unreadable'] += 1
        return report

    def dispatch(self, action, data):
        with self.workspace.lock:
            if action == 'feedback-save':
                return self.save(data)
            if action == 'feedback-summary':
                report = self.summary()
                return {'filename': 'review-assessment-counts.json',
                        'text': json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + '\n'}
            raise WorkspaceError('Unknown review assessment action.', 404)
