"""Tests for counterfactual narrative generation."""

import pytest
from openstef_narrator.counterfactual import (
    PERTURBATIONS,
    Perturbation,
    format_counterfactual_prose,
    generate_all_counterfactuals,
    generate_counterfactual,
    get_perturbation,
)
from openstef_narrator.feeders import FEEDERS
from openstef_narrator.forecast import generate_forecast


class TestPerturbations:
    def test_seeded_count(self):
        """At least 4 perturbations in the library."""
        assert len(PERTURBATIONS) >= 4

    def test_perturbations_are_frozen(self):
        p = PERTURBATIONS[0]
        with pytest.raises(AttributeError):
            p.label = "modified"  # type: ignore[misc]

    def test_perturbations_have_required_fields(self):
        for p in PERTURBATIONS:
            assert p.id
            assert p.label
            assert p.description
            assert isinstance(p.temp_offset, (int, float))
            assert isinstance(p.peak_hour_shift, int)

    def test_get_perturbation_valid(self):
        p = get_perturbation("early_front")
        assert p.id == "early_front"

    def test_get_perturbation_invalid(self):
        with pytest.raises(ValueError, match="Unknown perturbation"):
            get_perturbation("nonexistent")


class TestGenerateCounterfactual:
    def test_returns_dict(self):
        ctx = generate_forecast(feeder_id="feeder7", use_synth=False)
        p = get_perturbation("early_front")
        result = generate_counterfactual(ctx, p)
        assert isinstance(result, dict)

    def test_result_has_required_keys(self):
        ctx = generate_forecast(feeder_id="feeder7", use_synth=False)
        p = get_perturbation("early_front")
        result = generate_counterfactual(ctx, p)
        assert "perturbation_id" in result
        assert "perturbation_label" in result
        assert "original" in result
        assert "perturbed" in result
        assert "delta" in result
        assert "narrative" in result

    def test_original_matches_context(self):
        ctx = generate_forecast(feeder_id="feeder7", use_synth=False)
        p = get_perturbation("early_front")
        result = generate_counterfactual(ctx, p)
        assert result["original"]["peak_mw"] == ctx.peak_mw
        assert result["original"]["scenario"] == ctx.scenario

    def test_cold_perturbation_increases_load(self):
        """Colder temperatures should increase heating load."""
        ctx = generate_forecast(feeder_id="feeder7", use_synth=False)
        p = get_perturbation("colder_than_forecast")
        result = generate_counterfactual(ctx, p)
        assert result["delta"]["peak_mw_change"] > 0

    def test_warm_perturbation_decreases_load(self):
        """Warmer temperatures should decrease heating load."""
        ctx = generate_forecast(feeder_id="feeder7", use_synth=False)
        p = get_perturbation("warmer_than_forecast")
        result = generate_counterfactual(ctx, p)
        assert result["delta"]["peak_mw_change"] < 0

    def test_early_front_shifts_peak_earlier(self):
        ctx = generate_forecast(feeder_id="feeder7", use_synth=False)
        p = get_perturbation("early_front")
        result = generate_counterfactual(ctx, p)
        assert result["delta"]["peak_hour_shift"] == -3

    def test_delayed_front_shifts_peak_later(self):
        ctx = generate_forecast(feeder_id="feeder7", use_synth=False)
        p = get_perturbation("delayed_front")
        result = generate_counterfactual(ctx, p)
        assert result["delta"]["peak_hour_shift"] == 3

    def test_ev_surge_increases_load(self):
        ctx = generate_forecast(feeder_id="feeder7", use_synth=False)
        p = get_perturbation("ev_surge")
        result = generate_counterfactual(ctx, p)
        assert result["perturbed"]["peak_mw"] > result["original"]["peak_mw"]

    def test_does_not_call_generate_forecast(self, monkeypatch):
        """Counterfactual works purely by perturbation — no forecast call."""
        ctx = generate_forecast(feeder_id="feeder7", use_synth=False)
        p = get_perturbation("early_front")

        # Patch generate_forecast to raise if called
        import openstef_narrator.counterfactual as cf_mod
        monkeypatch.setattr(
            cf_mod, "generate_forecast",
            lambda **kw: (_ for _ in ()).throw(AssertionError("should not call generate_forecast")),
            raising=False,
        )
        # Should not raise
        result = generate_counterfactual(ctx, p)
        assert result["narrative"]

    @pytest.mark.parametrize("feeder_id", [f.id for f in FEEDERS])
    def test_works_for_all_feeders(self, feeder_id):
        ctx = generate_forecast(feeder_id=feeder_id, use_synth=False)
        p = get_perturbation("early_front")
        result = generate_counterfactual(ctx, p)
        assert result["narrative"]


