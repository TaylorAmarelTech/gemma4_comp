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


def _paths(data_dir: Path) -> dict[str, Path]:
    return {
        "facts": data_dir / "extracted_facts" / "facts.jsonl",
        "kb": data_dir / "knowledge_base" / "kb.json",
        "generated": data_dir / "generated_prompts" / "kb_prompts.jsonl",
        "rated": data_dir / "rated_prompts" / "rated.jsonl",
        "remixed": data_dir / "remixed_prompts" / "remixed.jsonl",
    }


@pytest.fixture(scope="module")
def isolated_pipeline(
    tmp_path_factory: pytest.TempPathFactory,
) -> tuple[dict[str, Path], dict[int, subprocess.CompletedProcess]]:
    data_dir = tmp_path_factory.mktemp("pipeline-data")
    paths = _paths(data_dir)
    results = {
        4: _run(
            "scripts/pipeline/stage4_knowledge_base.py",
            "--facts-input",
            str(paths["facts"]),
            "--output",
            str(paths["kb"]),
            "--include-existing",
        ),
    }
    results[5] = _run(
        "scripts/pipeline/stage5_generate_prompts.py",
        "--kb-input",
        str(paths["kb"]),
        "--output",
        str(paths["generated"]),
        "--max-entries",
        "3",
    )
    results[6] = _run(
        "scripts/pipeline/stage6_rate_evaluate.py",
        "--input",
        str(paths["generated"]),
        "--output",
        str(paths["rated"]),
        "--max-prompts",
        "5",
        "--heuristic",
    )
    results[7] = _run(
        "scripts/pipeline/stage7_remix.py",
        "--input",
        str(paths["rated"]),
        "--output",
        str(paths["remixed"]),
        "--max-base",
        "3",
        "--variations-per-gen",
        "1",
        "--heuristic",
    )
    return paths, results


class TestStage4KnowledgeBase:
    def test_builds_kb_from_configs(self, isolated_pipeline):
        paths, results = isolated_pipeline
        result = results[4]
        assert result.returncode == 0
        kb_path = paths["kb"]
        assert kb_path.exists()
        kb = json.loads(kb_path.read_text(encoding="utf-8"))
        assert kb["n_entries"] > 0

    def test_kb_has_legal_provisions(self, isolated_pipeline):
        paths, _ = isolated_pipeline
        kb_path = paths["kb"]
        kb = json.loads(kb_path.read_text(encoding="utf-8"))
        assert len(kb["data"].get("legal_provisions", [])) > 0


class TestStage5GeneratePrompts:
    def test_generates_prompts_from_kb(self, isolated_pipeline):
        paths, results = isolated_pipeline
        result = results[5]
        assert result.returncode == 0
        output = paths["generated"]
        assert output.exists()
        prompts = [json.loads(line) for line in output.open("r", encoding="utf-8")]
        assert len(prompts) > 0


class TestStage6RateEvaluate:
    def test_rates_prompts(self, isolated_pipeline):
        paths, results = isolated_pipeline
        result = results[6]
        assert result.returncode == 0
        output = paths["rated"]
        assert output.exists()


class TestStage7Remix:
    def test_remixes_with_generators(self, isolated_pipeline):
        paths, results = isolated_pipeline
        result = results[7]
        assert result.returncode == 0
        output = paths["remixed"]
        assert output.exists()
        prompts = [json.loads(line) for line in output.open("r", encoding="utf-8")]
        # Should have originals + variations
        assert len(prompts) > 3


class TestPipelineRunner:
    def test_heuristic_quick_mode_does_not_mutate_tracked_data(self, tmp_path):
        tracked_paths = [
            REPO_ROOT / "data" / "knowledge_base" / "kb.json",
            REPO_ROOT / "data" / "generated_prompts" / "kb_prompts.jsonl",
            REPO_ROOT / "data" / "rated_prompts" / "rated.jsonl",
            REPO_ROOT / "data" / "remixed_prompts" / "remixed.jsonl",
        ]
        before = {path: path.read_bytes() for path in tracked_paths}
        data_dir = tmp_path / "data"
        result = _run(
            "scripts/pipeline/run_pipeline.py",
            "--stages", "4,5,6,7",
            "--heuristic", "--quick",
            "--data-dir", str(data_dir),
        )
        assert result.returncode == 0
        assert "PIPELINE COMPLETE" in result.stdout
        assert "Failed: 0" in result.stdout
        assert (data_dir / "remixed_prompts" / "remixed.jsonl").is_file()
        assert {path: path.read_bytes() for path in tracked_paths} == before
