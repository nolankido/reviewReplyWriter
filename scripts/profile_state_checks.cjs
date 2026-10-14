'use strict';
// Execute the real profile controller and core reads with controlled private data.
const assert = require('node:assert/strict');
const fs = require('node:fs'), path = require('node:path'), vm = require('node:vm');
const {InputTracker} = require('../web/recovery.js');
const app = fs.readFileSync(path.join(__dirname, '../web/app.js'), 'utf8');
const controller = fs.readFileSync(path.join(__dirname, '../web/profiles.js'), 'utf8');

function fixture() {
  const elements = new Map(), calls = [], messages = [], events = {};
  const get = id => {
    if (!elements.has(id)) elements.set(id, {value: '', checked: false, disabled: false, hidden: false,
      textContent: '', dataset: {}, handlers: {}, children: [], classList: {toggle(){}},
      addEventListener(type, fn) {this.handlers[type] = fn;},
      replaceChildren(...children) {this.children = children;}, append(value) {this.children.push(value);}, setAttribute(){}});
    return elements.get(id);
  };
  for (const [id, value] of Object.entries({business: 'Demo Cafe', kind: 'cafe', tone: 'professional',
    platform: 'google', offer: 'a replacement coffee', signoff: '', 'approved-actions': '',
    'profile-name': 'demo', 'profile-select': '', review: 'CONTROLLED_PENDING_REVIEW'})) get(id).value = value;
  get('policy-confirmed').checked = true;
  let lost = false, failedRead = false, rejected = false, invalid = false, afterSave = null, loaded = 0;
  let stored = {}, revision = 'new';
  const context = {window: {addEventListener(type, fn){events[type] = fn;}}, busy: false, $: get,
    workspace: {profiles: {}, profiles_revision: 'new', drafts: []},
    document: {querySelector: () => get('shell'), querySelectorAll: () => []},
    Option: class {constructor(label, value){this.label = label; this.value = value;}},
    notify: text => messages.push(text), renderQueue(){}, typeChanged(){}, updateButtons(){}, qualityButtons(){},
    api: async (action, data) => {
      calls.push({action, data});
      if (action === 'state') {
        if (failedRead) throw Error('Controlled read failure');
        return {profiles: JSON.parse(JSON.stringify(stored)), profiles_revision: revision, drafts: []};
      }
      assert.equal(action, 'profile');
      if (rejected) {const error = Error('Controlled validation rejection'); error.status = 400; throw error;}
      assert.equal(data.profiles_revision, revision);
      stored[data.name] = {business: data.business.trim(), kind: data.kind, tone: data.tone, platform: data.platform,
        offer: data.offer.trim(), signoff: data.signoff.trim(), approved_actions: data.approved_actions,
        voice: {opener: 'CONTROLLED_EXISTING_VOICE'}};
      revision = 'a'.repeat(64);
      if (afterSave) afterSave();
      if (lost) {const error = Error('Controlled lost response'); error.uncertain = true; throw error;}
      return invalid ? {name: data.name} : {name: data.name, profile: {...stored[data.name]}, profiles_revision: revision};
    }};
  vm.createContext(context);
  const section = (start, end) => app.slice(app.indexOf(start), app.indexOf(end));
  vm.runInContext(section('function setBusy(', 'function updateProgress('), context);
  vm.runInContext(section('function settings(', 'function fillSettings('), context);
  vm.runInContext(section('function renderProfiles(', 'function renderDraft('), context);
  const tracker = new InputTracker({...context.settings(), review: ''});
  context.window.rrwRecovery = {profileLoaded(){loaded++; tracker.accept(context.settings(),
    ['business', 'kind', 'tone', 'platform', 'offer', 'signoff', 'approved_actions']);}, buttons(){}};
  vm.runInContext(controller, context);
  return {context, get, calls, messages, tracker,
    click: async id => {get(id).handlers.click(); await new Promise(resolve => setImmediate(resolve));},
    needsCheck: () => context.window.rrwProfiles.needsCheck(), accepted: () => loaded,
    failRead: value => {failedRead = value;}, lose: () => {lost = true;}, reject: () => {rejected = true;},
    invalid: () => {invalid = true;}, afterSave: fn => {afterSave = fn;},
    replaceSaved: value => {stored = value; revision = 'b'.repeat(64);},
    unload: () => {let prevented = false; events.beforeunload({preventDefault(){prevented = true;}}); return prevented;}};
}

