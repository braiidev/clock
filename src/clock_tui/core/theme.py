"""Temas de color y pares de curses.

Acopla los nombres de color en español con las constantes de curses.
Los pares de color se inicializan en la app (requieren curses ya iniciado);
este módulo solo define constantes y estructuras de temas.
"""

from __future__ import annotations

import curses
from typing import Any

# Pares de color (índices fijos, inicializados por la app)
PAIR_MARCO = 1
PAIR_HELPERS = 2
PAIR_CLIMA = 5
PAIR_TEXTO = 6
PAIR_NAV = 7
_ALERT_BLINK_PAIR_A = 3
_ALERT_BLINK_PAIR_B = 4
_HELP_BG_PAIR = 8

COLORS_PACK: dict[str, int] = {
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


def _set_custom_theme(props: dict[str, Any] | None = None) -> dict[str, Any]:
    """Devuelve el tema custom (colores configurados o sus valores por defecto)."""
    props = props or {}
    if props.get("make") is True:
        return {
            "custom_color_marco": "Azul",
            "custom_color_texto": "Blanco",
            "custom_color_clima": "Amarillo",
            "custom_color_helpers": "Azul",
            "custom_color_nav": "Azul",
        }
    return {
        "marco": COLORS_PACK.get(props.get("custom_color_marco"), COLORS_PACK["Azul"]),
        "texto": COLORS_PACK.get(
            props.get("custom_color_texto"), COLORS_PACK["Blanco"]
        ),
        "clima": COLORS_PACK.get(
            props.get("custom_color_clima"), COLORS_PACK["Amarillo"]
        ),
        "helpers": COLORS_PACK.get(
            props.get("custom_color_helpers"), COLORS_PACK["Azul"]
        ),
        "nav": COLORS_PACK.get(props.get("custom_color_nav"), COLORS_PACK["Azul"]),
    }


THEMES: dict[str, dict[str, int]] = {
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
    "custom": _set_custom_theme(),
}
THEME_NAMES = list(THEMES.keys())
