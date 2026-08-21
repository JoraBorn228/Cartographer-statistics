"""
Плавающий мини-виджет.
"""
import tkinter as tk
from tkinter import font as tkfont, messagebox
import time
import keyboard

try:
    from pynput.mouse import Controller, Button
    PYNPUT_AVAILABLE = True
except ImportError:
    PYNPUT_AVAILABLE = False

from src.utils.config import BG, FG, ACCENT
from src.utils.helpers import calc_points_per_hour, get_productive_tab_time
from src.core.settings_manager import load_settings


class FloatingWidget:
    def __init__(self, logic, point_price: float):
        self.logic = logic
        self.point_price = point_price
        self.settings = load_settings()
        self.window = tk.Toplevel()
        self.window.overrideredirect(True)
        self.window.attributes('-topmost', True)
        self.window.attributes('-alpha', 0.9)
        self.window.geometry("200x90+100+100")
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

        # Привязки
        self._current_hotkey_id = None
        self.window.bind("<Unmap>", lambda e: self._on_hide())
        self.window.bind("<Map>", lambda e: self._on_show())

        self.window.bind("<Double-Button-1>", lambda e: self.close())

        self._update_loop()
        self._on_show()

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
        try:
            if not self.window.winfo_exists():
                return
            self._update_content()
            self.window.after(1000, self._update_loop)
        except Exception:
            # Окно уже уничтожено — тихо прерываем цикл
            pass

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

    # ================= HOTKEY & CLICK =================
    def _update_hotkey(self):
        if not PYNPUT_AVAILABLE:
            return

        hk = self.settings.get("click_hotkey", "ctrl+shift+f").strip().lower()
        if self._current_hotkey_id:
            keyboard.remove_hotkey(self._current_hotkey_id)

        if hk:
            self._current_hotkey_id = keyboard.add_hotkey(hk, self._simulate_click, suppress=False)

    def _simulate_click(self):
        if not PYNPUT_AVAILABLE:
            messagebox.showwarning("Ошибка", "Установите pynput: pip install pynput")
            return

        try:
            mouse = Controller()
            target_x = self.settings.get("click_x", 500)
            target_y = self.settings.get("click_y", 500)
            
            # Сохраняем текущую позицию мыши
            current_pos = mouse.position
            current_x, current_y = current_pos
            
            # Перемещаем мышь в целевую точку
            mouse.position = (target_x, target_y)
            
            # Делаем клик
            mouse.click(Button.left, 1)
            
            # Возвращаем мышь в исходную позицию
            mouse.position = (current_x, current_y)
        except Exception as e:
            print(f"Ошибка клика: {e}")

    def _on_hide(self):
        """Когда окно скрыто/закрыто — отключаем хоткей"""
        try:
            if self._current_hotkey_id:
                keyboard.remove_hotkey(self._current_hotkey_id)
                self._current_hotkey_id = None
        except Exception:
            pass

    def _on_show(self):
        """Когда окно появляется — включаем хоткей"""
        try:
            self._update_hotkey()
        except Exception:
            pass

    def close(self):
        try:
            self._on_hide()
        except Exception:
            pass
        try:
            self.window.destroy()
        except Exception:
            pass