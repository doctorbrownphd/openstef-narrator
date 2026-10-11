"""Tests for output formatters."""

from openstef_narrator.formatters import (
    format_email,
    format_markdown,
    format_opfab,
    highlight_markers,
    strip_markers,
)
from openstef_narrator.types import NarrativeReport


def _sample_report():
    return NarrativeReport(
        situation="Load on «Feeder 7» will reach «94%» at «18:00».",
        risk="Exceedance probability is «12%».",
        recommendation="Activate DR before peak.",
        audit="Run «stef-09054».",
    )


class TestStripMarkers:
    def test_removes_markers(self):
        assert strip_markers("«94%»") == "94%"

    def test_multiple(self):
        assert strip_markers("«A» and «B»") == "A and B"

    def test_no_markers(self):
        assert strip_markers("plain text") == "plain text"


class TestHighlightMarkers:
    def test_segments(self):
        segs = highlight_markers("Load reaches «94%» at «18:00».")
        assert len(segs) == 5  # trailing "." is a text segment
        assert segs[0] == {"type": "text", "value": "Load reaches "}
        assert segs[1] == {"type": "fact", "value": "94%"}
        assert segs[2] == {"type": "text", "value": " at "}
        assert segs[3] == {"type": "fact", "value": "18:00"}

    def test_no_markers(self):
        segs = highlight_markers("plain text")
        assert len(segs) == 1
        assert segs[0]["type"] == "text"


class TestMarkdown:
    def test_facts_bolded(self):
        md = format_markdown(_sample_report())
        assert "**94%**" in md
        assert "**Feeder 7**" in md
        assert "«" not in md

    def test_has_sections(self):
        md = format_markdown(_sample_report())
        assert "## Situation" in md
        assert "## Recommendation" in md


class TestEmail:
    def test_subject_and_body(self):
        email = format_email(_sample_report())
        assert "subject" in email
        assert "body" in email
        assert "[OpenSTEF]" in email["subject"]
        assert "«" not in email["body"]


class TestOpFab:
    def test_has_publisher(self):
        card = format_opfab(_sample_report())
        assert card["publisher"] == "openstef-narrator"
        assert "situation" in card["data"]
