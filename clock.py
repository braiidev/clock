#!/usr/bin/env python3
"""
clock.py v6.1 — Terminal dashboard: reloj, clima, alarmas, pomodoro,
timers, cronómetro, notas/tareas y configuración.
Responsive: 40x8 mínimo, 40x16 óptimo, 60x20 ideal.
Layout: H=0 clima (W=0 izq) | H=end modo+nav | H=center contenido.
"""

import curses
import datetime
import time
import threading
import json
import os
import subprocess
import sys
import traceback
import urllib.request
import urllib.error
import urllib.parse
from zoneinfo import ZoneInfo

# ──────────────────────────────────────────────
#  HELPERS
# ──────────────────────────────────────────────


def secs_to_hms(secs):
    secs = max(0, int(secs))
    h = secs // 3600
    m = (secs % 3600) // 60
    s = secs % 60
    return h, m, s


def hms_to_secs(h, m, s):
    return h * 3600 + m * 60 + s


# ──────────────────────────────────────────────
#  RECURRENCIA
# ──────────────────────────────────────────────

DIAS_ABBR = ["L", "M", "X", "J", "V", "S", "D"]


def _repeat_days_normalize(repeat_days):
    if not repeat_days:
        return []
    try:
        return sorted({int(d) % 7 for d in repeat_days})
    except (TypeError, ValueError):
        return []


def _repeat_days_str(repeat_days):
    dias = _repeat_days_normalize(repeat_days)
    if not dias:
        return "una vez"
    if dias == [0, 1, 2, 3, 4]:
        return "L-V"
    if dias == [0, 1, 2, 3, 4, 5, 6]:
        return "todos"
    if dias == [5, 6]:
        return "S-D"
    return "".join(DIAS_ABBR[d] for d in dias)


def _todo_is_done(t, hoy=None):
    dias = _repeat_days_normalize(t.get("repeat_days"))
    if not dias:
        return not t.get("activo", True)
    if hoy is None:
        hoy = datetime.date.today().isoformat()
    return t.get("last_done_date") == hoy


def _todo_set_done(t, done, hoy=None):
    dias = _repeat_days_normalize(t.get("repeat_days"))
    if not dias:
        t["activo"] = not done
        return
    if hoy is None:
        hoy = datetime.date.today().isoformat()
    t["last_done_date"] = hoy if done else None


# ──────────────────────────────────────────────
#  RELOJ MUNDIAL
# ──────────────────────────────────────────────

WORLD_ZONES = [
    ("Pacific/Midway", "Midway", "Samoa Americana", "Oceanía", "MID"),
    ("Pacific/Honolulu", "Honolulu", "EEUU", "Oceanía", "HNL"),
    ("Pacific/Marquesas", "Taiohae", "Polinesia Francesa", "Oceanía", "MQS"),
    ("America/Anchorage", "Anchorage", "EEUU", "América", "ANC"),
    ("America/Los_Angeles", "Los Ángeles", "EEUU", "América", "LAX"),
    ("America/Denver", "Denver", "EEUU", "América", "DEN"),
    ("America/Mexico_City", "Ciudad de México", "México", "América", "MEX"),
    ("America/Chicago", "Chicago", "EEUU", "América", "CHI"),
    ("America/Bogota", "Bogotá", "Colombia", "América", "BOG"),
    ("America/New_York", "Nueva York", "EEUU", "América", "NY"),
    ("America/Caracas", "Caracas", "Venezuela", "América", "CCS"),
    ("America/Santiago", "Santiago", "Chile", "América", "SCL"),
    ("America/St_Johns", "St. John's", "Canadá", "América", "SJN"),
    ("America/Sao_Paulo", "São Paulo", "Brasil", "América", "SP"),
    ("America/Argentina/Buenos_Aires", "Buenos Aires", "Argentina", "América", "BUE"),
    ("Atlantic/Azores", "Azores", "Portugal", "Atlántico", "AZO"),
    ("Atlantic/Cape_Verde", "Praia", "Cabo Verde", "Atlántico", "CV"),
    ("UTC", "UTC", "—", "UTC", "UTC"),
    ("Europe/Lisbon", "Lisboa", "Portugal", "Europa", "LIS"),
    ("Europe/London", "Londres", "Reino Unido", "Europa", "LON"),
    ("Europe/Madrid", "Madrid", "España", "Europa", "MAD"),
    ("Europe/Paris", "París", "Francia", "Europa", "PAR"),
    ("Africa/Lagos", "Lagos", "Nigeria", "África", "LOS"),
    ("Europe/Athens", "Atenas", "Grecia", "Europa", "ATH"),
    ("Africa/Cairo", "El Cairo", "Egipto", "África", "CAI"),
    ("Africa/Johannesburg", "Johannesburgo", "Sudáfrica", "África", "JNB"),
    ("Europe/Moscow", "Moscú", "Rusia", "Europa", "MOW"),
    ("Asia/Tehran", "Teherán", "Irán", "Asia", "THR"),
    ("Asia/Dubai", "Dubái", "EAU", "Asia", "DXB"),
    ("Asia/Kabul", "Kabul", "Afganistán", "Asia", "KBL"),
    ("Asia/Karachi", "Karachi", "Pakistán", "Asia", "KHI"),
    ("Asia/Kolkata", "Bombay/Delhi", "India", "Asia", "IND"),
    ("Asia/Kathmandu", "Katmandú", "Nepal", "Asia", "KTM"),
    ("Asia/Dhaka", "Daca", "Bangladesh", "Asia", "DAC"),
    ("Asia/Yangon", "Rangún", "Myanmar", "Asia", "RGN"),
    ("Asia/Bangkok", "Bangkok", "Tailandia", "Asia", "BKK"),
    ("Asia/Shanghai", "Shanghái", "China", "Asia", "SHA"),
    ("Asia/Singapore", "Singapur", "Singapur", "Asia", "SIN"),
    ("Asia/Tokyo", "Tokio", "Japón", "Asia", "TYO"),
    ("Asia/Seoul", "Seúl", "Corea del Sur", "Asia", "SEL"),
    ("Australia/Adelaide", "Adelaida", "Australia", "Oceanía", "ADL"),
    ("Australia/Sydney", "Sídney", "Australia", "Oceanía", "SYD"),
    ("Pacific/Guadalcanal", "Honiara", "Islas Salomón", "Oceanía", "HIR"),
    ("Pacific/Auckland", "Auckland", "Nueva Zelanda", "Oceanía", "AKL"),
    ("Pacific/Chatham", "Chatham", "Nueva Zelanda", "Oceanía", "CHA"),
    ("Pacific/Tongatapu", "Nukuʻalofa", "Tonga", "Oceanía", "TBU"),
    ("Pacific/Kiritimati", "Kiritimati", "Kiribati", "Oceanía", "LINE"),
]


def _wc_zone_lookup(iana):
    for z in WORLD_ZONES:
        if z[0] == iana:
            return z
    return (iana, iana, "?", "?", iana[:4].upper())


def _wc_offset_info(iana, ref=None):
    try:
        tz = ZoneInfo(iana)
    except Exception:
        return None
    ahora_utc = ref if ref is not None else datetime.datetime.now(datetime.timezone.utc)
    if ahora_utc.tzinfo is None:
        ahora_utc = ahora_utc.replace(tzinfo=datetime.timezone.utc)
    dt_zona = ahora_utc.astimezone(tz)
    dt_local = ahora_utc.astimezone()
    off_zona = dt_zona.utcoffset() or datetime.timedelta(0)
    off_local = dt_local.utcoffset() or datetime.timedelta(0)
    diff_min = int(round((off_zona - off_local).total_seconds() / 60))
    return dt_zona, diff_min


def _wc_format_diff(diff_min):
    sign = "+" if diff_min >= 0 else "-"
    a = abs(diff_min)
    h, m = divmod(a, 60)
    return f"{sign}{h}.{m:02d}" if m else f"{sign}{h}"


def _wc_sorted_zones(zonas=None, ref=None):
    zonas = zonas if zonas is not None else WORLD_ZONES

    def _key(z):
        try:
            t = ref if ref is not None else datetime.datetime.now(datetime.timezone.utc)
            off = t.astimezone(ZoneInfo(z[0])).utcoffset()
        except Exception:
            off = datetime.timedelta(0)
        return off

    return sorted(zonas, key=_key)


# ──────────────────────────────────────────────
#  SONIDO
# ──────────────────────────────────────────────

_BEEP_SOUNDS = [
    "/usr/share/sounds/freedesktop/stereo/bell.oga",
    "/usr/share/sounds/freedesktop/stereo/complete.oga",
    "/usr/share/sounds/ubuntu/stereo/bell.ogg",
]

_SOUND_EXTS = (".wav", ".oga", ".ogg", ".mp3")


def try_beep(sound_path=None):
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


# ──────────────────────────────────────────────
#  CLIMA
# ──────────────────────────────────────────────


def wrap_text_weather(txt):
    if "Weather report: " not in txt:
        return txt.strip().splitlines()[0] if txt.strip() else ""
    return txt.replace("Weather report: ", "").strip() if txt.strip() else ""


def fetch_weather(location="", formato="compacto"):
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


# ──────────────────────────────────────────────
#  PERSISTENCIA
# ──────────────────────────────────────────────

_CONFIG_DIR = os.path.expanduser("~/.config/clock")
DATA_FILE = os.path.join(_CONFIG_DIR, "clock_data.json")
LOG_FILE = os.path.join(_CONFIG_DIR, "clock_error.log")
os.makedirs(_CONFIG_DIR, exist_ok=True)

_save_lock = threading.Lock()
_last_persistence_error = None


def pop_persistence_error():
    global _last_persistence_error
    err = _last_persistence_error
    _last_persistence_error = None
    return err


def _log_error(msg, trace=None):
    entry = {"ts": time.time(), "msg": str(msg)[:2000], "trace": trace, "visto": False}
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _log_read_all():
    if not os.path.exists(LOG_FILE):
        return []
    entries = []
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except OSError:
        return []
    return entries


def _log_has_unseen():
    return any(not e.get("visto", False) for e in _log_read_all())


