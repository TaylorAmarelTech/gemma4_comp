from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


MODULE = _load(
    "build_recorded_harmful_request_expansion",
    _ROOT / "scripts" / "build_recorded_harmful_request_expansion.py",
)
RECORDED = _load(
    "recorded_harmful_request_judge_study_for_expansion",
    _ROOT / "scripts" / "run_recorded_harmful_request_judge_study.py",
)


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text(
        "\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8"
    )


def _fixtures(tmp_path: Path, *, ranked: int = 3, complete: int = 3):
    rankings = []
    results = []
    for index in range(ranked):
        prompt_id = f"PROMPT-{index:04d}"
        rankings.append(
            {
                "model": "gemma4:31b",
                "prompt_id": prompt_id,
                "egregiousness": 9.0,
                "harm_type": "operational_facilitation",
                "why": "synthetic rationale",
                "worst_quote": "synthetic worst quote",
            }
        )
        if index < complete:
            results.append(
                {
                    "model": "gemma4:31b",
                    "prompt_id": prompt_id,
                    "arm": "baseline",
                    "response": f"unsafe recorded response {index}",
                    "prompt_text": f"recorded prompt {index}",
                }
            )
            results.append(
                {
                    "model": "gemma4:31b",
                    "prompt_id": prompt_id,
                    "arm": "harness_full",
                    "response": f"bounded recorded response {index}",
                    "prompt_text": f"recorded prompt {index}",
                }
            )
    rankings_path = tmp_path / "rankings.jsonl"
    _write_jsonl(rankings_path, rankings)
    results_path = tmp_path / "results.jsonl"
    _write_jsonl(results_path, results)
    return rankings_path, results_path


def test_expansion_freezes_all_qualifying_pairs(tmp_path: Path) -> None:
    rankings, results = _fixtures(tmp_path, ranked=3, complete=3)
    out = tmp_path / "pack"
    manifest = MODULE.build_expansion(
        rankings, results, out, subject_model="gemma4:31b", limit=0, force=False
    )
    assert manifest["pair_count"] == 3
    assert manifest["requested_verdicts"] == 6
    assert manifest["execution_status"] == "prepared_not_executed"
    assert manifest["publication_status"] == "local_evidence_not_for_publication"
    assert manifest["training_eligible"] is False
    rows = [
        json.loads(line)
        for line in (out / "recorded-egregious-examples.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]
    assert all(row["training_eligible"] is False for row in rows)
    frozen = [
        json.loads(line)
        for line in (out / "judge-requests.frozen.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]
    assert len(frozen) == 6
    assert all("request_text" not in row for row in frozen)


def test_partial_join_freezes_available_pairs_only(tmp_path: Path) -> None:
    rankings, results = _fixtures(tmp_path, ranked=4, complete=2)
    manifest = MODULE.build_expansion(
        rankings,
        results,
        tmp_path / "pack",
        subject_model="gemma4:31b",
        limit=0,
        force=False,
    )
    assert manifest["qualifying_ranked_prompts"] == 4
    assert manifest["pair_count"] == 2


def test_expansion_dir_passes_recorded_study_verification(tmp_path: Path) -> None:
    rankings, results = _fixtures(tmp_path)
    out = tmp_path / "pack"
    MODULE.build_expansion(
        rankings, results, out, subject_model="gemma4:31b", limit=0, force=False
    )
    manifest, rows = RECORDED.verified_rows(out)
    assert manifest["schema_version"] == MODULE.SCHEMA
    assert len(rows) == 3


def test_limit_caps_pair_count(tmp_path: Path) -> None:
    rankings, results = _fixtures(tmp_path)
    manifest = MODULE.build_expansion(
        rankings,
        results,
        tmp_path / "pack",
        subject_model="gemma4:31b",
        limit=2,
        force=False,
    )
    assert manifest["pair_count"] == 2


def test_refuses_to_replace_foreign_directory(tmp_path: Path) -> None:
    rankings, results = _fixtures(tmp_path)
    out = tmp_path / "pack"
    out.mkdir()
    (out / "keep.txt").write_text("not ours", encoding="utf-8")
    with pytest.raises(MODULE.StudyError):
        MODULE.build_expansion(
            rankings, results, out, subject_model="gemma4:31b", limit=0, force=True
        )


def test_request_pack_hash_is_deterministic(tmp_path: Path) -> None:
    rankings, results = _fixtures(tmp_path)
    first = MODULE.build_expansion(
        rankings, results, tmp_path / "p1", subject_model="gemma4:31b", limit=0, force=False
    )
    second = MODULE.build_expansion(
        rankings, results, tmp_path / "p2", subject_model="gemma4:31b", limit=0, force=False
    )
    assert first["request_pack_sha256"] == second["request_pack_sha256"]
