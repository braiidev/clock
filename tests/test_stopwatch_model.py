"""Tests para features.stopwatch.model."""

from clock_tui.features.stopwatch.model import StopwatchModel


def test_initial_state():
    m = StopwatchModel()
    assert m.active is False
    assert m.start_time is None
    assert m.base_elapsed == 0.0
    assert m.records == []
    assert m.last_record_at == 0.0
    assert m.scroll_offset == 0


def test_elapsed_when_inactive():
    m = StopwatchModel(base_elapsed=42.5)
    assert m.elapsed(1000.0) == 42.5


def test_elapsed_when_active():
    m = StopwatchModel(active=True, start_time=100.0, base_elapsed=10.0)
    assert m.elapsed(130.0) == 40.0


def test_elapsed_hms():
    m = StopwatchModel(base_elapsed=3661.0)
    assert m.elapsed_hms() == (1, 1, 1)


def test_elapsed_cs():
    m = StopwatchModel(base_elapsed=10.42)
    assert m.elapsed_cs() == 42


def test_elapsed_cs_zero_fraction():
    m = StopwatchModel(base_elapsed=5.0)
    assert m.elapsed_cs() == 0
