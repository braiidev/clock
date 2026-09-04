"""Vista del dashboard: rendering puro sobre curses.

3 secciones: fecha+hora | clima | divisor + actividades
Minimum tier: solo dia resumido + hora + clima.
"""

from __future__ import annotations

from typing import Any

from clock_tui.ui.frame import draw_frame
from clock_tui.ui.responsive import size_tier, Tier

from .model import DashboardSnapshot


def render(
    stdscr: Any,
    snap: DashboardSnapshot,
    *,
    pairs: dict[str, int],
    mostrar_marco: bool,
    mostrar_helpers: bool,
) -> None:
    tier = size_tier()

    if tier == Tier.MINIMUM:
        _render_minimum(stdscr, snap, pairs=pairs, mostrar_marco=mostrar_marco)
        return

    date_str = DashboardSnapshot.format_date(snap.now)
    time_str = DashboardSnapshot.format_time(
        snap.now, show_seconds=snap.show_seconds, format_24h=snap.format_24h
    )
    now_line = f"{date_str}  {time_str}"

    rows = [now_line]
    if snap.weather_line:
        rows.append(snap.weather_line)

    activities = snap.activities
    if activities:
        rows.append("  " + "\u2500" * 24)
        for i, act in enumerate(activities):
            sel = "\u25ba" if i == snap.selected_idx else " "
            rows.append(f"{sel} {act.label}")

    helper = ["\u2191\u2193:navegar  Enter:ir a vista  u:refresh clima"] if mostrar_helpers else []

    draw_frame(
        stdscr,
        "\u25c8 Dashboard",
        rows,
        mostrar_marco=mostrar_marco,
        helper_lines=helper,
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
    if snap.weather_line:
        rows.append(snap.weather_line)

    draw_frame(
        stdscr,
        "\u25c8 Dashboard",
        rows,
        mostrar_marco=mostrar_marco,
        pairs=pairs,
    )
