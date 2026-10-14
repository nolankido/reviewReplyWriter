'use strict';
const $ = id => document.getElementById(id);
const fragment = new URLSearchParams(location.hash.slice(1));
const supplied = fragment.get('token');
let session;
try { session = window.rrwConnection.session(sessionStorage, supplied); }
catch (error) { session = {token: supplied || '', available: false}; }
let token = session.token;
if (supplied) {
  history.replaceState(null, '', location.pathname);
}
if (!session.available) {
  $('session-storage-note').hidden = false;
  $('session-storage-note').textContent = 'Browser session storage is blocked. This tab can use the launcher link, but reopening requires a current launcher link. A pending result check is kept only in this tab; saved drafts remain in the library.';
}
let workspace = {drafts: [], profiles: {}, profiles_revision: 'new'};
let current = null;
let dirty = false;
let busy = false;
const labels = {pending: 'Needs review', approved: 'Approved', blocked: 'Needs changes', aside: 'Set aside'};
const samples = {
  positive: {business: 'Demo Cafe', kind: 'cafe', stars: 5,
    review: 'The oat milk latte was perfect, the seats were cozy, and the service was quick. A lovely start to my morning.'},
  negative: {business: 'Demo Cafe', kind: 'cafe', stars: 2,
    review: 'Cold coffee and a 25 minute wait. The barista ignored my question about the order. Disappointing.'},
  mixed: {business: 'Demo Stay', kind: 'stay', stars: 3,
    review: 'Beautiful room and a stunning ocean view, but check-in took forever and the shower pressure was weak.'},
  billing: {business: 'Demo Cafe', kind: 'cafe', stars: 3,
    review: 'The coffee was excellent, but I was charged twice. The waiter ignored my question about the bill.'}
};

