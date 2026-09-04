"""Tests para features.dashboard.controller."""

import curses
import datetime

from clock_tui.features.dashboard.controller import DashboardController, ActionResult
from clock_tui.features.dashboard.model import DashboardSnapshot


def _snap(**kw) -> DashboardSnapshot:
    defaults = dict(now=datetime.datetime(2025, 6, 16, 14, 5, 9))
    defaults.update(kw)
    return DashboardSnapshot(**defaults)


def _ctx() -> dict:
    return {}


def test_enter_with_alarm():
    c = DashboardController()
    alarm = {"nombre": "Rev", "hora": 15, "minutos": 0, "repeat_days": None}
    snap = _snap(next_alarm=alarm)
    r = c.handle(snap, ord("\n"), _ctx())
    assert r.jump_to == 2
    assert r.jump_item == 0


def test_enter_with_timer():
    c = DashboardController()
    timers = [{"name": "T1", "remaining": 60}]
    snap = _snap(active_timers=timers)
    snap.selected_idx = 0
    r = c.handle(snap, ord("\n"), _ctx())
    assert r.jump_to == 3


def test_enter_empty():
    c = DashboardController()
    snap = _snap()
    r = c.handle(snap, ord("\n"), _ctx())
    assert r.jump_to is None


def test_u_refreshes_weather():
    c = DashboardController()
    snap = _snap()
    r = c.handle(snap, ord("u"), _ctx())
    assert r.refresh_weather is True


def test_down_navigates():
    c = DashboardController()
    timers = [{"name": "T1", "remaining": 60}, {"name": "T2", "remaining": 60}]
    snap = _snap(active_timers=timers)
    c.handle(snap, curses.KEY_DOWN, _ctx())
    assert snap.selected_idx == 1


def test_up_navigates():
    c = DashboardController()
    timers = [{"name": "T1", "remaining": 60}, {"name": "T2", "remaining": 60}]
    snap = _snap(active_timers=timers)
    snap.selected_idx = 1
    c.handle(snap, curses.KEY_UP, _ctx())
    assert snap.selected_idx == 0


def test_down_stops_at_end():
    c = DashboardController()
    timers = [{"name": "T1", "remaining": 60}]
    snap = _snap(active_timers=timers)
    snap.selected_idx = 0
    c.handle(snap, curses.KEY_DOWN, _ctx())
    assert snap.selected_idx == 0


def test_up_stops_at_start():
    c = DashboardController()
    snap = _snap()
    snap.selected_idx = 0
    c.handle(snap, curses.KEY_UP, _ctx())
    assert snap.selected_idx == 0


def test_enter_with_stopwatch():
    c = DashboardController()
    snap = _snap(sw_active=True, sw_elapsed=100)
    snap.selected_idx = 0
    r = c.handle(snap, ord("\n"), _ctx())
    assert r.jump_to == 4


def test_enter_with_todo():
    c = DashboardController()
    snap = _snap(total_tasks=3, done_tasks=1)
    snap.selected_idx = 0
    r = c.handle(snap, ord("\n"), _ctx())
    assert r.jump_to == 5
