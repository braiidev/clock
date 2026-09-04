"""Tests para features.timers.model."""

from clock_tui.features.timers.model import Timer, TimersModel


def test_timer_defaults():
    t = Timer()
    assert t.name == "Timer"
    assert t.time == [0, 10, 0]
    assert t.active is False
    assert t.remaining == 600.0


def test_timer_total_secs():
    t = Timer(time=[1, 30, 0])
    assert t.total_secs() == 5400


def test_timer_hms():
    t = Timer(remaining=3661.0)
    assert t.hms() == (1, 1, 1)


def test_from_data():
    data = [{"name": "T1", "time": [0, 5, 0]}, {"name": "T2", "time": [1, 0, 0]}]
    m = TimersModel.from_data(data)
    assert len(m.timers) == 2
    assert m.timers[0].name == "T1"
    assert m.timers[0].remaining == 300.0
    assert m.timers[1].remaining == 3600.0


def test_to_data():
    m = TimersModel(timers=[Timer(name="X", time=[0, 3, 30])])
    d = m.to_data()
    assert d == [{"name": "X", "time": [0, 3, 30]}]


def test_tick_no_active():
    m = TimersModel(timers=[Timer()])
    completed = m.tick(now=1000.0)
    assert completed == []


def test_tick_active_does_not_complete():
    t = Timer(active=True, last_tick=100.0, remaining=10.0)
    m = TimersModel(timers=[t])
    completed = m.tick(now=105.0)
    assert completed == []
    assert t.remaining == 5.0
    assert t.last_tick == 105.0


def test_tick_completes():
    t = Timer(active=True, last_tick=100.0, remaining=3.0)
    m = TimersModel(timers=[t])
    completed = m.tick(now=105.0)
    assert completed == [0]
    assert t.active is False
    assert t.remaining == 0.0


def test_tick_first_tick_sets_baseline():
    t = Timer(active=True, last_tick=None, remaining=10.0)
    m = TimersModel(timers=[t])
    completed = m.tick(now=200.0)
    assert completed == []
    assert t.last_tick == 200.0
    assert t.remaining == 10.0


def test_clamp_scroll():
    m = TimersModel(
        timers=[Timer() for _ in range(10)],
        selected_idx=8,
        scroll_offset=0,
    )
    m._clamp_scroll()
    assert m.scroll_offset == 3
