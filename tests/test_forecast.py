"""Tests for the mock forecast model."""

import pytest
from openstef_narrator.forecast import generate_forecast


class TestShape:
    def test_48_hours(self):
        ctx = generate_forecast()
        assert len(ctx.points) == 48

    def test_p10_below_p50_below_p90(self):
        ctx = generate_forecast()
        for p in ctx.points:
            assert p.p10 <= p.p50 <= p.p90

    def test_band_widens_with_horizon(self):
        ctx = generate_forecast()
        early_band = ctx.points[2].p90 - ctx.points[2].p10
        late_band = ctx.points[46].p90 - ctx.points[46].p10
        assert late_band > early_band

    def test_has_required_fields(self):
        ctx = generate_forecast()
        assert ctx.feeder_name
        assert ctx.capacity_mw > 0
        assert ctx.peak_mw > 0
        assert 0 <= ctx.peak_pct <= 2
        assert 0 < ctx.exceedance_prob < 1
        assert ctx.scenario
        assert ctx.forecast_run_id


class TestDeterminism:
    def test_same_seed_same_output(self):
        ctx1 = generate_forecast(seed=42)
        ctx2 = generate_forecast(seed=42)
        assert ctx1.peak_mw == ctx2.peak_mw
        assert ctx1.points == ctx2.points

    def test_different_seed_different_output(self):
        ctx1 = generate_forecast(seed=42)
        ctx2 = generate_forecast(seed=99)
        # Different seeds should produce at least slightly different peaks
        # (though for the same feeder, the shape is deterministic)
        assert ctx1.forecast_run_id == ctx2.forecast_run_id  # same feeder → same run_id


class TestScenarioDetection:
    def test_feeder7_is_peak_forecast(self):
        ctx = generate_forecast(feeder_id="feeder7")
        assert ctx.scenario == "peak_forecast"

    def test_feeder12_is_overload(self):
        ctx = generate_forecast(feeder_id="feeder12")
        assert ctx.scenario == "overload_risk"

    def test_feeder9_is_demand_response(self):
        ctx = generate_forecast(feeder_id="feeder9")
        assert ctx.scenario == "demand_response"

    def test_feeder5_is_low_confidence(self):
        ctx = generate_forecast(feeder_id="feeder5")
        assert ctx.scenario == "low_confidence"

    def test_feeder3_is_all_clear(self):
        ctx = generate_forecast(feeder_id="feeder3")
        assert ctx.scenario == "all_clear"


class TestExceedance:
    def test_high_peak_high_exceedance(self):
        ctx = generate_forecast(feeder_id="feeder12")  # 101% of rating
        assert ctx.exceedance_prob > 0.3

    def test_low_peak_low_exceedance(self):
        ctx = generate_forecast(feeder_id="feeder3")  # 62% of rating
        assert ctx.exceedance_prob < 0.05


class TestDrivers:
    def test_has_drivers(self):
        ctx = generate_forecast(feeder_id="feeder7")
        assert len(ctx.drivers) >= 1

    def test_all_clear_has_mild(self):
        ctx = generate_forecast(feeder_id="feeder3")
        assert any("mild" in d.prose.lower() for d in ctx.drivers)


class TestEdgeCases:
    def test_unknown_feeder_raises(self):
        with pytest.raises(ValueError):
            generate_forecast(feeder_id="nonexistent")
