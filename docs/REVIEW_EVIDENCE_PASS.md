# Review evidence and hackathon assessment

Implemented October 13, 2026, Hawaii time, from main at
`e1ab0b0ee0c6dd4fb663d20bf293baeedf7b47eb`.

## What will matter to the judges

The official [Week 2 Side Hustle challenge](https://dev.to/challenges/hacktoberfest-week2-2026-10-12)
weights writing quality most heavily. It asks for a specific product someone
would pay for, a demonstration and an explanation of the value of open
innovation. A first user is valuable, but optional. The deadline is October 18,
2026, at 8:59 PM Hawaii time.

The project has useful technical foundations: actual historical Gemma receipts,
explicit owner authorization, checked fallbacks and approval tied to saved
content. Its competitive weakness is still the gap between engineering evidence
and evidence that a real operator benefits enough to adopt or pay for it.
Another generation feature would not resolve that gap by itself.

| Judging area | Assessment and action |
| --- | --- |
| Writing quality | Revised the unpublished article around one fictional cafe case, a concrete product decision and two inspectable engineering lessons. Consolidated limitations instead of making them the whole story. |
| Theme relevance | Narrowed the proposed first buyer to independent cafe and small hospitality operators. Paid installation, policy setup and support remain a hypothesis until an operator tests them. |
| Creativity | Made the authorization idea visible alongside customer-source evidence. Neither local inference nor an approval button is unique on its own. |
| Technical execution | Improved duplicate-charge fidelity, unanswered-question handling, exact source excerpts and stale-edit behavior. Existing authorization and serious-review routing are retained. |
| Gemma category | Actual Gemma is already part of the application. Historical smoke receipts remain unchanged; fresh inference on this changed version is still required to support a current-model claim. |

## Implemented behavior

- `review_quality.analyze` returns topic polarity, exact original clause offsets
  and quotations, reported wait durations, recognized duplicate-billing facts,
  a source SHA-256 and an interpretation version. The source is not normalized
  before assigning offsets.
- Prompts, final detail checks, fallbacks, browser coverage and evaluation
  records use this shared analysis. It remains a bounded English lexical
  interpretation, not a semantic parser.
- A generic billing apology no longer satisfies an explicitly reported double
  charge. “Twice as much” and selected negations do not become duplicate charges.
- Unanswered questions have their own topic and are prioritized over a generic
  staff label when the three-topic reply budget fills up. Existing wait-duration
  and mixed-review praise checks remain in place.
- The editor's **Details to keep** panel links a detected topic to the customer's
  exact wording. It says **Mention detected**, not “verified” or “safe.” Unsaved
  edits replace those statuses with **Recheck after saving**.
- Follow-up evidence concerns the current customer update. The original thread
  remains available separately, and serious original allegations still route to
  manual handling through the existing engine.
- The new fictional **Duplicate billing** example demonstrates a mixed review,
  a reported double charge and an ignored question without authorizing a refund.
- Detail evidence is covered by each Quality Lab result fingerprint. Original
  historical reports are untouched. The policy version is bumped so older
  approvals need a new human review.

The browser evidence code and CSS are separate local assets. This pass leaves
PR #9's pending owner-workflow changes independent and does not integrate the
binary reconstruction candidate in PR #7.

## Verification performed

- Baseline: 294 deterministic Python tests passed from the exact main source.
- Final: **312 tests passed**, including 18 new regression methods in
  `test_review_evidence.py`.
- New counterexamples were run before implementation. They exposed the generic
  billing acceptance, missing question topic, absent source spans and missing
  workspace coverage.
- Real local HTTP checks verify source quotations, refusal to copy an unapproved
  reply, rejection of a missing human-review confirmation and asset delivery.
- Development submission checker, JavaScript syntax checks and diff whitespace
  checks passed.
- The unchanged 30-case fictional template set produced **29 templates, one
  blocked oversized policy, zero execution errors and zero limited rubric
  flags**. There were **zero model calls and zero human assessments**.
  The complete report is
  [source-evidence-template-2026-10-14.json](../examples/evaluation/source-evidence-template-2026-10-14.json).
  Its drafting-source fingerprints match this pass.

The browser smoke script now exercises source quotations and stale evidence on
unsaved edits. It was **not executed in Chromium in this environment**: no
Chromium binary was installed, and the ordinary browser download failed with
invalid/truncated archive errors. JavaScript syntax and live HTTP checks do not
verify visual layout, clipboard behavior or interaction in a real browser.
Windows execution was not performed. Ollama was unavailable, so no fresh Gemma
quality or latency measurement is claimed.

## Highest-value work before submission

1. Run the current code with actual Gemma on the target machine, inspect its
   outputs and complete genuine Quality Lab assessments. Keep every failure and
   fallback. Record the final UI in its current form, with truthful engine labels.
2. Observe a consenting cafe or small hospitality operator using the product.
   Use the existing operator-trial protocol, record required edits and total
   handling time, then ask about adoption and willingness to pay. A polite
   reaction is not a customer or a purchase.
3. Provide judge-accessible code and a stable demo URL, verify links signed out,
   confirm the original development window and review the article against the
   official template. Public access and submission are still unfinished.
4. Replace the article's publication markers with the real links and measured
   results. Keep `published: false` until deliberate author publication.

For a current browser check in an environment with Chromium available:

```powershell
py -m unittest -q
py check_submission.py
py scripts/browser_smoke.py --screenshots evidence/browser
py scripts/quality_browser_smoke.py --screenshots evidence/browser
py scripts/submission_browser_smoke.py --screenshots evidence/browser
```

Those scripts require the optional Playwright test dependency documented in the
repository. App users do not need Playwright.

These improvements make the product easier to inspect and give the entry a more
concrete demonstration. They do not establish customer demand, comparative
quality, contest eligibility or a likelihood of winning.
