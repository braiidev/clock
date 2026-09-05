"""Vista de Config: rendering puro sobre curses.

Tabs por categoría + items configurables + overlay de texto.
"""

from __future__ import annotations

import os
from typing import Any

from clock_tui.ui.frame import content_capacity, draw_frame, scroll_window

from .model import TABS, ConfigModel

_MAX_VISIBLE = 10


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
    helper = (
        [
            "\u2190\u2192:categor\u00eda  \u2191\u2193:nav  Space/Enter:toggle/ciclar/elegir"
        ]
        if mostrar_helpers
        else []
    )
    sh, _ = stdscr.getmaxyx()
    cap = content_capacity(sh, len(helper))
    fixed = 2  # tabs + separador

    tab_parts = []
    for i, nombre in enumerate(TABS):
        tab_parts.append(f"[{nombre}]" if i == model.tab_idx else f" {nombre} ")
    rows = [" ".join(tab_parts), ""]
    if cap < 3:
        rows.pop()  # apretado: quita el separador
        fixed = 1
        if cap < 2:
            rows[:] = []  # muy apretado: solo items
            fixed = 0

    visibles = model.visible_items()
    n = len(visibles)
    if n == 0:
        rows.append("(sin opciones en esta categoria)")
    else:
        effective = min(_MAX_VISIBLE, max(1, cap - fixed))
        model.scroll_offset = scroll_window(
            model.selected_idx, n, effective, model.scroll_offset
        )
        for i_rel, it in enumerate(
            visibles[model.scroll_offset : model.scroll_offset + effective]
        ):
            sel = "\u25ba" if model.scroll_offset + i_rel == model.selected_idx else " "
            val = model.item_value(it)
            rows.append(f"{sel} {it.label:26s} [{val}]")

    draw_frame(
        stdscr,
        "\u2699 Configuraci\u00f3n",
        rows,
        mostrar_marco=mostrar_marco,
        helper_lines=helper,
        pairs=pairs,
        bottom_counter=(f"({model.selected_idx + 1}/{n})" if n else None),
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
