from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_recorded_harmful_request_judge_study.py"
SPEC = importlib.util.spec_from_file_location("recorded_harmful_request_judge", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def source_row() -> dict[str, object]:
    return {
        "fixture_id": "recorded-01",
        "prompt": "Recorded prompt",
        "egregious_response": "Unsafe operational response",
        "bounded_rewrite": "Safe bounded response",
        "training_eligible": False,
    }


def test_build_requests_blinds_both_orders() -> None:
    requests = MODULE.build_requests([source_row()])
    assert len(requests) == 2
    assert {row["order"] for row in requests} == {"control_as_a", "treatment_as_a"}
    assert all("recorded_harness_response" in row["request_id"] for row in requests)
    assert requests[0]["candidate_a_sha256"] == requests[1]["candidate_b_sha256"]
    assert requests[0]["candidate_b_sha256"] == requests[1]["candidate_a_sha256"]


def test_summary_normalizes_treatment_and_reports_scope() -> None:
    requests = MODULE.build_requests([source_row()])
    verdicts = [
        {
            "request_id": requests[0]["request_id"],
            "pair_id": requests[0]["pair_id"],
            "judge_model": "frozen-judge",
            "valid": True,
            "treatment_delta": 8.0,
        },
        {
            "request_id": requests[1]["request_id"],
            "pair_id": requests[1]["pair_id"],
            "judge_model": "frozen-judge",
            "valid": True,
            "treatment_delta": 6.0,
        },
    ]
    summary = MODULE.summarize(requests, verdicts)
    assert summary["complete"] is True
    assert summary["mean_harness_delta"] == 7.0
    assert summary["harness_wins"] == 1
    assert "real-world detection effectiveness" in summary["not_measured"]


def test_summary_reports_exact_sign_test_and_evidence_scale() -> None:
    requests = MODULE.build_requests([source_row()])
    verdicts = [
        {
            "request_id": requests[0]["request_id"],
            "pair_id": requests[0]["pair_id"],
            "judge_model": "frozen-judge",
            "valid": True,
            "treatment_delta": 8.0,
        },
        {
            "request_id": requests[1]["request_id"],
            "pair_id": requests[1]["pair_id"],
            "judge_model": "frozen-judge",
            "valid": True,
            "treatment_delta": 6.0,
        },
    ]
    summary = MODULE.summarize(requests, verdicts)
    assert summary["exact_sign_test_two_sided_p"] == 1.0
    assert summary["evidence_scale"] == "anecdote_scale_fewer_than_10_pairs"
    assert "descriptive only" in summary["small_sample_statistics_note"]
