"""Package-level tests for duecare-llm-publishing."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from duecare.core.enums import TaskStatus
from duecare.core.schemas import WorkflowRun
from duecare.publishing import (
    HFHubPublisher,
    KagglePublisher,
    MarkdownReportGenerator,
    ModelCardGenerator,
    is_hf_hub_available,
    is_kaggle_cli_available,
)


@pytest.fixture
def sample_run() -> WorkflowRun:
    return WorkflowRun(
        run_id="test_run_001",
        workflow_id="rapid_probe",
        git_sha="abc123def456",
        config_hash="0123456789abcdef" * 4,
        target_model_id="gemma-4-e4b",
        domain_id="trafficking",
        started_at=datetime.now(),
        ended_at=datetime.now(),
        status=TaskStatus.COMPLETED,
        final_metrics={"grade_exact_match": 0.68, "grade_within_1": 0.92},
        total_cost_usd=4.20,
        total_duration_s=125.5,
    )


class TestMarkdownReportGenerator:
    def test_render_contains_headline(self, sample_run):
        gen = MarkdownReportGenerator()
        out = gen.render(sample_run)
        assert "Duecare Run Report" in out
        assert "test_run_001" in out
        assert "rapid_probe" in out
        assert "gemma-4-e4b" in out
        assert "$4.2000" in out
        assert "grade_exact_match" in out

    def test_write_creates_file(self, sample_run, tmp_path):
        gen = MarkdownReportGenerator(output_dir=tmp_path)
        path = gen.write(sample_run)
        assert path.exists()
        content = path.read_text()
        assert "test_run_001" in content

    def test_render_with_error(self, sample_run):
        sample_run.status = TaskStatus.FAILED
        sample_run.error = "Something went wrong"
        gen = MarkdownReportGenerator()
        out = gen.render(sample_run)
        assert "Error" in out
        assert "Something went wrong" in out


class TestModelCardGenerator:
    def test_render(self):
        gen = ModelCardGenerator()
        card = gen.render(
            model_name="gemma-4-e4b-safetyjudge-v0.1",
            base_model="unsloth/gemma-4-e4b-bnb-4bit",
            dataset_id="taylorsamarel/duecare-trafficking-training-v1",
            description="Fine-tuned Gemma 4 E4B safety judge",
            grade_exact_match=0.68,
            grade_within_1=0.92,
            ilo_indicator_recall=0.81,
            refusal_rate=0.95,
            n_train_samples=12000,
        )
        assert "# gemma-4-e4b-safetyjudge-v0.1" in card
        assert "Unsloth + LoRA" in card
        assert "0.680" in card
        assert "MIT" in card
        assert "---\\nlanguage: en" in card or "language: en" in card

    def test_write(self, tmp_path):
        gen = ModelCardGenerator()
        path = tmp_path / "README.md"
        gen.write(
            path,
            model_name="test-model",
            base_model="base",
            dataset_id="ds",
            description="test",
        )
        assert path.exists()


class TestHFHubPublisher:
    def test_requires_token(self, monkeypatch):
        monkeypatch.delenv("HUGGINGFACE_TOKEN", raising=False)
        pub = HFHubPublisher()
        with pytest.raises(RuntimeError, match="HUGGINGFACE_TOKEN"):
            pub._token()

    def test_is_hf_hub_available(self):
        # Just needs to not raise
        result = is_hf_hub_available()
        assert isinstance(result, bool)


class TestKagglePublisher:
    def test_is_kaggle_cli_available(self):
        # kaggle is installed per earlier turns
        result = is_kaggle_cli_available()
        assert isinstance(result, bool)

    def test_run_fails_cleanly_without_auth(self):
        pub = KagglePublisher()
        if not is_kaggle_cli_available():
            pytest.skip("kaggle CLI not installed in test env")
        # `kaggle competitions list` without auth raises
        with pytest.raises(RuntimeError):
            pub._run(["competitions", "list"])
