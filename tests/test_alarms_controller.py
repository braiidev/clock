"""Tests para features.alarms.controller."""

import curses

from clock_tui.features.alarms.controller import AlarmsController
from clock_tui.features.alarms.model import Alarm, AlarmsModel


def _ctx() -> dict:
    return {}


def _es(**kw) -> dict:
    return {
        "edit_mode": False,
        "edit_target": None,
        "edit_field": 0,
        "temp_name": "",
        "temp_time": [0, 0],
        "temp_time_field": 0,
        "temp_days": [],
        "temp_days_cursor": 0,
        "confirm_delete": False,
        **kw,
    }


def _model(n: int = 3) -> AlarmsModel:
    alarms = [Alarm(nombre=f"A{i}", hora=i, minutos=0) for i in range(n)]
    return AlarmsModel(alarms=alarms)


# ── Navigation ──


def test_down():
    c = AlarmsController()
    m = _model()
    c.handle(m, curses.KEY_DOWN, _ctx())
    assert m.selected_idx == 1


def test_j_navigates_down():
    c = AlarmsController()
    m = _model()
    c.handle(m, ord("j"), _ctx())
    assert m.selected_idx == 1


def test_k_navigates_up():
    c = AlarmsController()
    m = _model()
    m.selected_idx = 1
    c.handle(m, ord("k"), _ctx())
    assert m.selected_idx == 0


def test_up_wraps():
    c = AlarmsController()
    m = _model()
    c.handle(m, curses.KEY_UP, _ctx())
    assert m.selected_idx == 2


def test_nav_empty():
    c = AlarmsController()
    m = AlarmsModel()
    c.handle(m, curses.KEY_DOWN, _ctx())


# ── Toggle ──


def test_toggle():
    c = AlarmsController()
    m = _model()
    r = c.handle(m, ord(" "), _ctx())
    assert m.alarms[0].status == "desactivado"
    assert r.needs_save is True


def test_toggle_empty():
    c = AlarmsController()
    m = AlarmsModel()
    c.handle(m, ord(" "), _ctx())


# ── Delete ──


def test_confirm_delete():
    c = AlarmsController()
    m = _model()
    es = _es()
    c.handle(m, ord("d"), _ctx(), es)
    assert es["confirm_delete"] is True


def test_confirm_delete_yes():
    c = AlarmsController()
    m = _model()
    es = _es(confirm_delete=True)
    r = c.handle(m, ord("y"), _ctx(), es)
    assert len(m.alarms) == 2
    assert es["confirm_delete"] is False
    assert r.needs_save is True


def test_confirm_delete_s_si():
    c = AlarmsController()
    m = _model()
    es = _es(confirm_delete=True)
    c.handle(m, ord("s"), _ctx(), es)
    assert len(m.alarms) == 2
    assert es["confirm_delete"] is False


def test_confirm_delete_S_mayuscula():
    c = AlarmsController()
    m = _model()
    es = _es(confirm_delete=True)
    c.handle(m, ord("S"), _ctx(), es)
    assert len(m.alarms) == 2


def test_confirm_delete_enter():
    c = AlarmsController()
    m = _model()
    es = _es(confirm_delete=True)
    c.handle(m, ord("\n"), _ctx(), es)
    assert len(m.alarms) == 2


def test_confirm_delete_no():
    c = AlarmsController()
    m = _model()
    es = _es(confirm_delete=True)
    c.handle(m, ord("x"), _ctx(), es)
    assert len(m.alarms) == 3
    assert es["confirm_delete"] is False


# ── Reorden ──


def test_J_reorder_down():
    c = AlarmsController()
    m = _model(3)
    r = c.handle(m, ord("J"), _ctx(), _es())
    assert m.alarms[0].nombre == "A1"
    assert m.alarms[1].nombre == "A0"
    assert m.selected_idx == 1
    assert r.needs_save is True


def test_J_no_move_at_end():
    c = AlarmsController()
    m = _model(2)
    m.selected_idx = 1
    c.handle(m, ord("J"), _ctx(), _es())
    assert m.alarms[1].nombre == "A1"
    assert m.selected_idx == 1


def test_K_reorder_up():
    c = AlarmsController()
    m = _model(3)
    m.selected_idx = 1
    c.handle(m, ord("K"), _ctx(), _es())
    assert m.alarms[0].nombre == "A1"
    assert m.alarms[1].nombre == "A0"
    assert m.selected_idx == 0


def test_K_no_move_at_start():
    c = AlarmsController()
    m = _model(3)
    c.handle(m, ord("K"), _ctx(), _es())
    assert m.alarms[0].nombre == "A0"
    assert m.selected_idx == 0


# ── Edit mode ──


def test_new_alarm():
    c = AlarmsController()
    m = _model()
    es = _es()
    c.handle(m, ord("a"), _ctx(), es)
    assert es["edit_mode"] is True
    assert es["temp_name"] == "Alarma"


