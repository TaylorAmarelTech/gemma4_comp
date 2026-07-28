"""Frozen no-call contract for the Kimi K3 / Gemini 3.1 directional campaign."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts import model_failure_study

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "configs/duecare/benchmarks/kimi_k3_500_context_judge_campaign.json"


def _selection_sha(prompts: list[dict]) -> str:
    payload = [
        {
            "id": prompt["id"],
            "text_sha256": hashlib.sha256(prompt["text"].encode("utf-8")).hexdigest(),
        }
        for prompt in prompts
    ]
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def test_campaign_manifest_matches_frozen_selection_and_call_topology() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    selection = manifest["selection"]
    prompts = model_failure_study.load_prompts(
        include_seeds=selection["include_seeds"],
        limit=selection["prompt_count"],
        selection_mode=selection["mode"],
        selection_seed=selection["seed"],
    )

    assert len(prompts) == 500
    assert len({prompt["category"] or "uncategorized" for prompt in prompts}) == 117
    assert _selection_sha(prompts) == selection["selection_sha256"]
    assert manifest["candidate_lane"]["calls"] == 500
    assert manifest["deterministic_lane"]["provider_calls"] == 0
    assert sum(lane["calls"] for lane in manifest["judge_lanes"]) == 1000
    assert manifest["aggregate_reservation"]["hosted_calls"] == 1500


def test_campaign_keeps_independent_and_self_judges_separate() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    by_model = {lane["model"]: lane for lane in manifest["judge_lanes"]}

    assert by_model["gemini-3.1-pro-preview"]["relationship"] == "cross_family"
    assert by_model["gemini-3.1-pro-preview"]["primary_eligible"] is True
    assert by_model["kimi-k3"]["relationship"] == "self_family"
    assert by_model["kimi-k3"]["primary_eligible"] is False
    assert manifest["execution_state"]["human_ratings"] == 0
    assert "human validation" in manifest["interpretation_contract"]["prohibited_claims"]
    gemini_args = manifest["commands"]["gemini_judge_plan_args"]
    kimi_args = manifest["commands"]["kimi_self_judge_plan_args"]
    reason_index = gemini_args.index("--reasoning-effort")
    assert gemini_args[reason_index : reason_index + 2] == ["--reasoning-effort", "low"]
    assert "--json-mode" in gemini_args
    assert "--json-mode" not in kimi_args
    assert all(
        args[args.index("--max-planned-model-calls") + 1] == "500"
        for args in manifest["commands"].values()
    )


def test_campaign_reservation_math_is_reconciled() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    candidate = manifest["candidate_lane"]
    judges = manifest["judge_lanes"]
    aggregate = manifest["aggregate_reservation"]

    assert aggregate["reserved_input_tokens"] == (
        candidate["reserved_input_tokens"]
        + 2 * manifest["judge_protocol"]["reserved_input_tokens_per_judge_lane"]
    )
    assert aggregate["reserved_output_tokens"] == (
        candidate["reserved_output_tokens"]
        + 2 * manifest["judge_protocol"]["reserved_output_tokens_per_judge_lane"]
    )
    assert (
        round(
            candidate["worst_case_usd"] + sum(row["worst_case_usd"] for row in judges),
            6,
        )
        == aggregate["worst_case_usd"]
    )
    assert aggregate["recommended_cash_ceiling_usd"] >= aggregate["worst_case_usd"]
