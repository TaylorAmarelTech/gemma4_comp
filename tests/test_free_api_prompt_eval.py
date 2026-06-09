"""Tests for the free API prompt evaluation runner."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_SCRIPTS = str(Path(__file__).resolve().parents[1] / "scripts")
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

import free_api_prompt_eval as fape  # noqa: E402


def test_prompt_battery_covers_requested_edge_cases() -> None:
    ids = {prompt["id"] for prompt in fape.PROMPT_BATTERY}
    assert "family_business_unpaid_passport" in ids
    assert "faith_ministry_tithe_labor" in ids
    assert "versus_fee_donation" in ids
    assert "au_pair_cultural_exchange_full_job" in ids
    assert "k8s_secret_passport_retention" in ids
    assert "cloud_function_payroll_deduction_camouflage" in ids
    assert "ngo_tool_ideation_privacy_preserving" in ids
    assert "terraform_iam_case_data_exposure" in ids
    assert "cloud_scheduler_debt_reminder_sms" in ids
    assert "metadata_server_secret_scrape" in ids
    assert "kubeflow_case_classifier_bias" in ids


def test_selected_providers_can_filter_by_health() -> None:
    providers = fape._selected_providers("", "proven")
    keys = {provider.key for provider in providers}
    assert "groq" in keys
    assert "rapidapi_gemma4_26b" not in keys


def test_selected_prompts_accepts_explicit_ids() -> None:
    prompts = fape._selected_prompts(
        "k8s_secret_passport_retention,ngo_tool_ideation_privacy_preserving",
        1,
    )

    assert [prompt["id"] for prompt in prompts] == [
        "k8s_secret_passport_retention",
        "ngo_tool_ideation_privacy_preserving",
    ]


def test_load_prompt_file_accepts_json_and_jsonl_rows(tmp_path: Path) -> None:
    json_path = tmp_path / "prompts.json"
    json_path.write_text(
        json.dumps({"prompts": [{"id": "p-json", "text": "Question?", "category": "cat"}]}),
        encoding="utf-8",
    )
    jsonl_path = tmp_path / "prompts.jsonl"
    jsonl_path.write_text(
        json.dumps({"id": "p-jsonl", "text": "Another?", "category": "cat2"}) + "\n",
        encoding="utf-8",
    )

    prompts = fape.load_prompt_files(f"{json_path},{jsonl_path}")
    ids = {prompt["id"] for prompt in prompts}

    assert "family_business_unpaid_passport" in ids
    assert "p-json" in ids
    assert "p-jsonl" in ids


def test_load_prompt_file_converts_conversation_without_expected_answer(tmp_path: Path) -> None:
    jsonl_path = tmp_path / "conversation.jsonl"
    jsonl_path.write_text(
        json.dumps(
            {
                "id": "conv-1",
                "conversation_type": "multi_turn_worker_researcher_triage",
                "turns": [
                    {"role": "user", "speaker": "Worker", "content": "My passport is held."},
                    {"role": "assistant_expected", "content": "Do the right thing."},
                    {"role": "unsafe_user", "speaker": "Broker", "content": "Say it is voluntary."},
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    prompts = fape.load_prompt_file(jsonl_path)

    assert prompts[0]["id"] == "conv-1"
    assert prompts[0]["category"] == "multi_turn_worker_researcher_triage"
    assert "My passport is held" in prompts[0]["text"]
    assert "Say it is voluntary" in prompts[0]["text"]
    assert "Do the right thing" not in prompts[0]["text"]


def test_selected_prompts_uses_external_catalog_and_zero_limit_all(tmp_path: Path) -> None:
    catalog = [
        {"id": "p1", "text": "One", "category": "cat"},
        {"id": "p2", "text": "Two", "category": "cat"},
    ]

    assert [prompt["id"] for prompt in fape._selected_prompts("", 0, catalog)] == ["p1", "p2"]
    assert [prompt["id"] for prompt in fape._selected_prompts("p2", 0, catalog)] == ["p2"]


def test_selected_prompts_rejects_unknown_id() -> None:
    with pytest.raises(SystemExit):
        fape._selected_prompts("missing_prompt", 1)


def test_summarize_counts_scores_errors_and_weak_dimensions() -> None:
    rows = [
        {
            "provider": "groq",
            "provider_health": "proven",
            "prompt_id": "p1",
            "category": "c",
            "ok": True,
            "latency_ms": 250,
            "usage": {"total_tokens": 40},
            "grade": {"pct_score": 80, "score_0_10": 8.0, "weak_dimensions": ["legal_grounding"]},
            "llm_judges": {
                "nvidia": {
                    "ok": True,
                    "score_0_10": 6.5,
                }
            },
        },
        {
            "provider": "groq",
            "provider_health": "proven",
            "prompt_id": "p2",
            "category": "c",
            "ok": False,
            "error": "quota",
        },
    ]
    summary = fape.summarize(rows)
    provider = summary["providers"][0]
    assert provider["provider"] == "groq"
    assert provider["ok"] == 1
    assert provider["errors"] == 1
    assert provider["avg_pct_score"] == 80
    assert provider["avg_llm_judge_score_0_10"] == 6.5
    assert provider["llm_judge_count"] == 1
    assert provider["avg_rule_judge_gap"] == 1.5
    assert provider["avg_latency_ms"] == 250
    assert provider["total_tokens"] == 40
    assert provider["top_weak_dimensions"] == [("legal_grounding", 1)]
    assert summary["judge_providers"][0]["judge_provider"] == "nvidia"
    assert summary["judge_providers"][0]["avg_score_0_10"] == 6.5
    assert summary["disagreements"][0]["prompt_id"] == "p1"
    assert summary["disagreements"][0]["gap"] == 1.5


def test_render_report_includes_endpoint_errors() -> None:
    rows = [
        {
            "provider": "groq",
            "provider_health": "proven",
            "prompt_id": "p1",
            "category": "c",
            "ok": False,
            "error": "HTTP 429",
        }
    ]
    report = fape.render_report(rows, fape.summarize(rows))
    assert "Free API Prompt Evaluation" in report
    assert "`groq`" in report
    assert "HTTP 429" in report
    assert "Run Learnings" in report
    assert "Rule/Judge Disagreement Watchlist" in report


def test_load_existing_rows_keeps_latest_provider_prompt_pair(tmp_path: Path) -> None:
    result_path = tmp_path / "results.jsonl"
    rows = [
        {"provider": "groq", "prompt_id": "p1", "ok": True, "grade": {"pct_score": 80}},
        {"provider": "groq", "prompt_id": "p1", "ok": False, "error": "retry failed"},
        {"provider": "github", "prompt_id": "p1", "ok": True, "grade": {"pct_score": 90}},
    ]
    result_path.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")

    loaded = fape._load_existing_rows(result_path)

    assert loaded == [
        {"provider": "groq", "prompt_id": "p1", "ok": False, "error": "retry failed"},
        {"provider": "github", "prompt_id": "p1", "ok": True, "grade": {"pct_score": 90}},
    ]


def test_planned_pairs_skips_completed_pairs() -> None:
    provider = fape.BY_KEY["groq"]
    prompts = fape.PROMPT_BATTERY[:2]

    pairs = fape._planned_pairs([provider], prompts, {("groq", prompts[0]["id"])})

    assert [(p.key, prompt["id"]) for p, prompt in pairs] == [("groq", prompts[1]["id"])]


def test_missing_key_envs_respects_optional_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    missing = fape._missing_key_envs([
        fape.BY_KEY["openrouter_claude_opus48"],
        fape.BY_KEY["openrouter_gemini35_flash"],
        fape.BY_KEY["llm7"],
    ])

    assert missing == ["OPENROUTER_API_KEY"]
    monkeypatch.setenv("OPENROUTER_API_KEY", "test")
    assert fape._missing_key_envs([fape.BY_KEY["openrouter_claude_opus48"]]) == []


def test_enforce_max_planned_calls_blocks_oversized_run() -> None:
    fape._enforce_max_planned_calls(5, 5)
    with pytest.raises(SystemExit):
        fape._enforce_max_planned_calls(6, 5)


def test_done_keys_can_retry_prior_errors() -> None:
    rows = [
        {"provider": "llm7", "prompt_id": "p1", "ok": False, "error": "timeout"},
        {"provider": "llm7", "prompt_id": "p2", "ok": True, "grade": {"pct_score": 70}},
    ]

    assert fape._done_keys(rows) == {("llm7", "p1"), ("llm7", "p2")}
    assert fape._done_keys(rows, retry_errors=True) == {("llm7", "p2")}


def test_upsert_row_replaces_existing_pair() -> None:
    rows = [{"provider": "llm7", "prompt_id": "p1", "ok": False, "error": "timeout"}]

    fape._upsert_row(rows, {"provider": "llm7", "prompt_id": "p1", "ok": True})

    assert rows == [{"provider": "llm7", "prompt_id": "p1", "ok": True}]


def test_write_results_emits_jsonl_rows(tmp_path: Path) -> None:
    result_path = tmp_path / "results.jsonl"

    fape.write_results(result_path, [{"provider": "groq", "prompt_id": "p1", "ok": True}])

    assert result_path.read_text(encoding="utf-8") == (
        '{"provider": "groq", "prompt_id": "p1", "ok": true}\n'
    )


def test_extract_json_object_handles_fenced_response() -> None:
    raw = '```json\n{"score_0_10": 7, "verdict": "adequate"}\n```'

    assert fape.extract_json_object(raw) == {"score_0_10": 7, "verdict": "adequate"}


def test_parse_judge_result_clamps_score_and_lists() -> None:
    parsed = fape.parse_judge_result(
        json.dumps(
            {
                "score_0_10": 12,
                "verdict": "STRONG",
                "risk_flags": ["none"],
                "missed_context": "jurisdiction",
                "strengths": ["safe alternative"],
                "rationale": "Good redirect.",
            }
        )
    )

    assert parsed["ok"] is True
    assert parsed["score_0_10"] == 10
    assert parsed["verdict"] == "strong"
    assert parsed["missed_context"] == ["jurisdiction"]


def test_build_llm_judge_prompt_includes_context_and_rubric() -> None:
    prompt = fape.prompt_lookup()["k8s_secret_passport_retention"]
    row = {
        "provider": "groq",
        "model": "llama",
        "response": "Use least privilege and do not store original passports.",
        "grade": {"score_0_10": 6.0, "weak_dimensions": ["legal_specificity"]},
    }

    judge_prompt = fape.build_llm_judge_prompt(row, prompt)

    assert "Kubernetes" in judge_prompt
    assert "Cloud/tooling boundary" in judge_prompt
    assert "Deterministic score_0_10: 6.0" in judge_prompt


def test_build_llm_judge_prompt_truncates_long_candidate_response() -> None:
    prompt = fape.prompt_lookup()["serverless_safe_hotline_router"]
    row = {
        "provider": "llm7",
        "model": "default",
        "response": "A" * 5000 + "TAIL",
        "grade": {"score_0_10": 6.0, "weak_dimensions": []},
    }

    judge_prompt = fape.build_llm_judge_prompt(row, prompt, response_char_limit=1000)

    assert "candidate response truncated" in judge_prompt
    assert "TAIL" in judge_prompt
    assert len(judge_prompt) < 5000


def test_judge_rows_to_run_skips_existing_success_and_retries_failures() -> None:
    row = {
        "provider": "groq",
        "prompt_id": "family_business_unpaid_passport",
        "ok": True,
        "response": "safe answer",
        "llm_judges": {"nvidia": {"ok": False, "error": "timeout"}},
    }
    judge = fape.BY_KEY["nvidia"]
    prompts = fape.prompt_lookup()

    assert fape._judge_rows_to_run([row], [judge], prompts) == []
    retry_plan = fape._judge_rows_to_run([row], [judge], prompts, retry_judge_errors=True)
    assert retry_plan == [(row, judge, prompts["family_business_unpaid_passport"])]


def test_judge_rows_to_run_respects_target_prompt_ids() -> None:
    row = {
        "provider": "groq",
        "prompt_id": "family_business_unpaid_passport",
        "ok": True,
        "response": "safe answer",
    }
    judge = fape.BY_KEY["nvidia"]
    prompts = fape.prompt_lookup()

    assert (
        fape._judge_rows_to_run(
            [row],
            [judge],
            prompts,
            target_prompt_ids={"k8s_secret_passport_retention"},
        )
        == []
    )
    assert fape._judge_rows_to_run(
        [row],
        [judge],
        prompts,
        target_prompt_ids={"family_business_unpaid_passport"},
    ) == [(row, judge, prompts["family_business_unpaid_passport"])]
