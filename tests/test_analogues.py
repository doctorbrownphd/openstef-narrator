"""Tests for historical analogue retrieval."""

import pytest
from openstef_narrator.analogues import (
    HISTORICAL_EVENTS,
    HistoricalEvent,
    find_analogues,
    format_analogue_prose,
)
from openstef_narrator.feeders import FEEDERS
from openstef_narrator.forecast import generate_forecast


class TestHistoricalEvents:
    def test_seeded_event_count(self):
        """At least 8 events in the store."""
        assert len(HISTORICAL_EVENTS) >= 8

    def test_events_are_frozen(self):
        """Events are immutable dataclasses."""
        evt = HISTORICAL_EVENTS[0]
        with pytest.raises(AttributeError):
            evt.label = "modified"  # type: ignore[misc]

    def test_events_have_required_fields(self):
        for evt in HISTORICAL_EVENTS:
            assert evt.event_id
            assert evt.date
            assert evt.label
            assert evt.scenario
            assert isinstance(evt.peak_pct, float)
            assert isinstance(evt.low_temp, (int, float))
            assert isinstance(evt.feeders_affected, int)
            assert evt.outcome
            assert evt.lesson

    def test_events_span_scenarios(self):
        """Events cover at least 4 different scenarios."""
        scenarios = {evt.scenario for evt in HISTORICAL_EVENTS}
        assert len(scenarios) >= 4


class TestFindAnalogues:
    def test_returns_list(self):
        ctx = generate_forecast(feeder_id="feeder7", use_synth=False)
        result = find_analogues(ctx)
        assert isinstance(result, list)

    def test_default_top_k_is_2(self):
        ctx = generate_forecast(feeder_id="feeder7", use_synth=False)
        result = find_analogues(ctx)
        assert len(result) == 2

    def test_custom_top_k(self):
        ctx = generate_forecast(feeder_id="feeder7", use_synth=False)
        result = find_analogues(ctx, top_k=3)
        assert len(result) == 3

    def test_top_k_1(self):
        ctx = generate_forecast(feeder_id="feeder7", use_synth=False)
        result = find_analogues(ctx, top_k=1)
        assert len(result) == 1

    def test_returns_historical_events(self):
        ctx = generate_forecast(feeder_id="feeder7", use_synth=False)
        result = find_analogues(ctx, top_k=2)
        for evt in result:
            assert isinstance(evt, HistoricalEvent)

    def test_scenario_match_preferred(self):
        """The top match should have the same scenario as the context."""
        for feeder in FEEDERS:
            ctx = generate_forecast(feeder_id=feeder.id, use_synth=False)
            result = find_analogues(ctx, top_k=1)
            assert result[0].scenario == ctx.scenario, (
                f"For {feeder.id} (scenario={ctx.scenario}), "
                f"top match was {result[0].scenario}"
            )

    @pytest.mark.parametrize("feeder_id", [f.id for f in FEEDERS])
    def test_works_for_all_feeders(self, feeder_id):
        ctx = generate_forecast(feeder_id=feeder_id, use_synth=False)
        result = find_analogues(ctx, top_k=2)
        assert len(result) >= 1


class TestFormatAnalogueProse:
    def test_returns_string(self):
        evt = HISTORICAL_EVENTS[0]
        result = format_analogue_prose(evt)
        assert isinstance(result, str)

    def test_contains_label(self):
        evt = HISTORICAL_EVENTS[0]
        result = format_analogue_prose(evt)
        assert evt.label in result

    def test_contains_lesson(self):
        evt = HISTORICAL_EVENTS[0]
        result = format_analogue_prose(evt)
        assert evt.lesson in result

    def test_contains_outcome(self):
        evt = HISTORICAL_EVENTS[0]
        result = format_analogue_prose(evt)
        assert evt.outcome in result

    def test_fact_markers_present(self):
        """All factual claims are wrapped in markers."""
        evt = HISTORICAL_EVENTS[0]
        result = format_analogue_prose(evt)
        assert "\u00ab" in result
        assert "\u00bb" in result
        # Label, lesson, and outcome should each be marked
        assert f"\u00ab{evt.label}\u00bb" in result
        assert f"\u00ab{evt.lesson}\u00bb" in result
        assert f"\u00ab{evt.outcome}\u00bb" in result

    def test_starts_with_this_pattern(self):
        evt = HISTORICAL_EVENTS[0]
        result = format_analogue_prose(evt)
        assert result.startswith("This pattern resembles")


class TestAnalogueInEngine:
    """Analogues are wired into the narrative engine."""

    def test_standard_has_analogue(self):
        ctx = generate_forecast(feeder_id="feeder7", use_synth=False)
        from openstef_narrator.engine import explain
        report, _ = explain(ctx, verbosity="standard", backend="template")
        assert report.analogue
        assert "\u00ab" in report.analogue

    def test_full_has_analogue(self):
        ctx = generate_forecast(feeder_id="feeder7", use_synth=False)
        from openstef_narrator.engine import explain
        report, _ = explain(ctx, verbosity="full", backend="template")
        assert report.analogue
        assert "\u00ab" in report.analogue

    def test_terse_has_no_analogue(self):
        ctx = generate_forecast(feeder_id="feeder7", use_synth=False)
        from openstef_narrator.engine import explain
        report, _ = explain(ctx, verbosity="terse", backend="template")
        assert report.analogue == ""

    @pytest.mark.parametrize("feeder_id", [f.id for f in FEEDERS])
    def test_all_feeders_standard(self, feeder_id):
        ctx = generate_forecast(feeder_id=feeder_id, use_synth=False)
        from openstef_narrator.engine import explain
        report, _ = explain(ctx, verbosity="standard", backend="template")
        assert report.analogue  # all feeders get an analogue at standard+
