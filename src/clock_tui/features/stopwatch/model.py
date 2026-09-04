"""Modelo del cronómetro: estado y cálculo de tiempo transcurrido.

Sin I/O, sin curses. Las laps son la diferencia entre marcas sucesivas.
El estado es efímero: no se persiste en data.json.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class StopwatchModel:
    active: bool = False
    start_time: float | None = None
    base_elapsed: float = 0.0
    records: list[float] = field(default_factory=list)
    last_record_at: float = 0.0
    scroll_offset: int = 0

    def elapsed(self, now: float | None = None) -> float:
        """Segundos totales transcurridos (incluyendo centésimas)."""
        if self.active and self.start_time is not None:
            ref = now if now is not None else time.monotonic()
            return self.base_elapsed + (ref - self.start_time)
        return self.base_elapsed

    def elapsed_hms(self, now: float | None = None) -> tuple[int, int, int]:
        """Horas, minutos, segundos del tiempo total."""
        from clock_tui.core.time_utils import secs_to_hms

        return secs_to_hms(self.elapsed(now))

    def elapsed_cs(self, now: float | None = None) -> int:
        """Centésimas de segundo del tiempo total (00-99)."""
        e = self.elapsed(now)
        return int(round((e - int(e)) * 100)) % 100
