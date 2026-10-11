"""Tests for the JSON-based feeder registry."""

import json
import os
import tempfile

from openstef_narrator.feeders import (
    FEEDERS,
    Feeder,
    _DEFAULT_FEEDERS,
    get_feeder,
    reload_feeders,
)


class TestBackwardCompatibility:
    """Existing imports and behavior must still work."""

    def test_feeders_tuple_has_5(self):
        assert len(FEEDERS) == 5

    def test_get_feeder_by_id(self):
        f = get_feeder("feeder7")
        assert f.name == "Feeder 7"
        assert f.district == "Eastgate"

    def test_get_feeder_unknown_raises(self):
        try:
            get_feeder("nonexistent")
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "nonexistent" in str(e)

    def test_feeder_dataclass_frozen(self):
        f = get_feeder("feeder3")
        try:
            f.name = "changed"
            assert False, "Should not allow assignment"
        except AttributeError:
            pass

    def test_all_defaults_present(self):
        ids = {f.id for f in FEEDERS}
        assert ids == {"feeder7", "feeder12", "feeder9", "feeder5", "feeder3"}


class TestJsonLoading:
    """Test loading feeders from JSON files."""

    def test_bundled_json_matches_defaults(self):
        # The bundled JSON should produce the same feeders as the hardcoded defaults
        for bundled, default in zip(FEEDERS, _DEFAULT_FEEDERS):
            assert bundled.id == default.id
            assert bundled.name == default.name
            assert bundled.capacity_mw == default.capacity_mw

    def test_reload_from_custom_file(self):
        custom = [
            {
                "id": "test1",
                "name": "Test Feeder 1",
                "district": "TestDistrict",
                "capacity_mw": 10.0,
                "base_load_mw": 5.0,
                "peak_pct": 0.9,
                "band_width": 0.1,
                "scenario": "all_clear",
                "confidence": "High",
            }
        ]
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(custom, f)
            tmp_path = f.name

        try:
            result = reload_feeders(tmp_path)
            assert len(result) == 1
            assert result[0].id == "test1"
            assert result[0].capacity_mw == 10.0
        finally:
            os.unlink(tmp_path)
            # Restore defaults
            reload_feeders()

    def test_reload_restores_defaults(self):
        reload_feeders()
        assert len(FEEDERS) == 5
        assert get_feeder("feeder7").name == "Feeder 7"

    def test_reload_from_env_var(self):
        custom = [
            {
                "id": "envtest",
                "name": "Env Feeder",
                "district": "EnvDistrict",
                "capacity_mw": 3.0,
                "base_load_mw": 1.5,
                "peak_pct": 0.7,
                "band_width": 0.12,
                "scenario": "all_clear",
                "confidence": "High",
            }
        ]
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(custom, f)
            tmp_path = f.name

        old_env = os.environ.get("NARRATOR_FEEDERS_FILE")
        try:
            os.environ["NARRATOR_FEEDERS_FILE"] = tmp_path
            result = reload_feeders()
            assert len(result) == 1
            assert result[0].id == "envtest"
        finally:
            if old_env is None:
                os.environ.pop("NARRATOR_FEEDERS_FILE", None)
            else:
                os.environ["NARRATOR_FEEDERS_FILE"] = old_env
            os.unlink(tmp_path)
            # Restore defaults
            reload_feeders()
