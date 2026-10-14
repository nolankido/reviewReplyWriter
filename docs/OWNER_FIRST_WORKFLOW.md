# Owner-first review workflow

## Purpose

Make the safe daily task obvious to a nontechnical operator: paste a review,
read the original alongside the draft, edit, confirm the details and policy,
approve the exact saved reply, then copy it for deliberate manual posting.

## Product improvements

- For high-stakes complaints, display a dedicated, visible manual-review
  screen instead of a generic API error. It shows the submitted text,
  factuality-neutral referral reasons and an edit-return action.
- Manual-only routing clears any older approved draft from the on-screen
  editor so its text cannot be mistaken for the newly submitted review.
  The old draft remains in the separately labeled saved library.
- The review and its saved owner policy appear alongside the draft on
  wide screens, with a stable stacked presentation at narrower widths.
- Draft, Read & Edit, Approve and Copy form a dynamic four-stage guide.
  Editing disarms the approval controls until saving and rechecking.
- The displayed manual review text is injected with textContent, not HTML.
  The client uses the server's 422 findings and does not infer eligibility
  to publish merely because text looks plausible.

## Evidence and limits

On the isolated reconstructed branch, 297 Python tests passed, including
a real local HTTP request asserting 422 with a manual referral and no new
saved draft. JavaScript syntax was checked with Node, HTML element and stage
IDs were validated, and CSS parsed without errors. These are engineering
checks, not human usability outcomes.

The Chromium automation environment blocks 127.0.0.1 by administrator policy,
so actual interactive Chromium verification did not run in this environment.
No change to the application's loopback-only security model was made to
bypass that restriction. Cross-platform accessibility, operator task times,
real model performance and contest readiness remain to be verified.

## Manual browser trial

Start `py rrw_web.py` in a user-controlled environment. Use the fictional
one-star waiter and duplicate-billing reviews to generate and edit a draft,
then approve and copy only after checking. Next enter a fictional five-star
food-poisoning complaint and confirm the dedicated manual-only screen appears.
There must be no newly generated draft or enabled export path for that
complaint. Try the same flow at desktop and 390px mobile width.
