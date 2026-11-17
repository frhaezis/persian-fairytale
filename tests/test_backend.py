"""Behavioral save/server tests; only temporary test data is damaged."""
from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from urllib.error import HTTPError
from urllib.request import Request, build_opener, ProxyHandler

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from saves import SaveError, SaveStore, default_state, envelope, canonical
from model_adapter import call_tool, inspect_model, local_chat


class SaveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="the-game-save-test-")
        self.store = SaveStore(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_draft_dialogue_world_roundtrip_and_deduplicate(self):
        state = default_state()
        state.update(location=3, player={"x": 123.5, "y": 321}, currentMission="m22", completed=["m01", "m01"], rewardIds=["lamp", "lamp"])
        state["missions"]["m22"] = {"draft": "# ещё не запускал\nответ = 42", "dialogue": 2, "stage": 3,
                                    "activity": {"threshold": .7}, "answer": "Проверю на новых данных", "hints": 1}
        self.store.save(state)
        loaded = SaveStore(self.temp.name).load()
        self.assertEqual(loaded["missions"], state["missions"])
        self.assertEqual(loaded["player"], state["player"])
        self.assertEqual(loaded["completed"], ["m01"])
        self.assertEqual(loaded["rewardIds"], ["lamp"])

    def test_corruption_never_overwrites_and_backup_restores(self):
        state = default_state(); state["lastAction"] = "first"
        self.store.save(state)
        state["lastAction"] = "second"; self.store.save(state)
        self.store.path.write_text("{broken TEST DATA", encoding="utf-8")
        with self.assertRaises(SaveError):
            self.store.load()
        with self.assertRaises(SaveError):
            self.store.save(default_state())
        self.assertEqual(self.store.path.read_text(), "{broken TEST DATA")
        recovered = self.store.recover()
        self.assertEqual(recovered["lastAction"], "first")
        self.assertTrue(list(self.store.directory.glob("save.before-recovery.*.json")))

    def test_export_import_checks_checksum(self):
        state = default_state(); state["missions"]["m04"] = {"draft": "x = 6"}
        self.store.save(state)
        exported = self.store.export()
        state["missions"]["m04"]["draft"] = "x = 7"; self.store.save(state)
        self.assertEqual(self.store.import_save(exported)["missions"]["m04"]["draft"], "x = 6")
        exported["state"]["missions"]["m04"]["draft"] = "tampered"
        with self.assertRaises(SaveError):
            self.store.import_save(exported)

    def test_restart_marks_unfinished_job_and_timer(self):
        state = default_state()
        state["job"] = {"jobId": "j", "status": "running"}
        state["rehearsal"].update(running=True, remaining=301)
        state["missions"]["m01"] = {"draft": "while True: pass", "rehearsal": {"remaining": 235, "running": True, "interrupted": False}}
        self.store.save(state)
        restarted = SaveStore(self.temp.name).mark_interrupted()
        self.assertEqual(restarted["job"]["status"], "interrupted")
        self.assertTrue(restarted["rehearsal"]["interrupted"])
        self.assertEqual(restarted["rehearsal"]["remaining"], 301)
        self.assertEqual(restarted["missions"]["m01"]["draft"], "while True: pass")
        self.assertTrue(restarted["missions"]["m01"]["rehearsal"]["interrupted"])
        self.assertFalse(restarted["missions"]["m01"]["rehearsal"]["running"])
        self.assertEqual(restarted["missions"]["m01"]["rehearsal"]["remaining"], 235)

    def test_missing_primary_with_backup_requires_recovery(self):
        self.store.save(default_state()); self.store.save(default_state()); self.store.path.unlink()
        with self.assertRaises(SaveError):
            self.store.load()

    def test_bad_version_and_nan_rejected(self):
        state = default_state(); state["version"] = 99
        with self.assertRaises(SaveError):
            self.store.save(state)
        state = default_state(); state["player"]["x"] = float("nan")
        with self.assertRaises(SaveError):
            self.store.save(state)

    def test_old_edition_import_preserves_current_profile(self):
        state = default_state()
        state["missions"]["m01"] = {"draft": "# V2 draft\nanswer = 7"}
        self.store.save(state)
        before = self.store.path.read_bytes()
        old = self.store.export()
        old["state"].pop("campaignEdition")
        old["checksum"] = hashlib.sha256(canonical(old["state"])).hexdigest()
        with self.assertRaises(SaveError):
            self.store.import_save(old)
        self.assertEqual(self.store.path.read_bytes(), before)
        self.assertEqual(self.store.load()["campaignEdition"], "persian-v2")


class ModelTests(unittest.TestCase):
    def test_inspection_does_not_load_or_change_model(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            (folder / "config.json").write_text('{"model_type":"qwen2","secret":"not exposed"}')
            (folder / "model.safetensors").write_bytes(b"not actual weights")
            before = {p.name: p.read_bytes() for p in folder.iterdir()}
            result = inspect_model(directory)
            self.assertEqual(result["format"], "transformers")
            self.assertFalse(result["loaded"])
            self.assertNotIn("secret", result["config"])
            self.assertEqual(before, {p.name: p.read_bytes() for p in folder.iterdir()})

    def test_external_api_rejected_before_network(self):
        for url in ("https://127.0.0.1/v1", "http://example.com/v1", "http://user:password@localhost/v1"):
            with self.assertRaises(ValueError):
                local_chat(url, "test", [{"role": "user", "content": "hi"}])

    def test_tool_schema_execution_and_stop(self):
        result = call_tool("read_gate", {"gate": "east"})
        opened = call_tool("open_gate", {"gate": "east", "signal": result["signal"]})
        self.assertTrue(opened["stop"])
        self.assertEqual(opened["mode"], "deterministic-game-tool")
        with self.assertRaises(ValueError):
            call_tool("read_private_file", {"gate": "east"})
        with self.assertRaises(ValueError):
            call_tool("read_gate", {"gate": "east", "extra": "x"})
        record = call_tool("lookup_record", {"id": "canal"})
        self.assertFalse(record["record"]["complete"])
        gate = call_tool("set_gate", {"threshold": .6})
        self.assertEqual(gate["confusionMatrix"], {"TP": 3, "FP": 1, "FN": 1, "TN": 3})
        self.assertTrue(gate["stop"])
        with self.assertRaises(ValueError):
            call_tool("set_gate", {"threshold": True})


@unittest.skipUnless((ROOT / "exercises.py").exists(), "exercise bank not yet built")
class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from server import GameServer
        cls.temp = tempfile.TemporaryDirectory(prefix="the-game-http-test-")
        cls.server = GameServer(("127.0.0.1", 0), cls.temp.name, job_timeout=3)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f"http://127.0.0.1:{cls.server.server_port}"
        cls.opener = build_opener(ProxyHandler({}))

    @classmethod
    def tearDownClass(cls):
        cls.server.jobs.close(); cls.server.shutdown(); cls.server.server_close(); cls.thread.join(timeout=3)
        cls.temp.cleanup()

    def request(self, path, body=None, headers=None):
        h = {"Content-Type": "application/json", "X-Game-Token": self.server.token}
        h.update(headers or {})
        data = json.dumps(body).encode() if body is not None else None
        with self.opener.open(Request(self.base + path, data=data, headers=h), timeout=8) as response:
            return json.loads(response.read())

    def wait_job(self, job_id):
        deadline = time.time() + 10
        while time.time() < deadline:
            result = self.request("/api/job?id=" + job_id)
            if result["status"] != "running":
                # Wait for watcher to reap process and preserve last result.
                time.sleep(.1)
                return result
            time.sleep(.05)
        self.fail("worker did not finish")

    def start(self, code):
        import exercises
        exercise_id = next(key for key, value in exercises.EXERCISES.items() if not value.get("requiresTorch"))
        return self.request("/api/run", {"exerciseId": exercise_id, "code": code})["jobId"]

    def test_health_and_wrong_origin_token(self):
        self.assertEqual(self.request("/api/health")["app"], "the-game")
        for headers in ({"X-Game-Token": "wrong"}, {"Origin": "http://example.org"}):
            with self.assertRaises(HTTPError) as raised:
                self.request("/api/save", {"state": default_state()}, headers)
            self.assertEqual(raised.exception.code, 403)

    def test_real_good_code_and_wrong_code(self):
        import exercises
        exercise_id = next(key for key, value in exercises.EXERCISES.items() if not value.get("requiresTorch"))
        solution = exercises.EXERCISES[exercise_id]["solution"]
        good = self.request("/api/run", {"exerciseId": exercise_id, "code": solution})
        self.assertEqual(self.wait_job(good["jobId"])["status"], "passed")
        bad = self.start("x = 123")
        self.assertIn(self.wait_job(bad)["status"], ("failed", "error"))

    def test_syntax_error_timeout_and_draft_saved_before_run(self):
        job = self.start("def broken(:\n pass")
        result = self.wait_job(job)
        self.assertEqual(result["status"], "error")
        self.assertIn("SyntaxError", result["stderr"])
        code = "while True:\n    pass"
        job = self.start(code)
        self.assertEqual(self.server.store.load()["missions"][self.server.store.load()["currentMission"]]["draft"], code)
        self.assertEqual(self.wait_job(job)["status"], "timeout")

    def test_cancel_only_target_process(self):
        unrelated = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(20)"])
        try:
            job = self.start("import time\ntime.sleep(20)")
            self.request("/api/stop", {"jobId": job})
            self.assertEqual(self.wait_job(job)["status"], "cancelled")
            self.assertIsNone(unrelated.poll())
        finally:
            unrelated.terminate(); unrelated.wait(timeout=3)

    def test_port_change_keeps_saved_draft(self):
        from server import GameServer
        state = default_state(); state["missions"]["m01"] = {"draft": "print('черновик')", "dialogue": 2}
        self.request("/api/save", {"state": state})
        other = GameServer(("127.0.0.1", 0), self.temp.name)
        try:
            self.assertNotEqual(other.server_port, self.server.server_port)
            self.assertEqual(other.store.load()["missions"]["m01"]["draft"], "print('черновик')")
        finally:
            other.server_close()

    def test_actual_torch_gradients_and_bounded_output(self):
        import exercises
        if not self.server.diagnostics["torch"]["available"]:
            self.skipTest("PyTorch not installed in this interpreter")
        job = self.request("/api/run", {"exerciseId": "autograd", "code": exercises.EXERCISES["autograd"]["solution"], "variant": "transfer"})
        self.assertEqual(self.wait_job(job["jobId"])["status"], "passed")
        noisy = self.start("print('x' * 200000)")
        result = self.wait_job(noisy)
        self.assertEqual(result["status"], "error")
        self.assertLessEqual(len(result["stdout"]), 65536)

    def test_worker_stops_if_server_disappears(self):
        import exercises
        exercise_id = next(key for key, value in exercises.EXERCISES.items() if not value.get("requiresTorch"))
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            request = folder / "request.json"
            request.write_text(json.dumps({"exerciseId": exercise_id, "code": "while True: pass", "timeout": 30,
                                           "parentPid": 99999999}), encoding="utf-8")
            kwargs = {"start_new_session": True} if os.name != "nt" else {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
            worker = subprocess.Popen([sys.executable, str(ROOT / "runner.py"), str(request), str(folder / "result.json")],
                                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **kwargs)
            try:
                if os.name == "nt":
                    self.skipTest("Windows parent-handle disappearance needs a real Windows process fixture")
                self.assertNotEqual(worker.wait(timeout=3), 0)
            finally:
                if worker.poll() is None:
                    worker.kill(); worker.wait(timeout=3)

    def test_finished_run_never_overwrites_newer_draft(self):
        import exercises
        exercise_id = next(key for key, value in exercises.EXERCISES.items() if not value.get("requiresTorch"))
        submitted = "import time\ntime.sleep(.5)\n" + exercises.EXERCISES[exercise_id]["solution"]
        job = self.request("/api/run", {"exerciseId": exercise_id, "code": submitted})
        state = self.server.store.load()
        mission_id = state["currentMission"]
        state["missions"][mission_id]["draft"] = "# newer unsent code\nprint(42)"
        self.request("/api/save", {"state": state})
        self.assertEqual(self.wait_job(job["jobId"])["status"], "passed")
        saved = self.server.store.load()["missions"][mission_id]
        self.assertEqual(saved["draft"], "# newer unsent code\nprint(42)")
        self.assertEqual(saved["lastRunCode"], submitted)


if __name__ == "__main__":
    unittest.main()
