"""Smoke tests for duecare-llm-nl2sql."""
from __future__ import annotations

import pytest


def test_nl2sql_imports() -> None:
    try:
        from duecare.nl2sql import (
            Translator, TranslationResult, validate_readonly, SQLSafetyError,
        )
    except ImportError as e:
        pytest.skip(f"nl2sql depends on packages not installed: {e}")
    assert Translator is not None
    assert TranslationResult is not None
    assert callable(validate_readonly)
    assert issubclass(SQLSafetyError, Exception)


def test_validate_readonly_blocks_writes() -> None:
    try:
        from duecare.nl2sql import validate_readonly, SQLSafetyError
    except ImportError as e:
        pytest.skip(f"nl2sql depends on packages not installed: {e}")
    # SELECT should pass
    validate_readonly("SELECT * FROM runs LIMIT 10")
    # write statements should be rejected
    for bad in ("DROP TABLE runs", "DELETE FROM runs",
                "UPDATE runs SET completed=1", "INSERT INTO runs VALUES (1)"):
        with pytest.raises(SQLSafetyError):
            validate_readonly(bad)
