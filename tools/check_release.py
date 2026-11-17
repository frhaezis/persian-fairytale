"""Verify an extracted release with an explicitly supplied test interpreter.

python tools/check_release.py /absolute/path/to/python
All save data is temporary; this never opens the player's normal data directory.
"""
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
from urllib.request import Request, urlopen
import zipfile

ROOT = Path(__file__).resolve().parents[1]
archive = ROOT / "release" / "persian fairytale. V2.zip"
python = sys.argv[1] if len(sys.argv) > 1 else sys.executable
report = {"kind": "extracted archive validation", "platform": sys.platform, "checks": []}
with tempfile.TemporaryDirectory(prefix="the-game-release-") as temporary:
    target = Path(temporary) / "Проверка архива с пробелами"
    target.mkdir()
    with zipfile.ZipFile(archive) as package:
        assert package.testzip() is None
        package.extractall(target)
    game = target / "persian fairytale. V2"
    manifest = json.loads((game / "MANIFEST.json").read_text(encoding="utf-8"))
    for name, expected in manifest.items():
        assert hashlib.sha256((game / name).read_bytes()).hexdigest() == expected, name
    assert not (game / ".venv").exists()
    assert not (game / "docs" / "BRIEF_RU.md").exists()
    report["checks"].append("ZIP integrity; all SHA256 manifest entries; no development environment or private brief")
    data = target / "Отдельные сохранения"
    launched = subprocess.run([python, str(game / "launcher.py"), "--python", python,
                               "--data-dir", str(data), "--no-browser", "--non-interactive"],
                              capture_output=True, text=True, timeout=65)
    assert launched.returncode == 0, launched.stderr + launched.stdout
    marker = json.loads((data / "server.json").read_text(encoding="utf-8"))
    base = "http://127.0.0.1:" + str(marker["port"])
    def get(route):
        with urlopen(base + route, timeout=30) as response:
            return json.load(response)
    try:
        boot = get("/api/bootstrap")
        assert len(boot["curriculum"]["missions"]) == 40
        assert boot["diagnostics"]["torchAvailable"]
        assert len(boot["exercises"]) == 20
        report["checks"].append("Real launcher starts extracted copy from Unicode/space path; 40 missions and 20 exercises")
        for route in ("/", "/app.js", "/world.js", "/style.css"):
            with urlopen(base + route, timeout=10) as response:
                assert response.status == 200 and len(response.read()) > 100
        report["checks"].append("All bundled frontend files served locally")
        code = subprocess.check_output([python, "-c", "import exercises; print(exercises.EXERCISES['autograd']['solution'])"],
                                       cwd=game, text=True)
        body = json.dumps({"exerciseId": "autograd", "code": code, "variant": "transfer"}).encode()
        req = Request(base + "/api/run", data=body, headers={"Content-Type": "application/json",
                      "X-Game-Token": boot["token"]})
        with urlopen(req, timeout=10) as response:
            job_id = json.load(response)["jobId"]
        deadline = time.monotonic() + 35
        while time.monotonic() < deadline:
            result = get("/api/job?id=" + job_id)
            if result["status"] != "running":
                break
            time.sleep(.1)
        assert result["status"] == "passed", result
        report["checks"].append("Actual PyTorch autograd transfer succeeds from extracted source")
        repeated = subprocess.run([python, str(game / "launcher.py"), "--python", python,
                                   "--data-dir", str(data), "--no-browser", "--non-interactive"],
                                  capture_output=True, text=True, timeout=20)
        assert repeated.returncode == 0
        assert json.loads((data / "server.json").read_text())["pid"] == marker["pid"]
        report["checks"].append("Repeated extracted launcher reuses the same backend")
    finally:
        os.kill(marker["pid"], signal.SIGTERM)
        for _ in range(100):
            if not (data / "server.json").exists():
                break
            time.sleep(.05)
report["passed"] = True
report["limitations"] = ["Linux execution only; Windows BAT and the user's model were not run.",
                         "Automatic checks do not measure human play duration or learning."]
(ROOT / "artifacts" / "release-check.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(report, ensure_ascii=False, indent=2))
