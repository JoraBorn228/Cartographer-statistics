"""
Редактор профилей спринтов.
"""
import tkinter as tk
from tkinter import ttk, messagebox
from typing import List, Optional

from src.core.profile_manager import SprintProfile, Phase, ProfileManager


class ProfileEditor:
    def __init__(self, parent, profile_manager: ProfileManager, on_update=None):
        self.parent = parent
        self.profile_manager = profile_manager
        self.on_update = on_update or (lambda: None)
        
        self.window = tk.Toplevel(parent)
        self.window.title("📝 Редактор профилей")
        self.window.geometry("700x600")
        self.window.minsize(600, 500)
        self.window.configure(bg="#0f0f23")
        self.window.attributes("-topmost", True)
        
        self.current_profile: Optional[SprintProfile] = None
        self.phase_entries = []
        self.repeat_var = tk.StringVar(value="1")
        
        self._build_ui()
        self._load_profiles()
    
    def _build_ui(self):
        # Заголовок
        header = tk.Frame(self.window, bg="#0f0f23")
        header.pack(fill=tk.X, padx=15, pady=(10, 5))
        
        tk.Label(
            header,
            text="📝 Редактор профилей спринтов",
            font=("Segoe UI", 16, "bold"),
            fg="#00d4aa",
            bg="#0f0f23"
        ).pack(side=tk.LEFT)
        
        # Список профилей
        list_frame = tk.Frame(self.window, bg="#0f0f23")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=5)
        
        tk.Label(
            list_frame,
            text="Список профилей:",
            font=("Segoe UI", 10, "bold"),
            fg="#eaeaea",
            bg="#0f0f23"
        ).pack(anchor=tk.W)
        
        list_row = tk.Frame(list_frame, bg="#0f0f23")
        list_row.pack(fill=tk.X, pady=5)
        
        self.profile_listbox = tk.Listbox(
            list_row,
            bg="#1a1a3e",
            fg="#eaeaea",
            font=("Segoe UI", 10),
            selectbackground="#00d4aa",
            selectforeground="#0f0f23",
            height=4
        )
        self.profile_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.profile_listbox.bind("<<ListboxSelect>>", self._on_profile_select)
        
        # Кнопки управления профилями
        btn_col = tk.Frame(list_row, bg="#0f0f23")
        btn_col.pack(side=tk.RIGHT, padx=(5, 0))
        
        tk.Button(
            btn_col,
            text="➕ Новый",
            command=self._new_profile,
            bg="#00d4aa",
            fg="#0f0f23",
            font=("Segoe UI", 9, "bold"),
            relief=tk.FLAT,
            padx=10,
            pady=3,
            cursor="hand2"
        ).pack(pady=2)
        
        tk.Button(
            btn_col,
            text="🗑 Удалить",
            command=self._delete_profile,
            bg="#ff6b6b",
            fg="#0f0f23",
            font=("Segoe UI", 9, "bold"),
            relief=tk.FLAT,
            padx=10,
            pady=3,
            cursor="hand2"
        ).pack(pady=2)
        
        tk.Button(
            btn_col,
            text="✅ Применить",
            command=self._apply_profile,
            bg="#4ecdc4",
            fg="#0f0f23",
            font=("Segoe UI", 9, "bold"),
            relief=tk.FLAT,
            padx=10,
            pady=3,
            cursor="hand2"
        ).pack(pady=2)
        
        # Редактор профиля
        editor_frame = tk.Frame(self.window, bg="#1a1a3e", relief=tk.GROOVE, bd=1)
        editor_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=5)
        
        # Имя профиля
        name_frame = tk.Frame(editor_frame, bg="#1a1a3e")
        name_frame.pack(fill=tk.X, padx=10, pady=(10, 5))
        
        tk.Label(
            name_frame,
            text="Название:",
            font=("Segoe UI", 10),
            fg="#eaeaea",
            bg="#1a1a3e"
        ).pack(side=tk.LEFT, padx=(0, 10))
        
        self.name_entry = tk.Entry(
            name_frame,
            font=("Segoe UI", 10),
            bg="#2a2a5e",
            fg="#eaeaea",
            insertbackground="#eaeaea",
            width=25
        )
        self.name_entry.pack(side=tk.LEFT)
        
        # Повторы
        repeat_frame = tk.Frame(editor_frame, bg="#1a1a3e")
        repeat_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(
            repeat_frame,
            text="Повторов цикла:",
            font=("Segoe UI", 10),
            fg="#eaeaea",
            bg="#1a1a3e"
        ).pack(side=tk.LEFT, padx=(0, 10))
        
        self.repeat_combo = ttk.Combobox(
            repeat_frame,
            textvariable=self.repeat_var,
            values=list(range(1, 11)),
            width=5,
            state="readonly"
        )
        self.repeat_combo.pack(side=tk.LEFT)
        
        # Список фаз
        phases_frame = tk.Frame(editor_frame, bg="#1a1a3e")
        phases_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        tk.Label(
            phases_frame,
            text="Фазы (спринты и перерывы):",
            font=("Segoe UI", 10, "bold"),
            fg="#eaeaea",
            bg="#1a1a3e"
        ).pack(anchor=tk.W)
        
        self.phases_container = tk.Frame(phases_frame, bg="#1a1a3e")
        self.phases_container.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Кнопки управления фазами
        phase_btn_frame = tk.Frame(phases_frame, bg="#1a1a3e")
        phase_btn_frame.pack(fill=tk.X, pady=5)
        
        tk.Button(
            phase_btn_frame,
            text="➕ Добавить спринт",
            command=lambda: self._add_phase("sprint"),
            bg="#2a2a5e",
            fg="#eaeaea",
            font=("Segoe UI", 9),
            relief=tk.FLAT,
            padx=10,
            pady=3,
            cursor="hand2"
        ).pack(side=tk.LEFT, padx=2)
        
        tk.Button(
            phase_btn_frame,
            text="➕ Добавить перерыв",
            command=lambda: self._add_phase("break"),
            bg="#2a2a5e",
            fg="#eaeaea",
            font=("Segoe UI", 9),
            relief=tk.FLAT,
            padx=10,
            pady=3,
            cursor="hand2"
        ).pack(side=tk.LEFT, padx=2)
        
        tk.Button(
            phase_btn_frame,
            text="🗑 Очистить все",
            command=self._clear_phases,
            bg="#ff6b6b",
            fg="#0f0f23",
            font=("Segoe UI", 9),
            relief=tk.FLAT,
            padx=10,
            pady=3,
            cursor="hand2"
        ).pack(side=tk.LEFT, padx=2)
        
        # Кнопка сохранения
        save_frame = tk.Frame(self.window, bg="#0f0f23")
        save_frame.pack(fill=tk.X, padx=15, pady=(5, 10))
        
        tk.Button(
            save_frame,
            text="💾 Сохранить профиль",
            command=self._save_profile,
            bg="#00d4aa",
            fg="#0f0f23",
            font=("Segoe UI", 11, "bold"),
            relief=tk.FLAT,
            padx=20,
            pady=8,
            cursor="hand2"
        ).pack(side=tk.RIGHT)
        
        tk.Button(
            save_frame,
            text="❌ Закрыть",
            command=self.window.destroy,
            bg="#2a2a5e",
            fg="#eaeaea",
            font=("Segoe UI", 10),
            relief=tk.FLAT,
            padx=15,
            pady=8,
            cursor="hand2"
        ).pack(side=tk.RIGHT, padx=5)
    
    def _load_profiles(self):
        """Загрузить список профилей."""
        self.profile_listbox.delete(0, tk.END)
        for profile in self.profile_manager.profiles:
            is_active = " ✅" if profile.id == self.profile_manager.active_profile_id else ""
            self.profile_listbox.insert(tk.END, f"{profile.name}{is_active}")
        
        if self.profile_manager.profiles:
            self.profile_listbox.selection_set(0)
            self._on_profile_select()
    
    def _on_profile_select(self, event=None):
        """Выбран профиль из списка."""
        selection = self.profile_listbox.curselection()
        if not selection:
            return
        
        idx = selection[0]
        if idx >= len(self.profile_manager.profiles):
            return
        
        profile = self.profile_manager.profiles[idx]
        self.current_profile = profile
        self._load_profile_to_editor(profile)
    
    def _load_profile_to_editor(self, profile: SprintProfile):
        """Загрузить профиль в редактор."""
        self.name_entry.delete(0, tk.END)
        self.name_entry.insert(0, profile.name)
        
        self.repeat_var.set(str(profile.repeat))
        
        self._clear_phases()
        for phase in profile.phases:
            self._add_phase(phase.type, phase.duration)
    
    def _add_phase(self, phase_type: str, duration: int = None):
        """Добавить фазу в редактор."""
        frame = tk.Frame(self.phases_container, bg="#1a1a3e")
        frame.pack(fill=tk.X, pady=2)
        
        # Иконка
        icon = "⏱" if phase_type == "sprint" else "☕"
        label = "Спринт" if phase_type == "sprint" else "Перерыв"
        
        tk.Label(
            frame,
            text=f"{icon} {label}:",
            font=("Segoe UI", 9),
            fg="#eaeaea",
            bg="#1a1a3e",
            width=12,
            anchor=tk.W
        ).pack(side=tk.LEFT)
        
        # Поле ввода длительности
        entry = tk.Entry(
            frame,
            font=("Segoe UI", 9),
            bg="#2a2a5e",
            fg="#eaeaea",
            insertbackground="#eaeaea",
            width=5
        )
        entry.pack(side=tk.LEFT, padx=5)
        entry.insert(0, str(duration or 15))
        
        tk.Label(
            frame,
            text="мин",
            font=("Segoe UI", 9),
            fg="#888",
            bg="#1a1a3e"
        ).pack(side=tk.LEFT, padx=(0, 5))
        
        # Кнопка удаления фазы
        tk.Button(
            frame,
            text="✕",
            command=lambda f=frame: self._remove_phase(f),
            bg="#ff6b6b",
            fg="#0f0f23",
            font=("Segoe UI", 8, "bold"),
            relief=tk.FLAT,
            padx=4,
            pady=1,
            cursor="hand2"
        ).pack(side=tk.LEFT, padx=5)
        
        self.phase_entries.append((frame, entry, phase_type))
    
    def _remove_phase(self, frame):
        """Удалить фазу."""
        frame.destroy()
        self.phase_entries = [e for e in self.phase_entries if e[0] != frame]
    
    def _clear_phases(self):
        """Очистить все фазы."""
        for frame, _, _ in self.phase_entries:
            frame.destroy()
        self.phase_entries.clear()
    
    def _save_profile(self):
        """Сохранить текущий профиль."""
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showerror("Ошибка", "Введите название профиля!", parent=self.window)
            return
        
        if not self.phase_entries:
            messagebox.showerror("Ошибка", "Добавьте хотя бы одну фазу!", parent=self.window)
            return
        
        try:
            repeat = int(self.repeat_var.get())
        except:
            repeat = 1
        
        phases = []
        for frame, entry, phase_type in self.phase_entries:
            try:
                duration = int(entry.get())
                if duration <= 0:
                    raise ValueError("Длительность должна быть > 0")
                phases.append(Phase(phase_type, duration))
            except ValueError:
                messagebox.showerror(
                    "Ошибка",
                    "Введите корректную длительность (целое число минут)",
                    parent=self.window
                )
                return
        
        # Обновляем или создаём профиль
        if self.current_profile:
            self.current_profile.name = name
            self.current_profile.phases = phases
            self.current_profile.repeat = repeat
        else:
            profile = SprintProfile(name=name, phases=phases, repeat=repeat)
            self.profile_manager.add_profile(profile)
            self.current_profile = profile
        
        self.profile_manager._save()
        self._load_profiles()
        self.on_update()
        
        messagebox.showinfo("Успех", f"Профиль '{name}' сохранён!", parent=self.window)
    
    def _new_profile(self):
        """Создать новый профиль."""
        self.current_profile = None
        self.name_entry.delete(0, tk.END)
        self.name_entry.insert(0, "Новый профиль")
        self.repeat_var.set("1")
        self._clear_phases()
        
        # Добавляем стандартные фазы
        self._add_phase("sprint", 15)
        self._add_phase("break", 3)
        self._add_phase("sprint", 15)
        
        self.profile_listbox.selection_clear(0, tk.END)
    
    def _delete_profile(self):
        """Удалить текущий профиль."""
        if not self.current_profile:
            return
        
        if not messagebox.askyesno(
            "Удалить профиль",
            f"Удалить профиль '{self.current_profile.name}'?",
            parent=self.window
        ):
            return
        
        self.profile_manager.delete_profile(self.current_profile.id)
        self.current_profile = None
        self._load_profiles()
        self.on_update()
    
    def _apply_profile(self):
        """Применить текущий профиль."""
        if not self.current_profile:
            return
        
        self.profile_manager.set_active(self.current_profile.id)
        self._load_profiles()
        self.on_update()
        
        messagebox.showinfo(
            "Применено",
            f"Профиль '{self.current_profile.name}' установлен как активный!",
            parent=self.window
        )