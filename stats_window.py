"""
Окно статистики с карточками сессий, быстрым выбором даты и агрегированной статистикой.
"""
import tkinter as tk
from tkinter import ttk
import time
from datetime import datetime, timedelta
from typing import List, Optional

from models import Session
from utils import (
    format_duration, format_datetime, format_points_per_hour,
    is_productive_tab, get_productive_tab_time,
    calc_points_per_hour, calc_level,
)
from config import BG, FG, ACCENT, BAR_BG, BTN_BG, BTN_STOP


class StatsWindow:
    def __init__(self, parent, logic):
        self.parent = parent
        self.logic = logic
        self.window = tk.Toplevel(parent)
        self.window.title("📊 Статистика сессий")
        self.window.geometry("900x800")
        self.window.configure(bg=BG)
        self.window.attributes("-topmost", True)
        self.window.protocol("WM_DELETE_WINDOW", self.close)

        self.selected_session: Optional[Session] = None
        self.filter_from = tk.StringVar(value="")
        self.filter_to = tk.StringVar(value="")
        self.sort_by = tk.StringVar(value="Дата (новые сначала)")
        self.filtered_sessions: List[Session] = []
        self.card_frames = []

        self._build_ui()
        self._apply_filter()  # начальный фильтр (всё время)

    # ---------- Построение интерфейса ----------
    def _build_ui(self):
        # --- Панель быстрых кнопок ---
        quick_frame = tk.Frame(self.window, bg=BG)
        quick_frame.pack(fill=tk.X, padx=10, pady=(10, 5))

        tk.Label(quick_frame, text="Быстрый выбор:", fg=FG, bg=BG).pack(side=tk.LEFT, padx=(0, 10))

        btn_today = tk.Button(
            quick_frame,
            text="Сегодня",
            command=lambda: self._set_quick_date(0),
            bg=BTN_BG,
            fg=FG,
            relief=tk.FLAT,
            padx=8,
            pady=2,
            cursor="hand2"
        )
        btn_today.pack(side=tk.LEFT, padx=2)

        btn_yesterday = tk.Button(
            quick_frame,
            text="Вчера",
            command=lambda: self._set_quick_date(1),
            bg=BTN_BG,
            fg=FG,
            relief=tk.FLAT,
            padx=8,
            pady=2,
            cursor="hand2"
        )
        btn_yesterday.pack(side=tk.LEFT, padx=2)

        btn_week = tk.Button(
            quick_frame,
            text="Неделя",
            command=lambda: self._set_quick_date(7),
            bg=BTN_BG,
            fg=FG,
            relief=tk.FLAT,
            padx=8,
            pady=2,
            cursor="hand2"
        )
        btn_week.pack(side=tk.LEFT, padx=2)

        btn_month = tk.Button(
            quick_frame,
            text="Месяц",
            command=lambda: self._set_quick_date(30),
            bg=BTN_BG,
            fg=FG,
            relief=tk.FLAT,
            padx=8,
            pady=2,
            cursor="hand2"
        )
        btn_month.pack(side=tk.LEFT, padx=2)

        btn_all = tk.Button(
            quick_frame,
            text="Всё время",
            command=self._set_all_time,
            bg=BTN_BG,
            fg=FG,
            relief=tk.FLAT,
            padx=8,
            pady=2,
            cursor="hand2"
        )
        btn_all.pack(side=tk.LEFT, padx=2)

        # --- Панель фильтрации (поля ввода даты) ---
        control_frame = tk.Frame(self.window, bg=BG)
        control_frame.pack(fill=tk.X, padx=10, pady=5)

        tk.Label(control_frame, text="Дата от:", fg=FG, bg=BG).pack(side=tk.LEFT, padx=(0, 2))
        from_entry = tk.Entry(control_frame, textvariable=self.filter_from, width=12, bg=BAR_BG, fg=FG, insertbackground=FG)
        from_entry.pack(side=tk.LEFT, padx=(0, 10))

        tk.Label(control_frame, text="до:", fg=FG, bg=BG).pack(side=tk.LEFT, padx=(0, 2))
        to_entry = tk.Entry(control_frame, textvariable=self.filter_to, width=12, bg=BAR_BG, fg=FG, insertbackground=FG)
        to_entry.pack(side=tk.LEFT, padx=(0, 10))

        tk.Button(
            control_frame,
            text="Применить фильтр",
            command=self._apply_filter,
            bg=ACCENT,
            fg=BG,
            relief=tk.FLAT,
            padx=6,
            pady=2,
            cursor="hand2"
        ).pack(side=tk.LEFT, padx=(0, 10))

        tk.Label(control_frame, text="Сортировка:", fg=FG, bg=BG).pack(side=tk.LEFT, padx=(0, 2))
        sort_combo = ttk.Combobox(
            control_frame,
            textvariable=self.sort_by,
            values=["Дата (новые сначала)", "Дата (старые сначала)", "По точкам (↑)", "По точкам (↓)", "По скорости (↑)", "По скорости (↓)"],
            width=20,
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

        # --- Блок агрегированной статистики за выбранный период ---
        self.stats_frame = tk.Frame(self.window, bg=BG)
        self.stats_frame.pack(fill=tk.X, padx=10, pady=(5, 10))

        self.stats_label = tk.Label(
            self.stats_frame,
            text="",
            font=("Segoe UI", 10),
            fg=FG,
            bg=BG,
            justify=tk.LEFT,
            anchor=tk.W
        )
        self.stats_label.pack(fill=tk.X)

        # --- Основная панель: список карточек слева, детали справа ---
        main_pane = tk.Frame(self.window, bg=BG)
        main_pane.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        left_frame = tk.Frame(main_pane, bg=BG, width=450)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        left_frame.pack_propagate(False)

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

        right_frame = tk.Frame(main_pane, bg=BG, width=400)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        right_frame.pack_propagate(False)

        tk.Label(
            right_frame,
            text="Детали сессии",
            font=("Segoe UI", 12, "bold"),
            fg=ACCENT,
            bg=BG
        ).pack(pady=(0, 10))

        self.detail_text = tk.Text(
            right_frame,
            bg=BAR_BG,
            fg=FG,
            font=("Segoe UI", 9),
            wrap=tk.WORD,
            relief=tk.FLAT,
            padx=10,
            pady=10,
            height=20
        )
        self.detail_text.pack(fill=tk.BOTH, expand=True)

        self.delete_btn = tk.Button(
            right_frame,
            text="🗑 Удалить выбранную сессию",
            bg=BTN_STOP,
            fg=FG,
            relief=tk.FLAT,
            padx=10,
            pady=5,
            cursor="hand2",
            command=self._delete_selected_session,
            state=tk.DISABLED
        )
        self.delete_btn.pack(pady=(10, 0))

    # ---------- Быстрый выбор даты ----------
    def _set_quick_date(self, days_back: int):
        """Установить фильтр на последние N дней (0 = сегодня)."""
        today = datetime.now().date()
        if days_back == 0:
            from_date = today
            to_date = today
        else:
            from_date = today - timedelta(days=days_back)
            to_date = today
        self.filter_from.set(from_date.strftime("%Y-%m-%d"))
        self.filter_to.set(to_date.strftime("%Y-%m-%d"))
        self._apply_filter()

    def _set_all_time(self):
        """Сбросить фильтр (всё время)."""
        self.filter_from.set("")
        self.filter_to.set("")
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

        # Обновляем агрегированную статистику
        self._update_aggregated_stats()

        # Очищаем старые карточки
        for frame in self.card_frames:
            frame.destroy()
        self.card_frames.clear()

        # Создаём карточки
        for idx, sess in enumerate(self.filtered_sessions):
            card = self._create_card(sess, idx)
            self.card_frames.append(card)
            card.pack(fill=tk.X, pady=3, padx=5)

        # Если есть выбранная, обновляем детали
        if self.selected_session in self.filtered_sessions:
            self._show_details(self.selected_session)
        else:
            self.selected_session = None
            self.detail_text.delete(1.0, tk.END)
            self.delete_btn.config(state=tk.DISABLED)

        self.scrollable_frame.update_idletasks()

    # ---------- Агрегированная статистика ----------
    def _update_aggregated_stats(self):
        sessions = self.filtered_sessions
        if not sessions:
            self.stats_label.config(text="Нет данных за выбранный период")
            return

        count = len(sessions)
        total_points = sum(s.points for s in sessions)
        total_productive = sum(get_productive_tab_time(s.tab_times) for s in sessions)
        total_duration = sum(s.duration for s in sessions)
        total_earnings = total_points * self.logic.point_price

        avg_speed = calc_points_per_hour(total_points, total_productive)
        avg_speed_str = f"{avg_speed:.1f} точ/ч" if avg_speed is not None else "—"

        avg_per_session = total_points / count if count else 0

        # Определяем текстовое описание периода
        date_from = self.filter_from.get().strip()
        date_to = self.filter_to.get().strip()
        if date_from and date_to:
            if date_from == date_to:
                period_label = date_from
            else:
                period_label = f"{date_from} — {date_to}"
        else:
            period_label = "Всё время"

        text = (
            f"📅 {period_label}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"▸ Сессий: {count}\n"
            f"▸ Всего точек: {total_points}\n"
            f"▸ Среднее точек за сессию: {avg_per_session:.1f}\n"
            f"▸ Чистое время в панорамах: {format_duration(total_productive)}\n"
            f"▸ Общая длительность сессий: {format_duration(total_duration)}\n"
            f"▸ Средняя скорость: {avg_speed_str}\n"
            f"▸ Заработано: {total_earnings:.2f} руб."
        )
        self.stats_label.config(text=text)

    # ---------- Создание карточки ----------
    def _create_card(self, session: Session, index: int) -> tk.Frame:
        card = tk.Frame(
            self.scrollable_frame,
            bg="#2a2a40",
            relief=tk.RAISED,
            borderwidth=1,
            highlightthickness=1,
            highlightcolor="#3d3d6b"
        )
        card.bind("<Button-1>", lambda e, s=session: self._on_card_click(s))
        card.bind("<Enter>", lambda e, c=card: c.configure(bg="#3d3d6b"))
        card.bind("<Leave>", lambda e, c=card: c.configure(bg="#2a2a40"))

        start = time.localtime(session.started_at)
        end = time.localtime(session.ended_at)
        prod_secs = get_productive_tab_time(session.tab_times)
        pph = format_points_per_hour(session.points, prod_secs)
        earnings = session.points * self.logic.point_price
        duration = session.duration

        top_frame = tk.Frame(card, bg="#2a2a40")
        top_frame.pack(fill=tk.X, padx=8, pady=(6, 2))

        lbl_date = tk.Label(
            top_frame,
            text=f"{start.tm_mday:02d}.{start.tm_mon:02d}.{start.tm_year} {start.tm_hour:02d}:{start.tm_min:02d} — {end.tm_hour:02d}:{end.tm_min:02d}",
            font=("Segoe UI", 10, "bold"),
            fg=ACCENT,
            bg="#2a2a40"
        )
        lbl_date.pack(side=tk.LEFT)

        lbl_points = tk.Label(
            top_frame,
            text=f"{session.points} pts",
            font=("Segoe UI", 10, "bold"),
            fg=FG,
            bg="#2a2a40"
        )
        lbl_points.pack(side=tk.RIGHT)

        bottom_frame = tk.Frame(card, bg="#2a2a40")
        bottom_frame.pack(fill=tk.X, padx=8, pady=(0, 6))

        info_text = f"⚡ {pph}  |  ⏱ {format_duration(duration)}  |  💰 {earnings:.2f} руб."
        lbl_info = tk.Label(
            bottom_frame,
            text=info_text,
            font=("Segoe UI", 9),
            fg="#888",
            bg="#2a2a40"
        )
        lbl_info.pack(side=tk.LEFT)

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
                card.configure(bg="#3d3d6b")
                for child in card.winfo_children():
                    child.configure(bg="#3d3d6b")
                break

    # ---------- Детали ----------
    def _show_details(self, session: Session):
        self.detail_text.delete(1.0, tk.END)
        prod_secs = get_productive_tab_time(session.tab_times)
        pph = format_points_per_hour(session.points, prod_secs)
        earnings = session.points * self.logic.point_price

        lines = [
            f"Начало:  {format_datetime(session.started_at)}",
            f"Конец:   {format_datetime(session.ended_at)}",
            f"Длительность: {format_duration(session.duration)}",
            f"Чистое время в панорамах: {format_duration(prod_secs)}",
            f"Точек: {session.points}",
            f"Скорость: {pph}",
            f"Заработано: {earnings:.2f} руб.",
            "",
            "Время по вкладкам:"
        ]
        self.detail_text.insert(tk.END, "\n".join(lines) + "\n")
        if session.tab_times:
            for title, secs in sorted(session.tab_times.items(), key=lambda x: x[1], reverse=True):
                marker = " ★" if is_productive_tab(title) else ""
                self.detail_text.insert(tk.END, f"  {format_duration(secs)}  —  {title}{marker}\n")
        else:
            self.detail_text.insert(tk.END, "  Нет данных по вкладкам\n")

        self.delete_btn.config(state=tk.NORMAL)

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

        from storage import save_progress
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

        self.selected_session = None
        self.logic.on_update()
        self._apply_filter()  # обновляем интерфейс

    # ---------- Закрытие ----------
    def close(self):
        self.window.destroy()