# Quality Lab: reproducible evaluation and honest evidence

Development pass: October 13, 2026. Base: `ce9618b83cc4d3b42e9efa47fa5993cc9ed611b7`.

## Use the browser

Launch `py rrw_web.py` and choose **Quality Lab**. This is a separate workspace
for fictional regression reviews. It does not import personal reviews, post
replies, update owner profiles, train voice, or change the production gap ledger.

1. Start with **Templates only (no AI)** and the three-case smoke set. Create
   an evaluation, then click **Run next case** for each case. No Ollama call,
   model installation or network preflight occurs in template mode.
2. To evaluate Gemma, click **Check Gemma setup**. The check distinguishes an
   unavailable service, missing model, unverified metadata, and an installed
   model. It records the server-reported digest, size, family, quantization and
   available Ollama version. It does not claim installation proves quality.
3. Select **Local Gemma 3 (4B)**, confirm the fictional run, create a new
   evaluation and run each case. A case uses the existing checked generation
   pipeline, including its one coached retry and honestly labelled fallback.
4. Read each result, its original review and owner policy. Record your own
   assessment: usable as a draft, needs editing, or unusable. Mark issues you
   actually observed. Corrections stay beside the original, never replace it.
   Assessments are not publication approvals or customer endorsements.
5. Export JSON evidence and the readable Markdown report. They include raw
   attempts and your notes, so inspect them before deliberately sharing them.
   The application uploads nothing and does not set contest attestations.

Reports are saved in ignored `.rrw/evaluations/`. The UI reopens them after
restart. One case is reserved before inference; a process crash leaves it
marked interrupted rather than silently omitting or rerunning it. Completed
results cannot be rerun in place. Start a new evaluation to repeat the protocol.
An interrupted case prevents that run from qualifying as complete live evidence.

Use **Check saved evaluation** after an uncertain case or assessment response.
It leaves pending assessment text alone; explicit loading rechecks the revision
and leaves review confirmation unchecked. Active reservations cannot be treated
as finished results or exported. See [request recovery](QUALITY_REQUEST_RECOVERY.md)
for restart, lost-creation and unexecuted-browser limits.

## Terminal workflow

Close the browser server first: the evaluation CLI shares its workspace lock.
Alternatively select a separate `--data-dir` for CLI evaluations.

```powershell
py rrw_evaluate.py --mode offline --suite full
py rrw_evaluate.py --mode gemma --suite smoke
py rrw_evaluate.py --resume eval-EXISTING_ID
py rrw_evaluate.py --report .rrw/evaluations/eval-EXISTING_ID.json
```

Use the actual saved ID, not the example placeholder. Ctrl+C preserves completed
rows. To inspect CLI results in the UI, restart `py rrw_web.py` with the same
workspace/data directory and select the saved evaluation in Quality Lab.

A return code of 0 means the protocol finished without execution errors. It
DOES NOT mean the replies were good, every case generated output, or the model
was used. A detected unsafe/oversized draft can be a deliberately blocked result.
Code 1 reports execution errors/interruption; code 2 reports setup/input problems.
The report contains the actual outcomes and unresolved human assessments.

## What the metrics mean

The 30 scenarios in `examples/evaluation_cases.json` are fictional, developer-
written fixtures. They include selected positive, negative, mixed and follow-up
cases; sarcastic/negated wording; rating conflicts; prompt injection; authorized
and unauthorized commitments; and a policy too long for the chosen word target.
They are deliberately diagnostic, not a random sample of real customer reviews.

Each run records **all selected cases**, including blocked, failed and interrupted
cases. It distinguishes model drafts, deliberate templates and model fallbacks.
First-try model outcomes and retries use case-level denominators. Median model
case duration includes retries for model-drafted cases and excludes templates,
fallbacks and failed cases. API receipts retain available nanosecond durations
and token counts, separately from client elapsed milliseconds.

The rubric only compares the intended tier and a short list of target topic
strings. A flag may be a real failure or a limitation of this simple probe;
absence of a flag is not proof of semantic correctness. The existing sentiment
heuristics still misread some negation, sarcasm and rating/text disagreements.
Those known cases remain in the set. Do not tune the corpus to erase failures.

Human-quality metrics have a separate reviewed-case denominator. Zero recorded
risk flags among unreviewed cases does not mean zero risk. The UI says **Unknown**
until an assessment exists. No human feedback is manufactured automatically.

## Model completion and reproducibility

Generation now rejects empty, wrong-model, unfinished and output-limit-truncated
responses. A successful text result includes a bounded typed API receipt.
Metadata errors do not become plausible model output. Available request/response
metrics are server-reported, not independently attested measurements.

The evaluation records source-file hashes, the complete fixture snapshots,
owner-policy version, model identity and generation parameters. Model identity
is checked before and after each Gemma case. Changed code prevents mixing new
cases into an old run. Reports can still be exported as historical evidence.
Default server context/seed settings are explicitly reported as not inspected;
a repeatable evaluation protocol does not guarantee identical stochastic text.

Report and result hashes detect accidental changes and stale tabs. They are not
signatures and do not defeat deliberate local forgery. Controlled test callers
are labelled `controlled-test`, never qualifying as genuine model evidence.
Templates cannot qualify as a fresh Gemma run. A report that includes a fallback
does not become entirely AI-generated simply because it attempted a model call.

## Privacy and scope

This remains a single-owner loopback app. All existing capability, Host/Origin,
JSON-size and fixed-route controls apply to Quality Lab, including its exports.
No arbitrary dataset paths, model endpoints or downloaded scripts can be supplied
through the browser. The CLI reads only the explicitly named local report file.

Install/start Ollama and run `ollama pull gemma3:4b`. For local-only operation,
set `disable_ollama_cloud` to true in Ollama's server configuration or use
`OLLAMA_NO_CLOUD=1`, then restart Ollama. Setting an environment variable only in
an unrelated client terminal does not reconfigure an already-running server.
A loopback URL does not prove that a model alias cannot forward work elsewhere.
The application does not change or independently audit Ollama configuration.

## Release check

```powershell
py check_submission.py --release --evaluation .rrw/evaluations/eval-EXISTING_ID.json
```

The file must be integrity-checked, match current source, include at least the
completed three-case smoke run, retain completed API receipts and at least one
accepted model draft, and have human assessments for the selected cases. This
is this project's evidence policy, not a claim that the contest mandates it.
The separate demo, accessibility, date-window and firsthand-claim confirmations
remain required. Do not set them true merely to get a green check.

## Validation and limitations

The pass adds deterministic evidence/transport/HTTP tests to the existing suite,
plus a real Chromium quality-workflow script. Both the original drafting workflow
and the new lab are exercised in browser CI. Test doubles do not establish fresh
Gemma performance; actual live attempts must be reported separately.

All operations are local and user-directed. There is no unattended scheduling.
One generation at a time shares the existing gate. Atomic files and optimistic
revisions are not database isolation against a malicious/competing local writer.

## Technical sources checked for this pass

- Ollama generation response and timing fields: https://docs.ollama.com/api/generate
- Ollama model digests and details: https://docs.ollama.com/api/tags
- Ollama local-only configuration and server defaults: https://docs.ollama.com/faq
