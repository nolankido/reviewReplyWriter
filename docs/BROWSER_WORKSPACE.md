# Local browser workspace

Development pass: October 13, 2026. Base: `cd931620ee4d3edc05a53775c61e80322a2d32d5`.

## Start and use

Windows: double-click `start_windows.bat`, or run `py rrw_web.py` from the project
folder. macOS/Linux: `python3 rrw_web.py`. Requires Python 3.10 or newer, with no
additional runtime packages. Keep the launcher terminal open. Ctrl+C stops it.

The server binds only to `127.0.0.1`, normally on port 8765. `--port 0` chooses a
free port. `--no-browser` prints the session link without opening a tab.
`--data-dir PATH` selects a separate local workspace containing `replies/` and
`.rrw/`. The default uses the existing repository's CLI draft and profile paths.

1. Try a fictional example in **Template preview (no AI)**, or paste a review.
2. Set business, voice, reply style and rating. Follow-up mode also requires the
   original review and the owner's previously posted response. The follow-up
   engine grades update text, so its rating control is disabled.
3. Leave owner policy blank unless you have actual authorization. Offers and
   action statements need an explicit confirmation for that business. Loading
   a profile does not silently confirm its promises. A changed business cannot
   reuse another business's saved voice profile.
4. Generate, read, and edit. **Save & recheck** preserves edits, records detected
   issues, and clears earlier approval. Invalid drafts can be saved for repair,
   but they cannot be approved or exported through this interface.
5. Read the exact saved policy in the editor, check the human-review box, and
   approve. Copy or export that exact approved text for manual posting.

Use search and status filters to reopen prior drafts. A stale tab receives a
conflict rather than overwriting or exporting a changed file. Profile updates
also check the revision read by the tab. Regeneration uses the selected draft's
saved policy, not unrelated edits in the compose form.

The CLI remains available for batch import, voice learning, and best-of-two
selection. Saved voice metadata is respected for matching browser profiles and
existing draft regeneration, but the browser does not expose a voice-training
or batch-import screen in this pass. GUI policy edits apply to new drafts only.

## Actual model versus a demonstration

Template preview does not call a model. To use Gemma, install/start Ollama and
run `ollama pull gemma3:4b`. Select **Local Gemma 3 (4B)** explicitly. The interface
records attempt counts, temperatures, measured call durations, and validation
findings. Unavailable or rejected model output falls back to a labelled template.
The interface never calls a template a Gemma-generated reply.

The browser fixes the model identifier to `gemma3:4b`, uses a direct loopback
endpoint, disables environment proxy use, and rejects redirects. This does not
prove that a model alias or the independently running Ollama server is configured
for local inference. Enable Ollama local-only mode. The initial model download
requires internet access; the app does not install models or audit network traffic.

No fresh Gemma inference, hardware speed benchmark, or real-business usability
study was performed in this pass. Controlled model responses in the tests prove
integration behavior, not the model's output quality.

## Local security boundaries

The UI has a per-server random session capability. The launcher passes it in a
URL fragment, which is not sent in the HTTP request. The page removes the fragment
from the address bar and stores it in this tab's session storage for reloads.
The API requires that capability on reads and writes. Restarting the server
invalidates old sessions. Reopen the newly printed link after a restart.

Host checks reject DNS-rebinding hostnames. Mutation requests require the exact
local Origin, a custom token header, and JSON. No CORS allowance is sent. Request
size and JSON structure are bounded. Only three fixed UI asset routes are served;
there is no directory listing or generic file-serving endpoint. Draft paths are
validated and symlink drafts are rejected. Responses are non-cacheable and use
CSP, frame denial, nosniff and no-referrer headers. Review/reply text is inserted
with textContent or textarea values, never HTML interpretation. No external
fonts, scripts, images, analytics, or UI assets are loaded.

This is still a single-owner desktop prototype, NOT a public or multi-user web
service. Do not expose the port, reverse-proxy it publicly, or share the session
link. Python's standard-library HTTP server is not recommended for production
internet hosting. A malicious local user, compromised browser extension, edited
approval JSON, or someone with the session capability is outside the protection
provided here. Profiles and drafts are plaintext local files, not encrypted storage.

The browser uses one in-process state lock and a one-generation-at-a-time gate.
A platform file lock blocks a second browser process in the same workspace.
External CLI processes do not honor that lock, so do not run competing writers.
Hash checks detect many external edits, but this is not database-style isolation.
If a tab closes during generation, the request may finish and save an unapproved
draft. Nothing is posted automatically.

Copy uses the browser Clipboard API. When access is denied, the approved reply
is selected for manual Ctrl+C/Command+C. The operating system clipboard may have
its own history or synchronization settings; copying deliberately leaves the app.

## Verification

`python -m unittest -v` runs the existing safety tests plus 41 new workspace and
real-loopback HTTP tests: approval/export gating, unsafe edits, stale revisions,
exact policy confirmation, same-business voice, profile corruption, checked
fallbacks, follow-up preservation, path restrictions, request boundaries, and
single-instance locking. The combined local suite has 168 tests.

The existing Ubuntu/Windows matrix on Python 3.10 and 3.13 now includes these tests.
A separate Chromium interaction job executes `scripts/browser_smoke.py`, with
screenshots and machine-readable results retained as a CI artifact. Read the
actual workflow conclusion before claiming a browser test passed. The browser
script covers editing, actual clipboard copy and download, stale second-tab
access, persistence, explicit profiles, follow-ups, inert hostile markup, a
controlled retry, and a 390px layout without horizontal overflow.

Developer-only browser setup:

```text
python -m pip install playwright==1.63.0
python -m playwright install --with-deps chromium
python scripts/browser_smoke.py --screenshots evidence/browser
```

The application itself does not depend on Playwright. `RRW_CHROMIUM_EXECUTABLE`
may select an existing permitted test browser. Do not bypass managed browser
restrictions; use a CI environment that supports the test instead.

`python check_submission.py` verifies development state. The separate `--release`
check remains intentionally blocked until the actual demonstration and owner
evidence are supplied. This interface is not a completed contest submission.

## Source references

- Python HTTP-server limitations: https://docs.python.org/3/library/http.server.html
- Ollama local-only configuration: https://docs.ollama.com/faq
- Clipboard behavior: https://developer.mozilla.org/en-US/docs/Web/API/Clipboard/writeText
- Browser CI setup: https://playwright.dev/python/docs/ci
