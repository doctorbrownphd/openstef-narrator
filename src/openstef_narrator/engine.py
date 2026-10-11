"""Narrative engine — single entry point for forecast explanation.

explain() is the public API. It renders a template draft, optionally
rewrites it via LLM, validates fact markers, and returns a typed report
with traceability metadata.
"""

from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone

from openstef_narrator.rewrite import (
    RewriteBackend,
    TemplateBackend,
    detect_backend,
    validate_markers,
)
from openstef_narrator.scenarios import get_scenario
from openstef_narrator.templates import Verbosity, render_template
from openstef_narrator.types import ForecastContext, NarrativeMeta, NarrativeReport


def explain(
    forecast_context: ForecastContext,
    verbosity: Verbosity = "standard",
    backend: str | None = None,
) -> tuple[NarrativeReport, NarrativeMeta]:
    """Generate a plain-language narrative report for a load forecast.

    Parameters
    ----------
    forecast_context : ForecastContext
        Typed input contract with forecast data, feeder metadata, and scenario.
    verbosity : "terse", "standard", or "full"
        Level of detail in the narrative.
    backend : str or None
        None = auto-detect LLM. "template" = force template only.
        "anthropic" = force Anthropic Claude.

    Returns
    -------
    report : NarrativeReport
        Prose with «fact» markers: situation, risk, recommendation, audit.
    meta : NarrativeMeta
        Traceability: narrative_id, run_id, backend, verbosity, timestamp,
        plus audit enrichment (model version, fallback sections, validation).
    """
    t0 = time.monotonic()

    # Track the requested backend for the audit trail
    backend_requested = backend or "auto"

    # Step 1: Render template draft with all facts injected
    template_report = render_template(forecast_context, verbosity)

    # Step 2: Resolve scenario and check template-only policy (1.5)
    scenario = get_scenario(forecast_context.scenario)
    tone = scenario.tone

    # Select rewrite backend — policy override for urgent scenarios
    if backend == "template" or scenario.template_only:
        rw: RewriteBackend = TemplateBackend()
        if scenario.template_only:
            backend_requested = f"{backend_requested}|policy:template_only"
    else:
        rw = detect_backend()

    initial_backend = rw.name
    model_version = getattr(rw, "model_version", "")
    fallback_sections: list[str] = []
    all_validations_passed = True

    # Step 3: Rewrite each section via LLM (if available)

    try:
        situation = rw.rewrite(template_report.situation, {}, tone)
        risk = rw.rewrite(template_report.risk, {}, tone)
        recommendation = rw.rewrite(template_report.recommendation, {}, tone)
        audit = template_report.audit  # audit text is never rewritten

        # Step 4: Validate fact markers survived in each section
        if not validate_markers(template_report.situation, situation):
            situation = template_report.situation
            fallback_sections.append("situation")
            all_validations_passed = False

        if not validate_markers(template_report.risk, risk):
            risk = template_report.risk
            fallback_sections.append("risk")
            all_validations_passed = False

        if not validate_markers(template_report.recommendation, recommendation):
            recommendation = template_report.recommendation
            fallback_sections.append("recommendation")
            all_validations_passed = False

    except Exception:
        # Step 5: Full fallback on LLM error
        situation = template_report.situation
        risk = template_report.risk
        recommendation = template_report.recommendation
        audit = template_report.audit
        fallback_sections = ["situation", "risk", "recommendation"]
        all_validations_passed = False

    # Determine resolved backend: if any section fell back, record it
    if fallback_sections:
        if len(fallback_sections) == 3:
            backend_resolved = "template_fallback"
        else:
            backend_resolved = f"{initial_backend}+partial_fallback"
    else:
        backend_resolved = initial_backend

    # Step 6: Historical analogue (standard and full verbosity only)
    analogue_text = ""
    if verbosity in ("standard", "full"):
        from openstef_narrator.analogues import find_analogues, format_analogue_prose

        analogues = find_analogues(forecast_context, top_k=1)
        if analogues:
            analogue_text = format_analogue_prose(analogues[0])

    report = NarrativeReport(
        situation=situation,
        risk=risk,
        recommendation=recommendation,
        audit=audit,
        analogue=analogue_text,
    )

    latency_ms = int((time.monotonic() - t0) * 1000)

    meta = NarrativeMeta(
        narrative_id=f"nar-{uuid.uuid4().hex[:8]}",
        forecast_run_id=forecast_context.forecast_run_id,
        scenario=forecast_context.scenario,
        verbosity=verbosity,
        backend=backend_resolved,
        generated_at=datetime.now(timezone.utc).isoformat(),
        model_version=model_version,
        backend_requested=backend_requested,
        backend_resolved=backend_resolved,
        validation_passed=all_validations_passed,
        fallback_sections=tuple(fallback_sections),
        latency_ms=latency_ms,
        temperature=0.0 if model_version else 0.0,
    )

    return report, meta
