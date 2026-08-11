"""
Чистые вспомогательные функции, не зависящие от состояния приложения.
"""
import math
import ctypes
from datetime import datetime
from typing import Optional

from src.utils.config import PRODUCTIVE_TAB_MARKERS, BROWSER_SUFFIXES


def calc_level(points: int) -> int:
    return math.floor((points / 50) ** 1.3) + 1


def format_duration(seconds: float) -> str:
    total = int(seconds)
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def format_datetime(ts: float) -> str:
    return datetime.fromtimestamp(ts).strftime("%d.%m.%Y %H:%M:%S")


def is_productive_tab(title: str) -> bool:
    """Проверить, является ли заголовок вкладки продуктивным (Бекофис Панорам)."""
    lower = title.lower()
    # Содержит "панорам" и один из маркеров (теперь включает "яндекс")
    return "панорам" in lower and any(m in lower for m in PRODUCTIVE_TAB_MARKERS)


def get_productive_tab_time(tab_times: dict[str, float]) -> float:
    return sum(secs for title, secs in tab_times.items() if is_productive_tab(title))


def calc_points_per_hour(points: int, seconds: float) -> Optional[float]:
    if seconds <= 0 or points <= 0:
        return None
    return points / (seconds / 3600)


def format_points_per_hour(points: int, seconds: float) -> str:
    pph = calc_points_per_hour(points, seconds)
    if pph is None:
        return "—"
    return f"{pph:.1f} точ/ч"


def parse_tab_title(window_title: str) -> str:
    if not window_title:
        return "—"
    for suffix in BROWSER_SUFFIXES:
        if window_title.endswith(suffix):
            return window_title[: -len(suffix)].strip() or window_title
    return window_title.strip()


def get_active_window_title() -> str:
    try:
        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        length = user32.GetWindowTextLengthW(hwnd) + 1
        buf = ctypes.create_unicode_buffer(length)
        user32.GetWindowTextW(hwnd, buf, length)
        return buf.value
    except Exception:
        return ""