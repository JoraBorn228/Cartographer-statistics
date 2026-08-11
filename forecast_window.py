"""
Окно прогнозов и финансового планирования.
"""
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta
import time

from utils import get_productive_tab_time
from storage import save_progress


class ForecastWindow:
    def __init__(self, parent, logic):
        self.parent = parent
        self.logic = logic
        self.tax_rate = 0.13
        
        # Данные из финансового учёта
        self.real_earnings = getattr(logic, 'real_earnings', {})
        
        self.window = tk.Toplevel(parent)
        self.window.title("📈 Прогнозы")
        self.window.geometry("900x780")
        self.window.minsize(750, 650)
        self.window.configure(bg="#0f0f23")
        self.window.attributes("-topmost", True)
        
        self._build_ui()
        self._update_forecast()
    
    def _build_ui(self):
        # Заголовок
        header = tk.Frame(self.window, bg="#0f0f23")
        header.pack(fill=tk.X, padx=20, pady=(10, 5))
        
        tk.Label(
            header,
            text="📈 Прогнозы и планирование",
            font=("Segoe UI", 18, "bold"),
            fg="#00d4aa",
            bg="#0f0f23"
        ).pack(side=tk.LEFT)
        
        # --- Входные данные ---
        input_frame = tk.Frame(self.window, bg="#1a1a3e", relief=tk.GROOVE, bd=1)
        input_frame.pack(fill=tk.X, padx=20, pady=(0, 15))
        
        # Цель (сумма)
        goal_frame = tk.Frame(input_frame, bg="#1a1a3e")
        goal_frame.pack(fill=tk.X, padx=15, pady=(10, 5))
        
        tk.Label(
            goal_frame,
            text="Желаемая сумма (руб.):",
            font=("Segoe UI", 10),
            fg="#eaeaea",
            bg="#1a1a3e"
        ).pack(side=tk.LEFT, padx=(0, 10))
        
        self.goal_entry = tk.Entry(
            goal_frame,
            font=("Segoe UI", 12),
            bg="#2a2a5e",
            fg="#eaeaea",
            insertbackground="#eaeaea",
            width=12
        )
        self.goal_entry.pack(side=tk.LEFT)
        self.goal_entry.insert(0, "10000")
        self.goal_entry.bind("<Return>", lambda e: self._update_forecast())
        
        # Дата цели
        date_frame = tk.Frame(input_frame, bg="#1a1a3e")
        date_frame.pack(fill=tk.X, padx=15, pady=(0, 5))
        
        tk.Label(
            date_frame,
            text="Достичь до даты (ГГГГ-ММ-ДД):",
            font=("Segoe UI", 10),
            fg="#eaeaea",
            bg="#1a1a3e"
        ).pack(side=tk.LEFT, padx=(0, 10))
        
        self.target_date_entry = tk.Entry(
            date_frame,
            font=("Segoe UI", 12),
            bg="#2a2a5e",
            fg="#eaeaea",
            insertbackground="#eaeaea",
            width=14
        )
        self.target_date_entry.pack(side=tk.LEFT)
        default_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        self.target_date_entry.insert(0, default_date)
        self.target_date_entry.bind("<Return>", lambda e: self._update_forecast())
        
        # Выбор режима расчёта
        mode_frame = tk.Frame(input_frame, bg="#1a1a3e")
        mode_frame.pack(fill=tk.X, padx=15, pady=(5, 5))
        
        tk.Label(
            mode_frame,
            text="Режим расчёта:",
            font=("Segoe UI", 10),
            fg="#eaeaea",
            bg="#1a1a3e"
        ).pack(side=tk.LEFT, padx=(0, 10))
        
        self.calc_mode = tk.StringVar(value="from_scratch")
        
        modes = [
            ("🔄 С нуля", "from_scratch"),
            ("💰 От реального заработка", "from_real"),
            ("📊 От приблизительного", "from_approx"),
        ]
        
        for text, value in modes:
            tk.Radiobutton(
                mode_frame,
                text=text,
                variable=self.calc_mode,
                value=value,
                command=self._update_forecast,
                bg="#1a1a3e",
                fg="#eaeaea",
                selectcolor="#1a1a3e",
                activebackground="#1a1a3e"
            ).pack(side=tk.LEFT, padx=(0, 15))
        
        # Выбор источника дохода
        income_frame = tk.Frame(input_frame, bg="#1a1a3e")
        income_frame.pack(fill=tk.X, padx=15, pady=(0, 5))
        
        tk.Label(
            income_frame,
            text="Источник дохода:",
            font=("Segoe UI", 10),
            fg="#eaeaea",
            bg="#1a1a3e"
        ).pack(side=tk.LEFT, padx=(0, 10))
        
        self.income_source = tk.StringVar(value="real")
        tk.Radiobutton(
            income_frame,
            text="Реальный (после налога)",
            variable=self.income_source,
            value="real",
            command=self._update_forecast,
            bg="#1a1a3e",
            fg="#eaeaea",
            selectcolor="#1a1a3e",
            activebackground="#1a1a3e"
        ).pack(side=tk.LEFT, padx=(0, 15))
        
        tk.Radiobutton(
            income_frame,
            text="Установленный пользователем",
            variable=self.income_source,
            value="user",
            command=self._update_forecast,
            bg="#1a1a3e",
            fg="#eaeaea",
            selectcolor="#1a1a3e",
            activebackground="#1a1a3e"
        ).pack(side=tk.LEFT)
        
        # Кнопки
        btn_frame = tk.Frame(input_frame, bg="#1a1a3e")
        btn_frame.pack(fill=tk.X, padx=15, pady=(5, 10))
        
        tk.Button(
            btn_frame,
            text="🔄 Рассчитать",
            command=self._update_forecast,
            bg="#00d4aa",
            fg="#0f0f23",
            font=("Segoe UI", 10, "bold"),
            relief=tk.FLAT,
            padx=20,
            pady=5,
            cursor="hand2"
        ).pack(side=tk.LEFT)
        
        # --- Кнопки сохранения цели ---
        tk.Button(
            btn_frame,
            text="💾 Сохранить цель",
            command=self._save_goal,
            bg="#ffd700",
            fg="#0f0f23",
            font=("Segoe UI", 10, "bold"),
            relief=tk.FLAT,
            padx=20,
            pady=5,
            cursor="hand2"
        ).pack(side=tk.LEFT, padx=10)
        
        tk.Button(
            btn_frame,
            text="📋 Управление целями",
            command=self._manage_goals,
            bg="#2a2a5e",
            fg="#eaeaea",
            font=("Segoe UI", 10, "bold"),
            relief=tk.FLAT,
            padx=20,
            pady=5,
            cursor="hand2"
        ).pack(side=tk.LEFT)
        
        # --- Статистика текущего дохода ---
        self.stats_frame = tk.Frame(self.window, bg="#0f0f23")
        self.stats_frame.pack(fill=tk.X, padx=20, pady=(0, 10))
        
        self.stats_label = tk.Label(
            self.stats_frame,
            text="",
            font=("Segoe UI", 9),
            fg="#888",
            bg="#0f0f23",
            anchor=tk.W
        )
        self.stats_label.pack(fill=tk.X)
        
        # --- Результаты ---
        self.result_frame = tk.Frame(self.window, bg="#0f0f23")
        self.result_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Карточки результатов
        self.result_cards = {}
        
        card_data = [
            ("🎯 Осталось заработать", "remaining"),
            ("⏱ Часов до цели", "hours"),
            ("📅 Дней до цели", "days"),
            ("📊 Недельный доход (прогноз)", "weekly"),
            ("📅 Месячный доход (прогноз)", "monthly"),
            ("⚡ Нужно часов в день", "hours_per_day"),
            ("📅 Дней до даты", "days_needed"),
        ]
        
        # Создаём карточки в 3 ряда
        row1 = tk.Frame(self.result_frame, bg="#0f0f23")
        row1.pack(fill=tk.X, pady=3)
        
        row2 = tk.Frame(self.result_frame, bg="#0f0f23")
        row2.pack(fill=tk.X, pady=3)
        
        row3 = tk.Frame(self.result_frame, bg="#0f0f23")
        row3.pack(fill=tk.X, pady=3)
        
        for i, (label, key) in enumerate(card_data):
            if i < 3:
                parent = row1
            elif i < 6:
                parent = row2
            else:
                parent = row3
            
            card = tk.Frame(parent, bg="#1a1a3e", relief=tk.GROOVE, bd=1, padx=12, pady=8)
            card.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=3)
            
            label_widget = tk.Label(
                card,
                text=label,
                font=("Segoe UI", 9),
                fg="#888",
                bg="#1a1a3e",
                anchor=tk.W
            )
            label_widget.pack(fill=tk.X)
            
            value_widget = tk.Label(
                card,
                text="—",
                font=("Segoe UI", 16, "bold"),
                fg="#eaeaea",
                bg="#1a1a3e",
                anchor=tk.W
            )
            value_widget.pack(fill=tk.X)
            
            self.result_cards[key] = value_widget
    
    def _calculate_statistics(self):
        """Рассчитать статистику на основе данных (только дни с реальными данными)."""
        # Собираем данные по дням из сессий
        daily_data = {}
        for sess in self.logic.sessions:
            day = time.strftime("%Y-%m-%d", time.localtime(sess.started_at))
            if day not in daily_data:
                daily_data[day] = {'points': 0, 'hours': 0.0}
            daily_data[day]['points'] += sess.points
            daily_data[day]['hours'] += get_productive_tab_time(sess.tab_times) / 3600.0
        
        # Добавляем текущую сессию
        if self.logic.session_active and self.logic.session_points > 0:
            today = time.strftime("%Y-%m-%d")
            if today not in daily_data:
                daily_data[today] = {'points': 0, 'hours': 0.0}
            daily_data[today]['points'] += self.logic.session_points
        
        # Считаем реальный и приблизительный доход (только дни с реальными данными)
        total_real_after_tax = 0.0
        total_approx = 0.0
        total_points = 0
        total_hours = 0.0
        days_with_data = 0
        
        real_earnings = getattr(self.logic, 'real_earnings', {})
        point_price = self.logic.point_price
        
        for day, data in daily_data.items():
            real = real_earnings.get(day, 0.0)
            real_after_tax = real * (1 - self.tax_rate) if real > 0 else 0.0
            
            # Учитываем только дни с реальными данными
            if real_after_tax > 0 and data['hours'] > 0:
                total_real_after_tax += real_after_tax
                total_points += data['points']
                total_hours += data['hours']
                days_with_data += 1
        
        # Приблизительный доход считаем только для дней с реальными данными
        approx_by_real_days = 0.0
        for day in real_earnings.keys():
            if day in daily_data:
                approx_by_real_days += daily_data[day]['points'] * point_price
        
        # Установленная цена пользователем
        user_price = self.logic.point_price
        
        # Средние показатели (только по дням с реальными данными)
        avg_hourly_real = total_real_after_tax / total_hours if total_hours > 0 else 0
        avg_daily_real = total_real_after_tax / days_with_data if days_with_data > 0 else 0
        
        total_user_income = total_points * user_price
        avg_hourly_user = total_user_income / total_hours if total_hours > 0 else 0
        avg_daily_user = total_user_income / days_with_data if days_with_data > 0 else 0
        
        return {
            'days_with_data': days_with_data,
            'total_real_after_tax': total_real_after_tax,
            'total_approx': approx_by_real_days,
            'total_points': total_points,
            'total_hours': total_hours,
            'avg_hourly_real': avg_hourly_real,
            'avg_daily_real': avg_daily_real,
            'avg_hourly_user': avg_hourly_user,
            'avg_daily_user': avg_daily_user,
            'user_price': user_price,
        }
    
    def _update_forecast(self):
        """Обновить прогнозы."""
        try:
            goal = float(self.goal_entry.get().replace(",", "."))
            if goal <= 0:
                raise ValueError("Сумма должна быть > 0")
        except ValueError:
            messagebox.showerror("Ошибка", "Введите корректную сумму (например, 10000)", parent=self.window)
            return
        
        # Парсим дату
        try:
            target_date = datetime.strptime(self.target_date_entry.get().strip(), "%Y-%m-%d")
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            if target_date < today:
                raise ValueError("Дата должна быть в будущем")
            days_until_target = (target_date - today).days
        except ValueError as e:
            messagebox.showerror("Ошибка", f"Некорректная дата: {e}\nИспользуйте формат ГГГГ-ММ-ДД", parent=self.window)
            return
        
        stats = self._calculate_statistics()
        
        if stats['days_with_data'] == 0:
            for key in self.result_cards:
                self.result_cards[key].config(text="Нет данных")
            self.stats_label.config(text="Нет данных для расчёта. Добавьте сессии и реальные заработки.")
            return
        
        # Выбираем источник дохода
        if self.income_source.get() == "real":
            avg_hourly = stats['avg_hourly_real']
            avg_daily = stats['avg_daily_real']
            source_name = "реальному (после налога)"
            current_earned = stats['total_real_after_tax']
        else:
            avg_hourly = stats['avg_hourly_user']
            avg_daily = stats['avg_daily_user']
            source_name = "установленному пользователем"
            current_earned = stats['total_points'] * stats['user_price']
        
        if avg_hourly <= 0:
            for key in self.result_cards:
                self.result_cards[key].config(text="—")
            self.stats_label.config(text="Недостаточно данных для расчёта. Нужны сессии с часами работы.")
            return
        
        # Определяем оставшуюся сумму в зависимости от режима
        mode = self.calc_mode.get()
        
        if mode == "from_scratch":
            remaining = goal
            mode_label = "С нуля"
            used_earned = 0
        elif mode == "from_real":
            remaining = max(0, goal - stats['total_real_after_tax'])
            mode_label = f"От реального (уже {stats['total_real_after_tax']:.0f})"
            used_earned = stats['total_real_after_tax']
        else:  # from_approx
            remaining = max(0, goal - stats['total_approx'])
            mode_label = f"От приблизительного (уже {stats['total_approx']:.0f})"
            used_earned = stats['total_approx']
        
        if remaining <= 0:
            self.result_cards['remaining'].config(text="0.00 🎉", fg="#00d4aa")
            self.result_cards['hours'].config(text="0")
            self.result_cards['days'].config(text="0")
            self.result_cards['weekly'].config(text="—")
            self.result_cards['monthly'].config(text="—")
            self.result_cards['hours_per_day'].config(text="0")
            self.result_cards['days_needed'].config(text="0")
            self.stats_label.config(text=f"✅ Цель уже достигнута! {source_name}, режим: {mode_label}")
            return
        
        # Расчёты
        hours_to_goal = remaining / avg_hourly if avg_hourly > 0 else 0
        days_to_goal = remaining / avg_daily if avg_daily > 0 else 0
        weekly_income = avg_daily * 7
        monthly_income = avg_daily * 30
        
        # Часов в день для достижения цели за указанный срок
        hours_per_day_needed = remaining / days_until_target / avg_hourly if avg_hourly > 0 else 0
        
        # Обновляем карточки
        self.result_cards['remaining'].config(text=f"{remaining:.2f} руб.", fg="#ffd700")
        self.result_cards['hours'].config(text=f"{hours_to_goal:.1f}")
        self.result_cards['days'].config(text=f"{days_to_goal:.1f}")
        self.result_cards['weekly'].config(text=f"{weekly_income:.2f} руб.")
        self.result_cards['monthly'].config(text=f"{monthly_income:.2f} руб.")
        self.result_cards['hours_per_day'].config(text=f"{hours_per_day_needed:.1f}")
        self.result_cards['days_needed'].config(text=f"{days_until_target} дн.")
        
        if hours_per_day_needed > 24:
            self.result_cards['hours_per_day'].config(fg="#ff6b6b")
            extra_text = f" ⚠️ Нужно {hours_per_day_needed:.1f} ч/день (больше 24!)"
        else:
            self.result_cards['hours_per_day'].config(fg="#4ecdc4")
            extra_text = ""
        
        self.stats_label.config(
            text=f"📊 {source_name} | Режим: {mode_label} | "
                 f"Средняя скорость: {avg_hourly:.2f} руб/ч | "
                 f"Дней с данными: {stats['days_with_data']} | "
                 f"Дней до {target_date.strftime('%d.%m.%Y')}: {days_until_target}{extra_text}"
        )
    
    def _save_goal(self):
        """Сохранить текущую цель."""
        try:
            goal = float(self.goal_entry.get().replace(",", "."))
            if goal <= 0:
                raise ValueError("Сумма должна быть > 0")
        except ValueError:
            messagebox.showerror("Ошибка", "Введите корректную сумму", parent=self.window)
            return
        
        target_date = self.target_date_entry.get().strip()
        mode = self.calc_mode.get()
        income_source = self.income_source.get()
        
        # Диалог для имени цели
        dialog = tk.Toplevel(self.window)
        dialog.title("Название цели")
        dialog.geometry("300x120")
        dialog.configure(bg="#0f0f23")
        dialog.attributes("-topmost", True)
        dialog.transient(self.window)
        dialog.grab_set()
        
        tk.Label(
            dialog,
            text="Введите название цели:",
            font=("Segoe UI", 10),
            fg="#eaeaea",
            bg="#0f0f23"
        ).pack(pady=(15, 5))
        
        name_entry = tk.Entry(dialog, font=("Segoe UI", 12), bg="#2a2a5e", fg="#eaeaea", insertbackground="#eaeaea")
        name_entry.pack(fill=tk.X, padx=20, pady=5)
        name_entry.insert(0, f"Цель {len(self.logic.goals) + 1}")
        name_entry.focus()
        name_entry.select_range(0, tk.END)
        
        def on_ok():
            name = name_entry.get().strip()
            if not name:
                name = f"Цель {len(self.logic.goals) + 1}"
            
            self.logic.add_goal(name, goal, target_date, mode, income_source)
            dialog.destroy()
            messagebox.showinfo("Успех", f"Цель '{name}' сохранена!", parent=self.window)
        
        def on_cancel():
            dialog.destroy()
        
        btn_frame = tk.Frame(dialog, bg="#0f0f23")
        btn_frame.pack(pady=10)
        
        tk.Button(
            btn_frame,
            text="OK",
            command=on_ok,
            bg="#00d4aa",
            fg="#0f0f23",
            font=("Segoe UI", 10, "bold"),
            relief=tk.FLAT,
            padx=20,
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
            padx=20,
            pady=5,
            cursor="hand2"
        ).pack(side=tk.LEFT, padx=5)
        
        name_entry.bind("<Return>", lambda e: on_ok())
        name_entry.bind("<Escape>", lambda e: on_cancel())
    
    def _manage_goals(self):
        """Открыть окно управления целями."""
        from manage_goals_window import ManageGoalsWindow
        ManageGoalsWindow(self.window, self.logic)
    
    def _save_data(self):
        self.logic.on_update()
        messagebox.showinfo("Успех", "Данные сохранены!", parent=self.window)