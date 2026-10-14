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
profileSelectionChecks().then(() => console.log(JSON.stringify({input_state_checks: 'passed', browser_navigation: false})))
  .catch(error => {console.error(error); process.exitCode = 1;});
