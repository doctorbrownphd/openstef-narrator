"""Tests for system-level rollup."""

import pytest
from openstef_narrator.rollup import rollup


class TestRollupBasic:
    def test_returns_all_keys(self):
        result = rollup(seed=42)
        assert "summary" in result
        assert "feeders" in result
        assert "worst" in result
        assert "at_risk" in result

    def test_all_feeders_included(self):
        result = rollup(seed=42)
        assert len(result["feeders"]) == 5

    def test_subset_of_feeders(self):
        result = rollup(feeder_ids=["feeder7", "feeder3"], seed=42)
        assert len(result["feeders"]) == 2
        ids = [f["forecast_context"]["feeder_id"] for f in result["feeders"]]
        assert "feeder7" in ids
        assert "feeder3" in ids

    def test_unknown_feeder_raises(self):
        with pytest.raises(ValueError, match="Unknown feeder"):
            rollup(feeder_ids=["nonexistent"])


class TestRollupSummary:
    def test_summary_has_fact_markers(self):
        result = rollup(seed=42)
        assert "\u00ab" in result["summary"]
        assert "\u00bb" in result["summary"]

    def test_summary_mentions_worst_feeder(self):
        result = rollup(seed=42)
        # The worst feeder's name should appear in the summary (inside markers)
        worst_id = result["worst"]
        worst_name = next(
            f["forecast_context"]["feeder_name"]
            for f in result["feeders"]
            if f["forecast_context"]["feeder_id"] == worst_id
        )
        assert worst_name in result["summary"]

    def test_summary_mentions_risk_count(self):
        result = rollup(seed=42)
        # Summary should contain a count of at-risk feeders
        n_risk = len(result["at_risk"])
        assert str(n_risk) in result["summary"]


class TestRollupWorst:
    def test_worst_is_highest_peak_pct(self):
        result = rollup(seed=42)
        peak_pcts = {
            f["forecast_context"]["feeder_id"]: f["forecast_context"]["peak_pct"]
            for f in result["feeders"]
        }
        actual_worst = max(peak_pcts, key=lambda k: peak_pcts[k])
        assert result["worst"] == actual_worst


class TestRollupAtRisk:
    def test_at_risk_threshold(self):
        result = rollup(seed=42)
        for f in result["feeders"]:
            fid = f["forecast_context"]["feeder_id"]
            pct = f["forecast_context"]["peak_pct"]
            if pct >= 0.85:
                assert fid in result["at_risk"], f"{fid} at {pct} should be at_risk"
            else:
                assert fid not in result["at_risk"], f"{fid} at {pct} should NOT be at_risk"


class TestRollupPerFeeder:
    def test_each_feeder_has_report(self):
        result = rollup(seed=42)
        for f in result["feeders"]:
            assert "report" in f
            assert "meta" in f
            assert "segments" in f
            assert f["report"]["situation"]

    def test_each_feeder_has_forecast_context(self):
        result = rollup(seed=42)
        for f in result["feeders"]:
            ctx = f["forecast_context"]
            assert "feeder_id" in ctx
            assert "peak_pct" in ctx
            assert "scenario" in ctx


class TestRollupDeterminism:
    def test_same_seed_same_result(self):
        r1 = rollup(seed=42)
        r2 = rollup(seed=42)
        assert r1["worst"] == r2["worst"]
        assert r1["at_risk"] == r2["at_risk"]
        assert r1["summary"] == r2["summary"]
