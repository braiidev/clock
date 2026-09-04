"""File browser (sonidos y restauración de backups)."""

from __future__ import annotations

import curses
import os
from typing import Any, Sequence

from ..services.audio import _SOUND_EXTS
from .frame import Painter, draw_box, display_width


def list_entries(cwd: str, mode: str) -> list[tuple[str, bool]]:
    """Lista el contenido de `cwd` filtrado según el modo.

    Returna (nombre, es_directorio). Modo 'sound' filtra por extensiones de
    audio; 'restore' por .json. Directorios siempre incluidos, ordenados antes.
    """
    try:
        con_tipo: list[tuple[str, bool]] = []
        for nombre in os.listdir(cwd):
            full = os.path.join(cwd, nombre)
            if os.path.isdir(full):
                con_tipo.append((nombre, True))
            elif mode == "restore" and nombre.lower().endswith(".json"):
                con_tipo.append((nombre, False))
            elif mode == "sound" and nombre.lower().endswith(_SOUND_EXTS):
                con_tipo.append((nombre, False))
        con_tipo.sort(key=lambda x: (not x[1], x[0].lower()))
    except OSError:
        con_tipo = []
    return con_tipo


def draw_browser(
    stdscr: Any,
    entries: Sequence[tuple[str, bool]],
    cwd: str,
    selected_idx: int,
    mode: str,
    pairs: dict[str, int],
) -> None:
    """Dibuja el panel del file browser."""
    painter = Painter(stdscr)
    sh, sw = painter.size
    panel_w = min(70, sw - 4)
    panel_h = min(24, sh - 4)
    px = (sw - panel_w) // 2
    py = (sh - panel_h) // 2
    p_marco = pairs.get("marco", 0)
    p_texto = pairs.get("texto", 0)
    p_helpers = pairs.get("helpers", 0)
    attr_sel = p_texto | curses.A_BOLD | curses.A_REVERSE

    draw_box(painter, py, px, panel_h, panel_w, attr=p_marco)
    titulo = "[ Restaurar backup .json ]" if mode == "restore" else "[ Elegir sonido ]"
    painter.safe(
        py, px + (panel_w - display_width(titulo)) // 2, titulo, p_marco | curses.A_BOLD
    )
    content_w = panel_w - 4
    painter.safe(py + 1, px + 2, cwd[-content_w:], p_helpers)
    list_start = py + 3
    list_h = panel_h - 5
    if not entries:
        painter.safe(list_start, px + 2, "(carpeta vacía)", p_helpers)
    else:
        n = len(entries)
        scroll = max(0, min(selected_idx - list_h // 2, n - list_h))
        for row in range(list_h):
            i = scroll + row
            if i >= n:
                break
            nombre, es_dir = entries[i]
            if es_dir:
                icono = "▸"
            elif mode == "restore":
                icono = "▤"
            else:
                icono = "♪"
            es_sel = i == selected_idx
            attr = attr_sel if es_sel else p_texto
            marca = "►" if es_sel else " "
            painter.safe(
                list_start + row,
                px + 2,
                f"{marca} {icono} {nombre}"[:content_w].ljust(content_w),
                attr,
            )
    hint = "↑↓:nav  Enter:abrir/elegir  Esc:subir nivel/cerrar"
    painter.safe(
        py + panel_h - 1,
        px + max(1, (panel_w - display_width(hint)) // 2),
        hint,
        p_helpers,
    )
