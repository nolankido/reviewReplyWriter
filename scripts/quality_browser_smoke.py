"""Real browser interactions for Quality Lab; template fixtures only, no AI claims."""
import argparse
import json
import os
from pathlib import Path
import sys
import tempfile
import threading

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rrw_web import LocalServer
from rrw_workspace import Workspace
from rrw_evaluate import load_report, live_evidence_blockers
from playwright.sync_api import sync_playwright, expect


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--screenshots', type=Path)
    args=ap.parse_args()
    if args.screenshots: args.screenshots.mkdir(parents=True, exist_ok=True)
    checks=[]
    with tempfile.TemporaryDirectory() as tmp:
        workspace=Workspace(tmp)
        server=LocalServer(workspace,0)
        thread=threading.Thread(target=server.serve_forever,kwargs={'poll_interval':.03},daemon=True)
        thread.start()
        try:
            with sync_playwright() as p:
                options={'headless':True}
                if os.getenv('RRW_CHROMIUM_EXECUTABLE'): options['executable_path']=os.environ['RRW_CHROMIUM_EXECUTABLE']
                browser=p.chromium.launch(**options)
                page=browser.new_page(viewport={'width':1480,'height':1050},reduced_motion='reduce')
                errors=[]; requests=[]
                page.on('pageerror',lambda error: errors.append(str(error)))
                page.on('request',lambda request: requests.append(request.url))
                page.goto(server.launch_url)
                expect(page.locator('#generate')).to_be_enabled()
                page.locator('#view-quality').click()
                expect(page.locator('#quality-panel')).to_be_visible()
                expect(page.locator('#draft-panel')).to_be_hidden()
                page.locator('#quality-start').click()
                expect(page.locator('#quality-run-name')).to_contain_text('templates')
                expect(page.locator('#quality-next')).to_be_enabled()
                page.locator('#quality-next').click()
                expect(page.locator('#quality-case-status')).to_have_text('template')
                expect(page.locator('#quality-metrics')).to_contain_text('Unknown')
                checks.append('Quality Lab creates isolated template evaluation with unknown human quality')
                original=page.locator('#quality-case-reply').inner_text()
                page.locator('#quality-decision').select_option('needs_edit')
                page.locator('#quality-notes').fill('A fictional test assessment, not business-owner feedback. <img src=x onerror="window.bad=1">')
                page.locator('#quality-reviewed').check()
                page.locator('#quality-assess').click()
                expect(page.locator('#notice')).to_contain_text('Human assessment saved')
                assert page.locator('#quality-case-reply').inner_text()==original
                assert page.evaluate('window.bad || 0')==0
                checks.append('Assessment preserves original output and handles markup as inert text')
                def drop_case_response(route):
                    response = route.fetch()
                    assert response.status == 200
                    route.abort('failed')
                page.route('**/api/quality-step', drop_case_response)
                page.locator('#quality-next').click()
                expect(page.locator('#quality-recovery-message')).to_contain_text('uncertain')
                expect(page.locator('#quality-next')).to_be_disabled()
                expect(page.locator('#quality-json')).to_be_disabled()
                page.unroute('**/api/quality-step', drop_case_response)
                pending = 'Controlled pending assessment after a lost case response'
                page.locator('#quality-notes').fill(pending)
                page.locator('#quality-recovery-check').click()
                expect(page.locator('#quality-recovery-message')).to_contain_text('2/3 saved cases')
                expect(page.locator('#quality-notes')).to_have_value(pending)
                expect(page.locator('#quality-recovery-message')).to_be_focused()
                page.once('dialog', lambda dialog: dialog.dismiss())
                page.locator('#quality-recovery-load').click()
                expect(page.locator('#quality-notes')).to_have_value(pending)
                page.once('dialog', lambda dialog: dialog.accept())
                page.locator('#quality-recovery-load').click()
                expect(page.locator('#quality-metrics')).to_contain_text('2/3')
                expect(page.locator('#quality-progress')).to_be_focused()
                expect(page.locator('#quality-reviewed')).not_to_be_checked()
                assert len(workspace.evaluations.dispatch('quality-get', {'id': workspace.evaluations.dispatch('quality-list', {})['runs'][0]['id']})['results']) == 2
                checks.append('Lost case response is checked without replacing pending assessment text, then loaded explicitly without a duplicate case')
                page.locator('#quality-next').click()
                expect(page.locator('#quality-metrics')).to_contain_text('3/3')
                expect(page.locator('#notice')).to_contain_text('Case recorded')
                expect(page.locator('#quality-next')).to_be_disabled()
                expect(page.locator('#quality-evidence-gaps')).to_contain_text('not a real Ollama evaluation')
                assert list(workspace.drafts.iterdir())==[]
                checks.append('All cases checkpointed without creating customer drafts or qualifying as live AI evidence')
                with page.expect_download() as download:
                    page.locator('#quality-json').click()
                path=Path(tmp)/'download.json'; download.value.save_as(path)
                report=load_report(path)
                assert len(report['results'])==3 and live_evidence_blockers(report)
                checks.append('JSON export downloads and passes integrity checks, but cannot satisfy real-model release evidence')
                with page.expect_download() as download:
                    page.locator('#quality-markdown').click()
                path=Path(tmp)/'report.md'; download.value.save_as(path)
                assert 'Unreviewed cases have unknown quality' in path.read_text()
                checks.append('Readable export distinguishes unreviewed results from human judgments')
                page.reload(); expect(page.locator('#view-quality')).to_be_enabled()
                page.locator('#view-quality').click()
                page.locator('#quality-runs').select_option(report['id'])
                expect(page.locator('#quality-progress')).to_contain_text('Run complete')
                page.locator('[data-case-id="cafe-praise"]').click()
                assert 'fictional test assessment' in page.locator('#quality-notes').input_value()
                checks.append('Saved evaluation and assessment survive page reload')
                if args.screenshots:
                    page.evaluate('window.scrollTo(0,0)')
                    page.screenshot(path=str(args.screenshots/'quality-desktop.png'),full_page=True)
                page.set_viewport_size({'width':390,'height':844})
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                if args.screenshots:
                    page.evaluate('window.scrollTo(0,0)')
                    page.screenshot(path=str(args.screenshots/'quality-mobile.png'),full_page=True)
                checks.append('Quality Lab fits 390px viewport without horizontal overflow')
                page.locator('#view-drafts').click(); expect(page.locator('#compose-form')).to_be_visible()
                assert not errors,errors
                assert all(url.startswith((server.origin,'blob:'+server.origin)) for url in requests),requests
                checks.append('Original workspace still accessible; no JavaScript errors or external UI requests')
                browser.close()
        finally:
            server.shutdown(); server.server_close(); thread.join(2)
    print(json.dumps({'passed':len(checks),'checks':checks,'model_evidence':'Templates only; no live Gemma'},indent=2))


if __name__=='__main__': main()
