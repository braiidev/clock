"""Servicio de clima: fetch de wttr.in con cache, reintentos y thread de fondo."""

from __future__ import annotations

import datetime
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable

WeatherCache = dict


def wrap_text_weather(txt: str) -> str:
    """Limpia la respuesta de wttr.in dejando solo la línea útil."""
    if "Weather report: " not in txt:
        return txt.strip().splitlines()[0] if txt.strip() else ""
    return txt.replace("Weather report: ", "").strip() if txt.strip() else ""


def fetch_weather(location: str = "", formato: str = "compacto") -> tuple[bool, str]:
    """Consume wttr.in y devuelve (ok, texto)."""
    headers = {"User-Agent": "curl/8.0"}
    try:
        if location and location.strip():
            loc = urllib.parse.quote(location.strip())
            url = f"http://wttr.in/{loc}?format=%l:+%t"
        else:
            url = "http://wttr.in/?format=%l:+%t"
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=6) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
        text = wrap_text_weather(raw)
        if not text:
            return False, "Sin datos"
        return True, text
    except urllib.error.URLError:
        return False, "Sin conexión"
    except Exception:
        return False, "Error al obtener clima"


def format_age(epoch: float | None) -> str:
    """Formatea la antigüedad de un dato en un texto corto."""
    if epoch is None:
        return ""
    secs = max(0, time.time() - epoch)
    if secs < 60:
        return "hace instantes"
    mins = int(secs // 60)
    if mins < 60:
        return f"hace {mins} min"
    hours = mins // 60
    if hours < 24:
        return f"hace {hours} h"
    return f"hace {hours // 24} d"


def _seconds_until_next_slot(intervalo_min: int) -> float:
    """Segundos hasta la próxima ranura alineada del intervalo dado."""
    now = datetime.datetime.now()
    slot = max(1, int(intervalo_min))
    minutes_since_midnight = now.hour * 60 + now.minute
    next_slot_minute = ((minutes_since_midnight // slot) + 1) * slot
    next_dt = now.replace(second=0, microsecond=0) + datetime.timedelta(
        minutes=(next_slot_minute - minutes_since_midnight)
    )
    return max(1.0, (next_dt - now).total_seconds())


class WeatherService:
    """Thread de fondo de clima con cache, reintentos y slots de update.

    Lee la config mediante el callable `get_config(key, default)` para no
    acoplarse al dict de la app. El callable `persist` guarda la cache.
    """

    def __init__(
        self,
        get_config: Callable[[str, object], object],
        persist: Callable[[bool, str, float], None],
    ):
        self._get_config = get_config
        self._persist = persist
        self._lock = threading.Lock()
        self._text: str | None = None
        self._ok = False
        self._epoch: float | None = None
        self._retry_count = 0
        self._retry_deadline: float | None = None
        self._stop = threading.Event()
        self._force = threading.Event()
        self._thread: threading.Thread | None = None

    # -- lectura de estado (desde la UI) --
    def snapshot(self) -> tuple[bool, str | None, float | None, int, float | None]:
        with self._lock:
            return (
                self._ok,
                self._text,
                self._epoch,
                self._retry_count,
                self._retry_deadline,
            )

    def restore_cache(self, text: str | None, ok: bool, epoch: float | None) -> None:
        with self._lock:
            self._text = text
            self._ok = ok
            self._epoch = epoch

    # -- control del thread --
    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()
        self._force.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def request_refresh(self) -> None:
        self._force.set()

    # -- config --
    def _intervalo(self) -> int:
        return int(self._get_config("clima_intervalo_min", 60))

    def _retry_max(self) -> int:
        return max(0, int(self._get_config("clima_retry_max", 3)))

    def _retry_segs(self) -> int:
        return max(1, int(self._get_config("clima_retry_segs", 60)))

    def _location(self) -> str:
        return str(self._get_config("clima_ubicacion", ""))

    def _formato(self) -> str:
        return str(self._get_config("clima_formato", "compacto"))

    # -- loop interno --
    def _loop(self) -> None:
        with self._lock:
            cached_epoch = self._epoch
            cache_is_fresh = (
                cached_epoch is not None
                and (time.time() - cached_epoch) < self._intervalo() * 60
            )
        if not cache_is_fresh:
            self._attempt_with_retries()
        while not self._stop.is_set():
            wait_secs = _seconds_until_next_slot(self._intervalo())
            waited = 0.0
            while waited < wait_secs:
                if self._stop.is_set():
                    return
                if self._force.is_set():
                    self._force.clear()
                    break
                time.sleep(1.0)
                waited += 1.0
            self._attempt_with_retries()

    def _attempt_with_retries(self) -> None:
        retry_max = self._retry_max()
        retry_segs = self._retry_segs()
        ok = self._do_fetch()
        if ok:
            self._reset_retry()
            return
        attempt = 0
        while attempt < retry_max:
            if self._stop.is_set():
                return
            attempt += 1
            with self._lock:
                self._retry_count = attempt
                self._retry_deadline = time.monotonic() + retry_segs
            waited = 0.0
            while waited < retry_segs:
                if self._stop.is_set():
                    return
                if self._force.is_set():
                    self._force.clear()
                    break
                time.sleep(1.0)
                waited += 1.0
            ok = self._do_fetch()
            if ok:
                self._reset_retry()
                return
        with self._lock:
            self._retry_count = 0
            self._retry_deadline = None
            self._ok = False
            self._text = "Error en la red"

    def _do_fetch(self) -> bool:
        ok, text = fetch_weather(self._location(), self._formato())
        now_epoch = time.time()
        with self._lock:
            self._ok = ok
            self._text = text
            self._epoch = now_epoch
        if ok and self._persist is not None:
            self._persist(ok, text, now_epoch)
        return ok

    def _reset_retry(self) -> None:
        with self._lock:
            self._retry_count = 0
            self._retry_deadline = None
