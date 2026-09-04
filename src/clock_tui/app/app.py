"""App principal: main loop curses que orquesta features, servicios y persistencia.

Fase 5 (integración) — pasos 5.3 + 5.4:
- Bootstrap: carga de estado (store v7), construcción de modelos, tema/pares.
- Main loop: input → Router → dispatch al controller de la feature activa →
  persistencia (needs_save) → render de la vista activa → quit.
- Ticks de fondo: timers (countdown), alarmas + snoozes (check/check_snoozes),
  errores de persistencia → alert overlay modal con sonido en loop.
- Los comandos del Config (backup/restore/log/sonido/theme) se integran en
  el paso 5.5.
"""

from __future__ import annotations

import curses
import datetime
import os
import time

from clock_tui.app.router import (
    VIEW_ALARMS,
    VIEW_CLOCK,
    VIEW_CONFIG,
    VIEW_DASHBOARD,
    VIEW_STOPWATCH,
    VIEW_TIMERS,
    VIEW_TODO,
    Router,
)
from clock_tui.core import store as store_mod
from clock_tui.core.store import pop_persistence_error
from clock_tui.core.theme import (
    _ALERT_BLINK_PAIR_A,
    _ALERT_BLINK_PAIR_B,
    PAIR_CLIMA,
    PAIR_HELPERS,
    PAIR_MARCO,
    PAIR_NAV,
    PAIR_TEXTO,
    THEMES,
    _set_custom_theme,
)
from clock_tui.features.alarms import AlarmsController, AlarmsModel
from clock_tui.features.clock import ClockController, ClockModel, WorldClock
from clock_tui.features.config import ConfigController, ConfigModel, default_config
from clock_tui.features.dashboard import DashboardController, DashboardSnapshot
from clock_tui.features.stopwatch import StopwatchController, StopwatchModel
from clock_tui.features.timers import TimersController, TimersModel
from clock_tui.features.todo import TodoController, TodoModel, todo_is_done
from clock_tui.services import weather as weather_service
from clock_tui.services.audio import AudioPlayer, resolve_sound_path
from clock_tui.ui.frame import draw_micro
from clock_tui.ui.overlay import draw_alert
from clock_tui.ui.responsive import size_tier


