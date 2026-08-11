"""
Окно настроек приложения.
"""
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable

from src.utils.config import BG, FG, ACCENT, BTN_BG, BTN_ACTIVE, BAR_BG
from src.core.settings_manager import load_settings, save_settings, DEFAULT_SETTINGS



class SettingsWindow:
    def __init__(self, parent, logic, on_settings_changed: Callable):
        self.parent = parent
        self.logic = logic
        self.on_settings_changed = on_settings_changed

        self.settings = load_settings()

        self.window = tk.Toplevel(parent)
        self.window.title("⚙️ Настройки")
        self.window.geometry("500x480")
        self.window.configure(bg=BG)
        self.window.attributes("-topmost", True)
        self.window.resizable(False, False)

        self._build_ui()

    def _build_ui(self):
        tk.Label(
            self.window,
            text="Настройки приложения",
            font=("Segoe UI", 14, "bold"),
            fg=ACCENT,
            bg=BG
        ).pack(pady=(15, 10))

        canvas = tk.Canvas(self.window, bg=BG, highlightthickness=0)
        scrollbar = tk.Scrollbar(self.window, orient=tk.VERTICAL, command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=BG)
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # ---------- Секция: Спринты ----------
        self._add_section(scrollable_frame, "Настройки спринтов")

        row1 = tk.Frame(scrollable_frame, bg=BG)
        row1.pack(fill=tk.X, pady=3)
        tk.Label(row1, text="Длительность спринта (мин):", fg=FG, bg=BG, width=25, anchor=tk.W).pack(side=tk.LEFT)
        self.sprint_var = tk.StringVar(value=str(self.settings.get("sprint_duration", 15)))
        sprint_combo = ttk.Combobox(row1, textvariable=self.sprint_var, values=[5,10,15,20,25,30,45,60], width=8, state="readonly")
        sprint_combo.pack(side=tk.LEFT)

        row2 = tk.Frame(scrollable_frame, bg=BG)
        row2.pack(fill=tk.X, pady=3)
        tk.Label(row2, text="Длительность перерыва (мин):", fg=FG, bg=BG, width=25, anchor=tk.W).pack(side=tk.LEFT)
        self.break_var = tk.StringVar(value=str(self.settings.get("break_duration", 5)))
        break_combo = ttk.Combobox(row2, textvariable=self.break_var, values=[1,2,3,5,10,15], width=8, state="readonly")
        break_combo.pack(side=tk.LEFT)

        row3 = tk.Frame(scrollable_frame, bg=BG)
        row3.pack(fill=tk.X, pady=3)
        tk.Label(row3, text="Количество повторов:", fg=FG, bg=BG, width=25, anchor=tk.W).pack(side=tk.LEFT)
        self.repeats_var = tk.StringVar(value=str(self.settings.get("sprint_repeats", 1)))
        repeats_combo = ttk.Combobox(row3, textvariable=self.repeats_var, values=list(range(1,11)), width=8, state="readonly")
        repeats_combo.pack(side=tk.LEFT)

        # ---------- Секция: Цель ----------
        self._add_section(scrollable_frame, "Цель")

        row4 = tk.Frame(scrollable_frame, bg=BG)
        row4.pack(fill=tk.X, pady=3)
        tk.Label(row4, text="Автоматическая корректировка цели:", fg=FG, bg=BG, width=25, anchor=tk.W).pack(side=tk.LEFT)
        self.auto_goal_var = tk.BooleanVar(value=self.settings.get("auto_goal_adjustment", True))
        tk.Checkbutton(row4, variable=self.auto_goal_var, bg=BG, fg=FG, selectcolor=BG, activebackground=BG).pack(side=tk.LEFT)

        # ---------- Секция: Заработок ----------
        self._add_section(scrollable_frame, "Заработок")

        row5 = tk.Frame(scrollable_frame, bg=BG)
        row5.pack(fill=tk.X, pady=3)
        tk.Label(row5, text="Цена одной точки (руб.):", fg=FG, bg=BG, width=25, anchor=tk.W).pack(side=tk.LEFT)
        self.price_var = tk.StringVar(value=str(self.settings.get("point_price", 1.3)))
        tk.Entry(row5, textvariable=self.price_var, width=8, bg=BAR_BG, fg=FG, insertbackground=FG).pack(side=tk.LEFT)

        # ---------- Секция: Системные ----------
        self._add_section(scrollable_frame, "Системные")

        row6 = tk.Frame(scrollable_frame, bg=BG)
        row6.pack(fill=tk.X, pady=3)
        tk.Label(row6, text="Интервал автосохранения (сек):", fg=FG, bg=BG, width=25, anchor=tk.W).pack(side=tk.LEFT)
        self.auto_save_var = tk.StringVar(value=str(self.settings.get("auto_save_interval", 60)))
        tk.Entry(row6, textvariable=self.auto_save_var, width=8, bg=BAR_BG, fg=FG, insertbackground=FG).pack(side=tk.LEFT)

        # ---------- Секция: Звуки ----------
        self._add_section(scrollable_frame, "Звуки")

        row7 = tk.Frame(scrollable_frame, bg=BG)
        row7.pack(fill=tk.X, pady=3)
        tk.Label(row7, text="Включить звуки:", fg=FG, bg=BG, width=25, anchor=tk.W).pack(side=tk.LEFT)
        self.sound_var = tk.BooleanVar(value=self.settings.get("sound_enabled", True))
        tk.Checkbutton(row7, variable=self.sound_var, bg=BG, fg=FG, selectcolor=BG, activebackground=BG).pack(side=tk.LEFT)

        # ---------- Кнопки ----------
        btn_frame = tk.Frame(self.window, bg=BG)
        btn_frame.pack(fill=tk.X, padx=10, pady=15)

        tk.Button(
            btn_frame,
            text="Сохранить",
            command=self._save_settings,
            bg=BTN_ACTIVE,
            fg=BG,
            relief=tk.FLAT,
            padx=15,
            pady=5,
            cursor="hand2"
        ).pack(side=tk.LEFT, padx=(0, 10))

        tk.Button(
            btn_frame,
            text="Сбросить к стандартным",
            command=self._reset_defaults,
            bg=BTN_BG,
            fg=FG,
            relief=tk.FLAT,
            padx=15,
            pady=5,
            cursor="hand2"
        ).pack(side=tk.LEFT, padx=(0, 10))

        tk.Button(
            btn_frame,
            text="Отмена",
            command=self.window.destroy,
            bg=BTN_BG,
            fg=FG,
            relief=tk.FLAT,
            padx=15,
            pady=5,
            cursor="hand2"
        ).pack(side=tk.LEFT)

    def _add_section(self, parent, title):
        tk.Label(
            parent,
            text=title,
            font=("Segoe UI", 10, "bold"),
            fg=ACCENT,
            bg=BG
        ).pack(anchor=tk.W, pady=(10, 3))

    def _save_settings(self):
        try:
            new_settings = {
                "sprint_duration": int(self.sprint_var.get()),
                "break_duration": int(self.break_var.get()),
                "sprint_repeats": int(self.repeats_var.get()),
                "point_price": float(self.price_var.get()),
                "auto_save_interval": int(self.auto_save_var.get()),
                "sound_enabled": self.sound_var.get(),
                "auto_goal_adjustment": self.auto_goal_var.get(),
            }
            if new_settings["sprint_duration"] <= 0:
                raise ValueError("Длительность спринта должна быть > 0")
            if new_settings["break_duration"] < 0:
                raise ValueError("Длительность перерыва не может быть отрицательной")
            if new_settings["point_price"] <= 0:
                raise ValueError("Цена точки должна быть > 0")
            if new_settings["auto_save_interval"] < 10:
                raise ValueError("Интервал автосохранения не может быть меньше 10 секунд")
        except ValueError as e:
            messagebox.showerror("Ошибка", str(e), parent=self.window)
            return

        save_settings(new_settings)

        self.logic.sprint_duration = new_settings["sprint_duration"]
        self.logic.break_duration = new_settings["break_duration"]
        self.logic.sprint_repeats = new_settings["sprint_repeats"]
        self.logic.point_price = new_settings["point_price"]
        self.logic.auto_save_interval = new_settings["auto_save_interval"]
        self.logic.sound_enabled = new_settings["sound_enabled"]
        self.logic.auto_goal_adjustment = new_settings["auto_goal_adjustment"]

        self.on_settings_changed()
        self.window.destroy()

    def _reset_defaults(self):
        if messagebox.askyesno("Сброс", "Сбросить все настройки к стандартным?", parent=self.window):
            self.sprint_var.set(str(DEFAULT_SETTINGS["sprint_duration"]))
            self.break_var.set(str(DEFAULT_SETTINGS["break_duration"]))
            self.repeats_var.set(str(DEFAULT_SETTINGS["sprint_repeats"]))
            self.price_var.set(str(DEFAULT_SETTINGS["point_price"]))
            self.auto_save_var.set(str(DEFAULT_SETTINGS["auto_save_interval"]))
            self.sound_var.set(DEFAULT_SETTINGS["sound_enabled"])
            self.auto_goal_var.set(DEFAULT_SETTINGS["auto_goal_adjustment"])