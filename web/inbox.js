'use strict';
(() => {
  let preview = null;
  let previewRequest = null;
  let selected = null;
  let initialized = false;
  const handlingDirty = new Set();
  function sourceInputs() { return {csv: $('inbox-csv').value, label: $('inbox-label').value}; }
  const sourceTracker = new InputTracker(sourceInputs());
  function hasUnsaved() { return handlingDirty.size > 0 || sourceTracker.changed(sourceInputs()); }
  const status = {pending: 'Ready to draft', manual: 'Personal handling', invalid: 'Fix the source row',
    duplicate: 'Duplicate, not drafted', drafted: 'Draft saved', generating: 'Drafting',
    error: 'Needs attention', blocked: 'Draft blocked', interrupted: 'Interrupted', skipped: 'Skipped'};

  function buttons() {
    if (busy) return;
    $('inbox-create').disabled = !preview || !$('inbox-confirm').checked ||
      !(preview.counts.pending + preview.counts.manual);
    $('inbox-next').disabled = !selected || selected.active || !selected.counts.pending;
  }
  function invalidatePreview() {
    preview = null; previewRequest = null;
    $('inbox-preview').hidden = true;
    $('inbox-confirm').checked = false;
    buttons();
  }
  function discardHandling(exceptRow = null) {
    return ![...handlingDirty].some(id => id !== exceptRow) ||
      window.confirm('Discard other unsaved private handling notes? Saved notes will be kept.');
  }
  function describeCounts(counts) {
    return (counts.pending || 0) + ' ready · ' + (counts.manual || 0) + ' personal handling · ' +
      (counts.duplicate || 0) + ' duplicates · ' + (counts.invalid || 0) + ' invalid · ' +
      (counts.drafted || 0) + ' drafted' + (counts.manual_handled ? ' · ' + counts.manual_handled + ' personally handled' : '');
  }
  function rowElement(row, record) {
    const card = node('article', undefined, 'inbox-row');
    const heading = node('header');
    heading.append(node('strong', 'CSV row ' + row.row + (row.external_id ? ' · ' + row.external_id : '')),
      node('span', status[row.status] || row.status, 'badge neutral'));
    card.append(heading, node('p', row.review.slice(0, 150) + (row.review.length > 150 ? '…' : '')));
    if (row.review.length > 150) {
      const original = node('details');
      original.append(node('summary', 'Read the complete review'), node('p', row.review, 'preserve'));
      card.append(original);
    }
    if (row.stars != null) card.append(node('p', row.stars + ' stars', 'helper'));
    for (const reason of row.findings || []) card.append(node('p', reason, 'helper'));
    if (row.engine) card.append(node('p', engineLabel(row.engine), 'helper'));
    if (!record) return card;
    const actions = node('div', undefined, 'editor-tools');
    if (row.status === 'manual') {
      const read = node('button', 'Read for personal handling', 'button secondary'); read.type = 'button';
      read.addEventListener('click', () => {
        if (!confirmDiscard()) return;
        fillForm({...record.settings, review: row.review, stars: row.stars});
        showView(false); showManualReview(row.review, row.findings);
        notify('This review needs personal handling. Routine drafting and approval are stopped.', true);
      });
      actions.append(read);
      const details = node('details');
      details.append(node('summary', row.handled ? 'Personal handling recorded' : 'Record private handling'));
      const form = node('form');
      const label = node('label', 'Private handling note');
      const field = node('textarea'); field.rows = 3; field.maxLength = 1200;
      field.id = 'handling-note-' + row.id; field.value = row.handling_note || '';
      label.htmlFor = field.id;
      const check = node('input'); check.type = 'checkbox'; check.checked = Boolean(row.handled);
      const checkLabel = node('label', undefined, 'check-row');
      checkLabel.append(check, node('span', 'I have personally handled this review. This is not posting approval.'));
      const save = node('button', 'Save private handling', 'button secondary'); save.type = 'submit';
      form.append(label, field, checkLabel, save,
        node('p', 'Notes stay in the local inbox. They are not model input, owner authorization or permission to publish.', 'helper'));
      form.addEventListener('submit', event => {
        event.preventDefault();
        if (!discardHandling(row.id)) return;
        run(async () => {
          render(await api('inbox-note', {id: selected.id, revision: selected.revision, row_id: row.id,
            note: field.value, handled: check.checked}));
          notify('Private handling saved. The review remains outside automated drafting and posting approval.');
        });
      });
      form.addEventListener('input', () => handlingDirty.add(row.id));
      form.addEventListener('change', () => handlingDirty.add(row.id));
      details.append(form); card.append(details);
    }
    if (row.draft_id) {
      card.append(node('p', 'Approval: ' + (labels[row.draft_status] || row.draft_status), 'helper'));
      const open = node('button', 'Review draft', 'button secondary');
      open.type = 'button';
      open.disabled = row.draft_status === 'unavailable';
      open.addEventListener('click', () => {
        if (!confirmDiscard()) return;
        run(async () => {
          const view = await api('get', {id: row.draft_id});
          fillForm(view);
          if (renderDraft(view, true)) {
            notify('Inbox draft opened. Read, edit and approve this exact reply individually.');
          } else notify('This saved review needs personal handling. Routine approval is stopped.', true);
        });
      });
      actions.append(open);
    }
    for (const [action, label] of [['skip', 'Skip this review'], ['retry', 'Retry interrupted review']]) {
      const allowed = action === 'skip' ? ['pending', 'error', 'interrupted'].includes(row.status)
        : ['error', 'interrupted'].includes(row.status) && !row.recovery_conflict;
      if (!allowed) continue;
      const button = node('button', label, 'text-button'); button.type = 'button';
      button.addEventListener('click', () => {
        if (!discardHandling()) return;
        run(async () => {
        render(await api('inbox-' + action, {id: selected.id, revision: selected.revision, row_id: row.id}));
        notify(action === 'skip' ? 'Review skipped. Its source remains in the inbox.' : 'Recovery checked. A saved draft is reused; unfinished work is ready for an explicit new attempt.');
        });
      });
      actions.append(button);
    }
    card.append(actions);
    return card;
  }
  function render(record) {
    handlingDirty.clear();
    selected = record;
    $('inbox-saved').hidden = false;
    $('inbox-saved-title').textContent = record.label;
    $('inbox-saved-info').textContent = record.settings.business + ' · ' + record.settings.tone +
      ' · ' + record.settings.platform + ' · No owner commitments imported';
    $('inbox-saved-counts').textContent = describeCounts(record.counts);
    $('inbox-saved-rows').replaceChildren(...record.rows.map(row => rowElement(row, record)));
    buttons();
  }
  async function reload() {
    const result = await api('inbox-list', {});
    const previous = selected && selected.id;
    $('inbox-select').replaceChildren(new Option('Choose a saved inbox', ''));
    for (const item of result.inboxes) $('inbox-select').append(new Option(item.label + ' · ' + item.settings.business, item.id));
    if (previous && result.inboxes.some(x => x.id === previous)) {
      $('inbox-select').value = previous;
      render(await api('inbox-get', {id: previous}));
    }
    initialized = true;
    buttons();
  }
  $('inbox-details').addEventListener('toggle', () => {
    if ($('inbox-details').open && !initialized) run(reload);
  });
  $('inbox-refresh').addEventListener('click', () => { if (discardHandling()) run(reload); });
  $('inbox-csv').addEventListener('input', invalidatePreview);
  for (const id of ['business', 'kind', 'tone', 'platform', 'signoff', 'profile-select']) {
    $(id).addEventListener('change', invalidatePreview);
    if (['business', 'signoff'].includes(id)) $(id).addEventListener('input', invalidatePreview);
  }
  $('inbox-file').addEventListener('change', () => run(async () => {
    const file = $('inbox-file').files[0];
    if (!file) return;
    if (sourceTracker.changed(sourceInputs()) &&
        !window.confirm('Replace unsaved inbox CSV and name? Saved inboxes and handling notes will be kept.')) {
      $('inbox-file').value = ''; return;
    }
    const before = sourceInputs();
    if (file.size > 48 * 1024) throw new Error('Choose a UTF-8 CSV of at most 48 KiB. Your current CSV and name have been kept.');
    let csv;
    try { csv = new TextDecoder('utf-8', {fatal: true}).decode(await file.arrayBuffer()); }
    catch (error) { throw new Error('This file could not be read as UTF-8. Your current CSV and name have been kept.'); }
    if (JSON.stringify(sourceInputs()) !== JSON.stringify(before))
      throw new Error('The inbox source changed while reading the file. Current text has been kept. Choose the file again.');
    invalidatePreview();
    $('inbox-csv').value = csv;
    $('inbox-label').value = file.name.slice(0, 140);
    notify('CSV loaded in this tab. Preview it before saving an inbox.');
  }));
  $('inbox-preview-button').addEventListener('click', () => run(async () => {
    invalidatePreview();
    const values = settings();
    const chosen = Object.fromEntries(['business', 'kind', 'tone', 'platform', 'signoff'].map(k => [k, values[k]]));
    const request = {csv: $('inbox-csv').value, settings: chosen};
    const result = await api('inbox-preview', request);
    previewRequest = request; preview = result;
    $('inbox-preview').hidden = false;
    $('inbox-preview-info').textContent = result.settings.business + ' · ' + result.settings.tone +
      ' · ' + result.settings.platform + ' · No owner commitments will be copied';
    $('inbox-preview-counts').textContent = describeCounts(result.counts);
    $('inbox-preview-rows').replaceChildren(...result.rows.map(row => rowElement(row)),
      ...result.warnings.map(w => node('p', w, 'helper')));
    notify('Preview ready. No inbox or replies have been saved.');
    buttons();
  }));
  $('inbox-confirm').addEventListener('change', buttons);
  $('inbox-create').addEventListener('click', () => {
    if (!discardHandling()) return;
    run(async () => {
    if (!previewRequest || !preview) throw new Error('Preview the CSV first.');
    const source = {csv: previewRequest.csv, label: $('inbox-label').value};
    const record = await api('inbox-create', {...previewRequest, preview_revision: preview.revision,
      confirmed: $('inbox-confirm').checked, label: source.label || 'Review inbox'});
    sourceTracker.accept(source);
    render(record); invalidatePreview(); await reload();
    notify('Inbox saved locally. Draft one review at a time, then approve each reply separately.');
    });
  });
  $('inbox-select').addEventListener('change', () => {
    if (!discardHandling()) { $('inbox-select').value = selected ? selected.id : ''; return; }
    if (!$('inbox-select').value) { handlingDirty.clear(); selected = null; $('inbox-saved').hidden = true; buttons(); return; }
    run(async () => render(await api('inbox-get', {id: $('inbox-select').value})));
  });
  $('inbox-next').addEventListener('click', () => {
    if (!selected || !confirmDiscard() || !discardHandling()) return;
    run(async () => {
      clearEditor();
      notify('Drafting one inbox review. Closing the tab does not cancel an in-flight model request.');
      const before = new Set(selected.rows.filter(x => x.draft_id).map(x => x.draft_id));
      const result = await api('inbox-step', {id: selected.id, revision: selected.revision, mode: $('inbox-mode').value});
      render(result); await refreshWorkspace();
      const newDraft = result.rows.find(x => x.draft_id && !before.has(x.draft_id));
      if (newDraft) {
        const view = await api('get', {id: newDraft.draft_id});
        fillForm(view); renderDraft(view, true);
        notify('One draft saved. Review and approve it individually. The remaining queue is saved.');
      } else notify('This row needs personal attention. Read its findings in the inbox.', true);
    });
  });
  window.rrwInbox = {buttons, invalidatePreview, hasUnsaved};
  buttons();
})();
