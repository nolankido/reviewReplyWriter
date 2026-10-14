# Submission Desk and no-install judge packet

The original pass connected the existing demo, model evidence and article to
the remaining handoff steps. Later owner-workflow/engine changes make the bundled
Gemma receipts historical. The desk checks that status from current source hashes.
No new model inference or contest submission is implied by export or by the
supporting-document freshness repair.

## In the browser

Launch `py rrw_web.py`, then choose **Submission Desk**.

Save a stable hosted demo link first. Watch it and test it signed out, then record
that confirmation. Replacing the URL clears its access confirmation on the server
as well as in the browser. The repository link is fixed to this project. No code
visibility setting can be changed from the desk.

Confirm only facts you personally checked: the original development window,
code/history privacy and judge access, exact demo link, article claims and rules.
The desk does not retrieve external URLs, verify account eligibility, or accept
rules on your behalf. URL checks cover syntax and reject local addresses,
placeholders, credentials, Actions artifacts and common signed-download links.
They cannot prove that a syntactically public URL is accessible, safe or relevant.

The article preview inserts the demo link into bounded template markers in
`POST_FINAL.md`. It preserves the technical narrative, required tags and
`published: false`. Missing items stay visible in working exports. Updating the
article or engine invalidates the saved claim-review confirmation. The tracked
article and `docs/submission_evidence.json` are never overwritten by browser use.

Select a run from this workspace's Quality Lab to see its actual assessments and
internal evidence blockers. Human assessments, real-customer adoption and
publication approvals are separate concepts. No checkbox creates a model run
or customer feedback. The stronger internal evidence gate is not an official
contest requirement; first-user evidence remains optional under the event prompt.

## Export

**Download DEV draft** creates Markdown, not a DEV post. **Export working judge
packet** creates a ZIP even with outstanding items, retaining those items in the
article and READINESS.json. **Export checked packet** requires the current local
preflight and explicit inclusion of the selected assessed evaluation. Even a
checked packet remains unpublished and is not independent eligibility verification.

Extract the entire ZIP and open **START_HERE.html**. A judge can inspect the
product's purpose, recorded model replies and raw evidence without Python,
Ollama or JavaScript. It is a read-only exhibit, not a hosted interactive app.
The packet includes an operator-trial protocol to obtain real feedback, not a
prefilled testimonial.

Exports use fixed filenames and allowlisted project documents. They do not scan
customer draft folders, copy profiles or environment files, or include session
capabilities. The selected Quality Lab report, including its raw text and notes,
is excluded unless explicitly enabled with per-export consent. Still inspect all
exported files before sharing: allowlisting is not an audit of all document text.
SHA-256 checksums detect accidental changes; they are not digital signatures.

Supporting documents in the fixed public allowlist now participate in the saved
review/version lease, alongside the article and evaluation. Changing one clears
the current claim-review confirmation and makes an older save/export revision
stale. Reload and review the article and packet documents before confirming again.
The packet builder compares the bytes it will copy against that snapshot, and
the browser export rechecks the snapshot before returning a ZIP. READINESS.json
records the same byte counts and SHA-256 hashes as the payload manifest.

Only bounded, single-link regular files are read for these documents. File and
parent symlinks, hard links, directories, FIFOs and oversized/missing documents
are refused rather than copied or opened as unbounded inputs. Missing documents
require a complete project copy; the desk does not reconstruct them. The
allowlist has not expanded and private workspace files remain excluded by default.
Hashes do not identify secrets in ordinary document text or prevent deliberate
local forgery. Inspect every exported file before sharing.

## Add an existing video to a local packet

Close the browser server, or select a separate data directory. This command
includes only the video file you explicitly name and never overwrites a packet:

```powershell
py rrw_submission.py --output "judge-packet.zip" --video "Review_Reply_Writer_Gemma_Demo.mp4"
```

Use the actual path to your video. The CLI requires an ordinary MP4 under 100 MiB.
Its container-header check does not establish that the content is accurate or
playable. The CLI excludes private evaluations; use the browser's deliberate
sharing controls to include one. No video is uploaded automatically. A local
packet is not the required judge-accessible hosted link or a DEV submission.

To verify an exported packet from the source repository:

```powershell
py check_submission.py --release --evidence "packet/submission_evidence.json" --post "packet/DEV_SUBMISSION_DRAFT.md"
```

The generated evidence file resolves its selected report relative to itself.
An explicit `--evaluation` path is resolved from your current directory. The
original repository checklist keeps its original repository-relative semantics.

## State and safety

Only ignored `.rrw/submission.json` stores browser checklist values. Writes are
atomic and stale tabs cannot save or export over changed state, an edited article,
or a changed selected evaluation. Corrupt, oversized and duplicate-key state is
reported and preserved. All new API routes use the existing loopback capability,
Host/Origin and request-size boundaries. No arbitrary paths can be supplied through
the browser. A competing local process or malicious file editor is still outside
database-style isolation; hashes do not defeat deliberate local forgery.

The original drafting/approval and Quality Lab source files remain byte-identical
for this pass. The browser launcher and UI gain the additional view, and the
submission checker gains explicit evidence/post paths. The local browser policy
blocks loopback access in this assistant environment, so Chromium interaction
verification runs in the existing GitHub CI environment, not by bypassing policy.

## Rules basis

Checked October 13, 2026. Recheck before publishing; this is a local checklist,
not a legal determination or a guarantee of acceptance.

- Official Week 2 rules: https://dev.to/page/hacktoberfest-week2-2026-10-12-contest-rules
- Challenge, template, tags and judging criteria: https://dev.to/challenges/hacktoberfest-week2-2026-10-12

The entry window ends October 18 at 11:59 PM PDT, or 8:59 PM Hawaii time. Writing
quality has the largest judging weight. Publishing through the DEV template with
a meaningful open-AI project, code access, a demo and the required explanation is
separate from completing this application's internal evidence gate.
