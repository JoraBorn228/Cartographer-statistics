"""
Синхронизация progress.json через Git между двумя устройствами.

Стратегия слияния при конфликте (автоматическая):
  - Объединяем сессии из обеих версий (дедупликация по started_at)
  - points = max(local, remote)
  - real_earnings, goals - объединяем
"""
from __future__ import annotations

import json
import os
import subprocess
import threading
import time
from pathlib import Path
from typing import Callable, Optional, Dict, Any

_REPO_ROOT = Path(__file__).parent.parent.parent
PROGRESS_FILE = _REPO_ROOT / "data" / "progress.json"


def _run_git(*args: str, timeout: int = 15) -> tuple:
    """Выполнить git-команду. Возвращает (success, output)."""
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=str(_REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        out = (result.stdout + result.stderr).strip()
        return result.returncode == 0, out
    except FileNotFoundError:
        return False, "git not found"
    except subprocess.TimeoutExpired:
        return False, "timeout"
    except Exception as e:
        return False, str(e)


def _load_json(path: Path) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _save_json(path: Path, data: Dict[str, Any]) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)


def _merge_progress(local: Dict, remote: Dict) -> Dict:
    """Умное слияние двух версий progress.json. Не теряет данные ни одной стороны."""
    merged = dict(local)

    # Очки и уровень - берём максимум
    merged["points"] = max(int(local.get("points", 0)), int(remote.get("points", 0)))
    merged["level"] = max(int(local.get("level", 1)), int(remote.get("level", 1)))

    # Сессии - объединяем, дедупликация по started_at (точность 0.1 сек)
    local_sessions = local.get("sessions", [])
    remote_sessions = remote.get("sessions", [])
    seen: Dict[float, Dict] = {}
    for s in local_sessions + remote_sessions:
        key = round(float(s.get("started_at", 0)), 1)
        if key not in seen:
            seen[key] = s
        elif int(s.get("points", 0)) > int(seen[key].get("points", 0)):
            seen[key] = s
    merged["sessions"] = sorted(seen.values(), key=lambda s: s.get("started_at", 0))

    # Реальные заработки - объединяем словари (берём максимум по каждой дате)
    local_earn = local.get("real_earnings") or {}
    remote_earn = remote.get("real_earnings") or {}
    merged_earn = dict(remote_earn)
    for k, v in local_earn.items():
        if k not in merged_earn:
            merged_earn[k] = v
        else:
            merged_earn[k] = max(merged_earn[k], v)
    merged["real_earnings"] = merged_earn

    # Цели - объединяем списки, дедупликация по id/name
    local_goals = local.get("goals") or []
    remote_goals = remote.get("goals") or []
    goals_by_id: Dict[str, Dict] = {}
    for g in remote_goals + local_goals:
        gid = g.get("id") or g.get("name", "")
        if gid:
            goals_by_id[gid] = g
    merged["goals"] = list(goals_by_id.values())

    # Числовые поля - берём максимум
    for field in ("daily_goal", "total_goal"):
        merged[field] = max(int(local.get(field, 0)), int(remote.get(field, 0)))

    # Настройки - берём локальные (на этом устройстве важнее)
    for field in ("goal_start_date", "active_goal_id", "sprint_duration",
                  "break_duration", "sprint_repeats"):
        merged[field] = local.get(field, remote.get(field))

    # Активная сессия - только локальная
    merged["active_session"] = local.get("active_session")
    return merged


