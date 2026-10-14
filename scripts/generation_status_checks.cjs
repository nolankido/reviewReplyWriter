'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const app = fs.readFileSync(require('node:path').join(__dirname, '../web/app.js'), 'utf8');
const elements = new Map();
let requests = 0, focus = '', qualityOpened = 0;
const get = id => {
  if (!elements.has(id)) elements.set(id, {textContent: '', hidden: false, open: false, events: {},
    addEventListener(type, fn) {this.events[type] = fn;}, click() {qualityOpened++;}});
  return elements.get(id);
};
get('reply-editor').value = 'Private pending edit';
get('human-reviewed').checked = false;
get('policy-confirmed').checked = false;
const context = {$: get, window: {rrwFocus: {request(id) {focus = id;}}},
  fetch() {requests++; throw new Error('Rendering must not call the network');}};
vm.createContext(context);
vm.runInContext(app.slice(app.indexOf('function renderGenerationStatus('), app.indexOf('function renderQueue(')), context);
for (const action of ['setup', 'quality', null]) {
  context.renderGenerationStatus({generation_status: {state: 'unavailable', title: '<script>not markup</script>',
    message: 'Controlled fallback', next_step: 'Deliberate next action', action, attempts: 2, checked_completions: 1}, human_edited: true});
  assert.equal(get('generation-status-title').textContent, '<script>not markup</script>');
  assert.equal(get('generation-status-panel').open, true);
  assert.equal(get('generation-status-setup').hidden, action !== 'setup');
  assert.equal(get('generation-status-quality').hidden, action !== 'quality');
  assert.equal(get('generation-status-edited').hidden, false);
  assert.match(get('generation-status-counts').textContent, /2 local request attempts.*1 checked completion receipts/);
  assert.equal(get('reply-editor').value, 'Private pending edit');
  assert.equal(get('human-reviewed').checked, false); assert.equal(get('policy-confirmed').checked, false);
}
context.renderGenerationStatus({});
assert.equal(get('generation-status-title').textContent, 'Generation result not recorded');
assert.equal(get('generation-status-counts').textContent, '');
assert.equal(get('generation-status-panel').open, false);
assert.equal(get('generation-status-edited').hidden, true);
assert.equal(qualityOpened, 0); assert.equal(focus, '');
get('generation-status-setup').events.click();
assert.equal(get('setup-guide').open, true); assert.equal(focus, 'setup-heading');
get('generation-status-quality').events.click();
assert.equal(qualityOpened, 1); assert.equal(requests, 0);
assert.equal(get('reply-editor').value, 'Private pending edit');
console.log(JSON.stringify({generation_status_checks: 'passed', browser_navigation: false, model_calls: 0}));
