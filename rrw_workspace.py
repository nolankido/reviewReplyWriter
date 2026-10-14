"""Local browser workspace over the existing checked drafting engine.

No publishing integration. The saved CLI drafts and approval format are shared.
Web requests never get to choose filesystem paths, model endpoints, or engines.
"""
from __future__ import annotations

import json
import random
import re
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import review_reply as rr
from reply_safety import SAFETY_VERSION, content_fingerprint, require_valid

MAX_REPLY_CHARS = 20000
MAX_FILE_BYTES = 512000


class WorkspaceError(ValueError):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


def text(value, label, maximum, required=False):
    if not isinstance(value, str) or len(value) > maximum:
        raise WorkspaceError(f"{label} must be text of at most {maximum} characters.")
    value = value.strip()
    if required and not value:
        raise WorkspaceError(f"{label} is required.")
    if any(ord(c) < 32 and c not in '\n\r\t' for c in value):
        raise WorkspaceError(f"{label} contains unsupported control characters.")
    return value


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise urllib.error.URLError("Local model redirects are not allowed")


def local_request(path, payload=None, timeout=3):
    """Use loopback directly, without environment proxies or HTTP redirects."""
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    body = None if payload is None else json.dumps(payload).encode('utf-8')
    req = urllib.request.Request('http://127.0.0.1:11434' + path, data=body,
                                 headers={'Content-Type': 'application/json'})
    with opener.open(req, timeout=timeout) as response:
        data = response.read(2 * 1024 * 1024 + 1)
    if len(data) > 2 * 1024 * 1024:
        raise ValueError('Local model response exceeded the size limit')
    return json.loads(data)


def gemma_caller(prompt, model, temperature):
    if model != rr.DEFAULT_MODEL:
        raise ValueError('The browser workspace uses the downloaded gemma3:4b model only')
    result = local_request('/api/generate', {
        'model': model, 'prompt': prompt, 'stream': False,
        'options': {'temperature': temperature, 'num_predict': 500}}, timeout=180)
    from rrw_model import checked_response
    return checked_response(result)


def model_status():
    from rrw_model import inspect_model
    return inspect_model(local_request)


