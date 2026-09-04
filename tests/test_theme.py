"""Tests para core.theme."""

from clock_tui.core.theme import (
    COLOR_LIST,
    COLORS_PACK,
    THEME_NAMES,
    THEMES,
    _set_custom_theme,
)


def test_color_list_default():
    assert "Azul" in COLOR_LIST
    assert "Blanco" in COLOR_LIST
    assert len(COLOR_LIST) == 8


def test_colors_pack():
    assert isinstance(COLORS_PACK["Azul"], int)
    assert "Amarillo" in COLORS_PACK


def test_themes_have_all_roles():
    for nombre, tema in THEMES.items():
        assert set(tema.keys()) == {"marco", "texto", "clima", "helpers", "nav"}, nombre


def test_theme_names_include_custom():
    assert "custom" in THEME_NAMES


def test_set_custom_theme_make_and_resolve():
    defaults = _set_custom_theme({"make": True})
    assert defaults["custom_color_marco"] == "Azul"
    resuelto = _set_custom_theme(
        {"custom_color_marco": "Verde", "custom_color_texto": "Magenta"}
    )
    assert resuelto["marco"] == COLORS_PACK["Verde"]
    assert resuelto["texto"] == COLORS_PACK["Magenta"]
    # valor no reconocido cae al default
    resuelto_default = _set_custom_theme({})
    assert resuelto_default["clima"] == COLORS_PACK["Amarillo"]
