"""Tests de render de overlays (alert, help, log viewer) sobre un curses falso."""

from __future__ import annotations

import time

from clock_tui.ui.overlay import (
    draw_activity,
    draw_alert,
    draw_help,
    draw_log_viewer,
)


class _Scr:
    def __init__(self, h: int = 24, w: int = 80) -> None:
        self.h = h
        self.w = w

    def getmaxyx(self) -> tuple[int, int]:
        return (self.h, self.w)

    def addstr(self, *a, **k) -> None:
        pass


def test_draw_alert_small_alerts_simple():
    draw_alert(_Scr(12, 40), {"title": "T", "msg": "M", "blink_state": 0}, 1, 2, 5)


def test_draw_alert_posponable_blink():
    draw_alert(
        _Scr(12, 40),
        {
            "title": "Alarma",
            "msg": "Sonando",
            "blink_state": 1,
            "posponable": True,
        },
        1,
        2,
        10,
    )


def test_draw_alert_tiny_terminal():
    draw_alert(_Scr(3, 5), {"title": "T", "msg": "M", "blink_state": 0}, 1, 2, 5)


def test_draw_help():
    draw_help(_Scr(20, 60), ["n:nuevo", "e:editar"], ["q:salir"], 8)


def test_draw_activity_sections():
    draw_activity(
        _Scr(24, 80),
        [("Alarmas", ["◷ Desayuno 06:55"]), ("Tareas", ["☐ 1. Comprar pan"])],
        8,
    )


def test_draw_activity_empty():
    draw_activity(_Scr(20, 60), [("Actividad", ["(sin actividad pendiente)"])], 8)


def test_draw_activity_tiny():
    draw_activity(_Scr(3, 5), [("Alarmas", ["◷ A 06:00"])], 8)


def test_draw_log_viewer_empty():
    assert draw_log_viewer(_Scr(24, 80), [], 0, 0, 8) == 0


def test_draw_log_viewer_scroll_keeps_valid():
    scr = _Scr(24, 80)
    entries = [
        {"ts": time.time() - i * 60, "msg": f"err {i}", "visto": True}
        for i in range(30)
    ]
    new_scroll = draw_log_viewer(scr, entries, 20, 5, 8)
    assert new_scroll >= 0


def test_draw_log_viewer_tiny():
    scr = _Scr(8, 10)
    draw_log_viewer(scr, [{"ts": time.time(), "msg": "boom", "visto": True}], 0, 0, 8)
    assert True
