"""Tests para features.dashboard.view (verificación de que no muta el snapshot)."""

import datetime

from clock_tui.features.dashboard.model import DashboardSnapshot


def test_render_does_not_mutate_snapshot():
    timers = [{"name": "T1", "remaining": 60}]
    snap = DashboardSnapshot(
        now=datetime.datetime(2025, 6, 16, 14, 5, 9),
        active_timers=timers,
        total_tasks=3,
        done_tasks=1,
        selected_idx=1,
    )
    idx_before = snap.selected_idx
    timers_before = list(snap.active_timers)

    from clock_tui.features.dashboard import view as d_view

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
        d_view.render(
            FakeStdscr(),
            snap,
            theme={},
            pairs={"marco": 1, "texto": 6, "helpers": 2},
            config={"mostrar_marco": True, "mostrar_helpers": True},
        )
    except Exception:
        pass

    assert snap.selected_idx == idx_before
    assert snap.active_timers == timers_before


def test_render_clima_usa_pair_clima():
    snap = DashboardSnapshot(
        now=datetime.datetime(2025, 6, 16, 14, 5, 9),
        weather_line="UV 23° Soleado",
        active_timers=[],
        total_tasks=0,
        done_tasks=0,
        selected_idx=0,
    )
    captured: dict = {}

    class FakeStdscr:
        def getmaxyx(self):
            return 24, 80

        def erase(self):
            pass

        def addstr(self, *a, **kw):
            pass

        def refresh(self):
            pass

    from clock_tui.features.dashboard import view as d_view

    def fake_draw_frame(stdscr, title, rows, row_attrs=None, **kw):
        captured["attrs"] = row_attrs
        captured["rows"] = list(rows)

    orig = d_view.draw_frame
    d_view.draw_frame = fake_draw_frame  # type: ignore[assignment]
    try:
        d_view.render(
            FakeStdscr(),
            snap,
            theme={},
            pairs={"marco": 1, "texto": 6, "helpers": 2, "clima": 31},
            config={"mostrar_marco": True, "mostrar_helpers": True},
        )
    finally:
        d_view.draw_frame = orig

    assert captured["rows"][1] == "UV 23° Soleado"
    assert captured["attrs"] == [None, 31]


def test_render_ventana_scroll_seleccion_ultima_visible():
    from clock_tui.features.dashboard import view as d_view

    timers = [{"name": f"T{i}", "remaining": i * 60, "idx": i} for i in range(5)]
    snap = DashboardSnapshot(
        now=datetime.datetime(2025, 6, 16, 14, 5, 9),
        active_timers=timers,
        total_tasks=0,
        done_tasks=0,
        selected_idx=3,
    )
    captured: dict = {}

    class FakeStdscr:
        def getmaxyx(self):
            return 8, 60

        def erase(self):
            pass

        def addstr(self, *a, **kw):
            pass

        def refresh(self):
            pass

    def fake_draw_frame(stdscr, title, rows, row_attrs=None, **kw):
        captured["rows"] = list(rows)

    orig = d_view.draw_frame
    d_view.draw_frame = fake_draw_frame  # type: ignore[assignment]
    try:
        offset = d_view.render(
            FakeStdscr(),
            snap,
            theme={},
            pairs={"marco": 1, "texto": 6, "helpers": 2},
            config={"mostrar_marco": True, "mostrar_helpers": True},
        )
    finally:
        d_view.draw_frame = orig

    assert offset > 0  # la selección está fuera de la ventana inicial
    assert any(r.startswith("\u25ba") for r in captured["rows"])
    assert any("de 4" in r for r in captured["rows"])
    assert all("T1" not in r for r in captured["rows"])  # las primeras salen
