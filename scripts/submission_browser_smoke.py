"""Exercise the real handoff UI with synthetic confirmations, not user attestations."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
from zipfile import ZipFile

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from rrw_web import LocalServer
from rrw_workspace import Workspace
from playwright.sync_api import sync_playwright, expect


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--screenshots',type=Path);args=ap.parse_args()
    if args.screenshots:args.screenshots.mkdir(parents=True,exist_ok=True)
    checks=[]
    with tempfile.TemporaryDirectory() as tmp:
        workspace=Workspace(tmp);server=LocalServer(workspace,0)
        thread=threading.Thread(target=server.serve_forever,kwargs={'poll_interval':.03},daemon=True);thread.start()
        try:
            with sync_playwright() as pw:
                options={'headless':True}
                if os.getenv('RRW_CHROMIUM_EXECUTABLE'):options['executable_path']=os.environ['RRW_CHROMIUM_EXECUTABLE']
                browser=pw.chromium.launch(**options)
                context=browser.new_context(viewport={'width':1480,'height':1050},reduced_motion='reduce')
                page=context.new_page();errors=[];requests=[]
                page.on('pageerror',lambda exc:errors.append(str(exc)))
                page.on('request',lambda req:requests.append(req.url))
                page.goto(server.launch_url);expect(page.locator('#generate')).to_be_enabled()
                page.locator('#view-submission').click()
                expect(page.locator('#submission-recorded')).to_contain_text('matches the drafting engine')
                expect(page.locator('#draft-panel')).to_be_hidden();expect(page.locator('#quality-panel')).to_be_hidden()
                expect(page.locator('#submission-final')).to_be_disabled()
                assert page.locator('#submission-confirmations input:checked').count()==0
                checks.append('Submission Desk shows existing evidence and unknown confirmations, not a completed entry')
                page.locator('#submission-demo').fill('https://localhost/video')
                page.locator('#submission-save').click()
                expect(page.locator('#notice')).to_contain_text('stable public/unlisted HTTPS')
                assert page.locator('#submission-demo').input_value()=='https://localhost/video'
                checks.append('Local/private demo links are rejected without losing the editor value')
                page.locator('#submission-demo').fill('https://youtu.be/synthetic-ui-test-one')
                page.locator('#submission-save').click()
                expect(page.locator('#notice')).to_contain_text('Checklist saved')
                expect(page.locator('#submission-demo_accessible_to_judges')).not_to_be_checked()
                page.locator('#submission-demo_accessible_to_judges').check()
                page.locator('#submission-rules_reviewed').check()
                page.locator('#submission-save').click();expect(page.locator('#submission-save')).to_be_disabled()
                checks.append('User-directed synthetic checkbox actions persist only in temporary test state')
                second=context.new_page();second.goto(server.launch_url);expect(second.locator('#generate')).to_be_enabled()
                second.locator('#view-submission').click();expect(second.locator('#submission-demo')).to_have_value('https://youtu.be/synthetic-ui-test-one')
                page.locator('#submission-demo').fill('https://youtu.be/synthetic-ui-test-two')
                expect(page.locator('#submission-demo_accessible_to_judges')).not_to_be_checked()
                page.locator('#submission-save').click();expect(page.locator('#submission-save')).to_be_disabled()
                second.locator('#submission-development_window_confirmed').check();second.locator('#submission-save').click()
                expect(second.locator('#notice')).to_contain_text('changed. Reload')
                second.once('dialog',lambda dialog:dialog.accept());second.close()
                checks.append('Changed links invalidate old access confirmation; stale second-tab writes are rejected')
                with page.expect_download() as event:page.locator('#submission-post').click()
                post=Path(tmp)/'download.md';event.value.save_as(post)
                text=post.read_text(encoding='utf-8');assert 'published: false' in text and 'TODO' in text and 'synthetic-ui-test-two' in text
                checks.append('Actual Markdown download has the chosen link, correct tags, draft status and outstanding items')
                (Path(tmp)/'.env').write_text('PRIVATE_ENV_CANARY')
                with page.expect_download() as event:page.locator('#submission-packet').click()
                packet=Path(tmp)/'packet.zip';event.value.save_as(packet)
                with ZipFile(packet) as archive:
                    joined=b'\n'.join(archive.read(n) for n in archive.namelist())
                    assert b'PRIVATE_ENV_CANARY' not in joined and server.token.encode() not in joined
                    assert not json.loads(archive.read('READINESS.json'))['published']
                    assert 'evidence/selected-evaluation.json' not in archive.namelist()
                    manifest=json.loads(archive.read('MANIFEST.json'))['files']
                    assert set(archive.namelist())-{'MANIFEST.json'}==set(manifest)
                    for name,value in manifest.items():assert hashlib.sha256(archive.read(name)).hexdigest()==value['sha256']
                    folder=Path(tmp)/'judge-guide';archive.extractall(folder)
                checks.append('Actual ZIP download is allowlisted, checksum-complete and excludes tokens and private files')
                report=workspace.dispatch('quality-start',{'mode':'offline'})
                workspace.dispatch('quality-step',{'id':report['id'],'revision':report['revision']})
                page.locator('#submission-refresh').click();expect(page.locator('#submission-packet')).to_be_enabled()
                page.locator('#submission-evaluation').select_option(report['id']);page.locator('#submission-save').click()
                expect(page.locator('#submission-evaluation-summary')).to_contain_text('0/3 cases assessed')
                page.locator('#submission-include').check();expect(page.locator('#submission-packet')).to_be_disabled()
                page.locator('#submission-sharing').check();expect(page.locator('#submission-packet')).to_be_enabled()
                expect(page.locator('#submission-final')).to_be_disabled()
                with page.expect_download() as event:page.locator('#submission-packet').click()
                private_packet=Path(tmp)/'explicit.zip';event.value.save_as(private_packet)
                with ZipFile(private_packet) as archive:
                    assert json.loads(archive.read('evidence/selected-evaluation.json'))['execution']=='templates'
                checks.append('Selected evaluation inclusion requires explicit consent and does not make template evidence qualify')
                page.locator('#submission-include').uncheck()
                page.reload();expect(page.locator('#generate')).to_be_enabled();page.locator('#view-submission').click()
                expect(page.locator('#submission-demo')).to_have_value('https://youtu.be/synthetic-ui-test-two')
                expect(page.locator('#submission-include')).not_to_be_checked()
                checks.append('Checklist survives reload; sharing consent is not silently persisted')
                if args.screenshots:page.screenshot(path=str(args.screenshots/'submission-desktop.png'),full_page=True)
                page.set_viewport_size({'width':390,'height':844})
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                if args.screenshots:page.screenshot(path=str(args.screenshots/'submission-mobile.png'),full_page=True)
                checks.append('Submission view fits a 390px viewport without horizontal overflow')
                page.locator('#submission-open-quality').click();expect(page.locator('#quality-panel')).to_be_visible()
                page.locator('#view-drafts').click();expect(page.locator('#compose-form')).to_be_visible()
                checks.append('Original drafting and Quality Lab views remain reachable')
                static_context=browser.new_context(java_script_enabled=False,viewport={'width':1280,'height':900})
                static=static_context.new_page();static.goto((folder/'START_HERE.html').as_uri())
                expect(static.locator('h1')).to_contain_text('refund policy')
                assert static.locator('script').count()==0
                assert static.locator('article').count()==3
                if args.screenshots:static.screenshot(path=str(args.screenshots/'judge-guide.png'),full_page=True)
                static.set_viewport_size({'width':390,'height':844})
                # JS is disabled; compare geometric bounds through locator bounding boxes.
                assert static.locator('main').bounding_box()['width']<=390
                checks.append('Extracted judge guide opens from disk with JavaScript disabled and shows three recorded cases')
                assert not errors,errors
                assert all(url.startswith((server.origin,'blob:'+server.origin)) for url in requests),requests
                checks.append('No JavaScript errors, external page assets or automatic publication requests')
                browser.close()
        finally:
            server.shutdown();server.server_close();thread.join(2)
    print(json.dumps({'passed':len(checks),'checks':checks,'attestations':'Synthetic test clicks in temporary state only; no real operator confirmations.'},indent=2))


if __name__=='__main__':main()
