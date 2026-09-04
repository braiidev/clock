"""Controller de timers: mutate el modelo según input del usuario.

Patrón: handle(model, key, context) → ActionResult
El controller NUNCA dibuja ni accede a curses.
"""

from __future__ import annotations

import curses
import time
from dataclasses import dataclass, field
from typing import Any

from clock_tui.core.time_utils import hms_to_secs

from .model import Timer, TimersModel, _MAX_TIMERS


@dataclass
class ActionResult:
    needs_save: bool = False
    edit_exit: bool = False
    alert_title: str | None = None
    alert_message: str | None = None


class TimersController:
    """Procesa input del usuario y muta el TimersModel."""

    def handle(
        self,
        model: TimersModel,
        key: int,
        context: dict[str, Any],
        now: float | None = None,
    ) -> ActionResult:
        """Procesa una tecla y retorna el ActionResult."""
        if model.edit_mode:
            return self._handle_edit(model, key)
        return self._handle_normal(model, key, now)

    # ── Edit mode ──

    def _handle_edit(self, model: TimersModel, key: int) -> ActionResult:
        if key in (ord("\n"), 10, 13):
            model.timers[model.edit_target].name = model.temp_name or "Timer"
            model.edit_mode = False
            return ActionResult(needs_save=True, edit_exit=True)
        if key == 27:
            model.edit_mode = False
            return ActionResult(edit_exit=True)
        if key in (curses.KEY_BACKSPACE, 127, 8):
            model.temp_name = model.temp_name[:-1]
            return ActionResult()
        if 32 <= key <= 126:
            model.temp_name += chr(key)
            return ActionResult()
        return ActionResult()

    # ── Normal mode ──

    def _handle_normal(
        self, model: TimersModel, key: int, now: float | None
    ) -> ActionResult:
        if key == curses.KEY_DOWN:
            return self._nav(model, 1)
        if key == curses.KEY_UP:
            return self._nav(model, -1)
        if key == ord("a"):
            return self._add(model)
        if key == ord("d"):
            return self._delete(model)
        if key == ord("e"):
            return self._edit_name(model)
        if key == 9:
            return self._cycle_field(model)
        if key == curses.KEY_RIGHT:
            return self._adjust(model, +1)
        if key == curses.KEY_LEFT:
            return self._adjust(model, -1)
        if key == ord(" "):
            return self._toggle(model, now)
        if key == ord("r"):
            return self._reset_selected(model)
        return ActionResult()

    def _nav(self, model: TimersModel, delta: int) -> ActionResult:
        if not model.timers:
            return ActionResult()
        model.selected_idx = (model.selected_idx + delta) % len(model.timers)
        model._clamp_scroll()
        return ActionResult()

    def _add(self, model: TimersModel) -> ActionResult:
        if len(model.timers) >= _MAX_TIMERS:
            return ActionResult()
        n = len(model.timers) + 1
        t = Timer(name=f"Temporizador{n}")
        model.timers.append(t)
        model.selected_idx = len(model.timers) - 1
        model._clamp_scroll()
        return ActionResult(needs_save=True)

    def _delete(self, model: TimersModel) -> ActionResult:
        if len(model.timers) <= 1:
            return ActionResult()
        model.timers.pop(model.selected_idx)
        if model.selected_idx >= len(model.timers):
            model.selected_idx = max(0, len(model.timers) - 1)
        model._clamp_scroll()
        return ActionResult(needs_save=True)

    def _edit_name(self, model: TimersModel) -> ActionResult:
        t = model.timers[model.selected_idx] if model.timers else None
        if not t:
            return ActionResult()
        model.edit_mode = True
        model.edit_target = model.selected_idx
        model.temp_name = t.name
        return ActionResult()

    def _cycle_field(self, model: TimersModel) -> ActionResult:
        t = model.timers[model.selected_idx] if model.timers else None
        if t and not t.active:
            model.time_field = (model.time_field + 1) % 3
        return ActionResult()

    def _adjust(self, model: TimersModel, delta: int) -> ActionResult:
        t = model.timers[model.selected_idx] if model.timers else None
        if not t or t.active:
            return ActionResult()
        f = model.time_field
        lim = 99 if f == 0 else 59
        t.time[f] = (t.time[f] + delta) % (lim + 1)
        t.remaining = float(hms_to_secs(*t.time))
        return ActionResult(needs_save=True)

    def _toggle(self, model: TimersModel, now: float | None) -> ActionResult:
        t = model.timers[model.selected_idx] if model.timers else None
        if not t:
            return ActionResult()
        if t.active:
            t.active = False
        else:
            if t.remaining <= 0:
                t.remaining = float(hms_to_secs(*t.time))
            t.active = True
            t.started = True
            t.last_tick = now if now is not None else time.monotonic()
        return ActionResult()

    def _reset_selected(self, model: TimersModel) -> ActionResult:
        t = model.timers[model.selected_idx] if model.timers else None
        if not t:
            return ActionResult()
        t.active = False
        t.started = False
        t.last_tick = None
        t.remaining = float(hms_to_secs(*t.time))
        return ActionResult()
