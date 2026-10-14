"""One-time integration; verifies exact locally tested bytes before any commit."""
import hashlib
import json
from pathlib import Path


def edit(name, replacements):
    path = Path(name)
    text = path.read_text(encoding='utf-8')
    for before, after in replacements:
        if text.count(before) != 1:
            raise ValueError(f'Expected one anchor in {name}: {before[:60]}')
        text = text.replace(before, after)
    path.write_text(text, encoding='utf-8')

edit('rrw_workspace.py', [
    ("    if not isinstance(result, dict) or not isinstance(result.get('response'), str):\n        raise ValueError('Ollama returned no text response')\n    return result['response'].strip()",
     "    from rrw_model import checked_response\n    return checked_response(result)"),
    ('        self.caller = caller or gemma_caller', '        self.caller = caller or gemma_caller\n        self.evaluations = None'),
    ('    def _generate(self, draft, mode):', '    def _generate(self, draft, mode, *, observe=None, record_ledger=True):'),
    ("            item = {'attempt': len(trace) + 1, 'temperature': temperature}", "            item = {'attempt': len(trace) + 1, 'temperature': temperature}\n            if observe is not None:\n                import hashlib\n                item['prompt_sha256'] = hashlib.sha256(prompt.encode('utf-8')).hexdigest()"),
    ("                item['findings'] = rr.draft_findings(dict(draft, reply=answer))", "                item['findings'] = rr.draft_findings(dict(draft, reply=answer))\n                if hasattr(answer, 'receipt'):\n                    item['receipt'] = answer.receipt\n                if observe is not None:\n                    item['candidate'] = str(answer) if isinstance(answer, str) else None"),
    ('                trace.append(item)', '                trace.append(item)\n                if observe is not None:\n                    observe(dict(item))'),
    ('settings = dict(caller=observed, ledger_path=str(self.ledger),', 'settings = dict(caller=observed, ledger_path=str(self.ledger) if record_ledger else None,'),
    ("        if action in ('generate', 'reroll'):", "        if action.startswith('quality-'):\n            from rrw_evaluate import EvaluationLab\n            with self.lock:\n                if self.evaluations is None:\n                    self.evaluations = EvaluationLab(self)\n            return self.evaluations.dispatch(action, data)\n        if action in ('generate', 'reroll'):")])
edit('rrw_web.py', [("           '/api/approved-text': 'approved-text'}", "           '/api/approved-text': 'approved-text'}\nACTIONS.update({f'/api/quality-{action}': f'quality-{action}' for action in\n    ('diagnostics', 'list', 'get', 'start', 'step', 'assess', 'export')})")])
edit('web/index.html', [
    ('    <div class="workspace-grid">', '    <nav class="view-switch" aria-label="Workspace view"><button id="view-drafts" class="button active" aria-pressed="true" type="button">Draft workspace</button><button id="view-quality" class="button" aria-pressed="false" type="button">Quality Lab</button></nav>\n    <div class="workspace-grid" id="draft-panel">'),
    ('    <footer class="page-footer">', Path('.development/quality_panel.html').read_text()+'    <footer class="page-footer">')])
edit('web/app.js', [
    ('  if (!value) { typeChanged(); updateButtons(); }','  if (!value) { typeChanged(); updateButtons(); qualityButtons(); }'),
    ("    else { control.disabled = control.dataset.wasDisabled === 'true'; delete control.dataset.wasDisabled; }", "    else if ('wasDisabled' in control.dataset) { control.disabled = control.dataset.wasDisabled === 'true'; delete control.dataset.wasDisabled; }"),
    ("window.addEventListener('beforeunload', event => { if (dirty || busy)", "window.addEventListener('beforeunload', event => { if (dirty || busy || qualityDirty)"),
    ('function renderDraft(view) {', 'function renderDraft(view) {\n  showView(false);'),
    ("  clearEditor(); $('review').value = '';", "  showView(false); clearEditor(); $('review').value = '';"),
    ('policyChanged(); countReview(); updateButtons();\nrun(async () => { await refreshWorkspace(); await checkModel(); });', '')])
