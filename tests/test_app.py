"""Tests para app.app: bootstrap, dispatch y alert overlay.

Instancia ClockApp con un curses falso (no corre el main loop) para
verificar contratos de integración: ticks de timers/alarmas/snoozes,
dismiss con reset de timer, posponer, y persistencia por needs_save.
"""

from __future__ import annotations

import datetime
import sys
import types
from typing import Any

import pytest


class _FakeCurses(types.ModuleType):
    def __init__(self) -> None:
        super().__init__("curses")
        for name, val in [
            ("COLOR_BLACK", 0),
            ("COLOR_RED", 1),
            ("COLOR_GREEN", 2),
            ("COLOR_YELLOW", 3),
            ("COLOR_BLUE", 4),
            ("COLOR_MAGENTA", 5),
            ("COLOR_CYAN", 6),
            ("COLOR_WHITE", 7),
        ]:
            setattr(self, name, val)
        for name, val in [
            ("KEY_LEFT", 260),
            ("KEY_RIGHT", 261),
            ("KEY_UP", 259),
            ("KEY_DOWN", 258),
            ("KEY_BACKSPACE", 263),
            ("KEY_RESIZE", 410),
        ]:
            setattr(self, name, val)
        for name, val in [
            ("A_BOLD", 1 << 8),
            ("A_DIM", 1 << 9),
            ("A_REVERSE", 1 << 10),
            ("A_NORMAL", 0),
        ]:
            setattr(self, name, val)
        self._pairs: dict[int, tuple[int, int]] = {}

        class _Err(Exception):
            pass

        self.error = _Err

    def init_pair(self, n: int, f: int, b: int) -> None:
        self._pairs[n] = (f, b)

    def color_pair(self, n: int) -> int:
        return n << 16 if n in self._pairs else 0

    def curs_set(self, n: int) -> None:
        pass

    def beep(self) -> None:
        pass


class _FakeStdscr:
    def __init__(self, h: int = 24, w: int = 80) -> None:
        self.h = h
        self.w = w

    def getmaxyx(self) -> tuple[int, int]:
        return (self.h, self.w)

    def getch(self) -> int:
        return -1

    def nodelay(self, v: bool) -> None:
        pass

    def keypad(self, v: bool) -> None:
        pass

    def addstr(self, *a: Any, **k: Any) -> None:
        pass

    def erase(self) -> None:
        pass

    def refresh(self) -> None:
        pass


@pytest.fixture
def fake_curses(monkeypatch):
    fc = _FakeCurses()
    monkeypatch.setitem(sys.modules, "curses", fc)
    import clock_tui.app.app as app_mod

    monkeypatch.setattr(app_mod, "curses", fc)
    yield fc


@pytest.fixture
def app(fake_curses):
    from clock_tui.app.app import ClockApp

    a = ClockApp(_FakeStdscr())
    a.config["sonido"] = False  # evita threads de audio en tests
    yield a
    a.weather.stop()


def test_bootstrap_models(app):
    assert app.config is not None
    assert app.alarms is not None
    assert app.timers is not None
    assert app.todo is not None
    assert app.clock is not None
    assert app.stopwatch is not None
    assert set(app._pairs) == {"marco", "texto", "clima", "helpers", "nav"}


def test_dispatch_all_views_returns_actions(app):
    from clock_tui.app.router import (
        VIEW_ALARMS,
        VIEW_CLOCK,
        VIEW_CONFIG,
        VIEW_DASHBOARD,
        VIEW_STOPWATCH,
        VIEW_TIMERS,
        VIEW_TODO,
    )

    for view in (
        VIEW_DASHBOARD,
        VIEW_CLOCK,
        VIEW_ALARMS,
        VIEW_TIMERS,
        VIEW_STOPWATCH,
        VIEW_TODO,
        VIEW_CONFIG,
    ):
        result = app._dispatch(view, ord(" "))
        assert result is not None


def test_handle_feature_result_needs_save(app, monkeypatch):
    saved = []

    def fake_save(*a: Any, **k: Any) -> None:
        saved.append(True)

    monkeypatch.setattr(app, "_save_now", fake_save)

    class Res:
        needs_save = True

    app._handle_feature_result(Res())
    assert saved == [True]


def test_show_alert_sets_state(app):
    app._show_alert("Titulo", "Mensaje", posponable=True)
    assert app._alert is not None
    assert app._alert["title"] == "Titulo"
    assert app._alert["msg"] == "Mensaje"
    assert app._alert["posponable"] is True
    assert app._alert["blink_state"] == 0


def test_alert_key_dismiss(app):
    app._show_alert("Titulo", "Mensaje")
    app._handle_alert_key(ord(" "))
    assert app._alert is None


