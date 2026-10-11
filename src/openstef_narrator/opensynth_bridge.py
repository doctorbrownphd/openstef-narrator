"""Bridge to opensynth-newengland — generates feeder-level forecasts from synthetic meters.

When opensynth_ne is installed, this module replaces the mock PRNG forecast
with structurally realistic load data: N synthetic meters (NE housing stock
distribution) aggregated to a feeder, with temperature ensemble for probabilistic
bands. If opensynth_ne is not available, raises ImportError.

Usage:
    from openstef_narrator.opensynth_bridge import generate_forecast_from_synth
    ctx = generate_forecast_from_synth("feeder7", seed=42)
"""

from __future__ import annotations

import math
from typing import Literal

import numpy as np

from openstef_narrator.feeders import get_feeder
from openstef_narrator.scenarios import detect_scenario
from openstef_narrator.types import Driver, ForecastContext, ForecastPoint

# Feeder customer counts — realistic for 5–11 MW distribution feeders
# Assumption: a typical New England distribution feeder serves 400-1,200 customers
_FEEDER_CUSTOMERS = {
    "feeder7": 850,   # Eastgate — suburban, 8.4 MW
    "feeder12": 520,  # Mill District — dense, 5.0 MW
    "feeder9": 700,   # Northborough — mixed, 7.0 MW
    "feeder5": 600,   # Lakeside — mixed, 6.2 MW
    "feeder3": 1100,  # Riverside — large, 11.0 MW
}

# Temperature trajectory: 48-hour forecast starting at 14:00
# Winter cold-front scenario by default
_START_HOUR = 14


def _temp_trajectory(base_temp: float, scenario: str, seed: int) -> np.ndarray:
    """Generate a 48-hour temperature trajectory (hourly).

    Models diurnal cycle + optional cold-front drop.
    """
    rng = np.random.default_rng(seed)
    hours = np.arange(48)
    hod = (_START_HOUR + hours) % 24

    # Diurnal: peaks at ~15:00, troughs at ~05:00
    diurnal = 6.0 * np.sin((hod - 9) / 24 * 2 * np.pi)

    # Cold front ramp (for peak/overload scenarios)
    if scenario in ("peak_forecast", "overload_risk"):
        front = -12.0 * np.clip((hours - 6) / 20, 0, 1)
    elif scenario == "low_confidence":
        front = -8.0 * np.clip((hours - 8) / 24, 0, 1)
    else:
        front = np.zeros(48)

    # Small noise for realism
    noise = rng.normal(0, 1.2, 48)

    return base_temp + diurnal + front + noise


def _aggregate_meters_to_hourly(
    meter_df,
    n_hours: int = 48,
) -> np.ndarray:
    """Aggregate 15-min meter data to hourly feeder load (MW).

    Parameters
    ----------
    meter_df : DataFrame from opensynth_ne.model.generate() — single day
        Columns: meter_id, interval, hour, net, ...

    Returns
    -------
    hourly_mw : array of shape (n_hours,) — total feeder load in MW
    """
    # Sum net load across all meters at each interval, convert kW → MW
    interval_totals = meter_df.groupby("interval")["net"].sum().values / 1000.0

    # Average 4 intervals (15-min) into 1 hour
    n_intervals = len(interval_totals)
    n_full_hours = n_intervals // 4
    hourly = np.array([
        interval_totals[i * 4:(i + 1) * 4].mean()
        for i in range(n_full_hours)
    ])

    return hourly[:n_hours]


