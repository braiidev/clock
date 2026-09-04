"""Tests para clock_tui.main: entry point bajo curses.wrapper."""

from __future__ import annotations

import sys
import types

import pytest


class _FakeCurses(types.ModuleType):
    def __init__(self) -> None:
        super().__init__("curses")

    def wrapper(self, cb):
        return cb(None)


@pytest.fixture
def fake_curses_main(monkeypatch):
    fc = _FakeCurses()
    monkeypatch.setitem(sys.modules, "curses", fc)
    import clock_tui.main as main_mod

    monkeypatch.setattr(main_mod, "curses", fc)
    yield fc, main_mod


def test_main_runs_app(fake_curses_main, monkeypatch):
    _, main_mod = fake_curses_main
    ran: list[int] = []

    class FakeApp:
        def __init__(self, stdscr) -> None:
            self.stdscr = stdscr

        def run(self) -> None:
            ran.append(1)

    monkeypatch.setattr(main_mod, "ClockApp", FakeApp)
    main_mod.main()
    assert ran == [1]


def test_main_crash_logs_and_exits_1(fake_curses_main, monkeypatch):
    _, main_mod = fake_curses_main
    logged: list[tuple[str, str]] = []

    class Boom:
        def __init__(self, stdscr) -> None:
            pass

        def run(self) -> None:
            raise RuntimeError("boom")

    monkeypatch.setattr(main_mod, "ClockApp", Boom)
    monkeypatch.setattr(
        main_mod, "_log_error", lambda msg, trace: logged.append((msg, trace))
    )

    with pytest.raises(SystemExit) as exc:
        main_mod.main()
    assert exc.value.code == 1
    assert logged and "boom" in logged[0][0]
