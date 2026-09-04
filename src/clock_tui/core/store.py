"""Persistencia JSON en ~/.config/clock/data.json (v7).

Incluye migración automática desde el formato anterior clock_data.json (v6).
La v7 elimina `pomodoro` (decisión D3 del proyecto).

Escritura thread-safe con lock y cambio atómico (temp + os.replace).
"""

from __future__ import annotations

import json
import os
import threading
import time
from typing import Any

from .time_utils import hms_to_secs

CONFIG_DIR = os.path.expanduser("~/.config/clock")
DATA_FILE = os.path.join(CONFIG_DIR, "data.json")
LEGACY_FILE = os.path.join(CONFIG_DIR, "clock_data.json")

_VERSION = 7

_save_lock = threading.Lock()
_last_persistence_error: str | None = None


def _ensure_dir() -> None:
    os.makedirs(CONFIG_DIR, exist_ok=True)


def pop_persistence_error() -> str | None:
    """Devuelve y limpia el último error de persistencia ocurrido."""
    global _last_persistence_error
    err = _last_persistence_error
    _last_persistence_error = None
    return err


def _atomic_write(path: str, data: dict[str, Any]) -> None:
    """Escribe data como JSON de forma atómica (temp + rename)."""
    _ensure_dir()
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def save(
    alarms: list[dict[str, Any]],
    timers: list[dict[str, Any]],
    todos: list[dict[str, Any]],
    config: dict[str, Any],
    weather_cache: dict[str, Any] | None = None,
) -> None:
    """Guarda el estado completo en formato v7 (sin pomodoro)."""
    global _last_persistence_error
    with _save_lock:
        timers_clean = [{"name": t["name"], "time": t["time"]} for t in timers]
        if weather_cache is None:
            weather_cache = _current_weather_cache()
        data = {
            "version": _VERSION,
            "alarms": alarms,
            "timers": timers_clean,
            "todos": todos,
            "config": config or {},
            "weather_cache": weather_cache,
        }
        try:
            _atomic_write(DATA_FILE, data)
        except OSError as e:
            _last_persistence_error = f"No se pudo guardar: {e.strerror or e}"
        except Exception as e:
            _last_persistence_error = f"No se pudo guardar: {e}"


def _current_weather_cache() -> dict[str, Any]:
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f).get("weather_cache", {})
    except Exception:
        return {}


def load() -> tuple[list, list, list, dict, dict] | None:
    """Carga el estado; si falta data.json, migra desde clock_data.json v6.

    Devuelve (alarms, timers, todos, config, weather_cache) o None si no hay datos.
    """
    global _last_persistence_error
    _ensure_dir()
    if not os.path.exists(DATA_FILE) and os.path.exists(LEGACY_FILE):
        _migrate_legacy()
    if not os.path.exists(DATA_FILE):
        return None
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        _last_persistence_error = f"Datos guardados corruptos ({e}); se ignoraron."
        return None
    except OSError as e:
        _last_persistence_error = f"No se pudo leer datos guardados: {e.strerror or e}"
        return None

    if data.get("version") != _VERSION:
        _last_persistence_error = (
            "Archivo de datos con versión no soportada; se ignoró."
        )
        return None

    timers = []
    for t in data.get("timers", []):
        secs = hms_to_secs(*t["time"])
        timers.append(
            {
                "name": t["name"],
                "time": t["time"],
                "active": False,
                "started": False,
                "remaining": float(secs),
                "last_tick": None,
            }
        )

    todos = data.get("todos", [])
    now_ts = time.time()
    now_dt = __import__("datetime").datetime.now()
    for i, t in enumerate(todos):
        if "tipo" not in t:
            t["tipo"] = "tarea"
        if "created_at" not in t:
            t["created_at"] = now_ts
        t.pop("due_date", None)
        t.setdefault("alarma_dia", now_dt.day)
        t.setdefault("alarma_mes", now_dt.month)
        t.setdefault("alarma_anio", now_dt.year)
        t.setdefault("repeat_days", [])
        t.setdefault("last_done_date", None)
        t.setdefault("id", i)

    alarms = data.get("alarms", [])
    for a in alarms:
        a.setdefault("repeat_days", [])

    config = data.get("config", {})
    weather_cache = data.get("weather_cache", {})
    return (alarms, timers, todos, config, weather_cache)


def _migrate_legacy() -> None:
    """Migra clock_data.json (v1-v6) a data.json (v7), descartando pomodoro."""
    global _last_persistence_error
    try:
        with open(LEGACY_FILE, "r", encoding="utf-8") as f:
            old = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        _last_persistence_error = (
            f"No se pudo migrar los datos previos: {getattr(e, 'strerror', None) or e}"
        )
        return

    version = old.get("version")
    if version not in (1, 2, 3, 4, 5, 6):
        _last_persistence_error = (
            "Archivo previo con versión no soportada; no se migró."
        )
        return

    now_ts = time.time()
    now_dt = __import__("datetime").datetime.now()
    todos = old.get("todos", [])
    for i, t in enumerate(todos):
        if "tipo" not in t:
            t["tipo"] = "tarea"
        if "created_at" not in t:
            t["created_at"] = now_ts
        t.pop("due_date", None)
        t.setdefault("alarma_dia", now_dt.day)
        t.setdefault("alarma_mes", now_dt.month)
        t.setdefault("alarma_anio", now_dt.year)
        t.setdefault("repeat_days", [])
        t.setdefault("last_done_date", None)
        t.setdefault("id", i)

    alarms = old.get("alarms", [])
    for a in alarms:
        a.setdefault("repeat_days", [])

    data = {
        "version": _VERSION,
        "alarms": alarms,
        "timers": old.get("timers", []),
        "todos": todos,
        "config": old.get("config", {}),
        "weather_cache": old.get("weather_cache", {}),
    }
    try:
        _atomic_write(DATA_FILE, data)
    except OSError as e:
        _last_persistence_error = f"No se pudo migrar los datos: {e.strerror or e}"
