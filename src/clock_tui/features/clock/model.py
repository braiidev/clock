"""Modelo del reloj: hora local formateada, world clocks CRUD y picker de zonas.

Sin I/O, sin curses. El picker y el editor de apodo son estados
efímeros dentro del modelo.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from typing import Any

from clock_tui.features.clock.world_zones import (
    WORLD_ZONES,
    _wc_format_diff,
    _wc_offset_info,
    _wc_sorted_zones,
)

_PICKER_MAX_VISIBLE = 10
_WC_MAX_VISIBLE = 4


@dataclass
class WorldClock:
    zona: str  # IANA timezone id
    apodo: str  # nickname shown on screen


@dataclass
class PickerState:
    open: bool = False
    edit_target: int | None = None
    zones: list[tuple[str, str, str, str, str]] = field(default_factory=list)
    idx: int = 0
    scroll: int = 0
    filter_active: bool = False
    filter_text: str = ""


@dataclass
class EditNicknameState:
    active: bool = False
    zona: tuple[str, str, str, str, str] | None = None
    temp_name: str = ""


@dataclass
class ClockModel:
    wc_list: list[WorldClock]
    wc_idx: int = 0
    wc_scroll: int = 0
    picker: PickerState = field(default_factory=PickerState)
    edit_nick: EditNicknameState = field(default_factory=EditNicknameState)
    confirm_delete: bool = False

    # ── Formatting ──

    @staticmethod
    def format_local_time(
        now: datetime.datetime,
        *,
        show_seconds: bool = True,
        format_24h: bool = True,
    ) -> str:
        if format_24h:
            fmt = "%H:%M:%S" if show_seconds else "%H:%M"
        else:
            fmt = "%I:%M:%S %p" if show_seconds else "%I:%M %p"
        return now.strftime(fmt)

    @staticmethod
    def format_date_line(now: datetime.datetime, time_str: str) -> str:
        DIAS = ["Lun", "Mar", "Mi\u00e9", "Jue", "Vie", "S\u00e1b", "Dom"]
        MESES = [
            "Ene",
            "Feb",
            "Mar",
            "Abr",
            "May",
            "Jun",
            "Jul",
            "Ago",
            "Sep",
            "Oct",
            "Nov",
            "Dic",
        ]
        return f"{DIAS[now.weekday()]} {now.day} {MESES[now.month - 1]}  {time_str}"

    # ── WC list ──

    def wc_add(self, zona_iana: str, apodo: str) -> None:
        self.wc_list.append(WorldClock(zona=zona_iana, apodo=apodo))

    def wc_update(self, idx: int, zona_iana: str, apodo: str) -> None:
        self.wc_list[idx] = WorldClock(zona=zona_iana, apodo=apodo)

    def wc_delete(self, idx: int) -> None:
        self.wc_list.pop(idx)
        if self.wc_idx >= len(self.wc_list):
            self.wc_idx = max(0, len(self.wc_list) - 1)
        self._clamp_wc_scroll()

    def nav_wc(self, delta: int) -> None:
        if not self.wc_list:
            return
        self.wc_idx = (self.wc_idx + delta) % len(self.wc_list)
        self._clamp_wc_scroll()

    def wc_swap(self, a: int, b: int) -> None:
        self.wc_list[a], self.wc_list[b] = self.wc_list[b], self.wc_list[a]
        self._clamp_wc_scroll()

    def _clamp_wc_scroll(self) -> None:
        n = len(self.wc_list)
        if not n:
            self.wc_scroll = 0
            return
        if self.wc_idx < self.wc_scroll:
            self.wc_scroll = self.wc_idx
        elif self.wc_idx >= self.wc_scroll + _WC_MAX_VISIBLE:
            self.wc_scroll = self.wc_idx - _WC_MAX_VISIBLE + 1

    # ── Picker ──

    def picker_open(self, edit_target: int | None = None) -> None:
        self.picker = PickerState(open=True, edit_target=edit_target)
        self._picker_refresh()
        if edit_target is not None and self.wc_list:
            zona_actual = self.wc_list[edit_target].zona
            for i, z in enumerate(self.picker.zones):
                if z[0] == zona_actual:
                    self.picker.idx = i
                    break

    def picker_close(self) -> None:
        self.picker = PickerState()

    def _picker_refresh(self) -> None:
        ordenada = _wc_sorted_zones()
        texto = self.picker.filter_text.strip().lower()
        if self.picker.filter_active and texto:
            ordenada = [
                z
                for z in ordenada
                if texto in z[1].lower()
                or texto in z[2].lower()
                or texto in z[3].lower()
            ]
        self.picker.zones = ordenada
        if not self.picker.zones:
            self.picker.idx = 0
        else:
            self.picker.idx = min(self.picker.idx, len(self.picker.zones) - 1)
        self.picker.scroll = 0

    def picker_nav(self, delta: int) -> None:
        n = len(self.picker.zones)
        if not n:
            return
        self.picker.idx = (self.picker.idx + delta) % n
        if self.picker.idx < self.picker.scroll:
            self.picker.scroll = self.picker.idx
        elif self.picker.idx >= self.picker.scroll + _PICKER_MAX_VISIBLE:
            self.picker.scroll = self.picker.idx - _PICKER_MAX_VISIBLE + 1
        if self.picker.idx == 0:
            self.picker.scroll = 0
        elif self.picker.idx == n - 1:
            self.picker.scroll = max(0, n - _PICKER_MAX_VISIBLE)

    def picker_confirm_zone(self) -> None:
        if not self.picker.zones:
            return
        zona = self.picker.zones[self.picker.idx]
        if self.picker.edit_target is not None and self.wc_list:
            actual = self.wc_list[self.picker.edit_target].apodo
        else:
            actual = zona[4]
        self.edit_nick = EditNicknameState(active=True, zona=zona, temp_name=actual)
        self.picker = PickerState()

    # ── Edit nickname ──

    def edit_nick_commit(self) -> WorldClock | None:
        if not self.edit_nick.zona:
            return None
        apodo = self.edit_nick.temp_name.strip() or self.edit_nick.zona[4]
        wc = WorldClock(zona=self.edit_nick.zona[0], apodo=apodo)
        self.edit_nick = EditNicknameState()
        return wc

    def edit_nick_cancel(self) -> None:
        self.edit_nick = EditNicknameState()
        self.picker = PickerState()

    # ── Helpers for view ──

    def wc_offset_info(self, iana: str) -> tuple[datetime.datetime, int] | None:
        return _wc_offset_info(iana)

    def wc_time_str(self, iana: str) -> str:
        info = _wc_offset_info(iana)
        if info is None:
            return "--:--"
        return info[0].strftime("%H:%M")

    def wc_diff_str(self, iana: str) -> str:
        info = _wc_offset_info(iana)
        if info is None:
            return ""
        return f" (UTC {_wc_format_diff(info[1])})"
