"""Tests para features.clock.view."""

from clock_tui.features.clock import view as c_view
from clock_tui.features.clock.model import ClockModel, WorldClock


def _wc(n: int) -> list[WorldClock]:
    return [WorldClock(zona="UTC", apodo=f"W{i}") for i in range(n)]


def test_render_does_not_mutate_model():
    m = ClockModel(
        wc_list=_wc(2),
        wc_idx=1,
    )
    wc_before = [(w.zona, w.apodo) for w in m.wc_list]
    idx_before = m.wc_idx

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


def test_build_wc_rows_empty():
    m = ClockModel(wc_list=[])
    assert c_view._build_wc_rows(m, {}) == []


def test_build_wc_rows_marca_seleccionado_con_playo():
    m = ClockModel(wc_list=_wc(2), wc_idx=1)
    rows = c_view._build_wc_rows(m, {})
    assert len(rows) == 2
    assert rows[0].startswith(" ")
    assert rows[1].startswith("\u25ba")


def test_build_wc_rows_ventana_scroll_no_rota():
    m = ClockModel(wc_list=_wc(6), wc_idx=4)
    m._clamp_wc_scroll()  # → wc_scroll == 1
    rows = c_view._build_wc_rows(m, {})
    assert len(rows) == 5  # 4 filas visibles + contador
    assert "W1" in rows[0]
    assert "W4" in rows[3]
    assert rows[3].startswith("\u25ba")


def test_build_wc_rows_sin_contador_si_no_sobra():
    m = ClockModel(wc_list=_wc(3), wc_idx=1)
    rows = c_view._build_wc_rows(m, {})
    assert len(rows) == 3
    assert "(1" not in rows[-1]


def test_wc_mostrar_no_ver_oculta_seccion():
    m = ClockModel(wc_list=_wc(2), wc_idx=0)

    class FakeStdscr:
        def getmaxyx(self):
            return 24, 80

        def erase(self):
            pass

        def addstr(self, *a, **kw):
            pass

        def refresh(self):
            pass

    captured: list[list[str]] = []

    def fake_draw_frame(stdscr, title, rows, **kw):
        captured.append(list(rows))

    import clock_tui.features.clock.view as vmod

    orig = vmod.draw_frame
    vmod.draw_frame = fake_draw_frame  # type: ignore[assignment]
    try:
        c_view.render(
            FakeStdscr(),
            m,
            theme={},
            pairs={"marco": 1, "texto": 6, "helpers": 2},
            config={
                "mostrar_marco": True,
                "mostrar_helpers": True,
                "wc_mostrar": "no ver",
            },
        )
    finally:
        vmod.draw_frame = orig

    assert captured
    rows = captured[0]
    assert any("W0" in r for r in rows) is False
    assert any("W1" in r for r in rows) is False
