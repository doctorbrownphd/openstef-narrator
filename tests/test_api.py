"""Tests for the FastAPI REST API."""

from fastapi.testclient import TestClient
from openstef_narrator.api import app

client = TestClient(app)


class TestFeeders:
    def test_returns_5(self):
        r = client.get("/api/feeders")
        assert r.status_code == 200
        assert len(r.json()["feeders"]) == 5

    def test_feeder_keys(self):
        r = client.get("/api/feeders")
        f = r.json()["feeders"][0]
        assert "id" in f
        assert "name" in f
        assert "capacity_mw" in f


class TestForecast:
    def test_default(self):
        r = client.get("/api/forecast")
        assert r.status_code == 200
        data = r.json()
        assert len(data["points"]) == 48
        assert data["scenario"]

    def test_custom_feeder(self):
        r = client.get("/api/forecast", params={"feeder_id": "feeder3"})
        assert r.status_code == 200
        assert r.json()["scenario"] == "all_clear"

    def test_unknown_feeder(self):
        r = client.get("/api/forecast", params={"feeder_id": "bad"})
        assert r.status_code == 400


class TestNarrate:
    def test_default(self):
        r = client.post("/api/narrate", json={"feeder_id": "feeder7"})
        assert r.status_code == 200
        data = r.json()
        assert "report" in data
        assert "meta" in data
        assert "segments" in data
        assert "«" in data["report"]["situation"]

    def test_terse(self):
        r = client.post("/api/narrate", json={"feeder_id": "feeder7", "verbosity": "terse"})
        assert r.status_code == 200

    def test_full(self):
        r = client.post("/api/narrate", json={"feeder_id": "feeder7", "verbosity": "full"})
        assert r.status_code == 200
        assert r.json()["report"]["audit"]  # full has audit

    def test_invalid_verbosity(self):
        r = client.post("/api/narrate", json={"verbosity": "extreme"})
        assert r.status_code == 400

    def test_unknown_feeder(self):
        r = client.post("/api/narrate", json={"feeder_id": "bad"})
        assert r.status_code == 400

    def test_segments_have_facts(self):
        r = client.post("/api/narrate", json={})
        segs = r.json()["segments"]["situation"]
        fact_segs = [s for s in segs if s["type"] == "fact"]
        assert len(fact_segs) >= 1


class TestScenarios:
    def test_returns_5(self):
        r = client.get("/api/scenarios")
        assert r.status_code == 200
        assert len(r.json()["scenarios"]) == 5

    def test_has_examples(self):
        r = client.get("/api/scenarios")
        s = r.json()["scenarios"][0]
        assert "example" in s
        assert "situation" in s["example"]


class TestAudit:
    def test_initially_may_have_entries(self):
        r = client.get("/api/audit")
        assert r.status_code == 200
        assert "entries" in r.json()

    def test_narrate_adds_entry(self):
        r1 = client.get("/api/audit")
        n_before = len(r1.json()["entries"])
        client.post("/api/narrate", json={"feeder_id": "feeder3"})
        r2 = client.get("/api/audit")
        assert len(r2.json()["entries"]) > n_before
