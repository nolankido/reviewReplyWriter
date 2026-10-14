# Review Reply Writer

Local-model review drafts, explicit owner authorization, and human approval.
Now includes a local browser workspace alongside the existing Python CLI.
Nothing is posted to review platforms automatically.

## Review with the owner's judgment

The editor shows the original review and its saved owner policy alongside the
reply on wide screens, with a Draft, Read & Edit, Approve, Copy guide. Serious
reviews open a dedicated personal-handling screen and clear any older reply
from the active editor. Private inbox notes can track personal handling without
generating or approving a public reply.

Complete concise replies no longer need filler or an invitation to return.
Maximum length, source-detail and authorization checks remain enforced. Warm
templates use a neutral greeting; owners can choose their own wording.
See [Owner workflow](docs/OWNER_FIRST_WORKFLOW.md).

## Protect pending work

Changed review inputs and business settings now get a warning before an example,
profile or saved draft replaces them. **Keep a private working copy for recovery**
explicitly saves form inputs and unsaved reply edits on this computer. Recovery
leaves policy confirmation unchecked and selects templates. Edits tied to a
changed or missing draft are shown for inspection instead of overwriting it.
Only one copy is kept, and it is excluded from judge packets.
See [Working copy recovery](docs/WORKING_COPY_RECOVERY.md).

Generation now keeps a private request receipt. If a connection is lost, use
**Check result**, then explicitly open the saved draft. Checking keeps the current
form intact. Repeating the same received request cannot start another generation.
Requests have browser deadlines; a timeout does not cancel the server. Blocked
browser session storage no longer prevents drafting from a current launcher link.
See [Connection and generation recovery](docs/CONNECTION_RECOVERY.md).

After a lost edit/approval response, **Check latest saved reply** compares the
current saved version without replacing your editor. **Keep my editor text**
retains further changes against the freshly checked revision; **Use checked saved
reply** asks before replacing different text. Neither action saves or approves a
reply, and recovered review/authorization checkboxes stay unchecked. A failed
library refresh no longer hides an acknowledged edit or approval.
See [Saved-change reconciliation](docs/SAVE_RECONCILIATION.md).

## Inspect edits and record review feedback

New browser drafts retain the starting reply for their current generation.
**Compare the starting draft with your saved reply** highlights removed and
added wording. **Use starting draft in editor** restores it for editing; saving,
rechecking and human approval still apply. Regeneration begins a new comparison.
Older drafts without a recorded baseline say so instead of reconstructing one.

The optional **Private review assessment** records the assessor's role, review
context, usefulness, reasons, notes and an optional observed review time.
Assessments become stale after draft edits or regeneration and stay separate
from posting approval. Exported counts exclude private notes and customer text,
separate operator/self/demo judgments, and count drafts rather than people.
See [Review feedback](docs/REVIEW_FEEDBACK.md) and [Operator trial](docs/OPERATOR_TRIAL.md).

## A review inbox for recurring work

Open **Review inbox** in the draft workspace. Load or paste a UTF-8 CSV for one
business, preview all rows, confirm the business and save the inbox. **Draft next
review** handles one ready row per click. Each resulting reply still needs its
own human review and approval before copying.

Use `review`, optional `stars` and optional `review_id` columns. Duplicates,
invalid rows and personal-handling referrals remain visible. The inbox keeps
its place across restarts and checks for an already saved draft after an
interrupted write. Owner offers and operational statements are excluded from
imports. The CLI's multi-business CSV format is separate.

See [Review inbox](docs/REVIEW_INBOX.md) and the downloadable fictional sample
in `web/inbox-sample.csv`.

## Keep the customer's actual details

The draft editor now shows **Details to keep**, with exact excerpts from the
saved review and mention checks for the saved reply. Unsaved edits make those
checks visibly stale until you save and recheck. Try the fictional **Duplicate
billing** example: the reply should retain both the reported double charge and
the unanswered question, while acknowledging the praise about the coffee.
Prompts, fallback drafts and detail checks share the same bounded interpretation.
These are English pattern checks, not proof that the reply understands the review.

See [the evidence and hackathon assessment](docs/REVIEW_EVIDENCE_PASS.md).

## High-risk review routing and checked local Gemma calls

