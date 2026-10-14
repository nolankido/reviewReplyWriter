'use strict';
// Execute real controller/core handlers in a controlled DOM, not a browser.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const app = fs.readFileSync(path.join(__dirname, '../web/app.js'), 'utf8');
const controller = fs.readFileSync(path.join(__dirname, '../web/save-recovery.js'), 'utf8');

function fixture() {
  const elements = new Map();
  const get = id => {
    if (!elements.has(id)) elements.set(id, {value: '', textContent: '', disabled: false, checked: false, hidden: false,
      className: '', dataset: {}, events: {}, classList: {toggle() {}, add() {}, remove() {}},
      addEventListener(name, handler) {this.events[name] = handler;},
      dispatchEvent(event) {return this.events[event.type]?.(event);}, focus() {}, setAttribute() {}, replaceChildren() {}, append() {}});
    return elements.get(id);
  };
  const view = {id: 'reply-fixture.md', revision: 'original', reply: 'Saved starting text.', status: 'pending',
    business: 'Demo Cafe', review: 'Fictional review.', approved_actions: [], findings: [], word_count: 3, word_target: [0, 90]};
  const messages = [], calls = [];
  let latest = {...view}, uncertain = false, refreshFails = false, readFails = false, confirm = true, refreshed = 0;
  const context = {window: {confirm: () => confirm}, current: {...view}, dirty: false, busy: false, $: get,
    Event: class {constructor(type) {this.type = type;}}, labels: {pending: 'Needs review', approved: 'Approved', aside: 'Set aside'},
    document: {querySelector: () => get('shell'), querySelectorAll: () => []},
    notify: (text, error) => messages.push({text, error}),
    typeChanged() {}, qualityButtons() {}, showView() {}, renderQueue() {}, renderReviewEvidence() {}, node() {return {};},
    engineLabel: value => value || 'Imported',
    api: async (action, data) => {
      calls.push({action, data});
      if (action === 'get') {
        if (readFails) throw new Error('Controlled failed saved-version read');
        return {...latest};
      }
      latest = {...latest, revision: action === 'edit' ? 'new-revision' : latest.revision,
        reply: action === 'edit' ? data.reply : latest.reply, status: action === 'decision' ? data.status : 'pending'};
      if (uncertain) {const error = new Error('Controlled lost response'); error.uncertain = true; throw error;}
      return {...latest};
    },
    refreshWorkspace: async () => {refreshed++; if (refreshFails) throw new Error('Controlled failed library read');},
    confirmDiscard: () => true};
  vm.createContext(context);
  const section = (start, end) => app.slice(app.indexOf(start), app.indexOf(end));
  vm.runInContext(section('function setBusy(', 'function confirmDiscard('), context);
  vm.runInContext(section('function renderDraft(', "$('compose-form').addEventListener"), context);
  vm.runInContext(section("$('reply-editor').addEventListener('input'", "$('copy').addEventListener"), context);
  vm.runInContext(controller, context);
  context.renderDraft({...view});
  return {context, get, calls, messages,
    latest: () => latest, setLatest: value => {latest = {...value};},
    loseResponse: () => {uncertain = true;}, allowResponse: () => {uncertain = false;},
    failRefresh: () => {refreshFails = true;}, refreshed: () => refreshed,
    failRead: () => {readFails = true;},
    confirm: value => {confirm = value;},
    edit: text => {get('reply-editor').value = text; get('reply-editor').dispatchEvent({type: 'input'});},
    click: async id => {get(id).events.click(); await new Promise(resolve => setImmediate(resolve));}};
}

