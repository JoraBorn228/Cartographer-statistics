"""
Главное окно приложения с улучшенным интерфейсом.
"""
import tkinter as tk
from tkinter import font as tkfont, ttk, messagebox, simpledialog
import time
import random
import math
import calendar
from typing import Optional, List

from src.core.logic import TrackerLogic
from src.core.models import Session, Particle
from src.core.storage import save_logic_progress
from src.utils.config import (
    WINDOW_W, WINDOW_H, BG, BG_CARD, FG, FG_SECONDARY, ACCENT, ACCENT_DARK,
    LEVEL_COLOR, COMBO_COLOR, BAR_BG, BAR_FG, BAR_FG_BREAK, GOAL_BAR_FG,
    BTN_BG, BTN_ACTIVE, BTN_STOP, BTN_HOVER, BG_FLASH,
    SPRINT_DURATIONS, BREAK_DURATIONS, REPEAT_OPTIONS,
    SPEED_CHART_LINE, SPEED_CHART_FILL, SPEED_CHART_DOT,
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
        self._build_speed_chart()

    def _init_fonts(self):
        self.big_font = tkfont.Font(family="Segoe UI", size=44, weight="bold")
        self.mid_font = tkfont.Font(family="Segoe UI", size=12, weight="bold")
        self.small_font = tkfont.Font(family="Segoe UI", size=9)
        self.card_value_font = tkfont.Font(family="Segoe UI", size=11, weight="bold")
        self.btn_font = tkfont.Font(family="Segoe UI", size=10, weight="bold")
        self.icon_btn_font = tkfont.Font(family="Segoe UI", size=11)
        self.tiny_font = tkfont.Font(family="Segoe UI", size=8)

    # ---------- Шапка ----------
    def _build_header(self):
        header = tk.Frame(self.root, bg=BG)
        header.pack(fill=tk.X, padx=14, pady=(10, 4))

        # Левая часть: ранг + время сессии
        left = tk.Frame(header, bg=BG)
        left.pack(side=tk.LEFT)

        self.rank_label = tk.Label(
            left,
            text="🌱 Стажёр",
            font=self.mid_font,
            fg=LEVEL_COLOR,
            bg=BG,
        )
        self.rank_label.pack(side=tk.LEFT)

        self.session_time_label = tk.Label(
            left,
            text="",
            font=self.tiny_font,
            fg=FG_SECONDARY,
            bg=BG,
        )
        self.session_time_label.pack(side=tk.LEFT, padx=(10, 0))

        # Кнопки справа
        btn_frame = tk.Frame(header, bg=BG)
        btn_frame.pack(side=tk.RIGHT)

        buttons = [
            ("⚙️", self.show_settings, "Настройки"),
            ("📊", self.show_statistics, "Статистика"),
            ("📈", self.show_charts, "Графики"),
            ("🖥", self.toggle_floating, "Виджет"),
            ("💰", self.show_finance, "Финансы"),
            ("📋", self.show_forecast, "Прогнозы"),
        ]
        for text, cmd, _ in buttons:
            btn = tk.Button(
                btn_frame,
                text=text,
                font=self.icon_btn_font,
                bg=BG_CARD,
                fg=FG_SECONDARY,
                activebackground=BTN_HOVER,
                activeforeground=ACCENT,
                relief=tk.FLAT,
                bd=0,
                padx=7,
                pady=4,
                cursor="hand2",
                command=cmd,
            )
            btn.pack(side=tk.LEFT, padx=2)
            self._add_hover(btn, BG_CARD, BTN_HOVER, FG_SECONDARY, ACCENT)

    @staticmethod
    def _add_hover(widget, normal_bg, hover_bg, normal_fg=None, hover_fg=None):
        """Добавить hover-эффект кнопке."""
        def on_enter(_):
            widget.configure(bg=hover_bg)
            if hover_fg:
                widget.configure(fg=hover_fg)

        def on_leave(_):
            widget.configure(bg=normal_bg)
            if normal_fg:
                widget.configure(fg=normal_fg)

        widget.bind("<Enter>", on_enter)
        widget.bind("<Leave>", on_leave)

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
        self.earnings_card = self._create_earnings_card(cards_frame)
        self.goal_card = self._create_stat_card(cards_frame, "🎯", "Прогноз", "—")

    def _create_earnings_card(self, parent):
        """Карточка заработка с переключателем периодов."""
        card = tk.Frame(
            parent,
            bg=BG_CARD,
            highlightbackground="#2a2a5e",
            highlightthickness=1,
            bd=0,
            padx=10,
            pady=6,
        )
        card.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)

        # Верхняя строка: иконка + заголовок + переключатель
        header = tk.Frame(card, bg=BG_CARD)
        header.pack(fill=tk.X)

        tk.Label(
            header,
            text="💰",
            font=self.small_font,
            fg=ACCENT,
            bg=BG_CARD,
        ).pack(side=tk.LEFT)

        tk.Label(
            header,
            text="Заработок",
            font=self.tiny_font,
            fg=FG_SECONDARY,
            bg=BG_CARD,
        ).pack(side=tk.LEFT, padx=(3, 0))

        # Переключатель периодов
        self.earnings_period_var = tk.StringVar(value="day")  # "day" / "period" / "all"
        self.earnings_toggle = tk.Button(
            header,
            text="День",
            font=self.tiny_font,
            fg=ACCENT,
            bg=BAR_BG,
            relief=tk.FLAT,
            bd=0,
            padx=4,
            pady=1,
            cursor="hand2",
            command=self._cycle_earnings_period,
        )
        self.earnings_toggle.pack(side=tk.RIGHT)

        # Даты периода
        self.earnings_dates_label = tk.Label(
            header,
            text="",
            font=self.tiny_font,
            fg="#888",
            bg=BG_CARD,
        )
        self.earnings_dates_label.pack(side=tk.RIGHT, padx=(4, 0))

        # Нижняя строка: два значения
        values_frame = tk.Frame(card, bg=BG_CARD)
        values_frame.pack(fill=tk.X, pady=(2, 0))

        # Слева - за день
        self.earnings_day = tk.Label(
            values_frame,
            text="—",
            font=self.card_value_font,
            fg="#ffd700",
            bg=BG_CARD,
            anchor=tk.W,
        )
        self.earnings_day.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Разделитель
        tk.Label(
            values_frame,
            text="|",
            font=self.card_value_font,
            fg="#444",
            bg=BG_CARD,
        ).pack(side=tk.LEFT, padx=4)

        # Справа - за период или всё время
        self.earnings_period = tk.Label(
            values_frame,
            text="—",
            font=self.card_value_font,
            fg="#ffd700",
            bg=BG_CARD,
            anchor=tk.W,
        )
        self.earnings_period.pack(side=tk.RIGHT, fill=tk.X, expand=True)

        return {"frame": card, "value": values_frame}

    def _cycle_earnings_period(self):
        """Переключить период: день → период → всё время."""
        order = ["day", "period", "all"]
        current = order.index(self.earnings_period_var.get())
        next_val = order[(current + 1) % len(order)]
        self.earnings_period_var.set(next_val)

        labels = {"day": "День", "period": "Период", "all": "Всё время"}
        self.earnings_toggle.config(text=labels[next_val])

    def _create_stat_card(self, parent, icon, label, value_text, accent_color=None):
        color = accent_color or ACCENT
        wrapper = tk.Frame(parent, bg=BG, padx=0, pady=0)
        wrapper.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)

        # Цветная левая полоска
        bar = tk.Frame(wrapper, bg=color, width=3)
        bar.pack(side=tk.LEFT, fill=tk.Y)

        card = tk.Frame(
            wrapper,
            bg=BG_CARD,
            highlightbackground="#1e1e4a",
            highlightthickness=1,
            bd=0,
            padx=10,
            pady=7,
        )
        card.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # hover-эффект на карточке
        self._add_hover(card, BG_CARD, "#1c1c3e")

        hdr = tk.Frame(card, bg=BG_CARD)
        hdr.pack(fill=tk.X)

        icon_lbl = tk.Label(hdr, text=icon, font=self.small_font, fg=color, bg=BG_CARD)
        icon_lbl.pack(side=tk.LEFT)

        tk.Label(
            hdr,
            text=label,
            font=self.tiny_font,
            fg=FG_SECONDARY,
            bg=BG_CARD,
        ).pack(side=tk.LEFT, padx=(4, 0))

        value = tk.Label(
            card,
            text=value_text,
            font=self.card_value_font,
            fg=FG,
            bg=BG_CARD,
            anchor=tk.W,
        )
        value.pack(fill=tk.X, pady=(3, 0))

        return {"frame": card, "wrapper": wrapper, "value": value, "bar": bar}

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
                padx=8,
                pady=3,
                cursor="hand2",
                command=cmd,
            )
            btn.pack(side=tk.LEFT, padx=(0, 4))
            self._add_hover(btn, BG_CARD, BTN_HOVER)

    def _create_progress_bar(self, color):
        canvas = tk.Canvas(
            self.root,
            width=WINDOW_W - 24,
            height=8,
            bg=BAR_BG,
            highlightthickness=0,
            bd=0,
        )
        canvas.pack(padx=12, pady=(2, 2))
        fill = canvas.create_rectangle(0, 0, 0, 8, fill=color, width=0)
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
            activeforeground=BG,
            relief=tk.FLAT,
            bd=0,
            padx=20,
            pady=7,
            cursor="hand2",
            command=self.logic.start_session,
        )
        self.start_btn.pack(side=tk.LEFT, padx=(0, 6))

        self.pause_btn = tk.Button(
            btn_frame,
            text="⏸ Пауза",
            font=self.btn_font,
            bg="#ffd166",
            fg=BG,
            activebackground="#e6b84d",
            activeforeground=BG,
            relief=tk.FLAT,
            bd=0,
            padx=16,
            pady=7,
            cursor="hand2",
            command=self._toggle_pause,
            state=tk.DISABLED,
        )
        self.pause_btn.pack(side=tk.LEFT, padx=(0, 6))

        self.stop_btn = tk.Button(
            btn_frame,
            text="■ Стоп",
            font=self.btn_font,
            bg=BTN_STOP,
            fg=FG,
            activebackground="#e05555",
            activeforeground="white",
            relief=tk.FLAT,
            bd=0,
            padx=20,
            pady=7,
            cursor="hand2",
            command=self.logic.stop_session,
            state=tk.DISABLED,
        )
        self.stop_btn.pack(side=tk.LEFT)

        self.skip_break_btn = tk.Button(
            btn_frame,
            text="⏭ Скип перерыва",
            font=self.tiny_font,
            bg=BG_CARD,
            fg=COMBO_COLOR,
            activebackground=BTN_HOVER,
            activeforeground=COMBO_COLOR,
            relief=tk.FLAT,
            bd=0,
            padx=8,
            pady=4,
            cursor="hand2",
            command=self._skip_break,
            state=tk.DISABLED,
        )
        self.skip_break_btn.pack(side=tk.LEFT, padx=(6, 0))

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
        # Строка статуса и % над баром
        status_row = tk.Frame(self.root, bg=BG)
        status_row.pack(fill=tk.X, padx=12, pady=(4, 1))

        self.session_status = tk.Label(
            status_row,
            text="",
            font=self.tiny_font,
            fg=FG_SECONDARY,
            bg=BG,
            anchor=tk.W,
        )
        self.session_status.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.sprint_pct_label = tk.Label(
            status_row,
            text="",
            font=self.tiny_font,
            fg=ACCENT,
            bg=BG,
            anchor=tk.E,
        )
        self.sprint_pct_label.pack(side=tk.RIGHT)

        # Сам бар (выше 14px)
        self.sprint_bar_bg = tk.Canvas(
            self.root,
            width=WINDOW_W - 24,
            height=14,
            bg=BAR_BG,
            highlightthickness=0,
        )
        self.sprint_bar_bg.pack(padx=12, pady=(0, 6))
        self.sprint_bar_fill = self.sprint_bar_bg.create_rectangle(
            0, 0, 0, 14, fill=BAR_FG, width=0
        )

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
        self._update_session_time()
        self._update_session_buttons()
        self._update_phase_label()
        self._update_tab_label()
        self._update_sprint_bar()
        self._update_stats_cards()
        self._update_goal_bar()
        self._update_active_goal()
        self._update_speed_chart()

    def _update_counter(self):
        today_points = self.logic.get_today_points()
        self.canvas.itemconfig(self.points_text, text=str(today_points))

    def _update_rank(self):
        self.rank_label.config(text=self.logic.get_rank())

    def _update_session_time(self):
        """\u041e\u0431\u043d\u043e\u0432\u0438\u0442\u044c \u0432\u0440\u0435\u043c\u044f \u0441\u0435\u0441\u0441\u0438\u0438 \u0432 \u0448\u0430\u043f\u043a\u0435."""
        if self.logic.session_active and self.logic.session_start:
            elapsed = int(time.time() - self.logic.session_start)
            h, rem = divmod(elapsed, 3600)
            m, s = divmod(rem, 60)
            if h:
                txt = f"\u23f1 {h}:{m:02d}:{s:02d}"
            else:
                txt = f"\u23f1 {m:02d}:{s:02d}"
            self.session_time_label.config(text=txt, fg=FG_SECONDARY)
        else:
            self.session_time_label.config(text="")

    def _update_session_buttons(self):
        if self.logic.session_active:
            self.start_btn.config(state=tk.DISABLED)
            self.pause_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.NORMAL)
            # Кнопка скипа перерыва активна только во время перерыва
            if self.logic.current_phase == "break" and not self.logic.paused:
                self.skip_break_btn.config(state=tk.NORMAL)
            else:
                self.skip_break_btn.config(state=tk.DISABLED)
        else:
            self.start_btn.config(state=tk.NORMAL)
            self.pause_btn.config(state=tk.DISABLED)
            self.stop_btn.config(state=tk.DISABLED)
            self.skip_break_btn.config(state=tk.DISABLED)

    def _toggle_pause(self):
        """Переключить паузу сессии."""
        self.logic.toggle_pause()
        if self.logic.paused:
            self.pause_btn.config(text="▶ Продолжить")
            self.phase_label.config(text="⏸ Пауза", fg="#ffd166")
        else:
            self.pause_btn.config(text="⏸ Пауза")
            self._update_phase_label()

    def _skip_break(self):
        """Пропустить текущий перерыв."""
        self.logic.skip_break()
        self._update_session_buttons()
        self._update_phase_label()

    def _update_phase_label(self):
        if self.logic.session_active:
            if self.logic.paused:
                self.phase_label.config(
                    text="⏸ Пауза (время остановлено)",
                    fg="#ffd166",
                )
            elif self.logic.current_phase == "sprint":
                num, total = self.logic.get_phase_number()
                self.phase_label.config(
                    text=f"⏱ Спринт {num}/{total}",
                    fg=ACCENT,
                )
            elif self.logic.current_phase == "break":
                num, total = self.logic.get_phase_number()
                self.phase_label.config(
                    text=f"☕ Перерыв {num}/{total}",
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
        # \u0426\u0432\u0435\u0442 \u0431\u0430\u0440\u0430 \u043c\u0435\u043d\u044f\u0435\u0442\u0441\u044f \u0434\u043b\u044f \u043f\u0435\u0440\u0435\u0440\u044b\u0432\u0430
        bar_color = BAR_FG_BREAK if phase == "break" else BAR_FG
        self.sprint_bar_bg.itemconfig(self.sprint_bar_fill, fill=bar_color)
        self.sprint_bar_bg.coords(self.sprint_bar_fill, 0, 0, int(bar_w * progress), 14)

        pct_text = f"{int(progress * 100)}%" if phase in ("sprint", "break") else ""
        self.sprint_pct_label.config(text=pct_text)

        if self.logic.paused:
            self.session_status.config(
                text="\u23f8 \u041f\u0430\u0443\u0437\u0430 \u2014 \u0432\u0440\u0435\u043c\u044f \u043e\u0441\u0442\u0430\u043d\u043e\u0432\u043b\u0435\u043d\u043e",
                fg="#ffd166",
            )
        elif phase == "sprint":
            mins, secs = divmod(int(remaining), 60)
            self.session_status.config(
                text=f"\u23f1 {mins:02d}:{secs:02d}  \u2022  \u0422\u043e\u0447\u0435\u043a \u0432 \u0441\u043f\u0440\u0438\u043d\u0442\u0435: {self.logic.session_points}",
                fg=ACCENT,
            )
        elif phase == "break":
            mins, secs = divmod(int(remaining), 60)
            self.session_status.config(
                text=f"\u2615 {mins:02d}:{secs:02d}  \u2022  \u041e\u0442\u0434\u044b\u0445",
                fg=COMBO_COLOR,
            )
        else:
            self.sprint_bar_bg.coords(self.sprint_bar_fill, 0, 0, 0, 14)
            self.session_status.config(text="", fg=FG_SECONDARY)

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
        self.earnings_day.config(text=f"{today_earn:.0f} ₽", fg="#ffd700")

        period_earn = 0.0
        dates_text = ""

        if self.earnings_period_var.get() == "day":
            period_earn = today_earn
            dates_text = time.strftime("%d.%m")
        elif self.earnings_period_var.get() == "period":
            # Первая половина месяца (1-15) или вторая (16-30/31)
            day = time.localtime().tm_mday
            if day <= 15:
                start_day, end_day = 1, 15
                dates_text = "1 — 15"
            else:
                _, last_day = calendar.monthrange(time.localtime().tm_year, time.localtime().tm_mon)
                start_day, end_day = 16, last_day
                dates_text = f"16 — {last_day}"

            # Считаем заработок за выбранный период
            period_points = 0
            for s in self.logic.sessions:
                sess_date = time.strftime("%Y-%m-%d", time.localtime(s.started_at))
                sess_day = int(sess_date.split("-")[2])
                if start_day <= sess_day <= end_day:
                    period_points += s.points
            period_earn = period_points * self.logic.point_price
        else:
            # Всё время
            total_earn = self.logic.get_total_earnings()
            period_earn = total_earn
            dates_text = "Всё время"

        self.earnings_period.config(text=f"{period_earn:.0f} ₽", fg="#ffd700")
        self.earnings_dates_label.config(text=dates_text)

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
        self.goal_bar_bg.coords(self.goal_bar_fill, 0, 0, int(bar_w * progress), 8)

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
                8,
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
            self.goal_bar_bg_act.coords(self.goal_bar_fill_act, 0, 0, 0, 8)
            self.goal_title_label.config(text="📋 Активная цель не выбрана", fg=FG_SECONDARY)
            self.goal_progress_label.config(text="Создайте цель в окне прогнозов (📋)", fg=FG_SECONDARY)

    # ---------- Мини-график скорости ----------
    def _build_speed_chart(self):
        """Построить Canvas для мини-графика скорости сессии."""
        self._speed_chart_frame = tk.Frame(self.root, bg=BG)
        # Изначально скрыт — появляется только при активной сессии
        # (не pack сразу)

        header_row = tk.Frame(self._speed_chart_frame, bg=BG)
        header_row.pack(fill=tk.X, padx=12, pady=(4, 0))

        tk.Label(
            header_row,
            text="⚡ Скорость сессии",
            font=self.tiny_font,
            fg=FG_SECONDARY,
            bg=BG,
            anchor=tk.W,
        ).pack(side=tk.LEFT)

        self._speed_chart_info = tk.Label(
            header_row,
            text="",
            font=self.tiny_font,
            fg=ACCENT,
            bg=BG,
            anchor=tk.E,
        )
        self._speed_chart_info.pack(side=tk.RIGHT)

        chart_h = 70
        self._speed_canvas = tk.Canvas(
            self._speed_chart_frame,
            width=WINDOW_W - 24,
            height=chart_h,
            bg="#0d0d22",
            highlightthickness=1,
            highlightbackground="#1e1e4a",
        )
        self._speed_canvas.pack(padx=12, pady=(2, 6))
        self._speed_chart_visible = False

    def _update_speed_chart(self):
        """Обновить мини-график скорости."""
        active = self.logic.session_active

        # Показываем / скрываем фрейм
        if active and not self._speed_chart_visible:
            self._speed_chart_frame.pack(fill=tk.X, before=self.sprint_bar_bg)
            self._speed_chart_visible = True
        elif not active and self._speed_chart_visible:
            self._speed_chart_frame.pack_forget()
            self._speed_chart_visible = False

        if not active:
            return

        history = self.logic.get_speed_history(window_minutes=30)
        c = self._speed_canvas
        c.delete("all")

        W = WINDOW_W - 24
        H = 70
        pad_l, pad_r, pad_t, pad_b = 4, 4, 6, 14

        plot_w = W - pad_l - pad_r
        plot_h = H - pad_t - pad_b

        # Сетка
        for i in range(3):
            y = pad_t + int(plot_h * i / 2)
            c.create_line(pad_l, y, W - pad_r, y, fill="#1a1a3a", width=1)

        if len(history) < 2:
            # Нет данных — подпись
            c.create_text(
                W // 2, H // 2,
                text="Данные появятся через 30 сек...",
                fill="#444466",
                font=("Segoe UI", 8),
            )
            self._speed_chart_info.config(text="")
            return

        speeds = [spd for _, spd in history]
        max_spd = max(speeds) if max(speeds) > 0 else 1
        min_spd = 0

        def to_xy(i, spd):
            x = pad_l + int(plot_w * i / (len(history) - 1))
            y = pad_t + int(plot_h * (1 - (spd - min_spd) / (max_spd - min_spd + 0.001)))
            return x, y

        # Заливка под кривой
        pts = []
        for i, (_, spd) in enumerate(history):
            pts.append(to_xy(i, spd))
        poly = [pad_l, H - pad_b] + [coord for xy in pts for coord in xy] + [W - pad_r, H - pad_b]
        c.create_polygon(poly, fill=SPEED_CHART_FILL, stipple="gray25", outline="")

        # Линия
        for i in range(len(pts) - 1):
            c.create_line(*pts[i], *pts[i + 1], fill=SPEED_CHART_LINE, width=2, smooth=True)

        # Точки
        for x, y in pts:
            c.create_oval(x - 2, y - 2, x + 2, y + 2, fill=SPEED_CHART_DOT, outline="")

        # Метка максимума
        c.create_text(pad_l + 2, pad_t + 2, text=f"{max_spd:.0f}", fill="#888", font=("Segoe UI", 7), anchor="nw")

        # Текущая скорость в info
        last_speed = speeds[-1]
        self._speed_chart_info.config(text=f"сейчас {last_speed:.0f} т/ч")

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
                card["frame"].configure(highlightbackground="#2a2a5e")
                for child in card["frame"].winfo_children():
                    child.configure(bg=bg)
            except:
                pass

    # ============================================================
    #  7. СОХРАНЕНИЕ И ЗАКРЫТИЕ
    # ============================================================
    def _auto_save(self):
        # Используем save_logic_progress — он передаёт все поля по именам,
        # включая current_cycle, paused, pause_start, paused_accumulated.
        save_logic_progress(self.logic)

    def on_close(self):
        # Завершаем сессию и сохраняем — всё в try-except,
        # чтобы гарантированно сохранить данные даже при ошибках в GUI
        try:
            self.logic.close()
        except Exception:
            pass
        try:
            save_logic_progress(self.logic)
        except Exception:
            pass
        if self.floating_widget and self.floating_widget.window.winfo_exists():
            self.floating_widget.close()
        if self._stats_window and self._stats_window.window.winfo_exists():
            self._stats_window.close()
        if self._settings_window and self._settings_window.window.winfo_exists():
            self._settings_window.window.destroy()
        self.root.destroy()


    def run(self):
        self.root.mainloop()