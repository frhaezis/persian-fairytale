#!/usr/bin/env python3
"""Small, dependency-free launcher for the local game.

Only INSTALL_DEPENDENCIES.bat / --install installs anything, into this game's
.venv. Normal launches never change a Python environment or fetch model weights.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser

ROOT = Path(__file__).resolve().parent
APP_ID = "the-game"


def data_dir():
    explicit = os.environ.get("THE_GAME_DATA_DIR")
    if explicit:
        return Path(explicit).expanduser().resolve()
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local")))
        return base / "PersianFairytaleV2"
    return Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local" / "share"))) / "PersianFairytaleV2"


def read_json(path):
    try:
        with Path(path).open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError, TypeError):
        return {}


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    with temp.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temp, path)


def command_output(command, timeout=10):
    try:
        return subprocess.run(command, capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=timeout,
                              creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).stdout
    except (OSError, subprocess.TimeoutExpired):
        return ""


def interpreter_candidates(directory, explicit=None):
    """Find executables, without importing or editing the user's projects."""
    saved = read_json(Path(directory) / "launcher.json").get("python")
    candidates = [explicit, saved,
                  str(ROOT / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")),
                  sys.executable]
    if os.name == "nt":
        py = shutil.which("py")
        if py:
            for line in command_output([py, "-0p"]).splitlines():
                # Both legacy '-V:3.12 * C:\\…' and current launcher lists.
                for index, char in enumerate(line):
                    if index + 2 < len(line) and char.isalpha() and line[index + 1:index + 3] == ":\\":
                        candidates.append(line[index:].strip())
                        break
        for name in ("python", "python3"):
            candidates.extend(command_output(["where.exe", name]).splitlines())
        # A normal python.org install can be absent from PATH and py.exe.
        try:
            import winreg
            for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
                for view in (winreg.KEY_WOW64_64KEY, winreg.KEY_WOW64_32KEY):
                    try:
                        with winreg.OpenKey(hive, r"Software\Python\PythonCore", 0, winreg.KEY_READ | view) as key:
                            for i in range(winreg.QueryInfoKey(key)[0]):
                                version = winreg.EnumKey(key, i)
                                try:
                                    with winreg.OpenKey(key, version + r"\InstallPath") as install:
                                        try:
                                            candidates.append(winreg.QueryValueEx(install, "ExecutablePath")[0])
                                        except OSError:
                                            candidates.append(str(Path(winreg.QueryValue(install, None)) / "python.exe"))
                                except OSError:
                                    pass
                    except OSError:
                        pass
        except ImportError:
            pass
    else:
        candidates.extend(shutil.which(name) for name in ("python3", "python"))
    seen = set()
    for value in candidates:
        if not value:
            continue
        path = Path(str(value).strip().strip('"')).expanduser()
        if not path.is_file():
            continue
        normalized = os.path.normcase(str(path.absolute()))
        if normalized in seen:
            continue
        seen.add(normalized)
        yield str(path.absolute())


def inspect_interpreter(path, timeout=25):
    # Import torch, rather than only finding its package: broken DLL installs
    # are common on Windows. Keep full diagnostic detail in a local JSON file.
    probe = """import json, sys
result = {'python': sys.executable, 'version': list(sys.version_info[:3]), 'torch': False}
try:
 import torch
 result['torch'] = True
 result['torchVersion'] = torch.__version__
 result['test'] = (torch.tensor([1., 2.]) + 1).tolist()
except Exception as exc:
 result['torchError'] = type(exc).__name__ + ': ' + str(exc)
print('__THE_GAME_PROBE__' + json.dumps(result, ensure_ascii=True))
"""
    output = command_output([path, "-c", probe], timeout=timeout)
    for line in reversed(output.splitlines()):
        if line.startswith("__THE_GAME_PROBE__"):
            try:
                result = json.loads(line[len("__THE_GAME_PROBE__"):])
                result["supported"] = result.get("version", [])[:2] >= [3, 10]
                return result
            except ValueError:
                break
    return {"python": path, "supported": False, "torch": False,
            "torchError": "Интерпретатор не ответил, завершился с ошибкой или превысил время проверки."}


def select_interpreter(directory, explicit=None, allow_prompt=True):
    inspected = []
    fallback = None
    if explicit:
        candidate = Path(str(explicit).strip().strip('"')).expanduser()
        if not candidate.is_file():
            raise RuntimeError("Указанный python.exe не найден: " + str(candidate))
        # Do not resolve symlinks: a venv's bin/python points at a base binary,
        # but invoking the symlink is what selects the virtual environment.
        info = inspect_interpreter(str(candidate.absolute()))
        write_json(Path(directory) / "environment-diagnostics.json", {"checked": [info], "selected": info})
        if not info.get("supported"):
            raise RuntimeError("Указанный интерпретатор не запускается или старше Python 3.10.")
        return info
    for executable in interpreter_candidates(directory, explicit):
        print("Проверяю Python:", executable, flush=True)
        info = inspect_interpreter(executable)
        inspected.append(info)
        if info.get("supported"):
            fallback = fallback or info
            if info.get("torch"):
                write_json(Path(directory) / "environment-diagnostics.json", {"checked": inspected, "selected": info})
                return info
    if not fallback and allow_prompt and sys.stdin.isatty():
        print("Нужен Python 3.10 или новее. Можно указать путь к python.exe существующего окружения.")
        candidate = input("Путь к python.exe (Enter — выйти): ").strip().strip('"')
        if candidate and Path(candidate).is_file():
            info = inspect_interpreter(candidate)
            inspected.append(info)
            if info.get("supported"):
                fallback = info
    write_json(Path(directory) / "environment-diagnostics.json", {"checked": inspected, "selected": fallback})
    return fallback


def health(port):
    try:
        port = int(port)
        if not 1 <= port <= 65535:
            return None
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open("http://127.0.0.1:%d/api/health" % port, timeout=1) as response:
            value = json.loads(response.read(4096).decode("utf-8"))
        if value.get("app") == APP_ID or value.get("instance") == APP_ID:
            return value
    except (OSError, ValueError, TypeError, urllib.error.URLError):
        pass
    return None


def running_server(directory):
    marker = read_json(Path(directory) / "server.json")
    if marker.get("instance") != APP_ID:
        return None
    result = health(marker.get("port"))
    if result and result.get("pid") == marker.get("pid"):
        return result
    return None


def open_game(server, open_browser=True):
    url = "http://127.0.0.1:%d/" % int(server["port"])
    print("Игра готова:", url, flush=True)
    if open_browser:
        try:
            if not webbrowser.open(url):
                print("Откройте этот адрес в браузере вручную.")
        except webbrowser.Error:
            print("Откройте этот адрес в браузере вручную.")
    return url


def install_dependencies(directory, explicit=None, allow_prompt=True):
    info = select_interpreter(directory, explicit, allow_prompt)
    if not info:
        raise RuntimeError("Не найден Python 3.10+. Установите Python с python.org или укажите существующий python.exe.")
    if info["version"][:2] > [3, 13]:
        raise RuntimeError("Для этой поставки установщик проверен с Python 3.10–3.13. Укажите такой интерпретатор через --python ПУТЬ.")
    target = ROOT / ".venv"
    python = target / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    print("Отдельное окружение игры:", target)
    if not python.is_file():
        subprocess.run([info["python"], "-m", "venv", str(target)], check=True)
    print("Устанавливаю CPU PyTorch. Нужны интернет и свободное место; другие окружения не изменяются.", flush=True)
    subprocess.run([str(python), "-m", "pip", "install", "--index-url", "https://download.pytorch.org/whl/cpu",
                    "-r", str(ROOT / "requirements.txt")], check=True)
    verified = inspect_interpreter(str(python), timeout=60)
    if not verified.get("torch"):
        raise RuntimeError("Установка завершилась, но import torch не работает: " + verified.get("torchError", "неизвестная ошибка"))
    write_json(Path(directory) / "launcher.json", {"python": verified["python"]})
    print("Готово. Запустите START_GAME.bat.")


def launch(directory, explicit=None, open_browser=True, allow_prompt=True):
    directory = Path(directory).resolve()
    directory.mkdir(parents=True, exist_ok=True)
    existing = running_server(directory)
    if existing:
        print("Локальный сервер уже работает; возвращаюсь к игре.")
        return open_game(existing, open_browser)
    lock = directory / "launcher.lock"
    # Only the short startup phase is locked. Never touch a game save here.
    deadline = time.monotonic() + 15
    while True:
        try:
            handle = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            os.write(handle, str(os.getpid()).encode("ascii"))
            os.close(handle)
            break
        except FileExistsError:
            existing = running_server(directory)
            if existing:
                return open_game(existing, open_browser)
            try:
                if time.time() - lock.stat().st_mtime > 180:
                    lock.unlink()
                    continue
            except FileNotFoundError:
                continue
            if time.monotonic() >= deadline:
                raise RuntimeError("Другой запуск ещё проверяет окружение. Подождите его завершения и повторите START_GAME.bat.")
            time.sleep(0.25)
    try:
        # Another launcher may have finished while this one waited.
        existing = running_server(directory)
        if existing:
            return open_game(existing, open_browser)
        info = select_interpreter(directory, explicit, allow_prompt)
        if not info:
            raise RuntimeError("Не найден рабочий Python 3.10+. См. docs/START_RU.md.")
        write_json(directory / "launcher.json", {"python": info["python"]})
        if not info.get("torch"):
            print("PyTorch пока недоступен. Мир и занятия без torch запустятся; для мастерской нужен INSTALL_DEPENDENCIES.bat.")
            print("Подробная диагностика:", directory / "environment-diagnostics.json")
        log_path = directory / "server.log"
        if log_path.exists() and log_path.stat().st_size > 2_000_000:
            os.replace(log_path, directory / "server.previous.log")
        arguments = [info["python"], "-u", str(ROOT / "server.py"), "--port", "0",
                     "--data-dir", str(directory), "--no-browser"]
        options = {"cwd": str(ROOT), "stdin": subprocess.DEVNULL}
        if os.name == "nt":
            options["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
        else:
            options["start_new_session"] = True
        with log_path.open("ab", buffering=0) as log:
            child = subprocess.Popen(arguments, stdout=log, stderr=log, **options)
        deadline = time.monotonic() + 35
        while time.monotonic() < deadline:
            if child.poll() is not None:
                raise RuntimeError("Сервер завершился при запуске. Диагностика: " + str(log_path))
            server = running_server(directory)
            if server and server.get("pid") == child.pid:
                return open_game(server, open_browser)
            time.sleep(0.25)
        raise RuntimeError("Сервер не ответил за 35 секунд. Его журнал: " + str(log_path))
    finally:
        try:
            lock.unlink()
        except FileNotFoundError:
            pass


def main():
    parser = argparse.ArgumentParser(description="Локальный запуск «Сада точных желаний»")
    parser.add_argument("--python", help="Полный путь к существующему python.exe")
    parser.add_argument("--data-dir", type=Path, default=data_dir())
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--non-interactive", action="store_true")
    parser.add_argument("--install", action="store_true", help="Установить зависимости только в .venv игры")
    args = parser.parse_args()
    try:
        if args.install:
            install_dependencies(args.data_dir, args.python, not args.non_interactive)
        else:
            launch(args.data_dir, args.python, not args.no_browser, not args.non_interactive)
        return 0
    except (OSError, RuntimeError, subprocess.SubprocessError, KeyboardInterrupt) as exc:
        print("\nНе удалось выполнить действие:", exc, file=sys.stderr)
        print("Сохранения остаются в:", args.data_dir, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
