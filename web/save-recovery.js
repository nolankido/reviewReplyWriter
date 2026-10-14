'use strict';
(() => {
  let pending = null, checked = null, reviewRequired = false;
  function needsAttention() { return Boolean(pending || reviewRequired); }
  function selected() {
    pending = null; checked = null; reviewRequired = false;
    $('save-recovery-panel').hidden = true;
    $('save-recovery-reply').value = '';
    $('save-recovery-status').textContent = '';
  }
  function buttons() {
    if (busy) return;
    $('save-recovery-check').disabled = !current;
    const ready = current && checked && checked.id === current.id;
    $('save-recovery-keep').disabled = !ready;
    $('save-recovery-load').disabled = !ready;
  }
  function message(value) {
    $('save-recovery-panel').hidden = false;
    $('save-recovery-message').textContent = value;
    buttons();
  }
  async function submit(action, data) {
    if (pending) throw new Error('Check the uncertain saved change before sending another edit or decision.');
    try { return await api(action, data); }
    catch (error) {
      if (error.uncertain || !error.status || error.status >= 500 || error.status === 409) {
        pending = {id: data.id, revision: data.revision}; checked = null;
        $('save-recovery-reply').value = '';
        $('save-recovery-status').textContent = '';
        $('human-reviewed').checked = false;
        message('The saved outcome is uncertain or the revision changed. Your editor text is kept. Check the latest saved reply before another save, approval or copy. No retry was sent.');
      }
      throw error;
    }
  }
  async function finish(view, success) {
    // The mutation already returned an authoritative checked view. A separate
    // library read must not hide that success or leave the old revision loaded.
    renderDraft(view);
    notify(success);
    try { await refreshWorkspace(); }
    catch (error) { notify(success + ' The library could not refresh; the saved reply is shown. Refresh the library later.', true); }
  }
  async function check() {
    if (!current) return;
    const identifier = current.id;
    checked = null;
    const view = await api('get', {id: identifier});
    if (!current || current.id !== identifier) throw new Error('The selected draft changed. Check its saved reply again.');
    checked = view;
    if (view.revision !== current.revision || view.status !== current.status) {
      pending = {id: identifier, revision: current.revision};
      $('human-reviewed').checked = false;
    }
    $('save-recovery-reply').value = view.reply;
    $('save-recovery-status').textContent = 'Latest saved status: ' + (labels[view.status] || view.status) +
      '. ' + (view.findings.length ? 'Changes needed before approval.' : 'Passed current checks; human review still applies.');
    const same = view.reply === $('reply-editor').value;
    message((same ? 'The latest saved reply matches your editor text.' : 'The latest saved reply differs from your editor text. Both are kept separately.') +
      ' Checking has not changed the editor, review inputs, owner policy or approval. Choose which text to continue with.');
  }
  async function adopt(keep) {
    if (!current || !checked || checked.id !== current.id) return;
    const target = checked;
    const view = await api('get', {id: target.id});
    if (view.revision !== target.revision || view.status !== target.status) {
      checked = null;
      message('The saved reply or decision changed again. Your editor was kept. Check the latest version before choosing.');
      return;
    }
    if (view.findings.some(f => f.includes('manual review required'))) {
      message('This saved review needs personal handling. Your editor text is kept for inspection; it cannot become a routine approved reply.');
      return;
    }
    const editor = $('reply-editor').value;
    if (!keep && editor !== view.reply && !window.confirm('Replace the current editor text with this checked saved reply? Keep a private working copy first if you need the current edits.')) return;
    // Never write during reconciliation. Future writes use the freshly read
    // revision and saved policy, not this tab's former source or compose policy.
    renderDraft(view);
    if (keep) {
      $('reply-editor').value = editor;
      $('reply-editor').dispatchEvent(new Event('input', {bubbles: true}));
    }
    reviewRequired = true;
    $('human-reviewed').checked = false;
    $('policy-confirmed').checked = false;
    updateButtons(); buttons();
    notify(keep ? 'Editor text kept against the checked saved version. Save and recheck any differences, then review and approve explicitly.'
      : 'Checked saved reply loaded. Read its source and policy, then review and approve explicitly. Nothing was posted.');
    $('reply-editor').focus();
  }
  $('save-recovery-check').addEventListener('click', () => run(check));
  $('save-recovery-keep').addEventListener('click', () => run(() => adopt(true)));
  $('save-recovery-load').addEventListener('click', () => run(() => adopt(false)));
  window.rrwSaveRecovery = {submit, finish, buttons, selected, needsAttention,
    unresolved: () => Boolean(pending), needsReview: () => reviewRequired,
    canLeave: () => !needsAttention() || dirty || window.confirm('Leave this saved-state review? It has not cancelled or repeated a request. Saved drafts remain in the library.')};
  buttons();
})();
