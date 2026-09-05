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


def test_render_selector_usa_playo():
    m = ConfigModel(config=default_config(), tab_idx=0, selected_idx=0)
    captured: dict = {}

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

    def fake_draw_frame(stdscr, title, rows, **kw):
        captured["rows"] = list(rows)
        captured["counter"] = kw.get("bottom_counter")

    orig = c_view.draw_frame
    c_view.draw_frame = fake_draw_frame  # type: ignore[assignment]
    try:
        c_view.render(
            FakeStdscr(),
            m,
            theme={},
            pairs={"marco": 1, "texto": 6, "helpers": 2},
            config={"mostrar_marco": True, "mostrar_helpers": True},
        )
    finally:
        c_view.draw_frame = orig

    visibles = m.visible_items()
    fila = next(r for r in captured["rows"] if visibles[0].label in r)
    assert fila.startswith("\u25ba")
    assert captured["counter"] == f"(1/{len(visibles)})"


def test_scroll_seleccion_siempre_visible_altura_chica():
    """Regresión v0.49: en altura chica la selección no se corta ni se oculta."""
    m = ConfigModel(config=default_config(), tab_idx=0, selected_idx=0)
    n = len(m.visible_items())

    from clock_tui.features.config import view as c_view

    class Rec:
        def __init__(self, h, w):
            self.h, self.w = h, w
            self.rows = []

        def getmaxyx(self):
            return self.h, self.w

        def erase(self):
            self.rows = []

        def addstr(self, y, x, s, *a, **k):
            self.rows.append((y, x, s))

        def refresh(self):
            pass

    for h in (16, 12, 10, 8):
        scr = Rec(h, 60)
        for sel in range(n):
            m.selected_idx = sel
            scr.erase()
            c_view.render(
                scr,
                m,
                theme={},
                pairs={"marco": 1, "texto": 6, "helpers": 2},
                config={"mostrar_marco": True, "mostrar_helpers": True},
            )
            contenido = "".join(s for y, x, s in scr.rows if isinstance(s, str))
            label = m.visible_items()[sel].label
            assert label in contenido, (h, sel)
            assert "\u25ba" in contenido, (h, sel)
