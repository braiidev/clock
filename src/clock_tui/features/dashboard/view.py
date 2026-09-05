"""Vista del dashboard: rendering puro sobre curses.

3 secciones: fecha+hora | clima | divisor + actividades
Minimum tier: solo dia resumido + hora + clima.
"""

from __future__ import annotations

from typing import Any

from clock_tui.ui.frame import draw_frame
from clock_tui.ui.responsive import size_tier

from .model import DashboardSnapshot


def render(
    stdscr: Any,
    snap: DashboardSnapshot,
    *,
    theme: dict[str, int],
    pairs: dict[str, int],
    config: dict[str, Any],
) -> None:
    mostrar_marco = config.get("mostrar_marco", True)
    mostrar_helpers = config.get("mostrar_helpers", True)
    sh, sw = stdscr.getmaxyx()
    tier = size_tier(sh, sw)

    if tier == "micro":
        _render_minimum(stdscr, snap, pairs=pairs, mostrar_marco=mostrar_marco)
        return

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
    if activities:
        rows.append("  " + "\u2500" * 24)
        row_attrs.append(None)
        for i, act in enumerate(activities):
            sel = "\u25ba" if i == snap.selected_idx else " "
            rows.append(f"{sel} {act.label}")
            row_attrs.append(None)

    helper = (
        ["\u2191\u2193 jk:navegar  Enter:ir a vista  u:refresh clima"]
        if mostrar_helpers
        else []
    )

    draw_frame(
        stdscr,
        "\u25c8 Dashboard",
        rows,
        mostrar_marco=mostrar_marco,
        helper_lines=helper,
        row_attrs=row_attrs,
        pairs=pairs,
    )


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
