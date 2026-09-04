"""Controller del cronómetro: mutate el modelo según input del usuario.

Patrón: handle(model, key, context) → ActionResult
El controller NUNCA dibuja ni accede a curses.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from .model import StopwatchModel


@dataclass
class ActionResult:
    alert_title: str | None = None
    alert_message: str | None = None
    toggle_pause: bool = False


class StopwatchController:
    """Procesa input del usuario y muta el StopwatchModel."""

    def handle(
        self,
        model: StopwatchModel,
        key: int,
        context: dict[str, Any],
        now: float | None = None,
    ) -> ActionResult:
        """Procesa una tecla y retorna el ActionResult.

        context debe contener:
            - global_paused: bool — estado de pausa global (Esc)
        now: timestamp monotónico (para testing; la app pasa time.monotonic()).
        """
        global_paused = context.get("global_paused", False)

        if key == ord(" "):
            return self._toggle(model, global_paused, now)
        if key == ord("m"):
            return self._lap(model, now)
        if key == ord("d"):
            return self._delete_last_lap(model)
        if key == ord("r"):
            return self._reset(model)
        return ActionResult()

    # ── Space: play / pause ──

    def _toggle(
        self, model: StopwatchModel, global_paused: bool, now: float | None = None
    ) -> ActionResult:
        if model.active:
            model.base_elapsed = model.elapsed(now)
            model.active = False
            model.start_time = None
        else:
            if global_paused:
                return ActionResult()
            model.active = True
            model.start_time = now if now is not None else time.monotonic()
        return ActionResult()

    # ── m: marcar lap ──

    def _lap(self, model: StopwatchModel, now: float | None = None) -> ActionResult:
        if not model.active:
            return ActionResult()
        ref = now if now is not None else time.monotonic()
        elapsed = model.elapsed(ref)
        diff = elapsed - model.last_record_at
        model.last_record_at = elapsed
        model.records.append(diff)
        model.scroll_offset = max(0, len(model.records) - 5)
        return ActionResult()

    # ── d: borrar último lap ──

    def _delete_last_lap(self, model: StopwatchModel) -> ActionResult:
        if not model.records:
            return ActionResult()
        model.records.pop()
        model.last_record_at = sum(model.records) if model.records else 0.0
        model.scroll_offset = max(0, len(model.records) - 5)
        return ActionResult()

    # ── r: reset total ──

    def _reset(self, model: StopwatchModel) -> ActionResult:
        model.active = False
        model.start_time = None
        model.base_elapsed = 0.0
        model.records = []
        model.last_record_at = 0.0
        model.scroll_offset = 0
        return ActionResult()
