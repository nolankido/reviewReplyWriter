# Local verification without GitHub Actions

The owner requested stopping repository jobs that use GitHub Actions on
October 14, 2026. Both workflow definitions were removed from current main.
Neither had a cron trigger. No queued or in-progress Actions run was found at
inspection. Scripts remain available for deliberate local execution. No tests
were weakened or deleted. Nothing schedules tests or installs tools automatically.

Run from a complete source checkout with Python 3.10 or newer:

```powershell
py rrw_verify.py
```

macOS/Linux: `python3 rrw_verify.py`. This runs the development checker, both real
launcher HTTP workflows and all nine Node state checks using fixed commands.
Node is a development-test tool; it is not required to use the app. Missing Node
is reported as unavailable and cannot produce a complete development pass.
Each check has a deadline; failure does not stop the remaining diagnostics.
Subprocess output is discarded so private paths, session links and raw errors
cannot enter the receipt. To investigate a failure, run its named script directly
and inspect the diagnostics locally. Nothing is sent to GitHub.

The command creates a new JSON receipt under ignored `.rrw/verification/`.
`--output NEW_FILE.json` chooses an explicit new path. Existing files and linked
receipt paths are refused. Keep failed/incomplete receipts too; inspect every
file before sharing. The receipt records actual check states and local elapsed
times, Python/OS/architecture, and before/after hashes of the fixed public code,
web assets, test scripts and fictional fixtures in `verification_sources.json`.
It excludes owner policy, customer reviews, private notes, full paths and raw
logs. A new test must be added to the inventory. Missing or linked sources,
changed source during verification, failed checks and deadlines cannot yield a
current pass. Hashes are not signatures or protection against local forgery.
The scope excludes documentation, owner policies and external tool installations;
this is not a fingerprint of every possible test input or dependency.

Browser navigation remains **not requested** by default. If Playwright and
Chromium are already installed on the target computer, explicitly run:

```powershell
py rrw_verify.py --browser
```

That runs all four existing browser smoke scripts. Nothing is downloaded or
installed, and a missing browser/tool is a failed or unavailable check. The
scripts use fictional inputs and controlled model responses, not actual Gemma.
Do not equate default Node state checks with real browser navigation.

| Exit code | Meaning |
| --- | --- |
| 0 | Every requested development check passed on unchanged inventoried source |
| 1 | Failed/timed-out check, source change, invalid source, or receipt-write failure |
| 2 | Incomplete because a required executable was unavailable |
| 130 | Interrupted; no completed verification or new receipt is claimed |

Local success applies only to the machine and source actually tested. It does
not establish Gemma quality, operator adoption, contest eligibility or completion
of submission. `py rrw_setup.py --verify-gemma` is a separate explicit local-model
test; record human assessments in Quality Lab. Nothing here downloads models,
posts replies, publishes an entry or changes GitHub billing/configuration.

Repository-wide Actions policy requires repository-administration access. The
connected tools cannot change that setting, and the available browser was signed
out. Removing source workflows is verified separately from globally disabling
Actions. Historical branches or future workflow files can reintroduce jobs; to
block those too, the owner can select Disable actions in repository Settings,
Actions, General. Keep that distinction when reporting automation status.
