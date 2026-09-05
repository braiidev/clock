"""Servicio de audio: fallback chain de reproducción y loop de alerta.

Cadena de reproducción: ffplay → paplay → aplay → curses.beep() → \a stderr.
Subprocess no-bloqueante, respetando la config de sonido.
"""

from __future__ import annotations

import curses
import os
import subprocess
import sys
import threading
import time
from collections.abc import Callable
from typing import Any

_BEEP_SOUNDS = [
    "/usr/share/sounds/freedesktop/stereo/bell.oga",
    "/usr/share/sounds/freedesktop/stereo/complete.oga",
    "/usr/share/sounds/ubuntu/stereo/bell.ogg",
]

_SOUND_EXTS = (".wav", ".oga", ".ogg", ".mp3")


def _bundled_sounds_dir() -> str:
    """Carpeta de sonidos empaquetados dentro del paquete (src/clock_tui/sounds)."""
    return os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sounds"
    )


def try_beep(sound_path: str | None = None) -> subprocess.Popen | None:
    """Reproduce un sonido con la mejor herramienta disponible.

    Si `sound_path` existe se intenta con ffplay; si no, usa curses.beep()
    y los sonidos del sistema con paplay/aplay. Devuelve el proceso si se pudo
    lanzar uno, o None.
    """
    if sound_path and os.path.exists(sound_path):
        try:
            proc = subprocess.Popen(
                ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", sound_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return proc
        except FileNotFoundError:
            pass
    try:
        curses.beep()
    except Exception:
        pass
    try:
        sys.stderr.write("\a")
        sys.stderr.flush()
    except Exception:
        pass
    for snd in _BEEP_SOUNDS:
        if os.path.exists(snd):
            try:
                return subprocess.Popen(
                    ["paplay", snd],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            except FileNotFoundError:
                try:
                    return subprocess.Popen(
                        ["aplay", "-q", snd],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                except FileNotFoundError:
                    pass
            break
    return None


def resolve_sound_path(config: dict[str, Any], audios_dir: str) -> str | None:
    """Resuelve el archivo de sonido a reproducir según la config."""
    if config.get("sonido_modo") == "custom":
        path = config.get("sonido_custom_path")
        return path if path and os.path.exists(path) else None
    archivo = config.get("sonido_archivo")
    return os.path.join(audios_dir, archivo) if archivo else None


class AudioPlayer:
    """Reproduce un sonido en loop mientras una alerta esté activa.

    `is_alert_active` es un callable que devuelve True mientras haya alerta.
    """

    def __init__(self, is_alert_active: Callable[[], bool]):
        self._is_alert_active = is_alert_active
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._proc: subprocess.Popen | None = None

    def start_loop(self, sound_path: str | None) -> None:
        self._stop.clear()
        threading.Thread(target=self._loop, args=(sound_path,), daemon=True).start()

    def stop(self) -> None:
        self._stop.set()
        with self._lock:
            if self._proc is not None:
                try:
                    self._proc.terminate()
                except (ProcessLookupError, OSError):
                    pass
                self._proc = None

    def _loop(self, sound_path: str | None) -> None:
        while not self._stop.is_set() and self._is_alert_active():
            proc = try_beep(sound_path)
            if proc is None:
                for _ in range(30):
                    if self._stop.is_set() or not self._is_alert_active():
                        return
                    time.sleep(0.1)
                continue
            with self._lock:
                self._proc = proc
            while not self._stop.is_set() and self._is_alert_active():
                if proc.poll() is not None:
                    break
                time.sleep(0.1)
            if self._stop.is_set() or not self._is_alert_active():
                try:
                    proc.terminate()
                except (ProcessLookupError, OSError):
                    pass
                return