def generate_forecast_from_synth(
    feeder_id: str = "feeder7",
    seed: int = 42,
    n_ensemble: int = 15,
    month: int | None = None,
) -> ForecastContext:
    """Generate a 48-hour probabilistic forecast using opensynth-ne synthetic meters.

    Runs an ensemble of temperature perturbations to produce p10/p50/p90 bands.
    Each ensemble member generates the full meter population at a slightly
    different temperature, simulating forecast uncertainty.

    Parameters
    ----------
    feeder_id : One of the 5 narrator feeders.
    seed : RNG seed for reproducibility.
    n_ensemble : Number of temperature ensemble members (more = smoother bands).
    month : 0-11. None defaults to January (cold scenario).
    """
    from opensynth_ne.model import generate as synth_generate

    feeder = get_feeder(feeder_id)
    n_customers = _FEEDER_CUSTOMERS.get(feeder_id, 700)

    # Default to January for cold scenarios, July for all-clear
    if month is None:
        month = 6 if feeder.scenario == "all_clear" else 0

    # Base temperature for this month
    from opensynth_ne.weather import MONTH_TEMP_F
    base_temp = MONTH_TEMP_F[month]

    # Generate temperature trajectory
    temp_series = _temp_trajectory(base_temp, feeder.scenario, seed)

    # Run ensemble: vary temperature ±3°F to simulate forecast uncertainty
    rng = np.random.default_rng(seed + 777)
    ensemble_loads = []
    component_day1 = None  # keep first ensemble member's raw data for decomposition

    for ens_idx in range(n_ensemble):
        temp_offset = rng.normal(0, 2.5)  # °F uncertainty
        ens_temp = base_temp + temp_offset
        ens_seed = seed + ens_idx * 1000

        # Generate day 1 (hours 0-23 of forecast = today 14:00 to tomorrow 13:59)
        day1 = synth_generate(
            n=n_customers,
            archetype=None,  # empirical NE distribution
            fuel=None,
            month=month,
            temp_f=ens_temp,
            distribution="empirical",
            seed=ens_seed,
        )
        hourly_day1 = _aggregate_meters_to_hourly(day1, n_hours=24)

        if ens_idx == 0:
            component_day1 = day1  # save for driver decomposition

        # Generate day 2 (hours 24-47, next day)
        day2_month = min(11, month + (1 if month < 11 else 0))
        day2 = synth_generate(
            n=n_customers,
            archetype=None,
            fuel=None,
            month=day2_month,
            temp_f=ens_temp + temp_offset * 0.5,  # more uncertainty day 2
            distribution="empirical",
            seed=ens_seed + 500,
        )
        hourly_day2 = _aggregate_meters_to_hourly(day2, n_hours=24)

        # Combine into 48 hours
        # Adjust for start hour: we start at 14:00, so day1 covers 14:00-23:59 (10h)
        # and day2 covers 00:00-23:59 (24h), day3 covers 00:00-13:59 (14h)
        # Simplification: use day1 for first 24h, day2 for second 24h
        # Shift by start hour offset
        shift = _START_HOUR
        full_48 = np.concatenate([
            hourly_day1[shift:],       # today 14:00 → 23:00 (10 hours)
            hourly_day2,               # tomorrow 00:00 → 23:00 (24 hours)
            hourly_day1[:shift],       # day-after 00:00 → 13:00 (14 hours)
        ])[:48]

        ensemble_loads.append(full_48)

    # Compute percentiles across ensemble
    ensemble_array = np.array(ensemble_loads)  # (n_ensemble, 48)

    # Capacity-aligned scaling: opensynth-ne meters peak at ~2-3 kW but real NE
    # homes at winter peak draw 5-10 kW. Scale the aggregate so the raw peak_pct
    # lands near the feeder's design peak_pct, preserving the load *shape* from
    # real physics while matching the feeder's magnitude. This is analogous to the
    # bias correction applied in production forecast pipelines.
    raw_p50_peak = float(np.percentile(ensemble_array, 50, axis=0).max())
    target_peak = feeder.capacity_mw * feeder.peak_pct
    scale_factor = target_peak / raw_p50_peak if raw_p50_peak > 0 else 1.0
    ensemble_array *= scale_factor

    p10 = np.percentile(ensemble_array, 10, axis=0)
    p50 = np.percentile(ensemble_array, 50, axis=0)
    p90 = np.percentile(ensemble_array, 90, axis=0)

    # Build ForecastPoints
    points = []
    for h in range(48):
        hod = (_START_HOUR + h) % 24
        points.append(ForecastPoint(
            hour=h,
            hour_of_day=hod,
            p10=round(float(p10[h]), 3),
            p50=round(float(p50[h]), 3),
            p90=round(float(p90[h]), 3),
            temperature=round(float(temp_series[h]), 1),
        ))

    # Derive statistics
    peak_pt = max(points, key=lambda p: p.p50)
    peak_pct = peak_pt.p50 / feeder.capacity_mw
    band_width = (peak_pt.p90 - peak_pt.p10) / (peak_pt.p50 + 0.001)

    # Exceedance probability (normal approximation)
    sigma = (peak_pt.p90 - peak_pt.p50) / 1.28 if peak_pt.p90 > peak_pt.p50 else 0.01
    z = (feeder.capacity_mw - peak_pt.p50) / sigma
    exceedance = max(0.002, min(0.985, 1.0 - _normal_cdf(z)))

    # Confidence from band width
    if band_width < 0.10:
        confidence = "High"
    elif band_width < 0.18:
        confidence = "Moderate"
    else:
        confidence = "Low"

    # Scenario detection
    scenario = detect_scenario(peak_pct, band_width)

    # Drivers — decomposed from actual load components at peak
    drivers = _decompose_drivers(component_day1, temp_series, scale_factor)

    return ForecastContext(
        feeder_id=feeder.id,
        feeder_name=feeder.name,
        district=feeder.district,
        capacity_mw=feeder.capacity_mw,
        points=tuple(points),
        peak_mw=peak_pt.p50,
        peak_hour=peak_pt.hour,
        peak_hour_of_day=peak_pt.hour_of_day,
        peak_pct=round(peak_pct, 3),
        exceedance_prob=round(exceedance, 4),
        confidence=confidence,
        band_width=round(band_width, 3),
        scenario=scenario,
        drivers=tuple(drivers),
        low_temp=round(float(temp_series.min()), 1),
        forecast_run_id=f"synth-{seed:05d}",
    )


