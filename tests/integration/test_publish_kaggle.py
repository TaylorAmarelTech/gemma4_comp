"""Integration tests for scripts/publish_kaggle.py.

These tests prove the orchestrator's logic works without needing real
Kaggle credentials by exercising --dry-run mode and by isolating the
auth-check path.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "publish_kaggle.py"
KERNELS_DIR = REPO_ROOT / "kaggle" / "kernels"


def _run(*args: str, env_overrides: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    import os

    env = os.environ.copy()
    if env_overrides:
        env.update(env_overrides)
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        check=False,
        env=env,
        cwd=str(REPO_ROOT),
    )


class TestCLI:
    def test_help(self):
        result = _run("--help")
        assert result.returncode == 0
        for cmd in (
            "auth-check",
            "push-notebooks",
            "status-notebooks",
            "publish-dataset",
            "publish-model",
            "publish-all",
        ):
            assert cmd in result.stdout

    def test_missing_subcommand_errors(self):
        result = _run()
        # argparse exits non-zero when required subcommand is missing
        assert result.returncode != 0


class TestDryRun:
    def test_push_notebooks_dry_run(self):
        result = _run("--dry-run", "push-notebooks")
        # Succeeds even without credentials because every run is a no-op print.
        assert result.returncode == 0, result.stderr
        # All 4 kernel directories should be referenced in the printed commands
        for kernel in (
            "duecare_01_quickstart",
            "duecare_02_cross_domain_proof",
            "duecare_03_agent_swarm_deep_dive",
            "duecare_04_submission_walkthrough",
        ):
            assert kernel in result.stdout, f"missing kernel {kernel} in dry-run output"

    def test_publish_dataset_dry_run(self):
        result = _run("--dry-run", "publish-dataset")
        assert result.returncode == 0, result.stderr
        assert "datasets" in result.stdout
        assert "duecare_eval_results" in result.stdout

    def test_publish_model_dry_run(self):
        result = _run("--dry-run", "publish-model")
        assert result.returncode == 0, result.stderr
        assert "models" in result.stdout
        assert "duecare_safety_harness" in result.stdout

    def test_publish_all_dry_run(self):
        result = _run("--dry-run", "publish-all")
        # publish-all runs auth-check, which in dry-run returns 0 regardless
        assert result.returncode == 0, result.stderr
        # All 4 kernels should appear
        assert result.stdout.count("duecare_0") >= 4


class TestValidation:
    def test_every_kernel_metadata_is_valid_json(self):
        """Each kernel dir has a complete, parseable kernel-metadata.json
        whose code_file sibling exists on disk."""
        for kernel_dir in sorted(KERNELS_DIR.iterdir()):
            if not kernel_dir.is_dir():
                continue
            meta = kernel_dir / "kernel-metadata.json"
            assert meta.exists(), f"{kernel_dir}: missing kernel-metadata.json"
            data = json.loads(meta.read_text())
            for field in ("id", "title", "code_file", "kernel_type", "language"):
                assert field in data, f"{meta}: missing field {field}"
            nb = kernel_dir / data["code_file"]
            assert nb.exists(), f"{meta}: code_file {nb} does not exist"
            # Wheels dataset must be attached as a source.
            assert "taylorsamarel/duecare-llm-wheels" in data.get("dataset_sources", [])

    def test_dataset_metadata_is_valid(self):
        meta = REPO_ROOT / "kaggle" / "datasets" / "duecare_eval_results" / "dataset-metadata.json"
        assert meta.exists()
        data = json.loads(meta.read_text())
        for field in ("id", "title", "licenses"):
            assert field in data

    def test_model_metadata_is_valid(self):
        meta = REPO_ROOT / "kaggle" / "models" / "duecare_safety_harness" / "model-metadata.json"
        assert meta.exists()
        data = json.loads(meta.read_text())
        for field in ("ownerSlug", "title", "slug", "description"):
            assert field in data
