"""Tests para features.config.view (verificación de que no muta el modelo)."""

from clock_tui.features.config.model import ConfigModel, default_config


def test_render_does_not_mutate_model():
    m = ConfigModel(config=default_config(), tab_idx=0, selected_idx=1)
    config_before = dict(m.config)
    tab_before = m.tab_idx
    sel_before = m.selected_idx

    from clock_tui.features.config import view as c_view

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

    assert m.config == config_before
    assert m.tab_idx == tab_before
    assert m.selected_idx == sel_before