for name, fragment in [('web/app.js','.development/quality_ui.js'), ('web/style.css','.development/quality_style.css')]:
    path = Path(name)
    path.write_text(path.read_text()+Path(fragment).read_text())
edit('check_submission.py', [
    ('\ndef main(argv=None):', '\n\ndef evaluation_blockers(path):\n    """Require a checked run artifact; a checkbox alone is not model evidence."""\n    if not path:\n        return ["missing evaluation report: pass --evaluation FILE from Quality Lab"]\n    from rrw_evaluate import load_report, live_evidence_blockers\n    try:\n        return live_evidence_blockers(load_report(path))\n    except (OSError, ValueError, TypeError, KeyError) as exc:\n        return ["invalid evaluation evidence: " + str(exc)]\n\n\ndef main(argv=None):'),
    ('    args = ap.parse_args(argv)', '    ap.add_argument("--evaluation", help="JSON report exported by Quality Lab, for release checks")\n    args = ap.parse_args(argv)'),
    ('            blockers.extend(release_blockers(evidence, post))', '            blockers.extend(release_blockers(evidence, post))\n            report_path = args.evaluation or evidence.get("evaluation_report")\n            if report_path and not os.path.isabs(report_path):\n                report_path = os.path.join(HERE, report_path)\n            blockers.extend(evaluation_blockers(report_path))')])
edit('README.md', [('## Open the app', '''## Quality Lab

The browser now includes **Quality Lab**, a separate evaluation workspace. Run
three fictional smoke scenarios or a 30-case stress set, one case per click.
It keeps model replies, retries, template fallbacks, blocked outputs and human
assessments separate. Results do not become customer drafts or posting approvals.

Start with templates to inspect the protocol. For real-model evidence, check
Gemma setup and explicitly select the installed model. Export the JSON evidence
and readable report after reviewing each result. Unreviewed quality remains
unknown, even when automatic checks pass. See [the Quality Lab guide](docs/QUALITY_LAB.md).

## Open the app''')])
edit('POST_FINAL.md', [('## Why Open Innovation Matters', '''## Testing the Difference Between a Demo and Evidence

Quality Lab runs a separate, developer-written set of fictional reviews. It
records raw attempts, checked fallbacks, blocked outputs, model metadata and
source fingerprints. Model timings exclude template-only cases, and a passed
wording check never becomes a claim of customer satisfaction.

There are three smoke scenarios and 30 stress scenarios. The latter deliberately
includes rating/text conflicts, negation, sarcasm, prompt injection, authorized
and unauthorized promises, and follow-up threads. These fixtures are not an
unbiased benchmark or real-customer validation. The initial template run exposed
sentiment and topic-selection weaknesses; those observations remain visible.

A human can assess each exact result and preserve corrections beside the original.
The exported evidence keeps these judgments separate from generated output and
from posting approval. A recorded evaluation file is now needed for the project's
release check; toggling a checkbox alone is no longer enough to claim a fresh run.
Fresh real-model evidence, operator feedback and a public demo still need to be
supplied and reviewed before publishing this article.

## Why Open Innovation Matters''')])
path = Path('docs/submission_evidence.json')
data = json.loads(path.read_text()); data['evaluation_report']=''
path.write_text(json.dumps(data,indent=2)+'\n')
edit('.github/workflows/tests.yml', [('          python scripts/browser_smoke.py --screenshots evidence/browser | tee evidence/browser/results.json', '          python scripts/browser_smoke.py --screenshots evidence/browser | tee evidence/browser/results.json\n          python scripts/quality_browser_smoke.py --screenshots evidence/browser | tee evidence/browser/quality-results.json')])
expected = json.loads(Path('.development/expected.json').read_text())
for name, target in expected.items():
    actual=hashlib.sha256(Path(name).read_bytes()).hexdigest()
    if actual != target: raise ValueError(f'Byte mismatch {name}: {actual}, expected {target}')
    print('Verified:', name, actual)
