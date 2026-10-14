'use strict';
const assert = require('node:assert/strict');
const {InputTracker} = require('../web/recovery.js');
const fs = require('node:fs'), path = require('node:path'), vm = require('node:vm');

const initial = {business: 'Demo Cafe', review: '', original: '', previous: '',
  offer: '', approved_actions: [], followup: false, stars: null};
const tracker = new InputTracker(initial);
assert.equal(tracker.changed(initial), false);
const typed = {...initial, review: 'A review not yet drafted.', offer: 'An owner statement input.'};
assert.equal(tracker.changed(typed), true);
assert.equal(tracker.changed(typed, ['business']), false);
assert.equal(tracker.changed(typed, ['offer']), true);

// New reply clears review/thread/rating, while pending owner settings remain protected.
const reset = {...typed, review: '', original: '', previous: '', followup: false, stars: null};
tracker.accept(reset, ['review', 'original', 'previous', 'followup', 'stars']);
assert.equal(tracker.changed(reset), true);
assert.equal(tracker.changed(reset, ['review', 'original', 'previous', 'stars']), false);
tracker.accept(reset, ['offer']);
assert.equal(tracker.changed(reset), false);

// Loading a profile must keep a separately typed review marked as changed.
const reviewed = {...reset, review: 'Pending customer review.', business: 'Saved Shop'};
tracker.accept(reviewed, ['business', 'offer', 'approved_actions']);
assert.equal(tracker.changed(reviewed), true);
tracker.accept(reviewed);
assert.equal(tracker.changed(reviewed), false);
assert.equal(tracker.changed({...reviewed, review: initial.review}), true);

// Snapshot values must not become clean through mutable array aliases.
const mutable = {approved_actions: ['First input']};
const other = new InputTracker(mutable);
mutable.approved_actions.push('Second input');
assert.equal(other.changed(mutable), true);

