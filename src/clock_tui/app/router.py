"""Router global: navegación entre vistas y dispatch de input.

Capa pura (sin curses, sin I/O). Decide si una tecla es GLOBAL (q, ?, 0-6,
[, ], Esc) o se delega al controller de la vista activa.

NO interpreta los ActionResult de las features: los empaqueta y devuelve
para que el main app los resuelva (persistencia, servicios, render).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# Índices de vista (orden = orden de la tab bar, CLOCK.md §3)
VIEW_DASHBOARD = 0
VIEW_CLOCK = 1
VIEW_ALARMS = 2
VIEW_TIMERS = 3
VIEW_STOPWATCH = 4
VIEW_TODO = 5
VIEW_CONFIG = 6

NUM_VIEWS = 7

# Nombres por índice (para tab bar / helpers)
VIEW_NAMES: list[str] = [
    "Dash",
    "Reloj",
    "Alarm",
    "Timer",
    "Crono",
    "ToDo",
    "Conf",
]


@dataclass
class RouterResult:
    # comandos globales que el main app debe procesar
    quit_app: bool = False
    toggle_help: bool = False
    toggle_activity: bool = False
    view_changed: bool = False

    # resultado del controller de la feature (si la tecla no era global)
    feature_result: Any = None
    feature_dispatched: bool = False


class Router:
    """Gestiona la vista activa y el dispatch de teclas globales vs feature."""

    def __init__(self, current_view: int = VIEW_DASHBOARD):
        self.current_view = current_view
        self.help_open = False
        self.activity_open = False

    # ── Navegación de vistas ──

    def goto_view(self, index: int) -> bool:
        """Cambia a la vista dada (0..NUM_VIEWS-1). Devuelve True si cambió."""
        if 0 <= index < NUM_VIEWS and index != self.current_view:
            self.current_view = index
            return True
        return False

    def cycle_view(self, delta: int) -> bool:
        """Cicla las vistas con wrap-around."""
        nuevo = (self.current_view + delta) % NUM_VIEWS
        return self.goto_view(nuevo)

    # ── Dispatch principal ──

    def route(self, key: int, dispatch: Any) -> RouterResult:
        """Procesa una tecla.

        `dispatch` es un callable feature-agnóstico que invoca al controller de
        la vista activa y devuelve su ActionResult.
        """
        # Help abierto: cualquier tecla lo cierra (excepto q que sale).
        if self.help_open:
            if key == ord("q"):
                return RouterResult(quit_app=True)
            self.help_open = False
            return RouterResult(toggle_help=True)

        # Overlay de actividad abierto: cualquier tecla lo cierra (excepto q).
        if self.activity_open:
            if key == ord("q"):
                return RouterResult(quit_app=True)
            self.activity_open = False
            return RouterResult(toggle_activity=True)

        # ── Globales ──
        if key == ord("q"):
            return RouterResult(quit_app=True)
        if key in (ord("?"), ord("/")):
            self.help_open = True
            return RouterResult(toggle_help=True)
        if key == ord("o") and self.current_view != VIEW_DASHBOARD:
            self.activity_open = not self.activity_open
            return RouterResult(toggle_activity=True)
        if ord("0") <= key <= ord(str(NUM_VIEWS - 1)):
            idx = key - ord("0")
            changed = self.goto_view(idx)
            return RouterResult(view_changed=changed)
        if key == ord("]"):
            changed = self.cycle_view(1)
            return RouterResult(view_changed=changed)
        if key == ord("["):
            changed = self.cycle_view(-1)
            return RouterResult(view_changed=changed)

        # ── Delegar a la feature activa ──
        result = dispatch(self.current_view, key)
        return RouterResult(feature_result=result, feature_dispatched=True)

    def view_name(self, index: int | None = None) -> str:
        i = self.current_view if index is None else index
        if 0 <= i < len(VIEW_NAMES):
            return VIEW_NAMES[i]
        return "?"

    def view_index(self) -> int:
        return self.current_view
