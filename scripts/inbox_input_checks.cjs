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
  const element = (tag = 'div', text = '') => ({tagName: tag, textContent: text, value: '', checked: false,
    disabled: false, hidden: false, open: false, children: [], events: {}, files: [],
    append(...children) {this.children.push(...children);}, replaceChildren(...children) {this.children = children;},
    addEventListener(type, handler) {this.events[type] = handler;}});
  const get = id => {if (!elements.has(id)) elements.set(id, element()); return elements.get(id);};
  get('inbox-label').value = 'Review inbox';
  const record = {id: 'inbox-fixture', revision: 'saved', label: 'Imported inbox', settings: {business: 'Demo Cafe', tone: 'professional', platform: 'generic'},
    counts: {pending: 0, manual: 1}, rows: [{id: 'manual-row', row: 2, review: 'A fictional sensitive review.', status: 'manual', findings: []}]};
  const context = {$: get, busy: false, dirty: false, qualityDirty: false, qualityNeedsCheck: false, InputTracker, TextDecoder,
    window: {addEventListener(type, handler) {windowEvents[type] = handler;},
      confirm() {confirmations++; return accept;}},
    Option: function(text, value) {return {...element('option', text), value};}, node: element,
    engineLabel: value => value, labels: {}, settings: () => record.settings,
    notify(message) {messages.push(message);}, confirmDiscard: () => true,
    api: async (action, data) => {
      requests.push({action, data});
      if (action === 'inbox-preview') return {...record, counts: {pending: 1, manual: 1}, warnings: []};
      if (action === 'inbox-create') {
        if (failCreate) throw new Error('Controlled failed save');
        if (changeDuringCreate) get('inbox-csv').value = 'Newer unsubmitted CSV';
        return record;
      }
      if (action === 'inbox-list') return {inboxes: [record]};
      if (action === 'inbox-get' || action === 'inbox-note') return record;
      throw new Error('Unexpected request ' + action);
    }};
  context.run = task => {
    const pending = (async () => {context.busy = true;
      try {await task();} catch (error) {messages.push(error.message);} finally {context.busy = false; context.window.rrwInbox.buttons();}})();
    tasks.push(pending); return pending;
  };
  vm.createContext(context); vm.runInContext(inbox, context);
  vm.runInContext(app.slice(app.indexOf("window.addEventListener('beforeunload'"), app.indexOf('// Quality experiments')), context);
  return {get, context, requests, messages, record, confirmations: () => confirmations,
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
  console.log(JSON.stringify({inbox_input_protection: 'passed', browser_navigation: false, model_calls: 0}));
}
main().catch(error => {console.error(error); process.exitCode = 1;});
