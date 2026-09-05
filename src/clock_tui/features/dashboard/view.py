"""Vista del dashboard: rendering puro sobre curses.

3 secciones: fecha+hora | clima | divisor + actividades (con scroll por
altura para que la selección siempre quede visible y el marco inferior
permanezca en pantalla). Minimum tier: solo dia resumido + hora + clima.
"""

from __future__ import annotations

from typing import Any

from clock_tui.ui.frame import content_capacity, draw_frame, scroll_window
from clock_tui.ui.responsive import size_tier

from .model import DashboardSnapshot


def render(
    stdscr: Any,
    snap: DashboardSnapshot,
    *,
    theme: dict[str, int] | None = None,
    pairs: dict[str, int],
    config: dict[str, Any],
    scroll: int = 0,
) -> int:
    """Dibuja el dashboard. Retorna el offset de scroll usado (para persistirlo)."""
    mostrar_marco = config.get("mostrar_marco", True)
    mostrar_helpers = config.get("mostrar_helpers", True)
    sh, sw = stdscr.getmaxyx()
    tier = size_tier(sh, sw)

    if tier == "micro":
        _render_minimum(stdscr, snap, pairs=pairs, mostrar_marco=mostrar_marco)
        return 0

    date_str = DashboardSnapshot.format_date(snap.now)
    time_str = DashboardSnapshot.format_time(
        snap.now, show_seconds=snap.show_seconds, format_24h=snap.format_24h
    )
    now_line = f"{date_str}  {time_str}"

    rows = [now_line]
    row_attrs: list[int | None] = [None]
    if snap.weather_line:
        rows.append(snap.weather_line)
        row_attrs.append(pairs.get("clima", 0))

    activities = snap.activities
    helper = (
        ["\u2191\u2193 jk:navegar  Enter:ir a vista  u:refresh clima"]
        if mostrar_helpers
        else []
    )
    offset = scroll
    bottom_counter: str | None = None
    if activities:
        fixed_n = len(rows)
        avail = max(0, content_capacity(sh, len(helper)) - fixed_n)
        use_divisor = avail >= 2  # el divisor consume una fila; si no sobra, omitirlo
        avail_items = avail - (1 if use_divisor else 0)
        offset = scroll_window(snap.selected_idx, len(activities), avail_items, scroll)
        visible = activities[offset : offset + avail_items]
        if visible:
            if use_divisor:
                rows.append("  " + "\u2500" * 20)
                row_attrs.append(None)
            for i_rel, act in enumerate(visible):
                es_sel = (offset + i_rel) == snap.selected_idx
                sel = "\u25ba" if es_sel else " "
                rows.append(f"{sel} {act.label}")
                row_attrs.append(None)
        bottom_counter = f"({snap.selected_idx + 1}/{len(activities)})"

    draw_frame(
        stdscr,
        "\u25c8 Dashboard",
        rows,
        mostrar_marco=mostrar_marco,
        helper_lines=helper,
        row_attrs=row_attrs,
        pairs=pairs,
        bottom_counter=bottom_counter,
    )
    return offset


def _render_minimum(
    stdscr: Any,
    snap: DashboardSnapshot,
    *,
    pairs: dict[str, int],
    mostrar_marco: bool,
) -> None:
    time_str = DashboardSnapshot.format_time(
        snap.now, show_seconds=snap.show_seconds, format_24h=snap.format_24h
    )
    rows = [time_str]
    row_attrs: list[int | None] = [None]
    if snap.weather_line:
        rows.append(snap.weather_line)
        row_attrs.append(pairs.get("clima", 0))

    draw_frame(
        stdscr,
        "\u25c8 Dashboard",
        rows,
        mostrar_marco=mostrar_marco,
        row_attrs=row_attrs,
        pairs=pairs,
    )
