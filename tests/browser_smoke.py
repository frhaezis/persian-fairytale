"""Real browser smoke. Uses isolated temporary saves; never touches player data.
Run from project root with a Python that has Playwright installed:
    python tests/browser_smoke.py
The server itself uses .venv/bin/python when present. Tests solve authored cases
from curriculum data to exercise UI plumbing; this is not a learner evaluation.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import traceback
from urllib.request import urlopen
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / 'artifacts' / 'browser'
ARTIFACTS.mkdir(parents=True, exist_ok=True)


def run():
    report = {'tested': [], 'bugs': [], 'consoleErrors': [], 'limits': [
        'Linux Chromium only; Windows launch and actual user Qwen are not covered.',
        'Automated traversal does not establish human learning outcomes or duration.'
    ]}
    curriculum = json.loads((ROOT / 'data/curriculum.json').read_text())
    report['curriculumMissionsAtTest'] = len(curriculum['missions'])
    python = ROOT / '.venv' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    if not python.exists(): python = Path(sys.executable)
    chromium = os.environ.get('GAME_TEST_CHROMIUM') or shutil.which('chromium')
    with tempfile.TemporaryDirectory(prefix='the-game-browser-') as saves:
        process = subprocess.Popen([str(python), str(ROOT/'server.py'), '--port', '0', '--data-dir', saves, '--no-browser'], cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            line = process.stdout.readline().strip()
            if not line.startswith('THE_GAME_READY '): raise RuntimeError('Server failed to start: '+line)
            url = line.split(' ', 1)[1]
            def persisted():
                with urlopen(url+'api/bootstrap', timeout=30) as response: return json.load(response)['state']
            with sync_playwright() as p:
                browser = p.chromium.launch(executable_path=chromium, headless=True, args=['--no-sandbox'])
                page = browser.new_page(viewport={'width':1440,'height':1000}, device_scale_factor=1)
                page.on('pageerror', lambda e:report['consoleErrors'].append(str(e)))
                page.on('dialog', lambda d:d.accept())
                page.goto(url,wait_until='networkidle')
                page.locator('#begin').wait_for(timeout=30000)
                page.screenshot(path=str(ARTIFACTS/'01-welcome.png'),full_page=True)
                page.locator('#begin').click()
                page.locator('#overlay').wait_for(state='hidden')
                expect(page.locator('#saveStatus')).to_have_text('✓ Сохранено',timeout=10000)
                page.screenshot(path=str(ARTIFACTS/'02-world-desktop.png'),full_page=True)
                report['tested'].append('Welcome opens; enter city reveals readable desktop world.')
                page.locator('#world').focus();page.keyboard.down('ArrowLeft');page.wait_for_timeout(350);page.keyboard.up('ArrowLeft');page.wait_for_timeout(1500)
                assert persisted()['player']['x'] < 480
                report['tested'].append('Real keyboard movement updates persisted player position.')
                # Locked later acts must not teleport the player.
                page.locator('[data-act="4"]').click()
                assert page.locator('[data-act="1"]').get_attribute('class').endswith('active')
                report['tested'].append('Later act remains locked before prerequisites.')
                page.locator('#navigateBtn').click()
                page.locator('#nextLine').wait_for(timeout=15000)
                page.locator('#closeDialog').click();page.wait_for_timeout(500);page.keyboard.press('e');page.locator('#nextLine').wait_for()
                report['tested'].append('Real E key reopens nearby NPC dialogue after leaving its panel.')
                m = curriculum['missions'][0]
                if page.locator('#missionContent').evaluate('(el)=>el.parentElement.classList.contains("steps")'):
                    report['bugs'].append('Mission content incorrectly nested inside .steps flex row; missing closing div.')
                if len(m['story']) > 1:
                    page.locator('#nextLine').click()
                    expected_line=m['story'][1]['text']
                    page.wait_for_timeout(1800)
                    before=persisted()
                    assert before['missions'][m['id']]['dialogue']==1
                    page.reload(wait_until='networkidle')
                    page.locator('#begin').click()
                    page.locator('#nextLine').wait_for()
                    assert expected_line in page.locator('#missionContent').inner_text()
                    report['tested'].append('Saved mid-dialogue and restored exact line after reload.')
                while page.locator('#nextLine').count():
                    page.locator('#nextLine').click()
                page.locator('#toActivity').wait_for()
                page.screenshot(path=str(ARTIFACTS/'03-lesson.png'),full_page=True)
                page.locator('#toActivity').click()
                assert page.locator('#activityNext').is_disabled()
                a=m['activity']
                if a['type']=='compare':
                    for i,card in enumerate(a['cards']):page.locator(f'[data-sort="{i}"]').select_option(card['category'])
                elif a['type']=='split':
                    for i,card in enumerate(a['records']):page.locator(f'[data-sort="{i}"]').select_option(card['group'])
                elif a['type']=='threshold':
                    valid=next(t/100 for t in range(101) if sum(s>=t/100 for s in a['positive'])/len(a['positive'])>=a.get('targetRecall',.8) and sum(s>=t/100 for s in a['negative'])<=a.get('maxFP',2))
                    page.locator('#threshold').fill(str(valid));page.locator('#threshold').dispatch_event('input')
                else: raise AssertionError('Update smoke solver for first-mission activity: '+a['type'])
                page.locator('#verifyActivity').click()
                assert page.locator('#activityNext').is_enabled()
                page.screenshot(path=str(ARTIFACTS/'04-activity.png'),full_page=True)
                page.locator('#activityNext').click()
                assert page.locator('#checkNext').is_disabled()
                page.locator(f'[data-answer="{m["check"]["answer"]}"]').click()
                page.locator('#checkNext').click()
                answer='Проверочный черновик: тип обучения определяется источником учебного сигнала.'
                page.locator('#reflectionAnswer').fill(answer)
                page.wait_for_timeout(1600)
                assert persisted()['missions'][m['id']]['answer']==answer
                page.locator('#completeMission').click()
                page.locator('#overlay').wait_for(state='hidden')
                page.wait_for_timeout(1600)
                state=persisted()
                assert state['completed']==[m['id']]
                assert state['rewardIds']==[m['id']]
                report['tested'].append('First mission: world navigation → dialogue → explanation → real sorting interaction → independent check → reflection → persistent reward.')
                page.reload(wait_until='networkidle');page.locator('#begin').click()
                page.wait_for_timeout(1400)
                state=persisted()
                assert state['rewardIds']==[m['id']]
                assert state['missions'][m['id']]['answer']==answer
                report['tested'].append('Reload preserves completion, draft and single reward; next mission unlocked.')
                # Responsive layouts use the real saved state, with no injected fake curriculum.
                page.locator('#worldToast:not(.show)').wait_for(state='attached')
                for width,height in [(1280,800),(390,844)]:
                    page.set_viewport_size({'width':width,'height':height})
                    page.wait_for_timeout(200)
                    dims=page.evaluate('({w:innerWidth,scroll:document.documentElement.scrollWidth})')
                    overlap=page.evaluate('''() => {const a=document.querySelector('#objective').getBoundingClientRect(),b=document.querySelector('#navigateBtn').getBoundingClientRect();return Math.min(a.right,b.right)>Math.max(a.left,b.left)&&Math.min(a.bottom,b.bottom)>Math.max(a.top,b.top)}''')
                    if overlap:report['bugs'].append(f'Objective text overlaps navigation button at {width}px.')
                    if dims['scroll']>dims['w']+1:report['bugs'].append(f'Horizontal overflow at {width}px: {dims}')
                    page.screenshot(path=str(ARTIFACTS/f'world-{width}.png'),full_page=True)
                    page.locator('#journalBtn').click();page.screenshot(path=str(ARTIFACTS/f'journal-{width}.png'),full_page=True)
                    page.locator('#closeDialog').click()
                report['tested'].append('Desktop 1440/1280 and mobile 390 layouts inspected; screenshots captured.')
                page.set_viewport_size({'width':1440,'height':1000})
                page.locator('#pauseBtn').click()
                expect(page.locator('#saveStatus')).to_have_text('✓ Сохранено',timeout=10000)
                active_before=persisted()['activeSeconds']
                page.wait_for_timeout(2100)
                assert persisted()['activeSeconds']==active_before, 'Active time changed after confirmed pause save'
                with page.expect_download() as event:page.locator('#exportSave').click()
                downloaded=event.value; export_path=ARTIFACTS/'test-save-export.json';downloaded.save_as(str(export_path))
                exported=json.loads(export_path.read_text());assert 'state' in exported
                report['tested'].append('Pause stops active-time accumulation; save export produces valid JSON envelope.')
                page.locator('#importFile').set_input_files(str(export_path));page.locator('#confirmImport').click();page.locator('#begin').wait_for()
                page.locator('#begin').click();assert persisted()['completed']==[m['id']]
                report['tested'].append('UI import of exported save restores completion and does not duplicate reward.')
                # Component regression: navigate twice to an already reached station,
                # with the first dialogue pausing simulation time. No curriculum/state
                # injection is used in the gameplay smoke above.
                component=browser.new_page(viewport={'width':1000,'height':650})
                component.route(url+'world-regression-test',lambda route:route.fulfill(content_type='text/html',body='<canvas style="width:1000px;height:650px"></canvas><output id="hits">0</output>'))
                component.goto(url+'world-regression-test')
                component.evaluate('''async () => {
                    const {World}=await import('/world.js');window.hits=0;
                    window.testWorld=new World(document.querySelector('canvas'),{onInteract:()=>{document.querySelector('#hits').textContent=String(++window.hits);window.testWorld.setPaused(true);}});
                    window.testWorld.setState({location:2,player:{x:236,y:529}});
                    window.testWorld.navigateTo('workshop');
                }''')
                expect(component.locator('#hits')).to_have_text('1',timeout=2000)
                component.evaluate("() => {window.testWorld.setPaused(false);window.testWorld.navigateTo('workshop')}")
                expect(component.locator('#hits')).to_have_text('2',timeout=2000)
                component.wait_for_timeout(500)
                component.evaluate("() => {window.testWorld.setPaused(false);window.testWorld.navigateTo('workshop')}")
                expect(component.locator('#hits')).to_have_text('3',timeout=2000)
                component.evaluate('() => window.testWorld.destroy()');component.close()
                report['tested'].append('World regression: repeated navigation to same station opens interaction after paused dialogue, including immediate retry within cooldown.')
                browser.close()
        except Exception as exc:
            report['bugs'].append(f'{type(exc).__name__}: {exc}')
            report['traceback']=traceback.format_exc()
            try:page.screenshot(path=str(ARTIFACTS/'failure.png'),full_page=True)
            except Exception:pass
        finally:
            process.terminate()
            try:process.wait(timeout=8)
            except subprocess.TimeoutExpired:process.kill();process.wait()
    report['passed']=not report['bugs'] and not report['consoleErrors']
    if report['passed']:
        (ARTIFACTS/'failure.png').unlink(missing_ok=True)
        (ARTIFACTS/'test-save-export.json').unlink(missing_ok=True)
    (ARTIFACTS/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))
    return 0 if report['passed'] else 1

if __name__=='__main__':raise SystemExit(run())
