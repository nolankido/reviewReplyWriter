"""One explicit private working copy. Recovery never grants policy or approval."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import re

import review_reply as rr
from rrw_workspace import WorkspaceError, text

SCHEMA = 'rrw-working-copy-v1'
MAX_BYTES = 96 * 1024
INPUT_FIELDS = {'business', 'kind', 'tone', 'platform', 'offer', 'signoff', 'approved_actions',
                'review', 'stars', 'followup', 'original', 'previous', 'mode'}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
        separators=(',', ':'), allow_nan=False).encode('utf-8')).hexdigest()


def working_copy(data):
    if not isinstance(data, dict) or set(data) != {'inputs', 'editor'}:
        raise WorkspaceError('Working copy must contain review inputs and optional reply edits only.')
    inputs = data['inputs']
    if not isinstance(inputs, dict) or set(inputs) != INPUT_FIELDS:
        raise WorkspaceError('Recovery fields are missing or unsupported. Authorization and approval are excluded.')
    result = dict(inputs)
    for key, maximum in (('business', 150), ('offer', 2000), ('signoff', 200),
                         ('review', rr.MAX_REVIEW_CHARS), ('original', rr.MAX_REVIEW_CHARS),
                         ('previous', rr.MAX_REVIEW_CHARS)):
        # Incomplete inputs are allowed. Semantic checks apply during generation.
        result[key] = text(inputs[key], key, maximum)
    for key, choices in (('kind', rr.KINDS), ('tone', rr.TONES), ('platform', rr.PLATFORMS),
                         ('mode', ('offline', 'gemma'))):
        if not isinstance(inputs[key], str) or inputs[key] not in choices:
            raise WorkspaceError('Unsupported recovery ' + key + '.')
    if type(inputs['followup']) is not bool:
        raise WorkspaceError('Recovery conversation choice must be boolean.')
    if inputs['stars'] is not None and (type(inputs['stars']) is not int or inputs['stars'] not in range(1, 6)):
        raise WorkspaceError('Recovery rating must be blank or an integer from 1 to 5.')
    actions = inputs['approved_actions']
    if not isinstance(actions, list) or len(actions) > 8:
        raise WorkspaceError('Recovery accepts at most eight statement inputs.')
    result['approved_actions'] = [text(a, 'Statement input', 2000) for a in actions]
    result['mode'] = 'offline'  # A recovered copy must not silently select model generation.
    editor = data['editor']
    if editor is not None:
        if not isinstance(editor, dict) or set(editor) != {'id', 'revision', 'reply'}:
            raise WorkspaceError('Reply recovery accepts an identifier, revision and text only.')
        if not isinstance(editor['id'], str) or not re.fullmatch(r'reply-[a-z0-9-]{1,150}\.md', editor['id']):
            raise WorkspaceError('Invalid recovery draft identifier.')
        if not isinstance(editor['revision'], str) or not re.fullmatch(r'[0-9a-f]{64}', editor['revision']):
            raise WorkspaceError('A saved draft fingerprint is required for reply recovery.')
        if not isinstance(editor['reply'], str) or len(editor['reply']) > 20000:
            raise WorkspaceError('Recovered reply edits must be text of at most 20000 characters.')
        text(editor['reply'], 'Reply edits', 20000)  # Check controls while preserving exact spacing.
        editor = dict(editor)
    payload = {'inputs': result, 'editor': editor}
    if len(json.dumps(payload, ensure_ascii=False, allow_nan=False).encode('utf-8')) > MAX_BYTES:
        raise WorkspaceError('Working copy exceeds 96 KiB. Your editor was kept; shorten inputs before saving a copy.')
    return payload


class Recovery:
    def __init__(self, workspace):
        self.workspace = workspace
        self.path = workspace.private / 'working-copy.json'

    def _read(self):
        if self.workspace.private.is_symlink() or self.path.is_symlink():
            raise WorkspaceError('Working copy links are not supported.')
        if not self.path.exists():
            return None
        if self.path.stat().st_size > MAX_BYTES + 4096:
            raise WorkspaceError('Working copy is too large; preserve it for recovery.')
        from rrw_web import strict_object, reject_constant
        record = json.loads(self.path.read_text(encoding='utf-8'), object_pairs_hook=strict_object,
                            parse_constant=reject_constant)
        if (not isinstance(record, dict) or set(record) != {'schema', 'saved_at', 'payload', 'sha256'}
                or record['schema'] != SCHEMA or not isinstance(record['saved_at'], str)
                or len(record['saved_at']) > 80
                or record['sha256'] != digest({k: v for k, v in record.items() if k != 'sha256'})):
            raise WorkspaceError('Working copy integrity failed; the file was preserved.')
        if record['payload'] is not None:
            payload = working_copy(record['payload'])
            if payload != record['payload']:
                raise WorkspaceError('Stored working copy is not normalized; preserve it for recovery.')
        return record

    def _view(self, record):
        payload = record['payload'] if record else None
        state = 'none'
        if payload and payload['editor']:
            editor = payload['editor']
            try:
                _, revision = self.workspace._read(editor['id'])
                state = 'current' if revision == editor['revision'] else 'changed'
            except WorkspaceError as exc:
                state = 'missing' if exc.status == 404 else 'unreadable'
            except (OSError, ValueError, TypeError, KeyError):
                state = 'unreadable'
        return {'revision': record['sha256'] if record else 'new',
                'available': payload is not None, 'saved_at': record['saved_at'] if record else None,
                'payload': payload, 'editor_state': state}

    def dispatch(self, action, data):
        with self.workspace.lock:
            old = self._read()
            if action == 'recovery-get':
                return self._view(old)
            if action not in ('recovery-save', 'recovery-clear'):
                raise WorkspaceError('Unknown recovery action.', 404)
            expected = old['sha256'] if old else 'new'
            if data.get('revision') != expected:
                raise WorkspaceError('Recovery copy changed elsewhere. Check the saved copy before replacing it.', 409)
            payload = working_copy(data.get('payload')) if action == 'recovery-save' else None
            record = {'schema': SCHEMA, 'saved_at': datetime.now(timezone.utc).isoformat(), 'payload': payload}
            record['sha256'] = digest(record)
            # Retain a content-free revision after clearing, so stale tabs cannot resurrect an old copy.
            rr.atomic_json(str(self.path), record)
            return self._view(record)
