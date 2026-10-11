"""Tests for the operator feedback loop (audit + API)."""

import pathlib
import tempfile

import pytest
from fastapi.testclient import TestClient

from openstef_narrator.audit import AuditStore
from openstef_narrator.types import NarrativeMeta, NarrativeReport


def _make_store(tmp_path: pathlib.Path) -> AuditStore:
    """Create a fresh AuditStore in a temp directory."""
    return AuditStore(db_path=tmp_path / "test_feedback.db")


def _sample_report() -> NarrativeReport:
    return NarrativeReport(
        situation="Load on \u00abFeeder 7\u00bb reaches \u00ab94%\u00bb.",
        risk="Exceedance is \u00ab12%\u00bb.",
        recommendation="Activate DR.",
        audit="",
    )


def _sample_meta(narrative_id: str = "nar-test001", scenario: str = "peak_forecast") -> NarrativeMeta:
    return NarrativeMeta(
        narrative_id=narrative_id,
        forecast_run_id="run-001",
        scenario=scenario,
        verbosity="standard",
        backend="template_fallback",
        generated_at="2026-06-02T00:00:00Z",
    )


class TestAuditFeedback:
    """Unit tests for AuditStore.add_feedback and feedback_summary."""

    def test_add_feedback_up(self, tmp_path):
        store = _make_store(tmp_path)
        store.append(_sample_report(), _sample_meta("nar-fb01"))
        assert store.add_feedback("nar-fb01", "up") is True

    def test_add_feedback_down(self, tmp_path):
        store = _make_store(tmp_path)
        store.append(_sample_report(), _sample_meta("nar-fb02"))
        assert store.add_feedback("nar-fb02", "down") is True

    def test_add_feedback_note(self, tmp_path):
        store = _make_store(tmp_path)
        store.append(_sample_report(), _sample_meta("nar-fb03"))
        assert store.add_feedback("nar-fb03", "note:looked reasonable") is True

    def test_add_feedback_unknown_id(self, tmp_path):
        store = _make_store(tmp_path)
        assert store.add_feedback("nar-nonexistent", "up") is False

    def test_feedback_summary_empty(self, tmp_path):
        store = _make_store(tmp_path)
        assert store.feedback_summary() == {}

    def test_feedback_summary_counts(self, tmp_path):
        store = _make_store(tmp_path)
        store.append(_sample_report(), _sample_meta("nar-s1", "peak_forecast"))
        store.append(_sample_report(), _sample_meta("nar-s2", "peak_forecast"))
        store.append(_sample_report(), _sample_meta("nar-s3", "overload_risk"))

        store.add_feedback("nar-s1", "up")
        store.add_feedback("nar-s2", "down")
        store.add_feedback("nar-s3", "up")

        summary = store.feedback_summary()
        assert summary["peak_forecast"]["up"] == 1
        assert summary["peak_forecast"]["down"] == 1
        assert summary["overload_risk"]["up"] == 1

    def test_feedback_summary_notes(self, tmp_path):
        store = _make_store(tmp_path)
        store.append(_sample_report(), _sample_meta("nar-n1"))
        store.add_feedback("nar-n1", "note:too cautious")
        summary = store.feedback_summary()
        assert summary["peak_forecast"]["note"] == 1

    def test_feedback_columns_exist_on_fresh_db(self, tmp_path):
        """Migration adds columns even on a brand-new DB."""
        store = _make_store(tmp_path)
        store.append(_sample_report(), _sample_meta("nar-fresh"))
        # Should not raise — columns exist
        store.add_feedback("nar-fresh", "up")
        store.close()

    def test_feedback_at_populated(self, tmp_path):
        store = _make_store(tmp_path)
        store.append(_sample_report(), _sample_meta("nar-ts"))
        store.add_feedback("nar-ts", "up")
        row = store._conn.execute(
            "SELECT feedback_at FROM audit_trail WHERE narrative_id = ?",
            ("nar-ts",),
        ).fetchone()
        assert row[0] is not None


class TestFeedbackAPI:
    """Integration tests for /api/feedback and /api/feedback/summary endpoints."""

    @pytest.fixture(autouse=True)
    def _client(self):
        """Import the app (which seeds audit) and create a test client."""
        from openstef_narrator.api import app
        self.client = TestClient(app)

    def _get_a_narrative_id(self) -> str:
        """Narrate something and get back a narrative_id."""
        r = self.client.post("/api/narrate", json={"feeder_id": "feeder7"})
        return r.json()["meta"]["narrative_id"]

    def test_feedback_up(self):
        nid = self._get_a_narrative_id()
        r = self.client.post("/api/feedback", json={"narrative_id": nid, "feedback": "up"})
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    def test_feedback_down(self):
        nid = self._get_a_narrative_id()
        r = self.client.post("/api/feedback", json={"narrative_id": nid, "feedback": "down"})
        assert r.status_code == 200

    def test_feedback_note(self):
        nid = self._get_a_narrative_id()
        r = self.client.post("/api/feedback", json={"narrative_id": nid, "feedback": "note:great job"})
        assert r.status_code == 200

    def test_feedback_invalid(self):
        nid = self._get_a_narrative_id()
        r = self.client.post("/api/feedback", json={"narrative_id": nid, "feedback": "maybe"})
        assert r.status_code == 400

    def test_feedback_unknown_narrative(self):
        r = self.client.post("/api/feedback", json={"narrative_id": "nar-bogus", "feedback": "up"})
        assert r.status_code == 404

    def test_feedback_summary_endpoint(self):
        r = self.client.get("/api/feedback/summary")
        assert r.status_code == 200
        assert "summary" in r.json()


class TestRollupAPI:
    """Integration tests for the /api/rollup endpoint."""

    @pytest.fixture(autouse=True)
    def _client(self):
        from openstef_narrator.api import app
        self.client = TestClient(app)

    def test_rollup_returns_200(self):
        r = self.client.get("/api/rollup")
        assert r.status_code == 200

    def test_rollup_has_summary(self):
        r = self.client.get("/api/rollup")
        data = r.json()
        assert "summary" in data
        assert "feeders" in data
        assert "worst" in data
        assert "at_risk" in data

    def test_rollup_five_feeders(self):
        r = self.client.get("/api/rollup")
        assert len(r.json()["feeders"]) == 5
