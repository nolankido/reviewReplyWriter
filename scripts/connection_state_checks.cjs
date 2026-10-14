'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const {webcrypto} = require('node:crypto');
const connection = require('../web/connection.js');
const app = fs.readFileSync(path.join(__dirname, '../web/app.js'), 'utf8');

// Execute actual generation handlers with controlled DOM and transport. These
// are acknowledged writes followed by a failed library read, not browser tests.
async function acknowledgedGenerationChecks() {
  function fixture() {
    const elements = new Map(), calls = [], notices = [];
    let failWrite = false, failRead = true, failGet = false, accepted = 0, opened = 0;
    const get = id => {
      if (!elements.has(id)) elements.set(id, {value: '', checked: false, disabled: false,
        hidden: false, dataset: {}, textContent: '', events: {},
        classList: {toggle(){}}, setAttribute(){},
        addEventListener(type, handler) {this.events[type] = handler;}});
      return elements.get(id);
    };
    const view = {id: 'reply-acknowledged.md', revision: 'new-revision', status: 'pending',
      reply: 'CONTROLLED_SAVED_REPLY', findings: [], engine: 'template engine (offline)'};
    const original = {id: 'reply-original.md', revision: 'old-revision', status: 'pending',
      reply: 'CONTROLLED_ORIGINAL_REPLY', findings: []};
    const context = {window: {confirm: () => true}, busy: false, current: original, dirty: false,
      workspace: {drafts: []}, $: get, crypto: webcrypto, Uint8Array,
      document: {querySelector: () => get('shell'), querySelectorAll: () => []},
      sessionStorage: {getItem: () => '', setItem(){}, removeItem(){}},
      notify(text, error) {notices.push({text, error});},
      settings: () => ({business: 'Demo Cafe'}), confirmDiscard: () => true,
      typeChanged(){}, updateButtons(){}, qualityButtons(){}, renderProfiles(){}, renderQueue(){},
      fillForm() {opened++;}, renderDraft(value) {context.current = value; context.dirty = false;},
      reviewContext: () => 'Controlled review', showManualReview(){},
      idRevision: () => ({id: context.current.id, revision: context.current.revision}),
      api: async (action, data) => {
        calls.push({action, data});
        if (action === 'state') {
          if (failRead) throw Error('CONTROLLED_LIBRARY_READ_FAILURE');
          return {drafts: [view]};
        }
        if (action === 'generation-check') return {state: 'saved', draft_id: view.id,
          draft_state: 'current', revision: view.revision};
        if (action === 'get') {if (failGet) throw Error('CONTROLLED_GET_FAILURE'); return view;}
        if (failWrite) {const error = Error('CONTROLLED_GENERATION_DISCONNECT'); error.uncertain = true; throw error;}
        return view;
      }};
    context.window.rrwRecovery = {accept() {accepted++;}, buttons(){}};
    get('review').value = 'Controlled pending review'; get('engine-mode').value = 'offline';
    vm.createContext(context);
    const section = (start, end) => app.slice(app.indexOf(start), app.indexOf(end));
    vm.runInContext(section('function setBusy(', 'function updateProgress('), context);
    vm.runInContext(section('async function refreshWorkspace(', 'function renderDraft('), context);
    vm.runInContext(fs.readFileSync(path.join(__dirname, '../web/generation.js'), 'utf8'), context);
    vm.runInContext(section("$('compose-form').addEventListener", "$('manual-back').addEventListener"), context);
    vm.runInContext(section("$('reroll').addEventListener", 'function approvedCopyMatches('), context);
    const tick = () => new Promise(resolve => setImmediate(resolve));
    return {context, calls, notices, view, get, accepted: () => accepted, opened: () => opened,
      original, tick, failWrite: value => {failWrite = value;},
      failRead: value => {failRead = value;}, failGet: value => {failGet = value;},
      submit: async () => {get('compose-form').events.submit({preventDefault(){}}); await tick();},
      reroll: async () => {get('reroll').events.click(); await tick();}};
  }
  const generated = fixture(); await generated.submit();
  assert.equal(generated.context.current, generated.view);
  assert.equal(generated.accepted(), 1);
  assert.equal(generated.context.window.rrwGeneration.hasPending(), false);
  assert.match(generated.notices.at(-1).text, /^Draft saved\./);
  assert.match(generated.notices.at(-1).text, /library could not refresh/i);
  assert.equal(generated.context.busy, false);
  assert.deepEqual(generated.calls.map(c => c.action), ['generate', 'state']);
  assert.equal(generated.get('review').value, 'Controlled pending review');

  const fallback = fixture(); fallback.view.engine = 'template fallback'; await fallback.submit();
  assert.match(fallback.notices.at(-1).text, /^A checked template was saved instead of AI output\./);
  assert.match(fallback.notices.at(-1).text, /library could not refresh/i);
  assert.equal(fallback.calls.filter(c => c.action === 'generate').length, 1);

  const rerolled = fixture(); await rerolled.reroll();
  assert.equal(rerolled.context.current, rerolled.view);
  assert.match(rerolled.notices.at(-1).text, /^New draft saved\./);
  assert.equal(rerolled.accepted(), 0);
  assert.deepEqual(rerolled.calls.map(c => c.action), ['reroll', 'state']);

  const lost = fixture(); lost.failWrite(true); await lost.submit();
  assert.equal(lost.context.current, lost.original);
  assert.equal(lost.accepted(), 0);
  assert.equal(lost.context.window.rrwGeneration.hasPending(), true);
  assert.equal(lost.calls.length, 1); // No automatic retry or invented success.
  assert.match(lost.notices.at(-1).text, /GENERATION_DISCONNECT/);
  lost.failWrite(false);
  lost.get('generation-check').events.click(); await lost.tick();
  assert.equal(lost.opened(), 0); // Read-only result check does not replace inputs.
  lost.get('generation-open').events.click(); await lost.tick();
  assert.equal(lost.opened(), 1); assert.equal(lost.context.current, lost.view);
  assert.equal(lost.context.window.rrwGeneration.hasPending(), false);
  assert.match(lost.notices.at(-1).text, /^Saved generation opened\./);
  assert.match(lost.notices.at(-1).text, /library could not refresh/i);
  assert.deepEqual(lost.calls.map(c => c.action), ['generate', 'generation-check', 'get', 'state']);

  const changed = fixture(); changed.failWrite(true); await changed.submit();
  changed.get('generation-check').events.click(); await changed.tick();
  changed.view.revision = 'later-revision';
  changed.get('generation-open').events.click(); await changed.tick();
  assert.match(changed.notices.at(-1).text, /^The saved draft changed\./);
  assert.match(changed.notices.at(-1).text, /library could not refresh/i);
  assert.equal(changed.context.current.revision, 'later-revision');
  assert.equal(changed.context.window.rrwGeneration.hasPending(), false);

  const unavailable = fixture(); unavailable.failWrite(true); await unavailable.submit();
  unavailable.get('generation-check').events.click(); await unavailable.tick();
  unavailable.failGet(true);
  unavailable.get('generation-open').events.click(); await unavailable.tick();
  assert.equal(unavailable.context.current, unavailable.original);
  assert.equal(unavailable.context.window.rrwGeneration.hasPending(), true);
  assert.equal(unavailable.opened(), 0);
  assert.match(unavailable.notices.at(-1).text, /GET_FAILURE/);

  const healthy = fixture(); healthy.failRead(false); await healthy.submit();
  assert.match(healthy.notices.at(-1).text, /^Draft saved\./);
  assert.equal(Boolean(healthy.notices.at(-1).error), false);
  assert.equal(healthy.context.workspace.drafts[0], healthy.view);
}

