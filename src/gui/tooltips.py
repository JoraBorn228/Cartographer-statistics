"""
Всплывающие подсказки для элементов интерфейса.
"""
import tkinter as tk


class Tooltip:
    """Класс для создания всплывающих подсказок."""
    
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip_window = None
        self._id = None
        
        widget.bind('<Enter>', self._show_tip)
        widget.bind('<Leave>', self._hide_tip)
        widget.bind('<ButtonPress>', self._hide_tip)
    
    def _show_tip(self, event):
        """Показать подсказку при наведении."""
        if self.tip_window or not self.text:
            return
        
        # Позиция подсказки
        x = self.widget.winfo_rootx() + 25
        y = self.widget.winfo_rooty() + 20
        
        # Создаём окно подсказки
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)  # Без рамки
        tw.wm_geometry(f"+{x}+{y}")
        
        # Настройка внешнего вида
        label = tk.Label(
            tw,
            text=self.text,
            justify=tk.LEFT,
            background="#2a2a4a",
            foreground="#eaeaea",
            relief=tk.SOLID,
            borderwidth=1,
            padx=8,
            pady=4,
            font=("Segoe UI", 9)
        )
        label.pack()
        
        # Авто-скрытие через 5 секунд
        self._id = tw.after(5000, self._hide_tip)
    
    def _hide_tip(self, event=None):
        """Скрыть подсказку."""
        if self.tip_window:
            if self._id:
                self.tip_window.after_cancel(self._id)
                self._id = None
            self.tip_window.destroy()
            self.tip_window = None


def add_tooltip(widget, text):
    """Упрощённая функция добавления подсказки."""
    return Tooltip(widget, text)