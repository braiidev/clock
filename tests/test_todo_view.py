"""Tests para features.todo.view (verificación de que no muta el modelo)."""

from clock_tui.features.todo.model import TodoModel


def test_render_does_not_mutate_model():
    todos = [
        {"id": 1, "tipo": "tarea", "texto": "T1", "activo": True,
         "recordarme": False, "repeat_days": [], "last_done_date": None,
         "alarma_hora": 10, "alarma_min": 0, "alarma_dia": 1, "alarma_mes": 1,
         "alarma_anio": 2025, "_disparada": False},
    ]
    m = TodoModel(todos=todos, selected_idx=0)
    selected_before = m.selected_idx
    count_before = m.count

    from clock_tui.features.todo import view as t_view

    class FakeStdscr:
        def getmaxyx(self):
            return 24, 80

        def erase(self):
            pass

        def addstr(self, *a, **kw):
            pass

        def refresh(self):
            pass

    try:
        t_view.render(
            FakeStdscr(),
            m,
            theme={},
            pairs={"marco": 1, "texto": 6, "helpers": 2},
            config={"mostrar_marco": True, "mostrar_helpers": True},
        )
    except Exception:
        pass

    assert m.selected_idx == selected_before
    assert m.count == count_before
