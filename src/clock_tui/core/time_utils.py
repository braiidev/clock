"""Utilidades puras de tiempo: conversión entre segundos y H/M/S."""

from __future__ import annotations


def secs_to_hms(secs: int | float) -> tuple[int, int, int]:
    """Convierte una cantidad de segundos en (horas, minutos, segundos)."""
    secs = max(0, int(secs))
    h, m, s = secs // 3600, (secs % 3600) // 60, secs % 60
    return h, m, s


def hms_to_secs(h: int, m: int, s: int) -> int:
    """Convierte (horas, minutos, segundos) a segundos totales."""
    return h * 3600 + m * 60 + s
