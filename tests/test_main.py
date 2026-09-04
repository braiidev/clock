"""Tests para clock_tui.main: entry point bajo curses.wrapper."""

from __future__ import annotations

import sys
import types

import pytest


class _FakeCurses(types.ModuleType):
    def __init__(self) -> None:
        super().__init__("curses")
        import curses as _real

        for name in dir(_real):
            if name.isupper():
                setattr(self, name, getattr(_real, name))
        self.wrapper = lambda cb: cb(None)


@pytest.fixture
def fake_curses_main(monkeypatch):
    fc = _FakeCurses()
    monkeypatch.setitem(sys.modules, "curses", fc)
    import clock_tui.main as main_mod

    monkeypatch.setattr(main_mod, "curses", fc)
    yield fc, main_mod


def test_main_help(fake_curses_main, monkeypatch, capsys):
    _, main_mod = fake_curses_main
    monkeypatch.setattr(sys, "argv", ["clock", "--help"])
    main_mod.main()
    out = capsys.readouterr().out
    assert "--update" in out and "--uninstall" in out


def test_main_version(fake_curses_main, monkeypatch, capsys):
    _, main_mod = fake_curses_main
    monkeypatch.setattr(sys, "argv", ["clock", "--version"])
    main_mod.main()
    out = capsys.readouterr().out
    assert "clock " in out


def test_main_does_not_start_tui_with_flag(fake_curses_main, monkeypatch):
    _, main_mod = fake_curses_main
    ran: list[int] = []

    class FakeApp:
        def __init__(self, stdscr) -> None:
            self.stdscr = stdscr

        def run(self) -> None:
            ran.append(1)

    monkeypatch.setattr(main_mod, "ClockApp", FakeApp)
    monkeypatch.setattr(sys, "argv", ["clock", "--check-update"])
    monkeypatch.setattr(
        main_mod,
        "check_update",
        lambda repo: type(
            "Info",
            (),
            {"ok": True, "behind": 0, "current": "v", "error": None, "available": ""},
        )(),
    )
    with pytest.raises(SystemExit):
        main_mod.main()
    assert ran == []


def test_cli_update_up_to_date(fake_curses_main, monkeypatch, capsys):
    _, main_mod = fake_curses_main
    monkeypatch.setattr(sys, "argv", ["clock", "--update"])
    monkeypatch.setattr(
        main_mod,
        "do_update",
        lambda repo: type("Res", (), {"ok": True, "message": "Estás al día"})(),
    )
    with pytest.raises(SystemExit) as exc:
        main_mod.main()
    assert exc.value.code == 0
    assert "Estás al día" in capsys.readouterr().out


def test_cli_uninstall_refuses_outside_install_dir(
    fake_curses_main, monkeypatch, capsys
):
    _, main_mod = fake_curses_main
    monkeypatch.setattr(sys, "argv", ["clock", "--uninstall"])
    monkeypatch.setattr(main_mod, "repo_root", lambda: "/tmp/otra-instalacion")
    with pytest.raises(SystemExit) as exc:
        main_mod.main()
    assert exc.value.code == 1
    assert "install.sh" in capsys.readouterr().err


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
