"""Feature reloj (hora local + relojes mundiales).

Sin clima (D13): el clima solo se muestra en el Dashboard.
Los relojes mundiales se gestionan como lista (CLOCK.md §5 vista 1).
"""

from .controller import ClockController
from .model import ClockModel, WorldClock

__all__ = ["ClockModel", "ClockController", "WorldClock"]