Potential poisoning, allergy, harassment, threats, sensitive-data exposure and
legal allegations are now referred to a person before routine generation.
This intentionally conservative English-language routing may over-refer or miss
unrecognized wording. Saved drafts, approvals and copy requests are rechecked.
The CLI uses the browser's checked Ollama adapter, including response completion
and model identity. Billing and waiter complaints now have improved handling.
See [the reliability pass](docs/RELIABILITY_PASS_2026_10_13.md).

## Submission Desk and judge handoff

The browser now has a **Submission Desk** beside Draft workspace and Quality Lab.
Save the hosted demo link, record only confirmations you actually checked, and
export a DEV draft or a no-install judge packet. Extract the ZIP and open
`START_HERE.html` to inspect recorded evidence without Python or Ollama.
No publication, visibility change or automatic upload occurs. Private evaluations
are excluded unless you explicitly include and review them. Details and CLI video
packaging: [Submission Desk](docs/SUBMISSION_DESK.md).


## Quality Lab

The browser now includes **Quality Lab**, a separate evaluation workspace. Run
three fictional smoke scenarios or a 30-case stress set, one case per click.
It keeps model replies, retries, template fallbacks, blocked outputs and human
assessments separate. Results do not become customer drafts or posting approvals.

Start with templates to inspect the protocol. For real-model evidence, check
Gemma setup and explicitly select the installed model. Export the JSON evidence
and readable report after reviewing each result. Unreviewed quality remains
unknown, even when automatic checks pass. See [the Quality Lab guide](docs/QUALITY_LAB.md).

## Open the app

Requires Python 3.10 or newer. No extra runtime packages, framework installation,
account, API key, or paid hosting are needed to try the template workflow.

**Windows:** extract the complete ZIP into a writable folder, then double-click
`start_windows.bat`, or run:

```powershell
py -3 rrw_setup.py --launch
```

**macOS/Linux:** `python3 rrw_setup.py --launch`.

The setup launcher checks Python, application files, writable storage, the
loopback connection and a template reply before opening the app. It selects a
free port by default and allows templates when Ollama is unavailable. The
Windows launcher tries a supported `py -3` interpreter, then a supported
`python` interpreter. No software or models are installed automatically.

Open **Getting started** in the app to load a fictional example, check Gemma
installation and move to Quality Lab. [Setup and target-machine verification](docs/LOCAL_SETUP.md).

The launcher opens a session link on `127.0.0.1`. Keep the terminal open and
press Ctrl+C to stop. Do not share its link or expose the port. Use `--port 0`
when the default port is occupied; `--no-browser` prints the link without
opening a tab. `--data-dir PATH` selects a separate local workspace. The direct
`rrw_web.py` entry point remains available with its existing default port.

Start with a fictional example in **Template preview (no AI)**. Read the draft,
edit it, use **Save & recheck**, then confirm human review and approve. Only the
exact approved text can be copied or exported through the app. Edits clear
approval; stale tabs cannot overwrite or copy a changed draft.

The workspace includes saved business profiles, explicit policy confirmation,
first replies and follow-ups, a searchable/filterable draft library, generation
details, and approved-only clipboard/text export. It uses the same draft files
and approval records as the CLI. Its UI assets are local, with no external
fonts, scripts, analytics, or images.

[Full browser guide and security boundaries](docs/BROWSER_WORKSPACE.md)

## Use actual local Gemma

Install/start Ollama, download the model once, then select **Local Gemma 3 (4B)**
in the browser's drafting-engine control:

```powershell
ollama pull gemma3:4b
py -3 rrw_setup.py
py -3 rrw_setup.py --verify-gemma
py -3 rrw_setup.py --launch
```

The browser starts in template mode deliberately. Engine credits and generation
details distinguish real model calls, coached retries, and template fallbacks.
A connection badge now uses the same digest, downloaded-size, model-family and
cloud-metadata checks as Quality Lab. It only reports installation. The explicit
`--verify-gemma` command runs three fictional reviews and saves the evaluation
for human assessment in Quality Lab. Fallbacks, missing receipts, interruptions,
changed model identity, stale drafting sources and rubric flags cannot produce
a passed smoke test. Neither check is a network-privacy audit.

Use Ollama's local-only setting. The first model download needs internet access.
A loopback request does not by itself prove local inference: model aliases and
Ollama's independent server configuration remain outside the app's audit.
Configuration: https://docs.ollama.com/faq#how-do-i-disable-ollama-cloud-features

