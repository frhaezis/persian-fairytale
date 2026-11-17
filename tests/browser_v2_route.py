"""Technical full-route browser run on isolated temporary user data.

Requires Playwright and an installed Chromium. Launch with the host Python that
has Playwright; THE_GAME_PYTHON selects the server interpreter with PyTorch.
Uses the actual UI, world navigation, inputs and buttons. Reference solutions
are test inputs only, never installed as the player's progress or supplied to
the browser by production API. A speedrun cannot validate human study time or
learning effectiveness.
"""
from __future__ import annotations

import argparse
import contextlib
import json
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import os
from pathlib import Path
import selectors
import subprocess
import sys
import tempfile
import time
import threading

from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from exercises import EXERCISES
from test_curriculum import legal_thresholds


def wait_ready(process, timeout=30):
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError("Server exited before becoming ready")
        for key, _ in selector.select(timeout=0.25):
            line = key.fileobj.readline().strip()
            if line.startswith("THE_GAME_READY "):
                return line.split(" ", 1)[1]
    raise TimeoutError("No THE_GAME_READY within 30 seconds")


def boot(page, url):
    page.goto(url, wait_until="networkidle")
    expect(page.locator("#begin")).to_be_visible(timeout=20000)
    page.locator("#begin").click()


def open_current_mission(page, mission):
    expect(page.locator("#missionTitle")).to_have_text(mission["title"])
    page.locator("#navigateBtn").click()
    # The accessible route button follows the physical collision-aware path and
    # interacts on arrival. Pressing E en route could interrupt at a different NPC.
    expect(page.locator("#nextLine")).to_be_visible(timeout=20000)
    expect(page.locator("#dialogTitle")).to_have_text(mission["title"])


