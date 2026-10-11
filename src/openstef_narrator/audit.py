"""Durable, append-only audit trail backed by SQLite.

Every narrative is recorded with its full provenance: which backend produced
it, whether validation passed, which sections fell back to template, the
exact model version, and the wall-clock latency. Records are append-only —
no updates or deletes — so the trail is tamper-evident by inspection.
"""

from __future__ import annotations

import hashlib
import json
import os
import pathlib
import sqlite3
from dataclasses import asdict
from typing import Any

from openstef_narrator.types import NarrativeMeta, NarrativeReport

_DEFAULT_DB = pathlib.Path(os.getenv(
    "NARRATOR_AUDIT_DB",
    pathlib.Path(__file__).parent.parent.parent / "audit.db",
))

_SCHEMA = """
CREATE TABLE IF NOT EXISTS audit_trail (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    narrative_id    TEXT NOT NULL UNIQUE,
    forecast_run_id TEXT NOT NULL,
    scenario        TEXT NOT NULL,
    verbosity       TEXT NOT NULL,

    -- report content
    situation       TEXT NOT NULL,
    risk            TEXT NOT NULL,
    recommendation  TEXT NOT NULL,
    audit_text      TEXT NOT NULL DEFAULT '',
    content_hash    TEXT NOT NULL,  -- SHA-256 of situation+risk+recommendation

    -- provenance (1.3)
    backend_requested TEXT NOT NULL,
    backend_resolved  TEXT NOT NULL,
    model_version     TEXT NOT NULL DEFAULT '',
    validation_passed INTEGER NOT NULL DEFAULT 1,
    fallback_sections TEXT NOT NULL DEFAULT '[]',  -- JSON array

    -- performance (1.4)
    latency_ms      INTEGER NOT NULL DEFAULT 0,
    temperature     REAL NOT NULL DEFAULT 0.0,

    -- segments (for UI rendering)
    segments_json   TEXT NOT NULL DEFAULT '{}',

    -- timestamps
    generated_at    TEXT NOT NULL,
    recorded_at     TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_audit_forecast ON audit_trail(forecast_run_id);
CREATE INDEX IF NOT EXISTS idx_audit_scenario ON audit_trail(scenario);
CREATE INDEX IF NOT EXISTS idx_audit_time ON audit_trail(generated_at);
"""

_MIGRATION_FEEDBACK = """
ALTER TABLE audit_trail ADD COLUMN feedback TEXT;
ALTER TABLE audit_trail ADD COLUMN feedback_at TEXT;
"""


def _content_hash(report: NarrativeReport) -> str:
    """SHA-256 of the narrative content for tamper detection."""
    raw = f"{report.situation}|{report.risk}|{report.recommendation}|{report.audit}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


