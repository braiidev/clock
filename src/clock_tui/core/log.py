"""Log de errores persistente en JSON (una entrada por línea)."""

from __future__ import annotations

import json
import os
import time
from typing import Any

LOG_FILE = os.path.join(os.path.expanduser("~/.config/clock"), "clock_error.log")


def _log_error(msg: str, trace: str | None = None) -> None:
    """Registra un error con timestamp y flag de no visto."""
    entry = {"ts": time.time(), "msg": str(msg)[:2000], "trace": trace, "visto": False}
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _log_read_all() -> list[dict[str, Any]]:
    """Lee todas las entradas del log en orden."""
    if not os.path.exists(LOG_FILE):
        return []
    entries: list[dict[str, Any]] = []
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except OSError:
        return []
    return entries


def _log_has_unseen() -> bool:
    """Indica si hay entradas sin marcar como vistas."""
    return any(not e.get("visto", False) for e in _log_read_all())


def _log_mark_all_seen() -> None:
    """Marca todas las entradas como vistas."""
    entries = _log_read_all()
    if not entries:
        return
    for e in entries:
        e["visto"] = True
    try:
        with open(LOG_FILE, "w", encoding="utf-8") as f:
            for e in entries:
                f.write(json.dumps(e, ensure_ascii=False) + "\n")
    except OSError:
        pass
