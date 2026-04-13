"""Integration tests for the 8-stage pipeline."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _run(script: str, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(REPO_ROOT / script), *args],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        timeout=60,
    )


class TestStage4KnowledgeBase:
    def test_builds_kb_from_configs(self):
        result = _run("scripts/pipeline/stage4_knowledge_base.py", "--include-existing")
        assert result.returncode == 0
        kb_path = REPO_ROOT / "data" / "knowledge_base" / "kb.json"
        assert kb_path.exists()
        kb = json.loads(kb_path.read_text(encoding="utf-8"))
        assert kb["n_entries"] > 0

    def test_kb_has_legal_provisions(self):
        kb_path = REPO_ROOT / "data" / "knowledge_base" / "kb.json"
        if not kb_path.exists():
            pytest.skip("KB not built yet")
        kb = json.loads(kb_path.read_text(encoding="utf-8"))
        assert len(kb["data"].get("legal_provisions", [])) > 0


class TestStage5GeneratePrompts:
    def test_generates_prompts_from_kb(self):
        result = _run("scripts/pipeline/stage5_generate_prompts.py", "--max-entries", "3")
        assert result.returncode == 0
        output = REPO_ROOT / "data" / "generated_prompts" / "kb_prompts.jsonl"
        assert output.exists()
        prompts = [json.loads(line) for line in output.open("r", encoding="utf-8")]
        assert len(prompts) > 0


class TestStage6RateEvaluate:
    def test_rates_prompts(self):
        result = _run("scripts/pipeline/stage6_rate_evaluate.py", "--max-prompts", "5", "--heuristic")
        assert result.returncode == 0
        output = REPO_ROOT / "data" / "rated_prompts" / "rated.jsonl"
        assert output.exists()


class TestStage7Remix:
    def test_remixes_with_generators(self):
        result = _run("scripts/pipeline/stage7_remix.py", "--max-base", "3", "--variations-per-gen", "1", "--heuristic")
        assert result.returncode == 0
        output = REPO_ROOT / "data" / "remixed_prompts" / "remixed.jsonl"
        assert output.exists()
        prompts = [json.loads(line) for line in output.open("r", encoding="utf-8")]
        # Should have originals + variations
        assert len(prompts) > 3


class TestPipelineRunner:
    def test_heuristic_quick_mode(self):
        result = _run(
            "scripts/pipeline/run_pipeline.py",
            "--stages", "4,5,6,7",
            "--heuristic", "--quick",
        )
        assert result.returncode == 0
        assert "PIPELINE COMPLETE" in result.stdout
        assert "Failed: 0" in result.stdout
