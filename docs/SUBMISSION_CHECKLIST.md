# Submission checklist: Week 2 Side Hustle

Checked October 14, 2026. This document separates contest requirements from this
project's stronger internal evidence checks. No entry has been published by this
workflow and no repository visibility setting has been changed.

## Official entry requirements

Source: https://dev.to/page/hacktoberfest-week2-2026-10-12-contest-rules
Challenge and template: https://dev.to/challenges/hacktoberfest-week2-2026-10-12

The entry period is October 12 at noon PDT through October 18 at 11:59 PM PDT,
which is October 12 at 9 AM through October 18 at 8:59 PM in Hawaii. Publish one
DEV entry using the provided template and tags. Include a new project developed
within the entry period, a deployed app or video link, code-repository access,
why open innovation matters, and a plausible paying customer for the Side
Hustle theme. Name Best Use of Gemma for the meaningful Gemma integration.
Writing quality has the greatest judging weight. A real first user is valuable
but optional; do not invent one. GitHub commits alone are not an entry.

## 1. Resolve eligibility and code access first

These are the verified provenance facts as of October 14. They support review;
they do not establish eligibility or authorize publishing private material.

| Observation | Evidence and limit |
| --- | --- |
| Repository created October 13 at 22:20:14 UTC | GitHub repository metadata. This is October 13 at 12:20:14 PM Hawaii time, within the entry period. Repository creation is not the original development start. |
| Supplied archive imported October 13 at 22:27:51 UTC | Commit [`0bb612080f8d35ccbb70c0197845aa8b6f40a679`](https://github.com/nolankido/reviewReplyWriter/commit/0bb612080f8d35ccbb70c0197845aa8b6f40a679). All 17 supplied file contents were compared with the Git blobs and match exactly. The extra import-tree file is `.gitattributes`. |
| Archive stored dates span October 12 at 19:28:14 through October 13 at 11:02:06 | ZIP timestamps have no timezone and can be rewritten. They do not prove when development began. |
| Original archive fingerprint | SHA-256 `d1df2dc327c6266b9e514454289e6cd85620f29c486e284ced582fa21c21369c`. The original archive remains private and unchanged. |
| Current repository is private and MIT licensed | Judge access is unconfirmed. The application license does not replace Gemma's separate terms. |
| Current tracked-path review | The inspected main at `568b8b8d60accff66cf318b8203311889422d7da` has 144 tracked files, no `.rrw/`, `replies/`, `evidence/`, local backup or environment paths, and no Actions workflow files. This is a path inventory, not a secret scan or a full history/artifact audit. |

Nolan must confirm the original work began on or after **October 12, 2026 at
9 AM Hawaii time**, including work before the archive was uploaded. Review the
original coding session or other contemporaneous record. If it began earlier,
do not mark eligibility confirmed or assume later improvements fix that issue.
Resolve uncertainty with the organizers before representing the entry as eligible.

For judge access, the simplest route is the existing repository's public URL
after a deliberate privacy review. Inspect current files, earlier commits,
branches, PRs and historical Actions logs/artifacts first. The imported article
contains superseded firsthand and privacy claims; it is historical material,
not evidence for the current application. Check the original sample profiles
and examples as well. Do not publish owner workspaces, customer identities,
private policies, notes, backups or session links.

Only Nolan should decide to change visibility. GitHub documents that making a
repository public also exposes Actions history and logs:
https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/managing-repository-settings/setting-repository-visibility

If keeping the repository private, first establish an organizer-approved access
route and test the intended judge account. A private URL or a working packet
alone does not show that judges can inspect the code. No collaborators have
been invited and no repository setting has been changed by this workflow.

Leave `development_window_confirmed` and `repository_accessible_to_judges` false
until those facts have actually been checked. The remaining preparation can
continue while this decision is outstanding; final publication cannot claim
these items complete.

## 2. Run current Gemma and assess the actual replies

Use the final source copy on the intended computer. Pause source changes until
the run, assessments and recording are complete. On Windows, open a terminal in
the extracted project folder:

```powershell
py -3 rrw_verify.py
py -3 rrw_setup.py --report evidence/owner-setup.json
```

The first command needs Node for its development scripts. It is a developer
handoff check, not an application runtime requirement. If Ollama or the model is
missing, follow [Local setup](LOCAL_SETUP.md); the tools do not install or
configure them for you. After the intended local runtime is ready, close any
running app instance and run:

```powershell
py -3 rrw_setup.py --verify-gemma
py -3 rrw_setup.py --launch
```

Keep the terminal's evaluation identifier. Open **Quality Lab**, select that
saved evaluation and read all three cases, their exact owner policy, replies,
raw attempts and available receipts. For each result, choose **Usable as a
draft**, **Needs editing** or **Unusable / no draft produced**, record only
problems you actually see, confirm that you read the exact result and save the
assessment. Check missed details, invented facts, unapproved promises, tone and
generic filler. Do not select a favorable judgment merely to pass a gate.
Export both JSON and the readable report. Preserve retries and fallbacks.

An install check is not inference. A completed API receipt is not a quality
judgment. Nolan's assessments are builder assessments, not operator feedback or
independent endorsements. A failure or a required edit is a valid result.

The October 14 assistant setup check passed Python, installation, storage,
loopback and the template probe. Its model state was unavailable; no Gemma test
was requested and no new model evidence was produced. The bundled historical
report still reports different drafting sources and missing human assessments.
This item remains unfinished until the target-machine work above is performed.

## 3. Record the duplicate-billing demonstration

Use the actual app on that computer with fictional data. These are planned
beats, not a recorded runtime or measured generation speed. Target about two
minutes; allow the real generation to finish and disclose any cuts.

| Target beat | Screen action | Point to explain |
| --- | --- | --- |
| 0:00 to 0:15 | Open Draft workspace and choose **Duplicate billing**. Show the review and blank owner-policy fields. | The customer praised the coffee, reported being charged twice and received no answer about the bill. No refund is authorized. |
| 0:15 to 0:50 | Select local Gemma and generate once. Keep the actual engine label visible. | A template or fallback is not Gemma output. If inference fails, show the actual result rather than narrating a successful call. |
| 0:50 to 1:10 | Read the reply beside **Details to keep**; expand the source wording for billing and the unanswered question. | The reply must retain the complaint. Mention checks help inspection; they do not prove understanding. |
| 1:10 to 1:30 | Append `We will give you a full refund.` and choose **Save & recheck**. | Show **Needs changes** and disabled approval/copy controls because the owner did not authorize a refund. |
| 1:30 to 1:50 | Remove that added sentence, save and recheck. Read the saved reply, then explicitly approve and copy it. | Approval belongs to this exact saved text. Nothing is posted to a review platform. |
| 1:50 to 2:00 | Show the current Quality Lab run and distinguish the builder's assessments from customer evidence. | Raw failures and model receipts remain inspectable; this is supervised drafting. |

If the model draft needs another edit, make it visibly and explain it. Never
present the corrected wording as untouched Gemma output. If clipboard permission
is denied, show the read-only approved-copy fallback and use manual copying.

The optional `scripts/record_demo.py --output evidence/billing-demo --live`
records an automated walkthrough only in an existing Playwright/Chromium runtime.
Choose a new output directory; an existing recording folder is refused.
It uses an isolated fictional workspace; its Quality Lab screen does not contain
the owner's separately assessed run. Show that run yourself in the final video.
Without `--live`, it records templates and labels them as no AI. It never creates
a genuine human assessment. No Chromium binary is available in the assistant
workspace; no current browser recording is claimed here.

Watch the result, remove any session link or private information, then supply a
stable hosted URL and test it signed out. A local recording, working packet or
private Actions artifact is not the required accessible link. No upload or
hosting change is performed by these instructions.

## 4. Finish the article around the same case

Review [POST_FINAL.md](../POST_FINAL.md). Keep its duplicate-billing example,
specific customer, owner-authority distinction, Gemma's role and evidence limits.
Replace the demo marker only with the exact watched and access-checked URL.
Reconcile [the historical results page](REPLY_QUALITY_RESULTS.md) with any new
run without replacing the original JSON receipts or presenting old timings as
current performance. Review the code link and all technical/firsthand claims.

Use **Submission Desk** to select the assessed run and prepare the article and
working judge packet. Confirm only facts already verified. Changing supporting
documents requires a fresh claim review. Export remains unpublished; deliberate
publication through the official DEV template is still required.

## 5. Observe one consenting operator if practical

Use [Operator trial](OPERATOR_TRIAL.md), including its private observation sheet.
Ask for permission first, then observe one positive, negative and mixed task.
Record the actual setup, edits, confusing steps and adoption answer. A template
trial is workflow evidence only. Builder judgments, scripted demonstration
clicks and fictional regression fixtures are not operator results. A first-user
story is optional; omit it if no session occurs.

## Internal release check

```powershell
py check_submission.py --release --evaluation .rrw/evaluations/ACTUAL_RUN_ID.json
```

Use the actual report path produced by the run. Complete
`docs/submission_evidence.json` only for facts you have really verified. A green
check does not submit the article or establish eligibility. Preserve missing
items as false instead of bypassing checks to make the status look complete.