class Workspace:
    def __init__(self, root, caller=None):
        self.root = Path(root).resolve()
        from rrw_backup import require_complete_recovery
        try:
            require_complete_recovery(self.root)
        except (OSError, ValueError) as exc:
            raise WorkspaceError('Recovered workspace cannot be opened safely. Preserve it and recover the backup into another new directory.') from exc
        self.drafts = self.root / 'replies'
        self.private = self.root / '.rrw'
        self.profiles = self.private / 'profiles.json'
        self.ledger = self.root / 'gap_ledger.json'
        self.drafts.mkdir(parents=True, exist_ok=True)
        self.private.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self.generation = threading.Lock()
        self.caller = caller or gemma_caller
        self.evaluations = None
        self.inboxes = None
        self.review_notes = None
        self.recovery = None
        self.requests = None

    def _notes(self):
        if self.review_notes is None:
            from rrw_feedback import ReviewNotes
            self.review_notes = ReviewNotes(self)
        return self.review_notes

    def _path(self, name):
        if not isinstance(name, str) or not re.fullmatch(r'reply-[a-z0-9-]+\.md', name):
            raise WorkspaceError('Invalid draft identifier.')
        path = self.drafts / name
        if path.is_symlink() or path.resolve().parent != self.drafts.resolve():
            raise WorkspaceError('Draft links are not supported.')
        if not path.is_file():
            raise WorkspaceError('Draft no longer exists.', 404)
        if path.stat().st_size > MAX_FILE_BYTES:
            raise WorkspaceError('Draft is too large to open safely.')
        return path

    def _read(self, name):
        path = self._path(name)
        before = content_fingerprint(path)
        draft = rr.parse_draft(path)
        if before != content_fingerprint(path):
            raise WorkspaceError('Draft changed while opening it. Reload and review again.', 409)
        if not isinstance(draft.get('review'), str) or not isinstance(draft.get('reply'), str):
            raise WorkspaceError('Saved draft is malformed; the original file was not changed.')
        if len(draft['reply']) > MAX_REPLY_CHARS:
            raise WorkspaceError('Saved reply is too large to edit in the browser.')
        return draft, before

    def _state(self):
        path = self.drafts / rr.TRIAGE_NAME
        if not path.exists():
            return {}
        if path.is_symlink() or path.stat().st_size > MAX_FILE_BYTES:
            raise WorkspaceError('Approval state cannot be read safely.')
        state = json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(state, dict):
            raise WorkspaceError('Approval state is malformed; restore it from backup.')
        for name, item in state.items():
            if not re.fullmatch(r'reply-[a-z0-9-]+\.md', name) or not isinstance(item, dict):
                raise WorkspaceError('Approval state is malformed; restore it from backup.')
            if item.get('status', 'pending') not in ('pending', 'approved', 'aside'):
                raise WorkspaceError('Approval status is malformed.')
        return state

    def _view(self, name, state=None):
        from rrw_feedback import comparison
        from rrw_generation_status import summary
        draft, revision = self._read(name)
        findings = rr.draft_findings(draft)
        state = self._state() if state is None else state
        entry = state.get(name, {})
        status = entry.get('status', 'pending')
        current = (entry.get('content_sha256') == revision and
                   entry.get('safety_version') == SAFETY_VERSION)
        invalidated = status == 'approved' and not current
        if invalidated:
            status = 'pending'
        if findings:
            status = 'blocked'
        import review_quality as quality
        review_evidence = quality.coverage(rr._body(draft['reply'], draft.get('signoff')),
            draft['review'], None if 'original' in draft else draft.get('stars'))
        review_evidence.update(source=draft['review'],
            source_label='Customer update' if 'original' in draft else 'Customer review')
        return dict(draft, id=name, revision=revision, findings=findings,
                    reply_comparison=comparison(draft), review_note=self._notes().view(name, revision),
                    review_evidence=review_evidence,
                    generation_status=summary(draft),
                    status=status, approval_invalidated=invalidated,
                    word_count=len(draft['reply'].split()),
                    word_target=rr.PLATFORMS.get(draft.get('platform'), rr.PLATFORMS['generic']))

    def _revision(self, name, revision):
        draft, actual = self._read(name)
        if not isinstance(revision, str) or revision != actual:
            raise WorkspaceError('This draft changed elsewhere. Reload it before continuing.', 409)
        return draft

    def _profiles(self):
        if self.profiles.is_symlink() or (self.profiles.exists() and self.profiles.stat().st_size > MAX_FILE_BYTES):
            raise WorkspaceError('Profile state cannot be read safely.')
        # Do not silently import sample compensation policies from profiles.json.
        values = rr.load_profiles(str(self.profiles))
        revision = content_fingerprint(self.profiles) if self.profiles.exists() else 'new'
        return values, revision

    def _inputs(self, data):
        business = text(data.get('business', ''), 'Business name', 150, True)
        kind, tone = data.get('kind', 'cafe'), data.get('tone', 'professional')
        if kind not in rr.KINDS or tone not in rr.TONES:
            raise WorkspaceError('Choose a supported business type and tone.')
        offer = text(data.get('offer', ''), 'Owner offer', 2000) or None
        signoff = text(data.get('signoff', ''), 'Sign-off', 200) or None
        actions = data.get('approved_actions', [])
        if not isinstance(actions, list) or len(actions) > 8:
            raise WorkspaceError('Use at most eight owner-approved statements.')
        actions = [text(x, 'Owner-approved statement', 2000, True) for x in actions]
        if (offer or actions) and data.get('policy_confirmed') is not True:
            raise WorkspaceError('Confirm that the owner authorized these statements for this business.')
        platform = data.get('platform', 'google')
        rr.validate_input('profile', None, platform, offer, actions)
        return dict(business=business, kind=kind, tone=tone, platform=platform,
                    offer=offer, signoff=signoff, approved_actions=actions)

    def _new_draft(self, data):
        draft = self._inputs(data)
        draft['review'] = text(data.get('review', ''), 'Review', rr.MAX_REVIEW_CHARS, True)
        draft['stars'] = data.get('stars')
        rr.validate_input(draft['review'], draft['stars'], draft['platform'],
                          draft['offer'], draft['approved_actions'])
        draft['choices'] = 1
        profile_key = data.get('profile_key')
        if profile_key:
            profiles, _ = self._profiles()
            profile = profiles.get(profile_key)
            if not profile or rr._norm(profile.get('business', '')) != rr._norm(draft['business']):
                raise WorkspaceError('Selected profile belongs to a different business. Choose a matching profile.')
            if profile.get('voice'):
                draft['voice'] = profile['voice']
                if not draft['signoff']:
                    draft['signoff'] = text(profile['voice'].get('signoff', '') or '', 'Voice sign-off', 200) or None
        if data.get('followup', False) is True:
            draft['original'] = text(data.get('original', ''), 'Original review', rr.MAX_REVIEW_CHARS, True)
            draft['previous'] = text(data.get('previous', ''), 'Previously posted reply', rr.MAX_REVIEW_CHARS, True)
            rr.validate_input(draft['original'], None, draft['platform'],
                              draft['offer'], draft['approved_actions'])
            draft['stars'] = None  # The existing follow-up engine grades the update text.
        return draft

    def _generate(self, draft, mode, *, observe=None, record_ledger=True):
        if mode not in ('offline', 'gemma'):
            raise WorkspaceError('Choose Gemma or template preview.')
        trace = []
        common = {k: draft.get(k) for k in ('offer', 'signoff', 'platform', 'approved_actions')}
        followup = 'original' in draft and 'previous' in draft

        def observed(prompt, model, temperature):
            started = time.monotonic()
            item = {'attempt': len(trace) + 1, 'temperature': temperature}
            if observe is not None:
                import hashlib
                item['prompt_sha256'] = hashlib.sha256(prompt.encode('utf-8')).hexdigest()
            try:
                answer = self.caller(prompt, model, temperature)
                item['findings'] = rr.draft_findings(dict(draft, reply=answer))
                if hasattr(answer, 'receipt'):
                    item['receipt'] = answer.receipt
                if observe is not None:
                    item['candidate'] = str(answer) if isinstance(answer, str) else None
                return answer
            except (OSError, ValueError, KeyError, urllib.error.URLError) as exc:
                item['failure'] = 'unavailable' if isinstance(exc, OSError) else 'invalid_response'
                item['findings'] = [f'Model call failed: {exc}']
                raise
            finally:
                item['elapsed_ms'] = round((time.monotonic() - started) * 1000)
                trace.append(item)
                if observe is not None:
                    observe(dict(item))

        reply, engine = None, 'template engine (offline)'
        if mode == 'gemma':
            settings = dict(caller=observed, ledger_path=str(self.ledger) if record_ledger else None, voice=draft.get('voice'), **common)
            if followup:
                reply, engine = rr.generate_followup(
                    draft['original'], draft['previous'], draft['review'], draft['business'],
                    draft['tone'], draft['kind'], rr.DEFAULT_MODEL, **settings)
            else:
                reply, engine = rr.generate_with_model(
                    draft['review'], draft['business'], draft['tone'], draft['stars'],
                    draft['kind'], rr.DEFAULT_MODEL, **settings)
        from rrw_generation_status import outcome
        generation_outcome = outcome(mode, reply is None, reply, trace)
        if reply is None:
            if followup:
                reply = rr.template_followup(draft['original'], draft['previous'], draft['review'],
                    draft['business'], draft['tone'], draft['kind'], random.Random(0), **common)
            else:
                reply = rr.template_reply(draft['review'], draft['business'], draft['tone'],
                    draft['stars'], draft['kind'], random.Random(0), **common)
            engine = ('template engine (offline)' if mode == 'offline' else
                      f"template engine (fallback: {generation_outcome['state']})")
        result = dict(draft, reply=reply, engine=engine, generation_trace=trace,
                      generation_outcome=generation_outcome,
                      generated_at=datetime.now(timezone.utc).isoformat(), human_edited=False)
        result['generation_baseline'] = {key: str(result[key]) for key in ('reply', 'engine', 'generated_at')}
        result['tier'] = rr.review_tier(draft['review'], None if followup else draft.get('stars'))
        require_valid(rr.draft_findings(result))  # Independent final output check.
        return result

    def _write(self, draft, name=None):
        context = {k: draft[k] for k in ('stars', 'offer', 'signoff', 'approved_actions',
            'original', 'previous', 'choices', 'voice', 'generation_trace', 'generation_outcome', 'generated_at',
            'human_edited', 'generation_baseline', 'inbox_id', 'inbox_row_id', 'generation_request') if k in draft}
        args = (draft['business'], draft['review'], draft['reply'],
                draft.get('engine', 'imported draft'), draft['tone'], draft['kind'],
                draft.get('tier') or rr.review_tier(draft['review'], draft.get('stars')),
                draft.get('platform', 'generic'))
        if name is None:
            name = Path(rr.save_reply_file(str(self.drafts), *args, **context)).name
        else:
            rr._write_reply_file(self._path(name), *args, **context)
        state = self._state()
        state[name] = {'status': 'pending'}
        rr.save_triage(str(self.drafts), state)
        return self._view(name)

    def generate(self, data, reroll=False, *, request=None):
        if not self.generation.acquire(blocking=False):
            raise WorkspaceError('A draft is already being generated. Finish that run first.', 409)
        try:
            with self.lock:
                self._state()  # Fail before generation if approval state needs recovery.
                draft = (self._revision(data.get('id'), data.get('revision')) if reroll
                         else self._new_draft(data))
            result = self._generate(draft, data.get('mode', 'offline'))
            result.pop('generation_request', None)
            if request is not None:
                result['generation_request'] = request
            with self.lock:
                if reroll:
                    self._revision(data['id'], data.get('revision'))
                return self._write(result, data['id'] if reroll else None)
        finally:
            self.generation.release()

    def dispatch(self, action, data=None):
        data = {} if data is None else data
        if not isinstance(data, dict):
            raise WorkspaceError('Request must be a JSON object.')
        if action == 'generation-check' or (action in ('generate', 'reroll') and 'request_id' in data):
            from rrw_requests import GenerationRequests
            with self.lock:
                if self.requests is None:
                    self.requests = GenerationRequests(self)
            if action == 'generation-check':
                return self.requests.check(data.get('request_id'))
            return self.requests.generate(data, action == 'reroll')
        if action.startswith('recovery-'):
            from rrw_recovery import Recovery
            with self.lock:
                if self.recovery is None:
                    self.recovery = Recovery(self)
                return self.recovery.dispatch(action, data)
        if action.startswith('feedback-'):
            with self.lock:
                return self._notes().dispatch(action, data)
        if action.startswith('inbox-'):
            from rrw_inbox import ReviewInbox
            with self.lock:
                if self.inboxes is None:
                    self.inboxes = ReviewInbox(self)
            return self.inboxes.dispatch(action, data)
        if action.startswith('quality-'):
            from rrw_evaluate import EvaluationLab
            with self.lock:
                if self.evaluations is None:
                    self.evaluations = EvaluationLab(self)
            return self.evaluations.dispatch(action, data)
        if action in ('generate', 'reroll'):
            return self.generate(data, action == 'reroll')
        with self.lock:
            if action == 'state':
                values, revision = self._profiles()
                state, drafts = self._state(), []
                for name in reversed(rr.list_drafts(str(self.drafts))):
                    try:
                        view = self._view(name, state)
                        drafts.append({k: view.get(k) for k in ('id', 'business', 'review', 'tier',
                                      'status', 'engine', 'human_edited', 'generated_at')})
                    except (OSError, ValueError, TypeError, KeyError):
                        drafts.append({'id': name, 'business': 'Unreadable draft', 'review': '',
                                       'status': 'blocked', 'error': 'File needs recovery; it was not changed.'})
                return {'drafts': drafts, 'profiles': values, 'profiles_revision': revision,
                        'generating': self.generation.locked(), 'safety_version': SAFETY_VERSION}
            if action == 'get':
                return self._view(data.get('id'))
            if action == 'profile':
                name = data.get('name')
                if not isinstance(name, str) or not re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,39}', name):
                    raise WorkspaceError('Profile key: 1-40 lowercase letters, numbers, hyphens or underscores.')
                values, revision = self._profiles()
                if data.get('profiles_revision') != revision:
                    raise WorkspaceError('Profiles changed elsewhere. Refresh before saving.', 409)
                settings = self._inputs(data)
                old = values.get(name, {})
                if old and rr._norm(old.get('business', '')) != rr._norm(settings['business']):
                    raise WorkspaceError('Use a new profile key for a different business.')
                values[name] = dict(old, **settings)
                rr.atomic_json(str(self.profiles), values)
                return {'name': name}
            if action not in ('edit', 'validate', 'decision', 'approved-text'):
                raise WorkspaceError('Unknown workspace action.', 404)
            name = data.get('id')
            draft = self._revision(name, data.get('revision'))
            if action in ('edit', 'validate'):
                reply = text(data.get('reply'), 'Reply', MAX_REPLY_CHARS, required=True)
                updated = dict(draft, reply=reply, human_edited=True)
                if action == 'validate':
                    return {'findings': rr.draft_findings(updated), 'word_count': len(reply.split())}
                self._state()
                return self._write(updated, name)
            state = self._state()
            if action == 'decision':
                status = data.get('status')
                if status not in ('approved', 'aside', 'pending'):
                    raise WorkspaceError('Unknown review decision.')
                if status == 'approved':
                    if data.get('reviewed') is not True:
                        raise WorkspaceError('Confirm that you reviewed the draft and its owner policy.')
                    require_valid(rr.draft_findings(draft))
                    self._revision(name, data.get('revision'))
                    state[name] = {'status': status, 'content_sha256': data['revision'],
                                   'safety_version': SAFETY_VERSION,
                                   'approved_at': datetime.now(timezone.utc).isoformat()}
                else:
                    state[name] = {'status': status}
                rr.save_triage(str(self.drafts), state)
                return self._view(name)
            view = self._view(name, state)
            if view['status'] != 'approved':
                raise WorkspaceError('Review and approve the current saved draft before copying or exporting.', 409)
            self._revision(name, data.get('revision'))
            return {'text': view['reply'], 'filename': name.removesuffix('.md') + '.txt'}
