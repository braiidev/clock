"""Controller del ToDo: 3 modos (normal, edit, confirm_delete).

Keys normal: a nuevo, e editar, d borrar, Space toggle done,
x toggle recordatorio, ←→ reorder, ↑↓ nav.
"""

from __future__ import annotations

import curses
import calendar
from dataclasses import dataclass
from typing import Any

from .model import TodoModel


@dataclass
class ActionResult:
    needs_save: bool = False


class TodoController:
    def handle(
        self, model: TodoModel, key: int, context: dict[str, Any]
    ) -> ActionResult:
        if model.edit_mode:
            return self._handle_edit(model, key)
        if model.confirm_delete:
            return self._handle_confirm(model, key)
        return self._handle_normal(model, key)

    # ── Edit mode ──

    def _handle_edit(self, model: TodoModel, key: int) -> ActionResult:
        f = model.edit_field

        if key in (curses.KEY_UP, curses.KEY_DOWN):
            delta = 1 if key == curses.KEY_DOWN else -1
            model.edit_nav_field(delta)
            return ActionResult()

        if f != 1 and key in (ord("j"), ord("k")):
            delta = 1 if key == ord("j") else -1
            model.edit_nav_field(delta)
            return ActionResult()

        if f == 0:
            if key in (9, ord(" ")):
                model.edit_toggle_tipo()
                return ActionResult()
        elif f == 1:
            if key in (curses.KEY_BACKSPACE, 127, 8):
                model.temp_texto = model.temp_texto[:-1]
                return ActionResult()
            if 32 <= key <= 126:
                model.temp_texto += chr(key)
                return ActionResult()
        elif f == 2 and model.temp_tipo == "tarea":
            if key in (9, ord(" ")):
                model.edit_toggle_recordarme()
                return ActionResult()

        rec_active = model.temp_tipo == "tarea" and model.temp_recordarme

        if rec_active:
            if f == 3:
                if key in (9, ord(" ")):
                    model.edit_toggle_repetir()
                    return ActionResult()
            if model.temp_repetir:
                if f == 4:
                    return self._handle_days(model, key)
                elif f == 5:
                    return self._handle_adj(model, key, model.edit_adjust_hour)
                elif f == 6:
                    return self._handle_adj(model, key, model.edit_adjust_min)
            else:
                if f == 4:
                    return self._handle_adj(model, key, model.edit_adjust_hour)
                elif f == 5:
                    return self._handle_adj(model, key, model.edit_adjust_min)
                elif f == 6:
                    return self._handle_adj(model, key, model.edit_adjust_day)
                elif f == 7:
                    return self._handle_adj(model, key, model.edit_adjust_month)
                elif f == 8:
                    return self._handle_adj(model, key, model.edit_adjust_year)

        if key in (ord("\n"), 10, 13):
            model.commit_edit()
            return ActionResult(needs_save=True)
        if key == 27:
            model.cancel_edit()
            return ActionResult()
        return ActionResult()

    def _handle_days(self, model: TodoModel, key: int) -> ActionResult:
        if key in (curses.KEY_RIGHT, ord("l")):
            model.edit_nav_days(1)
        elif key in (curses.KEY_LEFT, ord("h")):
            model.edit_nav_days(-1)
        elif key == ord(" "):
            model.edit_toggle_day()
        return ActionResult()

    def _handle_adj(self, model: TodoModel, key: int, fn: Any) -> ActionResult:
        if key in (curses.KEY_RIGHT, ord("l")):
            fn(1)
        elif key in (curses.KEY_LEFT, ord("h")):
            fn(-1)
        return ActionResult()

    # ── Confirm delete ──

    def _handle_confirm(self, model: TodoModel, key: int) -> ActionResult:
        if key in (ord("y"), ord("Y"), ord("s"), ord("S"), ord("\n"), 10, 13):
            model.delete(model.selected_idx)
            model.confirm_delete = False
            return ActionResult(needs_save=True)
        model.confirm_delete = False
        return ActionResult()

    # ── Normal mode ──

    def _reorder(self, model: TodoModel, delta: int) -> ActionResult:
        if not model.todos:
            return ActionResult()
        idx = model.selected_idx
        nxt = idx + delta
        if nxt < 0 or nxt >= len(model.todos):
            return ActionResult()
        model.swap(idx, nxt)
        model.selected_idx = nxt
        model._clamp_scroll()
        return ActionResult(needs_save=True)

    def _handle_normal(self, model: TodoModel, key: int) -> ActionResult:
        if key == ord("a"):
            model.open_edit(idx=None)
            return ActionResult()
        if key in (curses.KEY_UP, ord("k")):
            model.nav(-1)
            return ActionResult()
        if key in (curses.KEY_DOWN, ord("j")):
            model.nav(1)
            return ActionResult()
        if key in (ord("J"), curses.KEY_RIGHT):
            return self._reorder(model, 1)
        if key in (ord("K"), curses.KEY_LEFT):
            return self._reorder(model, -1)
        if key == ord(" ") and model.todos:
            model.toggle_done(model.selected_idx)
            return ActionResult(needs_save=True)
        if key == ord("d") and model.todos:
            model.confirm_delete = True
            return ActionResult()
        if key == ord("e") and model.todos:
            model.open_edit(idx=model.selected_idx)
            return ActionResult()
        if key == ord("x") and model.todos:
            model.toggle_recordarme(model.selected_idx)
            return ActionResult(needs_save=True)
        return ActionResult()
