"""Tests para core.recurrence."""

from clock_tui.core.recurrence import (
    _repeat_days_normalize,
    _repeat_days_str,
    _todo_is_done,
    _todo_set_done,
)


def test_normalize_dedupe_and_sort():
    assert _repeat_days_normalize([5, 1, 1, 3]) == [1, 3, 5]
    assert _repeat_days_normalize(None) == []
    assert _repeat_days_normalize("abc") == []
    # 7 -> 0 (domingo, wrap)
    assert _repeat_days_normalize([7]) == [0]


def test_repeat_days_str():
    assert _repeat_days_str([]) == "una vez"
    assert _repeat_days_str([0, 1, 2, 3, 4]) == "L-V"
    assert _repeat_days_str([0, 1, 2, 3, 4, 5, 6]) == "todos"
    assert _repeat_days_str([5, 6]) == "S-D"
    assert _repeat_days_str([1, 4]) == "MV"  # M=M, V=viernes


def test_todo_done_plain():
    t = {"texto": "x", "activo": True, "repeat_days": []}
    assert _todo_is_done(t) is False
    _todo_set_done(t, True)
    assert t["activo"] is False
    assert _todo_is_done(t) is True
    _todo_set_done(t, False)
    assert t["activo"] is True


def test_todo_done_recurrent_by_date():
    t = {"texto": "x", "repeat_days": [0, 1], "last_done_date": None}
    assert _todo_is_done(t, hoy="2026-09-04") is False
    _todo_set_done(t, True, hoy="2026-09-04")
    assert _todo_is_done(t, hoy="2026-09-04") is True
    assert _todo_is_done(t, hoy="2026-09-05") is False
    _todo_set_done(t, False, hoy="2026-09-05")
    assert t["last_done_date"] is None
