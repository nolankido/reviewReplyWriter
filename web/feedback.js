'use strict';
(() => {
  let selected = null;
  let noteRevision = 'new';
  let formBaseline = '';
  let noteDirty = false;
  let replyChanged = false;
  const controls = ['review-note-role', 'review-note-scenario', 'review-note-decision',
    'review-note-text', 'review-note-seconds'];
  const reasons = () => [...document.querySelectorAll('[name="review-reason"]')];

  function assessment() {
    return {role: $('review-note-role').value, scenario: $('review-note-scenario').value,
      decision: $('review-note-decision').value, note: $('review-note-text').value,
      reasons: reasons().filter(box => box.checked).map(box => box.value),
      review_seconds: $('review-note-seconds').value === '' ? null : Number($('review-note-seconds').value)};
  }
  function fillNote(value) {
    const a = value.assessment || {};
    for (const [key, id] of [['role', 'review-note-role'], ['scenario', 'review-note-scenario'],
      ['decision', 'review-note-decision'], ['note', 'review-note-text'], ['review_seconds', 'review-note-seconds']]) {
      $(id).value = a[key] == null ? '' : String(a[key]);
    }
    for (const box of reasons()) box.checked = (a.reasons || []).includes(box.value);
    noteRevision = value.revision;
    formBaseline = JSON.stringify(assessment());
    noteDirty = false;
    replyChanged = false;
  }
  function noteState() {
    if (!selected) return;
    const note = selected.review_note;
    $('review-note-target').textContent = selected.reply_comparison.available
      ? 'Usefulness of the starting draft' : 'Usefulness of the saved reply (starting draft unavailable)';
    $('review-note-state').textContent = note.error || (dirty ? 'Save and recheck reply edits before recording an assessment.'
      : replyChanged && noteDirty ? 'The saved reply changed. Check that these unsaved notes still describe the version you assessed.'
      : noteDirty ? 'Unsaved assessment. Save it or keep editing; posting approval is separate.'
      : note.assessment && !note.current ? 'Earlier assessment belongs to a different saved draft. Reassess before updating it.'
      : note.assessment ? 'Assessment saved for this draft version. It does not approve posting.'
      : 'Optional observations, separate from posting approval. Choose only facts you observed.');
  }
  function buttons() {
    if (busy) return;
    const ready = selected && !dirty && noteRevision !== null;
    const needsSave = noteDirty || (selected && selected.review_note.assessment && !selected.review_note.current);
    $('review-note-save').disabled = !ready || !needsSave || !$('review-note-form').checkValidity();
    $('review-note-reload').disabled = !selected;
    $('comparison-restore').disabled = !selected || !selected.reply_comparison.available ||
      $('reply-editor').value === selected.reply_comparison.baseline_reply;
    if (selected) {
      const c = selected.reply_comparison;
      $('comparison-state').textContent = dirty ? 'Unsaved edits are not shown here. Save & recheck to compare them.'
        : !c.available ? c.message : !c.changed ? 'The saved reply matches the starting draft.'
        : 'Starting draft: ' + c.baseline_words + ' words. Saved reply: ' + c.saved_words + ' words. ' +
          (c.highlight_limited ? 'Long text is shown without highlights.' : 'Removed wording is marked on the left; added wording on the right.');
    }
    noteState();
  }
  function render(view) {
    const same = selected && selected.id === view.id;
    if (same && selected.revision !== view.revision) replyChanged = true;
    if (!same || !noteDirty) fillNote(view.review_note);
    selected = view;
    const c = view.reply_comparison;
    $('comparison-panes').hidden = !c.available;
    $('comparison-before').replaceChildren(); $('comparison-after').replaceChildren();
    $('comparison-source').textContent = c.available ? engineLabel(c.baseline_engine) : '';
    if (c.available) {
      if (c.highlight_limited) {
        $('comparison-before').textContent = c.baseline_reply;
        $('comparison-after').textContent = view.reply;
      } else for (const part of c.changes) {
        if (part.before) $('comparison-before').append(node(['delete', 'replace'].includes(part.kind) ? 'del' : 'span', part.before));
        if (part.after) $('comparison-after').append(node(['insert', 'replace'].includes(part.kind) ? 'ins' : 'span', part.after));
      }
    }
    buttons();
  }
  function reset() { selected = null; noteDirty = false; replyChanged = false; }
  function canDiscard() {
    return !noteDirty || window.confirm('Discard unsaved review assessment notes? Saved notes will be kept.');
  }
  for (const element of [...controls.map(id => $(id)), ...reasons()]) element.addEventListener('input', () => {
    noteDirty = JSON.stringify(assessment()) !== formBaseline; buttons();
  });
  $('comparison-restore').addEventListener('click', () => {
    if (!selected || !selected.reply_comparison.available) return;
    if (dirty && !window.confirm('Replace unsaved reply edits with the starting draft?')) return;
    $('reply-editor').value = selected.reply_comparison.baseline_reply;
    $('reply-editor').dispatchEvent(new Event('input', {bubbles: true}));
    $('reply-editor').focus();
    notify('Starting draft loaded in the editor. Save, recheck and review it before approval.');
  });
  $('review-note-form').addEventListener('submit', event => {
    event.preventDefault();
    if (!selected || dirty || noteRevision === null) return;
    run(async () => {
      const value = await api('feedback-save', {id: selected.id, revision: selected.revision,
        note_revision: noteRevision, assessment: assessment()});
      selected.review_note = value;
      fillNote(value);
      noteState();
      notify('Private assessment saved. Posting approval is separate.');
    });
  });
  $('review-note-reload').addEventListener('click', () => {
    if (!selected || !canDiscard()) return;
    run(async () => {
      const view = await api('get', {id: selected.id});
      if (!current || view.revision !== current.revision) {
        notify('The draft changed elsewhere. Refresh and read the saved draft before reloading its notes.', true); return;
      }
      selected.review_note = view.review_note;
      fillNote(view.review_note); noteState();
      notify('Saved assessment reloaded. Your reply editor was kept.');
    });
  });
  $('review-note-export').addEventListener('click', () => run(async () => {
    const result = await api('feedback-summary', {});
    const url = URL.createObjectURL(new Blob([result.text], {type: 'application/json;charset=utf-8'}));
    const link = document.createElement('a'); link.href = url; link.download = result.filename;
    document.body.append(link); link.click(); link.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000);
    notify('Counts exported without private notes or customer text. Counts describe drafts, not users.');
  }));
  window.rrwFeedback = {render, reset, buttons, canDiscard, hasUnsaved: () => noteDirty};
})();