def test_alert_key_escape(app):
    app._show_alert("Titulo", "Mensaje")
    app._handle_alert_key(27)
    assert app._alert is None


def test_alert_key_actions_not_global_when_alert(app, monkeypatch):
    from clock_tui.app.router import VIEW_DASHBOARD

    app._show_alert("Titulo", "Mensaje")
    routed: list[int] = []

    def fake_route(key: int, dispatch: Any):
        routed.append(key)
        from clock_tui.app.router import RouterResult

        return RouterResult()

    monkeypatch.setattr(app.router, "route", fake_route)
    quit_flag = app._handle_key(ord("1"))
    assert routed == []  # no se rutea mientras hay alerta
    assert quit_flag is False


def test_alert_quits_only_for_real_quit(app, monkeypatch):
    app._show_alert("Titulo", "Mensaje")
    # q mientras hay alerta: se ignora (no sale)
    quit_flag = app._handle_key(ord("q"))
    assert quit_flag is False


def test_timer_completion_shows_alert_and_resets(app):
    now = __import__("time").monotonic()
    from clock_tui.features.timers.model import Timer

    t = Timer(
        name="Cafe", time=[0, 0, 5], active=True, remaining=0.0, last_tick=now - 10
    )
    app.timers.timers = [t]
    app._tick()
    assert app._alert is not None
    assert "Cafe" in app._alert["title"]
    # dismiss resetea el timer al tiempo configurado
    app._handle_alert_key(ord(" "))
    assert t.remaining == 5.0
    assert t.active is False


def test_alarm_fire_pospone(app, monkeypatch):
    import clock_tui.app.app as app_mod
    from clock_tui.features.alarms.model import Alarm

    _real_dt = datetime.datetime  # clase real capturada antes del patch

    class _FixedDT:
        @staticmethod
        def now() -> datetime.datetime:
            return _real_dt(2026, 9, 4, 13, 59, 0)

    monkeypatch.setattr(app_mod.datetime, "datetime", _FixedDT)

    app.alarms.alarms = [
        Alarm(nombre="Despertar", hora=13, minutos=59, status="activado")
    ]
    app.alarms._last_minute = (13, 58)
    app.alarms._fired_this_minute = set()

    app._tick()
    assert app._alert is not None
    assert app._alert["posponable"] is True
    app._handle_alert_key(ord("p"))
    assert app._alert is None
    assert len(app.alarms.snoozes) == 1
    assert app.alarms.snoozes[0].nombre == "Despertar"


# ── Fase 5.5: dashboard jump / config commands / overlays ──


def test_dashboard_jump_sets_selected_and_view(app):
    from clock_tui.app.router import VIEW_TIMERS
    from clock_tui.features.timers.model import Timer

    app.timers.timers = [
        Timer(name="T1", time=[0, 0, 1]),
        Timer(name="T2", time=[0, 0, 2]),
    ]

    class Res:
        jump_to = VIEW_TIMERS
        jump_item = 1

    app._handle_feature_result(Res())
    assert app.router.current_view == VIEW_TIMERS
    assert app.timers.selected_idx == 1


def test_dashboard_refresh_weather(app, monkeypatch):
    refreshed: list[int] = []
    monkeypatch.setattr(app.weather, "request_refresh", lambda: refreshed.append(1))

    class Res:
        refresh_weather = True

    app._handle_feature_result(Res())
    assert refreshed == [1]


def test_theme_changed_reinstalls_pairs(app):
    app._pairs = {}

    class Res:
        theme_changed = True

    app._handle_feature_result(Res())
    assert app._pairs


def test_command_weather_toggle_start_stop(app, monkeypatch):
    started: list[int] = []
    stopped: list[int] = []
    monkeypatch.setattr(app.weather, "start", lambda: started.append(1))
    monkeypatch.setattr(app.weather, "stop", lambda: stopped.append(1))

    app.config["clima_activo"] = True
    app._handle_command("weather_toggle")
    assert started == [1]

    app.config["clima_activo"] = False
    app._handle_command("weather_toggle")
    assert stopped == [1]


def test_command_backup_creates_file(app, tmp_path, monkeypatch):
    import clock_tui.app.app as app_mod

    data = tmp_path / "data.json"
    data.write_text('{"version": 7}', encoding="utf-8")
    monkeypatch.setattr(app_mod.store_mod, "DATA_FILE", str(data))
    monkeypatch.setattr(
        app_mod.backup_data.__globals__["os"].path,
        "expanduser",
        lambda p: str(tmp_path),
    )

    alerts: list[tuple[str, str]] = []
    monkeypatch.setattr(
        app, "_show_alert", lambda title, msg: alerts.append((title, msg))
    )

    app._handle_command("backup")
    backups = list(tmp_path.glob("clock_backup_*.json"))
    assert len(backups) == 1
    assert alerts and "Backup creado" in alerts[0][0]


