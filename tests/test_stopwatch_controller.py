"""Tests para features.stopwatch.controller."""

from clock_tui.features.stopwatch.controller import StopwatchController
from clock_tui.features.stopwatch.model import StopwatchModel


def _make_active_model(elapsed: float = 10.0) -> StopwatchModel:
    return StopwatchModel(
        active=True, start_time=100.0, base_elapsed=elapsed - 100.0 + 100.0
    )


def _ctx(global_paused: bool = False) -> dict:
    return {"global_paused": global_paused}


# ── Toggle (Space) ──


def test_space_starts_when_inactive():
    c = StopwatchController()
    m = StopwatchModel()
    r = c.handle(m, ord(" "), _ctx(), now=200.0)
    assert m.active is True
    assert m.start_time == 200.0
    assert r.alert_title is None


def test_space_pauses_when_active():
    c = StopwatchController()
    m = StopwatchModel(active=True, start_time=100.0, base_elapsed=5.0)
    r = c.handle(m, ord(" "), _ctx(), now=130.0)
    assert m.active is False
    assert m.start_time is None
    assert m.base_elapsed == 35.0
    assert r.alert_title is None


def test_space_when_paused_globally_does_nothing():
    c = StopwatchController()
    m = StopwatchModel()
    c.handle(m, ord(" "), _ctx(global_paused=True), now=200.0)
    assert m.active is False


def test_pause_preserves_elapsed():
    c = StopwatchController()
    m = StopwatchModel(active=True, start_time=100.0, base_elapsed=10.0)
    c.handle(m, ord(" "), _ctx(), now=120.0)
    assert m.base_elapsed == 30.0


# ── Lap (m) ──


def test_lap_when_active_records_diff():
    c = StopwatchController()
    m = StopwatchModel(active=True, start_time=100.0, base_elapsed=0.0)
    c.handle(m, ord("m"), _ctx(), now=105.0)
    assert len(m.records) == 1
    assert m.records[0] == 5.0


def test_lap_when_inactive_does_nothing():
    c = StopwatchController()
    m = StopwatchModel()
    c.handle(m, ord("m"), _ctx())
    assert m.records == []


def test_multiple_laps():
    c = StopwatchController()
    m = StopwatchModel(active=True, start_time=100.0, base_elapsed=0.0)
    c.handle(m, ord("m"), _ctx(), now=105.0)
    c.handle(m, ord("m"), _ctx(), now=110.0)
    assert len(m.records) == 2
    assert m.records[0] == 5.0
    assert m.records[1] == 5.0


def test_lap_updates_scroll_offset():
    c = StopwatchController()
    m = StopwatchModel(active=True, start_time=100.0, base_elapsed=0.0)
    for i in range(7):
        c.handle(m, ord("m"), _ctx(), now=100.0 + i + 1)
    assert m.scroll_offset == 2


# ── Delete last lap (d) ──


def test_delete_last_lap():
    c = StopwatchController()
    m = StopwatchModel(records=[5.0, 3.0], last_record_at=8.0)
    c.handle(m, ord("d"), _ctx())
    assert len(m.records) == 1
    assert m.records[0] == 5.0
    assert m.last_record_at == 5.0


def test_delete_empty_records_does_nothing():
    c = StopwatchController()
    m = StopwatchModel()
    c.handle(m, ord("d"), _ctx())
    assert m.records == []


def test_delete_all_records():
    c = StopwatchController()
    m = StopwatchModel(records=[5.0])
    c.handle(m, ord("d"), _ctx())
    assert m.records == []
    assert m.last_record_at == 0.0


# ── Reset (r) ──


def test_reset_clears_everything():
    c = StopwatchController()
    m = StopwatchModel(
        active=True,
        start_time=100.0,
        base_elapsed=10.0,
        records=[5.0, 3.0],
        last_record_at=8.0,
        scroll_offset=2,
    )
    c.handle(m, ord("r"), _ctx())
    assert m.active is False
    assert m.start_time is None
    assert m.base_elapsed == 0.0
    assert m.records == []
    assert m.last_record_at == 0.0
    assert m.scroll_offset == 0


# ── Unknown key ──


def test_unknown_key_does_nothing():
    c = StopwatchController()
    m = StopwatchModel()
    before = (m.active, m.base_elapsed, m.records)
    c.handle(m, ord("x"), _ctx())
    assert (m.active, m.base_elapsed, m.records) == before
