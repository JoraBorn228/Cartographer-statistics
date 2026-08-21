"""
Основная бизнес-логика приложения.
"""
import time
import math
from typing import Optional, List, Dict, Callable, Any
from datetime import datetime, timedelta

import keyboard

from src.core.models import Session
from src.core.profile_manager import ProfileManager
from src.utils.config import RANKS
from src.utils.helpers import (
    calc_level,
    get_productive_tab_time,
    parse_tab_title,
    get_active_window_title,
    calc_points_per_hour,
    is_productive_tab
)


class TrackerLogic:
    def __init__(self, on_update=None, on_beep=None, on_level_up=None, profile_manager=None):
        self.on_update = on_update or (lambda: None)
        self.on_beep = on_beep or (lambda f, d: None)
        self.on_level_up = on_level_up or (lambda: None)

        # Общее количество точек
        self.points = 0
        self.level = 1

        # Настройки (будут переопределены из профиля)
        self.sprint_duration = 15
        self.break_duration = 5
        self.sprint_repeats = 1
        self.point_price = 1.3
        self.auto_save_interval = 60
        self.sound_enabled = True
        self.auto_goal_adjustment = True

        # Менеджер профилей — используем переданный или создаём новый
        self.profile_manager = profile_manager or ProfileManager()
        self._current_phase_duration = 0  # длительность текущей фазы в секундах

        # Цель на день
        self.daily_goal = 0
        self.goal_start_date = time.strftime("%Y-%m-%d")
        self._goal_achieved_notified = False

        # Общая цель
        self.total_goal = 0
        self.total_goal_achieved_notified = False

        # Сессии и состояние
        self.session_active = False
        self.session_start: Optional[float] = None
        self.session_points = 0
        self.tab_times: Dict[str, float] = {}
        self.current_tab = ""
        self._last_tab_poll = 0.0
        self.sessions: List[Session] = []

        # Фазы спринта
        self.current_phase = "idle"
        self.current_phase_start: Optional[float] = None
        self.current_sprint_index = 0
        self.current_cycle = 0
        self.sprint_finished = False
        self._recording = False

        # Флаги для предупреждений
        self._sprint_warning_sent = False
        self._break_warning_sent = False

        # Пауза
        self.paused = False
        self.pause_start: Optional[float] = None
        self.paused_accumulated: float = 0.0

        # Хоткей
        self._hotkey_registered = False
        self._hotkey_latch = False
        self._hotkey_handle = None
        self._closing = False

        # Автосохранение
        self.last_auto_save = time.time()

        # Реальные заработки
        self.real_earnings: Dict[str, float] = {}

        # Цели (прогнозы)
        self.goals: List[Dict] = []
        self.active_goal_id: Optional[str] = None

        # История скорости внутри сессии: список (timestamp, points_per_hour)
        self.speed_history: List[tuple] = []
        self._last_speed_snapshot = 0.0  # время последнего снимка

        # Применяем активный профиль при старте
        self._apply_profile()

    # ---------- Профили ----------
    def _apply_profile(self):
        """Применить активный профиль к настройкам."""
        profile = self.profile_manager.get_active_profile()
        if profile and profile.phases:
            # Берём первую фазу как основную
            first_phase = profile.phases[0]
            if first_phase.type == "sprint":
                self.sprint_duration = first_phase.duration
            else:
                self.sprint_duration = 15

            # Ищем первый перерыв
            for phase in profile.phases:
                if phase.type == "break":
                    self.break_duration = phase.duration
                    break
            else:
                self.break_duration = 5

            # Количество повторов = количество спринтов в профиле
            sprint_count = sum(1 for p in profile.phases if p.type == "sprint")
            self.sprint_repeats = max(1, sprint_count)
            return True
        return False

    def get_phase_duration(self, phase_type: str, index: int) -> int:
        """Получить длительность фазы из профиля."""
        profile = self.profile_manager.get_active_profile()
        if profile and index < len(profile.phases):
            phase = profile.phases[index]
            if phase.type == phase_type:
                return phase.duration * 60  # в секундах
        # Fallback
        if phase_type == "sprint":
            return self.sprint_duration * 60
        else:
            return self.break_duration * 60

    def get_profile_phases(self) -> List[Dict]:
        """Получить список фаз из активного профиля."""
        return self.profile_manager.get_profile_phases(self.profile_manager.active_profile_id)

    # ---------- Ранги ----------
    def get_rank(self) -> str:
        rank = "Стажёр"
        for threshold, name in sorted(RANKS.items()):
            if self.points >= threshold:
                rank = name
        return rank

    # ---------- Точки за сегодня ----------
    def get_today_points(self) -> int:
        today = time.strftime("%Y-%m-%d")
        total = 0
        for sess in self.sessions:
            if time.strftime("%Y-%m-%d", time.localtime(sess.started_at)) == today:
                total += sess.points
        if self.session_active and self.session_start:
            if time.strftime("%Y-%m-%d", time.localtime(self.session_start)) == today:
                total += self.session_points
        return total

    # ---------- Заработок ----------
    def get_today_earnings(self) -> float:
        return self.get_today_points() * self.point_price

    def get_total_earnings(self) -> float:
        return self.points * self.point_price

    def get_session_earnings(self, session: Session) -> float:
        return session.points * self.point_price

    # ---------- Цель на день ----------
    def set_daily_goal(self, goal_points: int) -> None:
        self.daily_goal = max(0, goal_points)
        self.goal_start_date = time.strftime("%Y-%m-%d")
        self._goal_achieved_notified = False
        self.on_update()

    def get_daily_goal_progress(self) -> float:
        if self.daily_goal <= 0:
            return 0.0
        today_pts = self.get_today_points()
        return min(1.0, today_pts / self.daily_goal)

    def get_goal_eta(self) -> Optional[float]:
        goal = self.daily_goal
        if goal <= 0:
            return None
        today_points = self.get_today_points()
        remaining = goal - today_points
        if remaining <= 0:
            return 0.0
        current_speed = None
        if self.session_active and self.session_points > 0:
            prod_time = self.get_current_productive_seconds()
            if prod_time > 0:
                current_speed = self.session_points / (prod_time / 3600)
        if current_speed is None:
            today = time.strftime("%Y-%m-%d")
            total_pts = 0
            total_prod = 0.0
            for sess in self.sessions:
                if time.strftime("%Y-%m-%d", time.localtime(sess.started_at)) == today:
                    total_pts += sess.points
                    total_prod += get_productive_tab_time(sess.tab_times)
            if total_prod > 0:
                current_speed = total_pts / (total_prod / 3600)
        if current_speed is None or current_speed <= 0:
            return None
        return remaining / current_speed

    def suggest_goal_adjustment(self) -> Optional[int]:
        if not self.auto_goal_adjustment:
            return None
        if self.daily_goal <= 0:
            return None
        today = time.strftime("%Y-%m-%d")
        last_7_days = {}
        for sess in self.sessions:
            day = time.strftime("%Y-%m-%d", time.localtime(sess.started_at))
            if day == today:
                continue
            last_7_days[day] = last_7_days.get(day, 0) + sess.points
        if len(last_7_days) < 5:
            return None
        over_perform = 0
        for day, pts in last_7_days.items():
            if pts > self.daily_goal * 1.1:
                over_perform += 1
        if over_perform >= 3:
            new_goal = int(math.ceil(self.daily_goal * 1.15 / 10) * 10)
            return new_goal
        return None

    def _check_day_change(self) -> None:
        today = time.strftime("%Y-%m-%d")
        if self.goal_start_date != today and self.daily_goal > 0:
            self.daily_goal = 0
            self.goal_start_date = today
            self._goal_achieved_notified = False
            self.on_update()

    # ---------- Общая цель ----------
    def set_total_goal(self, goal_points: int) -> None:
        self.total_goal = max(0, goal_points)
        self.total_goal_achieved_notified = False
        self.on_update()

    def get_total_goal_progress(self) -> float:
        if self.total_goal <= 0:
            return 0.0
        return min(1.0, self.points / self.total_goal)

    def get_total_goal_remaining(self) -> int:
        if self.total_goal <= 0:
            return 0
        return max(0, self.total_goal - self.points)

    def get_total_goal_time_remaining(self) -> Optional[float]:
        goal = self.total_goal
        if goal <= 0:
            return None
        remaining = goal - self.points
        if remaining <= 0:
            return 0.0
        
        days = {}
        for sess in self.sessions:
            day = time.strftime("%Y-%m-%d", time.localtime(sess.started_at))
            days[day] = days.get(day, 0) + sess.points
        
        if not days:
            return None
        
        total_points = sum(days.values())
        days_count = len(days)
        avg_per_day = total_points / days_count if days_count > 0 else 0
        
        if avg_per_day <= 0:
            return None
        
        return remaining / avg_per_day

    # ---------- Активная цель (прогнозы) ----------
    def add_goal(self, name: str, target_amount: float, target_date: str, 
                 mode: str, income_source: str) -> str:
        goal_id = str(time.time())
        goal = {
            'id': goal_id,
            'name': name,
            'target_amount': target_amount,
            'target_date': target_date,
            'mode': mode,
            'income_source': income_source,
            'created_at': time.time(),
        }
        self.goals.append(goal)
        if self.active_goal_id is None:
            self.active_goal_id = goal_id
        self.on_update()
        return goal_id

    def delete_goal(self, goal_id: str) -> None:
        self.goals = [g for g in self.goals if g['id'] != goal_id]
        if self.active_goal_id == goal_id:
            self.active_goal_id = self.goals[0]['id'] if self.goals else None
        self.on_update()

    def set_active_goal(self, goal_id: str) -> None:
        if any(g['id'] == goal_id for g in self.goals):
            self.active_goal_id = goal_id
            self.on_update()

    def get_active_goal(self) -> Optional[Dict]:
        for goal in self.goals:
            if goal['id'] == self.active_goal_id:
                return goal
        return None

    def _get_current_period_days(self):
        """Возвращает дни текущего периода (1-15 или 16-конец месяца)."""
        import calendar
        import datetime
        now = time.localtime()
        year, month, day = now.tm_year, now.tm_mon, now.tm_mday
        
        if day <= 15:
            start_day, end_day = 1, 15
        else:
            _, last_day = calendar.monthrange(year, month)
            start_day, end_day = 16, last_day
        
        # Собираем все даты в этом периоде за текущий месяц
        period_days = set()
        for d in range(start_day, end_day + 1):
            try:
                dt = datetime.date(year, month, d)
                period_days.add(dt.strftime("%Y-%m-%d"))
            except ValueError:
                pass
        
        return period_days

    def _calculate_goal_stats(self):
        daily_data = {}
        for sess in self.sessions:
            day = time.strftime("%Y-%m-%d", time.localtime(sess.started_at))
            if day not in daily_data:
                daily_data[day] = {'points': 0, 'hours': 0.0}
            daily_data[day]['points'] += sess.points
            daily_data[day]['hours'] += get_productive_tab_time(sess.tab_times) / 3600.0
        
        if self.session_active and self.session_points > 0:
            today = time.strftime("%Y-%m-%d", time.localtime())
            if today not in daily_data:
                daily_data[today] = {'points': 0, 'hours': 0.0}
            daily_data[today]['points'] += self.session_points
        
        # Получаем дни текущего периода
        period_days = self._get_current_period_days()
        
        real_earnings = getattr(self, 'real_earnings', {})
        if not isinstance(real_earnings, dict):
            real_earnings = {}
        point_price = self.point_price
        tax_rate = 0.13
        
        # === ЗАРАБОТАНО ЗА ТЕКУЩИЙ ПЕРИОД (для вычитания из цели) ===
        total_real_after_tax = 0.0
        approx_by_real_days = 0.0
        
        for day, data in daily_data.items():
            if day not in period_days:
                continue
            real = real_earnings.get(day, 0.0)
            real_after_tax = real * (1 - tax_rate) if real > 0 else 0.0
            if real_after_tax > 0:
                total_real_after_tax += real_after_tax
            # Приблизительный заработок: ВСЕ точки периода × цена
            approx_by_real_days += data['points'] * point_price
        
        # === СРЕДНИЕ ПО ВСЕМ ДАННЫМ (для прогноза скорости/дохода) ===
        total_points = 0
        total_hours = 0.0
        days_with_data = 0
        
        for day, data in daily_data.items():
            real = real_earnings.get(day, 0.0)
            real_after_tax = real * (1 - tax_rate) if real > 0 else 0.0
            
            if real_after_tax > 0 and data['hours'] > 0:
                total_points += data['points']
                total_hours += data['hours']
                days_with_data += 1
        
        avg_daily_real = total_real_after_tax / days_with_data if days_with_data > 0 else 0
        avg_daily_user = (total_points * point_price) / days_with_data if days_with_data > 0 else 0
        
        return {
            'days_with_data': days_with_data,
            'total_real_after_tax': total_real_after_tax,
            'total_approx': approx_by_real_days,
            'total_points': total_points,
            'total_hours': total_hours,
            'avg_daily_real': avg_daily_real,
            'avg_daily_user': avg_daily_user,
        }

    def get_goal_progress(self, goal: Dict) -> Dict:
        goal_amount = goal['target_amount']
        
        stats = self._calculate_goal_stats()
        
        if goal['mode'] == 'from_scratch':
            earned = 0
            mode_label = "С нуля"
        elif goal['mode'] == 'from_real':
            earned = stats['total_real_after_tax']
            mode_label = "От реального"
        else:  # from_approx
            earned = stats['total_approx']
            mode_label = "От приблизительного"
        
        remaining = max(0, goal_amount - earned)
        progress = min(1.0, earned / goal_amount) if goal_amount > 0 else 0
        
        avg_daily = stats['avg_daily_real'] if goal['income_source'] == 'real' else stats['avg_daily_user']
        
        try:
            target_date = datetime.strptime(goal['target_date'], "%Y-%m-%d")
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            days_until = max(1, (target_date - today).days)
        except:
            days_until = 30
        
        needed_per_day = remaining / days_until if days_until > 0 else 0
        point_price = self.point_price
        needed_points_per_day = needed_per_day / point_price if point_price > 0 else 0
        total_points_needed = remaining / point_price if point_price > 0 else 0
        
        return {
            'remaining': remaining,
            'progress': progress,
            'earned': earned,
            'needed_per_day': needed_per_day,
            'needed_points_per_day': needed_points_per_day,
            'total_points_needed': total_points_needed,
            'days_until': days_until,
            'mode_label': mode_label,
            'avg_daily': avg_daily,
        }

    # ---------- Звуки предупреждений ----------
    def _play_warning_sound(self, pattern: str = "short"):
        if not self.sound_enabled:
            return
        import threading

        def _beep():
            try:
                import winsound
                import time as _time
                if pattern == "short":
                    winsound.Beep(880, 150)
                    _time.sleep(0.1)
                    winsound.Beep(880, 150)
                elif pattern == "long":
                    winsound.Beep(440, 300)
                    _time.sleep(0.15)
                    winsound.Beep(660, 300)
                elif pattern == "sprint_end":
                    winsound.Beep(880, 200)
                    _time.sleep(0.1)
                    winsound.Beep(660, 200)
            except Exception:
                pass

        threading.Thread(target=_beep, daemon=True).start()

    # ---------- Пауза ----------
    def toggle_pause(self) -> None:
        if not self.session_active:
            return
        if self.current_phase != "sprint":
            return

        if not self.paused:
            self._flush_tab_time()
        self.paused = not self.paused

        if self.paused:
            self.pause_start = time.time()
        else:
            if self.pause_start:
                self.paused_accumulated += time.time() - self.pause_start
                self.pause_start = None

        self.on_update()

    def get_effective_phase_time(self) -> float:
        if not self.session_active or self.current_phase_start is None:
            return 0.0
        elapsed = time.time() - self.current_phase_start
        current_pause = time.time() - self.pause_start if self.paused and self.pause_start else 0.0
        return max(0.0, elapsed - self.paused_accumulated - current_pause)

    # ---------- Сессия ----------
    def start_session(self) -> None:
        if self.session_active:
            return
        
        # Применяем профиль перед стартом
        self._apply_profile()
        
        now = time.time()
        self.session_active = True
        self.session_start = now
        self.session_points = 0
        self.tab_times = {}
        self.current_tab = ""
        self._last_tab_poll = now
        self.current_sprint_index = 0
        self.current_cycle = 0
        self.sprint_finished = False
        self._goal_achieved_notified = False
        self.total_goal_achieved_notified = False
        self._sprint_warning_sent = False
        self._break_warning_sent = False
        self.paused = False
        self.pause_start = None
        self.paused_accumulated = 0.0
        self.speed_history = []
        self._last_speed_snapshot = now

        self._start_phase("sprint")
        self.on_update()

    def stop_session(self) -> None:
        if not self.session_active:
            return
        self._flush_tab_time()
        now = time.time()
        started = self.session_start or now

        if self.session_points > 0 or self.tab_times:
            self.sessions.append(Session(
                started_at=started,
                ended_at=now,
                points=self.session_points,
                tab_times=dict(self.tab_times),
            ))

        self.session_active = False
        self.session_start = None
        self.current_phase = "idle"
        self.current_phase_start = None
        self.sprint_finished = False
        self.current_sprint_index = 0
        self.current_cycle = 0
        self._recording = False
        self._sprint_warning_sent = False
        self._break_warning_sent = False
        self.paused = False
        self.pause_start = None
        self.paused_accumulated = 0.0

        self.on_update()

    # ---------- Спринты ----------
    def _start_phase(self, phase: str) -> None:
        if not self.session_active:
            return
        
        self.current_phase = phase
        self.current_phase_start = time.time()
        self._recording = (phase == "sprint")
        self._sprint_warning_sent = False
        self._break_warning_sent = False
        self.paused = False
        self.pause_start = None
        self.paused_accumulated = 0.0

        # Получаем длительность из профиля
        profile = self.profile_manager.get_active_profile()
        if profile and self.current_sprint_index < len(profile.phases):
            current_phase_obj = profile.phases[self.current_sprint_index]
            if current_phase_obj.type == phase:
                self._current_phase_duration = current_phase_obj.duration * 60
            else:
                # Если тип не совпадает, используем стандартные значения
                self._current_phase_duration = (self.sprint_duration if phase == "sprint" else self.break_duration) * 60
        else:
            self._current_phase_duration = (self.sprint_duration if phase == "sprint" else self.break_duration) * 60

        if phase == "sprint":
            self._play_warning_sound("short")
        else:
            self._play_warning_sound("long")
        self.on_update()

    def _check_phase_complete(self) -> None:
        if not self.session_active or self.current_phase_start is None:
            return

        elapsed = self.get_effective_phase_time()
        duration = self._current_phase_duration
        remaining = duration - elapsed

        if self.current_phase == "sprint":
            if remaining <= 10 and remaining > 0 and not self._sprint_warning_sent:
                self._sprint_warning_sent = True
                self._play_warning_sound("short")

            if remaining > 10:
                self._sprint_warning_sent = False

            if elapsed >= duration:
                self._sprint_warning_sent = False
                
                self._advance_phase()
        else:  # break
            if remaining <= 5 and remaining > 0 and not self._break_warning_sent:
                self._break_warning_sent = True
                self._play_warning_sound("long")

            if remaining > 5:
                self._break_warning_sent = False

            if elapsed >= duration:
                self._break_warning_sent = False
                
                self._advance_phase()

    def _advance_phase(self) -> None:
        """Перейти к следующей фазе или завершить все повторы профиля."""
        profile = self.profile_manager.get_active_profile()
        if not profile or not profile.phases:
            self.sprint_finished = True
        elif self.current_sprint_index + 1 < len(profile.phases):
            self.current_sprint_index += 1
            self._start_phase(profile.phases[self.current_sprint_index].type)
            return
        elif self.current_cycle + 1 < max(1, profile.repeat):
            self.current_cycle += 1
            self.current_sprint_index = 0
            self._start_phase(profile.phases[0].type)
            return
        else:
            self.sprint_finished = True

        self.current_phase = "idle"
        self.current_phase_start = None
        self._recording = False
        self._play_warning_sound("sprint_end")
        self.on_update()

    def skip_break(self) -> None:
        """Пропустить текущий перерыв и перейти к следующей фазе."""
        if not self.session_active:
            return
        if self.current_phase != "break":
            return
        self._advance_phase()

    def restore_active_session(self, data: Dict[str, Any]) -> bool:
        """Восстановить сохранённую сессию в паузе, чтобы не учитывать время простоя."""
        if not data or not data.get("active") or not data.get("started_at"):
            return False
        phase = data.get("current_phase", "idle")
        if phase not in ("sprint", "break"):
            return False

        self.session_active = True
        self.session_start = float(data["started_at"])
        self.session_points = int(data.get("points", 0))
        self.tab_times = dict(data.get("tab_times", {}))
        self.current_phase = phase
        self.current_sprint_index = max(0, int(data.get("current_sprint_index", 0)))
        self.current_cycle = max(0, int(data.get("current_cycle", 0)))
        self.sprint_finished = bool(data.get("sprint_finished", False))
        self.current_tab = str(data.get("current_tab", ""))
        self._last_tab_poll = time.time()
        self._recording = phase == "sprint" and not self.sprint_finished
        self._current_phase_duration = self.get_phase_duration(phase, self.current_sprint_index)
        
        # Восстанавливаем phase_start с учётом прошедшего времени
        saved_phase_start = data.get("phase_start")
        if saved_phase_start:
            elapsed_since_save = time.time() - float(saved_phase_start)
            self.current_phase_start = time.time() - elapsed_since_save
        else:
            self.current_phase_start = time.time()
        
        # Восстанавливаем состояние паузы из сохранённых данных
        # Если paused отсутствует в данных (старый формат), считаем что сессия была на паузе
        self.paused = data.get("paused", True)
        self.pause_start = data.get("pause_start")
        self.paused_accumulated = float(data.get("paused_accumulated", 0.0))
        
        # Если сессия была на паузе при сохранении, ставим pause_start на "сейчас"
        if self.paused and self.pause_start is None:
            self.pause_start = time.time()
        
        return True

    def _update_phase_progress(self) -> tuple[Optional[str], float, float]:
        if not self.session_active or self.current_phase_start is None:
            return None, 0.0, 0.0

        elapsed = self.get_effective_phase_time()
        total = self._current_phase_duration

        remaining = max(0.0, total - elapsed)
        progress = elapsed / total if total > 0 else 0
        return self.current_phase, remaining, min(progress, 1.0)

    # ---------- Нажатия ----------
    def on_point(self) -> None:
        if not self.session_active:
            return

        if self.paused:
            return

        if self.current_phase == "break":
            return

        if self.current_phase != "sprint" or self.sprint_finished:
            return

        self.points += 1
        self.session_points += 1

        new_level = calc_level(self.points)
        if new_level > self.level:
            self.level = new_level
            self.on_level_up()

        if self.daily_goal > 0:
            progress = self.get_daily_goal_progress()
            if progress >= 1.0 and not self._goal_achieved_notified:
                self._goal_achieved_notified = True

        if self.total_goal > 0:
            progress_total = self.get_total_goal_progress()
            if progress_total >= 1.0 and not self.total_goal_achieved_notified:
                self.total_goal_achieved_notified = True

        self.on_update()

    # ---------- Вкладки ----------
    def _flush_tab_time(self) -> None:
        if not self.session_active or self.paused or not self.current_tab or not self._recording:
            return
        now = time.time()
        elapsed = now - self._last_tab_poll
        if elapsed > 0:
            self.tab_times[self.current_tab] = (
                self.tab_times.get(self.current_tab, 0.0) + elapsed
            )
        self._last_tab_poll = now

    def poll_active_tab(self) -> None:
        if not self.session_active:
            return
        raw = get_active_window_title()
        tab = parse_tab_title(raw)
        now = time.time()

        if tab != self.current_tab:
            self._flush_tab_time()
            self.current_tab = tab
            self._last_tab_poll = now
            self.on_update()

    def get_current_productive_seconds(self) -> float:
        if not self.session_active:
            return 0.0
        productive = get_productive_tab_time(self.tab_times)
        # Не добавляем текущий незафлашенный отрезок если на паузе
        if not self.paused and self._recording and self.current_tab and is_productive_tab(self.current_tab):
            now = time.time()
            elapsed = now - self._last_tab_poll
            if elapsed > 0:
                productive += elapsed
        return productive

    # ---------- Хоткей ----------
    def register_hotkey(self) -> None:
        def on_hotkey() -> None:
            if self._closing or self._hotkey_latch:
                return
            self._hotkey_latch = True
            self.on_point()

        def release_latch(_event) -> None:
            self._hotkey_latch = False

        try:
            self._hotkey_handle = keyboard.add_hotkey(
                "ctrl+a", on_hotkey, suppress=False, trigger_on_release=False
            )
            for key in ("a", "ctrl", "left ctrl", "right ctrl"):
                keyboard.on_release_key(key, release_latch, suppress=False)
            self._hotkey_registered = True
        except Exception as exc:
            print(f"Не удалось зарегистрировать Ctrl+A: {exc}")

    def unregister_hotkey(self) -> None:
        if self._hotkey_registered:
            try:
                keyboard.unhook_all()
            except Exception:
                pass
            self._hotkey_registered = False

    # ---------- Тик ----------
    def tick(self) -> None:
        if self._closing:
            return

        self._check_day_change()

        if self.session_active:
            self.poll_active_tab()
            if time.time() - self._last_tab_poll >= 500 / 1000:
                self._flush_tab_time()
                self._last_tab_poll = time.time()

        if self.session_active and self.current_phase != "idle":
            self._check_phase_complete()

        # Записываем снимок скорости каждые 30 секунд во время спринта
        if (self.session_active and self.current_phase == "sprint"
                and not self.paused
                and time.time() - self._last_speed_snapshot >= 30):
            self.record_speed_snapshot()

        self.on_update()

    # ---------- История скорости ----------
    def record_speed_snapshot(self) -> None:
        """3аписать текущую скорость в историю."""
        prod_secs = self.get_current_productive_seconds()
        if prod_secs > 0 and self.session_points > 0:
            speed = self.session_points / (prod_secs / 3600)
            self.speed_history.append((time.time(), speed))
        elif self.session_points == 0:
            # Даже без точек запишем нуль, чтобы график начинался с 0
            self.speed_history.append((time.time(), 0.0))
        self._last_speed_snapshot = time.time()
        # Храним не больше 120 снимков (1 час при интервале 30с)
        if len(self.speed_history) > 120:
            self.speed_history = self.speed_history[-120:]

    def get_speed_history(self, window_minutes: float = 30.0) -> List[tuple]:
        """Vернуть снимки скорости за последние window_minutes минут."""
        if not self.speed_history:
            return []
        cutoff = time.time() - window_minutes * 60
        return [(ts, spd) for ts, spd in self.speed_history if ts >= cutoff]

    def close(self) -> None:
        self._closing = True
        if self.session_active:
            self.stop_session()
        self.unregister_hotkey()

    # ---------- Пересчёт ----------
    def auto_set_goal(self) -> None:
        today = time.strftime("%Y-%m-%d")
        if self.goal_start_date == today and self.daily_goal > 0:
            return

        last_7_days = {}
        for sess in self.sessions:
            day = time.strftime("%Y-%m-%d", time.localtime(sess.started_at))
            if day != today:
                last_7_days[day] = last_7_days.get(day, 0) + sess.points

        if len(last_7_days) < 3:
            new_goal = 100
        else:
            avg = sum(last_7_days.values()) / len(last_7_days)
            new_goal = int(math.ceil(avg * 1.1 / 10) * 10)
            new_goal = max(50, new_goal)

        self.set_daily_goal(new_goal)
