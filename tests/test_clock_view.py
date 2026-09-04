"""Tests para features.clock.view (verificación de que no muta el modelo)."""

from clock_tui.features.clock.model import ClockModel, WorldClock


def test_render_does_not_mutate_model():
    m = ClockModel(
        wc_list=[
            WorldClock(zona="UTC", apodo="U"),
            WorldClock(zona="Asia/Tokyo", apodo="TYO"),
        ],
        wc_idx=1,
    )
    wc_before = [(w.zona, w.apodo) for w in m.wc_list]
    idx_before = m.wc_idx

    from clock_tui.features.clock import view as c_view

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
        c_view.render(
            FakeStdscr(),
            m,
            theme={},
            pairs={"marco": 1, "texto": 6, "helpers": 2},
            config={"mostrar_marco": True, "mostrar_helpers": True},
        )
    except Exception:
        pass

    after = [(w.zona, w.apodo) for w in m.wc_list]
    assert after == wc_before
    assert m.wc_idx == idx_before
