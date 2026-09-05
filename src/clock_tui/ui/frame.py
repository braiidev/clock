"""Primitivas de dibujo de frame: cajas, centrado, ellipsis y layout general.

Son funciones puras: reciben el stdscr y los atributos de color como
parámetros, sin depender del estado de la app. El layout respeta los tiers
micro/full (decisión D10).
"""

from __future__ import annotations

import curses
from typing import Any, Callable, Sequence

from .responsive import Tier, size_tier

# Emojis y bloques se cuentan con ancho 2 (como en el original).
_WIDE = (
    (0x1F000, 0x1FFFF),
    (0x2600, 0x27BF),
    (0x1100, 0x11FF),
    (0x2E80, 0x9FFF),
    (0xAC00, 0xD7AF),
)


def display_width(s: str) -> int:
    """Ancho visual de un string (los emojis ocupan 2 columnas)."""
    width = 0
    for ch in s:
        cp = ord(ch)
        if any(lo <= cp <= hi for lo, hi in _WIDE):
            width += 2
        else:
            width += 1
    return width


def truncate_ellipsis(text: str, max_width: int) -> str:
    """Trunca `text` a `max_width` columnas agregando '…' al final si excede."""
    if display_width(text) <= max_width:
        return text
    out = ""
    used = 0
    for ch in text:
        w = display_width(ch)
        if used + w > max_width:
            break
        out += ch
        used += w
    # reservar una columna para la ellipsis
    while out and used >= max_width:
        out = out[:-1]
        used -= 1
    return out + "…"


def content_capacity(sh: int, helper_count: int = 0) -> int:
    """Filas de contenido que entran dentro de la caja en pantalla.

    Deja la última fila del terminal libre (footer) y reserva el marco.
    Es el mismo cálculo que usa `draw_frame` para acotar la caja.
    """
    helpers_below = (helper_count + 1) if helper_count else 0
    box_h_cap = max(4, sh - 2 - helpers_below)
    return max(1, box_h_cap - 4)


def scroll_window(selected: int, total: int, capacity: int, current: int = 0) -> int:
    """Offset de ventana que mantiene `selected` visible en [offset, offset+capacity).

    Incremental: conserva `current` salvo que la selección salga de la
    ventana (patrón normalizado para todos los views).
    """
    if total <= 0 or capacity <= 0 or total <= capacity:
        return 0
    if selected < current:
        return max(0, selected)
    if selected >= current + capacity:
        return min(selected - capacity + 1, total - capacity)
    return min(current, total - capacity)


class Painter:
    """Helper de dibujo seguro sobre un stdscr."""

    def __init__(self, stdscr: Any):
        self.stdscr = stdscr

    @property
    def size(self) -> tuple[int, int]:
        return self.stdscr.getmaxyx()

    def safe(self, y: int, x: int, s: str, attr: int = 0) -> None:
        h, w = self.size
        if 0 <= y < h and 0 <= x < w - 1:
            try:
                self.stdscr.addstr(y, x, s[: w - x - 1], attr)
            except curses.error:
                pass

    def centered(
        self, y: int, x_start: int, width: int, text: str, attr: int = 0
    ) -> None:
        h, w = self.size
        cx = x_start + (width - len(text)) // 2
        cx = max(0, min(cx, w - len(text) - 1))
        self.safe(y, cx, text, attr)


def draw_box(
    painter: Painter,
    sy: int,
    sx: int,
    bh: int,
    bw: int,
    title: str = "",
    attr: int = 0,
    title_attr: int | None = None,
) -> None:
    """Dibuja una caja con esquinas y un título centrado en el borde superior."""
    painter.safe(sy, sx, "┌" + "─" * (bw - 2) + "┐", attr)
    painter.safe(sy + bh - 1, sx, "└" + "─" * (bw - 2) + "┘", attr)
    for r in range(1, bh - 1):
        painter.safe(sy + r, sx, "│", attr)
        painter.safe(sy + r, sx + bw - 1, "│", attr)
    if title:
        ts = f"[ {title} ]"
        vis_w = display_width(ts)
        tx = sx + (bw - vis_w) // 2
        painter.safe(
            sy, tx, ts, title_attr if title_attr is not None else attr | curses.A_BOLD
        )


