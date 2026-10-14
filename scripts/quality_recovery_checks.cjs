'use strict';
// Actual Quality Lab functions/handlers with controlled DOM and API responses.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const app = fs.readFileSync(require('node:path').join(__dirname, '../web/app.js'), 'utf8');
const clone = value => JSON.parse(JSON.stringify(value));

function report(attempted = 1, revision = 'one') {
  return {id: 'eval-' + 'a'.repeat(32), revision, active: false, sources_current: true,
    mode: 'offline', suite: 'smoke', execution: 'templates', provenance: 'Controlled fictional fixture',
    preflight: {ready: false}, evidence_blockers: ['No actual model evidence'],
    summary: {attempted, total: 3, model: 0, template: attempted, fallback: 0, blocked: 0,
      error: 0, interrupted: 0, rubric_flagged: 0, human_reviewed: 0, human_risk_flags: 0,
      model_median_seconds: null, complete: attempted === 3, first_try_model: 0, retried_cases: 0, completed_api_responses: 0},
    cases: [0, 1, 2].map(i => ({id: 'case-' + i, label: 'Fictional case ' + i, expected_tier: 'negative',
      input: {business: 'Demo Cafe', review: 'Cold coffee.', platform: 'generic', approved_actions: []}})),
    results: Array.from({length: attempted}, (_, i) => ({case_id: 'case-' + i, status: 'template',
      reply: 'Controlled reply ' + i, findings: [], rubric_findings: [], attempts: [], result_sha256: 'result-' + i}))};
}
function fixture() {
  const elements = new Map(), calls = [], messages = [], pending = [];
  let saved = report(), loseStart = false, loseStep = false, loseAssessment = false, failList = false, failGet = false, accept = true, focus = '';
  const element = (tag = 'div', text = '') => ({tagName: tag, textContent: text, value: '', checked: false,
    hidden: false, disabled: false, open: false, children: [], events: {}, dataset: {}, classList: {toggle() {}},
    setAttribute() {}, addEventListener(type, handler) {this.events[type] = handler;},
    replaceChildren(...children) {this.children = children;}, append(...children) {this.children.push(...children);}});
  const get = id => {if (!elements.has(id)) elements.set(id, element()); return elements.get(id);};
  get('quality-mode').value = 'offline'; get('quality-suite').value = 'smoke';
  get('quality-confirm').checked = true; get('policy-confirmed').checked = false; get('human-reviewed').checked = false;
  get('review').value = 'Private pending compose input'; get('reply-editor').value = 'Private pending owner reply';
  const issues = [{value: 'wrong_tone', checked: false}];
  const context = {$: get, busy: false, window: {confirm: () => accept, rrwFocus: {request(id) {focus = id;}}},
    document: {querySelectorAll: selector => selector.endsWith(':checked') ? issues.filter(x => x.checked) : issues},
    Option: function(text, value) {return {...element('option', text), value};}, node: element,
    notify(message, error) {messages.push({message, error});},
    URL: {createObjectURL() {throw new Error('Unresolved export must be blocked');}}, Blob: function() {},
    api: async (action, data) => {
      calls.push({action, data: clone(data)});
      if (action === 'quality-get') {if (failGet) throw new Error('Controlled read failure'); return clone(saved);}
      if (action === 'quality-list') {
        if (failList) throw new Error('Controlled list failure');
        return {runs: [{...clone(saved), created_at: '2026-10-14T15:00:00Z'}]};
      }
      if (action === 'quality-start') {
        saved = report(0, 'created');
        if (loseStart) {const error = new Error('Controlled dropped creation'); error.uncertain = true; throw error;}
        return clone(saved);
      }
      if (action === 'quality-step') {
        saved = report(saved.results.length + 1, 'step-saved');
        if (loseStep) {const error = new Error('Controlled dropped response'); error.uncertain = true; throw error;}
        return clone(saved);
      }
      if (action === 'quality-assess') {
        saved.results.find(row => row.case_id === data.case_id).human_review = {decision: data.decision, notes: data.notes};
        saved.revision = 'assessment-saved'; saved.summary.human_reviewed++;
        if (loseAssessment) {const error = new Error('Controlled dropped assessment'); error.uncertain = true; throw error;}
        return clone(saved);
      }
      throw new Error('Unexpected mutation ' + action);
    }};
  context.run = task => {
    if (context.busy) return;
    const promise = (async () => {context.busy = true;
      try {await task();} catch (error) {context.notify(error.message, true);}
      finally {context.busy = false; context.qualityButtons();}})();
    pending.push(promise); return promise;
  };
  vm.createContext(context);
  const start = app.indexOf('// Quality experiments');
  vm.runInContext(app.slice(start, app.indexOf('policyChanged(); countReview(); updateButtons(); qualityButtons();', start)), context);
  const state = () => vm.runInContext('({qualityRun, qualityCase, qualityDirty, qualityNeedsCheck, qualityChecked})', context);
  context.renderQuality(clone(saved));
  return {get, context, state, calls, messages, issues, focus: () => focus,
    saved: () => saved, setSaved(value) {saved = clone(value);},
    loseStart() {loseStart = true;}, loseStep() {loseStep = true;}, loseAssessment() {loseAssessment = true;},
    failList() {failList = true;}, failGet() {failGet = true;}, accept(value) {accept = value;},
    edit(text) {get('quality-notes').value = text; get('quality-assess-form').events.input();},
    async click(id, type = 'click') {get(id).events[type]({preventDefault() {}}); await Promise.all(pending.splice(0));},
    assertPrivateKept() {
      assert.equal(get('review').value, 'Private pending compose input');
      assert.equal(get('reply-editor').value, 'Private pending owner reply');
      assert.equal(get('policy-confirmed').checked, false); assert.equal(get('human-reviewed').checked, false);
    }};
}
async function main() {
  const lost = fixture(); lost.loseStep(); await lost.click('quality-next');
  assert.equal(lost.state().qualityNeedsCheck, true); assert.equal(lost.state().qualityRun.revision, 'one');
  assert.equal(lost.get('quality-next').disabled, true); assert.equal(lost.get('quality-json').disabled, true);
  // Even programmatic/form activation cannot bypass the local unresolved gate.
  for (const [id, type] of [['quality-next', 'click'], ['quality-start', 'click'],
      ['quality-assess-form', 'submit'], ['quality-json', 'click']]) await lost.click(id, type);
  assert.equal(lost.calls.filter(x => x.action === 'quality-step').length, 1);
  assert.equal(lost.calls.filter(x => ['quality-start', 'quality-assess', 'quality-export'].includes(x.action)).length, 0);
  lost.edit('Pending assessment remains private'); lost.get('quality-reviewed').checked = false;
  await lost.click('quality-recovery-check');
  assert.equal(lost.get('quality-notes').value, 'Pending assessment remains private');
  assert.equal(lost.state().qualityDirty, true); assert.equal(lost.state().qualityRun.revision, 'one');
  assert.equal(lost.focus(), 'quality-recovery-message'); lost.assertPrivateKept();
  lost.accept(false); const reads = lost.calls.length; await lost.click('quality-recovery-load');
  assert.equal(lost.calls.length, reads); assert.equal(lost.get('quality-notes').value, 'Pending assessment remains private');
  lost.accept(true); await lost.click('quality-recovery-load');
  assert.equal(lost.state().qualityRun.revision, 'step-saved'); assert.equal(lost.state().qualityCase.case_id, 'case-1');
  assert.equal(lost.state().qualityNeedsCheck, false); assert.equal(lost.get('quality-reviewed').checked, false);
  assert.equal(lost.get('quality-confirm').checked, false); assert.equal(lost.focus(), 'quality-progress');
  assert.equal(lost.calls.filter(x => x.action === 'quality-step').length, 1); lost.assertPrivateKept();

  const changed = fixture(); changed.loseStep(); await changed.click('quality-next');
  await changed.click('quality-recovery-check'); changed.setSaved(report(3, 'newer-checkpoint'));
  changed.edit('Do not overwrite from a stale check'); await changed.click('quality-recovery-load');
  assert.equal(changed.state().qualityRun.revision, 'one'); assert.equal(changed.state().qualityChecked, null);
  assert.equal(changed.get('quality-notes').value, 'Do not overwrite from a stale check');
  assert.match(changed.get('quality-recovery-message').textContent, /changed or is still running/);

  const active = fixture(); const inFlight = report(3, 'reserved'); inFlight.active = true;
  inFlight.summary.interrupted = 1; inFlight.summary.template = 2;
  inFlight.results[2].status = 'interrupted'; active.setSaved(inFlight);
  active.context.renderQuality(clone(inFlight));
  assert.match(active.get('quality-progress').textContent, /Case still running/);
  assert.doesNotMatch(active.get('quality-progress').textContent, /Run complete/);
  assert.equal(active.get('quality-assess').disabled, true); await active.click('quality-recovery-check');
  assert.equal(active.get('quality-recovery-load').disabled, true);
  await active.click('quality-recovery-load'); assert.equal(active.calls.length, 1);
  inFlight.active = false; active.setSaved(inFlight); await active.click('quality-recovery-check');
  assert.match(active.get('quality-recovery-message').textContent, /interrupted case.*not be silently repeated/);
  await active.click('quality-recovery-load'); assert.equal(active.state().qualityRun.summary.interrupted, 1);

  const assessment = fixture(); assessment.edit('Assessment sent before disconnect');
  assessment.get('quality-decision').value = 'needs_edit'; assessment.get('quality-reviewed').checked = true;
  assessment.loseAssessment(); await assessment.click('quality-assess-form', 'submit');
  assert.equal(assessment.state().qualityDirty, true); assert.equal(assessment.get('quality-reviewed').checked, false);
  assessment.edit('Further private unsaved notes'); await assessment.click('quality-recovery-check');
  assert.equal(assessment.get('quality-notes').value, 'Further private unsaved notes');
  assert.equal(assessment.calls.filter(x => x.action === 'quality-assess').length, 1);
  await assessment.click('quality-recovery-load');
  assert.equal(assessment.get('quality-notes').value, 'Assessment sent before disconnect');
  assert.equal(assessment.get('quality-reviewed').checked, false); assessment.assertPrivateKept();

  const failRead = fixture(); failRead.loseStep(); await failRead.click('quality-next'); failRead.failGet();
  await failRead.click('quality-recovery-check'); assert.equal(failRead.state().qualityNeedsCheck, true);
  assert.equal(failRead.state().qualityRun.revision, 'one'); assert.equal(failRead.get('quality-next').disabled, true);

  for (const [id, type, expected] of [['quality-next', 'click', 'step-saved'],
      ['quality-start', 'click', 'created'], ['quality-assess-form', 'submit', 'assessment-saved']]) {
    const acknowledged = fixture(); acknowledged.failList();
    if (id === 'quality-assess-form') {acknowledged.get('quality-decision').value = 'usable'; acknowledged.get('quality-reviewed').checked = true;}
    await acknowledged.click(id, type);
    assert.equal(acknowledged.state().qualityRun.revision, expected);
    assert.equal(acknowledged.state().qualityNeedsCheck, false);
    assert.match(acknowledged.messages.at(-1).message, /acknowledged result is displayed; no write was repeated/);
    assert.equal(acknowledged.calls.filter(x => !['quality-get', 'quality-list'].includes(x.action)).length, 1);
  }
  const creation = fixture(); creation.loseStart(); await creation.click('quality-start');
  assert.equal(creation.state().qualityRun.revision, 'one');
  assert.match(creation.messages.at(-1).message, /Refresh saved evaluations and select its run/);
  assert.equal(creation.calls.filter(x => x.action === 'quality-start').length, 1);
  assert.equal(creation.calls.filter(x => x.action === 'quality-step').length, 0);
  console.log(JSON.stringify({quality_recovery_checks: 'passed', browser_navigation: false, model_calls: 0}));
}
main().catch(error => {console.error(error); process.exitCode = 1;});
