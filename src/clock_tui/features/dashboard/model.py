"""Modelo del dashboard: aggregates de solo lectura de todas las features.

Sin I/O, sin curses. El main loop construye el snapshot y lo pasa al
controller y view.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from typing import Any

from clock_tui.app.router import (
    VIEW_ALARMS,
    VIEW_STOPWATCH,
    VIEW_TIMERS,
    VIEW_TODO,
)
from clock_tui.core.time_utils import secs_to_hms
from clock_tui.core.recurrence import _next_occurrence, _repeat_days_str


def _todo_is_done(t: dict) -> bool:
    return t.get("done", False) or t.get("status") == "done"


@dataclass
class ActivityRow:
    label: str
    target_view: int
    target_idx: int
    selected: bool = False


@dataclass
class DashboardSnapshot:
    """Immutable snapshot of all dashboard data, built by the main loop."""

    # time
    now: datetime.datetime
    show_seconds: bool = True
    format_24h: bool = True

    # weather (D13: only dashboard)
    weather_line: str | None = None

    # next alarm
    next_alarm: dict | None = None

    # active timers (max 3 shown in dashboard)
    active_timers: list[dict] = field(default_factory=list)

    # stopwatch
    sw_active: bool = False
    sw_elapsed: float = 0.0

    # todo stats
    total_tasks: int = 0
    done_tasks: int = 0

    # snoozed alarms
    snoozed_count: int = 0

    # navigation
    selected_idx: int = 0

    @property
    def activities(self) -> list[ActivityRow]:
        rows: list[ActivityRow] = []
        if self.next_alarm is not None:
            rows.append(
                ActivityRow(
                    label=_fmt_next_alarm(self.next_alarm, self.now),
                    target_view=VIEW_ALARMS,
                    target_idx=0,
                )
            )
        for i, t in enumerate(self.active_timers[:3]):
            hh, mm, ss = secs_to_hms(t.get("remaining", 0))
            name = t.get("name", "Timer")
            rows.append(
                ActivityRow(
                    label=f"\u23f1 {name}  {hh:02d}:{mm:02d}:{ss:02d}",
                    target_view=VIEW_TIMERS,
                    target_idx=t.get("idx", i),
                )
            )
        if len(self.active_timers) > 3:
            rows.append(
                ActivityRow(
                    label=f"\u23f1 +{len(self.active_timers) - 3} m\u00e1s",
                    target_view=VIEW_TIMERS,
                    target_idx=0,
                )
            )
        if self.sw_active:
            hh, mm, ss = secs_to_hms(int(self.sw_elapsed))
            cs = int((self.sw_elapsed - int(self.sw_elapsed)) * 100)
            rows.append(
                ActivityRow(
                    label=f"\u25f7 Crono  {hh:02d}:{mm:02d}:{ss:02d}.{cs:02d}",
                    target_view=VIEW_STOPWATCH,
                    target_idx=0,
                )
            )
        pending = self.total_tasks - self.done_tasks
        if pending > 0:
            rows.append(
                ActivityRow(
                    label=f"\u25a4 {pending} tareas pendientes ({self.done_tasks}/{self.total_tasks})",
                    target_view=VIEW_TODO,
                    target_idx=0,
                )
            )
        if self.snoozed_count > 0:
            rows.append(
                ActivityRow(
                    label=f"\U0001f4a4 {self.snoozed_count} pospuesta(s)",
                    target_view=VIEW_ALARMS,
                    target_idx=0,
                )
            )
        return rows

    @staticmethod
    def format_time(
        now: datetime.datetime, *, show_seconds: bool = True, format_24h: bool = True
    ) -> str:
        if format_24h:
            fmt = "%H:%M:%S" if show_seconds else "%H:%M"
        else:
            fmt = "%I:%M:%S %p" if show_seconds else "%I:%M %p"
        return now.strftime(fmt)

    @staticmethod
    def format_date(now: datetime.datetime) -> str:
        DIAS = ["Lun", "Mar", "Mi\u00e9", "Jue", "Vie", "S\u00e1b", "Dom"]
        MESES = [
            "Ene",
            "Feb",
            "Mar",
            "Abr",
            "May",
            "Jun",
            "Jul",
            "Ago",
            "Sep",
            "Oct",
            "Nov",
            "Dic",
        ]
        return f"{DIAS[now.weekday()]} {now.day} {MESES[now.month - 1]}"


def _fmt_next_alarm(alarm: dict, now: datetime.datetime) -> str:
    a = alarm
    rep = _repeat_days_str(a.get("repeat_days"))
    rep_txt = f" \u21bb{rep}" if rep != "una vez" else ""
    next_dt = _next_occurrence(a["hora"], a["minutos"], a.get("repeat_days"), now)
    total_min = max(0, int((next_dt - now).total_seconds()) // 60)
    days, rest = divmod(total_min, 1440)
    h_rest, m_rest = divmod(rest, 60)
    cuando = f"en {days}d {h_rest}h" if days else f"en {h_rest}h {m_rest}m"
    return f"\u25f7 Pr\u00f3x: {a['nombre']} {a['hora']:02d}:{a['minutos']:02d}{rep_txt}  ({cuando})"
