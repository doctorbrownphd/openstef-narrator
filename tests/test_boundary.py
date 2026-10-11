"""Tests for the hallucination boundary — marker validation and driver protection."""

from openstef_narrator.rewrite import validate_markers, _find_rogue_numbers
from openstef_narrator.templates import render_template
from openstef_narrator.forecast import generate_forecast


class TestMarkerPreservation:
    """Existing behavior: all original markers must survive in rewrite."""

    def test_valid_rewrite(self):
        orig = "Load on «Feeder 7» reaches «94%» at «18:00»."
        rewrite = "«Feeder 7» is expected to hit «94%» of capacity around «18:00»."
        assert validate_markers(orig, rewrite)

    def test_dropped_marker_rejected(self):
        orig = "Load on «Feeder 7» reaches «94%» at «18:00»."
        rewrite = "Load on «Feeder 7» reaches 94% at «18:00»."  # dropped «94%»
        assert not validate_markers(orig, rewrite)

    def test_all_markers_dropped(self):
        orig = "«Feeder 7» peaks at «94%»."
        rewrite = "Feeder 7 peaks at 94%."
        assert not validate_markers(orig, rewrite)

    def test_passthrough_always_valid(self):
        orig = "«Feeder 7» peaks at «94%» at «18:00»."
        assert validate_markers(orig, orig)


class TestRogueNumberRejection:
    """New behavior: LLM must not invent numbers outside markers."""

    def test_rogue_percentage_rejected(self):
        orig = "Load on «Feeder 7» reaches «94%»."
        rewrite = "Load on «Feeder 7» reaches «94%», about 15% over normal."
        assert not validate_markers(orig, rewrite)

    def test_rogue_mw_rejected(self):
        orig = "Peak is «8.1 MW» on «Feeder 7»."
        rewrite = "Peak is «8.1 MW» on «Feeder 7», up from 6.5 MW yesterday."
        assert not validate_markers(orig, rewrite)

    def test_rogue_temperature_rejected(self):
        orig = "Temperature will drop to «16°F»."
        rewrite = "Temperature will drop to «16°F», with a 22°F wind chill."
        assert not validate_markers(orig, rewrite)

    def test_marked_numbers_allowed(self):
        orig = "Load reaches «94%» of «8.4 MW» at «16°F»."
        rewrite = "At «16°F», load hits «94%» of the «8.4 MW» rating."
        assert validate_markers(orig, rewrite)

    def test_no_numbers_always_valid(self):
        orig = "The feeder has ample headroom."
        rewrite = "There is plenty of margin on the feeder."
        assert validate_markers(orig, rewrite)

    def test_template_numbers_preserved(self):
        """Numbers that existed in the original template's unmarked prose are fine."""
        orig = "The 48-hour forecast for «Feeder 7» shows «94%» peak."
        rewrite = "Over the 48-hour window, «Feeder 7» peaks at «94%»."
        assert validate_markers(orig, rewrite)


class TestFindRogueNumbers:
    """Unit tests for the rogue number scanner."""

    def test_catches_percentage(self):
        rogues = _find_rogue_numbers("«94%» of capacity.", "«94%» of capacity, 15% above normal.")
        assert any("15%" in r for r in rogues)

    def test_catches_power(self):
        rogues = _find_rogue_numbers("«8.1 MW» peak.", "«8.1 MW» peak, down from 9.2 MW.")
        assert len(rogues) > 0

    def test_no_false_positive_on_marked(self):
        rogues = _find_rogue_numbers("«94%» peak.", "«94%» peak.")
        assert rogues == []

    def test_no_false_positive_on_template_numbers(self):
        rogues = _find_rogue_numbers(
            "Over the 48-hour horizon, load peaks.",
            "The 48-hour forecast shows a peak.",
        )
        assert rogues == []


class TestDriversMarkerLocked:
    """Drivers must be wrapped in «» markers in template output."""

    def test_drivers_in_markers(self):
        ctx = generate_forecast("feeder7", seed=42, use_synth=False)
        report = render_template(ctx, "standard")
        # Each driver's prose should appear inside «» markers
        for driver in ctx.drivers:
            assert f"«{driver.prose}»" in report.situation, (
                f"Driver '{driver.prose}' not marker-locked in situation text"
            )

    def test_all_scenarios_lock_drivers(self):
        for fid in ["feeder7", "feeder12", "feeder9", "feeder5", "feeder3"]:
            ctx = generate_forecast(fid, seed=42, use_synth=False)
            report = render_template(ctx, "standard")
            for driver in ctx.drivers:
                # Driver prose must be in markers somewhere in the narrative
                all_text = report.situation + report.risk + report.recommendation
                assert f"«{driver.prose}»" in all_text, (
                    f"Driver '{driver.prose}' not marker-locked for {fid}/{ctx.scenario}"
                )

    def test_terse_verbosity_has_no_drivers_in_situation(self):
        """Terse mode omits driver prose from situation — that's fine,
        but if it appears, it must be marked."""
        ctx = generate_forecast("feeder7", seed=42, use_synth=False)
        report = render_template(ctx, "terse")
        all_text = report.situation + report.risk + report.recommendation
        # Any driver prose that appears must be in markers
        for driver in ctx.drivers:
            if driver.prose in all_text:
                assert f"«{driver.prose}»" in all_text
