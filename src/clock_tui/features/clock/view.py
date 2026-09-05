"""Vista del reloj: rendering puro sobre curses.

4 pantallas: normal, picker, edit_nick, confirm_delete.
Sin clima (D13): el clima solo se muestra en el Dashboard.
"""

from __future__ import annotations

import curses
from typing import Any

from clock_tui.ui.frame import content_capacity, draw_frame, scroll_window

from .model import ClockModel, _WC_MAX_VISIBLE

_PICKER_MAX_VISIBLE = 10


def render(
    stdscr: Any,
    model: ClockModel,
    *,
    theme: dict[str, int],
    pairs: dict[str, int],
    config: dict[str, Any],
) -> None:
    mostrar_marco = config.get("mostrar_marco", True)
    mostrar_helpers = config.get("mostrar_helpers", True)

    if model.picker.open:
        _render_picker(stdscr, model, pairs=pairs, mostrar_marco=mostrar_marco)
        return
    if model.edit_nick.active:
        _render_edit_nick(stdscr, model, pairs=pairs, mostrar_marco=mostrar_marco)
        return

    show_seconds = config.get("mostrar_segundos", True)
    format_24h = config.get("formato_24h", True)

    import datetime

    now = datetime.datetime.now()
    time_str = ClockModel.format_local_time(
        now, show_seconds=show_seconds, format_24h=format_24h
    )
    date_line = ClockModel.format_date_line(now, time_str)

    if model.confirm_delete:
        wc = model.wc_list[model.wc_idx] if model.wc_list else None
        nombre = wc.apodo if wc else "?"
        rows = [
            date_line,
            f"\u00bfEliminar reloj '{nombre}'?",
            "  y / s / Enter = S\u00ed    cualquier tecla = No",
        ]
        draw_frame(
            stdscr,
            "\u25f7 Reloj",
            rows,
            mostrar_marco=mostrar_marco,
            pairs=pairs,
        )
        return

    rows = [date_line]
    bottom_counter: str | None = None
    if config.get("wc_mostrar", "ver") != "no ver":
        helper = (
            [
                "\u2191\u2193 \u2190\u2192 jk:nav WC  J/K:orden  a:+WC  e:editar  d:borrar"
            ]
            if mostrar_helpers
            else []
        )
        sh, _ = stdscr.getmaxyx()
        wc_rows = _build_wc_rows(model, pairs, content_capacity(sh, len(helper)) - 1)
        if wc_rows:
            rows.extend(wc_rows)
        if model.wc_list:
            bottom_counter = f"({model.wc_idx + 1}/{len(model.wc_list)})"
    else:
        helper = []

    draw_frame(
        stdscr,
        "\u25f7 Reloj",
        rows,
        mostrar_marco=mostrar_marco,
        helper_lines=helper,
        pairs=pairs,
        bottom_counter=bottom_counter,
    )


def _build_wc_rows(
    model: ClockModel, pairs: dict[str, int], capacity: int | None = None
) -> list[str]:
    if not model.wc_list:
        return []
    rows: list[str] = []
    n = len(model.wc_list)
    effective = min(
        _WC_MAX_VISIBLE, capacity if capacity is not None else _WC_MAX_VISIBLE
    )
    model.wc_scroll = scroll_window(model.wc_idx, n, effective, model.wc_scroll)
    for i in range(min(effective, n - model.wc_scroll)):
        i_abs = model.wc_scroll + i
        wc = model.wc_list[i_abs]
        hhmm = model.wc_time_str(wc.zona)
        sel = "\u25ba" if i_abs == model.wc_idx else " "
        diff = model.wc_local_diff_str(wc.zona)
        extra = f"{diff} " if diff else ""
        rows.append(f"{sel} {wc.apodo} {extra}{hhmm}")
    return rows


def _render_picker(
    stdscr: Any,
    model: ClockModel,
    *,
    pairs: dict[str, int],
    mostrar_marco: bool,
) -> None:
    p = model.picker
    titulo = (
        "Editar reloj mundial" if p.edit_target is not None else "Nuevo reloj mundial"
    )

    if p.filter_active:
        helper = ["Escribiendo filtro  Enter:elegir  Esc:salir del filtro"]
    else:
        helper = ["\u2191\u2193:nav  f:filtro  Enter:elegir  Esc:cancelar"]

    sh, _ = stdscr.getmaxyx()
    extras = 1 if p.filter_active else 0
    effective = min(
        _PICKER_MAX_VISIBLE,
        max(1, content_capacity(sh, len(helper)) - extras),
    )
    p.scroll = scroll_window(p.idx, len(p.zones), effective, p.scroll)

    rows: list[str] = []
    for i_rel in range(min(effective, max(0, len(p.zones) - p.scroll))):
        i_abs = i_rel + p.scroll
        if i_abs >= len(p.zones):
            break
        z = p.zones[i_abs]
        sel = "\u25ba" if i_abs == p.idx else " "
        diff_txt = model.wc_diff_str(z[0])
        rows.append(f"{sel} {z[1]} / {z[2]}{diff_txt}")

    if not rows:
        rows.append("  (sin resultados)")
    if p.filter_active:
        rows.append(f"Filtro: {p.filter_text}_")

    draw_frame(
        stdscr,
        titulo,
        rows,
        mostrar_marco=mostrar_marco,
        helper_lines=helper,
        pairs=pairs,
        bottom_counter=(f"({p.idx + 1}/{len(p.zones)})" if p.zones else None),
    )


def _render_edit_nick(
    stdscr: Any,
    model: ClockModel,
    *,
    pairs: dict[str, int],
    mostrar_marco: bool,
) -> None:
    en = model.edit_nick
    z = en.zona
    zona_txt = f"{z[1]} / {z[2]} / {z[3]}" if z else "?"
    utc_txt = model.wc_diff_str(z[0]).strip(" ()") if z else "?"
    if utc_txt.startswith("UTC"):
        utc_txt = utc_txt
    else:
        utc_txt = f"UTC {utc_txt}" if utc_txt else "?"

    rows = [
        f"Zona: {zona_txt}",
        f"Diferencia: {utc_txt}",
        f"Nombre: {en.temp_name}_",
    ]
    helper = ["Enter:guardar  Esc:cancelar"]
    draw_frame(
        stdscr,
        "\u270e Nombre",
        rows,
        mostrar_marco=mostrar_marco,
        helper_lines=helper,
        pairs=pairs,
    )
