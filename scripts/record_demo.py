"""Record the duplicate-billing owner-control workflow. Does not publish anything.

Developer tools: Playwright/Chromium, plus ffmpeg for MP4 conversion.
python scripts/record_demo.py --output evidence/demo [--live]
Without --live the recording is explicitly a no-AI template demonstration.
Automated review-checkbox clicks are interface tests, never owner endorsements.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import rrw_web
from rrw_workspace import Workspace
from rrw_evaluate import source_snapshot
from playwright.sync_api import sync_playwright, expect


def stamp(seconds):
    ms = max(0, round(seconds * 1000))
    hours, ms = divmod(ms, 3600000)
    minutes, ms = divmod(ms, 60000)
    secs, ms = divmod(ms, 1000)
    return f'{hours:02}:{minutes:02}:{secs:02},{ms:03}'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--live', action='store_true')
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    cues = []
    metadata = {'fictional_review': True, 'automated_walkthrough': True,
                'owner_endorsement': False, 'requested_live': args.live,
                'scenario': 'duplicate-billing', 'human_assessment': False,
                'drafting_sources': source_snapshot()}
    with tempfile.TemporaryDirectory() as tmp:
        workspace = Workspace(tmp)
        server = rrw_web.LocalServer(workspace, 0)
        thread = threading.Thread(target=server.serve_forever, kwargs={'poll_interval': .05}, daemon=True)
        thread.start()
        try:
            with sync_playwright() as pw:
                launch = {'headless': True}
                if os.getenv('RRW_CHROMIUM_EXECUTABLE'):
                    launch['executable_path'] = os.environ['RRW_CHROMIUM_EXECUTABLE']
                browser = pw.chromium.launch(**launch)
                context = browser.new_context(viewport={'width': 1440, 'height': 1000},
                    record_video_dir=str(out / 'raw'), record_video_size={'width': 1440, 'height': 1000},
                    reduced_motion='reduce', permissions=['clipboard-read', 'clipboard-write'])
                page = context.new_page()
                started = time.monotonic()
                def cue(text, pause=3):
                    cues.append((time.monotonic() - started, text))
                    page.wait_for_timeout(pause * 1000)
                page.goto(server.launch_url)
                expect(page.locator('#generate')).to_be_enabled()
                cue('Review Reply Writer | Actual application, fictional review.\nAutomated walkthrough, not customer endorsement.', 5)
                page.get_by_role('button', name='Duplicate billing', exact=True).click()
                expect(page.locator('#review')).to_have_value(re.compile('charged twice'))
                expect(page.locator('#offer')).to_have_value('')
                expect(page.locator('#approved-actions')).to_have_value('')
                page.locator('#engine-mode').select_option('gemma' if args.live else 'offline')
                cue('1. Start with the review and owner policy.\nNo compensation is authorized in this example.', 4)
                page.locator('#generate').click()
                cue('2. ' + ('Requesting local Gemma. The actual result label follows.' if args.live else 'Template preview only. No AI model is called.'), 1)
                expect(page.locator('#draft-status')).to_have_text('Needs review', timeout=400000)
                original = page.locator('#reply-editor').input_value()
                label = page.locator('#draft-source').inner_text()
                metadata['observed_engine_label'] = label
                metadata['reply'] = original
                page.locator('#reply-editor').scroll_into_view_if_needed()
                cue('3. Actual source: ' + label + '.\nRead the duplicate-charge and unanswered-question details.', 7)
                for detail in page.locator('#review-evidence details').all():
                    detail.locator('summary').click()
                expect(page.locator('#review-evidence')).to_contain_text('charged twice')
                cue('Compare Details to keep with the customer wording.\nA detected mention is not proof of understanding.', 5)
                page.screenshot(path=str(out / 'draft-desktop.png'), full_page=True)
                page.locator('#reply-editor').fill(original + '\nWe will give you a full refund.')
                page.locator('#save-edit').click()
                expect(page.locator('#draft-status')).to_have_text('Needs changes')
                expect(page.locator('#approve')).to_be_disabled()
                expect(page.locator('#copy')).to_be_disabled()
                cue('4. Deliberately add an unauthorized refund.\nSave & recheck blocks approval and export.', 7)
                page.screenshot(path=str(out / 'blocked-edit.png'), full_page=True)
                page.locator('#reply-editor').fill(original)
                page.locator('#save-edit').click()
                expect(page.locator('#draft-status')).to_have_text('Needs review')
                cue('5. Remove the unauthorized promise and recheck.\nPassing checks still requires a human decision.', 5)
                page.locator('#human-reviewed').check()
                page.locator('#approve').click()
                expect(page.locator('#copy')).to_be_enabled()
                page.locator('#copy').click()
                expect(page.locator('#notice')).to_contain_text(re.compile('Approved reply copied|Automatic copy is unavailable'))
                if page.locator('#manual-copy-panel').is_visible():
                    expect(page.locator('#manual-copy-text')).to_have_value(original)
                    cue('Automatic copy was unavailable.\nThe read-only approved text is available for manual copying.', 4)
                else:
                    expect(page.locator('#notice')).to_contain_text('Approved reply copied')
                cue('6. Demonstrating the approval controls.\nThese automated clicks are not a real owner assessment.', 6)
                page.locator('#view-quality').click()
                cue('7. Quality Lab keeps raw attempts, failures and assessments.\nNo customer replies are posted automatically.', 6)
                page.screenshot(path=str(out / 'quality-lab.png'), full_page=True)
                ended = time.monotonic() - started
                path = page.video.path()
                context.close()
                browser.close()
                shutil.copyfile(path, out / 'walkthrough.webm')
                metadata['duration_seconds'] = round(ended, 2)
        finally:
            server.shutdown(); server.server_close(); thread.join(timeout=2)
    srt = []
    if source_snapshot() != metadata['drafting_sources']:
        raise RuntimeError('Drafting sources changed during recording. Preserve the raw capture and record again.')
    for index, (start, text) in enumerate(cues):
        end = cues[index + 1][0] if index + 1 < len(cues) else ended
        srt.append(f'{index+1}\n{stamp(start)} --> {stamp(end)}\n{text}\n')
    (out / 'captions.srt').write_text('\n'.join(srt), encoding='utf-8')
    (out / 'recording.json').write_text(json.dumps(metadata, indent=2), encoding='utf-8')
    if shutil.which('ffmpeg'):
        subprocess.run(['ffmpeg', '-y', '-i', 'walkthrough.webm', '-vf', 'subtitles=captions.srt',
            '-c:v', 'libx264', '-preset', 'fast', '-crf', '23', '-pix_fmt', 'yuv420p',
            '-movflags', '+faststart', 'walkthrough.mp4'], cwd=out, check=True,
            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    print(json.dumps(metadata, indent=2))


if __name__ == '__main__':
    main()
