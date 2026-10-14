'use strict';
// Real application handlers with controlled DOM/API/clipboard, not browser navigation.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const {FocusHandoff} = require('../web/focus.js');
const app = fs.readFileSync(path.join(__dirname, '../web/app.js'), 'utf8');

function fixture() {
  const elements = new Map(), controls = [], writes = [], calls = [], messages = [];
  let focus = '', denied = true, failed = false, afterRead = null, beforeReject = null, attention = false;
  const get = id => {
    if (!elements.has(id)) {
      const textarea = ['reply-editor', 'manual-copy-text'].includes(id);
      const element = {id, tagName: textarea ? 'TEXTAREA' : 'DIV', value: '', disabled: false,
        readOnly: id === 'manual-copy-text', checked: true, hidden: false, dataset: {}, events: {},
        isConnected: true, textContent: '', className: '', classList: {toggle(){}, add(){}, remove(){}},
        addEventListener(type, handler) {this.events[type] = handler;},
        dispatchEvent(event) {this.events[event.type]?.(event);},
        setAttribute(){}, replaceChildren(){}, append(){},
        closest(selector) {return selector === '[hidden]' && (this.hidden ||
          id === 'manual-copy-text' && get('manual-copy-panel').hidden) ? {} : null;},
        getClientRects: () => [{}],
        focus() {assert.equal(this.disabled, false); focus = id;}, scrollIntoView(){},
        select() {throw Error('Live editor selection must never be used by copy fallback');}};
      if (textarea) controls.push(element);
      elements.set(id, element);
    }
    return elements.get(id);
  };
  const view = {id: 'reply-controlled.md', revision: 'checked-revision', reply: 'CONTROLLED_APPROVED_REPLY',
    status: 'approved', findings: [], business: 'Demo Cafe', review: 'Fictional review.',
    word_count: 1, word_target: [0, 120], engine: 'template', generation_trace: []};
  const context = {window: {}, current: {...view}, dirty: false, busy: false, $: get,
    document: {querySelector: () => get('shell'), querySelectorAll: selector => selector === 'button, input, select, textarea' ? controls : []},
    navigator: {clipboard: {writeText: async text => {
      if (denied) {if (beforeReject) beforeReject(); throw Error('Controlled clipboard denial');}
      writes.push(text);
    }}},
    requestAnimationFrame() {throw Error('Delayed selection must never be scheduled');},
    api: async (action, data) => {
      calls.push({action, data});
      if (failed) {const error = new Error('Controlled stale approval'); error.status = 409; throw error;}
      if (afterRead) afterRead();
      return {text: view.reply};
    },
    notify(text, error) {messages.push({text, error}); get('notice').hidden = false;},
    typeChanged(){}, updateButtons(){}, qualityButtons(){}, showView(){}, renderQueue(){}, renderReviewEvidence(){},
    resetReviewEvidence(){}, renderGenerationStatus(){}, engineLabel: value => value, node(){return {};},
    labels: {approved: 'Approved', pending: 'Needs review'},
    idRevision: () => ({id: context.current.id, revision: context.current.revision})};
  context.window.rrwSaveRecovery = {needsAttention: () => attention, selected(){}, buttons(){}};
  context.window.rrwFocus = new FocusHandoff(get, () => context.busy);
  get('reply-editor').value = view.reply; get('manual-copy-text'); get('manual-copy-panel').hidden = true;
  vm.createContext(context);
  const section = (start, end) => app.slice(app.indexOf(start), app.indexOf(end));
  vm.runInContext(section('function setBusy(', 'function updateProgress('), context);
  vm.runInContext(section('function clearEditor(', 'function showManualReview('), context);
  vm.runInContext(section('function renderDraft(', 'function idRevision('), context);
  vm.runInContext(section("$('reply-editor').addEventListener('input'", "$('save-edit').addEventListener"), context);
  vm.runInContext(section('function approvedCopyMatches(', "$('download').addEventListener"), context);
  const edit = text => {get('reply-editor').value = text; get('reply-editor').dispatchEvent({type: 'input'});};
  return {context, get, calls, writes, messages, view, edit, focus: () => focus,
    click: async () => {get('copy').events.click(); await new Promise(resolve => setImmediate(resolve));},
    allow: () => {denied = false;}, fail: () => {failed = true;},
    afterRead: callback => {afterRead = callback;}, beforeReject: callback => {beforeReject = callback;},
    attention: () => {attention = true;}};
}

