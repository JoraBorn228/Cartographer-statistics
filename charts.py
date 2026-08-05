"""
Построение настраиваемых графиков продуктивности.
"""
import time
import tkinter as tk
from tkinter import ttk
from typing import List, Dict

import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from models import Session
from utils import get_productive_tab_time


class ChartsWindow:
    def __init__(self, parent, sessions: List[Session], points: int, current_points_today: int, hours_data: Dict[int, Dict], point_price: float):
        self.sessions = sessions
        self.points = points
        self.current_points_today = current_points_today
        self.hours_data = hours_data
        self.point_price = point_price

        self.daily_data = self._aggregate_daily_data()

        self.window = tk.Toplevel(parent)
        self.window.title("📊 Графики продуктивности")
        self.window.geometry("900x750")
        self.window.configure(bg="#1a1a2e")
        self.window.attributes("-topmost", True)

        tk.Label(
            self.window,
            text="Настройка отображения графиков",
            font=("Segoe UI", 12, "bold"),
            fg="#00d4aa",
            bg="#1a1a2e"
        ).pack(pady=(10, 5))

        self.settings_frame = tk.Frame(self.window, bg="#1a1a2e")
        self.settings_frame.pack(fill=tk.X, padx=20, pady=(0, 10))

        self.show_points = tk.BooleanVar(value=True)
        self.show_money = tk.BooleanVar(value=True)
        self.show_hours = tk.BooleanVar(value=True)
        self.show_cumulative = tk.BooleanVar(value=False)

        tk.Checkbutton(
            self.settings_frame,
            text="📌 Точки",
            variable=self.show_points,
            command=self._update_chart,
            bg="#1a1a2e",
            fg="white",
            selectcolor="#1a1a2e",
            activebackground="#1a1a2e",
            activeforeground="white"
        ).pack(side=tk.LEFT, padx=(0, 15))

        tk.Checkbutton(
            self.settings_frame,
            text="💰 Заработок (руб.)",
            variable=self.show_money,
            command=self._update_chart,
            bg="#1a1a2e",
            fg="white",
            selectcolor="#1a1a2e",
            activebackground="#1a1a2e",
            activeforeground="white"
        ).pack(side=tk.LEFT, padx=(0, 15))

        tk.Checkbutton(
            self.settings_frame,
            text="⏱ Время работы (ч)",
            variable=self.show_hours,
            command=self._update_chart,
            bg="#1a1a2e",
            fg="white",
            selectcolor="#1a1a2e",
            activebackground="#1a1a2e",
            activeforeground="white"
        ).pack(side=tk.LEFT, padx=(0, 15))

        tk.Checkbutton(
            self.settings_frame,
            text="📈 Накопленный итог",
            variable=self.show_cumulative,
            command=self._update_chart,
            bg="#1a1a2e",
            fg="white",
            selectcolor="#1a1a2e",
            activebackground="#1a1a2e",
            activeforeground="white"
        ).pack(side=tk.LEFT)

        btn_frame = tk.Frame(self.window, bg="#1a1a2e")
        btn_frame.pack(pady=5)
        tk.Button(
            btn_frame,
            text="Закрыть",
            command=self.window.destroy,
            bg="#2a2a40",
            fg="#eaeaea",
            activebackground="#3d3d6b",
            relief=tk.FLAT,
            padx=10,
            pady=5,
            cursor="hand2"
        ).pack()

        self.fig = Figure(figsize=(8, 5), dpi=100, facecolor="#1a1a2e")
        self.ax = self.fig.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.window)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        self._update_chart()

    # ---------- Агрегация ----------
    def _aggregate_daily_data(self) -> Dict[str, Dict]:
        daily = {}
        today = time.strftime("%Y-%m-%d")

        for sess in self.sessions:
            day = time.strftime("%Y-%m-%d", time.localtime(sess.started_at))
            if day not in daily:
                daily[day] = {'points': 0, 'money': 0.0, 'hours': 0.0}
            daily[day]['points'] += sess.points
            daily[day]['money'] += sess.points * self.point_price
            daily[day]['hours'] += get_productive_tab_time(sess.tab_times) / 3600.0

        if self.current_points_today > 0:
            if today not in daily:
                daily[today] = {'points': 0, 'money': 0.0, 'hours': 0.0}
            daily[today]['points'] += self.current_points_today
            daily[today]['money'] += self.current_points_today * self.point_price

        return daily

    # ---------- Обновление ----------
    def _update_chart(self):
        self.ax.clear()

        if not self.daily_data:
            self.ax.text(0.5, 0.5, "Нет данных для отображения", 
                         ha='center', va='center', color='white', fontsize=14)
            self.ax.set_facecolor('#1a1a2e')
            self.canvas.draw()
            return

        dates = sorted(self.daily_data.keys())
        x = list(range(len(dates)))

        points_vals = [self.daily_data[d]['points'] for d in dates]
        money_vals = [self.daily_data[d]['money'] for d in dates]
        hours_vals = [self.daily_data[d]['hours'] for d in dates]

        if self.show_cumulative.get():
            cum_points = []
            cum_money = []
            cum_hours = []
            p = m = h = 0
            for i in range(len(dates)):
                p += points_vals[i]
                m += money_vals[i]
                h += hours_vals[i]
                cum_points.append(p)
                cum_money.append(m)
                cum_hours.append(h)
            points_vals = cum_points
            money_vals = cum_money
            hours_vals = cum_hours

        width = 0.25
        colors = {'points': '#00d4aa', 'money': '#ffd700', 'hours': '#ff6b6b'}
        labels = {'points': 'Точки', 'money': 'Заработок (руб.)', 'hours': 'Время (ч)'}

        plotted = []
        if self.show_points.get():
            self.ax.bar([i - width for i in x], points_vals, width, color=colors['points'], label=labels['points'], alpha=0.8)
            plotted.append('points')
        if self.show_money.get():
            self.ax.bar(x, money_vals, width, color=colors['money'], label=labels['money'], alpha=0.8)
            plotted.append('money')
        if self.show_hours.get():
            self.ax.bar([i + width for i in x], hours_vals, width, color=colors['hours'], label=labels['hours'], alpha=0.8)
            plotted.append('hours')

        if not plotted:
            self.ax.text(0.5, 0.5, "Выберите хотя бы одну метрику", 
                         ha='center', va='center', color='white', fontsize=14)
            self.ax.set_facecolor('#1a1a2e')
            self.ax.set_xticks([])
            self.canvas.draw()
            return

        self.ax.set_title("Продуктивность по дням" + (" (накопленный итог)" if self.show_cumulative.get() else ""), 
                          color='white', fontsize=14)
        self.ax.set_xlabel("Дата", color='white')
        self.ax.set_ylabel("Значение", color='white')
        self.ax.tick_params(colors='white')
        self.ax.grid(True, color='#2a2a40', linestyle='--', axis='y')
        self.ax.set_facecolor('#1a1a2e')

        self.ax.set_xticks(x)
        self.ax.set_xticklabels(dates, rotation=45, ha='right', color='white')

        self.ax.legend(loc='upper left', facecolor='#1a1a2e', labelcolor='white', edgecolor='#2a2a40')

        self.ax.relim()
        self.ax.autoscale_view()

        self.canvas.draw()