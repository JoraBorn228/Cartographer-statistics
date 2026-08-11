"""
Управление настройками приложения (сохранение/загрузка).
"""
import json
from pathlib import Path

SETTINGS_FILE = Path(__file__).parent.parent.parent / "data" / "settings.json"

DEFAULT_SETTINGS = {
    "sprint_duration": 15,
    "break_duration": 5,
    "sprint_repeats": 1,
    "point_price": 1.3,
    "auto_save_interval": 60,
    "sound_enabled": True,
    "auto_goal_adjustment": True,
}


def save_settings(settings: dict):
    # Создаём папку data, если её нет
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_FILE.write_text(json.dumps(settings, indent=2, ensure_ascii=False), encoding="utf-8")


def load_settings() -> dict:
    if not SETTINGS_FILE.exists():
        return DEFAULT_SETTINGS.copy()
    try:
        data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        for key, value in DEFAULT_SETTINGS.items():
            if key not in data:
                data[key] = value
        return data
    except (json.JSONDecodeError, OSError):
        return DEFAULT_SETTINGS.copy()