from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_duecare_system_evidence_receipt.py"
sys.path.insert(0, str(ROOT / "scripts"))
SPEC = importlib.util.spec_from_file_location("system_evidence_receipt", SCRIPT)
assert SPEC and SPEC.loader
receipt_builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(receipt_builder)


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def test_build_receipt_keeps_capability_boundary(tmp_path: Path) -> None:
    judge = tmp_path / "judge.jsonl"
    deterministic = tmp_path / "deterministic.jsonl"
    attack_judge = tmp_path / "attack.jsonl"
    attack_matrix = tmp_path / "attack-matrix.json"
    paired = [
        {"prompt_id": "p1", "model": "gemma-test", "arm": "baseline", "dim": "safety", "score": 2},
        {"prompt_id": "p1", "model": "gemma-test", "arm": "harnessed", "dim": "safety", "score": 8},
        {"prompt_id": "p2", "model": "gemma-test", "arm": "baseline", "dim": "safety", "score": 4},
        {"prompt_id": "p2", "model": "gemma-test", "arm": "harnessed", "dim": "safety", "score": 7},
    ]
    _write_jsonl(judge, paired)
    _write_jsonl(deterministic, paired)
    _write_jsonl(
        attack_judge,
        [
            {
                "prompt_id": "a1",
                "model": "gemma-test",
                "arm": "baseline",
                "dim": "safety",
                "score": 1,
            },
            {
                "prompt_id": "a1",
                "model": "gemma-test",
                "arm": "harnessed",
                "dim": "safety",
                "score": 9,
            },
        ],
    )
    attack_matrix.write_text(
        json.dumps(
            {
                "prompts": [
                    {
                        "id": "a1",
                        "transform": "instruction_override",
                        "category": "input_attack",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    receipt = receipt_builder.build_receipt(
        llm_judge_path=judge,
        deterministic_path=deterministic,
        attack_judge_path=attack_judge,
        attack_matrix_path=attack_matrix,
        expected_judge_pairs=2,
        expected_deterministic_pairs=2,
        expected_attack_pairs=1,
    )

    assert receipt["large_pairwise_model_judge"]["lift"] == 4.5
    assert receipt["adversarial_robustness"]["overall"]["mean"] == 8.0
    assert receipt["training_eligible"] is False
    assert "victim identification accuracy" in receipt["not_measured"]
    assert len(receipt["receipt_payload_sha256"]) == 64


def test_build_receipt_rejects_expected_count_mismatch(tmp_path: Path) -> None:
    path = tmp_path / "rows.jsonl"
    rows = [
        {"prompt_id": "p1", "model": "gemma-test", "arm": "baseline", "dim": "safety", "score": 2},
        {"prompt_id": "p1", "model": "gemma-test", "arm": "harnessed", "dim": "safety", "score": 8},
    ]
    _write_jsonl(path, rows)
    matrix = tmp_path / "matrix.json"
    matrix.write_text(
        json.dumps({"prompts": [{"id": "p1", "transform": "rot13"}]}),
        encoding="utf-8",
    )

    try:
        receipt_builder.build_receipt(
            llm_judge_path=path,
            deterministic_path=path,
            attack_judge_path=path,
            attack_matrix_path=matrix,
            expected_judge_pairs=2,
            expected_deterministic_pairs=1,
            expected_attack_pairs=1,
        )
    except receipt_builder.ReceiptError as exc:
        assert "large paired judge prompts" in str(exc)
    else:
        raise AssertionError("expected ReceiptError")
