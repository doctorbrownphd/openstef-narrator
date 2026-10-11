"""Counterfactual narratives — perturb forecasts and narrate the delta.

"If the cold front arrives 3 hours earlier, peak shifts into the evening
DR window." Works purely by mathematical perturbation of an existing
ForecastContext — never calls generate_forecast().
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from openstef_narrator.scenarios import detect_scenario
from openstef_narrator.types import ForecastContext


@dataclass(frozen=True)
class Perturbation:
    """A what-if perturbation to apply to a forecast."""

    id: str               # "early_front", "delayed_front", etc.
    label: str            # "Cold front arrives 3h earlier"
    description: str      # what changes
    temp_offset: float    # degrees F shift applied to the forecast
    peak_hour_shift: int  # hours to shift the peak


# ------------------------------------------------------------------
# Standard perturbation library
# ------------------------------------------------------------------

PERTURBATIONS: tuple[Perturbation, ...] = (
    Perturbation(
        id="early_front",
        label="Cold front arrives 3h earlier",
        description="The cold front arrives 3 hours earlier than forecast, "
                    "dropping temperatures sooner and shifting the peak forward.",
        temp_offset=-3.0,
        peak_hour_shift=-3,
    ),
    Perturbation(
        id="delayed_front",
        label="Cold front arrives 3h later",
        description="The cold front is delayed by 3 hours, keeping temperatures "
                    "warmer longer and pushing the peak later.",
        temp_offset=2.0,
        peak_hour_shift=3,
    ),
    Perturbation(
        id="colder_than_forecast",
        label="5 degrees F colder than forecast",
        description="Temperatures run 5 degrees F colder than the central forecast, "
                    "increasing heating load.",
        temp_offset=-5.0,
        peak_hour_shift=0,
    ),
    Perturbation(
        id="warmer_than_forecast",
        label="5 degrees F warmer than forecast",
        description="Temperatures run 5 degrees F warmer than the central forecast, "
                    "reducing heating load.",
        temp_offset=5.0,
        peak_hour_shift=0,
    ),
    Perturbation(
        id="ev_surge",
        label="Evening EV charging surge (+15%)",
        description="A 15% increase in evening EV charging load adds to the "
                    "existing evening peak.",
        temp_offset=0.0,
        peak_hour_shift=0,
    ),
)

_PERTURBATION_INDEX: dict[str, Perturbation] = {p.id: p for p in PERTURBATIONS}


def get_perturbation(perturbation_id: str) -> Perturbation:
    """Look up a perturbation by ID. Raises ValueError if not found."""
    try:
        return _PERTURBATION_INDEX[perturbation_id]
    except KeyError:
        valid = ", ".join(_PERTURBATION_INDEX)
        raise ValueError(
            f"Unknown perturbation '{perturbation_id}'. Valid: {valid}"
        ) from None


# ------------------------------------------------------------------
# Heating sensitivity: ~2% peak MW change per degree F
# ------------------------------------------------------------------
_HEATING_SENSITIVITY = 0.02  # fraction of peak_mw per degree F

# EV surge: 15% added to peak
_EV_SURGE_FACTOR = 0.15


def _perturb_context(ctx: ForecastContext, perturbation: Perturbation) -> ForecastContext:
    """Apply a perturbation to a ForecastContext, returning a new context.

    This is pure math — no forecast re-generation.
    """
    # Temperature shift
    new_low_temp = ctx.low_temp + perturbation.temp_offset

    # Peak MW adjustment from temperature change
    temp_load_delta = -perturbation.temp_offset * _HEATING_SENSITIVITY * ctx.peak_mw
    new_peak_mw = ctx.peak_mw + temp_load_delta

    # EV surge adds 15% to peak (only for ev_surge perturbation)
    if perturbation.id == "ev_surge":
        new_peak_mw = ctx.peak_mw * (1.0 + _EV_SURGE_FACTOR)

    new_peak_pct = new_peak_mw / ctx.capacity_mw

    # Peak hour shift
    new_peak_hour = max(0, min(47, ctx.peak_hour + perturbation.peak_hour_shift))
    new_peak_hour_of_day = (ctx.peak_hour_of_day + perturbation.peak_hour_shift) % 24

    # Re-detect scenario from perturbed values
    new_scenario = detect_scenario(new_peak_pct, ctx.band_width)

    return replace(
        ctx,
        peak_mw=round(new_peak_mw, 3),
        peak_pct=round(new_peak_pct, 4),
        peak_hour=new_peak_hour,
        peak_hour_of_day=new_peak_hour_of_day,
        low_temp=round(new_low_temp, 1),
        scenario=new_scenario,
    )


def generate_counterfactual(
    ctx: ForecastContext,
    perturbation: Perturbation,
) -> dict:
    """Generate a single counterfactual analysis.

    Parameters
    ----------
    ctx : ForecastContext
        The original (unperturbed) forecast.
    perturbation : Perturbation
        The what-if scenario to apply.

    Returns
    -------
    dict with keys:
        perturbation_id, perturbation_label,
        original (summary), perturbed (summary),
        delta (what changed), narrative (prose sentence)
    """
    perturbed = _perturb_context(ctx, perturbation)

    original_summary = {
        "peak_mw": ctx.peak_mw,
        "peak_pct": round(ctx.peak_pct, 4),
        "peak_hour_of_day": ctx.peak_hour_of_day,
        "low_temp": ctx.low_temp,
        "scenario": ctx.scenario,
    }

    perturbed_summary = {
        "peak_mw": perturbed.peak_mw,
        "peak_pct": round(perturbed.peak_pct, 4),
        "peak_hour_of_day": perturbed.peak_hour_of_day,
        "low_temp": perturbed.low_temp,
        "scenario": perturbed.scenario,
    }

    delta = {
        "peak_mw_change": round(perturbed.peak_mw - ctx.peak_mw, 3),
        "peak_pct_change": round(perturbed.peak_pct - ctx.peak_pct, 4),
        "peak_hour_shift": perturbed.peak_hour_of_day - ctx.peak_hour_of_day,
        "low_temp_change": round(perturbed.low_temp - ctx.low_temp, 1),
        "scenario_changed": perturbed.scenario != ctx.scenario,
        "new_scenario": perturbed.scenario,
    }

    narrative = format_counterfactual_prose(ctx, perturbation, {
        "original": original_summary,
        "perturbed": perturbed_summary,
        "delta": delta,
    })

    return {
        "perturbation_id": perturbation.id,
        "perturbation_label": perturbation.label,
        "original": original_summary,
        "perturbed": perturbed_summary,
        "delta": delta,
        "narrative": narrative,
    }


def format_counterfactual_prose(
    ctx: ForecastContext,
    perturbation: Perturbation,
    result: dict,
) -> str:
    """Format a counterfactual result as a narrative sentence.

    All computed values are wrapped in fact markers.
    """
    perturbed = result["perturbed"]
    delta = result["delta"]

    peak_time = f"{perturbed['peak_hour_of_day']:02d}:00"
    peak_pct_str = f"{round(perturbed['peak_pct'] * 100)}%"
    new_scenario = perturbed["scenario"].replace("_", " ")

    # Build the consequence clause
    parts: list[str] = []
    parts.append(f"peak shifts to \u00ab{peak_time}\u00bb")
    parts.append(f"load reaches \u00ab{peak_pct_str}\u00bb of rating")

    if delta["scenario_changed"]:
        parts.append(f"triggering an \u00ab{new_scenario}\u00bb classification")

    consequence = " and ".join(parts)

    return (
        f"If \u00ab{perturbation.label}\u00bb, {consequence}."
    )


def _is_relevant(ctx: ForecastContext, perturbation: Perturbation) -> bool:
    """Check whether a perturbation is relevant to the current scenario.

    Filters out nonsensical combinations, e.g. "colder" on a mild all_clear
    summer day, or "warmer" when already in overload.
    """
    # Temperature-based perturbations are less interesting for mild scenarios
    if perturbation.id == "colder_than_forecast" and ctx.scenario == "all_clear":
        # Skip "what if colder" when the feeder has ample headroom and it's warm
        if ctx.low_temp > 55.0:
            return False
    if perturbation.id == "warmer_than_forecast" and ctx.scenario == "overload_risk":
        # "What if warmer" is uninteresting during a cold-driven overload
        # unless temps are already warm (cooling scenario)
        if ctx.low_temp < 40.0:
            return False

    return True


def generate_all_counterfactuals(ctx: ForecastContext) -> list[dict]:
    """Generate counterfactuals for all relevant perturbations.

    Returns results sorted by severity (biggest increase in peak_pct first).
    """
    results: list[dict] = []
    for p in PERTURBATIONS:
        if _is_relevant(ctx, p):
            results.append(generate_counterfactual(ctx, p))

    # Sort by delta in peak_pct (biggest increase = most severe = first)
    results.sort(key=lambda r: r["delta"]["peak_pct_change"], reverse=True)
    return results
