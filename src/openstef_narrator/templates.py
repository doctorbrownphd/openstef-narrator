"""Template narrative engine — 5 scenarios × 3 verbosities.

All numeric facts are injected as «value» markers. The LLM rewrite
layer (phase 5) reshapes the prose between markers but never touches
the numbers themselves.
"""

from __future__ import annotations

from typing import Literal

from openstef_narrator.types import ForecastContext, NarrativeReport

Verbosity = Literal["terse", "standard", "full"]


def _extract_facts(ctx: ForecastContext) -> dict[str, str]:
    """Build the fact dictionary from a ForecastContext."""
    peak_day = "today" if ctx.peak_hour < 24 else "tomorrow"
    peak_time = f"{ctx.peak_hour_of_day:02d}:00"
    return {
        "feeder": ctx.feeder_name,
        "district": ctx.district,
        "pct": f"{round(ctx.peak_pct * 100)}%",
        "when": f"{peak_day} {peak_time}",
        "load": f"{ctx.peak_mw:.1f} MW",
        "cap": f"{ctx.capacity_mw:.1f} MW",
        "low_temp": f"{round(ctx.low_temp)}°F",
        "exc": f"{round(ctx.exceedance_prob * 100)}%",
        "conf": ctx.confidence.lower(),
        "band_pct": f"{round(ctx.band_width * 100)}%",
    }


def _f(val: str) -> str:
    """Wrap a value in fact markers."""
    return f"«{val}»"


def render_template(
    ctx: ForecastContext,
    verbosity: Verbosity = "standard",
) -> NarrativeReport:
    """Render a narrative from templates, injecting «facts».

    Returns a NarrativeReport with all numeric values wrapped in «» markers.
    """
    facts = _extract_facts(ctx)
    fdr = _f(facts["feeder"])
    pct = _f(facts["pct"])
    when = _f(facts["when"])
    load = _f(facts["load"])
    cap = _f(facts["cap"])
    low = _f(facts["low_temp"])
    exc = _f(facts["exc"])
    conf = _f(facts["conf"])
    band_pct = _f(facts["band_pct"])

    # Wrap each driver in «» markers so the LLM cannot originate causal claims.
    # The model may rephrase around these but cannot invent new causes.
    driver_prose = (
        " and ".join(_f(d.prose) for d in ctx.drivers)
        if ctx.drivers else _f("seasonal patterns")
    )
    v = verbosity

    situation = ""
    risk = ""
    recommendation = ""
    audit = ""

    if ctx.scenario == "all_clear":
        situation = (
            f"{fdr} stays comfortable — peak reaches only {pct} of rating {when}, no action expected."
            if v == "terse" else
            f"Peak load on {fdr} is forecast to reach {load}, just {pct} of its {cap} rating, "
            f"{when}, owing to {driver_prose}. The feeder has ample headroom across the full 48-hour horizon."
        )
        risk = f"Forecast confidence is {conf}; probability of exceeding rating is negligible at {exc}."
        recommendation = (
            "No operator action required."
            if v == "terse" else
            "No proactive switching or demand response is warranted. Monitoring only."
        )

    elif ctx.scenario == "overload_risk":
        situation = (
            f"{fdr} is forecast to reach {pct} of transformer rating {when} — overload risk."
            if v == "terse" else
            f"Peak load on {fdr} is forecast to reach {load} — {pct} of its {cap} transformer "
            f"rating — {when}, driven by {driver_prose}. The central estimate sits at or above nameplate."
        )
        risk = (
            f"Confidence is {conf}. There is a {exc} probability of thermal exceedance at peak; "
            f"the upper band crosses rating for roughly three hours."
        )
        recommendation = (
            "Stage a load transfer before peak."
            if v == "terse" else
            "Stage a feeder load transfer or firm demand-response activation ahead of the peak "
            "window to hold the transformer below nameplate."
        )

    elif ctx.scenario == "demand_response":
        situation = (
            f"{fdr} peaks at {pct} of rating {when} — a demand-response candidate."
            if v == "terse" else
            f"Peak load on {fdr} is forecast to reach {load}, or {pct} of its {cap} rating, "
            f"{when}, driven by {driver_prose}."
        )
        risk = (
            f"Confidence is {conf}; exceedance probability is {exc}. "
            f"Enrolled DR capacity is sufficient to shave the forecast peak."
        )
        recommendation = (
            "Pre-arm demand response for the evening window."
            if v == "terse" else
            "Pre-arm the enrolled demand-response block for the evening window; a modest "
            "curtailment keeps the feeder comfortably below rating without switching."
        )

    elif ctx.scenario == "low_confidence":
        # Hedge language proportionally to band width and exceedance probability
        if ctx.band_width > 0.25:
            _hedge_adverb = "highly"
            _hedge_qualifier = "very rough estimate"
        elif ctx.band_width > 0.18:
            _hedge_adverb = "notably"
            _hedge_qualifier = "rough estimate"
        else:
            _hedge_adverb = "moderately"
            _hedge_qualifier = "approximate estimate"

        situation = (
            f"{fdr} uncertain — forecast band is {band_pct} wide; may peak near {pct} of rating {when}."
            if v == "terse" else
            f"Peak load on {fdr} is {_hedge_adverb} uncertain: the {band_pct}-wide prediction band "
            f"puts the {_hedge_qualifier} near {load} — about {pct} of its {cap} rating — "
            f"{when}, owing to {driver_prose}. Treat these numbers with caution."
        )
        risk = (
            f"Confidence is {conf}: the 48-hour band spans {band_pct} of peak load and the exceedance "
            f"probability ({exc}) is poorly constrained. The point estimate is a {_hedge_qualifier} — "
            f"do not rely on it for operational decisions without a re-run."
        )
        recommendation = (
            "Re-run forecast as the front resolves."
            if v == "terse" else
            "Hold action and re-run the forecast as the weather front resolves; "
            "revisit if the band narrows toward rating."
        )

    else:  # peak_forecast (default)
        situation = (
            f"{fdr} peaks at {pct} of transformer rating {when}."
            if v == "terse" else
            f"Tomorrow's peak load on {fdr} is forecast to reach {pct} of transformer rated "
            f"capacity at approximately {_f(facts['when'].split()[-1])} ({load} of {cap}). "
            f"The primary drivers are {driver_prose}."
        )
        risk = (
            f"Model confidence is {conf} — there is a {exc} probability of thermal exceedance "
            f"if temperatures fall below the {low} baseline assumption."
        )
        recommendation = (
            "Consider proactive switching before peak."
            if v == "terse" else
            "A proactive switching operation or demand-response activation before the peak "
            "window is recommended."
        )

    if v == "full":
        situation += f" Estimated low temperature over the horizon is {low}."
        audit = (
            f"Generated from forecast run «{ctx.forecast_run_id}» · "
            f"«{ctx.confidence.lower()} confidence» · "
            f"all numeric facts injected from the OpenSTEF output, not model-generated."
        )

    return NarrativeReport(
        situation=situation,
        risk=risk,
        recommendation=recommendation,
        audit=audit,
    )
