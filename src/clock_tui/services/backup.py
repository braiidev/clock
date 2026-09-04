"""Backup y restauración del archivo de datos."""

from __future__ import annotations

import datetime
import json
import os


def backup_data(data_file: str, dest_dir: str | None = None) -> tuple[bool, str]:
    """Copia data_file a un backup con timestamp. Devuelve (ok, destino|error)."""
    ts = datetime.datetime.now().strftime("%Y-%m-%d_%H%M")
    dest = os.path.join(dest_dir or os.path.expanduser("~"), f"clock_backup_{ts}.json")
    try:
        with open(data_file, "r", encoding="utf-8") as f:
            contenido = f.read()
        with open(dest, "w", encoding="utf-8") as f:
            f.write(contenido)
        return True, dest
    except OSError as e:
        return False, str(e.strerror or e)


def restore_from_file(path: str, data_file: str) -> tuple[bool, str, str | None]:
    """Valida y restaura un backup. Devuelve (ok, mensaje, contenido|None).

    Si ok es True, `contenido` es el JSON del archivo restaurado.
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            contenido = f.read()
        json.loads(contenido)
    except (OSError, json.JSONDecodeError) as e:
        return False, f"Archivo inválido: {e}", None
    try:
        with open(data_file, "w", encoding="utf-8") as f:
            f.write(contenido)
    except OSError as e:
        return False, str(e.strerror or e), None
    return True, "Restaurado", contenido
