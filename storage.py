"""
Загрузка и сохранение данных в JSON.
"""
import json
import time
from pathlib import Path
from typing import List, Dict, Any, Optional

from models import Session, sessions_from_list, sessions_to_list
from config import SAVE_FILE


def save_progress(
    points: int,
    level: int,
    sprint_duration: int,
    break_duration: int,
    sprint_repeats: int,
    sessions: List[Session],
    session_active: bool,
    session_start: Optional[float],
    session_points: int,
    tab_times: Dict[str, float],
    daily_goal: int,
    goal_start_date: str,
    records: Dict[str, Any],
) -> None:
    all_sessions = sessions.copy()
    if session_active and session_start is not None:
        now = time.time()
        live_session = Session(
            started_at=session_start,
            ended_at=now,
            points=session_points,
            tab_times=dict(tab_times),
        )
        all_sessions.append(live_session)

    data = {
        "points": points,
        "level": level,
        "sprint_duration": sprint_duration,
        "break_duration": break_duration,
        "sprint_repeats": sprint_repeats,
        "sessions": sessions_to_list(all_sessions),
        "daily_goal": daily_goal,
        "goal_start_date": goal_start_date,
        "records": records,
    }
    SAVE_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def load_progress() -> Dict[str, Any]:
    if not SAVE_FILE.exists():
        return {}

    try:
        data = json.loads(SAVE_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}

    # Миграция старых данных
    if "sessions" not in data:
        old_last = data.get("last_session")
        if old_last:
            started = old_last.get("started_at")
            ended = old_last.get("ended_at", time.time())
            if started is None:
                started = ended - old_last.get("duration", 0)
            data["sessions"] = [{
                "started_at": started,
                "ended_at": ended,
                "points": old_last.get("points", 0),
                "tab_times": old_last.get("tab_times", {}),
            }]
        else:
            data["sessions"] = []

    if "daily_goal" not in data:
        data["daily_goal"] = 0
    if "goal_start_date" not in data:
        data["goal_start_date"] = time.strftime("%Y-%m-%d")
    if "records" not in data:
        data["records"] = {
            "max_points_per_day": 0,
            "max_points_per_sprint": 0,
            "max_speed_per_session": 0.0,
            "max_speed_per_day": 0.0,
        }

    return {
        "points": int(data.get("points", 0)),
        "level": int(data.get("level", 1)),
        "sprint_duration": int(data.get("sprint_duration", 15)),
        "break_duration": int(data.get("break_duration", 5)),
        "sprint_repeats": int(data.get("sprint_repeats", 1)),
        "sessions": sessions_from_list(data.get("sessions", [])),
        "daily_goal": int(data.get("daily_goal", 0)),
        "goal_start_date": data.get("goal_start_date", time.strftime("%Y-%m-%d")),
        "records": data.get("records", {}),
    }