def _log_mark_all_seen():
    entries = _log_read_all()
    if not entries:
        return
    for e in entries:
        e["visto"] = True
    try:
        with open(LOG_FILE, "w", encoding="utf-8") as f:
            for e in entries:
                f.write(json.dumps(e, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _save_data(alarm_lists, timers, pomodoro, todos, config=None, weather_cache=None):
    global _last_persistence_error
    with _save_lock:
        timers_clean = [{"name": t["name"], "time": t["time"]} for t in timers]
        pomo_clean = {
            "work": {
                "time": pomodoro["work"]["time"],
                "count": pomodoro["work"]["count"],
            },
            "shortbreak": {
                "time": pomodoro["shortbreak"]["time"],
                "count": pomodoro["shortbreak"]["count"],
            },
            "longrest": {
                "time": pomodoro["longrest"]["time"],
                "count": pomodoro["longrest"]["count"],
            },
        }
        if weather_cache is None:
            try:
                with open(DATA_FILE, "r", encoding="utf-8") as f:
                    weather_cache = json.load(f).get("weather_cache", {})
            except FileNotFoundError:
                weather_cache = {}
            except Exception:
                weather_cache = {}
        data = {
            "version": 6,
            "alarms": alarm_lists,
            "timers": timers_clean,
            "pomodoro": pomo_clean,
            "todos": todos,
            "config": config or {},
            "weather_cache": weather_cache,
        }
        try:
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except OSError as e:
            _last_persistence_error = f"No se pudo guardar: {e.strerror or e}"
        except Exception as e:
            _last_persistence_error = f"No se pudo guardar: {e}"


def _load_data():
    global _last_persistence_error
    if not os.path.exists(DATA_FILE):
        return None
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if data.get("version") not in (1, 2, 3, 4, 5, 6):
            _last_persistence_error = (
                "Archivo de datos con versión no soportada; se ignoró."
            )
            return None
        timers = []
        for t in data.get("timers", []):
            secs = hms_to_secs(*t["time"])
            timers.append(
                {
                    "name": t["name"],
                    "time": t["time"],
                    "active": False,
                    "started": False,
                    "remaining": float(secs),
                    "last_tick": None,
                }
            )
        todos = data.get("todos", [])
        now_ts = time.time()
        now_dt = datetime.datetime.now()
        for i, t in enumerate(todos):
            if "tipo" not in t:
                t["tipo"] = "tarea"
            if "created_at" not in t:
                t["created_at"] = now_ts
            t.pop("due_date", None)
            t.setdefault("alarma_dia", now_dt.day)
            t.setdefault("alarma_mes", now_dt.month)
            t.setdefault("alarma_anio", now_dt.year)
            t.setdefault("repeat_days", [])
            t.setdefault("last_done_date", None)
            t.setdefault("id", i)
        alarms = data.get("alarms", [])
        for a in alarms:
            a.setdefault("repeat_days", [])
        config = data.get("config", {})
        weather_cache = data.get("weather_cache", {})
        return (alarms, timers, data.get("pomodoro", {}), todos, config, weather_cache)
    except json.JSONDecodeError as e:
        _last_persistence_error = f"Datos guardados corruptos ({e}); se ignoraron."
        return None
    except OSError as e:
        _last_persistence_error = f"No se pudo leer datos guardados: {e.strerror or e}"
        return None
    except Exception as e:
        _last_persistence_error = f"No se pudo leer datos guardados: {e}"
        return None


# ──────────────────────────────────────────────
#  TEMAS
# ──────────────────────────────────────────────


def SET_CUSTOM_THEME(props={}):
    if props.get("make") == True:
        return {
            "custom_color_marco": "Azul",
            "custom_color_texto": "Blanco",
            "custom_color_clima": "Amarillo",
            "custom_color_helpers": "Azul",
            "custom_color_nav": "Azul",
        }
    return {
        "marco": COLORS_PACK.get(props.get("custom_color_marco"), "Azul"),
        "texto": COLORS_PACK.get(props.get("custom_color_texto"), "Blanco"),
        "clima": COLORS_PACK.get(props.get("custom_color_clima"), "Amarillo"),
        "helpers": COLORS_PACK.get(props.get("custom_color_helpers"), "Azul"),
        "nav": COLORS_PACK.get(props.get("custom_color_nav"), "Azul"),
    }


COLORS_PACK = {
    "Negro": curses.COLOR_BLACK,
    "Rojo": curses.COLOR_RED,
    "Verde": curses.COLOR_GREEN,
    "Amarillo": curses.COLOR_YELLOW,
    "Azul": curses.COLOR_BLUE,
    "Magenta": curses.COLOR_MAGENTA,
    "Cian": curses.COLOR_CYAN,
    "Blanco": curses.COLOR_WHITE,
}
COLOR_LIST = list(COLORS_PACK.keys())

THEMES = {
    "clasico": {
        "marco": curses.COLOR_CYAN,
        "texto": curses.COLOR_WHITE,
        "clima": curses.COLOR_GREEN,
        "helpers": curses.COLOR_YELLOW,
        "nav": curses.COLOR_CYAN,
    },
    "mono": {
        "marco": curses.COLOR_WHITE,
        "texto": curses.COLOR_WHITE,
        "clima": curses.COLOR_WHITE,
        "helpers": curses.COLOR_WHITE,
        "nav": curses.COLOR_WHITE,
    },
    "calido": {
        "marco": curses.COLOR_YELLOW,
        "texto": curses.COLOR_WHITE,
        "clima": curses.COLOR_RED,
        "helpers": curses.COLOR_YELLOW,
        "nav": curses.COLOR_RED,
    },
    "alto_contraste": {
        "marco": curses.COLOR_MAGENTA,
        "texto": curses.COLOR_WHITE,
        "clima": curses.COLOR_GREEN,
        "helpers": curses.COLOR_MAGENTA,
        "nav": curses.COLOR_MAGENTA,
    },
    "custom": SET_CUSTOM_THEME(),
}
THEME_NAMES = list(THEMES.keys())

_ALERT_BLINK_PAIR_A = 3
_ALERT_BLINK_PAIR_B = 4
_HELP_BG_PAIR = 8
PAIR_MARCO = 1
PAIR_HELPERS = 2
PAIR_CLIMA = 5
PAIR_TEXTO = 6
PAIR_NAV = 7


# ──────────────────────────────────────────────
#  MAIN APP
# ──────────────────────────────────────────────


class ClockApp:

    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.current_view = 0
        self.running = True

        self.alarm_lists = []
        self.alarm_edit_mode = False
        self.alarm_edit_target = None
        self.alarm_edit_field = 0
        self.temp_alarm_time_field = 0
        self.temp_alarm_time = [0, 0]
        self.temp_alarm_name = "Alarma"
        self.temp_alarm_days = []
        self.temp_alarm_days_cursor = 0
        self.selected_alarm_idx = 0
        self.alarm_confirm_delete = False
        self.alarm_scroll_offset = 0

        self.snooze_alarms = []
        self._alarm_fired_this_minute = set()
        self._last_alarm_minute = None
        self._todo_fired_this_minute = set()
        self._last_todo_minute = None

        self.world_clocks = []
        self.wc_selected_idx = 0
        self.wc_focus = False
        self.wc_group_offset = 0
        self.wc_picker_open = False
        self.wc_picker_edit_target = None
        self.wc_picker_list = []
        self.wc_picker_idx = 0
        self.wc_picker_scroll = 0
        self.wc_picker_filter_active = False
        self.wc_picker_filter_text = ""
        self.wc_apodo_mode = False
        self.temp_wc_zona = None
        self.temp_wc_apodo = ""
        self.wc_confirm_delete = False
        self._wc_offset_cache = {}
        self._wc_offset_cache_minute = None

        self.pomodoro = {
            "is_active": False,
            "started": False,
            "current_mode": "work",
            "work": {"next": "shortbreak", "time": [0, 20, 0], "count": 3, "left": 3},
            "shortbreak": {"next": "work", "time": [0, 5, 0], "count": 2, "left": 2},
            "longrest": {"next": "work", "time": [0, 15, 0], "count": 1, "left": 1},
            "timer_value": 0,
            "cycle_idx": 0,
            "edit_field": 0,
            "mode_nav": "work",
            "time_field": 0,
        }
        self._pomo_last_tick = None
        self._pomo_seq_cache = None

        self.timers = [
            {
                "name": "Temporizador1",
                "time": [0, 10, 0],
                "active": False,
                "started": False,
                "remaining": 600,
                "last_tick": None,
            }
        ]
        self.selected_timer_idx = 0
        self.timer_edit_mode = False
        self.timer_edit_target = None
        self.temp_timer_name = ""
        self.timer_time_field = 0
        self.timer_scroll_offset = 0

        self.stopwatch = {
            "active": False,
            "start_time": None,
            "base_elapsed": 0.0,
            "records": [],
            "last_record_at": 0.0,
        }
        self.sw_scroll_offset = 0

        self.todos = []
        self._todo_next_id = 1
        self.todo_selected_idx = 0
        self.todo_scroll_offset = 0
        self.todo_confirm_delete = False
        self.todo_edit_mode = False
        self.todo_edit_target = None
        self.todo_edit_field = 0
        self.temp_todo_tipo = "tarea"
        self.temp_todo_texto = ""
        self.temp_todo_recordarme = False
        self.temp_todo_alarma = [0, 0, 1, 1, 2025]
        self.temp_todo_repetir = False
        self.temp_todo_days = []
        self.temp_todo_days_cursor = 0
        self._notes_panel_open = False
        self._notes_scroll = 0
        self._notes_selected_idx = 0
        self._notes_expanded = set()

        self.config = {
            "mostrar_marco": True,
            "mostrar_helpers": True,
            "mostrar_segundos": True,
            "formato_24h": True,
            "sonido": True,
            "sonido_modo": "default",
            "sonido_archivo": None,
            "sonido_custom_path": None,
            "clima_activo": False,
            "clima_ubicacion": "",
            "clima_formato": "compacto",
            "clima_intervalo_min": 60,
            "clima_mostrar_hace": True,
            "clima_retry_max": 3,
            "clima_retry_segs": 60,
            "tema": "clasico",
            "alarma_posponer_min": 5,
            "badge_modo": "inline",
            "wc_mostrar": "ver",
            "alarmas_mostrar": "ver",
            "world_clocks": [],
            **SET_CUSTOM_THEME({"make": True}),
        }
        self._config_items = [
            ("tema", "Tema de color", "Apariencia", "choice", THEME_NAMES),
            (
                "custom_color_marco",
                "- Custom: Marco",
                "Apariencia",
                "choice",
                COLOR_LIST,
            ),
            (
                "custom_color_texto",
                "- Custom: Texto",
                "Apariencia",
                "choice",
                COLOR_LIST,
            ),
            (
                "custom_color_clima",
                "- Custom: Clima",
                "Apariencia",
                "choice",
                COLOR_LIST,
            ),
            (
                "custom_color_helpers",
                "- Custom: Helpers",
                "Apariencia",
                "choice",
                COLOR_LIST,
            ),
            ("custom_color_nav", "- Custom: Nav", "Apariencia", "choice", COLOR_LIST),
            ("mostrar_marco", "Mostrar marco", "Apariencia", "bool", None),
            ("mostrar_helpers", "Mostrar ayuda (helpers)", "Apariencia", "bool", None),
            ("mostrar_segundos", "Mostrar segundos", "Reloj", "bool", None),
            ("formato_24h", "Formato 24h", "Reloj", "bool", None),
            (
                "alarma_posponer_min",
                "Posponer alarma (min)",
                "Reloj",
                "choice",
                [1, 2, 5, 10, 15, 20, 30],
            ),
            (
                "badge_modo",
                "Badge de actividad",
                "Reloj",
                "choice",
                ["inline", "detallado"],
            ),
            ("wc_mostrar", "Reloj Mundial", "Reloj", "choice", ["ver", "no ver"]),
            ("alarmas_mostrar", "Alarmas", "Reloj", "choice", ["ver", "no ver"]),
            ("clima_activo", "Mostrar clima", "Clima", "bool", None),
            ("clima_ubicacion", "Ubicación del clima", "Clima", "text", None),
            (
                "clima_intervalo_min",
                "Auto-actualizar clima",
                "Clima",
                "choice",
                [5, 10, 15, 30, 60, 120],
            ),
            (
                "clima_mostrar_hace",
                "Mostrar 'hace N min' en clima",
                "Clima",
                "bool",
                None,
            ),
            (
                "clima_retry_max",
                "Reintentos máx. si falla clima",
                "Clima",
                "choice",
                [1, 2, 3, 5],
            ),
            (
                "clima_retry_segs",
                "Espera entre reintentos",
                "Clima",
                "choice",
                [30, 60, 90, 120],
            ),
            ("sonido", "Sonido (beep) ON/OFF", "Sonido", "bool", None),
            (
                "sonido_modo",
                "Origen del sonido",
                "Sonido",
                "soundmode",
                ["default", "custom"],
            ),
            (
                "sonido_archivo",
                "- Archivo (carpeta default)",
                "Sonido",
                "soundfile",
                None,
            ),
            (
                "sonido_custom_path",
                "- Archivo (elegido a mano)",
                "Sonido",
                "soundbrowser",
                None,
            ),
            ("backup_action", "Crear backup", "Data", "action", "backup"),
            ("restore_action", "Restaurar backup", "Data", "action", "restore"),
            ("log_view_action", "Ver log de errores", "Data", "action", "log_view"),
            (
                "log_export_action",
                "Descargar log de errores",
                "Data",
                "action",
                "log_export",
            ),
        ]
        self._config_tabs = ["Apariencia", "Reloj", "Clima", "Sonido", "Data"]
        self.config_tab_idx = 0
        self.config_selected_idx = 0
        self.config_text_edit = False
        self.config_text_edit_key = None
        self.config_text_edit_value = ""

        self._AUDIOS_DIR = os.path.join(_CONFIG_DIR, "sounds")
        self._sound_files_cache = None
        self._browser_open = False
        self._browser_mode = "sound"
        self._browser_cwd = os.path.expanduser("~")
        self._browser_entries = []
        self._browser_selected_idx = 0
        self._audio_proc = None
        self._audio_lock = threading.Lock()
        self._audio_loop_stop = threading.Event()
        self._help_open = False
        self._log_viewer_open = False
        self._log_viewer_entries = []
        self._log_viewer_idx = 0
        self._log_viewer_scroll = 0

        # FIX: toggle real de pause/play
        self._global_paused = False

        self._weather_lock = threading.Lock()
        self._weather_text = None
        self._weather_ok = False
        self._weather_epoch = None
        self._weather_thread = None
        self._weather_stop = threading.Event()
        self._weather_force = threading.Event()
        self._weather_retry_count = 0
        self._weather_retry_deadline = None

        self._alert = None
        self._alert_blink_counter = 0

        loaded = _load_data()
        if loaded is not None:
            alarms, timers, pomo_patch, todos, saved_config, weather_cache = loaded
            self.alarm_lists = alarms
            if timers:
                self.timers = timers
            for mode in ("work", "shortbreak", "longrest"):
                if mode in pomo_patch:
                    self.pomodoro[mode]["count"] = pomo_patch[mode].get(
                        "count", self.pomodoro[mode]["count"]
                    )
                    self.pomodoro[mode]["left"] = self.pomodoro[mode]["count"]
                    saved_time = pomo_patch[mode].get("time")
                    if saved_time and len(saved_time) == 3:
                        self.pomodoro[mode]["time"] = saved_time
            self.todos = todos
            choice_opts = {
                k: opciones
                for k, _, _, tipo, opciones in self._config_items
                if tipo == "choice"
            }
            for k in self.config:
                if k in saved_config:
                    if k == "sonido_archivo":
                        val = saved_config[k]
                        self.config[k] = (
                            val if (val is None or isinstance(val, str)) else None
                        )
                    elif k == "sonido_modo":
                        val = saved_config[k]
                        self.config[k] = (
                            val if val in ("default", "custom") else "default"
                        )
                    elif k == "sonido_custom_path":
                        val = saved_config[k]
                        self.config[k] = (
                            val if (val is None or isinstance(val, str)) else None
                        )
                    elif k == "clima_ubicacion":
                        val = saved_config[k]
                        self.config[k] = val if isinstance(val, str) else ""
                    elif k == "world_clocks":
                        val = saved_config[k]
                        limpio = []
                        if isinstance(val, list):
                            for item in val:
                                if (
                                    isinstance(item, dict)
                                    and isinstance(item.get("zona"), str)
                                    and isinstance(item.get("apodo"), str)
                                ):
                                    limpio.append(
                                        {"zona": item["zona"], "apodo": item["apodo"]}
                                    )
                        self.config[k] = limpio[:8]
                    elif k in choice_opts:
                        val = saved_config[k]
                        self.config[k] = (
                            val if val in choice_opts[k] else choice_opts[k][0]
                        )
                    elif k == "clima_formato":
                        val = saved_config[k]
                        self.config[k] = val if isinstance(val, str) else "compacto"
                    else:
                        self.config[k] = bool(saved_config[k])
            if self.todos:
                self._todo_next_id = max(t["id"] for t in self.todos) + 1
            self.world_clocks = list(self.config.get("world_clocks", []))
            if weather_cache and weather_cache.get("text"):
                self._weather_text = weather_cache["text"]
                self._weather_ok = bool(weather_cache.get("ok", True))
                self._weather_epoch = weather_cache.get("ts")

        curses.curs_set(0)
        self.stdscr.nodelay(True)
        self.stdscr.keypad(True)
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(_ALERT_BLINK_PAIR_A, curses.COLOR_BLACK, curses.COLOR_RED)
        curses.init_pair(_ALERT_BLINK_PAIR_B, curses.COLOR_RED, curses.COLOR_WHITE)
        curses.init_pair(_HELP_BG_PAIR, curses.COLOR_WHITE, curses.COLOR_BLACK)
        self._apply_theme()

        if self.config.get("clima_activo", False):
            self._weather_start()

        if _log_has_unseen():
            self._show_alert(
                "⚠ Hay errores en el log", "Revisalos en Ajustes [7] → Data → Ver log"
            )

    # ──────────────────────────────────────────
    #  SIZE TIER
    # ──────────────────────────────────────────

    def _size_tier(self):
        h, w = self.stdscr.getmaxyx()
        if h < 8 or w < 40:
            return "micro"
        elif h < 16:
            return "minimum"
        else:
            return "full"

    def _mode_indicator(self):
        if (
            self.alarm_edit_mode
            or self.todo_edit_mode
            or self.timer_edit_mode
            or self.wc_apodo_mode
            or self.config_text_edit
        ):
            return "-- EDICIÓN --"
        if (
            self.alarm_confirm_delete
            or self.todo_confirm_delete
            or self.wc_confirm_delete
        ):
            return "-- CONFIRMAR --"
        if self.wc_picker_open or self._browser_open or self._log_viewer_open:
            return "-- PICKER --"
        return "-- NORMAL --"

    # ──────────────────────────────────────────
    #  MAIN LOOP
    # ──────────────────────────────────────────

    _HJKL_TO_ARROW = {
        ord("h"): curses.KEY_LEFT,
        ord("j"): curses.KEY_DOWN,
        ord("k"): curses.KEY_UP,
        ord("l"): curses.KEY_RIGHT,
    }

    def _typing_text_now(self):
        if self.timer_edit_mode:
            return True
        if self.alarm_edit_mode and self.alarm_edit_field == 0:
            return True
        if self.todo_edit_mode and self.todo_edit_field == 1:
            return True
        if self.wc_apodo_mode:
            return True
        if self.wc_picker_open and self.wc_picker_filter_active:
            return True
        if self.config_text_edit:
            return True
        return False

    def run(self):
        while self.running:
            if self._alert is None:
                perr = pop_persistence_error()
                if perr:
                    self._show_alert("⚠ Persistencia", perr)

            key = self.stdscr.getch()
            if key in self._HJKL_TO_ARROW and not self._typing_text_now():
                key = self._HJKL_TO_ARROW[key]

            # ── Alert modal ──
            if self._alert is not None:
                if key in (ord(" "), ord("\n"), 10, 13):
                    ref = self._alert.get("alarm_ref")
                    if ref is not None and ref.get("tipo") == "tarea":
                        ref["recordarme"] = False
                        self._todo_save()
                    # FIX: Timer completado → reiniciar al cerrar con Space/Enter
                    elif ref is not None and "remaining" in ref and "time" in ref:
                        ref["remaining"] = hms_to_secs(*ref["time"])
                        ref["started"] = False
                        ref["last_tick"] = None
                    self._alert = None
                    self._kill_audio()
                elif key == 27:
                    self._alert = None
                    self._kill_audio()
                elif key in (ord("p"), ord("P")) and self._alert.get("posponable"):
                    self._postpone_alert()
                self._tick_alert()
                self._draw_alert()
                time.sleep(0.05)
                continue

            # ── Browser ──
            if self._browser_open:
                if key != -1:
                    self._input_browser(key)
                curses.flushinp()
                self._update_view()
                time.sleep(0.05)
                continue

            # ── Log viewer ──
            if self._log_viewer_open:
                if key != -1:
                    self._input_log_viewer(key)
                curses.flushinp()
                self._update_view()
                time.sleep(0.05)
                continue

            # ── Config text edit ──
            if self.config_text_edit:
                if key != -1:
                    self._input_config_text(key)
                self._tick_pomodoro()
                self._tick_timers()
                self._tick_todo_alarms()
                self._check_alarms()
                self._check_snoozes()
                self._update_view()
                time.sleep(0.05)
                continue

            # ── Editores de texto libre ──
            en_modo_texto_libre = (
                self.alarm_edit_mode or self.todo_edit_mode or self.timer_edit_mode
            )
            if en_modo_texto_libre:
                if key != -1:
                    self._handle_input(key)
                self._tick_pomodoro()
                self._tick_timers()
                self._tick_todo_alarms()
                self._check_alarms()
                self._check_snoozes()
                self._update_view()
                time.sleep(0.05)
                continue

            # ── Confirmación borrado ToDo ──
            if self.todo_confirm_delete:
                if key != -1:
                    self._input_todo(key)
                self._tick_pomodoro()
                self._tick_timers()
                self._tick_todo_alarms()
                self._check_alarms()
                self._check_snoozes()
                self._update_view()
                time.sleep(0.05)
                continue

            # ── Teclas globales ──
            if key == ord("q"):
                self.running = False
                _save_data(
                    self.alarm_lists,
                    self.timers,
                    self.pomodoro,
                    self.todos,
                    self.config,
                )
                continue

            if key == ord("o"):
                self._notes_panel_open = not self._notes_panel_open
                self._notes_scroll = 0
                self._notes_selected_idx = 0
                self._notes_expanded = set()
                curses.flushinp()
                self._update_view()
                time.sleep(0.05)
                continue

            if (
                key == 27
                and self._notes_panel_open
                and not (self.todo_edit_mode or self.todo_confirm_delete)
            ):
                self._notes_panel_open = False
                curses.flushinp()
                self._update_view()
                time.sleep(0.05)
                continue

            # Panel de notas abierto
            if self._notes_panel_open and not (
                self.todo_edit_mode or self.todo_confirm_delete
            ):
                notas_idx = [i for i, _ in enumerate(self.todos)]
                if key == curses.KEY_DOWN:
                    if notas_idx:
                        self._notes_selected_idx = min(
                            self._notes_selected_idx + 1, len(notas_idx) - 1
                        )
                    curses.flushinp()
                    self._update_view()
                    time.sleep(0.05)
                    continue
                if key == curses.KEY_UP:
                    if notas_idx:
                        self._notes_selected_idx = max(self._notes_selected_idx - 1, 0)
                    curses.flushinp()
                    self._update_view()
                    time.sleep(0.05)
                    continue
                if key in (ord("\n"), 10, 13) and notas_idx:
                    real_idx = notas_idx[self._notes_selected_idx]
                    item_id = self.todos[real_idx]["id"]
                    if item_id in self._notes_expanded:
                        self._notes_expanded.discard(item_id)
                    else:
                        self._notes_expanded.add(item_id)
                    curses.flushinp()
                    self._update_view()
                    time.sleep(0.05)
                    continue
                if key == ord("n"):
                    self._input_todo(ord("n"))
                    self.temp_todo_tipo = "nota"
                    curses.flushinp()
                    self._update_view()
                    time.sleep(0.05)
                    continue
                if key == ord("e") and notas_idx:
                    real_idx = notas_idx[self._notes_selected_idx]
                    self.todo_selected_idx = real_idx
                    self._input_todo(ord("e"))
                    curses.flushinp()
                    self._update_view()
                    time.sleep(0.05)
                    continue
                if key == ord("d") and notas_idx:
                    real_idx = notas_idx[self._notes_selected_idx]
                    self.todo_selected_idx = real_idx
                    self._input_todo(ord("d"))
                    curses.flushinp()
                    self._update_view()
                    time.sleep(0.05)
                    continue
                if key == ord(" ") and notas_idx:
                    real_idx = notas_idx[self._notes_selected_idx]
                    t = self.todos[real_idx]
                    if t.get("tipo", "tarea") == "tarea":
                        _todo_set_done(t, not _todo_is_done(t))
                        self._todo_save()
                    curses.flushinp()
                    self._update_view()
                    time.sleep(0.05)
                    continue

            if key == ord("?"):
                self._help_open = not self._help_open
                curses.flushinp()
                self._update_view()
                time.sleep(0.05)
                continue

            if self._help_open:
                if key != -1:
                    self._help_open = False
                curses.flushinp()
                self._update_view()
                time.sleep(0.05)
                continue

            # FIX: Esc toggle real con _global_paused
            modo_editor_o_confirm_activo = (
                self.alarm_edit_mode
                or self.alarm_confirm_delete
                or self.timer_edit_mode
                or self.todo_edit_mode
                or self.todo_confirm_delete
                or self.wc_picker_open
                or self.wc_apodo_mode
                or self.wc_confirm_delete
            )
            if key == 27 and not modo_editor_o_confirm_activo:
                self._global_pause_play()
                curses.flushinp()
                self._update_view()
                time.sleep(0.05)
                continue

            # Cambio de vista 0-7
            if (
                key
                in (
                    ord("0"),
                    ord("1"),
                    ord("2"),
                    ord("3"),
                    ord("4"),
                    ord("5"),
                    ord("6"),
                    ord("7"),
                )
                and not self.wc_apodo_mode
            ):
                self.current_view = int(chr(key))
                curses.flushinp()
                self._update_view()
                time.sleep(0.05)
                continue

            if key != -1:
                self._handle_input(key)

            self._tick_pomodoro()
            self._tick_timers()
            self._tick_todo_alarms()
            self._check_alarms()
            self._check_snoozes()
            self._update_view()
            time.sleep(0.05)

    # ──────────────────────────────────────────
    #  INPUT DISPATCH
    # ──────────────────────────────────────────

    def _handle_input(self, key):
        if (
            self._notes_panel_open
            and self.current_view != 6
            and (self.todo_edit_mode or self.todo_confirm_delete)
        ):
            self._input_todo(key)
        elif self.current_view == 0:
            self._input_dashboard(key)
        elif self.current_view == 1:
            self._input_clock(key)
        elif self.current_view == 2:
            self._input_alarms(key)
        elif self.current_view == 3:
            self._input_pomodoro(key)
        elif self.current_view == 4:
            self._input_timer(key)
        elif self.current_view == 5:
            self._input_stopwatch(key)
        elif self.current_view == 6:
            self._input_todo(key)
        elif self.current_view == 7:
            self._input_config(key)

        en_modo_texto_libre = (
            self.alarm_edit_mode
            or self.todo_edit_mode
            or self.timer_edit_mode
            or self.wc_apodo_mode
            or (self.wc_picker_open and self.wc_picker_filter_active)
            or self.config_text_edit
        )
        TECLAS_DE_ACCION_TEXTO = {
            ord("n"),
            ord("e"),
            ord("d"),
            ord("u"),
            ord("y"),
            ord("Y"),
            ord("f"),
            ord("x"),
        }
        if key == 27:
            curses.flushinp()
        elif key in TECLAS_DE_ACCION_TEXTO and not en_modo_texto_libre:
            curses.flushinp()

    # ──────────────────────────────────────────
    #  TICKS
    # ──────────────────────────────────────────

    def _tick_pomodoro(self):
        p = self.pomodoro
        if not p["is_active"]:
            self._pomo_last_tick = None
            return
        now = time.monotonic()
        if self._pomo_last_tick is None:
            self._pomo_last_tick = now
            return
        elapsed = now - self._pomo_last_tick
        self._pomo_last_tick = now
        p["timer_value"] = max(0, p["timer_value"] - elapsed)
        if p["timer_value"] <= 0:
            p["is_active"] = False
            self._pomo_last_tick = None
            self._pomo_advance()

    def _pomo_advance(self):
        p = self.pomodoro
        seq = self._build_pomo_sequence()
        if not seq:
            return
        prev_mode = seq[p["cycle_idx"]]
        p["cycle_idx"] = (p["cycle_idx"] + 1) % len(seq)
        next_mode = seq[p["cycle_idx"]]
        p["current_mode"] = next_mode
        t = p[next_mode]["time"]
        p["timer_value"] = hms_to_secs(*t)
        next_label = {
            "work": "WORK",
            "shortbreak": "Descanso corto",
            "longrest": "Descanso largo",
        }[next_mode]
        h, m, s = t
        dur = f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"
        if prev_mode == "work":
            title = "💪 Sesión completada"
        elif prev_mode == "shortbreak":
            title = "☕ Descanso terminado"
        else:
            title = "🌿 Descanso largo terminado"
        self._show_alert(title, f"→ {next_label}  ({dur})")

    def _build_pomo_sequence(self):
        p = self.pomodoro
        key = (p["work"]["count"], p["shortbreak"]["count"], p["longrest"]["count"])
        if self._pomo_seq_cache and self._pomo_seq_cache[0] == key:
            return self._pomo_seq_cache[1]
        seq = []
        w, sb, lr = p["work"]["count"], p["shortbreak"]["count"], p["longrest"]["count"]
        for _ in range(lr):
            for i in range(w):
                seq.append("work")
                if i < sb:
                    seq.append("shortbreak")
            seq.append("longrest")
        if not seq:
            seq = ["work", "longrest"]
        self._pomo_seq_cache = (key, seq)
        return seq

    def _tick_timers(self):
        now = time.monotonic()
        for t in self.timers:
            if not t["active"]:
                t["last_tick"] = None
                continue
            if t["last_tick"] is None:
                t["last_tick"] = now
                continue
            elapsed = now - t["last_tick"]
            t["last_tick"] = now
            t["remaining"] = max(0.0, t["remaining"] - elapsed)
            if t["remaining"] <= 0:
                t["active"] = False
                t["last_tick"] = None
                h, m, s = t["time"]
                dur = f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"
                # FIX: pasar alarm_ref=t para que Space/Enter reinicie el timer
                self._show_alert(f"⏱  {t['name']}", f"Completado — {dur}", alarm_ref=t)

    # ──────────────────────────────────────────
    #  ALARMAS
    # ──────────────────────────────────────────

    def _check_alarms(self):
        now = datetime.datetime.now()
        weekday = now.weekday()
        current_minute = (now.hour, now.minute)
        if self._last_alarm_minute != current_minute:
            self._last_alarm_minute = current_minute
            self._alarm_fired_this_minute = set()
        for i, a in enumerate(self.alarm_lists):
            dias = _repeat_days_normalize(a.get("repeat_days"))
            day_ok = not dias or weekday in dias
            is_match = a["hora"] == now.hour and a["minutos"] == now.minute and day_ok
            if a["status"] == "activado" and is_match:
                if i not in self._alarm_fired_this_minute:
                    self._alarm_fired_this_minute.add(i)
                    self._show_alert(
                        f"◷  {a['nombre']}",
                        f"{a['hora']:02d}:{a['minutos']:02d} — ¡Alarma!",
                        posponable=True,
                        alarm_ref=a,
                    )
                    a["status"] = "disparada"
            elif a["status"] == "disparada" and not is_match:
                if dias:
                    a["status"] = "activado"
                else:
                    a["status"] = "desactivado"

    def _check_snoozes(self):
        now = datetime.datetime.now()
        to_remove = []
        for i, s in enumerate(self.snooze_alarms):
            if s["hora"] == now.hour and s["minutos"] == now.minute:
                if not s.get("_fired"):
                    s["_fired"] = True
                    self._show_alert(
                        f"◷  {s['nombre']} (pospuesta)",
                        f"{s['hora']:02d}:{s['minutos']:02d} — ¡Alarma pospuesta!",
                        posponable=True,
                        alarm_ref=s,
                    )
                    to_remove.append(i)
        for i in reversed(to_remove):
            self.snooze_alarms.pop(i)

    def _postpone_alert(self):
        if self._alert is None or not self._alert.get("posponable"):
            return
        mins = int(self.config.get("alarma_posponer_min", 5))
        ref = self._alert.get("alarm_ref")
        nombre = "Alarma"
        if ref is not None:
            nombre = ref.get("nombre", ref.get("texto", "Alarma"))[:20]
        nueva = datetime.datetime.now() + datetime.timedelta(minutes=mins)
        self.snooze_alarms.append(
            {
                "hora": nueva.hour,
                "minutos": nueva.minute,
                "nombre": nombre,
                "creado": time.time(),
            }
        )
        self._alert = None
        self._kill_audio()

    # ──────────────────────────────────────────
    #  TODO ALARMS
    # ──────────────────────────────────────────

    def _tick_todo_alarms(self):
        now = datetime.datetime.now()
        weekday = now.weekday()
        current_minute = (now.hour, now.minute)
        if self._last_todo_minute != current_minute:
            self._last_todo_minute = current_minute
            self._todo_fired_this_minute = set()
        for i, t in enumerate(self.todos):
            if not t.get("recordarme"):
                continue
            if i in self._todo_fired_this_minute:
                continue
            dias = _repeat_days_normalize(t.get("repeat_days"))
            if dias:
                is_match = (
                    weekday in dias
                    and t.get("alarma_hora") == now.hour
                    and t.get("alarma_min") == now.minute
                )
                if t.get("_disparada", False):
                    if not is_match:
                        t["_disparada"] = False
                    continue
            else:
                if t.get("_disparada", False):
                    continue
                is_match = (
                    t.get("alarma_anio") == now.year
                    and t.get("alarma_mes") == now.month
                    and t.get("alarma_dia") == now.day
                    and t.get("alarma_hora") == now.hour
                    and t.get("alarma_min") == now.minute
                )
            if is_match:
                self._todo_fired_this_minute.add(i)
                t["_disparada"] = True
                dias_semana = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
                meses_corto = [
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
                if dias:
                    detalle = f"{dias_semana[weekday]}  {t['alarma_hora']:02d}:{t['alarma_min']:02d} ({_repeat_days_str(dias)})"
                else:
                    try:
                        dia_nombre = dias_semana[
                            datetime.date(
                                t["alarma_anio"], t["alarma_mes"], t["alarma_dia"]
                            ).weekday()
                        ]
                        mes_nombre = meses_corto[t["alarma_mes"] - 1]
                    except (ValueError, IndexError):
                        dia_nombre, mes_nombre = "", ""
                    detalle = f"{dia_nombre} {t['alarma_dia']} {mes_nombre}  {t['alarma_hora']:02d}:{t['alarma_min']:02d}"
                self._show_alert(
                    f"▤  {t['texto'][:30]}", detalle, posponable=True, alarm_ref=t
                )

    # ──────────────────────────────────────────
    #  ALERT OVERLAY
    # ──────────────────────────────────────────

    def _resolve_sound_path(self):
        if self.config.get("sonido_modo") == "custom":
            path = self.config.get("sonido_custom_path")
            return path if path and os.path.exists(path) else None
        archivo = self.config.get("sonido_archivo")
        return os.path.join(self._AUDIOS_DIR, archivo) if archivo else None

    def _kill_audio(self):
        self._audio_loop_stop.set()
        with self._audio_lock:
            if self._audio_proc is not None:
                try:
                    self._audio_proc.terminate()
                except (ProcessLookupError, OSError):
                    pass
                self._audio_proc = None

    def _audio_loop(self):
        sound_path = self._resolve_sound_path()
        while not self._audio_loop_stop.is_set() and self._alert is not None:
            proc = try_beep(sound_path)
            if proc is None:
                for _ in range(30):
                    if self._audio_loop_stop.is_set() or self._alert is None:
                        return
                    time.sleep(0.1)
                continue
            with self._audio_lock:
                self._audio_proc = proc
            while not self._audio_loop_stop.is_set() and self._alert is not None:
                if proc.poll() is not None:
                    break
                time.sleep(0.1)
            if self._audio_loop_stop.is_set() or self._alert is None:
                try:
                    proc.terminate()
                except (ProcessLookupError, OSError):
                    pass
                return

    def _show_alert(self, title, msg, posponable=False, alarm_ref=None):
        self._kill_audio()
        self._alert = {
            "title": title,
            "msg": msg,
            "blink_state": 0,
            "posponable": posponable,
            "alarm_ref": alarm_ref,
        }
        self._alert_blink_counter = 0
        if self.config.get("sonido", True):
            self._audio_loop_stop.clear()
            threading.Thread(target=self._audio_loop, daemon=True).start()

    def _tick_alert(self):
        if self._alert is None:
            return
        self._alert_blink_counter += 1
        if self._alert_blink_counter >= 6:
            self._alert_blink_counter = 0
            self._alert["blink_state"] ^= 1

    def _draw_alert(self):
        if self._alert is None:
            return
        h, w = self.stdscr.getmaxyx()
        pair = (
            curses.color_pair(_ALERT_BLINK_PAIR_A)
            if self._alert["blink_state"]
            else curses.color_pair(_ALERT_BLINK_PAIR_B)
        )
        attr = pair | curses.A_BOLD
        title = self._alert["title"]
        msg = self._alert["msg"]
        hint = "[ SPACE / ENTER para continuar ]"
        posponable = self._alert.get("posponable", False)
        mins = int(self.config.get("alarma_posponer_min", 5))
        hint2 = f"[ P → Posponer {mins} min ]" if posponable else ""
        box_w = max(len(title), len(msg), len(hint), len(hint2)) + 6
        box_h = 9 if hint2 else 7
        sy = (h - box_h) // 2
        sx = (w - box_w) // 2
        for row in range(box_h):
            self.stdscr.addstr(sy + row, sx, " " * box_w, attr)
        self._centered_str(sy + 1, sx, box_w, title, attr)
        self._centered_str(sy + 3, sx, box_w, msg, attr)
        self._centered_str(sy + 5, sx, box_w, hint, attr)
        if hint2:
            self._centered_str(sy + 7, sx, box_w, hint2, attr)

    # ──────────────────────────────────────────
    #  DRAWING HELPERS
    # ──────────────────────────────────────────

    def _centered_str(self, y, x_start, width, text, attr=0):
        h, w = self.stdscr.getmaxyx()
        cx = x_start + (width - len(text)) // 2
        cx = max(0, min(cx, w - len(text) - 1))
        if 0 <= y < h:
            try:
                self.stdscr.addstr(y, cx, text, attr)
            except curses.error:
                pass

    def _apply_theme(self):
        nombre = self.config.get("tema", "clasico")
        paleta = (
            SET_CUSTOM_THEME(self.config)
            if nombre == "custom"
            else THEMES.get(nombre, THEMES["clasico"])
        )
        curses.init_pair(PAIR_MARCO, paleta["marco"], -1)
        curses.init_pair(PAIR_TEXTO, paleta["texto"], -1)
        curses.init_pair(PAIR_CLIMA, paleta["clima"], -1)
        curses.init_pair(PAIR_HELPERS, paleta["helpers"], -1)
        curses.init_pair(PAIR_NAV, paleta["nav"], -1)

    def _sound_ensure_dir(self):
        try:
            os.makedirs(self._AUDIOS_DIR, exist_ok=True)
        except OSError:
            return
        try:
            ya_tiene_algo = any(
                f.lower().endswith(_SOUND_EXTS) for f in os.listdir(self._AUDIOS_DIR)
            )
        except OSError:
            return
        if ya_tiene_algo:
            return
        for src in _BEEP_SOUNDS:
            if os.path.exists(src):
                try:
                    dst = os.path.join(self._AUDIOS_DIR, os.path.basename(src))
                    with open(src, "rb") as fsrc, open(dst, "wb") as fdst:
                        fdst.write(fsrc.read())
                except OSError:
                    pass
                break

    def _sound_list_files(self, force_refresh=False):
        if self._sound_files_cache is not None and not force_refresh:
            return self._sound_files_cache
        self._sound_ensure_dir()
        try:
            archivos = sorted(
                f
                for f in os.listdir(self._AUDIOS_DIR)
                if f.lower().endswith(_SOUND_EXTS)
            )
        except OSError:
            archivos = []
        self._sound_files_cache = archivos
        return archivos

    @staticmethod
    def _display_width(s):
        width = 0
        for ch in s:
            cp = ord(ch)
            if (
                0x1F000 <= cp <= 0x1FFFF
                or 0x2600 <= cp <= 0x27BF
                or 0x1100 <= cp <= 0x11FF
                or 0x2E80 <= cp <= 0x9FFF
                or 0xAC00 <= cp <= 0xD7AF
            ):
                width += 2
            else:
                width += 1
        return width

    def _draw_box(self, sy, sx, bh, bw, title=""):
        attr = curses.color_pair(PAIR_MARCO)
        h, w = self.stdscr.getmaxyx()

        def safe(y, x, s, a=0):
            if 0 <= y < h and 0 <= x < w - 1:
                try:
                    self.stdscr.addstr(y, x, s[: w - x - 1], a)
                except curses.error:
                    pass

        safe(sy, sx, "┌" + "─" * (bw - 2) + "┐", attr)
        safe(sy + bh - 1, sx, "└" + "─" * (bw - 2) + "┘", attr)
        for r in range(1, bh - 1):
            safe(sy + r, sx, "│", attr)
            safe(sy + r, sx + bw - 1, "│", attr)
        if title:
            ts = f"[ {title} ]"
            vis_w = self._display_width(ts)
            tx = sx + (bw - vis_w) // 2
            safe(sy, tx, ts, attr | curses.A_BOLD)

    def _draw_frame(
        self, title, rows, helper_lines=None, weather_line=None, row_attrs=None
    ):
        """Layout v6.1:
        H=0: clima (W=0, izquierda) — solo en vistas que lo tienen
        H=1..end-2: contenido centrado V+H
        H=end (sh-1): -- MODO -- [nav vistas]
        """
        self.stdscr.erase()
        sh, sw = self.stdscr.getmaxyx()
        tier = self._size_tier()

        # ── H=0: clima en W=center ──
        if weather_line and tier != "micro":
            wx = max(0, (sw - len(weather_line)) // 2)
            try:
                self.stdscr.addstr(
                    0, wx, weather_line[: sw - 1], curses.color_pair(PAIR_CLIMA)
                )
            except curses.error:
                pass

        # ── Calcular box ──
        helper_lines = helper_lines if self.config.get("mostrar_helpers", True) else []
        helper_lines = helper_lines or []
        all_widths = (
            [len(r) for r in rows]
            + [len(h) for h in helper_lines]
            + [len(title) + 8, 44]
        )
        box_w = min(max(all_widths) + 6, sw - 2)
        box_h = len(rows) + 4
        total_h = box_h + (len(helper_lines) + 1 if helper_lines else 0)
        # Centrar entre H=1 y H=end-1 (reservando fila 0 y última fila)
        sy = max(1, (sh - 1 - total_h) // 2)
        sx = max(0, (sw - box_w) // 2)

        # ── Box + contenido ──
        if self.config.get("mostrar_marco", True):
            self._draw_box(sy, sx, box_h, box_w, title)
            content_y0 = sy + 2
        else:
            self._centered_str(
                sy,
                sx,
                box_w,
                f"[ {title} ]",
                curses.color_pair(PAIR_MARCO) | curses.A_BOLD,
            )
            content_y0 = sy + 2

        for i, row in enumerate(rows):
            attr = None
            if row_attrs is not None and i < len(row_attrs):
                attr = row_attrs[i]
            self._centered_str(
                content_y0 + i,
                sx,
                box_w,
                row,
                attr if attr is not None else curses.color_pair(PAIR_TEXTO),
            )

        # ── Helpers debajo del box ──
        for j, hline in enumerate(helper_lines):
            hy = sy + box_h + j + 1
            if 0 <= hy < sh:
                hx = sx + (box_w - len(hline)) // 2
                hx = max(0, hx)
                try:
                    self.stdscr.addstr(hy, hx, hline, curses.color_pair(PAIR_HELPERS))
                except curses.error:
                    pass

        # ── Badge de actividad (encima del footer) ──
        fy = sh - 1  # FIX: última fila real
        modo_badge = self.config.get("badge_modo", "inline")
        pending = [
            t
            for t in self.todos
            if not _todo_is_done(t)
            and t.get("tipo", "tarea") == "tarea"
            and t.get("recordarme", False)
        ]
        total_tasks = len([t for t in self.todos if t.get("tipo", "tarea") == "tarea"])
        done_tasks = len(
            [
                t
                for t in self.todos
                if t.get("tipo", "tarea") == "tarea" and _todo_is_done(t)
            ]
        )
        alarmas_en_badge = self.config.get("alarmas_mostrar", "ver") == "no ver"
        alarmas_activas = (
            sorted(
                [a for a in self.alarm_lists if a["status"] == "activado"],
                key=lambda a: (a["hora"], a["minutos"]),
            )
            if alarmas_en_badge
            else []
        )

        if modo_badge == "detallado":
            stack = []
            if self.stopwatch.get("active") and self.current_view != 5:
                e = self._sw_elapsed()
                hh, mm, ss = secs_to_hms(e)
                cs = int((e - int(e)) * 100)
                stack.append(f"◷ Crono  {hh:02d}:{mm:02d}:{ss:02d}.{cs:02d}")
            shown_timers = (
                [t for t in self.timers if t.get("active")]
                if self.current_view != 4
                else []
            )
            for t in shown_timers:
                hh, mm, ss = secs_to_hms(t["remaining"])
                stack.append(f"⏱ {t['name']}  {hh:02d}:{mm:02d}:{ss:02d}")
            if self.pomodoro["is_active"] and self.current_view != 3:
                modo_label = {
                    "work": "WORK",
                    "shortbreak": "SHORT",
                    "longrest": "LONG",
                }[self.pomodoro["current_mode"]]
                hh, mm, ss = secs_to_hms(self.pomodoro["timer_value"])
                stack.append(f"◆ Pomo:{modo_label}  {hh:02d}:{mm:02d}")
            if pending and self.current_view != 6:
                stack.append(f"▤ {done_tasks}/{total_tasks} ToDo")
            if alarmas_activas:
                shown_a = alarmas_activas[:3]
                for a in shown_a:
                    rep = _repeat_days_str(a.get("repeat_days"))
                    rep_txt = "" if rep == "una vez" else f" ↻{rep}"
                    stack.append(
                        f"◷ {a['nombre']} {a['hora']:02d}:{a['minutos']:02d}{rep_txt}"
                    )
                extra_a = len(alarmas_activas) - len(shown_a)
                if extra_a > 0:
                    stack.append(f"◷ +{extra_a} más")
            for i, line in enumerate(stack):
                by = fy - 2 - i
                bx = (sw - len(line) - 4) // 2
                if 0 <= by < sh:
                    try:
                        self.stdscr.addstr(
                            by,
                            max(0, bx),
                            f"[ {line} ]",
                            curses.color_pair(PAIR_HELPERS) | curses.A_BOLD,
                        )
                    except curses.error:
                        pass
        else:
            partes = []
            if self.pomodoro["is_active"] and self.current_view != 3:
                modo_label = {
                    "work": "WORK",
                    "shortbreak": "SHORT",
                    "longrest": "LONG",
                }[self.pomodoro["current_mode"]]
                partes.append(f"◆ Pomo:{modo_label}")
            running_timers = (
                [t for t in self.timers if t.get("active")]
                if self.current_view != 4
                else []
            )
            if running_timers:
                shown = running_timers[:3]
                names = " · ".join(
                    f"{t['name']} {secs_to_hms(t['remaining'])[0]:02d}:{secs_to_hms(t['remaining'])[1]:02d}"
                    for t in shown
                )
                extra = (
                    f" +{len(running_timers) - 3}" if len(running_timers) > 3 else ""
                )
                partes.append(f"⏱ {names}{extra}")
            if self.stopwatch.get("active") and self.current_view != 5:
                partes.append("◷ Crono")
            if pending and self.current_view != 6:
                partes.append(f"▤ {done_tasks}/{total_tasks} ToDo")
            if alarmas_activas:
                shown_a = alarmas_activas[:3]
                nombres_a = " · ".join(
                    f"{a['hora']:02d}:{a['minutos']:02d} {a['nombre']}" for a in shown_a
                )
                extra_a = (
                    f" +{len(alarmas_activas) - 3}" if len(alarmas_activas) > 3 else ""
                )
                partes.append(f"◷ {nombres_a}{extra_a}")
            if partes:
                badge = "[ " + "  ·  ".join(partes) + " ]"
                by = fy - 1
                bx = (sw - len(badge)) // 2
                if 0 <= by < sh:
                    try:
                        self.stdscr.addstr(
                            by,
                            max(0, bx),
                            badge,
                            curses.color_pair(PAIR_HELPERS) | curses.A_BOLD,
                        )
                    except curses.error:
                        pass

        # ── H=end: modo + navegación ──
        if tier != "micro":
            mode_ind = self._mode_indicator()
            if tier == "minimum":
                footer = f"{mode_ind}  [0-7 q]"
            else:
                footer = f"{mode_ind}  [0:Dash 1:Reloj 2:Alarm 3:Pomo 4:Timer 5:Crono 6:ToDo 7:Conf q]"
            if 0 <= fy < sh:
                try:
                    self.stdscr.addstr(
                        fy,
                        max(0, (sw - len(footer)) // 2),
                        footer,
                        curses.color_pair(PAIR_NAV),
                    )
                except curses.error:
                    pass

        return sy, sx, box_w

    def _draw_micro(self):
        self.stdscr.erase()
        sh, sw = self.stdscr.getmaxyx()
        now = datetime.datetime.now()
        hora_str = self._format_clock_time(now)
        y = sh // 2
        x = max(0, (sw - len(hora_str)) // 2)
        try:
            self.stdscr.addstr(
                y, x, hora_str, curses.color_pair(PAIR_TEXTO) | curses.A_BOLD
            )
        except curses.error:
            pass
        self.stdscr.refresh()

    # ──────────────────────────────────────────
    #  VIEW DISPATCHER
    # ──────────────────────────────────────────

    def _update_view(self):
        tier = self._size_tier()
        if tier == "micro":
            self._draw_micro()
            return
        if self.current_view == 0:
            self._draw_dashboard()
        elif self.current_view == 1:
            self._draw_clock()
        elif self.current_view == 2:
            self._draw_alarms()
        elif self.current_view == 3:
            self._draw_pomodoro()
        elif self.current_view == 4:
            self._draw_timers()
        elif self.current_view == 5:
            self._draw_stopwatch()
        elif self.current_view == 6:
            self._draw_todo()
        elif self.current_view == 7:
            self._draw_config()

        if self._notes_panel_open and self.current_view != 6:
            self._draw_notes_panel()
        if self.todo_edit_mode or self.todo_confirm_delete:
            self._draw_todo()
        if self._browser_open:
            self._draw_browser()
        if self._log_viewer_open:
            self._draw_log_viewer()
        if self._help_open:
            self._draw_help_overlay()
        self.stdscr.refresh()

    # ──────────────────────────────────────────
    #  VIEW 0 — DASHBOARD (fecha inline + sin age)
    # ──────────────────────────────────────────

    def _input_dashboard(self, key):
        pass

    def _draw_dashboard(self):
        tier = self._size_tier()
        now = datetime.datetime.now()
        dias = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
        meses = [
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
        hora_str = self._format_clock_time(now)
        now_str = f"{dias[now.weekday()]} {now.day} {meses[now.month - 1]}  {hora_str}"

        if tier == "minimum":
            rows = [now_str]
            prox_alarmas = sorted(
                [a for a in self.alarm_lists if a["status"] == "activado"],
                key=lambda a: (a["hora"], a["minutos"]),
            )
            if prox_alarmas:
                a = prox_alarmas[0]
                rows.append(f"◷ {a['nombre']} {a['hora']:02d}:{a['minutos']:02d}")
            self._draw_frame(
                "◈ Dashboard",
                rows,
                weather_line=self._weather_display_line(show_age=False),
            )
            return

        rows = [now_str]
        weather = self._weather_display_line(show_age=False)
        if weather:
            rows.append(weather)

        prox_alarmas = sorted(
            [a for a in self.alarm_lists if a["status"] == "activado"],
            key=lambda a: (a["hora"], a["minutos"]),
        )
        if prox_alarmas:
            a = prox_alarmas[0]
            rep = _repeat_days_str(a.get("repeat_days"))
            rep_txt = f" ↻{rep}" if rep != "una vez" else ""
            now_dt = datetime.datetime.now()
            alarm_dt = now_dt.replace(
                hour=a["hora"], minute=a["minutos"], second=0, microsecond=0
            )
            if alarm_dt <= now_dt:
                alarm_dt += datetime.timedelta(days=1)
            diff = alarm_dt - now_dt
            h_rest, m_rest = divmod(int(diff.total_seconds()) // 60, 60)
            rows.append(
                f"◷ Próx: {a['nombre']} {a['hora']:02d}:{a['minutos']:02d}{rep_txt}  (en {h_rest}h {m_rest}m)"
            )

        if self.pomodoro["is_active"]:
            modo_label = {"work": "WORK", "shortbreak": "SHORT", "longrest": "LONG"}[
                self.pomodoro["current_mode"]
            ]
            hh, mm, ss = secs_to_hms(self.pomodoro["timer_value"])
            rows.append(f"◆ Pomo:{modo_label}  {hh:02d}:{mm:02d}:{ss:02d}")

        running_timers = [t for t in self.timers if t.get("active")]
        for t in running_timers[:3]:
            hh, mm, ss = secs_to_hms(t["remaining"])
            rows.append(f"⏱ {t['name']}  {hh:02d}:{mm:02d}:{ss:02d}")
        if len(running_timers) > 3:
            rows.append(f"⏱ +{len(running_timers) - 3} más")

        if self.stopwatch.get("active"):
            e = self._sw_elapsed()
            hh, mm, ss = secs_to_hms(e)
            cs = int((e - int(e)) * 100)
            rows.append(f"◷ Crono  {hh:02d}:{mm:02d}:{ss:02d}.{cs:02d}")

        total_tasks = len([t for t in self.todos if t.get("tipo", "tarea") == "tarea"])
        done_tasks = len(
            [
                t
                for t in self.todos
                if t.get("tipo", "tarea") == "tarea" and _todo_is_done(t)
            ]
        )
        pending = total_tasks - done_tasks
        if pending > 0:
            rows.append(f"▤ {pending} tareas pendientes ({done_tasks}/{total_tasks})")

        if self.snooze_alarms:
            rows.append(f"💤 {len(self.snooze_alarms)} pospuesta(s)")

        self._draw_frame("◈ Dashboard", rows)

    # ──────────────────────────────────────────
    #  VIEW 1 — RELOJ
    # ──────────────────────────────────────────

    def _format_clock_time(self, now):
        if self.config.get("formato_24h", True):
            fmt = "%H:%M:%S" if self.config.get("mostrar_segundos", True) else "%H:%M"
        else:
            fmt = (
                "%I:%M:%S %p"
                if self.config.get("mostrar_segundos", True)
                else "%I:%M %p"
            )
        return now.strftime(fmt)

    def _input_clock(self, key):
        if self.wc_picker_open:
            if self.wc_picker_filter_active:
                if key == 27:
                    self.wc_picker_filter_active = False
                    self.wc_picker_filter_text = ""
                    self._wc_refresh_picker_list()
                elif key in (curses.KEY_BACKSPACE, 127, 8):
                    self.wc_picker_filter_text = self.wc_picker_filter_text[:-1]
                    self._wc_refresh_picker_list()
                elif key in (ord("\n"), 10, 13):
                    self._wc_picker_confirm_zone()
                elif 32 <= key <= 126:
                    self.wc_picker_filter_text += chr(key)
                    self._wc_refresh_picker_list()
                return
            if key in (curses.KEY_UP, curses.KEY_DOWN) and self.wc_picker_list:
                n = len(self.wc_picker_list)
                step = 1 if key == curses.KEY_DOWN else -1
                self.wc_picker_idx = (self.wc_picker_idx + step) % n
                MAX_VIS = 10
                if self.wc_picker_idx < self.wc_picker_scroll:
                    self.wc_picker_scroll = self.wc_picker_idx
                elif self.wc_picker_idx >= self.wc_picker_scroll + MAX_VIS:
                    self.wc_picker_scroll = self.wc_picker_idx - MAX_VIS + 1
                if self.wc_picker_idx == 0:
                    self.wc_picker_scroll = 0
                elif self.wc_picker_idx == n - 1:
                    self.wc_picker_scroll = max(0, n - MAX_VIS)
            elif key == ord("f"):
                self.wc_picker_filter_active = True
                self.wc_picker_filter_text = ""
            elif key in (ord("\n"), 10, 13):
                self._wc_picker_confirm_zone()
            elif key == 27:
                self._wc_cancel_all()
            return

        if self.wc_apodo_mode:
            if key in (curses.KEY_BACKSPACE, 127, 8):
                self.temp_wc_apodo = self.temp_wc_apodo[:-1]
            elif key in (ord("\n"), 10, 13):
                self._wc_commit_apodo()
            elif key == 27:
                self._wc_cancel_all()
            elif 32 <= key <= 126:
                self.temp_wc_apodo += chr(key)
            return

        if self.wc_confirm_delete:
            if key in (ord("y"), ord("Y"), ord("\n"), 10, 13):
                if self.world_clocks:
                    self.world_clocks.pop(self.wc_selected_idx)
                    if self.wc_selected_idx >= len(self.world_clocks):
                        self.wc_selected_idx = max(0, len(self.world_clocks) - 1)
                    if not self.world_clocks:
                        self.wc_focus = False
                        self.wc_group_offset = 0
                    self._wc_save()
                self.wc_confirm_delete = False
            return

        if key == curses.KEY_DOWN:
            self._wc_move_focus(1)
        elif key == curses.KEY_UP:
            self._wc_move_focus(-1)
        elif key == curses.KEY_RIGHT and self.wc_focus:
            if self.world_clocks:
                self.wc_group_offset = (self.wc_group_offset + 1) % len(
                    self.world_clocks
                )
        elif key == curses.KEY_LEFT and self.wc_focus:
            if self.world_clocks:
                self.wc_group_offset = (self.wc_group_offset - 1) % len(
                    self.world_clocks
                )
        elif key == ord("n"):
            if self.wc_focus:
                self._wc_open_picker(edit_target=None)
        elif key == ord("e"):
            if self.wc_focus:
                if self.world_clocks:
                    self._wc_open_picker(
                        edit_target=self.wc_group_offset % len(self.world_clocks)
                    )
        elif key == ord("d"):
            if self.wc_focus:
                if self.world_clocks:
                    self.wc_selected_idx = self.wc_group_offset % len(self.world_clocks)
                    self.wc_confirm_delete = True
        elif key == ord("u"):
            self._weather_request_refresh()

    def _wc_move_focus(self, step):
        mostrar_wc = self.config.get("wc_mostrar", "ver") == "ver"
        show_wc_line = mostrar_wc and bool(self.world_clocks)
        if self.wc_focus:
            self.wc_focus = False
        elif show_wc_line:
            self.wc_focus = True

    def _wc_offset_info_cached(self, iana):
        now = datetime.datetime.now()
        current_minute = (now.hour, now.minute)
        if self._wc_offset_cache_minute != current_minute:
            self._wc_offset_cache = {}
            self._wc_offset_cache_minute = current_minute
        if iana not in self._wc_offset_cache:
            self._wc_offset_cache[iana] = _wc_offset_info(iana)
        return self._wc_offset_cache[iana]

    def _draw_clock(self):
        tier = self._size_tier()
        now = datetime.datetime.now()
        dias = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
        meses = [
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
        hora_str = self._format_clock_time(now)
        now_str = f"{dias[now.weekday()]} {now.day} {meses[now.month - 1]}  {hora_str}"

        if self.wc_picker_open:
            self._draw_wc_picker()
            return
        if self.wc_apodo_mode:
            self._draw_wc_apodo()
            return
        if self.wc_confirm_delete:
            objetivo = (
                self.world_clocks[self.wc_selected_idx] if self.world_clocks else None
            )
            nombre = objetivo["apodo"] if objetivo else "?"
            rows = [
                now_str,
                f"¿Eliminar reloj '{nombre}'?",
                "  y / Enter = Sí    cualquier tecla = No",
            ]
            self._draw_frame("◷ Reloj", rows, weather_line=self._weather_display_line())
            return

        if tier == "minimum":
            rows = [now_str]
            self._draw_frame("◷ Reloj", rows, weather_line=self._weather_display_line())
            return

        rows = [now_str]
        row_attrs = [None]
        mostrar_wc = self.config.get("wc_mostrar", "ver") == "ver"
        if mostrar_wc and self.world_clocks:
            n_wc = len(self.world_clocks)
            self.wc_group_offset = self.wc_group_offset % n_wc
            partes = []
            for pos in range(min(4, n_wc)):
                idx = (self.wc_group_offset + pos) % n_wc
                w = self.world_clocks[idx]
                info = self._wc_offset_info_cached(w["zona"])
                hhmm = info[0].strftime("%H:%M") if info else "--:--"
                texto = f"{w['apodo']} {hhmm}"
                if pos == 0 and self.wc_focus:
                    partes.append(f"»{texto}«")
                else:
                    partes.append(f" {texto} ")
            rows.append("".join(partes))
            row_attrs.append(None)

        helper_keys = "↑↓:sección  ←→:alternar WC  n:+WC  e:editar  d:borrar  u:clima"
        helper = [helper_keys]
        self._draw_frame(
            "◷ Reloj",
            rows,
            helper,
            weather_line=self._weather_display_line(),
            row_attrs=row_attrs,
        )

    # ──────────────────────────────────────────
    #  VIEW 2 — ALARMAS
    # ──────────────────────────────────────────

    def _input_alarms(self, key):
        if self.alarm_edit_mode:
            if key in (curses.KEY_UP, curses.KEY_DOWN):
                if key == curses.KEY_DOWN:
                    self.alarm_edit_field = (self.alarm_edit_field + 1) % 3
                else:
                    self.alarm_edit_field = (self.alarm_edit_field - 1) % 3
            elif self.alarm_edit_field == 0:
                if key in (curses.KEY_BACKSPACE, 127, 8):
                    self.temp_alarm_name = self.temp_alarm_name[:-1]
                elif 32 <= key <= 126:
                    self.temp_alarm_name += chr(key)
            elif self.alarm_edit_field == 1:
                if key == 9:
                    self.temp_alarm_time_field = (self.temp_alarm_time_field + 1) % 2
                elif key == curses.KEY_RIGHT:
                    f = self.temp_alarm_time_field
                    self.temp_alarm_time[f] = (self.temp_alarm_time[f] + 1) % (
                        24 if f == 0 else 60
                    )
                elif key == curses.KEY_LEFT:
                    f = self.temp_alarm_time_field
                    self.temp_alarm_time[f] = (self.temp_alarm_time[f] - 1) % (
                        24 if f == 0 else 60
                    )
            elif self.alarm_edit_field == 2:
                if key == curses.KEY_RIGHT:
                    self.temp_alarm_days_cursor = (self.temp_alarm_days_cursor + 1) % 7
                elif key == curses.KEY_LEFT:
                    self.temp_alarm_days_cursor = (self.temp_alarm_days_cursor - 1) % 7
                elif key == ord(" "):
                    d = self.temp_alarm_days_cursor
                    if d in self.temp_alarm_days:
                        self.temp_alarm_days.remove(d)
                    else:
                        self.temp_alarm_days.append(d)
                    self.temp_alarm_days.sort()
            if key in (ord("\n"), 10, 13) and self.alarm_edit_field == 0:
                self.alarm_edit_field = 1
            elif key in (ord("\n"), 10, 13) and self.alarm_edit_field == 1:
                self.alarm_edit_field = 2
            elif key in (ord("\n"), 10, 13):
                alarm = {
                    "tipo": "alarma",
                    "hora": self.temp_alarm_time[0],
                    "minutos": self.temp_alarm_time[1],
                    "segundos": 0,
                    "status": "activado",
                    "nombre": self.temp_alarm_name or "Alarma",
                    "repeat_days": list(self.temp_alarm_days),
                }
                if self.alarm_edit_target is not None:
                    self.alarm_lists[self.alarm_edit_target] = alarm
                else:
                    self.alarm_lists.append(alarm)
                self.alarm_edit_mode = False
                self.alarm_edit_target = None
                _save_data(
                    self.alarm_lists,
                    self.timers,
                    self.pomodoro,
                    self.todos,
                    self.config,
                )
            elif key == 27:
                self.alarm_edit_mode = False
                self.alarm_edit_target = None
            return

        if self.alarm_confirm_delete:
            if key in (ord("y"), ord("Y"), ord("\n"), 10, 13):
                if self.alarm_lists:
                    self.alarm_lists.pop(self.selected_alarm_idx)
                    if self.selected_alarm_idx >= len(self.alarm_lists):
                        self.selected_alarm_idx = max(0, len(self.alarm_lists) - 1)
                    _save_data(
                        self.alarm_lists,
                        self.timers,
                        self.pomodoro,
                        self.todos,
                        self.config,
                    )
                self.alarm_confirm_delete = False
            return

        if key == ord("n"):
            self.alarm_edit_mode = True
            self.alarm_edit_target = None
            self.temp_alarm_time = [0, 0]
            self.temp_alarm_time_field = 0
            self.alarm_edit_field = 0
            self.temp_alarm_name = "Alarma"
            self.temp_alarm_days = []
            self.temp_alarm_days_cursor = 0
        elif key == curses.KEY_DOWN:
            if self.alarm_lists:
                self.selected_alarm_idx = (self.selected_alarm_idx + 1) % len(
                    self.alarm_lists
                )
                self.alarm_scroll_offset = max(0, self.selected_alarm_idx - 4)
        elif key == curses.KEY_UP:
            if self.alarm_lists:
                self.selected_alarm_idx = (self.selected_alarm_idx - 1) % len(
                    self.alarm_lists
                )
                self.alarm_scroll_offset = max(0, self.selected_alarm_idx - 4)
        elif key == ord(" "):
            if self.alarm_lists:
                a = self.alarm_lists[self.selected_alarm_idx]
                a["status"] = "desactivado" if a["status"] == "activado" else "activado"
                _save_data(
                    self.alarm_lists,
                    self.timers,
                    self.pomodoro,
                    self.todos,
                    self.config,
                )
        elif key == ord("d"):
            if self.alarm_lists:
                self.alarm_confirm_delete = True
        elif key == ord("e"):
            if self.alarm_lists:
                a = self.alarm_lists[self.selected_alarm_idx]
                self.alarm_edit_mode = True
                self.alarm_edit_target = self.selected_alarm_idx
                self.temp_alarm_time = [a["hora"], a["minutos"]]
                self.temp_alarm_time_field = 0
                self.temp_alarm_name = a["nombre"]
                self.temp_alarm_days = _repeat_days_normalize(a.get("repeat_days"))
                self.temp_alarm_days_cursor = 0
                self.alarm_edit_field = 0

    def _draw_alarms(self):
        tier = self._size_tier()
        if self.alarm_edit_mode:
            hh, mm = self.temp_alarm_time
            n_mark = "►" if self.alarm_edit_field == 0 else " "
            t_mark = "►" if self.alarm_edit_field == 1 else " "
            d_mark = "►" if self.alarm_edit_field == 2 else " "
            hh_activo = self.alarm_edit_field == 1 and self.temp_alarm_time_field == 0
            mm_activo = self.alarm_edit_field == 1 and self.temp_alarm_time_field == 1
            hh_str = f"◄{hh:02d}►" if hh_activo else f"{hh:02d}"
            mm_str = f"◄{mm:02d}►" if mm_activo else f"{mm:02d}"
            dias_field_activo = self.alarm_edit_field == 2
            partes_dias = []
            for d in range(7):
                marcado = d in self.temp_alarm_days
                txt = f"[{DIAS_ABBR[d]}]" if marcado else f" {DIAS_ABBR[d]} "
                if dias_field_activo and d == self.temp_alarm_days_cursor:
                    txt = f"»{txt}«" if marcado else f"»{DIAS_ABBR[d]}«"
                partes_dias.append(txt)
            dias_str = "".join(partes_dias)
            rows = [
                (
                    f"{n_mark} Nombre : {self.temp_alarm_name}_"
                    if self.alarm_edit_field == 0
                    else f"{n_mark} Nombre : {self.temp_alarm_name}"
                ),
                f"{t_mark} Hora   : {hh_str}:{mm_str}",
                f"{d_mark} Días   : {dias_str}",
                f"   ({_repeat_days_str(self.temp_alarm_days)})",
            ]
            helper = [
                "↑↓:línea  Tab:HH/MM  ←→:valor  Enter:guardar  Esc:cancelar",
                "Días: ←→ mover  Space:✔/○",
            ]
            self._draw_frame("✎ Editar Alarma", rows, helper)
            return

        if self.alarm_confirm_delete:
            a = self.alarm_lists[self.selected_alarm_idx] if self.alarm_lists else None
            name = a["nombre"] if a else "?"
            rows = [f"¿Eliminar '{name}'?", "  y / Enter = Sí    cualquier tecla = No"]
            self._draw_frame("◷ Alarmas", rows)
            return

        MAX_VISIBLE = 6 if tier == "full" else 3
        total = len(self.alarm_lists)
        rows = []
        row_attrs = []
        if not total:
            rows.append("<n> para crear alarma")
        else:
            if self.selected_alarm_idx < self.alarm_scroll_offset:
                self.alarm_scroll_offset = self.selected_alarm_idx
            elif self.selected_alarm_idx >= self.alarm_scroll_offset + MAX_VISIBLE:
                self.alarm_scroll_offset = self.selected_alarm_idx - MAX_VISIBLE + 1
            visible = self.alarm_lists[
                self.alarm_scroll_offset : self.alarm_scroll_offset + MAX_VISIBLE
            ]
            for i_rel, a in enumerate(visible):
                i_abs = i_rel + self.alarm_scroll_offset
                activa = a["status"] == "activado"
                es_sel = i_abs == self.selected_alarm_idx
                sel = "►" if es_sel else " "
                sta = "✔" if activa else "✘"
                rep = _repeat_days_str(a.get("repeat_days"))
                rep_txt = "" if rep == "una vez" else f"  ↻{rep}"
                rows.append(
                    f"{sel} {sta} {a['nombre']:<10.10s} {a['hora']:02d}:{a['minutos']:02d}{rep_txt}"
                )
                if es_sel:
                    row_attrs.append(curses.color_pair(PAIR_TEXTO) | curses.A_BOLD)
                elif not activa:
                    row_attrs.append(curses.color_pair(PAIR_HELPERS) | curses.A_DIM)
                else:
                    row_attrs.append(None)
            if total > MAX_VISIBLE:
                shown_end = min(self.alarm_scroll_offset + MAX_VISIBLE, total)
                rows.append(
                    f"  ({self.alarm_scroll_offset + 1}–{shown_end} de {total})"
                )
                row_attrs.append(curses.color_pair(PAIR_HELPERS) | curses.A_DIM)
        helper = ["n:nueva  ↑↓:nav  Space:on/off  e:editar  d:borrar"]
        self._draw_frame(
            "◷ Alarmas", rows, helper, row_attrs=row_attrs if row_attrs else None
        )

    # ──────────────────────────────────────────
    #  VIEW 3 — POMODORO
    # ──────────────────────────────────────────

    def _input_pomodoro(self, key):
        p = self.pomodoro
        if key in (curses.KEY_UP, curses.KEY_DOWN):
            p["edit_field"] ^= 1
        elif p["edit_field"] == 0:
            modes = ["work", "shortbreak", "longrest"]
            idx = modes.index(p["mode_nav"])
            if key == 9:
                p["mode_nav"] = modes[(idx + 1) % 3]
            elif key == curses.KEY_RIGHT:
                m = p["mode_nav"]
                if m == "shortbreak":
                    p[m]["count"] = min(6, p[m]["count"] + 1)
                elif m == "work":
                    p[m]["count"] = min(9, p[m]["count"] + 1)
                elif m == "longrest":
                    p[m]["count"] = min(3, p[m]["count"] + 1)
            elif key == curses.KEY_LEFT:
                m = p["mode_nav"]
                if m in ("work", "longrest"):
                    p[m]["count"] = max(1, p[m]["count"] - 1)
                else:
                    p[m]["count"] = max(0, p[m]["count"] - 1)
        elif p["edit_field"] == 1:
            if key == 9:
                p["time_field"] = (p["time_field"] + 1) % 3
            elif key == curses.KEY_RIGHT:
                m = p["mode_nav"]
                f = p["time_field"]
                lim = 99 if f == 0 else 59
                p[m]["time"][f] = (p[m]["time"][f] + 1) % (lim + 1)
            elif key == curses.KEY_LEFT:
                m = p["mode_nav"]
                f = p["time_field"]
                lim = 99 if f == 0 else 59
                p[m]["time"][f] = (p[m]["time"][f] - 1) % (lim + 1)
        if key == ord("R"):
            p["work"] = {
                "next": "shortbreak",
                "time": [0, 20, 0],
                "count": 3,
                "left": 3,
            }
            p["shortbreak"] = {"next": "work", "time": [0, 5, 0], "count": 2, "left": 2}
            p["longrest"] = {"next": "work", "time": [0, 15, 0], "count": 1, "left": 1}
            p["is_active"] = False
            p["started"] = False
            p["cycle_idx"] = 0
            p["current_mode"] = "work"
            p["mode_nav"] = "work"
            t = p["work"]["time"]
            p["timer_value"] = hms_to_secs(*t)
            self._pomo_last_tick = None
            self._pomo_seq_cache = None
            _save_data(
                self.alarm_lists, self.timers, self.pomodoro, self.todos, self.config
            )
        elif key == ord(" "):
            if not p["is_active"]:
                if p["timer_value"] <= 0:
                    t = p[p["current_mode"]]["time"]
                    p["timer_value"] = hms_to_secs(*t)
                p["is_active"] = True
                p["started"] = True
                self._pomo_last_tick = time.monotonic()
            else:
                p["is_active"] = False
                self._pomo_last_tick = None

    def _draw_pomodoro(self):
        p = self.pomodoro
        nav = p["mode_nav"]
        label_map = {
            "work": "WORK",
            "shortbreak": "SHORT BREAK",
            "longrest": "LONG REST",
        }
        m1 = "►" if p["edit_field"] == 0 else " "
        count_str = (
            f"◄{p[nav]['count']}►" if p["edit_field"] == 0 else f"{p[nav]['count']}"
        )
        mode_str = f"{m1}[ {label_map[nav]}  ({count_str}) ]"
        if p["is_active"] or p["timer_value"] > 0:
            h, m, s = secs_to_hms(p["timer_value"])
        else:
            h, m, s = p[nav]["time"]
        m2 = "►" if p["edit_field"] == 1 else " "
        h_act = p["edit_field"] == 1 and p["time_field"] == 0
        m_act = p["edit_field"] == 1 and p["time_field"] == 1
        s_act = p["edit_field"] == 1 and p["time_field"] == 2
        h_str = f"◄{h:02d}►" if h_act else f"{h:02d}"
        m_str = f"◄{m:02d}►" if m_act else f"{m:02d}"
        s_str = f"◄{s:02d}►" if s_act else f"{s:02d}"
        time_str = f"{m2}[ {h_str}:{m_str}:{s_str} ]"
        play_icon = "❚❚" if p["is_active"] else "▶"
        cur_label = label_map[p["current_mode"]]
        seq = self._build_pomo_sequence()
        rows = [
            mode_str,
            time_str,
            "",
            f"Modo activo: {cur_label}  |  Ciclo: {len(seq)} pasos",
        ]
        helper = [f"↑↓:fila  Space:{play_icon}  R:reset", "Tab:cicla  ←→:valor"]
        self._draw_frame("◆ Pomodoro", rows, helper)

    # ──────────────────────────────────────────
    #  VIEW 4 — TIMERS
    # ──────────────────────────────────────────

    def _input_timer(self, key):
        if self.timer_edit_mode:
            if key in (ord("\n"), 10, 13):
                self.timers[self.timer_edit_target]["name"] = (
                    self.temp_timer_name or "Timer"
                )
                self.timer_edit_mode = False
                _save_data(
                    self.alarm_lists,
                    self.timers,
                    self.pomodoro,
                    self.todos,
                    self.config,
                )
            elif key == 27:
                self.timer_edit_mode = False
            elif key in (curses.KEY_BACKSPACE, 127, 8):
                self.temp_timer_name = self.temp_timer_name[:-1]
            elif 32 <= key <= 126:
                self.temp_timer_name += chr(key)
            return
        t = self.timers[self.selected_timer_idx] if self.timers else None
        if key == curses.KEY_DOWN:
            if self.timers:
                self.selected_timer_idx = (self.selected_timer_idx + 1) % len(
                    self.timers
                )
                self.timer_scroll_offset = max(0, self.selected_timer_idx - 4)
        elif key == curses.KEY_UP:
            if self.timers:
                self.selected_timer_idx = (self.selected_timer_idx - 1) % len(
                    self.timers
                )
                self.timer_scroll_offset = max(0, self.selected_timer_idx - 4)
        elif key == ord("n"):
            if len(self.timers) < 10:
                n = len(self.timers) + 1
                self.timers.append(
                    {
                        "name": f"Temporizador{n}",
                        "time": [0, 10, 0],
                        "active": False,
                        "started": False,
                        "remaining": 600,
                        "last_tick": None,
                    }
                )
                self.selected_timer_idx = len(self.timers) - 1
                self.timer_scroll_offset = max(0, self.selected_timer_idx - 4)
                _save_data(
                    self.alarm_lists,
                    self.timers,
                    self.pomodoro,
                    self.todos,
                    self.config,
                )
        elif key == ord("d"):
            if len(self.timers) > 1:
                self.timers.pop(self.selected_timer_idx)
                if self.selected_timer_idx >= len(self.timers):
                    self.selected_timer_idx = max(0, len(self.timers) - 1)
                self.timer_scroll_offset = max(0, self.selected_timer_idx - 4)
                _save_data(
                    self.alarm_lists,
                    self.timers,
                    self.pomodoro,
                    self.todos,
                    self.config,
                )
        elif key == ord("e"):
            if t:
                self.timer_edit_mode = True
                self.timer_edit_target = self.selected_timer_idx
                self.temp_timer_name = t["name"]
        elif key == 9:
            if t and not t["active"]:
                self.timer_time_field = (self.timer_time_field + 1) % 3
        elif key == curses.KEY_RIGHT:
            if t and not t["active"]:
                f = self.timer_time_field
                lim = 99 if f == 0 else 59
                t["time"][f] = (t["time"][f] + 1) % (lim + 1)
                t["remaining"] = hms_to_secs(*t["time"])
        elif key == curses.KEY_LEFT:
            if t and not t["active"]:
                f = self.timer_time_field
                lim = 99 if f == 0 else 59
                t["time"][f] = (t["time"][f] - 1) % (lim + 1)
                t["remaining"] = hms_to_secs(*t["time"])
        elif key == ord(" "):
            if t:
                if t["active"]:
                    t["active"] = False
                else:
                    if t["remaining"] <= 0:
                        t["remaining"] = hms_to_secs(*t["time"])
                    t["active"] = True
                    t["started"] = True
                    t["last_tick"] = time.monotonic()
        elif key == ord("R"):
            for timer in self.timers:
                timer["active"] = False
                timer["started"] = False
                timer["last_tick"] = None
                timer["remaining"] = hms_to_secs(*timer["time"])

    def _draw_timers(self):
        if self.timer_edit_mode:
            rows = [f"Nuevo nombre: {self.temp_timer_name}_"]
            helper = ["Enter:guardar  Esc:cancelar"]
            self._draw_frame("✎ Editar", rows, helper)
            return
        MAX_VISIBLE = 6
        total = len(self.timers)
        if self.selected_timer_idx < self.timer_scroll_offset:
            self.timer_scroll_offset = self.selected_timer_idx
        elif self.selected_timer_idx >= self.timer_scroll_offset + MAX_VISIBLE:
            self.timer_scroll_offset = self.selected_timer_idx - MAX_VISIBLE + 1
        rows = []
        visible = self.timers[
            self.timer_scroll_offset : self.timer_scroll_offset + MAX_VISIBLE
        ]
        for i_rel, t in enumerate(visible):
            i_abs = i_rel + self.timer_scroll_offset
            sel = "►" if i_abs == self.selected_timer_idx else " "
            h, m, s = secs_to_hms(t["remaining"])
            run_icon = "▶ " if t["active"] else "  "
            if i_abs == self.selected_timer_idx and not t["active"]:
                h_act = self.timer_time_field == 0
                m_act = self.timer_time_field == 1
                s_act = self.timer_time_field == 2
                h_str = f"◄{h:02d}►" if h_act else f"{h:02d}"
                m_str = f"◄{m:02d}►" if m_act else f"{m:02d}"
                s_str = f"◄{s:02d}►" if s_act else f"{s:02d}"
                tstr = f"[{h_str}:{m_str}:{s_str}]"
            else:
                tstr = f"[{h:02d}:{m:02d}:{s:02d}]"
            rows.append(f"{sel}{run_icon} {t['name']:14s}  {tstr}")
        if total > MAX_VISIBLE:
            shown_end = min(self.timer_scroll_offset + MAX_VISIBLE, total)
            rows.append(f"  ({self.timer_scroll_offset + 1}–{shown_end} de {total})")
        helper = [
            "↑↓:nav  n:nuevo  e:editar  d:borrar",
            "Tab:campo  ←→:valor  Space:▶/❚❚  R:reset todo",
        ]
        self._draw_frame("⏱ Timers", rows, helper)

    # ──────────────────────────────────────────
    #  VIEW 5 — STOPWATCH
    # ──────────────────────────────────────────

    def _sw_elapsed(self):
        sw = self.stopwatch
        if sw["active"] and sw["start_time"] is not None:
            return sw["base_elapsed"] + (time.monotonic() - sw["start_time"])
        return sw["base_elapsed"]

    def _input_stopwatch(self, key):
        sw = self.stopwatch
        elapsed = self._sw_elapsed()
        if key == ord(" "):
            if sw["active"]:
                sw["base_elapsed"] = elapsed
                sw["active"] = False
                sw["start_time"] = None
            else:
                sw["active"] = True
                sw["start_time"] = time.monotonic()
        elif key == 9:
            if sw["active"]:
                diff = elapsed - sw["last_record_at"]
                sw["last_record_at"] = elapsed
                sw["records"].append(diff)
                self.sw_scroll_offset = max(0, len(sw["records"]) - 5)
        elif key == ord("d"):
            if sw["records"]:
                sw["records"].pop()
                if sw["records"]:
                    sw["last_record_at"] = sum(sw["records"])
                else:
                    sw["last_record_at"] = 0.0
                self.sw_scroll_offset = max(0, len(sw["records"]) - 5)
        elif key == ord("R"):
            sw["active"] = False
            sw["start_time"] = None
            sw["base_elapsed"] = 0.0
            sw["records"] = []
            sw["last_record_at"] = 0.0
            self.sw_scroll_offset = 0

    def _draw_stopwatch(self):
        elapsed = self._sw_elapsed()
        h, m, s = secs_to_hms(elapsed)
        ms = int((elapsed - int(elapsed)) * 100)
        main_time = f"{h:02d}:{m:02d}:{s:02d}.{ms:02d}"
        sw = self.stopwatch
        run_icon = "▶ " if sw["active"] else "  "
        rows = [f"{run_icon}{main_time}", ""]
        MAX_VISIBLE = 5
        records = sw["records"]
        total_rec = len(records)
        if records:
            accums = []
            acc = 0.0
            for d in records:
                acc += d
                accums.append(acc)
            if self.sw_scroll_offset + MAX_VISIBLE > total_rec:
                self.sw_scroll_offset = max(0, total_rec - MAX_VISIBLE)
            for i in range(
                self.sw_scroll_offset,
                min(self.sw_scroll_offset + MAX_VISIBLE, total_rec),
            ):
                diff = records[i]
                accum = accums[i]
                ah, am, as_ = secs_to_hms(accum)
                dh, dm, ds = secs_to_hms(diff)
                marker = "►" if i == total_rec - 1 else " "
                rows.append(
                    f"{marker} {i + 1:2d}.  {ah:02d}:{am:02d}:{as_:02d}   (+{dh:02d}:{dm:02d}:{ds:02d})"
                )
            if total_rec > MAX_VISIBLE:
                shown_end = min(self.sw_scroll_offset + MAX_VISIBLE, total_rec)
                rows.append(
                    f"  ({self.sw_scroll_offset + 1}–{shown_end} de {total_rec})"
                )
        else:
            rows.append("(sin registros)")
        helper = ["Space:▶/❚❚  Tab:marcar lap  d:borrar último  R:reset"]
        self._draw_frame("⏲ Cronómetro", rows, helper)

    # ──────────────────────────────────────────
    #  VIEW 6 — TODO
    # ──────────────────────────────────────────

    def _todo_save(self):
        _save_data(
            self.alarm_lists, self.timers, self.pomodoro, self.todos, self.config
        )

    def _todo_view(self):
        indices_reales = list(range(len(self.todos)))
        return list(self.todos), indices_reales

    def _input_todo(self, key):
        if self.todo_edit_mode:
            f = self.todo_edit_field
            es_nota = self.temp_todo_tipo == "nota"
            muestra_recordatorio = (not es_nota) and self.temp_todo_recordarme
            if es_nota:
                n_fields = 2
            elif not muestra_recordatorio:
                n_fields = 3
            elif self.temp_todo_repetir:
                n_fields = 7
            else:
                n_fields = 9
            if key in (curses.KEY_UP, curses.KEY_DOWN):
                if key == curses.KEY_DOWN:
                    self.todo_edit_field = (self.todo_edit_field + 1) % n_fields
                else:
                    self.todo_edit_field = (self.todo_edit_field - 1) % n_fields
            elif f == 0:
                if key in (9, ord(" ")):
                    if self.temp_todo_tipo == "tarea":
                        self.temp_todo_tipo = "nota"
                        self.temp_todo_recordarme = False
                    else:
                        self.temp_todo_tipo = "tarea"
                    if self.temp_todo_tipo == "nota":
                        nuevo_n = 2
                    elif not self.temp_todo_recordarme:
                        nuevo_n = 3
                    elif self.temp_todo_repetir:
                        nuevo_n = 7
                    else:
                        nuevo_n = 9
                    if self.todo_edit_field >= nuevo_n:
                        self.todo_edit_field = 0
            elif f == 1:
                if key in (curses.KEY_BACKSPACE, 127, 8):
                    self.temp_todo_texto = self.temp_todo_texto[:-1]
                elif 32 <= key <= 126:
                    self.temp_todo_texto += chr(key)
            elif f == 2:
                if key in (9, ord(" ")) and not es_nota:
                    self.temp_todo_recordarme = not self.temp_todo_recordarme
                    if self.temp_todo_recordarme:
                        ahora = datetime.datetime.now()
                        self.temp_todo_alarma = [
                            ahora.hour,
                            ahora.minute,
                            ahora.day,
                            ahora.month,
                            ahora.year,
                        ]
                        self.temp_todo_repetir = False
                        self.temp_todo_days = []
                        self.temp_todo_days_cursor = 0
                    else:
                        if self.todo_edit_field > 2:
                            self.todo_edit_field = 2
            elif f == 3 and muestra_recordatorio:
                if key in (9, ord(" ")):
                    self.temp_todo_repetir = not self.temp_todo_repetir
                    if self.todo_edit_field > (6 if self.temp_todo_repetir else 8):
                        self.todo_edit_field = 3
            elif f == 4 and muestra_recordatorio and self.temp_todo_repetir:
                if key == curses.KEY_RIGHT:
                    self.temp_todo_days_cursor = (self.temp_todo_days_cursor + 1) % 7
                elif key == curses.KEY_LEFT:
                    self.temp_todo_days_cursor = (self.temp_todo_days_cursor - 1) % 7
                elif key == ord(" "):
                    d = self.temp_todo_days_cursor
                    if d in self.temp_todo_days:
                        self.temp_todo_days.remove(d)
                    else:
                        self.temp_todo_days.append(d)
                    self.temp_todo_days.sort()
            elif f == 5 and muestra_recordatorio and self.temp_todo_repetir:
                if key == curses.KEY_RIGHT:
                    self.temp_todo_alarma[0] = (self.temp_todo_alarma[0] + 1) % 24
                elif key == curses.KEY_LEFT:
                    self.temp_todo_alarma[0] = (self.temp_todo_alarma[0] - 1) % 24
            elif f == 6 and muestra_recordatorio and self.temp_todo_repetir:
                if key == curses.KEY_RIGHT:
                    self.temp_todo_alarma[1] = (self.temp_todo_alarma[1] + 1) % 60
                elif key == curses.KEY_LEFT:
                    self.temp_todo_alarma[1] = (self.temp_todo_alarma[1] - 1) % 60
            elif f == 4 and muestra_recordatorio and not self.temp_todo_repetir:
                if key == curses.KEY_RIGHT:
                    self.temp_todo_alarma[0] = (self.temp_todo_alarma[0] + 1) % 24
                elif key == curses.KEY_LEFT:
                    self.temp_todo_alarma[0] = (self.temp_todo_alarma[0] - 1) % 24
            elif f == 5 and muestra_recordatorio and not self.temp_todo_repetir:
                if key == curses.KEY_RIGHT:
                    self.temp_todo_alarma[1] = (self.temp_todo_alarma[1] + 1) % 60
                elif key == curses.KEY_LEFT:
                    self.temp_todo_alarma[1] = (self.temp_todo_alarma[1] - 1) % 60
            elif f == 6 and muestra_recordatorio and not self.temp_todo_repetir:
                import calendar

                anio_actual = self.temp_todo_alarma[4]
                mes_actual = self.temp_todo_alarma[3]
                max_day = calendar.monthrange(anio_actual, mes_actual)[1]
                if key == curses.KEY_RIGHT:
                    self.temp_todo_alarma[2] = (self.temp_todo_alarma[2] % max_day) + 1
                elif key == curses.KEY_LEFT:
                    self.temp_todo_alarma[2] = (
                        (self.temp_todo_alarma[2] - 2) % max_day
                    ) + 1
            elif f == 7 and muestra_recordatorio and not self.temp_todo_repetir:
                if key == curses.KEY_RIGHT:
                    self.temp_todo_alarma[3] = (self.temp_todo_alarma[3] % 12) + 1
                elif key == curses.KEY_LEFT:
                    self.temp_todo_alarma[3] = ((self.temp_todo_alarma[3] - 2) % 12) + 1
            elif f == 8 and muestra_recordatorio and not self.temp_todo_repetir:
                if key == curses.KEY_RIGHT:
                    self.temp_todo_alarma[4] += 1
                elif key == curses.KEY_LEFT:
                    self.temp_todo_alarma[4] = max(2025, self.temp_todo_alarma[4] - 1)
            if key in (ord("\n"), 10, 13):
                self._todo_commit_edit()
            elif key == 27:
                self.todo_edit_mode = False
                self.todo_edit_target = None
            return

        if self.todo_confirm_delete:
            if key in (ord("y"), ord("Y"), ord("\n"), 10, 13):
                if self.todos:
                    _, indices_reales = self._todo_view()
                    real_idx = indices_reales[self.todo_selected_idx]
                    self.todos.pop(real_idx)
                    if self.todo_selected_idx >= len(self.todos):
                        self.todo_selected_idx = max(0, len(self.todos) - 1)
                    self._todo_save()
                self.todo_confirm_delete = False
            return

        if key == ord("n"):
            ahora = datetime.datetime.now()
            self.todo_edit_mode = True
            self.todo_edit_target = None
            self.todo_edit_field = 0
            self.temp_todo_tipo = "tarea"
            self.temp_todo_texto = ""
            self.temp_todo_recordarme = False
            self.temp_todo_alarma = [
                ahora.hour,
                ahora.minute,
                ahora.day,
                ahora.month,
                ahora.year,
            ]
            self.temp_todo_repetir = False
            self.temp_todo_days = []
            self.temp_todo_days_cursor = 0
        elif key == curses.KEY_DOWN:
            if self.todos:
                self.todo_selected_idx = (self.todo_selected_idx + 1) % len(self.todos)
                self.todo_scroll_offset = max(0, self.todo_selected_idx - 5)
        elif key == curses.KEY_UP:
            if self.todos:
                self.todo_selected_idx = (self.todo_selected_idx - 1) % len(self.todos)
                self.todo_scroll_offset = max(0, self.todo_selected_idx - 5)
        elif key == curses.KEY_RIGHT:
            if self.todos:
                _, indices_reales = self._todo_view()
                idx = self.todo_selected_idx
                if idx < len(indices_reales) - 1:
                    real_a = indices_reales[idx]
                    real_b = indices_reales[idx + 1]
                    self.todos[real_a], self.todos[real_b] = (
                        self.todos[real_b],
                        self.todos[real_a],
                    )
                    self.todo_selected_idx += 1
                    self._todo_save()
        elif key == curses.KEY_LEFT:
            if self.todos:
                _, indices_reales = self._todo_view()
                idx = self.todo_selected_idx
                if idx > 0:
                    real_a = indices_reales[idx]
                    real_b = indices_reales[idx - 1]
                    self.todos[real_a], self.todos[real_b] = (
                        self.todos[real_b],
                        self.todos[real_a],
                    )
                    self.todo_selected_idx -= 1
                    self._todo_save()
        elif key == ord(" "):
            if self.todos:
                _, indices_reales = self._todo_view()
                real_idx = indices_reales[self.todo_selected_idx]
                t = self.todos[real_idx]
                if t.get("tipo", "tarea") == "tarea":
                    _todo_set_done(t, not _todo_is_done(t))
                    self._todo_save()
        elif key == ord("d"):
            if self.todos:
                self.todo_confirm_delete = True
        elif key == ord("e"):
            if self.todos:
                _, indices_reales = self._todo_view()
                real_idx = indices_reales[self.todo_selected_idx]
                t = self.todos[real_idx]
                self.todo_edit_mode = True
                self.todo_edit_target = real_idx
                self.todo_edit_field = 0
                self.temp_todo_tipo = t.get("tipo", "tarea")
                self.temp_todo_texto = t["texto"]
                self.temp_todo_recordarme = t.get("recordarme", False)
                ahora = datetime.datetime.now()
                self.temp_todo_alarma = [
                    t.get("alarma_hora", ahora.hour),
                    t.get("alarma_min", ahora.minute),
                    t.get("alarma_dia", ahora.day),
                    t.get("alarma_mes", ahora.month),
                    t.get("alarma_anio", ahora.year),
                ]
                self.temp_todo_days = _repeat_days_normalize(t.get("repeat_days"))
                self.temp_todo_repetir = bool(self.temp_todo_days)
                self.temp_todo_days_cursor = 0
        elif key == ord("x"):
            if self.todos:
                _, indices_reales = self._todo_view()
                real_idx = indices_reales[self.todo_selected_idx]
                t = self.todos[real_idx]
                if t.get("tipo", "tarea") == "tarea":
                    t["recordarme"] = not t.get("recordarme", False)
                    if t["recordarme"]:
                        t["_disparada"] = False
                    self._todo_save()

    def _todo_commit_edit(self):
        texto = self.temp_todo_texto.strip() or (
            "Nueva nota" if self.temp_todo_tipo == "nota" else "Nueva tarea"
        )
        recordarme = self.temp_todo_recordarme and self.temp_todo_tipo == "tarea"
        hh, mm, dia, mes, anio = self.temp_todo_alarma
        repeat_days = (
            list(self.temp_todo_days) if (recordarme and self.temp_todo_repetir) else []
        )
        if self.todo_edit_target is not None:
            t = self.todos[self.todo_edit_target]
            t["tipo"] = self.temp_todo_tipo
            t["texto"] = texto
            t["recordarme"] = recordarme
            t["alarma_hora"] = hh
            t["alarma_min"] = mm
            t["alarma_dia"] = dia
            t["alarma_mes"] = mes
            t["alarma_anio"] = anio
            t["repeat_days"] = repeat_days
            t["_disparada"] = False
        else:
            self.todos.append(
                {
                    "id": self._todo_next_id,
                    "tipo": self.temp_todo_tipo,
                    "orden": len(self.todos) + 1,
                    "texto": texto,
                    "activo": True,
                    "last_done_date": None,
                    "recordarme": recordarme,
                    "alarma_hora": hh,
                    "alarma_min": mm,
                    "alarma_dia": dia,
                    "alarma_mes": mes,
                    "alarma_anio": anio,
                    "repeat_days": repeat_days,
                    "created_at": time.time(),
                    "_disparada": False,
                }
            )
            self._todo_next_id += 1
            nuevo_real_idx = len(self.todos) - 1
            _, indices_despues = self._todo_view()
            self.todo_selected_idx = (
                indices_despues.index(nuevo_real_idx)
                if nuevo_real_idx in indices_despues
                else max(0, len(self.todos) - 1)
            )
            self.todo_scroll_offset = max(0, self.todo_selected_idx - 5)
        self.todo_edit_mode = False
        self.todo_edit_target = None
        self._todo_save()

    def _draw_todo(self):
        now_str = datetime.datetime.now().strftime("%H:%M:%S")
        if self.todo_edit_mode:
            f = self.todo_edit_field
            es_nota = self.temp_todo_tipo == "nota"
            muestra_recordatorio = (not es_nota) and self.temp_todo_recordarme
            rec_str = "✔ Sí" if self.temp_todo_recordarme else "✘ No"
            hh, mm, dia, mes, anio = self.temp_todo_alarma

            def fmark(n):
                return "►" if f == n else " "

            tipo_str = "Tarea" if not es_nota else "Nota"
            rows = [
                f"{fmark(0)} Tipo       : [{tipo_str}]",
                (
                    f"{fmark(1)} Texto      : {self.temp_todo_texto}_"
                    if f == 1
                    else f"{fmark(1)} Texto      : {self.temp_todo_texto}"
                ),
            ]
            if not es_nota:
                rows.append(f"{fmark(2)} Recordarme : [{rec_str}]")
            if muestra_recordatorio:
                rep_str = "✔ Sí" if self.temp_todo_repetir else "✘ No"
                rows.append(f"{fmark(3)} Repetir    : [{rep_str}]")
                if self.temp_todo_repetir:
                    dias_field_activo = f == 4
                    partes_dias = []
                    for d in range(7):
                        marcado = d in self.temp_todo_days
                        txt = f"[{DIAS_ABBR[d]}]" if marcado else f" {DIAS_ABBR[d]} "
                        if dias_field_activo and d == self.temp_todo_days_cursor:
                            txt = f"»{txt}«" if marcado else f"»{DIAS_ABBR[d]}«"
                        partes_dias.append(txt)
                    rows += [
                        f"{fmark(4)} Días       : {''.join(partes_dias)}",
                        f"{fmark(5)} Hora       : ◄{hh:02d}►",
                        f"{fmark(6)} Minuto     : ◄{mm:02d}►",
                    ]
                else:
                    rows += [
                        f"{fmark(4)} Hora       : ◄{hh:02d}►",
                        f"{fmark(5)} Minuto     : ◄{mm:02d}►",
                        f"{fmark(6)} Día        : ◄{dia:02d}►",
                        f"{fmark(7)} Mes        : ◄{mes:02d}►",
                        f"{fmark(8)} Año        : ◄{anio}►",
                    ]
            helper = (
                ["↑↓:línea  Enter:guardar  Esc:cancelar"]
                if es_nota
                else [
                    "↑↓:línea  Enter:guardar  Esc:cancelar",
                    "Tipo/Recordarme/Repetir: Tab o Space  |  Valores/Días: ←→ Space",
                ]
            )
            self._draw_frame("✎ Editar", rows, helper)
            return

        if self.todo_confirm_delete and self.todos:
            vista, _ = self._todo_view()
            t = vista[self.todo_selected_idx]
            rows = [
                now_str,
                "",
                f"¿Eliminar '{t['texto'][:28]}'?",
                "  y / Enter = Sí    cualquier tecla = No",
            ]
            self._draw_frame("▤ ToDo", rows)
            return

        MAX_VISIBLE = 8
        vista, _ = self._todo_view()
        total = len(vista)
        rows = [now_str, ""]
        if total:
            if self.todo_selected_idx < self.todo_scroll_offset:
                self.todo_scroll_offset = self.todo_selected_idx
            elif self.todo_selected_idx >= self.todo_scroll_offset + MAX_VISIBLE:
                self.todo_scroll_offset = self.todo_selected_idx - MAX_VISIBLE + 1
            visible = vista[
                self.todo_scroll_offset : self.todo_scroll_offset + MAX_VISIBLE
            ]
            for i_rel, t in enumerate(visible):
                i_abs = i_rel + self.todo_scroll_offset
                sel = "►" if i_abs == self.todo_selected_idx else " "
                tipo = t.get("tipo", "tarea")
                if tipo == "nota":
                    icono = "✎"
                else:
                    icono = "✔" if _todo_is_done(t) else "☐"
                if t.get("recordarme"):
                    dias = _repeat_days_normalize(t.get("repeat_days"))
                    if dias:
                        rec = f" ⟳{_repeat_days_str(dias)} {t['alarma_hora']:02d}:{t['alarma_min']:02d}"
                    else:
                        rec = f" ◷{t['alarma_dia']:02d}/{t['alarma_mes']:02d} {t['alarma_hora']:02d}:{t['alarma_min']:02d}"
                else:
                    rec = ""
                texto = t["texto"][:30]
                rows.append(f"{sel} {icono} {texto:<10}{rec}")
            if total > MAX_VISIBLE:
                shown_end = min(self.todo_scroll_offset + MAX_VISIBLE, total)
                rows.append(f"  ({self.todo_scroll_offset + 1}–{shown_end} de {total})")
        else:
            rows.append("<n> para crear tarea")
        helper = [
            "n:nuevo  ↑↓:nav  ←→:mover  Space:✔/○  e:editar  d:borrar  x:alarma",
            "o:notas",
        ]
        self._draw_frame("▤ ToDo", rows, helper)
        if self._notes_panel_open:
            self._draw_notes_panel()

    # ──────────────────────────────────────────
    #  VIEW 7 — CONFIGURACIÓN
    # ──────────────────────────────────────────

    def _config_visible_items(self):
        tab = self._config_tabs[self.config_tab_idx]
        tema_actual = self.config.get("tema", "clasico")
        modo_sonido = self.config.get("sonido_modo", "default")
        out = []
        for real_idx, item in enumerate(self._config_items):
            key, label, group, tipo, opciones = item
            if group != tab:
                continue
            if key.startswith("custom_color") and tema_actual != "custom":
                continue
            if not self.config.get("sonido", True) and key in (
                "sonido_modo",
                "sonido_archivo",
                "sonido_custom_path",
            ):
                continue
            if key == "sonido_archivo" and modo_sonido != "default":
                continue
            if key == "sonido_custom_path" and modo_sonido != "custom":
                continue
            out.append((real_idx, item))
        return out

    def _input_config_text(self, key):
        if key in (ord("\n"), 10, 13):
            self.config[self.config_text_edit_key] = self.config_text_edit_value
            self.config_text_edit = False
            self.config_text_edit_key = None
            _save_data(
                self.alarm_lists, self.timers, self.pomodoro, self.todos, self.config
            )
        elif key == 27:
            self.config_text_edit = False
            self.config_text_edit_key = None
        elif key in (curses.KEY_BACKSPACE, 127, 8):
            self.config_text_edit_value = self.config_text_edit_value[:-1]
        elif 32 <= key <= 126:
            self.config_text_edit_value += chr(key)

    def _input_config(self, key):
        if self.config_text_edit:
            self._input_config_text(key)
            return
        visibles = self._config_visible_items()
        n = len(visibles)
        if key == curses.KEY_LEFT:
            self.config_tab_idx = (self.config_tab_idx - 1) % len(self._config_tabs)
            self.config_selected_idx = 0
            if self._config_tabs[self.config_tab_idx] == "Sonido":
                self._sound_list_files(force_refresh=True)
            return
        if key == curses.KEY_RIGHT:
            self.config_tab_idx = (self.config_tab_idx + 1) % len(self._config_tabs)
            self.config_selected_idx = 0
            if self._config_tabs[self.config_tab_idx] == "Sonido":
                self._sound_list_files(force_refresh=True)
            return
        if n == 0:
            return
        if key == curses.KEY_DOWN:
            self.config_selected_idx = (self.config_selected_idx + 1) % n
        elif key == curses.KEY_UP:
            self.config_selected_idx = (self.config_selected_idx - 1) % n
        elif key in (ord(" "), ord("\n"), 10, 13):
            real_idx, (k, _, _, tipo, opciones) = visibles[
                min(self.config_selected_idx, n - 1)
            ]
            if tipo == "action":
                if opciones == "backup":
                    self._backup_data()
                elif opciones == "restore":
                    self._browser_mode = "restore"
                    self._browser_open = True
                    self._browser_cwd = os.path.expanduser("~")
                    self._browser_selected_idx = 0
                    self._browser_refresh_entries()
                elif opciones == "log_view":
                    self._open_log_viewer()
                elif opciones == "log_export":
                    self._export_log()
                return
            if tipo == "text":
                self.config_text_edit = True
                self.config_text_edit_key = k
                self.config_text_edit_value = str(self.config.get(k, ""))
                return
            if tipo == "soundbrowser":
                self._browser_mode = "sound"
                self._browser_open = True
                actual = self.config.get("sonido_custom_path")
                self._browser_cwd = (
                    os.path.dirname(actual)
                    if actual and os.path.exists(os.path.dirname(actual))
                    else os.path.expanduser("~")
                )
                self._browser_selected_idx = 0
                self._browser_refresh_entries()
                return
            if tipo == "soundmode":
                idx = opciones.index(self.config[k])
                self.config[k] = opciones[(idx + 1) % len(opciones)]
                self.config_selected_idx = 0
            elif tipo == "soundfile":
                archivos = self._sound_list_files()
                actual = self.config.get("sonido_archivo")
                opciones_ciclo = [None] + archivos
                try:
                    idx = opciones_ciclo.index(actual)
                except ValueError:
                    idx = 0
                self.config["sonido_archivo"] = opciones_ciclo[
                    (idx + 1) % len(opciones_ciclo)
                ]
                self._kill_audio()
                nuevo = self.config["sonido_archivo"]
                sound_path = os.path.join(self._AUDIOS_DIR, nuevo) if nuevo else None
                self._audio_proc = try_beep(sound_path)
            elif tipo == "choice":
                idx = opciones.index(self.config[k])
                self.config[k] = opciones[(idx + 1) % len(opciones)]
            else:
                self.config[k] = not self.config[k]
                if k == "sonido" and not self.config[k]:
                    self.config_selected_idx = 0
            if k == "clima_activo":
                self._weather_on_toggle()
            if k == "tema":
                self._apply_theme()
                self.config_selected_idx = 0
            if k.startswith("custom_color"):
                self._apply_theme()
            _save_data(
                self.alarm_lists, self.timers, self.pomodoro, self.todos, self.config
            )

    def _draw_config(self):
        if self.config_text_edit:
            rows = [
                f"Valor: {self.config_text_edit_value}_",
                "",
                "Enter:guardar  Esc:cancelar",
            ]
            self._draw_frame("✎ Editar valor", rows)
            return
        visibles = self._config_visible_items()
        n = len(visibles)
        if n and self.config_selected_idx >= n:
            self.config_selected_idx = n - 1
        tab_parts = []
        for i, nombre_tab in enumerate(self._config_tabs):
            if i == self.config_tab_idx:
                tab_parts.append(f"[{nombre_tab}]")
            else:
                tab_parts.append(f" {nombre_tab} ")
        rows = [" ".join(tab_parts), ""]
        if n == 0:
            rows.append("(sin opciones en esta categoría)")
        else:
            for i, (real_idx, (key, label, group, tipo, opciones)) in enumerate(
                visibles
            ):
                sel = "►" if i == self.config_selected_idx else " "
                if tipo == "soundmode":
                    val = (
                        "Carpeta default"
                        if self.config[key] == "default"
                        else "Archivo a mano"
                    )
                elif tipo == "soundfile":
                    archivo = self.config.get("sonido_archivo")
                    val = archivo if archivo else "Beep default"
                elif tipo == "soundbrowser":
                    path = self.config.get("sonido_custom_path")
                    val = (
                        os.path.basename(path)
                        if path
                        else "(sin elegir, Enter para buscar)"
                    )
                elif tipo == "text":
                    val = self.config.get(key, "") or "(vacío = IP)"
                elif tipo == "choice":
                    val = self.config[key]
                    if key == "clima_intervalo_min":
                        val = f"{val} min"
                    elif key == "clima_retry_segs":
                        val = f"{val}s"
                    elif key == "tema":
                        val = val.replace("_", " ").title()
                elif tipo == "action":
                    val = "Enter para ejecutar"
                else:
                    val = "✔ ON " if self.config[key] else "✘ OFF"
                rows.append(f"{sel} {label:26s} [{val}]")
        helper = ["←→:categoría  ↑↓:nav  Space/Enter:toggle/ciclar/elegir"]
        if self._config_tabs[self.config_tab_idx] == "Sonido":
            helper.append(f"Carpeta default: {self._AUDIOS_DIR}")
        self._draw_frame("⚙ Configuración", rows, helper)

    # ──────────────────────────────────────────
    #  RELOJ MUNDIAL — helpers
    # ──────────────────────────────────────────

    def _wc_save(self):
        self.config["world_clocks"] = list(self.world_clocks)
        _save_data(
            self.alarm_lists, self.timers, self.pomodoro, self.todos, self.config
        )

    def _wc_refresh_picker_list(self):
        ordenada = _wc_sorted_zones()
        texto = self.wc_picker_filter_text.strip().lower()
        if self.wc_picker_filter_active and texto:
            ordenada = [
                z
                for z in ordenada
                if texto in z[1].lower()
                or texto in z[2].lower()
                or texto in z[3].lower()
            ]
        self.wc_picker_list = ordenada
        if not self.wc_picker_list:
            self.wc_picker_idx = 0
        else:
            self.wc_picker_idx = min(self.wc_picker_idx, len(self.wc_picker_list) - 1)
        self.wc_picker_scroll = 0

    def _wc_open_picker(self, edit_target=None):
        self.wc_picker_open = True
        self.wc_picker_edit_target = edit_target
        self.wc_picker_filter_active = False
        self.wc_picker_filter_text = ""
        self.wc_picker_idx = 0
        self._wc_refresh_picker_list()
        if edit_target is not None:
            zona_actual = self.world_clocks[edit_target]["zona"]
            for i, z in enumerate(self.wc_picker_list):
                if z[0] == zona_actual:
                    self.wc_picker_idx = i
                    break

    def _wc_close_picker(self):
        self.wc_picker_open = False
        self.wc_picker_edit_target = None
        self.wc_picker_filter_active = False
        self.wc_picker_filter_text = ""

    def _wc_picker_confirm_zone(self):
        if not self.wc_picker_list:
            return
        zona = self.wc_picker_list[self.wc_picker_idx]
        self.temp_wc_zona = zona
        if self.wc_picker_edit_target is not None:
            self.temp_wc_apodo = self.world_clocks[self.wc_picker_edit_target]["apodo"]
        else:
            self.temp_wc_apodo = zona[4]
        self.wc_apodo_mode = True
        self.wc_picker_open = False

    def _wc_commit_apodo(self):
        apodo = self.temp_wc_apodo.strip() or self.temp_wc_zona[4]
        entry = {"zona": self.temp_wc_zona[0], "apodo": apodo}
        if self.wc_picker_edit_target is not None:
            self.world_clocks[self.wc_picker_edit_target] = entry
        else:
            self.world_clocks.append(entry)
        self._wc_save()
        self.wc_apodo_mode = False
        self.temp_wc_zona = None
        self.wc_picker_edit_target = None

    def _wc_cancel_all(self):
        self.wc_picker_open = False
        self.wc_apodo_mode = False
        self.wc_picker_edit_target = None
        self.wc_picker_filter_active = False
        self.wc_picker_filter_text = ""
        self.temp_wc_zona = None

    def _draw_wc_picker(self):
        titulo = (
            "Editar reloj mundial"
            if self.wc_picker_edit_target is not None
            else "Nuevo reloj mundial"
        )
        MAX_VIS = 10
        lst = self.wc_picker_list
        n = len(lst)
        visible = lst[self.wc_picker_scroll : self.wc_picker_scroll + MAX_VIS]
        rows = []
        for i_rel, z in enumerate(visible):
            i_abs = i_rel + self.wc_picker_scroll
            sel = "►" if i_abs == self.wc_picker_idx else " "
            info = self._wc_offset_info_cached(z[0])
            diff_txt = f" (UTC {_wc_format_diff(info[1])})" if info else ""
            rows.append(f"{sel} {z[1]} / {z[2]}{diff_txt}")
        if not rows:
            rows.append("  (sin resultados)")
        if self.wc_picker_filter_active:
            rows.append(f"Filtro: {self.wc_picker_filter_text}_")
        if n:
            rows.append(f"({self.wc_picker_idx + 1}/{n})")
        if self.wc_picker_filter_active:
            helper = ["Escribiendo filtro  Enter:elegir  Esc:salir del filtro"]
        else:
            helper = ["↑↓:nav  f:filtro  Enter:elegir  Esc:cancelar"]
        self._draw_frame(
            titulo, rows, helper, weather_line=self._weather_display_line()
        )

    def _draw_wc_apodo(self):
        z = self.temp_wc_zona
        zona_txt = f"{z[1]} / {z[2]} / {z[3]}" if z else "?"
        info = self._wc_offset_info_cached(z[0]) if z else None
        utc_txt = f"UTC {_wc_format_diff(info[1])}" if info else "?"
        rows = [
            f"Zona: {zona_txt}",
            f"Diferencia: {utc_txt}",
            f"Nombre: {self.temp_wc_apodo}_",
        ]
        helper = ["Enter:guardar  Esc:cancelar"]
        self._draw_frame(
            "✎ Nombre", rows, helper, weather_line=self._weather_display_line()
        )

    # ──────────────────────────────────────────
    #  CLIMA — helpers
    # ──────────────────────────────────────────

    def _weather_on_toggle(self):
        if self.config.get("clima_activo", False):
            self._weather_start()
        else:
            self._weather_stop_thread()

    def _weather_start(self):
        if self._weather_thread is not None and self._weather_thread.is_alive():
            return
        self._weather_stop.clear()
        self._weather_force.clear()
        self._weather_thread = threading.Thread(target=self._weather_loop, daemon=True)
        self._weather_thread.start()

    def _weather_stop_thread(self):
        self._weather_stop.set()

    def _weather_request_refresh(self):
        if self.config.get("clima_activo", False):
            self._weather_force.set()

    def _seconds_until_next_slot(self, intervalo_min):
        now = datetime.datetime.now()
        slot = max(1, int(intervalo_min))
        minutes_since_midnight = now.hour * 60 + now.minute
        next_slot_minute = ((minutes_since_midnight // slot) + 1) * slot
        next_dt = now.replace(second=0, microsecond=0) + datetime.timedelta(
            minutes=(next_slot_minute - minutes_since_midnight)
        )
        return max(1.0, (next_dt - now).total_seconds())

    def _weather_loop(self):
        with self._weather_lock:
            cached_epoch = self._weather_epoch
            intervalo = self.config.get("clima_intervalo_min", 60)
            cache_is_fresh = (
                cached_epoch is not None
                and (time.time() - cached_epoch) < intervalo * 60
            )
        if not cache_is_fresh:
            self._weather_attempt_with_retries()
        while not self._weather_stop.is_set():
            intervalo = self.config.get("clima_intervalo_min", 60)
            wait_secs = self._seconds_until_next_slot(intervalo)
            waited = 0.0
            while waited < wait_secs:
                if self._weather_stop.is_set():
                    return
                if self._weather_force.is_set():
                    self._weather_force.clear()
                    break
                time.sleep(1.0)
                waited += 1.0
            self._weather_attempt_with_retries()

    def _weather_attempt_with_retries(self):
        retry_max = max(0, int(self.config.get("clima_retry_max", 3)))
        retry_segs = max(1, int(self.config.get("clima_retry_segs", 60)))
        ok = self._weather_do_fetch()
        if ok:
            with self._weather_lock:
                self._weather_retry_count = 0
                self._weather_retry_deadline = None
            return
        attempt = 0
        while attempt < retry_max:
            if self._weather_stop.is_set():
                return
            attempt += 1
            with self._weather_lock:
                self._weather_retry_count = attempt
                self._weather_retry_deadline = time.monotonic() + retry_segs
            waited = 0.0
            while waited < retry_segs:
                if self._weather_stop.is_set():
                    return
                if self._weather_force.is_set():
                    self._weather_force.clear()
                    break
                time.sleep(1.0)
                waited += 1.0
            ok = self._weather_do_fetch()
            if ok:
                with self._weather_lock:
                    self._weather_retry_count = 0
                    self._weather_retry_deadline = None
                return
        with self._weather_lock:
            self._weather_retry_count = 0
            self._weather_retry_deadline = None
            self._weather_ok = False
            self._weather_text = "Error en la red"

    def _weather_do_fetch(self):
        formato = self.config.get("clima_formato", "compacto")
        location = self.config.get("clima_ubicacion", "")
        ok, text = fetch_weather(location, formato)
        now_epoch = time.time()
        with self._weather_lock:
            self._weather_ok = ok
            self._weather_text = text
            self._weather_epoch = now_epoch
        if ok:
            _save_data(
                self.alarm_lists,
                self.timers,
                self.pomodoro,
                self.todos,
                self.config,
                weather_cache={"text": text, "ok": ok, "ts": now_epoch},
            )
        return ok

    def _weather_snapshot(self):
        with self._weather_lock:
            return (
                self._weather_ok,
                self._weather_text,
                self._weather_epoch,
                self._weather_retry_count,
                self._weather_retry_deadline,
            )

    @staticmethod
    def _format_age(epoch):
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
        days = hours // 24
        return f"hace {days} d"

    @staticmethod
    def _format_until(target_dt):
        diff = (target_dt - datetime.datetime.now()).total_seconds()
        venció = diff < 0
        secs = abs(diff)
        if secs < 60:
            cuerpo = "instantes"
        else:
            mins = int(secs // 60)
            if mins < 60:
                cuerpo = f"{mins} min"
            else:
                hours = mins // 60
                if hours < 24:
                    cuerpo = f"{hours} h"
                else:
                    days = hours // 24
                    cuerpo = f"{days} d"
        return f"venció hace {cuerpo}" if venció else f"faltan {cuerpo}"

    def _weather_display_line(self, show_age=True):
        if not self.config.get("clima_activo", False):
            return None
        ok, text, epoch, retry_count, retry_deadline = self._weather_snapshot()
        if retry_count > 0 and retry_deadline is not None:
            retry_max = self.config.get("clima_retry_max", 3)
            secs_left = max(0, int(retry_deadline - time.monotonic()))
            return f"※ [!] Reintento {retry_count}/{retry_max} ({secs_left}s)"
        if text is None:
            return "※ Clima: cargando…"
        prefix = "※ " if ok else "※ [!] "
        suffix = ""
        if show_age and self.config.get("clima_mostrar_hace", True):
            age = self._format_age(epoch)
            suffix = f"  ({age})" if age else ""
        return f"{prefix}{text}{suffix}"

    # ──────────────────────────────────────────
    #  BROWSER
    # ──────────────────────────────────────────

    def _browser_refresh_entries(self):
        try:
            con_tipo = []
            for nombre in os.listdir(self._browser_cwd):
                full = os.path.join(self._browser_cwd, nombre)
                if os.path.isdir(full):
                    con_tipo.append((nombre, True))
                elif self._browser_mode == "restore" and nombre.lower().endswith(
                    ".json"
                ):
                    con_tipo.append((nombre, False))
                elif self._browser_mode == "sound" and nombre.lower().endswith(
                    _SOUND_EXTS
                ):
                    con_tipo.append((nombre, False))
            con_tipo.sort(key=lambda x: (not x[1], x[0].lower()))
        except OSError:
            con_tipo = []
        self._browser_entries = con_tipo
        if self._browser_selected_idx >= len(con_tipo):
            self._browser_selected_idx = max(0, len(con_tipo) - 1)

    def _input_browser(self, key):
        n = len(self._browser_entries)
        if key == 27:
            padre = os.path.dirname(self._browser_cwd)
            if padre and padre != self._browser_cwd:
                self._browser_cwd = padre
                self._browser_selected_idx = 0
                self._browser_refresh_entries()
            else:
                self._browser_open = False
            return
        if n == 0:
            return
        if key == curses.KEY_DOWN:
            self._browser_selected_idx = (self._browser_selected_idx + 1) % n
        elif key == curses.KEY_UP:
            self._browser_selected_idx = (self._browser_selected_idx - 1) % n
        elif key in (ord("\n"), 10, 13):
            nombre, es_dir = self._browser_entries[self._browser_selected_idx]
            full = os.path.join(self._browser_cwd, nombre)
            if es_dir:
                self._browser_cwd = full
                self._browser_selected_idx = 0
                self._browser_refresh_entries()
            elif self._browser_mode == "restore":
                self._restore_from_file(full)
            else:
                self.config["sonido_custom_path"] = full
                self.config["sonido_modo"] = "custom"
                self._browser_open = False
                self._kill_audio()
                self._audio_proc = try_beep(full)
                _save_data(
                    self.alarm_lists,
                    self.timers,
                    self.pomodoro,
                    self.todos,
                    self.config,
                )

    def _draw_browser(self):
        sh, sw = self.stdscr.getmaxyx()
        panel_w = min(70, sw - 4)
        panel_h = min(24, sh - 4)
        px = (sw - panel_w) // 2
        py = (sh - panel_h) // 2
        attr_marco = curses.color_pair(PAIR_MARCO)
        attr_texto = curses.color_pair(PAIR_TEXTO)
        attr_helper = curses.color_pair(PAIR_HELPERS)
        attr_sel = curses.color_pair(PAIR_TEXTO) | curses.A_BOLD | curses.A_REVERSE

        def safe(y, x, s, a=0):
            if 0 <= y < sh and 0 <= x < sw - 1:
                try:
                    self.stdscr.addstr(y, x, s[: sw - x - 1], a)
                except curses.error:
                    pass

        safe(py, px, "┌" + "─" * (panel_w - 2) + "┐", attr_marco)
        safe(py + panel_h - 1, px, "└" + "─" * (panel_w - 2) + "┘", attr_marco)
        for r in range(1, panel_h - 1):
            safe(py + r, px, "│", attr_marco)
            safe(py + r, px + panel_w - 1, "│", attr_marco)
        titulo = (
            "[ Restaurar backup .json ]"
            if self._browser_mode == "restore"
            else "[ Elegir sonido ]"
        )
        safe(py, px + (panel_w - len(titulo)) // 2, titulo, attr_marco | curses.A_BOLD)
        ruta = self._browser_cwd
        content_w = panel_w - 4
        safe(py + 1, px + 2, ruta[-content_w:], attr_helper)
        list_start = py + 3
        list_h = panel_h - 5
        if not self._browser_entries:
            safe(list_start, px + 2, "(carpeta vacía)", attr_helper)
        else:
            n = len(self._browser_entries)
            scroll = max(0, min(self._browser_selected_idx - list_h // 2, n - list_h))
            for row in range(list_h):
                i = scroll + row
                if i >= n:
                    break
                nombre, es_dir = self._browser_entries[i]
                if es_dir:
                    icono = "▸"
                elif self._browser_mode == "restore":
                    icono = "▤"
                else:
                    icono = "♪"
                es_sel = i == self._browser_selected_idx
                attr = attr_sel if es_sel else attr_texto
                marca = "►" if es_sel else " "
                safe(
                    list_start + row,
                    px + 2,
                    f"{marca} {icono} {nombre}"[:content_w].ljust(content_w),
                    attr,
                )
        hint = "↑↓:nav  Enter:abrir/elegir  Esc:subir nivel/cerrar"
        safe(
            py + panel_h - 1, px + max(1, (panel_w - len(hint)) // 2), hint, attr_helper
        )

    # ──────────────────────────────────────────
    #  BACKUP / RESTORE
    # ──────────────────────────────────────────

    def _backup_data(self):
        ts = datetime.datetime.now().strftime("%Y-%m-%d_%H%M")
        dest = os.path.expanduser(f"~/clock_backup_{ts}.json")
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                contenido = f.read()
            with open(dest, "w", encoding="utf-8") as f:
                f.write(contenido)
            self._show_alert("✓ Backup creado", f"Guardado en {dest}")
        except OSError as e:
            self._show_alert("⚠ Backup falló", str(e.strerror or e))

    def _restore_from_file(self, path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                contenido = f.read()
            json.loads(contenido)
        except (OSError, json.JSONDecodeError) as e:
            self._browser_open = False
            self._show_alert("⚠ Restaurar falló", f"Archivo inválido: {e}")
            return
        try:
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                f.write(contenido)
        except OSError as e:
            self._browser_open = False
            self._show_alert("⚠ Restaurar falló", str(e.strerror or e))
            return
        self._kill_audio()
        self._weather_stop_thread()
        curses.endwin()
        os.execv(sys.executable, [sys.executable] + sys.argv)

    # ──────────────────────────────────────────
    #  LOG VIEWER
    # ──────────────────────────────────────────

    def _open_log_viewer(self):
        entries = list(reversed(_log_read_all()))
        self._log_viewer_entries = entries
        self._log_viewer_idx = 0
        self._log_viewer_scroll = 0
        self._log_viewer_open = True
        _log_mark_all_seen()

    def _export_log(self):
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

    def _input_log_viewer(self, key):
        n = len(self._log_viewer_entries)
        if key in (27, ord(" "), ord("\n"), 10, 13):
            self._log_viewer_open = False
            return
        if n == 0:
            return
        if key == curses.KEY_DOWN:
            self._log_viewer_idx = min(self._log_viewer_idx + 1, n - 1)
        elif key == curses.KEY_UP:
            self._log_viewer_idx = max(self._log_viewer_idx - 1, 0)

    def _draw_log_viewer(self):
        sh, sw = self.stdscr.getmaxyx()
        entries = self._log_viewer_entries
        n = len(entries)
        box_w = min(70, max(40, sw - 6))
        box_h = min(20, max(8, sh - 4))
        sy = max(0, (sh - box_h) // 2)
        sx = max(0, (sw - box_w) // 2)
        content_w = box_w - 4
        bg_attr = curses.color_pair(_HELP_BG_PAIR)
        marco_attr = curses.color_pair(_HELP_BG_PAIR) | curses.A_BOLD
        texto_attr = curses.color_pair(_HELP_BG_PAIR)
        sel_attr = curses.color_pair(_HELP_BG_PAIR) | curses.A_REVERSE
        helper_attr = curses.color_pair(_HELP_BG_PAIR) | curses.A_DIM

        def safe(y, x, s, a=0):
            if 0 <= y < sh and 0 <= x < sw - 1:
                try:
                    self.stdscr.addstr(y, x, s[: sw - x - 1], a)
                except curses.error:
                    pass

        for r in range(box_h):
            safe(sy + r, sx, " " * box_w, bg_attr)
        safe(sy, sx, "┌" + "─" * (box_w - 2) + "┐", marco_attr)
        safe(sy + box_h - 1, sx, "└" + "─" * (box_w - 2) + "┘", marco_attr)
        for r in range(1, box_h - 1):
            safe(sy + r, sx, "│", marco_attr)
            safe(sy + r, sx + box_w - 1, "│", marco_attr)
        titulo = "[ ⚠ Log de errores ]"
        safe(sy, sx + (box_w - len(titulo)) // 2, titulo, marco_attr)
        if n == 0:
            msg = "(sin errores registrados)"
            safe(sy + 3, sx + (box_w - len(msg)) // 2, msg, helper_attr)
        else:
            MAX_VISIBLE = box_h - 4
            if self._log_viewer_idx < self._log_viewer_scroll:
                self._log_viewer_scroll = self._log_viewer_idx
            elif self._log_viewer_idx >= self._log_viewer_scroll + MAX_VISIBLE:
                self._log_viewer_scroll = self._log_viewer_idx - MAX_VISIBLE + 1
            visibles = entries[
                self._log_viewer_scroll : self._log_viewer_scroll + MAX_VISIBLE
            ]
            for i_rel, e in enumerate(visibles):
                i_abs = i_rel + self._log_viewer_scroll
                es_sel = i_abs == self._log_viewer_idx
                ts = e.get("ts")
                fecha = (
                    datetime.datetime.fromtimestamp(ts).strftime("%d/%m %H:%M")
                    if ts
                    else "??/?? ??:??"
                )
                msg = str(e.get("msg", ""))[: content_w - 13]
                linea = f"{fecha}  {msg}"
                a = sel_attr if es_sel else texto_attr
                safe(sy + 2 + i_rel, sx + 2, linea.ljust(content_w)[:content_w], a)
            ind = f"({self._log_viewer_idx + 1}/{n})"
            safe(sy + box_h - 2, sx + (box_w - len(ind)) // 2, ind, helper_attr)
        hint = "↑↓:nav  Esc/Enter:cerrar"
        safe(sy + box_h - 1, sx + (box_w - len(hint)) // 2, hint, helper_attr)

    # ──────────────────────────────────────────
    #  PANEL DE NOTAS
    # ──────────────────────────────────────────

    def _draw_notes_panel(self):
        sh, sw = self.stdscr.getmaxyx()
        items = self.todos
        if items:
            self._notes_selected_idx = min(self._notes_selected_idx, len(items) - 1)
        else:
            self._notes_selected_idx = 0
        panel_w = min(36, max(24, sw // 3))
        panel_h = sh - 6
        px = sw - panel_w - 1
        py = 3
        attr_marco = curses.color_pair(PAIR_MARCO)
        attr_texto = curses.color_pair(PAIR_TEXTO)
        attr_helper = curses.color_pair(PAIR_HELPERS)
        attr_sel = curses.color_pair(PAIR_TEXTO) | curses.A_BOLD | curses.A_REVERSE

        def safe(y, x, s, a=0):
            if 0 <= y < sh and 0 <= x < sw - 1:
                try:
                    self.stdscr.addstr(y, x, s[: sw - x - 1], a)
                except curses.error:
                    pass

        safe(py, px, "┌" + "─" * (panel_w - 2) + "┐", attr_marco)
        safe(py + panel_h - 1, px, "└" + "─" * (panel_w - 2) + "┘", attr_marco)
        for r in range(1, panel_h - 1):
            safe(py + r, px, "│", attr_marco)
            safe(py + r, px + panel_w - 1, "│", attr_marco)
        titulo = "[ ▤ Notas y Tareas ]"
        tx = px + (panel_w - len(titulo)) // 2
        safe(py, tx, titulo, attr_marco | curses.A_BOLD)
        content_w = panel_w - 4

        def _item_alarma_dt(item):
            try:
                return datetime.datetime(
                    item["alarma_anio"],
                    item["alarma_mes"],
                    item["alarma_dia"],
                    item["alarma_hora"],
                    item["alarma_min"],
                )
            except (KeyError, ValueError):
                return None

        def _line1(item):
            tipo = item.get("tipo", "tarea")
            if tipo == "nota":
                return f"✎ {item['texto']}"
            check = "✓" if _todo_is_done(item) else "□"
            sufijo = " ⧗" if item.get("recordarme") else ""
            return f"{check} {item['texto']}{sufijo}"

        def _line2(item):
            tipo = item.get("tipo", "tarea")
            if tipo == "nota":
                return self._format_age(item.get("created_at"))
            if item.get("recordarme"):
                dias = _repeat_days_normalize(item.get("repeat_days"))
                if dias:
                    return f"repetir {_repeat_days_str(dias)} a las {item['alarma_hora']:02d}:{item['alarma_min']:02d}"
                dt = _item_alarma_dt(item)
                return self._format_until(dt) if dt else ""
            return f"creado {self._format_age(item.get('created_at'))}"

        if not items:
            msg = "(sin items)"
            safe(py + 2, px + (panel_w - len(msg)) // 2, msg, attr_helper)
        else:
            if self._notes_selected_idx < self._notes_scroll:
                self._notes_scroll = self._notes_selected_idx

            def _row_height(item, ancho_disp):
                texto_len = len(item["texto"]) + 2
                h = max(1, -(-texto_len // content_w))
                if item["id"] in self._notes_expanded:
                    h += 1
                return h

            def _selection_visible(scroll_from):
                row_y = py + 2
                for i in range(scroll_from, len(items)):
                    if row_y >= py + panel_h - 2:
                        return False
                    if i == self._notes_selected_idx:
                        return True
                    row_y += _row_height(items[i], content_w)
                    if i < len(items) - 1:
                        row_y += 1
                return False

            guard = 0
            while not _selection_visible(self._notes_scroll) and guard < len(items):
                self._notes_scroll += 1
                guard += 1

            row_y = py + 2
            shown = 0
            for i in range(self._notes_scroll, len(items)):
                if row_y >= py + panel_h - 2:
                    break
                item = items[i]
                es_sel = i == self._notes_selected_idx
                marca = "►" if es_sel else " "
                attr_linea = attr_sel if es_sel else attr_texto
                texto = _line1(item)
                primera_linea = True
                while texto and row_y < py + panel_h - 2:
                    ancho_disp = content_w - 1
                    prefijo = marca if primera_linea else " "
                    safe(
                        row_y,
                        px + 2,
                        (prefijo + texto[:ancho_disp].ljust(ancho_disp)),
                        attr_linea,
                    )
                    texto = texto[ancho_disp:]
                    row_y += 1
                    primera_linea = False
                if item["id"] in self._notes_expanded and row_y < py + panel_h - 2:
                    detalle = _line2(item)
                    if detalle:
                        safe(row_y, px + 2, f"  {detalle}"[:content_w], attr_helper)
                    row_y += 1
                if i < len(items) - 1 and row_y < py + panel_h - 2:
                    safe(row_y, px + 2, ("─" * content_w)[:content_w], attr_helper)
                    row_y += 1
                shown += 1
            if len(items) > shown or self._notes_scroll > 0:
                ind = f"({self._notes_selected_idx + 1}/{len(items)})"
                safe(py + panel_h - 2, px + (panel_w - len(ind)) // 2, ind, attr_helper)
        hint = "↑↓:nav  Space:✔/○  o/Esc:cerrar"
        safe(py + panel_h - 1, px + (panel_w - len(hint)) // 2, hint, attr_helper)

    # ──────────────────────────────────────────
    #  HELP OVERLAY
    # ──────────────────────────────────────────

    _HELP_BY_VIEW = {
        0: ["Vista de solo lectura: resumen de todo lo activo"],
        1: ["↑↓:sección  ←→:alternar WC  n:+WC  e:editar  d:borrar  u:clima"],
        2: ["n:nueva  ↑↓:nav  Space:on/off  e:editar  d:borrar"],
        3: ["↑↓:fila  Tab:cicla  ←→:valor  Space:play/pause  R:reset"],
        4: [
            "n:nuevo  ↑↓:nav  Tab:campo  ←→:valor  Space:play/pause  e:editar  d:borrar  R:reset"
        ],
        5: ["Space:play/pause  Tab:marcar lap  d:borrar último  R:reset"],
        6: ["n:nuevo  ↑↓:nav  ←→:mover  Space:✔/○  e:editar  d:borrar  x:alarma"],
        7: ["←→:categoría  ↑↓:nav  Enter/Space:cambiar"],
    }

    def _draw_help_overlay(self):
        sh, sw = self.stdscr.getmaxyx()
        vista_lines = self._HELP_BY_VIEW.get(self.current_view, [])
        global_lines = [
            "q:salir   0-7:cambiar vista   o:panel de notas",
            "Esc:pause/play global   ?:esta ayuda   hjkl = ←↓↑→",
            "n:nuevo  e:editar  d:borrar(y)  R:reset  x:toggle",
        ]
        lines = ["Comandos de esta vista:"] + vista_lines
        lines += ["", "─" * 36, "", "Comandos globales:"] + global_lines
        box_w = min(max(len(l) for l in lines) + 6, sw - 4)
        box_h = len(lines) + 4
        sy = max(0, (sh - box_h) // 2)
        sx = max(0, (sw - box_w) // 2)

        def safe(y, x, s, a=0):
            if 0 <= y < sh and 0 <= x < sw - 1:
                try:
                    self.stdscr.addstr(y, x, s[: sw - x - 1], a)
                except curses.error:
                    pass

        bg_attr = curses.color_pair(_HELP_BG_PAIR)
        marco_attr = curses.color_pair(_HELP_BG_PAIR) | curses.A_BOLD
        texto_attr = curses.color_pair(_HELP_BG_PAIR)
        helper_attr = curses.color_pair(_HELP_BG_PAIR) | curses.A_DIM
        for r in range(box_h):
            safe(sy + r, sx, " " * box_w, bg_attr)
        safe(sy, sx, "┌" + "─" * (box_w - 2) + "┐", marco_attr)
        safe(sy + box_h - 1, sx, "└" + "─" * (box_w - 2) + "┘", marco_attr)
        for r in range(1, box_h - 1):
            safe(sy + r, sx, "│", marco_attr)
            safe(sy + r, sx + box_w - 1, "│", marco_attr)
        titulo = "[ ? Ayuda ]"
        safe(sy, sx + (box_w - len(titulo)) // 2, titulo, marco_attr)
        for i, line in enumerate(lines):
            a = (
                helper_attr
                if (line.startswith("Comandos") or line.startswith("─"))
                else texto_attr
            )
            safe(sy + 2 + i, sx + 3, line[: box_w - 6], a)
        hint = "(cualquier tecla para cerrar)"
        safe(sy + box_h - 1, sx + (box_w - len(hint)) // 2, hint, helper_attr)

    # ──────────────────────────────────────────
    #  GLOBAL ACTIONS (FIX: toggle real)
    # ──────────────────────────────────────────

    def _global_pause_play(self):
        if not self._global_paused:
            if self.pomodoro["is_active"]:
                self.pomodoro["is_active"] = False
                self._pomo_last_tick = None
            for t in self.timers:
                if t.get("active"):
                    t["active"] = False
                    t["last_tick"] = None
            self._global_paused = True
        else:
            if self.pomodoro["started"] and self.pomodoro["timer_value"] > 0:
                self.pomodoro["is_active"] = True
                self._pomo_last_tick = time.monotonic()
            for t in self.timers:
                if t.get("started") and t.get("remaining", 0) > 0 and not t["active"]:
                    t["active"] = True
                    t["last_tick"] = time.monotonic()
            self._global_paused = False


# ──────────────────────────────────────────────
#  ENTRY POINT
# ──────────────────────────────────────────────


def main():
    try:
        curses.wrapper(lambda stdscr: ClockApp(stdscr).run())
    except Exception as e:
        _log_error(f"Crash no manejado: {e}", traceback.format_exc())
        print(f"clock: ocurrió un error inesperado. Detalle en {LOG_FILE}")
        sys.exit(1)


if __name__ == "__main__":
    main()