No fresh Gemma inference or real-business user study was performed in the browser
pass. Model integration tests use controlled stand-in responses, not real-model
quality or performance measurements.

## Owner policy is not customer text

The default reply does not promise refunds, replacements, free goods, repairs,
or staff action. Enter an offer or an approved action only when the business
owner has actually authorized it. Exact statements are checked separately from
review text, previous replies, or learned voice samples. One authorized offer
does not authorize a bigger refund or new redemption instructions.

These are conservative English-language pattern checks, not a factuality or
safety guarantee. They can miss paraphrases and reject harmless wording. Every
reply still needs a human read. The tool trusts owner statements; it does not
prove that a repair, refund, or other authorized claim is true.

[Safety design and earlier regression evidence](docs/SAFETY_PASS.md)

## CLI workflows remain available

```powershell
py review_reply.py "Cold coffee and a 25 minute wait. Disappointing." --business "Demo Cafe" --stars 2 --offline --platform google --save
py review_reply.py --triage
py review_reply.py --batch examples/batch-sample.csv --offline
```

Exact owner authorization:

```powershell
py review_reply.py "Cold coffee and a long wait." --business "Demo Cafe" --stars 2 --offer "a replacement coffee on your next visit" --offline
py review_reply.py "The coffee machine was broken." --business "Demo Cafe" --stars 2 --approved-action "We have repaired the coffee machine." --offline
```

`--approved-action` is repeatable. Only use the repair statement if it is true.
Use `--save-profile NAME` and `--profile NAME` for saved settings. Personal
profiles write to ignored `.rrw/profiles.json`. The CLI retains the tracked
`profiles.json` as an initial read fallback; the browser does not silently
import sample compensation policies. Audit any old personal data in that
tracked file before making the repository public.

`--followup --file update.txt --original original.txt --previous previous.txt`
keeps a review thread. `--learn-voice FILE --profile NAME` learns recurring
phrases from replies separated by `---`. `--choices 2` compares two passing
model candidates. `--tour` demonstrates the existing workflow. The browser
respects saved voice metadata for the same business. Multi-business batch import,
voice training and best-of-two controls remain CLI features. The new browser
inbox supports one business and uses the selected tone and sign-off, with no
automatic import of offers, actions or learned voice metadata.

CSV row-level offers are owner-controlled policy input. Do not import an
unreviewed third-party CSV as authorization. Different businesses do not inherit
one another's default commitments. Platform word ranges are application style
targets, not official service limits. Only their upper bounds are enforced;
minimum length and return invitations are editorial choices.

## Verification and submission

```powershell
py -m unittest -v
py check_submission.py
py check_submission.py --release
```

The deterministic suite includes workspace tests and real-loopback HTTP tests.
GitHub checks run on Ubuntu and Windows, Python 3.10 and 3.13. A separate Chromium
job exercises the browser workflow and retains screenshots/results. Read the
actual workflow conclusion, not just its configuration, for passing evidence.

Development checks do not prove model quality, eligibility, or contest readiness.
The separate `--release` check remains blocked until actual demo and owner
evidence are supplied in `docs/submission_evidence.json`. Those entries are
attestations, not independent external verification.

[POST_FINAL.md](POST_FINAL.md) is still unpublished. Current safety examples in
[examples/safety](examples/safety) are explicitly template-generated. Historical
model-labelled examples and the earlier article are retained for provenance,
not endorsed as current compliant drafts. No contest submission or repository
visibility change is performed by running the app.

Local state is plaintext, not encrypted. Use one writer at a time; external CLI
processes do not share the browser process lock. Do not host this prototype on
the public internet. MIT covers this source, not third-party model terms.

## Reply-quality update and submission

The current checker preserves detected complaint topics and explicit wait durations,
handles selected negation and rating conflicts, and distinguishes past regret from
completed-action claims. Fallbacks are shorter and more specific. This is still a
heuristic drafting aid, not autonomous customer service. Existing approvals need
a fresh review under the updated policy version.

See [the measured quality pass](docs/REPLY_QUALITY_PASS.md) and the
[submission checklist](docs/SUBMISSION_CHECKLIST.md). The earlier live smoke remains
historical evidence. Current-code evaluations and actual human assessments are
still required by the internal release check.