async function main() {
  await acknowledgedGenerationChecks();
  const blocked = {getItem() {throw new Error('Blocked');}, setItem() {throw new Error('Blocked');}};
  assert.deepEqual(connection.session(blocked, 'fixture-session'), {token: 'fixture-session', available: false});
  assert.deepEqual(connection.session(blocked, ''), {token: '', available: false});
  const response = value => ({ok: true, json: async () => value});
  let calls = 0, signal;
  await assert.rejects(connection.request('generate', {review: 'fixture'}, 'fixture-session', async (url, options) => {
    calls++; signal = options.signal;
    return new Promise(() => {}); // Transport deliberately ignores cancellation.
  }, 5), error => error.uncertain === true && error.message.includes('deadline'));
  assert.equal(calls, 1); assert.equal(signal.aborted, true);
  await assert.rejects(connection.request('edit', {}, 'fixture-session', async () => {throw new TypeError('Network');}),
    error => error.uncertain === true);
  await assert.rejects(connection.request('state', undefined, 'fixture-session', async () => ({ok: true, json: async () => {throw new Error('Not JSON');}})),
    error => error.uncertain === true);
  await assert.rejects(connection.request('generate', {}, 'fixture-session', async () => ({ok: false, status: 422,
    json: async () => ({error: 'Controlled manual referral', findings: ['manual review required']})})),
    error => error.status === 422 && error.findings[0] === 'manual review required');
  let resolveLate;
  const late = connection.request('generate', {}, 'fixture-session', () => new Promise(resolve => {resolveLate = resolve;}), 5);
  await assert.rejects(late, error => error.uncertain);
  resolveLate(response({id: 'late-result'}));
  assert.deepEqual(await connection.request('state', undefined, 'fixture-session', async (url, options) => {
    assert.equal(options.credentials, 'omit'); assert.equal(options.cache, 'no-store');
    return response({drafts: []});
  }), {drafts: []});

  // Execute the actual startup prefix with the browser storage getter blocked.
  const prefix = fs.readFileSync(path.join(__dirname, '../web/app.js'), 'utf8').split('let workspace =')[0];
  let removed = false;
  const note = {hidden: true, textContent: ''};
  const startup = {document: {getElementById: () => note}, URLSearchParams,
    location: {hash: '#token=fixture-session', pathname: '/'},
    history: {replaceState() {removed = true;}}, window: {rrwConnection: connection}};
  Object.defineProperty(startup, 'sessionStorage', {get() {throw new Error('Blocked storage getter');}});
  vm.runInNewContext(prefix, startup);
  assert.equal(removed, true); assert.equal(note.hidden, false);
  assert.equal(vm.runInNewContext('token', startup), 'fixture-session');

  // Execute the actual result controller, without claiming browser rendering.
  const elements = new Map();
  const get = id => {
    if (!elements.has(id)) elements.set(id, {disabled: false, hidden: true, textContent: '',
      events: {}, addEventListener(name, handler) {this.events[name] = handler;}});
    return elements.get(id);
  };
  let stored = '', canDiscard = false, opened = 0, confirmed = false, submittedId = '', lastRun;
  let status = {state: 'saved', draft_id: 'reply-fixture.md', draft_state: 'current'};
  const context = {window: {}, busy: false, $: get, crypto: webcrypto, Uint8Array,
    sessionStorage: {getItem: () => stored, setItem(key, value) {stored = value;}, removeItem() {stored = '';}},
    updateButtons() {}, confirmDiscard: () => canDiscard, notify() {},
    fillForm() {opened++;}, renderDraft() {}, refreshWorkspace: async () => {}, run: task => {lastRun = task(); return lastRun;},
    api: async (action, data) => {
      if (action === 'generation-check') return status;
      if (action === 'get') return {id: data.id};
      submittedId = data.request_id;
      const error = new Error('Controlled lost response'); error.uncertain = true; throw error;
    }};
  context.window.confirm = () => confirmed;
  vm.runInNewContext(app.slice(app.indexOf('async function refreshAfterSaved('), app.indexOf('function renderDraft(')), context);
  vm.runInNewContext(fs.readFileSync(path.join(__dirname, '../web/generation.js'), 'utf8'), context);
  await assert.rejects(context.window.rrwGeneration.submit('generate', {review: 'fixture'}));
  assert.match(stored, /^[0-9a-f]{32}$/); assert.equal(stored, submittedId);
  assert.equal(context.window.rrwGeneration.hasPending(), true);
  assert.equal(get('generate').disabled, true);
  await assert.rejects(context.window.rrwGeneration.submit('generate', {}), /previous generation/);
  await get('generation-check').events.click();
  assert.equal(opened, 0); // Checking never replaces the form.
  assert.equal(get('generation-open').disabled, false);
  get('generation-open').events.click(); assert.equal(opened, 0); // Cancelled replacement guard.
  status = {...status, draft_state: 'changed'};
  await get('generation-check').events.click();
  assert.match(get('generation-message').textContent, /later changed/);
  canDiscard = true;
  get('generation-open').events.click(); await lastRun;
  assert.equal(opened, 1); assert.equal(stored, '');
  assert.equal(context.window.rrwGeneration.hasPending(), false);
  context.sessionStorage.setItem = () => {throw new Error('Controlled storage quota');};
  await assert.rejects(context.window.rrwGeneration.submit('generate', {}));
  assert.equal(context.window.rrwGeneration.hasPending(), true);
  assert.equal(get('session-storage-note').hidden, false);
  assert.match(get('session-storage-note').textContent, /could not keep this result check/);
  get('generation-dismiss').events.click();
  assert.equal(context.window.rrwGeneration.hasPending(), true); // Cancelling keeps the memory-only check.
  confirmed = true; get('generation-dismiss').events.click();
  assert.equal(context.window.rrwGeneration.hasPending(), false);
  console.log(JSON.stringify({connection_and_result_state: 'passed', browser_navigation: false, model_calls: 0}));
}
main().catch(error => {console.error(error); process.exitCode = 1;});
