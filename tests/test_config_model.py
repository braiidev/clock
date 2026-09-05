"""Tests para features.config.model."""

from clock_tui.features.config.model import (
    ConfigModel,
    TABS,
    default_config,
)


def _model(tema="clasico", **kw) -> ConfigModel:
    cfg = default_config()
    cfg["tema"] = tema
    cfg.update(kw)
    return ConfigModel(config=cfg)


def test_default_config_has_kis():
    cfg = default_config()
    for k in ("mostrar_marco", "mostrar_helpers", "sonido", "tema", "world_clocks"):
        assert k in cfg


def test_tabs():
    assert TABS == ["Apariencia", "Reloj", "Clima", "Sonido", "Sistema"]


def test_sistema_tab_agrupa_backup_y_actualizacion():
    m = _model()
    m.tab_idx = TABS.index("Sistema")
    items = m.visible_items()
    claves = [it.key for it in items]
    assert "backup_action" in claves
    assert "restore_action" in claves
    assert "update_check_action" in claves
    assert all(it.tab == "Sistema" for it in items)


def test_visible_items_apariencia():
    m = _model(tema="clasico")
    items = m.visible_items()
    assert all(it.tab == "Apariencia" for it in items)
    assert not any(it.key.startswith("custom_color") for it in items)


def test_visible_items_custom_shows_custom_colors():
    m = _model(tema="custom")
    items = m.visible_items()
    assert any(it.key == "custom_color_marco" for it in items)


def test_visible_items_sonido_off_hides_sound():
    m = _model(sonido=False)
    m.switch_tab(TABS.index("Sonido"))
    items = m.visible_items()
    assert not any(it.key.startswith("sonido_") for it in items)


def test_sonido_mode_default_hides_custom_path():
    m = _model()
    m.switch_tab(TABS.index("Sonido"))
    items = m.visible_items()
    assert any(it.key == "sonido_archivo" for it in items)
    assert not any(it.key == "sonido_custom_path" for it in items)


def test_sonido_mode_custom_hides_file():
    m = _model(sonido_modo="custom")
    m.switch_tab(TABS.index("Sonido"))
    items = m.visible_items()
    assert not any(it.key == "sonido_archivo" for it in items)
    assert any(it.key == "sonido_custom_path" for it in items)


def test_switch_tab():
    m = _model()
    m.switch_tab(1)
    assert m.tab_idx == 1
    assert m.selected_idx == 0


def test_switch_tab_wraps():
    m = _model()
    m.switch_tab(-1)
    assert m.tab_idx == len(TABS) - 1


def test_nav():
    m = _model()
    # Apariencia tiene >1 visible (tema, viewer, etc.)
    m.switch_tab(TABS.index("Clima"))
    before = m.selected_idx
    m.nav(1)
    assert m.selected_idx == (before + 1) % len(m.visible_items())


def test_toggle_bool():
    m = _model()
    m.toggle_bool("mostrar_marco")
    assert m.config["mostrar_marco"] is False
    m.toggle_bool("mostrar_marco")
    assert m.config["mostrar_marco"] is True


def test_cycle_choice():
    m = _model()
    before = m.config["alarma_posponer_min"]
    item = next(it for it in m.items if it.key == "alarma_posponer_min")
    m.cycle(item)
    assert m.config["alarma_posponer_min"] != before


def test_cycle_soundmode():
    m = _model(sonido_modo="default")
    item = next(it for it in m.items if it.key == "sonido_modo")
    m.cycle(item)
    assert m.config["sonido_modo"] == "custom"


def test_item_value_bool():
    m = _model()
    item = next(it for it in m.items if it.key == "mostrar_marco")
    assert m.item_value(item) == "ON "


def test_item_value_choice_intervalo():
    m = _model(clima_intervalo_min=60)
    item = next(it for it in m.items if it.key == "clima_intervalo_min")
    assert m.item_value(item) == "60 min"


def test_start_text_edit():
    m = _model(clima_ubicacion="Buenos Aires")
    item = next(it for it in m.items if it.key == "clima_ubicacion")
    m.start_text_edit(item)
    assert m.text_edit is True
    assert m.text_edit_value == "Buenos Aires"


def test_text_commit():
    m = _model()
    item = next(it for it in m.items if it.key == "clima_ubicacion")
    m.start_text_edit(item)
    m.text_edit_value = "Lima"
    changed = m.text_commit()
    assert changed is True
    assert m.config["clima_ubicacion"] == "Lima"
    assert m.text_edit is False


def test_text_cancel():
    m = _model()
    item = next(it for it in m.items if it.key == "clima_ubicacion")
    m.start_text_edit(item)
    m.text_cancel()
    assert m.text_edit is False
    assert m.text_edit_key is None
