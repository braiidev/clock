"""Controller de alarmas: mutate el modelo según input del usuario.

Patrón: handle(model, key, context) → ActionResult
El controller NUNCA dibuja ni accede a curses.

Modos: normal | edit (3 campos: nombre, hora, días) | confirm_delete
"""

from __future__ import annotations

import curses
from dataclasses import dataclass
from typing import Any

from clock_tui.core.recurrence import _repeat_days_normalize

from .model import Alarm, AlarmsModel


@dataclass
class ActionResult:
    needs_save: bool = False
    edit_exit: bool = False
    postpone: bool = False
    postpone_nombre: str = ""
    postpone_minutes: int = 5


class AlarmsController:
    """Procesa input del usuario y muta el AlarmsModel."""

    def handle(
        self,
        model: AlarmsModel,
        key: int,
        context: dict[str, Any],
        edit_state: dict[str, Any] | None = None,
    ) -> ActionResult:
        """Procesa una tecla y retorna el ActionResult.

        context:
            - edit_state: dict compartido con la UI que contiene:
                edit_mode, edit_target, edit_field, temp_name,
                temp_time, temp_time_field, temp_days, temp_days_cursor,
                confirm_delete
        """
        es = edit_state if edit_state is not None else {}
        if es.get("edit_mode"):
            return self._handle_edit(model, key, es)
        if es.get("confirm_delete"):
            return self._handle_confirm(model, key, es)
        return self._handle_normal(model, key, es, context)

    # ── Edit mode ──

    def _handle_edit(
        self, model: AlarmsModel, key: int, es: dict[str, Any]
    ) -> ActionResult:
        ef = es.get("edit_field", 0)

        if key == 27:
            es["edit_mode"] = False
            es["edit_target"] = None
            return ActionResult(edit_exit=True)

        if key in (curses.KEY_UP, curses.KEY_DOWN):
            es["edit_field"] = (ef + (1 if key == curses.KEY_DOWN else -1)) % 3
            return ActionResult()

        if ef == 0:
            return self._edit_name(key, es)
        if ef == 1:
            return self._edit_time(key, es)
        if ef == 2:
            return self._edit_days(model, key, es)

        return ActionResult()

    def _edit_name(self, key: int, es: dict[str, Any]) -> ActionResult:
        if key in (curses.KEY_BACKSPACE, 127, 8):
            es["temp_name"] = es["temp_name"][:-1]
        elif 32 <= key <= 126:
            es["temp_name"] += chr(key)

        if key in (ord("\n"), 10, 13):
            es["edit_field"] = 1
        return ActionResult()

    def _edit_time(self, key: int, es: dict[str, Any]) -> ActionResult:
        if key == 9:
            es["temp_time_field"] = (es["temp_time_field"] + 1) % 2
        elif key == curses.KEY_RIGHT:
            f = es["temp_time_field"]
            lim = 24 if f == 0 else 60
            es["temp_time"][f] = (es["temp_time"][f] + 1) % lim
        elif key == curses.KEY_LEFT:
            f = es["temp_time_field"]
            lim = 24 if f == 0 else 60
            es["temp_time"][f] = (es["temp_time"][f] - 1) % lim

        if key in (ord("\n"), 10, 13):
            es["edit_field"] = 2
        return ActionResult()

    def _edit_days(
        self, model: AlarmsModel, key: int, es: dict[str, Any]
    ) -> ActionResult:
        if key == curses.KEY_RIGHT:
            es["temp_days_cursor"] = (es["temp_days_cursor"] + 1) % 7
        elif key == curses.KEY_LEFT:
            es["temp_days_cursor"] = (es["temp_days_cursor"] - 1) % 7
        elif key == ord(" "):
            d = es["temp_days_cursor"]
            if d in es["temp_days"]:
                es["temp_days"].remove(d)
            else:
                es["temp_days"].append(d)
            es["temp_days"].sort()

        if key in (ord("\n"), 10, 13):
            return self._save_alarm(model, es)
        return ActionResult()

    def _save_alarm(self, model: AlarmsModel, es: dict[str, Any]) -> ActionResult:
        a = Alarm(
            nombre=es.get("temp_name", "") or "Alarma",
            hora=es["temp_time"][0],
            minutos=es["temp_time"][1],
            status="activado",
            repeat_days=list(es.get("temp_days", [])),
        )
        target = es.get("edit_target")
        if target is not None:
            model.alarms[target] = a
        else:
            model.alarms.append(a)
        es["edit_mode"] = False
        es["edit_target"] = None
        return ActionResult(needs_save=True, edit_exit=True)

    # ── Confirm delete ──

    def _handle_confirm(
        self, model: AlarmsModel, key: int, es: dict[str, Any]
    ) -> ActionResult:
        if key in (ord("y"), ord("Y"), ord("s"), ord("S"), ord("\n"), 10, 13):
            if model.alarms:
                model.alarms.pop(model.selected_idx)
                if model.selected_idx >= len(model.alarms):
                    model.selected_idx = max(0, len(model.alarms) - 1)
                model._clamp_scroll()
            es["confirm_delete"] = False
            return ActionResult(needs_save=True)
        es["confirm_delete"] = False
        return ActionResult()

    # ── Normal mode ──

    def _handle_normal(
        self,
        model: AlarmsModel,
        key: int,
        es: dict[str, Any],
        context: dict[str, Any],
    ) -> ActionResult:
        if key == ord("a"):
            return self._new_alarm(model, es)
        if key == curses.KEY_DOWN:
            return self._nav(model, 1)
        if key == curses.KEY_UP:
            return self._nav(model, -1)
        if key == ord("J"):
            return self._reorder(model, 1)
        if key == ord("K"):
            return self._reorder(model, -1)
        if key == ord(" "):
            return self._toggle(model)
        if key == ord("d"):
            return self._confirm_delete(model, es)
        if key == ord("e"):
            return self._edit_alarm(model, es)
        return ActionResult()

    def _new_alarm(self, model: AlarmsModel, es: dict[str, Any]) -> ActionResult:
        es["edit_mode"] = True
        es["edit_target"] = None
        es["edit_field"] = 0
        es["temp_name"] = "Alarma"
        es["temp_time"] = [0, 0]
        es["temp_time_field"] = 0
        es["temp_days"] = []
        es["temp_days_cursor"] = 0
        return ActionResult()

    def _nav(self, model: AlarmsModel, delta: int) -> ActionResult:
        if not model.alarms:
            return ActionResult()
        model.selected_idx = (model.selected_idx + delta) % len(model.alarms)
        model._clamp_scroll()
        return ActionResult()

    def _reorder(self, model: AlarmsModel, delta: int) -> ActionResult:
        if not model.alarms:
            return ActionResult()
        idx = model.selected_idx
        nxt = idx + delta
        if nxt < 0 or nxt >= len(model.alarms):
            return ActionResult()
        model.swap(idx, nxt)
        model.selected_idx = nxt
        model._clamp_scroll()
        return ActionResult(needs_save=True)

    def _toggle(self, model: AlarmsModel) -> ActionResult:
        if not model.alarms:
            return ActionResult()
        model.alarms[model.selected_idx].toggle()
        return ActionResult(needs_save=True)

    def _confirm_delete(self, model: AlarmsModel, es: dict[str, Any]) -> ActionResult:
        if not model.alarms:
            return ActionResult()
        es["confirm_delete"] = True
        return ActionResult()

    def _edit_alarm(self, model: AlarmsModel, es: dict[str, Any]) -> ActionResult:
        if not model.alarms:
            return ActionResult()
        a = model.alarms[model.selected_idx]
        es["edit_mode"] = True
        es["edit_target"] = model.selected_idx
        es["edit_field"] = 0
        es["temp_name"] = a.nombre
        es["temp_time"] = [a.hora, a.minutos]
        es["temp_time_field"] = 0
        es["temp_days"] = _repeat_days_normalize(a.repeat_days)
        es["temp_days_cursor"] = 0
        return ActionResult()
