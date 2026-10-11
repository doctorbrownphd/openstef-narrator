"""Tests for detect_scenario_with_flags and updated detect_scenario."""

from openstef_narrator.scenarios import detect_scenario, detect_scenario_with_flags


class TestDetectScenarioWithFlags:
    """detect_scenario_with_flags returns primary + secondary overlap flags."""

    def test_primary_matches_detect_scenario(self):
        """Primary result must always agree with detect_scenario."""
        cases = [
            (0.50, 0.05),  # all_clear
            (0.90, 0.08),  # demand_response
            (0.96, 0.07),  # peak_forecast
            (1.01, 0.06),  # overload_risk
            (0.80, 0.20),  # low_confidence
        ]
        for peak_pct, bw in cases:
            primary, _ = detect_scenario_with_flags(peak_pct, bw)
            assert primary == detect_scenario(peak_pct, bw), (
                f"Mismatch at peak_pct={peak_pct}, bw={bw}"
            )

    def test_all_clear_no_flags(self):
        primary, flags = detect_scenario_with_flags(0.50, 0.05)
        assert primary == "all_clear"
        assert flags == ()

    def test_overload_with_wide_band_gets_low_confidence_flag(self):
        """peak_pct >= 1.0 wins, but band_width > 0.15 is a secondary flag."""
        # With band_width > 0.15, low_confidence wins the precedence
        primary, flags = detect_scenario_with_flags(1.05, 0.20)
        assert primary == "low_confidence"
        assert "overload_risk" in flags
        assert "peak_forecast" in flags

    def test_low_confidence_with_high_peak_has_flags(self):
        """Wide band + high load -> low_confidence primary, overload secondary."""
        primary, flags = detect_scenario_with_flags(1.01, 0.18)
        assert primary == "low_confidence"
        assert "overload_risk" in flags

    def test_peak_forecast_no_overlap(self):
        primary, flags = detect_scenario_with_flags(0.96, 0.07)
        assert primary == "peak_forecast"
        # No other thresholds match: not >= 1.0, not < 0.75, not in 0.85-0.95
        assert flags == ()

    def test_demand_response_no_overlap(self):
        primary, flags = detect_scenario_with_flags(0.90, 0.08)
        assert primary == "demand_response"
        # peak_forecast flag because peak_pct >= 0.85
        assert "peak_forecast" in flags

    def test_overload_with_tight_band(self):
        """Pure overload, tight band — secondary flag is peak_forecast."""
        primary, flags = detect_scenario_with_flags(1.01, 0.06)
        assert primary == "overload_risk"
        assert "peak_forecast" in flags

    def test_low_confidence_mild_load(self):
        """Wide band but mild load — low_confidence primary, no DR/overload flags."""
        primary, flags = detect_scenario_with_flags(0.60, 0.20)
        assert primary == "low_confidence"
        assert "all_clear" in flags
        assert "overload_risk" not in flags
        assert "demand_response" not in flags


class TestDetectScenarioPrecedenceDoc:
    """Verify the documented precedence order is correct."""

    def test_low_confidence_beats_overload(self):
        """Wide band takes priority over overload."""
        assert detect_scenario(1.05, 0.20) == "low_confidence"

    def test_overload_beats_demand_response(self):
        """At 100%+ peak, overload trumps the DR range."""
        assert detect_scenario(1.00, 0.10) == "overload_risk"

    def test_all_clear_beats_default(self):
        assert detect_scenario(0.50, 0.05) == "all_clear"
