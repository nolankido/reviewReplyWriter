"""Private generation receipts: a disconnected client never needs a blind retry."""
from __future__ import annotations

import hashlib
import json
import re

import review_reply as rr
from rrw_workspace import WorkspaceError

SCHEMA = 'rrw-generation-request-v1'


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
        separators=(',', ':'), allow_nan=False).encode('utf-8')).hexdigest()


class GenerationRequests:
    def __init__(self, workspace):
        self.workspace = workspace
        self.directory = workspace.private / 'generation-requests'
        self.active = set()

    def _path(self, identifier):
        if not isinstance(identifier, str) or not re.fullmatch(r'[0-9a-f]{32}', identifier):
            raise WorkspaceError('Invalid generation request identifier.')
        path = self.directory / (identifier + '.json')
        if self.workspace.private.is_symlink() or self.directory.is_symlink() or path.is_symlink():
            raise WorkspaceError('Generation receipt links are not supported.')
        return path

    def _read(self, identifier):
        path = self._path(identifier)
        if not path.exists():
            return None
        if path.stat().st_size > 4096:
            raise WorkspaceError('Generation receipt is too large; preserve it for recovery.')
        from rrw_web import strict_object, reject_constant
        record = json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=strict_object,
                            parse_constant=reject_constant)
        if (not isinstance(record, dict) or set(record) != {'schema', 'request_id', 'fingerprint',
                'action', 'state', 'draft_id', 'revision', 'sha256'}
                or record['schema'] != SCHEMA or record['request_id'] != identifier
                or record['action'] not in ('generate', 'reroll')
                or record['state'] not in ('pending', 'saved', 'failed')
                or not isinstance(record['fingerprint'], str)
                or not re.fullmatch(r'[0-9a-f]{64}', record['fingerprint'])
                or record['sha256'] != digest({k: v for k, v in record.items() if k != 'sha256'})):
            raise WorkspaceError('Generation receipt integrity failed; the file was preserved.')
        if record['state'] == 'saved':
            if (not isinstance(record['draft_id'], str)
                    or not re.fullmatch(r'reply-[a-z0-9-]+\.md', record['draft_id'])
                    or not isinstance(record['revision'], str)
                    or not re.fullmatch(r'[0-9a-f]{64}', record['revision'])):
                raise WorkspaceError('Saved generation receipt is malformed.')
        elif record['draft_id'] is not None or record['revision'] is not None:
            raise WorkspaceError('Unfinished generation receipt is malformed.')
        return record

    def _save(self, record):
        record = {k: v for k, v in record.items() if k != 'sha256'}
        record['sha256'] = digest(record)
        rr.atomic_json(str(self._path(record['request_id'])), record)

    def _locate(self, record):
        # The draft carries the receipt too. A failed final checkpoint must not
        # cause another model call, even after the server is restarted.
        matches = []
        for name in rr.list_drafts(str(self.workspace.drafts)):
            try:
                draft, revision = self.workspace._read(name)
                if draft.get('generation_request') == {
                        'id': record['request_id'], 'fingerprint': record['fingerprint']}:
                    matches.append((name, revision))
            except (OSError, ValueError, TypeError, KeyError):
                continue
        if len(matches) > 1:
            raise WorkspaceError('Multiple matching saved drafts. Inspect the library before continuing.', 409)
        if matches:
            name, revision = matches[0]
            return dict(record, state='saved', draft_id=name, revision=revision)
        return record

    def check(self, identifier):
        with self.workspace.lock:
            record = self._read(identifier)
            if record is None:
                return {'state': 'unknown', 'draft_id': None, 'revision': None, 'draft_state': None}
            if record['state'] == 'pending':
                record = self._locate(record)
            state = record['state']
            if state == 'pending' and identifier not in self.active:
                state = 'interrupted'
            draft_state = None
            if state == 'saved':
                try:
                    _, actual = self.workspace._read(record['draft_id'])
                    draft_state = 'current' if actual == record['revision'] else 'changed'
                except WorkspaceError as exc:
                    draft_state = 'missing' if exc.status == 404 else 'unreadable'
                except (OSError, ValueError, TypeError, KeyError):
                    draft_state = 'unreadable'
            return {'state': state, 'draft_id': record['draft_id'], 'revision': record['revision'],
                    'draft_state': draft_state}

    def generate(self, data, reroll):
        identifier = data['request_id']
        self._path(identifier)
        action = 'reroll' if reroll else 'generate'
        fingerprint = digest({'action': action, 'inputs': {k: v for k, v in data.items() if k != 'request_id'}})
        with self.workspace.lock:
            record = self._read(identifier)
            if record is not None:
                if record['fingerprint'] != fingerprint or record['action'] != action:
                    raise WorkspaceError('This request identifier was used with different inputs.', 409)
                status = self.check(identifier)
                if status['state'] == 'saved' and status['draft_state'] == 'current':
                    return self.workspace._view(status['draft_id'])
                raise WorkspaceError('This request was already received. Check its saved result before starting another.', 409)
            if self.workspace.generation.locked():
                raise WorkspaceError('A draft is already being generated. Finish that run first.', 409)
            record = {'schema': SCHEMA, 'request_id': identifier, 'fingerprint': fingerprint,
                      'action': action, 'state': 'pending', 'draft_id': None, 'revision': None}
            self._save(record)  # Reserve before any model call or draft write.
            self.active.add(identifier)
        try:
            provenance = {'id': identifier, 'fingerprint': fingerprint}
            result = self.workspace.generate(data, reroll, request=provenance)
            with self.workspace.lock:
                self._save(dict(record, state='saved', draft_id=result['id'], revision=result['revision']))
            return result
        except Exception:
            with self.workspace.lock:
                # Preserve a durable pending reservation if the disk cannot
                # record failure. It will never be automatically replayed.
                try:
                    recovered = self._locate(record)
                    self._save(recovered if recovered['state'] == 'saved' else dict(record, state='failed'))
                except (OSError, ValueError, TypeError, KeyError):
                    pass
            raise
        finally:
            with self.workspace.lock:
                self.active.discard(identifier)
