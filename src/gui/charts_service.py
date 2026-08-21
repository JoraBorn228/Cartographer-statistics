# src/gui/charts_service.py
"""Utility service for chart data aggregation and performance optimizations.

This module centralises all heavy data-processing logic used by ``ChartsWindow``.
It provides:
- Cached aggregation of daily session data.
- Calculation of speed per day.
- Helper methods for best‑day and virtual‑real earnings data.

All public functions are type‑annotated and documented, making them easy to unit‑test
and reuse elsewhere in the project.
"""

from __future__ import annotations

import functools
from typing import List, Dict, Tuple

from src.core.models import Session
from src.utils.helpers import get_productive_tab_time


class ChartsService:
    """Service class offering static methods for chart calculations.

    The methods are deliberately ``@staticmethod`` so they can be called without
    instantiating the class. ``@functools.lru_cache`` is used to memoise
    results based on the ``sessions`` tuple, dramatically reducing the amount of
    work required when the UI refreshes.
    """

    @staticmethod
    @functools.lru_cache(maxsize=32)
    def aggregate_daily_data(sessions: Tuple[Session, ...]) -> Dict[str, Dict[str, int]]:
        """Aggregate points, money and duration per calendar day.

        Parameters
        ----------
        sessions: Tuple[Session, ...]
            Immutable collection of ``Session`` objects.

        Returns
        -------
        dict
            Mapping ``date_str -> {"points": int, "money": int, "duration": int}``.
        """
        daily: Dict[str, Dict[str, int]] = {}
        for sess in sessions:
            date_key = sess.started_at.date().isoformat()
            if date_key not in daily:
                daily[date_key] = {"points": 0, "money": 0, "duration": 0}
            daily[date_key]["points"] += sess.points
            daily[date_key]["money"] += sess.money
            daily[date_key]["duration"] += sess.duration
        return daily

    @staticmethod
    @functools.lru_cache(maxsize=32)
    def calculate_speed_by_day(sessions: Tuple[Session, ...]) -> Dict[str, float]:
        """Calculate average speed (points per hour) for each day.

        Speed is defined as ``points / hours`` where ``hours`` is the productive
        time of the session (excluding break time). The result is a mapping of
        date strings to speed values.
        """
        speed: Dict[str, float] = {}
        for sess in sessions:
            date_key = sess.started_at.date().isoformat()
            prod_seconds = get_productive_tab_time(sess.tab_times)
            if prod_seconds > 0:
                speed[date_key] = speed.get(date_key, 0) + (sess.points / (prod_seconds / 3600))
        return speed

    @staticmethod
    @functools.lru_cache(maxsize=32)
    def best_days_data(sessions: Tuple[Session, ...], top_n: int = 5) -> Tuple[List[str], List[int], List[int]]:
        """Return dates, points and money for the top ``top_n`` days.
        """
        daily = ChartsService.aggregate_daily_data(sessions)
        sorted_items = sorted(daily.items(), key=lambda kv: kv[1]["points"], reverse=True)[:top_n]
        dates = [item[0] for item in sorted_items]
        points = [item[1]["points"] for item in sorted_items]
        money = [item[1]["money"] for item in sorted_items]
        return dates, points, money

    @staticmethod
    @functools.lru_cache(maxsize=32)
    def virtual_real_data(sessions: Tuple[Session, ...]) -> Tuple[List[str], List[float], List[float]]:
        """Prepare data for the virtual vs real earnings chart.
        Returns ``dates, virtual_money, real_money``.
        """
        daily = ChartsService.aggregate_daily_data(sessions)
        dates = sorted(daily.keys())
        virtual: List[float] = []
        real: List[float] = []
        for d in dates:
            money = daily[d]["money"]
            # virtual earnings assume 13% tax on the real money
            virtual.append(money / 0.87)  # reverse tax deduction
            real.append(money)
        return dates, virtual, real

# End of charts_service.py
