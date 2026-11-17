"""Local-only game server. Run: python server.py --port 0 --no-browser."""
from __future__ import annotations

import argparse
import copy
import importlib.util
import json
import mimetypes
import os
from pathlib import Path
import secrets
import shutil
import signal
import subprocess
import sys
import threading
import time
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse
import uuid
import webbrowser

from saves import SaveError, SaveStore, canonical, default_data_dir
from model_adapter import TOOL_SCHEMAS, call_tool, inspect_model, local_chat

ROOT = Path(__file__).resolve().parent
MAX_BODY = 4 * 1024 * 1024 + 16384
MAX_OUTPUT = 65536


def diagnostics():
    torch_info = {"available": False, "version": None}
    try:
        if importlib.util.find_spec("torch"):
            result = subprocess.run([sys.executable, "-c", "import torch; print(torch.__version__); print(torch.ones(1).item())"], capture_output=True, text=True, timeout=15)
            if result.returncode == 0:
                torch_info = {"available": True, "version": result.stdout.splitlines()[0]}
            else:
                torch_info["error"] = result.stderr[-1500:]
    except (OSError, subprocess.TimeoutExpired) as exc:
        torch_info["error"] = str(exc)
    return {"python": sys.version.split()[0], "executable": sys.executable, "platform": sys.platform,
            "torch": torch_info, "torchAvailable": torch_info["available"], "localOnly": True,
            "codeExecution": "Настоящий локальный Python в отдельном процессе. Ограничение времени не является защитной песочницей; запускайте только понятный вам код.",
            "model": "Не подключена. Основной маршрут работает без модели.", "windowsTested": False}


