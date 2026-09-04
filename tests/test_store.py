"""Tests para core.store: save/load roundtrip y migracion v6 a v7."""

import json
import os

import clock_tui.core.store as store


def _move_files(tmp_path, monkeypatch):
    store.DATA_FILE = str(tmp_path / "data.json")
    store.LEGACY_FILE = str(tmp_path / "clock_data.json")
    store.CONFIG_DIR = str(tmp_path)


def test_save_load_roundtrip(tmp_path, monkeypatch):
    _move_files(tmp_path, monkeypatch)
    alarms = [{"nombre": "Reunión", "hora": 15, "minutos": 0, "status": "activado"}]
    timers = [{"name": "T1", "time": [0, 10, 0]}]
    todos = [{"id": 1, "tipo": "tarea", "texto": "leche", "activo": True}]
    config = {"tema": "clasico"}
    wcache = {"text": "BUE +12C", "ok": True, "ts": 123}

    store.save(alarms, timers, todos, config, wcache)

    loaded = store.load()
    assert loaded is not None
    l_alarms, l_timers, l_todos, l_config, l_wcache = loaded
    assert l_alarms[0]["nombre"] == "Reunión"
    assert l_timers[0]["remaining"] == 600.0
    assert l_timers[0]["active"] is False
    assert l_todos[0]["texto"] == "leche"
    assert l_config["tema"] == "clasico"
    assert l_wcache["text"] == "BUE +12C"


def test_save_never_writes_pomodoro(tmp_path, monkeypatch):
    _move_files(tmp_path, monkeypatch)
    store.save([], [], [], {}, {})
    with open(store.DATA_FILE, "r", encoding="utf-8") as f:
        raw = f.read()
    assert "pomodoro" not in raw
    assert json.loads(raw)["version"] == 7


def test_load_migrates_legacy_v6(tmp_path, monkeypatch):
    _move_files(tmp_path, monkeypatch)
    legacy = {
        "version": 6,
        "alarms": [{"nombre": "Alarma6", "hora": 7, "minutos": 0}],
        "timers": [{"name": "T6", "time": [0, 5, 0]}],
        "pomodoro": {"work": {"time": [0, 20, 0], "count": 3}},
        "todos": [{"id": 1, "tipo": "tarea", "texto": "x"}],
        "config": {"tema": "mono"},
        "weather_cache": {"text": "x", "ok": True, "ts": 1},
    }
    with open(store.LEGACY_FILE, "w", encoding="utf-8") as f:
        json.dump(legacy, f)

    loaded = store.load()
    assert loaded is not None
    l_alarms, l_timers, l_todos, l_config, _ = loaded
    assert l_alarms[0]["nombre"] == "Alarma6"
    assert l_timers[0]["remaining"] == 300.0
    assert l_todos[0]["tipo"] == "tarea"
    assert l_config["tema"] == "mono"
    # el archivo nuevo ya no contiene pomodoro
    with open(store.DATA_FILE, "r", encoding="utf-8") as f:
        nuevo = json.load(f)
    assert "pomodoro" not in nuevo
    assert nuevo["version"] == 7


def test_load_empty_returns_none(tmp_path, monkeypatch):
    _move_files(tmp_path, monkeypatch)
    assert store.load() is None
