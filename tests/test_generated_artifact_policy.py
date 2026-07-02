"""Regression checks for generated artifact commit-safety policy."""
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _gitignore_entries() -> set[str]:
    return {
        line.strip()
        for line in (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }


def test_training_report_store_is_gitignored() -> None:
    """Training builders document reports/training as a generated store."""
    assert "reports/training/" in _gitignore_entries()


def test_human_validation_exports_are_gitignored() -> None:
    """Expert-rating sheets and hidden keys stay in the generated reports store."""
    assert "reports/human_validation/" in _gitignore_entries()


def test_model_failure_study_artifacts_are_gitignored() -> None:
    """Response, judge, and checkpoint artifacts can contain raw model outputs."""
    assert "reports/model_failure_study/" in _gitignore_entries()


def test_benchmark_research_artifacts_are_gitignored() -> None:
    """Domain promptsets, curation queues, and research plans are generated outputs."""
    assert "reports/benchmark/" in _gitignore_entries()
