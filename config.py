"""
Глобальные константы и настройки приложения.
"""
from pathlib import Path

# --- Размеры окна ---
WINDOW_W = 420
WINDOW_H = 420

# --- Файл сохранения ---
SAVE_FILE = Path(__file__).parent / "progress.json"

# --- Маркеры для определения продуктивной вкладки (расширены) ---
PRODUCTIVE_TAB_MARKERS = ("бекофис", "бэкофис", "backoffice", "яндекс", "yandex")

# --- Настройки спринтов (доступные значения для выпадающих списков) ---
SPRINT_DURATIONS = (5, 10, 15, 20, 25, 30, 45, 60)
BREAK_DURATIONS = (1, 2, 3, 5, 10, 15)
REPEAT_OPTIONS = list(range(1, 11))

# --- Звания (по накопленным очкам) ---
RANKS = {
    0: "Стажёр",
    100: "Картограф",
    500: "Эксперт",
    1000: "Мастер",
    5000: "Гуру",
    10000: "Легенда"
}

# --- Цветовая схема ---
BG = "#1a1a2e"
BG_FLASH = "#3d3d6b"
FG = "#eaeaea"
ACCENT = "#00d4aa"
LEVEL_COLOR = "#ff6b6b"
BAR_BG = "#2a2a40"
BAR_FG = "#00d4aa"
GOAL_BAR_FG = "#ffd166"
BTN_BG = "#2a2a40"
BTN_ACTIVE = "#00d4aa"
BTN_STOP = "#ff6b6b"
PARTICLE_COLORS = ("#00d4aa", "#ffd166", "#ff6b6b", "#4ecdc4", "#a29bfe")

# --- Суффиксы браузеров для парсинга заголовка окна ---
BROWSER_SUFFIXES = (
    " - Google Chrome",
    " — Google Chrome",
    " - Mozilla Firefox",
    " — Mozilla Firefox",
    " - Microsoft Edge",
    " — Microsoft Edge",
    " - Opera",
    " - Brave",
    " - Yandex",
    " - Vivaldi",
)