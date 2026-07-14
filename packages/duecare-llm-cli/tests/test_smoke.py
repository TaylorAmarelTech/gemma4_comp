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


def _load_click_main():
    """Load the Click CLI module (main.py) by file path.

    In the PYTHONPATH test env, `duecare.cli` is a split namespace (the meta
    package's Typer CLI can shadow this Click one); a pip install merges them.
    Loading the file directly makes this test deterministic either way.
    """
    import importlib.util
    import pathlib

    main_path = (
        pathlib.Path(__file__).resolve().parents[1]
        / "src" / "duecare" / "cli" / "main.py"
    )
    spec = importlib.util.spec_from_file_location("dc_cli_main_test", main_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_quickstart_registered_and_help() -> None:
    """The one-shot `quickstart` onboarding command must be registered and its
    help must parse (the chained init/doctor/demo-init run in production)."""
    pytest.importorskip("click")
    from click.testing import CliRunner

    try:
        mod = _load_click_main()
    except Exception as e:  # depends on engine/server/etc not on the path
        pytest.skip(f"cli main depends on packages not installed: {e}")
    assert "quickstart" in mod.cli.commands
    result = CliRunner().invoke(mod.cli, ["quickstart", "--help"])
    assert result.exit_code == 0
    assert "init + doctor + sample data" in result.output
    # role choices are surfaced so an operator can tailor the next steps
    assert "ngo" in result.output and "worker" in result.output


def test_training_kickoff_uses_canonical_gemma_and_current_handoff_copy() -> None:
    pytest.importorskip("click")
    mod = _load_click_main()

    base_model = next(
        parameter
        for parameter in mod.cmd_train_kickoff.params
        if parameter.name == "base_model"
    )
    assert base_model.default == "google/gemma-4-E4B-it"
    assert "Coming Soon" not in (mod.cmd_train.help or "")
