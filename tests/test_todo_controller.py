"""Tests para features.todo.controller."""

import curses

from clock_tui.features.todo.controller import TodoController
from clock_tui.features.todo.model import TodoModel


def _model(n: int = 0) -> TodoModel:
    todos = [
        {"id": i, "tipo": "tarea", "texto": f"T{i}", "activo": True,
         "recordarme": False, "repeat_days": [], "last_done_date": None,
         "alarma_hora": 10, "alarma_min": 0, "alarma_dia": 1, "alarma_mes": 1,
         "alarma_anio": 2025, "_disparada": False}
        for i in range(n)
    ]
    return TodoModel(todos=todos, next_id=n + 1)


def _ctx() -> dict:
    return {}


def test_a_opens_new():
    c = TodoController()
    m = _model()
    c.handle(m, ord("a"), _ctx())
    assert m.edit_mode is True
    assert m.edit_target is None


def test_e_opens_edit():
    c = TodoController()
    m = _model(2)
    c.handle(m, ord("e"), _ctx())
    assert m.edit_mode is True
    assert m.edit_target == 0


def test_e_no_todos():
    c = TodoController()
    m = _model()
    c.handle(m, ord("e"), _ctx())
    assert m.edit_mode is False


def test_d_confirm_delete():
    c = TodoController()
    m = _model(2)
    c.handle(m, ord("d"), _ctx())
    assert m.confirm_delete is True


def test_d_no_todos():
    c = TodoController()
    m = _model()
    c.handle(m, ord("d"), _ctx())
    assert m.confirm_delete is False


def test_space_toggle_done():
    c = TodoController()
    m = _model(1)
    c.handle(m, ord(" "), _ctx())
    assert m.todos[0]["activo"] is False


def test_x_toggle_recordarme():
    c = TodoController()
    m = _model(1)
    c.handle(m, ord("x"), _ctx())
    assert m.todos[0]["recordarme"] is True


def test_down_nav():
    c = TodoController()
    m = _model(3)
    c.handle(m, curses.KEY_DOWN, _ctx())
    assert m.selected_idx == 1


def test_up_nav():
    c = TodoController()
    m = _model(3)
    m.selected_idx = 1
    c.handle(m, curses.KEY_UP, _ctx())
    assert m.selected_idx == 0


def test_right_reorder():
    c = TodoController()
    m = _model(3)
    c.handle(m, curses.KEY_RIGHT, _ctx())
    assert m.todos[0]["texto"] == "T1"
    assert m.todos[1]["texto"] == "T0"
    assert m.selected_idx == 1


def test_right_no_swap_at_end():
    c = TodoController()
    m = _model(2)
    m.selected_idx = 1
    c.handle(m, curses.KEY_RIGHT, _ctx())
    assert m.todos[1]["texto"] == "T1"


def test_left_reorder():
    c = TodoController()
    m = _model(3)
    m.selected_idx = 1
    c.handle(m, curses.KEY_LEFT, _ctx())
    assert m.todos[0]["texto"] == "T1"
    assert m.selected_idx == 0


def test_left_no_swap_at_start():
    c = TodoController()
    m = _model(2)
    m.selected_idx = 0
    c.handle(m, curses.KEY_LEFT, _ctx())
    assert m.todos[0]["texto"] == "T0"


# ── Confirm delete ──


def test_confirm_yes():
    c = TodoController()
    m = _model(2)
    m.confirm_delete = True
    r = c.handle(m, ord("y"), _ctx())
    assert len(m.todos) == 1
    assert m.confirm_delete is False
    assert r.needs_save is True


def test_confirm_enter():
    c = TodoController()
    m = _model(2)
    m.confirm_delete = True
    c.handle(m, ord("\n"), _ctx())
    assert len(m.todos) == 1


def test_confirm_no():
    c = TodoController()
    m = _model(2)
    m.confirm_delete = True
    c.handle(m, ord("x"), _ctx())
    assert len(m.todos) == 2
    assert m.confirm_delete is False


# ── Edit mode ──


def test_edit_enter_saves():
    c = TodoController()
    m = _model()
    m.open_edit(idx=None)
    m.temp_texto = "Test"
    r = c.handle(m, ord("\n"), _ctx())
    assert len(m.todos) == 1
    assert r.needs_save is True
    assert m.edit_mode is False


def test_edit_esc_cancels():
    c = TodoController()
    m = _model()
    m.open_edit(idx=None)
    c.handle(m, 27, _ctx())
    assert m.edit_mode is False
    assert len(m.todos) == 0


def test_edit_type_text():
    c = TodoController()
    m = _model()
    m.open_edit(idx=None)
    m.edit_field = 1
    c.handle(m, ord("X"), _ctx())
    assert m.temp_texto == "X"


def test_edit_backspace():
    c = TodoController()
    m = _model()
    m.open_edit(idx=None)
    m.edit_field = 1
    m.temp_texto = "abc"
    c.handle(m, curses.KEY_BACKSPACE, _ctx())
    assert m.temp_texto == "ab"


def test_edit_toggle_tipo():
    c = TodoController()
    m = _model()
    m.open_edit(idx=None)
    m.edit_field = 0
    c.handle(m, ord(" "), _ctx())
    assert m.temp_tipo == "nota"


def test_edit_toggle_recordarme():
    c = TodoController()
    m = _model()
    m.open_edit(idx=None)
    m.edit_field = 2
    c.handle(m, ord(" "), _ctx())
    assert m.temp_recordarme is True


def test_edit_nav_field():
    c = TodoController()
    m = _model()
    m.open_edit(idx=None)
    c.handle(m, curses.KEY_DOWN, _ctx())
    assert m.edit_field == 1
    c.handle(m, curses.KEY_UP, _ctx())
    assert m.edit_field == 0


def test_edit_adjust_hour():
    c = TodoController()
    m = _model()
    m.open_edit(idx=None)
    m.temp_recordarme = True
    m.edit_field = 4
    m.temp_alarma[0] = 23
    c.handle(m, curses.KEY_RIGHT, _ctx())
    assert m.temp_alarma[0] == 0
