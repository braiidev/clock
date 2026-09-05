"""Modelo de timers: estado, navegación, CRUD y countdown tick.

Persiste en data.json (los timers se guardan como dicts simplificados).
El tick muta `remaining` de timers activos.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from clock_tui.core.time_utils import hms_to_secs, secs_to_hms

_MAX_TIMERS = 10
_MAX_VISIBLE = 6


@dataclass
class Timer:
    name: str = "Timer"
    time: list[int] = field(default_factory=lambda: [0, 10, 0])
    active: bool = False
    started: bool = False
    remaining: float = 600.0
    last_tick: float | None = None

    def total_secs(self) -> int:
        return hms_to_secs(*self.time)

    def hms(self) -> tuple[int, int, int]:
        return secs_to_hms(self.remaining)


@dataclass
class TimersModel:
    timers: list[Timer] = field(default_factory=list)
    selected_idx: int = 0
    scroll_offset: int = 0
    edit_mode: bool = False
    edit_target: int = 0
    temp_name: str = ""
    time_field: int = 0
    confirm_delete: bool = False

    @classmethod
    def from_data(cls, data_timers: list[dict]) -> TimersModel:
        """Crea el modelo desde los dicts persistidos en data.json."""
        timers = []
        for d in data_timers:
            t = Timer(
                name=d["name"],
                time=list(d["time"]),
                remaining=float(hms_to_secs(*d["time"])),
            )
            timers.append(t)
        return cls(timers=timers)

    def to_data(self) -> list[dict]:
        """Serializa los timers para persistencia (sin estado runtime)."""
        return [{"name": t.name, "time": list(t.time)} for t in self.timers]

    def tick(self, now: float | None = None) -> list[int]:
        """Descuenta tiempo de timers activos. Devuelve índices de los que completaron."""
        ref = now if now is not None else time.monotonic()
        completed: list[int] = []
        for i, t in enumerate(self.timers):
            if not t.active:
                t.last_tick = None
                continue
            if t.last_tick is None:
                t.last_tick = ref
                continue
            elapsed = ref - t.last_tick
            t.last_tick = ref
            t.remaining = max(0.0, t.remaining - elapsed)
            if t.remaining <= 0:
                t.active = False
                t.last_tick = None
                completed.append(i)
        return completed

    def _clamp_scroll(self) -> None:
        if self.selected_idx < self.scroll_offset:
            self.scroll_offset = self.selected_idx
        elif self.selected_idx >= self.scroll_offset + _MAX_VISIBLE:
            self.scroll_offset = self.selected_idx - _MAX_VISIBLE + 1

    def swap(self, a: int, b: int) -> None:
        self.timers[a], self.timers[b] = self.timers[b], self.timers[a]