def _normal_cdf(z: float) -> float:
    """Approximation of the standard normal CDF."""
    t = 1.0 / (1.0 + 0.2316419 * abs(z))
    d = 0.3989423 * math.exp(-z * z / 2)
    p = d * t * (0.3193815 + t * (-0.3565638 + t * (1.781478 + t * (-1.821256 + t * 1.330274))))
    return 1.0 - p if z > 0 else p


def _decompose_drivers(
    meter_df,
    temps: np.ndarray,
    scale_factor: float,
) -> list[Driver]:
    """Extract drivers from actual load component decomposition at peak.

    Instead of hardcoding "cold front" or "EV charging", this reads the
    synthetic meter data to determine what is *actually* driving the peak:
    which components (heating, behavioral, EV, cooling, solar) contribute
    the most load at the peak interval, and by how much.

    This is the narrator's equivalent of SHAP values: the model says what
    caused the number, and the narrative reports it.
    """
    COMPONENTS = ["base", "heat", "ev", "cool", "solar", "behav"]

    # Find the peak interval across all meters
    interval_totals = meter_df.groupby("interval")["net"].sum()
    peak_interval = int(interval_totals.idxmax())
    peak_data = meter_df[meter_df["interval"] == peak_interval]
    gross_at_peak = peak_data["gross"].sum()

    if gross_at_peak <= 0:
        return [Driver("thermo", "Seasonal baseline", "normal conditions",
                        "seasonal baseline conditions")]

    # Compute each component's share of gross load at peak
    shares = {}
    for comp in COMPONENTS:
        total = float(peak_data[comp].sum())
        shares[comp] = {
            "kw": total,
            "mw": abs(total) * scale_factor / 1000.0,
            "pct": abs(total) / gross_at_peak * 100 if gross_at_peak > 0 else 0,
        }

    # Rank components by contribution (descending), exclude negligible (<3%)
    ranked = sorted(
        [(c, s) for c, s in shares.items() if s["pct"] >= 3.0],
        key=lambda x: x[1]["pct"],
        reverse=True,
    )

    # Map component names to driver metadata
    _COMP_META = {
        "heat": {"icon": "flame", "label": "Electric heating",
                 "prose_template": "electric heating at {pct:.0f}% of peak load"},
        "behav": {"icon": "home", "label": "Behavioral load",
                  "prose_template": "evening behavioral load ({pct:.0f}% of peak)"},
        "ev": {"icon": "car", "label": "EV charging",
               "prose_template": "EV charging contributing {pct:.0f}% of peak load"},
        "cool": {"icon": "thermo", "label": "Cooling demand",
                 "prose_template": "cooling demand at {pct:.0f}% of peak"},
        "base": {"icon": "bolt", "label": "Baseload",
                 "prose_template": "baseload appliances at {pct:.0f}% of peak"},
        "solar": {"icon": "solar", "label": "Solar offset",
                  "prose_template": "behind-meter solar reducing net load by {mw:.1f} MW"},
    }

    drivers = []

    # Temperature context — always include as first driver
    low_temp = float(temps.min())
    high_temp = float(temps.max())
    if low_temp < 25:
        drivers.append(Driver(
            icon="snow",
            label="Cold front",
            detail=f"low {int(low_temp)}\u00b0F forecast",
            prose=f"a cold front with lows near {int(low_temp)}\u00b0F",
        ))
    elif high_temp > 85:
        drivers.append(Driver(
            icon="thermo",
            label="Heat wave",
            detail=f"high {int(high_temp)}\u00b0F forecast",
            prose=f"high temperatures reaching {int(high_temp)}\u00b0F",
        ))
    else:
        drivers.append(Driver(
            icon="thermo",
            label="Mild temperatures",
            detail=f"{int(low_temp)}\u2013{int(high_temp)}\u00b0F range",
            prose=f"mild temperatures in the {int(low_temp)}\u2013{int(high_temp)}\u00b0F range",
        ))

    # Top 2 load components (after temperature) — the "what" behind the "why"
    for comp, s in ranked[:2]:
        meta = _COMP_META.get(comp)
        if not meta:
            continue
        drivers.append(Driver(
            icon=meta["icon"],
            label=meta["label"],
            detail=f"{s['mw']:.1f} MW ({s['pct']:.0f}% of peak)",
            prose=meta["prose_template"].format(pct=s["pct"], mw=s["mw"]),
        ))

    # Solar offset — if solar is present and non-negligible, note it
    solar_s = shares.get("solar", {"pct": 0, "mw": 0})
    if solar_s["pct"] >= 2.0 and solar_s["kw"] < 0:
        drivers.append(Driver(
            icon="solar",
            label="Solar offset (absent at peak)",
            detail=f"no generation at evening peak",
            prose="absent solar generation at the evening peak",
        ))

    return drivers


def is_available() -> bool:
    """Check if opensynth-ne is importable."""
    try:
        import opensynth_ne.model  # noqa: F401
        return True
    except ImportError:
        return False
