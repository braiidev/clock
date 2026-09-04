"""Tiers responsive (decisión D10: solo micro / full)."""

from __future__ import annotations

from typing import Literal

Tier = Literal["micro", "full"]

_MIN_W = 40
_MIN_H = 5


def size_tier(h: int, w: int) -> Tier:
    """Devuelve el tier según el tamaño del terminal.

    micro:      w < 40  AND  h < 5
    full:       todo lo demás
    """
    if w < _MIN_W and h < _MIN_H:
        return "micro"
    return "full"
