"""Tests para features.dashboard.model."""

import datetime

from clock_tui.features.dashboard.model import (
    ActivityRow,
    DashboardSnapshot,
    _todo_is_done,
)


def _snap(**kw) -> DashboardSnapshot:
    defaults = dict(now=datetime.datetime(2025, 6, 16, 14, 5, 9))
    defaults.update(kw)
    return DashboardSnapshot(**defaults)


def test_format_time_24h():
    snap = _snap()
    assert DashboardSnapshot.format_time(snap.now) == "14:05:09"


def test_format_time_12h():
    snap = _snap()
    assert DashboardSnapshot.format_time(snap.now, format_24h=False) == "02:05:09 PM"


def test_format_time_no_seconds():
    snap = _snap()
    assert DashboardSnapshot.format_time(snap.now, show_seconds=False) == "14:05"


def test_format_date():
    snap = _snap()
    result = DashboardSnapshot.format_date(snap.now)
    assert "Lun" in result
    assert "16" in result
    assert "Jun" in result


def test_activities_empty():
    snap = _snap()
    assert snap.activities == []


def test_activities_with_alarm():
    alarm = {"nombre": "Reunion", "hora": 15, "minutos": 0, "repeat_days": None}
    snap = _snap(next_alarm=alarm)
    acts = snap.activities
    assert len(acts) == 1
    assert "Reunion" in acts[0].label
    assert acts[0].target_view == 2


def test_activities_with_timers():
    timers = [
        {"name": "T1", "remaining": 120},
        {"name": "T2", "remaining": 60},
    ]
    snap = _snap(active_timers=timers)
    acts = snap.activities
    assert len(acts) == 2
    assert "T1" in acts[0].label
    assert "T2" in acts[1].label
    assert acts[0].target_view == 4


def test_activities_with_stopwatch():
    snap = _snap(sw_active=True, sw_elapsed=3661.5)
    acts = snap.activities
    assert len(acts) == 1
    assert "Crono" in acts[0].label
    assert "01:01:01" in acts[0].label
    assert acts[0].target_view == 5


def test_activities_with_pending_tasks():
    snap = _snap(total_tasks=5, done_tasks=2)
    acts = snap.activities
    assert len(acts) == 1
    assert "3" in acts[0].label
    assert "2/5" in acts[0].label
    assert acts[0].target_view == 6


def test_activities_with_snoozed():
    snap = _snap(snoozed_count=2)
    acts = snap.activities
    assert len(acts) == 1
    assert "2" in acts[0].label
    assert acts[0].target_view == 2


def test_activities_combined():
    timers = [{"name": "T1", "remaining": 60}]
    snap = _snap(
        active_timers=timers,
        sw_active=True,
        sw_elapsed=100,
        total_tasks=3,
        done_tasks=1,
        snoozed_count=1,
    )
    acts = snap.activities
    labels = [a.label for a in acts]
    assert any("T1" in l for l in labels)
    assert any("Crono" in l for l in labels)
    assert any("2" in l for l in labels)
    assert any("pospuesta" in l for l in labels)


def test_activities_max_3_timers():
    timers = [
        {"name": "T1", "remaining": 60},
        {"name": "T2", "remaining": 60},
        {"name": "T3", "remaining": 60},
        {"name": "T4", "remaining": 60},
    ]
    snap = _snap(active_timers=timers)
    acts = snap.activities
    assert len(acts) == 4
    assert "+1" in acts[3].label


def test_todo_is_done():
    assert _todo_is_done({"done": True}) is True
    assert _todo_is_done({"status": "done"}) is True
    assert _todo_is_done({"done": False}) is False
    assert _todo_is_done({}) is False


def test_selected_idx_default():
    snap = _snap()
    assert snap.selected_idx == 0
