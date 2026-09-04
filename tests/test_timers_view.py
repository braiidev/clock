"""Tests para features.timers.view (verificación de que no muta el modelo)."""

from clock_tui.features.timers.model import Timer, TimersModel


def test_render_does_not_mutate_model():
    m = TimersModel(
        timers=[Timer(name="T1", time=[0, 5, 0]), Timer(name="T2", time=[0, 10, 0])],
        selected_idx=1,
        scroll_offset=0,
    )
    timers_before = [(t.name, list(t.time), t.active) for t in m.timers]
    idx_before = m.selected_idx

    from clock_tui.features.timers import view as t_view

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

    after = [(t.name, list(t.time), t.active) for t in m.timers]
    assert after == timers_before
    assert m.selected_idx == idx_before
