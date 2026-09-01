"""
Окно настроек приложения (улучшенный интерфейс).
"""
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable

from src.utils.config import (
    BG, BG_CARD, BG_CARD_HOVER, FG, FG_SECONDARY, ACCENT, ACCENT_DARK,
    BTN_BG, BTN_ACTIVE, BTN_HOVER, BAR_BG,
)
from src.core.settings_manager import load_settings, save_settings, DEFAULT_SETTINGS
from src.gui.profile_editor import ProfileEditor
try:
    from src.core.sync_manager import SyncManager as _SyncManager
except ImportError:
    _SyncManager = None

# Шрифты
_FONT_TITLE = ("Segoe UI", 16, "bold")
_FONT_SECTION = ("Segoe UI", 11, "bold")
_FONT_LABEL = ("Segoe UI", 9)
_FONT_LABEL_BOLD = ("Segoe UI", 9, "bold")
_FONT_HINT = ("Segoe UI", 8)
_FONT_BTN = ("Segoe UI", 10, "bold")
_FONT_BTN_SECONDARY = ("Segoe UI", 10)


class SettingsWindow:
    def __init__(self, parent, logic, on_settings_changed: Callable, sync_manager=None):
        self.parent = parent
        self.logic = logic
        self.on_settings_changed = on_settings_changed
        self.sync_manager = sync_manager

        # Используем единый ProfileManager из логики
        self.settings = load_settings()
        self.profile_manager = self.logic.profile_manager

        self.window = tk.Toplevel(parent)
        self.window.title("⚙️ Настройки")
        self.window.geometry("580x700")
        self.window.minsize(520, 620)
        self.window.configure(bg=BG)
        self.window.attributes("-topmost", True)

        # Настройка стиля ttk для Combobox
        self._setup_style()

        self._build_ui()
        self._update_profile_info()
        self._update_combos_from_profile()

    # ============================================================
    #  СТИЛЬ
    # ============================================================
    def _setup_style(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure(
            "Settings.TCombobox",
            fieldbackground=BAR_BG,
            background=BAR_BG,
            foreground=FG,
            bordercolor=ACCENT_DARK,
            lightcolor=ACCENT_DARK,
            darkcolor=ACCENT_DARK,
            arrowcolor=ACCENT,
            insertcolor=FG,
            relief=tk.FLAT,
            borderwidth=1,
            padding=4,
        )
        style.map(
            "Settings.TCombobox",
            fieldbackground=[("readonly", BAR_BG)],
            foreground=[("readonly", FG)],
            bordercolor=[("focus", ACCENT)],
        )
        style.configure(
            "Settings.TEntry",
            fieldbackground=BAR_BG,
            foreground=FG,
            insertcolor=FG,
            bordercolor=ACCENT_DARK,
            lightcolor=ACCENT_DARK,
            darkcolor=ACCENT_DARK,
            relief=tk.FLAT,
            borderwidth=1,
            padding=4,
        )
        style.map(
            "Settings.TEntry",
            bordercolor=[("focus", ACCENT)],
        )

    # ============================================================
    #  ПОСТРОЕНИЕ ИНТЕРФЕЙСА
    # ============================================================
    def _build_ui(self):
        # --- Шапка ---
        header = tk.Frame(self.window, bg=BG)
        header.pack(fill=tk.X, padx=18, pady=(14, 6))

        tk.Label(
            header,
            text="⚙️",
            font=("Segoe UI", 18),
            bg=BG,
        ).pack(side=tk.LEFT, padx=(0, 8))

        tk.Label(
            header,
            text="Настройки",
            font=_FONT_TITLE,
            fg=ACCENT,
            bg=BG,
        ).pack(side=tk.LEFT)

        # --- Подзаголовок-описание ---
        tk.Label(
            self.window,
            text="Настройте спринты, цель, заработок и систему под себя",
            fg=FG_SECONDARY,
            bg=BG,
            font=_FONT_HINT,
        ).pack(anchor=tk.W, padx=18, pady=(0, 8))

        # --- Canvas со скроллом ---
        canvas = tk.Canvas(self.window, bg=BG, highlightthickness=0, bd=0)
        scrollbar = tk.Scrollbar(self.window, orient=tk.VERTICAL, command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=BG)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Колесо мыши для скролла
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        self.window.bind("<Destroy>", lambda e: canvas.unbind_all("<MouseWheel>"), add="+")

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(14, 0), pady=(0, 4))
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=(0, 4))

        # Внутренний отступ для контента
        content = tk.Frame(scrollable_frame, bg=BG)
        content.pack(fill=tk.X, padx=14, pady=4)

        # ============================================================
        # ПРОФИЛЬ СПРИНТОВ
        # ============================================================
        card = self._add_card(content, "🎯 Профиль спринтов")

        row1 = tk.Frame(card, bg=BG_CARD)
        row1.pack(fill=tk.X, padx=12, pady=(10, 2))

        tk.Label(
            row1,
            text="Активный профиль",
            fg=FG_SECONDARY,
            bg=BG_CARD,
            font=_FONT_LABEL,
        ).pack(side=tk.LEFT)

        self.profile_label = tk.Label(
            row1,
            text="Загрузка...",
            fg=ACCENT,
            bg=BG_CARD,
            font=_FONT_LABEL_BOLD,
        )
        self.profile_label.pack(side=tk.RIGHT)

        row2 = tk.Frame(card, bg=BG_CARD)
        row2.pack(fill=tk.X, padx=12, pady=(6, 12))

        self.edit_btn = self._make_button(
            row2,
            text="📝 Редактировать профили",
            command=self._edit_profiles,
            primary=True,
        )
        self.edit_btn.pack(side=tk.LEFT)

        tk.Label(
            row2,
            text="Создайте свои последовательности",
            fg=FG_SECONDARY,
            bg=BG_CARD,
            font=_FONT_HINT,
        ).pack(side=tk.LEFT, padx=(10, 0))

        # ============================================================
        # БАЗОВЫЕ НАСТРОЙКИ
        # ============================================================
        card = self._add_card(content, "⏱ Базовые настройки спринтов")

        tk.Label(
            card,
            text="Используются, если не выбран профиль",
            fg=FG_SECONDARY,
            bg=BG_CARD,
            font=_FONT_HINT,
        ).pack(anchor=tk.W, padx=12, pady=(8, 6))

        self.sprint_var = tk.StringVar(value=str(self.settings.get("sprint_duration", 15)))
        self._add_field(card, "Длительность спринта (мин)", self.sprint_var, "combo", [5, 10, 15, 20, 25, 30, 45, 60])

        self.break_var = tk.StringVar(value=str(self.settings.get("break_duration", 5)))
        self._add_field(card, "Длительность перерыва (мин)", self.break_var, "combo", [1, 2, 3, 5, 10, 15])

        self.repeats_var = tk.StringVar(value=str(self.settings.get("sprint_repeats", 1)))
        self._add_field(card, "Количество повторов", self.repeats_var, "combo", list(range(1, 11)))

        # ============================================================
        # ЦЕЛЬ
        # ============================================================
        card = self._add_card(content, "🎯 Цель")

        self.auto_goal_var = tk.BooleanVar(value=self.settings.get("auto_goal_adjustment", True))
        self._add_toggle(card, "Автоматическая корректировка цели", self.auto_goal_var)

        # ============================================================
        # ЗАРАБОТОК
        # ============================================================
        card = self._add_card(content, "💰 Заработок")

        self.price_var = tk.StringVar(value=str(self.settings.get("point_price", 1.3)))
        self._add_field(card, "Цена одной точки (руб.)", self.price_var, "entry")

        # ============================================================
        # СИСТЕМНЫЕ
        # ============================================================
        card = self._add_card(content, "⚙️ Системные")

        self.auto_save_var = tk.StringVar(value=str(self.settings.get("auto_save_interval", 60)))
        self._add_field(card, "Интервал автосохранения (сек)", self.auto_save_var, "entry")

        # ============================================================
        # ГОРЯЧАЯ КЛАВИША И КЛИК
        # ============================================================
        card = self._add_card(content, "🖱 Горячая клавиша и клик")

        tk.Label(
            card,
            text="Нажми «Указать» и кликни мышкой на экран, чтобы выбрать точку для клика",
            fg=FG_SECONDARY,
            bg=BG_CARD,
            font=_FONT_HINT,
        ).pack(anchor=tk.W, padx=12, pady=(8, 6))

        hk_frame = tk.Frame(card, bg=BG_CARD)
        hk_frame.pack(fill=tk.X, padx=12, pady=6)

        tk.Label(
            hk_frame,
            text="X:",
            fg=FG,
            bg=BG_CARD,
            font=_FONT_LABEL,
        ).pack(side=tk.LEFT, padx=(0, 2))

        self.click_x_var = tk.StringVar(value=str(self.settings.get("click_x", 500)))
        ttk.Entry(
            hk_frame, textvariable=self.click_x_var,
            width=6, style="Settings.TEntry",
        ).pack(side=tk.LEFT, padx=(0, 8))

        tk.Label(
            hk_frame,
            text="Y:",
            fg=FG,
            bg=BG_CARD,
            font=_FONT_LABEL,
        ).pack(side=tk.LEFT, padx=(0, 2))

        self.click_y_var = tk.StringVar(value=str(self.settings.get("click_y", 500)))
        ttk.Entry(
            hk_frame, textvariable=self.click_y_var,
            width=6, style="Settings.TEntry",
        ).pack(side=tk.LEFT, padx=(0, 12))

        tk.Label(
            hk_frame,
            text="Горячая:",
            fg=FG,
            bg=BG_CARD,
            font=_FONT_LABEL,
        ).pack(side=tk.LEFT, padx=(0, 2))

        self.hotkey_var = tk.StringVar(value=self.settings.get("click_hotkey", "ctrl+shift+f"))
        self.hotkey_entry = ttk.Entry(
            hk_frame, textvariable=self.hotkey_var,
            width=12, style="Settings.TEntry",
        )
        self.hotkey_entry.pack(side=tk.LEFT, padx=(0, 8))

        self.pick_btn = self._make_button(
            hk_frame,
            text="📍 Указать",
            command=self._pick_click_point,
            primary=True,
        )
        self.pick_btn.pack(side=tk.LEFT)

        self.pick_status = tk.Label(
            card,
            text="Готово к выбору",
            fg=FG_SECONDARY,
            bg=BG_CARD,
            font=_FONT_HINT,
        )
        self.pick_status.pack(anchor=tk.W, padx=12, pady=(4, 8))

        # ============================================================
        # ЗВУКИ
        # ============================================================
        card = self._add_card(content, "🔊 Звуки")

        self.sound_var = tk.BooleanVar(value=self.settings.get("sound_enabled", True))
        self._add_toggle(card, "Включить звуки", self.sound_var)

        # ============================================================
        # СИНХРОНИЗАЦИЯ ЧЕРЕЗ GIT
        # ============================================================
        card = self._add_card(content, "☁ Синхронизация (Git)")

        self.sync_enabled_var = tk.BooleanVar(value=self.settings.get("sync_enabled", True))
        self._add_toggle(card, "Включить синхронизацию через Git", self.sync_enabled_var)

        # Интервал авто-пуша
        sync_row = tk.Frame(card, bg=BG_CARD)
        sync_row.pack(fill=tk.X, padx=12, pady=(4, 4))
        tk.Label(
            sync_row, text="Авто-пуш каждые (мин, 0 = выкл.):",
            fg=FG, bg=BG_CARD, font=_FONT_LABEL
        ).pack(side=tk.LEFT)
        self.auto_push_var = tk.StringVar(value=str(self.settings.get("auto_push_interval", 10)))
        tk.Spinbox(
            sync_row,
            from_=0, to=120, increment=5,
            textvariable=self.auto_push_var,
            width=5,
            bg=BG_CARD, fg=FG,
            buttonbackground=BG_CARD,
            relief=tk.FLAT,
            font=_FONT_LABEL,
        ).pack(side=tk.LEFT, padx=(8, 0))

        # Кнопка «Синхронизировать сейчас»
        sync_btn_row = tk.Frame(card, bg=BG_CARD)
        sync_btn_row.pack(fill=tk.X, padx=12, pady=(4, 8))
        self._make_button(
            sync_btn_row,
            text="☁ Синхронизировать сейчас",
            command=self._do_sync_now,
        ).pack(side=tk.LEFT)
        self.sync_info_label = tk.Label(
            sync_btn_row,
            text="",
            fg=FG_SECONDARY,
            bg=BG_CARD,
            font=_FONT_HINT,
        )
        self.sync_info_label.pack(side=tk.LEFT, padx=(10, 0))
        self._update_sync_info()

        # ============================================================
        # КНОПКИ
        # ============================================================
        btn_frame = tk.Frame(self.window, bg=BG)
        btn_frame.pack(fill=tk.X, padx=18, pady=(6, 14))


        self._make_button(
            btn_frame,
            text="💾 Сохранить",
            command=self._save_settings,
            primary=True,
        ).pack(side=tk.LEFT, padx=(0, 8))

        self._make_button(
            btn_frame,
            text="🔄 Сбросить",
            command=self._reset_defaults,
        ).pack(side=tk.LEFT, padx=(0, 8))

        self._make_button(
            btn_frame,
            text="Закрыть",
            command=self.window.destroy,
        ).pack(side=tk.LEFT)

    # ============================================================
    #  ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ИНТЕРФЕЙСА
    # ============================================================
    def _add_card(self, parent, title):
        """Карточка секции с заголовком и акцентной левой границей."""
        wrapper = tk.Frame(parent, bg=BG)
        wrapper.pack(fill=tk.X, pady=(6, 6))

        # Акцентная левая полоска
        bar = tk.Frame(wrapper, bg=ACCENT, width=3)
        bar.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 0))

        # Карточка
        card = tk.Frame(wrapper, bg=BG_CARD)
        card.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Заголовок карточки
        header = tk.Frame(card, bg=BG_CARD)
        header.pack(fill=tk.X, padx=12, pady=(10, 4))
        tk.Label(
            header,
            text=title,
            font=_FONT_SECTION,
            fg=FG,
            bg=BG_CARD,
        ).pack(side=tk.LEFT)

        # Тонкая разделительная линия
        tk.Frame(card, bg=ACCENT_DARK, height=1).pack(fill=tk.X, padx=12, pady=(0, 2))

        # Hover-эффект на карточке
        self._bind_hover(card, BG_CARD, BG_CARD_HOVER)
        return card

    def _add_field(self, card, label_text, var, kind="entry", values=None):
        """Поле ввода / комбобокс внутри карточки."""
        row = tk.Frame(card, bg=BG_CARD)
        row.pack(fill=tk.X, padx=12, pady=4)

        tk.Label(
            row,
            text=label_text,
            fg=FG,
            bg=BG_CARD,
            font=_FONT_LABEL,
            width=26,
            anchor=tk.W,
        ).pack(side=tk.LEFT)

        if kind == "combo":
            cb = ttk.Combobox(
                row, textvariable=var, values=values,
                width=10, state="readonly", style="Settings.TCombobox",
            )
            cb.pack(side=tk.LEFT)
        else:
            ttk.Entry(
                row, textvariable=var,
                width=10, style="Settings.TEntry",
            ).pack(side=tk.LEFT)

        # Нижний отступ последнего поля карточки — добавим через pady
        return row

    def _add_toggle(self, card, label_text, var):
        """Кастомный переключатель (switch) вместо чекбокса."""
        row = tk.Frame(card, bg=BG_CARD)
        row.pack(fill=tk.X, padx=12, pady=(6, 12))

        tk.Label(
            row,
            text=label_text,
            fg=FG,
            bg=BG_CARD,
            font=_FONT_LABEL,
        ).pack(side=tk.LEFT)

        # Контейнер переключателя
        switch = tk.Frame(row, bg=BG_CARD)
        switch.pack(side=tk.RIGHT)

        track = tk.Frame(switch, bg=BAR_BG, width=42, height=22)
        track.pack_propagate(False)
        track.pack()

        knob = tk.Frame(track, bg=ACCENT, width=18, height=18)

        def render():
            # Перерисовка knob
            knob.place_forget()
            if var.get():
                track.configure(bg=ACCENT_DARK)
                knob.configure(bg=BG)
                knob.place(x=22, y=2)
            else:
                track.configure(bg=BAR_BG)
                knob.configure(bg=FG_SECONDARY)
                knob.place(x=2, y=2)

        def toggle(event=None):
            var.set(not var.get())
            render()

        track.bind("<Button-1>", toggle)
        knob.bind("<Button-1>", toggle)
        # Кликабельность по всей площади
        for w in (switch,):
            w.bind("<Button-1>", toggle)

        render()

    def _make_button(self, parent, text, command, primary=False):
        """Кнопка с hover-эффектом."""
        bg = BTN_ACTIVE if primary else BTN_BG
        fg = BG if primary else FG
        hover_bg = ACCENT_DARK if primary else BTN_HOVER
        font = _FONT_BTN if primary else _FONT_BTN_SECONDARY

        btn = tk.Button(
            parent,
            text=text,
            command=command,
            bg=bg,
            fg=fg,
            font=font,
            relief=tk.FLAT,
            padx=18,
            pady=7,
            cursor="hand2",
            borderwidth=0,
            highlightthickness=0,
        )
        self._bind_hover(btn, bg, hover_bg)
        return btn

    def _bind_hover(self, widget, normal_bg, hover_bg):
        """Привязать hover-эффект к виджету."""
        widget.bind("<Enter>", lambda e: widget.configure(bg=hover_bg))
        widget.bind("<Leave>", lambda e: widget.configure(bg=normal_bg))

    def _add_section(self, parent, title):
        # Совместимость: теперь используется _add_card, но оставим на всякий случай
        tk.Label(
            parent,
            text=title,
            font=_FONT_SECTION,
            fg=ACCENT,
            bg=BG,
        ).pack(anchor=tk.W, pady=(10, 4), padx=5)

    def _update_profile_info(self):
        """Обновить информацию о профиле (с проверкой, что виджет существует)."""
        # Проверяем, что окно ещё существует
        try:
            if not self.window.winfo_exists():
                return
        except:
            return
        
        profile = self.profile_manager.get_active_profile()
        if profile:
            phase_count = len(profile.phases)
            self.profile_label.config(text=f"{profile.name} ({phase_count} фаз)")
        else:
            self.profile_label.config(text="Не выбран")

    def _update_combos_from_profile(self):
        """Обновить combobox'ы значениями из активного профиля."""
        profile = self.profile_manager.get_active_profile()
        if profile and profile.phases:
            # Берём длительность первого спринта
            for phase in profile.phases:
                if phase.type == "sprint":
                    self.sprint_var.set(str(phase.duration))
                    break
            # Берём длительность первого перерыва
            for phase in profile.phases:
                if phase.type == "break":
                    self.break_var.set(str(phase.duration))
                    break
            # Количество спринтов
            sprint_count = sum(1 for p in profile.phases if p.type == "sprint")
            self.repeats_var.set(str(max(1, sprint_count)))

    def _edit_profiles(self):
        """Открыть редактор профилей."""
        def on_profile_applied():
            """Вызывается при применении/сохранении профиля в ProfileEditor."""
            self._update_profile_info()
            self._update_combos_from_profile()
            self.profile_manager.apply_profile_to_logic(self.logic)
            self.on_settings_changed()

        try:
            editor = ProfileEditor(self.window, self.profile_manager, on_profile_applied)
            self.window.wait_window(editor.window)
            
            # Проверяем, что окно ещё существует перед обновлением
            if self.window.winfo_exists():
                self._update_profile_info()
                self.profile_manager.apply_profile_to_logic(self.logic)
                self.on_settings_changed()
        except Exception as e:
            print(f"Ошибка при открытии редактора профилей: {e}")

    def _pick_click_point(self):
        """Выбрать точку клика — обратный отсчёт 3 сек, потом читаем позицию курсора.

        Использует ctypes.GetCursorPos (логические пиксели) — то же пространство
        координат, что SetCursorPos при клике. Это устраняет смещение при
        DPI-масштабировании (125%, 150% и т.д.) на ноутбуках.
        Старый способ через pynput.Listener оставлен как запасной.
        """
        try:
            import ctypes, ctypes.wintypes
            HAVE_CTYPES = True
        except ImportError:
            HAVE_CTYPES = False

        if not HAVE_CTYPES:
            self._pick_via_pynput()
            return

        self.pick_status.config(
            text="👆 Наведи курсор на нужную кнопку и жди отсчёта...", fg=ACCENT
        )
        self.pick_btn.config(text="⏳ 3...", state=tk.DISABLED)
        self.window.attributes("-alpha", 0.3)

        def _countdown(n):
            try:
                if not self.window.winfo_exists():
                    return
                if n > 0:
                    self.pick_btn.config(text=f"⏳ {n}...")
                    self.window.after(1000, lambda: _countdown(n - 1))
                else:
                    pt = ctypes.wintypes.POINT()
                    ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
                    x, y = pt.x, pt.y
                    self.window.attributes("-alpha", 1.0)
                    self.pick_btn.config(text="📍 Указать", state=tk.NORMAL)
                    self.click_x_var.set(str(x))
                    self.click_y_var.set(str(y))
                    self.pick_status.config(
                        text=f"✅ Выбрано: ({x}, {y})", fg="#4ecdc4"
                    )
            except Exception:
                try:
                    self.window.attributes("-alpha", 1.0)
                    self.pick_btn.config(text="📍 Указать", state=tk.NORMAL)
                    self.pick_status.config(text="❌ Ошибка выбора", fg="#ff6b6b")
                except Exception:
                    pass

        self.window.after(0, lambda: _countdown(3))

    def _pick_via_pynput(self):
        """Запасной вариант выбора через pynput (может давать смещение при DPI != 100%)."""
        import threading
        try:
            from pynput.mouse import Listener
        except ImportError:
            self.pick_status.config(text="❌ Нет pynput: pip install pynput", fg="#ff6b6b")
            return

        self.pick_status.config(text="👆 Кликни мышкой на нужную кнопку...", fg=ACCENT)
        self.pick_btn.config(text="⏳ Выбор...", state=tk.DISABLED)
        self.window.attributes("-alpha", 0.3)
        picked = {"x": None, "y": None}

        def _listen():
            def on_click(x, y, button, pressed):
                if pressed:
                    picked["x"] = int(x)
                    picked["y"] = int(y)
                    return False
            with Listener(on_click=on_click) as listener:
                listener.join()
            try:
                if self.window.winfo_exists():
                    self.window.after(0, _on_done)
            except Exception:
                pass

        def _on_done():
            try:
                self.window.attributes("-alpha", 1.0)
                self.pick_btn.config(text="📍 Указать", state=tk.NORMAL)
                if picked["x"] is not None:
                    self.click_x_var.set(str(picked["x"]))
                    self.click_y_var.set(str(picked["y"]))
                    self.pick_status.config(
                        text=f"✅ Выбрано: ({picked['x']}, {picked['y']})", fg="#4ecdc4"
                    )
                else:
                    self.pick_status.config(text="❌ Выбор отменён", fg="#ff6b6b")
            except Exception:
                pass

        threading.Thread(target=_listen, daemon=True).start()

    def _update_sync_info(self) -> None:
        """Show last remote commit time in sync info label."""
        try:
            if self.sync_manager:
                info = self.sync_manager.get_last_remote_info()
                self.sync_info_label.config(text="GitHub: " + info, fg=FG_SECONDARY)
            else:
                self.sync_info_label.config(text="(sync manager не подключён)", fg=FG_SECONDARY)
        except Exception:
            pass

    def _do_sync_now(self) -> None:
        """Manual sync button handler."""
        from src.core.storage import save_logic_progress
        try:
            save_logic_progress(self.logic)
        except Exception:
            pass
        if self.sync_manager:
            self.sync_info_label.config(text="Синхронизация...", fg="#ffd166")
            self.window.update_idletasks()
            self.sync_manager.push("manual: sync from settings", blocking=False)
            self.window.after(3000, self._update_sync_info)
        else:
            self.sync_info_label.config(text="Синхронизация недоступна", fg="#ff6b6b")

    def _save_settings(self):
        try:
            new_settings = {
                "sprint_duration": int(self.sprint_var.get()),
                "break_duration": int(self.break_var.get()),
                "sprint_repeats": int(self.repeats_var.get()),
                "point_price": float(self.price_var.get()),
                "auto_save_interval": int(self.auto_save_var.get()),
                "sound_enabled": self.sound_var.get(),
                "auto_goal_adjustment": self.auto_goal_var.get(),
                "click_x": int(self.click_x_var.get()),
                "click_y": int(self.click_y_var.get()),
                "click_hotkey": self.hotkey_var.get().strip().lower(),
                "sync_enabled": self.sync_enabled_var.get(),
                "auto_push_interval": int(self.auto_push_var.get()),
            }
            if new_settings["sprint_duration"] <= 0:
                raise ValueError("Длительность спринта должна быть > 0")
            if new_settings["break_duration"] < 0:
                raise ValueError("Длительность перерыва не может быть отрицательной")
            if new_settings["point_price"] <= 0:
                raise ValueError("Цена точки должна быть > 0")
            if new_settings["auto_save_interval"] < 10:
                raise ValueError("Интервал автосохранения не может быть меньше 10 секунд")
        except ValueError as e:
            messagebox.showerror("Ошибка", str(e), parent=self.window)
            return

        save_settings(new_settings)

        self.logic.sprint_duration = new_settings["sprint_duration"]
        self.logic.break_duration = new_settings["break_duration"]
        self.logic.sprint_repeats = new_settings["sprint_repeats"]
        self.logic.point_price = new_settings["point_price"]
        self.logic.auto_save_interval = new_settings["auto_save_interval"]
        self.logic.sound_enabled = new_settings["sound_enabled"]
        self.logic.auto_goal_adjustment = new_settings["auto_goal_adjustment"]

        self.profile_manager.apply_profile_to_logic(self.logic)
        self.on_settings_changed()
        self.window.destroy()

    def _reset_defaults(self):
        if messagebox.askyesno("Сброс", "Сбросить все настройки к стандартным?", parent=self.window):
            self.sprint_var.set(str(DEFAULT_SETTINGS["sprint_duration"]))
            self.break_var.set(str(DEFAULT_SETTINGS["break_duration"]))
            self.repeats_var.set(str(DEFAULT_SETTINGS["sprint_repeats"]))
            self.price_var.set(str(DEFAULT_SETTINGS["point_price"]))
            self.auto_save_var.set(str(DEFAULT_SETTINGS["auto_save_interval"]))
            self.sound_var.set(DEFAULT_SETTINGS["sound_enabled"])
            self.auto_goal_var.set(DEFAULT_SETTINGS["auto_goal_adjustment"])
            self.click_x_var.set(str(DEFAULT_SETTINGS.get("click_x", 500)))
            self.click_y_var.set(str(DEFAULT_SETTINGS.get("click_y", 500)))
            self.hotkey_var.set(DEFAULT_SETTINGS.get("click_hotkey", "ctrl+shift+f"))
            self.pick_status.config(text="✅ Сброшено", fg="#4ecdc4")