class AuditStore:
    """Append-only SQLite audit trail."""

    def __init__(self, db_path: str | pathlib.Path | None = None):
        self._path = pathlib.Path(db_path) if db_path else _DEFAULT_DB
        self._conn = sqlite3.connect(str(self._path), check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.executescript(_SCHEMA)
        self._migrate_feedback()

    def append(
        self,
        report: NarrativeReport,
        meta: NarrativeMeta,
        segments: dict[str, Any] | None = None,
    ) -> None:
        """Record a narrative. Append-only — no updates or deletes."""
        self._conn.execute(
            """INSERT OR IGNORE INTO audit_trail (
                narrative_id, forecast_run_id, scenario, verbosity,
                situation, risk, recommendation, audit_text, content_hash,
                backend_requested, backend_resolved, model_version,
                validation_passed, fallback_sections,
                latency_ms, temperature,
                segments_json, generated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                meta.narrative_id, meta.forecast_run_id, meta.scenario, meta.verbosity,
                report.situation, report.risk, report.recommendation, report.audit,
                _content_hash(report),
                meta.backend_requested, meta.backend_resolved, meta.model_version,
                1 if meta.validation_passed else 0,
                json.dumps(list(meta.fallback_sections)),
                meta.latency_ms, meta.temperature,
                json.dumps(segments or {}), meta.generated_at,
            ),
        )
        self._conn.commit()

    def list_entries(
        self,
        scenario: str | None = None,
        backend: str | None = None,
        limit: int = 100,
    ) -> list[dict]:
        """Query the audit trail. Returns dicts matching the API response shape."""
        clauses = []
        params: list[Any] = []
        if scenario:
            clauses.append("scenario = ?")
            params.append(scenario)
        if backend:
            clauses.append("backend_resolved LIKE ?")
            params.append(f"%{backend}%")

        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        params.append(limit)

        rows = self._conn.execute(
            f"""SELECT narrative_id, forecast_run_id, scenario, verbosity,
                       situation, risk, recommendation, audit_text,
                       backend_requested, backend_resolved, model_version,
                       validation_passed, fallback_sections,
                       latency_ms, temperature,
                       segments_json, generated_at, content_hash
                FROM audit_trail {where}
                ORDER BY id DESC LIMIT ?""",
            params,
        ).fetchall()

        entries = []
        for row in rows:
            entries.append({
                "report": {
                    "situation": row[4],
                    "risk": row[5],
                    "recommendation": row[6],
                    "audit": row[7],
                },
                "meta": {
                    "narrative_id": row[0],
                    "forecast_run_id": row[1],
                    "scenario": row[2],
                    "verbosity": row[3],
                    "backend": row[9],
                    "generated_at": row[16],
                    "delivery_targets": [],
                    "model_version": row[10],
                    "backend_requested": row[8],
                    "backend_resolved": row[9],
                    "validation_passed": bool(row[11]),
                    "fallback_sections": json.loads(row[12]),
                    "latency_ms": row[13],
                    "temperature": row[14],
                    "content_hash": row[17],
                },
                "segments": json.loads(row[15]),
            })
        return entries

    def count(self) -> int:
        return self._conn.execute("SELECT COUNT(*) FROM audit_trail").fetchone()[0]

    # ------------------------------------------------------------------
    # Operator feedback (3.4)
    # ------------------------------------------------------------------

    def _migrate_feedback(self) -> None:
        """Add feedback columns if they don't already exist (idempotent)."""
        cursor = self._conn.execute("PRAGMA table_info(audit_trail)")
        cols = {row[1] for row in cursor.fetchall()}
        if "feedback" not in cols:
            self._conn.execute(
                "ALTER TABLE audit_trail ADD COLUMN feedback TEXT"
            )
        if "feedback_at" not in cols:
            self._conn.execute(
                "ALTER TABLE audit_trail ADD COLUMN feedback_at TEXT"
            )
        self._conn.commit()

    def add_feedback(self, narrative_id: str, feedback: str) -> bool:
        """Attach operator feedback to an existing audit entry.

        Parameters
        ----------
        narrative_id : str
            The ``nar-XXXXXXXX`` id of the narrative.
        feedback : str
            One of ``"up"``, ``"down"``, or ``"note:..."`` free-text.

        Returns
        -------
        bool
            True if the entry was found and updated, False otherwise.
        """
        cur = self._conn.execute(
            """UPDATE audit_trail
               SET feedback = ?, feedback_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now')
               WHERE narrative_id = ?""",
            (feedback, narrative_id),
        )
        self._conn.commit()
        return cur.rowcount > 0

    def feedback_summary(self) -> dict[str, dict[str, int]]:
        """Return counts of up/down feedback grouped by scenario.

        Returns
        -------
        dict  e.g. {"peak_forecast": {"up": 3, "down": 1}, ...}
        """
        rows = self._conn.execute(
            """SELECT scenario, feedback, COUNT(*) as cnt
               FROM audit_trail
               WHERE feedback IS NOT NULL
               GROUP BY scenario, feedback"""
        ).fetchall()
        summary: dict[str, dict[str, int]] = {}
        for scenario, fb, cnt in rows:
            if scenario not in summary:
                summary[scenario] = {"up": 0, "down": 0, "note": 0}
            if fb == "up":
                summary[scenario]["up"] += cnt
            elif fb == "down":
                summary[scenario]["down"] += cnt
            elif fb and fb.startswith("note:"):
                summary[scenario]["note"] += cnt
        return summary

    def close(self):
        self._conn.close()
