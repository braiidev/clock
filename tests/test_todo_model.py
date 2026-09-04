"""Tests para features.todo.model."""

import datetime

from clock_tui.features.todo.model import (
    TodoModel,
    todo_is_done,
    todo_set_done,
)


def _model(n: int = 0) -> TodoModel:
    todos = [
        {
            "id": i,
            "tipo": "tarea",
            "texto": f"T{i}",
            "activo": True,
            "recordarme": False,
            "repeat_days": [],
            "last_done_date": None,
            "alarma_hora": 10,
            "alarma_min": 0,
            "alarma_dia": 1,
            "alarma_mes": 1,
            "alarma_anio": 2025,
            "_disparada": False,
        }
        for i in range(n)
    ]
    return TodoModel(todos=todos, next_id=n + 1)


# ── todo_is_done / todo_set_done ──


def test_todo_is_done_no_repeat():
    t = {"activo": True, "repeat_days": []}
    assert todo_is_done(t) is False
    t["activo"] = False
    assert todo_is_done(t) is True


def test_todo_set_done_no_repeat():
    t = {"activo": True, "repeat_days": []}
    todo_set_done(t, True)
    assert t["activo"] is False
    todo_set_done(t, False)
    assert t["activo"] is True


def test_todo_is_done_with_repeat():
    today = datetime.date.today().isoformat()
    t = {"repeat_days": [0, 1, 2], "last_done_date": today}
    assert todo_is_done(t) is True
    t["last_done_date"] = None
    assert todo_is_done(t) is False


# ── Navigation ──


def test_nav_down():
    m = _model(3)
    m.nav(1)
    assert m.selected_idx == 1


def test_nav_wraps():
    m = _model(3)
    m.nav(1)
    m.nav(1)
    m.nav(1)
    assert m.selected_idx == 0


def test_nav_empty():
    m = _model(0)
    m.nav(1)
    assert m.selected_idx == 0


# ── CRUD ──


def test_add():
    m = _model()
    t = m.add(texto="New")
    assert len(m.todos) == 1
    assert t["texto"] == "New"
    assert t["id"] == 1
    assert m.selected_idx == 0


def test_delete():
    m = _model(3)
    m.delete(1)
    assert len(m.todos) == 2
    assert m.todos[0]["texto"] == "T0"
    assert m.todos[1]["texto"] == "T2"


def test_delete_clamps_idx():
    m = _model(2)
    m.selected_idx = 1
    m.delete(1)
    assert m.selected_idx == 0


def test_swap():
    m = _model(3)
    m.swap(0, 2)
    assert m.todos[0]["texto"] == "T2"
    assert m.todos[2]["texto"] == "T0"


def test_toggle_done():
    m = _model(1)
    m.toggle_done(0)
    assert m.todos[0]["activo"] is False
    m.toggle_done(0)
    assert m.todos[0]["activo"] is True


def test_toggle_done_ignores_nota():
    m = _model()
    m.add(tipo="nota", texto="N1")
    m.toggle_done(0)
    assert m.todos[0].get("activo", True) is True


def test_toggle_recordarme():
    m = _model(1)
    m.toggle_recordarme(0)
    assert m.todos[0]["recordarme"] is True
    assert m.todos[0]["_disparada"] is False
    m.toggle_recordarme(0)
    assert m.todos[0]["recordarme"] is False


# ── Edit mode ──


def test_open_edit_new():
    m = _model()
    m.open_edit(idx=None)
    assert m.edit_mode is True
    assert m.edit_target is None
    assert m.temp_tipo == "tarea"
    assert m.temp_texto == ""


def test_open_edit_existing():
    m = _model(1)
    m.open_edit(idx=0)
    assert m.edit_mode is True
    assert m.edit_target == 0
    assert m.temp_texto == "T0"


def test_commit_edit_new():
    m = _model()
    m.open_edit(idx=None)
    m.temp_texto = "Comprar leche"
    m.commit_edit()
    assert len(m.todos) == 1
    assert m.todos[0]["texto"] == "Comprar leche"
    assert m.edit_mode is False


