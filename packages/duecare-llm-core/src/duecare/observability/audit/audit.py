"""Audit trail. SQLite-backed, append-only, stores hashes NOT plaintext."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from threading import Lock


SCHEMA = """
CREATE TABLE IF NOT EXISTS anon_audit (
    id TEXT PRIMARY KEY,
    item_id TEXT NOT NULL,
    detector_name TEXT NOT NULL,
    detector_version TEXT NOT NULL,
    span_start INTEGER NOT NULL,
    span_end INTEGER NOT NULL,
    category TEXT NOT NULL,
    original_hash TEXT NOT NULL,
    strategy TEXT NOT NULL,
    replacement TEXT NOT NULL,
    operator TEXT NOT NULL,
    timestamp TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_anon_audit_item ON anon_audit(item_id);
CREATE INDEX IF NOT EXISTS idx_anon_audit_category ON anon_audit(category);

CREATE TABLE IF NOT EXISTS run_audit (
    run_id TEXT PRIMARY KEY,
    workflow_id TEXT NOT NULL,
    git_sha TEXT NOT NULL,
    config_hash TEXT NOT NULL,
    target_model_id TEXT NOT NULL,
    domain_id TEXT NOT NULL,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    status TEXT NOT NULL,
    total_cost_usd REAL DEFAULT 0.0,
    final_metrics TEXT
);
"""


class AuditTrail:
    """Append-only audit trail backed by SQLite."""

    def __init__(self, db_path: Path | str) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
        self._init_schema()

    def _init_schema(self) -> None:
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.executescript(SCHEMA)

    def record_anonymization(
        self,
        *,
        audit_id: str,
        item_id: str,
        detector_name: str,
        detector_version: str,
        span_start: int,
        span_end: int,
        category: str,
        original_hash: str,
        strategy: str,
        replacement: str,
        operator: str = "auto",
    ) -> None:
        """Record one anonymization decision. Stores hash, never plaintext."""
        row = (
            audit_id,
            item_id,
            detector_name,
            detector_version,
            span_start,
            span_end,
            category,
            original_hash,
            strategy,
            replacement,
            operator,
            datetime.now().isoformat(timespec="seconds"),
        )
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT INTO anon_audit VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    row,
                )
                conn.commit()

    def record_run_start(
        self,
        *,
        run_id: str,
        workflow_id: str,
        git_sha: str,
        config_hash: str,
        target_model_id: str,
        domain_id: str,
    ) -> None:
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO run_audit VALUES "
                    "(?, ?, ?, ?, ?, ?, ?, NULL, ?, 0.0, NULL)",
                    (
                        run_id,
                        workflow_id,
                        git_sha,
                        config_hash,
                        target_model_id,
                        domain_id,
                        datetime.now().isoformat(timespec="seconds"),
                        "running",
                    ),
                )
                conn.commit()

    def record_run_end(
        self,
        *,
        run_id: str,
        status: str,
        total_cost_usd: float = 0.0,
        final_metrics: dict | None = None,
    ) -> None:
        import json
        metrics_json = json.dumps(final_metrics or {})
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "UPDATE run_audit SET ended_at = ?, status = ?, "
                    "total_cost_usd = ?, final_metrics = ? WHERE run_id = ?",
                    (
                        datetime.now().isoformat(timespec="seconds"),
                        status,
                        total_cost_usd,
                        metrics_json,
                        run_id,
                    ),
                )
                conn.commit()