class JobManager:
    def __init__(self, store, timeout=30):
        self.store = store
        self.timeout = min(max(float(timeout), 0.2), 30)
        self.lock = threading.RLock()
        self.jobs = {}
        self.current = None
        try:
            state = store.mark_interrupted()
            previous = state.get("job")
            if isinstance(previous, dict) and previous.get("jobId"):
                self.current = previous["jobId"]
                self.jobs[self.current] = dict(previous)
        except SaveError:
            pass

    def snapshot(self, job_id=None):
        with self.lock:
            job_id = job_id or self.current
            if job_id not in self.jobs:
                return None
            return copy.deepcopy({k: v for k, v in self.jobs[job_id].items() if not k.startswith("_")})

    def _persist(self, job):
        if self.current != job["jobId"]:
            return
        try:
            with self.store.lock:
                state = self.store.load()
                state["job"] = self.snapshot(job["jobId"])
                mission_id = job.get("missionId")
                if mission_id:
                    mission = state.setdefault("missions", {}).setdefault(mission_id, {})
                    if job["status"] != "running":
                        mission["lastResult"] = state["job"]
                self.store.save(state)
        except (SaveError, OSError):
            # Existing save error is surfaced by the next save/bootstrap request.
            pass

    def start(self, exercise_id, code, variant):
        import exercises
        if exercise_id not in exercises.EXERCISES:
            raise ValueError("Неизвестное упражнение")
        if not isinstance(code, str) or not code.strip() or len(code.encode("utf-8")) > 131072:
            raise ValueError("Введите код размером не более 128 КБ")
        if variant not in ("practice", "transfer"):
            raise ValueError("Неизвестный вариант проверки")
        with self.lock:
            if self.current and self.jobs[self.current].get("status") == "running":
                raise RuntimeError("Уже выполняется эксперимент. Дождитесь результата или остановите его.")
            state = self.store.load()
            job_id = uuid.uuid4().hex
            mission_id = state.get("currentMission", "m01")
            job = {"jobId": job_id, "exerciseId": exercise_id, "missionId": mission_id, "variant": variant,
                   "status": "running", "stdout": "", "stderr": "", "feedback": "Python выполняет код…", "results": [],
                   "startedAt": time.time(), "_code": code}
            self.jobs[job_id] = job
            self.current = job_id
            # Saving is mandatory before launching; a failed disk write prevents execution.
            state.setdefault("missions", {}).setdefault(mission_id, {})["draft"] = code
            state["missions"][mission_id]["lastRunCode"] = code
            state["job"] = self.snapshot(job_id)
            self.store.save(state)
            folder = self.store.directory / "jobs" / job_id
            folder.mkdir(parents=True, exist_ok=True)
            request_path, result_path = folder / "request.json", folder / "result.json"
            request_path.write_text(json.dumps({"exerciseId": exercise_id, "code": code, "variant": variant, "timeout": self.timeout,
                                                "parentPid": os.getpid()}, ensure_ascii=False), encoding="utf-8")
            env = os.environ.copy()
            env.update({"PYTHONIOENCODING": "utf-8", "PYTHONUNBUFFERED": "1", "OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1"})
            kwargs = {"start_new_session": True} if os.name != "nt" else {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
            try:
                proc = subprocess.Popen([sys.executable, "-u", str(ROOT / "runner.py"), str(request_path), str(result_path)], cwd=folder, env=env,
                                        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kwargs)
            except OSError as exc:
                job.update(status="error", feedback=f"Не удалось запустить Python: {exc}")
                self._persist(job)
                raise
            job["_process"] = proc
            threading.Thread(target=self._watch, args=(job_id, folder, result_path), daemon=True).start()
            return job_id

    @staticmethod
    def _terminate(proc):
        try:
            if os.name == "nt":
                if proc.poll() is None:
                    subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)
                    if proc.poll() is None:
                        proc.kill()
            else:
                os.killpg(proc.pid, signal.SIGKILL)
        except (ProcessLookupError, OSError, subprocess.TimeoutExpired):
            if proc.poll() is None:
                try:
                    proc.kill()
                except OSError:
                    pass

    def _reader(self, job_id, pipe, field):
        try:
            while True:
                chunk = os.read(pipe.fileno(), 4096)
                if not chunk:
                    break
                text = chunk.decode("utf-8", errors="replace")
                with self.lock:
                    job = self.jobs[job_id]
                    available = MAX_OUTPUT - len(job[field])
                    if available > 0:
                        job[field] += text[:available]
                    if len(text) > available and job.get("status") == "running":
                        job.update(status="error", feedback="Слишком большой вывод (лимит 64 КБ на поток). Уберите print из длинного цикла.")
                        self._terminate(job["_process"])
        except (OSError, ValueError):
            pass
        finally:
            pipe.close()

    def _watch(self, job_id, folder, result_path):
        with self.lock:
            job = self.jobs[job_id]
            proc = job["_process"]
        readers = [threading.Thread(target=self._reader, args=(job_id, pipe, field), daemon=True)
                   for pipe, field in ((proc.stdout, "stdout"), (proc.stderr, "stderr"))]
        for thread in readers:
            thread.start()
        try:
            proc.wait(timeout=self.timeout)
        except subprocess.TimeoutExpired:
            with self.lock:
                if job["status"] == "running":
                    job.update(status="timeout", feedback=f"Лимит {self.timeout:g} секунд. Код сохранён; сократите цикл или размер эксперимента.")
            self._terminate(proc)
            proc.wait(timeout=5)
        finally:
            # Clean up descendants of this worker, never other Python processes.
            self._terminate(proc)
        for thread in readers:
            thread.join(timeout=2)
        with self.lock:
            if job["status"] == "running":
                try:
                    if result_path.stat().st_size > 250000:
                        raise ValueError("Результат проверки слишком большой")
                    result = json.loads(result_path.read_text(encoding="utf-8"))
                    if result.get("status") not in ("passed", "failed", "error"):
                        raise ValueError("Некорректный статус проверки")
                    for key in ("status", "passed", "feedback", "results", "artifact"):
                        if key in result:
                            job[key] = result[key]
                except (OSError, ValueError) as exc:
                    job.update(status="error", feedback=f"Python завершился без корректного результата: {exc}")
            job["finishedAt"] = time.time()
            self._persist(job)
            # Keep only lightweight completed results in memory; code is in the save.
            job.pop("_process", None)
            job.pop("_code", None)
            while len(self.jobs) > 20:
                oldest = next(iter(self.jobs))
                if oldest == self.current:
                    break
                self.jobs.pop(oldest)
        shutil.rmtree(folder, ignore_errors=True)

    def stop(self, job_id):
        with self.lock:
            if job_id not in self.jobs:
                raise ValueError("Запуск не найден")
            job = self.jobs[job_id]
            if job.get("status") == "running":
                job.update(status="cancelled", feedback="Запуск остановлен. Код сохранён; задание не засчитано.")
                self._terminate(job["_process"])
                self._persist(job)
            return self.snapshot(job_id)

    def close(self):
        with self.lock:
            if self.current and self.jobs[self.current].get("status") == "running":
                job = self.jobs[self.current]
                job.update(status="interrupted", feedback="Сервер закрыт во время выполнения. Запустите сохранённый код снова.")
                self._terminate(job["_process"])
                self._persist(job)


class GameServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, address, data_dir=None, job_timeout=30):
        super().__init__(address, Handler)
        self.store = SaveStore(data_dir)
        self.token = secrets.token_urlsafe(32)
        self.jobs = JobManager(self.store, job_timeout)
        self.diagnostics = diagnostics()
        self.diagnostics["dataDir"] = str(self.store.directory)
        self.marker = self.store.directory / "server.json"


class Handler(BaseHTTPRequestHandler):
    server_version = "TheGame/1"

    def log_message(self, fmt, *args):
        # Local request logs intentionally omit bodies, code and filesystem paths.
        if os.environ.get("THE_GAME_VERBOSE"):
            super().log_message(fmt, *args)

    def _allowed(self):
        port = self.server.server_port
        expected = {f"127.0.0.1:{port}", f"localhost:{port}", f"[::1]:{port}"}
        if self.headers.get("Host", "").lower() not in expected:
            self._json({"error": "Неверный Host"}, 403)
            return False
        origin = self.headers.get("Origin")
        if origin and origin not in {"http://" + host for host in expected}:
            self._json({"error": "Запрос с другого сайта запрещён"}, 403)
            return False
        return True

    def _json(self, value, status=200, attachment=None):
        body = json.dumps(value, ensure_ascii=False, allow_nan=False, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        if attachment:
            self.send_header("Content-Disposition", f'attachment; filename="{attachment}"')
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_GET(self):
        if not self._allowed():
            return
        route = urlparse(self.path)
        try:
            if route.path == "/api/health":
                return self._json({"app": "the-game", "instance": "the-game", "version": 1, "port": self.server.server_port, "pid": os.getpid()})
            if route.path == "/api/bootstrap":
                import exercises
                save_error = None
                try:
                    state = self.server.store.load()
                except SaveError as exc:
                    state, save_error = None, str(exc)
                curriculum = json.loads((ROOT / "data" / "curriculum.json").read_text(encoding="utf-8"))
                return self._json({"state": state, "curriculum": curriculum, "exercises": exercises.public_exercises(),
                                   "diagnostics": self.server.diagnostics, "token": self.server.token,
                                   "saveError": save_error, "recoveryAvailable": self.server.store.backup.exists(), "toolSchemas": TOOL_SCHEMAS})
            if route.path == "/api/export":
                return self._json(self.server.store.export(), attachment="the-game-save.json")
            if route.path == "/api/job":
                job_id = parse_qs(route.query).get("id", [None])[0]
                job = self.server.jobs.snapshot(job_id)
                return self._json(job if job else {"error": "Запуск не найден"}, 200 if job else 404)
            if route.path == "/api/sources" or route.path == "/data/sources.json":
                return self._json(json.loads((ROOT / "data" / "sources.json").read_text(encoding="utf-8")))
            if route.path.startswith("/api/"):
                return self._json({"error": "Маршрут не найден"}, 404)
            relative = "index.html" if route.path == "/" else route.path.lstrip("/")
            target = (ROOT / "static" / relative).resolve()
            if not target.is_relative_to((ROOT / "static").resolve()) or not target.is_file():
                return self._json({"error": "Файл не найден"}, 404)
            content = target.read_bytes()
            mime = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
            if target.suffix == ".js":
                mime = "text/javascript"
            self.send_response(200)
            self.send_header("Content-Type", mime + ("; charset=utf-8" if mime.startswith("text/") else ""))
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", "no-cache")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; object-src 'none'; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(content)
        except SaveError as exc:
            self._json({"error": str(exc), "saveError": True, "recoveryAvailable": self.server.store.backup.exists()}, 409)
        except (OSError, ValueError, ImportError) as exc:
            self._json({"error": str(exc)}, 500)

    def do_POST(self):
        if not self._allowed():
            return
        if not secrets.compare_digest(self.headers.get("X-Game-Token", ""), self.server.token):
            return self._json({"error": "Токен устарел. Обновите страницу после перезапуска сервера; черновик сохранён при последней успешной записи."}, 403)
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= MAX_BODY:
                return self._json({"error": "Недопустимый размер запроса"}, 413)
            if self.headers.get_content_type() != "application/json":
                return self._json({"error": "Ожидается application/json"}, 415)
            body = json.loads(self.rfile.read(length))
            if not isinstance(body, dict):
                raise ValueError("Ожидается JSON-объект")
            path = urlparse(self.path).path
            if path == "/api/save":
                state = body["state"]
                current_job = self.server.jobs.snapshot()
                if current_job and isinstance(state, dict):
                    state["job"] = current_job
                saved = self.server.store.save(state)
                return self._json({"ok": True, "savedAt": saved["savedAt"]})
            if path == "/api/import":
                current = self.server.jobs.snapshot()
                if current and current.get("status") == "running":
                    raise RuntimeError("Сначала остановите выполняющийся код")
                state = self.server.store.import_save(body["save"])
                self.server.jobs.current = None
                state = self.server.store.mark_interrupted()
                return self._json({"state": state})
            if path == "/api/recover":
                current = self.server.jobs.snapshot()
                if current and current.get("status") == "running":
                    raise RuntimeError("Сначала остановите выполняющийся код")
                state = self.server.store.recover()
                self.server.jobs.current = None
                state = self.server.store.mark_interrupted()
                return self._json({"state": state})
            if path == "/api/run":
                job_id = self.server.jobs.start(body["exerciseId"], body["code"], body.get("variant", "practice"))
                return self._json({"jobId": job_id})
            if path == "/api/stop":
                return self._json(self.server.jobs.stop(body["jobId"]))
            if path == "/api/model/inspect":
                return self._json(inspect_model(body["path"]))
            if path == "/api/model/chat":
                return self._json(local_chat(body["baseUrl"], body.get("model", "local-model"), body["messages"]))
            if path == "/api/model/agent":
                from model_adapter import run_local_agent
                return self._json(run_local_agent(body["baseUrl"], body.get("model", "local-model"),
                    body.get("goal", "Найди условия безопасного доступа к архиву и объясни ответ."),
                    body.get("budget", 3)))
            if path == "/api/tool":
                return self._json(call_tool(body["name"], body.get("args", {})))
            return self._json({"error": "Маршрут не найден"}, 404)
        except SaveError as exc:
            self._json({"error": str(exc), "saveError": True, "recoveryAvailable": self.server.store.backup.exists()}, 409)
        except RuntimeError as exc:
            self._json({"error": str(exc)}, 409)
        except (KeyError, TypeError, ValueError) as exc:
            self._json({"error": str(exc)}, 400)
        except Exception as exc:
            self._json({"error": str(exc)}, 500)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--data-dir", default=None)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--job-timeout", type=float, default=30, help=argparse.SUPPRESS)
    args = parser.parse_args()
    server = GameServer(("127.0.0.1", args.port), args.data_dir, args.job_timeout)
    marker = {"port": server.server_port, "pid": os.getpid(), "instance": "the-game"}
    server.store._atomic(server.marker, canonical(marker))
    url = f"http://127.0.0.1:{server.server_port}/"
    print(f"THE_GAME_READY {url}", flush=True)
    print(f"Сохранения: {server.store.directory}", flush=True)
    if not args.no_browser:
        webbrowser.open(url)
    def stop_signal(signum, frame):
        threading.Thread(target=server.shutdown, daemon=True).start()
    if threading.current_thread() is threading.main_thread():
        signal.signal(signal.SIGINT, stop_signal)
        if hasattr(signal, "SIGTERM"):
            signal.signal(signal.SIGTERM, stop_signal)
    try:
        server.serve_forever(poll_interval=0.2)
    finally:
        server.jobs.close()
        server.server_close()
        try:
            if json.loads(server.marker.read_text(encoding="utf-8")).get("pid") == os.getpid():
                server.marker.unlink()
        except (OSError, ValueError):
            pass


if __name__ == "__main__":
    main()
