"""Tests para features.config.controller."""

import curses

from clock_tui.features.config.controller import ConfigController
from clock_tui.features.config.model import ConfigModel, TABS, default_config


def _model() -> ConfigModel:
    return ConfigModel(config=default_config())


def _ctx() -> dict:
    return {}


def test_left_switch_tab():
    c = ConfigController()
    m = _model()
    c.handle(m, curses.KEY_LEFT, _ctx())
    assert m.tab_idx == len(TABS) - 1


def test_right_switch_tab():
    c = ConfigController()
    m = _model()
    c.handle(m, curses.KEY_RIGHT, _ctx())
    assert m.tab_idx == 1


def test_down_nav():
    c = ConfigController()
    m = _model()
    m.switch_tab(TABS.index("Clima"))
    before = m.selected_idx
    c.handle(m, curses.KEY_DOWN, _ctx())
    assert m.selected_idx == (before + 1) % len(m.visible_items())


def test_bool_toggle():
    c = ConfigController()
    m = _model()
    # Apariencia: item 0 = tema (choice), item 1 = mostrar_marco (bool)
    c.handle(m, curses.KEY_DOWN, _ctx())
    r = c.handle(m, ord("\n"), _ctx())
    assert m.config["mostrar_marco"] is False
    assert r.needs_save is True


def test_cycle_choice_needs_save():
    c = ConfigController()
    m = _model()
    m.switch_tab(TABS.index("Reloj"))
    # primer item de Reloj: mostrar_segundos bool
    r = c.handle(m, ord("\n"), _ctx())
    assert r.needs_save is True


def test_action_backup():
    c = ConfigController()
    m = _model()
    m.switch_tab(TABS.index("Data"))
    r = c.handle(m, ord("\n"), _ctx())
    assert r.command == "backup"


def test_action_restore():
    c = ConfigController()
    m = _model()
    m.switch_tab(TABS.index("Data"))
    m.nav(1)
    r = c.handle(m, ord("\n"), _ctx())
    assert r.command == "restore"


def test_action_update_check_sistema():
    c = ConfigController()
    m = _model()
    m.switch_tab(TABS.index("Sistema"))
    r = c.handle(m, ord("\n"), _ctx())
    assert r.command == "update_check"


def test_text_edit_start():
    c = ConfigController()
    m = _model()
    m.switch_tab(TABS.index("Clima"))
    # item 1 = clima_ubicacion (text)
    c.handle(m, curses.KEY_DOWN, _ctx())
    item = m.current_item()
    assert item is not None
    assert item.key == "clima_ubicacion"
    c.handle(m, ord("\n"), _ctx())
    assert m.text_edit is True


def test_text_edit_type_and_commit():
    c = ConfigController()
    m = _model()
    m.switch_tab(TABS.index("Clima"))
    c.handle(m, curses.KEY_DOWN, _ctx())
    c.handle(m, ord("\n"), _ctx())
    for ch in "Lima":
        c.handle(m, ord(ch), _ctx())
    r = c.handle(m, ord("\n"), _ctx())
    assert m.config["clima_ubicacion"] == "Lima"
    assert r.needs_save is True


def test_text_edit_esc_cancels():
    c = ConfigController()
    m = _model()
    m.switch_tab(TABS.index("Clima"))
    c.handle(m, curses.KEY_DOWN, _ctx())
    c.handle(m, ord("\n"), _ctx())
    c.handle(m, 27, _ctx())
    assert m.text_edit is False


def test_sound_browser():
    c = ConfigController()
    m = _model()
    m.config["sonido_modo"] = "custom"
    m.switch_tab(TABS.index("Sonido"))
    c.handle(m, curses.KEY_DOWN, _ctx())
    c.handle(m, curses.KEY_DOWN, _ctx())
    r = c.handle(m, ord("\n"), _ctx())
    assert r.command == "sound_browser"


def test_sound_cycle():
    c = ConfigController()
    m = _model()
    m.switch_tab(TABS.index("Sonido"))
    # primer item sonido bool, segundo soundmode
    c.handle(m, curses.KEY_DOWN, _ctx())
    c.handle(m, curses.KEY_DOWN, _ctx())
    r = c.handle(m, ord("\n"), _ctx())
    assert r.command == "sound_cycle"