class SyncManager:
    """Менеджер синхронизации прогресса через Git."""

    def __init__(self, on_status=None, auto_push_interval: int = 0):
        """
        on_status(text, color) - колбэк для UI статуса.
        auto_push_interval - интервал авто-пуша в минутах (0 = выключен).
        """
        self.on_status = on_status or (lambda t, c: None)
        self.auto_push_interval = auto_push_interval
        self._auto_push_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self.last_push_time: float = 0.0
        self.last_pull_time: float = 0.0
        self.enabled = True

    # ------------------------------------------------------------------ #
    #  PULL при старте                                                     #
    # ------------------------------------------------------------------ #

    def pull_on_start(self) -> str:
        """
        Синхронный вызов при запуске приложения.
        Возвращает строку статуса: 'up_to_date' | 'pulled_and_merged' |
        'pull_failed' | 'sync_disabled'
        """
        if not self.enabled:
            return "sync_disabled"

        local_data = _load_json(PROGRESS_FILE)
        mtime_before = self._file_mtime()

        ok, out = _run_git("pull", "--rebase", "origin", "main")
        if not ok:
            # Попробуем без rebase
            ok, out = _run_git("pull", "origin", "main")
        if not ok:
            self.last_pull_time = time.time()
            return "pull_failed"

        mtime_after = self._file_mtime()
        if mtime_after == mtime_before:
            self.last_pull_time = time.time()
            return "up_to_date"

        # Файл изменился - сливаем
        remote_data = _load_json(PROGRESS_FILE)
        if local_data and remote_data:
            merged = _merge_progress(local_data, remote_data)
            _save_json(PROGRESS_FILE, merged)

        self.last_pull_time = time.time()
        return "pulled_and_merged"

    # ------------------------------------------------------------------ #
    #  PUSH                                                                #
    # ------------------------------------------------------------------ #

    def push(self, message: str = "auto: sync progress", blocking: bool = False) -> None:
        """Закоммитить и запушить data/progress.json."""
        if not self.enabled:
            return
        if blocking:
            self._do_push(message)
        else:
            threading.Thread(target=self._do_push, args=(message,), daemon=True).start()

    def _do_push(self, message: str) -> None:
        self.on_status("Синхронизация...", "#ffd166")

        ok, _ = _run_git("add", "data/progress.json")
        if not ok:
            self.on_status("Ошибка git add", "#ff6b6b")
            return

        # Проверяем есть ли изменения
        ok_nochange, _ = _run_git("diff", "--cached", "--quiet")
        if ok_nochange:
            # Нет изменений
            self.on_status("Актуально", "#4ecdc4")
            self.last_push_time = time.time()
            return

        ok, out = _run_git("commit", "-m", message)
        if not ok:
            self.on_status("Ошибка git commit", "#ff6b6b")
            return

        ok, out = _run_git("push", "origin", "main")
        if ok:
            self.last_push_time = time.time()
            ts = time.strftime("%H:%M")
            self.on_status("Синхронизировано " + ts, "#4ecdc4")
        else:
            self.on_status("Ошибка git push", "#ff6b6b")

    # ------------------------------------------------------------------ #
    #  АВТОпуш                                                            #
    # ------------------------------------------------------------------ #

    def start_auto_push(self, interval_minutes: int = 10) -> None:
        """Запустить фоновый авто-пуш каждые N минут."""
        self.stop_auto_push()
        if interval_minutes <= 0:
            return
        self.auto_push_interval = interval_minutes
        self._stop_event.clear()
        self._auto_push_thread = threading.Thread(
            target=self._auto_push_loop, args=(interval_minutes,), daemon=True
        )
        self._auto_push_thread.start()

    def stop_auto_push(self) -> None:
        """Остановить фоновый авто-пуш."""
        self._stop_event.set()

    def _auto_push_loop(self, interval_minutes: int) -> None:
        interval_sec = interval_minutes * 60
        while not self._stop_event.wait(timeout=interval_sec):
            self._do_push("auto: sync every " + str(interval_minutes) + "min")

    # ------------------------------------------------------------------ #
    #  Вспомогательные                                                    #
    # ------------------------------------------------------------------ #

    def _file_mtime(self) -> float:
        try:
            return PROGRESS_FILE.stat().st_mtime
        except Exception:
            return 0.0

    def get_last_remote_info(self) -> str:
        """Когда последний раз обновлялся remote (человекочитаемо)."""
        ok, out = _run_git("log", "origin/main", "-1", "--format=%cr", timeout=8)
        if ok and out:
            return out.strip()
        return "?"

    def is_git_available(self) -> bool:
        ok, _ = _run_git("--version", timeout=5)
        return ok
