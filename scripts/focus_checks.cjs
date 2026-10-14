'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const {FocusHandoff} = require('../web/focus.js');

async function main() {
  let busy = true, focused = '', scrolled = '', enabledAtFocus = false;
  const details = {open: false};
  const target = {isConnected: true, disabled: true, tagName: 'TEXTAREA', hidden: false,
    closest(selector) {return selector === 'details' ? details : this.hidden ? {} : null;},
    getClientRects: () => [{}],
    focus(options) {assert.equal(options.preventScroll, true); focused = 'editor'; enabledAtFocus = !this.disabled;},
    scrollIntoView(options) {assert.equal(options.behavior, 'auto'); scrolled = options.block;}};
  const helper = new FocusHandoff(id => id === 'editor' ? target : null, () => busy);
  helper.request('editor', true);
  assert.equal(focused, ''); assert.equal(helper.flush(), false);
  busy = false; target.disabled = false;
  assert.equal(helper.flush(), true); assert.equal(details.open, true);
  assert.equal(enabledAtFocus, true); assert.equal(scrolled, 'nearest');
  for (const change of [{disabled: true}, {isConnected: false}, {hidden: true}]) {
    Object.assign(target, change); focused = '';
    helper.request('editor', true); assert.equal(focused, '');
    Object.assign(target, {disabled: false, isConnected: true, hidden: false});
  }
  helper.request('missing'); assert.equal(helper.pending, null);
  target.getClientRects = () => []; focused = ''; helper.request('editor', true); assert.equal(focused, '');
  target.getClientRects = () => [{}];
  details.open = false; focused = ''; helper.request('editor'); assert.equal(focused, '');
  busy = true; helper.request('editor', true); helper.request('missing'); busy = false;
  assert.equal(helper.flush(), false); assert.equal(focused, ''); // Latest request wins, no delayed focus theft.

  // Actual library/render/run code, with controlled DOM removal and focus.
  const app = fs.readFileSync(path.join(__dirname, '../web/app.js'), 'utf8');
  const elements = new Map(), controls = [];
  let active = null;
  const sourceDetails = {open: false};
  function element(tag = 'div') {
    const value = {tagName: tag.toUpperCase(), value: '', children: [], dataset: {}, disabled: false,
      isConnected: true, hidden: false, textContent: '', events: {}, classList: {toggle() {}, add() {}, remove() {}},
      setAttribute() {}, append(...children) {this.children.push(...children);},
      replaceChildren(...children) {
        if (this.children.includes(active)) {active.isConnected = false; active = null;}
        this.children = children;
      },
      addEventListener(type, handler) {this.events[type] = handler;},
      closest(selector) {return selector === 'details' && this.id === 'saved-source-heading' ? sourceDetails
        : selector === '[hidden]' && this.hidden ? {} : null;}, getClientRects: () => [{}],
      focus() {assert.equal(this.disabled, false); active = this;}, scrollIntoView() {}};
    if (['BUTTON', 'INPUT', 'SELECT', 'TEXTAREA'].includes(value.tagName)) controls.push(value);
    return value;
  }
  const get = id => {
    if (!elements.has(id)) {
      const tag = id === 'reply-editor' ? 'textarea' : id === 'generate' ? 'button' : id === 'saved-source-heading' ? 'summary' : 'div';
      const value = element(tag); value.id = id; elements.set(id, value);
    }
    return elements.get(id);
  };
  get('queue-filter').value = 'all'; get('human-reviewed').checked = true;
  const view = {id: 'reply-demo.md', revision: 'fixture-revision', business: 'Demo Cafe', review: 'Fictional review.',
    reply: 'Fictional saved reply.', status: 'pending', findings: [], word_count: 3, word_target: [0, 90]};
  let accept = true, reads = 0, rejectRead = false;
  const context = {window: {}, busy: false, current: null, dirty: false,
    workspace: {drafts: [view]}, $: get, node: (tag, text, className) => element(tag),
    document: {querySelector: () => element(), querySelectorAll: selector => selector === 'button, input, select, textarea' ? controls : []},
    labels: {pending: 'Needs review'},
    confirmDiscard: () => accept,
    api: async () => {reads++; if (rejectRead) throw new Error('Controlled read failure'); return view;},
    fillForm() {}, notify(message) {get('notice').hidden = false; get('notice').textContent = message;},
    typeChanged() {}, updateButtons() {}, qualityButtons() {}, showView() {}, renderReviewEvidence() {},
    engineLabel: () => 'Template preview', resetReviewEvidence() {},
    reviewContext: value => value.review};
  context.window.rrwFocus = new FocusHandoff(get, () => context.busy);
  vm.createContext(context);
  const section = (start, end) => app.slice(app.indexOf(start), app.indexOf(end));
  vm.runInContext(section('function setBusy(', 'function updateProgress('), context);
  vm.runInContext(section('function renderQueue(', 'function renderProfiles('), context);
  vm.runInContext(section('function renderDraft(', 'function idRevision('), context);
  context.renderQueue();
  let button = get('queue-list').children[0]; active = button;
  accept = false; button.events.click();
  assert.equal(active, button); assert.equal(reads, 0);
  accept = true; button.events.click(); await new Promise(resolve => setImmediate(resolve));
  assert.equal(button.isConnected, false);
  assert.equal(active.id, 'saved-source-heading'); assert.equal(sourceDetails.open, true);
  assert.equal(get('reply-editor').value, view.reply);
  // Background refresh does not pull focus away from typed text.
  active = get('reply-editor'); context.renderDraft(view);
  assert.equal(active.id, 'reply-editor');
  rejectRead = true; context.renderQueue(); button = get('queue-list').children[0]; active = button;
  button.events.click(); await new Promise(resolve => setImmediate(resolve));
  assert.equal(active.id, 'notice'); assert.match(get('notice').textContent, /Controlled read failure/);
  console.log(JSON.stringify({focus_handoff_checks: 'passed', browser_navigation: false, model_calls: 0}));
}
main().catch(error => {console.error(error); process.exitCode = 1;});
