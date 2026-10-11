"""Feeder definitions — distribution feeders loaded from a JSON registry.

Feeders are loaded from (in priority order):
  1. The path in ``NARRATOR_FEEDERS_FILE`` environment variable
  2. The bundled ``feeders.json`` next to this module

The 5 hardcoded defaults are kept as a fallback if JSON loading fails.
"""

from __future__ import annotations

import json
import os
import pathlib
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Feeder:
    """A distribution feeder with transformer rating and forecast characteristics."""

    id: str
    name: str
    district: str
    capacity_mw: float
    base_load_mw: float
    peak_pct: float       # typical peak as fraction of capacity
    band_width: float     # forecast uncertainty (0.05 = tight, 0.17 = wide)
    scenario: str         # default scenario for this feeder
    confidence: str       # "High", "Moderate", "Low"


# ------------------------------------------------------------------
# Hardcoded defaults — used when no JSON file is available
# ------------------------------------------------------------------
_DEFAULT_FEEDERS: tuple[Feeder, ...] = (
    Feeder("feeder7", "Feeder 7", "Eastgate", 8.4, 4.2, 0.96, 0.075,
           "peak_forecast", "Moderate"),
    Feeder("feeder12", "Feeder 12", "Mill District", 5.0, 2.9, 1.01, 0.065,
           "overload_risk", "Moderate"),
    Feeder("feeder9", "Feeder 9", "Northborough", 7.0, 3.6, 0.88, 0.08,
           "demand_response", "Moderate"),
    Feeder("feeder5", "Feeder 5", "Lakeside", 6.2, 3.0, 0.84, 0.17,
           "low_confidence", "Low"),
    Feeder("feeder3", "Feeder 3", "Riverside", 11.0, 5.4, 0.62, 0.05,
           "all_clear", "High"),
)

_BUNDLED_JSON = pathlib.Path(__file__).parent / "feeders.json"


def _load_from_json(path: pathlib.Path) -> tuple[Feeder, ...]:
    """Parse a JSON file into a tuple of Feeder instances."""
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    return tuple(Feeder(**entry) for entry in data)


def _load_feeders(path: str | pathlib.Path | None = None) -> tuple[Feeder, ...]:
    """Load feeders from *path*, the env var, the bundled JSON, or hardcoded defaults."""
    # Explicit path passed in
    if path is not None:
        return _load_from_json(pathlib.Path(path))

    # Environment variable
    env_path = os.getenv("NARRATOR_FEEDERS_FILE")
    if env_path:
        return _load_from_json(pathlib.Path(env_path))

    # Bundled JSON
    if _BUNDLED_JSON.exists():
        return _load_from_json(_BUNDLED_JSON)

    # Hardcoded fallback
    return _DEFAULT_FEEDERS


# ------------------------------------------------------------------
# Module-level state — backward compatible with existing imports
# ------------------------------------------------------------------
FEEDERS: tuple[Feeder, ...] = _load_feeders()
_FEEDER_INDEX: dict[str, Feeder] = {f.id: f for f in FEEDERS}


def get_feeder(id: str) -> Feeder:
    """Look up a feeder by ID. Raises ValueError if not found."""
    try:
        return _FEEDER_INDEX[id]
    except KeyError:
        valid = ", ".join(_FEEDER_INDEX)
        raise ValueError(f"Unknown feeder '{id}'. Valid: {valid}") from None


def reload_feeders(path: str | pathlib.Path | None = None) -> tuple[Feeder, ...]:
    """Hot-reload the feeder registry from a JSON file.

    Parameters
    ----------
    path : str or Path, optional
        JSON file to load. Falls back to ``NARRATOR_FEEDERS_FILE`` env var,
        then the bundled ``feeders.json``, then hardcoded defaults.

    Returns
    -------
    tuple[Feeder, ...]
        The newly loaded feeders (also updates the module-level ``FEEDERS``).
    """
    global FEEDERS, _FEEDER_INDEX
    FEEDERS = _load_feeders(path)
    _FEEDER_INDEX = {f.id: f for f in FEEDERS}
    return FEEDERS
