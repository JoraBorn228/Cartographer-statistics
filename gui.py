"""
Графический интерфейс на tkinter.
"""
import tkinter as tk
from tkinter import font as tkfont, ttk, messagebox, simpledialog
import time
import random
import math
from typing import Optional, List

from config import (
    WINDOW_W, WINDOW_H, BG, FG, ACCENT, LEVEL_COLOR,
    BAR_BG, BAR_FG, GOAL_BAR_FG, BTN_BG, BTN_ACTIVE, BTN_STOP, BG_FLASH,
    SPRINT_DURATIONS, BREAK_DURATIONS, REPEAT_OPTIONS,
)
from models import Particle, Session
from records_window import RecordsWindow
from utils import (
    format_duration, format_datetime, format_points_per_hour,
    is_productive_tab, get_productive_tab_time,
    calc_points_per_hour, calc_level,
)
from charts import ChartsWindow
from storage import save_progress
from floating import FloatingWidget
from settings_window import SettingsWindow
from stats_window import StatsWindow


class TrackerGUI:
    def __init__(self, logic):
        self.logic = logic
        self.root = tk.Tk()
        self.root.title("Картограф")
        self.root.geometry(f"{WINDOW_W}x{WINDOW_H}")
        self.root.resizable(False, False)
        self.root.configure(bg=BG)
        self.root.attributes("-topmost", True)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.logic.on_update = self.refresh_all
        self.logic.on_beep = self._beep
        self.logic.on_level_up = self._level_up_effect

        self.particles: List[Particle] = []
        self.points_scale = 1.0
        self.flash_frames = 0
        self._stats_window: Optional[StatsWindow] = None
        self._settings_window: Optional[SettingsWindow] = None
        self._last_today_points = 0
        self.floating_widget = None

        self._build_ui()
        self.logic.register_hotkey()
        self._tick()
        self._check_goal_adjustment()

    # ---------- Построение интерфейса ----------
    def _build_ui(self):
        self.big_font = tkfont.Font(family="Segoe UI", size=38, weight="bold")
        self.mid_font = tkfont.Font(family="Segoe UI", size=13, weight="bold")
        self.small_font = tkfont.Font(family="Segoe UI", size=9)
        self.btn_font = tkfont.Font(family="Segoe UI", size=9, weight="bold")

        top = tk.Frame(self.root, bg=BG)
        top.pack(fill=tk.X, padx=12, pady=(8, 0))

        self.rank_label = tk.Label(
            top, text="Стажёр", font=self.mid_font, fg=LEVEL_COLOR, bg=BG
        )
        self.rank_label.pack(side=tk.LEFT)

        right_top = tk.Frame(top, bg=BG)
        right_top.pack(side=tk.RIGHT)

        # Кнопки
        self.settings_btn = tk.Button(
            right_top,
            text="⚙️",
            font=self.btn_font,
            bg=BTN_BG,
            fg=FG,
            activebackground=ACCENT,
            relief=tk.FLAT,
            bd=0,
            padx=6,
            pady=2,
            cursor="hand2",
            command=self.show_settings,
        )
        self.settings_btn.pack(side=tk.LEFT, padx=(0, 4))

        self.stats_btn = tk.Button(
            right_top,
            text="📊",
            font=self.btn_font,
            bg=BTN_BG,
            fg=FG,
            activebackground=ACCENT,
            relief=tk.FLAT,
            bd=0,
            padx=6,
            pady=2,
            cursor="hand2",
            command=self.show_statistics,
        )
        self.stats_btn.pack(side=tk.LEFT, padx=(0, 4))

        self.charts_btn = tk.Button(
            right_top,
            text="📈",
            font=self.btn_font,
            bg=BTN_BG,
            fg=FG,
            activebackground=ACCENT,
            relief=tk.FLAT,
            bd=0,
            padx=6,
            pady=2,
            cursor="hand2",
            command=self.show_charts,
        )
        self.charts_btn.pack(side=tk.LEFT, padx=(0, 4))

        self.records_btn = tk.Button(
            right_top,
            text="🏆",
            font=self.btn_font,
            bg=BTN_BG,
            fg=FG,
            activebackground=ACCENT,
            relief=tk.FLAT,
            bd=0,
            padx=6,
            pady=2,
            cursor="hand2",
            command=self.show_records,
        )
        self.records_btn.pack(side=tk.LEFT, padx=(0, 4))

        self.floating_btn = tk.Button(
            right_top,
            text="🖥",
            font=self.btn_font,
            bg=BTN_BG,
            fg=FG,
            activebackground=ACCENT,
            relief=tk.FLAT,
            bd=0,
            padx=6,
            pady=2,
            cursor="hand2",
            command=self.toggle_floating,
        )
        self.floating_btn.pack(side=tk.LEFT)

        # Холст с числом очков
        self.canvas = tk.Canvas(
            self.root, width=WINDOW_W - 24, height=90, bg=BG, highlightthickness=0
        )
        self.canvas.pack(padx=12, pady=2)
        self.points_text = self.canvas.create_text(
            (WINDOW_W - 24) // 2, 45, text="0", fill=FG, font=self.big_font
        )

        # Вкладка
        self.tab_label = tk.Label(
            self.root,
            text="Вкладка: —",
            font=self.small_font,
            fg="#888",
            bg=BG,
            anchor=tk.W,
        )
        self.tab_label.pack(fill=tk.X, padx=12)

        # Статус фазы
        self.phase_label = tk.Label(
            self.root,
            text="Сессия: не начата",
            font=self.small_font,
            fg="#888",
            bg=BG,
            anchor=tk.W,
        )
        self.phase_label.pack(fill=tk.X, padx=12, pady=(2, 0))

        # Скорость
        self.speed_label = tk.Label(
            self.root,
            text="Скорость: —",
            font=self.small_font,
            fg=ACCENT,
            bg=BG,
            anchor=tk.W,
        )
        self.speed_label.pack(fill=tk.X, padx=12, pady=(2, 0))

        # Заработок
        self.earnings_label = tk.Label(
            self.root,
            text="💰 Сегодня: 0.00 руб. | Всего: 0.00 руб.",
            font=self.small_font,
            fg="#ffd700",
            bg=BG,
            anchor=tk.W,
        )
        self.earnings_label.pack(fill=tk.X, padx=12, pady=(2, 0))

        # Прогресс-бар цели
        goal_frame = tk.Frame(self.root, bg=BG)
        goal_frame.pack(fill=tk.X, padx=12, pady=(4, 0))

        self.goal_label = tk.Label(
            goal_frame,
            text="Цель на день: 0 / 0",
            font=self.small_font,
            fg="#888",
            bg=BG,
            anchor=tk.W,
        )
        self.goal_label.pack(fill=tk.X)

        self.goal_bar_bg = tk.Canvas(
            self.root, width=WINDOW_W - 24, height=8, bg=BAR_BG, highlightthickness=0
        )
        self.goal_bar_bg.pack(padx=12, pady=(2, 4))
        self.goal_bar_fill = self.goal_bar_bg.create_rectangle(0, 0, 0, 8, fill=GOAL_BAR_FG, width=0)

        # ETA
        self.eta_label = tk.Label(
            self.root,
            text="",
            font=self.small_font,
            fg="#888",
            bg=BG,
            anchor=tk.W,
        )
        self.eta_label.pack(fill=tk.X, padx=12, pady=(0, 2))


        # Кнопка установки цели
        goal_btn_frame = tk.Frame(self.root, bg=BG)
        goal_btn_frame.pack(fill=tk.X, padx=12, pady=(0, 4))
        tk.Button(
            goal_btn_frame,
            text="Установить цель",
            font=self.btn_font,
            bg=BTN_BG,
            fg=FG,
            activebackground=ACCENT,
            relief=tk.FLAT,
            bd=0,
            padx=6,
            pady=2,
            cursor="hand2",
            command=self._set_goal_dialog,
        ).pack(side=tk.LEFT)

        # Кнопки управления сессией
        session_frame = tk.Frame(self.root, bg=BG)
        session_frame.pack(fill=tk.X, padx=12, pady=(6, 0))

        self.start_btn = tk.Button(
            session_frame,
            text="▶ Старт",
            font=self.btn_font,
            bg=BTN_ACTIVE,
            fg=BG,
            activebackground="#00b894",
            relief=tk.FLAT,
            bd=0,
            padx=10,
            pady=4,
            cursor="hand2",
            command=self.logic.start_session,
        )
        self.start_btn.pack(side=tk.LEFT)

        self.stop_btn = tk.Button(
            session_frame,
            text="■ Стоп",
            font=self.btn_font,
            bg=BTN_STOP,
            fg=FG,
            activebackground="#e05555",
            relief=tk.FLAT,
            bd=0,
            padx=10,
            pady=4,
            cursor="hand2",
            command=self.logic.stop_session,
            state=tk.DISABLED,
        )
        self.stop_btn.pack(side=tk.LEFT, padx=(6, 0))

        # Прогресс-бар спринта
        self.bar_bg = tk.Canvas(
            self.root, width=WINDOW_W - 24, height=10, bg=BAR_BG, highlightthickness=0
        )
        self.bar_bg.pack(padx=12, pady=(6, 2))
        self.bar_fill = self.bar_bg.create_rectangle(0, 0, 0, 10, fill=BAR_FG, width=0)

        self.session_status = tk.Label(
            self.root,
            text="",
            font=self.small_font,
            fg="#888",
            bg=BG,
        )
        self.session_status.pack(fill=tk.X, padx=12, pady=(2, 8))

    # ---------- Вспомогательные методы ----------
    def _set_goal_dialog(self):
        today = time.strftime("%Y-%m-%d")
        current_goal = self.logic.daily_goal
        response = simpledialog.askinteger(
            "Цель на день",
            f"Установите количество точек на сегодня ({today}):",
            initialvalue=current_goal if current_goal > 0 else 100,
            minvalue=0,
            maxvalue=10000,
            parent=self.root
        )
        if response is not None:
            self.logic.set_daily_goal(response)

    def _beep(self, freq: int, duration: int):
        if not self.logic.sound_enabled:
            return
        import threading
        try:
            import winsound
            threading.Thread(target=winsound.Beep, args=(freq, duration), daemon=True).start()
        except ImportError:
            pass

    def _level_up_effect(self):
        self.flash_frames = 12
        self._beep(1200, 100)
        import threading
        threading.Timer(0.12, lambda: self._beep(1500, 120)).start()

    def _auto_save(self):
        save_progress(
            self.logic.points,
            self.logic.level,
            self.logic.sprint_duration,
            self.logic.break_duration,
            self.logic.sprint_repeats,
            self.logic.sessions,
            self.logic.session_active,
            self.logic.session_start,
            self.logic.session_points,
            self.logic.tab_times,
            self.logic.daily_goal,
            self.logic.goal_start_date,
            self.logic.records,
        )

    def _check_goal_adjustment(self):
        new_goal = self.logic.suggest_goal_adjustment()
        if new_goal is not None:
            response = messagebox.askyesno(
                "Корректировка цели",
                f"Вы часто перевыполняете цель. Предлагаем увеличить её до {new_goal} точек. Принять?",
                parent=self.root
            )
            if response:
                self.logic.set_daily_goal(new_goal)

    # ---------- Обновление интерфейса ----------
    def refresh_all(self):
        today_points = self.logic.get_today_points()
        self.canvas.itemconfig(self.points_text, text=str(today_points))

        rank = self.logic.get_rank()
        self.rank_label.config(text=rank)

        if self.logic.session_active:
            self.start_btn.config(state=tk.DISABLED)
            self.stop_btn.config(state=tk.NORMAL)
            if self.logic.current_phase == "sprint":
                self.phase_label.config(
                    text=f"Спринт {self.logic.current_sprint_index + 1}/{self.logic.sprint_repeats}",
                    fg=ACCENT
                )
            elif self.logic.current_phase == "break":
                self.phase_label.config(
                    text=f"Перерыв {self.logic.current_sprint_index + 1}/{self.logic.sprint_repeats}",
                    fg="#ffd166"
                )
            elif self.logic.sprint_finished:
                self.phase_label.config(text="✅ Все спринты завершены!", fg=ACCENT)
            else:
                self.phase_label.config(text="Сессия: идёт", fg=ACCENT)
        else:
            self.start_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.DISABLED)
            self.phase_label.config(text="Сессия: не начата", fg="#888")

        display = self.logic.current_tab if len(self.logic.current_tab) <= 48 else self.logic.current_tab[:45] + "..."
        self.tab_label.config(text=f"Вкладка: {display}")

        phase, remaining, progress = self.logic._update_phase_progress()
        bar_w = WINDOW_W - 24
        if phase == "sprint":
            self.bar_bg.coords(self.bar_fill, 0, 0, int(bar_w * progress), 10)
            mins, secs = divmod(int(remaining), 60)
            self.session_status.config(
                text=f"⏱ Спринт: {mins:02d}:{secs:02d}  |  Точки в спринте: {self.logic.session_points}"
            )
        elif phase == "break":
            self.bar_bg.coords(self.bar_fill, 0, 0, int(bar_w * progress), 10)
            mins, secs = divmod(int(remaining), 60)
            self.session_status.config(
                text=f"⏱ Перерыв: {mins:02d}:{secs:02d}  |  Следующий спринт через {mins} мин"
            )
        else:
            self.bar_bg.coords(self.bar_fill, 0, 0, 0, 10)
            if not self.logic.session_active:
                self.session_status.config(text="")

        # Обновление скорости
        self._update_speed_label()
        self._update_goal_bar()

        # ETA
        eta_hours = self.logic.get_goal_eta()
        if eta_hours is not None and eta_hours >= 0:
            if eta_hours == 0:
                eta_text = "Цель достигнута! 🎉"
            else:
                hours = int(eta_hours)
                minutes = int((eta_hours - hours) * 60)
                eta_text = f"Прогноз: ~{hours} ч {minutes} мин"
        else:
            eta_text = ""
        self.eta_label.config(text=eta_text)


        # Заработок
        today_earn = self.logic.get_today_earnings()
        total_earn = self.logic.get_total_earnings()
        self.earnings_label.config(
            text=f"💰 Сегодня: {today_earn:.2f} руб. | Всего: {total_earn:.2f} руб."
        )

    def _update_speed_label(self):
        """Обновление скорости."""
        if self.logic.session_active and self.logic.session_points > 0:
            prod_time = self.logic.get_current_productive_seconds()
            speed = calc_points_per_hour(self.logic.session_points, prod_time)
            if speed is not None:
                self.speed_label.config(text=f"Скорость: {speed:.1f} точ/ч", fg=ACCENT)
            else:
                self.speed_label.config(text="Скорость: —", fg="#888")
        else:
            total_points = self.logic.points
            total_prod = 0.0
            for s in self.logic.sessions:
                total_prod += get_productive_tab_time(s.tab_times)
            speed = calc_points_per_hour(total_points, total_prod)
            if speed is not None:
                self.speed_label.config(text=f"Средняя скорость: {speed:.1f} точ/ч", fg="#888")
            else:
                self.speed_label.config(text="Скорость: —", fg="#888")

    def _update_goal_bar(self):
        goal = self.logic.daily_goal
        today_points = self.logic.get_today_points()
        progress = self.logic.get_goal_progress()
        bar_w = WINDOW_W - 24
        self.goal_bar_bg.coords(self.goal_bar_fill, 0, 0, int(bar_w * progress), 8)
        if goal > 0:
            self.goal_label.config(
                text=f"Цель на день: {today_points} / {goal} точек  (выполнено {int(progress*100)}%)",
                fg=ACCENT if progress >= 1.0 else "#888"
            )
        else:
            self.goal_label.config(text="Цель не установлена", fg="#888")

    # ---------- Главный цикл анимации ----------
    def _tick(self):
        today_points = self.logic.get_today_points()

        if self.points_scale > 1.0:
            self.points_scale = max(1.0, self.points_scale - 0.035)
        size = int(38 * self.points_scale)
        anim_font = tkfont.Font(family="Segoe UI", size=size, weight="bold")
        self.canvas.itemconfig(self.points_text, text=str(today_points), font=anim_font)

        bg = BG_FLASH if self.flash_frames > 0 else BG
        if self.flash_frames > 0:
            self.flash_frames -= 1
        for widget in (
            self.root,
            self.canvas,
            self.rank_label,
            self.tab_label,
            self.phase_label,
            self.speed_label,
            self.earnings_label,
            self.goal_label,
            self.goal_bar_bg,
            self.eta_label,
            self.session_status,
            self.stats_btn,
            self.settings_btn,
            self.charts_btn,
            self.records_btn,
            self.floating_btn,
        ):
            try:
                widget.configure(bg=bg)
            except tk.TclError:
                pass
        self.canvas.configure(bg=bg)

        self.canvas.delete("particle")
        alive = []
        for p in self.particles:
            if p.update():
                alive.append(p)
                alpha = p.life / p.max_life
                r = int(p.size * (0.5 + alpha * 0.5))
                self.canvas.create_oval(
                    p.x - r, p.y - r, p.x + r, p.y + r,
                    fill=p.color, outline="", tags="particle",
                )
        self.particles = alive

        self.logic.tick()

        now = time.time()
        if now - self.logic.last_auto_save >= self.logic.auto_save_interval:
            self._auto_save()
            self.logic.last_auto_save = now

        if today_points != self._last_today_points:
            cx = (WINDOW_W - 24) // 2
            cy = 45
            for _ in range(8):
                self.particles.append(Particle(cx + random.uniform(-20, 20), cy))
            self._last_today_points = today_points
            self.points_scale = 1.35

        self.root.after(16, self._tick)

    # ---------- Плавающий виджет ----------
    def toggle_floating(self):
        if self.floating_widget and self.floating_widget.window.winfo_exists():
            self.floating_widget.close()
            self.floating_widget = None
        else:
            self.floating_widget = FloatingWidget(self.logic, self.logic.point_price)

    # ---------- Графики ----------
    def show_charts(self):
        ChartsWindow(
            self.root,
            self.logic.sessions,
            self.logic.points,
            self.logic.get_today_points(),
            self.logic.get_productivity_by_hour(),
            self.logic.point_price
        )

    # ---------- Рекорды ----------
    def show_records(self):
        RecordsWindow(self.root, self.logic)

    # ---------- Настройки ----------
    def show_settings(self):
        if self._settings_window and self._settings_window.window.winfo_exists():
            self._settings_window.window.lift()
            return
        self._settings_window = SettingsWindow(self.root, self.logic, self._on_settings_changed)
        self._settings_window.window.protocol("WM_DELETE_WINDOW", self._close_settings_window)

    def _close_settings_window(self):
        if self._settings_window and self._settings_window.window.winfo_exists():
            self._settings_window.window.destroy()
            self._settings_window = None

    def _on_settings_changed(self):
        self.refresh_all()

    # ---------- Статистика ----------
    def show_statistics(self):
        if self._stats_window and self._stats_window.window.winfo_exists():
            self._stats_window.window.lift()
            return
        self._stats_window = StatsWindow(self.root, self.logic)
        self._stats_window.window.protocol("WM_DELETE_WINDOW", self._close_stats_window)

    def _close_stats_window(self):
        if self._stats_window and self._stats_window.window.winfo_exists():
            self._stats_window.close()
            self._stats_window = None

    # ---------- Закрытие ----------
    def on_close(self):
        self.logic.close()
        if self.floating_widget and self.floating_widget.window.winfo_exists():
            self.floating_widget.close()
        if self._stats_window and self._stats_window.window.winfo_exists():
            self._stats_window.close()
        if self._settings_window and self._settings_window.window.winfo_exists():
            self._settings_window.window.destroy()
        self.root.destroy()

    def run(self):
        self.root.mainloop()