def test_commit_edit_existing():
    m = _model(1)
    m.open_edit(idx=0)
    m.temp_texto = "Updated"
    m.commit_edit()
    assert m.todos[0]["texto"] == "Updated"
    assert m.edit_mode is False


def test_commit_edit_empty_uses_default():
    m = _model()
    m.open_edit(idx=None)
    m.temp_texto = ""
    m.commit_edit()
    assert m.todos[0]["texto"] == "Nueva tarea"


def test_cancel_edit():
    m = _model()
    m.open_edit(idx=None)
    m.cancel_edit()
    assert m.edit_mode is False
    assert m.edit_target is None


# ── Dynamic fields ──


def test_n_fields_tarea():
    m = _model()
    m.open_edit(idx=None)
    assert m.n_fields == 3


def test_n_fields_nota():
    m = _model()
    m.open_edit(idx=None)
    m.temp_tipo = "nota"
    assert m.n_fields == 2


def test_n_fields_tarea_with_recordarme():
    m = _model()
    m.open_edit(idx=None)
    m.temp_recordarme = True
    assert m.n_fields == 9


def test_n_fields_tarea_with_repeat():
    m = _model()
    m.open_edit(idx=None)
    m.temp_recordarme = True
    m.temp_repetir = True
    assert m.n_fields == 7


def test_edit_toggle_tipo():
    m = _model()
    m.open_edit(idx=None)
    m.edit_toggle_tipo()
    assert m.temp_tipo == "nota"
    m.edit_toggle_tipo()
    assert m.temp_tipo == "tarea"


def test_edit_toggle_recordarme():
    m = _model()
    m.open_edit(idx=None)
    m.edit_toggle_recordarme()
    assert m.temp_recordarme is True
    m.edit_toggle_recordarme()
    assert m.temp_recordarme is False


def test_edit_adjust_hour():
    m = _model()
    m.open_edit(idx=None)
    m.temp_alarma[0] = 23
    m.edit_adjust_hour(1)
    assert m.temp_alarma[0] == 0


def test_edit_adjust_min():
    m = _model()
    m.open_edit(idx=None)
    m.temp_alarma[1] = 59
    m.edit_adjust_min(1)
    assert m.temp_alarma[1] == 0


def test_edit_toggle_day():
    m = _model()
    m.open_edit(idx=None)
    m.temp_days_cursor = 0
    m.edit_toggle_day()
    assert 0 in m.temp_days
    m.edit_toggle_day()
    assert 0 not in m.temp_days


# ── Visible range ──


def test_visible_range():
    m = _model(12)
    start, end = m.visible_range()
    assert start == 0
    assert end == 8


def test_visible_range_scrolled():
    m = _model(12)
    m.scroll_offset = 5
    start, end = m.visible_range()
    assert start == 5
    assert end == 12


# ── Item display ──


def test_item_display_tarea():
    m = _model()
    t = {
        "tipo": "tarea",
        "texto": "Comprar leche",
        "activo": True,
        "recordarme": False,
        "repeat_days": [],
        "alarma_hora": 7,
        "alarma_min": 0,
        "alarma_dia": 1,
        "alarma_mes": 1,
        "alarma_anio": 2025,
    }
    result = m.item_display(t)
    assert "\u2610" in result
    assert "Comprar leche" in result


def test_item_display_nota():
    m = _model()
    t = {"tipo": "nota", "texto": "Ideas"}
    result = m.item_display(t)
    assert "\u270e" in result
    assert "Ideas" in result


def test_item_display_with_repeat():
    m = _model()
    t = {
        "tipo": "tarea",
        "texto": "Llamar",
        "activo": True,
        "recordarme": True,
        "repeat_days": [0, 1, 2, 3, 4],
        "alarma_hora": 7,
        "alarma_min": 30,
        "alarma_dia": 1,
        "alarma_mes": 1,
        "alarma_anio": 2025,
    }
    result = m.item_display(t)
    assert "L-V" in result
    assert "07:30" in result
