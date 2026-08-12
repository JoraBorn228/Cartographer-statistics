"""
Загрузка и сохранение данных в JSON.
"""
import json
import time
import os
from pathlib import Path
from typing import List, Dict, Any, Optional

from src.core.models import Session, sessions_from_list, sessions_to_list

# Путь к файлу с данными теперь в папке data
SAVE_FILE = Path(__file__).parent.parent.parent / "data" / "progress.json"


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
    current_phase: str = "idle",
    current_sprint_index: int = 0,
    current_cycle: int = 0,
    sprint_finished: bool = False,
    current_phase_start: Optional[float] = None,
    current_tab: str = "",
    last_tab_poll: float = 0.0,
    recording: bool = False,
    total_goal: int = 0,
    total_goal_achieved_notified: bool = False,
    real_earnings: Optional[Dict[str, float]] = None,
    goals: Optional[List[Dict]] = None,
    active_goal_id: Optional[str] = None,
    paused: bool = False,
    pause_start: Optional[float] = None,
    paused_accumulated: float = 0.0,
) -> None:
    """Сохранить прогресс, включая состояние активной сессии.
    
    Защита: если real_earnings или goals пустые, пытаемся сохранить
    старые значения из файла, чтобы авто-сохранение не затёрло данные.
    """
    if real_earnings is None:
        real_earnings = {}
    if goals is None:
        goals = []
    
    # === ЗАЩИТА ОТ СЛУЧАЙНОГО УДАЛЕНИЯ ДАННЫХ АВТО-СОХРАНЕНИЕМ ===
    # Если real_earnings или goals пустые, пытаемся сохранить
    # старые значения из файла. Это защищает от ситуации, когда
    # в памяти данные случайно очищаются, а авто-сохранение
    # каждые 60 секунд перезаписывает файл пустыми значениями.
    if not real_earnings and SAVE_FILE.exists():
        try:
            old_data = json.loads(SAVE_FILE.read_text(encoding="utf-8"))
            old_real = old_data.get("real_earnings")
            if isinstance(old_real, dict) and len(old_real) > 0:
                real_earnings = old_real
        except Exception:
            pass
    
    if not goals and SAVE_FILE.exists():
        try:
            old_data = json.loads(SAVE_FILE.read_text(encoding="utf-8"))
            old_goals = old_data.get("goals")
            if isinstance(old_goals, list) and len(old_goals) > 0:
                goals = old_goals
        except Exception:
            pass
    
    all_sessions = sessions.copy()
    
    active_session_data = None
    if session_active and session_start is not None:
        active_session_data = {
            "active": True,
            "started_at": session_start,
            "points": session_points,
            "tab_times": tab_times,
            "current_phase": current_phase,
            "current_sprint_index": current_sprint_index,
            "current_cycle": current_cycle,
            "sprint_finished": sprint_finished,
            "phase_start": current_phase_start,
            "current_tab": current_tab,
            "last_tab_poll": last_tab_poll,
            "recording": recording,
            "paused": paused,
            "pause_start": pause_start,
            "paused_accumulated": paused_accumulated,
        }

    data = {
        "points": points,
        "level": level,
        "sprint_duration": sprint_duration,
        "break_duration": break_duration,
        "sprint_repeats": sprint_repeats,
        "sessions": sessions_to_list(all_sessions),
        "daily_goal": daily_goal,
        "goal_start_date": goal_start_date,
        "active_session": active_session_data,
        "total_goal": total_goal,
        "total_goal_achieved_notified": total_goal_achieved_notified,
        "real_earnings": real_earnings,
        "goals": goals,
        "active_goal_id": active_goal_id,
    }
    
    # Создаём папку data, если её нет
    SAVE_FILE.parent.mkdir(parents=True, exist_ok=True)
    temp_file = SAVE_FILE.with_suffix(".tmp")
    temp_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(temp_file, SAVE_FILE)


def save_logic_progress(logic: Any) -> None:
    """Сохранить всё состояние TrackerLogic без дублирования списка аргументов в UI."""
    save_progress(
        points=logic.points,
        level=logic.level,
        sprint_duration=logic.sprint_duration,
        break_duration=logic.break_duration,
        sprint_repeats=logic.sprint_repeats,
        sessions=logic.sessions,
        session_active=logic.session_active,
        session_start=logic.session_start,
        session_points=logic.session_points,
        tab_times=logic.tab_times,
        daily_goal=logic.daily_goal,
        goal_start_date=logic.goal_start_date,
        current_phase=logic.current_phase,
        current_sprint_index=logic.current_sprint_index,
        current_cycle=logic.current_cycle,
        sprint_finished=logic.sprint_finished,
        current_phase_start=logic.current_phase_start,
        current_tab=logic.current_tab,
        last_tab_poll=logic._last_tab_poll,
        recording=logic._recording,
        total_goal=logic.total_goal,
        total_goal_achieved_notified=logic.total_goal_achieved_notified,
        real_earnings=logic.real_earnings,
        goals=logic.goals,
        active_goal_id=logic.active_goal_id,
        paused=logic.paused,
        pause_start=logic.pause_start,
        paused_accumulated=logic.paused_accumulated,
    )


