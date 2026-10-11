"""Forecast driver computation — what's causing the load pattern."""

from __future__ import annotations

from openstef_narrator.types import Driver

_DRIVER_MAP: dict[str, tuple[Driver, ...]] = {
    "peak_forecast": (
        Driver("snow", "Cold front", "low 16°F forecast", "a cold front"),
        Driver("car", "EV evening charging", "eastern laterals", "rising EV evening charging"),
    ),
    "overload_risk": (
        Driver("flame", "Heating coincidence", "electric + heat-pump", "an electric-heating coincidence"),
        Driver("car", "EV + standby load", "evening stack", "stacked EV and standby load"),
    ),
    "demand_response": (
        Driver("car", "EV evening peak", "homecoming window", "the EV homecoming peak"),
        Driver("bolt", "DR capacity available", "1.2 MW enrolled", "enrolled demand-response capacity"),
    ),
    "low_confidence": (
        Driver("solar", "Behind-meter solar", "cloud variability", "behind-meter solar variability"),
        Driver("snow", "Uncertain front timing", "±3 h", "uncertain weather-front timing"),
    ),
    "all_clear": (
        Driver("thermo", "Mild temperatures", "seasonal normal", "mild seasonal temperatures"),
    ),
}


def compute_drivers(scenario: str) -> tuple[Driver, ...]:
    """Return the drivers for a given scenario."""
    return _DRIVER_MAP.get(scenario, ())
