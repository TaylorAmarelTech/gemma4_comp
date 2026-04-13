"""Real tests for duecare.observability.audit.AuditTrail."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from duecare.observability.audit import AuditTrail


@pytest.fixture
def audit(tmp_path: Path) -> AuditTrail:
    return AuditTrail(tmp_path / "audit.sqlite")


def test_init_creates_schema(audit: AuditTrail):
    with sqlite3.connect(audit.db_path) as conn:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
    assert "anon_audit" in tables
    assert "run_audit" in tables


def test_record_anonymization_stores_hash_not_plaintext(audit: AuditTrail):
    audit.record_anonymization(
        audit_id="a1",
        item_id="item_001",
        detector_name="regex",
        detector_version="0.1",
        span_start=0,
        span_end=5,
        category="phone",
        original_hash="abc123",
        strategy="redact",
        replacement="[PHONE]",
    )
    with sqlite3.connect(audit.db_path) as conn:
        rows = conn.execute(
            "SELECT original_hash, replacement FROM anon_audit WHERE item_id = ?",
            ("item_001",),
        ).fetchall()
    assert len(rows) == 1
    assert rows[0][0] == "abc123"  # hash stored
    assert rows[0][1] == "[PHONE]"


def test_record_run_lifecycle(audit: AuditTrail):
    audit.record_run_start(
        run_id="r1",
        workflow_id="evaluate_only",
        git_sha="abc",
        config_hash="def",
        target_model_id="gemma-4-e4b",
        domain_id="trafficking",
    )
    audit.record_run_end(
        run_id="r1",
        status="completed",
        total_cost_usd=4.20,
        final_metrics={"grade_exact_match": 0.68},
    )

    with sqlite3.connect(audit.db_path) as conn:
        row = conn.execute(
            "SELECT workflow_id, status, total_cost_usd, final_metrics "
            "FROM run_audit WHERE run_id = ?",
            ("r1",),
        ).fetchone()

    assert row[0] == "evaluate_only"
    assert row[1] == "completed"
    assert row[2] == 4.20
    assert "grade_exact_match" in row[3]


def test_multiple_anonymization_records(audit: AuditTrail):
    for i in range(5):
        audit.record_anonymization(
            audit_id=f"a{i}",
            item_id="item_001",
            detector_name="regex",
            detector_version="0.1",
            span_start=i * 10,
            span_end=i * 10 + 5,
            category="phone",
            original_hash=f"hash{i}",
            strategy="redact",
            replacement="[PHONE]",
        )
    with sqlite3.connect(audit.db_path) as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM anon_audit WHERE item_id = ?",
            ("item_001",),
        ).fetchone()[0]
    assert count == 5


def test_audit_parent_dir_autocreated(tmp_path: Path):
    path = tmp_path / "deep" / "nested" / "audit.sqlite"
    AuditTrail(path)
    assert path.exists()