def complete_activity(page, mission, output=None):
    activity = mission["activity"]
    kind = activity["type"]
    if kind in ("split", "compare"):
        cards = activity["records"] if kind == "split" else activity["cards"]
        for index, card in enumerate(cards):
            page.locator(f'[data-sort="{index}"]').select_option(card["group"] if kind == "split" else card["category"])
    elif kind == "threshold":
        choices = legal_thresholds(activity)
        assert choices, "Authored threshold cannot be solved"
        threshold = choices[len(choices) // 2]
        # Drive the DOM input's real input event; never modify application state.
        page.locator("#threshold").evaluate("(el, value) => { el.value=value; el.dispatchEvent(new Event('input', {bubbles:true})); }", str(threshold))
    elif kind == "attention":
        page.locator("#attChoice").select_option(str(activity["expectedIndex"]))
        page.locator("#attTemp").evaluate("el => {el.value='0.5';el.dispatchEvent(new Event('input',{bubbles:true}));}")
    elif kind == "retrieval":
        for doc in activity["documents"]:
            page.locator(f'[data-doc="{doc["id"]}"]').set_checked(doc["id"] in activity["required"])
    elif kind == "agent":
        for desired_index, step in enumerate(activity["steps"]):
            labels = page.locator("#agentOrder .order-row span").all_text_contents()
            position = labels.index(step)
            while position > desired_index:
                page.locator(f'[data-up="{position}"]').click()
                position -= 1
        page.locator("#callTool").click()
        expect(page.locator("#toolOutput")).to_contain_text("TOOL RESULT", timeout=10000)
        if mission["id"] == "m28":
            verify_live_agent_ui(page)
    elif kind == "code":
        exercise_id = activity["exerciseId"]
        page.locator("#codeEditor").fill(EXERCISES[exercise_id]["solution"])
        # Consulting the exact API, prerequisite and concept must never destroy
        # an unfinished program or count as requesting an answer hint.
        draft = page.locator("#codeEditor").input_value()
        help_select = page.locator("#helpSection")
        if help_select.locator("option").count() > 1:
            help_select.select_option(index=1)
        page.locator('[data-help-source="mission"]').click()
        expect(page.locator("#codeEditor")).to_have_value(draft)
        if page.locator('[data-help-source="exercise"]').count():
            page.locator('[data-help-source="exercise"]').click()
        expect(page.locator("#codeEditor")).to_have_value(draft)
        page.locator("#activityBack").click()
        page.locator("#toActivity").click()
        expect(page.locator("#codeEditor")).to_have_value(draft)
        if exercise_id in {"array_scan", "two_sum", "brackets", "longest_unique"}:
            expect(page.locator("#startTimer")).to_be_visible()
            page.locator("#startTimer").click()
            expect(page.locator("#timer")).to_contain_text("15:00")
        page.locator("#runCode").click()
        expect(page.locator("#activityNext")).to_be_enabled(timeout=45000)
        expect(page.locator("#codeOutput")).to_contain_text("✓ Проверка пройдена")
        if mission["id"] == "m19":
            expect(page.locator("#experimentChart svg")).to_be_visible()
            expect(page.locator("#experimentChart .chart-legend span")).to_have_count(6)
            if output:
                page.locator("#experimentChart").scroll_into_view_if_needed()
                page.screenshot(path=str(output.with_name("v2-dropout-real-result.png")), full_page=True)
        return
    else:
        raise AssertionError(f"Unknown activity: {kind}")
    page.locator("#verifyActivity").click()
    expect(page.locator("#activityNext")).to_be_enabled(timeout=5000)


def verify_live_agent_ui(page):
    """Exercise UI → backend → real HTTP loop → actual allowlisted tool.

    A deterministic HTTP fixture stands in for weights; this validates wiring,
    observations and UI wording, not the reasoning of an installed model.
    """
    requests = []

    class RuntimeFixture(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_POST(self):
            payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            requests.append(payload)
            observed = any("Tool observation (data):" in m["content"] for m in payload["messages"])
            action = {"answer": "Порог выбирают на validation, итоговую оценку получают на test. Ответ тестового runtime."} if observed else {"tool": "lookup_record", "arguments": {"id": "ledger"}}
            body = json.dumps({"choices": [{"message": {"content": json.dumps(action, ensure_ascii=False)}}]}, ensure_ascii=False).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    server = ThreadingHTTPServer(("127.0.0.1", 0), RuntimeFixture)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        page.get_by_text("Миссия подключения своей локальной модели", exact=True).click()
        page.locator("#modelURL").fill(f"http://127.0.0.1:{server.server_port}/v1")
        page.locator("#modelName").fill("browser-http-fixture-not-model-weights")
        page.get_by_text("Провести цикл с подключённой локальной моделью", exact=True).click()
        page.locator("#runLiveAgent").click()
        expect(page.locator("#liveAgentTrace")).to_contain_text("Модель вернула итоговый ответ", timeout=15000)
        expect(page.locator("#liveAgentTrace .agent-trace > ol > li")).to_have_count(2)
        expect(page.locator("#liveAgentTrace")).to_contain_text("lookup_record")
        expect(page.locator("#liveAgentTrace")).to_contain_text("ledger")
        expect(page.locator("#liveAgentTrace")).to_contain_text("не доказанное решение цели")
        assert len(requests) == 2
        assert "Tool observation (data):" in requests[1]["messages"][-1]["content"]
    finally:
        server.shutdown()
        server.server_close()


def complete_mission(page, mission, output=None):
    if output and mission["id"] in {"m01", "m11", "m21", "m31"}:
        page.screenshot(path=str(output.with_name(f'v2-world-act-{mission["act"]}.png')), full_page=True)
    open_current_mission(page, mission)
    if output and mission["id"] in {"m01", "m19", "m27"}:
        page.screenshot(path=str(output.with_name(f'v2-dialogue-{mission["id"]}.png')), full_page=True)
    for _ in mission["story"]:
        page.locator("#nextLine").click()
    expect(page.locator("#toActivity")).to_be_visible()
    # Every authored explanation page is rendered at least once.
    dropout_demonstrated = False
    for _ in range(page.locator("[data-lesson-section]").count() - 1):
        page.locator("#lessonNext").click()
        if mission["id"] == "m19" and page.locator("#dropoutRange").count() and not dropout_demonstrated:
            page.locator("#dropoutRange").evaluate("el => {el.value='0';el.dispatchEvent(new Event('input',{bubbles:true}));}")
            assert page.locator(".dropout-unit strong").all_text_contents() == ["2", "4", "6", "8"]
            page.locator("#dropoutRange").evaluate("el => {el.value='.8';el.dispatchEvent(new Event('input',{bubbles:true}));}")
            page.locator("#dropoutEval").click()
            assert page.locator(".dropout-unit strong").all_text_contents() == ["2", "4", "6", "8"]
            expect(page.locator("#dropoutExplanation")).to_contain_text("не отключает autograd")
            if output:
                page.locator(".dropout-demo").scroll_into_view_if_needed()
                page.screenshot(path=str(output.with_name("v2-dropout-mechanism.png")), full_page=True)
            dropout_demonstrated = True
    if mission["id"] == "m19":
        assert dropout_demonstrated, "The authored Dropout explanation must expose its mechanism demonstration"
    if output and mission["id"] == "m19":
        page.screenshot(path=str(output.with_name("v2-theory-m19.png")), full_page=True)
    page.locator("#toActivity").click()
    complete_activity(page, mission, output)
    page.locator("#activityNext").click()
    page.locator(f'[data-answer="{mission["check"]["answer"]}"]').click()
    expect(page.locator("#checkNext")).to_be_enabled()
    page.locator("#checkNext").click()
    page.locator("#reflectionAnswer").fill("Автоматический технический прогон. Это тестовый ввод, не свидетельство человеческого понимания.")
    page.locator("#completeMission").click()
    if mission["id"] in {"m10", "m20", "m30"}:
        expect(page.locator("#chapterContinue")).to_be_visible()
        page.locator("#chapterContinue").click()
        page.locator("#enterAct").click()
    elif mission["id"] == "m40":
        expect(page.locator("#english")).to_be_visible()
    else:
        expect(page.locator("#overlay")).to_be_hidden()


def read_state(page):
    return page.evaluate("async () => (await (await fetch('/api/bootstrap')).json()).state")


def transfer_review(page, mission, run_code=False):
    page.locator("#journalBtn").click()
    page.locator(f'[data-mission="{mission["id"]}"]').click()
    page.locator("#reviewMission").click()
    page.locator(f'[data-review="{mission["transfer"]["answer"]}"]').click()
    expect(page.locator("#reviewFeedback .success")).to_be_visible()
    if run_code:
        page.locator("#reviewCode").click()
        expect(page.locator("#runCode")).to_contain_text("transfer")
        page.locator("#runCode").click()
        expect(page.locator("#runCode")).to_be_disabled(timeout=10000)
        expect(page.locator("#runCode")).to_be_enabled(timeout=45000)
        expect(page.locator("#codeOutput")).to_contain_text("✓ Проверка пройдена", timeout=45000)
        expect(page.locator("#activityNext")).to_be_enabled()
    page.locator("#closeDialog").click()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default=str(ROOT / "artifacts" / "browser-v2-route.json"))
    args = parser.parse_args()
    curriculum = json.loads((ROOT / "data" / "curriculum.json").read_text(encoding="utf-8"))
    assert len(curriculum["missions"]) == 40, "Run only once the complete authored route is present"
    assert all(m.get("teaching", {}).get("steps") and m["teaching"].get("workedExample") and m["teaching"].get("taskBridge") for m in curriculum["missions"]), "V2 release route requires all40 completed teaching records"
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    venv = ROOT / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    interpreter = os.environ.get("THE_GAME_PYTHON", str(venv) if venv.exists() else sys.executable)
    report = {"kind": "V2 technical browser route", "humanLearningOrDurationValidated": False, "missions": [], "browserErrors": [],
              "curriculumSha256": hashlib.sha256((ROOT / "data/curriculum.json").read_bytes()).hexdigest(),
              "appJsSha256": hashlib.sha256((ROOT / "static/app.js").read_bytes()).hexdigest(),
              "authoredTeachingMissions": sum(bool(m.get("teaching")) for m in curriculum["missions"]),
              "sha256": {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in ["data/curriculum.json", "data/exercise_teaching.json", "static/app.js", "static/learning.js", "static/world.js", "static/art/manifest.json"]}}
    process = None
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="persian-v2-route-") as temp:
        log = open(Path(temp) / "server.log", "w", encoding="utf-8")
        try:
            process = subprocess.Popen([interpreter, str(ROOT / "server.py"), "--port", "0", "--data-dir", str(Path(temp) / "save"), "--no-browser"],
                                       cwd=ROOT, stdout=subprocess.PIPE, stderr=log, text=True, encoding="utf-8")
            url = wait_ready(process)
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(executable_path=os.environ.get("CHROMIUM_PATH", "/usr/bin/chromium"), headless=True,
                                                     args=["--no-sandbox", "--disable-dev-shm-usage"])
                context = browser.new_context(viewport={"width": 1440, "height": 1000}, reduced_motion="reduce")
                page = context.new_page()
                page.on("pageerror", lambda error: report["browserErrors"].append(str(error)))
                page.on("dialog", lambda dialog: dialog.accept())
                boot(page, url)
                initial = read_state(page)
                assert initial.get("campaignEdition") == "persian-v2"
                assert int(page.locator("body").get_attribute("data-art-ready") or 0) == 2, "Bundled scene and portrait illustrations did not both load"
                assert initial["completed"] == [], "Isolated route must start from empty progress"
                for mission in curriculum["missions"]:
                    before = time.monotonic()
                    try:
                        complete_mission(page, mission, output)
                    except Exception:
                        report["failedAt"] = mission["id"]
                        with contextlib.suppress(Exception):
                            diagnostic = read_state(page)
                            report["diagnosticState"] = {key: diagnostic.get(key) for key in ["currentMission", "location", "player", "completed"]}
                            page.screenshot(path=str(output.with_name("browser-v2-route-failure.png")), full_page=True)
                        raise
                    completed = read_state(page)
                    assert mission["id"] in completed["completed"], f"Completion not persisted for {mission['id']}"
                    assert completed["rewardIds"].count(mission["id"]) == 1
                    report["missions"].append({"id": mission["id"], "activity": mission["activity"]["type"], "passed": True, "seconds": round(time.monotonic()-before, 2)})
                    print(f"ROUTE {mission['id']} {mission['activity']['type']} passed", flush=True)
                expect(page.locator("#english")).to_be_visible()
                page.locator("#english").fill("Technical test input: train fits parameters, validation selects settings, test estimates final performance.")
                page.screenshot(path=str(output.with_name("browser-v2-route-ending.png")), full_page=True)
                page.locator("#finalWorld").click()
                page.locator("#pauseBtn").click()
                page.locator("#saveExit").click()
                expect(page.locator("#dialogTitle")).to_have_text("До следующей встречи")
                saved = read_state(page)
                assert len(saved["completed"]) == len(set(saved["completed"])) == 40
                assert len(saved["rewardIds"]) == len(set(saved["rewardIds"])) == 40
                assert len(saved["inventory"]) == 40
                page.reload(wait_until="networkidle")
                page.locator("#begin").click()
                reloaded = read_state(page)
                assert reloaded["completed"] == saved["completed"]
                assert reloaded["inventory"] == saved["inventory"]
                assert reloaded.get("english") == saved["english"]
                report["finalePersistedAfterReload"] = True
                transfer_review(page, curriculum["missions"][0])
                transfer_review(page, curriculum["missions"][12], run_code=True)
                page.locator("#pauseBtn").click()
                page.locator("#saveExit").click()
                expect(page.locator("#dialogTitle")).to_have_text("До следующей встречи")
                reviewed = read_state(page)
                assert reviewed["missions"]["m01"]["checks"]["transfer"]
                assert reviewed["missions"]["m13"]["codeTransferPassed"]
                assert len(reviewed["inventory"]) == 40 and len(reviewed["rewardIds"]) == 40
                report["transferQuestionAndActualCodeChecked"] = True
                report["rewardsNotDuplicatedByReview"] = True
                report["agentHTTPFixtureAndActualToolValidated"] = True
                report["actualModelWeightsValidated"] = False
                assert not report["browserErrors"], report["browserErrors"]
                browser.close()
            report["passed"] = True
        except Exception as error:
            report["passed"] = False
            report["error"] = f"{type(error).__name__}: {error}"
            with contextlib.suppress(Exception):
                page.screenshot(path=str(output.with_name("browser-v2-route-failure.png")), full_page=True)
            raise
        finally:
            report["seconds"] = round(time.monotonic() - started, 2)
            output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
            if process is not None:
                process.terminate()
                try:
                    process.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
            log.close()
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