// Real profile-selection and recovery handlers with controlled DOM/API data.
async function profileSelectionChecks() {
  const app = fs.readFileSync(path.join(__dirname, '../web/app.js'), 'utf8');
  const recovery = fs.readFileSync(path.join(__dirname, '../web/recovery.js'), 'utf8');
  async function fixture() {
    const elements = new Map(), prompts = [], calls = [];
    let confirm = false, lastRun, stored = {available: false, revision: 'new'};
    const get = id => {
      if (!elements.has(id)) elements.set(id, {value: '', checked: false, hidden: false,
        disabled: false, events: {}, textContent: '',
        addEventListener(type, handler) {this.events[type] = handler;},
        dispatchEvent(event) {this.events[event.type]?.(event);}});
      return elements.get(id);
    };
    const profile = {business: 'Saved Shop', kind: 'shop', tone: 'warm', platform: 'google',
      offer: 'Controlled saved offer', approved_actions: ['Controlled saved action.'], signoff: 'Saved team'};
    for (const [id, value] of Object.entries({business: 'Demo Cafe', kind: 'cafe',
      tone: 'professional', platform: 'google', 'reply-type': 'first', 'profile-select': 'demo'})) get(id).value = value;
    const context = {window: {confirm(message) {prompts.push(message); return confirm;}}, $: get,
      busy: false, current: null, dirty: false, Event: class {constructor(type){this.type = type;}},
      workspace: {profiles: {shop: profile}}, notify(){}, typeChanged(){}, countReview(){},
      clearEditor(){}, renderDraft(){return true;}, confirmDiscard: () => true,
      api: async (action, data) => {calls.push({action, data}); assert.equal(action, 'recovery-get'); return stored;},
      run: task => {lastRun = task(); return lastRun;}};
    vm.createContext(context);
    const section = (start, end) => app.slice(app.indexOf(start), app.indexOf(end));
    vm.runInContext(section('function policyChanged(', 'function typeChanged('), context);
    vm.runInContext(section('function settings(', 'function clearEditor('), context);
    vm.runInContext(recovery, context);
    vm.runInContext(section("$('profile-select').addEventListener", "for (const id of ['business', 'offer'"), context);
    await new Promise(resolve => setImmediate(resolve));
    return {context, get, prompts, calls, profile,
      choose: key => {get('profile-select').value = key; get('profile-select').events.change();},
      confirm: value => {confirm = value;},
      restore: async inputs => {
        stored = {available: true, revision: 'new', saved_at: 'CONTROLLED_TIME', editor_state: 'none',
          payload: {inputs, editor: null}};
        get('recovery-check').events.click(); await lastRun;
        get('recovery-restore').events.click(); await lastRun;
      }};
  }
  const pending = await fixture();
  pending.get('offer').value = 'CONTROLLED_UNSAVED_OWNER_TEXT';
  pending.context.policyChanged(); pending.choose('');
  assert.equal(pending.context.window.rrwRecovery.hasInputChanges(), true);
  assert.equal(pending.context.window.rrwRecovery.canReplace(), false);
  assert.equal(pending.get('offer').value, 'CONTROLLED_UNSAVED_OWNER_TEXT');
  assert.equal(pending.get('policy-confirmed').checked, false);
  assert.equal(pending.context.window.rrwRecovery.previousProfile(), '');
  pending.choose('shop'); // Cancelling a later load returns to the blank selection.
  assert.equal(pending.get('profile-select').value, '');
  assert.equal(pending.get('offer').value, 'CONTROLLED_UNSAVED_OWNER_TEXT');
  pending.confirm(true); pending.choose('shop');
  assert.equal(pending.get('business').value, 'Saved Shop');
  assert.equal(pending.context.window.rrwRecovery.hasInputChanges(), false);
  assert.equal(pending.get('policy-confirmed').checked, false);

  const review = await fixture(); review.get('review').value = 'CONTROLLED_PENDING_REVIEW';
  review.choose('shop');
  assert.equal(review.prompts.length, 0); // No changed settings were replaced.
  assert.equal(review.context.window.rrwRecovery.hasInputChanges(), true);
  assert.equal(review.get('review').value, 'CONTROLLED_PENDING_REVIEW');

  const clean = await fixture(); clean.choose('');
  assert.equal(clean.context.window.rrwRecovery.hasInputChanges(), false);
  assert.equal(clean.prompts.length, 0);

  const recovered = await fixture();
  await recovered.restore({business: 'Recovered Cafe', kind: 'cafe', tone: 'professional',
    platform: 'google', offer: 'CONTROLLED_RECOVERED_OWNER_TEXT', signoff: '', approved_actions: [],
    review: 'CONTROLLED_RECOVERED_REVIEW', stars: 2, followup: false, original: '', previous: '', mode: 'offline'});
  assert.equal(recovered.context.window.rrwRecovery.hasInputChanges(), true);
  recovered.choose('shop');
  assert.equal(recovered.get('business').value, 'Recovered Cafe');
  assert.equal(recovered.get('offer').value, 'CONTROLLED_RECOVERED_OWNER_TEXT');
  assert.equal(recovered.get('policy-confirmed').checked, false);
  assert.match(recovered.prompts.at(-1), /Replace changed business settings/);
  recovered.confirm(true); recovered.choose('shop');
  assert.equal(recovered.get('business').value, 'Saved Shop');
  assert.equal(recovered.get('review').value, 'CONTROLLED_RECOVERED_REVIEW');
  assert.equal(recovered.context.window.rrwRecovery.hasInputChanges(), true);
  const promptCount = recovered.prompts.length;
  assert.equal(recovered.context.window.rrwRecovery.canLoadProfile(), true);
  assert.equal(recovered.prompts.length, promptCount); // Settings are acknowledged; recovered review still is not.
  assert.ok([...pending.calls, ...review.calls, ...clean.calls, ...recovered.calls].every(c => c.action === 'recovery-get'));
}
async function recoveryMutationChecks() {
  const recovery = fs.readFileSync(path.join(__dirname, '../web/recovery.js'), 'utf8');
  async function fixture(available = false) {
    const elements = new Map(), calls = [], messages = [];
    let mode = '', lastRun;
    const get = id => {
      if (!elements.has(id)) elements.set(id, {value: '', checked: false, hidden: false, disabled: false,
        textContent: '', events: {}, addEventListener(type, fn) {this.events[type] = fn;}});
      return elements.get(id);
    };
    const values = {business: 'Demo Cafe', kind: 'cafe', tone: 'professional', platform: 'google',
      offer: '', signoff: '', approved_actions: []};
    const payload = {inputs: {...values, review: 'CONTROLLED_SAVED_REVIEW', stars: null,
      followup: false, original: '', previous: '', mode: 'offline'}, editor: null};
    let stored = {available, revision: available ? 'a'.repeat(64) : 'new',
      payload: available ? payload : null, saved_at: available ? 'CONTROLLED_TIME' : null, editor_state: 'none'};
    const context = {$: get, window: {confirm: () => true}, busy: false, dirty: true,
      current: {id: 'reply-fixture.md', revision: 'd'.repeat(64)}, settings: () => ({...values}),
      notify: message => messages.push(message), confirmDiscard: () => true,
      api: async (action, data) => {
        calls.push({action, data});
        if (action === 'recovery-get') return stored;
        assert.ok(['recovery-save', 'recovery-clear'].includes(action));
        if (mode === 'reject') {const error = Error('CONTROLLED_REJECTION'); error.status = 400; throw error;}
        stored = {available: action === 'recovery-save', revision: 'b'.repeat(64),
          payload: action === 'recovery-save' ? JSON.parse(JSON.stringify(data.payload)) : null,
          saved_at: 'CONTROLLED_NEW_TIME', editor_state: action === 'recovery-save' ? 'current' : 'none'};
        if (mode === 'different') stored.payload.inputs.review = 'CONTROLLED_OTHER_REVIEW';
        if (mode === 'lost' || mode === 'conflict') {
          const error = Error('CONTROLLED_UNCERTAIN_COPY');
          if (mode === 'lost') error.uncertain = true; else error.status = 409;
          throw error;
        }
        return mode === 'malformed' ? {available: false} : mode === 'malformed_payload' ?
          {...stored, payload: {inputs: null, editor: null}} : stored;
      },
      run: task => {lastRun = (async () => {
        context.busy = true;
        try {await task();} catch (error) {messages.push(error.message);}
        finally {context.busy = false; context.window.rrwRecovery.buttons();}
      })(); return lastRun;}};
    vm.createContext(context); vm.runInContext(recovery, context);
    await new Promise(resolve => setImmediate(resolve));
    get('review').value = 'CONTROLLED_PENDING_REVIEW';
    get('reply-editor').value = 'CONTROLLED_PENDING_REPLY';
    get('recovery-orphan-text').value = 'CONTROLLED_INSPECTION_TEXT';
    return {get, context, calls, messages, mode: value => {mode = value;},
      click: async id => {get(id).events.click(); await lastRun;}};
  }
  const saved = await fixture(); await saved.click('recovery-save');
  assert.match(saved.messages.at(-1), /^Working copy saved privately/);
  assert.equal(saved.get('recovery-restore').disabled, false);
  assert.equal(saved.context.window.rrwRecovery.hasInputChanges(), true);
  assert.equal(saved.calls[1].data.payload.editor.reply, 'CONTROLLED_PENDING_REPLY');

  for (const action of ['save', 'clear']) for (const mode of ['lost', 'conflict', 'malformed', ...(action === 'save' ? ['different', 'malformed_payload'] : [])]) {
    const pending = await fixture(action === 'clear'); pending.mode(mode);
    await pending.click('recovery-' + action);
    if (mode === 'malformed_payload') assert.match(pending.messages.at(-1), /no matching receipt/);
    assert.equal(pending.get('review').value, 'CONTROLLED_PENDING_REVIEW');
    assert.equal(pending.get('reply-editor').value, 'CONTROLLED_PENDING_REPLY');
    assert.equal(pending.get('recovery-orphan-text').value, 'CONTROLLED_INSPECTION_TEXT');
    assert.equal(pending.get('policy-confirmed').checked, false);
    assert.match(pending.get('recovery-status').textContent, /uncertain.*Check the saved copy/);
    for (const id of ['recovery-save', 'recovery-restore', 'recovery-clear'])
      assert.equal(pending.get(id).disabled, true);
    await pending.click('recovery-save'); await pending.click('recovery-restore'); await pending.click('recovery-clear');
    assert.equal(pending.calls.filter(c => c.action !== 'recovery-get').length, 1);
    pending.mode(''); await pending.click('recovery-check');
    assert.equal(pending.get('recovery-save').disabled, false);
    assert.equal(pending.get('recovery-restore').disabled, action === 'clear');
    assert.equal(pending.get('review').value, 'CONTROLLED_PENDING_REVIEW');
    assert.equal(pending.get('reply-editor').value, 'CONTROLLED_PENDING_REPLY');
    assert.equal(pending.get('policy-confirmed').checked, false);
    assert.equal(pending.calls.filter(c => c.action !== 'recovery-get').length, 1); // Checking never repeats the write.
  }
  const cleared = await fixture(true); await cleared.click('recovery-clear');
  assert.match(cleared.messages.at(-1), /^Recovery copy discarded/);
  assert.equal(cleared.get('recovery-orphan-text').value, '');
  assert.equal(cleared.get('review').value, 'CONTROLLED_PENDING_REVIEW');
  assert.equal(cleared.get('reply-editor').value, 'CONTROLLED_PENDING_REPLY');
  const rejected = await fixture(); rejected.mode('reject'); await rejected.click('recovery-save');
  assert.equal(rejected.get('recovery-save').disabled, false); // A known pre-write rejection does not invalidate a read lease.
  assert.equal(rejected.get('review').value, 'CONTROLLED_PENDING_REVIEW');
}
profileSelectionChecks().then(recoveryMutationChecks).then(() => console.log(JSON.stringify({input_state_checks: 'passed', browser_navigation: false})))
  .catch(error => {console.error(error); process.exitCode = 1;});
