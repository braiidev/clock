"""Catalogo de zonas horarias mundiales y utilidades de offset UTC.

Cada zona es una tupla:
    (IANA, ciudad, país, continente, código)
El codigo es la abreviatura corta mostrada en pantalla.

Las funciones de offset son puras: reciben la zona y un instante UTC de
referencia y devuelven el dato sin acceder a la UI.
"""

from __future__ import annotations

import datetime
from zoneinfo import ZoneInfo

WORLD_ZONES: list[tuple[str, str, str, str, str]] = [
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


def _wc_zone_lookup(iana: str) -> tuple[str, str, str, str, str]:
    """Devuelve la tupla completa de una zona dado su identificador IANA."""
    for z in WORLD_ZONES:
        if z[0] == iana:
            return z
    return (iana, iana, "?", "?", iana[:4].upper())


def _wc_offset_info(
    iana: str, ref: datetime.datetime | None = None
) -> tuple[datetime.datetime, int] | None:
    """Devuelve (hora local en la zona, diferencia en min respecto a local).

    Si la zona IANA es inválida devuelve None.
    """
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


def _wc_format_diff(diff_min: int) -> str:
    """Formatea una diferencia en minutos como '+H.MM' o '-H'."""
    sign = "+" if diff_min >= 0 else "-"
    a = abs(diff_min)
    h, m = divmod(a, 60)
    return f"{sign}{h}.{m:02d}" if m else f"{sign}{h}"


def _wc_sorted_zones(
    zonas: list[tuple[str, str, str, str, str]] | None = None,
    ref: datetime.datetime | None = None,
) -> list[tuple[str, str, str, str, str]]:
    """Ordena las zonas por su offset UTC actual (los más lejanos primero)."""
    zonas = zonas if zonas is not None else WORLD_ZONES

    def _key(z: tuple[str, str, str, str, str]) -> datetime.timedelta:
        try:
            t = ref if ref is not None else datetime.datetime.now(datetime.timezone.utc)
            off = t.astimezone(ZoneInfo(z[0])).utcoffset()
        except Exception:
            off = datetime.timedelta(0)
        return off

    return sorted(zonas, key=_key)
