"""Actual Chromium inbox smoke test. Uses templates only, not Gemma evidence.

Uses the optional Playwright dependency documented by scripts/browser_smoke.py.
"""
import argparse
import json
import os
import re
from pathlib import Path
import sys
import tempfile
import threading

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rrw_web import LocalServer
from rrw_workspace import Workspace
from playwright.sync_api import sync_playwright, expect


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--screenshots', type=Path)
    args = parser.parse_args()
    if args.screenshots:
        args.screenshots.mkdir(parents=True, exist_ok=True)
    checks, errors = [], []
    with tempfile.TemporaryDirectory() as root:
        workspace = Workspace(root)
        server = LocalServer(workspace, 0)
        thread = threading.Thread(target=server.serve_forever, kwargs={'poll_interval': .01}, daemon=True)
        thread.start()
        try:
            with sync_playwright() as p:
                launch = {'headless': True}
                if os.getenv('RRW_CHROMIUM_EXECUTABLE'):
                    launch['executable_path'] = os.environ['RRW_CHROMIUM_EXECUTABLE']
                browser = p.chromium.launch(**launch)
                page = browser.new_page(viewport={'width': 1480, 'height': 1100}, reduced_motion='reduce')
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.goto(server.launch_url)
                expect(page.locator('#generate')).to_be_enabled()
                page.locator('#inbox-details').evaluate('(el) => el.open = true')
                page.locator('#inbox-csv').fill((Path(__file__).resolve().parents[1] / 'web/inbox-sample.csv').read_text())
                page.locator('#inbox-preview-button').click()
                expect(page.locator('#inbox-preview-counts')).to_contain_text('3 ready')
                expect(page.locator('#inbox-preview-counts')).to_contain_text('1 duplicates')
                expect(page.locator('#inbox-preview-counts')).to_contain_text('1 personal handling')
                assert workspace.dispatch('state')['drafts'] == []
                expect(page.locator('#inbox-create')).to_be_disabled()
                checks.append('Preview classifies all five source rows and creates no drafts')
                page.locator('#inbox-confirm').check()
                page.locator('#inbox-create').click()
                expect(page.locator('#inbox-saved-counts')).to_contain_text('3 ready')
                page.locator('#inbox-next').click()
                expect(page.locator('#draft-status')).to_have_text('Needs review')
                expect(page.locator('#reply-editor')).to_have_value(re.compile('duplicate billing'))
                expect(page.locator('#reply-editor')).to_have_value(re.compile('unanswered question'))
                expect(page.locator('#copy')).to_be_disabled()
                expect(page.locator('#saved-policy')).to_contain_text('No compensation')
                expect(page.locator('#inbox-saved-counts')).to_contain_text('1 drafted')
                checks.append('One click saves one unapproved draft with no inherited owner commitments')
                page.locator('#human-reviewed').check()
                page.locator('#approve').click()
                expect(page.locator('#copy')).to_be_enabled()
                page.locator('#inbox-refresh').click()
                expect(page.locator('#inbox-saved-rows')).to_contain_text('Approval: Approved')
                checks.append('Existing explicit approval is visible in inbox status')
                if args.screenshots:
                    page.screenshot(path=str(args.screenshots / 'inbox-desktop.png'), full_page=True)
                page.reload()
                expect(page.locator('#generate')).to_be_enabled()
                page.locator('#inbox-details').evaluate('(el) => el.open = true')
                expect(page.locator('#inbox-select option')).to_have_count(2)
                inbox_id = workspace.dispatch('inbox-list', {})['inboxes'][0]['id']
                page.locator('#inbox-select').select_option(inbox_id)
                expect(page.locator('#inbox-saved-counts')).to_contain_text('2 ready')
                page.locator('#inbox-next').click()
                expect(page.locator('#inbox-saved-counts')).to_contain_text('2 drafted')
                assert len(workspace.dispatch('state')['drafts']) == 2
                checks.append('Reload resumes the remaining queue without repeating the first review')
                manual = page.locator('.inbox-row').filter(has_text='The cafe exposed my private information.')
                manual.get_by_role('button', name='Read for personal handling').click()
                expect(page.locator('#manual-review-panel')).to_be_visible()
                expect(page.locator('#draft-status')).to_have_text('Manual only')
                expect(page.locator('#reply-editor')).to_have_value('')
                expect(page.locator('#copy')).to_be_disabled()
                manual.get_by_text('Record private handling', exact=True).click()
                manual.locator('textarea').fill('Synthetic browser-test handling note. No real operator result.')
                manual.locator('input[type=checkbox]').check()
                manual.get_by_role('button', name='Save private handling').click()
                expect(page.locator('#inbox-saved-counts')).to_contain_text('1 personally handled')
                assert len(workspace.dispatch('state')['drafts']) == 2
                checks.append('Manual item has a separate screen and private tracking, without generating or approving a reply')
                page.locator('#inbox-csv').fill('review,stars\n"Great coffee. <img src=x onerror=window.injected=1>",5\n')
                page.locator('#inbox-preview-button').click()
                expect(page.locator('#inbox-preview-rows')).to_contain_text('<img')
                assert page.evaluate('window.injected || 0') == 0
                checks.append('Customer HTML in import preview is inert text')
                page.set_viewport_size({'width': 390, 'height': 844})
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
                if args.screenshots:
                    page.screenshot(path=str(args.screenshots / 'inbox-mobile.png'), full_page=True)
                checks.append('Inbox fits 390px without horizontal overflow')
                assert not errors, errors
                browser.close()
        finally:
            server.shutdown(); server.server_close(); thread.join(2)
    print(json.dumps({'checks': checks, 'browser_errors': errors, 'engine': 'templates only; no real Gemma inference'}, indent=2))


if __name__ == '__main__':
    main()
