"""Actual Chromium persistence checks. Seeds isolated TEST state, never user progress.

Run with system Python (Playwright installed) from the project directory.
Uses the project's .venv Python for the local PyTorch backend.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import traceback
from urllib.error import URLError
from urllib.request import Request, ProxyHandler, build_opener

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from saves import default_state, envelope
from exercises import EXERCISES

ARTIFACTS = ROOT / "artifacts"
ARTIFACTS.mkdir(exist_ok=True)
RESULT = {"suite": "real Chromium persistence", "platform": sys.platform,
          "seeded": True, "seedNote": "Isolated synthetic save state opens m11/m10/m01 directly; not a learning or full-route playthrough.",
          "checks": [], "consoleErrors": [], "pageErrors": [], "screenshots": [], "startedAt": time.time()}
OPENER = build_opener(ProxyHandler({}))


def eventually(test, timeout=10, label="condition"):
    deadline = time.monotonic() + timeout
    error = None
    while time.monotonic() < deadline:
        try:
            value = test()
            if value:
                return value
        except Exception as exc:
            error = str(exc)
        time.sleep(.05)
    raise AssertionError(f"Timed out waiting for {label}; last error: {error}")


class Fixture:
    def __init__(self, folder):
        self.folder = Path(folder)
        self.process = None
        self.port = None
        self.base = None
        self.log = None
        self.token = None

    def start(self, port=0):
        marker = self.folder / "server.json"
        marker.unlink(missing_ok=True)
        self.log = open(self.folder / f"server-{time.time_ns()}.log", "wb")
        self.process = subprocess.Popen([str(ROOT / ".venv" / "bin" / "python"), str(ROOT / "server.py"),
                                         "--no-browser", "--port", str(port), "--data-dir", str(self.folder)],
                                        stdout=self.log, stderr=subprocess.STDOUT, cwd=ROOT)
        def ready():
            if self.process.poll() is not None:
                raise AssertionError(f"Server exited {self.process.returncode}")
            if marker.exists():
                data = json.loads(marker.read_text())
                self.port = data["port"]
                self.base = f"http://127.0.0.1:{self.port}"
                self.request("health")
                self.token = self.request("bootstrap")["token"]
                return True
            return False
        eventually(ready, 20, "server readiness")

    def stop(self):
        if self.process and self.process.poll() is None:
            self.process.terminate()
            self.process.wait(timeout=10)
        if self.log:
            self.log.close()

    def request(self, path, body=None):
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["X-Game-Token"] = self.token
        request = Request(self.base + "/api/" + path, data=json.dumps(body).encode() if body is not None else None, headers=headers)
        with OPENER.open(request, timeout=5) as response:
            return json.loads(response.read())

    def state(self):
        return self.request("bootstrap")["state"]

    def seed(self, mission="m11", stage=2, dialogue=0):
        state = default_state()
        number = int(mission[1:])
        state.update(currentMission=mission, location=(number - 1) // 10 + 1,
                     completed=[f"m{i:02}" for i in range(1, number)],
                     rewardIds=[f"m{i:02}" for i in range(1, number)],
                     ui={"kind": "mission", "missionId": mission})
        state["missions"][mission] = {"stage": stage, "dialogue": dialogue, "draft": "# seeded TEST draft\n", "codeInitialized": True,
                                      "answer": "", "activity": {}, "checks": {}, "hints": 0, "attempts": 0, "status": "familiar"}
        self.request("import", {"save": envelope(state)})


def main():
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="the-game-browser-persistence-") as directory:
        fixture = Fixture(directory)
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True, executable_path="/usr/bin/chromium", args=["--no-sandbox"])
            context = browser.new_context(viewport={"width": 1440, "height": 1000}, accept_downloads=True)
            page = None

            def new_page():
                nonlocal page
                if page and not page.is_closed():
                    page.close()
                page = context.new_page()
                page.on("pageerror", lambda error: RESULT["pageErrors"].append(str(error)))
                page.on("console", lambda message: RESULT["consoleErrors"].append(message.text) if message.type == "error" else None)
                page.on("dialog", lambda dialog: dialog.accept())
                page.goto(fixture.base, wait_until="networkidle")
                return page

            def enter():
                page.locator("#begin").wait_for()
                page.locator("#begin").click()

            def screenshot(name):
                path = ARTIFACTS / f"persistence-{name}.png"
                page.screenshot(path=str(path), full_page=True)
                RESULT["screenshots"].append(str(path.relative_to(ROOT)))

            def check(name, fn):
                entry = {"name": name, "startedAt": time.time()}
                try:
                    details = fn()
                    entry.update(status="passed", details=details)
                except Exception as exc:
                    entry.update(status="failed", error=str(exc), traceback=traceback.format_exc())
                    try:
                        screenshot("failure-" + str(len(RESULT["checks"]) + 1))
                    except Exception:
                        pass
                entry["finishedAt"] = time.time()
                RESULT["checks"].append(entry)
                print(json.dumps(entry, ensure_ascii=False), flush=True)
                (ARTIFACTS / "persistence.json").write_text(json.dumps(RESULT, ensure_ascii=False, indent=2), encoding="utf-8")

            try:
                fixture.start()
                fixture.seed()
                new_page(); enter()

                def unsent_draft():
                    editor = page.locator("#codeEditor")
                    editor.wait_for()
                    draft = "# unsent draft: кириллица сохраняется\nvalue = [3, 1, 4]\n"
                    before = time.monotonic(); editor.fill(draft)
                    eventually(lambda: fixture.state()["missions"]["m11"]["draft"] == draft, 3, "draft autosave")
                    delay = time.monotonic() - before
                    assert delay <= 2, f"Draft saved after {delay:.3f}s"
                    page.reload(wait_until="networkidle"); enter()
                    assert page.locator("#codeEditor").input_value() == draft
                    assert fixture.state()["missions"]["m11"]["stage"] == 2
                    screenshot("draft-restored")
                    return {"draftSaveSeconds": round(delay, 3), "exactCodeRestored": True, "stage": 2}
                check("unsent code autosaves within two seconds and restores exact editor", unsent_draft)

                def pause_resume():
                    draft = page.locator("#codeEditor").input_value()
                    page.keyboard.press("Escape"); page.locator("#resume").wait_for()
                    eventually(lambda: fixture.state()["ui"] == {"kind": "mission", "missionId": "m11"}, 3)
                    before = fixture.state()["activeSeconds"]
                    page.wait_for_timeout(1200)
                    after = fixture.state()["activeSeconds"]
                    assert after == before
                    page.keyboard.press("Escape")
                    page.locator("#codeEditor").wait_for()
                    assert page.locator("#codeEditor").input_value() == draft
                    return {"pauseDidNotAccumulateTime": True, "escapeRestoredStage": 2}
                check("pause and Escape resume exact editor and stop active time", pause_resume)

                def changed_during_run():
                    submitted = "import time\ntime.sleep(1.5)\n" + EXERCISES["tensors"]["solution"]
                    replacement = "# typed while previous experiment runs\nvalue = 'not submitted yet'\n"
                    page.locator("#codeEditor").fill(submitted)
                    page.locator("#runCode").click()
                    eventually(lambda: (fixture.state().get("job") or {}).get("status") == "running", 4, "real worker running")
                    page.locator("#codeEditor").fill(replacement)
                    eventually(lambda: "✓ Проверка пройдена" in page.locator("#codeOutput").inner_text(), 12, "torch result")
                    assert page.locator("#activityNext").is_disabled()
                    eventually(lambda: fixture.state()["missions"]["m11"].get("draft") == replacement and not fixture.state()["missions"]["m11"].get("activity", {}).get("passed"), 4)
                    state = fixture.state(); assert state["missions"]["m11"]["lastRunCode"] == submitted
                    screenshot("edited-during-run")
                    page.reload(wait_until="networkidle"); enter()
                    assert page.locator("#codeEditor").input_value() == replacement
                    assert page.locator("#activityNext").is_disabled()
                    return {"actualTorchStatus": state["job"]["status"], "newDraftPreserved": True, "unrunDraftNotCredited": True}
                check("edited code during real successful experiment is preserved and not credited", changed_during_run)

                def restart_refresh():
                    port, old_token = fixture.port, fixture.token
                    fixture.stop(); fixture.start(port)
                    assert fixture.token != old_token
                    draft = "# existing page survives backend token refresh\nnew_value = 29\n"
                    page.locator("#codeEditor").fill(draft)
                    eventually(lambda: fixture.state()["missions"]["m11"]["draft"] == draft, 6, "save after backend restart")
                    assert page.locator("#codeEditor").input_value() == draft
                    screenshot("backend-reconnected")
                    return {"pageReloaded": False, "newTokenObtained": True, "currentDraftSaved": True}
                check("backend restart refreshes token and saves current page draft", restart_refresh)

                def changed_port():
                    draft = page.locator("#codeEditor").input_value(); previous_port = fixture.port
                    page.close(); fixture.stop(); fixture.start()
                    if fixture.port == previous_port:
                        fixture.stop(); fixture.start()
                    assert fixture.port != previous_port
                    new_page(); enter()
                    assert page.locator("#codeEditor").input_value() == draft
                    return {"oldPort": previous_port, "newPort": fixture.port, "sameDraft": True}
                check("different free port restores same saved mission and draft", changed_port)

                def export_import():
                    exported_draft = page.locator("#codeEditor").input_value()
                    page.keyboard.press("Escape")
                    with page.expect_download() as downloaded:
                        page.locator("#exportSave").click()
                    exported = Path(directory) / "exported.json"
                    downloaded.value.save_as(str(exported))
                    page.locator("#resume").click()
                    page.locator("#codeEditor").fill("# newer draft to replace through explicit import\n")
                    page.keyboard.press("Escape")
                    page.locator("#importFile").set_input_files(str(exported))
                    page.locator("#confirmImport").click()
                    page.locator("#begin").wait_for(); enter()
                    page.locator("#codeEditor").wait_for(timeout=5000)
                    assert page.locator("#codeEditor").input_value() == exported_draft
                    page.wait_for_timeout(1100)
                    assert fixture.state()["missions"]["m11"]["draft"] == exported_draft
                    return {"downloadedValidEnvelope": True, "importRestoresUIAndDraft": True, "oldAutosaveCannotOverwriteImport": True}
                check("UI export import preserves saved editor despite pending newer autosave", export_import)

                def timer_interruption():
                    page.close(); fixture.seed("m10"); new_page(); enter()
                    page.locator("#startTimer").click()
                    page.wait_for_timeout(1300)
                    eventually(lambda: fixture.state()["missions"]["m10"].get("rehearsal", {}).get("running"), 3)
                    fixture.stop()  # stop backend before page close so its stale timer cannot be written again
                    page.close(); fixture.start(); new_page(); enter()
                    status = page.locator("#timerStatus").inner_text()
                    assert "прервана" in status
                    timer = fixture.state()["missions"]["m10"]["rehearsal"]
                    assert timer["interrupted"] and not timer["running"]
                    assert 890 <= timer["remaining"] <= 900
                    screenshot("timer-interrupted")
                    return {"interrupted": timer["interrupted"], "remainingSecondsPreserved": timer["remaining"]}
                check("restart interrupts a real 15-minute rehearsal and preserves remaining time", timer_interruption)

                def dialogue_restore():
                    page.close(); fixture.seed("m01", stage=0, dialogue=1); new_page(); enter()
                    expected = page.locator(".quote").inner_text()
                    page.keyboard.press("Escape"); page.locator("#saveExit").click()
                    page.get_by_text("ЗАПИСЬ ПОДТВЕРЖДЕНА").wait_for()
                    page.reload(wait_until="networkidle"); enter()
                    assert page.locator(".quote").inner_text() == expected
                    assert fixture.state()["missions"]["m01"]["dialogue"] == 1
                    screenshot("dialogue-restored")
                    return {"dialogueLine": 1, "saveExitConfirmedBeforeReload": True, "sameDialogueText": True}
                check("save and exit midway through dialogue restores exact line", dialogue_restore)

                def corruption_recovery():
                    page.keyboard.press("Escape")
                    page.locator("#saveExit").click(); page.get_by_text("ЗАПИСЬ ПОДТВЕРЖДЕНА").wait_for()
                    page.close(); fixture.stop()
                    primary = Path(directory) / "save.json"
                    backup = json.loads((Path(directory) / "save.previous.json").read_text())
                    primary.write_text("{ damaged isolated TEST save", encoding="utf-8")
                    fixture.start(); new_page()
                    page.locator("#recover").wait_for()
                    assert primary.read_text() == "{ damaged isolated TEST save"
                    assert page.locator("#recover").is_enabled()
                    screenshot("corrupt-save-blocked")
                    page.locator("#recover").click(); enter()
                    state = fixture.state()
                    assert state["currentMission"] == backup["state"]["currentMission"]
                    assert state["missions"]["m01"]["dialogue"] == backup["state"]["missions"]["m01"]["dialogue"]
                    assert list(Path(directory).glob("save.before-recovery.*.json"))
                    screenshot("backup-restored")
                    return {"damagedPrimaryNotOverwritten": True, "backupRestored": True, "damagedBytesPreserved": True}
                check("corrupted test save shows recovery screen and restores previous working backup", corruption_recovery)
            finally:
                browser.close(); fixture.stop()
    RESULT["elapsedSeconds"] = round(time.monotonic() - started, 2)
    RESULT["passed"] = sum(item["status"] == "passed" for item in RESULT["checks"])
    RESULT["failed"] = sum(item["status"] == "failed" for item in RESULT["checks"])
    RESULT["finishedAt"] = time.time()
    (ARTIFACTS / "persistence.json").write_text(json.dumps(RESULT, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"passed": RESULT["passed"], "failed": RESULT["failed"], "pageErrors": RESULT["pageErrors"], "elapsedSeconds": RESULT["elapsedSeconds"]}), flush=True)
    return 1 if RESULT["failed"] or RESULT["pageErrors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