async function main() {
  const successful = fixture();
  successful.failRefresh(); successful.edit('Known saved edit.');
  await successful.click('save-edit');
  assert.equal(successful.context.current.revision, 'new-revision');
  assert.equal(successful.get('reply-editor').value, 'Known saved edit.');
  assert.equal(successful.context.dirty, false);
  assert.match(successful.messages.at(-1).text, /Edits saved.*library could not refresh/);
  assert.equal(successful.calls.filter(x => x.action === 'edit').length, 1);
  successful.get('human-reviewed').checked = true;
  await successful.click('approve');
  assert.equal(successful.context.current.status, 'approved');
  assert.equal(successful.get('copy').disabled, false);
  assert.match(successful.messages.at(-1).text, /Approved.*library could not refresh/);

  const lost = fixture();
  lost.edit('My pending edit.'); lost.loseResponse();
  await lost.click('save-edit');
  assert.equal(lost.context.current.revision, 'original');
  assert.equal(lost.get('reply-editor').value, 'My pending edit.');
  assert.equal(lost.get('save-edit').disabled, true);
  assert.equal(lost.get('approve').disabled, true);
  assert.equal(lost.get('copy').disabled, true);
  await assert.rejects(lost.context.window.rrwSaveRecovery.submit('edit', {}), /Check the uncertain/);
  await lost.click('save-recovery-check');
  assert.equal(lost.context.current.revision, 'original'); // Read-only check.
  assert.equal(lost.get('save-recovery-reply').value, 'My pending edit.');
  lost.edit('Further unsaved text.');
  const newer = {...lost.latest(), revision: 'elsewhere', reply: 'A concurrent saved reply.'};
  lost.setLatest(newer);
  await lost.click('save-recovery-keep');
  assert.equal(lost.context.current.revision, 'original');
  assert.equal(lost.get('reply-editor').value, 'Further unsaved text.');
  assert.match(lost.get('save-recovery-message').textContent, /changed again/);
  await lost.click('save-recovery-check');
  await lost.click('save-recovery-keep');
  assert.equal(lost.context.current.revision, 'elsewhere');
  assert.equal(lost.get('reply-editor').value, 'Further unsaved text.');
  assert.equal(lost.context.dirty, true);
  assert.equal(lost.get('human-reviewed').checked, false);
  assert.equal(lost.get('policy-confirmed').checked, false);
  assert.equal(lost.get('copy').disabled, true);
  assert.equal(lost.calls.filter(x => x.action !== 'get').length, 1); // Reconciliation never writes.
  lost.allowResponse(); await lost.click('save-edit');
  assert.equal(lost.calls.at(-1).data.revision, 'elsewhere');

  const approval = fixture();
  approval.get('human-reviewed').checked = true; approval.loseResponse();
  await approval.click('approve'); await approval.click('save-recovery-check');
  // A status-only change must be noticed even though the content hash is the same.
  approval.setLatest({...approval.latest(), status: 'aside'});
  await approval.click('save-recovery-load');
  assert.equal(approval.context.current.status, 'pending');
  assert.match(approval.get('save-recovery-message').textContent, /changed again/);
  approval.setLatest({...approval.latest(), status: 'approved'});
  await approval.click('save-recovery-check'); await approval.click('save-recovery-load');
  assert.equal(approval.context.current.status, 'approved');
  assert.equal(approval.get('human-reviewed').checked, false);
  assert.equal(approval.get('copy').disabled, true); // No recovered approval checkbox/copy grant.
  assert.equal(approval.get('download').disabled, true);
  approval.get('human-reviewed').checked = true; approval.context.updateButtons();
  assert.equal(approval.get('approve').disabled, false);
  approval.allowResponse(); await approval.click('approve');
  assert.equal(approval.get('copy').disabled, false);

  const load = fixture(); load.edit('Keep this private editor text.');
  await load.click('save-recovery-check'); load.confirm(false);
  await load.click('save-recovery-load');
  assert.equal(load.get('reply-editor').value, 'Keep this private editor text.');
  load.setLatest({...load.latest(), findings: ['manual review required']});
  await load.click('save-recovery-check'); await load.click('save-recovery-keep');
  assert.equal(load.get('reply-editor').value, 'Keep this private editor text.');
  assert.match(load.get('save-recovery-message').textContent, /personal handling/);
  const manual = fixture();
  manual.setLatest({...manual.latest(), revision: 'external', status: 'approved'});
  await manual.click('save-recovery-check');
  assert.equal(manual.context.window.rrwSaveRecovery.unresolved(), true);
  assert.equal(manual.get('approve').disabled, true);
  assert.equal(manual.get('copy').disabled, true);
  assert.equal(manual.context.current.revision, 'original');
  assert.equal(manual.get('reply-editor').value, 'Saved starting text.');
  manual.failRead(); await manual.click('save-recovery-check');
  assert.equal(manual.get('save-recovery-keep').disabled, true);
  assert.equal(manual.get('save-recovery-load').disabled, true);
  assert.equal(manual.get('reply-editor').value, 'Saved starting text.');
  console.log(JSON.stringify({save_recovery_and_authority_checks: 'passed', browser_navigation: false, model_calls: 0}));
}
main().catch(error => {console.error(error); process.exitCode = 1;});
