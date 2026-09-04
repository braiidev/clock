"""Overlays compartidos: alerta modal, ayuda y visor de log."""

from __future__ import annotations

import curses
import datetime
from typing import Any, Sequence

from .frame import Painter, draw_box, display_width


def draw_alert(
    stdscr: Any,
    alert: dict[str, Any],
    pair_a: int,
    pair_b: int,
    alarma_posponer_min: int = 5,
) -> None:
    """Dibuja el modal de alerta con parpadeo entre dos pares de color."""
    painter = Painter(stdscr)
    h, w = painter.size
    pair = pair_a if alert.get("blink_state") else pair_b
    attr = pair | curses.A_BOLD
    title = alert["title"]
    msg = alert["msg"]
    hint = "[ SPACE / ENTER para continuar ]"
    posponable = alert.get("posponable", False)
    hint2 = f"[ P → Posponer {alarma_posponer_min} min ]" if posponable else ""
    box_w = max(len(title), len(msg), len(hint), len(hint2)) + 6
    box_h = 9 if hint2 else 7
    sy = (h - box_h) // 2
    sx = (w - box_w) // 2
    for row in range(box_h):
        painter.safe(sy + row, sx, " " * box_w, attr)
    painter.centered(sy + 1, sx, box_w, title, attr)
    painter.centered(sy + 3, sx, box_w, msg, attr)
    painter.centered(sy + 5, sx, box_w, hint, attr)
    if hint2:
        painter.centered(sy + 7, sx, box_w, hint2, attr)


def draw_help(
    stdscr: Any,
    vista_lines: Sequence[str],
    global_lines: Sequence[str],
    pair_bg: int,
) -> None:
    """Dibuja el overlay de ayuda (cualquier tecla lo cierra)."""
    painter = Painter(stdscr)
    sh, sw = painter.size
    lines = ["Comandos de esta vista:"] + list(vista_lines)
    lines += ["", "─" * 36, "", "Comandos globales:"] + list(global_lines)
    box_w = min(max(display_width(l) for l in lines) + 6, sw - 4)
    box_h = len(lines) + 4
    sy = max(0, (sh - box_h) // 2)
    sx = max(0, (sw - box_w) // 2)

    bg_attr = pair_bg
    marco_attr = pair_bg | curses.A_BOLD
    texto_attr = pair_bg
    helper_attr = pair_bg | curses.A_DIM
    for r in range(box_h):
        painter.safe(sy + r, sx, " " * box_w, bg_attr)
    draw_box(painter, sy, sx, box_h, box_w, "? Ayuda", attr=marco_attr)
    for i, line in enumerate(lines):
        a = (
            helper_attr
            if (line.startswith("Comandos") or line.startswith("─"))
            else texto_attr
        )
        painter.safe(sy + 2 + i, sx + 3, line[: box_w - 6], a)
    hint = "(cualquier tecla para cerrar)"
    painter.safe(
        sy + box_h - 1, sx + (box_w - display_width(hint)) // 2, hint, helper_attr
    )


def draw_log_viewer(
    stdscr: Any,
    entries: Sequence[dict[str, Any]],
    idx: int,
    scroll: int,
    pair_bg: int,
) -> int:
    """Dibuja el visor de log. Retorna el scroll actualizado."""
    painter = Painter(stdscr)
    sh, sw = painter.size
    n = len(entries)
    box_w = min(70, max(40, sw - 6))
    box_h = min(20, max(8, sh - 4))
    sy = max(0, (sh - box_h) // 2)
    sx = max(0, (sw - box_w) // 2)
    content_w = box_w - 4
    bg_attr = pair_bg
    marco_attr = pair_bg | curses.A_BOLD
    texto_attr = pair_bg
    sel_attr = pair_bg | curses.A_REVERSE
    helper_attr = pair_bg | curses.A_DIM

    for r in range(box_h):
        painter.safe(sy + r, sx, " " * box_w, bg_attr)
    draw_box(painter, sy, sx, box_h, box_w, "⚠ Log de errores", attr=marco_attr)

    if n == 0:
        msg = "(sin errores registrados)"
        painter.safe(sy + 3, sx + (box_w - len(msg)) // 2, msg, helper_attr)
    else:
        MAX_VISIBLE = box_h - 4
        if idx < scroll:
            scroll = idx
        elif idx >= scroll + MAX_VISIBLE:
            scroll = idx - MAX_VISIBLE + 1
        visibles = entries[scroll : scroll + MAX_VISIBLE]
        for i_rel, e in enumerate(visibles):
            i_abs = i_rel + scroll
            es_sel = i_abs == idx
            ts = e.get("ts")
            fecha = (
                datetime.datetime.fromtimestamp(ts).strftime("%d/%m %H:%M")
                if ts
                else "??/?? ??:??"
            )
            msg = str(e.get("msg", ""))[: content_w - 13]
            linea = f"{fecha}  {msg}"
            a = sel_attr if es_sel else texto_attr
            painter.safe(sy + 2 + i_rel, sx + 2, linea.ljust(content_w)[:content_w], a)
        ind = f"({idx + 1}/{n})"
        painter.safe(sy + box_h - 2, sx + (box_w - len(ind)) // 2, ind, helper_attr)
    hint = "↑↓:nav  Esc/Enter:cerrar"
    painter.safe(sy + box_h - 1, sx + (box_w - len(hint)) // 2, hint, helper_attr)
    return scroll