class ClockApp:
    def __init__(self, stdscr: object) -> None:
        self.stdscr = stdscr
        self.router = Router()

        loaded = store_mod.load()
        if loaded:
            data_alarms, data_timers, todos, saved_config, self.weather_cache = loaded
        else:
            data_alarms, data_timers, todos, saved_config, self.weather_cache = (
                [],
                [],
                [],
                {},
                {},
            )

        # Config = contrato global (D15); merge de defaults + guardado.
        self.config = default_config()
        self._merge_config(saved_config)
        self.config_model = ConfigModel(config=self.config)

        # Modelos de features.
        self.alarms = AlarmsModel.from_data(data_alarms)
        self.timers = TimersModel.from_data(data_timers)
        self.stopwatch = StopwatchModel()
        self.todo = TodoModel(todos=todos)
        if todos:
            self.todo.next_id = max(t.get("id", 0) for t in todos) + 1
        self.clock = ClockModel(wc_list=self._load_world_clocks())

        # Servicio de clima.
        self.weather = weather_service.WeatherService(
            get_config=lambda k, d: self.config.get(k, d),
            persist=self._persist_weather,
        )
        if self.weather_cache:
            self.weather.restore_cache(
                self.weather_cache.get("text"),
                bool(self.weather_cache.get("ok", True)),
                self.weather_cache.get("ts"),
            )
        if self.config.get("clima_activo", False):
            self.weather.start()

        # Pares fijos de alerta (rojo) y help (blanco/negro); se inicializan una vez.
        curses.init_pair(_ALERT_BLINK_PAIR_A, curses.COLOR_BLACK, curses.COLOR_RED)
        curses.init_pair(_ALERT_BLINK_PAIR_B, curses.COLOR_RED, curses.COLOR_WHITE)

        self._alert: dict[str, object] | None = None
        self._alert_blink_counter = 0
        self._audio_player = AudioPlayer(self._is_alert_active)
        self._pairs = self._install_theme()

    # ── Config / theme ──

    def _merge_config(self, saved: dict) -> None:
        for k, default in self.config.items():
            if k not in saved:
                continue
            val = saved[k]
            if isinstance(default, bool):
                self.config[k] = bool(val)
            elif k in ("sonido_archivo", "sonido_custom_path"):
                self.config[k] = val if isinstance(val, str) else None
            elif k == "clima_ubicacion":
                self.config[k] = val if isinstance(val, str) else ""
            elif k == "world_clocks":
                limpio = [
                    {"zona": w["zona"], "apodo": w["apodo"]}
                    for w in val
                    if isinstance(w, dict)
                    and isinstance(w.get("zona"), str)
                    and isinstance(w.get("apodo"), str)
                ]
                self.config[k] = limpio[:8]
            elif isinstance(default, int):
                self.config[k] = int(val) if not isinstance(val, bool) else default
            else:
                self.config[k] = val

    def _load_world_clocks(self) -> list[WorldClock]:
        return [
            WorldClock(zona=wc["zona"], apodo=wc["apodo"])
            for wc in self.config.get("world_clocks", [])
        ]

    def _install_theme(self) -> dict[str, int]:
        nombre = self.config.get("tema", "clasico")
        paleta = (
            _set_custom_theme(self.config)
            if nombre == "custom"
            else THEMES.get(nombre, THEMES["clasico"])
        )
        curses.init_pair(PAIR_MARCO, paleta["marco"], -1)
        curses.init_pair(PAIR_TEXTO, paleta["texto"], -1)
        curses.init_pair(PAIR_CLIMA, paleta["clima"], -1)
        curses.init_pair(PAIR_HELPERS, paleta["helpers"], -1)
        curses.init_pair(PAIR_NAV, paleta["nav"], -1)
        return {
            "marco": curses.color_pair(PAIR_MARCO),
            "texto": curses.color_pair(PAIR_TEXTO),
            "clima": curses.color_pair(PAIR_CLIMA),
            "helpers": curses.color_pair(PAIR_HELPERS),
            "nav": curses.color_pair(PAIR_NAV),
        }

    # ── Persistencia ──

    def _persist_weather(self, ok: bool, text: str, epoch: float) -> None:
        self.weather_cache = {"text": text, "ok": ok, "ts": epoch}
        self._save_now()

    def _save_now(self) -> None:
        self.config["world_clocks"] = [
            {"zona": w.zona, "apodo": w.apodo} for w in self.clock.wc_list
        ]
        store_mod.save(
            self.alarms.to_data(),
            self.timers.to_data(),
            self.todo.todos,
            self.config,
            self.weather_cache,
        )

    # ── Main loop ──

    def run(self) -> None:
        curses.curs_set(0)
        self.stdscr.nodelay(1)
        self.stdscr.keypad(1)
        try:
            while True:
                if self._alert is None:
                    perr = pop_persistence_error()
                    if perr:
                        self._show_alert("⚠ Persistencia", perr)
                key = self.stdscr.getch()
                if key != -1:
                    if self._handle_key(key):
                        break
                self._tick()
                self._render()
                time.sleep(0.03)
        finally:
            self._audio_player.stop()
            self.weather.stop()
            self._save_now()
            curses.curs_set(1)

    # ── Input ──

    def _handle_key(self, key: int) -> bool:
        # Negocio de teclas globales cuando hay alerta activa.
        if self._alert is not None:
            return self._handle_alert_key(key)
        res = self.router.route(key, self._dispatch)
        if res.quit_app:
            return True
        if res.feature_dispatched and res.feature_result is not None:
            self._handle_feature_result(res.feature_result)
        return False

    def _handle_feature_result(self, result: object) -> None:
        needs_save = getattr(result, "needs_save", False)
        if needs_save:
            self._save_now()

    # ── Alert overlay ──

    def _is_alert_active(self) -> bool:
        return self._alert is not None

    def _show_alert(
        self,
        title: str,
        msg: str,
        *,
        posponable: bool = False,
        alarm_ref: object | None = None,
    ) -> None:
        self._audio_player.stop()
        self._alert = {
            "title": title,
            "msg": msg,
            "blink_state": 0,
            "posponable": posponable,
            "alarm_ref": alarm_ref,
        }
        self._alert_blink_counter = 0
        if self.config.get("sonido", True):
            self._start_alert_audio()

    def _start_alert_audio(self) -> None:
        path = resolve_sound_path(self.config, self._audios_dir())
        self._audio_player.start_loop(path)

    def _audios_dir(self) -> str:
        return os.path.join(store_mod.CONFIG_DIR, "sounds")

    def _dismiss_alert(self) -> None:
        ref = (self._alert or {}).get("alarm_ref")
        if ref is not None and hasattr(ref, "total_secs"):
            # Timer completado → reiniciar al cerrar con Space/Enter.
            ref.active = False
            ref.remaining = float(ref.total_secs())
            ref.last_tick = None
        self._alert = None
        self._audio_player.stop()

    def _postpone_alert(self) -> None:
        if self._alert is None or not self._alert.get("posponable"):
            return
        mins = int(self.config.get("alarma_posponer_min", 5))
        ref = self._alert.get("alarm_ref")
        nombre = "Alarma"
        if ref is not None:
            nombre = getattr(ref, "nombre", "Alarma")[:20]
        self.alarms.create_snooze(nombre, mins)
        self._alert = None
        self._audio_player.stop()
        self._save_now()

    def _handle_alert_key(self, key: int) -> bool:
        if self._alert is None:
            return False
        if key in (ord(" "), ord("\n"), 10, 13):
            self._dismiss_alert()
        elif key == 27:
            self._alert = None
            self._audio_player.stop()
        elif key in (ord("p"), ord("P")) and self._alert.get("posponable"):
            self._postpone_alert()
        return False

    def _tick_alert(self) -> None:
        if self._alert is None:
            return
        self._alert_blink_counter += 1
        if self._alert_blink_counter >= 6:
            self._alert_blink_counter = 0
            self._alert["blink_state"] = int(self._alert["blink_state"]) ^ 1

    def _dispatch(self, view: int, key: int) -> object:
        if view == VIEW_DASHBOARD:
            snap = self._build_dashboard_snapshot()
            return DashboardController().handle(snap, key, {})
        if view == VIEW_CLOCK:
            return ClockController().handle(self.clock, key, {})
        if view == VIEW_ALARMS:
            return AlarmsController().handle(self.alarms, key, {})
        if view == VIEW_TIMERS:
            return TimersController().handle(self.timers, key, {})
        if view == VIEW_STOPWATCH:
            return StopwatchController().handle(self.stopwatch, key, {})
        if view == VIEW_TODO:
            return TodoController().handle(self.todo, key, {})
        if view == VIEW_CONFIG:
            return ConfigController().handle(self.config_model, key, {})
        return None

    # ── Snapshot dashboard ──

    def _build_dashboard_snapshot(self) -> DashboardSnapshot:
        return DashboardSnapshot(
            now=datetime.datetime.now(),
            show_seconds=self.config.get("mostrar_segundos", True),
            format_24h=self.config.get("formato_24h", True),
            weather_line=self._weather_display_line(),
            next_alarm=self._next_alarm_data(),
            active_timers=[
                {"name": t.name, "remaining": t.remaining}
                for t in self.timers.timers
                if t.active
            ],
            sw_active=self.stopwatch.active,
            sw_elapsed=self.stopwatch.elapsed(),
            total_tasks=len(
                [t for t in self.todo.todos if t.get("tipo", "tarea") == "tarea"]
            ),
            done_tasks=len(
                [
                    t
                    for t in self.todo.todos
                    if t.get("tipo", "tarea") == "tarea" and todo_is_done(t)
                ]
            ),
            snoozed_count=len(self.alarms.snoozes),
        )

    def _next_alarm_data(self) -> dict | None:
        activados = [a for a in self.alarms.alarms if a.status == "activado"]
        if not activados:
            return None
        prox = min(activados, key=lambda a: (a.hora, a.minutos))
        return {
            "nombre": prox.nombre,
            "hora": prox.hora,
            "minutos": prox.minutos,
            "repeat_days": list(prox.repeat_days),
        }

    def _weather_display_line(self) -> str | None:
        if not self.config.get("clima_activo", False):
            return None
        ok, text, _epoch, retry_count, retry_deadline = self.weather.snapshot()
        if retry_count and retry_deadline is not None:
            secs = max(0, int(retry_deadline - time.monotonic()))
            return f"* [!] Reintento {retry_count}/{self.config.get('clima_retry_max', 3)} ({secs}s)"
        if text is None:
            return "* Clima: cargando..."
        return f"{'' if ok else '[!] '}{text}"

    # ── Ticks de fondo ──

    def _tick(self) -> None:
        now = datetime.datetime.now()

        # Timers countdown
        completed = self.timers.tick()
        for i in completed:
            t = self.timers.timers[i]
            h, m, s = t.time
            dur = f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"
            self._show_alert(f"⏱  {t.name}", f"Completado — {dur}", alarm_ref=t)

        # Alarmas
        fired = self.alarms.check(now)
        for a, title in fired:
            self._show_alert(
                f"◷  {a.nombre}", title, posponable=True, alarm_ref=a
            )

        # Snoozes
        snoozed = self.alarms.check_snoozes(now)
        for s, title in snoozed:
            self._show_alert(
                f"◷  {s.nombre} (pospuesta)", title, posponable=True, alarm_ref=s
            )

        # Blink del overlay activo
        self._tick_alert()

    # ── Render ──

    def _render(self) -> None:
        sh, sw = self.stdscr.getmaxyx()
        tier = size_tier(sh, sw)
        if tier == "micro":
            draw_micro(self.stdscr, self._clock_str(), self._pairs["texto"])
        else:
            self._render_view()
            self._render_footer()
        self._render_alert_overlay()

    def _render_alert_overlay(self) -> None:
        if self._alert is None:
            return
        draw_alert(
            self.stdscr,
            self._alert,
            curses.color_pair(_ALERT_BLINK_PAIR_A),
            curses.color_pair(_ALERT_BLINK_PAIR_B),
            int(self.config.get("alarma_posponer_min", 5)),
        )

    def _clock_str(self) -> str:
        return ClockModel.format_local_time(
            datetime.datetime.now(),
            show_seconds=self.config.get("mostrar_segundos", True),
            format_24h=self.config.get("formato_24h", True),
        )

    def _render_view(self) -> None:
        view = self.router.view_index()
        pairs = self._pairs
        cfg = self.config
        if view == VIEW_DASHBOARD:
            from clock_tui.features.dashboard import view as d_view

            d_view.render(
                self.stdscr,
                self._build_dashboard_snapshot(),
                theme={},
                pairs=pairs,
                config=cfg,
            )
            return
        specs = {
            VIEW_CLOCK: (self.clock, "clock"),
            VIEW_ALARMS: (self.alarms, "alarms"),
            VIEW_TIMERS: (self.timers, "timers"),
            VIEW_STOPWATCH: (self.stopwatch, "stopwatch"),
            VIEW_TODO: (self.todo, "todo"),
            VIEW_CONFIG: (self.config_model, "config"),
        }
        model, name = specs[view]
        _VIEWS[name].render(
            self.stdscr, model, theme={}, pairs=pairs, config=cfg
        )

    def _render_footer(self) -> None:
        from clock_tui.ui.frame import Painter

        painter = Painter(self.stdscr)
        h, w = painter.size
        names = [
            "Dash", "Reloj", "Alarm", "Timer", "Crono", "ToDo", "Conf"
        ]
        cur = self.router.view_index()
        tabs = " . ".join(
            (f"{n}" if i == cur else n) for i, n in enumerate(names)
        )
        footer = f"-- {self._clock_str()} --  {tabs}  q"
        x = max(0, (w - len(footer)) // 2)
        for ch_i, ch in enumerate(footer):
            if x + ch_i < w - 1:
                painter.safe(h - 1, x + ch_i, ch, self._pairs["nav"])


def _import_views() -> dict[str, object]:
    from clock_tui.features.alarms import view as alarms
    from clock_tui.features.clock import view as clock
    from clock_tui.features.config import view as config
    from clock_tui.features.stopwatch import view as stopwatch
    from clock_tui.features.timers import view as timers
    from clock_tui.features.todo import view as todo

    return {
        "clock": clock,
        "alarms": alarms,
        "timers": timers,
        "stopwatch": stopwatch,
        "todo": todo,
        "config": config,
    }


_VIEWS = _import_views()
