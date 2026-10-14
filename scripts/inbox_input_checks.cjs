'use strict';
// Real inbox module and unload handler in a controlled DOM, not a browser.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const {InputTracker} = require('../web/recovery.js');
const inbox = fs.readFileSync(path.join(__dirname, '../web/inbox.js'), 'utf8');
const app = fs.readFileSync(path.join(__dirname, '../web/app.js'), 'utf8');
function fixture() {
  const elements = new Map(), tasks = [], requests = [], messages = [], windowEvents = {};
  let accept = true, failCreate = false, changeDuringCreate = false, confirmations = 0;
  let failList = false, failGet = false, failState = false, failStep = false;
  const opened = [];
  const element = (tag = 'div', text = '') => ({tagName: tag, textContent: text, value: '', checked: false,
    disabled: false, hidden: false, open: false, children: [], events: {}, files: [],
    append(...children) {this.children.push(...children);}, replaceChildren(...children) {this.children = children;},
    addEventListener(type, handler) {this.events[type] = handler;}});
  const get = id => {if (!elements.has(id)) elements.set(id, element()); return elements.get(id);};
  get('inbox-label').value = 'Review inbox';
  const record = {id: 'inbox-fixture', revision: 'saved', label: 'Imported inbox', settings: {business: 'Demo Cafe', tone: 'professional', platform: 'generic'},
    counts: {pending: 0, manual: 1}, rows: [{id: 'manual-row', row: 2, review: 'A fictional sensitive review.', status: 'manual', findings: []}]};
  const draft = {id: 'reply-inbox-fixture.md', revision: 'checked-revision', status: 'pending',
    reply: 'CONTROLLED_UNAPPROVED_REPLY', review: 'Cold coffee.', findings: []};
  const stepped = {...record, revision: 'after-step', counts: {pending: 0, manual: 1, drafted: 1},
    rows: [...record.rows, {id: 'routine-row', row: 3, review: draft.review,
      status: 'drafted', draft_id: draft.id, draft_status: 'pending', findings: []}]};
  const context = {$: get, busy: false, dirty: false, qualityDirty: false, qualityNeedsCheck: false, InputTracker, TextDecoder,
    window: {addEventListener(type, handler) {windowEvents[type] = handler;},
      confirm() {confirmations++; return accept;}},
    Option: function(text, value) {return {...element('option', text), value};}, node: element,
    engineLabel: value => value, labels: {}, settings: () => record.settings,
    clearEditor() {context.current = null;}, fillForm(view) {get('review').value = view.review;},
    renderDraft(view) {opened.push(view); context.current = view; return true;},
    refreshWorkspace: async () => {await context.api('state');},
    notify(message) {messages.push(message);}, confirmDiscard: () => true,
    api: async (action, data) => {
      requests.push({action, data});
      if (action === 'inbox-preview') return {...record, counts: {pending: 1, manual: 1}, warnings: []};
      if (action === 'inbox-create') {
        if (failCreate) throw new Error('Controlled failed save');
        if (changeDuringCreate) get('inbox-csv').value = 'Newer unsubmitted CSV';
        return record;
      }
      if (action === 'inbox-list') {if (failList) throw Error('CONTROLLED_INBOX_LIST_FAILURE'); return {inboxes: [record]};}
      if (action === 'inbox-step') {if (failStep) throw Error('CONTROLLED_STEP_FAILURE'); return stepped;}
      if (action === 'get') {if (failGet) throw Error('CONTROLLED_DRAFT_READ_FAILURE'); return draft;}
      if (action === 'state') {if (failState) throw Error('CONTROLLED_LIBRARY_FAILURE'); return {drafts: [draft]};}
      if (action === 'inbox-get' || action === 'inbox-note') return record;
      throw new Error('Unexpected request ' + action);
    }};
  context.run = task => {
    const pending = (async () => {context.busy = true;
      try {await task();} catch (error) {messages.push(error.message);} finally {context.busy = false; context.window.rrwInbox.buttons();}})();
    tasks.push(pending); return pending;
  };
  vm.createContext(context);
  vm.runInContext(app.slice(app.indexOf('async function refreshAfterSaved('), app.indexOf('function renderDraft(')), context);
  vm.runInContext(inbox, context);
  vm.runInContext(app.slice(app.indexOf("window.addEventListener('beforeunload'"), app.indexOf('// Quality experiments')), context);
  return {get, context, requests, messages, record, draft, opened, confirmations: () => confirmations,
    ready() {record.counts.pending = 1; record.rows.push({id: 'routine-row', row: 3,
      review: draft.review, status: 'pending', findings: []});},
    blocked() {stepped.rows[1] = {id: 'routine-row', row: 3, review: draft.review,
      status: 'blocked', findings: ['CONTROLLED_CHECK_FINDING']};
      stepped.counts = {pending: 0, manual: 1, blocked: 1};},
    failList() {failList = true;}, failGet() {failGet = true;}, failState() {failState = true;}, failStep() {failStep = true;},
    accept(value) {accept = value;}, failCreate() {failCreate = true;}, changeDuringCreate() {changeDuringCreate = true;},
    hasUnsaved: () => context.window.rrwInbox.hasUnsaved(),
    unload() {let stopped = false; const event = {preventDefault() {stopped = true;}}; windowEvents.beforeunload(event); return stopped;},
    async invoke(handler) {handler({preventDefault() {}}); await Promise.all(tasks.splice(0));},
    async click(id, type = 'click') {await this.invoke(get(id).events[type]);},
    async choose(bytes, size = bytes.length, name = 'new.csv') {
      get('inbox-file').files = [{size, name, arrayBuffer: async () => Uint8Array.from(bytes).buffer}];
      await this.click('inbox-file', 'change');
    }};
}
async function main() {
  const initial = fixture(); assert.equal(initial.hasUnsaved(), false); assert.equal(initial.unload(), false);
  initial.get('inbox-csv').value = 'review\nPending private review';
  initial.get('inbox-label').value = 'Pending name';
  assert.equal(initial.hasUnsaved(), true); assert.equal(initial.unload(), true);
  const bytes = [...Buffer.from('review\nNew fictional review')];
  initial.accept(false); await initial.choose(bytes);
  assert.equal(initial.get('inbox-csv').value, 'review\nPending private review');
  assert.equal(initial.get('inbox-label').value, 'Pending name'); assert.equal(initial.requests.length, 0);
  initial.accept(true); await initial.choose([0xff]);
  assert.equal(initial.get('inbox-csv').value, 'review\nPending private review');
  assert.equal(initial.get('inbox-label').value, 'Pending name'); assert.match(initial.messages.at(-1), /kept/);
  await initial.choose(bytes, 48 * 1024 + 1);
  assert.equal(initial.get('inbox-csv').value, 'review\nPending private review');
  assert.equal(initial.get('inbox-label').value, 'Pending name');
  await initial.choose(bytes); assert.equal(initial.get('inbox-csv').value, Buffer.from(bytes).toString());
  assert.equal(initial.get('inbox-label').value, 'new.csv'); assert.equal(initial.get('inbox-confirm').checked, false);
  assert.equal(initial.hasUnsaved(), true); // A successful local read is not a saved import.
  await initial.click('inbox-preview-button'); assert.equal(initial.hasUnsaved(), true);
  initial.get('inbox-confirm').checked = true; await initial.click('inbox-create');
  assert.equal(initial.hasUnsaved(), false); assert.equal(initial.unload(), false);
  assert.equal(initial.requests.filter(x => x.action === 'inbox-create').length, 1);
  const savedConfirmations = initial.confirmations(); await initial.choose(bytes);
  assert.equal(initial.confirmations(), savedConfirmations); // Accepted saved source is not an unsaved replacement.

  const delayed = fixture(); let release;
  const data = new Promise(resolve => {release = resolve;});
  delayed.get('inbox-file').files = [{size: bytes.length, name: 'old.csv', arrayBuffer: () => data}];
  delayed.get('inbox-file').events.change();
  delayed.get('inbox-csv').value = 'Newer text while file read is pending'; release(Uint8Array.from(bytes).buffer);
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(delayed.get('inbox-csv').value, 'Newer text while file read is pending');
  assert.equal(delayed.get('inbox-label').value, 'Review inbox'); assert.match(delayed.messages.at(-1), /changed while reading/);

  const failed = fixture(); failed.get('inbox-csv').value = 'review\nUnsaved source';
  await failed.click('inbox-preview-button'); failed.get('inbox-confirm').checked = true;
  failed.failCreate(); await failed.click('inbox-create'); assert.equal(failed.hasUnsaved(), true);
  assert.equal(failed.get('inbox-csv').value, 'review\nUnsaved source');
  const changed = fixture(); changed.get('inbox-csv').value = 'review\nSubmitted source';
  await changed.click('inbox-preview-button'); changed.get('inbox-confirm').checked = true;
  changed.changeDuringCreate(); await changed.click('inbox-create');
  assert.equal(changed.hasUnsaved(), true); assert.equal(changed.get('inbox-csv').value, 'Newer unsubmitted CSV');

  const handling = fixture(); handling.get('inbox-select').value = handling.record.id;
  await handling.click('inbox-select', 'change');
  const card = handling.get('inbox-saved-rows').children[0];
  const details = card.children.find(child => child.tagName === 'details');
  const form = details.children.find(child => child.tagName === 'form');
  const field = form.children.find(child => child.tagName === 'textarea');
  field.value = 'Private unsaved handling note'; form.events.input();
  assert.equal(handling.hasUnsaved(), true); assert.equal(handling.unload(), true);
  await handling.invoke(form.events.submit); assert.equal(handling.hasUnsaved(), false);
  assert.equal(handling.requests.filter(x => x.action === 'inbox-note').length, 1);
  assert.equal(handling.requests.find(x => x.action === 'inbox-note').data.note, 'Private unsaved handling note');

  const saved = fixture(); saved.get('inbox-csv').value = 'review\nControlled source';
  await saved.click('inbox-preview-button'); saved.get('inbox-confirm').checked = true;
  saved.failList(); await saved.click('inbox-create');
  assert.match(saved.messages.at(-1), /^Inbox saved locally\./);
  assert.match(saved.messages.at(-1), /could not refresh/i);
  assert.equal(saved.get('inbox-saved-title').textContent, saved.record.label);
  assert.equal(saved.hasUnsaved(), false);
  assert.equal(saved.requests.filter(x => x.action === 'inbox-create').length, 1);

  const completed = fixture(); completed.ready(); completed.get('inbox-select').value = completed.record.id;
  await completed.click('inbox-select', 'change'); completed.failState();
  await completed.click('inbox-next');
  assert.equal(completed.opened[0], completed.draft);
  assert.match(completed.messages.at(-1), /^One draft saved\./);
  assert.match(completed.messages.at(-1), /could not refresh/i);
  assert.equal(completed.requests.filter(x => x.action === 'inbox-step').length, 1);
  assert.equal(completed.opened[0].status, 'pending');
  assert.equal(completed.get('inbox-next').disabled, true);

  const unavailable = fixture(); unavailable.ready(); unavailable.get('inbox-select').value = unavailable.record.id;
  await unavailable.click('inbox-select', 'change'); unavailable.failGet();
  await unavailable.click('inbox-next');
  assert.equal(unavailable.opened.length, 0);
  assert.match(unavailable.messages.at(-1), /^One draft was saved in the inbox/);
  assert.match(unavailable.messages.at(-1), /Review draft/);
  assert.equal(unavailable.get('inbox-saved-rows').children.length, 2);
  const row = unavailable.get('inbox-saved-rows').children[1];
  const actions = row.children.find(x => x.tagName === 'div');
  assert.equal(actions.children.find(x => x.textContent === 'Review draft').disabled, false);
  assert.equal(unavailable.requests.filter(x => x.action === 'inbox-step').length, 1);

  const interrupted = fixture(); interrupted.ready(); interrupted.get('inbox-select').value = interrupted.record.id;
  await interrupted.click('inbox-select', 'change'); interrupted.failStep();
  await interrupted.click('inbox-next');
  assert.equal(interrupted.opened.length, 0);
  assert.equal(interrupted.messages.at(-1), 'CONTROLLED_STEP_FAILURE');
  assert.equal(interrupted.get('inbox-saved-rows').children.length, 2);
  assert.equal(interrupted.requests.filter(x => x.action === 'get').length, 0);
  assert.equal(interrupted.requests.filter(x => x.action === 'inbox-step').length, 1);
  const attention = fixture(); attention.ready(); attention.blocked();
  attention.get('inbox-select').value = attention.record.id;
  await attention.click('inbox-select', 'change'); attention.failState();
  await attention.click('inbox-next');
  assert.equal(attention.opened.length, 0);
  assert.match(attention.messages.at(-1), /^Inbox progress saved\./);
  assert.match(attention.messages.at(-1), /personal attention.*could not refresh/i);
  assert.equal(attention.requests.filter(x => x.action === 'get').length, 0);
  assert.equal(attention.requests.filter(x => x.action === 'inbox-step').length, 1);
  for (const item of [saved, completed, unavailable, interrupted, attention])
    assert.ok(item.requests.every(x => !['decision', 'approved-text'].includes(x.action)));
  console.log(JSON.stringify({inbox_input_protection: 'passed', browser_navigation: false, model_calls: 0}));
}
main().catch(error => {console.error(error); process.exitCode = 1;});
