# Set up an owner's computer and record what actually works

Requires Python 3.10 or newer. Runtime dependencies are Python's standard
library. Extract the whole repository ZIP, including `web/`, into a writable
folder. No account, API key, model or paid hosting is required for templates.

## Launch

Windows: double-click `start_windows.bat`. It checks the Python version before
using `py -3`, then tries `python` if the first interpreter is unavailable or
too old. A failure remains visible until the window is dismissed.

Terminal equivalent:

```powershell
py -3 rrw_setup.py --launch
```

macOS/Linux:

```bash
python3 rrw_setup.py --launch
```

The launcher checks installation files, storage, a loopback bind and a checked
fictional template before opening the browser. It chooses a free local port by
default. Keep the terminal open. Ctrl+C stops the server. The session link is
private and is removed from the browser's URL after initialization.

To choose storage outside the extracted folder, add `--data-dir PATH`. The
checker can create this directory and writes temporary probes that are removed;
it does not open customer profiles or replies. Existing `.rrw/` and `replies/`
directories must also be writable. Workspace folder links are rejected by the
checker. Add `--no-browser` to print the session link or `--port 8765` to choose
a particular port. The direct `rrw_web.py` command remains supported.

The browser's **Getting started** guide can load the complaint example without
generating, recheck installation and open Quality Lab. Existing editor discard
confirmation still applies when loading an example.

## Check without launching or generating

```powershell
py -3 rrw_setup.py --report evidence/setup-check.json
```

Checks distinguish Python/application/storage/browser readiness from model
installation. Ollama being absent does not fail template readiness. The model
check uses bounded loopback requests with environment proxies and redirects
disabled. The browser badge, CLI doctor and Quality Lab share this inspection.
A name alone is insufficient: a single `gemma3:4b` listing must include a digest,
positive downloaded size and the `gemma3` family, without remote model metadata.
This trusts server metadata; it does not attest the weights or network behavior.

Diagnostics contain the check time, Python/OS/architecture, fixed status
messages and selected model identity fields. They exclude customer data, full
workspace paths, raw error text, session links and free-form server metadata.
Inspect any report before sharing. No report is uploaded by the app.

## Explicitly verify actual Gemma output

Install/start Ollama, download `gemma3:4b`, enable Ollama's local-only setting,
then restart Ollama. See the official configuration link in the README.
The initial download requires internet; the setup tool does not download models
or modify configuration. Close the browser app before the command below so the
evaluation can hold the workspace lock.

```powershell
ollama pull gemma3:4b
py -3 rrw_setup.py --verify-gemma
py -3 rrw_setup.py --launch
```

The explicit verification command runs the existing three fictional smoke
scenarios. Model output, retries and available API receipts are checkpointed in
`.rrw/evaluations/`. No customer draft, approval or gap ledger is created by the
evaluation. Ctrl+C preserves completed cases and marks an in-flight case
interrupted. Run a fresh test after resolving an interruption or failure.

Diagnostics are also saved to `.rrw/setup-check.json`, or your `--report` path.
The summary references the evaluation ID and drafting source hashes, without
copying reply text or absolute paths. Reopen **Quality Lab**, choose the saved
evaluation and assess each result yourself. Export its full JSON and readable
report if using it as submission evidence.

A passed smoke check requires all three cases to finish with accepted model
drafts, completed receipts per case, unchanged model identity, current drafting
sources and no limited rubric flags. Templates, controlled test callers and
fallbacks do not qualify. Human assessment remains separate, and passing does
not prove factuality, usefulness or an independently audited private runtime.

| Command outcome | Exit code | Meaning |
| --- | ---: | --- |
| Setup ready | 0 | Templates can launch; generation may remain untested |
| Setup or diagnostic saving failed | 1 | Fix installation, storage, browser permission or report location |
| Explicit Gemma smoke did not pass | 2 | Read diagnostics and any saved case results; no success is implied |
| Verification interrupted | 130 | Completed cases remain saved; the run did not pass |

## Verification limits for this implementation

Local regression tests use controlled model responses and protocol fixtures.
The implementation environment passed its Python, file, storage, loopback and
template checks; Ollama was unavailable, so no actual model call was made.
The Windows batch file and expanded Chromium setup-guide interactions still
require execution on their target runtimes. They are included in the existing
local verification scripts. Run `py rrw_verify.py` on the target computer;
add `--browser` only with Playwright/Chromium already installed. GitHub Actions
workflows were removed at the owner's request. An old Actions run that executed no steps cannot
validate them. Do not substitute these local checks for a real owner trial.

`python scripts/launcher_smoke.py` exercises the actual setup launcher, a data
directory whose path contains spaces, a free loopback port, template generation,
human approval and approved text export. It uses `start_windows.bat` on Windows
and the Python setup launcher elsewhere. Session links are kept out of its
output and the temporary workspace is removed. This HTTP test is separate from
Chromium navigation and actual Gemma quality.
