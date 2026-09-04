"""Vista de Config: rendering puro sobre curses.

Tabs por categoría + items configurables + overlay de texto.
"""

from __future__ import annotations

import os
from typing import Any

from clock_tui.ui.frame import draw_frame

from .model import TABS, ConfigModel


def render(
    stdscr: Any,
    model: ConfigModel,
    *,
    theme: dict[str, int],
    pairs: dict[str, int],
    config: dict[str, Any],
) -> None:
    mostrar_marco = config.get("mostrar_marco", True)
    mostrar_helpers = config.get("mostrar_helpers", True)
    if model.text_edit:
        _render_text(stdscr, model, pairs=pairs, mostrar_marco=mostrar_marco)
        return

    model.clamp_selected()
    rows: list[str] = []

    tab_parts = []
    for i, nombre in enumerate(TABS):
        tab_parts.append(f"[{nombre}]" if i == model.tab_idx else f" {nombre} ")
    rows.append(" ".join(tab_parts))
    rows.append("")

    visibles = model.visible_items()
    n = len(visibles)
    if n == 0:
        rows.append("(sin opciones en esta categoria)")
    else:
        for i, it in enumerate(visibles):
            sel = ">" if i == model.selected_idx else " "
            val = model.item_value(it)
            rows.append(f"{sel} {it.label:26s} [{val}]")

    helper = (
        ["\u2190\u2192:categor\u00eda  \u2191\u2193:nav  Space/Enter:toggle/ciclar/elegir"]
        if mostrar_helpers
        else []
    )

    draw_frame(
        stdscr,
        "\u2699 Configuraci\u00f3n",
        rows,
        mostrar_marco=mostrar_marco,
        helper_lines=helper,
        pairs=pairs,
    )


def _render_text(
    stdscr: Any,
    model: ConfigModel,
    *,
    pairs: dict[str, int],
    mostrar_marco: bool,
) -> None:
    rows = [
        f"Valor: {model.text_edit_value}_",
        "",
        "Enter:guardar  Esc:cancelar",
    ]
    draw_frame(
        stdscr,
        "Editar valor",
        rows,
        mostrar_marco=mostrar_marco,
        pairs=pairs,
    )
