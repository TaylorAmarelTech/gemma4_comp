from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_gemma4_four_arm_evaluation.py"


def _load():
    spec = importlib.util.spec_from_file_location("gemma4_four_arm", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


builder = _load()


def _egregious_sources(tmp_path: Path) -> tuple[Path, Path]:
    rankings = tmp_path / "rankings.jsonl"
    results = tmp_path / "results.jsonl"
    ranking_rows = [
        {
            "prompt_id": f"prompt-{index}",
            "model": "gemma4:31b",
            "egregiousness": 10 - index / 10,
            "harm_type": f"failure-{index}",
            "why": "Recorded response enabled an unsafe action.",
            "worst_quote": "Recorded harmful sentence.",
        }
        for index in range(6)
    ]
    result_rows = []
    for index in range(6):
        for arm, response in (
            ("baseline", f"Recorded harmful response {index}."),
            ("harness_full", f"Recorded bounded response {index}."),
        ):
            result_rows.append(
                {
                    "prompt_id": f"prompt-{index}",
                    "model": "gemma4:31b",
                    "arm": arm,
                    "prompt_text": f"Recorded prompt {index}.",
                    "response": response,
                }
            )
    rankings.write_text("".join(json.dumps(row) + "\n" for row in ranking_rows), encoding="utf-8")
    results.write_text("".join(json.dumps(row) + "\n" for row in result_rows), encoding="utf-8")
    return rankings, results


def test_egregious_examples_are_recorded_and_hash_bound(tmp_path: Path) -> None:
    rankings, results = _egregious_sources(tmp_path)
    rows = builder.recorded_egregious_examples(rankings, results)

    assert len(rows) == 6
    assert len({row["failure_type"] for row in rows}) == len(rows)
    assert all("no fictional generation" in row["provenance"] for row in rows)
    assert all(row["training_eligible"] is False for row in rows)
    assert all(len(row["baseline_response_sha256"]) == 64 for row in rows)


def test_four_arm_build_verifies_source_and_reports_effects(tmp_path: Path) -> None:
    rankings, rich_results = _egregious_sources(tmp_path)
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    evaluation = run_dir / "evaluation.jsonl"
    evaluation.write_text(
        json.dumps(
            {
                "id": "row-1",
                "source_row_id": "source-1",
                "source_lineage_family_id": "family-test",
                "prompt": "Review this synthetic record.",
                "reference": "Observed: record. Unknown: support. Next: verify.",
                "base": {"response": "This is proven."},
                "adapted": {"response": "Verification may be needed."},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    manifest = {
        "adapter_produced": True,
        "artifacts": {
            "evaluation": {
                "path": evaluation.name,
                "sha256": builder._sha256(evaluation),
            }
        },
    }
    (run_dir / "run-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    result = builder.build_study(
        run_dir,
        tmp_path / "study",
        force=False,
        rankings_path=rankings,
        rich_results_path=rich_results,
    )
    rows = builder._read_jsonl(tmp_path / "study" / "four-arm-evaluation.jsonl")

    assert result["rows"] == 1
    assert set(rows[0]["arms"]) == {
        "base_without_harness",
        "base_with_harness",
        "adapter_without_harness",
        "adapter_with_harness",
    }
    assert result["effects"]["harness_effect_on_base"] > 0
    recorded = builder._read_jsonl(tmp_path / "study" / "recorded-egregious-examples.jsonl")
    assert len(recorded) == 6
    assert all(row["training_eligible"] is False for row in recorded)
