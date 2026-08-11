#!/usr/bin/env python3
"""
Трекер продуктивности картографа.
Точка входа.
"""
import sys
import time
from pathlib import Path

# Добавляем путь к src для импортов
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.logic import TrackerLogic
from src.gui.main_window import TrackerGUI
from src.core.storage import load_progress
from src.core.settings_manager import load_settings


def main():
    data = load_progress()
    settings = load_settings()

    logic = TrackerLogic()
    logic.points = data.get("points", 0)
    logic.level = data.get("level", 1)
    logic.sessions = data.get("sessions", [])
    logic.daily_goal = data.get("daily_goal", 0)
    logic.goal_start_date = data.get("goal_start_date", time.strftime("%Y-%m-%d"))

    logic.total_goal = data.get("total_goal", 0)
    logic.total_goal_achieved_notified = data.get("total_goal_achieved_notified", False)
    logic.real_earnings = data.get("real_earnings", {})
    logic.goals = data.get("goals", [])
    logic.active_goal_id = data.get("active_goal_id", None)

    # Применяем настройки
    logic.sprint_duration = settings.get("sprint_duration", 15)
    logic.break_duration = settings.get("break_duration", 5)
    logic.sprint_repeats = settings.get("sprint_repeats", 1)
    logic.point_price = settings.get("point_price", 1.3)
    logic.auto_save_interval = settings.get("auto_save_interval", 60)
    logic.sound_enabled = settings.get("sound_enabled", True)
    logic.auto_goal_adjustment = settings.get("auto_goal_adjustment", True)

    gui = TrackerGUI(logic)
    gui.run()


if __name__ == "__main__":
    main()