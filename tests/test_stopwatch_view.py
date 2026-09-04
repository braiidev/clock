"""Tests para features.stopwatch.view (verificación de que no muta el modelo)."""

from clock_tui.features.stopwatch.model import StopwatchModel


def test_render_does_not_mutate_model():
    m = StopwatchModel(
        active=True,
        start_time=100.0,
        base_elapsed=5.0,
        records=[3.0, 2.0],
        last_record_at=10.0,
        scroll_offset=0,
    )
    records_before = list(m.records)
    active_before = m.active

    from clock_tui.features.stopwatch import view as sw_view

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
        sw_view.render(
            FakeStdscr(),
            m,
            theme={},
            pairs={"marco": 1, "texto": 6, "helpers": 2},
            config={"mostrar_marco": True, "mostrar_helpers": True},
        )
    except Exception:
        pass

    assert m.records == records_before
    assert m.active == active_before
