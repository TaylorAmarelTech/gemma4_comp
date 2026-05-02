"""Behavioral tests for nl2sql safety gate.

The nl2sql translator MUST reject any non-readonly SQL — otherwise a
crafted natural-language query could trigger a DROP / DELETE / UPDATE
on the evidence DB. The validate_readonly function is the gate.
"""
from __future__ import annotations

import pytest


def test_select_passes() -> None:
    try:
        from duecare.nl2sql import validate_readonly
    except ImportError as e:
        pytest.skip(f"nl2sql unavailable: {e}")
    validate_readonly("SELECT * FROM runs")
    validate_readonly("SELECT id, name FROM entities WHERE severity > 5")


def test_with_cte_passes() -> None:
    try:
        from duecare.nl2sql import validate_readonly
    except ImportError as e:
        pytest.skip(f"nl2sql unavailable: {e}")
    validate_readonly(
        "WITH high_sev AS (SELECT * FROM findings WHERE severity > 7) "
        "SELECT * FROM high_sev")


def test_drop_blocked() -> None:
    try:
        from duecare.nl2sql import validate_readonly, SQLSafetyError
    except ImportError as e:
        pytest.skip(f"nl2sql unavailable: {e}")
    with pytest.raises(SQLSafetyError):
        validate_readonly("DROP TABLE runs")


def test_delete_blocked() -> None:
    try:
        from duecare.nl2sql import validate_readonly, SQLSafetyError
    except ImportError as e:
        pytest.skip(f"nl2sql unavailable: {e}")
    with pytest.raises(SQLSafetyError):
        validate_readonly("DELETE FROM runs WHERE id = 1")


def test_update_blocked() -> None:
    try:
        from duecare.nl2sql import validate_readonly, SQLSafetyError
    except ImportError as e:
        pytest.skip(f"nl2sql unavailable: {e}")
    with pytest.raises(SQLSafetyError):
        validate_readonly("UPDATE runs SET completed = 1")


def test_insert_blocked() -> None:
    try:
        from duecare.nl2sql import validate_readonly, SQLSafetyError
    except ImportError as e:
        pytest.skip(f"nl2sql unavailable: {e}")
    with pytest.raises(SQLSafetyError):
        validate_readonly("INSERT INTO runs VALUES (1, 'x')")


def test_attach_blocked() -> None:
    """ATTACH could pull in a writable second DB and bypass the gate."""
    try:
        from duecare.nl2sql import validate_readonly, SQLSafetyError
    except ImportError as e:
        pytest.skip(f"nl2sql unavailable: {e}")
    with pytest.raises(SQLSafetyError):
        validate_readonly("ATTACH '/tmp/other.db' AS other")
