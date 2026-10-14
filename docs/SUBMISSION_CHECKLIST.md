# Submission checklist: Week 2 Side Hustle

Checked October 13, 2026. This document separates contest requirements from this
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

## What Nolan still needs to decide or confirm

1. Verify when original development began, including the code imported from the
   first archive. A newly created repository alone does not establish this.
2. Inspect repository files and history, then deliberately make code accessible
   to judges. Do not publish personal reviews, policies or private source files.
3. Watch the recorded demo and upload it to a public or unlisted video location
   accessible without a judge joining this private repository. Test the link
   signed out. A local artifact or Actions download is not a public demo URL.
4. Run/review a current Gemma smoke evaluation and record honest assessments.
   This is our evidence policy, not an extra official contest requirement.
5. Read POST_FINAL.md, replace the actual demo URL, verify technical and
   firsthand statements, and publish it through the official DEV template.

## Suggested two-minute demonstration

Explain the problem in one sentence: a fluent reply can invent a business
commitment. Show a fictional complaint, the owner's exact permitted policy,
and the actual Gemma generation label. Point out the retained wait duration.
Deliberately edit in an unauthorized refund and show the blocked approval.
Remove it, recheck and demonstrate the approval/copy workflow. End with Quality
Lab's raw evidence and the explicit statement that this is not autonomous
customer service. Do not describe demonstration clicks as customer validation.

## Internal release check

```powershell
py check_submission.py --release --evaluation .rrw/evaluations/ACTUAL_RUN_ID.json
```

Use the actual report path produced by the run. Complete
`docs/submission_evidence.json` only for facts you have really verified. A green
check does not submit the article or establish eligibility. Preserve missing
items as false instead of bypassing checks to make the status look complete.
