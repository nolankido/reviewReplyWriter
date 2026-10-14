/* Local-only handoff. Uses the existing session-bound API, never external requests. */
'use strict';
(() => {
  let state = null;
  let changed = false;
  function readValues() {
    const values = {demo_url: $('submission-demo').value, evaluation_id: $('submission-evaluation').value};
    for (const key of Object.keys(state.confirmations)) values[key] = $('submission-' + key).checked;
    return values;
  }
  function buttons() {
    if (busy) return;
    $('submission-save').disabled = !state || !changed;
    const include = $('submission-include').checked;
    const canExport = Boolean(state && !changed && (!include || ($('submission-sharing').checked && state.selected_summary)));
    $('submission-post').disabled = !state || changed;
    $('submission-packet').disabled = !canExport;
    $('submission-final').disabled = !canExport || !state.preflight_ready || !include;
    $('submission-sharing-row').hidden = !include;
    $('submission-include').disabled = !state || changed || !state.selected_summary;
    $('submission-dirty').hidden = !changed;
    const access = $('submission-demo_accessible_to_judges');
    if (access) access.disabled = !state.values.demo_url || $('submission-demo').value !== state.values.demo_url;
  }
  function markChanged() { changed = true; buttons(); }
  function list(target, findings, success) {
    $(target).replaceChildren(...(findings.length ? findings : [success]).map(text => node('li', text)));
  }
  function render(view) {
    state = view; changed = false;
    $('submission-repo').value = view.repository_url;
    $('submission-demo').value = view.values.demo_url;
    $('submission-confirmations').replaceChildren();
    for (const [key, title] of Object.entries(view.confirmations)) {
      const label = node('label', undefined, 'check-row');
      const input = node('input'); input.type = 'checkbox'; input.id = 'submission-' + key; input.checked = view.values[key];
      input.addEventListener('change', markChanged); label.append(input, node('span', title));
      $('submission-confirmations').append(label);
    }
    $('submission-evaluation').replaceChildren(new Option('Select a saved evaluation', ''));
    for (const option of view.evaluation_options) $('submission-evaluation').append(new Option(option.label, option.id));
    if (view.values.evaluation_id && !view.evaluation_options.some(x => x.id === view.values.evaluation_id))
      $('submission-evaluation').append(new Option('Missing saved evaluation, reopen Quality Lab', view.values.evaluation_id));
    $('submission-evaluation').value = view.values.evaluation_id;
    $('submission-summary').replaceChildren();
    for (const [value, title] of [[view.official_blockers.length, 'Entry confirmations outstanding'],
      [view.reference_summary.genuine_model_drafts + '/' + view.reference_summary.total, 'Recorded model drafts'],
      ['Not submitted', 'Publication remains your action']]) {
      const card = node('div'); card.append(node('strong', String(value)), node('span', title)); $('submission-summary').append(card);
    }
    $('submission-deadline').textContent = 'Entry deadline: ' + view.deadline;
    $('submission-recorded').replaceChildren(node('strong', view.reference_sources_current ? 'Recorded evidence matches the drafting engine.' : 'Recorded evidence is historical after engine changes.'),
      node('p', view.reference_summary.completed_api_responses + ' completed API responses in the bundled fictional smoke run. No new inference was run by this desk.'),
      node('p', 'Real business-operator usefulness remains unknown. Local file hashes are not independent attestations.', 'helper'));
    const selected = view.selected_summary;
    $('submission-evaluation-summary').textContent = selected ? selected.human_reviewed + '/' + selected.total + ' cases assessed. ' + selected.genuine_model_drafts + ' model-written drafts recorded.' : 'No current personal evaluation selected. Your notes stay private unless explicitly included.';
    list('submission-entry-gaps', [...view.official_blockers, ...view.document_blockers], 'Local confirmations and document checks are complete. Web access and eligibility are not independently verified.');
    list('submission-internal-gaps', view.internal_blockers, 'Selected evidence passed the local internal gate. This is not a contest ruling.');
    $('submission-preview').value = view.post;
    $('submission-challenge-link').href = view.challenge_url; $('submission-rules-link').href = view.rules_url;
    $('submission-rules-date').textContent = 'Rules checked ' + view.rules_checked + '. Recheck the official page before publishing. ' + view.test_status;
    $('submission-include').checked = false; $('submission-sharing').checked = false;
    buttons();
  }
  async function reload() { render(await api('submission-state', {})); }
  $('view-submission').addEventListener('click', () => {
    showView('submission');
    if (!state) run(reload);
  });
  $('submission-refresh').addEventListener('click', () => {
    if (changed && !window.confirm('Discard unsaved submission checklist changes?')) return;
    run(reload);
  });
  $('submission-form').addEventListener('submit', event => {
    event.preventDefault();
    run(async () => {
      render(await api('submission-save', {revision: state.revision, values: readValues()}));
      notify('Checklist saved on this computer. A changed demo link requires a new signed-out access confirmation. Nothing was submitted.');
    });
  });
  $('submission-demo').addEventListener('input', () => {
    if ($('submission-demo_accessible_to_judges')) $('submission-demo_accessible_to_judges').checked = false;
    markChanged();
  });
  $('submission-evaluation').addEventListener('change', markChanged);
  $('submission-include').addEventListener('change', () => { $('submission-sharing').checked = false; buttons(); });
  $('submission-sharing').addEventListener('change', buttons);
  $('submission-open-quality').addEventListener('click', () => { $('view-quality').click(); });
  async function download(format, final = false) {
    const result = await api('submission-export', {revision: state.revision, format, final,
      include_evaluation: format === 'zip' && $('submission-include').checked,
      sharing_confirmed: format === 'zip' && $('submission-sharing').checked});
    const content = result.base64 ? Uint8Array.from(atob(result.base64), c => c.charCodeAt(0)) : result.text;
    const url = URL.createObjectURL(new Blob([content], {type: result.mime}));
    const link = node('a'); link.href = url; link.download = result.filename;
    document.body.append(link); link.click(); link.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000);
    notify('Local ' + (format === 'zip' ? 'judge packet' : 'DEV draft') + ' exported. Inspect before sharing; use DEV to publish manually.');
  }
  $('submission-post').addEventListener('click', () => run(() => download('markdown')));
  $('submission-packet').addEventListener('click', () => run(() => download('zip')));
  $('submission-final').addEventListener('click', () => run(() => download('zip', true)));
  window.addEventListener('beforeunload', event => { if (changed) { event.preventDefault(); event.returnValue = ''; } });
  window.rrwSubmission = {buttons};
  buttons();
})();
