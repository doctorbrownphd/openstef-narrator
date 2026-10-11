"""Tests for the narrative engine — explain() entry point."""

import pytest
from openstef_narrator.engine import explain
from openstef_narrator.feeders import FEEDERS
from openstef_narrator.forecast import generate_forecast


class TestExplain:
    def test_returns_report_and_meta(self):
        ctx = generate_forecast()
        report, meta = explain(ctx)
        assert report.situation
        assert report.risk
        assert report.recommendation
        assert meta.narrative_id
        assert meta.forecast_run_id

    def test_template_fallback(self):
        ctx = generate_forecast()
        _, meta = explain(ctx, backend="template")
        assert meta.backend == "template_fallback"

    def test_fact_markers_present(self):
        ctx = generate_forecast()
        report, _ = explain(ctx)
        assert "«" in report.situation
        assert "»" in report.situation


class TestAllBranches:
    """All 15 scenario × verbosity combinations produce valid output."""

    @pytest.mark.parametrize("feeder_id", [f.id for f in FEEDERS])
    @pytest.mark.parametrize("verbosity", ["terse", "standard", "full"])
    def test_branch(self, feeder_id, verbosity):
        ctx = generate_forecast(feeder_id=feeder_id)
        report, meta = explain(ctx, verbosity=verbosity, backend="template")
        assert report.situation
        assert report.risk
        assert report.recommendation
        assert "«" in report.situation  # has at least one fact marker
        assert meta.backend == "template_fallback"

    @pytest.mark.parametrize("feeder_id", [f.id for f in FEEDERS])
    def test_full_has_audit(self, feeder_id):
        ctx = generate_forecast(feeder_id=feeder_id)
        report, _ = explain(ctx, verbosity="full", backend="template")
        assert report.audit  # full verbosity always has audit block


class TestVerbosityOrdering:
    def test_terse_shorter_than_standard(self):
        ctx = generate_forecast()
        terse, _ = explain(ctx, verbosity="terse", backend="template")
        standard, _ = explain(ctx, verbosity="standard", backend="template")
        assert len(terse.situation) < len(standard.situation)

    def test_standard_shorter_than_full(self):
        ctx = generate_forecast()
        standard, _ = explain(ctx, verbosity="standard", backend="template")
        full, _ = explain(ctx, verbosity="full", backend="template")
        assert len(standard.situation) < len(full.situation)


class TestScenarioDifferentiation:
    def test_different_scenarios_different_text(self):
        texts = set()
        for f in FEEDERS:
            ctx = generate_forecast(feeder_id=f.id)
            report, _ = explain(ctx, backend="template")
            texts.add(report.situation)
        assert len(texts) == 5  # all 5 feeders produce distinct narratives


class TestTemplateOnlyPolicy:
    """1.5: overload_risk is template-only by policy."""

    def test_overload_forced_to_template(self):
        """Even when backend=None (auto-detect), overload_risk uses template."""
        ctx = generate_forecast(feeder_id="feeder12", use_synth=False)
        assert ctx.scenario == "overload_risk"
        _, meta = explain(ctx, backend=None)
        assert "template" in meta.backend_resolved
        assert "policy:template_only" in meta.backend_requested

    def test_overload_ignores_explicit_backend(self):
        """Policy overrides even an explicit backend request."""
        ctx = generate_forecast(feeder_id="feeder12", use_synth=False)
        _, meta = explain(ctx, backend="anthropic")
        assert "template" in meta.backend_resolved

    def test_non_urgent_allows_llm(self):
        """Non-urgent scenarios don't force template."""
        ctx = generate_forecast(feeder_id="feeder7", use_synth=False)
        assert ctx.scenario == "peak_forecast"
        _, meta = explain(ctx, backend=None)
        # Will be template_fallback in practice (no API key), but the
        # policy flag should NOT be present
        assert "policy:template_only" not in meta.backend_requested
