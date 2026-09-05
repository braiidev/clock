"""Tiers responsive (decisión D10/D20: micro / mini / full por altura)."""

from __future__ import annotations

from typing import Literal

Tier = Literal["micro", "mini", "full"]

_MIN_H = 3
_MIN_H_FULL = 8


def size_tier(h: int, w: int) -> Tier:
    """Devuelve el estado solo según la altura (D20); el ancho no degrada.

    micro:  h < 3          → MVP de Dashboard sin marco (1-2 líneas)
    mini:   3 <= h < 8     → vistas con marco, sin helpers/footer
    full:   h >= 8         → vista completa
    """
    if h < _MIN_H:
        return "micro"
    if h >= _MIN_H_FULL:
        return "full"
    return "mini"
