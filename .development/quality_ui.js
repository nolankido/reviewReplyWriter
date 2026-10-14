
// Quality experiments are separate from real drafts and publication approvals.
let qualityRun = null;
let qualityCase = null;
let qualityDirty = false;
function showView(quality) {
  $('quality-panel').hidden = !quality; $('draft-panel').hidden = quality;
  for (const [id, active] of [['view-quality', quality], ['view-drafts', !quality]]) {
    $(id).classList.toggle('active', active); $(id).setAttribute('aria-pressed', String(active));
  }
}
function qualityDiscard() {
  return !qualityDirty || window.confirm('Discard unsaved quality assessment changes? Saved results remain unchanged.');
}
function qualityRef() { return {id: qualityRun.id, revision: qualityRun.revision}; }
function qualityButtons() {
  if (busy) return;
  const summary = qualityRun && qualityRun.summary;
  $('quality-next').disabled = !summary || summary.attempted >= summary.total || !qualityRun.sources_current ||
    (qualityRun.mode === 'gemma' && !qualityRun.preflight.ready);
  $('quality-next').textContent = summary && summary.attempted >= summary.total ? 'All cases recorded' : 'Run next case';
  $('quality-start').disabled = $('quality-mode').value === 'gemma' && !$('quality-confirm').checked;
}
async function qualityList() {
  const list = await api('quality-list', {});
  $('quality-runs').replaceChildren(new Option('Choose a saved evaluation', ''));
  for (const run of list.runs) {
    const label = run.error ? run.id + ' (needs recovery)' : run.created_at.slice(0, 19).replace('T', ' ') +
      ' UTC | ' + run.execution + ' | ' + run.summary.attempted + '/' + run.summary.total;
    $('quality-runs').append(new Option(label, run.id));
  }
  if (qualityRun) $('quality-runs').value = qualityRun.id;
}
function renderQuality(report, selectCase) {
  qualityRun = report;
  $('quality-empty').hidden = true; $('quality-results').hidden = false;
  $('quality-run-name').textContent = report.execution + ' | ' + report.suite + ' evaluation';
  $('quality-provenance').textContent = report.provenance;
  const s = report.summary;
  const values = [['Cases recorded', s.attempted + '/' + s.total], ['Model drafts', s.model],
    ['Templates / fallbacks', s.template + ' / ' + s.fallback], ['Blocked / errors / interrupted', s.blocked + ' / ' + s.error + ' / ' + s.interrupted],
    ['Cases with rubric flags', s.rubric_flagged], ['Human-reviewed cases', s.human_reviewed + '/' + s.total],
    ['Human-reported risk flags', s.human_reviewed ? s.human_risk_flags + ' / ' + s.human_reviewed : 'Unknown'],
    ['Median seconds, model cases', s.model_median_seconds === null ? 'Not measured' : s.model_median_seconds.toFixed(2)]];
  $('quality-metrics').replaceChildren(...values.map(([label, value]) => {
    const box = node('div', undefined, 'quality-metric'); box.append(node('strong', String(value)), node('span', label)); return box;
  }));
  $('quality-progress').textContent = (s.complete ? 'Run complete. ' : 'Progress saved. ') +
    (report.sources_current ? '' : 'Code changed since this run. Start a new evaluation. ') +
    'First-try model drafts: ' + s.first_try_model + '. Retried cases: ' + s.retried_cases +
    '. Completed real API responses: ' + s.completed_api_responses + '.';
  $('quality-evidence-gaps').replaceChildren(...(report.evidence_blockers.length ? report.evidence_blockers :
    ['Evidence structure checks passed. This is not proof of factuality, external verification, or contest eligibility.']).map(x => node('li', x)));
  const selected = selectCase || (qualityCase && qualityCase.case_id) || (report.results[0] && report.results[0].case_id);
  $('quality-cases').replaceChildren(...report.cases.map((c, i) => {
    const row = report.results[i]; const button = node('button', undefined, 'quality-case' + (c.id === selected ? ' active' : ''));
    button.type = 'button'; button.disabled = !row; button.dataset.caseId = c.id;
    button.append(node('strong', c.label), node('span', row ? row.status + (row.rubric_findings.length ? ' | rubric flag' : '') +
      (row.human_review ? ' | assessed' : ' | unreviewed') : 'Not run'));
    button.addEventListener('click', () => { if (qualityDiscard()) renderQuality(qualityRun, c.id); }); return button;
  }));
  qualityCase = report.results.find(r => r.case_id === selected) || null;
  $('quality-case-panel').hidden = !qualityCase;
  if (qualityCase) renderQualityCase();
  qualityDirty = false; qualityButtons();
}
function renderQualityCase() {
  const row = qualityCase;
  const c = qualityRun.cases.find(x => x.id === row.case_id);
  $('quality-case-title').textContent = c.label;
  $('quality-case-status').textContent = row.status;
  $('quality-case-info').textContent = c.input.business + ' | ' + c.input.platform + ' | expected tier: ' + c.expected_tier;
  $('quality-case-review').textContent = c.input.review;
  $('quality-thread').hidden = !c.input.followup;
  $('quality-original').textContent = c.input.original || '';
  $('quality-previous').textContent = c.input.previous || '';
  $('quality-case-policy').textContent = [c.input.offer, ...(c.input.approved_actions || [])].filter(Boolean).join('\n') || 'No commitments authorized.';
  $('quality-case-reply').textContent = row.reply || 'No draft produced. This failure remains part of the evidence.';
  $('quality-findings-list').replaceChildren(...[...row.findings, ...row.rubric_findings].map(x => node('li', x)));
  if (!row.findings.length && !row.rubric_findings.length) $('quality-findings-list').append(node('li', 'No automated probe flagged. Human review is still required.'));
  $('quality-attempts').replaceChildren(...row.attempts.map(a => node('p',
    'Attempt ' + a.attempt + ' | ' + (a.elapsed_ms / 1000).toFixed(2) + 's | temperature ' + a.temperature + '\n' +
    (a.findings.join('; ') || 'Current checks passed') + '\n' + (a.candidate || 'No text response') +
    '\nReceipt: ' + JSON.stringify(a.receipt || 'No genuine API receipt recorded'))));
  if (!row.attempts.length) $('quality-attempts').append(node('p', 'No model call recorded. Template output is not AI evidence.'));
  const assessment = row.human_review || {};
  $('quality-decision').value = assessment.decision || '';
  $('quality-notes').value = assessment.notes || '';
  $('quality-edited').value = assessment.edited_reply || '';
  $('quality-reviewed').checked = false;
  document.querySelectorAll('.quality-issues input').forEach(input => input.checked = (assessment.issues || []).includes(input.value));
  $('quality-edit-findings').textContent = (assessment.edited_findings || []).join('; ');
}
$('view-quality').addEventListener('click', () => run(async () => { showView(true); await qualityList(); }));
$('view-drafts').addEventListener('click', () => showView(false));
$('quality-mode').addEventListener('change', () => { $('quality-confirm-row').hidden = $('quality-mode').value !== 'gemma'; $('quality-confirm').checked = false; qualityButtons(); });
$('quality-confirm').addEventListener('change', qualityButtons);
$('quality-check').addEventListener('click', () => run(async () => {
  const d = await api('quality-diagnostics', {});
  $('quality-diagnostics').textContent = d.message;
  $('quality-model-info').hidden = false;
  $('quality-model-info').textContent = (d.identity ? 'Model digest: ' + d.identity.digest + '\nQuantization: ' + d.identity.quantization + '\n' : '') +
    'Ollama version: ' + (d.version || 'not reported') + '\nLocal execution: not independently verified.\n' + d.privacy_note;
  notify(d.ready ? 'Installation identified. Run the smoke test to measure actual generation.' : d.message, !d.ready);
}));
$('quality-start').addEventListener('click', () => {
  if (!qualityDiscard()) return;
  run(async () => { const report = await api('quality-start', {mode: $('quality-mode').value,
    suite: $('quality-suite').value, confirmed: $('quality-confirm').checked});
    renderQuality(report); await qualityList();
    notify(report.mode === 'gemma' && !report.preflight.ready ? report.preflight.message : 'Evaluation created. Run one case at a time. Customer drafts are not changed.'); });
});
$('quality-next').addEventListener('click', () => {
  if (!qualityDiscard()) return;
  run(async () => { notify('Running one fictional case. It may include one retry. Results are checkpointed locally.');
    const report = await api('quality-step', qualityRef());
    renderQuality(report, report.results[report.results.length - 1].case_id); await qualityList();
    notify('Case recorded. Inspect its result before drawing a quality conclusion.'); });
});
$('quality-runs').addEventListener('change', () => {
  if (!$('quality-runs').value || !qualityDiscard()) return;
  run(async () => { renderQuality(await api('quality-get', {id: $('quality-runs').value})); });
});
$('quality-refresh').addEventListener('click', () => {
  if (!qualityDiscard()) return;
  run(async () => { await qualityList(); if (qualityRun) renderQuality(await api('quality-get', {id: qualityRun.id})); });
});
$('quality-assess-form').addEventListener('input', () => { qualityDirty = true; });
$('quality-assess-form').addEventListener('submit', event => {
  event.preventDefault();
  run(async () => { const report = await api('quality-assess', {...qualityRef(), case_id: qualityCase.case_id,
    result_sha256: qualityCase.result_sha256, reviewed: $('quality-reviewed').checked,
    decision: $('quality-decision').value, notes: $('quality-notes').value,
    edited_reply: $('quality-edited').value,
    issues: [...document.querySelectorAll('.quality-issues input:checked')].map(x => x.value)});
    renderQuality(report); await qualityList(); notify('Human assessment saved beside the unchanged original. This does not approve a reply for posting.'); });
});
for (const [id, format] of [['quality-json', 'json'], ['quality-markdown', 'markdown']]) {
  $(id).addEventListener('click', () => {
    if (!qualityDiscard()) return;
    run(async () => { const result = await api('quality-export', {...qualityRef(), format});
      const url = URL.createObjectURL(new Blob([result.text], {type: result.mime + ';charset=utf-8'}));
      const link = node('a'); link.href = url; link.download = result.filename; document.body.append(link); link.click(); link.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000); notify('Evidence exported. Review the fictional cases, raw outputs, and notes before sharing.'); });
  });
}
policyChanged(); countReview(); updateButtons(); qualityButtons();
run(async () => { await refreshWorkspace(); await checkModel(); });
