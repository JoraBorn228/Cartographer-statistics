"""
Глобальные константы и настройки приложения.
"""
from pathlib import Path

# --- Размеры окна ---
WINDOW_W = 440
WINDOW_H = 520

# --- Файл сохранения ---
SAVE_FILE = Path(__file__).parent / "progress.json"

# --- Маркеры для определения продуктивной вкладки ---
PRODUCTIVE_TAB_MARKERS = ("бекофис", "бэкофис", "backoffice", "яндекс", "yandex")

# --- Настройки спринтов ---
SPRINT_DURATIONS = (5, 10, 15, 20, 25, 30, 45, 60)
BREAK_DURATIONS = (1, 2, 3, 5, 10, 15)
REPEAT_OPTIONS = list(range(1, 11))

# --- Звания ---
RANKS = {
    0: "🌱 Стажёр",
    100: "🗺️ Картограф",
    500: "📐 Эксперт",
    1000: "🏅 Мастер",
    5000: "👑 Гуру",
    10000: "🌟 Легенда"
}

# --- Цветовая схема ---
BG = "#0a0a1a"
BG_CARD = "#141430"
BG_CARD_HOVER = "#1a1a3e"
BG_FLASH = "#1a1a3e"
FG = "#eaeaea"
FG_SECONDARY = "#8888aa"
ACCENT = "#00d4aa"
ACCENT_DARK = "#00a88a"
LEVEL_COLOR = "#ff6b6b"
COMBO_COLOR = "#ffd166"
BAR_BG = "#1a1a3e"
BAR_FG = "#00d4aa"
GOAL_BAR_FG = "#ffd166"
BTN_BG = "#1a1a3e"
BTN_ACTIVE = "#00d4aa"
BTN_STOP = "#ff6b6b"
BTN_HOVER = "#2a2a5e"
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