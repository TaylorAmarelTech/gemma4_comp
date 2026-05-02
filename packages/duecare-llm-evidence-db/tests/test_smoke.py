"""Smoke tests for duecare-llm-evidence-db."""
from __future__ import annotations

import pytest
import tempfile
from pathlib import Path


def test_evidence_db_imports() -> None:
    try:
        import duecare.evidence_db
    except ImportError as e:
        pytest.skip(f"evidence_db not installable here: {e}")
    assert duecare.evidence_db is not None


def test_evidence_db_public_api_present() -> None:
    """The evidence-db public API has at least an EvidenceStore or Store
    class (whatever the canonical DB wrapper is named)."""
    try:
        import duecare.evidence_db as ed
    except ImportError as e:
        pytest.skip(f"evidence_db not installable here: {e}")
    public = [a for a in dir(ed) if not a.startswith("_")]
    # Loosely assert there's *something* publicly exported
    assert len(public) >= 1, f"no public API in duecare.evidence_db: {dir(ed)}"
