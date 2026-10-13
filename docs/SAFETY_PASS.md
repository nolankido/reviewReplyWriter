# Owner-authorization development pass

Date: October 13, 2026. Baseline: `1c76355c608901ac6cb51186db41536899d50f0e`.

## Result

The baseline had 81 passing tests but allowed unauthorized compensation in
model prompts and default templates. The updated suite has 127 passing tests,
including 46 additional regression tests. Existing tests that required an
unsolicited offer were deliberately revised to enforce the new policy instead.

This is a safer supervised drafting prototype, not a production-ready autonomous
reply system. Policy detection is conservative English-language pattern matching.
It cannot prove factual accuracy or catch every paraphrase. Owner statements are
trusted inputs whose truth the application does not independently establish.

## Implemented boundaries

1. **Explicit owner authorization.** `--offer` authorizes exact wording only.
   The repeatable `--approved-action` flag allows exact owner-confirmed actions
   or contact instructions. Customer reviews, previous replies and learned voice
   samples are never authorization. Approved statements must stand alone and
   cannot be extended, repeated or silently enlarged. No default monetary offers
   or invented completed actions remain in the fallback templates.
2. **Validated final output.** Model candidates, coached retries, direct
   templates, CLI output, batch rows, follow-ups, rerolls and the tour check the
   final draft. A blocked output is not printed or saved as a ready generated
   reply. Library callers may save an imported draft, but its findings and
   blocked status are recorded and triage will not approve it.
3. **No automatic follow-up escalation.** An already used offer does not imply
   permission to promise a refund or an owner intervention. The fallback
   acknowledges unresolved concerns without inventing a stronger commitment.
4. **Approval integrity.** Triage rechecks current content and binds approval to
   a SHA-256 fingerprint and safety version. Edits invalidate approval. Changes
   during review require redisplay. Legacy unbound approvals return to pending.
5. **Owner-policy isolation.** Batch defaults are not applied across business
   identities. The CLI rejects rebinding an existing profile to another business.
   Explicit row-level CSV offers remain trusted owner data and must be reviewed
   before import; do not feed an unreviewed external CSV into this policy surface.
6. **Local-state and input reliability.** Personal profiles write to ignored
   `.rrw/profiles.json`, with the tracked sample profiles as an initial read
   fallback. Profile, gap-ledger and triage writes are atomic. Corrupt state is
   reported rather than silently replaced. CSV headers, ratings, blank reviews,
   oversized inputs and incompatible modes receive validation. Numeric
   grounding uses exact tokens rather than substring matches.
7. **Honest submission checks.** Development verification is separate from
   `check_submission.py --release`. Release checks require explicit demo,
   accessibility, development-window and firsthand-evidence attestations.
   Current missing evidence causes an intentional nonzero exit. The original
   article and historical Gemma-labelled samples are preserved, while the new
   safety gallery is explicitly labelled as template output.

## Verification performed

| Check | Result in local Python 3.13 environment |
| --- | --- |
| Baseline suite | 81 tests passed before edits |
| Revised suite | 127 tests passed |
| Current safety gallery and development checker | Passed |
| Template matrix | Positive, mixed and negative inputs across all 4 kinds, 3 tones and 5 platform targets passed as subcases |
| Unauthorized policy phrases | Compensation, actions and instructions blocked for the targeted adversarial phrases |
| Model paths | Controlled caller tests cover rejection, coached retry and checked fallback |
| Final-output barriers | Deliberately faulty template implementations blocked by CLI, batch, follow-up, reroll and tour boundaries |
| Approval changes | Edited and legacy drafts return to pending; invalid drafts cannot be approved |
| Release checker | Intentionally blocked by missing real demonstration and owner confirmations |
| Live Gemma inference | Not run: no local Ollama service available |
| Real owner usability and commercial validation | Not performed |

The GitHub test matrix has been expanded to Ubuntu and Windows on Python 3.10
and 3.13. Its results must be read from the actual workflow run; configuration
alone is not evidence that those runs passed. A separate read-only workflow
retains the tested source snapshot and deterministic test log for seven days.

## Reproduce

```powershell
py -m unittest -v
py check_submission.py
py review_reply.py "Cold coffee and a long wait. Disappointing." --business "Demo Cafe" --stars 2 --offline --platform google
py check_submission.py --release
```

The final command should currently fail with a clear list of outstanding
submission evidence. Do not change booleans to true merely to obtain a green
result. They are owner attestations, not automatic verification.

## Remaining limitations and next pass

The sentiment and factual-detail classifiers remain heuristic. Sarcasm, negation,
star/text disagreements, unfamiliar names and paraphrased promises can still
cause errors. The strict policy layer can also reject harmless discussion of a
refund or a repair. These tradeoffs should be measured on a representative set
of real model outputs, not hidden by reducing tests until they pass.

This remains a single-owner terminal workflow. State writes are atomic, but
concurrent processes do not have database-style transaction isolation. Approval
protects the saved draft and policy snapshot, not the truth of owner-supplied
statements. A local user able to rewrite approval JSON is outside the threat
model. The program still cannot audit every Ollama alias or network setting.

Next priority: a small local graphical interface over the existing checked
pipeline, with owner-policy setup, editable drafts, visible findings, explicit
approval and copy controls. Then record real Gemma runs, measure editing effort
and failure rates, obtain owner feedback and finish the contest demonstration.
No public visibility change, contest registration or submission is part of this
code pass.
