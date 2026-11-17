"""V2 usability regressions using real UI actions and isolated progress.

Checks illustrated assets, keyboard containment, useful teaching beside an
unfinished program, error-to-explanation navigation, responsive Windows sizes,
reload, and pause. It does not evaluate a human learner or native Windows.
"""
from __future__ import annotations

import contextlib
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

from playwright.sync_api import expect, sync_playwright

from browser_v2_route import ROOT, EXERCISES, complete_mission, open_current_mission, read_state, wait_ready


def main():
    output = ROOT / "artifacts" / "browser-v2-ui"
    output.mkdir(parents=True, exist_ok=True)
    curriculum = json.loads((ROOT / "data/curriculum.json").read_text())
    report = {"passed": False, "checks": [], "browserErrors": [], "externalRequests": [],
              "curriculumSha256": hashlib.sha256((ROOT / "data/curriculum.json").read_bytes()).hexdigest(),
              "appJsSha256": hashlib.sha256((ROOT / "static/app.js").read_bytes()).hexdigest(),
              "limits": ["Linux Chromium; native Windows launch is not covered.",
                         "Automated interactions do not establish human learning outcomes."]}
    interpreter = os.environ.get("THE_GAME_PYTHON", sys.executable)
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="persian-v2-ui-") as temp:
        log = open(Path(temp) / "server.log", "w")
        process = subprocess.Popen([interpreter, str(ROOT / "server.py"), "--port", "0", "--data-dir", str(Path(temp) / "save"), "--no-browser"],
                                   cwd=ROOT, stdout=subprocess.PIPE, stderr=log, text=True)
        try:
            url = wait_ready(process)
            with sync_playwright() as pw:
                browser = pw.chromium.launch(executable_path=os.environ.get("CHROMIUM_PATH", "/usr/bin/chromium"), headless=True,
                                             args=["--no-sandbox", "--disable-dev-shm-usage"])
                page = browser.new_page(viewport={"width": 1440, "height": 1000}, reduced_motion="reduce")
                page.on("pageerror", lambda e: report["browserErrors"].append(str(e)))
                page.on("request", lambda r: report["externalRequests"].append(r.url) if r.url.startswith("http") and not r.url.startswith(url) else None)
                page.on("dialog", lambda d: d.accept())
                page.goto(url, wait_until="networkidle")
                expect(page.locator("#begin")).to_be_visible()
                assert page.title() == "persian fairytale. V2"
                assert page.locator("body").get_attribute("data-art-ready") == "2"
                assert "persian-scenes.png" in page.locator(".welcome-art").get_attribute("style")
                expect(page.locator("#begin")).to_be_focused()
                page.keyboard.press("Shift+Tab")
                expect(page.locator("#begin")).to_be_focused()
                page.screenshot(path=str(output / "01-welcome.png"), full_page=True)
                page.locator("#begin").click()
                report["checks"].append("Original scene and portrait atlases load locally; exact title; welcome focus stays in modal.")

                for mission in curriculum["missions"][:3]:
                    complete_mission(page, mission)
                mission = curriculum["missions"][3]
                open_current_mission(page, mission)
                while page.locator("#nextLine").count():
                    page.locator("#nextLine").click()
                expect(page.locator("[data-lesson-section]").first).to_be_visible()
                page.locator("#toActivity").focus()
                page.keyboard.press("Tab")
                expect(page.locator("#closeDialog")).to_be_focused()
                page.locator("#toActivity").click()
                draft = '# Unfinished program intentionally saved by the UI test\nraise ValueError("inspect teaching")\n'
                page.locator("#codeEditor").fill(draft)
                page.locator("#helpSection").select_option(index=1)
                page.locator('[data-help-source="mission"]').click()
                page.locator('[data-help-source="exercise"]').click()
                expect(page.locator("#codeEditor")).to_have_value(draft)
                page.locator("#runCode").click()
                expect(page.locator("#runCode")).to_be_enabled(timeout=45000)
                expect(page.locator("#activityNext")).to_be_disabled()
                expect(page.locator("[data-code-support]").first).to_be_visible()
                worked_label = page.locator("[data-code-support]").nth(1).inner_text()
                page.locator("[data-code-support]").nth(1).click()
                expect(page.locator("#codeEditor")).to_have_value(draft)
                expect(page.locator(".help-page h4")).to_have_text(worked_label)
                page.locator("#activityBack").click()
                page.locator("#toActivity").click()
                expect(page.locator("#codeEditor")).to_have_value(draft)
                expect(page.locator("#saveStatus")).to_have_text("✓ Сохранено", timeout=10000)
                before = read_state(page)
                assert before["missions"]["m04"]["hints"] == 0
                page.reload(wait_until="networkidle")
                page.locator("#begin").click()
                expect(page.locator("#codeEditor")).to_have_value(draft)
                expect(page.locator("#activityNext")).to_be_disabled()
                report["checks"].append("Unfinished failed code survives help tabs, worked example, full theory and reload; reading explanations costs no hint.")

                page.locator("#codeEditor").fill(EXERCISES[mission["activity"]["exerciseId"]]["solution"])
                page.locator("#runCode").click()
                expect(page.locator("#activityNext")).to_be_enabled(timeout=45000)
                expect(page.locator("#codeOutput")).to_contain_text("✓ Проверка пройдена")
                report["checks"].append("Corrected program really executes and unlocks the next step.")

                for width, height in [(1440, 1000), (1366, 768), (1024, 768), (800, 900)]:
                    page.set_viewport_size({"width": width, "height": height})
                    page.locator("#codeEditor").scroll_into_view_if_needed()
                    bounds = page.evaluate("""() => {
                      const work=document.querySelector('.practice-work').getBoundingClientRect();
                      const help=document.querySelector('#practiceHelp').getBoundingClientRect();
                      const dialog=document.querySelector('#dialog');
                      return {horizontal:document.documentElement.scrollWidth>innerWidth+1,
                              dialogOverflow:dialog.scrollWidth>dialog.clientWidth+1,
                              sideBySide:help.left>=work.right-1};
                    }""")
                    assert not bounds["horizontal"] and not bounds["dialogOverflow"], (width, bounds)
                    if width >= 1024:
                        assert bounds["sideBySide"], (width, bounds)
                    page.screenshot(path=str(output / f"02-practice-{width}.png"), full_page=True)
                report["checks"].append("1440, 1366, 1024 and 800 px layouts have no horizontal overflow; theory remains beside code at desktop widths.")

                page.set_viewport_size({"width": 1440, "height": 1000})
                page.keyboard.press("Escape")
                expect(page.locator("#resume")).to_be_visible()
                expect(page.locator("#saveStatus")).to_have_text("✓ Сохранено", timeout=10000)
                time_before = read_state(page)["activeSeconds"]
                pixels_before = page.locator("#world").evaluate("canvas => canvas.toDataURL()")
                page.wait_for_timeout(1200)
                assert page.locator("#world").evaluate("canvas => canvas.toDataURL()") == pixels_before
                assert read_state(page)["activeSeconds"] == time_before
                page.locator("#resume").click()
                expect(page.locator("#codeEditor")).to_have_value(EXERCISES[mission["activity"]["exerciseId"]]["solution"])
                report["checks"].append("Pause freezes the world and active-time counter and preserves the successful program on resume.")
                assert not report["browserErrors"], report["browserErrors"]
                assert not report["externalRequests"], report["externalRequests"]
                browser.close()
            report["passed"] = True
        except Exception as error:
            report["error"] = f"{type(error).__name__}: {error}"
            with contextlib.suppress(Exception):
                page.screenshot(path=str(output / "failure.png"), full_page=True)
            raise
        finally:
            report["seconds"] = round(time.monotonic() - started, 2)
            (output / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))
            process.terminate()
            try:
                process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                process.kill()
            log.close()
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
