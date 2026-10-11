"""System-level rollup — aggregate narratives across multiple feeders.

Generates forecasts and narratives for all (or selected) feeders, then
produces a plain-language summary with the most critical feeder highlighted.
All key numbers in the summary use «fact» markers.
"""

from __future__ import annotations

from dataclasses import asdict

from openstef_narrator.engine import explain
from openstef_narrator.feeders import FEEDERS, get_feeder
from openstef_narrator.forecast import generate_forecast
from openstef_narrator.formatters import highlight_markers
from openstef_narrator.templates import _f


def rollup(feeder_ids: list[str] | None = None, seed: int = 42) -> dict:
    """Generate forecasts and narratives for multiple feeders, then summarise.

    Parameters
    ----------
    feeder_ids : list[str] or None
        Feeders to include.  ``None`` means all known feeders.
    seed : int
        Deterministic seed passed to each forecast.

    Returns
    -------
    dict with keys:
        summary   — 1-2 sentence plain-language rollup with «fact» markers
        feeders   — list of per-feeder dicts (context + narrative + meta)
        worst     — feeder_id with the highest peak_pct
        at_risk   — list of feeder_ids where peak_pct >= 0.85
    """
    ids = feeder_ids if feeder_ids is not None else [f.id for f in FEEDERS]

    # Validate all feeder ids up-front
    for fid in ids:
        get_feeder(fid)  # raises ValueError if unknown

    results: list[dict] = []
    for fid in ids:
        ctx = generate_forecast(feeder_id=fid, seed=seed, use_synth=False)
        report, meta = explain(ctx, verbosity="standard", backend="template")
        segments = {
            "situation": highlight_markers(report.situation),
            "risk": highlight_markers(report.risk),
            "recommendation": highlight_markers(report.recommendation),
        }
        results.append({
            "forecast_context": asdict(ctx),
            "report": asdict(report),
            "meta": asdict(meta),
            "segments": segments,
        })

    # Derive aggregate statistics
    total = len(results)
    at_risk = [
        r["forecast_context"]["feeder_id"]
        for r in results
        if r["forecast_context"]["peak_pct"] >= 0.85
    ]
    worst_entry = max(results, key=lambda r: r["forecast_context"]["peak_pct"])
    worst_id = worst_entry["forecast_context"]["feeder_id"]
    worst_name = worst_entry["forecast_context"]["feeder_name"]
    worst_district = worst_entry["forecast_context"]["district"]
    worst_pct = worst_entry["forecast_context"]["peak_pct"]

    # Build the summary sentence with «fact» markers
    n_risk = len(at_risk)
    n_risk_f = _f(str(n_risk))
    total_f = _f(str(total))
    worst_pct_f = _f(f"{round(worst_pct * 100)}%")
    worst_name_f = _f(worst_name)
    worst_district_f = _f(worst_district)

    if n_risk == 0:
        summary = (
            f"All {total_f} feeders are within comfortable limits. "
            f"{worst_name_f} in {worst_district_f} has the highest loading at {worst_pct_f} of rating."
        )
    else:
        summary = (
            f"{n_risk_f} of {total_f} feeders at elevated risk. "
            f"{worst_name_f} in {worst_district_f} is the most critical at {worst_pct_f} of rating."
        )

    return {
        "summary": summary,
        "feeders": results,
        "worst": worst_id,
        "at_risk": at_risk,
    }
