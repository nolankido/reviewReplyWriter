"""Actual Chromium interaction smoke test. Model responses are test stand-ins.

Optional dev dependency: pip install playwright==1.63.0
Then: python -m playwright install chromium
Run: python scripts/browser_smoke.py --screenshots /path/to/evidence
App users do not need Playwright. No real model evaluation is claimed here.
"""
import argparse
import json
import os
from pathlib import Path
import sys
import tempfile
import threading

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import rrw_web
from rrw_workspace import Workspace
from playwright.sync_api import sync_playwright, expect


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--screenshots', type=Path)
    args = parser.parse_args()
    if args.screenshots:
        args.screenshots.mkdir(parents=True, exist_ok=True)
    assertions = []
    with tempfile.TemporaryDirectory() as tmp:
        workspace = Workspace(tmp)
        server = rrw_web.LocalServer(workspace, 0)
        thread = threading.Thread(target=server.serve_forever, kwargs={'poll_interval': .05}, daemon=True)
        thread.start()
        try:
            with sync_playwright() as p:
                launch = {'headless': True}
                if os.getenv('RRW_CHROMIUM_EXECUTABLE'):
                    launch['executable_path'] = os.environ['RRW_CHROMIUM_EXECUTABLE']
                browser = p.chromium.launch(**launch)
                context = browser.new_context(viewport={'width': 1480, 'height': 1160},
                    reduced_motion='reduce', permissions=['clipboard-read', 'clipboard-write'])
                page = context.new_page()
                errors, requests = [], []
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.on('request', lambda req: requests.append(req.url))
                page.goto(server.launch_url)
                expect(page.locator('#generate')).to_be_enabled()
                expect(page.locator('#model-status')).not_to_have_text('Checking Ollama')
                assert '#token=' not in page.url
                assertions.append('Session token removed from URL; workspace initializes')
                page.locator('#review').fill('SYNTHETIC_PENDING_REVIEW')
                page.locator('#owner-policy').evaluate('(el) => el.open = true')
                page.locator('#offer').fill('a replacement coffee on your next visit')
                page.locator('#policy-confirmed').check()
                page.once('dialog', lambda dialog: dialog.dismiss())
                page.get_by_role('button', name='Positive', exact=True).click()
                expect(page.locator('#review')).to_have_value('SYNTHETIC_PENDING_REVIEW')
                page.locator('#recovery-panel summary').first.click()
                page.locator('#recovery-check').click()
                expect(page.locator('#recovery-save')).to_be_enabled()
                page.locator('#recovery-save').click()
                expect(page.locator('#recovery-status')).to_contain_text('Working copy saved')
                page.once('dialog', lambda dialog: dialog.accept())
                page.reload()
                expect(page.locator('#generate')).to_be_enabled()
                expect(page.locator('#review')).to_have_value('')
                page.locator('#recovery-panel summary').first.click()
                page.locator('#recovery-check').click()
                expect(page.locator('#recovery-restore')).to_be_enabled()
                page.locator('#recovery-restore').click()
                expect(page.locator('#review')).to_have_value('SYNTHETIC_PENDING_REVIEW')
                expect(page.locator('#offer')).to_have_value('a replacement coffee on your next visit')
                expect(page.locator('#policy-confirmed')).not_to_be_checked()
                expect(page.locator('#engine-mode')).to_have_value('offline')
                page.once('dialog', lambda dialog: dialog.accept())
                page.locator('#recovery-clear').click()
                expect(page.locator('#recovery-status')).to_contain_text('No recovery copy')
                page.locator('#recovery-panel summary').first.click()
                page.once('dialog', lambda dialog: dialog.accept())
                assertions.append('Pending inputs resist replacement; explicit recovery survives reload without restoring owner authorization')
                page.locator('#setup-guide summary').click()
                expect(page.locator('#setup-model-message')).not_to_have_text('Checking the local model installation.')
                page.locator('#setup-quality').click()
                expect(page.locator('#quality-panel')).to_be_visible()
                page.locator('#setup-example').click()
                expect(page.locator('#draft-panel')).to_be_visible()
                assert 'Cold coffee' in page.locator('#review').input_value()
                page.locator('#setup-guide summary').click()
                assertions.append('Setup guide links to Quality Lab and loads a fictional example without generating')
                def drop_generation_response(route):
                    route.fetch()  # Real server saves a template, then the browser loses its response.
                    route.abort()
                page.route('**/api/generate', drop_generation_response)
                page.locator('#generate').click()
                expect(page.locator('#generation-recovery')).to_be_visible()
                expect(page.locator('#notice')).to_contain_text('Connection lost')
                expect(page.locator('#generate')).to_be_disabled()
                page.unroute('**/api/generate', drop_generation_response)
                page.locator('#generation-check').click()
                expect(page.locator('#generation-open')).to_be_enabled()
                page.locator('#review').fill('SYNTHETIC_NEW_PENDING_INPUT')
                page.once('dialog', lambda dialog: dialog.dismiss())
                page.locator('#generation-open').click()
                expect(page.locator('#review')).to_have_value('SYNTHETIC_NEW_PENDING_INPUT')
                page.once('dialog', lambda dialog: dialog.accept())
                page.reload()
                expect(page.locator('#generation-recovery')).to_be_visible()
                page.locator('#generation-check').click()
                expect(page.locator('#generation-open')).to_be_enabled()
                page.locator('#generation-open').click()
                expect(page.locator('#generation-recovery')).to_be_hidden()
                expect(page.locator('#policy-confirmed')).not_to_be_checked()
                assert len(workspace.dispatch('state')['drafts']) == 1
                assertions.append('Lost template response is recovered after reload without a duplicate or replacing pending inputs silently')
                expect(page.locator('#draft-status')).to_have_text('Needs review')
                expect(page.locator('#copy')).to_be_disabled()
                expect(page.locator('#draft-source')).to_contain_text('Template preview, no AI')
                expect(page.locator('#reply-editor')).not_to_have_value('')
                expect(page.locator('#review-evidence')).to_be_visible()
                expect(page.locator('#review-evidence')).to_contain_text('25 minute')
                page.locator('#review-evidence summary').first.click()
                expect(page.locator('#review-evidence blockquote').first).to_be_visible()
                assert page.locator('#review-evidence blockquote').first.inner_text() in page.locator('#saved-review').inner_text()
                assertions.append('Detected details link to exact customer wording beside the saved draft')
                original = page.locator('#reply-editor').input_value()
                page.locator('#reply-comparison summary').click()
                expect(page.locator('#comparison-state')).to_contain_text('matches the starting draft')
                assert page.locator('#comparison-before').text_content() == original
                page.locator('#review-notes summary').click()
                page.locator('#review-note-role').select_option('demo')
                page.locator('#review-note-scenario').select_option('fictional')
                page.locator('#review-note-decision').select_option('as_is')
                page.locator('#review-note-text').fill('SYNTHETIC_BROWSER_ASSESSMENT')
                page.locator('#review-note-save').click()
                expect(page.locator('#review-note-state')).to_contain_text('Assessment saved')
                expect(page.locator('#copy')).to_be_disabled()
                assertions.append('Offline example generates a saved unapproved draft with honest credit')
                if args.screenshots:
                    page.evaluate('window.scrollTo(0, 0)')
                    page.screenshot(path=str(args.screenshots / 'workspace-desktop.png'), full_page=True)
                page.locator('#human-reviewed').check()
                page.locator('#approve').click()
                expect(page.locator('#copy')).to_be_enabled()
                page.locator('#copy').click()
                expect(page.locator('#notice')).to_contain_text('Approved reply copied')
                assert page.evaluate('navigator.clipboard.readText()') == original
                with page.expect_download() as download_info:
                    page.locator('#download').click()
                download = download_info.value
                assert Path(download.path()).read_text() == original
                assertions.append('Explicit approval enables real clipboard copy and text export')
                page.locator('#reply-editor').fill(original + '\nWe will refund you.')
                expect(page.locator('#review-evidence-note')).to_contain_text('Unsaved edits')
                expect(page.locator('#review-evidence')).not_to_contain_text('Mention detected')
                expect(page.locator('#copy')).to_be_disabled()
                expect(page.locator('#approve')).to_be_disabled()
                expect(page.locator('#findings-title')).to_have_text('Edits have not been checked yet.')
                page.locator('#reply-editor').fill(original)
                expect(page.locator('#review-evidence-note')).not_to_contain_text('Unsaved edits')
                expect(page.locator('#findings-title')).to_contain_text('Passed the current checks')
                expect(page.locator('#copy')).to_be_enabled()
                page.locator('#reply-editor').fill(original + '\nWe will refund you.')
                page.locator('#save-edit').click()
                expect(page.locator('#draft-status')).to_have_text('Needs changes')
                expect(page.locator('#human-reviewed')).to_be_disabled()
                assert page.locator('#comparison-before').text_content() == original
                expect(page.locator('#comparison-after ins')).to_contain_text('We will refund you.')
                expect(page.locator('#review-note-state')).to_contain_text('different saved draft')
                assertions.append('Unsafe edit invalidates approval and stays blocked after saving')
                page.locator('#comparison-restore').click()
                expect(page.locator('#reply-editor')).to_have_value(original)
                expect(page.locator('#copy')).to_be_disabled()
                page.locator('#save-edit').click()
                expect(page.locator('#draft-status')).to_have_text('Needs review')
                page.locator('#review-note-save').click()
                expect(page.locator('#review-note-state')).to_contain_text('Assessment saved')
                with page.expect_download() as counts_download:
                    page.locator('#review-note-export').click()
                exported_counts = Path(counts_download.value.path()).read_text()
                assert json.loads(exported_counts)['counts']['demo']['fictional']['as_is'] == 1
                assert 'SYNTHETIC_BROWSER_ASSESSMENT' not in exported_counts
                assert original not in exported_counts
                page.locator('#reply-comparison summary').click()
                page.locator('#review-notes summary').click()
                assertions.append('Saved baseline survives edits; restoration requires review; assessments stay separate and export only counts')
                page.locator('#human-reviewed').check()
                page.locator('#approve').click()
                expect(page.locator('#draft-status')).to_have_text('Approved')
                # Another tab must not overwrite changes or use a stale approval.
                second = context.new_page()
                second.goto(server.launch_url)
                expect(second.locator('#generate')).to_be_enabled()
                second.get_by_role('button', name='Demo Cafe: Approved', exact=True).click()
                expect(second.locator('#copy')).to_be_enabled()
                page.locator('#reply-editor').fill(original + '\nThank you.')
                page.locator('#save-edit').click()
                expect(page.locator('#draft-status')).to_have_text('Needs review')
                second.locator('#copy').click()
                expect(second.locator('#notice')).to_contain_text('changed elsewhere')
                second.close()
                assertions.append('Stale second-tab copy request is rejected server-side')
                page.reload()
                expect(page.locator('#generate')).to_be_enabled()
                page.get_by_role('button', name='Demo Cafe: Needs review', exact=True).click()
                expect(page.locator('#reply-editor')).to_have_value(original + '\nThank you.')
                assertions.append('Session reload and saved draft reopening preserve content')
                expect(page.locator('.review-progress li[aria-current=step]')).to_contain_text('Read')
                # Save an owner profile, then verify an exact authorized statement.
                page.locator('#owner-policy').evaluate('(el) => el.open = true')
                page.locator('#approved-actions').fill('We have repaired the coffee machine.')
                page.locator('#profile-name').evaluate("el => el.closest('details').open = true")
                page.locator('#profile-name').fill('demo')
                page.locator('#save-profile').click()
                expect(page.locator('#notice')).to_contain_text('Confirm that the owner authorized')
                page.locator('#policy-confirmed').check()
                page.locator('#save-profile').click()
                expect(page.locator('#notice')).to_contain_text('Business profile saved locally')
                page.locator('#generate').click()
                expect(page.locator('#notice')).to_contain_text('Draft saved')
                assert 'We have repaired the coffee machine.' in page.locator('#reply-editor').input_value()
                assertions.append('Profile saving requires explicit policy confirmation; exact action persists')
                # Follow-up form and checked generation.
                page.locator('#reply-type').select_option('followup')
                page.locator('#original').fill(REVIEW := 'Cold coffee and a long wait.')
                page.locator('#previous').fill('Thank you for your review. We are sorry about the coffee.')
                page.locator('#review').fill('Update: the coffee was still cold.')
                expect(page.locator('#stars')).to_be_disabled()
                page.locator('#generate').click()
                expect(page.locator('#notice')).to_contain_text('Draft saved')
                assert 'update' in page.locator('#reply-editor').input_value().lower()
                expect(page.locator('#stars')).to_be_disabled()
                assertions.append('Follow-up view retains thread context and disables unused rating')
                # Literal hostile markup remains text, never executable HTML.
                page.locator('#reply-editor').fill(page.locator('#reply-editor').input_value() + '<img src=x onerror="window.injected=1">')
                page.locator('#save-edit').click()
                expect(page.locator('#notice')).to_contain_text('Edits saved')
                assert page.evaluate('window.injected || 0') == 0
                assertions.append('Edited HTML stays inert text')
                # Demonstrate retry wiring using controlled output, never a real-model claim.
                page.get_by_role('button', name='Complaint', exact=True).click()
                replies = iter([original + '\nWe will refund you.', original])
                workspace.caller = lambda *unused: next(replies)
                page.locator('#engine-mode').select_option('gemma')
                page.locator('#generate').click()
                expect(page.locator('#notice')).to_contain_text('Draft saved')
                expect(page.locator('#draft-source')).to_contain_text('retry')
                page.locator('#trace-panel').evaluate('(el) => el.open = true')
                expect(page.locator('#trace-content')).to_contain_text('Attempt 2')
                assertions.append('Controlled model rejection and retry are visible in generation details')
                # Finish screenshots in honest template mode.
                page.locator('#engine-mode').select_option('offline')
                page.locator('#reroll').click()
                expect(page.locator('#notice')).to_contain_text('New draft saved')
                page.locator('#trace-panel').evaluate('(el) => el.open = false')
                page.locator('#owner-policy').evaluate('(el) => el.open = false')
                page.locator('#profile-name').evaluate("el => el.closest('details').open = false")
                if args.screenshots:
                    page.evaluate('window.scrollTo(0, 0)')
                    page.screenshot(path=str(args.screenshots / 'workspace-desktop.png'), full_page=True)
                page.set_viewport_size({'width': 390, 'height': 844})
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                expect(page.locator('#reply-editor')).to_be_visible()
                if args.screenshots:
                    page.evaluate('window.scrollTo(0, 0)')
                    page.screenshot(path=str(args.screenshots / 'workspace-mobile.png'), full_page=True)
                assertions.append('390px responsive layout has no horizontal overflow')
                external = [url for url in requests if not url.startswith((server.origin, 'blob:' + server.origin))]
                assert not external, external
                assert not errors, errors
                assertions.append('No browser JavaScript errors or external UI requests')
                blocked = browser.new_context()
                blocked.add_init_script("Object.defineProperty(window, 'sessionStorage', {get() {throw new Error('Controlled blocked storage');}})")
                blocked_page = blocked.new_page()
                blocked_page.goto(server.launch_url)
                expect(blocked_page.locator('#generate')).to_be_enabled()
                expect(blocked_page.locator('#session-storage-note')).to_be_visible()
                assert '#token=' not in blocked_page.url
                blocked_page.get_by_role('button', name='Complaint', exact=True).click()
                blocked_page.locator('#generate').click()
                expect(blocked_page.locator('#draft-status')).to_have_text('Needs review')
                assertions.append('Controlled blocked session-storage getter still permits template drafting with a current launcher link')
                blocked.close()
                browser.close()
        finally:
            server.shutdown(); server.server_close(); thread.join(timeout=2)
    print(json.dumps({'passed': len(assertions), 'checks': assertions,
                      'model_evidence': 'Controlled stand-in responses only; no live Gemma inference'}, indent=2))


if __name__ == '__main__':
    main()