function notify(message, error = false) {
  $('notice').textContent = message;
  $('notice').className = 'notice' + (error ? ' error' : '');
  $('notice').hidden = !message;
}
function node(tag, content, className) {
  const el = document.createElement(tag);
  if (content !== undefined) el.textContent = content;
  if (className) el.className = className;
  return el;
}
async function api(path, data) {
  return window.rrwConnection.request(path, data, token);
}
function setBusy(value) {
  busy = value;
  document.querySelector('.app-shell').classList.toggle('busy', value);
  $('main').setAttribute('aria-busy', String(value));
  for (const control of document.querySelectorAll('button, input, select, textarea')) {
    if (value) { control.dataset.wasDisabled = String(control.disabled); control.disabled = true; }
    else if ('wasDisabled' in control.dataset) { control.disabled = control.dataset.wasDisabled === 'true'; delete control.dataset.wasDisabled; }
  }
  $('generate').textContent = value ? 'Working...' : 'Generate draft ↗';
  if (!value) { typeChanged(); updateButtons(); qualityButtons(); if (window.rrwSubmission) window.rrwSubmission.buttons(); if (window.rrwInbox) window.rrwInbox.buttons(); if (window.rrwFeedback) window.rrwFeedback.buttons(); if (window.rrwRecovery) window.rrwRecovery.buttons(); if (window.rrwGeneration) window.rrwGeneration.buttons(); if (window.rrwSaveRecovery) window.rrwSaveRecovery.buttons(); }
  if (!value && window.rrwFocus) window.rrwFocus.flush();
}
async function run(task) {
  if (busy) return;
  setBusy(true);
  try { await task(); }
  catch (error) { notify(error.message || 'Could not complete that action. Your editor text has been kept.', true);
    if (window.rrwFocus) window.rrwFocus.request('notice'); }
  finally { setBusy(false); }
}
function updateProgress() {
  if (!current) return;
  const stage = current.status === 'approved' && !dirty &&
    !(window.rrwSaveRecovery && window.rrwSaveRecovery.needsAttention()) ? 3
    : (!$('human-reviewed').checked || dirty || current.findings.length ? 1 : 2);
  for (const element of document.querySelectorAll('.review-progress li')) {
    const n = Number(element.dataset.step);
    element.classList.toggle('complete', n < stage);
    element.classList.toggle('active', n === stage);
    if (n === stage) element.setAttribute('aria-current', 'step');
    else element.removeAttribute('aria-current');
  }
}
function updateButtons() {
  if (busy) return;
  const unresolved = Boolean(window.rrwSaveRecovery && window.rrwSaveRecovery.unresolved());
  const saved = current && !dirty && !unresolved;
  const approved = saved && current.status === 'approved' && current.findings.length === 0 &&
    !(window.rrwSaveRecovery && window.rrwSaveRecovery.needsReview());
  $('save-edit').disabled = !current || !dirty || unresolved || !$('reply-editor').value.trim();
  $('approve').disabled = !saved || current.findings.length > 0 || !$('human-reviewed').checked || approved;
  $('copy').disabled = !approved;
  $('download').disabled = !approved;
  $('reroll').disabled = !current || unresolved || Boolean(window.rrwGeneration && window.rrwGeneration.hasPending());
  $('set-aside').disabled = !current || unresolved;
  $('human-reviewed').disabled = !saved || current.findings.length > 0 || approved;
  $('approve').textContent = approved ? 'Approved for manual posting' : 'Approve this reply';
  updateProgress();
}
function confirmDiscard(replaceInputs = true) {
  return (!window.rrwSaveRecovery || window.rrwSaveRecovery.canLeave()) &&
    (!replaceInputs || !window.rrwRecovery || window.rrwRecovery.canReplace()) &&
    (!dirty || window.confirm('Discard the unsaved reply edits? The last saved draft will be kept.')) &&
    (!window.rrwFeedback || window.rrwFeedback.canDiscard());
}
function policyChanged(reset = true) {
  const present = Boolean($('offer').value.trim() || $('approved-actions').value.trim());
  $('policy-confirm-row').hidden = !present;
  $('policy-summary').textContent = present ? 'Owner confirmation required' : 'No commitments enabled';
  if (reset) $('policy-confirmed').checked = false;
}
function typeChanged() {
  const followup = $('reply-type').value === 'followup';
  $('thread-fields').hidden = !followup;
  $('original').required = followup;
  $('previous').required = followup;
  $('stars').disabled = followup;
  $('review-label').textContent = followup ? "Customer's update" : 'Customer review';
}
function countReview() { $('review-count').textContent = $('review').value.length.toLocaleString() + ' / 20,000'; }
function settings() {
  return {profile_key: $('profile-select').value, business: $('business').value, kind: $('kind').value, tone: $('tone').value,
    platform: $('platform').value, offer: $('offer').value, signoff: $('signoff').value,
    approved_actions: $('approved-actions').value.split('\n').map(s => s.trim()).filter(Boolean),
    policy_confirmed: $('policy-confirmed').checked};
}
function fillSettings(values) {
  for (const key of ['business', 'kind', 'tone', 'platform', 'offer', 'signoff']) {
    if (values[key] != null) $(key).value = values[key];
    else if (['offer', 'signoff'].includes(key)) $(key).value = '';
  }
  $('approved-actions').value = (values.approved_actions || []).join('\n');
  policyChanged();
  if (window.rrwInbox) window.rrwInbox.invalidatePreview();
}
function fillForm(view) {
  fillSettings(view);
  $('review').value = view.review;
  $('stars').value = view.stars == null ? '' : String(view.stars);
  $('original').value = view.original || '';
  $('previous').value = view.previous || '';
  $('reply-type').value = view.original !== undefined ? 'followup' : 'first';
  $('profile-select').value = '';
  $('profile-name').value = '';
  typeChanged(); countReview();
  if (window.rrwRecovery) window.rrwRecovery.accept();
}
function clearEditor() {
  if (window.rrwSaveRecovery) window.rrwSaveRecovery.selected();
  if (window.rrwFeedback) window.rrwFeedback.reset();
  resetReviewEvidence();
  current = null; dirty = false;
  $('editor-empty').hidden = false;
  $('editor-content').hidden = true;
  $('manual-review-panel').hidden = true;
  $('draft-panel').classList.remove('has-draft');
  $('reply-editor').value = '';
  $('draft-status').textContent = 'No draft yet';
  $('draft-status').className = 'badge neutral';
  $('human-reviewed').checked = false;
  renderQueue(); updateButtons();
}
function showManualReview(review, findings) {
  // A rejected review never leaves an older, possibly approved draft visible.
  clearEditor();
  $('editor-empty').hidden = true;
  $('manual-review-panel').hidden = false;
  $('draft-panel').classList.add('has-draft');
  $('manual-review-text').textContent = review;
  $('manual-review-reasons').replaceChildren(...findings.map(reason => node('li', reason)));
  $('draft-status').textContent = 'Manual only';
  $('draft-status').className = 'badge blocked';
  updateButtons();
  if (window.rrwFocus) window.rrwFocus.request('manual-review-title');
}
function reviewContext(view) {
  return view.original !== undefined ? 'Original review: ' + view.original + '\n\nCustomer update: ' + view.review : view.review;
}
function engineLabel(engine) {
  if (!engine) return 'Imported draft';
  if (engine.includes('template')) return engine.includes('fallback') ? 'Template fallback, not AI output' : 'Template preview, no AI';
  return engine;
}
function renderGenerationStatus(view) {
  const status = view.generation_status || {
    title: 'Generation result not recorded', message: 'No recognized saved generation result is available.',
    next_step: 'Read and check the current reply before approval.', action: null};
  $('generation-status-title').textContent = status.title;
  $('generation-status-panel').open = ['unavailable', 'invalid_response', 'rejected', 'model_unverified'].includes(status.state);
  $('generation-status-message').textContent = status.message;
  $('generation-status-next').textContent = status.next_step;
  $('generation-status-counts').textContent = Number.isInteger(status.attempts) ?
    status.attempts + ' local request attempts · ' + status.checked_completions + ' checked completion receipts' : '';
  $('generation-status-edited').hidden = !view.human_edited;
  $('generation-status-setup').hidden = status.action !== 'setup';
  $('generation-status-quality').hidden = status.action !== 'quality';
}
$('generation-status-setup').addEventListener('click', () => {
  $('setup-guide').open = true;
  if (window.rrwFocus) window.rrwFocus.request('setup-heading', true);
});
$('generation-status-quality').addEventListener('click', () => $('view-quality').click());
function renderQueue() {
  const search = $('queue-search').value.toLowerCase();
  const filter = $('queue-filter').value;
  const items = workspace.drafts.filter(d => (filter === 'all' || d.status === filter) &&
    [d.business, d.review].join(' ').toLowerCase().includes(search));
  $('queue-count').textContent = String(items.length);
  $('queue-list').replaceChildren();
  if (!items.length) {
    const empty = node('div', undefined, 'queue-empty');
    empty.append(node('strong', workspace.drafts.length ? 'No matching drafts' : 'A clean slate'));
    empty.append(node('span', workspace.drafts.length ? 'Try a different search or filter.' : 'Your saved replies will appear here.'));
    $('queue-list').append(empty); return;
  }
  for (const draft of items) {
    const button = node('button', undefined, 'draft-item' + (current && current.id === draft.id ? ' active' : ''));
    button.type = 'button';
    button.setAttribute('aria-label', draft.business + ': ' + (labels[draft.status] || draft.status));
    button.setAttribute('aria-pressed', String(Boolean(current && current.id === draft.id)));
    button.append(node('strong', draft.business || 'Business'));
    button.append(node('span', draft.error || draft.review, 'preview'));
    button.append(node('span', labels[draft.status] || draft.status, 'badge ' + draft.status));
    button.addEventListener('click', () => {
      if (!confirmDiscard()) return;
      run(async () => {
        const view = await api('get', {id: draft.id});
        fillForm(view);
        if (renderDraft(view, true)) notify('Saved draft opened. Its original owner policy is preserved.');
        else notify('This saved review needs personal handling. Routine approval is stopped.', true);
      });
    });
    $('queue-list').append(button);
  }
}
function renderProfiles() {
  const previous = $('profile-select').value;
  $('profile-select').replaceChildren(new Option('New / unsaved business', ''));
  for (const [key, value] of Object.entries(workspace.profiles)) {
    $('profile-select').append(new Option((value.business || key) + ' (' + key + ')', key));
  }
  $('profile-select').value = previous;
}
async function refreshWorkspace() {
  workspace = await api('state');
  renderProfiles(); renderQueue();
}
function renderDraft(view, focusSource = false) {
  if (window.rrwSaveRecovery) window.rrwSaveRecovery.selected();
  showView(false);
  const manual = view.findings.filter(f => f.includes('manual review required'));
  if (manual.length) { showManualReview(reviewContext(view), manual); return false; }
  current = view; dirty = false;
  $('editor-empty').hidden = true; $('editor-content').hidden = false;
  $('manual-review-panel').hidden = true;
  $('draft-panel').classList.add('has-draft');
  $('draft-status').textContent = labels[view.status];
  $('draft-status').className = 'badge ' + view.status;
  $('draft-business').textContent = view.business || 'Business';
  $('draft-tier').textContent = (view.tier || 'Unclassified') + ' review';
  $('draft-source').textContent = engineLabel(view.engine) + (view.human_edited ? ' · edited by owner' : '');
  renderGenerationStatus(view);
  $('saved-review').textContent = view.review;
  $('saved-thread').hidden = view.original === undefined;
  $('saved-original').textContent = view.original || '';
  $('saved-previous').textContent = view.previous || '';
  $('saved-policy').textContent = [view.offer, ...(view.approved_actions || [])].filter(Boolean).join('\n\n') || 'No compensation or action statements authorized.';
  $('reply-editor').value = view.reply;
  renderReviewEvidence(view.review_evidence, view.reply);
  $('reply-count').textContent = view.word_count + ' words · maximum ' + view.word_target[1];
  $('dirty-note').hidden = true;
  $('findings-box').className = 'findings' + (view.findings.length ? ' blocked' : '');
  $('findings-title').textContent = view.findings.length ? 'Changes needed before approval' : 'Passed the current checks. Your review comes next.';
  $('findings-list').replaceChildren(...view.findings.map(f => node('li', f)));
  $('human-reviewed').checked = view.status === 'approved';
  $('trace-content').replaceChildren(node('p', 'Source: ' + (view.engine || 'Imported draft')));
  const trace = view.generation_trace || [];
  if (!trace.length) $('trace-content').append(node('p', 'No model call was recorded for this draft. Templates are not Gemma output.'));
  for (const attempt of trace) {
    $('trace-content').append(node('p', 'Attempt ' + attempt.attempt + ' · temperature ' + attempt.temperature + ' · ' + (attempt.elapsed_ms / 1000).toFixed(1) + 's\n' +
      (attempt.findings.length ? attempt.findings.join('; ') : 'Passed draft checks.')));
  }
  if (view.approval_invalidated) notify('This draft changed after its earlier approval. Review and approve it again.');
  if (window.rrwFeedback) window.rrwFeedback.render(view);
  renderQueue(); updateButtons();
  if (focusSource && window.rrwFocus) window.rrwFocus.request('saved-source-heading', true);
  return true;
}
function idRevision() { return {id: current.id, revision: current.revision}; }

