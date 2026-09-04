"""Modelo de alarmas: estado, CRUD, check por minuto y snooze.

Persiste alarmas en data.json. Snoozes son efímeros (en memoria).
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field

from clock_tui.core.recurrence import _repeat_days_normalize, _repeat_days_str

_MAX_VISIBLE = 6


@dataclass
class Alarm:
    nombre: str = "Alarma"
    hora: int = 0
    minutos: int = 0
    status: str = "activado"  # "activado" | "desactivado" | "disparada"
    repeat_days: list[int] = field(default_factory=list)

    def is_enabled(self) -> bool:
        return self.status == "activado"

    def toggle(self) -> None:
        if self.status == "activado":
            self.status = "desactivado"
        else:
            self.status = "activado"

    def repeat_str(self) -> str:
        return _repeat_days_str(self.repeat_days)


@dataclass
class SnoozeEntry:
    hora: int
    minutos: int
    nombre: str
    _fired: bool = False


@dataclass
class AlarmsModel:
    alarms: list[Alarm] = field(default_factory=list)
    snoozes: list[SnoozeEntry] = field(default_factory=list)
    selected_idx: int = 0
    scroll_offset: int = 0
    _last_minute: tuple[int, int] | None = None
    _fired_this_minute: set[int] = field(default_factory=set)

    @classmethod
    def from_data(cls, data_alarms: list[dict]) -> AlarmsModel:
        alarms = []
        for d in data_alarms:
            a = Alarm(
                nombre=d.get("nombre", "Alarma"),
                hora=d.get("hora", 0),
                minutos=d.get("minutos", 0),
                status=d.get("status", "activado"),
                repeat_days=list(d.get("repeat_days", [])),
            )
            alarms.append(a)
        return cls(alarms=alarms)

    def to_data(self) -> list[dict]:
        return [
            {
                "tipo": "alarma",
                "hora": a.hora,
                "minutos": a.minutos,
                "segundos": 0,
                "status": a.status,
                "nombre": a.nombre,
                "repeat_days": list(a.repeat_days),
            }
            for a in self.alarms
        ]

    def check(
        self, now: datetime.datetime | None = None
    ) -> list[tuple[Alarm, str]]:
        """Compara hora actual con alarmas. Devuelve [(alarm, titulo)] de las que dispararon.

        Maneja el ciclo activado→disparada→re-activado/desactivado.
        """
        now = now or datetime.datetime.now()
        weekday = now.weekday()
        current_minute = (now.hour, now.minute)

        if self._last_minute != current_minute:
            self._last_minute = current_minute
            self._fired_this_minute = set()

        fired: list[tuple[Alarm, str]] = []

        for i, a in enumerate(self.alarms):
            dias = _repeat_days_normalize(a.repeat_days)
            day_ok = not dias or weekday in dias
            is_match = a.hora == now.hour and a.minutos == now.minute and day_ok

            if a.status == "activado" and is_match:
                if i not in self._fired_this_minute:
                    self._fired_this_minute.add(i)
                    fired.append(
                        (a, f"{a.hora:02d}:{a.minutos:02d} \u2014 \u00a1Alarma!")
                    )
                    a.status = "disparada"
            elif a.status == "disparada" and not is_match:
                if dias:
                    a.status = "activado"
                else:
                    a.status = "desactivado"

        return fired

    def check_snoozes(
        self, now: datetime.datetime | None = None
    ) -> list[tuple[SnoozeEntry, str]]:
        """Dispara snoozes cuyo hora/minuto matchea. Los elimina de la lista."""
        now = now or datetime.datetime.now()
        fired: list[tuple[SnoozeEntry, str]] = []
        to_remove: list[int] = []

        for i, s in enumerate(self.snoozes):
            if s.hora == now.hour and s.minutos == now.minute:
                if not s._fired:
                    s._fired = True
                    fired.append(
                        (s, f"{s.hora:02d}:{s.minutos:02d} \u2014 \u00a1Alarma pospuesta!")
                    )
                    to_remove.append(i)

        for i in reversed(to_remove):
            self.snoozes.pop(i)

        return fired

    def create_snooze(
        self, nombre: str, postpone_min: int, now: datetime.datetime | None = None
    ) -> None:
        """Crea un snooze con la hora objetivo."""
        now = now or datetime.datetime.now()
        target = now + datetime.timedelta(minutes=postpone_min)
        self.snoozes.append(
            SnoozeEntry(hora=target.hour, minutos=target.minute, nombre=nombre)
        )

    def _clamp_scroll(self) -> None:
        if self.selected_idx < self.scroll_offset:
            self.scroll_offset = self.selected_idx
        elif self.selected_idx >= self.scroll_offset + _MAX_VISIBLE:
            self.scroll_offset = self.selected_idx - _MAX_VISIBLE + 1
