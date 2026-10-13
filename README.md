# Review Reply Writer

Local-model review drafts with explicit owner authorization and human approval.
Python 3.10 or newer. Standard-library-only command-line application.
Nothing is posted to review platforms automatically.

## Current status

The owner-policy pass adds conservative commitment checks, validated fallbacks,
content-bound approvals and stricter input handling. It is still a prototype,
not an autonomous customer-service system or a guarantee of factual accuracy.
Read [the safety design and evidence](docs/SAFETY_PASS.md) before using real reviews.

## Start without installing a model

```powershell
py -m unittest -v
py check_submission.py
py review_reply.py "Cold coffee and a 25 minute wait. Disappointing." --business "Demo Cafe" --kind cafe --stars 2 --offline --platform google
```

On macOS/Linux, use `python3` instead of `py`. Offline mode uses conservative
fixed templates. No model is required to exercise the policy and approval flow.
Tone customization is primarily supplied by the model; fallbacks deliberately
favor neutral wording over creative or playful language.

## Use local Gemma

Install and start Ollama, download the model once, then run:

```powershell
ollama pull gemma3:4b
py review_reply.py --doctor
py review_reply.py "Cold coffee and a 25 minute wait. Disappointing." --business "Demo Cafe" --kind cafe --stars 2 --platform google --save
py review_reply.py --triage
```

The application calls the Ollama server on localhost. This alone does not prove
inference is local: arbitrary model aliases and the server configuration remain
outside this application's audit. Use the downloaded `gemma3:4b` model and
Ollama's local-only setting. The initial model download requires a network
connection. Do not claim that the application verifies zero network traffic.
Official configuration: <https://docs.ollama.com/faq#how-do-i-disable-ollama-cloud-features>.

This development pass did not run live Gemma inference. Model-path tests use
controlled stand-in callers, clearly distinguished from real model evaluation.

## Owner authorization is explicit

Without a configured offer, neither the model nor a fallback is asked to promise
refunds, replacements or free products. An apology and acknowledgment are valid.
The program never derives authorization from the review, previous reply or voice
samples. Configure a real policy only when you are authorized to do so:

```powershell
py review_reply.py "Cold coffee and a long wait." --business "Demo Cafe" --stars 2 --offer "a replacement coffee on your next visit" --offline
```

The offer must appear as an exact standalone sentence or line, without added
conditions, larger amounts or invented redemption instructions. One authorized
offer does not permit an extra refund. Previously used offers do not authorize
escalation in follow-ups.

Owner-confirmed actions and contact instructions use a repeatable flag:

```powershell
py review_reply.py "The coffee machine was broken." --business "Demo Cafe" --stars 2 --approved-action "We have repaired the coffee machine." --offline
```

Only supply that statement if the owner actually confirmed it. The program does
not verify the owner's claim. `--approved-action` grants permission for exact
wording, not a general license to invent related facts. Policy checks are
English-language heuristics, so false positives and missed paraphrases remain
possible. Human approval is mandatory.

## Profiles, batches and follow-ups

`--save-profile NAME` saves business, offer, approved actions, tone and sign-off.
`--profile NAME` reuses them. Personal profiles now write to ignored
`.rrw/profiles.json`, never the tracked `profiles.json`. The latter contains demo
profiles and is used as an initial read fallback. Demo offers are not real
business authorization. Existing root-level profiles are not deleted or
rewritten automatically; review their contents before making the repository public.

```powershell
py review_reply.py --batch examples/batch-sample.csv --offline
py review_reply.py --triage
py review_reply.py --followup --file update.txt --original original.txt --previous previous.txt --profile mybusiness
```

CSV requires a unique `review` header. Supported fields include `business`,
`kind`, `tone`, `stars`, `platform`, `offer` and `signoff`. Row-level offers are
owner-controlled policy input; never treat an unreviewed third-party CSV as
trusted policy. One business's default offer, actions, sign-off and voice are
not inherited by a different business's row. Bad rows are reported as blocked;
valid rows continue. A CLI batch with blocked rows exits nonzero.

Every output path checks its final draft, including model retries, offline
fallbacks, batches, follow-ups and rerolls. A policy or length failure blocks
that output instead of silently truncating owner terms. Platform word ranges
are application style targets, not official service limits.

Approval is bound to a SHA-256 fingerprint of the saved draft and its policy
context. Editing or rerolling the file, or changing the safety-version marker,
invalidates approval. Legacy approvals without a fingerprint return to pending.
Stored drafts with unresolved findings cannot be approved through triage.
JSON state writes are atomic; corrupt state is reported rather than overwritten.
This is a single-owner local workflow, not a concurrent multi-user database.

## Other existing tools

`--learn-voice FILE --profile NAME` extracts recurring phrases from previous
replies separated by `---`. Voice samples are not authorization.
`--choices 2` compares two valid model candidates for topic coverage.
`--tour` demonstrates the workflow. `--seed` remains accepted for compatibility;
the safety fallback is intentionally deterministic.

## Verification and submission

```powershell
py -m unittest -v
py check_submission.py
py check_submission.py --release
```

Development checks cover tests and the explicitly template-generated safety
gallery. They do not prove live model quality, eligibility or contest readiness.
`--release` also checks `docs/submission_evidence.json`, post links, required
sections and unresolved markers. It intentionally fails until real demo and
owner-verification evidence have been added. Those fields are attestations,
not independent verification by the checker.

Current examples: [examples/safety](examples/safety). Historical model-labelled
examples are retained for provenance, not endorsed as current compliant drafts.
[POST_FINAL.md](POST_FINAL.md) is an unpublished draft. The previous article is
archived separately because its guarantees and examples no longer describe the
current implementation. No contest submission or visibility change was performed.

MIT license covers this source code, not third-party model weights or terms.