def test_command_sound_cycle(app, tmp_path, monkeypatch):
    import clock_tui.app.app as app_mod

    monkeypatch.setattr(app, "_audios_dir", lambda: str(tmp_path))
    (tmp_path / "a.wav").write_text("x")
    (tmp_path / "b.wav").write_text("x")
    monkeypatch.setattr(app_mod, "try_beep", lambda p: None)
    app.config["sonido_archivo"] = None

    app._cycle_sound_file()
    assert app.config["sonido_archivo"] == "a.wav"
    app._cycle_sound_file()
    assert app.config["sonido_archivo"] == "b.wav"


def test_browser_esc_closes_at_root(app):
    app._browser = {"mode": "restore", "cwd": "/", "idx": 0, "entries": []}
    app._handle_browser_key(27)
    assert app._browser is None


def test_browser_enter_into_dir(app, tmp_path):
    (tmp_path / "sub").mkdir()
    app._browser = {
        "mode": "restore",
        "cwd": str(tmp_path),
        "idx": 0,
        "entries": [("sub", True)],
    }
    app._handle_browser_key(ord("\n"))
    assert app._browser["cwd"] == str(tmp_path / "sub")


def test_browser_up_navigate(app):
    app._browser = {"mode": "restore", "cwd": "/work/x/sub", "idx": 0, "entries": []}
    app._handle_browser_key(27)
    assert app._browser["cwd"] == "/work/x"


def test_sound_browser_select_sets_config_and_saves(app, tmp_path, monkeypatch):
    saved: list[int] = []
    monkeypatch.setattr(app, "_save_now", lambda: saved.append(1))
    wav = tmp_path / "custom.wav"
    wav.write_text("x")
    app._browser = {
        "mode": "sound",
        "cwd": str(tmp_path),
        "idx": 0,
        "entries": [("custom.wav", False)],
    }
    app._handle_browser_key(ord("\n"))
    assert app.config["sonido_custom_path"] == str(wav)
    assert app.config["sonido_modo"] == "custom"
    assert app._browser is None
    assert saved == [1]


def test_log_viewer_open_close_and_mark(app, monkeypatch):
    import clock_tui.app.app as app_mod

    entries = [{"ts": 100.0, "msg": "boom", "visto": False}]
    marked: list[int] = []
    monkeypatch.setattr(app_mod, "_log_read_all", lambda: list(entries))
    monkeypatch.setattr(app_mod, "_log_mark_all_seen", lambda: marked.append(1))

    app._open_log_viewer()
    assert app._log_viewer is not None
    assert app._log_viewer["entries"][0]["msg"] == "boom"
    assert marked == [1]

    app._handle_log_viewer_key(27)
    assert app._log_viewer is None


def test_log_export_writes_file(app, tmp_path, monkeypatch):
    import clock_tui.app.app as app_mod

    log = tmp_path / "clock_error.log"
    log.write_text("error line", encoding="utf-8")
    monkeypatch.setattr(app_mod, "LOG_FILE", str(log))
    monkeypatch.setattr(
        app_mod.os.path,
        "expanduser",
        lambda p: str(tmp_path / "out.txt") if p.startswith("~/") else p,
    )

    alerts: list[tuple[str, str]] = []
    monkeypatch.setattr(
        app, "_show_alert", lambda title, msg: alerts.append((title, msg))
    )

    app._export_log()
    assert (tmp_path / "out.txt").read_text(encoding="utf-8") == "error line"
    assert alerts and "Log exportado" in alerts[0][0]


def test_log_export_missing_shows_alert(app, monkeypatch):
    import clock_tui.app.app as app_mod

    monkeypatch.setattr(app_mod, "LOG_FILE", "/no/existe.log")
    alerts: list[tuple[str, str]] = []
    monkeypatch.setattr(
        app, "_show_alert", lambda title, msg: alerts.append((title, msg))
    )

    app._export_log()
    assert alerts and "Sin log" in alerts[0][0]


def test_render_with_browser_log_and_help(app):
    app._browser = {
        "mode": "sound",
        "cwd": "/tmp",
        "idx": 0,
        "entries": [("a.wav", False)],
    }
    app._log_viewer = {
        "entries": [{"ts": 1.0, "msg": "boo", "visto": True}],
        "idx": 0,
        "scroll": 0,
    }
    app.router.help_open = True
    app._render()
    assert app._log_viewer["scroll"] == 0
