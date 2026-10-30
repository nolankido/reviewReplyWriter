# Review Reply Writer

Local-model review drafts, explicit owner authorization, and human approval.
Now includes a local browser workspace alongside the existing Python CLI.
Nothing is posted to review platforms automatically.

The [Week 2 Side Hustle entry](https://dev.to/kidon/the-model-writes-the-review-reply-the-owner-keeps-the-promises-57a2)
was published on DEV on October 14, 2026, with the public code link and a labelled
historical Gemma video. Current-source Gemma results and human assessments remain
pending; publication does not mean the internal release evidence check passed.

## Published reproducible case study

The [public Review Reply Writer case study](https://nolankido.com/technology/local-ai-review-replies/) examines the recorded 30-case offline template evaluation separately from earlier three-case Gemma smoke tests. The [source-linked evidence report](docs/CASE_STUDY_EVIDENCE_2026_10_29.md) retains the measurements and caveats; an [AI-assisted case-by-case editorial audit](docs/CASE_STUDY_EDITORIAL_AUDIT_2026_10_30.md) examines all 30 archived outcomes and documents details the automatic checks did not flag. Neither is a human operator study, a safety certification, or a claim of business time savings.

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

Business-profile saves now return the saved settings and their revision before
refreshing the list. A failed list refresh cannot hide an acknowledged save.
After an uncertain save, **Check saved profiles** reads the latest private list
without replacing the current review/settings or restoring authorization. Further
profile saves wait for that check. [Profile-save recovery](docs/PROFILE_SAVES.md).
Choosing **New / unsaved business** keeps pending settings protected. Loading a
profile asks before replacing recovered settings and keeps the pending review.
Working-copy saves and discards require matching readback. After an uncertain
change, **Check saved copy** before another action; current form and reply text
stay in place. Earlier copies remain readable without automatic rewriting.

## Back up private review work

After saving pending work and closing the launcher, use `py rrw_backup.py create
--confirm-private` from the app folder. This writes a checked private archive to
`.rrw/backups/`. Backups contain customer text, owner policy and private notes;
they are not encrypted and must not be shared with judges or committed to Git.
Inspect an archive before relying on it. Recovery only writes to a new directory,
keeps the original workspace intact and clears posting approvals.
See [Private backup and recovery](docs/PRIVATE_BACKUP.md) for exact commands,
included files, limits and opening the recovered workspace.

Keyboard handoffs now wait until busy controls are enabled. Opening a draft moves
to its saved review/policy summary, while recovered reply edits move to the
editor. Cancelled replacement guards do not move focus or discard work. See
[Keyboard recovery handoffs](docs/KEYBOARD_HANDOFF.md) for scope and test limits.

Saved generation results explain connection failures, unaccepted responses and
rejected model replies separately. Templates stay labelled as not AI output.
Explicit help buttons open setup or Quality Lab without retrying, installing or
authorizing anything. See [Saved generation results](docs/GENERATION_RESULTS.md).

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
Assessment saves require matching readback. Failed or uncertain saves and
unreadable reloads keep typed notes pending; newer edits survive a known save.
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
Saved inbox progress stays visible after a failed library refresh. If a saved
reply cannot open, use its **Review draft** control later; generation is not
repeated automatically.

## Keep the customer's actual details

The draft editor now shows **Details to keep**, with exact excerpts from the
saved review and mention checks for the saved reply. Unsaved edits make those
checks visibly stale until you save and recheck. Try the fictional **Duplicate
billing** example: the reply should retain both the reported double charge and
the unanswered question, while acknowledging the praise about the coffee.
Prompts, fallback drafts and detail checks share the same bounded interpretation.
These are English pattern checks, not proof that the reply understands the review.

See [the evidence and hackathon assessment](docs/REVIEW_EVIDENCE_PASS.md).

Reported duplicate billing and response complaints now stay in the limited
checklist even after three earlier topics. Templates, model prompts, saved-reply
checks and source quotations use the same selection. The original requirements
remain, and any other detected complaints outside the checklist get a reminder
to read the full review. Existing approvals require fresh review under the new
check version. [Material complaint coverage](docs/MATERIAL_COMPLAINTS.md).
Unapproved business plans and team promises also block approval and approved
copy; exact owner statements remain required. [Planned-action checks](docs/PLANNED_ACTIONS.md).
Fractional waits such as 1.5 hours now retain the customer's exact decimal
spelling in templates and checks. [Fractional durations](docs/FRACTIONAL_DURATIONS.md).
Saved generations also keep their success notice when a separate library refresh
fails. [Generation acknowledgement](docs/GENERATION_ACKNOWLEDGEMENT.md).

## High-risk review routing and checked local Gemma calls

Potential poisoning, allergy, harassment, threats, sensitive-data exposure and
legal allegations are now referred to a person before routine generation.
This intentionally conservative English-language routing may over-refer or miss
unrecognized wording. Saved drafts, approvals and copy requests are rechecked.
The CLI uses the browser's checked Ollama adapter, including response completion
and model identity. Billing and waiter complaints now have improved handling.
See [the reliability pass](docs/RELIABILITY_PASS_2026_10_13.md).

## Submission Desk and judge handoff

For the five remaining entry tasks, follow the ordered
[submission checklist](docs/SUBMISSION_CHECKLIST.md): eligibility/access, a current
Gemma assessment, the duplicate-billing demo, article review and an optional
operator trial. Historical model receipts are not current-source verification.

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

An uncertain case or assessment can be checked read-only before explicitly loading
its saved checkpoint. Pending notes are preserved during checking, active cases
cannot be mistaken for finished evidence, and no case is retried automatically.
See [Quality Lab request recovery](docs/QUALITY_REQUEST_RECOVERY.md).

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

If automatic clipboard access fails, a separate read-only box shows the exact
server-checked approved reply for manual selection. Editing or opening a draft
clears that box; the live editor is never selected by a delayed copy callback.
[Approved-copy fallback](docs/APPROVED_COPY.md).

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
py rrw_verify.py
```

One command runs the existing development suite, real launcher/backup HTTP
workflows and nine Node checks, then saves an explicit local receipt under
ignored `.rrw/verification/`. Missing tools and changed source cannot claim a
complete pass. Browser checks require an already installed development runtime
and an explicit `--browser`; no tools or models are installed. Receipts exclude
private state and raw logs. [Commands, scope and exit codes](docs/LOCAL_VERIFICATION.md).

Individual development and release checks remain available:

```powershell
py -m unittest -v
py check_submission.py
py check_submission.py --release
```

The deterministic suite includes workspace tests and real-loopback HTTP tests.
GitHub Actions workflows were removed at the owner's request on October 14,
2026. No push, pull-request, scheduled or manual Actions workflow is configured
on current main. Verification remains available locally; see
[local verification](docs/LOCAL_VERIFICATION.md). Earlier workflow definitions
and historical results in Git history do not establish current platform evidence.

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
