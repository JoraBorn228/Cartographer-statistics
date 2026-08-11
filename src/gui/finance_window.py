"""
Окно финансового учёта.
"""
import tkinter as tk
from tkinter import ttk, messagebox
import time
from datetime import datetime
from typing import List, Dict, Optional

from src.core.models import Session
from src.core.storage import save_progress
from src.utils.helpers import get_productive_tab_time, format_duration



class FinanceWindow:
    def __init__(self, parent, logic):
        self.parent = parent
        self.logic = logic
        self.tax_rate = 0.13  # 13%
        
        # Загружаем сохранённые реальные заработки
        self.real_earnings: Dict[str, float] = self._load_real_earnings()
        
        self.window = tk.Toplevel(parent)
        self.window.title("💰 Финансовый учёт")
        self.window.geometry("1150x800")
        self.window.minsize(900, 700)
        self.window.configure(bg="#0f0f23")
        self.window.attributes("-topmost", True)
        
        self._build_ui()
        self._update_table()
    
    def _load_real_earnings(self) -> Dict[str, float]:
        if hasattr(self.logic, 'real_earnings'):
            return self.logic.real_earnings
        return {}
    
    def _save_real_earnings(self):
        self.logic.real_earnings = self.real_earnings
    
    def _save_to_file(self):
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
        )
    
    def _build_ui(self):
        # Заголовок
        header = tk.Frame(self.window, bg="#0f0f23")
        header.pack(fill=tk.X, padx=20, pady=(10, 5))
        
        tk.Label(
            header,
            text="💰 Финансовый учёт",
            font=("Segoe UI", 18, "bold"),
            fg="#00d4aa",
            bg="#0f0f23"
        ).pack(side=tk.LEFT)
        
        tk.Label(
            header,
            text=f"Налог: {self.tax_rate*100:.0f}%",
            font=("Segoe UI", 10),
            fg="#888",
            bg="#0f0f23"
        ).pack(side=tk.RIGHT)
        
        # --- Верхняя панель с основной статистикой ---
        self._build_main_stats()
        
        # --- Дополнительная панель (дни, точки, время, цена, доход в час) ---
        self._build_extra_stats()
        
        # --- Основной фрейм с таблицей ---
        main_frame = tk.Frame(self.window, bg="#0f0f23")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Создаём таблицу с сеткой
        columns = ("date", "points", "time", "approx", "real", "real_after_tax", "diff", "real_price", "status")
        self.tree = ttk.Treeview(
            main_frame,
            columns=columns,
            show="headings",
            height=18
        )
        
        # Настройка колонок
        self.tree.heading("date", text="📅 Дата")
        self.tree.heading("points", text="📌 Точки")
        self.tree.heading("time", text="⏱ Время (ч)")
        self.tree.heading("approx", text="💰 Приблиз.")
        self.tree.heading("real", text="💵 Реальный (до налога)")
        self.tree.heading("real_after_tax", text="💵 Реальный (после налога)")
        self.tree.heading("diff", text="📊 Разница")
        self.tree.heading("real_price", text="💎 Цена за точку")
        self.tree.heading("status", text="Статус")
        
        self.tree.column("date", width=105, anchor="center")
        self.tree.column("points", width=80, anchor="center")
        self.tree.column("time", width=80, anchor="center")
        self.tree.column("approx", width=110, anchor="center")
        self.tree.column("real", width=130, anchor="center")
        self.tree.column("real_after_tax", width=145, anchor="center")
        self.tree.column("diff", width=110, anchor="center")
        self.tree.column("real_price", width=120, anchor="center")
        self.tree.column("status", width=80, anchor="center")
        
        # Стиль таблицы с сеткой
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", 
                       background="#1a1a3e", 
                       foreground="#eaeaea", 
                       fieldbackground="#1a1a3e",
                       font=("Segoe UI", 9),
                       rowheight=28)
        style.configure("Treeview.Heading", 
                       background="#2a2a5e", 
                       foreground="#00d4aa", 
                       font=("Segoe UI", 9, "bold"),
                       relief="flat")
        style.map("Treeview", 
                 background=[('selected', '#00d4aa')],
                 foreground=[('selected', '#0f0f23')])
        
        # Добавляем сетку
        style.configure("Treeview", relief="solid", borderwidth=1)
        style.configure("Treeview.Heading", relief="solid", borderwidth=1)
        style.layout("Treeview", [('Treeview.treearea', {'sticky': 'nswe'})])
        
        # Скроллбар
        scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Привязываем двойной клик для редактирования
        self.tree.bind("<Double-1>", self._on_double_click)
        
        # Подсказка
        tk.Label(
            self.window,
            text="💡 Двойной клик по строке для ввода реального заработка",
            font=("Segoe UI", 9),
            fg="#666",
            bg="#0f0f23",
            anchor=tk.W
        ).pack(fill=tk.X, padx=20, pady=(0, 5))
        
        # --- Нижняя панель с кнопками (закреплена внизу) ---
        bottom_frame = tk.Frame(self.window, bg="#0f0f23")
        bottom_frame.pack(fill=tk.X, padx=20, pady=(0, 10), side=tk.BOTTOM)
        
        btn_frame = tk.Frame(bottom_frame, bg="#0f0f23")
        btn_frame.pack(side=tk.RIGHT)
        
        for btn in [
            ("🔄 Обновить", self._update_table, "#2a2a5e"),
            ("💾 Сохранить", self._save_data, "#00d4aa"),
            ("❌ Закрыть", self.window.destroy, "#2a2a5e")
        ]:
            tk.Button(
                btn_frame,
                text=btn[0],
                command=btn[1],
                bg=btn[2],
                fg="white" if btn[2] != "#00d4aa" else "#0f0f23",
                font=("Segoe UI", 9, "bold"),
                relief=tk.FLAT,
                padx=20,
                pady=8,
                cursor="hand2"
            ).pack(side=tk.LEFT, padx=5)
    
    def _build_main_stats(self):
        """Основная статистика (4 главные карточки)."""
        main_frame = tk.Frame(self.window, bg="#0f0f23")
        main_frame.pack(fill=tk.X, padx=20, pady=(0, 5))
        
        self.main_cards = {}
        
        card_data = [
            ("💰 Приблизительный", "approx", "#2a2a5e"),
            ("💵 Реальный (до налога)", "real", "#2a2a5e"),
            ("💵 Реальный (после налога)", "real_after_tax", "#2a2a5e"),
            ("📊 Общая разница", "diff", "#1a1a5e"),
        ]
        
        for label, key, color in card_data:
            card = tk.Frame(main_frame, bg=color, relief=tk.GROOVE, bd=1, padx=15, pady=8)
            card.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=3)
            
            label_widget = tk.Label(
                card,
                text=label,
                font=("Segoe UI", 9),
                fg="#888",
                bg=color,
                anchor=tk.W
            )
            label_widget.pack(fill=tk.X)
            
            value_widget = tk.Label(
                card,
                text="—",
                font=("Segoe UI", 18, "bold"),
                fg="#eaeaea",
                bg=color,
                anchor=tk.W
            )
            value_widget.pack(fill=tk.X)
            
            self.main_cards[key] = value_widget
    
    def _build_extra_stats(self):
        """Дополнительная статистика (дни, точки, время, цена, доход в час)."""
        extra_frame = tk.Frame(self.window, bg="#0f0f23")
        extra_frame.pack(fill=tk.X, padx=20, pady=(0, 10))
        
        self.extra_cards = {}
        
        card_data = [
            ("📊 Дней", "days", "#1a1a3e"),
            ("📌 Точки", "points", "#1a1a3e"),
            ("⏱ Время (ч)", "time", "#1a1a3e"),
            ("💎 Цена за точку", "real_price", "#1a1a3e"),
            ("💰 Доход в час", "hourly_rate", "#1a1a3e"),
        ]
        
        for label, key, color in card_data:
            card = tk.Frame(extra_frame, bg=color, relief=tk.GROOVE, bd=1, padx=10, pady=4)
            card.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=3)
            
            label_widget = tk.Label(
                card,
                text=label,
                font=("Segoe UI", 8),
                fg="#666",
                bg=color,
                anchor=tk.W
            )
            label_widget.pack(fill=tk.X)
            
            value_widget = tk.Label(
                card,
                text="—",
                font=("Segoe UI", 11, "bold"),
                fg="#eaeaea",
                bg=color,
                anchor=tk.W
            )
            value_widget.pack(fill=tk.X)
            
            self.extra_cards[key] = value_widget
    
    def _update_main_cards(self, stats: dict):
        """Обновить основные карточки."""
        for key, value in stats.items():
            if key in self.main_cards:
                if key == "diff":
                    if value > 0:
                        self.main_cards[key].config(text=f"+{value:.2f}", fg="#00d4aa")
                    elif value < 0:
                        self.main_cards[key].config(text=f"{value:.2f}", fg="#ff6b6b")
                    else:
                        self.main_cards[key].config(text=f"{value:.2f}", fg="#eaeaea")
                else:
                    self.main_cards[key].config(text=f"{value:.2f}")
    
    def _update_extra_cards(self, stats: dict):
        """Обновить дополнительные карточки."""
        for key, value in stats.items():
            if key in self.extra_cards:
                if key in ["days", "points"]:
                    self.extra_cards[key].config(text=f"{value:,}".replace(",", " "))
                elif key == "time":
                    self.extra_cards[key].config(text=f"{value:.1f}")
                elif key == "real_price":
                    if value > 0:
                        self.extra_cards[key].config(text=f"{value:.2f}", fg="#ffd700")
                    else:
                        self.extra_cards[key].config(text="—", fg="#eaeaea")
                elif key == "hourly_rate":
                    if value > 0:
                        self.extra_cards[key].config(text=f"{value:.2f} руб/ч", fg="#4ecdc4")
                    else:
                        self.extra_cards[key].config(text="—", fg="#eaeaea")
    
    def _update_table(self):
        """Обновить таблицу данными."""
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        daily_data = self._aggregate_daily_data()
        
        all_days = set(daily_data.keys())
        real_days = set(self.real_earnings.keys())
        all_days = all_days | real_days
        
        total_days = len(real_days)
        total_points = 0
        total_time = 0.0
        total_approx = 0.0
        total_real = 0.0
        total_real_after_tax = 0.0
        total_diff = 0.0
        total_points_for_price = 0
        total_real_after_tax_for_price = 0.0
        total_hourly = 0.0
        days_with_hourly = 0
        
        for day in sorted(all_days, reverse=True):
            data = daily_data.get(day, {'points': 0, 'hours': 0.0, 'approx': 0.0})
            
            points = data['points']
            hours = data['hours']
            approx = data['approx']
            
            real = self.real_earnings.get(day, 0.0)
            real_after_tax = real * (1 - self.tax_rate) if real > 0 else 0.0
            has_real = real > 0
            
            diff = real_after_tax - approx if has_real else 0.0
            real_price = real_after_tax / points if points > 0 and has_real else 0.0
            hourly_rate = real_after_tax / hours if hours > 0 and has_real else 0.0
            
            if has_real:
                total_days = len(real_days)
                total_points += points
                total_time += hours
                total_approx += approx
                total_real += real
                total_real_after_tax += real_after_tax
                total_diff += diff
                if points > 0:
                    total_points_for_price += points
                    total_real_after_tax_for_price += real_after_tax
                if hours > 0:
                    total_hourly += hourly_rate
                    days_with_hourly += 1
            
            points_str = f"{points:,}".replace(",", " ")
            time_str = f"{hours:.1f}"
            approx_str = f"{approx:.2f}"
            real_str = f"{real:.2f}" if has_real else ""
            real_after_tax_str = f"{real_after_tax:.2f}" if has_real else ""
            diff_str = f"{diff:+.2f}" if has_real else ""
            real_price_str = f"{real_price:.2f}" if has_real and real_price > 0 else ""
            status = "✅" if has_real else "⏳"
            
            if has_real and diff > 0:
                diff_str = f"+{diff:.2f}"
            elif has_real and diff < 0:
                diff_str = f"{diff:.2f}"
            
            self.tree.insert(
                "",
                tk.END,
                values=(
                    day, points_str, time_str, approx_str,
                    real_str, real_after_tax_str, diff_str, real_price_str, status
                ),
                tags=('row',)
            )
        
        avg_real_price = total_real_after_tax_for_price / total_points_for_price if total_points_for_price > 0 else 0
        avg_hourly = total_hourly / days_with_hourly if days_with_hourly > 0 else 0
        
        main_stats = {
            'approx': total_approx,
            'real': total_real,
            'real_after_tax': total_real_after_tax,
            'diff': total_diff,
        }
        
        extra_stats = {
            'days': total_days,
            'points': total_points,
            'time': total_time,
            'real_price': avg_real_price,
            'hourly_rate': avg_hourly,
        }
        
        self._update_main_cards(main_stats)
        self._update_extra_cards(extra_stats)
    
    def _aggregate_daily_data(self) -> Dict[str, Dict]:
        """Агрегировать данные по дням."""
        daily = {}
        point_price = self.logic.point_price
        
        for sess in self.logic.sessions:
            day = time.strftime("%Y-%m-%d", time.localtime(sess.started_at))
            if day not in daily:
                daily[day] = {'points': 0, 'hours': 0.0, 'approx': 0.0}
            daily[day]['points'] += sess.points
            daily[day]['hours'] += get_productive_tab_time(sess.tab_times) / 3600.0
        
        if self.logic.session_active and self.logic.session_points > 0:
            today = time.strftime("%Y-%m-%d")
            if today not in daily:
                daily[today] = {'points': 0, 'hours': 0.0, 'approx': 0.0}
            daily[today]['points'] += self.logic.session_points
        
        for day, data in daily.items():
            data['approx'] = data['points'] * point_price
        
        return daily
    
    def _on_double_click(self, event):
        """Обработка двойного клика для редактирования реального заработка."""
        selection = self.tree.selection()
        if not selection:
            return
        
        item = selection[0]
        values = self.tree.item(item, 'values')
        if not values:
            return
        
        date = values[0]
        current_real = self.real_earnings.get(date, 0.0)
        
        dialog = tk.Toplevel(self.window)
        dialog.title(f"Реальный заработок за {date}")
        dialog.geometry("320x160")
        dialog.configure(bg="#0f0f23")
        dialog.attributes("-topmost", True)
        dialog.transient(self.window)
        dialog.grab_set()
        
        tk.Label(
            dialog,
            text=f"Введите реальный заработок за {date} (ДО налога):",
            font=("Segoe UI", 10),
            fg="#eaeaea",
            bg="#0f0f23"
        ).pack(pady=(15, 5))
        
        entry = tk.Entry(dialog, font=("Segoe UI", 14), bg="#1a1a3e", fg="#eaeaea", insertbackground="#eaeaea")
        entry.pack(pady=5, padx=20, fill=tk.X)
        entry.insert(0, str(current_real) if current_real > 0 else "")
        entry.focus()
        entry.select_range(0, tk.END)
        
        def on_ok():
            try:
                value = float(entry.get().replace(",", "."))
                if value < 0:
                    raise ValueError("Заработок не может быть отрицательным")
                self.real_earnings[date] = value
                self._save_real_earnings()
                dialog.destroy()
                self._update_table()
            except ValueError as e:
                messagebox.showerror("Ошибка", str(e), parent=dialog)
        
        def on_cancel():
            dialog.destroy()
        
        btn_frame = tk.Frame(dialog, bg="#0f0f23")
        btn_frame.pack(pady=15)
        
        tk.Button(
            btn_frame,
            text="OK",
            command=on_ok,
            bg="#00d4aa",
            fg="#0f0f23",
            font=("Segoe UI", 10, "bold"),
            relief=tk.FLAT,
            padx=25,
            pady=5,
            cursor="hand2"
        ).pack(side=tk.LEFT, padx=5)
        
        tk.Button(
            btn_frame,
            text="Отмена",
            command=on_cancel,
            bg="#2a2a5e",
            fg="#eaeaea",
            font=("Segoe UI", 10),
            relief=tk.FLAT,
            padx=25,
            pady=5,
            cursor="hand2"
        ).pack(side=tk.LEFT, padx=5)
        
        entry.bind("<Return>", lambda e: on_ok())
        entry.bind("<Escape>", lambda e: on_cancel())
    
    def _save_data(self):
        self._save_real_earnings()
        self._save_to_file()
        self._update_table()
        messagebox.showinfo("Успех", "Данные сохранены!", parent=self.window)