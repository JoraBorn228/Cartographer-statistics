"""
Окно статистики с карточками сессий, быстрым выбором даты и агрегированной статистикой.
"""
import tkinter as tk
from tkinter import ttk
import time
from datetime import datetime, timedelta
from typing import List, Optional

import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from src.core.models import Session
from src.core.storage import save_progress
from src.utils.config import BG, FG, ACCENT, BAR_BG, BTN_BG, BTN_STOP
from src.utils.helpers import (
    format_duration, format_datetime, format_points_per_hour,
    is_productive_tab, get_productive_tab_time,
    calc_points_per_hour, calc_level,
)


class StatsWindow:
    def __init__(self, parent, logic):
        self.parent = parent
        self.logic = logic
        self.window = tk.Toplevel(parent)
        self.window.title("📊 Статистика сессий")
        self.window.geometry("1000x850")
        self.window.minsize(800, 700)
        self.window.configure(bg=BG)
        self.window.attributes("-topmost", True)
        self.window.protocol("WM_DELETE_WINDOW", self.close)

        self.selected_session: Optional[Session] = None
        self.filter_from = tk.StringVar(value="")
        self.filter_to = tk.StringVar(value="")
        self.sort_by = tk.StringVar(value="Дата (новые сначала)")
        self.filtered_sessions: List[Session] = []
        self.card_frames = []
        self.quick_cards = {}

        self._build_ui()
        self._apply_filter()

    # ---------- Построение интерфейса ----------
    def _build_ui(self):
        # --- Панель быстрых кнопок ---
        quick_frame = tk.Frame(self.window, bg=BG)
        quick_frame.pack(fill=tk.X, padx=10, pady=(10, 5))

        tk.Label(quick_frame, text="📅 Период:", fg=FG, bg=BG, font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=(0, 10))

        for label, days in [("Сегодня", 0), ("Вчера", 1), ("Неделя", 7), ("Месяц", 30), ("Всё", -1)]:
            btn = tk.Button(
                quick_frame,
                text=label,
                command=lambda d=days: self._set_quick_date(d),
                bg=BTN_BG,
                fg=FG,
                relief=tk.FLAT,
                padx=8,
                pady=2,
                cursor="hand2",
                font=("Segoe UI", 8)
            )
            btn.pack(side=tk.LEFT, padx=2)

        # --- Карточки быстрой статистики ---
        self._build_quick_cards()

        # --- Панель фильтрации ---
        control_frame = tk.Frame(self.window, bg=BG)
        control_frame.pack(fill=tk.X, padx=10, pady=5)

        tk.Label(control_frame, text="От:", fg=FG, bg=BG).pack(side=tk.LEFT, padx=(0, 2))
        from_entry = tk.Entry(control_frame, textvariable=self.filter_from, width=10, bg=BAR_BG, fg=FG, insertbackground=FG)
        from_entry.pack(side=tk.LEFT, padx=(0, 5))

        tk.Label(control_frame, text="До:", fg=FG, bg=BG).pack(side=tk.LEFT, padx=(0, 2))
        to_entry = tk.Entry(control_frame, textvariable=self.filter_to, width=10, bg=BAR_BG, fg=FG, insertbackground=FG)
        to_entry.pack(side=tk.LEFT, padx=(0, 5))

        tk.Button(
            control_frame,
            text="🔄 Применить",
            command=self._apply_filter,
            bg=ACCENT,
            fg=BG,
            relief=tk.FLAT,
            padx=8,
            pady=2,
            cursor="hand2"
        ).pack(side=tk.LEFT, padx=(0, 10))

        tk.Label(control_frame, text="Сортировка:", fg=FG, bg=BG).pack(side=tk.LEFT, padx=(0, 2))
        sort_combo = ttk.Combobox(
            control_frame,
            textvariable=self.sort_by,
            values=[
                "Дата (новые сначала)", "Дата (старые сначала)",
                "По точкам (↑)", "По точкам (↓)",
                "По скорости (↑)", "По скорости (↓)"
            ],
            width=16,
            state="readonly"
        )
        sort_combo.pack(side=tk.LEFT, padx=(0, 10))
        sort_combo.bind("<<ComboboxSelected>>", lambda e: self._apply_filter())

        tk.Button(
            control_frame,
            text="🔄 Обновить",
            command=self._apply_filter,
            bg=BTN_BG,
            fg=FG,
            relief=tk.FLAT,
            padx=6,
            pady=2,
            cursor="hand2"
        ).pack(side=tk.LEFT)

        # --- Мини-график ---
        self._build_mini_chart()

        # --- Основная панель: список карточек слева, детали справа ---
        main_pane = tk.Frame(self.window, bg=BG)
        main_pane.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        # Левая часть - список сессий
        left_frame = tk.Frame(main_pane, bg=BG, width=450)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        left_frame.pack_propagate(False)

        # Заголовок списка
        tk.Label(
            left_frame,
            text="📋 Сессии",
            font=("Segoe UI", 10, "bold"),
            fg=ACCENT,
            bg=BG,
            anchor=tk.W
        ).pack(fill=tk.X, pady=(0, 5))

        canvas = tk.Canvas(left_frame, bg=BG, highlightthickness=0)
        scrollbar = tk.Scrollbar(left_frame, orient=tk.VERTICAL, command=canvas.yview)
        self.scrollable_frame = tk.Frame(canvas, bg=BG)
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Правая часть - детали
        right_frame = tk.Frame(main_pane, bg=BG, width=400)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        right_frame.pack_propagate(False)

        tk.Label(
            right_frame,
            text="📄 Детали сессии",
            font=("Segoe UI", 10, "bold"),
            fg=ACCENT,
            bg=BG,
            anchor=tk.W
        ).pack(fill=tk.X, pady=(0, 5))

        self.detail_text = tk.Text(
            right_frame,
            bg=BAR_BG,
            fg=FG,
            font=("Consolas", 9),
            wrap=tk.WORD,
            relief=tk.FLAT,
            padx=10,
            pady=10,
            height=20
        )
        self.detail_text.pack(fill=tk.BOTH, expand=True)

        btn_frame = tk.Frame(right_frame, bg=BG)
        btn_frame.pack(fill=tk.X, pady=(10, 0))

        self.delete_btn = tk.Button(
            btn_frame,
            text="🗑 Удалить сессию",
            bg=BTN_STOP,
            fg=FG,
            relief=tk.FLAT,
            padx=10,
            pady=5,
            cursor="hand2",
            command=self._delete_selected_session,
            state=tk.DISABLED
        )
        self.delete_btn.pack(side=tk.LEFT, padx=2)

        tk.Button(
            btn_frame,
            text="📋 Копировать детали",
            bg=BTN_BG,
            fg=FG,
            relief=tk.FLAT,
            padx=10,
            pady=5,
            cursor="hand2",
            command=self._copy_details
        ).pack(side=tk.LEFT, padx=2)

    # ---------- Карточки быстрой статистики ----------
    def _build_quick_cards(self):
        """Создать карточки быстрой статистики."""
        cards_frame = tk.Frame(self.window, bg=BG)
        cards_frame.pack(fill=tk.X, padx=10, pady=(0, 5))

        stats = [
            ("📌", "Точек", "0", "#00d4aa"),
            ("⚡", "Скорость", "0 т/ч", "#ffd166"),
            ("💰", "Заработано", "0 ₽", "#ff6b6b"),
            ("⏱", "Время", "0:00", "#4ecdc4"),
            ("📅", "Сессий", "0", "#a29bfe"),
        ]

        for icon, label, default, color in stats:
            card = tk.Frame(
                cards_frame,
                bg="#1a1a3e",
                relief=tk.GROOVE,
                bd=1,
                padx=8,
                pady=4
            )
            card.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)

            header = tk.Frame(card, bg="#1a1a3e")
            header.pack(fill=tk.X)

            tk.Label(
                header,
                text=icon,
                font=("Segoe UI", 10),
                fg=color,
                bg="#1a1a3e"
            ).pack(side=tk.LEFT)

            tk.Label(
                header,
                text=label,
                font=("Segoe UI", 8),
                fg="#888",
                bg="#1a1a3e"
            ).pack(side=tk.LEFT, padx=(2, 0))

            value = tk.Label(
                card,
                text=default,
                font=("Segoe UI", 12, "bold"),
                fg=FG,
                bg="#1a1a3e",
                anchor=tk.W
            )
            value.pack(fill=tk.X, pady=(0, 2))

            key = label.lower()
            self.quick_cards[key] = value

    # ---------- Мини-график ----------
    def _build_mini_chart(self):
        """Создать мини-график точек по дням."""
        chart_frame = tk.Frame(self.window, bg=BG)
        chart_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        self.fig = Figure(figsize=(8, 1.5), dpi=80, facecolor="#1a1a3e")
        self.ax = self.fig.add_subplot(111)
        self.ax.set_facecolor("#1a1a3e")
        self.ax.tick_params(colors='#888', labelsize=8)
        self.ax.grid(True, color='#2a2a40', linestyle='--', alpha=0.3)

        self.canvas = FigureCanvasTkAgg(self.fig, master=chart_frame)
        self.canvas.get_tk_widget().pack(fill=tk.X, pady=5)

    def _update_mini_chart(self):
        """Обновить мини-график."""
        self.ax.clear()

        if not self.filtered_sessions:
            self.ax.text(0.5, 0.5, "Нет данных", ha='center', va='center', color='#888', fontsize=10)
            self.ax.set_facecolor("#1a1a3e")
            self.canvas.draw()
            return

        # Агрегируем по дням
        daily = {}
        for sess in self.filtered_sessions:
            day = time.strftime("%Y-%m-%d", time.localtime(sess.started_at))
            daily[day] = daily.get(day, 0) + sess.points

        dates = sorted(daily.keys())[-30:]  # последние 30 дней
        values = [daily[d] for d in dates]

        if len(dates) > 1:
            self.ax.plot(range(len(dates)), values, marker='o', color='#00d4aa', linewidth=2, markersize=4)
            self.ax.fill_between(range(len(dates)), 0, values, alpha=0.2, color='#00d4aa')
            self.ax.set_xticks(range(len(dates)))

            step = max(1, len(dates) // 8)
            labels = [d[5:] if i % step == 0 else "" for i, d in enumerate(dates)]
            self.ax.set_xticklabels(labels, rotation=45, ha='right', color='#888', fontsize=7)

        if values:
            avg = sum(values) / len(values)
            self.ax.axhline(y=avg, color='#ff6b6b', linestyle='--', linewidth=1, alpha=0.5)

        self.ax.set_facecolor("#1a1a3e")
        self.fig.tight_layout()
        self.canvas.draw()

    # ---------- Быстрый выбор даты ----------
    def _set_quick_date(self, days_back: int):
        """Установить фильтр на последние N дней (-1 = всё время)."""
        if days_back == -1:
            self.filter_from.set("")
            self.filter_to.set("")
        else:
            today = datetime.now().date()
            from_date = today - timedelta(days=days_back)
            self.filter_from.set(from_date.strftime("%Y-%m-%d"))
            self.filter_to.set(today.strftime("%Y-%m-%d"))
        self._apply_filter()

    # ---------- Фильтрация и сортировка ----------
    def _get_sessions(self) -> List[Session]:
        sessions = self.logic.sessions.copy()
        if self.logic.session_active and self.logic.session_start:
            now = time.time()
            live = Session(
                started_at=self.logic.session_start,
                ended_at=now,
                points=self.logic.session_points,
                tab_times=dict(self.logic.tab_times),
            )
            sessions.append(live)

        date_from = self.filter_from.get().strip()
        date_to = self.filter_to.get().strip()
        if date_from:
            try:
                from_ts = time.mktime(time.strptime(date_from, "%Y-%m-%d"))
                sessions = [s for s in sessions if s.started_at >= from_ts]
            except ValueError:
                pass
        if date_to:
            try:
                to_ts = time.mktime(time.strptime(date_to, "%Y-%m-%d")) + 24*3600 - 1
                sessions = [s for s in sessions if s.started_at <= to_ts]
            except ValueError:
                pass

        return sessions

    def _sort_sessions(self, sessions: List[Session]) -> List[Session]:
        sort_key = self.sort_by.get()
        if sort_key == "Дата (новые сначала)":
            return sorted(sessions, key=lambda s: s.started_at, reverse=True)
        elif sort_key == "Дата (старые сначала)":
            return sorted(sessions, key=lambda s: s.started_at)
        elif sort_key == "По точкам (↑)":
            return sorted(sessions, key=lambda s: s.points)
        elif sort_key == "По точкам (↓)":
            return sorted(sessions, key=lambda s: s.points, reverse=True)
        elif sort_key == "По скорости (↑)":
            return sorted(sessions, key=lambda s: s.points / (get_productive_tab_time(s.tab_times) / 3600) if get_productive_tab_time(s.tab_times) > 0 else 0)
        elif sort_key == "По скорости (↓)":
            return sorted(sessions, key=lambda s: s.points / (get_productive_tab_time(s.tab_times) / 3600) if get_productive_tab_time(s.tab_times) > 0 else 0, reverse=True)
        else:
            return sessions

    def _apply_filter(self):
        """Применить фильтр и обновить интерфейс."""
        raw = self._get_sessions()
        self.filtered_sessions = self._sort_sessions(raw)

        self._update_aggregated_stats()
        self._update_mini_chart()

        # Очищаем старые карточки
        for frame in self.card_frames:
            frame.destroy()
        self.card_frames.clear()

        # Создаём карточки
        if self.filtered_sessions:
            max_points = max(s.points for s in self.filtered_sessions)
            for idx, sess in enumerate(self.filtered_sessions):
                card = self._create_card(sess, idx, max_points)
                self.card_frames.append(card)
                card.pack(fill=tk.X, pady=2, padx=2)

        if self.selected_session in self.filtered_sessions:
            self._show_details(self.selected_session)
        else:
            self.selected_session = None
            self.detail_text.delete(1.0, tk.END)
            self.delete_btn.config(state=tk.DISABLED)

        self.scrollable_frame.update_idletasks()

    # ---------- Агрегированная статистика ----------
    def _get_speed_color(self, speed: float) -> str:
        """Цвет для скорости."""
        if speed is None:
            return "#888"
        if speed >= 300:
            return "#00d4aa"
        elif speed >= 200:
            return "#ffd166"
        elif speed >= 100:
            return "#ff9f43"
        else:
            return "#ff6b6b"

    def _update_aggregated_stats(self):
        """Обновить карточки быстрой статистики."""
        sessions = self.filtered_sessions
        if not sessions:
            for card in self.quick_cards.values():
                card.config(text="—")
            return

        count = len(sessions)
        total_points = sum(s.points for s in sessions)
        total_productive = sum(get_productive_tab_time(s.tab_times) for s in sessions)
        total_duration = sum(s.duration for s in sessions)
        total_earnings = total_points * self.logic.point_price

        avg_speed = calc_points_per_hour(total_points, total_productive)
        avg_speed_str = f"{avg_speed:.0f} т/ч" if avg_speed is not None else "—"

        self.quick_cards['точек'].config(text=f"{total_points:,}")
        self.quick_cards['скорость'].config(
            text=avg_speed_str,
            fg=self._get_speed_color(avg_speed) if avg_speed else FG
        )
        self.quick_cards['заработано'].config(text=f"{total_earnings:.0f} ₽")
        self.quick_cards['время'].config(text=format_duration(total_productive))
        self.quick_cards['сессий'].config(text=str(count))

    # ---------- Создание карточки ----------
    def _create_card(self, session: Session, index: int, max_points: int) -> tk.Frame:
        card = tk.Frame(
            self.scrollable_frame,
            bg="#2a2a40",
            relief=tk.RAISED,
            borderwidth=1,
            highlightthickness=1,
            highlightcolor="#3d3d6b"
        )

        is_best = session.points == max_points and max_points > 0
        if is_best:
            card.configure(bg="#1a3a2e", highlightcolor="#00d4aa")

        card.bind("<Button-1>", lambda e, s=session: self._on_card_click(s))
        card.bind("<Enter>", lambda e, c=card: c.configure(bg="#3d3d6b" if not is_best else "#1a4a3e"))
        card.bind("<Leave>", lambda e, c=card: c.configure(bg="#2a2a40" if not is_best else "#1a3a2e"))

        start = time.localtime(session.started_at)
        end = time.localtime(session.ended_at)
        prod_secs = get_productive_tab_time(session.tab_times)
        speed = calc_points_per_hour(session.points, prod_secs)
        speed_str = format_points_per_hour(session.points, prod_secs)
        earnings = session.points * self.logic.point_price
        duration = session.duration

        # Верхняя часть карточки
        top_frame = tk.Frame(card, bg=card.cget('bg'))
        top_frame.pack(fill=tk.X, padx=8, pady=(4, 2))

        left_frame = tk.Frame(top_frame, bg=card.cget('bg'))
        left_frame.pack(side=tk.LEFT)

        tk.Label(
            left_frame,
            text=f"{start.tm_mday:02d}.{start.tm_mon:02d}.{start.tm_year} {start.tm_hour:02d}:{start.tm_min:02d}",
            font=("Segoe UI", 9, "bold"),
            fg=ACCENT if not is_best else "#00d4aa",
            bg=card.cget('bg')
        ).pack(side=tk.LEFT)

        if is_best:
            tk.Label(
                left_frame,
                text=" ⭐ Рекорд!",
                font=("Segoe UI", 8, "bold"),
                fg="#ffd700",
                bg=card.cget('bg')
            ).pack(side=tk.LEFT, padx=(5, 0))

        right_frame = tk.Frame(top_frame, bg=card.cget('bg'))
        right_frame.pack(side=tk.RIGHT)

        speed_color = self._get_speed_color(speed) if speed else "#888"
        tk.Label(
            right_frame,
            text=f"{session.points} pts",
            font=("Segoe UI", 10, "bold"),
            fg=speed_color,
            bg=card.cget('bg')
        ).pack(side=tk.RIGHT, padx=(0, 10))

        bottom_frame = tk.Frame(card, bg=card.cget('bg'))
        bottom_frame.pack(fill=tk.X, padx=8, pady=(0, 4))

        info_text = f"⚡ {speed_str}  |  ⏱ {format_duration(duration)}  |  💰 {earnings:.0f} ₽"
        tk.Label(
            bottom_frame,
            text=info_text,
            font=("Segoe UI", 8),
            fg="#888",
            bg=card.cget('bg')
        ).pack(side=tk.LEFT)

        def bind_click(widget):
            widget.bind("<Button-1>", lambda e, s=session: self._on_card_click(s))
            for child in widget.winfo_children():
                bind_click(child)

        bind_click(card)

        return card

    # ---------- Обработка клика ----------
    def _on_card_click(self, session: Session):
        self.selected_session = session
        self._show_details(session)
        for frame in self.card_frames:
            frame.configure(bg="#2a2a40")
            for child in frame.winfo_children():
                child.configure(bg="#2a2a40")
        for idx, sess in enumerate(self.filtered_sessions):
            if sess == session:
                card = self.card_frames[idx]
                is_best = sess.points == max(s.points for s in self.filtered_sessions) if self.filtered_sessions else False
                card.configure(bg="#1a3a2e" if is_best else "#3d3d6b")
                for child in card.winfo_children():
                    child.configure(bg="#1a3a2e" if is_best else "#3d3d6b")
                break

    # ---------- Детали ----------
    def _show_details(self, session: Session):
        self.detail_text.delete(1.0, tk.END)
        prod_secs = get_productive_tab_time(session.tab_times)
        speed = calc_points_per_hour(session.points, prod_secs)
        speed_str = format_points_per_hour(session.points, prod_secs)
        earnings = session.points * self.logic.point_price

        lines = [
            "┌──────────────────────────────────────────────",
            f"│ 📅 {format_datetime(session.started_at)}",
            f"│ ⏱ Длительность:  {format_duration(session.duration)}",
            f"│ 📌 Точек:        {session.points}",
            f"│ ⚡ Скорость:     {speed_str}",
            f"│ 💰 Заработано:   {earnings:.0f} ₽",
            f"│ ⏱ Чистое время:  {format_duration(prod_secs)}",
            "├──────────────────────────────────────────────",
            "│ 📂 Вкладки (только время спринтов):",
        ]
        self.detail_text.insert(tk.END, "\n".join(lines) + "\n")

        if session.tab_times:
            for title, secs in sorted(session.tab_times.items(), key=lambda x: x[1], reverse=True)[:10]:
                marker = " ⭐" if is_productive_tab(title) else ""
                self.detail_text.insert(tk.END, f"│   {format_duration(secs)}  —  {title[:40]}{marker}\n")
            if len(session.tab_times) > 10:
                self.detail_text.insert(tk.END, f"│   ... и ещё {len(session.tab_times) - 10} вкладок\n")
        else:
            self.detail_text.insert(tk.END, "│   Нет данных по вкладкам\n")

        self.detail_text.insert(tk.END, "└──────────────────────────────────────────────")
        self.delete_btn.config(state=tk.NORMAL)

    def _copy_details(self):
        """Копировать детали в буфер обмена."""
        text = self.detail_text.get(1.0, tk.END)
        self.window.clipboard_clear()
        self.window.clipboard_append(text)
        self.window.update()

    # ---------- Удаление ----------
    def _delete_selected_session(self):
        if self.selected_session is None:
            return
        if (self.logic.session_active and self.logic.session_start and
            self.selected_session.started_at == self.logic.session_start):
            tk.messagebox.showinfo("Удаление", "Нельзя удалить текущую активную сессию.", parent=self.window)
            return

        try:
            real_idx = self.logic.sessions.index(self.selected_session)
        except ValueError:
            tk.messagebox.showerror("Ошибка", "Сессия не найдена.", parent=self.window)
            return

        if not tk.messagebox.askyesno(
            "Удалить сессию",
            f"Вы уверены, что хотите удалить сессию от {format_datetime(self.selected_session.started_at)}?",
            parent=self.window
        ):
            return

        removed = self.logic.sessions.pop(real_idx)
        self.logic.points = max(0, self.logic.points - removed.points)
        self.logic.level = calc_level(self.logic.points)

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

        self.selected_session = None
        self.logic.on_update()
        self._apply_filter()

    # ---------- Закрытие ----------
    def close(self):
        self.window.destroy()