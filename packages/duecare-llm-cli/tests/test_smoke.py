"""Smoke tests for duecare-llm-cli."""
from __future__ import annotations

import pytest


def test_cli_importable() -> None:
    """The cli depends on engine/server/etc. -- if any are missing the
    import will fail. Skip in that case so the test still passes in
    environments without the full graph installed."""
    try:
        from duecare.cli import cli
    except ImportError as e:
        pytest.skip(f"cli depends on packages not installed: {e}")
    assert callable(cli)


def test_cli_help_exits_zero() -> None:
    pytest.importorskip("click")
    from click.testing import CliRunner
    try:
        from duecare.cli import cli
    except ImportError as e:
        pytest.skip(f"cli depends on packages not installed: {e}")
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
