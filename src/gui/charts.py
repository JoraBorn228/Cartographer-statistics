"""
Построение настраиваемых графиков продуктивности (Tkinter).
Обновлённый интерфейс в стиле тёмной темы с подсказками на графике.
"""
import time
import tkinter as tk
from tkinter import ttk
from typing import List, Dict
import numpy as np

import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
from matplotlib.patches import Patch
from matplotlib import rcParams

# Настройка шрифтов для matplotlib
rcParams['font.sans-serif'] = ['Segoe UI', 'DejaVu Sans', 'Arial Unicode MS', 'Microsoft YaHei']
rcParams['axes.unicode_minus'] = False

from src.core.models import Session
from src.utils.helpers import get_productive_tab_time


class ChartsWindow:
    def __init__(self, parent, sessions: List[Session], logic):
        self.parent = parent
        self.logic = logic
        self.sessions = sessions
        self.point_price = logic.point_price
        
        # Агрегируем данные по дням
        self.daily_data = self._aggregate_daily_data()
        self.speed_data = self._calculate_speed_by_day()

        self.window = tk.Toplevel(parent)
        self.window.title("📊 Графики продуктивности")
        self.window.geometry("1200x900")
        self.window.minsize(1000, 750)
        self.window.configure(bg="#0f0f23")
        self.window.attributes("-topmost", True)

        # Для хранения аннотаций
        self.annotation = None
        self.annotation_bar = None

        # Заголовок
        self._build_header()

        # Создаём вкладки
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TNotebook', background='#0f0f23', borderwidth=0)
        style.configure('TNotebook.Tab', 
                       background='#1a1a3e', 
                       foreground='#8888aa',
                       padding=[15, 8],
                       font=('Segoe UI', 10),
                       borderwidth=0)
        style.map('TNotebook.Tab', 
                 background=[('selected', '#2a2a5e')],
                 foreground=[('selected', '#00d4aa')])

        self.notebook = ttk.Notebook(self.window)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=(5, 10))

        # Вкладка 1: Продуктивность по дням
        self.tab1 = tk.Frame(self.notebook, bg="#0f0f23")
        self.notebook.add(self.tab1, text="📊 Продуктивность")
        
        # Вкладка 2: Диаграмма Ганта (сессии по дням)
        self.tab2 = tk.Frame(self.notebook, bg="#0f0f23")
        self.notebook.add(self.tab2, text="📅 Сессии по дням")

        # Вкладка 3: Скорость и тренд
        self.tab3 = tk.Frame(self.notebook, bg="#0f0f23")
        self.notebook.add(self.tab3, text="⚡ Скорость и тренд")

        # --- Вкладка 1: Продуктивность ---
        self._build_productivity_tab()
        
        # --- Вкладка 2: Диаграмма Ганта ---
        self._build_gantt_tab()
        
        # --- Вкладка 3: Скорость и тренд ---
        self._build_speed_tab()

    # ---------- Шапка ----------
    def _build_header(self):
        header = tk.Frame(self.window, bg="#0f0f23")
        header.pack(fill=tk.X, padx=20, pady=(10, 5))

        tk.Label(
            header,
            text="📊 Графики продуктивности",
            font=("Segoe UI", 18, "bold"),
            fg="#00d4aa",
            bg="#0f0f23"
        ).pack(side=tk.LEFT)

        stats_frame = tk.Frame(header, bg="#0f0f23")
        stats_frame.pack(side=tk.RIGHT)

        total_points = sum(self.daily_data[d]['points'] for d in self.daily_data)
        total_days = len(self.daily_data)
        avg_points = total_points / total_days if total_days > 0 else 0

        for text, value, color in [
            (f"📌 Всего точек", f"{total_points:,}", "#00d4aa"),
            (f"📅 Дней", f"{total_days}", "#ffd166"),
            (f"📊 В среднем", f"{avg_points:.0f}", "#ff6b6b"),
        ]:
            card = tk.Frame(stats_frame, bg="#1a1a3e", relief=tk.GROOVE, bd=1, padx=10, pady=3)
            card.pack(side=tk.LEFT, padx=3)
            
            tk.Label(
                card,
                text=text,
                font=("Segoe UI", 8),
                fg="#888",
                bg="#1a1a3e"
            ).pack()
            
            tk.Label(
                card,
                text=value,
                font=("Segoe UI", 10, "bold"),
                fg=color,
                bg="#1a1a3e"
            ).pack()

    # ---------- Агрегация данных ----------
    def _aggregate_daily_data(self) -> Dict[str, Dict]:
        daily = {}
        for sess in self.sessions:
            day = time.strftime("%Y-%m-%d", time.localtime(sess.started_at))
            if day not in daily:
                daily[day] = {'points': 0, 'money': 0.0, 'hours': 0.0}
            daily[day]['points'] += sess.points
            daily[day]['money'] += sess.points * self.point_price
            daily[day]['hours'] += get_productive_tab_time(sess.tab_times) / 3600.0

        # Добавляем текущую сессию ТОЛЬКО если она ещё не в self.sessions
        if self.logic.session_active and self.logic.session_points > 0:
            # Проверяем, есть ли уже сессия с таким же started_at
            already_counted = any(
                s.started_at == self.logic.session_start
                for s in self.sessions
            )
            if not already_counted:
                today = time.strftime("%Y-%m-%d")
                if today not in daily:
                    daily[today] = {'points': 0, 'money': 0.0, 'hours': 0.0}
                daily[today]['points'] += self.logic.session_points
                daily[today]['money'] += self.logic.session_points * self.point_price

        return daily

    def _calculate_speed_by_day(self) -> Dict[str, float]:
        speed_data = {}
        
        for sess in self.sessions:
            day = time.strftime("%Y-%m-%d", time.localtime(sess.started_at))
            prod_time = get_productive_tab_time(sess.tab_times)
            
            if prod_time > 60:
                speed = sess.points / (prod_time / 3600)
                if day not in speed_data:
                    speed_data[day] = {'total_points': 0, 'total_time': 0}
                speed_data[day]['total_points'] += sess.points
                speed_data[day]['total_time'] += prod_time
        
        result = {}
        for day, data in speed_data.items():
            if data['total_time'] > 0:
                result[day] = data['total_points'] / (data['total_time'] / 3600)
        
        return result

    # ============================================================
    # ВКЛАДКА 1: ПРОДУКТИВНОСТЬ
    # ============================================================
    def _build_productivity_tab(self):
        settings_frame = tk.Frame(self.tab1, bg="#0f0f23")
        settings_frame.pack(fill=tk.X, padx=15, pady=(10, 5))

        self.show_points = tk.BooleanVar(value=True)
        self.show_money = tk.BooleanVar(value=True)
        self.show_hours = tk.BooleanVar(value=True)
        self.show_cumulative = tk.BooleanVar(value=False)

        card = tk.Frame(settings_frame, bg="#1a1a3e", relief=tk.GROOVE, bd=1, padx=12, pady=6)
        card.pack(side=tk.LEFT)

        for var, text, color in [
            (self.show_points, "📌 Точки", "#00d4aa"),
            (self.show_money, "💰 Заработок (руб.)", "#ffd700"),
            (self.show_hours, "⏱ Время (ч)", "#ff6b6b"),
            (self.show_cumulative, "📈 Накопленный итог", "#a29bfe"),
        ]:
            cb = tk.Checkbutton(
                card,
                text=text,
                variable=var,
                command=self._update_productivity_chart,
                bg="#1a1a3e",
                fg="#eaeaea",
                selectcolor="#1a1a3e",
                activebackground="#1a1a3e",
                activeforeground="#00d4aa",
                font=("Segoe UI", 9)
            )
            cb.pack(side=tk.LEFT, padx=(0, 15))
            cb.config(highlightcolor=color)

        tk.Label(
            settings_frame,
            text="💡 Наведите на столбец",
            fg="#666",
            bg="#0f0f23",
            font=("Segoe UI", 9)
        ).pack(side=tk.LEFT, padx=(15, 0))

        self.fig1 = Figure(figsize=(10, 5.5), dpi=100, facecolor="#0f0f23")
        self.ax1 = self.fig1.add_subplot(111)
        self.ax1.set_facecolor("#1a1a3e")
        
        self.canvas1 = FigureCanvasTkAgg(self.fig1, master=self.tab1)
        self.canvas1.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=10, pady=(5, 10))

        # Подключаем событие наведения
        self.canvas1.mpl_connect('motion_notify_event', self._on_bar_hover)
        self.canvas1.mpl_connect('axes_leave_event', self._clear_annotation)

        self._update_productivity_chart()

    def _on_bar_hover(self, event):
        """Показать подсказку при наведении на столбец."""
        if event.inaxes != self.ax1:
            self._clear_annotation()
            return
        
        if event.xdata is None:
            self._clear_annotation()
            return
        
        if not hasattr(self, '_bar_data') or not self._bar_data:
            return
        
        idx = int(round(event.xdata))
        if 0 <= idx < len(self._bar_dates):
            if abs(event.xdata - idx) < 0.4:
                data = self._bar_data[idx]
                text = (
                    f"📅 {self._bar_dates[idx]}\n"
                    f"📌 Точки: {data['points']:,}\n"
                    f"💰 Заработок: {data['money']:.2f} руб.\n"
                    f"⏱ Время: {data['hours']:.1f} ч"
                )
                self._show_annotation(event, text)
                return
        
        self._clear_annotation()

    def _show_annotation(self, event, text):
        """Показать аннотацию на графике."""
        if self.annotation:
            self.annotation.remove()
            self.annotation = None
        
        self.annotation = self.ax1.annotate(
            text,
            xy=(event.xdata, event.ydata),
            xytext=(10, -30),
            textcoords='offset points',
            bbox=dict(boxstyle='round,pad=0.5', facecolor='#1a1a3e', edgecolor='#00d4aa', alpha=0.95),
            color='white',
            fontsize=9,
            ha='left',
            va='top'
        )
        self.fig1.canvas.draw_idle()

    def _clear_annotation(self, event=None):
        """Очистить аннотацию."""
        if self.annotation:
            self.annotation.remove()
            self.annotation = None
            self.fig1.canvas.draw_idle()

    def _update_productivity_chart(self):
        self.ax1.clear()
        self.annotation = None

        if not self.daily_data:
            self.ax1.text(0.5, 0.5, "Нет данных для отображения", 
                          ha='center', va='center', color='#888', fontsize=14, fontweight='bold')
            self.ax1.set_facecolor("#1a1a3e")
            self.canvas1.draw()
            return

        dates = sorted(self.daily_data.keys())
        x = list(range(len(dates)))

        points_vals = [self.daily_data[d]['points'] for d in dates]
        money_vals = [self.daily_data[d]['money'] for d in dates]
        hours_vals = [self.daily_data[d]['hours'] for d in dates]

        if self.show_cumulative.get():
            cum_points, cum_money, cum_hours = [], [], []
            p = m = h = 0
            for i in range(len(dates)):
                p += points_vals[i]
                m += money_vals[i]
                h += hours_vals[i]
                cum_points.append(p)
                cum_money.append(m)
                cum_hours.append(h)
            points_vals, money_vals, hours_vals = cum_points, cum_money, cum_hours

        width = 0.25
        colors = {'points': '#00d4aa', 'money': '#ffd700', 'hours': '#ff6b6b'}
        labels = {'points': 'Точки', 'money': 'Заработок (руб.)', 'hours': 'Время (ч)'}

        plotted = False
        self._bar_data = []
        self._bar_dates = dates

        if self.show_points.get():
            self.ax1.bar([i - width for i in x], points_vals, width, 
                         color=colors['points'], label=labels['points'], 
                         alpha=0.85, edgecolor='#00d4aa', linewidth=0.5)
            plotted = True
        if self.show_money.get():
            self.ax1.bar(x, money_vals, width, 
                         color=colors['money'], label=labels['money'], 
                         alpha=0.85, edgecolor='#ffd700', linewidth=0.5)
            plotted = True
        if self.show_hours.get():
            self.ax1.bar([i + width for i in x], hours_vals, width, 
                         color=colors['hours'], label=labels['hours'], 
                         alpha=0.85, edgecolor='#ff6b6b', linewidth=0.5)
            plotted = True

        for i, date in enumerate(dates):
            self._bar_data.append({
                'points': points_vals[i],
                'money': money_vals[i],
                'hours': hours_vals[i],
            })

        if not plotted:
            self.ax1.text(0.5, 0.5, "Выберите хотя бы одну метрику", 
                          ha='center', va='center', color='#888', fontsize=14)
            self.ax1.set_facecolor('#1a1a3e')
            self.ax1.set_xticks([])
            self.canvas1.draw()
            return

        title = "📊 Продуктивность по дням"
        if self.show_cumulative.get():
            title += " (накопленный итог)"
        
        self.ax1.set_title(title, color='white', fontsize=14, fontweight='bold', pad=15)
        self.ax1.set_xlabel("Дата", color='#888', fontsize=11)
        self.ax1.set_ylabel("Значение", color='#888', fontsize=11)
        self.ax1.tick_params(colors='#888', labelsize=9)
        self.ax1.grid(True, color='#2a2a40', linestyle='--', alpha=0.5, axis='y')
        self.ax1.set_facecolor('#1a1a3e')
        
        self.ax1.spines['top'].set_visible(False)
        self.ax1.spines['right'].set_visible(False)
        self.ax1.spines['left'].set_color('#2a2a40')
        self.ax1.spines['bottom'].set_color('#2a2a40')
        
        self.ax1.set_xticks(x)
        self.ax1.set_xticklabels(dates, rotation=45, ha='right', color='#888', fontsize=8)

        legend = self.ax1.legend(loc='upper left', facecolor='#1a1a3e', 
                                 labelcolor='white', edgecolor='#2a2a40', 
                                 fontsize=10, framealpha=0.9)
        legend.get_frame().set_linewidth(0)

        self.ax1.relim()
        self.ax1.autoscale_view()
        self.fig1.tight_layout()
        self.canvas1.draw()

    # ============================================================
    # ВКЛАДКА 2: ДИАГРАММА ГАНТА
    # ============================================================
    def _build_gantt_tab(self):
        self.fig2 = Figure(figsize=(10, 6), dpi=100, facecolor="#0f0f23")
        self.ax2 = self.fig2.add_subplot(111)
        self.ax2.set_facecolor("#1a1a3e")
        
        self.canvas2 = FigureCanvasTkAgg(self.fig2, master=self.tab2)
        self.canvas2.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.canvas2.mpl_connect('motion_notify_event', self._on_gantt_hover)
        self.canvas2.mpl_connect('axes_leave_event', self._clear_gantt_annotation)

        self._gantt_annotation = None
        self._update_gantt_chart()

    def _on_gantt_hover(self, event):
        if event.inaxes != self.ax2:
            self._clear_gantt_annotation()
            return
        
        if event.xdata is None or event.ydata is None:
            self._clear_gantt_annotation()
            return
        
        if not hasattr(self, '_gantt_data'):
            return
        
        y_idx = int(round(event.ydata)) - 1
        if 0 <= y_idx < len(self._gantt_dates):
            date = self._gantt_dates[y_idx]
            sessions = self._gantt_data.get(date, [])
            
            for sess in sessions:
                start = sess['start_minutes']
                end = sess['end_minutes']
                if start <= event.xdata <= end:
                    text = (
                        f"📅 {date}\n"
                        f"⏱ {sess['start_str']} - {sess['end_str']}\n"
                        f"📌 Точки: {sess['points']}\n"
                        f"💰 Заработок: {sess['points'] * self.point_price:.2f} руб."
                    )
                    self._show_gantt_annotation(event, text)
                    return
        
        self._clear_gantt_annotation()

    def _show_gantt_annotation(self, event, text):
        if self._gantt_annotation:
            self._gantt_annotation.remove()
            self._gantt_annotation = None
        
        self._gantt_annotation = self.ax2.annotate(
            text,
            xy=(event.xdata, event.ydata),
            xytext=(10, -30),
            textcoords='offset points',
            bbox=dict(boxstyle='round,pad=0.5', facecolor='#1a1a3e', edgecolor='#4ecdc4', alpha=0.95),
            color='white',
            fontsize=9,
            ha='left',
            va='top'
        )
        self.fig2.canvas.draw_idle()

    def _clear_gantt_annotation(self, event=None):
        if self._gantt_annotation:
            self._gantt_annotation.remove()
            self._gantt_annotation = None
            self.fig2.canvas.draw_idle()

    def _update_gantt_chart(self):
        self.ax2.clear()
        self._gantt_annotation = None

        if not self.sessions:
            self.ax2.text(0.5, 0.5, "Нет данных о сессиях", 
                          ha='center', va='center', color='#888', fontsize=14, fontweight='bold')
            self.ax2.set_facecolor('#1a1a3e')
            self.canvas2.draw()
            return

        days_data = {}
        for sess in self.sessions:
            day = time.strftime("%Y-%m-%d", time.localtime(sess.started_at))
            if day not in days_data:
                days_data[day] = []
            days_data[day].append(sess)

        sorted_days = sorted(days_data.keys())
        num_days = len(sorted_days)
        colors = ['#00d4aa', '#4ecdc4', '#45b7d1', '#96ceb4', '#ffd166', '#ff6b6b', '#a29bfe']

        self._gantt_data = {}
        self._gantt_dates = sorted_days

        for day_idx, day in enumerate(sorted_days):
            sessions_in_day = sorted(days_data[day], key=lambda s: s.started_at)
            
            for sess_idx, sess in enumerate(sessions_in_day):
                start_local = time.localtime(sess.started_at)
                end_local = time.localtime(sess.ended_at)
                
                start_minutes = start_local.tm_hour * 60 + start_local.tm_min
                end_minutes = end_local.tm_hour * 60 + end_local.tm_min
                
                if end_minutes < start_minutes:
                    end_minutes += 24 * 60
                
                duration = end_minutes - start_minutes
                if duration <= 0:
                    duration = 1
                
                y_pos = day_idx + 1
                color = colors[sess_idx % len(colors)]
                
                self.ax2.barh(y_pos, duration, left=start_minutes, height=0.6,
                              color=color, alpha=0.8, edgecolor=color, linewidth=0.5)
                
                if day not in self._gantt_data:
                    self._gantt_data[day] = []
                self._gantt_data[day].append({
                    'start_minutes': start_minutes,
                    'end_minutes': end_minutes,
                    'start_str': f"{start_local.tm_hour:02d}:{start_local.tm_min:02d}",
                    'end_str': f"{end_local.tm_hour:02d}:{end_local.tm_min:02d}",
                    'points': sess.points,
                })
                
                if duration > 15:
                    self.ax2.text(start_minutes + duration/2, y_pos,
                                f"{sess.points} pts",
                                ha='center', va='center',
                                color='white', fontsize=8, fontweight='bold')

        self.ax2.set_xlabel("Время дня", color='#888', fontsize=11)
        self.ax2.set_ylabel("Дата", color='#888', fontsize=11)
        self.ax2.set_title("📅 Сессии по дням (диаграмма Ганта)", color='white', fontsize=14, fontweight='bold', pad=15)
        self.ax2.tick_params(colors='#888', labelsize=9)
        self.ax2.grid(True, color='#2a2a40', linestyle='--', alpha=0.5, axis='x')
        self.ax2.set_facecolor('#1a1a3e')
        self.ax2.set_xlim(0, 24 * 60)
        
        self.ax2.spines['top'].set_visible(False)
        self.ax2.spines['right'].set_visible(False)
        self.ax2.spines['left'].set_color('#2a2a40')
        self.ax2.spines['bottom'].set_color('#2a2a40')
        
        hour_ticks = list(range(0, 24 * 60 + 1, 2 * 60))
        hour_labels = [f"{h // 60:02d}:00" for h in hour_ticks]
        self.ax2.set_xticks(hour_ticks)
        self.ax2.set_xticklabels(hour_labels, color='#888', fontsize=8)

        self.ax2.set_yticks(range(1, num_days + 1))
        self.ax2.set_yticklabels(sorted_days, color='#888', fontsize=8)
        self.ax2.invert_yaxis()

        legend_elements = [Patch(facecolor='#00d4aa', alpha=0.8, label='Сессия', edgecolor='#00d4aa')]
        legend = self.ax2.legend(handles=legend_elements, loc='upper right',
                                 facecolor='#1a1a3e', labelcolor='white', 
                                 edgecolor='#2a2a40', fontsize=10, framealpha=0.9)
        legend.get_frame().set_linewidth(0)

        self.fig2.tight_layout()
        self.canvas2.draw()

    # ============================================================
    # ВКЛАДКА 3: СКОРОСТЬ И ТРЕНД
    # ============================================================
    def _build_speed_tab(self):
        self.fig3 = Figure(figsize=(10, 6), dpi=100, facecolor="#0f0f23")
        self.ax3 = self.fig3.add_subplot(111)
        self.ax3.set_facecolor("#1a1a3e")
        
        self.canvas3 = FigureCanvasTkAgg(self.fig3, master=self.tab3)
        self.canvas3.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.canvas3.mpl_connect('motion_notify_event', self._on_speed_hover)
        self.canvas3.mpl_connect('axes_leave_event', self._clear_speed_annotation)

        self._speed_annotation = None
        self._update_speed_chart()

    def _on_speed_hover(self, event):
        if event.inaxes != self.ax3:
            self._clear_speed_annotation()
            return
        
        if event.xdata is None:
            self._clear_speed_annotation()
            return
        
        if not hasattr(self, '_speed_data') or not self._speed_data:
            return
        
        idx = int(round(event.xdata))
        if 0 <= idx < len(self._speed_data):
            if abs(event.xdata - idx) < 0.5:
                date = self._speed_dates[idx]
                speed = self._speed_data[idx]
                text = f"📅 {date}\n⚡ Скорость: {speed:.1f} точ/ч"
                self._show_speed_annotation(event, text)
                return
        
        self._clear_speed_annotation()

    def _show_speed_annotation(self, event, text):
        if self._speed_annotation:
            self._speed_annotation.remove()
            self._speed_annotation = None
        
        self._speed_annotation = self.ax3.annotate(
            text,
            xy=(event.xdata, event.ydata),
            xytext=(10, -30),
            textcoords='offset points',
            bbox=dict(boxstyle='round,pad=0.5', facecolor='#1a1a3e', edgecolor='#ffd166', alpha=0.95),
            color='white',
            fontsize=9,
            ha='left',
            va='top'
        )
        self.fig3.canvas.draw_idle()

    def _clear_speed_annotation(self, event=None):
        if self._speed_annotation:
            self._speed_annotation.remove()
            self._speed_annotation = None
            self.fig3.canvas.draw_idle()

    def _update_speed_chart(self):
        self.ax3.clear()
        self._speed_annotation = None

        if not self.speed_data:
            self.ax3.text(0.5, 0.5, "Нет данных о скорости", 
                          ha='center', va='center', color='#888', fontsize=14, fontweight='bold')
            self.ax3.set_facecolor('#1a1a3e')
            self.canvas3.draw()
            return

        dates = sorted(self.speed_data.keys())
        speeds = [self.speed_data[d] for d in dates]
        x = list(range(len(dates)))

        self._speed_data = speeds
        self._speed_dates = dates

        self.ax3.plot(x, speeds, marker='o', linestyle='-', 
                      color='#00d4aa', linewidth=2.5, markersize=8,
                      label='Скорость (точ/ч)', alpha=0.9)
        
        self.ax3.fill_between(x, 0, speeds, color='#00d4aa', alpha=0.15)

        if len(speeds) >= 2:
            coeffs = np.polyfit(x, speeds, 1)
            trend_line = np.polyval(coeffs, x)
            self.ax3.plot(x, trend_line, '--', color='#ff6b6b', linewidth=2.5, 
                         label=f'Тренд: {coeffs[0]:.1f} точ/ч за день')

            if coeffs[0] > 0.5:
                trend_text = "📈 Рост продуктивности!"
                trend_color = '#4ecdc4'
            elif coeffs[0] < -0.5:
                trend_text = "📉 Спад продуктивности"
                trend_color = '#ff6b6b'
            else:
                trend_text = "➡️ Стабильная продуктивность"
                trend_color = '#ffd166'
            
            self.ax3.text(0.02, 0.95, trend_text, transform=self.ax3.transAxes,
                         fontsize=12, fontweight='bold', color=trend_color,
                         bbox=dict(boxstyle='round,pad=0.3', facecolor='#1a1a3e', edgecolor=trend_color, alpha=0.8))

        for i, speed in enumerate(speeds):
            self.ax3.text(x[i], speed + max(speeds) * 0.03, f"{speed:.0f}", 
                         ha='center', va='bottom', color='#888', fontsize=9, fontweight='bold')

        self.ax3.set_xlabel("Дата", color='#888', fontsize=11)
        self.ax3.set_ylabel("Скорость (точек в час)", color='#888', fontsize=11)
        self.ax3.set_title("⚡ Динамика скорости и тренд продуктивности", color='white', fontsize=14, fontweight='bold', pad=15)
        self.ax3.tick_params(colors='#888', labelsize=9)
        self.ax3.grid(True, color='#2a2a40', linestyle='--', alpha=0.5)
        self.ax3.set_facecolor('#1a1a3e')
        
        self.ax3.spines['top'].set_visible(False)
        self.ax3.spines['right'].set_visible(False)
        self.ax3.spines['left'].set_color('#2a2a40')
        self.ax3.spines['bottom'].set_color('#2a2a40')

        self.ax3.set_xticks(x)
        self.ax3.set_xticklabels(dates, rotation=45, ha='right', color='#888', fontsize=8)

        avg_speed = sum(speeds) / len(speeds)
        self.ax3.axhline(y=avg_speed, color='#a29bfe', linestyle=':', linewidth=2,
                        alpha=0.7, label=f'Средняя: {avg_speed:.0f} точ/ч')

        legend = self.ax3.legend(loc='upper left', facecolor='#1a1a3e', 
                                 labelcolor='white', edgecolor='#2a2a40', 
                                 fontsize=10, framealpha=0.9)
        legend.get_frame().set_linewidth(0)

        self.fig3.tight_layout()
        self.canvas3.draw()