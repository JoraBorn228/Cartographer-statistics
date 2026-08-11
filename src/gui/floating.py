"""
Плавающий мини-виджет.
"""
import tkinter as tk
from tkinter import font as tkfont
import time

from src.utils.config import BG, FG, ACCENT
from src.utils.helpers import calc_points_per_hour, get_productive_tab_time


class FloatingWidget:
    def __init__(self, logic, point_price: float):
        self.logic = logic
        self.point_price = point_price
        self.window = tk.Toplevel()
        self.window.overrideredirect(True)
        self.window.attributes('-topmost', True)
        self.window.attributes('-alpha', 0.9)
        self.window.geometry("180x70+100+100")
        self.window.configure(bg=BG, highlightthickness=0)

        self.window.bind("<ButtonPress-1>", self._start_move)
        self.window.bind("<ButtonRelease-1>", self._stop_move)
        self.window.bind("<B1-Motion>", self._on_move)
        self._drag_data = {"x": 0, "y": 0}

        small_font = tkfont.Font(family="Segoe UI", size=9)
        mid_font = tkfont.Font(family="Segoe UI", size=12, weight="bold")

        self.speed_label = tk.Label(
            self.window,
            text="Скорость: —",
            font=mid_font,
            fg=ACCENT,
            bg=BG
        )
        self.speed_label.pack(pady=(8, 0))

        self.time_label = tk.Label(
            self.window,
            text="До конца: —",
            font=small_font,
            fg=FG,
            bg=BG
        )
        self.time_label.pack(pady=(2, 8))

        self.window.bind("<Double-Button-1>", lambda e: self.close())

        self._update_loop()

    def _start_move(self, event):
        self._drag_data["x"] = event.x
        self._drag_data["y"] = event.y

    def _stop_move(self, event):
        self._drag_data["x"] = 0
        self._drag_data["y"] = 0

    def _on_move(self, event):
        x = self.window.winfo_x() + (event.x - self._drag_data["x"])
        y = self.window.winfo_y() + (event.y - self._drag_data["y"])
        self.window.geometry(f"+{x}+{y}")

    def _update_loop(self):
        self._update_content()
        self.window.after(1000, self._update_loop)

    def _update_content(self):
        speed_text = "Скорость: —"
        if self.logic.session_active and self.logic.session_points > 0:
            prod_time = self.logic.get_current_productive_seconds()
            speed = calc_points_per_hour(self.logic.session_points, prod_time)
            if speed is not None:
                speed_text = f"Скорость: {speed:.0f} т/ч"
        else:
            total_points = self.logic.points
            total_prod = 0.0
            for s in self.logic.sessions:
                total_prod += get_productive_tab_time(s.tab_times)
            speed = calc_points_per_hour(total_points, total_prod)
            if speed is not None:
                speed_text = f"Ср. скорость: {speed:.0f} т/ч"
        self.speed_label.config(text=speed_text)

        time_text = "До конца: —"
        if self.logic.session_active:
            phase, remaining, _ = self.logic._update_phase_progress()
            if phase == "sprint":
                mins, secs = divmod(int(remaining), 60)
                time_text = f"До конца спринта: {mins:02d}:{secs:02d}"
            elif phase == "break":
                mins, secs = divmod(int(remaining), 60)
                time_text = f"До конца перерыва: {mins:02d}:{secs:02d}"
            elif self.logic.sprint_finished:
                time_text = "Все спринты завершены"
            else:
                time_text = "Сессия активна"
        self.time_label.config(text=time_text)

    def close(self):
        self.window.destroy()