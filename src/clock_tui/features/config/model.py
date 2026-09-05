"""Modelo de Config: contrato global.

Config no es un feature aislado (D15): define el objeto `config` (dict plano)
que todas las vistas consumen. Este modelo gestiona esos valores, describe los
items configurables por categoría, y calcula visibilidad condicional.

El controller retorna `ActionResult(command=...)` para acciones que requieren
servicios del main app (backup/restore/log), ya que el modelo no hace I/O.
"""

from __future__ import annotations

import calendar
import datetime
from dataclasses import dataclass, field
from typing import Any

from clock_tui.core.theme import COLOR_LIST, THEME_NAMES, _set_custom_theme

TABS = ["Apariencia", "Reloj", "Clima", "Sonido", "Sistema"]

POSPONER_MIN = [1, 2, 5, 10, 15, 20, 30]
CLIMA_INTERVALO = [5, 10, 15, 30, 60, 120]
CLIMA_RETRY_MAX = [1, 2, 3, 5]
CLIMA_RETRY_SEGS = [30, 60, 90, 120]
WC_MOSTRAR = ["ver", "no ver"]
ALARMAS_MOSTRAR = ["ver", "no ver"]


@dataclass
class ConfigItem:
    key: str
    label: str
    tab: str
    tipo: str  # bool | choice | text | soundmode | soundfile | soundbrowser | action
    opciones: Any = None


def default_config() -> dict[str, Any]:
    cfg: dict[str, Any] = {
        "mostrar_marco": True,
        "mostrar_helpers": True,
        "mostrar_nav": True,
        "mostrar_segundos": True,
        "formato_24h": True,
        "sonido": True,
        "sonido_modo": "default",
        "sonido_archivo": None,
        "sonido_custom_path": None,
        "clima_activo": False,
        "clima_ubicacion": "",
        "clima_intervalo_min": 60,
        "clima_mostrar_hace": True,
        "clima_retry_max": 3,
        "clima_retry_segs": 60,
        "tema": "clasico",
        "alarma_posponer_min": 5,
        "wc_mostrar": "ver",
        "alarmas_mostrar": "ver",
        "world_clocks": [],
        **_set_custom_theme({"make": True}),
    }
    return cfg


def config_items() -> list[ConfigItem]:
    return [
        ConfigItem("tema", "Tema de color", "Apariencia", "choice", THEME_NAMES),
        ConfigItem(
            "custom_color_marco", "- Custom: Marco", "Apariencia", "choice", COLOR_LIST
        ),
        ConfigItem(
            "custom_color_texto", "- Custom: Texto", "Apariencia", "choice", COLOR_LIST
        ),
        ConfigItem(
            "custom_color_clima", "- Custom: Clima", "Apariencia", "choice", COLOR_LIST
        ),
        ConfigItem(
            "custom_color_helpers",
            "- Custom: Helpers",
            "Apariencia",
            "choice",
            COLOR_LIST,
        ),
        ConfigItem(
            "custom_color_nav", "- Custom: Nav", "Apariencia", "choice", COLOR_LIST
        ),
        ConfigItem("mostrar_marco", "Mostrar marco", "Apariencia", "bool"),
        ConfigItem("mostrar_helpers", "Mostrar ayuda (helpers)", "Apariencia", "bool"),
        ConfigItem("mostrar_nav", "Mostrar barra de navegación", "Apariencia", "bool"),
        ConfigItem("mostrar_segundos", "Mostrar segundos", "Reloj", "bool"),
        ConfigItem("formato_24h", "Formato 24h", "Reloj", "bool"),
        ConfigItem(
            "alarma_posponer_min",
            "Posponer alarma (min)",
            "Reloj",
            "choice",
            POSPONER_MIN,
        ),
        ConfigItem("wc_mostrar", "Reloj Mundial", "Reloj", "choice", WC_MOSTRAR),
        ConfigItem(
            "alarmas_mostrar", "Alarmas en activity", "Reloj", "choice", ALARMAS_MOSTRAR
        ),
        ConfigItem("clima_activo", "Mostrar clima", "Clima", "bool"),
        ConfigItem("clima_ubicacion", "Ubicacion del clima", "Clima", "text"),
        ConfigItem(
            "clima_intervalo_min",
            "Auto-actualizar clima",
            "Clima",
            "choice",
            CLIMA_INTERVALO,
        ),
        ConfigItem(
            "clima_mostrar_hace", "Mostrar 'hace N min' en clima", "Clima", "bool"
        ),
        ConfigItem(
            "clima_retry_max",
            "Reintentos max. si falla clima",
            "Clima",
            "choice",
            CLIMA_RETRY_MAX,
        ),
        ConfigItem(
            "clima_retry_segs",
            "Espera entre reintentos",
            "Clima",
            "choice",
            CLIMA_RETRY_SEGS,
        ),
        ConfigItem("sonido", "Sonido (beep) ON/OFF", "Sonido", "bool"),
        ConfigItem(
            "sonido_modo",
            "Origen del sonido",
            "Sonido",
            "soundmode",
            ["default", "custom"],
        ),
        ConfigItem(
            "sonido_archivo", "- Archivo (carpeta default)", "Sonido", "soundfile"
        ),
        ConfigItem(
            "sonido_custom_path", "- Archivo (elegido a mano)", "Sonido", "soundbrowser"
        ),
        ConfigItem("backup_action", "Crear backup", "Sistema", "action", "backup"),
        ConfigItem(
            "restore_action", "Restaurar backup", "Sistema", "action", "restore"
        ),
        ConfigItem(
            "log_view_action", "Ver log de errores", "Sistema", "action", "log_view"
        ),
        ConfigItem(
            "log_export_action",
            "Descargar log de errores",
            "Sistema",
            "action",
            "log_export",
        ),
        ConfigItem(
            "update_check_action",
            "Comprobar actualizacion",
            "Sistema",
            "action",
            "update_check",
        ),
    ]


