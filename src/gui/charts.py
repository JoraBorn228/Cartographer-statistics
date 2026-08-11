"""
Построение настраиваемых графиков продуктивности (Tkinter).
Добавлены: Динамика скорости + Тренд продуктивности (линия регрессии).
"""
import time
import tkinter as tk
from tkinter import ttk
from typing import List, Dict
import matplotlib
import numpy as np

import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'DejaVu Sans', 'Microsoft YaHei', 'SimHei']
plt.rcParams['axes.unicode_minus'] = False
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
from matplotlib.patches import Patch

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
        self.window.geometry("1100x900")
        self.window.configure(bg="#1a1a2e")
        self.window.attributes("-topmost", True)

        # Создаём вкладки
        self.notebook = ttk.Notebook(self.window)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=(10, 5))

        # Вкладка 1: Продуктивность по дням
        self.tab1 = tk.Frame(self.notebook, bg="#1a1a2e")
        self.notebook.add(self.tab1, text="📊 Продуктивность")
        
        # Вкладка 2: Диаграмма Ганта (сессии по дням)
        self.tab2 = tk.Frame(self.notebook, bg="#1a1a2e")
        self.notebook.add(self.tab2, text="📅 Сессии по дням")

        # Вкладка 3: Скорость и тренд
        self.tab3 = tk.Frame(self.notebook, bg="#1a1a2e")
        self.notebook.add(self.tab3, text="⚡ Скорость и тренд")

        # --- Вкладка 1: Продуктивность ---
        self._build_productivity_tab()
        
        # --- Вкладка 2: Диаграмма Ганта ---
        self._build_gantt_tab()
        
        # --- Вкладка 3: Скорость и тренд ---
        self._build_speed_tab()

    # ---------- Агрегация данных по дням ----------
    def _aggregate_daily_data(self) -> Dict[str, Dict]:
        daily = {}
        for sess in self.sessions:
            day = time.strftime("%Y-%m-%d", time.localtime(sess.started_at))
            if day not in daily:
                daily[day] = {'points': 0, 'money': 0.0, 'hours': 0.0}
            daily[day]['points'] += sess.points
            daily[day]['money'] += sess.points * self.point_price
            daily[day]['hours'] += get_productive_tab_time(sess.tab_times) / 3600.0

        if self.logic.session_active and self.logic.session_points > 0:
            today = time.strftime("%Y-%m-%d")
            if today not in daily:
                daily[today] = {'points': 0, 'money': 0.0, 'hours': 0.0}
            daily[today]['points'] += self.logic.session_points
            daily[today]['money'] += self.logic.session_points * self.point_price

        return daily

    # ---------- Расчёт скорости по дням ----------
    def _calculate_speed_by_day(self) -> Dict[str, float]:
        speed_data = {}
        
        for sess in self.sessions:
            day = time.strftime("%Y-%m-%d", time.localtime(sess.started_at))
            prod_time = get_productive_tab_time(sess.tab_times)
            
            if prod_time > 60:  # минимум 1 минута продуктивного времени
                speed = sess.points / (prod_time / 3600)  # точек в час
                if day not in speed_data:
                    speed_data[day] = {'total_points': 0, 'total_time': 0}
                speed_data[day]['total_points'] += sess.points
                speed_data[day]['total_time'] += prod_time
        
        # Вычисляем среднюю скорость за день
        result = {}
        for day, data in speed_data.items():
            if data['total_time'] > 0:
                result[day] = data['total_points'] / (data['total_time'] / 3600)
        
        return result

    # ---------- Вкладка 1: Продуктивность ----------
    def _build_productivity_tab(self):
        settings_frame = tk.Frame(self.tab1, bg="#1a1a2e")
        settings_frame.pack(fill=tk.X, padx=20, pady=(10, 10))

        self.show_points = tk.BooleanVar(value=True)
        self.show_money = tk.BooleanVar(value=True)
        self.show_hours = tk.BooleanVar(value=True)
        self.show_cumulative = tk.BooleanVar(value=False)

        tk.Checkbutton(
            settings_frame,
            text="📌 Точки",
            variable=self.show_points,
            command=self._update_productivity_chart,
            bg="#1a1a2e",
            fg="white",
            selectcolor="#1a1a2e",
            activebackground="#1a1a2e",
            activeforeground="white"
        ).pack(side=tk.LEFT, padx=(0, 15))

        tk.Checkbutton(
            settings_frame,
            text="💰 Заработок (руб.)",
            variable=self.show_money,
            command=self._update_productivity_chart,
            bg="#1a1a2e",
            fg="white",
            selectcolor="#1a1a2e",
            activebackground="#1a1a2e",
            activeforeground="white"
        ).pack(side=tk.LEFT, padx=(0, 15))

        tk.Checkbutton(
            settings_frame,
            text="⏱ Время работы (ч)",
            variable=self.show_hours,
            command=self._update_productivity_chart,
            bg="#1a1a2e",
            fg="white",
            selectcolor="#1a1a2e",
            activebackground="#1a1a2e",
            activeforeground="white"
        ).pack(side=tk.LEFT, padx=(0, 15))

        tk.Checkbutton(
            settings_frame,
            text="📈 Накопленный итог",
            variable=self.show_cumulative,
            command=self._update_productivity_chart,
            bg="#1a1a2e",
            fg="white",
            selectcolor="#1a1a2e",
            activebackground="#1a1a2e",
            activeforeground="white"
        ).pack(side=tk.LEFT)

        self.fig1 = Figure(figsize=(8, 5), dpi=100, facecolor="#1a1a2e")
        self.ax1 = self.fig1.add_subplot(111)
        self.canvas1 = FigureCanvasTkAgg(self.fig1, master=self.tab1)
        toolbar1 = NavigationToolbar2Tk(self.canvas1, self.tab1)
        toolbar1.update()
        toolbar1.pack(side=tk.TOP, fill=tk.X)
        self.canvas1.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        self._update_productivity_chart()

    def _update_productivity_chart(self):
        self.ax1.clear()

        if not self.daily_data:
            self.ax1.text(0.5, 0.5, "Нет данных для отображения", 
                          ha='center', va='center', color='white', fontsize=14)
            self.ax1.set_facecolor('#1a1a2e')
            self.canvas1.draw()
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

        plotted = False

        if self.show_points.get():
            self.ax1.bar([i - width for i in x], points_vals, width, 
                         color=colors['points'], label=labels['points'], alpha=0.85)
            plotted = True
        if self.show_money.get():
            self.ax1.bar(x, money_vals, width, 
                         color=colors['money'], label=labels['money'], alpha=0.85)
            plotted = True
        if self.show_hours.get():
            self.ax1.bar([i + width for i in x], hours_vals, width, 
                         color=colors['hours'], label=labels['hours'], alpha=0.85)
            plotted = True

        if not plotted:
            self.ax1.text(0.5, 0.5, "Выберите хотя бы одну метрику", 
                          ha='center', va='center', color='white', fontsize=14)
            self.ax1.set_facecolor('#1a1a2e')
            self.ax1.set_xticks([])
            self.canvas1.draw()
            return

        title = "Продуктивность по дням"
        if self.show_cumulative.get():
            title += " (накопленный итог)"
        
        self.ax1.set_title(title, color='white', fontsize=14)
        self.ax1.set_xlabel("Дата", color='white')
        self.ax1.set_ylabel("Значение", color='white')
        self.ax1.tick_params(colors='white')
        self.ax1.grid(True, color='#2a2a40', linestyle='--', axis='y')
        self.ax1.set_facecolor('#1a1a2e')
        self.ax1.set_xticks(x)
        self.ax1.set_xticklabels(dates, rotation=45, ha='right', color='white')
        self.ax1.legend(loc='upper left', facecolor='#1a1a2e', labelcolor='white', edgecolor='#2a2a40')

        self.ax1.relim()
        self.ax1.autoscale_view()
        self.canvas1.draw()

    # ---------- Вкладка 2: Диаграмма Ганта ----------
    def _build_gantt_tab(self):
        self.fig2 = Figure(figsize=(9, 6), dpi=100, facecolor="#1a1a2e")
        self.ax2 = self.fig2.add_subplot(111)
        self.canvas2 = FigureCanvasTkAgg(self.fig2, master=self.tab2)
        toolbar2 = NavigationToolbar2Tk(self.canvas2, self.tab2)
        toolbar2.update()
        toolbar2.pack(side=tk.TOP, fill=tk.X)
        self.canvas2.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        self._update_gantt_chart()

    def _update_gantt_chart(self):
        self.ax2.clear()

        if not self.sessions:
            self.ax2.text(0.5, 0.5, "Нет данных о сессиях", 
                          ha='center', va='center', color='white', fontsize=14)
            self.ax2.set_facecolor('#1a1a2e')
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
                
                self.ax2.barh(y_pos, duration, left=start_minutes, height=0.7,
                              color=color, alpha=0.8, edgecolor=color, linewidth=1)
                
                if duration > 20:
                    self.ax2.text(start_minutes + duration/2, y_pos,
                                f"{sess.points} pts",
                                ha='center', va='center',
                                color='white', fontsize=8, fontweight='bold')

        self.ax2.set_xlabel("Время дня", color='white', fontsize=12)
        self.ax2.set_ylabel("Дата", color='white', fontsize=12)
        self.ax2.set_title("Сессии по дням (диаграмма Ганта)", color='white', fontsize=14)
        self.ax2.tick_params(colors='white')
        self.ax2.grid(True, color='#2a2a40', linestyle='--', alpha=0.5, axis='x')
        self.ax2.set_facecolor('#1a1a2e')
        self.ax2.set_xlim(0, 24 * 60)
        
        hour_ticks = list(range(0, 24 * 60 + 1, 2 * 60))
        hour_labels = [f"{h // 60:02d}:00" for h in hour_ticks]
        self.ax2.set_xticks(hour_ticks)
        self.ax2.set_xticklabels(hour_labels, color='white')

        self.ax2.set_yticks(range(1, num_days + 1))
        self.ax2.set_yticklabels(sorted_days, color='white', fontsize=9)
        self.ax2.invert_yaxis()

        legend_elements = [Patch(facecolor='#00d4aa', alpha=0.8, label='Сессия')]
        self.ax2.legend(handles=legend_elements, loc='upper right',
                        facecolor='#1a1a2e', labelcolor='white', edgecolor='#2a2a40')

        self.fig2.tight_layout()
        self.canvas2.draw()

    # ---------- Вкладка 3: Скорость и тренд ----------
    def _build_speed_tab(self):
        self.fig3 = Figure(figsize=(9, 6), dpi=100, facecolor="#1a1a2e")
        self.ax3 = self.fig3.add_subplot(111)
        self.canvas3 = FigureCanvasTkAgg(self.fig3, master=self.tab3)
        toolbar3 = NavigationToolbar2Tk(self.canvas3, self.tab3)
        toolbar3.update()
        toolbar3.pack(side=tk.TOP, fill=tk.X)
        self.canvas3.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        self._update_speed_chart()

    def _update_speed_chart(self):
        self.ax3.clear()

        if not self.speed_data:
            self.ax3.text(0.5, 0.5, "Нет данных о скорости", 
                          ha='center', va='center', color='white', fontsize=14)
            self.ax3.set_facecolor('#1a1a2e')
            self.canvas3.draw()
            return

        # Сортируем по дате
        dates = sorted(self.speed_data.keys())
        speeds = [self.speed_data[d] for d in dates]
        x = list(range(len(dates)))

        # 1. Линейный график скорости
        self.ax3.plot(x, speeds, marker='o', linestyle='-', 
                      color='#00d4aa', linewidth=2, markersize=8,
                      label='Скорость (точ/ч)', alpha=0.8)

        # 2. Заполнение под графиком
        self.ax3.fill_between(x, 0, speeds, color='#00d4aa', alpha=0.15)

        # 3. Линия регрессии (тренд)
        if len(speeds) >= 2:
            # Линейная регрессия через numpy
            coeffs = np.polyfit(x, speeds, 1)
            trend_line = np.polyval(coeffs, x)
            self.ax3.plot(x, trend_line, '--', color='#ff6b6b', linewidth=2, 
                         label=f'Тренд: {coeffs[0]:.1f} точ/ч за день')

            # Если тренд положительный или отрицательный
            if coeffs[0] > 0.1:
                trend_text = "📈 Рост продуктивности!"
                trend_color = '#4ecdc4'
            elif coeffs[0] < -0.1:
                trend_text = "📉 Спад продуктивности"
                trend_color = '#ff6b6b'
            else:
                trend_text = "➡️ Стабильная продуктивность"
                trend_color = '#ffd166'
            
            # Добавляем текст с трендом
            self.ax3.text(0.02, 0.95, trend_text, transform=self.ax3.transAxes,
                         fontsize=12, fontweight='bold', color=trend_color)

        # Значения над точками
        for i, speed in enumerate(speeds):
            self.ax3.text(x[i], speed + 5, f"{speed:.0f}", 
                         ha='center', va='bottom', color='white', fontsize=9)

        # Настройки осей
        self.ax3.set_xlabel("Дата", color='white', fontsize=12)
        self.ax3.set_ylabel("Скорость (точек в час)", color='white', fontsize=12)
        self.ax3.set_title("Динамика скорости и тренд продуктивности", color='white', fontsize=14)
        self.ax3.tick_params(colors='white')
        self.ax3.grid(True, color='#2a2a40', linestyle='--', alpha=0.5)
        self.ax3.set_facecolor('#1a1a2e')

        # Подписи оси X — даты
        self.ax3.set_xticks(x)
        self.ax3.set_xticklabels(dates, rotation=45, ha='right', color='white')

        # Легенда
        self.ax3.legend(loc='upper left', facecolor='#1a1a2e', 
                        labelcolor='white', edgecolor='#2a2a40')

        # Добавляем среднюю скорость
        avg_speed = sum(speeds) / len(speeds)
        self.ax3.axhline(y=avg_speed, color='#a29bfe', linestyle=':', linewidth=1.5,
                        alpha=0.7, label=f'Средняя: {avg_speed:.0f} точ/ч')
        self.ax3.legend(loc='upper left', facecolor='#1a1a2e', 
                        labelcolor='white', edgecolor='#2a2a40')

        self.fig3.tight_layout()
        self.canvas3.draw()