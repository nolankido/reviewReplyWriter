"""A local CSV review queue. Import never authorizes policy or posting.

Each click handles one review. Checkpoints and draft provenance allow recovery
after a crash without silently creating another copy of a saved draft.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import unicodedata
import uuid
from datetime import datetime, timezone

import review_reply as rr
from reply_safety import DraftBlocked
from rrw_risk import manual_review_findings
from rrw_workspace import WorkspaceError, text

MAX_CSV_BYTES = 48 * 1024
MAX_ROWS = 50
SCHEMA = 'rrw-inbox-v1'
STATUSES = {'pending', 'manual', 'invalid', 'duplicate', 'generating',
            'drafted', 'blocked', 'error', 'interrupted', 'skipped'}
SETTINGS = {'business', 'kind', 'tone', 'platform', 'signoff'}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
        separators=(',', ':'), allow_nan=False).encode('utf-8')).hexdigest()


def norm(value):
    return ' '.join(unicodedata.normalize('NFKC', value).casefold().split())


def review_key(business, review, stars):
    return digest([norm(business), norm(review), stars])


def parse_csv(source):
    if not isinstance(source, str) or len(source.encode('utf-8')) > MAX_CSV_BYTES:
        raise WorkspaceError('Choose a UTF-8 CSV of at most 48 KiB.')
    try:
        reader = csv.reader(io.StringIO(source.lstrip('\ufeff'), newline=''), strict=True)
        header = next(reader, [])
        names = [name.strip().lower() for name in header]
        if not names or len(names) != len(set(names)) or 'review' not in names:
            raise WorkspaceError('CSV needs one review column; column names must be unique.')
        if set(names) - {'review', 'stars', 'review_id'}:
            raise WorkspaceError('Supported CSV columns: review, stars, review_id. Business settings and owner promises must not come from the file.')
        rows = []
        for raw in reader:
            if not raw or not any(x.strip() for x in raw):
                continue
            if len(rows) >= MAX_ROWS:
                raise WorkspaceError('Import at most 50 reviews per inbox.')
            row = dict(row=len(rows) + 2, review='', stars=None, external_id='',
                       status='pending', findings=[])
            rows.append(row)
            if len(raw) != len(names):
                row.update(status='invalid', findings=['Cell count does not match the header.'])
                continue
            values = dict(zip(names, raw))
            try:
                row['review'] = text(values['review'], 'Review', rr.MAX_REVIEW_CHARS, True)
                row['external_id'] = text(values.get('review_id', ''), 'Review ID', 120)
                rating = values.get('stars', '').strip()
                if rating and rating not in ('1', '2', '3', '4', '5'):
                    raise WorkspaceError('Rating must be blank or an integer from 1 to 5.')
                row['stars'] = int(rating) if rating else None
                row['findings'] = manual_review_findings(row['review'])
                if row['findings']:
                    row['status'] = 'manual'
            except ValueError as exc:
                row.update(status='invalid', findings=[str(exc)])
        if not rows:
            raise WorkspaceError('The CSV contains no review rows.')
        return rows
    except csv.Error as exc:
        raise WorkspaceError('CSV quoting is malformed. Export it as a standard UTF-8 CSV.') from exc


class ReviewInbox:
    def __init__(self, workspace):
        self.workspace = workspace
        self.folder = workspace.private / 'inboxes'
        if workspace.private.is_symlink() or self.folder.is_symlink():
            raise WorkspaceError('Inbox folders cannot be symbolic links.')
        self.folder.mkdir(exist_ok=True)
        self.active = None

    def settings(self, values):
        if not isinstance(values, dict) or set(values) - SETTINGS:
            raise WorkspaceError('Inbox settings accept only business, kind, tone, platform and signoff. No owner commitments are imported.')
        return self.workspace._inputs(dict(values, offer='', approved_actions=[]))

    def _path(self, name):
        if self.workspace.private.is_symlink() or self.folder.is_symlink():
            raise WorkspaceError('Inbox folders cannot be symbolic links.')
        if not isinstance(name, str) or not re.fullmatch(r'inbox-[0-9a-f]{32}', name):
            raise WorkspaceError('Invalid inbox identifier.')
        path = self.folder / (name + '.json')
        if path.is_symlink():
            raise WorkspaceError('Inbox links are not supported.')
        return path

    def _read(self, name, revision=None):
        path = self._path(name)
        if not path.exists():
            raise WorkspaceError('Inbox not found.', 404)
        if path.stat().st_size > 512000:
            raise WorkspaceError('Inbox is too large to read safely.')
        from rrw_web import strict_object, reject_constant
        record = json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=strict_object,
                            parse_constant=reject_constant)
        if not isinstance(record, dict) or record.get('schema') != SCHEMA or record.get('id') != name:
            raise WorkspaceError('Inbox state is malformed; preserve the file for recovery.')
        actual = digest({k: v for k, v in record.items() if k != 'sha256'})
        if record.get('sha256') != actual:
            raise WorkspaceError('Inbox integrity check failed; preserve the file for recovery.')
        if revision is not None and revision != actual:
            raise WorkspaceError('Inbox changed elsewhere. Reload it before continuing.', 409)
        saved = record.get('settings', {})
        if saved.get('offer') or saved.get('approved_actions'):
            raise WorkspaceError('Inbox state contains unsupported commitments.')
        request_settings = {k: v for k, v in saved.items() if k in SETTINGS}
        if request_settings.get('signoff') is None:
            request_settings['signoff'] = ''
        if self.settings(request_settings) != saved:
            raise WorkspaceError('Inbox business settings are malformed.')
        rows = record.get('rows')
        if not isinstance(rows, list) or not 1 <= len(rows) <= MAX_ROWS:
            raise WorkspaceError('Inbox row list is malformed.')
        ids = set()
        for row in rows:
            if not isinstance(row, dict) or row.get('status') not in STATUSES or \
                    not re.fullmatch(r'[0-9a-f]{32}', str(row.get('id', ''))) or row['id'] in ids:
                raise WorkspaceError('Inbox row state is malformed.')
            ids.add(row['id'])
            text(row.get('review'), 'Review', rr.MAX_REVIEW_CHARS,
                 required=row['status'] not in ('invalid', 'duplicate'))
            text(row.get('external_id'), 'Review ID', 120)
            if row['status'] not in ('invalid', 'duplicate'):
                stars = row.get('stars')
                if stars is not None and (type(stars) is not int or not 1 <= stars <= 5):
                    raise WorkspaceError('Saved inbox rating is malformed.')
        return record

    def _save(self, record):
        record['updated_at'] = datetime.now(timezone.utc).isoformat()
        record['sha256'] = digest({k: v for k, v in record.items() if k != 'sha256'})
        rr.atomic_json(str(self._path(record['id'])), record)
        return record

    def _revision(self, data):
        value = data.get('revision')
        if not isinstance(value, str) or not re.fullmatch(r'[0-9a-f]{64}', value):
            raise WorkspaceError('Reload the inbox before changing it.', 409)
        return value

    def _known(self, business):
        keys, external, warnings = set(), {}, []
        for name in rr.list_drafts(str(self.workspace.drafts)):
            try:
                draft, _ = self.workspace._read(name)
                if norm(draft.get('business', '')) == norm(business):
                    keys.add(review_key(business, draft['review'], draft.get('stars')))
            except (OSError, ValueError, TypeError, KeyError):
                warnings.append('A saved draft could not be checked for duplicates.')
        for path in sorted(self.folder.glob('inbox-*.json')):
            record = self._read(path.stem)
            if norm(record['settings']['business']) != norm(business):
                continue
            for row in record['rows']:
                if row['status'] in ('invalid', 'duplicate', 'skipped'):
                    continue
                key = review_key(business, row['review'], row['stars'])
                keys.add(key)
                if row['external_id']:
                    external[row['external_id']] = key
        return keys, external, list(dict.fromkeys(warnings))

    def preview(self, data):
        settings = self.settings(data.get('settings'))
        rows = parse_csv(data.get('csv'))
        known, external, warnings = self._known(settings['business'])
        seen, local_ids = {}, {}
        for row in rows:
            if row['status'] == 'invalid':
                continue
            key = review_key(settings['business'], row['review'], row['stars'])
            ident = row['external_id']
            if ident and ((ident in external and external[ident] != key) or
                          (ident in local_ids and local_ids[ident]['key'] != key)):
                row.update(status='invalid', findings=['Review ID conflicts with different wording or rating. Check the source file.'])
                if ident in local_ids:
                    local_ids[ident]['row'].update(status='invalid', findings=list(row['findings']))
            elif key in known or key in seen or (ident and ident in external):
                row.update(status='duplicate', findings=['Already present in this business workspace or repeated in the file.'])
            else:
                seen[key] = row
            if ident and ident not in local_ids:
                local_ids[ident] = {'key': key, 'row': row}
        result = dict(settings=settings, rows=rows, warnings=warnings,
                      source_sha256=hashlib.sha256(data['csv'].encode('utf-8')).hexdigest())
        result['revision'] = digest(result)
        result['counts'] = {status: sum(r['status'] == status for r in rows)
                            for status in ('pending', 'manual', 'invalid', 'duplicate')}
        return result

    def create(self, data):
        if data.get('confirmed') is not True:
            raise WorkspaceError('Confirm that the reviews belong to the selected business.')
        preview = self.preview(data)
        if data.get('preview_revision') != preview['revision']:
            raise WorkspaceError('Import preview changed. Preview the file again before saving.', 409)
        if not any(r['status'] in ('pending', 'manual') for r in preview['rows']):
            raise WorkspaceError('No new valid or manual-review rows are available to import.')
        record = dict(schema=SCHEMA, id='inbox-' + uuid.uuid4().hex,
            label=text(data.get('label', 'Review inbox'), 'Inbox name', 140, True),
            created_at=datetime.now(timezone.utc).isoformat(), settings=preview['settings'],
            source_sha256=preview['source_sha256'],
            rows=[dict(r, id=uuid.uuid4().hex) for r in preview['rows']])
        return self._view(self._save(record))

    def _recover(self, record):
        if self.active == record['id']:
            return record
        changed = False
        for row in record['rows']:
            if row['status'] != 'generating':
                continue
            found = []
            for name in rr.list_drafts(str(self.workspace.drafts)):
                draft, _ = self.workspace._read(name)
                if draft.get('inbox_id') == record['id'] and draft.get('inbox_row_id') == row['id']:
                    found.append((name, draft))
            if len(found) == 1:
                row.update(status='drafted', draft_id=found[0][0], engine=found[0][1].get('engine'), findings=[])
            else:
                row.update(status='interrupted', findings=['Drafting was interrupted. Inspect the saved library before choosing Retry.'])
                if found:
                    row.update(status='error', findings=['Multiple saved drafts match this row. Inspect the library; automatic retry is disabled.'], recovery_conflict=True)
            changed = True
        return self._save(record) if changed else record

    def _view(self, record):
        rows = []
        for item in record['rows']:
            row = dict(item)
            if row.get('draft_id'):
                try:
                    view = self.workspace._view(row['draft_id'])
                    row['draft_status'] = view['status']
                except (OSError, ValueError, TypeError, KeyError):
                    row['draft_status'] = 'unavailable'
            rows.append(row)
        return dict(record, revision=record['sha256'], rows=rows,
                    active=self.active == record['id'],
                    counts={status: sum(r['status'] == status for r in rows) for status in STATUSES})

    def step(self, data):
        if data.get('mode') not in ('offline', 'gemma'):
            raise WorkspaceError('Choose Gemma or template preview.')
        if not self.workspace.generation.acquire(blocking=False):
            raise WorkspaceError('A draft is already being generated. Finish it first.', 409)
        try:
            with self.workspace.lock:
                record = self._read(data.get('id'), self._revision(data))
                self._recover(record)
                row = next((r for r in record['rows'] if r['status'] == 'pending'), None)
                if row is None:
                    raise WorkspaceError('No pending rows remain. Review the drafts and manual items.', 409)
                self.workspace._state()  # Fail before inference if approval state needs recovery.
                row.update(status='generating', findings=[])
                self.active = record['id']
                reserved = self._save(record)['sha256']
            result = None
            try:
                values = {k: v for k, v in record['settings'].items() if k in SETTINGS}
                values['signoff'] = values.get('signoff') or ''
                draft = self.workspace._new_draft(dict(values, review=row['review'], stars=row['stars']))
                draft.update(inbox_id=record['id'], inbox_row_id=row['id'])
                result = self.workspace._generate(draft, data['mode'])
            except DraftBlocked as exc:
                row.update(status='manual' if any('manual review required' in f for f in exc.findings) else 'blocked', findings=exc.findings)
            except (OSError, ValueError, TypeError, KeyError) as exc:
                row.update(status='error', findings=[str(exc)[:600]])
            with self.workspace.lock:
                self._read(record['id'], reserved)
                if result is not None:
                    view = self.workspace._write(result)
                    row.update(status='drafted', draft_id=view['id'], engine=view['engine'], findings=[])
                return self._view(self._save(record))
        finally:
            self.active = None
            self.workspace.generation.release()

    def dispatch(self, action, data):
        if action == 'inbox-step':
            return self.step(data)
        with self.workspace.lock:
            if action == 'inbox-preview':
                return self.preview(data)
            if action == 'inbox-create':
                return self.create(data)
            if action == 'inbox-list':
                records = []
                for path in sorted(self.folder.glob('inbox-*.json'), reverse=True):
                    r = self._view(self._recover(self._read(path.stem)))
                    records.append({k: r[k] for k in ('id', 'label', 'settings', 'counts', 'created_at')})
                return {'inboxes': records}
            record = self._read(data.get('id'), None if action == 'inbox-get' else self._revision(data))
            if action == 'inbox-get':
                return self._view(self._recover(record))
            if self.active == record['id']:
                raise WorkspaceError('Finish the active review before changing this inbox.', 409)
            row = next((r for r in record['rows'] if r['id'] == data.get('row_id')), None)
            if row is None:
                raise WorkspaceError('Review row not found.', 404)
            if action == 'inbox-skip' and row['status'] in ('pending', 'interrupted', 'error'):
                row.update(status='skipped')
            elif action == 'inbox-retry' and row['status'] in ('interrupted', 'error') and not row.get('recovery_conflict'):
                # Recover a saved candidate before retrying, even if the earlier
                # final inbox checkpoint could not be written.
                row['status'] = 'generating'
                self._recover(record)
                if row['status'] == 'interrupted':
                    row.update(status='pending', findings=[])
            else:
                raise WorkspaceError('This row cannot use that action.', 409)
            return self._view(self._save(record))
