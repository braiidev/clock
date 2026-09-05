"""App principal: main loop curses que orquesta features, servicios y persistencia.

Fase 5 (integración) — pasos 5.3 + 5.4 + 5.5:
- Bootstrap: carga de estado (store v7), construcción de modelos, tema/pares.
- Main loop: input → Router → dispatch al controller de la feature activa →
  persistencia (needs_save) → render de la vista activa → quit.
- Ticks de fondo: timers (countdown), alarmas + snoozes (check/check_snoozes),
  errores de persistencia → alert overlay modal con sonido en loop.
- Resultados de features: saves, dashboard jump (Enter → vista + item),
  refresh de clima (u), theme_changed, y comandos del Config
  (backup/restore/log_view/log_export/weather_toggle/sound_browser/sound_cycle).
- Overlays: file browser (restaurar/sonido), visor de log, help (?).
"""

from __future__ import annotations

import curses
import datetime
import os
import threading
import time
from typing import Any

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
from clock_tui.core.log import LOG_FILE, _log_mark_all_seen, _log_read_all
from clock_tui.core.store import pop_persistence_error
from clock_tui.core.theme import (
    _ALERT_BLINK_PAIR_A,
    _ALERT_BLINK_PAIR_B,
    _HELP_BG_PAIR,
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
from clock_tui.services.audio import (
    _SOUND_EXTS,
    AudioPlayer,
    resolve_sound_path,
    try_beep,
)
from clock_tui.services.backup import backup_data, restore_from_file
from clock_tui.ui.browser import draw_browser, list_entries
from clock_tui.ui.frame import draw_micro
from clock_tui.ui.overlay import (
    draw_activity,
    draw_alert,
    draw_help,
    draw_log_viewer,
)
from clock_tui.ui.responsive import size_tier

_GLOBAL_HELP_LINES = [
    "q:salir   0-6:cambiar vista   []:ciclar vista   ?:esta ayuda",
    "o:actividad (alarmas, timers, crono, tareas)",
    "↑↓ ←→ hj kl: navegar   Esc:cancelar",
    "n:nuevo   e:editar   d:borrar(con tecla)   Space:toggle/play   R:reset",
]


class ClockApp:
    _HELP_BY_VIEW: dict[int, list[str]] = {
        0: [
            "Vista de solo lectura: resumen de todo lo activo. Enter:ir a la fila, u:actualizar clima"
        ],
        1: ["←→ jk:alternar WC  J/K:orden  n:+WC  e:editar  d:borrar  u:clima"],
        2: ["n:nueva  ↑↓ jk:nav  J/K:orden  Space:on/off  e:editar  d:borrar"],
        3: ["↑↓ jk:fila  Tab:cicla  ←→:valor  Space:play/pause  R:reset"],
        4: ["n:nuevo  ↑↓:nav  Tab:campo  ←→:valor  Space:play/pause  R:reset"],
        5: ["Space:play/pause  Tab:marcar lap  d:borrar última  R:reset"],
        6: ["←→:categoría  ↑↓:nav  Enter/Space:cambiar  Esc:cancelar edición"],
    }

    def __init__(self, stdscr: Any) -> None:
        self.stdscr = stdscr
        self.router = Router()

        # Servicio de clima (thread en background).
        self.weather = weather_service.WeatherService(
            get_config=lambda k, d: self.config.get(k, d),
            persist=self._persist_weather,
        )
        self._load_models_from_store()
        self._restore_weather_cache()
        if self.config.get("clima_activo", False):
            self.weather.start()

        # Pares fijos: alerta (rojo), help (blanco/negro); se inicializan una vez.
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(_ALERT_BLINK_PAIR_A, curses.COLOR_BLACK, curses.COLOR_RED)
        curses.init_pair(_ALERT_BLINK_PAIR_B, curses.COLOR_RED, curses.COLOR_WHITE)
        curses.init_pair(_HELP_BG_PAIR, curses.COLOR_WHITE, curses.COLOR_BLACK)

        self._alert: dict[str, Any] | None = None
        self._alert_blink_counter = 0
        self._browser: dict[str, Any] | None = None
        self._log_viewer: dict[str, Any] | None = None
        self._alarm_edit: dict[str, Any] = {}
        self._toast: tuple[str, float] | None = None
        self._audio_player = AudioPlayer(self._is_alert_active)
        self._pairs = self._install_theme()

        self._maybe_start_auto_check()

    # ── Estado / models ──

    def _load_models_from_store(self) -> None:
        """(Re)construye config y modelos desde store. Reusable tras un restore."""
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

    def _restore_weather_cache(self) -> None:
        if self.weather_cache:
            self.weather.restore_cache(
                self.weather_cache.get("text"),
                bool(self.weather_cache.get("ok", True)),
                self.weather_cache.get("ts"),
            )

    def _reload_after_restore(self) -> None:
        """Recarga todo desde store tras restaurar un backup."""
        self._audio_player.stop()
        self.weather.stop()
        self._browser = None
        self._log_viewer = None
        self._load_models_from_store()
        self._restore_weather_cache()
        if self.config.get("clima_activo", False):
            self.weather.start()
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
                if key == curses.KEY_RESIZE:
                    self._on_resize()
                    continue
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

    def _on_resize(self) -> None:
        """Refresca las curses tras un resize para evitar rendering corrupto."""
        try:
            self.stdscr.clear()
            self.stdscr.refresh()
        except Exception:
            pass

    def _handle_key(self, key: int) -> bool:
        # Overlays modales tienen prioridad sobre el router.
        if self._alert is not None:
            return self._handle_alert_key(key)
        if self._browser is not None:
            return self._handle_browser_key(key)
        if self._log_viewer is not None:
            return self._handle_log_viewer_key(key)
        # Modo de edición activo: el feature captura TODAS las teclas
        # (los globales q/0-6/o/? se escriben en el campo en vez de ejecutarse).
        if self._capture_active():
            res = self.router.route(key, self._dispatch, capture=True)
            if res.feature_result is not None:
                self._handle_feature_result(res.feature_result)
            return False
        res = self.router.route(key, self._dispatch)
        if res.quit_app:
            return True
        if res.feature_dispatched and res.feature_result is not None:
            self._handle_feature_result(res.feature_result)
        return False

    def _capture_active(self) -> bool:
        """True si la vista activa está en modo edición/confirmación.

        Mientras un feature captura el teclado, los globales (q, 0-6, o, ?)
        quedan suspendidos y todas las teclas van a su controller.
        """
        view = self.router.view_index()
        if view == VIEW_ALARMS:
            es = self._alarm_edit
            return bool(es.get("edit_mode") or es.get("confirm_delete"))
        if view == VIEW_TIMERS:
            return bool(self.timers.edit_mode or self.timers.confirm_delete)
        if view == VIEW_TODO:
            return bool(self.todo.edit_mode or self.todo.confirm_delete)
        if view == VIEW_CLOCK:
            return bool(
                self.clock.picker.open
                or self.clock.edit_nick.active
                or self.clock.confirm_delete
            )
        if view == VIEW_CONFIG:
            return bool(self.config_model.text_edit)
        return False

    def _handle_feature_result(self, result: object) -> None:
        needs_save = getattr(result, "needs_save", False)
        if needs_save:
            self._save_now()

        jump_to = getattr(result, "jump_to", None)
        if jump_to is not None:
            self._handle_jump(int(jump_to), int(getattr(result, "jump_item", 0)))
        if getattr(result, "refresh_weather", False):
            self.weather.request_refresh()

        if getattr(result, "theme_changed", False):
            self._pairs = self._install_theme()

        command = getattr(result, "command", None)
        if command:
            self._handle_command(str(command))

    def _handle_jump(self, view: int, idx: int) -> None:
        self.router.goto_view(view)
        if view == VIEW_ALARMS and self.alarms.alarms:
            self.alarms.selected_idx = min(idx, len(self.alarms.alarms) - 1)
            self.alarms._clamp_scroll()
        elif view == VIEW_TIMERS and self.timers.timers:
            self.timers.selected_idx = min(idx, len(self.timers.timers) - 1)
            self.timers._clamp_scroll()
        elif view == VIEW_TODO and self.todo.todos:
            self.todo.selected_idx = min(idx, len(self.todo.todos) - 1)
            self.todo._clamp_scroll()

    def _handle_command(self, command: str) -> None:
        if command == "backup":
            ok, dest = backup_data(store_mod.DATA_FILE)
            self._show_alert(
                "✓ Backup creado" if ok else "⚠ Backup falló",
                f"Guardado en {dest}" if ok else dest,
            )
        elif command == "restore":
            self._open_browser("restore")
        elif command == "log_view":
            self._open_log_viewer()
        elif command == "log_export":
            self._export_log()
        elif command == "weather_toggle":
            if self.config.get("clima_activo", False):
                self.weather.start()
            else:
                self.weather.stop()
        elif command == "sound_browser":
            self._open_browser("sound")
        elif command == "sound_cycle":
            self._cycle_sound_file()
        elif command == "update_check":
            threading.Thread(target=self._run_update_command, daemon=True).start()

    # ── Self-update / toasts ──

    def toast(self, msg: str, seconds: float = 8.0) -> None:
        """Muestra un aviso transitorio (no modal) en pantalla."""
        self._toast = (msg, time.monotonic() + seconds)

    def _maybe_start_auto_check(self) -> None:
        from clock_tui import update as update_mod

        if not update_mod.is_auto_update_enabled():
            return
        try:
            threading.Thread(
                target=self._check_updates_background,
                name="clock-auto-update",
                daemon=True,
            ).start()
        except Exception:
            pass

    def _check_updates_background(self) -> None:
        from clock_tui import update as update_mod

        try:
            info = update_mod.check_update(update_mod.repo_root())
            if info.ok and info.behind > 0:
                self.toast(
                    f"↻ Actualización disponible: {info.available} "
                    "(Config → Sistema).",
                    seconds=12.0,
                )
        except Exception:
            pass

    def _run_update_command(self) -> None:
        from clock_tui import update as update_mod

        res = update_mod.do_update(update_mod.repo_root())
        self.toast(res.message, seconds=12.0)

    def _render_toast(self) -> None:
        if self._toast is None:
            return
        msg, deadline = self._toast
        if time.monotonic() >= deadline:
            self._toast = None
            return
        try:
            from clock_tui.ui.frame import Painter

            sh, sw = self.stdscr.getmaxyx()
            if sh < 4 or sw < 12:
                return
            painter = Painter(self.stdscr)
            x = max(0, (sw - len(msg)) // 2)
            attr = curses.A_REVERSE
            for i, ch in enumerate(msg):
                if x + i < sw - 1:
                    painter.safe(sh - 2, x + i, ch, attr)
        except Exception:
            pass

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

    # ── File browser (restore / sonido) ──

    def _open_browser(self, mode: str) -> None:
        if mode == "restore":
            cwd = os.path.expanduser("~")
        else:
            actual = self.config.get("sonido_custom_path")
            cwd = (
                os.path.dirname(actual)
                if actual and os.path.exists(os.path.dirname(actual))
                else os.path.expanduser("~")
            )
        self._browser = {
            "mode": mode,
            "cwd": cwd,
            "idx": 0,
            "entries": list_entries(cwd, mode),
        }

    def _refresh_browser_entries(self) -> None:
        if self._browser is not None:
            self._browser["entries"] = list_entries(
                str(self._browser["cwd"]), str(self._browser["mode"])
            )
            n = len(self._browser["entries"])
            if int(self._browser["idx"]) >= n:
                self._browser["idx"] = max(0, n - 1)

    def _handle_browser_key(self, key: int) -> bool:
        browser = self._browser
        if browser is None:
            return False
        entries = list(browser["entries"])
        n = len(entries)
        if key == 27:
            padre = os.path.dirname(str(browser["cwd"]))
            if padre and padre != browser["cwd"]:
                browser["cwd"] = padre
                browser["idx"] = 0
                self._refresh_browser_entries()
            else:
                self._browser = None
            return False
        if n == 0:
            return False
        if key == curses.KEY_DOWN:
            browser["idx"] = (int(browser["idx"]) + 1) % n
        elif key == curses.KEY_UP:
            browser["idx"] = (int(browser["idx"]) - 1) % n
        elif key in (ord("\n"), 10, 13):
            nombre, es_dir = entries[int(browser["idx"])]
            full = os.path.join(str(browser["cwd"]), nombre)
            if es_dir:
                browser["cwd"] = full
                browser["idx"] = 0
                self._refresh_browser_entries()
            elif browser["mode"] == "restore":
                self._restore_from_browser(full)
            else:
                self.config["sonido_custom_path"] = full
                self.config["sonido_modo"] = "custom"
                self._browser = None
                self._audio_player.stop()
                if self.config.get("sonido", True):
                    try_beep(full)
                self._save_now()
        return False

    def _restore_from_browser(self, path: str) -> None:
        ok, msg, _contenido = restore_from_file(path, store_mod.DATA_FILE)
        self._browser = None
        if not ok:
            self._show_alert("⚠ Restaurar falló", msg)
            return
        self._reload_after_restore()
        self._show_alert("✓ Backup restaurado", "Datos recargados.")

    def _render_browser(self) -> None:
        browser = self._browser
        if browser is None:
            return
        draw_browser(
            self.stdscr,
            list(browser["entries"]),
            str(browser["cwd"]),
            int(browser["idx"]),
            str(browser["mode"]),
            self._pairs,
        )

    # ── Log viewer ──

    def _open_log_viewer(self) -> None:
        self._log_viewer = {
            "entries": list(reversed(_log_read_all())),
            "idx": 0,
            "scroll": 0,
        }
        _log_mark_all_seen()

    def _handle_log_viewer_key(self, key: int) -> bool:
        viewer = self._log_viewer
        if viewer is None:
            return False
        n = len(viewer["entries"])
        if key in (27, ord(" "), ord("\n"), 10, 13):
            self._log_viewer = None
            return False
        if n == 0:
            return False
        if key == curses.KEY_DOWN:
            viewer["idx"] = min(int(viewer["idx"]) + 1, n - 1)
        elif key == curses.KEY_UP:
            viewer["idx"] = max(int(viewer["idx"]) - 1, 0)
        return False

    def _render_log_viewer(self) -> None:
        viewer = self._log_viewer
        if viewer is None:
            return
        viewer["scroll"] = draw_log_viewer(
            self.stdscr,
            list(viewer["entries"]),
            int(viewer["idx"]),
            int(viewer["scroll"]),
            curses.color_pair(_HELP_BG_PAIR),
        )

    def _export_log(self) -> None:
        if not os.path.exists(LOG_FILE):
            self._show_alert("⚠ Sin log", "Todavía no hay errores registrados.")
            return
        dest = os.path.expanduser("~/clock_error_log.txt")
        try:
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                contenido = f.read()
            with open(dest, "w", encoding="utf-8") as f:
                f.write(contenido)
            _log_mark_all_seen()
            self._show_alert("✓ Log exportado", f"Guardado en {dest}")
        except OSError as e:
            self._show_alert("⚠ Exportar falló", str(e.strerror or e))

    # ── Sonido ──

    def _cycle_sound_file(self) -> None:
        d = self._audios_dir()
        archivos = (
            sorted(f for f in os.listdir(d) if f.lower().endswith(_SOUND_EXTS))
            if os.path.isdir(d)
            else []
        )
        actual = self.config.get("sonido_archivo")
        opciones = [None] + archivos
        try:
            idx = opciones.index(actual)
        except ValueError:
            idx = 0
        self.config["sonido_archivo"] = opciones[(idx + 1) % len(opciones)]
        if self.config.get("sonido", True):
            try_beep(resolve_sound_path(self.config, d))

    # ── Help overlay ──

    def _render_help(self) -> None:
        draw_help(
            self.stdscr,
            self._HELP_BY_VIEW.get(self.router.view_index(), []),
            _GLOBAL_HELP_LINES,
            curses.color_pair(_HELP_BG_PAIR),
        )

    # ── Overlay de actividad ──

    def _build_activity_sections(self) -> list[tuple[str, list[str]]]:
        """Resumen en vivo de pendientes, agrupado por tipo (tecla `o`)."""
        secciones: list[tuple[str, list[str]]] = []

        if self.config.get("alarmas_mostrar", "ver") != "no ver":
            lineas = []
            activas = [a for a in self.alarms.alarms if a.status == "activado"]
            for a in sorted(activas, key=lambda a: (a.hora, a.minutos)):
                dias = a.repeat_str()
                sufijo = f"  {dias}" if dias else ""
                lineas.append(f"◷ {a.nombre}  {a.hora:02d}:{a.minutos:02d}{sufijo}")
            if lineas:
                secciones.append(("Alarmas activas", lineas))

        lineas = []
        for t in [t for t in self.timers.timers if t.active]:
            h, m, s = t.hms()
            rest = f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"
            lineas.append(f"⏱ {t.name}  {rest}")
        if lineas:
            secciones.append(("Timers activos", lineas))

        if self.stopwatch.active:
            h, m, s = self.stopwatch.elapsed_hms()
            secciones.append(("Cronómetro", [f"◷ {h:02d}:{m:02d}:{s:02d}"]))

        lineas = []
        pendientes = [
            t
            for t in self.todo.todos
            if t.get("tipo", "tarea") == "tarea" and not todo_is_done(t)
        ]
        for t in sorted(pendientes, key=lambda t: t.get("orden", 0)):
            texto = str(t.get("texto", ""))[:42]
            lineas.append(f"☐ {t.get('orden', '?')}. {texto}")
        if lineas:
            secciones.append(("Tareas pendientes", lineas))

        if not secciones:
            secciones = [("Actividad", ["(sin actividad pendiente)"])]
        return secciones

    def _render_activity_overlay(self) -> None:
        draw_activity(
            self.stdscr,
            self._build_activity_sections(),
            curses.color_pair(_HELP_BG_PAIR),
        )

    def _dispatch(self, view: int, key: int) -> object:
        if view == VIEW_DASHBOARD:
            snap = self._build_dashboard_snapshot()
            return DashboardController().handle(snap, key, {})
        if view == VIEW_CLOCK:
            return ClockController().handle(self.clock, key, {})
        if view == VIEW_ALARMS:
            return AlarmsController().handle(self.alarms, key, {}, self._alarm_edit)
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
                {"name": t.name, "remaining": t.remaining, "idx": i}
                for i, t in enumerate(self.timers.timers)
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
            self._show_alert(f"◷  {a.nombre}", title, posponable=True, alarm_ref=a)

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
            if self._log_viewer is not None:
                self._render_log_viewer()
            if self._browser is not None:
                self._render_browser()
            if self.router.help_open:
                self._render_help()
            if self.router.activity_open:
                self._render_activity_overlay()
        self._render_alert_overlay()
        self._render_toast()

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
        if name == "alarms":
            _VIEWS[name].render(
                self.stdscr,
                model,
                theme={},
                pairs=pairs,
                config=cfg,
                edit_state=self._alarm_edit,
            )
            return
        _VIEWS[name].render(self.stdscr, model, theme={}, pairs=pairs, config=cfg)

    def _render_footer(self) -> None:
        from clock_tui.ui.frame import Painter

        painter = Painter(self.stdscr)
        h, w = painter.size
        names = ["Dash", "Reloj", "Alarm", "Timer", "Crono", "ToDo", "Conf"]
        cur = self.router.view_index()
        tabs = " . ".join((f"{n}" if i == cur else n) for i, n in enumerate(names))
        footer = f"-- {self._clock_str()} --  {tabs}  q"
        x = max(0, (w - len(footer)) // 2)
        for ch_i, ch in enumerate(footer):
            if x + ch_i < w - 1:
                painter.safe(h - 1, x + ch_i, ch, self._pairs["nav"])


def _import_views() -> dict[str, Any]:
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
