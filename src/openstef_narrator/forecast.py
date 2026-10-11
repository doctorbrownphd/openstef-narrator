"""Mock 48-hour probabilistic forecast model.

Deterministic per seed — produces the same forecast for the same inputs.
Port of data.js forecast() function.
"""

from __future__ import annotations

import math
from typing import Callable

from openstef_narrator.drivers import compute_drivers
from openstef_narrator.feeders import FEEDERS, Feeder, get_feeder
from openstef_narrator.scenarios import detect_scenario, detect_scenario_with_flags
from openstef_narrator.types import ForecastContext, ForecastPoint

_U32 = 0xFFFFFFFF
START_HOUR = 14  # forecast starts at 14:00 (2 PM)


def _mulberry32(seed: int) -> Callable[[], float]:
    """Mulberry32 seeded PRNG. Returns a callable producing floats in [0, 1)."""
    state = [seed & _U32]

    def next_float() -> float:
        a = (state[0] + 0x6D2B79F5) & _U32
        state[0] = a
        t = ((a ^ (a >> 15)) * (1 | a)) & _U32
        t = ((t + (((t ^ (t >> 7)) * (61 | t)) & _U32)) & _U32) ^ t
        return ((t ^ (t >> 14)) & _U32) / 4294967296

    return next_float


def _hash_str(s: str) -> int:
    """FNV-1a hash of a string, returning an unsigned 32-bit integer."""
    h = 2166136261
    for c in s:
        h = (h ^ ord(c)) & _U32
        h = (h * 16777619) & _U32
    return h


def _bump(h: float, center: float, width: float) -> float:
    """Gaussian bump."""
    x = (h - center) / width
    return math.exp(-0.5 * x * x)


def _ncdf(z: float) -> float:
    """Normal CDF approximation (Abramowitz & Stegun)."""
    t = 1.0 / (1.0 + 0.2316419 * abs(z))
    d = 0.3989423 * math.exp(-z * z / 2)
    p = d * t * (0.3193815 + t * (-0.3565638 + t * (1.781478 + t * (-1.821256 + t * 1.330274))))
    return 1.0 - p if z > 0 else p


def _clock_label(abs_hour: int) -> dict:
    """Convert absolute hour to human-readable clock label."""
    day_offset = abs_hour // 24
    hod = abs_hour % 24
    day_str = "today" if day_offset == 0 else "tomorrow" if day_offset == 1 else f"in {day_offset} days"
    time_str = f"{hod:02d}:00"
    return {"day": day_str, "time": time_str, "label": f"{day_str} {time_str}"}


def generate_forecast(
    feeder_id: str = "feeder7",
    seed: int = 42,
    use_synth: bool | None = None,
) -> ForecastContext:
    """Generate a 48-hour probabilistic forecast for one feeder.

    When opensynth-ne is installed, generates structurally realistic data from
    synthetic NE meters. Falls back to deterministic mock if unavailable.

    Parameters
    ----------
    use_synth : None = auto-detect, True = force opensynth, False = force mock
    """
    if use_synth is None:
        import os
        use_synth = os.getenv("NARRATOR_USE_SYNTH", "").lower() in ("1", "true", "yes")

    if use_synth:
        from openstef_narrator.opensynth_bridge import generate_forecast_from_synth
        return generate_forecast_from_synth(feeder_id=feeder_id, seed=seed)

    f = get_feeder(feeder_id)
    r = _mulberry32(_hash_str(feeder_id) + seed)
    n_hours = 48

    # Cold front intensity by scenario
    cold = 0.25 if f.scenario == "all_clear" else 0.7 if f.scenario == "low_confidence" else 1.0

    # Temperature model: diurnal cycle + cold front ramp
    def temp_at(h: int) -> float:
        hod = (START_HOUR + h) % 24
        diurnal = 4.0 * math.sin((hod - 9) / 24 * 6.283)
        front = 30.0 - cold * 16.0 * max(0.0, min(1.0, (h - 4) / 22))
        return front + diurnal

    # Raw normalized load shape
    raw = []
    for h in range(n_hours):
        hod = (START_HOUR + h) % 24
        temp = temp_at(h)
        coldness = max(0.0, min(1.0, (60.0 - temp) / 55.0))

        morning = _bump(hod, 8, 2.0)
        evening = _bump(hod, 18.5, 2.6)
        midday = _bump(hod, 13, 3.0)

        v = 0.46 + 0.34 * morning + 0.62 * evening + 0.12 * midday
        v += 0.55 * coldness * (0.4 + 0.8 * evening)

        if f.scenario == "all_clear":
            v -= 0.10 * midday  # BTM solar dip
        if f.scenario == "low_confidence":
            v -= 0.18 * midday  # larger solar dip

        raw.append(max(0.2, v))

    raw_max = max(raw)
    peak_load = f.peak_pct * f.capacity_mw

    # Build forecast points with confidence bands
    points = []
    for h in range(n_hours):
        p50 = raw[h] / raw_max * peak_load
        horiz = 0.35 + 0.65 * (h / n_hours)  # band widens with horizon
        sigma_rel = f.band_width * horiz
        p10 = max(0.0, p50 * (1 - 1.28 * sigma_rel))
        p90 = p50 * (1 + 1.28 * sigma_rel)

        points.append(ForecastPoint(
            hour=h,
            hour_of_day=(START_HOUR + h) % 24,
            p10=round(p10, 3),
            p50=round(p50, 3),
            p90=round(p90, 3),
            temperature=round(temp_at(h), 1),
        ))

    # Peak statistics
    peak_pt = max(points, key=lambda p: p.p50)
    sigma = (peak_pt.p90 - peak_pt.p50) / 1.28 if peak_pt.p90 > peak_pt.p50 else 0.01
    exceedance = max(0.002, min(0.985, 1.0 - _ncdf((f.capacity_mw - peak_pt.p50) / sigma)))

    clock = _clock_label(START_HOUR + peak_pt.hour)

    # Scenario and drivers (with secondary overlap flags)
    scenario, secondary_flags = detect_scenario_with_flags(
        peak_pt.p50 / f.capacity_mw, f.band_width,
    )
    drivers = compute_drivers(scenario)

    run_id = f"stef-{_hash_str(feeder_id) % 99999:05d}"

    return ForecastContext(
        feeder_id=feeder_id,
        feeder_name=f.name,
        district=f.district,
        capacity_mw=f.capacity_mw,
        points=tuple(points),
        peak_mw=peak_pt.p50,
        peak_hour=peak_pt.hour,
        peak_hour_of_day=peak_pt.hour_of_day,
        peak_pct=peak_pt.p50 / f.capacity_mw,
        exceedance_prob=exceedance,
        confidence=f.confidence,
        band_width=f.band_width,
        scenario=scenario,
        drivers=drivers,
        low_temp=min(p.temperature for p in points),
        forecast_run_id=run_id,
        secondary_flags=secondary_flags,
    )
