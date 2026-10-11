"""Tests for delivery functions and the /api/deliver endpoint."""

import os
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from openstef_narrator.api import app
from openstef_narrator.formatters import (
    deliver,
    send_email,
    send_opfab,
    send_sms,
)
from openstef_narrator.types import NarrativeReport

client = TestClient(app)


def _sample_report():
    return NarrativeReport(
        situation="Load on «Feeder 7» will reach «94%» at «18:00».",
        risk="Exceedance probability is «12%».",
        recommendation="Activate DR before peak.",
        audit="Run «stef-09054».",
    )


# ------------------------------------------------------------------
# send_email
# ------------------------------------------------------------------

class TestSendEmail:
    def test_skipped_when_no_host(self):
        env = {
            "NARRATOR_SMTP_HOST": "",
            "NARRATOR_SMTP_PORT": "",
            "NARRATOR_EMAIL_TO": "",
            "NARRATOR_EMAIL_FROM": "",
        }
        with patch.dict(os.environ, env, clear=False):
            # Ensure no host is set
            os.environ.pop("NARRATOR_SMTP_HOST", None)
            result = send_email(_sample_report())
        assert result["status"] == "skipped"
        assert "SMTP_HOST" in result["reason"]

    def test_skipped_when_no_to(self):
        env = {
            "NARRATOR_SMTP_HOST": "smtp.example.com",
            "NARRATOR_SMTP_PORT": "587",
            "NARRATOR_EMAIL_FROM": "test@example.com",
        }
        with patch.dict(os.environ, env, clear=False):
            os.environ.pop("NARRATOR_EMAIL_TO", None)
            result = send_email(_sample_report())
        assert result["status"] == "skipped"
        assert "EMAIL_TO" in result["reason"]

    def test_sent_with_mock_smtp(self):
        env = {
            "NARRATOR_SMTP_HOST": "smtp.example.com",
            "NARRATOR_SMTP_PORT": "587",
            "NARRATOR_EMAIL_TO": "ops@example.com",
            "NARRATOR_EMAIL_FROM": "narrator@example.com",
        }
        with patch.dict(os.environ, env, clear=False):
            with patch("openstef_narrator.formatters.smtplib.SMTP") as mock_smtp:
                mock_server = MagicMock()
                mock_smtp.return_value.__enter__ = MagicMock(return_value=mock_server)
                mock_smtp.return_value.__exit__ = MagicMock(return_value=False)
                result = send_email(_sample_report())

        assert result["status"] == "sent"
        assert result["to"] == "ops@example.com"

    def test_explicit_params_override_env(self):
        with patch("openstef_narrator.formatters.smtplib.SMTP") as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value.__enter__ = MagicMock(return_value=mock_server)
            mock_smtp.return_value.__exit__ = MagicMock(return_value=False)
            result = send_email(
                _sample_report(),
                to_addr="explicit@test.com",
                smtp_host="mail.test.com",
                smtp_port=25,
            )

        assert result["status"] == "sent"
        assert result["to"] == "explicit@test.com"


# ------------------------------------------------------------------
# send_opfab
# ------------------------------------------------------------------

class TestSendOpfab:
    def test_skipped_when_no_url(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("NARRATOR_OPFAB_URL", None)
            result = send_opfab(_sample_report())
        assert result["status"] == "skipped"
        assert "OPFAB_URL" in result["reason"]

    def test_sent_with_mock_urlopen(self):
        with patch.dict(os.environ, {"NARRATOR_OPFAB_URL": "https://opfab.example.com/cards"}, clear=False):
            with patch("openstef_narrator.formatters.urllib.request.urlopen") as mock_urlopen:
                mock_resp = MagicMock()
                mock_resp.read.return_value = b"{}"
                mock_resp.__enter__ = MagicMock(return_value=mock_resp)
                mock_resp.__exit__ = MagicMock(return_value=False)
                mock_urlopen.return_value = mock_resp
                result = send_opfab(_sample_report())

        assert result["status"] == "sent"
        assert result["url"] == "https://opfab.example.com/cards"

    def test_explicit_url_overrides_env(self):
        with patch("openstef_narrator.formatters.urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = b"{}"
            mock_resp.__enter__ = MagicMock(return_value=mock_resp)
            mock_resp.__exit__ = MagicMock(return_value=False)
            mock_urlopen.return_value = mock_resp
            result = send_opfab(_sample_report(), opfab_url="https://custom.opfab.io/api")

        assert result["status"] == "sent"
        assert result["url"] == "https://custom.opfab.io/api"


# ------------------------------------------------------------------
# send_sms
# ------------------------------------------------------------------

class TestSendSms:
    def test_always_skipped(self):
        result = send_sms(_sample_report())
        assert result["status"] == "skipped"
        assert "SMS" in result["reason"]

    def test_skipped_even_with_phone(self):
        result = send_sms(_sample_report(), phone="+15551234567")
        assert result["status"] == "skipped"


# ------------------------------------------------------------------
# deliver orchestrator
# ------------------------------------------------------------------

class TestDeliver:
    def test_default_targets_opfab(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("NARRATOR_OPFAB_URL", None)
            result = deliver(_sample_report())
        assert "opfab" in result
        assert result["opfab"]["status"] == "skipped"

    def test_multiple_targets(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("NARRATOR_OPFAB_URL", None)
            os.environ.pop("NARRATOR_SMTP_HOST", None)
            result = deliver(_sample_report(), targets=["opfab", "email", "sms"])
        assert len(result) == 3
        for target in ("opfab", "email", "sms"):
            assert target in result
            assert result[target]["status"] == "skipped"

    def test_unknown_target(self):
        result = deliver(_sample_report(), targets=["carrier_pigeon"])
        assert result["carrier_pigeon"]["status"] == "skipped"
        assert "Unknown" in result["carrier_pigeon"]["reason"]


# ------------------------------------------------------------------
# /api/deliver endpoint
# ------------------------------------------------------------------

class TestDeliverEndpoint:
    def _get_narrative_id(self):
        """Get a narrative_id from the audit store."""
        r = client.get("/api/audit")
        entries = r.json()["entries"]
        assert len(entries) > 0
        return entries[0]["meta"]["narrative_id"]

    def test_deliver_returns_results(self):
        nar_id = self._get_narrative_id()
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("NARRATOR_OPFAB_URL", None)
            r = client.post("/api/deliver", json={
                "narrative_id": nar_id,
                "targets": ["opfab"],
            })
        assert r.status_code == 200
        data = r.json()
        assert data["narrative_id"] == nar_id
        assert "delivery" in data
        assert data["delivery"]["opfab"]["status"] == "skipped"

    def test_deliver_unknown_narrative(self):
        r = client.post("/api/deliver", json={
            "narrative_id": "nar-nonexistent",
            "targets": ["opfab"],
        })
        assert r.status_code == 404

    def test_deliver_multiple_targets(self):
        nar_id = self._get_narrative_id()
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("NARRATOR_OPFAB_URL", None)
            os.environ.pop("NARRATOR_SMTP_HOST", None)
            r = client.post("/api/deliver", json={
                "narrative_id": nar_id,
                "targets": ["opfab", "email", "sms"],
            })
        assert r.status_code == 200
        delivery = r.json()["delivery"]
        assert len(delivery) == 3
