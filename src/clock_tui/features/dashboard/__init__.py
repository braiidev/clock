"""Feature dashboard: resumen de solo lectura (fecha+hora, clima, actividades)."""

from .controller import DashboardController
from .model import ActivityRow, DashboardSnapshot

__all__ = ["DashboardSnapshot", "DashboardController", "ActivityRow"]