async function main() {
  const saved = fixture(); saved.failRead(true); await saved.click('save-profile');
  assert.match(saved.messages.at(-1), /Business profile saved.*list could not refresh/);
  assert.equal(saved.context.workspace.profiles_revision, 'a'.repeat(64));
  assert.equal(saved.context.workspace.profiles.demo.voice.opener, 'CONTROLLED_EXISTING_VOICE');
  assert.equal(saved.get('profile-select').value, 'demo'); assert.equal(saved.accepted(), 1);
  assert.equal(saved.get('review').value, 'CONTROLLED_PENDING_REVIEW');
  assert.equal(saved.get('policy-confirmed').checked, true); // Explicit confirmation was not restored by a read.
  assert.equal(saved.calls.filter(row => row.action === 'profile').length, 1);
  assert.equal(saved.get('save-profile').disabled, false);
  assert.equal(saved.tracker.changed({...saved.context.settings(), review: saved.get('review').value}), true);

  const lost = fixture(); lost.lose(); await lost.click('save-profile');
  assert.equal(lost.needsCheck(), true); assert.equal(lost.get('save-profile').disabled, true);
  assert.equal(lost.get('policy-confirmed').checked, false); assert.equal(lost.unload(), true);
  await lost.click('save-profile'); assert.equal(lost.calls.filter(row => row.action === 'profile').length, 1);
  lost.get('offer').value = 'New unsaved owner input'; lost.failRead(true); await lost.click('profile-check');
  assert.equal(lost.needsCheck(), true); assert.equal(lost.get('offer').value, 'New unsaved owner input');
  lost.failRead(false); await lost.click('profile-check');
  assert.equal(lost.needsCheck(), false); assert.equal(lost.get('policy-confirmed').checked, false);
  assert.equal(lost.get('offer').value, 'New unsaved owner input');
  assert.match(lost.get('profile-save-state').textContent, /matches the submitted.*does not identify/);
  assert.equal(lost.get('review').value, 'CONTROLLED_PENDING_REVIEW');
  assert.equal(lost.calls.filter(row => row.action === 'profile').length, 1);
  assert.equal(lost.accepted(), 0); assert.equal(lost.unload(), false);

  for (const stored of [{}, {demo: {business: 'Changed Cafe', offer: '', approved_actions: []}}]) {
    const changed = fixture(); changed.lose(); await changed.click('save-profile'); changed.replaceSaved(stored);
    await changed.click('profile-check');
    assert.equal(changed.get('business').value, 'Demo Cafe');
    assert.equal(changed.get('policy-confirmed').checked, false);
    assert.equal(changed.context.workspace.profiles_revision, 'b'.repeat(64));
    assert.match(changed.get('profile-save-state').textContent, stored.demo ? /differs/ : /not in/);
    assert.equal(changed.calls.filter(row => row.action === 'profile').length, 1);
  }

  const typing = fixture(); typing.afterSave(() => {typing.get('business').value = 'Further unsaved business'; typing.get('profile-name').value = 'new-key';});
  await typing.click('save-profile');
  assert.equal(typing.get('business').value, 'Further unsaved business'); assert.equal(typing.accepted(), 0);
  assert.equal(typing.context.workspace.profiles.demo.business, 'Demo Cafe');
  assert.equal(typing.get('profile-select').value, '');

  const rejected = fixture(); rejected.reject(); await rejected.click('save-profile');
  assert.equal(rejected.needsCheck(), false); assert.equal(rejected.get('policy-confirmed').checked, true);
  assert.match(rejected.get('profile-save-state').textContent, /rejected/);
  const malformed = fixture(); malformed.invalid(); await malformed.click('save-profile');
  assert.equal(malformed.needsCheck(), true); assert.equal(malformed.get('policy-confirmed').checked, false);
  console.log(JSON.stringify({profile_save_recovery_checks: 'passed', browser_navigation: false, model_calls: 0}));
}
main().catch(error => {console.error(error); process.exitCode = 1;});
