"""Tests para features.clock.controller."""

import curses

from clock_tui.features.clock.controller import ClockController
from clock_tui.features.clock.model import ClockModel, WorldClock


def _ctx() -> dict:
    return {}


def _model(n: int = 0) -> ClockModel:
    wc = [WorldClock(zona="UTC", apodo=f"W{i}") for i in range(n)]
    return ClockModel(wc_list=wc)


# ── Normal mode ──


def test_right_navigates_wc():
    c = ClockController()
    m = _model(3)
    c.handle(m, curses.KEY_RIGHT, _ctx())
    assert m.wc_idx == 1


def test_j_navigates_wc_next():
    c = ClockController()
    m = _model(3)
    c.handle(m, ord("j"), _ctx())
    assert m.wc_idx == 1


def test_down_navigates_wc():
    c = ClockController()
    m = _model(3)
    c.handle(m, curses.KEY_DOWN, _ctx())
    assert m.wc_idx == 1


def test_up_navigates_wc_prev():
    c = ClockController()
    m = _model(3)
    m.wc_idx = 1
    c.handle(m, curses.KEY_UP, _ctx())
    assert m.wc_idx == 0


def test_k_navigates_wc_prev():
    c = ClockController()
    m = _model(3)
    m.wc_idx = 1
    c.handle(m, ord("k"), _ctx())
    assert m.wc_idx == 0


def test_right_wraps():
    c = ClockController()
    m = _model(3)
    m.wc_idx = 2
    c.handle(m, curses.KEY_RIGHT, _ctx())
    assert m.wc_idx == 0


def test_left_navigates_wc():
    c = ClockController()
    m = _model(3)
    c.handle(m, curses.KEY_LEFT, _ctx())
    assert m.wc_idx == 2


def test_right_no_wc():
    c = ClockController()
    m = _model(0)
    c.handle(m, curses.KEY_RIGHT, _ctx())
    assert m.wc_idx == 0


def test_a_opens_picker():
    c = ClockController()
    m = _model()
    c.handle(m, ord("a"), _ctx())
    assert m.picker.open is True


def test_e_opens_picker_for_edit():
    c = ClockController()
    m = _model(2)
    c.handle(m, ord("e"), _ctx())
    assert m.picker.open is True
    assert m.picker.edit_target == 0


def test_e_no_wc():
    c = ClockController()
    m = _model(0)
    c.handle(m, ord("e"), _ctx())
    assert m.picker.open is False


def test_d_confirm_delete():
    c = ClockController()
    m = _model(2)
    c.handle(m, ord("d"), _ctx())
    assert m.confirm_delete is True


def test_d_no_wc():
    c = ClockController()
    m = _model(0)
    c.handle(m, ord("d"), _ctx())
    assert m.confirm_delete is False


# ── Picker mode ──


def test_picker_nav_down():
    c = ClockController()
    m = _model()
    m.picker_open()
    initial = m.picker.idx
    c.handle(m, curses.KEY_DOWN, _ctx())
    assert m.picker.idx == initial + 1


def test_picker_nav_up():
    c = ClockController()
    m = _model()
    m.picker_open()
    c.handle(m, curses.KEY_UP, _ctx())
    assert m.picker.idx == len(m.picker.zones) - 1


def test_picker_nav_j_k():
    c = ClockController()
    m = _model()
    m.picker_open()
    initial = m.picker.idx
    c.handle(m, ord("j"), _ctx())
    assert m.picker.idx == initial + 1
    c.handle(m, ord("k"), _ctx())
    assert m.picker.idx == initial


def test_picker_f_opens_filter():
    c = ClockController()
    m = _model()
    m.picker_open()
    c.handle(m, ord("f"), _ctx())
    assert m.picker.filter_active is True


def test_picker_type_filter():
    c = ClockController()
    m = _model()
    m.picker_open()
    m.picker.filter_active = True
    c.handle(m, ord("L"), _ctx())
    assert m.picker.filter_text == "L"


def test_picker_backspace_filter():
    c = ClockController()
    m = _model()
    m.picker_open()
    m.picker.filter_active = True
    m.picker.filter_text = "abc"
    c.handle(m, curses.KEY_BACKSPACE, _ctx())
    assert m.picker.filter_text == "ab"


def test_picker_esc_clears_filter():
    c = ClockController()
    m = _model()
    m.picker_open()
    m.picker.filter_active = True
    m.picker.filter_text = "test"
    c.handle(m, 27, _ctx())
    assert m.picker.filter_active is False
    assert m.picker.filter_text == ""


