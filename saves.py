"""Versioned atomic saves kept outside the installation directory."""
from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import threading
import time

FORMAT_VERSION = 1
MAX_SAVE_BYTES = 4 * 1024 * 1024


class SaveError(ValueError):
    pass


def default_data_dir() -> Path:
    override = os.environ.get("THE_GAME_DATA_DIR")
    if override:
        return Path(override).expanduser().resolve()
    if os.name == "nt":
        return Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))) / "PersianFairytaleV2"
    return Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local" / "share"))) / "PersianFairytaleV2"


def default_state() -> dict:
    return {"version": 1, "campaignEdition": "persian-v2", "location": 1, "player": {"x": 500, "y": 500},
            "currentMission": "m01", "completed": [], "inventory": [], "missions": {},
            "settings": {"reducedMotion": False, "gentle": True}, "activeSeconds": 0,
            "lastAction": "Добро пожаловать в Сад точных желаний", "job": None,
            "rehearsal": {"remaining": 900, "interrupted": False}, "rewardIds": []}


def canonical(value) -> bytes:
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (ValueError, TypeError, RecursionError) as exc:
        raise SaveError("Сохранение содержит неподдерживаемые данные") from exc


def validate_state(state) -> dict:
    if not isinstance(state, dict) or state.get("version") != FORMAT_VERSION:
        raise SaveError("Неподдерживаемая версия сохранения")
    if state.get("campaignEdition") != "persian-v2":
        raise SaveError("Сохранение относится к другой редакции сада. Для новой учебной программы используется отдельный прогресс; старый файл не изменён.")
    if len(canonical(state)) > MAX_SAVE_BYTES:
        raise SaveError("Сохранение превышает 4 МБ")
    for key in ("completed", "inventory", "rewardIds"):
        if key in state and not isinstance(state[key], list):
            raise SaveError(f"Повреждено поле {key}")
    if not isinstance(state.get("missions", {}), dict):
        raise SaveError("Повреждено поле missions")
    # Deduplication protects idempotent replay without discarding other fields.
    result = copy.deepcopy(state)
    for key in ("completed", "rewardIds"):
        if key in result:
            if not all(isinstance(x, str) for x in result[key]):
                raise SaveError(f"Повреждены идентификаторы {key}")
            result[key] = list(dict.fromkeys(result[key]))
    return result


def envelope(state) -> dict:
    state = validate_state(state)
    return {"format": "the-game-save", "version": FORMAT_VERSION, "savedAt": time.time(),
            "checksum": hashlib.sha256(canonical(state)).hexdigest(), "state": state}


def unpack(value) -> dict:
    if not isinstance(value, dict) or value.get("format") != "the-game-save" or value.get("version") != FORMAT_VERSION:
        raise SaveError("Это не совместимое сохранение The Game")
    state = validate_state(value.get("state"))
    if value.get("checksum") != hashlib.sha256(canonical(value["state"])).hexdigest():
        raise SaveError("Контрольная сумма сохранения не совпадает. Доступна резервная копия или импорт.")
    return state


class SaveStore:
    def __init__(self, directory=None):
        self.directory = Path(directory) if directory else default_data_dir()
        self.directory.mkdir(parents=True, exist_ok=True)
        self.path = self.directory / "save.json"
        self.backup = self.directory / "save.previous.json"
        self.lock = threading.RLock()
        self.error = None

    @staticmethod
    def _read(path):
        try:
            if path.stat().st_size > MAX_SAVE_BYTES + 8192:
                raise SaveError("Сохранение слишком большое")
            value = json.loads(path.read_text(encoding="utf-8"))
            unpack(value)
            return value
        except (OSError, ValueError, TypeError, RecursionError) as exc:
            raise SaveError(f"Не удалось прочитать {path.name}: {exc}") from exc

    def load(self):
        with self.lock:
            if not self.path.exists():
                if self.backup.exists():
                    self.error = "Основное сохранение отсутствует; используйте восстановление резервной копии."
                    raise SaveError(self.error)
                return default_state()
            try:
                value = self._read(self.path)
                self.error = None
                return unpack(value)
            except SaveError as exc:
                self.error = str(exc)
                raise

    def _atomic(self, path, data):
        temp = path.with_suffix(path.suffix + ".tmp")
        try:
            with open(temp, "wb") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp, path)
            if os.name != "nt":
                fd = os.open(str(path.parent), os.O_RDONLY)
                try:
                    os.fsync(fd)
                finally:
                    os.close(fd)
        finally:
            try:
                temp.unlink(missing_ok=True)
            except OSError:
                pass

    def save(self, state, *, explicit=False):
        with self.lock:
            value = envelope(state)
            if self.error and not explicit:
                raise SaveError("Сначала восстановите или импортируйте сохранение: " + self.error)
            if self.path.exists():
                try:
                    old = self._read(self.path)
                except SaveError:
                    if not explicit:
                        self.error = "Текущее сохранение повреждено"
                        raise SaveError(self.error)
                    # Preserve corrupt bytes for diagnosis instead of silently discarding.
                    damaged = self.directory / f"save.damaged.{time.time_ns()}.json"
                    self._atomic(damaged, self.path.read_bytes()[:MAX_SAVE_BYTES + 8192])
                else:
                    self._atomic(self.backup, canonical(old))
            self._atomic(self.path, canonical(value))
            self.error = None
            return value

    def export(self):
        with self.lock:
            return envelope(self.load())

    def import_save(self, value):
        state = unpack(value)
        self.save(state, explicit=True)
        return state

    def recover(self):
        with self.lock:
            value = self._read(self.backup)
            state = unpack(value)
            # Do not replace a known good backup with a damaged primary.
            if self.path.exists():
                damaged = self.directory / f"save.before-recovery.{time.time_ns()}.json"
                self._atomic(damaged, self.path.read_bytes()[:MAX_SAVE_BYTES + 8192])
            self._atomic(self.path, canonical(value))
            self.error = None
            return state

    def mark_interrupted(self):
        with self.lock:
            state = self.load()
            changed = False
            job = state.get("job")
            if isinstance(job, dict) and job.get("status") in ("running", "queued"):
                job["status"] = "interrupted"
                job["feedback"] = "Запуск прерван закрытием сервера. Код сохранён; запустите его снова."
                changed = True
            rehearsal = state.get("rehearsal")
            if isinstance(rehearsal, dict) and rehearsal.get("running"):
                rehearsal["running"] = False
                rehearsal["interrupted"] = True
                changed = True
            for mission in state.get("missions", {}).values():
                if not isinstance(mission, dict):
                    continue
                rehearsal = mission.get("rehearsal")
                if isinstance(rehearsal, dict) and rehearsal.get("running"):
                    rehearsal["running"] = False
                    rehearsal["interrupted"] = True
                    changed = True
            if changed:
                self.save(state)
            return state
