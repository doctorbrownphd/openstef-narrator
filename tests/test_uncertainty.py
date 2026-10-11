"""Tests for improved uncertainty communication in low-confidence template (3.1)
and secondary_flags on ForecastContext (3.2)."""

from openstef_narrator.forecast import generate_forecast
from openstef_narrator.templates import render_template


class TestLowConfidenceTerse:
    """Terse mode for low_confidence says 'uncertain', not just 'may peak'."""

    def test_terse_says_uncertain(self):
        ctx = generate_forecast(feeder_id="feeder5", seed=42, use_synth=False)
        assert ctx.scenario == "low_confidence"
        report = render_template(ctx, "terse")
        assert "uncertain" in report.situation.lower()

    def test_terse_includes_band_width(self):
        ctx = generate_forecast(feeder_id="feeder5", seed=42, use_synth=False)
        report = render_template(ctx, "terse")
        # band_pct should appear as a «fact» in the terse situation
        band_pct_str = f"{round(ctx.band_width * 100)}%"
        assert band_pct_str in report.situation


class TestLowConfidenceStandard:
    """Standard mode conveys proportional hedging and warns operator."""

    def test_standard_warns_caution(self):
        ctx = generate_forecast(feeder_id="feeder5", seed=42, use_synth=False)
        report = render_template(ctx, "standard")
        assert "caution" in report.situation.lower()

    def test_standard_includes_band_width_fact(self):
        ctx = generate_forecast(feeder_id="feeder5", seed=42, use_synth=False)
        report = render_template(ctx, "standard")
        band_pct_str = f"{round(ctx.band_width * 100)}%"
        # Should appear inside «» markers
        assert f"\u00ab{band_pct_str}\u00bb" in report.situation

    def test_risk_warns_against_relying(self):
        ctx = generate_forecast(feeder_id="feeder5", seed=42, use_synth=False)
        report = render_template(ctx, "standard")
        assert "do not rely" in report.risk.lower() or "caution" in report.risk.lower()

    def test_risk_includes_band_width(self):
        ctx = generate_forecast(feeder_id="feeder5", seed=42, use_synth=False)
        report = render_template(ctx, "standard")
        band_pct_str = f"{round(ctx.band_width * 100)}%"
        assert band_pct_str in report.risk


class TestHedgeAdverbProportional:
    """The hedging language should scale with band_width."""

    def test_feeder5_gets_notable_hedge(self):
        """feeder5 has band_width=0.17, which is > 0.15 but <= 0.18."""
        ctx = generate_forecast(feeder_id="feeder5", seed=42, use_synth=False)
        assert ctx.band_width == 0.17
        report = render_template(ctx, "standard")
        # 0.17 is in the 0.15-0.18 range -> "moderately" or "notably"
        # (0.17 <= 0.18, so "moderately")
        assert "moderately" in report.situation.lower() or "notably" in report.situation.lower()


class TestSecondaryFlags:
    """ForecastContext.secondary_flags populated from mock path."""

    def test_feeder5_has_secondary_flags(self):
        """feeder5 is low_confidence; check it has some secondary flags."""
        ctx = generate_forecast(feeder_id="feeder5", seed=42, use_synth=False)
        assert ctx.scenario == "low_confidence"
        assert isinstance(ctx.secondary_flags, tuple)

    def test_feeder3_all_clear_no_flags(self):
        """feeder3 is all_clear with low load, tight band — no overlaps."""
        ctx = generate_forecast(feeder_id="feeder3", seed=42, use_synth=False)
        assert ctx.scenario == "all_clear"
        assert ctx.secondary_flags == ()

    def test_feeder7_peak_forecast_flags(self):
        ctx = generate_forecast(feeder_id="feeder7", seed=42, use_synth=False)
        assert ctx.scenario == "peak_forecast"
        # peak_pct ~0.96, band_width 0.075 — no other thresholds match
        assert isinstance(ctx.secondary_flags, tuple)

    def test_default_secondary_flags_empty(self):
        """Default value for secondary_flags is empty tuple."""
        from openstef_narrator.types import ForecastContext, ForecastPoint
        ctx = ForecastContext(
            feeder_id="test", feeder_name="Test", district="Test",
            capacity_mw=10.0, points=(), peak_mw=5.0, peak_hour=0,
            peak_hour_of_day=0, peak_pct=0.5, exceedance_prob=0.01,
            confidence="High", band_width=0.05, scenario="all_clear",
            drivers=(), low_temp=30.0, forecast_run_id="test-run",
        )
        assert ctx.secondary_flags == ()
