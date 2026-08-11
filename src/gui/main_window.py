"""
Главное окно приложения с улучшенным интерфейсом.
"""
import tkinter as tk
from tkinter import font as tkfont, ttk, messagebox, simpledialog
import time
import random
import math
from typing import Optional, List

from src.core.logic import TrackerLogic
from src.core.models import Session, Particle
from src.core.storage import save_progress
from src.utils.config import (
    WINDOW_W, WINDOW_H, BG, BG_CARD, FG, FG_SECONDARY, ACCENT, ACCENT_DARK,
    LEVEL_COLOR, COMBO_COLOR, BAR_BG, BAR_FG, GOAL_BAR_FG,
    BTN_BG, BTN_ACTIVE, BTN_STOP, BTN_HOVER, BG_FLASH,
    SPRINT_DURATIONS, BREAK_DURATIONS, REPEAT_OPTIONS,
)
from src.utils.helpers import (
    format_duration, format_datetime, format_points_per_hour,
    is_productive_tab, get_productive_tab_time,
    calc_points_per_hour, calc_level,
)
from src.gui.charts import ChartsWindow
from src.gui.stats_window import StatsWindow
from src.gui.finance_window import FinanceWindow
from src.gui.forecast_window import ForecastWindow
from src.gui.floating import FloatingWidget
from src.gui.settings_window import SettingsWindow
from src.gui.manage_goals_window import ManageGoalsWindow



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
        self._last_today_points = 0
        self._stats_window: Optional[StatsWindow] = None
        self._settings_window: Optional[SettingsWindow] = None
        self.floating_widget = None

        self._build_ui()
        self.logic.register_hotkey()
        self._tick()
        self._check_goal_adjustment()

    # ============================================================
    #  1. ПОСТРОЕНИЕ ИНТЕРФЕЙСА
    # ============================================================
    def _build_ui(self):
        self._init_fonts()
        self._build_header()
        self._build_counter()
        self._build_stats_cards()
        self._build_goal_section()
        self._build_session_controls()
        self._build_sprint_bar()

    def _init_fonts(self):
        self.big_font = tkfont.Font(family="Segoe UI", size=42, weight="bold")
        self.mid_font = tkfont.Font(family="Segoe UI", size=12, weight="bold")
        self.small_font = tkfont.Font(family="Segoe UI", size=9)
        self.btn_font = tkfont.Font(family="Segoe UI", size=9, weight="bold")
        self.tiny_font = tkfont.Font(family="Segoe UI", size=8)

    # ---------- Шапка ----------
    def _build_header(self):
        header = tk.Frame(self.root, bg=BG)
        header.pack(fill=tk.X, padx=12, pady=(8, 4))

        # Ранг
        self.rank_label = tk.Label(
            header,
            text="🌱 Стажёр",
            font=self.mid_font,
            fg=LEVEL_COLOR,
            bg=BG
        )
        self.rank_label.pack(side=tk.LEFT)

        # Кнопки
        btn_frame = tk.Frame(header, bg=BG)
        btn_frame.pack(side=tk.RIGHT)

        buttons = [
            ("⚙️", self.show_settings),
            ("📊", self.show_statistics),
            ("📈", self.show_charts),
            ("🖥", self.toggle_floating),
            ("💰", self.show_finance),
            ("📋", self.show_forecast),
        ]
        for text, cmd in buttons:
            btn = tk.Button(
                btn_frame,
                text=text,
                font=self.btn_font,
                bg=BG,
                fg=FG_SECONDARY,
                activebackground=BTN_HOVER,
                activeforeground=ACCENT,
                relief=tk.FLAT,
                bd=0,
                padx=4,
                pady=2,
                cursor="hand2",
                command=cmd,
            )
            btn.pack(side=tk.LEFT, padx=(0, 2))

    # ---------- Счётчик ----------
    def _build_counter(self):
        self.canvas = tk.Canvas(
            self.root,
            width=WINDOW_W - 24,
            height=100,
            bg=BG,
            highlightthickness=0,
        )
        self.canvas.pack(padx=12, pady=(0, 4))

        # Тень под числом — убираем или делаем обычным цветом
        self.canvas.create_text(
            (WINDOW_W - 24) // 2 + 1, 51,
            text="0",
            fill="#2a2a4a",  # просто тёмный цвет вместо прозрачного
            font=self.big_font,
        )
        self.points_text = self.canvas.create_text(
            (WINDOW_W - 24) // 2, 50,
            text="0",
            fill=FG,
            font=self.big_font,
        )

        # Подпись "ТОЧЕК СЕГОДНЯ"
        self.canvas.create_text(
            (WINDOW_W - 24) // 2, 90,
            text="ТОЧЕК СЕГОДНЯ",
            fill=FG_SECONDARY,
            font=self.tiny_font,
        )

    # ---------- Карточки статистики ----------
    def _build_stats_cards(self):
        cards_frame = tk.Frame(self.root, bg=BG)
        cards_frame.pack(fill=tk.X, padx=12, pady=(0, 6))

        # 3 карточки в ряд
        self.speed_card = self._create_stat_card(cards_frame, "⚡", "Скорость", "—")
        self.earnings_card = self._create_stat_card(cards_frame, "💰", "Заработок", "0.00 ₽")
        self.goal_card = self._create_stat_card(cards_frame, "🎯", "Прогноз", "—")

    def _create_stat_card(self, parent, icon, label, value_text):
        card = tk.Frame(
            parent,
            bg=BG_CARD,
            relief=tk.FLAT,
            bd=0,
            padx=8,
            pady=4,
        )
        card.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)

        # Иконка и заголовок
        header = tk.Frame(card, bg=BG_CARD)
        header.pack(fill=tk.X)

        tk.Label(
            header,
            text=icon,
            font=self.small_font,
            fg=ACCENT,
            bg=BG_CARD,
        ).pack(side=tk.LEFT)

        tk.Label(
            header,
            text=label,
            font=self.tiny_font,
            fg=FG_SECONDARY,
            bg=BG_CARD,
        ).pack(side=tk.LEFT, padx=(2, 0))

        # Значение
        value = tk.Label(
            card,
            text=value_text,
            font=self.small_font,
            fg=FG,
            bg=BG_CARD,
            anchor=tk.W,
        )
        value.pack(fill=tk.X, pady=(0, 2))

        # Сохраняем ссылки
        return {"frame": card, "value": value}

    # ---------- Секция целей ----------
    def _build_goal_section(self):
        # Дневная цель
        daily_frame = tk.Frame(self.root, bg=BG)
        daily_frame.pack(fill=tk.X, padx=12, pady=(0, 4))

        self.goal_label = tk.Label(
            daily_frame,
            text="🎯 Цель на день: 0 / 0",
            font=self.small_font,
            fg=FG_SECONDARY,
            bg=BG,
            anchor=tk.W,
        )
        self.goal_label.pack(fill=tk.X)

        self.goal_bar_bg, self.goal_bar_fill = self._create_progress_bar(GOAL_BAR_FG)

        # Общая цель
        total_frame = tk.Frame(self.root, bg=BG)
        total_frame.pack(fill=tk.X, padx=12, pady=(0, 4))

        self.total_goal_label = tk.Label(
            total_frame,
            text="🏆 Общая цель: 0 / 0",
            font=self.small_font,
            fg=FG_SECONDARY,
            bg=BG,
            anchor=tk.W,
        )
        self.total_goal_label.pack(fill=tk.X)

        self.total_goal_bar_bg, self.total_goal_bar_fill = self._create_progress_bar("#a29bfe")

        # Активная цель (прогноз)
        active_frame = tk.Frame(self.root, bg=BG)
        active_frame.pack(fill=tk.X, padx=12, pady=(0, 4))

        self.goal_title_label = tk.Label(
            active_frame,
            text="📋 Активная цель: не выбрана",
            font=self.small_font,
            fg=ACCENT,
            bg=BG,
            anchor=tk.W,
        )
        self.goal_title_label.pack(fill=tk.X)

        self.goal_progress_label = tk.Label(
            active_frame,
            text="",
            font=self.tiny_font,
            fg=FG_SECONDARY,
            bg=BG,
            anchor=tk.W,
        )
        self.goal_progress_label.pack(fill=tk.X)

        self.goal_bar_bg_act, self.goal_bar_fill_act = self._create_progress_bar(ACCENT)

        # Кнопки управления целями
        btn_frame = tk.Frame(self.root, bg=BG)
        btn_frame.pack(fill=tk.X, padx=12, pady=(0, 4))

        for text, cmd in [
            ("🎯 Установить цель на день", self._set_goal_dialog),
            ("🏆 Общая цель", self._set_total_goal_dialog),
            ("📋 Управление целями", self._manage_goals),
        ]:
            btn = tk.Button(
                btn_frame,
                text=text,
                font=self.tiny_font,
                bg=BG_CARD,
                fg=FG,
                activebackground=BTN_HOVER,
                activeforeground=ACCENT,
                relief=tk.FLAT,
                bd=0,
                padx=6,
                pady=2,
                cursor="hand2",
                command=cmd,
            )
            btn.pack(side=tk.LEFT, padx=(0, 4))

    def _create_progress_bar(self, color):
        canvas = tk.Canvas(
            self.root,
            width=WINDOW_W - 24,
            height=6,
            bg=BAR_BG,
            highlightthickness=0,
            bd=0,
        )
        canvas.pack(padx=12, pady=(2, 2))
        fill = canvas.create_rectangle(0, 0, 0, 6, fill=color, width=0)
        return canvas, fill

    # ---------- Управление сессией ----------
    def _build_session_controls(self):
        frame = tk.Frame(self.root, bg=BG)
        frame.pack(fill=tk.X, padx=12, pady=(4, 0))

        # Статус фазы
        self.phase_label = tk.Label(
            frame,
            text="Сессия: не начата",
            font=self.small_font,
            fg=FG_SECONDARY,
            bg=BG,
            anchor=tk.W,
        )
        self.phase_label.pack(fill=tk.X)

        # Кнопки
        btn_frame = tk.Frame(self.root, bg=BG)
        btn_frame.pack(fill=tk.X, padx=12, pady=(4, 0))

        self.start_btn = tk.Button(
            btn_frame,
            text="▶ Старт",
            font=self.btn_font,
            bg=BTN_ACTIVE,
            fg=BG,
            activebackground=ACCENT_DARK,
            relief=tk.FLAT,
            bd=0,
            padx=16,
            pady=6,
            cursor="hand2",
            command=self.logic.start_session,
        )
        self.start_btn.pack(side=tk.LEFT, padx=(0, 6))

        self.stop_btn = tk.Button(
            btn_frame,
            text="■ Стоп",
            font=self.btn_font,
            bg=BTN_STOP,
            fg=FG,
            activebackground="#e05555",
            relief=tk.FLAT,
            bd=0,
            padx=16,
            pady=6,
            cursor="hand2",
            command=self.logic.stop_session,
            state=tk.DISABLED,
        )
        self.stop_btn.pack(side=tk.LEFT)

        # Информация о вкладке
        self.tab_label = tk.Label(
            self.root,
            text="Вкладка: —",
            font=self.tiny_font,
            fg=FG_SECONDARY,
            bg=BG,
            anchor=tk.W,
        )
        self.tab_label.pack(fill=tk.X, padx=12, pady=(4, 0))

    # ---------- Прогресс-бар спринта ----------
    def _build_sprint_bar(self):
        self.sprint_bar_bg = tk.Canvas(
            self.root,
            width=WINDOW_W - 24,
            height=10,
            bg=BAR_BG,
            highlightthickness=0,
        )
        self.sprint_bar_bg.pack(padx=12, pady=(4, 2))
        self.sprint_bar_fill = self.sprint_bar_bg.create_rectangle(
            0, 0, 0, 10, fill=BAR_FG, width=0
        )

        self.session_status = tk.Label(
            self.root,
            text="",
            font=self.tiny_font,
            fg=FG_SECONDARY,
            bg=BG,
        )
        self.session_status.pack(fill=tk.X, padx=12, pady=(0, 6))

    # ============================================================
    #  2. ДИАЛОГИ
    # ============================================================
    def _set_goal_dialog(self):
        today = time.strftime("%Y-%m-%d")
        current = self.logic.daily_goal
        response = simpledialog.askinteger(
            "Цель на день",
            f"Установите количество точек на сегодня ({today}):",
            initialvalue=current if current > 0 else 100,
            minvalue=0,
            maxvalue=10000,
            parent=self.root,
        )
        if response is not None:
            self.logic.set_daily_goal(response)

    def _set_total_goal_dialog(self):
        current = self.logic.total_goal
        response = simpledialog.askinteger(
            "Общая цель",
            "Установите общую цель (накопленные точки за всё время):",
            initialvalue=current if current > 0 else 10000,
            minvalue=0,
            maxvalue=1000000,
            parent=self.root,
        )
        if response is not None:
            self.logic.set_total_goal(response)

    def _manage_goals(self):
        ManageGoalsWindow(self.root, self.logic)

    def _check_goal_adjustment(self):
        new_goal = self.logic.suggest_goal_adjustment()
        if new_goal is not None:
            response = messagebox.askyesno(
                "Корректировка цели",
                f"Вы часто перевыполняете цель. Предлагаем увеличить её до {new_goal} точек. Принять?",
                parent=self.root,
            )
            if response:
                self.logic.set_daily_goal(new_goal)

    # ============================================================
    #  3. ОТКРЫТИЕ ОКОН
    # ============================================================
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

    def show_charts(self):
        ChartsWindow(self.root, self.logic.sessions, self.logic)

    def toggle_floating(self):
        if self.floating_widget and self.floating_widget.window.winfo_exists():
            self.floating_widget.close()
            self.floating_widget = None
        else:
            self.floating_widget = FloatingWidget(self.logic, self.logic.point_price)

    def show_finance(self):
        FinanceWindow(self.root, self.logic)

    def show_forecast(self):
        ForecastWindow(self.root, self.logic)

    # ============================================================
    #  4. ЗВУКИ
    # ============================================================
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

    # ============================================================
    #  5. ОБНОВЛЕНИЕ
    # ============================================================
    def refresh_all(self):
        self._update_counter()
        self._update_rank()
        self._update_session_buttons()
        self._update_phase_label()
        self._update_tab_label()
        self._update_sprint_bar()
        self._update_stats_cards()
        self._update_goal_bar()
        self._update_total_goal_bar()
        self._update_active_goal()

    def _update_counter(self):
        today_points = self.logic.get_today_points()
        self.canvas.itemconfig(self.points_text, text=str(today_points))

    def _update_rank(self):
        self.rank_label.config(text=self.logic.get_rank())

    def _update_session_buttons(self):
        if self.logic.session_active:
            self.start_btn.config(state=tk.DISABLED)
            self.stop_btn.config(state=tk.NORMAL)
        else:
            self.start_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.DISABLED)

    def _update_phase_label(self):
        if self.logic.session_active:
            if self.logic.current_phase == "sprint":
                self.phase_label.config(
                    text=f"⏱ Спринт {self.logic.current_sprint_index + 1}/{self.logic.sprint_repeats}",
                    fg=ACCENT,
                )
            elif self.logic.current_phase == "break":
                self.phase_label.config(
                    text=f"☕ Перерыв {self.logic.current_sprint_index + 1}/{self.logic.sprint_repeats}",
                    fg=COMBO_COLOR,
                )
            elif self.logic.sprint_finished:
                self.phase_label.config(text="✅ Все спринты завершены!", fg=ACCENT)
            else:
                self.phase_label.config(text="Сессия: идёт", fg=ACCENT)
        else:
            self.phase_label.config(text="⏸ Сессия: не начата", fg=FG_SECONDARY)

    def _update_tab_label(self):
        display = self.logic.current_tab if len(self.logic.current_tab) <= 48 else self.logic.current_tab[:45] + "..."
        self.tab_label.config(text=f"📂 {display}")

    def _update_sprint_bar(self):
        phase, remaining, progress = self.logic._update_phase_progress()
        bar_w = WINDOW_W - 24
        self.sprint_bar_bg.coords(self.sprint_bar_fill, 0, 0, int(bar_w * progress), 10)

        if phase == "sprint":
            mins, secs = divmod(int(remaining), 60)
            self.session_status.config(
                text=f"⏱ {mins:02d}:{secs:02d}  |  Точки в спринте: {self.logic.session_points}"
            )
        elif phase == "break":
            mins, secs = divmod(int(remaining), 60)
            self.session_status.config(text=f"☕ {mins:02d}:{secs:02d}  |  Следующий спринт через {mins} мин")
        else:
            self.sprint_bar_bg.coords(self.sprint_bar_fill, 0, 0, 0, 10)
            self.session_status.config(text="")

    def _update_stats_cards(self):
        # Скорость
        if self.logic.session_active and self.logic.session_points > 0:
            prod_time = self.logic.get_current_productive_seconds()
            speed = calc_points_per_hour(self.logic.session_points, prod_time)
            if speed is not None:
                self.speed_card["value"].config(text=f"{speed:.0f} точ/ч", fg=ACCENT)
            else:
                self.speed_card["value"].config(text="—", fg=FG_SECONDARY)
        else:
            total_points = self.logic.points
            total_prod = 0.0
            for s in self.logic.sessions:
                total_prod += get_productive_tab_time(s.tab_times)
            speed = calc_points_per_hour(total_points, total_prod)
            if speed is not None:
                self.speed_card["value"].config(text=f"{speed:.0f} точ/ч (ср.)", fg=FG_SECONDARY)
            else:
                self.speed_card["value"].config(text="—", fg=FG_SECONDARY)

        # Заработок
        today_earn = self.logic.get_today_earnings()
        total_earn = self.logic.get_total_earnings()
        self.earnings_card["value"].config(text=f"{today_earn:.0f} ₽ / {total_earn:.0f} ₽", fg="#ffd700")

        # Прогноз ETA
        eta_hours = self.logic.get_goal_eta()
        if eta_hours is not None and eta_hours >= 0:
            if eta_hours == 0:
                eta_text = "🎉 Цель достигнута!"
            else:
                hours = int(eta_hours)
                minutes = int((eta_hours - hours) * 60)
                eta_text = f"~{hours}ч {minutes}м"
        else:
            eta_text = "—"
        self.goal_card["value"].config(text=eta_text, fg=ACCENT if eta_text != "—" else FG_SECONDARY)

    def _update_goal_bar(self):
        goal = self.logic.daily_goal
        today_points = self.logic.get_today_points()
        progress = self.logic.get_daily_goal_progress()
        bar_w = WINDOW_W - 24
        self.goal_bar_bg.coords(self.goal_bar_fill, 0, 0, int(bar_w * progress), 6)

        if goal > 0:
            time_remaining = self.logic.get_goal_eta()
            time_text = ""
            if time_remaining is not None and time_remaining > 0:
                hours = int(time_remaining)
                minutes = int((time_remaining - hours) * 60)
                time_text = f" ({hours}ч {minutes}м)" if hours > 0 else f" ({minutes}м)"
            elif time_remaining == 0:
                time_text = " ✅"

            self.goal_label.config(
                text=f"🎯 {today_points} / {goal}  ({int(progress*100)}%){time_text}",
                fg=ACCENT if progress >= 1.0 else FG,
            )
        else:
            self.goal_label.config(text="🎯 Цель не установлена", fg=FG_SECONDARY)

    def _update_total_goal_bar(self):
        total_goal = self.logic.total_goal
        total_points = self.logic.points
        progress = self.logic.get_total_goal_progress()
        bar_w = WINDOW_W - 24
        self.total_goal_bar_bg.coords(self.total_goal_bar_fill, 0, 0, int(bar_w * progress), 6)

        if total_goal > 0:
            remaining = self.logic.get_total_goal_remaining()
            self.total_goal_label.config(
                text=f"🏆 {total_points} / {total_goal}  ({int(progress*100)}%)  •  осталось {remaining}",
                fg="#a29bfe" if progress >= 1.0 else FG,
            )
        else:
            self.total_goal_label.config(text="🏆 Общая цель не установлена", fg=FG_SECONDARY)

    def _update_active_goal(self):
        active_goal = self.logic.get_active_goal()
        bar_w = WINDOW_W - 24

        if active_goal:
            progress_data = self.logic.get_goal_progress(active_goal)
            self.goal_bar_bg_act.coords(
                self.goal_bar_fill_act,
                0,
                0,
                int(bar_w * progress_data['progress']),
                6,
            )

            name = active_goal.get('name', 'Цель')
            remaining = progress_data['remaining']
            total = active_goal['target_amount']
            points_per_day = progress_data['needed_points_per_day']

            self.goal_title_label.config(
                text=f"📋 {name}",
                fg=ACCENT if progress_data['progress'] >= 1.0 else FG,
            )
            if progress_data['progress'] >= 1.0:
                self.goal_progress_label.config(text="✅ Цель достигнута!", fg=ACCENT)
            else:
                self.goal_progress_label.config(
                    text=f"Осталось {remaining:.0f} ₽  •  {points_per_day:.0f} точек/день",
                    fg=FG_SECONDARY,
                )
        else:
            self.goal_bar_bg_act.coords(self.goal_bar_fill_act, 0, 0, 0, 6)
            self.goal_title_label.config(text="📋 Активная цель не выбрана", fg=FG_SECONDARY)
            self.goal_progress_label.config(text="Создайте цель в окне прогнозов (📋)", fg=FG_SECONDARY)

    # ============================================================
    #  6. АНИМАЦИЯ
    # ============================================================
    def _tick(self):
        today_points = self.logic.get_today_points()

        if self.points_scale > 1.0:
            self.points_scale = max(1.0, self.points_scale - 0.035)
        size = int(42 * self.points_scale)
        anim_font = tkfont.Font(family="Segoe UI", size=size, weight="bold")
        self.canvas.itemconfig(self.points_text, font=anim_font)

        bg = BG_FLASH if self.flash_frames > 0 else BG
        if self.flash_frames > 0:
            self.flash_frames -= 1
        self._update_widgets_background(bg)

        self._update_particles()

        self.logic.tick()

        now = time.time()
        if now - self.logic.last_auto_save >= self.logic.auto_save_interval:
            self._auto_save()
            self.logic.last_auto_save = now

        if today_points != self._last_today_points:
            cx = (WINDOW_W - 24) // 2
            cy = 50
            for _ in range(6):
                self.particles.append(Particle(cx + random.uniform(-20, 20), cy))
            self._last_today_points = today_points
            self.points_scale = 1.35

        self.root.after(16, self._tick)

    def _update_particles(self):
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

    def _update_widgets_background(self, bg):
        for widget in (
            self.root,
            self.canvas,
            self.rank_label,
            self.tab_label,
            self.phase_label,
            self.goal_label,
            self.goal_bar_bg,
            self.total_goal_label,
            self.total_goal_bar_bg,
            self.goal_title_label,
            self.goal_progress_label,
            self.goal_bar_bg_act,
            self.session_status,
            self.sprint_bar_bg,
        ):
            try:
                widget.configure(bg=bg)
            except tk.TclError:
                pass
        for card in (self.speed_card, self.earnings_card, self.goal_card):
            try:
                card["frame"].configure(bg=bg)
                for child in card["frame"].winfo_children():
                    child.configure(bg=bg)
            except:
                pass

    # ============================================================
    #  7. СОХРАНЕНИЕ И ЗАКРЫТИЕ
    # ============================================================
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
            self.logic.current_phase,
            self.logic.current_sprint_index,
            self.logic.sprint_finished,
            self.logic.current_phase_start,
            self.logic.current_tab,
            self.logic._last_tab_poll,
            self.logic._recording,
            self.logic.total_goal,
            self.logic.total_goal_achieved_notified,
            self.logic.real_earnings,
            self.logic.goals,
            self.logic.active_goal_id,
        )

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