class TestFormatCounterfactualProse:
    def test_fact_markers_present(self):
        ctx = generate_forecast(feeder_id="feeder7", use_synth=False)
        p = get_perturbation("early_front")
        result = generate_counterfactual(ctx, p)
        narrative = result["narrative"]
        assert "\u00ab" in narrative
        assert "\u00bb" in narrative

    def test_contains_perturbation_label(self):
        ctx = generate_forecast(feeder_id="feeder7", use_synth=False)
        p = get_perturbation("early_front")
        result = generate_counterfactual(ctx, p)
        assert p.label in result["narrative"]

    def test_starts_with_if(self):
        ctx = generate_forecast(feeder_id="feeder7", use_synth=False)
        p = get_perturbation("early_front")
        result = generate_counterfactual(ctx, p)
        assert result["narrative"].startswith("If")

    def test_scenario_change_mentioned(self):
        """When scenario changes, the prose should mention the new classification."""
        # Use feeder9 (demand_response, peak_pct ~0.88) with colder perturbation
        # which should push it toward peak_forecast or overload
        ctx = generate_forecast(feeder_id="feeder9", use_synth=False)
        p = get_perturbation("colder_than_forecast")
        result = generate_counterfactual(ctx, p)
        if result["delta"]["scenario_changed"]:
            assert "classification" in result["narrative"]


class TestGenerateAllCounterfactuals:
    def test_returns_list(self):
        ctx = generate_forecast(feeder_id="feeder7", use_synth=False)
        results = generate_all_counterfactuals(ctx)
        assert isinstance(results, list)
        assert len(results) >= 1

    def test_sorted_by_severity(self):
        """Results are sorted by peak_pct_change descending."""
        ctx = generate_forecast(feeder_id="feeder7", use_synth=False)
        results = generate_all_counterfactuals(ctx)
        if len(results) >= 2:
            deltas = [r["delta"]["peak_pct_change"] for r in results]
            assert deltas == sorted(deltas, reverse=True)

    @pytest.mark.parametrize("feeder_id", [f.id for f in FEEDERS])
    def test_works_for_all_feeders(self, feeder_id):
        ctx = generate_forecast(feeder_id=feeder_id, use_synth=False)
        results = generate_all_counterfactuals(ctx)
        assert isinstance(results, list)
        # Every result should have a narrative
        for r in results:
            assert r["narrative"]

    def test_all_clear_filters_warm_colder(self):
        """For an all_clear summer scenario with warm temps, colder should be filtered."""
        ctx = generate_forecast(feeder_id="feeder3", use_synth=False)
        assert ctx.scenario == "all_clear"
        results = generate_all_counterfactuals(ctx)
        perturbation_ids = [r["perturbation_id"] for r in results]
        # colder_than_forecast should be filtered when low_temp > 55
        if ctx.low_temp > 55.0:
            assert "colder_than_forecast" not in perturbation_ids


class TestCounterfactualAPI:
    """Tests for the REST API endpoints."""

    from fastapi.testclient import TestClient
    from openstef_narrator.api import app

    client = TestClient(app)

    def test_get_counterfactual(self):
        r = self.client.get("/api/counterfactual", params={"feeder_id": "feeder7", "seed": 42})
        assert r.status_code == 200
        data = r.json()
        assert "counterfactuals" in data
        assert len(data["counterfactuals"]) >= 1
        assert data["feeder_id"] == "feeder7"

    def test_get_counterfactual_default_params(self):
        r = self.client.get("/api/counterfactual")
        assert r.status_code == 200

    def test_get_counterfactual_unknown_feeder(self):
        r = self.client.get("/api/counterfactual", params={"feeder_id": "bad"})
        assert r.status_code == 400

    def test_post_counterfactual(self):
        r = self.client.post("/api/counterfactual", json={
            "feeder_id": "feeder7",
            "perturbation_id": "early_front",
            "seed": 42,
        })
        assert r.status_code == 200
        data = r.json()
        assert "counterfactual" in data
        assert data["counterfactual"]["perturbation_id"] == "early_front"

    def test_post_counterfactual_unknown_feeder(self):
        r = self.client.post("/api/counterfactual", json={
            "feeder_id": "bad",
            "perturbation_id": "early_front",
        })
        assert r.status_code == 400

    def test_post_counterfactual_unknown_perturbation(self):
        r = self.client.post("/api/counterfactual", json={
            "feeder_id": "feeder7",
            "perturbation_id": "nonexistent",
        })
        assert r.status_code == 400

    def test_post_counterfactual_has_narrative(self):
        r = self.client.post("/api/counterfactual", json={
            "feeder_id": "feeder7",
            "perturbation_id": "colder_than_forecast",
        })
        data = r.json()
        narrative = data["counterfactual"]["narrative"]
        assert "\u00ab" in narrative
        assert "\u00bb" in narrative

    @pytest.mark.parametrize("perturbation_id", [p.id for p in PERTURBATIONS])
    def test_all_perturbations_via_post(self, perturbation_id):
        r = self.client.post("/api/counterfactual", json={
            "feeder_id": "feeder7",
            "perturbation_id": perturbation_id,
        })
        assert r.status_code == 200
