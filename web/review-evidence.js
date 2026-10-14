'use strict';

// Customer quotations remain inert text. Mention checks never approve a reply.
let evidenceView = null;
let evidenceReply = '';
function evidenceNode(tag, text, className) {
  const element = document.createElement(tag);
  if (text !== undefined) element.textContent = text;
  if (className) element.className = className;
  return element;
}
function evidencePanel() {
  let panel = document.getElementById('review-evidence');
  if (panel) return panel;
  panel = evidenceNode('section', undefined, 'review-evidence');
  panel.id = 'review-evidence';
  panel.setAttribute('aria-labelledby', 'review-evidence-title');
  const source = document.querySelector('#editor-content .source-review');
  source.insertAdjacentElement('afterend', panel);
  return panel;
}
function resetReviewEvidence() {
  evidenceView = null;
  const panel = document.getElementById('review-evidence');
  if (panel) { panel.replaceChildren(); panel.hidden = true; }
}
function renderReviewEvidence(value, savedReply) {
  evidenceView = value || null;
  evidenceReply = savedReply || '';
  paintReviewEvidence(false);
}
function paintReviewEvidence(unsaved) {
  if (!evidenceView) { resetReviewEvidence(); return; }
  const panel = evidencePanel();
  panel.hidden = false;
  const heading = evidenceNode('h4', 'Details to keep');
  heading.id = 'review-evidence-title';
  const note = evidenceNode('p', unsaved
    ? 'Unsaved edits. Save & recheck to refresh these detail checks.'
    : 'Compare these customer-reported details with your reply. A mention is a starting point for your review.', 'helper');
  note.id = 'review-evidence-note';
  note.setAttribute('role', 'status');
  const list = evidenceNode('ul', undefined, 'evidence-list');
  for (const item of evidenceView.checks || []) {
    const row = evidenceNode('li');
    const label = evidenceNode('strong', item.label);
    const status = unsaved ? 'Recheck after saving' : item.covered ? 'Mention detected' : 'Check this detail';
    row.append(label, evidenceNode('span', status,
      'evidence-status' + (!unsaved && !item.covered ? ' needs-detail' : '')));
    if (item.source && typeof item.source.quote === 'string') {
      const source = evidenceNode('details');
      source.append(evidenceNode('summary', (evidenceView.source_label || 'Customer review') + ' wording'),
        evidenceNode('blockquote', item.source.quote, 'preserve'));
      row.append(source);
    }
    list.append(row);
  }
  if (!list.children.length) list.append(evidenceNode('li', 'No familiar detail was identified. Read the complete review yourself.'));
  const warnings = (evidenceView.brief && evidenceView.brief.warnings) || [];
  panel.replaceChildren(heading, note, list,
    ...warnings.map(w => evidenceNode('p', w, 'evidence-warning')),
    evidenceNode('p', 'These English pattern checks can miss meaning or paraphrases. Customer wording does not authorize refunds or business actions.', 'helper'));
}
document.getElementById('reply-editor').addEventListener('input', () => {
  if (evidenceView) paintReviewEvidence(document.getElementById('reply-editor').value !== evidenceReply);
});
