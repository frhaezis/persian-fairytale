"""Child-process worker. Learner code is local Python, NOT a security sandbox."""
from __future__ import annotations

import json
import os
from pathlib import Path
import runpy
import signal
import subprocess
import sys
import threading
import time
import traceback


def watchdog(timeout, parent_pid):
    """Keep the time limit even if the HTTP server crashes during learner code."""
    deadline = time.monotonic() + min(max(float(timeout), .2), 31)
    while time.monotonic() < deadline:
        parent_alive = True
        if parent_pid:
            if os.name != "nt":
                parent_alive = os.getppid() == parent_pid
            else:
                try:
                    import ctypes
                    kernel = ctypes.windll.kernel32
                    kernel.OpenProcess.restype = ctypes.c_void_p
                    kernel.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
                    kernel.CloseHandle.argtypes = [ctypes.c_void_p]
                    handle = kernel.OpenProcess(0x00100000, False, parent_pid)
                    if handle:
                        parent_alive = kernel.WaitForSingleObject(handle, 0) != 0
                        kernel.CloseHandle(handle)
                except (AttributeError, OSError):
                    pass
        if not parent_alive:
            break
        time.sleep(.1)
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(os.getpid()), "/T", "/F"], timeout=3, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        elif os.getpgrp() == os.getpid():
            os.killpg(os.getpid(), signal.SIGKILL)
    finally:
        os._exit(124)


def main():
    request_path, result_path = map(Path, sys.argv[1:3])
    request = json.loads(request_path.read_text(encoding="utf-8"))
    threading.Thread(target=watchdog, args=(request.get("timeout", 30) + .5, request.get("parentPid")), daemon=True).start()
    os.environ.setdefault("OMP_NUM_THREADS", "1")
    os.environ.setdefault("MKL_NUM_THREADS", "1")
    try:
        import exercises
        exercise_id = request["exerciseId"]
        if exercise_id not in exercises.EXERCISES:
            raise ValueError("Неизвестное упражнение")
        if exercises.EXERCISES[exercise_id].get("requiresTorch"):
            try:
                import torch
                torch.set_num_threads(1)
                torch.manual_seed(17)
            except ImportError as exc:
                raise RuntimeError("PyTorch не установлен в выбранном Python. Запустите INSTALL_DEPENDENCIES.bat или выберите среду с torch.") from exc
        source = request_path.parent / "learner.py"
        source.write_text(request["code"], encoding="utf-8")
        namespace = runpy.run_path(str(source), run_name="__main__")
        result = exercises.validate(exercise_id, namespace, request.get("variant", "practice"))
        result["status"] = "passed" if result.get("passed") else "failed"
    except BaseException as exc:
        traceback.print_exc()
        result = {"status": "error", "passed": False, "feedback": f"{type(exc).__name__}: {exc}", "results": []}
    try:
        encoded = json.dumps(result, ensure_ascii=False, default=str, allow_nan=False)
    except (TypeError, ValueError):
        encoded = json.dumps({"status": "error", "passed": False, "feedback": "Проверка вернула недопустимые числа или данные", "results": []})
    result_path.write_text(encoded[:250000], encoding="utf-8")


if __name__ == "__main__":
    main()