@dataclass
class ConfigModel:
    config: dict[str, Any]
    tab_idx: int = 0
    selected_idx: int = 0
    text_edit: bool = False
    text_edit_key: str | None = None
    text_edit_value: str = ""

    def __post_init__(self) -> None:
        self._items = config_items()

    @property
    def items(self) -> list[ConfigItem]:
        return self._items

    def visible_items(self) -> list[ConfigItem]:
        tab = TABS[self.tab_idx]
        tema = self.config.get("tema", "clasico")
        modo = self.config.get("sonido_modo", "default")
        sonido_on = self.config.get("sonido", True)
        out: list[ConfigItem] = []
        for it in self._items:
            if it.tab != tab:
                continue
            if it.key.startswith("custom_color") and tema != "custom":
                continue
            if not sonido_on and it.key in (
                "sonido_modo",
                "sonido_archivo",
                "sonido_custom_path",
            ):
                continue
            if it.key == "sonido_archivo" and modo != "default":
                continue
            if it.key == "sonido_custom_path" and modo != "custom":
                continue
            out.append(it)
        return out

    def clamp_selected(self) -> None:
        n = len(self.visible_items())
        if n and self.selected_idx >= n:
            self.selected_idx = n - 1

    def switch_tab(self, delta: int) -> None:
        self.tab_idx = (self.tab_idx + delta) % len(TABS)
        self.selected_idx = 0
        self.clamp_selected()

    def nav(self, delta: int) -> None:
        n = len(self.visible_items())
        if n == 0:
            return
        self.selected_idx = (self.selected_idx + delta) % n

    def current_item(self) -> ConfigItem | None:
        visibles = self.visible_items()
        if not visibles:
            return None
        return visibles[min(self.selected_idx, len(visibles) - 1)]

    # ── Values / display ──

    def item_value(self, it: ConfigItem) -> Any:
        if it.tipo == "soundmode":
            return (
                "Carpeta default"
                if self.config.get("sonido_modo") == "default"
                else "Archivo a mano"
            )
        if it.tipo == "soundfile":
            archivo = self.config.get("sonido_archivo")
            return archivo if archivo else "Beep default"
        if it.tipo == "soundbrowser":
            path = self.config.get("sonido_custom_path")
            if path:
                import os

                return os.path.basename(path)
            return "(sin elegir, Enter para buscar)"
        if it.tipo == "text":
            return self.config.get(it.key, "") or "(vacio = IP)"
        if it.tipo == "choice":
            val = self.config[it.key]
            if it.key == "clima_intervalo_min":
                return f"{val} min"
            if it.key == "clima_retry_segs":
                return f"{val}s"
            if it.key == "tema":
                return str(val).replace("_", " ").title()
            return val
        if it.tipo == "action":
            return "Enter para ejecutar"
        return "ON " if self.config.get(it.key) else "OFF"

    # ── Mutations (called by controller) ──

    def toggle_bool(self, key: str) -> None:
        self.config[key] = not self.config.get(key, False)
        if key == "sonido" and not self.config[key]:
            self.selected_idx = 0

    def cycle(self, it: ConfigItem) -> None:
        if it.tipo == "choice":
            opciones = it.opciones
            idx = opciones.index(self.config[it.key])
            self.config[it.key] = opciones[(idx + 1) % len(opciones)]
        elif it.tipo == "soundmode":
            opciones = it.opciones
            idx = opciones.index(self.config.get("sonido_modo"))
            self.config["sonido_modo"] = opciones[(idx + 1) % len(opciones)]
            self.selected_idx = 0
        elif it.tipo == "soundfile":
            self.selected_idx = 0  # main loop actualiza sonido_archivo

    def start_text_edit(self, it: ConfigItem) -> None:
        self.text_edit = True
        self.text_edit_key = it.key
        self.text_edit_value = str(self.config.get(it.key, ""))

    def text_commit(self) -> bool:
        if self.text_edit_key is None:
            self.text_edit = False
            return False
        self.config[self.text_edit_key] = self.text_edit_value
        self.text_edit = False
        self.text_edit_key = None
        return True

    def text_cancel(self) -> None:
        self.text_edit = False
        self.text_edit_key = None
