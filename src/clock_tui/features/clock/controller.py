"""Controller del reloj: mutate el modelo según input del usuario.

4 modos: normal | picker | edit_nick | confirm_delete
El controller NUNCA dibuja ni accede a curses.
"""

from __future__ import annotations

import curses
from dataclasses import dataclass
from typing import Any

from .model import ClockModel


@dataclass
class ActionResult:
    needs_save: bool = False


class ClockController:
    """Procesa input del usuario y muta el ClockModel."""

    def handle(
        self, model: ClockModel, key: int, context: dict[str, Any]
    ) -> ActionResult:
        if model.picker.open:
            return self._handle_picker(model, key)
        if model.edit_nick.active:
            return self._handle_edit_nick(model, key)
        if model.confirm_delete:
            return self._handle_confirm(model, key)
        return self._handle_normal(model, key)

    # ── Picker ──

    def _handle_picker(self, model: ClockModel, key: int) -> ActionResult:
        p = model.picker
        if p.filter_active:
            if key == 27:
                p.filter_active = False
                p.filter_text = ""
                model._picker_refresh()
                return ActionResult()
            if key in (curses.KEY_BACKSPACE, 127, 8):
                p.filter_text = p.filter_text[:-1]
                model._picker_refresh()
                return ActionResult()
            if key in (ord("\n"), 10, 13):
                model.picker_confirm_zone()
                return ActionResult()
            if 32 <= key <= 126:
                p.filter_text += chr(key)
                model._picker_refresh()
                return ActionResult()
            return ActionResult()

        if key in (curses.KEY_UP, curses.KEY_DOWN):
            delta = 1 if key == curses.KEY_DOWN else -1
            model.picker_nav(delta)
            return ActionResult()
        if key == ord("f"):
            p.filter_active = True
            p.filter_text = ""
            return ActionResult()
        if key in (ord("\n"), 10, 13):
            model.picker_confirm_zone()
            return ActionResult()
        if key == 27:
            model.picker_close()
            return ActionResult()
        return ActionResult()

    # ── Edit nickname ──

    def _handle_edit_nick(self, model: ClockModel, key: int) -> ActionResult:
        en = model.edit_nick
        if key in (curses.KEY_BACKSPACE, 127, 8):
            en.temp_name = en.temp_name[:-1]
            return ActionResult()
        if key in (ord("\n"), 10, 13):
            wc = model.edit_nick_commit()
            if wc is None:
                return ActionResult()
            target = model.picker.edit_target
            if target is not None:
                model.wc_list[target] = wc
            else:
                model.wc_list.append(wc)
            return ActionResult(needs_save=True)
        if key == 27:
            model.edit_nick_cancel()
            return ActionResult()
        if 32 <= key <= 126:
            en.temp_name += chr(key)
            return ActionResult()
        return ActionResult()

    # ── Confirm delete ──

    def _handle_confirm(self, model: ClockModel, key: int) -> ActionResult:
        if key in (ord("y"), ord("Y"), ord("s"), ord("S"), ord("\n"), 10, 13):
            model.wc_delete(model.wc_idx)
            model.confirm_delete = False
            return ActionResult(needs_save=True)
        model.confirm_delete = False
        return ActionResult()

    # ── Normal mode ──

    def _handle_normal(self, model: ClockModel, key: int) -> ActionResult:
        if key == ord("J"):
            return self._reorder(model, 1)
        if key == ord("K"):
            return self._reorder(model, -1)
        if key == curses.KEY_DOWN:
            return self._nav_section(model)
        if key == curses.KEY_UP:
            return self._nav_section(model)
        if key in (curses.KEY_RIGHT, ord("j")) and model.wc_list:
            model.wc_idx = (model.wc_idx + 1) % len(model.wc_list)
            return ActionResult()
        if key in (curses.KEY_LEFT, ord("k")) and model.wc_list:
            model.wc_idx = (model.wc_idx - 1) % len(model.wc_list)
            return ActionResult()
        if key == ord("a"):
            model.picker_open(edit_target=None)
            return ActionResult()
        if key == ord("e") and model.wc_list:
            model.picker_open(edit_target=model.wc_idx)
            return ActionResult()
        if key == ord("d") and model.wc_list:
            model.confirm_delete = True
            return ActionResult()
        return ActionResult()

    def _nav_section(self, model: ClockModel) -> ActionResult:
        if not model.wc_list:
            return ActionResult()
        model.wc_idx = model.wc_idx % len(model.wc_list)
        return ActionResult()

    def _reorder(self, model: ClockModel, delta: int) -> ActionResult:
        if not model.wc_list:
            return ActionResult()
        idx = model.wc_idx
        nxt = idx + delta
        if nxt < 0 or nxt >= len(model.wc_list):
            return ActionResult()
        model.wc_list[idx], model.wc_list[nxt] = model.wc_list[nxt], model.wc_list[idx]
        model.wc_idx = nxt
        return ActionResult(needs_save=True)
