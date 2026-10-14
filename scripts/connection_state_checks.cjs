'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const {webcrypto} = require('node:crypto');
const connection = require('../web/connection.js');

async function main() {
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
  console.log(JSON.stringify({connection_and_result_state: 'passed', browser_navigation: false, model_calls: 0}));
}
main().catch(error => {console.error(error); process.exitCode = 1;});
