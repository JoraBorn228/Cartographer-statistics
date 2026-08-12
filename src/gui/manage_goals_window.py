"""
Окно управления целями.
"""
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime


class ManageGoalsWindow:
    def __init__(self, parent, logic):
        self.parent = parent
        self.logic = logic
        
        self.window = tk.Toplevel(parent)
        self.window.title("📋 Управление целями")
        self.window.geometry("600x450")
        self.window.minsize(500, 350)
        self.window.configure(bg="#0f0f23")
        self.window.attributes("-topmost", True)
        
        self._build_ui()
        self._update_list()
    
    def _build_ui(self):
        # Заголовок
        tk.Label(
            self.window,
            text="📋 Мои цели",
            font=("Segoe UI", 16, "bold"),
            fg="#00d4aa",
            bg="#0f0f23"
        ).pack(pady=(10, 5))
        
        # Список целей
        self.listbox = tk.Listbox(
            self.window,
            bg="#1a1a3e",
            fg="#eaeaea",
            font=("Segoe UI", 10),
            selectbackground="#00d4aa",
            selectforeground="#0f0f23",
            height=10
        )
        self.listbox.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        self.listbox.bind("<Double-1>", self._on_select)
        
        # Информация о выбранной цели
        self.info_label = tk.Label(
            self.window,
            text="",
            font=("Segoe UI", 9),
            fg="#888",
            bg="#0f0f23",
            anchor=tk.W,
            justify=tk.LEFT
        )
        self.info_label.pack(fill=tk.X, padx=20, pady=(0, 10))
        
        # Кнопки
        btn_frame = tk.Frame(self.window, bg="#0f0f23")
        btn_frame.pack(fill=tk.X, padx=20, pady=(0, 10))
        
        tk.Button(
            btn_frame,
            text="✅ Выбрать",
            command=self._on_select,
            bg="#00d4aa",
            fg="#0f0f23",
            font=("Segoe UI", 10, "bold"),
            relief=tk.FLAT,
            padx=15,
            pady=5,
            cursor="hand2"
        ).pack(side=tk.LEFT, padx=2)
        
        tk.Button(
            btn_frame,
            text="🗑 Удалить",
            command=self._on_delete,
            bg="#ff6b6b",
            fg="#0f0f23",
            font=("Segoe UI", 10, "bold"),
            relief=tk.FLAT,
            padx=15,
            pady=5,
            cursor="hand2"
        ).pack(side=tk.LEFT, padx=2)
        
        tk.Button(
            btn_frame,
            text="🔄 Обновить",
            command=self._update_list,
            bg="#2a2a5e",
            fg="#eaeaea",
            font=("Segoe UI", 10, "bold"),
            relief=tk.FLAT,
            padx=15,
            pady=5,
            cursor="hand2"
        ).pack(side=tk.LEFT, padx=2)
        
        tk.Button(
            btn_frame,
            text="❌ Закрыть",
            command=self.window.destroy,
            bg="#2a2a5e",
            fg="#eaeaea",
            font=("Segoe UI", 10, "bold"),
            relief=tk.FLAT,
            padx=15,
            pady=5,
            cursor="hand2"
        ).pack(side=tk.RIGHT, padx=2)
    
    def _update_list(self):
        self.listbox.delete(0, tk.END)
        
        if not self.logic.goals:
            self.listbox.insert(tk.END, "— Нет целей —")
            self.info_label.config(text="Нажмите 'Сохранить цель' в окне прогнозов (📈)")
            return
        
        active_id = self.logic.active_goal_id
        
        for goal in self.logic.goals:
            name = goal.get('name', 'Без названия')
            amount = goal.get('target_amount', 0)
            date = goal.get('target_date', '—')
            is_active = " ✅" if goal['id'] == active_id else ""
            label = f"{name}: {amount:.0f} руб. до {date}{is_active}"
            self.listbox.insert(tk.END, label)
        
        self._show_info()
    
    def _show_info(self):
        selection = self.listbox.curselection()
        if not selection or not self.logic.goals:
            self.info_label.config(text="")
            return
        
        idx = selection[0]
        if idx >= len(self.logic.goals):
            return
        
        goal = self.logic.goals[idx]
        progress = self.logic.get_goal_progress(goal)
        
        info_text = (
            f"📌 {goal.get('name', 'Без названия')}\n"
            f"💰 Цель: {goal['target_amount']:.0f} руб.\n"
            f"📅 Дата: {goal.get('target_date', '—')}\n"
            f"📊 Режим: {progress['mode_label']}\n"
            f"📈 Осталось: {progress['remaining']:.0f} руб.\n"
            f"⚡ Нужно в день: {progress['needed_per_day']:.0f} руб. ({progress['needed_points_per_day']:.0f} точек)\n"
            f"📅 Дней осталось: {progress['days_until']}"
        )
        self.info_label.config(text=info_text)
    
    def _on_select(self, event=None):
        selection = self.listbox.curselection()
        if not selection or not self.logic.goals:
            if not self.logic.goals:
                messagebox.showinfo("Цели", "Создайте цель в окне прогнозов (📈)", parent=self.window)
            return
        
        idx = selection[0]
        if idx >= len(self.logic.goals):
            return
        
        goal = self.logic.goals[idx]
        self.logic.set_active_goal(goal['id'])
        self._update_list()
        self.window.destroy()
    
    def _on_delete(self):
        selection = self.listbox.curselection()
        if not selection or not self.logic.goals:
            if not self.logic.goals:
                messagebox.showinfo("Цели", "Создайте цель в окне прогнозов (📈)", parent=self.window)
            return
        
        idx = selection[0]
        if idx >= len(self.logic.goals):
            return
        
        goal = self.logic.goals[idx]
        
        if not messagebox.askyesno(
            "Удалить цель",
            f"Удалить цель '{goal.get('name', 'Без названия')}'?",
            parent=self.window
        ):
            return
        
        self.logic.delete_goal(goal['id'])
        self._update_list()