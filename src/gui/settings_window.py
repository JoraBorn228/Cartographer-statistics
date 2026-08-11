"""
Окно настроек приложения.
"""
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable

from src.utils.config import BG, FG, ACCENT, BTN_BG, BTN_ACTIVE, BAR_BG
from src.core.settings_manager import load_settings, save_settings, DEFAULT_SETTINGS
from src.core.profile_manager import ProfileManager
from src.gui.profile_editor import ProfileEditor


class SettingsWindow:
    def __init__(self, parent, logic, on_settings_changed: Callable):
        self.parent = parent
        self.logic = logic
        self.on_settings_changed = on_settings_changed

        self.settings = load_settings()
        self.profile_manager = ProfileManager()

        self.window = tk.Toplevel(parent)
        self.window.title("⚙️ Настройки")
        self.window.geometry("550x650")
        self.window.minsize(500, 600)
        self.window.configure(bg=BG)
        self.window.attributes("-topmost", True)

        self._build_ui()
        self._update_profile_info()

    def _build_ui(self):
        # Заголовок
        header = tk.Frame(self.window, bg=BG)
        header.pack(fill=tk.X, padx=15, pady=(12, 8))
        
        tk.Label(
            header,
            text="⚙️ Настройки",
            font=("Segoe UI", 16, "bold"),
            fg=ACCENT,
            bg=BG
        ).pack(side=tk.LEFT)

        # Canvas со скроллом
        canvas = tk.Canvas(self.window, bg=BG, highlightthickness=0)
        scrollbar = tk.Scrollbar(self.window, orient=tk.VERTICAL, command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=BG)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=(0, 5))
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=(0, 5))

        # ============================================================
        # ПРОФИЛЬ СПРИНТОВ
        # ============================================================
        self._add_section(scrollable_frame, "🎯 Профиль спринтов")

        profile_frame = tk.Frame(scrollable_frame, bg=BG, relief=tk.GROOVE, bd=1)
        profile_frame.pack(fill=tk.X, pady=3, padx=2)

        row1 = tk.Frame(profile_frame, bg=BG)
        row1.pack(fill=tk.X, padx=8, pady=(6, 2))

        tk.Label(
            row1,
            text="Активный профиль:",
            fg=FG,
            bg=BG,
            font=("Segoe UI", 9)
        ).pack(side=tk.LEFT)

        self.profile_label = tk.Label(
            row1,
            text="Загрузка...",
            fg=ACCENT,
            bg=BG,
            font=("Segoe UI", 9, "bold")
        )
        self.profile_label.pack(side=tk.LEFT, padx=(8, 0))

        row2 = tk.Frame(profile_frame, bg=BG)
        row2.pack(fill=tk.X, padx=8, pady=(2, 6))

        self.edit_btn = tk.Button(
            row2,
            text="📝 Редактировать профили",
            command=self._edit_profiles,
            bg=BTN_ACTIVE,
            fg=BG,
            font=("Segoe UI", 9, "bold"),
            relief=tk.FLAT,
            padx=12,
            pady=4,
            cursor="hand2"
        )
        self.edit_btn.pack(side=tk.LEFT)

        tk.Label(
            row2,
            text="Создайте свои последовательности",
            fg="#666",
            bg=BG,
            font=("Segoe UI", 8)
        ).pack(side=tk.LEFT, padx=(10, 0))

        # ============================================================
        # БАЗОВЫЕ НАСТРОЙКИ
        # ============================================================
        self._add_section(scrollable_frame, "⏱ Базовые настройки спринтов")

        tk.Label(
            scrollable_frame,
            text="Используются, если не выбран профиль",
            fg="#666",
            bg=BG,
            font=("Segoe UI", 8)
        ).pack(anchor=tk.W, padx=8, pady=(0, 5))

        # Спринт
        row = tk.Frame(scrollable_frame, bg=BG)
        row.pack(fill=tk.X, pady=3, padx=5)
        tk.Label(row, text="Длительность спринта (мин):", fg=FG, bg=BG, width=22, anchor=tk.W).pack(side=tk.LEFT)
        self.sprint_var = tk.StringVar(value=str(self.settings.get("sprint_duration", 15)))
        ttk.Combobox(
            row, textvariable=self.sprint_var,
            values=[5, 10, 15, 20, 25, 30, 45, 60],
            width=8, state="readonly"
        ).pack(side=tk.LEFT)

        # Перерыв
        row = tk.Frame(scrollable_frame, bg=BG)
        row.pack(fill=tk.X, pady=3, padx=5)
        tk.Label(row, text="Длительность перерыва (мин):", fg=FG, bg=BG, width=22, anchor=tk.W).pack(side=tk.LEFT)
        self.break_var = tk.StringVar(value=str(self.settings.get("break_duration", 5)))
        ttk.Combobox(
            row, textvariable=self.break_var,
            values=[1, 2, 3, 5, 10, 15],
            width=8, state="readonly"
        ).pack(side=tk.LEFT)

        # Повторы
        row = tk.Frame(scrollable_frame, bg=BG)
        row.pack(fill=tk.X, pady=3, padx=5)
        tk.Label(row, text="Количество повторов:", fg=FG, bg=BG, width=22, anchor=tk.W).pack(side=tk.LEFT)
        self.repeats_var = tk.StringVar(value=str(self.settings.get("sprint_repeats", 1)))
        ttk.Combobox(
            row, textvariable=self.repeats_var,
            values=list(range(1, 11)),
            width=8, state="readonly"
        ).pack(side=tk.LEFT)

        # ============================================================
        # ЦЕЛЬ
        # ============================================================
        self._add_section(scrollable_frame, "🎯 Цель")

        row = tk.Frame(scrollable_frame, bg=BG)
        row.pack(fill=tk.X, pady=3, padx=5)
        tk.Label(row, text="Автоматическая корректировка цели:", fg=FG, bg=BG, width=22, anchor=tk.W).pack(side=tk.LEFT)
        self.auto_goal_var = tk.BooleanVar(value=self.settings.get("auto_goal_adjustment", True))
        tk.Checkbutton(
            row, variable=self.auto_goal_var,
            bg=BG, fg=FG, selectcolor=BG, activebackground=BG
        ).pack(side=tk.LEFT)

        # ============================================================
        # ЗАРАБОТОК
        # ============================================================
        self._add_section(scrollable_frame, "💰 Заработок")

        row = tk.Frame(scrollable_frame, bg=BG)
        row.pack(fill=tk.X, pady=3, padx=5)
        tk.Label(row, text="Цена одной точки (руб.):", fg=FG, bg=BG, width=22, anchor=tk.W).pack(side=tk.LEFT)
        self.price_var = tk.StringVar(value=str(self.settings.get("point_price", 1.3)))
        tk.Entry(
            row, textvariable=self.price_var,
            width=8, bg=BAR_BG, fg=FG, insertbackground=FG
        ).pack(side=tk.LEFT)

        # ============================================================
        # СИСТЕМНЫЕ
        # ============================================================
        self._add_section(scrollable_frame, "⚙️ Системные")

        row = tk.Frame(scrollable_frame, bg=BG)
        row.pack(fill=tk.X, pady=3, padx=5)
        tk.Label(row, text="Интервал автосохранения (сек):", fg=FG, bg=BG, width=22, anchor=tk.W).pack(side=tk.LEFT)
        self.auto_save_var = tk.StringVar(value=str(self.settings.get("auto_save_interval", 60)))
        tk.Entry(
            row, textvariable=self.auto_save_var,
            width=8, bg=BAR_BG, fg=FG, insertbackground=FG
        ).pack(side=tk.LEFT)

        # ============================================================
        # ЗВУКИ
        # ============================================================
        self._add_section(scrollable_frame, "🔊 Звуки")

        row = tk.Frame(scrollable_frame, bg=BG)
        row.pack(fill=tk.X, pady=3, padx=5)
        tk.Label(row, text="Включить звуки:", fg=FG, bg=BG, width=22, anchor=tk.W).pack(side=tk.LEFT)
        self.sound_var = tk.BooleanVar(value=self.settings.get("sound_enabled", True))
        tk.Checkbutton(
            row, variable=self.sound_var,
            bg=BG, fg=FG, selectcolor=BG, activebackground=BG
        ).pack(side=tk.LEFT)

        # ============================================================
        # КНОПКИ
        # ============================================================
        btn_frame = tk.Frame(self.window, bg=BG)
        btn_frame.pack(fill=tk.X, padx=15, pady=12)

        tk.Button(
            btn_frame,
            text="💾 Сохранить",
            command=self._save_settings,
            bg=BTN_ACTIVE,
            fg=BG,
            font=("Segoe UI", 10, "bold"),
            relief=tk.FLAT,
            padx=20,
            pady=6,
            cursor="hand2"
        ).pack(side=tk.LEFT, padx=(0, 8))

        tk.Button(
            btn_frame,
            text="🔄 Сброс",
            command=self._reset_defaults,
            bg=BTN_BG,
            fg=FG,
            font=("Segoe UI", 10),
            relief=tk.FLAT,
            padx=16,
            pady=6,
            cursor="hand2"
        ).pack(side=tk.LEFT, padx=(0, 8))

        tk.Button(
            btn_frame,
            text="❌ Закрыть",
            command=self.window.destroy,
            bg=BTN_BG,
            fg=FG,
            font=("Segoe UI", 10),
            relief=tk.FLAT,
            padx=16,
            pady=6,
            cursor="hand2"
        ).pack(side=tk.LEFT)

    def _add_section(self, parent, title):
        tk.Label(
            parent,
            text=title,
            font=("Segoe UI", 11, "bold"),
            fg=ACCENT,
            bg=BG
        ).pack(anchor=tk.W, pady=(10, 4), padx=5)

    def _update_profile_info(self):
        """Обновить информацию о профиле (с проверкой, что виджет существует)."""
        # Проверяем, что окно ещё существует
        try:
            if not self.window.winfo_exists():
                return
        except:
            return
        
        profile = self.profile_manager.get_active_profile()
        if profile:
            phase_count = len(profile.phases)
            self.profile_label.config(text=f"{profile.name} ({phase_count} фаз)")
        else:
            self.profile_label.config(text="Не выбран")

    def _edit_profiles(self):
        """Открыть редактор профилей."""
        try:
            editor = ProfileEditor(self.window, self.profile_manager, self._update_profile_info)
            self.window.wait_window(editor.window)
            
            # Проверяем, что окно ещё существует перед обновлением
            if self.window.winfo_exists():
                self._update_profile_info()
                self.profile_manager.apply_profile_to_logic(self.logic)
                self.on_settings_changed()
        except Exception as e:
            print(f"Ошибка при открытии редактора профилей: {e}")

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

        self.profile_manager.apply_profile_to_logic(self.logic)
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