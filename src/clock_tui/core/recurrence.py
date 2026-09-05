"""Utilidades puras de recurrencia semanal y estado de tareas.

Definen la abreviatura de días y el manejo de días de repetición (L-V, todos,
S-D) junto con la lógica de "hecho" para tareas recurrentes o de una vez.
"""

from __future__ import annotations

import datetime
from typing import Any

DIAS_ABBR = ["L", "M", "X", "J", "V", "S", "D"]


def _repeat_days_normalize(repeat_days: Any) -> list[int]:
    """Normaliza una lista de días a valores únicos ordenados 0-6 (L=0)."""
    if not repeat_days:
        return []
    try:
        return sorted({int(d) % 7 for d in repeat_days})
    except (TypeError, ValueError):
        return []


def _repeat_days_str(repeat_days: Any) -> str:
    """Genera una etiqueta legible para una lista de días de repetición."""
    dias = _repeat_days_normalize(repeat_days)
    if not dias:
        return "una vez"
    if dias == [0, 1, 2, 3, 4]:
        return "L-V"
    if dias == [0, 1, 2, 3, 4, 5, 6]:
        return "todos"
    if dias == [5, 6]:
        return "S-D"
    return "".join(DIAS_ABBR[d] for d in dias)


def _next_occurrence(
    hora: int, minutos: int, repeat_days: Any, now: datetime.datetime
) -> datetime.datetime:
    """Próxima vez que sonará una alarma según sus días de repetición.

    Misma lógica que AlarmsModel.check: si hoy no es día de repetición (o la
    hora ya pasó), busca el siguiente día en `repeat_days`. Lista vacía == una
    vez → hoy si la hora no pasó, si no mañana.
    """
    dias = _repeat_days_normalize(repeat_days)
    cand = now.replace(hour=hora, minute=minutos, second=0, microsecond=0)
    if cand > now and (not dias or now.weekday() in dias):
        return cand
    if not dias:
        return cand + datetime.timedelta(days=1)
    for d in range(1, 8):
        if (now + datetime.timedelta(days=d)).weekday() in dias:
            return cand + datetime.timedelta(days=d)
    return cand + datetime.timedelta(days=1)


def _todo_is_done(t: dict[str, Any], hoy: str | None = None) -> bool:
    """Indica si una tarea está hecha. Las recurrentes dependen de la fecha."""
    dias = _repeat_days_normalize(t.get("repeat_days"))
    if not dias:
        return not t.get("activo", True)
    if hoy is None:
        hoy = datetime.date.today().isoformat()
    return t.get("last_done_date") == hoy


def _todo_set_done(t: dict[str, Any], done: bool, hoy: str | None = None) -> None:
    """Marca una tarea como hecha o no. Las recurrentes fijan la fecha."""
    dias = _repeat_days_normalize(t.get("repeat_days"))
    if not dias:
        t["activo"] = not done
        return
    if hoy is None:
        hoy = datetime.date.today().isoformat()
    t["last_done_date"] = hoy if done else None
