#!/usr/bin/env python3
"""Local submission handoff. No publication, external URL fetching, or attestations by proxy.

python rrw_submission.py --output judge-packet.zip [--video DEMO.mp4]
The browser and CLI use the same ignored submission state and fixed export allowlist.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
from html import escape
import io
import ipaddress
import json
import os
from pathlib import Path
import re
import stat
import threading
from urllib.parse import parse_qsl, quote, unquote, urlsplit
from zipfile import ZipFile, ZIP_DEFLATED

import review_reply as rr
from rrw_evaluate import load_report, live_evidence_blockers, source_snapshot, summarize, digest
from rrw_workspace import WorkspaceError

HERE = Path(__file__).resolve().parent
SCHEMA = 'rrw-submission-v1'
REPOSITORY = 'https://github.com/nolankido/reviewReplyWriter'
CHALLENGE = 'https://dev.to/challenges/hacktoberfest-week2-2026-10-12'
RULES = 'https://dev.to/page/hacktoberfest-week2-2026-10-12-contest-rules'
RULES_CHECKED = '2026-10-13'
DEADLINE = 'October 18, 2026 at 8:59 PM Hawaii time (11:59 PM PDT)'
REFERENCE = 'examples/evaluation/live-quality-smoke-2026-10-13.json'
CONFIRMATIONS = {
    'development_window_confirmed': 'Original project and repository development were within the entry window, including imported work.',
    'repository_accessible_to_judges': 'I inspected code and history for private data and checked judge access to this repository.',
    'demo_accessible_to_judges': 'I watched the demo and tested this exact hosted link signed out.',
    'firsthand_claims_reviewed': 'I reviewed the article, supporting packet documents and their technical and firsthand claims; no user feedback is invented.',
    'rules_reviewed': 'I checked the official rules, eligibility, team credits and submission instructions.',
}
FIELDS = ('demo_url', 'evaluation_id', *CONFIRMATIONS)
PUBLIC_DOCS = ('docs/REPLY_QUALITY_RESULTS.md', 'docs/SUBMISSION_CHECKLIST.md',
               'docs/OPERATOR_TRIAL.md',
               'examples/evaluation/template-quality-comparison.json')
MAX_STATE_BYTES = 32768
MAX_PUBLIC_DOCUMENT_BYTES = 1024 * 1024
MAX_VIDEO_BYTES = 100 * 1024 * 1024


def read_packet_file(path, maximum, label, missing_message):
    """Read one explicitly selected regular file through a bounded, checked descriptor."""
    try:
        before = path.stat(follow_symlinks=False)
    except OSError as exc:
        raise WorkspaceError(missing_message) from exc
    if (not stat.S_ISREG(before.st_mode) or before.st_nlink != 1
            or before.st_size > maximum):
        raise WorkspaceError(f'{label} must be a single-link regular file within its size limit.')
    def version(info):
        return (info.st_dev, info.st_ino, info.st_mode, info.st_nlink,
                info.st_size, info.st_mtime_ns)
    changed = f'{label} changed while reading; choose a stable file before exporting.'
    flags = (os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0)
             | getattr(os, 'O_BINARY', 0))
    with os.fdopen(os.open(path, flags), 'rb') as stream:
        opened = os.fstat(stream.fileno())
        if version(opened) != version(before):
            raise WorkspaceError(changed, 409)
        content = stream.read(maximum + 1)
        after = os.fstat(stream.fileno())
    current = path.stat(follow_symlinks=False)
    if (len(content) > maximum or len(content) != opened.st_size
            or version(after) != version(opened) or version(current) != version(opened)):
        raise WorkspaceError(changed, 409)
    return content


def read_public_documents(project):
    """Read only fixed, single-link regular files, bounded and checked for change."""
    base = Path(project).resolve()
    files = {}
    for name in PUBLIC_DOCS:
        relative = Path(name)
        path = base / relative
        if (any((base.joinpath(*relative.parts[:i])).is_symlink()
                for i in range(1, len(relative.parts) + 1))
                or not path.resolve().is_relative_to(base)):
            raise WorkspaceError('Public packet documents must not use filesystem links.')
        files[name] = read_packet_file(path, MAX_PUBLIC_DOCUMENT_BYTES, 'Public packet document',
            'A public packet document is missing or unreadable. Use a complete project copy.')
    return files


def public_document_fingerprints(files):
    return {name: {'sha256': hashlib.sha256(content).hexdigest(), 'bytes': len(content)}
            for name, content in files.items()}


def public_demo_url(value):
    """Validate link syntax only. Never request the URL or claim it is reachable."""
    if not isinstance(value, str) or len(value) > 2048:
        raise WorkspaceError('Demo URL must be text of at most 2048 characters.')
    if not value:
        return ''
    if value != value.strip() or re.search(r'[\s<>\[\]"\\`]', value):
        raise WorkspaceError('Use a plain HTTPS demo link without spaces, markup or credentials.')
    decoded = unquote(value)
    if re.search(r'[\x00-\x20\x7f<>"\\`]', decoded):
        raise WorkspaceError('Demo URL contains unsafe encoded characters.')
    try:
        parsed = urlsplit(value)
        host = (parsed.hostname or '').lower()
        if parsed.scheme != 'https' or parsed.username or parsed.password or parsed.port not in (None, 443):
            raise ValueError('Not public HTTPS')
        if not re.fullmatch(r'(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}', host):
            raise ValueError('Not a public hostname')
        reserved = ('localhost', 'local', 'internal', 'lan', 'test', 'invalid', 'example',
                    'example.com', 'example.net', 'example.org', 'onion')
        if any(host == suffix or host.endswith('.' + suffix) for suffix in reserved):
            raise ValueError('Reserved hostname')
        try:
            ipaddress.ip_address(host)
        except ValueError:
            pass
        else:
            raise ValueError('IP addresses are not accepted')
        if host.endswith(('oaiusercontent.com', 'githubusercontent.com')) or host == 'api.github.com':
            raise ValueError('Temporary/private download')
        if host == 'github.com' and re.search(r'/(?:actions|artifacts)(?:/|$)', unquote(parsed.path), re.I):
            raise ValueError('Actions artifacts are not a hosted demo')
        for key, _ in parse_qsl(parsed.query, keep_blank_values=True):
            if re.search(r'token|secret|signature|credential|^sig$|^x-amz-|^x-goog-|^key$', key, re.I):
                raise ValueError('Credential-bearing URL')
        if re.search(r'(?i)(?:token|secret|credential)=', unquote(parsed.fragment)):
            raise ValueError('Session-bearing URL')
    except ValueError as exc:
        raise WorkspaceError('Use a stable public/unlisted HTTPS video or deployed-app link, not a local address, example, Actions artifact or signed download.') from exc
    # Parentheses can close Markdown links. Encode instead of interpreting markup.
    return quote(value, safe=':/?#&=+%;@,._~-')


def default_values():
    return dict(demo_url='', evaluation_id='', **{key: False for key in CONFIRMATIONS})


def validate_values(value):
    if not isinstance(value, dict) or set(value) != set(FIELDS):
        raise WorkspaceError('Submission settings have missing or unsupported fields.')
    result = dict(value)
    result['demo_url'] = public_demo_url(value['demo_url'])
    name = value['evaluation_id']
    if not isinstance(name, str) or (name and not re.fullmatch(r'eval-[0-9a-f]{32}', name)):
        raise WorkspaceError('Choose an evaluation from this workspace, not a file path.')
    for key in CONFIRMATIONS:
        if type(value[key]) is not bool:
            raise WorkspaceError('Each confirmation must be an explicit true or false value.')
    return result


def _strict_json(path):
    if path.is_symlink() or path.stat().st_size > MAX_STATE_BYTES:
        raise WorkspaceError('Submission file cannot be read safely; the original was kept.')
    from rrw_web import strict_object, reject_constant
    content = path.read_bytes()
    if len(content) > MAX_STATE_BYTES:
        raise WorkspaceError('Submission state is too large.')
    return (json.loads(content.decode('utf-8'), object_pairs_hook=strict_object, parse_constant=reject_constant),
            hashlib.sha256(content).hexdigest())


def _replace_block(post, name, replacement):
    start, end = f'<!-- RRW:{name}:START -->', f'<!-- RRW:{name}:END -->'
    if post.count(start) != 1 or post.count(end) != 1 or post.index(end) < post.index(start):
        raise WorkspaceError('The article template changed. Restore its export markers before exporting.')
    a, b = post.index(start), post.index(end) + len(end)
    return post[:a] + replacement + post[b:]


def render_post(template, values, outstanding):
    notice = ('> DRAFT: not submitted. Complete the outstanding items in READINESS.json before publication.\n'
              '> TODO: ' + '; '.join(outstanding) + '\n') if outstanding else ''
    if values['demo_url']:
        demo = ('[Watch the application demonstration](<' + public_demo_url(values['demo_url']) + '>).\n\n'
                'The recording uses a fictional review. Real model calls and template output are labelled separately. '
                'Demonstration approval clicks are not operator endorsements.\n')
    else:
        demo = 'TODO: Add the hosted video or deployed-app link after watching it and checking signed-out access.\n'
    post = _replace_block(template, 'NOTICE', notice)
    post = _replace_block(post, 'DEMO', demo)
    if not re.search(r'^published: false$', post, re.M):
        raise WorkspaceError('Export must preserve published: false; this tool never publishes.')
    return post


class SubmissionDesk:
    def __init__(self, root, lock=None, project=HERE):
        self.root = Path(root).resolve()
        self.private = self.root / '.rrw'
        self.path = self.private / 'submission.json'
        self.project = Path(project).resolve()
        self.lock = lock or threading.RLock()

    def _boundary(self):
        if self.private.is_symlink() or self.private.resolve().parent != self.root or self.path.is_symlink():
            raise WorkspaceError('Submission storage must be a regular local workspace, not a link.')

    def _read(self):
        self._boundary()
        if not self.path.exists():
            return {'schema': SCHEMA, 'values': default_values(), 'claims_version': ''}, 'new'
        raw, revision = _strict_json(self.path)
        if not isinstance(raw, dict) or set(raw) != {'schema', 'values', 'claims_version'} or raw['schema'] != SCHEMA:
            raise WorkspaceError('Unsupported submission state; preserve it for recovery.')
        raw['values'] = validate_values(raw['values'])
        if not isinstance(raw['claims_version'], str):
            raise WorkspaceError('Invalid submission version.')
        return raw, revision

    def _evaluation_path(self, name):
        if not re.fullmatch(r'eval-[0-9a-f]{32}', name):
            raise WorkspaceError('Invalid evaluation identifier.')
        folder = self.private / 'evaluations'
        path = folder / (name + '.json')
        if folder.is_symlink() or path.is_symlink():
            raise WorkspaceError('Evaluation links are not supported.')
        return path

    def _report(self, name):
        if not name:
            return None, ['Select and assess a current Gemma run in Quality Lab.']
        try:
            report = load_report(self._evaluation_path(name))
            return report, live_evidence_blockers(report)
        except (OSError, ValueError, TypeError, KeyError) as exc:
            return None, ['Evaluation is unavailable or invalid. Preserve the original and reopen Quality Lab.']

    def _options(self):
        folder = self.private / 'evaluations'
        if folder.is_symlink():
            raise WorkspaceError('Evaluation folder cannot be a link.')
        if not folder.is_dir():
            return []
        options = []
        for path in sorted(folder.glob('eval-*.json'), reverse=True)[:100]:
            if not re.fullmatch(r'eval-[0-9a-f]{32}', path.stem):
                continue
            try:
                report = load_report(self._evaluation_path(path.stem))
                if report['id'] != path.stem:
                    raise ValueError('Report identity does not match its filename')
                s = summarize(report)
                label = f"{report['created_at'][:19]} | {report['mode']} | {s['attempted']}/{s['total']} cases | {s['human_reviewed']} assessed"
                options.append({'id': path.stem, 'label': label})
            except (OSError, ValueError, KeyError, TypeError):
                options.append({'id': path.stem, 'label': path.stem + ' | unreadable, original preserved'})
        return options

    def _snapshot(self):
        raw, file_revision = self._read()
        template = (self.project / 'POST_FINAL.md').read_text(encoding='utf-8')
        sources = source_snapshot()
        public_documents = public_document_fingerprints(read_public_documents(self.project))
        claims_version = digest({'post': template, 'sources': sources, 'rules_checked': RULES_CHECKED,
                                 'public_documents': public_documents})
        values = dict(raw['values'])
        if not values['demo_url']:
            values['demo_accessible_to_judges'] = False
        if raw['claims_version'] != claims_version:
            values['firsthand_claims_reviewed'] = False
        report, evaluation_gaps = self._report(values['evaluation_id'])
        if report and report['id'] != values['evaluation_id']:
            report, evaluation_gaps = None, ['Evaluation identity does not match the selected file.']
        reference = load_report(self.project / REFERENCE)
        reference_summary = summarize(reference)
        reference_current = reference['sources'] == sources
        revision = digest({'state': file_revision, 'claims': claims_version,
                           'selected_report': report['sha256'] if report else evaluation_gaps,
                           'reference': reference['sha256']})
        checks = []
        for key, title in CONFIRMATIONS.items():
            checks.append({'key': key, 'title': title, 'status': 'owner-confirmed' if values[key] else 'needs-confirmation'})
        if not values['demo_url']:
            checks.append({'key': 'demo_url', 'title': 'Add a hosted demo or deployed-app URL.', 'status': 'missing'})
        official = [item['title'] for item in checks if item['status'] != 'owner-confirmed']
        if not reference_current:
            evaluation_gaps = [*evaluation_gaps, 'Bundled demonstration evidence is historical after source changes; review the article before release.']
        # These are local preflight results, never verification of web accessibility or eligibility.
        post = render_post(template, values, official)
        from check_submission import release_blockers
        evidence = dict(repository_url=REPOSITORY, demo_url=values['demo_url'],
                        **{key: values[key] for key in CONFIRMATIONS},
                        fresh_gemma_run_recorded=bool(report and not live_evidence_blockers(report)),
                        evaluation_report='evidence/selected-evaluation.json' if report else '')
        internal = list(evaluation_gaps)
        document_gaps = [x for x in release_blockers(evidence, post)
                         if not x.startswith('owner evidence not confirmed:')]
        view = dict(schema=SCHEMA, revision=revision, values=values, confirmations=CONFIRMATIONS,
            repository_url=REPOSITORY, challenge_url=CHALLENGE, rules_url=RULES, rules_checked=RULES_CHECKED,
            deadline=DEADLINE, official_checks=checks, official_blockers=official,
            internal_blockers=internal, document_blockers=document_gaps, evaluation_options=self._options(),
            selected_summary=summarize(report) if report else None,
            reference_summary=reference_summary, reference_sources_current=reference_current,
            public_documents=public_documents,
            reference_sha256=reference['sha256'], post=post,
            preflight_ready=not official and not internal and not document_gaps, published=False,
            external_checks='Not performed. Link access, eligibility and claims are owner attestations.',
            test_status='Not run by Submission Desk. See the repository CI and run the development checker.')
        return view, report, reference, claims_version

    def state(self):
        with self.lock:
            return self._snapshot()[0]

    def _revision(self, expected):
        snapshot = self._snapshot()
        if expected != snapshot[0]['revision']:
            raise WorkspaceError('Submission inputs, article or evidence changed. Reload before saving or exporting.', 409)
        return snapshot

    def dispatch(self, action, data=None):
        data = {} if data is None else data
        if not isinstance(data, dict):
            raise WorkspaceError('Request must be a JSON object.')
        with self.lock:
            if action == 'submission-state' and not data:
                return self._snapshot()[0]
            if action == 'submission-save':
                if set(data) != {'revision', 'values'}:
                    raise WorkspaceError('Unsupported submission settings.')
                before, _, _, claims_version = self._revision(data['revision'])
                values = validate_values(data['values'])
                if values['evaluation_id']:
                    self._evaluation_path(values['evaluation_id'])
                # Access confirmation belongs to the URL actually tested, not its replacement.
                if values['demo_url'] != before['values']['demo_url']:
                    values['demo_accessible_to_judges'] = False
                self._boundary()
                self.private.mkdir(parents=True, exist_ok=True)
                rr.atomic_json(str(self.path), {'schema': SCHEMA, 'values': values, 'claims_version': claims_version})
                return self._snapshot()[0]
            if action == 'submission-export':
                if set(data) != {'revision', 'format', 'include_evaluation', 'sharing_confirmed', 'final'}:
                    raise WorkspaceError('Unsupported export settings.')
                for key in ('include_evaluation', 'sharing_confirmed', 'final'):
                    if type(data[key]) is not bool:
                        raise WorkspaceError('Export confirmations must be explicit booleans.')
                view, report, reference, _ = self._revision(data['revision'])
                if data['final'] and (not view['preflight_ready'] or not data['include_evaluation'] or not data['sharing_confirmed']):
                    raise WorkspaceError('Final preflight is blocked. Export a working packet without claiming readiness.', 422)
                if data['include_evaluation'] and (not data['sharing_confirmed'] or report is None):
                    raise WorkspaceError('Select a readable evaluation and confirm sharing its raw text and notes.')
                if data['format'] == 'markdown':
                    return dict(filename='DEV_SUBMISSION_DRAFT.md', mime='text/markdown', text=view['post'])
                if data['format'] != 'zip':
                    raise WorkspaceError('Choose Markdown or ZIP export.')
                content = make_packet(view, reference, report if data['include_evaluation'] else None, project=self.project)
                # A second snapshot catches ordinary competing writes before a stale export is returned.
                self._revision(data['revision'])
                return dict(filename='Review_Reply_Writer_Judge_Packet.zip', mime='application/zip',
                            base64=base64.b64encode(content).decode('ascii'))
            raise WorkspaceError('Unknown submission action.', 404)


def exhibit(view, reference, video=False):
    """Standalone no-script evidence page. Nothing can generate or approve replies here."""
    s = summarize(reference)
    cards = []
    for case, row in zip(reference['cases'], reference['results']):
        cards.append('<article><p class="label">RECORDED ' + escape(row['status'].upper()) + '</p><h3>' +
            escape(case['label']) + '</h3><h4>Fictional customer review</h4><p>' + escape(case['input']['review']) +
            '</p><h4>Recorded response</h4><blockquote>' + escape(row.get('reply') or 'No reply generated') +
            '</blockquote><details><summary>Evidence and limitations</summary><p>' +
            escape(str(len(row.get('attempts', [])))) + ' attempts. ' + escape(str(round(row.get('elapsed_ms', 0)/1000, 3))) +
            ' seconds on the recorded hosted machine, not your computer.</p><p>No real business-operator assessment is claimed.</p></details></article>')
    media = '<video controls preload="metadata" src="assets/demo.mp4" aria-label="Recorded application demonstration"></video><p class="note">Author-supplied local recording. Check its engine labels and captions. Demonstration clicks are not operator endorsements.</p>' if video else '<p>The packet does not contain a local video. Use the hosted demo link once supplied.</p>'
    link = '<a class="button" rel="noreferrer noopener" href="' + escape(view['values']['demo_url'], quote=True) + '">Open hosted demo</a>' if view['values']['demo_url'] else '<p class="warning">Hosted demo URL not supplied. This packet is not a submitted entry.</p>'
    remaining = ''.join('<li>' + escape(x) + '</li>' for x in view['official_blockers'])
    return '''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; media-src 'self'; base-uri 'none'; form-action 'none'">
<title>Review Reply Writer | Judge guide</title><style>
*{box-sizing:border-box}body{margin:0;background:#f5f4ef;color:#202d2a;font:17px/1.65 system-ui,sans-serif}main{max-width:1060px;margin:auto;padding:48px 24px}h1{font-size:clamp(2.3rem,6vw,4.5rem);line-height:1.06;letter-spacing:-.04em;max-width:880px}h2{font-size:1.85rem;line-height:1.2;margin-top:42px}h3{font-size:1.35rem}h4{margin-bottom:8px}.label{font-size:.76rem;letter-spacing:.17em;font-weight:700;color:#36584b}.lead{font-size:1.2rem;max-width:780px}.strip{display:flex;flex-wrap:wrap;gap:14px;margin:30px 0}.strip div,article{background:white;border:1px solid #d9dfd7;border-radius:16px;padding:24px}.strip div{flex:1;min-width:180px}.strip strong{font-size:2rem;display:block}article{margin:20px 0}blockquote{border-left:3px solid #46765c;margin:8px 0;padding:8px 22px;white-space:pre-wrap}.note{font-size:.88rem;color:#53645a}.warning{background:#fff2d5;padding:14px 18px;border-radius:10px}a{color:#20543b;overflow-wrap:anywhere}.button{display:inline-block;background:#25543e;color:white;padding:12px 20px;border-radius:9px;text-decoration:none}video{width:100%;max-height:740px;background:#172a22;border-radius:12px}details{font-size:.9rem}summary{cursor:pointer}code{overflow-wrap:anywhere}li{margin:10px 0}footer{margin-top:48px;border-top:1px solid #cbd4c8;padding-top:20px;font-size:.85rem}
</style></head><body><main><p class="label">HACKTOBERFEST WEEK 2 · SIDE HUSTLE</p>
<h1>Write the reply.<br>Not the refund policy.</h1><p class="lead">Local Gemma drafts customer-review replies. The owner supplies permitted commitments, checks the result, and decides what gets posted.</p>
<p class="note">Read-only judge guide. No Python or Ollama is needed to inspect this packet. This page does not run AI or submit an entry.</p>
''' + media + link + f'''<div class="strip"><div><strong>{s['genuine_model_drafts']}/{s['total']}</strong>Recorded model drafts</div><div><strong>{s['completed_api_responses']}</strong>Completed API responses</div><div><strong>Unknown</strong>Real operator usefulness</div></div>
<section><h2>The product decision</h2><p>The proposed customer is an independent cafe, shop or accommodation operator. Paid installation, owner-policy setup and support around free code are a commercial hypothesis, not proven revenue.</p><p>Gemma is central to generation. Deterministic checks and human approval constrain its output; neither proves factual truth. Refunds and operational claims require exact owner authorization. There is no automatic posting.</p></section>
<section><h2>Inspect the actual recorded outputs</h2><p>These selected fictional cases are retained diagnostic evidence, not a blind benchmark or a live test in this page. The source fingerprint is {'current for the drafting engine' if view['reference_sources_current'] else 'historical, different from the current engine'}.</p>''' + ''.join(cards) + '''</section>
<section><h2>Reproduce and inspect</h2><p>Run <code>py rrw_web.py</code> from the project on Windows, then use Draft workspace or Quality Lab. Download <code>gemma3:4b</code> with Ollama for model output. Template preview needs no model.</p>
<p><a href="evidence/recorded-smoke.json">Raw recorded responses and fingerprints</a> · <a href="DEV_SUBMISSION_DRAFT.md">DEV draft</a> · <a href="READINESS.json">Readiness and unresolved confirmations</a> · <a href="MANIFEST.json">Package checksums</a></p>
<p><a rel="noreferrer noopener" href="''' + REPOSITORY + '''">Inspect the GitHub repository</a>. Access must be checked signed out; this page does not claim the repository is public.</p></section>
<section><h2>Submission handoff</h2><p>A source ZIP, commit or local video is not a DEV entry. Publish through the <a rel="noreferrer noopener" href="''' + CHALLENGE + '''">official template</a> only after the author checks requirements.</p><ul>''' + (remaining or '<li>Local owner confirmations recorded. External facts have not been independently verified.</li>') + '''</ul></section>
<footer>Open-weight model terms and the application MIT license are separate. English-language safeguards are heuristics. No external assets, scripts, analytics or uploads. Human judgment is required.</footer></main></body></html>'''


def make_packet(view, reference, selected=None, project=HERE, video_bytes=None):
    """Only explicit text/record allowlists. Never scan private workspace contents."""
    if video_bytes is not None and (len(video_bytes) > MAX_VIDEO_BYTES or video_bytes[4:8] != b'ftyp'):
        raise WorkspaceError('Optional demo must be an MP4 of at most 100 MiB.')
    documents = read_public_documents(project)
    if public_document_fingerprints(documents) != view.get('public_documents'):
        raise WorkspaceError('Public packet documents changed. Reload and review before exporting.', 409)
    readiness = {k: view[k] for k in ('schema', 'official_checks', 'official_blockers', 'internal_blockers', 'document_blockers',
                    'preflight_ready', 'published', 'external_checks', 'test_status', 'deadline', 'rules_checked', 'reference_sources_current', 'public_documents')}
    readiness['selected_evaluation_included'] = selected is not None
    readiness['preflight_ready'] = bool(view['preflight_ready'] and selected is not None)
    if selected is None and not readiness['internal_blockers']:
        readiness['internal_blockers'] = ['Selected evaluation excluded from this packet; internal release evidence is not included.']
    readiness['reference_sha256'] = reference['sha256']
    readiness['rules_url'] = RULES
    evidence = dict(repository_url=REPOSITORY, demo_url=view['values']['demo_url'],
                   **{key: view['values'][key] for key in CONFIRMATIONS},
                   fresh_gemma_run_recorded=bool(selected and not live_evidence_blockers(selected)),
                   evaluation_report='evidence/selected-evaluation.json' if selected else '')
    files = {
        'START_HERE.html': exhibit(view, reference, video_bytes is not None).encode('utf-8'),
        'DEV_SUBMISSION_DRAFT.md': view['post'].encode('utf-8'),
        'READINESS.json': json.dumps(readiness, indent=2, ensure_ascii=False).encode('utf-8'),
        'submission_evidence.json': json.dumps(evidence, indent=2).encode('utf-8'),
        'evidence/recorded-smoke.json': json.dumps(reference, indent=2, ensure_ascii=False).encode('utf-8'),
        'START_HERE.txt': ('Extract the complete ZIP, then open START_HERE.html. This is a read-only guide, not the application.\n'
            'No Python or model installation is needed to inspect it. No entry has been submitted.\n'
            'The DEV file always has published: false. Use the official challenge template for manual publication.\n'
            'Confirmations are the author\'s statements, not proof of access or eligibility.\n'
            'The selected private evaluation is excluded unless explicitly enabled at export.\n'
            'Before hosting any packet, inspect its files, notes and recorded replies.\n'
            'From the source repository, run: py check_submission.py --release --evidence PATH_TO_PACKET/submission_evidence.json --post PATH_TO_PACKET/DEV_SUBMISSION_DRAFT.md\n').encode('utf-8'),
    }
    files.update(documents)
    files[REFERENCE] = files['evidence/recorded-smoke.json']
    if selected is not None:
        files['evidence/selected-evaluation.json'] = json.dumps(selected, indent=2, ensure_ascii=False).encode('utf-8')
    if video_bytes is not None:
        files['assets/demo.mp4'] = video_bytes
    manifest = {'schema': 'rrw-judge-packet-v1', 'checksums_are_not_signatures': True,
                'files': {name: {'sha256': hashlib.sha256(content).hexdigest(), 'bytes': len(content)} for name, content in sorted(files.items())}}
    files['MANIFEST.json'] = json.dumps(manifest, indent=2).encode('utf-8')
    output = io.BytesIO()
    with ZipFile(output, 'w', compression=ZIP_DEFLATED) as archive:
        for name, content in sorted(files.items()):
            archive.writestr(name, content)
    return output.getvalue()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--data-dir', type=Path, default=HERE)
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--video', type=Path, help='Explicitly include this reviewed local MP4, never uploaded')
    args = ap.parse_args(argv)
    try:
        from rrw_web import InstanceLock
        # The CLI never replaces existing files or takes data from unrelated directories.
        if args.output.exists() or args.output.is_symlink():
            raise WorkspaceError('Output already exists. Choose a new filename; nothing was overwritten.')
        with InstanceLock(args.data_dir):
            desk = SubmissionDesk(args.data_dir)
            view, _, reference, _ = desk._snapshot()
            video = None
            if args.video:
                video = read_packet_file(args.video, MAX_VIDEO_BYTES, 'Demo file',
                    'Demo file is missing or unreadable. Choose an existing reviewed MP4.')
            content = make_packet(view, reference, project=HERE, video_bytes=video)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            with args.output.open('xb') as fh:
                fh.write(content)
        print('Created local working judge packet:', args.output)
        print('Nothing was published. Outstanding entry confirmations:', len(view['official_blockers']))
        print('Private evaluations, profiles, tokens and customer drafts are excluded.')
        return 0
    except (OSError, ValueError) as exc:
        print('Packet not created:', str(exc), file=__import__('sys').stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
