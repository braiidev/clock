"""Vista de timers: rendering puro sobre curses.

Recibe el modelo y contextos de render. NUNCA muta estado.
"""

from __future__ import annotations

import curses
from typing import Any

from clock_tui.ui.frame import draw_frame

from .model import TimersModel, _MAX_VISIBLE

_PAIR_EDIT = 9


def render(
    stdscr: Any,
    model: TimersModel,
    *,
    theme: dict[str, int],
    pairs: dict[str, int],
    config: dict[str, Any],
) -> None:
    """Dibuja la vista de timers sobre stdscr."""
    mostrar_marco = config.get("mostrar_marco", True)
    mostrar_helpers = config.get("mostrar_helpers", True)

    if model.edit_mode:
        _render_edit(stdscr, model, pairs=pairs, mostrar_marco=mostrar_marco)
        return

    if model.confirm_delete:
        _render_confirm(stdscr, model, pairs=pairs, mostrar_marco=mostrar_marco)
        return

    rows = _build_rows(model)
    helper = (
        [
            "\u2191\u2193:nav  a:nuevo  e:editar  d:borrar",
            "Tab:campo  \u2190\u2192:valor  Space:\u25b6/\u25c9\u25c9  r:reset",
        ]
        if mostrar_helpers
        else []
    )

    draw_frame(
        stdscr,
        "\u23f1 Timers",
        rows,
        mostrar_marco=mostrar_marco,
        helper_lines=helper,
        pairs=pairs,
    )


def _render_edit(
    stdscr: Any,
    model: TimersModel,
    *,
    pairs: dict[str, int],
    mostrar_marco: bool,
) -> None:
    rows = [f"Nuevo nombre: {model.temp_name}_"]
    helper = ["Enter:guardar  Esc:cancelar"]
    draw_frame(
        stdscr,
        "\u270e Editar",
        rows,
        mostrar_marco=mostrar_marco,
        helper_lines=helper,
        pairs=pairs,
    )


def _render_confirm(
    stdscr: Any,
    model: TimersModel,
    *,
    pairs: dict[str, int],
    mostrar_marco: bool,
) -> None:
    t = model.timers[model.selected_idx] if model.timers else None
    name = t.name if t else "?"
    rows = [
        f"\u00bfEliminar '{name}'?",
        "  y / s / Enter = S\u00ed    cualquier tecla = No",
    ]
    draw_frame(
        stdscr,
        "\u23f1 Timers",
        rows,
        mostrar_marco=mostrar_marco,
        pairs=pairs,
    )


def _build_rows(model: TimersModel) -> list[str]:
    timers = model.timers
    total = len(timers)
    offset = model.scroll_offset
    rows: list[str] = []

    for i_rel in range(min(_MAX_VISIBLE, max(0, total - offset))):
        i_abs = i_rel + offset
        if i_abs >= total:
            break
        t = timers[i_abs]
        sel = "\u25ba" if i_abs == model.selected_idx else " "
        run_icon = "\u25b6 " if t.active else "  "

        if i_abs == model.selected_idx and not t.active:
            h, m, s = t.hms()
            f = model.time_field
            h_str = f"\u25c4{h:02d}\u25ba" if f == 0 else f"{h:02d}"
            m_str = f"\u25c4{m:02d}\u25ba" if f == 1 else f"{m:02d}"
            s_str = f"\u25c4{s:02d}\u25ba" if f == 2 else f"{s:02d}"
            tstr = f"[{h_str}:{m_str}:{s_str}]"
        else:
            h, m, s = t.hms()
            tstr = f"[{h:02d}:{m:02d}:{s:02d}]"

        rows.append(f"{sel}{run_icon} {t.name:14s}  {tstr}")

    if total > _MAX_VISIBLE:
        shown_end = min(offset + _MAX_VISIBLE, total)
        rows.append(f"  ({offset + 1}\u2013{shown_end} de {total})")

    return rows
