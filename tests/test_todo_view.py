"""Tests para features.todo.view (verificación de que no muta el modelo)."""

from clock_tui.features.todo.model import TodoModel


def test_render_does_not_mutate_model():
    todos = [
        {
            "id": 1,
            "tipo": "tarea",
            "texto": "T1",
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
        },
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


def _todo(t: int) -> list[dict]:
    return [
        {
            "id": i,
            "tipo": "tarea",
            "texto": f"Tarea {i}",
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
        for i in range(t)
    ]


def test_scroll_ventana_seleccion_siempre_visible_alturas_chicas():
    """Regresión v0.48: con 10 tareas, la selección queda siempre visible
    (las filas fijas de hora/separador ya no roban la ventana)."""
    from clock_tui.features.todo import view as t_view

    class Rec:
        def __init__(self, h, w):
            self.h, self.w = h, w
            self.rows: list[tuple[int, int, str]] = []

        def getmaxyx(self):
            return self.h, self.w

        def erase(self):
            self.rows = []

        def addstr(self, y, x, s, *a, **k):
            self.rows.append((y, x, s))

        def refresh(self):
            pass

    for h in (20, 18, 16, 14, 12, 10):
        m = TodoModel(todos=_todo(10), selected_idx=0)
        scr = Rec(h, 60)
        for sel in range(10):
            m.selected_idx = sel
            scr.erase()
            t_view.render(
                scr,
                m,
                theme={},
                pairs={"marco": 1, "texto": 6, "helpers": 2},
                config={"mostrar_marco": True, "mostrar_helpers": True},
            )
            contenido = "".join(s for y, x, s in scr.rows if isinstance(s, str))
            assert f"Tarea {sel}" in contenido, (h, sel)
            assert "\u25ba" in contenido, (h, sel)
