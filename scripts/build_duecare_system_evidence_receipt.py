#!/usr/bin/env python3
"""Build a machine-readable receipt for DueCare's broader harness evidence.

The receipt deliberately measures response quality on synthetic/composite
benchmark prompts. It does not relabel those prompts as real trafficking
cases and it does not claim victim identification or field effectiveness.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import attack_lift_report
import lift_stats

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LLM_JUDGE = ROOT / "reports" / "harness_lift_1000_judge.jsonl"
DEFAULT_DETERMINISTIC = ROOT / "reports" / "harness_lift_1000.jsonl"
DEFAULT_ATTACK_JUDGE = ROOT / "reports" / "attack_lift_judge.jsonl"
DEFAULT_ATTACK_MATRIX = ROOT / "configs" / "duecare" / "benchmarks" / "attack_matrix.json"
DEFAULT_OUTPUT = (
    ROOT
    / "reports"
    / "training_runs"
    / "gemma4_e2b_grounded_adapter_v3"
    / "system-evidence-receipt.json"
)
SCHEMA = "duecare.system_evidence_receipt.v1"


class ReceiptError(RuntimeError):
    """Raised when source evidence is incomplete or inconsistent."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ReceiptError(f"expected an object at {path}:{line_number}")
        rows.append(value)
    if not rows:
        raise ReceiptError(f"source is empty: {path}")
    return rows


def _one_model_stats(path: Path) -> tuple[dict[str, Any], int]:
    rows = _read_jsonl(path)
    stats = lift_stats.model_stats(rows)
    if len(stats) != 1:
        raise ReceiptError(f"expected exactly one subject model in {path}, found {len(stats)}")
    return stats[0], len(rows)


def _assert_count(label: str, actual: int, expected: int | None) -> None:
    if expected is not None and actual != expected:
        raise ReceiptError(f"{label}: expected {expected}, found {actual}")


def build_receipt(
    *,
    llm_judge_path: Path,
    deterministic_path: Path,
    attack_judge_path: Path,
    attack_matrix_path: Path,
    expected_judge_pairs: int | None = 911,
    expected_deterministic_pairs: int | None = 998,
    expected_attack_pairs: int | None = 140,
) -> dict[str, Any]:
    """Verify the source checkpoints and return a deterministic receipt."""

    paths = [llm_judge_path, deterministic_path, attack_judge_path, attack_matrix_path]
    for path in paths:
        if not path.is_file():
            raise ReceiptError(f"missing source evidence: {path}")

    judge_stats, judge_cells = _one_model_stats(llm_judge_path)
    deterministic_stats, deterministic_cells = _one_model_stats(deterministic_path)
    if judge_stats["model"] != deterministic_stats["model"]:
        raise ReceiptError("judge and deterministic checkpoints use different subject models")

    transform_map = attack_lift_report.transform_map(attack_matrix_path)
    by_transform, overall = attack_lift_report.paired_lifts(attack_judge_path, transform_map)
    if not overall:
        raise ReceiptError("attack checkpoint has no paired baseline/harness results")
    attack = attack_lift_report.aggregate(by_transform, overall)

    _assert_count(
        "large paired judge prompts",
        int(judge_stats["n_prompts_paired"]),
        expected_judge_pairs,
    )
    _assert_count(
        "deterministic paired prompts",
        int(deterministic_stats["n_prompts_paired"]),
        expected_deterministic_pairs,
    )
    _assert_count("paired attack prompts", int(attack["n_overall"]), expected_attack_pairs)

    source_files = {
        "large_pairwise_model_judge": {
            "path": llm_judge_path.relative_to(ROOT).as_posix()
            if llm_judge_path.is_relative_to(ROOT)
            else llm_judge_path.name,
            "sha256": _sha256(llm_judge_path),
            "graded_cells": judge_cells,
        },
        "large_pairwise_deterministic_grader": {
            "path": deterministic_path.relative_to(ROOT).as_posix()
            if deterministic_path.is_relative_to(ROOT)
            else deterministic_path.name,
            "sha256": _sha256(deterministic_path),
            "graded_cells": deterministic_cells,
        },
        "adversarial_model_judge": {
            "path": attack_judge_path.relative_to(ROOT).as_posix()
            if attack_judge_path.is_relative_to(ROOT)
            else attack_judge_path.name,
            "sha256": _sha256(attack_judge_path),
            "graded_cells": len(_read_jsonl(attack_judge_path)),
        },
        "attack_matrix": {
            "path": attack_matrix_path.relative_to(ROOT).as_posix()
            if attack_matrix_path.is_relative_to(ROOT)
            else attack_matrix_path.name,
            "sha256": _sha256(attack_matrix_path),
        },
    }
    payload: dict[str, Any] = {
        "schema_version": SCHEMA,
        "subject_model": judge_stats["model"],
        "benchmark_scope": (
            "Synthetic/composite trafficking-safety prompts and deterministic "
            "attack transformations; no real-case prevalence sample."
        ),
        "large_pairwise_model_judge": judge_stats,
        "large_pairwise_deterministic_grader": deterministic_stats,
        "adversarial_robustness": attack,
        "source_files": source_files,
        "measured_capabilities": [
            "response quality on paired trafficking-safety benchmark prompts",
            "harmful-request response robustness under declared prompt transformations",
            "agreement and disagreement between a model judge and deterministic grader",
        ],
        "not_measured": [
            "victim identification accuracy",
            "case prevalence",
            "legal findings",
            "real-world field detection effectiveness",
            "worker outcomes",
        ],
        "training_eligible": False,
    }
    receipt = dict(payload)
    receipt["receipt_payload_sha256"] = _canonical_sha256(payload)
    return receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--llm-judge", type=Path, default=DEFAULT_LLM_JUDGE)
    parser.add_argument("--deterministic", type=Path, default=DEFAULT_DETERMINISTIC)
    parser.add_argument("--attack-judge", type=Path, default=DEFAULT_ATTACK_JUDGE)
    parser.add_argument("--attack-matrix", type=Path, default=DEFAULT_ATTACK_MATRIX)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--expected-judge-pairs", type=int, default=911)
    parser.add_argument("--expected-deterministic-pairs", type=int, default=998)
    parser.add_argument("--expected-attack-pairs", type=int, default=140)
    args = parser.parse_args(argv)

    receipt = build_receipt(
        llm_judge_path=args.llm_judge.resolve(),
        deterministic_path=args.deterministic.resolve(),
        attack_judge_path=args.attack_judge.resolve(),
        attack_matrix_path=args.attack_matrix.resolve(),
        expected_judge_pairs=args.expected_judge_pairs,
        expected_deterministic_pairs=args.expected_deterministic_pairs,
        expected_attack_pairs=args.expected_attack_pairs,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(
        json.dumps(
            {
                "output": str(args.output),
                "receipt_payload_sha256": receipt["receipt_payload_sha256"],
                "judge_pairs": receipt["large_pairwise_model_judge"]["n_prompts_paired"],
                "attack_pairs": receipt["adversarial_robustness"]["n_overall"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
