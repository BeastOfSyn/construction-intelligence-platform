"""Weather-aware site advisories."""
from __future__ import annotations

from typing import Dict, List

from . import config as C


def list_conditions() -> List[str]:
    """Return the selectable weather conditions."""
    return list(C.WEATHER_CONDITIONS)


def get_alert(condition: str) -> Dict[str, object]:
    """Return the alert (level, headline, actions) for a weather condition.

    Raises:
        ValueError: if the condition is not recognised.
    """
    if condition not in C.WEATHER_ALERTS:
        raise ValueError(f"Unknown weather condition: {condition}")
    return C.WEATHER_ALERTS[condition]
