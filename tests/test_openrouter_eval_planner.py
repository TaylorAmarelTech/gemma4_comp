"""Tests for the OpenRouter paid-evaluation planner."""
from __future__ import annotations

from collections import Counter
import json
import sys
from pathlib import Path

import pytest

_SCRIPTS = str(Path(__file__).resolve().parents[1] / "scripts")
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

import openrouter_eval_planner as planner  # noqa: E402


PROMPT_CATALOG = [
    {
        "id": "k8s_worker_location_cronjob",
        "category": "cloud_k8s_tooling",
        "text": "GPS geofence CronJob prompt",
    },
    {
        "id": "cloud_function_payroll_deduction_camouflage",
        "category": "cloud_function_tooling",
        "text": "Payroll deduction camouflage prompt",
    },
    {
        "id": "faith_ministry_tithe_labor",
        "category": "faith_relationship",
        "text": "Faith relationship prompt",
    },
    {
        "id": "worker_asks_for_help",
        "category": "victim_safety",
        "text": "Worker help prompt",
    },
    {
        "id": "agency_query_009",
        "category": "agency_compliance",
        "text": "Agency legal compliance prompt",
    },
    {
        "id": "external_gap",
        "category": "new_external",
        "text": "Unseen external prompt",
    },
    {
        "id": "safe_tool",
        "category": "safe_tool_ideation",
        "text": "Safe tool prompt",
    },
    {
        "id": "metadata_server_secret_scrape",
        "category": "cloud_security_boundary",
        "text": "Metadata server secret scrape prompt",
    },
]


def test_aggregate_prompts_prioritizes_low_judge_and_risk_flags() -> None:
    rows = [
        {
            "provider": "llm7",
            "prompt_id": "k8s_worker_location_cronjob",
            "ok": True,
            "grade": {"score_0_10": 5.8},
            "llm_judges": {
                "llm7": {
                    "ok": True,
                    "score_0_10": 3,
                    "verdict": "weak",
                    "risk_flags": ["enables geofencing surveillance"],
                }
            },
        }
    ]

    items = planner.aggregate_prompts(rows, PROMPT_CATALOG)
    target = next(item for item in items if item["prompt_id"] == "k8s_worker_location_cronjob")

    assert target["bucket"] == "harm_stress"
    assert target["priority_score"] > 50
    assert "low judge score" in target["why"]


def test_select_prompt_plan_keeps_relationship_and_coverage_cases() -> None:
    rows = [
        {
            "provider": "llm7",
            "prompt_id": "cloud_function_payroll_deduction_camouflage",
            "ok": True,
            "grade": {"score_0_10": 1.0},
            "llm_judges": {"llm7": {"ok": True, "score_0_10": 2, "risk_flags": ["wage theft"]}},
        }
    ]
    items = planner.aggregate_prompts(rows, PROMPT_CATALOG)

    selected = planner.select_prompt_plan(items, 8)
    selected_ids = {item["prompt_id"] for item in selected}

    assert "cloud_function_payroll_deduction_camouflage" in selected_ids
    assert any(item["bucket"] == "relationship_semantic" for item in selected)
    assert any(item["bucket"] == "coverage_gap" for item in selected)


def test_select_prompt_plan_balances_categories_within_bucket() -> None:
    prompt_catalog = [
        {
            "id": f"family_case_{index:02d}",
            "category": "family_relationship",
            "text": "Family relationship prompt",
        }
        for index in range(12)
    ] + [
        {
            "id": f"faith_case_{index:02d}",
            "category": "faith_relationship",
            "text": "Faith relationship prompt",
        }
        for index in range(12)
    ]

    selected = planner.select_prompt_plan(planner.aggregate_prompts([], prompt_catalog), 20)
    category_counts = Counter(item["category"] for item in selected)

    assert category_counts["family_relationship"] >= 2
    assert category_counts["faith_relationship"] >= 2


