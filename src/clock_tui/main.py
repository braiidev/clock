"""Entry point de clock-tui: CLI (update/uninstall/version) + TUI bajo curses.wrapper."""

from __future__ import annotations

import curses
import os
import shutil
import sys
import traceback

from clock_tui import __version__
from clock_tui.app.app import ClockApp
from clock_tui.core.log import LOG_FILE, _log_error
from clock_tui.update import check_update, do_update, repo_root

BIN_DIR = os.path.join(os.path.expanduser("~"), ".local", "bin")
BIN_PATH = os.path.join(BIN_DIR, "clock")
BIN_PATH_LEGACY = os.path.join(BIN_DIR, "clock-tui")
INSTALL_DIR_EXPECTED = os.path.join(
    os.path.expanduser("~"), ".local", "share", "clock-tui"
)
DATA_DIR = os.path.join(os.path.expanduser("~"), ".config", "clock")

USAGE = """uso: clock [--update | --check-update | --uninstall | --version]

  (sin argumentos)   arranca la TUI
  --update           actualiza el paquete (git pull) y sale
  --check-update     verifica si hay versión nueva
  --uninstall        desinstala el paquete (y, si confirmás, los datos)
  --version          imprime la versión instalada"""


def _cli_update() -> int:
    res = do_update(repo_root())
    print(res.message)
    return 0 if res.ok else 1


def _cli_check_update() -> int:
    info = check_update(repo_root())
    if not info.ok:
        print(f"⚠ No se pudo verificar: {info.error}", file=sys.stderr)
        return 1
    if info.behind > 0:
        print(
            f"→ Hay una actualización disponible ({info.available}). Ejecutá: clock --update"
        )
    else:
        print(f"✓ Estás al día ({info.current})")
    return 0


def _confirm(prompt: str) -> bool:
    try:
        r = input(f"{prompt} [y/N] ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        return False
    return r in ("y", "yes")


def _cli_uninstall() -> int:
    source = repo_root()
    if not source.startswith(INSTALL_DIR_EXPECTED):
        print(
            "Error: el código no vive en una instalación vía install.sh; no se borra.",
            file=sys.stderr,
        )
        print(f"  (repo detectado: {source})", file=sys.stderr)
        return 1

    print("▶ Desinstalando clock...")
    targets = [BIN_PATH, BIN_PATH_LEGACY, source]
    for p in targets:
        print(f"  ↳ {p}")
    if not _confirm("¿Eliminar la instalación? "):
        print("Cancelado.")
        return 1

    for p in (BIN_PATH, BIN_PATH_LEGACY):
        if os.path.islink(p) or os.path.exists(p):
            try:
                os.unlink(p)
            except OSError:
                pass
    shutil.rmtree(source, ignore_errors=True)

    if os.path.isdir(DATA_DIR):
        print(f"  ↳ datos en {DATA_DIR}")
        if _confirm("¿Borrar también los datos (data.json, sonidos, log)? "):
            shutil.rmtree(DATA_DIR, ignore_errors=True)
        else:
            print("  · datos conservados en", DATA_DIR)

    print("✓ clock desinstalado")
    return 0


def main() -> None:
    argv = sys.argv[1:]
    if "-h" in argv or "--help" in argv:
        print(USAGE)
        return
    if "--update" in argv:
        sys.exit(_cli_update())
    if "--check-update" in argv:
        sys.exit(_cli_check_update())
    if "--uninstall" in argv:
        sys.exit(_cli_uninstall())
    if "--version" in argv:
        print(f"clock {__version__}")
        return

    try:
        curses.wrapper(lambda stdscr: ClockApp(stdscr).run())
    except Exception as e:
        _log_error(f"Crash no manejado: {e}", traceback.format_exc())
        print(f"clock: ocurrió un error inesperado. Detalle en {LOG_FILE}")
        sys.exit(1)


if __name__ == "__main__":
    main()
