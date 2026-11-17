"""Launcher contract checks that can run on Linux without changing user data."""
import contextlib
import io
import json
import os
from pathlib import Path
import signal
import socket
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import launcher


STUB = r'''
import argparse, json, os
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
p = argparse.ArgumentParser()
p.add_argument('--port', type=int)
p.add_argument('--data-dir', type=Path)
p.add_argument('--no-browser', action='store_true')
a=p.parse_args()
class Handler(BaseHTTPRequestHandler):
 def do_GET(self):
  body=json.dumps({'app':'the-game','instance':'the-game','pid':os.getpid(),'port':self.server.server_port}).encode()
  self.send_response(200); self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
 def log_message(self,*args): pass
s=ThreadingHTTPServer(('127.0.0.1',a.port),Handler)
(a.data_dir/'server.json').write_text(json.dumps({'instance':'the-game','pid':os.getpid(),'port':s.server_port}))
s.serve_forever()
'''


class LauncherChecks(unittest.TestCase):
    def test_data_dir_is_independent_of_installation(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch.dict(os.environ, {"THE_GAME_DATA_DIR": str(Path(temp) / "данные с пробелом")}):
                self.assertEqual(launcher.data_dir(), Path(temp) / "данные с пробелом")

    def test_bad_health_and_corrupt_marker_do_not_reuse(self):
        with tempfile.TemporaryDirectory() as temp:
            Path(temp, "server.json").write_text("{broken", encoding="utf-8")
            self.assertIsNone(launcher.running_server(temp))
            self.assertIsNone(launcher.health(None))
            self.assertIsNone(launcher.health(-1))

    def test_explicit_python_is_honored_without_torch(self):
        info = {"python": sys.executable, "version": [3, 12, 0], "supported": True, "torch": False}
        with tempfile.TemporaryDirectory() as temp, patch.object(launcher, "inspect_interpreter", return_value=info) as probe:
            result = launcher.select_interpreter(temp, explicit=sys.executable, allow_prompt=False)
            self.assertEqual(result, info)
            self.assertEqual(probe.call_count, 1)
            self.assertEqual(probe.call_args.args[0], str(Path(sys.executable).absolute()))
            self.assertEqual(launcher.read_json(Path(temp) / "environment-diagnostics.json")["selected"], info)

    def test_atomic_settings_and_bad_json(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "подпапка" / "launcher.json"
            launcher.write_json(target, {"python": "C:\\Путь к Python\\python.exe"})
            self.assertEqual(launcher.read_json(target)["python"], "C:\\Путь к Python\\python.exe")
            self.assertFalse(target.with_name("launcher.json.tmp").exists())
            self.assertEqual(launcher.read_json(Path(temp) / "missing.json"), {})

    @unittest.skipIf(os.name == "nt", "This subprocess cleanup uses POSIX process groups; Windows is untested here")
    def test_dynamic_port_unicode_paths_and_repeated_launch(self):
        child_pid = None
        with tempfile.TemporaryDirectory(prefix="the-game-launcher-") as temp:
            root = Path(temp) / "Игра с пробелами"
            root.mkdir()
            directory = Path(temp) / "Мои данные"
            (root / "server.py").write_text(STUB, encoding="utf-8")
            info = {"python": sys.executable, "version": [3, 12, 0], "supported": True, "torch": False}
            blocker = socket.socket()
            blocker.bind(("127.0.0.1", 0))
            blocker.listen()
            try:
                with patch.object(launcher, "ROOT", root), patch.object(launcher, "select_interpreter", return_value=info), contextlib.redirect_stdout(io.StringIO()):
                    first_url = launcher.launch(directory, open_browser=False, allow_prompt=False)
                    first = launcher.running_server(directory)
                    self.assertIsNotNone(first)
                    child_pid = first["pid"]
                    self.assertNotEqual(first["port"], blocker.getsockname()[1])
                    self.assertEqual(launcher.launch(directory, open_browser=False, allow_prompt=False), first_url)
                    self.assertEqual(launcher.running_server(directory)["pid"], child_pid)
                    self.assertFalse((directory / "launcher.lock").exists())
                    self.assertTrue((directory / "server.log").is_file())
            finally:
                blocker.close()
                if child_pid:
                    os.killpg(child_pid, signal.SIGTERM)
                    # The detached process is still our child for this test.
                    try:
                        os.waitpid(child_pid, 0)
                    except ChildProcessError:
                        pass


if __name__ == "__main__":
    unittest.main()
