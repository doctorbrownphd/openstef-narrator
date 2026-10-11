"""Tests for core domain types."""

import pytest
from openstef_narrator.feeders import FEEDERS, get_feeder
from openstef_narrator.scenarios import SCENARIOS, detect_scenario, get_scenario
from openstef_narrator.types import Driver, ForecastPoint, NarrativeMeta, NarrativeReport


class TestFeeders:
    def test_count(self):
        assert len(FEEDERS) == 5

    def test_lookup(self):
        f = get_feeder("feeder7")
        assert f.name == "Feeder 7"
        assert f.capacity_mw == 8.4

    def test_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown feeder"):
            get_feeder("feeder99")

    def test_all_ids_unique(self):
        ids = [f.id for f in FEEDERS]
        assert len(ids) == len(set(ids))

    def test_all_have_scenarios(self):
        valid = {s.id for s in SCENARIOS}
        for f in FEEDERS:
            assert f.scenario in valid


class TestScenarios:
    def test_count(self):
        assert len(SCENARIOS) == 5

    def test_lookup(self):
        s = get_scenario("overload_risk")
        assert s.tone == "urgent"

    def test_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown scenario"):
            get_scenario("blackout")

    def test_detect_overload(self):
        assert detect_scenario(1.01, 0.065) == "overload_risk"

    def test_detect_all_clear(self):
        assert detect_scenario(0.50, 0.05) == "all_clear"

    def test_detect_low_confidence(self):
        assert detect_scenario(0.80, 0.20) == "low_confidence"

    def test_detect_demand_response(self):
        assert detect_scenario(0.90, 0.08) == "demand_response"

    def test_detect_peak_forecast(self):
        assert detect_scenario(0.96, 0.07) == "peak_forecast"


class TestDataclasses:
    def test_driver_frozen(self):
        d = Driver("snow", "Cold", "16F", "a cold front")
        with pytest.raises(AttributeError):
            d.label = "Hot"

    def test_forecast_point(self):
        p = ForecastPoint(0, 14, 3.0, 5.0, 7.0, 22.0)
        assert p.p50 == 5.0

    def test_narrative_report(self):
        r = NarrativeReport("sit", "risk", "rec", "")
        assert r.situation == "sit"

    def test_narrative_meta(self):
        m = NarrativeMeta("nar-1", "run-1", "peak_forecast", "standard", "template_fallback", "2026-06-02T00:00:00Z")
        assert m.backend == "template_fallback"
