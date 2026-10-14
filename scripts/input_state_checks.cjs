'use strict';
const assert = require('node:assert/strict');
const {InputTracker} = require('../web/recovery.js');

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
console.log(JSON.stringify({input_state_checks: 'passed', browser_navigation: false}));
