'use strict';
// Profile checking never replaces compose values or grants owner authorization.
(() => {
  let needsCheck = false, submitted = null;
  function canonical(value) {
    return {business: (value.business || '').trim(), kind: value.kind, tone: value.tone,
      platform: value.platform, offer: (value.offer || '').trim(), signoff: (value.signoff || '').trim(),
      approved_actions: (value.approved_actions || []).map(text => text.trim())};
  }
  function matches(left, right) { return JSON.stringify(canonical(left)) === JSON.stringify(canonical(right)); }
  function message(text) { $('profile-save-state').textContent = text; }
  function buttons() {
    if (busy) return;
    $('save-profile').disabled = needsCheck;
    $('profile-check').disabled = false;
  }
  function loaded(view) {
    if (submitted) {
      const saved = view.profiles[submitted.name];
      message(!saved ? 'The submitted profile key is not in the latest saved list. Your current inputs were kept. No request was repeated.'
        : matches(saved, submitted.values) ? 'The latest stored profile matches the submitted business settings. Checking kept your current inputs; it does not identify which request saved those values.'
        : 'The latest stored profile differs from the submitted settings. Your current inputs were kept. Load a profile explicitly or review the current form before saving again.');
    }
    needsCheck = false;
    buttons();
  }
  async function save() {
    if (needsCheck) throw new Error('Check saved profiles before another profile save. Your current inputs are kept.');
    const data = {...settings(), name: $('profile-name').value, profiles_revision: workspace.profiles_revision};
    submitted = {name: data.name, values: canonical(data)};
    let result;
    try {
      result = await api('profile', data);
      if (!result || result.name !== data.name || !result.profile ||
          !/^[0-9a-f]{64}$/.test(result.profiles_revision || '') || !matches(result.profile, data)) {
        const error = new Error('Profile save returned no matching receipt. Check saved profiles before another save.');
        error.uncertain = true; throw error;
      }
    } catch (error) {
      if (error.uncertain || !error.status || error.status >= 500 || error.status === 409) {
        needsCheck = true;
        $('policy-confirmed').checked = false;
        message('The profile save is uncertain or changed elsewhere. Your current form is kept. Check saved profiles before another save; no retry was sent. Confirm owner statements again before using them.');
      } else message('Profile save was rejected. Your current form is kept; review the reported issue before another save.');
      throw error;
    }
    // The acknowledged write carries the exact saved settings and new lease.
    // A failed later list read must not hide that success or restore an old lease.
    workspace = {...workspace, profiles: {...workspace.profiles, [result.name]: result.profile},
      profiles_revision: result.profiles_revision};
    renderProfiles();
    const sameForm = $('profile-name').value === data.name && matches(settings(), data);
    if (sameForm) {
      $('profile-select').value = result.name;
      if (window.rrwRecovery) window.rrwRecovery.profileLoaded();
    }
    const success = 'Business profile saved locally. Existing drafts keep their original policy.';
    message(success); notify(success);
    try { await refreshWorkspace(); }
    catch (error) {
      message(success + ' The saved-profile list could not refresh. The acknowledged profile and revision are kept. Use Check saved profiles later; no save was repeated.');
      notify(success + ' The list could not refresh; the acknowledged save is kept.', true);
    }
  }
  $('save-profile').addEventListener('click', () => run(save));
  $('profile-check').addEventListener('click', () => run(async () => {
    await refreshWorkspace();
    notify('Saved profiles checked. Your current form was kept. Nothing was saved, approved or posted.');
    if (window.rrwFocus) window.rrwFocus.request('profile-save-state', true);
  }));
  window.addEventListener('beforeunload', event => {
    if (needsCheck) {event.preventDefault(); event.returnValue = '';}
  });
  window.rrwProfiles = {buttons, loaded, needsCheck: () => needsCheck};
  buttons();
})();
