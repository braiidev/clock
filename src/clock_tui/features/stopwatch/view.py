"""Vista del cronómetro: rendering puro sobre curses.

Recibe el modelo y contextos de render. NUNCA muta estado.
"""

from __future__ import annotations

import curses
from typing import Any

from clock_tui.core.time_utils import secs_to_hms
from clock_tui.ui.frame import draw_frame

from .model import StopwatchModel

_MAX_VISIBLE_LAPS = 5


def render(
    stdscr: Any,
    model: StopwatchModel,
    *,
    theme: dict[str, int],
    pairs: dict[str, int],
    config: dict[str, Any],
) -> None:
    """Dibuja la vista del cronómetro sobre stdscr."""
    mostrar_marco = config.get("mostrar_marco", True)
    mostrar_helpers = config.get("mostrar_helpers", True)

    elapsed = model.elapsed()
    h, m, s = secs_to_hms(elapsed)
    cs = model.elapsed_cs()
    run_icon = "\u25b6 " if model.active else "  "
    rows = [f"{run_icon}{h:02d}:{m:02d}:{s:02d}.{cs:02d}", ""]

    records = model.records
    total_rec = len(records)

    if records:
        accums: list[float] = []
        acc = 0.0
        for d in records:
            acc += d
            accums.append(acc)

        offset = model.scroll_offset
        if offset + _MAX_VISIBLE_LAPS > total_rec:
            offset = max(0, total_rec - _MAX_VISIBLE_LAPS)
            model.scroll_offset = offset

        for i in range(offset, min(offset + _MAX_VISIBLE_LAPS, total_rec)):
            diff = records[i]
            accum = accums[i]
            ah, am, as_ = secs_to_hms(accum)
            dh, dm, ds = secs_to_hms(diff)
            marker = "\u25ba" if i == total_rec - 1 else " "
            rows.append(
                f"{marker} {i + 1:2d}.  "
                f"{ah:02d}:{am:02d}:{as_:02d}   (+{dh:02d}:{dm:02d}:{ds:02d})"
            )

        if total_rec > _MAX_VISIBLE_LAPS:
            shown_end = min(offset + _MAX_VISIBLE_LAPS, total_rec)
            rows.append(f"  ({offset + 1}\u2013{shown_end} de {total_rec})")
    else:
        rows.append("(sin registros)")

    helper = (
        ["Space:\u25b6/\u25c9\u25c9  m:marcar lap  d:borrar \u00faltimo  r:reset"]
        if mostrar_helpers
        else []
    )

    draw_frame(
        stdscr,
        "\u23f2 Cron\u00f3metro",
        rows,
        mostrar_marco=mostrar_marco,
        helper_lines=helper,
        pairs=pairs,
    )
