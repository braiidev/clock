"""Tests para features.alarms.view (verificación de que no muta el modelo)."""

from clock_tui.features.alarms.model import Alarm, AlarmsModel


def test_render_does_not_mutate_model():
    m = AlarmsModel(
        alarms=[
            Alarm(nombre="A1", hora=8, minutos=0, status="activado"),
            Alarm(nombre="A2", hora=12, minutos=30, status="desactivado"),
        ],
        selected_idx=1,
    )
    alarms_before = [(a.nombre, a.hora, a.status) for a in m.alarms]
    idx_before = m.selected_idx

    from clock_tui.features.alarms import view as a_view

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
        a_view.render(
            FakeStdscr(),
            m,
            theme={},
            pairs={"marco": 1, "texto": 6, "helpers": 2},
            config={"mostrar_marco": True, "mostrar_helpers": True},
        )
    except Exception:
        pass

    after = [(a.nombre, a.hora, a.status) for a in m.alarms]
    assert after == alarms_before
    assert m.selected_idx == idx_before
