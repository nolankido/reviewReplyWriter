'use strict';
// Focus is a handoff after an explicit action, never approval or a value change.
class FocusHandoff {
  constructor(find, isBusy) { this.find = find; this.isBusy = isBusy; this.pending = null; }
  request(id, open = false) {
    this.pending = {id, open};
    if (!this.isBusy()) this.flush();
  }
  flush() {
    if (this.isBusy() || !this.pending) return false;
    const item = this.pending; this.pending = null;
    const target = this.find(item.id);
    if (!target || target.isConnected === false || target.disabled || target.closest('[hidden]')) return false;
    const details = target.closest('details');
    if (details && item.open) details.open = true;
    if (details && !details.open && target.tagName !== 'SUMMARY') return false;
    if (typeof target.getClientRects === 'function' && !target.getClientRects().length) return false;
    target.focus({preventScroll: true});
    target.scrollIntoView({block: 'nearest', behavior: 'auto'});
    return true;
  }
}
if (typeof module !== 'undefined' && module.exports) module.exports = {FocusHandoff};
else window.rrwFocus = new FocusHandoff(id => document.getElementById(id), () => busy);
