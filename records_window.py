"""
Окно рекордов с красивым отображением лучших показателей и кнопкой пересчёта.
"""
import tkinter as tk
from tkinter import messagebox
from tkinter import font as tkfont
from typing import Dict, Any

from config import BG, FG, ACCENT, BAR_BG, BTN_BG


class RecordsWindow:
    def __init__(self, parent, logic):
        self.parent = parent
        self.logic = logic
        self.window = tk.Toplevel(parent)
        self.window.title("🏆 Рекорды")
        self.window.geometry("500x500")
        self.window.configure(bg=BG)
        self.window.attributes("-topmost", True)
        self.window.resizable(False, False)

        # Заголовок
        tk.Label(
            self.window,
            text="🏆 Ваши рекорды",
            font=("Segoe UI", 16, "bold"),
            fg=ACCENT,
            bg=BG
        ).pack(pady=(15, 10))

        # Основной фрейм с прокруткой
        canvas = tk.Canvas(self.window, bg=BG, highlightthickness=0)
        scrollbar = tk.Scrollbar(self.window, orient=tk.VERTICAL, command=canvas.yview)
        self.scrollable_frame = tk.Frame(canvas, bg=BG)
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=20)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Строим карточки рекордов
        self._build_records(self.scrollable_frame)

        # Кнопка пересчёта рекордов
        btn_frame = tk.Frame(self.window, bg=BG)
        btn_frame.pack(pady=10)

        tk.Button(
            btn_frame,
            text="🔄 Пересчитать рекорды",
            command=self._recalculate,
            bg=BTN_BG,
            fg=FG,
            relief=tk.FLAT,
            padx=12,
            pady=5,
            cursor="hand2"
        ).pack(side=tk.LEFT, padx=5)

        tk.Button(
            btn_frame,
            text="Закрыть",
            command=self.window.destroy,
            bg=BTN_BG,
            fg=FG,
            relief=tk.FLAT,
            padx=12,
            pady=5,
            cursor="hand2"
        ).pack(side=tk.LEFT, padx=5)

    def _recalculate(self):
        """Пересчитать рекорды и обновить отображение."""
        self.logic.recalculate_records()
        # Очищаем и перестраиваем карточки
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        self._build_records(self.scrollable_frame)
        messagebox.showinfo("Готово", "Рекорды пересчитаны на основе всех сессий.", parent=self.window)

    def _build_records(self, parent):
        records = self.logic.records
        point_price = self.logic.point_price

        # Определяем рекорды с иконками, цветами и описаниями
        record_items = [
            {
                "icon": "📌",
                "title": "Максимум точек за день",
                "value": records.get("max_points_per_day", 0),
                "color": "#00d4aa",
                "unit": "точек"
            },
            {
                "icon": "⚡",
                "title": "Максимум точек за спринт",
                "value": records.get("max_points_per_sprint", 0),
                "color": "#ffd166",
                "unit": "точек"
            },
            {
                "icon": "🚀",
                "title": "Максимальная скорость (за сессию)",
                "value": f"{records.get('max_speed_per_session', 0):.1f}",
                "color": "#ff6b6b",
                "unit": "точ/ч"
            },
            {
                "icon": "💨",
                "title": "Максимальная скорость (за день)",
                "value": f"{records.get('max_speed_per_day', 0):.1f}",
                "color": "#4ecdc4",
                "unit": "точ/ч"
            },
            {
                "icon": "💰",
                "title": "Максимум заработка за день",
                "value": f"{records.get('max_points_per_day', 0) * point_price:.2f}",
                "color": "#ffd700",
                "unit": "руб."
            },
            {
                "icon": "🏅",
                "title": "Всего точек за всё время",
                "value": self.logic.points,
                "color": "#a29bfe",
                "unit": "точек"
            },
            {
                "icon": "📅",
                "title": "Всего дней с активностью",
                "value": len(self.logic.get_daily_points_series()),
                "color": "#fd79a8",
                "unit": "дней"
            }
        ]

        # Создаём карточки
        for item in record_items:
            card = tk.Frame(
                parent,
                bg="#2a2a40",
                relief=tk.RAISED,
                borderwidth=1,
                highlightthickness=1,
                highlightcolor="#3d3d6b"
            )
            card.pack(fill=tk.X, pady=5)

            # Иконка и заголовок
            header_frame = tk.Frame(card, bg="#2a2a40")
            header_frame.pack(fill=tk.X, padx=10, pady=(6, 2))

            tk.Label(
                header_frame,
                text=f"{item['icon']} {item['title']}",
                font=("Segoe UI", 10, "bold"),
                fg=FG,
                bg="#2a2a40"
            ).pack(side=tk.LEFT)

            # Значение и единица измерения
            value_frame = tk.Frame(card, bg="#2a2a40")
            value_frame.pack(fill=tk.X, padx=10, pady=(0, 6))

            tk.Label(
                value_frame,
                text=f"{item['value']}",
                font=("Segoe UI", 16, "bold"),
                fg=item["color"],
                bg="#2a2a40"
            ).pack(side=tk.LEFT)

            tk.Label(
                value_frame,
                text=f" {item['unit']}",
                font=("Segoe UI", 10),
                fg="#888",
                bg="#2a2a40"
            ).pack(side=tk.LEFT)