def draw_frame(
    stdscr: Any,
    title: str,
    rows: Sequence[str],
    *,
    mostrar_marco: bool = True,
    helper_lines: Sequence[str] = (),
    weather_line: str | None = None,
    footer: str = "",
    pairs: dict[str, int] | None = None,
    row_attrs: Sequence[int | None] | None = None,
    bottom_counter: str | None = None,
) -> tuple[int, int, int, Tier]:
    """Dibuja el layout completo de una vista.

    `bottom_counter` (p.ej. "(3/10)") se dibuja alineado a la derecha sobre
    el borde inferior del marco, sin ocupar filas de contenido.
    Retorna (sy, sx, box_w, tier).
    """
    pairs = pairs or {}
    p_marco = pairs.get("marco", 0)
    p_texto = pairs.get("texto", 0)
    p_helpers = pairs.get("helpers", 0)
    p_clima = pairs.get("clima", 0)
    p_nav = pairs.get("nav", 0)

    painter = Painter(stdscr)
    stdscr.erase()
    sh, sw = painter.size
    tier = size_tier(sh, sw)

    if weather_line and tier != "micro":
        wx = max(0, (sw - len(weather_line)) // 2)
        painter.safe(0, wx, weather_line[: sw - 1], p_clima)

    helper_lines = list(helper_lines or [])
    n_help = len(helper_lines)
    all_widths = (
        [display_width(r) for r in rows]
        + [display_width(h) for h in helper_lines]
        + [display_width(title) + 8, 44]
    )
    box_w = min(max(all_widths) + 6, sw - 2)
    box_h = min(len(rows) + 4, content_capacity(sh, n_help) + 4)
    total_h = box_h + (n_help + 1 if n_help else 0)
    sy = max(1, (sh - 1 - total_h) // 2)
    sx = max(0, (sw - box_w) // 2)

    if mostrar_marco:
        draw_box(painter, sy, sx, box_h, box_w, title, attr=p_marco)
        content_y0 = sy + 2
    else:
        painter.centered(sy, sx, box_w, f"[ {title} ]", p_marco | curses.A_BOLD)
        content_y0 = sy + 2

    content_w = max(1, box_w - 4)
    for i, row in enumerate(rows[: box_h - 4]):
        attr = p_texto
        if row_attrs is not None and i < len(row_attrs):
            ra = row_attrs[i]
            if ra is not None:
                attr = ra
        painter.centered(
            content_y0 + i, sx, box_w, truncate_ellipsis(row, content_w), attr
        )

    for j, hline in enumerate(helper_lines):
        hy = sy + box_h + j + 1
        if 0 <= hy < sh:
            hx = sx + (box_w - display_width(hline)) // 2
            hx = max(0, hx)
            painter.safe(hy, hx, hline, p_helpers)

    if mostrar_marco and bottom_counter:
        cw = display_width(bottom_counter)
        if cw + 4 <= box_w:
            bx = sx + box_w - cw - 2
            painter.safe(sy + box_h - 1, bx, bottom_counter, p_nav or p_marco)

    fy = sh - 1
    if tier != "micro" and footer:
        if 0 <= fy < sh:
            painter.safe(fy, max(0, (sw - display_width(footer)) // 2), footer, p_nav)

    return sy, sx, box_w, tier


def draw_micro(stdscr: Any, hora_str: str, pair_texto: int = 0) -> None:
    """Dibuja la vista micro: reloj centrado sin marco."""
    painter = Painter(stdscr)
    painter.stdscr.erase()
    sh, sw = painter.size
    y = sh // 2
    x = max(0, (sw - display_width(hora_str)) // 2)
    painter.safe(y, x, hora_str, pair_texto | curses.A_BOLD)
    painter.stdscr.refresh()