def load_progress() -> Dict[str, Any]:
    """Загрузить прогресс."""
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

    # === МИГРАЦИЯ: восстановление перепутанных полей ===
    # Если данные перепутались (реальные заработки попали в total_goal_achieved_notified,
    # цели попали в real_earnings и т.д.), пытаемся восстановить их на правильные места.
    if not isinstance(data.get("real_earnings"), dict):
        real_earnings_value = data.get("real_earnings")
        goals_value = data.get("goals")
        achieved_value = data.get("total_goal_achieved_notified")
        
        # Проверяем, не перепутаны ли поля
        # real_earnings должен быть dict с датами -> числа
        # Если real_earnings — список с объектами типа "name", "target_amount" — это цели
        # Если total_goal_achieved_notified — dict с датами -> числа — это реальные заработки
        
        is_real_earnings_actually_goals = (
            isinstance(real_earnings_value, list) 
            and len(real_earnings_value) > 0
            and isinstance(real_earnings_value[0], dict)
            and any(k in real_earnings_value[0] for k in ("name", "target_amount", "mode"))
        )
        
        is_goals_actually_active_id = (
            isinstance(goals_value, str)
            and goals_value.replace(".", "").isdigit()
        )
        
        is_achieved_actually_real_earnings = (
            isinstance(achieved_value, dict)
            and len(achieved_value) > 0
            and any(isinstance(v, (int, float)) for v in achieved_value.values())
            and any(k.isdigit() or "-" in str(k) for k in achieved_value.keys())
        )
        
        # Если поля перепутаны — меняем их местами
        if is_real_earnings_actually_goals:
            if is_achieved_actually_real_earnings:
                # Меняем real_earnings и total_goal_achieved_notified местами
                data["real_earnings"] = achieved_value
                data["total_goal_achieved_notified"] = False
                print("[storage] Миграция: real_earnings и total_goal_achieved_notified перепутаны — восстановлено")
            elif not isinstance(real_earnings_value, dict):
                data["real_earnings"] = {}
        
        if is_goals_actually_active_id:
            # goals содержит id — переносим в active_goal_id
            data["active_goal_id"] = goals_value
            data["goals"] = real_earnings_value if is_real_earnings_actually_goals else []
            print(f"[storage] Миграция: goals был id '{goals_value}' — восстановлен active_goal_id")
        elif not isinstance(goals_value, list):
            data["goals"] = []
        
        # Если goals был строкой, а real_earnings был списком целей — восстанавливаем цели
        if is_goals_actually_active_id and is_real_earnings_actually_goals:
            data["goals"] = real_earnings_value
        elif not isinstance(data.get("goals"), list):
            data["goals"] = []
    
    if not isinstance(data.get("total_goal"), (int, float)):
        # Проверяем, не boolean ли это
        if isinstance(data.get("total_goal"), bool):
            data["total_goal"] = 0
        else:
            data["total_goal"] = 0
    if not isinstance(data.get("total_goal_achieved_notified"), bool):
        data["total_goal_achieved_notified"] = False
    if not isinstance(data.get("active_goal_id"), (str, type(None))):
        data["active_goal_id"] = None

    return {
        "points": int(data.get("points", 0)),
        "level": int(data.get("level", 1)),
        "sprint_duration": int(data.get("sprint_duration", 15)),
        "break_duration": int(data.get("break_duration", 5)),
        "sprint_repeats": int(data.get("sprint_repeats", 1)),
        "sessions": sessions_from_list(data.get("sessions", [])),
        "daily_goal": int(data.get("daily_goal", 0)),
        "goal_start_date": data.get("goal_start_date", time.strftime("%Y-%m-%d")),
        "active_session": data.get("active_session"),
        "total_goal": int(data.get("total_goal", 0)),
        "total_goal_achieved_notified": data.get("total_goal_achieved_notified", False),
        "real_earnings": data.get("real_earnings", {}),
        "goals": data.get("goals", []),
        "active_goal_id": data.get("active_goal_id", None),
    }
