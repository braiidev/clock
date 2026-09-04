"""Entry point de clock-tui: arranca la app bajo curses.wrapper."""

from __future__ import annotations

import curses
import sys
import traceback

from clock_tui.app.app import ClockApp
from clock_tui.core.log import LOG_FILE, _log_error


def main() -> None:
    """Punto de entrada del comando `clock-tui`."""
    try:
        curses.wrapper(lambda stdscr: ClockApp(stdscr).run())
    except Exception as e:
        _log_error(f"Crash no manejado: {e}", traceback.format_exc())
        print(f"clock-tui: ocurrió un error inesperado. Detalle en {LOG_FILE}")
        sys.exit(1)