async function main() {
  const blocked = fixture(); await blocked.click();
  assert.equal(blocked.get('manual-copy-panel').hidden, false);
  assert.equal(blocked.get('manual-copy-text').value, blocked.view.reply);
  assert.equal(blocked.get('manual-copy-text').readOnly, true);
  assert.equal(blocked.get('reply-editor').value, blocked.view.reply);
  assert.equal(blocked.focus(), 'manual-copy-text');
  assert.equal(blocked.context.busy, false); assert.equal(blocked.writes.length, 0);
  assert.match(blocked.messages.at(-1).text, /read-only approved reply/);
  blocked.edit('CONTROLLED_UNSAVED_TEXT');
  assert.equal(blocked.get('manual-copy-panel').hidden, true);
  assert.equal(blocked.get('manual-copy-text').value, '');
  assert.equal(blocked.get('human-reviewed').checked, false);
  assert.equal(blocked.calls.length, 1); // No write, approval or copy retry.

  const successful = fixture(); successful.allow(); await successful.click();
  assert.deepEqual(successful.writes, [successful.view.reply]);
  assert.equal(successful.get('manual-copy-panel').hidden, true);
  assert.equal(successful.get('manual-copy-text').value, '');

  const missing = fixture(); missing.context.navigator = {}; await missing.click();
  assert.equal(missing.get('manual-copy-text').value, missing.view.reply);

  const stale = fixture(); await stale.click(); stale.fail(); await stale.click();
  assert.equal(stale.get('manual-copy-panel').hidden, true);
  assert.equal(stale.get('manual-copy-text').value, '');
  assert.equal(stale.writes.length, 0); assert.match(stale.messages.at(-1).text, /stale approval/);

  const changed = fixture(); changed.allow(); changed.afterRead(() => changed.edit('Further owner edits'));
  await changed.click(); assert.equal(changed.writes.length, 0);
  assert.equal(changed.get('manual-copy-panel').hidden, true);
  assert.match(changed.messages.at(-1).text, /selected reply changed/);

  const delayed = fixture(); delayed.beforeReject(() => delayed.edit('Edited during clipboard rejection'));
  await delayed.click(); assert.equal(delayed.get('manual-copy-panel').hidden, true);
  assert.equal(delayed.get('manual-copy-text').value, '');

  const switched = fixture(); switched.afterRead(() => switched.context.renderDraft({...switched.view, id: 'reply-other.md'}));
  await switched.click(); assert.equal(switched.get('manual-copy-panel').hidden, true);
  assert.equal(switched.writes.length, 0);

  const reset = fixture(); await reset.click(); reset.context.renderDraft({...reset.view});
  assert.equal(reset.get('manual-copy-text').value, '');
  await reset.click(); reset.context.clearEditor();
  assert.equal(reset.get('manual-copy-panel').hidden, true);
  assert.equal(reset.get('manual-copy-text').value, '');

  const unresolved = fixture(); unresolved.attention(); await unresolved.click();
  assert.equal(unresolved.get('manual-copy-panel').hidden, true);
  assert.equal(unresolved.writes.length, 0);
  for (const item of [blocked, successful, missing, stale, changed, delayed, switched, reset, unresolved])
    assert.ok(item.calls.every(call => call.action === 'approved-text'));
  console.log(JSON.stringify({approved_copy_fallback_checks: 'passed', browser_navigation: false, model_calls: 0}));
}
main().catch(error => {console.error(error); process.exitCode = 1;});
