"""Controller de Config.

Procesa input del usuario y muta el ConfigModel. Tabs con `←→`, nav `↑↓`,
toggle/cycle/act con Space/Enter, y modo texto.

Las acciones (backup/restore/log) NO se ejecutan acá: se devuelven como
`ActionResult(command=...)` para que el main app las resuelva con servicios.
EJECUTA_SONIDO marca que el main loop debe refrescar la lista de sonidos.
"""

from __future__ import annotations

import curses
from dataclasses import dataclass
from typing import Any

from .model import ConfigItem, ConfigModel


@dataclass
class ActionResult:
    needs_save: bool = False
    command: str | None = None
    theme_changed: bool = False


class ConfigController:
    def handle(
        self, model: ConfigModel, key: int, context: dict[str, Any]
    ) -> ActionResult:
        if model.text_edit:
            return self._handle_text(model, key)
        return self._handle_normal(model, key)

    def _handle_text(self, model: ConfigModel, key: int) -> ActionResult:
        if key in (ord("\n"), 10, 13):
            changed = model.text_commit()
            return ActionResult(needs_save=changed)
        if key == 27:
            model.text_cancel()
            return ActionResult()
        if key in (curses.KEY_BACKSPACE, 127, 8):
            model.text_edit_value = model.text_edit_value[:-1]
            return ActionResult()
        if 32 <= key <= 126:
            model.text_edit_value += chr(key)
            return ActionResult()
        return ActionResult()

    def _handle_normal(self, model: ConfigModel, key: int) -> ActionResult:
        if key == curses.KEY_LEFT:
            model.switch_tab(-1)
            return ActionResult()
        if key == curses.KEY_RIGHT:
            model.switch_tab(1)
            return ActionResult()

        it = model.current_item()
        if it is None:
            return ActionResult()

        if key in (curses.KEY_DOWN, ord("j")):
            model.nav(1)
            return ActionResult()
        if key in (curses.KEY_UP, ord("k")):
            model.nav(-1)
            return ActionResult()

        if key in (ord(" "), ord("\n"), 10, 13):
            return self._activate(model, it)
        return ActionResult()

    def _activate(self, model: ConfigModel, it: ConfigItem) -> ActionResult:
        if it.tipo == "action":
            return ActionResult(command=it.opciones)
        if it.tipo == "text":
            model.start_text_edit(it)
            return ActionResult()
        if it.tipo == "bool":
            model.toggle_bool(it.key)
            r = ActionResult(needs_save=True)
            if it.key == "clima_activo":
                r.command = "weather_toggle"
            return r
        if it.tipo == "choice":
            model.cycle(it)
            r = ActionResult(needs_save=True)
            if it.key == "tema":
                r.theme_changed = True
            return r
        if it.tipo == "soundmode":
            model.cycle(it)
            return ActionResult(needs_save=True)
        if it.tipo == "soundbrowser":
            return ActionResult(command="sound_browser")
        if it.tipo == "soundfile":
            return ActionResult(command="sound_cycle", needs_save=True)
        return ActionResult()
