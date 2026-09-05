"""Tests para features.timers.controller."""

import curses

from clock_tui.features.timers.controller import TimersController
from clock_tui.features.timers.model import Timer, TimersModel


def _ctx() -> dict:
    return {}


def _model(n: int = 3) -> TimersModel:
    timers = [Timer(name=f"T{i}", time=[0, i + 1, 0]) for i in range(n)]
    return TimersModel(timers=timers)


# ── Navigation ──


def test_down_wraps():
    c = TimersController()
    m = _model(3)
    c.handle(m, curses.KEY_DOWN, _ctx())
    assert m.selected_idx == 1


def test_j_navigates_down():
    c = TimersController()
    m = _model(3)
    c.handle(m, ord("j"), _ctx())
    assert m.selected_idx == 1


def test_k_navigates_up():
    c = TimersController()
    m = _model(3)
    m.selected_idx = 1
    c.handle(m, ord("k"), _ctx())
    assert m.selected_idx == 0


def test_down_wraps_to_start():
    c = TimersController()
    m = _model(3)
    m.selected_idx = 2
    c.handle(m, curses.KEY_DOWN, _ctx())
    assert m.selected_idx == 0


def test_up_wraps():
    c = TimersController()
    m = _model(3)
    c.handle(m, curses.KEY_UP, _ctx())
    assert m.selected_idx == 2


def test_nav_empty():
    c = TimersController()
    m = TimersModel()
    c.handle(m, curses.KEY_DOWN, _ctx())
    assert m.selected_idx == 0


# ── Add ──


def test_add_timer():
    c = TimersController()
    m = _model(2)
    r = c.handle(m, ord("a"), _ctx())
    assert len(m.timers) == 3
    assert m.timers[2].name == "Temporizador3"
    assert m.selected_idx == 2
    assert r.needs_save is True


def test_add_at_max_does_nothing():
    c = TimersController()
    m = _model(10)
    c.handle(m, ord("a"), _ctx())
    assert len(m.timers) == 10


# ── Delete ──


def test_delete_pide_confirmacion():
    """'d' ya no borra directo: entra en modo confirmación."""
    c = TimersController()
    m = _model(3)
    r = c.handle(m, ord("d"), _ctx())
    assert m.confirm_delete is True
    assert r.needs_save is False
    assert len(m.timers) == 3


def test_confirm_delete_con_s():
    c = TimersController()
    m = _model(3)
    c.handle(m, ord("d"), _ctx())
    r = c.handle(m, ord("s"), _ctx())
    assert len(m.timers) == 2
    assert m.confirm_delete is False
    assert r.needs_save is True


def test_confirm_delete_con_y():
    c = TimersController()
    m = _model(3)
    c.handle(m, ord("d"), _ctx())
    c.handle(m, ord("y"), _ctx())
    assert len(m.timers) == 2
    assert m.confirm_delete is False


def test_confirm_delete_con_S_mayuscula():
    c = TimersController()
    m = _model(3)
    c.handle(m, ord("d"), _ctx())
    c.handle(m, ord("S"), _ctx())
    assert len(m.timers) == 2


def test_confirm_delete_con_enter():
    c = TimersController()
    m = _model(3)
    c.handle(m, ord("d"), _ctx())
    c.handle(m, ord("\n"), _ctx())
    assert len(m.timers) == 2


def test_confirm_delete_cualquier_tecla_cancela():
    c = TimersController()
    m = _model(3)
    c.handle(m, ord("d"), _ctx())
    r = c.handle(m, ord("x"), _ctx())
    assert len(m.timers) == 3
    assert m.confirm_delete is False
    assert r.needs_save is False


def test_delete_last_keeps_one():
    c = TimersController()
    m = _model(1)
    c.handle(m, ord("d"), _ctx())
    assert len(m.timers) == 1
    assert m.confirm_delete is False
    c.handle(m, ord("y"), _ctx())
    assert len(m.timers) == 1


def test_delete_clamps_idx():
    c = TimersController()
    m = _model(3)
    m.selected_idx = 2
    c.handle(m, ord("d"), _ctx())
    c.handle(m, ord("y"), _ctx())
    assert m.selected_idx == 1


# ── Reorden ──


def test_J_reorder_down():
    c = TimersController()
    m = _model(3)
    r = c.handle(m, ord("J"), _ctx())
    assert m.timers[0].name == "T1"
    assert m.timers[1].name == "T0"
    assert m.selected_idx == 1
    assert r.needs_save is True


def test_J_no_move_at_end():
    c = TimersController()
    m = _model(2)
    m.selected_idx = 1
    c.handle(m, ord("J"), _ctx())
    assert m.timers[1].name == "T1"
    assert m.selected_idx == 1


