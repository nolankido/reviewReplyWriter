# Audit reliability candidate: staged patch, not integrated application source

The original judge audit is preserved on main at
`docs/audits/2026-10-13/JUDGE_AUDIT_AND_ROADMAP.md`.

A substantial remediation was implemented and tested in a separate working copy.
It has 323 passing deterministic tests (281 baseline plus 42 additions), the
unchanged original 23 probes were rerun, and the unchanged 30-case template set
retains 29 drafts and one blocked oversized policy with no execution errors.

## Important delivery status

The revised application files have NOT yet replaced the application on this
branch or main. This directory preserves their exact reconstructible patch.
GitHub Actions run 38515514513 and its retry failed before any steps started.
No job log exists through the connected API. The underlying reason is not
established, and Windows/Chromium verification is not claimed.

The one-time write workflow has been removed to prevent unattended application
later. Do not merge this transport branch as though it is an integrated release.
The complete ready-to-run candidate source and tests are also supplied as the
conversation attachment `Review_Reply_Writer_Audit_Reliability_Candidate.zip`.

## Candidate scope

- Shared source-linked review interpretation instead of disagreeing substring
  extractors; fixes ordinary waiter and duplicate-billing cases.
- Conservative pre-generation manual routing for possible health, harassment,
  threats, privacy and legal allegations, including sensitive original threads.
- Targeted compensation/operational-claim patterns and a narrow feel-free idiom
  exception. Unknown paraphrases still need a human read.
- One checked Ollama adapter for CLI/browser/batch/follow-ups/evaluation.
- No mandatory filler or invitation to return; source details and manual reasons
  visible in the UI; higher-contrast placeholders.
- Historical model reports remain untouched and do not qualify as current-source
  evidence. No live inference or operator feedback was fabricated.

## Exact reconstruction for a maintainer

Use an isolated checkout of this branch with no local edits. Inspect
`.development/apply_audit.py` before running it. It reads only the pinned data
pieces, validates their complete SHA-256, validates every before/after file hash,
and prepares all output bytes before writing. It does not download or execute
code from the data payload, contact an external service, change main, or commit.

```text
python .development/apply_audit.py
```

Then replace `.github/workflows/tests.yml` with `.development/final-tests.yml`
and run `python -m unittest -v`, `python check_submission.py`, and the browser
scripts in an environment where Chromium is supported. Retain the findings and
finish normal review before integrating the source into main. Remove this
transport directory and its temporary `.gitattributes` exception after applying.

Compressed payload SHA-256:
`2dcee139c8c6195b1db7887c022398a641e8ecb007f767ac3e2db3f5752460c9`

Expected clean candidate Git tree, including the final test workflow and original
audit but excluding this directory and its attributes exception:
`238705275544094afdbb6e9b1f453e7d3f662dc0`.

The audit, original scripts/results/checksums, new probes and local before/after
logs are part of the candidate. They are diagnostic evidence, not a claim of
best-in-class performance or independent customer validation.
