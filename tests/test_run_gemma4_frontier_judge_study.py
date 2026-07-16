from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import run_gemma4_frontier_judge_study as study


def _row() -> dict:
    return {
        "id": "heldout-1",
        "prompt": "Review this approved source excerpt and preserve uncertainty.",
        "reference": "Observed: one statement. Unknown: corroboration. Next: review.",
        "arms": {
            "base_without_harness": {"text": "certain claim"},
            "base_with_harness": {"text": "unverified base draft"},
            "adapter_without_harness": {"text": "bounded claim"},
            "adapter_with_harness": {"text": "unverified adapted draft"},
        },
    }


def test_requests_are_blinded_and_use_both_orders() -> None:
    requests = study.build_requests([_row()])
    assert len(requests) == 8
    assert {row["order"] for row in requests} == {"control_as_a", "treatment_as_a"}
    assert all("base_without_harness" not in row["request_text"] for row in requests)
    assert len({row["context_sha256"] for row in requests}) == 1
    assert len({row["rubric_sha256"] for row in requests}) == 1


def test_order_swap_is_normalized_to_treatment_direction(tmp_path: Path) -> None:
    requests = study.build_requests([_row()])[:2]

    def caller(prompt: str, **_: object) -> str:
        delta = 6 if "CANDIDATE A\ncertain claim" in prompt else -4
        return json.dumps(
            {
                "delta": delta,
                "confidence": "high",
                "abstain": False,
                "criteria": {},
                "defect_tags_a": [],
                "defect_tags_b": [],
            }
        )

    rows = study.execute_requests(
        requests,
        tmp_path / "checkpoint.jsonl",
        judge_model="glm-5.2:cloud",
        caller=caller,
    )
    assert [row["treatment_delta"] for row in rows] == [6.0, 4.0]


def test_invalid_verdict_is_not_silently_scored(tmp_path: Path) -> None:
    request = study.build_requests([_row()])[:1]
    rows = study.execute_requests(
        request,
        tmp_path / "checkpoint.jsonl",
        judge_model="judge",
        caller=lambda *_args, **_kwargs: "not json",
    )
    assert rows[0]["valid"] is False
    assert rows[0]["treatment_delta"] is None


def test_invalid_checkpoint_entry_is_retried(tmp_path: Path) -> None:
    request = study.build_requests([_row()])[:1]
    checkpoint = tmp_path / "checkpoint.jsonl"
    invalid = {
        "request_id": request[0]["request_id"],
        "request_sha256": request[0]["request_sha256"],
        "valid": False,
    }
    checkpoint.write_text(json.dumps(invalid) + "\n", encoding="utf-8")
    rows = study.execute_requests(
        request,
        checkpoint,
        judge_model="glm-5.2:cloud",
        caller=lambda *_args, **_kwargs: json.dumps(
            {"delta": 2, "confidence": "medium", "abstain": False}
        ),
    )
    assert rows[0]["valid"] is True
    assert rows[0]["decoding_temperature"] == 0.0


def test_summary_requires_complete_two_order_pairs() -> None:
    requests = study.build_requests([_row()])
    verdicts = []
    for request in requests:
        verdicts.append(
            {
                "request_id": request["request_id"],
                "pair_id": request["pair_id"],
                "comparison": request["comparison"],
                "judge_model": "glm-5.2:cloud",
                "valid": True,
                "treatment_delta": 2.0,
            }
        )
    summary = study.summarize(requests, verdicts)
    assert summary["complete"] is True
    assert summary["same_judge_before_and_after"] is True
    assert all(value["complete_pairs"] == 1 for value in summary["comparisons"].values())


def test_exact_sign_test_matches_hand_computation() -> None:
    assert study._exact_sign_test_two_sided_p(6, 0) == 0.03125
    assert study._exact_sign_test_two_sided_p(0, 4) == 0.125
    assert study._exact_sign_test_two_sided_p(2, 2) == 1.0
    assert study._exact_sign_test_two_sided_p(0, 0) is None
    assert study._exact_sign_test_two_sided_p(9, 1) == round(22 / 1024, 6)


def test_summary_reports_exact_sign_test_and_evidence_scale() -> None:
    requests = study.build_requests([_row()])
    verdicts = []
    for request in requests:
        verdicts.append(
            {
                "request_id": request["request_id"],
                "pair_id": request["pair_id"],
                "comparison": request["comparison"],
                "judge_model": "glm-5.2:cloud",
                "valid": True,
                "treatment_delta": 2.0,
            }
        )
    summary = study.summarize(requests, verdicts)
    for value in summary["comparisons"].values():
        assert value["exact_sign_test_two_sided_p"] == 1.0
        assert value["evidence_scale"] == "anecdote_scale_fewer_than_10_pairs"
    assert "descriptive only" in summary["small_sample_statistics_note"]


def test_bad_delta_is_rejected() -> None:
    assert study._validated_verdict('{"delta": 11, "confidence": "high"}') is None
    assert study._validated_verdict('{"delta": 1, "confidence": "unknown"}') is None
    with pytest.raises(study.JudgeStudyError):
        study.build_requests([{**_row(), "reference": ""}])


def test_registry_overrides_prepend_without_erasing_fallbacks() -> None:
    candidates = study.configured_judge_candidates(
        study.DEFAULT_MODEL_REGISTRY,
        overrides=["operator:first"],
    )
    assert candidates[0] == "operator:first"
    assert "glm-5.2:cloud" in candidates
    assert len(candidates) >= 4


def test_preflight_selects_once_after_failed_candidate() -> None:
    calls = []

    def caller(_prompt: str, *, model: str, **_kwargs: object) -> str:
        calls.append(model)
        if model == "bad:first":
            raise RuntimeError("unavailable")
        return '{"delta":0,"confidence":"high","abstain":false}'

    selected, receipt = study.preflight_and_freeze_judge(
        ["bad:first", "good:second", "unused:third"],
        caller=caller,
        max_tokens=128,
        temperature=0.0,
    )
    assert selected == "good:second"
    assert calls == ["bad:first", "good:second"]
    assert receipt["switching_during_study_allowed"] is False
