# Local verification without GitHub Actions

The owner requested stopping repository jobs that use GitHub Actions on
October 14, 2026. Both workflow definitions were removed from current main.
Neither had a cron trigger. No queued or in-progress Actions run was found at
inspection. Scripts remain available for deliberate local execution. No tests
were weakened or deleted. Nothing schedules tests or installs tools automatically.

Run from a complete source checkout with Python 3.10 or newer:

```powershell
py check_submission.py
py scripts/launcher_smoke.py
py scripts/backup_smoke.py
```

With Node already installed, also run each `scripts/*_checks.cjs` state check.
Real browser checks use the existing `scripts/*browser_smoke.py` scripts and
require an installed Playwright/Chromium test environment. These are development
tools, not application runtime requirements. Do not equate controlled state
checks with real browser navigation.

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
