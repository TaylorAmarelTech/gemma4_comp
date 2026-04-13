"""Package-level tests for duecare-llm meta (CLI)."""

from __future__ import annotations

from typer.testing import CliRunner

from duecare.cli import app


runner = CliRunner()


class TestCLI:
    def test_help(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "Duecare" in result.output

    def test_agents_list(self):
        result = runner.invoke(app, ["agents", "list"])
        assert result.exit_code == 0
        for agent_id in ("scout", "judge", "historian", "coordinator"):
            assert agent_id in result.output

    def test_models_list(self):
        result = runner.invoke(app, ["models", "list"])
        assert result.exit_code == 0
        for model_id in ("transformers", "llama_cpp", "openai_compatible", "anthropic"):
            assert model_id in result.output

    def test_tasks_list(self):
        result = runner.invoke(app, ["tasks", "list"])
        assert result.exit_code == 0
        for task_id in ("guardrails", "anonymization", "classification"):
            assert task_id in result.output

    def test_domains_list(self):
        result = runner.invoke(app, ["domains", "list"])
        assert result.exit_code == 0

    def test_status(self):
        result = runner.invoke(app, ["status"])
        assert result.exit_code == 0
        assert "models" in result.output
        assert "agents" in result.output
