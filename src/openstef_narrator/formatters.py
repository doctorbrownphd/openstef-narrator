"""Output formatters — pluggable adapters for different delivery targets."""

from __future__ import annotations

import json as _json
import os
import re
import smtplib
import urllib.request
from email.message import EmailMessage

from openstef_narrator.types import NarrativeReport


def strip_markers(text: str) -> str:
    """Remove «» markers, leaving just the values."""
    return re.sub(r"«([^»]+)»", r"\1", text)


def highlight_markers(text: str) -> list[dict]:
    """Parse text into segments for frontend FactText rendering.

    Returns a list of dicts:
        [{"type": "text", "value": "..."}, {"type": "fact", "value": "..."}, ...]
    """
    parts = re.split(r"(«[^»]+»)", text)
    segments = []
    for part in parts:
        if not part:
            continue
        if part.startswith("«") and part.endswith("»"):
            segments.append({"type": "fact", "value": part[1:-1]})
        else:
            segments.append({"type": "text", "value": part})
    return segments


def format_markdown(report: NarrativeReport) -> str:
    """Convert narrative to Markdown, rendering «facts» as **bold**."""
    def bold_facts(text: str) -> str:
        return re.sub(r"«([^»]+)»", r"**\1**", text)

    lines = [
        "## Situation",
        "",
        bold_facts(report.situation),
        "",
        "## Risk & Confidence",
        "",
        bold_facts(report.risk),
        "",
        "## Recommendation",
        "",
        bold_facts(report.recommendation),
    ]
    if report.audit:
        lines.extend(["", "---", "", f"*{bold_facts(report.audit)}*"])
    return "\n".join(lines)


def format_email(report: NarrativeReport, subject_prefix: str = "[OpenSTEF]") -> dict[str, str]:
    """Convert narrative to email dict with 'subject' and 'body' keys."""
    # Extract feeder name from situation for subject
    situation_clean = strip_markers(report.situation)
    subject = f"{subject_prefix} {situation_clean[:80]}"

    body = (
        f"{strip_markers(report.situation)}\n\n"
        f"Risk: {strip_markers(report.risk)}\n\n"
        f"Recommendation: {strip_markers(report.recommendation)}"
    )
    if report.audit:
        body += f"\n\n---\n{strip_markers(report.audit)}"

    return {"subject": subject, "body": body}


def format_opfab(report: NarrativeReport) -> dict:
    """Stub: Convert narrative to OperatorFabric card format.

    Returns a dict approximating the OpFab card JSON schema.
    Requires a running OpFab instance to validate — stubbed for v0.1.
    """
    return {
        "publisher": "openstef-narrator",
        "processVersion": "1",
        "severity": "ALARM",
        "title": {"key": "narrator.title", "parameters": {}},
        "summary": {"key": "narrator.summary", "parameters": {
            "situation": strip_markers(report.situation),
        }},
        "data": {
            "situation": report.situation,
            "risk": report.risk,
            "recommendation": report.recommendation,
            "audit": report.audit,
        },
    }


# ------------------------------------------------------------------
# Delivery functions
# ------------------------------------------------------------------

def send_email(
    report: NarrativeReport,
    subject_prefix: str = "[OpenSTEF]",
    to_addr: str | None = None,
    smtp_host: str | None = None,
    smtp_port: int | None = None,
) -> dict:
    """Send a narrative report via SMTP email.

    Reads defaults from environment variables:
        ``NARRATOR_SMTP_HOST``, ``NARRATOR_SMTP_PORT``,
        ``NARRATOR_EMAIL_TO``, ``NARRATOR_EMAIL_FROM``

    Returns ``{"status": "sent", "to": addr}`` on success or
    ``{"status": "skipped", "reason": "..."}`` if not configured or on error.
    """
    host = smtp_host or os.getenv("NARRATOR_SMTP_HOST")
    raw_port = os.getenv("NARRATOR_SMTP_PORT", "")
    port = smtp_port or (int(raw_port) if raw_port.strip() else None)
    to = to_addr or os.getenv("NARRATOR_EMAIL_TO")
    from_addr = os.getenv("NARRATOR_EMAIL_FROM", "narrator@openstef.local")

    if not host:
        return {"status": "skipped", "reason": "NARRATOR_SMTP_HOST not configured"}
    if not to:
        return {"status": "skipped", "reason": "NARRATOR_EMAIL_TO not configured"}
    if not port:
        return {"status": "skipped", "reason": "NARRATOR_SMTP_PORT not configured"}

    email_data = format_email(report, subject_prefix=subject_prefix)

    msg = EmailMessage()
    msg["Subject"] = email_data["subject"]
    msg["From"] = from_addr
    msg["To"] = to
    msg.set_content(email_data["body"])

    try:
        with smtplib.SMTP(host, port, timeout=10) as server:
            server.send_message(msg)
        return {"status": "sent", "to": to}
    except Exception as exc:
        return {"status": "skipped", "reason": f"SMTP error: {exc}"}


def send_opfab(
    report: NarrativeReport,
    opfab_url: str | None = None,
) -> dict:
    """Post a narrative report as an OperatorFabric card.

    Reads ``NARRATOR_OPFAB_URL`` from env if *opfab_url* is not provided.
    Uses ``urllib.request`` so no extra dependency is needed.

    Returns ``{"status": "sent", "url": url}`` on success or
    ``{"status": "skipped", "reason": "..."}`` if not configured or on error.
    """
    url = opfab_url or os.getenv("NARRATOR_OPFAB_URL")
    if not url:
        return {"status": "skipped", "reason": "NARRATOR_OPFAB_URL not configured"}

    card = format_opfab(report)
    payload = _json.dumps(card).encode("utf-8")

    try:
        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            resp.read()
        return {"status": "sent", "url": url}
    except Exception as exc:
        return {"status": "skipped", "reason": f"OpFab POST error: {exc}"}


def send_sms(
    report: NarrativeReport,
    phone: str | None = None,
) -> dict:
    """Stub for SMS delivery.

    Reads ``NARRATOR_SMS_PROVIDER`` from env. Currently always returns
    skipped — a real implementation would integrate with Twilio, AWS SNS,
    or a similar provider.
    """
    # TODO: integrate with Twilio or similar SMS provider.
    # When implemented, read NARRATOR_SMS_PROVIDER to choose the backend
    # and NARRATOR_SMS_API_KEY / NARRATOR_SMS_FROM for credentials.
    _provider = phone  # suppress unused-arg linter warning
    _provider = os.getenv("NARRATOR_SMS_PROVIDER")
    return {"status": "skipped", "reason": "SMS provider not configured"}


def deliver(
    report: NarrativeReport,
    targets: tuple[str, ...] | list[str] = ("opfab",),
) -> dict:
    """Orchestrate delivery to one or more targets.

    Parameters
    ----------
    report : NarrativeReport
        The narrative to deliver.
    targets : sequence of str
        Delivery channel names: ``"opfab"``, ``"email"``, ``"sms"``.

    Returns
    -------
    dict
        Mapping of target name to its delivery result dict.
    """
    dispatchers = {
        "opfab": send_opfab,
        "email": send_email,
        "sms": send_sms,
    }

    results: dict[str, dict] = {}
    for target in targets:
        sender = dispatchers.get(target)
        if sender is None:
            results[target] = {"status": "skipped", "reason": f"Unknown target: {target}"}
        else:
            results[target] = sender(report)
    return results
