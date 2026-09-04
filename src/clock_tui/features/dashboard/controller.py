"""Controller del dashboard: Enter jump + u refresh weather.

El dashboard es solo lectura. Solo 2 teclas activas.
"""

from __future__ import annotations

import curses
from dataclasses import dataclass
from typing import Any

from .model import DashboardSnapshot


@dataclass
class ActionResult:
    jump_to: int | None = None
    jump_item: int = 0
    refresh_weather: bool = False


class DashboardController:
    def handle(self, snap: DashboardSnapshot, key: int, context: dict[str, Any]) -> ActionResult:
        if key in (ord("\n"), 10, 13):
            activities = snap.activities
            if activities and 0 <= snap.selected_idx < len(activities):
                row = activities[snap.selected_idx]
                return ActionResult(jump_to=row.target_view, jump_item=row.target_idx)
            return ActionResult()
        if key == ord("u"):
            return ActionResult(refresh_weather=True)
        if key == curses.KEY_DOWN:
            activities = snap.activities
            if snap.selected_idx < len(activities) - 1:
                snap.selected_idx += 1
            return ActionResult()
        if key == curses.KEY_UP:
            if snap.selected_idx > 0:
                snap.selected_idx -= 1
            return ActionResult()
        return ActionResult()
