"""Feature Config: contrato global consumido por todas las vistas."""

from .controller import ConfigController
from .model import (
    ConfigItem,
    ConfigModel,
    TABS,
    config_items,
    default_config,
)

__all__ = [
    "ConfigModel",
    "ConfigController",
    "ConfigItem",
    "TABS",
    "config_items",
    "default_config",
]