def test_K_reorder_up():
    c = TimersController()
    m = _model(3)
    m.selected_idx = 1
    c.handle(m, ord("K"), _ctx())
    assert m.timers[0].name == "T1"
    assert m.timers[1].name == "T0"
    assert m.selected_idx == 0


def test_K_no_move_at_start():
    c = TimersController()
    m = _model(3)
    c.handle(m, ord("K"), _ctx())
    assert m.timers[0].name == "T0"
    assert m.selected_idx == 0


# ── Edit name ──


def test_edit_name_enters_mode():
    c = TimersController()
    m = _model()
    c.handle(m, ord("e"), _ctx())
    assert m.edit_mode is True
    assert m.temp_name == "T0"


def test_edit_name_save():
    c = TimersController()
    m = _model()
    m.edit_mode = True
    m.temp_name = "Nuevo"
    r = c.handle(m, ord("\n"), _ctx())
    assert m.timers[0].name == "Nuevo"
    assert m.edit_mode is False
    assert r.needs_save is True


def test_edit_name_cancel():
    c = TimersController()
    m = _model()
    m.edit_mode = True
    r = c.handle(m, 27, _ctx())
    assert m.edit_mode is False
    assert m.timers[0].name == "T0"


def test_edit_name_backspace():
    c = TimersController()
    m = _model()
    m.edit_mode = True
    m.temp_name = "abc"
    c.handle(m, curses.KEY_BACKSPACE, _ctx())
    assert m.temp_name == "ab"


def test_edit_name_type_char():
    c = TimersController()
    m = _model()
    m.edit_mode = True
    m.temp_name = ""
    c.handle(m, ord("X"), _ctx())
    assert m.temp_name == "X"


# ── Cycle field ──


def test_cycle_field():
    c = TimersController()
    m = _model()
    assert m.time_field == 0
    c.handle(m, 9, _ctx())
    assert m.time_field == 1
    c.handle(m, 9, _ctx())
    assert m.time_field == 2
    c.handle(m, 9, _ctx())
    assert m.time_field == 0


def test_cycle_field_skips_if_active():
    c = TimersController()
    m = _model()
    m.timers[0].active = True
    c.handle(m, 9, _ctx())
    assert m.time_field == 0


# ── Adjust ──


def test_adjust_right():
    c = TimersController()
    m = _model()
    m.time_field = 1
    c.handle(m, curses.KEY_RIGHT, _ctx())
    assert m.timers[0].time[1] == 2


def test_adjust_left():
    c = TimersController()
    m = _model()
    m.time_field = 1
    c.handle(m, curses.KEY_LEFT, _ctx())
    assert m.timers[0].time[1] == 0


def test_adjust_wraps():
    c = TimersController()
    m = _model()
    m.time_field = 1
    m.timers[0].time[1] = 59
    c.handle(m, curses.KEY_RIGHT, _ctx())
    assert m.timers[0].time[1] == 0


def test_adjust_h_l_mirror():
    c = TimersController()
    m = _model()
    m.time_field = 1
    c.handle(m, ord("l"), _ctx())
    assert m.timers[0].time[1] == 2
    c.handle(m, ord("h"), _ctx())
    assert m.timers[0].time[1] == 1


def test_adjust_hours_limit():
    c = TimersController()
    m = _model()
    m.time_field = 0
    m.timers[0].time[0] = 99
    c.handle(m, curses.KEY_RIGHT, _ctx())
    assert m.timers[0].time[0] == 0


def test_adjust_skips_if_active():
    c = TimersController()
    m = _model()
    m.timers[0].active = True
    c.handle(m, curses.KEY_RIGHT, _ctx())
    assert m.timers[0].time[0] == 0


def test_adjust_updates_remaining():
    c = TimersController()
    m = _model()
    m.time_field = 1
    c.handle(m, curses.KEY_RIGHT, _ctx())
    assert m.timers[0].remaining == 120.0


# ── Toggle ──


def test_toggle_play():
    c = TimersController()
    m = _model()
    r = c.handle(m, ord(" "), _ctx(), now=200.0)
    assert m.timers[0].active is True
    assert m.timers[0].last_tick == 200.0


def test_toggle_pause():
    c = TimersController()
    m = _model()
    m.timers[0].active = True
    c.handle(m, ord(" "), _ctx())
    assert m.timers[0].active is False


def test_toggle_at_zero_resets():
    c = TimersController()
    m = _model()
    m.timers[0].remaining = 0.0
    c.handle(m, ord(" "), _ctx(), now=100.0)
    assert m.timers[0].remaining == 60.0
    assert m.timers[0].active is True


# ── Reset selected ──


def test_reset_selected():
    c = TimersController()
    m = _model()
    m.timers[0].active = True
    m.timers[0].remaining = 10.0
    c.handle(m, ord("r"), _ctx())
    assert m.timers[0].active is False
    assert m.timers[0].remaining == 60.0
