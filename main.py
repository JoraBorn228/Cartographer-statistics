#!/usr/bin/env python3
"""
Трекер продуктивности картографа.
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from logic import TrackerLogic
from gui import TrackerGUI
from storage import load_progress
from settings_manager import load_settings


def main():
    data = load_progress()
    settings = load_settings()

    logic = TrackerLogic()
    logic.points = data.get("points", 0)
    logic.level = data.get("level", 1)
    logic.sessions = data.get("sessions", [])
    logic.daily_goal = data.get("daily_goal", 0)
    logic.goal_start_date = data.get("goal_start_date", time.strftime("%Y-%m-%d"))
    logic.records = data.get("records", {
        "max_points_per_day": 0,
        "max_points_per_sprint": 0,
        "max_speed_per_session": 0.0,
        "max_speed_per_day": 0.0,
    })

    # Применяем настройки
    logic.sprint_duration = settings.get("sprint_duration", 15)
    logic.break_duration = settings.get("break_duration", 5)
    logic.sprint_repeats = settings.get("sprint_repeats", 1)
    logic.point_price = settings.get("point_price", 1.3)
    logic.auto_save_interval = settings.get("auto_save_interval", 60)
    logic.sound_enabled = settings.get("sound_enabled", True)
    logic.auto_goal_adjustment = settings.get("auto_goal_adjustment", True)

    # Комбо удалено, проверка не нужна
    # if logic.last_press_time and (time.time() - logic.last_press_time) > logic.combo_timeout:
    #     logic.combo = 0

    gui = TrackerGUI(logic)
    gui.run()


if __name__ == "__main__":
    main()