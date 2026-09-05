"""Vista de alarmas: rendering puro sobre curses.

Recibe el modelo, edit_state y contextos de render. NUNCA muta estado.
"""

from __future__ import annotations

import curses
from typing import Any

from clock_tui.core.recurrence import DIAS_ABBR, _repeat_days_str
from clock_tui.ui.frame import content_capacity, draw_frame, scroll_window

from .model import AlarmsModel, _MAX_VISIBLE


def render(
    stdscr: Any,
    model: AlarmsModel,
    *,
    theme: dict[str, int],
    pairs: dict[str, int],
    config: dict[str, Any],
    edit_state: dict[str, Any] | None = None,
) -> None:
    """Dibuja la vista de alarmas sobre stdscr."""
    mostrar_marco = config.get("mostrar_marco", True)
    mostrar_helpers = config.get("mostrar_helpers", True)
    es = edit_state or {}

    if es.get("edit_mode"):
        _render_edit(stdscr, es, pairs=pairs, mostrar_marco=mostrar_marco)
        return

    if es.get("confirm_delete"):
        _render_confirm(stdscr, model, es, pairs=pairs, mostrar_marco=mostrar_marco)
        return

    helper = (
        ["a:nueva  \u2191\u2193 jk:nav  J/K:orden  Space:on/off  e:editar  d:borrar"]
        if mostrar_helpers
        else []
    )
    sh, _ = stdscr.getmaxyx()
    rows = _build_rows(model, pairs, content_capacity(sh, len(helper)))

    draw_frame(
        stdscr,
        "\u25f7 Alarmas",
        rows,
        mostrar_marco=mostrar_marco,
        helper_lines=helper,
        pairs=pairs,
        bottom_counter=(
            f"({model.selected_idx + 1}/{len(model.alarms)})" if model.alarms else None
        ),
    )


def _render_edit(
    stdscr: Any,
    es: dict[str, Any],
    *,
    pairs: dict[str, int],
    mostrar_marco: bool,
) -> None:
    ef = es.get("edit_field", 0)
    name = es.get("temp_name", "")
    hh, mm = es.get("temp_time", [0, 0])
    tf = es.get("temp_time_field", 0)
    days = es.get("temp_days", [])
    cursor = es.get("temp_days_cursor", 0)

    n_mark = "\u25ba" if ef == 0 else " "
    t_mark = "\u25ba" if ef == 1 else " "
    d_mark = "\u25ba" if ef == 2 else " "

    hh_activo = ef == 1 and tf == 0
    mm_activo = ef == 1 and tf == 1
    hh_str = f"\u25c4{hh:02d}\u25ba" if hh_activo else f"{hh:02d}"
    mm_str = f"\u25c4{mm:02d}\u25ba" if mm_activo else f"{mm:02d}"

    dias_field_activo = ef == 2
    partes_dias = []
    for d in range(7):
        marcado = d in days
        txt = f"[{DIAS_ABBR[d]}]" if marcado else f" {DIAS_ABBR[d]} "
        if dias_field_activo and d == cursor:
            txt = f"\u00bb{txt}\u00ab" if marcado else f"\u00bb{DIAS_ABBR[d]}\u00ab"
        partes_dias.append(txt)
    dias_str = "".join(partes_dias)

    name_display = f"{name}_" if ef == 0 else name
    rows = [
        f"{n_mark} Nombre : {name_display}",
        f"{t_mark} Hora   : {hh_str}:{mm_str}",
        f"{d_mark} D\u00edas   : {dias_str}",
        f"   ({_repeat_days_str(days)})",
    ]
    helper = [
        "\u2191\u2193:l\u00ednea  Tab:HH/MM  \u2190\u2192:valor  Enter:guardar  Esc:cancelar",
        "D\u00edas: \u2190\u2192 mover  Space:\u2714/\u25cb",
    ]
    draw_frame(
        stdscr,
        "\u270e Editar Alarma",
        rows,
        mostrar_marco=mostrar_marco,
        helper_lines=helper,
        pairs=pairs,
    )


def _render_confirm(
    stdscr: Any,
    model: AlarmsModel,
    es: dict[str, Any],
    *,
    pairs: dict[str, int],
    mostrar_marco: bool,
) -> None:
    a = model.alarms[model.selected_idx] if model.alarms else None
    name = a.nombre if a else "?"
    rows = [
        f"\u00bfEliminar '{name}'?",
        "  y / s / Enter = S\u00ed    cualquier tecla = No",
    ]
    draw_frame(
        stdscr,
        "\u25f7 Alarmas",
        rows,
        mostrar_marco=mostrar_marco,
        pairs=pairs,
    )


def _build_rows(
    model: AlarmsModel, pairs: dict[str, int], capacity: int | None = None
) -> list[str]:
    alarms = model.alarms
    total = len(alarms)
    effective = min(_MAX_VISIBLE, capacity if capacity is not None else _MAX_VISIBLE)
    offset = model.scroll_offset
    rows: list[str] = []
    row_attrs: list[int | None] = []

    if not total:
        rows.append("a para crear alarma")
        return rows

    p_texto = pairs.get("texto", 0)
    p_helpers = pairs.get("helpers", 0)

    model.scroll_offset = scroll_window(model.selected_idx, total, effective, offset)
    offset = model.scroll_offset

    for i_rel in range(min(effective, max(0, total - offset))):
        i_abs = i_rel + offset
        if i_abs >= total:
            break
        a = alarms[i_abs]
        activa = a.is_enabled()
        es_sel = i_abs == model.selected_idx
        sel = "\u25ba" if es_sel else " "
        sta = "\u2714" if activa else "\u2718"
        rep = a.repeat_str()
        rep_txt = "" if rep == "una vez" else f"  \u21bb{rep}"
        rows.append(
            f"{sel} {sta} {a.nombre:<10.10s} {a.hora:02d}:{a.minutos:02d}{rep_txt}"
        )
        if es_sel:
            row_attrs.append(p_texto | curses.A_BOLD)
        elif not activa:
            row_attrs.append(p_helpers | curses.A_DIM)
        else:
            row_attrs.append(None)

    return rows