def test_edit_alarm():
    c = AlarmsController()
    m = _model()
    es = _es()
    c.handle(m, ord("e"), _ctx(), es)
    assert es["edit_mode"] is True
    assert es["edit_target"] == 0
    assert es["temp_name"] == "A0"
    assert es["temp_time"] == [0, 0]


def test_edit_field_navigation():
    c = AlarmsController()
    m = _model()
    es = _es(edit_mode=True, edit_field=0)
    c.handle(m, curses.KEY_DOWN, _ctx(), es)
    assert es["edit_field"] == 1
    c.handle(m, curses.KEY_DOWN, _ctx(), es)
    assert es["edit_field"] == 2
    c.handle(m, curses.KEY_DOWN, _ctx(), es)
    assert es["edit_field"] == 0


def test_edit_name_type():
    c = AlarmsController()
    m = _model()
    es = _es(edit_mode=True, edit_field=0, temp_name="")
    c.handle(m, ord("X"), _ctx(), es)
    assert es["temp_name"] == "X"


def test_edit_name_backspace():
    c = AlarmsController()
    m = _model()
    es = _es(edit_mode=True, edit_field=0, temp_name="abc")
    c.handle(m, curses.KEY_BACKSPACE, _ctx(), es)
    assert es["temp_name"] == "ab"


def test_edit_name_enter_advances():
    c = AlarmsController()
    m = _model()
    es = _es(edit_mode=True, edit_field=0, temp_name="X")
    c.handle(m, ord("\n"), _ctx(), es)
    assert es["edit_field"] == 1


def test_edit_time_tab():
    c = AlarmsController()
    m = _model()
    es = _es(edit_mode=True, edit_field=1, temp_time=[10, 30])
    c.handle(m, 9, _ctx(), es)
    assert es["temp_time_field"] == 1


def test_edit_time_right():
    c = AlarmsController()
    m = _model()
    es = _es(edit_mode=True, edit_field=1, temp_time=[10, 30], temp_time_field=1)
    c.handle(m, curses.KEY_RIGHT, _ctx(), es)
    assert es["temp_time"] == [10, 31]


def test_edit_time_left():
    c = AlarmsController()
    m = _model()
    es = _es(edit_mode=True, edit_field=1, temp_time=[10, 30], temp_time_field=1)
    c.handle(m, curses.KEY_LEFT, _ctx(), es)
    assert es["temp_time"] == [10, 29]


def test_edit_time_enter_advances():
    c = AlarmsController()
    m = _model()
    es = _es(edit_mode=True, edit_field=1)
    c.handle(m, ord("\n"), _ctx(), es)
    assert es["edit_field"] == 2


def test_edit_days_toggle():
    c = AlarmsController()
    m = _model()
    es = _es(edit_mode=True, edit_field=2, temp_days=[], temp_days_cursor=0)
    c.handle(m, ord(" "), _ctx(), es)
    assert es["temp_days"] == [0]


def test_edit_days_toggle_off():
    c = AlarmsController()
    m = _model()
    es = _es(edit_mode=True, edit_field=2, temp_days=[0, 1], temp_days_cursor=0)
    c.handle(m, ord(" "), _ctx(), es)
    assert es["temp_days"] == [1]


def test_edit_days_cursor():
    c = AlarmsController()
    m = _model()
    es = _es(edit_mode=True, edit_field=2, temp_days_cursor=0)
    c.handle(m, curses.KEY_RIGHT, _ctx(), es)
    assert es["temp_days_cursor"] == 1


def test_edit_days_save():
    c = AlarmsController()
    m = _model()
    es = _es(
        edit_mode=True,
        edit_field=2,
        temp_name="Nueva",
        temp_time=[8, 30],
        temp_days=[0, 1, 2],
        edit_target=None,
    )
    r = c.handle(m, ord("\n"), _ctx(), es)
    assert len(m.alarms) == 4
    saved = m.alarms[3]
    assert saved.nombre == "Nueva"
    assert saved.hora == 8
    assert saved.minutos == 30
    assert saved.repeat_days == [0, 1, 2]
    assert es["edit_mode"] is False
    assert r.needs_save is True


def test_edit_existing_alarm():
    c = AlarmsController()
    m = _model()
    es = _es(
        edit_mode=True,
        edit_field=2,
        temp_name="Modificada",
        temp_time=[12, 0],
        temp_days=[5],
        edit_target=0,
    )
    c.handle(m, ord("\n"), _ctx(), es)
    assert m.alarms[0].nombre == "Modificada"
    assert m.alarms[0].hora == 12


def test_edit_cancel():
    c = AlarmsController()
    m = _model()
    es = _es(edit_mode=True)
    r = c.handle(m, 27, _ctx(), es)
    assert es["edit_mode"] is False
    assert r.edit_exit is True