$('compose-form').addEventListener('submit', event => {
  event.preventDefault();
  if (!confirmDiscard(false)) return;
  run(async () => {
    const data = {...settings(), review: $('review').value,
      stars: $('stars').value ? Number($('stars').value) : null,
      followup: $('reply-type').value === 'followup', original: $('original').value,
      previous: $('previous').value, mode: $('engine-mode').value};
    notify(data.mode === 'gemma' ? 'Gemma is drafting and checking. A rejected draft gets one retry; a checked template is the fallback.' : 'Creating a checked template preview. No AI model is being called.');
    let view;
    try { view = await window.rrwGeneration.submit('generate', data); }
    catch (error) {
      const reasons = (error.findings || []).filter(f => f.includes('manual review required'));
      if (error.status === 422 && reasons.length) {
        const submitted = data.followup ? 'Original review: ' + data.original + '\n\nCustomer update: ' + data.review : data.review;
        showManualReview(submitted, reasons);
        notify('Manual handling required. No automated draft was created.', true);
        return;
      }
      throw error;
    }
    renderDraft(view, true);
    if (window.rrwRecovery) window.rrwRecovery.accept();
    await refreshWorkspace();
    notify(view.engine.includes('fallback') ? 'A checked template was saved instead of AI output. Read the saved generation result for the reason and next steps.' : 'Draft saved. Read it, make any edits, then approve the exact reply.');
  });
});
$('manual-back').addEventListener('click', () => {
  $('review').focus();
  $('review').scrollIntoView({behavior: 'smooth', block: 'center'});
});
$('reply-editor').addEventListener('input', () => {
  dirty = Boolean(current && $('reply-editor').value !== current.reply);
  $('dirty-note').hidden = !dirty;
  $('human-reviewed').checked = false;
  $('reply-count').textContent = $('reply-editor').value.trim().split(/\s+/).filter(Boolean).length + ' words' + (dirty ? ' · unsaved' : '');
  if (dirty) { $('draft-status').textContent = 'Unsaved edits'; $('draft-status').className = 'badge pending'; $('findings-title').textContent = 'Edits have not been checked yet.'; $('findings-box').className = 'findings blocked'; $('findings-list').replaceChildren(); }
  else if (current) {
    $('draft-status').textContent = labels[current.status];
    $('draft-status').className = 'badge ' + current.status;
    $('findings-box').className = 'findings' + (current.findings.length ? ' blocked' : '');
    $('findings-title').textContent = current.findings.length ? 'Changes needed before approval' : 'Passed the current checks. Your review comes next.';
    $('findings-list').replaceChildren(...current.findings.map(f => node('li', f)));
    $('human-reviewed').checked = current.status === 'approved' &&
      !(window.rrwSaveRecovery && window.rrwSaveRecovery.needsAttention());
  }
  updateButtons();
  if (window.rrwFeedback) window.rrwFeedback.buttons();
});
$('save-edit').addEventListener('click', () => run(async () => {
  const view = await window.rrwSaveRecovery.submit('edit', {...idRevision(), reply: $('reply-editor').value});
  await window.rrwSaveRecovery.finish(view, view.findings.length ? 'Edits saved, but checks found issues. This draft cannot be approved yet.' : 'Edits saved and checked. Previous approval was cleared.');
}));
$('human-reviewed').addEventListener('change', updateButtons);
$('approve').addEventListener('click', () => run(async () => {
  const view = await window.rrwSaveRecovery.submit('decision', {...idRevision(), status: 'approved', reviewed: $('human-reviewed').checked});
  await window.rrwSaveRecovery.finish(view, 'Approved. Copy or export this exact reply for manual posting.');
}));
$('set-aside').addEventListener('click', () => {
  if (!confirmDiscard(false)) return;
  run(async () => { const view = await window.rrwSaveRecovery.submit('decision', {...idRevision(), status: 'aside'});
    await window.rrwSaveRecovery.finish(view, 'Draft set aside. It remains in your workspace.'); });
});
$('reroll').addEventListener('click', () => {
  if (!confirmDiscard(false)) return;
  run(async () => { notify('Regenerating with the policy saved in this draft.');
    let view;
    try { view = await window.rrwGeneration.submit('reroll', {...idRevision(), mode: $('engine-mode').value}); }
    catch (error) {
      const reasons = (error.findings || []).filter(f => f.includes('manual review required'));
      if (error.status === 422 && reasons.length) {
        showManualReview(reviewContext(current), reasons);
        notify('Manual handling required. No new automated draft was saved.', true);
        return;
      }
      throw error;
    }
    renderDraft(view, true); await refreshWorkspace(); notify('New draft saved. Review it before approving.'); });
});
$('copy').addEventListener('click', () => run(async () => {
  const result = await api('approved-text', idRevision());
  try { await navigator.clipboard.writeText(result.text); notify('Approved reply copied. Nothing has been posted.'); }
  catch (error) { requestAnimationFrame(() => { $('reply-editor').focus(); $('reply-editor').select(); }); notify('Automatic copy is unavailable. Approved text is selected; press Ctrl+C or Command+C.'); }
}));
$('download').addEventListener('click', () => run(async () => {
  const result = await api('approved-text', idRevision());
  const url = URL.createObjectURL(new Blob([result.text], {type: 'text/plain;charset=utf-8'}));
  const link = node('a'); link.href = url; link.download = result.filename;
  document.body.append(link); link.click(); link.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  notify('Approved reply exported as plain text. Nothing has been posted.');
}));
$('save-profile').addEventListener('click', () => run(async () => {
  const result = await api('profile', {...settings(), name: $('profile-name').value,
    profiles_revision: workspace.profiles_revision});
  await refreshWorkspace(); $('profile-select').value = result.name; notify('Business profile saved locally. Existing drafts keep their original policy.');
  if (window.rrwRecovery) window.rrwRecovery.profileLoaded();
}));
$('profile-select').addEventListener('change', () => {
  const key = $('profile-select').value;
  if (key && window.rrwRecovery && !window.rrwRecovery.canLoadProfile()) {
    $('profile-select').value = window.rrwRecovery.previousProfile(); return;
  }
  if (key && workspace.profiles[key]) { fillSettings(workspace.profiles[key]); $('profile-name').value = key;
    notify('Profile loaded. Confirm any owner commitments before generating a new reply.'); }
  if (window.rrwRecovery) window.rrwRecovery.profileLoaded();
});
for (const id of ['business', 'offer', 'approved-actions']) $(id).addEventListener('input', () => policyChanged());
$('review').addEventListener('input', countReview);
$('reply-type').addEventListener('change', typeChanged);
$('queue-search').addEventListener('input', renderQueue);
$('queue-filter').addEventListener('change', renderQueue);
$('new-draft').addEventListener('click', () => {
  if (!confirmDiscard()) return;
  showView(false); clearEditor(); $('review').value = ''; $('original').value = ''; $('previous').value = '';
  $('stars').value = ''; $('reply-type').value = 'first'; policyChanged(); typeChanged(); countReview();
  if (window.rrwRecovery) window.rrwRecovery.accept(['review', 'original', 'previous', 'stars', 'followup']);
  notify('New reply. Your saved drafts are still in the library.'); $('review').focus();
});
for (const button of document.querySelectorAll('[data-sample]')) button.addEventListener('click', () => {
  if (!confirmDiscard()) return;
  clearEditor(); const sample = samples[button.dataset.sample];
  fillSettings({...sample, tone: 'professional', platform: 'google', approved_actions: []});
  $('profile-select').value = ''; $('profile-name').value = '';
  $('review').value = sample.review; $('stars').value = String(sample.stars);
  $('original').value = ''; $('previous').value = '';
  $('reply-type').value = 'first'; typeChanged(); countReview();
  if (window.rrwRecovery) window.rrwRecovery.accept();
  notify('Fictional example loaded with no owner commitments. Generate a draft to try the workflow.');
});
$('refresh-queue').addEventListener('click', () => run(async () => {
  await refreshWorkspace();
  const attention = window.rrwSaveRecovery && window.rrwSaveRecovery.needsAttention();
  if (current && !dirty && !attention) renderDraft(await api('get', {id: current.id}));
  notify(dirty || attention ? 'Library refreshed. Your editor and saved-state check were preserved.' : 'Workspace refreshed.');
}));
async function checkModel() {
  const result = await api('model');
  const labels = {installed: 'Gemma installed · installation check only', missing: 'Gemma missing · templates ready',
    unavailable: 'Ollama offline · templates ready', unverified: 'Model needs attention · templates ready'};
  $('model-status').textContent = labels[result.state] || 'Check model setup';
  $('model-status').className = 'badge neutral';
  $('setup-model-message').textContent = result.message;
  return result;
}
$('refresh-model').addEventListener('click', () => run(checkModel));
$('setup-recheck').addEventListener('click', () => run(checkModel));
$('setup-example').addEventListener('click', () => {
  $('view-drafts').click();
  document.querySelector('[data-sample="negative"]').click();
});
$('setup-quality').addEventListener('click', () => $('view-quality').click());
$('engine-mode').addEventListener('change', () => {
  $('engine-note').textContent = $('engine-mode').value === 'gemma'
    ? 'Uses gemma3:4b through local Ollama. Enable Ollama local-only mode. Rejected or unavailable output falls back to a labelled template.'
    : 'Template preview lets you try the workflow without a model. Nothing is posted.';
});
window.addEventListener('beforeunload', event => { if (dirty || busy || qualityDirty || (window.rrwSaveRecovery && window.rrwSaveRecovery.needsAttention()) || (window.rrwGeneration && window.rrwGeneration.hasPending()) || (window.rrwFeedback && window.rrwFeedback.hasUnsaved()) || (window.rrwRecovery && window.rrwRecovery.hasInputChanges())) { event.preventDefault(); event.returnValue = ''; } });


// Quality experiments are separate from real drafts and publication approvals.
let qualityRun = null;
let qualityCase = null;
let qualityDirty = false;
function showView(value) {
  const selected = value === 'submission' ? 'submission' : (value ? 'quality' : 'drafts');
  $('inbox-panel').hidden = selected !== 'drafts';
  for (const [name, panel] of [['drafts', 'draft-panel'], ['quality', 'quality-panel'], ['submission', 'submission-panel']]) {
    $(panel).hidden = selected !== name;
    $('view-' + name).classList.toggle('active', selected === name);
    $('view-' + name).setAttribute('aria-pressed', String(selected === name));
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
