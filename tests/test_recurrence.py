"""Tests para core.recurrence."""

import datetime

from clock_tui.core.recurrence import (
    _next_occurrence,
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


def test_next_occurrence_hoy_si_hora_no_paso():
    now = datetime.datetime(2026, 9, 5, 10, 0)
    # 2026-09-05 es sábado (weekday 5)
    r = _next_occurrence(15, 30, [], now)
    assert r == datetime.datetime(2026, 9, 5, 15, 30)


def test_next_occurrence_manana_si_hora_paso():
    now = datetime.datetime(2026, 9, 5, 10, 0)
    r = _next_occurrence(9, 0, [], now)
    assert r == datetime.datetime(2026, 9, 6, 9, 0)


def test_next_occurrence_hoy_si_dia_repite_y_no_paso():
    now = datetime.datetime(2026, 9, 5, 10, 0)  # sábado
    r = _next_occurrence(15, 0, [5, 6], now)  # S-D
    assert r == datetime.datetime(2026, 9, 5, 15, 0)


def test_next_occurrence_salta_dia_no_repetido():
    now = datetime.datetime(2026, 9, 5, 10, 0)  # sábado
    r = _next_occurrence(10, 0, [0, 1], now)  # L-X
    assert r == datetime.datetime(2026, 9, 7, 10, 0)


def test_next_occurrence_hora_pasada_salta_al_proximo_dia_repetido():
    now = datetime.datetime(2026, 9, 5, 10, 0)  # sábado
    r = _next_occurrence(9, 0, [5, 6], now)  # ya pasó hoy, mañana
    assert r == datetime.datetime(2026, 9, 6, 9, 0)
