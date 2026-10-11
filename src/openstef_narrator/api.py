"""FastAPI application — REST API and static file serving."""

from __future__ import annotations

import os
import pathlib
from dataclasses import asdict

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from openstef_narrator.audit import AuditStore
from openstef_narrator.engine import explain
from openstef_narrator.feeders import FEEDERS, get_feeder
from openstef_narrator.forecast import generate_forecast
from openstef_narrator.formatters import deliver, highlight_markers
from openstef_narrator.rollup import rollup
from openstef_narrator.scenarios import SCENARIOS

app = FastAPI(
    title="OpenSTEF Narrator",
    version="0.1.0",
    description="Plain-language narrative reports for load forecasts",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

_audit = AuditStore()


def _seed_audit():
    """Pre-populate audit trail with one narration per feeder for demo."""
    if _audit.count() > 0:
        return  # already seeded from a previous run (durable DB)
    for feeder in FEEDERS:
        ctx = generate_forecast(feeder_id=feeder.id, seed=42)
        report, meta = explain(ctx, verbosity="standard", backend=None)
        segments = {
            "situation": highlight_markers(report.situation),
            "risk": highlight_markers(report.risk),
            "recommendation": highlight_markers(report.recommendation),
        }
        _audit.append(report, meta, segments)


_seed_audit()


@app.get("/api/feeders")
def api_feeders() -> dict:
    return {"feeders": [asdict(f) for f in FEEDERS]}


@app.get("/api/forecast")
def api_forecast(feeder_id: str = Query("feeder7"), seed: int = Query(42)) -> dict:
    try:
        get_feeder(feeder_id)
    except ValueError:
        raise HTTPException(400, f"Unknown feeder: {feeder_id}")
    ctx = generate_forecast(feeder_id=feeder_id, seed=seed)
    return {
        "feeder_id": ctx.feeder_id, "feeder_name": ctx.feeder_name,
        "district": ctx.district, "capacity_mw": ctx.capacity_mw,
        "scenario": ctx.scenario, "confidence": ctx.confidence,
        "peak_mw": ctx.peak_mw, "peak_hour": ctx.peak_hour,
        "peak_hour_of_day": ctx.peak_hour_of_day, "peak_pct": ctx.peak_pct,
        "exceedance_prob": ctx.exceedance_prob, "band_width": ctx.band_width,
        "low_temp": ctx.low_temp, "forecast_run_id": ctx.forecast_run_id,
        "drivers": [asdict(d) for d in ctx.drivers],
        "points": [asdict(p) for p in ctx.points],
    }


class NarrateRequest(BaseModel):
    feeder_id: str = "feeder7"
    verbosity: str = "standard"
    backend: str | None = None
    seed: int = 42


@app.post("/api/narrate")
def api_narrate(body: NarrateRequest) -> dict:
    try:
        get_feeder(body.feeder_id)
    except ValueError:
        raise HTTPException(400, f"Unknown feeder: {body.feeder_id}")
    if body.verbosity not in ("terse", "standard", "full"):
        raise HTTPException(400, f"Invalid verbosity: {body.verbosity}")

    ctx = generate_forecast(feeder_id=body.feeder_id, seed=body.seed)
    report, meta = explain(ctx, verbosity=body.verbosity, backend=body.backend)

    segments = {
        "situation": highlight_markers(report.situation),
        "risk": highlight_markers(report.risk),
        "recommendation": highlight_markers(report.recommendation),
    }
    _audit.append(report, meta, segments)

    return {
        "report": asdict(report),
        "meta": asdict(meta),
        "segments": segments,
    }


@app.get("/api/scenarios")
def api_scenarios() -> dict:
    scenarios = []
    for s in SCENARIOS:
        example_feeder = next((f for f in FEEDERS if f.scenario == s.id), FEEDERS[0])
        ctx = generate_forecast(feeder_id=example_feeder.id, seed=42)
        report, _ = explain(ctx, verbosity="standard", backend="template")
        scenarios.append({
            **asdict(s),
            "example": {
                "feeder": example_feeder.name,
                "run_id": ctx.forecast_run_id,
                "situation": report.situation,
                "situation_segments": highlight_markers(report.situation),
                "recommendation": report.recommendation,
            },
        })
    return {"scenarios": scenarios}


@app.get("/api/rollup")
def api_rollup(seed: int = Query(42)) -> dict:
    return rollup(seed=seed)


class FeedbackRequest(BaseModel):
    narrative_id: str
    feedback: str  # "up", "down", or "note:..."


@app.post("/api/feedback")
def api_feedback(body: FeedbackRequest) -> dict:
    if body.feedback not in ("up", "down") and not body.feedback.startswith("note:"):
        raise HTTPException(
            400,
            f"Invalid feedback '{body.feedback}'. Must be 'up', 'down', or 'note:...'",
        )
    found = _audit.add_feedback(body.narrative_id, body.feedback)
    if not found:
        raise HTTPException(404, f"Narrative '{body.narrative_id}' not found")
    return {"status": "ok", "narrative_id": body.narrative_id}


@app.get("/api/feedback/summary")
def api_feedback_summary() -> dict:
    return {"summary": _audit.feedback_summary()}


@app.get("/api/audit")
def api_audit() -> dict:
    return {"entries": _audit.list_entries()}


class DeliverRequest(BaseModel):
    narrative_id: str
    targets: list[str] = ["opfab"]


@app.post("/api/deliver")
def api_deliver(body: DeliverRequest) -> dict:
    """Look up a narrative from the audit store and deliver it."""
    from openstef_narrator.types import NarrativeReport

    entries = _audit.list_entries()
    entry = next(
        (e for e in entries if e["meta"]["narrative_id"] == body.narrative_id),
        None,
    )
    if entry is None:
        raise HTTPException(404, f"Narrative '{body.narrative_id}' not found")

    report = NarrativeReport(
        situation=entry["report"]["situation"],
        risk=entry["report"]["risk"],
        recommendation=entry["report"]["recommendation"],
        audit=entry["report"]["audit"],
        analogue=entry["report"].get("analogue", ""),
    )

    results = deliver(report, targets=body.targets)
    return {"narrative_id": body.narrative_id, "delivery": results}


@app.get("/api/counterfactual")
def api_counterfactual_get(
    feeder_id: str = Query("feeder7"),
    seed: int = Query(42),
) -> dict:
    """Generate counterfactual analyses for all relevant perturbations."""
    from openstef_narrator.counterfactual import generate_all_counterfactuals

    try:
        get_feeder(feeder_id)
    except ValueError:
        raise HTTPException(400, f"Unknown feeder: {feeder_id}")

    ctx = generate_forecast(feeder_id=feeder_id, seed=seed)
    results = generate_all_counterfactuals(ctx)
    return {
        "feeder_id": feeder_id,
        "scenario": ctx.scenario,
        "counterfactuals": results,
    }


class CounterfactualRequest(BaseModel):
    feeder_id: str = "feeder7"
    perturbation_id: str = "early_front"
    seed: int = 42


@app.post("/api/counterfactual")
def api_counterfactual_post(body: CounterfactualRequest) -> dict:
    """Generate a single counterfactual analysis for one perturbation."""
    from openstef_narrator.counterfactual import (
        generate_counterfactual,
        get_perturbation,
    )

    try:
        get_feeder(body.feeder_id)
    except ValueError:
        raise HTTPException(400, f"Unknown feeder: {body.feeder_id}")

    try:
        perturbation = get_perturbation(body.perturbation_id)
    except ValueError:
        raise HTTPException(400, f"Unknown perturbation: {body.perturbation_id}")

    ctx = generate_forecast(feeder_id=body.feeder_id, seed=body.seed)
    result = generate_counterfactual(ctx, perturbation)
    return {
        "feeder_id": body.feeder_id,
        "scenario": ctx.scenario,
        "counterfactual": result,
    }


# Serve frontend: check editable-install path, then package-relative path
_web_candidates = [
    pathlib.Path(__file__).parent.parent.parent / "web" / "dist",  # editable install
    pathlib.Path(__file__).parent / "web_dist",                     # packaged install
]
_web_dist = next((p for p in _web_candidates if p.is_dir()), None)
if _web_dist:
    app.mount("/", StaticFiles(directory=str(_web_dist), html=True), name="static")


def main() -> None:
    import uvicorn
    host = os.getenv("NARRATOR_HOST", "0.0.0.0")
    port = int(os.getenv("NARRATOR_PORT", "8001"))
    uvicorn.run("openstef_narrator.api:app", host=host, port=port)
