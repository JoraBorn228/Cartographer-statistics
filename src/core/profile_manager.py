"""
Управление профилями спринтов.
"""
import json
import time
import uuid
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass, field, asdict


@dataclass
class Phase:
    """Одна фаза спринта (спринт или перерыв)."""
    type: str  # "sprint" или "break"
    duration: int  # в минутах


@dataclass
class SprintProfile:
    """Профиль спринтов."""
    name: str
    phases: List[Phase] = field(default_factory=list)
    repeat: int = 1  # количество повторений всего цикла
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    def total_duration(self) -> int:
        """Общая длительность профиля в минутах."""
        return sum(p.duration for p in self.phases) * self.repeat
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "phases": [{"type": p.type, "duration": p.duration} for p in self.phases],
            "repeat": self.repeat,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "SprintProfile":
        phases = [Phase(**p) for p in data.get("phases", [])]
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            name=data.get("name", "Без названия"),
            phases=phases,
            repeat=data.get("repeat", 1),
        )


class ProfileManager:
    """Менеджер профилей спринтов."""
    
    PROFILES_FILE = Path(__file__).parent.parent.parent / "data" / "profiles.json"
    
    def __init__(self):
        self.profiles: List[SprintProfile] = []
        self.active_profile_id: Optional[str] = None
        self._load()
    
    def _load(self):
        """Загрузить профили из файла."""
        if not self.PROFILES_FILE.exists():
            self._create_default_profiles()
            return
        
        try:
            data = json.loads(self.PROFILES_FILE.read_text(encoding="utf-8"))
            self.profiles = [SprintProfile.from_dict(p) for p in data.get("profiles", [])]
            self.active_profile_id = data.get("active_profile_id")
            seen_ids = set()
            changed = False
            for profile in self.profiles:
                if profile.id in seen_ids:
                    profile.id = str(uuid.uuid4())
                    changed = True
                seen_ids.add(profile.id)
            
            # Если нет активного профиля, берём первый
            if self.active_profile_id is None and self.profiles:
                self.active_profile_id = self.profiles[0].id
                changed = True
            if self.get_profile(self.active_profile_id) is None and self.profiles:
                self.active_profile_id = self.profiles[0].id
                changed = True
            if changed:
                self._save()
        except Exception:
            self._create_default_profiles()
    
    def _save(self):
        """Сохранить профили в файл."""
        self.PROFILES_FILE.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "profiles": [p.to_dict() for p in self.profiles],
            "active_profile_id": self.active_profile_id,
        }
        self.PROFILES_FILE.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
    
    def _create_default_profiles(self):
        """Создать стандартные профили."""
        self.profiles = [
            SprintProfile(
                name="Стандартный",
                phases=[
                    Phase("sprint", 15),
                    Phase("break", 3),
                    Phase("sprint", 15),
                    Phase("break", 5),
                ],
                repeat=1,
            ),
            SprintProfile(
                name="Интенсивный",
                phases=[
                    Phase("sprint", 25),
                    Phase("break", 5),
                    Phase("sprint", 25),
                    Phase("break", 5),
                ],
                repeat=1,
            ),
            SprintProfile(
                name="Маленькие шаги",
                phases=[
                    Phase("sprint", 5),
                    Phase("break", 2),
                    Phase("sprint", 5),
                    Phase("break", 2),
                    Phase("sprint", 5),
                ],
                repeat=1,
            ),
            SprintProfile(
                name="Одиночный спринт",
                phases=[
                    Phase("sprint", 15),
                ],
                repeat=1,
            ),
        ]
        self.active_profile_id = self.profiles[0].id
        self._save()
    
    def get_profile(self, profile_id: str) -> Optional[SprintProfile]:
        """Получить профиль по ID."""
        for p in self.profiles:
            if p.id == profile_id:
                return p
        return None
    
    def get_active_profile(self) -> Optional[SprintProfile]:
        """Получить активный профиль."""
        return self.get_profile(self.active_profile_id)
    
    def add_profile(self, profile: SprintProfile):
        """Добавить новый профиль."""
        self.profiles.append(profile)
        if self.active_profile_id is None:
            self.active_profile_id = profile.id
        self._save()
    
    def delete_profile(self, profile_id: str):
        """Удалить профиль."""
        self.profiles = [p for p in self.profiles if p.id != profile_id]
        if self.active_profile_id == profile_id:
            self.active_profile_id = self.profiles[0].id if self.profiles else None
        self._save()
    
    def set_active(self, profile_id: str):
        """Установить активный профиль."""
        if self.get_profile(profile_id):
            self.active_profile_id = profile_id
            self._save()
    
    def get_profile_phases(self, profile_id: str) -> List[Dict]:
        """Получить фазы профиля для отображения."""
        profile = self.get_profile(profile_id)
        if not profile:
            return []
        
        phases = []
        for i, phase in enumerate(profile.phases):
            icon = "⏱" if phase.type == "sprint" else "☕"
            label = "Спринт" if phase.type == "sprint" else "Перерыв"
            phases.append({
                "icon": icon,
                "label": f"{label} {i+1}",
                "duration": f"{phase.duration} мин",
                "type": phase.type,
            })
        return phases
    
    def apply_profile_to_logic(self, logic):
        """Применить профиль к логике."""
        profile = self.get_active_profile()
        if not profile or not profile.phases:
            return False
        
        # Берём первую фазу как основную
        first_phase = profile.phases[0]
        if first_phase.type == "sprint":
            logic.sprint_duration = first_phase.duration
        else:
            logic.sprint_duration = 15  # fallback
        
        # Ищем первый перерыв
        for phase in profile.phases:
            if phase.type == "break":
                logic.break_duration = phase.duration
                break
        else:
            logic.break_duration = 5  # fallback
        
        # Количество спринтов в профиле
        sprint_count = sum(1 for p in profile.phases if p.type == "sprint")
        logic.sprint_repeats = max(1, sprint_count)
        
        return True
