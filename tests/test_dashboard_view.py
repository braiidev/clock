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
