'use strict';
(function () {
  let pending = '', checked = null;
  function storage(action, value) {
    try {
      if (action === 'read') return sessionStorage.getItem('rrw-generation-request') || '';
      if (value) sessionStorage.setItem('rrw-generation-request', value);
      else sessionStorage.removeItem('rrw-generation-request');
    } catch (error) {
      $('session-storage-note').hidden = false;
      $('session-storage-note').textContent = 'Browser storage could not keep this result check across reloads. Keep this tab open to check it, or inspect saved drafts in the library after reopening with a current launcher link.';
    }
    return '';
  }
  const stored = storage('read');
  if (/^[0-9a-f]{32}$/.test(stored)) pending = stored;
  function buttons() {
    $('generation-recovery').hidden = !pending;
    if (busy) return;
    $('generation-check').disabled = !pending;
    $('generation-open').disabled = !checked || checked.state !== 'saved' || !['current', 'changed'].includes(checked.draft_state);
    $('generation-dismiss').disabled = !pending;
    if (pending) { $('generate').disabled = true; $('reroll').disabled = true; }
    else $('generate').disabled = false;
  }
  function message(text) { $('generation-message').textContent = text; buttons(); }
  function clear() { pending = ''; checked = null; storage('write', ''); updateButtons(); buttons(); }
  async function submit(action, data) {
    if (pending) throw new Error('Check the previous generation result before starting another draft.');
    const bytes = new Uint8Array(16); crypto.getRandomValues(bytes);
    pending = Array.from(bytes, b => b.toString(16).padStart(2, '0')).join('');
    checked = null; storage('write', pending);
    message('A generation request is in progress. Closing this tab or losing the connection does not stop the server.');
    try {
      const view = await api(action, {...data, request_id: pending});
      clear(); return view;
    } catch (error) {
      if (error.status && error.status >= 400 && error.status < 500 && error.status !== 409) clear();
      else message('The result is uncertain. Check this request before generating again. No retry has been sent.');
      throw error;
    }
  }
  $('generation-check').addEventListener('click', () => run(async () => {
    const result = await api('generation-check', {request_id: pending});
    checked = result;
    const labels = {
      pending: 'The server is still working. Check again later. Do not resend the request.',
      saved: result.draft_state === 'current' ? 'Your draft was saved. Open it when you are ready to replace the current form.'
        : result.draft_state === 'changed' ? 'A draft was saved and later changed. Open its current version and review it again.'
        : 'A saved draft was recorded, but its file is missing or unreadable. Inspect the library and preserve your files.',
      failed: 'The request ended without a readable saved result. Your inputs are kept. Inspect the library if files need recovery, then dismiss this check before a new request.',
      interrupted: 'The server restarted before this request completed, and no readable saved result was found. Inspect the library before starting again.',
      unknown: 'This workspace has no receipt for that request. It may not have arrived, or a different workspace may be open. Inspect the library before starting again.'
    };
    message(labels[result.state] || 'The request needs manual inspection.');
  }));
  $('generation-open').addEventListener('click', () => {
    if (!confirmDiscard()) return;
    run(async () => {
      const view = await api('get', {id: checked.draft_id});
      const changed = view.revision !== checked.revision;
      // Opening is explicit. Never overwrite a newer draft or form in response
      // to a late completion, and never restore policy authorization.
      fillForm(view); renderDraft(view); clear();
      notify(changed ? 'The saved draft changed. Its current version is open. Read the reply and policy again.'
        : 'Saved generation opened. Read the current reply and policy before approving.');
      await refreshWorkspace();
    });
  });
  $('generation-dismiss').addEventListener('click', () => {
    if ((!checked || !['saved', 'failed'].includes(checked.state)) &&
        !window.confirm('The result is still uncertain. Dismissing this check does not cancel the server. Inspect the library before generating again. Dismiss anyway?')) return;
    clear(); notify('Result check dismissed. Saved drafts remain in the library.');
  });
  window.rrwGeneration = {submit, buttons, hasPending: () => Boolean(pending)};
  if (pending) message('A previous generation needs checking. Your form will not be replaced automatically.');
  buttons();
})();
