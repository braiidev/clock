"""Modelo del ToDo: state, CRUD, dynamic edit fields, commit logic.

Sin I/O, sin curses. El main loop pasa la lista por referencia.
"""

from __future__ import annotations

import time
import datetime
import calendar
from dataclasses import dataclass, field
from typing import Any

from clock_tui.core.recurrence import _repeat_days_normalize, _repeat_days_str

_MAX_VISIBLE = 8


def todo_is_done(t: dict, hoy: str | None = None) -> bool:
    dias = _repeat_days_normalize(t.get("repeat_days"))
    if not dias:
        return not t.get("activo", True)
    if hoy is None:
        hoy = datetime.date.today().isoformat()
    return t.get("last_done_date") == hoy


def todo_set_done(t: dict, done: bool, hoy: str | None = None) -> None:
    dias = _repeat_days_normalize(t.get("repeat_days"))
    if not dias:
        t["activo"] = not done
        return
    if hoy is None:
        hoy = datetime.date.today().isoformat()
    t["last_done_date"] = hoy if done else None


@dataclass
class TodoModel:
    todos: list[dict]
    next_id: int = 1
    selected_idx: int = 0
    scroll_offset: int = 0
    edit_mode: bool = False
    edit_target: int | None = None
    edit_field: int = 0
    confirm_delete: bool = False

    # temp edit fields
    temp_tipo: str = "tarea"
    temp_texto: str = ""
    temp_recordarme: bool = False
    temp_alarma: list[int] = field(default_factory=lambda: [0, 0, 1, 1, 2025])
    temp_repetir: bool = False
    temp_days: list[int] = field(default_factory=list)
    temp_days_cursor: int = 0

    @property
    def count(self) -> int:
        return len(self.todos)

    # ── Dynamic field count ──

    @property
    def n_fields(self) -> int:
        if self.temp_tipo == "nota":
            return 2
        if not self.temp_recordarme:
            return 3
        if self.temp_repetir:
            return 7
        return 9

    # ── Navigation ──

    def nav(self, delta: int) -> None:
        if self.todos:
            self.selected_idx = (self.selected_idx + delta) % len(self.todos)
            self._clamp_scroll()

    def _clamp_scroll(self) -> None:
        if self.selected_idx < self.scroll_offset:
            self.scroll_offset = self.selected_idx
        elif self.selected_idx >= self.scroll_offset + _MAX_VISIBLE:
            self.scroll_offset = self.selected_idx - _MAX_VISIBLE + 1

    def visible_range(self) -> tuple[int, int]:
        end = min(self.scroll_offset + _MAX_VISIBLE, len(self.todos))
        return self.scroll_offset, end

    # ── CRUD ──

    def add(self, **overrides: Any) -> dict:
        ahora = datetime.datetime.now()
        t: dict[str, Any] = {
            "id": self.next_id,
            "tipo": "tarea",
            "orden": len(self.todos) + 1,
            "texto": "",
            "activo": True,
            "last_done_date": None,
            "recordarme": False,
            "alarma_hora": ahora.hour,
            "alarma_min": ahora.minute,
            "alarma_dia": ahora.day,
            "alarma_mes": ahora.month,
            "alarma_anio": ahora.year,
            "repeat_days": [],
            "created_at": time.time(),
            "_disparada": False,
        }
        t.update(overrides)
        self.todos.append(t)
        self.next_id += 1
        self.selected_idx = len(self.todos) - 1
        self._clamp_scroll()
        return t

    def delete(self, idx: int) -> None:
        self.todos.pop(idx)
        if self.selected_idx >= len(self.todos):
            self.selected_idx = max(0, len(self.todos) - 1)
        self._clamp_scroll()

    def swap(self, a: int, b: int) -> None:
        self.todos[a], self.todos[b] = self.todos[b], self.todos[a]

    def toggle_done(self, idx: int) -> None:
        t = self.todos[idx]
        if t.get("tipo", "tarea") == "tarea":
            todo_set_done(t, not todo_is_done(t))

    def toggle_recordarme(self, idx: int) -> None:
        t = self.todos[idx]
        if t.get("tipo", "tarea") == "tarea":
            t["recordarme"] = not t.get("recordarme", False)
            if t["recordarme"]:
                t["_disparada"] = False

    # ── Edit mode ──

    def open_edit(self, idx: int | None = None) -> None:
        ahora = datetime.datetime.now()
        self.edit_mode = True
        self.edit_target = idx
        self.edit_field = 0
        if idx is not None and self.todos:
            t = self.todos[idx]
            self.temp_tipo = t.get("tipo", "tarea")
            self.temp_texto = t["texto"]
            self.temp_recordarme = t.get("recordarme", False)
            self.temp_alarma = [
                t.get("alarma_hora", ahora.hour),
                t.get("alarma_min", ahora.minute),
                t.get("alarma_dia", ahora.day),
                t.get("alarma_mes", ahora.month),
                t.get("alarma_anio", ahora.year),
            ]
            self.temp_days = _repeat_days_normalize(t.get("repeat_days"))
            self.temp_repetir = bool(self.temp_days)
        else:
            self.temp_tipo = "tarea"
            self.temp_texto = ""
            self.temp_recordarme = False
            self.temp_alarma = [
                ahora.hour, ahora.minute, ahora.day, ahora.month, ahora.year,
            ]
            self.temp_repetir = False
            self.temp_days = []
        self.temp_days_cursor = 0

    def commit_edit(self) -> dict | None:
        texto = self.temp_texto.strip() or (
            "Nueva nota" if self.temp_tipo == "nota" else "Nueva tarea"
        )
        recordarme = self.temp_recordarme and self.temp_tipo == "tarea"
        hh, mm, dia, mes, anio = self.temp_alarma
        repeat_days = (
            list(self.temp_days) if (recordarme and self.temp_repetir) else []
        )
        if self.edit_target is not None and self.todos:
            t = self.todos[self.edit_target]
            t["tipo"] = self.temp_tipo
            t["texto"] = texto
            t["recordarme"] = recordarme
            t["alarma_hora"] = hh
            t["alarma_min"] = mm
            t["alarma_dia"] = dia
            t["alarma_mes"] = mes
            t["alarma_anio"] = anio
            t["repeat_days"] = repeat_days
            t["_disparada"] = False
            result = t
        else:
            result = self.add(
                tipo=self.temp_tipo,
                texto=texto,
                recordarme=recordarme,
                alarma_hora=hh,
                alarma_min=mm,
                alarma_dia=dia,
                alarma_mes=mes,
                alarma_anio=anio,
                repeat_days=repeat_days,
            )
        self.edit_mode = False
        self.edit_target = None
        return result

    def cancel_edit(self) -> None:
        self.edit_mode = False
        self.edit_target = None

    # ── Edit field helpers ──

    def edit_toggle_tipo(self) -> None:
        if self.temp_tipo == "tarea":
            self.temp_tipo = "nota"
            self.temp_recordarme = False
        else:
            self.temp_tipo = "tarea"
        self._clamp_edit_field()

    def edit_toggle_recordarme(self) -> None:
        self.temp_recordarme = not self.temp_recordarme
        if self.temp_recordarme:
            ahora = datetime.datetime.now()
            self.temp_alarma = [
                ahora.hour, ahora.minute, ahora.day, ahora.month, ahora.year,
            ]
            self.temp_repetir = False
            self.temp_days = []
        self._clamp_edit_field()

    def edit_toggle_repetir(self) -> None:
        self.temp_repetir = not self.temp_repetir
        self._clamp_edit_field()

    def _clamp_edit_field(self) -> None:
        if self.edit_field >= self.n_fields:
            self.edit_field = 0

    def edit_nav_field(self, delta: int) -> None:
        self.edit_field = (self.edit_field + delta) % self.n_fields

    def edit_adjust_hour(self, delta: int) -> None:
        self.temp_alarma[0] = (self.temp_alarma[0] + delta) % 24

    def edit_adjust_min(self, delta: int) -> None:
        self.temp_alarma[1] = (self.temp_alarma[1] + delta) % 60

    def edit_adjust_day(self, delta: int) -> None:
        anio = self.temp_alarma[4]
        mes = self.temp_alarma[3]
        max_day = calendar.monthrange(anio, mes)[1]
        self.temp_alarma[2] = (self.temp_alarma[2] + delta - 1) % max_day + 1

    def edit_adjust_month(self, delta: int) -> None:
        self.temp_alarma[3] = (self.temp_alarma[3] + delta - 1) % 12 + 1

    def edit_adjust_year(self, delta: int) -> None:
        self.temp_alarma[4] = max(2025, self.temp_alarma[4] + delta)

    def edit_nav_days(self, delta: int) -> None:
        self.temp_days_cursor = (self.temp_days_cursor + delta) % 7

    def edit_toggle_day(self) -> None:
        d = self.temp_days_cursor
        if d in self.temp_days:
            self.temp_days.remove(d)
        else:
            self.temp_days.append(d)
        self.temp_days.sort()

    # ── Display helpers ──

    def item_display(self, t: dict) -> str:
        tipo = t.get("tipo", "tarea")
        if tipo == "nota":
            icono = "\u270e"
        else:
            icono = "\u2714" if todo_is_done(t) else "\u2610"
        if t.get("recordarme"):
            dias = _repeat_days_normalize(t.get("repeat_days"))
            if dias:
                rec = f" \u27f3{_repeat_days_str(dias)} {t['alarma_hora']:02d}:{t['alarma_min']:02d}"
            else:
                rec = f" \u25f7{t['alarma_dia']:02d}/{t['alarma_mes']:02d} {t['alarma_hora']:02d}:{t['alarma_min']:02d}"
        else:
            rec = ""
        texto = t["texto"][:30]
        return f"{icono} {texto}{rec}"