def test_picker_enter_confirms_zone():
    c = ClockController()
    m = _model()
    m.picker_open()
    c.handle(m, ord("\n"), _ctx())
    assert m.edit_nick.active is True


def test_picker_esc_closes():
    c = ClockController()
    m = _model()
    m.picker_open()
    c.handle(m, 27, _ctx())
    assert m.picker.open is False


# ── Edit nickname ──


def test_edit_nick_type():
    c = ClockController()
    m = _model()
    m.picker_open()
    m.picker_confirm_zone()
    m.edit_nick.temp_name = ""
    c.handle(m, ord("X"), _ctx())
    assert m.edit_nick.temp_name == "X"


def test_edit_nick_backspace():
    c = ClockController()
    m = _model()
    m.picker_open()
    m.picker_confirm_zone()
    m.edit_nick.temp_name = "abc"
    c.handle(m, curses.KEY_BACKSPACE, _ctx())
    assert m.edit_nick.temp_name == "ab"


def test_edit_nick_enter_saves():
    c = ClockController()
    m = _model()
    m.picker_open()
    m.picker_confirm_zone()
    m.edit_nick.temp_name = "MiReloj"
    r = c.handle(m, ord("\n"), _ctx())
    assert len(m.wc_list) == 1
    assert m.wc_list[0].apodo == "MiReloj"
    assert r.needs_save is True
    assert m.edit_nick.active is False


def test_edit_nick_esc_cancels():
    c = ClockController()
    m = _model()
    m.picker_open()
    m.picker_confirm_zone()
    c.handle(m, 27, _ctx())
    assert m.edit_nick.active is False
    assert m.picker.open is False


def test_edit_nick_enter_empty_uses_code():
    c = ClockController()
    m = _model()
    m.picker_open()
    m.picker_confirm_zone()
    m.edit_nick.temp_name = ""
    c.handle(m, ord("\n"), _ctx())
    assert len(m.wc_list) == 1
    assert m.wc_list[0].apodo is not None


# ── Confirm delete ──


def test_confirm_delete_yes():
    c = ClockController()
    m = _model(2)
    m.confirm_delete = True
    r = c.handle(m, ord("y"), _ctx())
    assert len(m.wc_list) == 1
    assert m.confirm_delete is False
    assert r.needs_save is True


def test_confirm_delete_s_si():
    c = ClockController()
    m = _model(2)
    m.confirm_delete = True
    c.handle(m, ord("s"), _ctx())
    assert len(m.wc_list) == 1
    assert m.confirm_delete is False


def test_confirm_delete_S_mayuscula():
    c = ClockController()
    m = _model(2)
    m.confirm_delete = True
    c.handle(m, ord("S"), _ctx())
    assert len(m.wc_list) == 1
    assert m.confirm_delete is False


def test_confirm_delete_enter():
    c = ClockController()
    m = _model(2)
    m.confirm_delete = True
    c.handle(m, ord("\n"), _ctx())
    assert len(m.wc_list) == 1


def test_confirm_delete_no():
    c = ClockController()
    m = _model(2)
    m.confirm_delete = True
    c.handle(m, ord("x"), _ctx())
    assert len(m.wc_list) == 2
    assert m.confirm_delete is False


# ── Reorden de world clocks ──


def test_J_reorder_wc_down():
    c = ClockController()
    m = _model(3)
    r = c.handle(m, ord("J"), _ctx())
    assert m.wc_list[0].apodo == "W1"
    assert m.wc_list[1].apodo == "W0"
    assert m.wc_idx == 1
    assert r.needs_save is True


def test_J_no_move_wc_at_end():
    c = ClockController()
    m = _model(2)
    m.wc_idx = 1
    c.handle(m, ord("J"), _ctx())
    assert m.wc_list[1].apodo == "W1"
    assert m.wc_idx == 1


def test_K_reorder_wc_up():
    c = ClockController()
    m = _model(3)
    m.wc_idx = 1
    c.handle(m, ord("K"), _ctx())
    assert m.wc_list[0].apodo == "W1"
    assert m.wc_list[1].apodo == "W0"
    assert m.wc_idx == 0


def test_K_no_move_wc_at_start():
    c = ClockController()
    m = _model(3)
    c.handle(m, ord("K"), _ctx())
    assert m.wc_list[0].apodo == "W0"
    assert m.wc_idx == 0
