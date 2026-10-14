'use strict';

// A programmatic reset can accept only the fields it actually replaced.
class InputTracker {
  constructor(values) { this.baseline = {}; this.accept(values); }
  accept(values, keys = Object.keys(values)) {
    for (const key of keys) this.baseline[key] = JSON.stringify(values[key]);
  }
  changed(values, keys = Object.keys(values)) {
    return keys.some(key => JSON.stringify(values[key]) !== this.baseline[key]);
  }
}
if (typeof module !== 'undefined' && module.exports) module.exports = {InputTracker};
else (() => {
  let saved = null;
  let recoveredInputs = false;
  let recoveredSettings = false;
  let previousProfile = $('profile-select').value;
  const settingsKeys = ['business', 'kind', 'tone', 'platform', 'offer', 'signoff', 'approved_actions'];
  function inputs() {
    const value = settings();
    delete value.profile_key; delete value.policy_confirmed;
    return {...value, review: $('review').value, stars: $('stars').value ? Number($('stars').value) : null,
      followup: $('reply-type').value === 'followup', original: $('original').value, previous: $('previous').value,
      mode: 'offline'};
  }
  const tracker = new InputTracker(inputs());
  function accept(keys) {
    tracker.accept(inputs(), keys); previousProfile = $('profile-select').value;
    if (keys === undefined) { recoveredInputs = false; recoveredSettings = false; }
  }
  function hasInputChanges() { return recoveredInputs || tracker.changed(inputs()); }
  function canReplace() {
    return !hasInputChanges() || window.confirm('Replace changed review inputs? Saved drafts and recovery copies will be kept.');
  }
  function canLoadProfile() {
    return (!recoveredSettings && !tracker.changed(inputs(), settingsKeys)) || window.confirm('Replace changed business settings with this saved profile? Your review text will be kept.');
  }
  function show(value) {
    saved = value;
    $('recovery-status').textContent = value.available
      ? 'Working copy saved ' + value.saved_at + '. ' + (value.editor_state === 'current'
        ? 'Reply edits match the saved draft version.' : value.editor_state === 'none'
        ? 'Review inputs only.' : 'Reply edits belong to a changed, missing or unreadable draft and need manual comparison.')
      : 'No recovery copy is saved. Your current form and reply editor are kept.';
    buttons();
  }
  function buttons() {
    if (busy) return;
    $('recovery-save').disabled = !saved;
    $('recovery-restore').disabled = !saved || !saved.available;
    $('recovery-clear').disabled = !saved || !saved.available;
  }
  function copyMatches(actual, expected) {
    const snapshot = payload => JSON.stringify({inputs: Object.keys(payload.inputs).sort().map(key => {
      let value = payload.inputs[key];
      if (typeof value === 'string') value = value.trim();
      if (key === 'approved_actions') value = value.map(text => text.trim());
      return [key, value];
    }), editor: payload.editor === null ? null : Object.keys(payload.editor).sort().map(key => [key, payload.editor[key]])});
    try { return snapshot(actual) === snapshot(expected); }
    catch (error) { return false; }
  }
  async function changeCopy(action, data) {
    try {
      const value = await api(action, data);
      if (!value || !/^[0-9a-f]{64}$/.test(value.revision || '') ||
          value.available !== (action === 'recovery-save') ||
          (value.available ? !copyMatches(value.payload, data.payload) : value.payload !== null)) {
        const error = new Error('The working-copy change returned no matching receipt. Check the saved copy; your current inputs are kept.');
        error.uncertain = true; throw error;
      }
      return value;
    }
    catch (error) {
      if (error.uncertain || !error.status || error.status >= 500 || error.status === 409) {
        saved = null;
        $('recovery-status').textContent = 'The working-copy change is uncertain or changed elsewhere. Current inputs and reply edits are kept. Check the saved copy before saving, recovering or discarding it; no retry was sent.';
        buttons();
      }
      throw error;
    }
  }
  $('recovery-check').addEventListener('click', () => run(async () => show(await api('recovery-get', {}))));
  $('recovery-save').addEventListener('click', () => run(async () => {
    if (!saved) throw new Error('Check for an earlier recovery copy first.');
    const editor = current && dirty ? {id: current.id, revision: current.revision, reply: $('reply-editor').value} : null;
    show(await changeCopy('recovery-save', {revision: saved.revision, payload: {inputs: inputs(), editor}}));
    notify('Working copy saved privately. It does not save, approve or post the reply.');
  }));
  $('recovery-restore').addEventListener('click', () => {
    if (!saved || !saved.available || !confirmDiscard()) return;
    run(async () => {
      const value = await api('recovery-get', {});
      if (value.revision !== saved.revision) throw new Error('Recovery copy changed elsewhere. Check the saved copy before restoring.');
      if (!value.available) throw new Error('The recovery copy is no longer available.');
      let editorView = null;
      const edit = value.payload.editor;
      if (edit && value.editor_state === 'current') {
        const view = await api('get', {id: edit.id});
        if (view.revision === edit.revision) editorView = view;
      }
      clearEditor();
      const restored = {...value.payload.inputs};
      if (!restored.followup) { delete restored.original; delete restored.previous; }
      fillForm(restored);
      $('engine-mode').value = 'offline'; $('engine-mode').dispatchEvent(new Event('change'));
      $('policy-confirmed').checked = false;
      $('recovery-orphan').hidden = true; $('recovery-orphan-text').value = '';
      if (editorView && renderDraft(editorView)) {
        $('reply-editor').value = edit.reply;
        $('reply-editor').dispatchEvent(new Event('input', {bubbles: true}));
        if (window.rrwFocus) window.rrwFocus.request('reply-editor');
      } else if (edit) {
        $('recovery-orphan').hidden = false; $('recovery-orphan').open = true;
        $('recovery-orphan-text').value = edit.reply;
        if (window.rrwFocus) window.rrwFocus.request('recovery-orphan-text', true);
      } else if (window.rrwFocus) {
        window.rrwFocus.request('review');
      }
      accept(); recoveredInputs = true; recoveredSettings = true; show(value);
      notify('Working copy recovered. Confirm owner policy again. Reply edits still need saving, checks and human review.');
    });
  });
  $('recovery-clear').addEventListener('click', () => {
    if (!saved || !saved.available || !window.confirm('Discard the saved recovery copy? Your current form and reply editor will be kept.')) return;
    run(async () => {
      if (!saved) throw new Error('Check the saved recovery copy before discarding it.');
      show(await changeCopy('recovery-clear', {revision: saved.revision}));
      $('recovery-orphan').hidden = true; $('recovery-orphan-text').value = '';
      notify('Recovery copy discarded. Current editor text and saved drafts were kept.');
    });
  });
  window.rrwRecovery = {accept, hasInputChanges, canReplace, canLoadProfile,
    previousProfile: () => previousProfile,
    profileSelected: () => { previousProfile = $('profile-select').value; },
    profileLoaded: () => { accept(settingsKeys); recoveredSettings = false; }, buttons};
  // Initialize independently of workspace/model checks; a damaged optional copy must not block drafting.
  api('recovery-get', {}).then(show).catch(() => {
    $('recovery-status').textContent = 'Recovery copy could not be checked. Drafting still works; the saved file was preserved.';
  });
})();