def test_build_plan_emits_commands_and_costs(tmp_path: Path) -> None:
    result_path = tmp_path / "results.jsonl"
    result_path.write_text(
        json.dumps(
            {
                "provider": "llm7",
                "prompt_id": "metadata_server_secret_scrape",
                "ok": True,
                "response": "No.",
                "grade": {"score_0_10": 6.4},
                "llm_judges": {"llm7": {"ok": True, "score_0_10": 3, "risk_flags": ["weak redirect"]}},
            }
        )
        + "\n",
        encoding="utf-8",
    )

    rows = planner.load_rows([result_path])
    plan = planner.build_plan(
        rows,
        prompt_catalog=PROMPT_CATALOG,
        prompt_limit=6,
        budget_usd=100,
        out_dir="reports/free_api_prompt_eval/openrouter_paid_test",
        prompt_file="reports/openrouter_eval_plan/selected_prompts.jsonl",
        result_paths=[result_path],
    )

    assert plan["selected_prompts"]
    assert plan["cost_estimate"]["estimated_cost_usd"] > 0
    assert "candidate" in plan["commands"]
    assert plan["candidate_providers"] == ["openrouter_nemotron_ultra"]
    assert "openrouter_nemotron_ultra" in plan["commands"]["candidate"]
    assert "--prompt-file reports/openrouter_eval_plan/selected_prompts.jsonl" in plan["commands"]["candidate"]
    assert "--resume" in plan["commands"]["candidate"]
    assert "--fail-on-missing-keys" in plan["commands"]["candidate"]
    assert "--retry-errors" in plan["commands"]["candidate"]
    assert f"--max-planned-calls {plan['phase_call_counts']['candidate']}" in plan["commands"]["candidate"]
    assert plan["preflight_commands"]["candidate"].endswith(" --dry-run")
    assert "critical_second_judge" in plan["commands"]
    assert "--prompt-file reports/openrouter_eval_plan/critical_prompts.jsonl" in plan["commands"]["critical_second_judge"]
    assert "--prompt-ids" not in plan["commands"]["critical_second_judge"]
    assert "--retry-judge-errors" in plan["commands"]["critical_second_judge"]
    assert f"--max-planned-calls {plan['phase_call_counts']['critical_second_judge']}" in plan["commands"]["critical_second_judge"]
    assert "arbiter_judge" in plan["commands"]
    assert "--prompt-file reports/openrouter_eval_plan/arbiter_prompts.jsonl" in plan["commands"]["arbiter_judge"]
    assert "--prompt-ids" not in plan["commands"]["arbiter_judge"]
    assert f"--max-planned-calls {plan['phase_call_counts']['arbiter_judge']}" in plan["commands"]["arbiter_judge"]
    assert "metadata_server_secret_scrape" in {
        item["prompt_id"] for item in plan["selected_prompts"]
    }


def test_build_plan_accepts_single_custom_candidate() -> None:
    plan = planner.build_plan(
        [],
        prompt_catalog=PROMPT_CATALOG,
        prompt_limit=4,
        budget_usd=100,
        out_dir="reports/free_api_prompt_eval/openrouter_paid_test",
        prompt_file="reports/openrouter_eval_plan/selected_prompts.jsonl",
        result_paths=[],
        candidate_providers=["openrouter_claude_opus48"],
    )

    assert plan["candidate_providers"] == ["openrouter_claude_opus48"]
    assert plan["cost_estimate"]["candidate_calls"] == 4
    assert "--providers openrouter_claude_opus48" in plan["commands"]["candidate"]


def test_parse_provider_keys_rejects_unknown_key() -> None:
    assert planner.parse_provider_keys("", ["openrouter_nemotron_ultra"]) == ["openrouter_nemotron_ultra"]
    with pytest.raises(SystemExit):
        planner.parse_provider_keys("missing", [])


def test_refresh_model_roster_from_catalog_updates_prices() -> None:
    roster = {
        "p1": {
            "model": "provider/model-1",
            "role": "candidate",
            "prompt_cost": 1.0,
            "completion_cost": 2.0,
        }
    }
    refreshed = planner.refresh_model_roster_from_catalog(
        roster,
        [
            {
                "id": "provider/model-1",
                "context_length": 1234,
                "pricing": {"prompt": "0.000001", "completion": "0.000002"},
                "top_provider": {"max_completion_tokens": 567},
            }
        ],
    )

    assert refreshed["p1"]["prompt_cost"] == 0.000001
    assert refreshed["p1"]["completion_cost"] == 0.000002
    assert refreshed["p1"]["openrouter_context_length"] == 1234
    assert refreshed["p1"]["openrouter_max_completion_tokens"] == 567


def test_refresh_model_roster_from_catalog_rejects_missing_model() -> None:
    with pytest.raises(SystemExit):
        planner.refresh_model_roster_from_catalog(
            {
                "p1": {
                    "model": "provider/missing",
                    "role": "candidate",
                    "prompt_cost": 1.0,
                    "completion_cost": 2.0,
                }
            },
            [],
        )


def test_write_plan_emits_phase_prompt_files(tmp_path: Path) -> None:
    plan = planner.build_plan(
        [
            {
                "provider": "llm7",
                "prompt_id": "metadata_server_secret_scrape",
                "ok": True,
                "response": "No.",
                "grade": {"score_0_10": 6.4},
                "llm_judges": {"llm7": {"ok": True, "score_0_10": 3, "risk_flags": ["weak redirect"]}},
            }
        ],
        prompt_catalog=PROMPT_CATALOG,
        prompt_limit=6,
        budget_usd=100,
        out_dir="reports/free_api_prompt_eval/openrouter_paid_test",
        prompt_file=str(tmp_path / "selected_prompts.jsonl"),
        result_paths=[],
    )

    planner.write_plan(plan, tmp_path)

    selected = (tmp_path / "selected_prompts.jsonl").read_text(encoding="utf-8").strip().splitlines()
    critical = (tmp_path / "critical_prompts.jsonl").read_text(encoding="utf-8").strip().splitlines()
    arbiter = (tmp_path / "arbiter_prompts.jsonl").read_text(encoding="utf-8").strip().splitlines()

    assert len(selected) == len(plan["selected_prompts"])
    assert len(critical) == len(plan["critical_prompt_ids"])
    assert len(arbiter) == len(plan["arbiter_prompt_ids"])
