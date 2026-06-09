"""Plan a paid OpenRouter evaluation from prior free-endpoint evidence.

This script does not call OpenRouter. It reads existing free/freemium benchmark
JSONL files, ranks prompt coverage, proposes a candidate/judge model mix, and
writes a JSON + Markdown plan that can be reviewed before spending credits.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from free_api_prompt_eval import load_prompt_files  # noqa: E402


OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"
STATIC_PRICING_SOURCE = "static OpenRouter model catalog snapshot checked on 2026-06-09"

OPENROUTER_MODEL_ROSTER: dict[str, dict[str, Any]] = {
    # Pricing values are USD per token from the OpenRouter model catalog snapshot
    # checked on 2026-06-09. Refresh against /api/v1/models before spending.
    "openrouter_claude_opus48": {
        "model": "anthropic/claude-opus-4.8",
        "role": "frontier_candidate_and_critical_judge",
        "prompt_cost": 0.000005,
        "completion_cost": 0.000025,
    },
    "openrouter_gemini35_flash": {
        "model": "google/gemini-3.5-flash",
        "role": "broad_candidate_and_primary_judge",
        "prompt_cost": 0.0000015,
        "completion_cost": 0.000009,
    },
    "openrouter_grok43": {
        "model": "x-ai/grok-4.3",
        "role": "fast_reasoning_candidate_and_arbiter",
        "prompt_cost": 0.00000125,
        "completion_cost": 0.0000025,
    },
    "openrouter_nemotron_ultra": {
        "model": "nvidia/nemotron-3-ultra-550b-a55b",
        "role": "low_cost_large_candidate",
        "prompt_cost": 0.0000005,
        "completion_cost": 0.0000025,
    },
    "openrouter_qwen37max": {
        "model": "qwen/qwen3.7-max",
        "role": "cost_effective_agentic_candidate",
        "prompt_cost": 0.00000125,
        "completion_cost": 0.00000375,
    },
    "openrouter_qwen37plus": {
        "model": "qwen/qwen3.7-plus",
        "role": "recent_low_cost_multimodal_candidate",
        "prompt_cost": 0.0000004,
        "completion_cost": 0.0000016,
    },
}

COMPARISON_CANDIDATE_PROVIDERS = [
    "openrouter_claude_opus48",
    "openrouter_gemini35_flash",
    "openrouter_grok43",
    "openrouter_nemotron_ultra",
]
DEFAULT_CANDIDATE_PROVIDERS = ["openrouter_nemotron_ultra"]
DEFAULT_PRIMARY_JUDGES = ["openrouter_gemini35_flash"]
DEFAULT_CRITICAL_JUDGES = ["openrouter_claude_opus48"]
DEFAULT_ARBITER_JUDGES = ["openrouter_grok43"]

DEFAULT_PROMPT_SOURCES = [
    REPO / "configs/duecare/benchmarks/harness_lift_prompts_500.json",
    REPO / "configs/duecare/benchmarks/harness_lift_prompts_expansion.jsonl",
    REPO / "configs/duecare/benchmarks/harness_lift_prompt_mix_expansion.jsonl",
]

BUCKET_MIX = {
    "harm_stress": 0.34,
    "legal_grounding_corridor": 0.24,
    "relationship_semantic": 0.18,
    "safe_tool_regression": 0.14,
    "coverage_gap": 0.08,
    "rule_calibration": 0.02,
}
BUCKET_MAX_SHARE = {
    "harm_stress": 0.40,
    "legal_grounding_corridor": 0.32,
    "relationship_semantic": 0.24,
    "safe_tool_regression": 0.18,
    "coverage_gap": 0.16,
    "rule_calibration": 0.08,
}

RELATIONSHIP_CATEGORIES = {
    "family_relationship",
    "faith_relationship",
    "versus_edge_case",
    "semantic_ambiguity",
    "status_laundering",
    "training_status",
    "victim_safety",
    "coercion_family_pressure",
    "justification_religious",
    "religious_justification",
    "moral_religious_biblical",
    "moral_religious_cultural",
    "moral_religious_duty_honor",
    "moral_religious_framing",
    "moral_religious_philosophical",
    "benevolent_framing",
    "mixed_persona",
    "persuasion_style",
    "justification_authority",
    "justification_destitution",
}
SAFE_TOOL_CATEGORIES = {
    "defensive_cloud_tooling",
    "safe_tool_ideation",
    "cloud_iam_tooling",
}
HIGH_RISK_TOOL_CATEGORIES = {
    "cloud_function_tooling",
    "cloud_k8s_tooling",
    "cloud_security_boundary",
    "ci_cd_tooling",
    "mlops_tooling",
    "movement_restriction",
    "document_retention",
    "adversarial",
    "base_harmful",
    "business_framed_exploitation",
    "combined_attack",
    "pretext_jailbreak",
    "override_jailbreak",
    "evasion_probe",
    "false_legitimacy",
    "relabeling",
    "predatory_norm",
    "scam_compound",
    "contract_substitution",
    "financial_obfuscation",
    "multi-entity fee laundering",
    "circular debt structures",
    "franchise exploitation networks",
    "integrated service complexes",
    "coercion_document_confiscation",
}
LEGAL_GROUNDING_CATEGORIES = {
    "agency_compliance",
    "agency_legal_question",
    "legal_accuracy",
    "legal_provisions",
    "corridor_specific",
    "rights_query",
    "verification_query",
    "worker_query",
    "worker_mixed",
    "bystander_dilemma",
    "investigative_case",
    "sector_scenario",
    "jurisdictional_hierarchy",
    "jurisdictional_hierarchy_exploitation",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise SystemExit(f"Invalid JSONL in {path} line {line_no}: {exc}") from exc
            if isinstance(row, dict):
                rows.append(row)
    return rows


def discover_result_paths(report_root: Path) -> list[Path]:
    if report_root.is_file():
        return [report_root]
    return sorted(path for path in report_root.glob("*/results.jsonl") if path.exists())


def load_rows(paths: list[Path]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in paths:
        for row in load_jsonl(path):
            row.setdefault("_source_path", str(path))
            rows.append(row)
    return rows


def parse_provider_keys(value: str, default: list[str]) -> list[str]:
    keys = [item.strip() for item in value.split(",") if item.strip()] if value else list(default)
    missing = [key for key in keys if key not in OPENROUTER_MODEL_ROSTER]
    if missing:
        raise SystemExit(f"Unknown OpenRouter provider key(s): {', '.join(missing)}")
    return keys


def _float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def fetch_openrouter_model_catalog(url: str = OPENROUTER_MODELS_URL, timeout: int = 30) -> list[dict[str, Any]]:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "DueCare-Eval-Planner/1.0"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    rows = data.get("data") if isinstance(data, dict) else None
    if not isinstance(rows, list):
        raise SystemExit("OpenRouter model catalog response did not contain a data list")
    return [row for row in rows if isinstance(row, dict)]


def refresh_model_roster_from_catalog(
    roster: dict[str, dict[str, Any]],
    catalog_rows: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    by_model_id = {
        str(row.get("id")): row
        for row in catalog_rows
        if row.get("id") is not None
    }
    missing: list[str] = []
    invalid_pricing: list[str] = []
    refreshed: dict[str, dict[str, Any]] = {}
    for provider_key, model in roster.items():
        model_id = str(model["model"])
        catalog_row = by_model_id.get(model_id)
        if not catalog_row:
            missing.append(model_id)
            continue
        pricing = catalog_row.get("pricing")
        pricing = pricing if isinstance(pricing, dict) else {}
        prompt_cost = _float(pricing.get("prompt"))
        completion_cost = _float(pricing.get("completion"))
        if (
            prompt_cost is None
            or completion_cost is None
            or prompt_cost < 0
            or completion_cost < 0
        ):
            invalid_pricing.append(model_id)
            continue
        updated = dict(model)
        updated["prompt_cost"] = prompt_cost
        updated["completion_cost"] = completion_cost
        updated["openrouter_context_length"] = catalog_row.get("context_length")
        top_provider = catalog_row.get("top_provider")
        if isinstance(top_provider, dict):
            updated["openrouter_max_completion_tokens"] = top_provider.get("max_completion_tokens")
        refreshed[provider_key] = updated
    if missing or invalid_pricing:
        parts: list[str] = []
        if missing:
            parts.append("missing model id(s): " + ", ".join(missing))
        if invalid_pricing:
            parts.append("invalid pricing for model id(s): " + ", ".join(invalid_pricing))
        raise SystemExit("; ".join(parts))
    return refreshed


def _avg(values: list[float]) -> float | None:
    return round(sum(values) / len(values), 2) if values else None


def _judge_scores(row: dict[str, Any]) -> list[float]:
    judges = row.get("llm_judges", {})
    if not isinstance(judges, dict):
        return []
    out: list[float] = []
    for judgment in judges.values():
        if not isinstance(judgment, dict) or not judgment.get("ok"):
            continue
        score = _float(judgment.get("score_0_10"))
        if score is not None:
            out.append(score)
    return out


def _judge_flags(row: dict[str, Any]) -> list[str]:
    judges = row.get("llm_judges", {})
    if not isinstance(judges, dict):
        return []
    flags: list[str] = []
    for judgment in judges.values():
        if not isinstance(judgment, dict) or not judgment.get("ok"):
            continue
        raw_flags = judgment.get("risk_flags")
        if isinstance(raw_flags, list):
            flags.extend(str(flag)[:160] for flag in raw_flags if flag)
    return flags


def _judge_verdicts(row: dict[str, Any]) -> list[str]:
    judges = row.get("llm_judges", {})
    if not isinstance(judges, dict):
        return []
    verdicts: list[str] = []
    for judgment in judges.values():
        if isinstance(judgment, dict) and judgment.get("ok") and judgment.get("verdict"):
            verdicts.append(str(judgment["verdict"])[:48])
    return verdicts


def _max_rule_judge_gap(rows: list[dict[str, Any]]) -> float:
    gaps: list[float] = []
    for row in rows:
        rule = _float(row.get("grade", {}).get("score_0_10"))
        judge_scores = _judge_scores(row)
        if rule is not None and judge_scores:
            gaps.append(abs(rule - (sum(judge_scores) / len(judge_scores))))
    return round(max(gaps), 2) if gaps else 0.0


def classify_bucket(item: dict[str, Any]) -> str:
    category = str(item["category"])
    min_judge = item.get("min_llm_judge_score_0_10")
    if (min_judge is not None and min_judge < 5.0) or item["risk_flags"]:
        return "harm_stress"
    if category in RELATIONSHIP_CATEGORIES:
        return "relationship_semantic"
    if category in SAFE_TOOL_CATEGORIES:
        return "safe_tool_regression"
    if category in LEGAL_GROUNDING_CATEGORIES:
        return "legal_grounding_corridor"
    if item["max_rule_judge_gap"] >= 2.5:
        return "rule_calibration"
    if category in HIGH_RISK_TOOL_CATEGORIES:
        return "harm_stress"
    if item["judge_count"] == 0 or item["candidate_count"] == 0:
        return "coverage_gap"
    return "rule_calibration"


def priority_score(item: dict[str, Any]) -> float:
    category = str(item["category"])
    min_judge = item.get("min_llm_judge_score_0_10")
    avg_rule = item.get("avg_rule_score_0_10")
    score = 0.0
    if min_judge is not None:
        score += max(0.0, 5.0 - min_judge) * 16.0
        score += max(0.0, 9.0 - min_judge) * 2.0
    else:
        score += 18.0
    score += min(30.0, item["max_rule_judge_gap"] * 7.5)
    score += min(18.0, len(item["risk_flags"]) * 4.0)
    if avg_rule is not None and avg_rule < 5.5:
        score += (5.5 - avg_rule) * 4.0
    if item["judge_count"] == 0:
        score += 14.0
    if category in HIGH_RISK_TOOL_CATEGORIES:
        score += 11.0
    if category in RELATIONSHIP_CATEGORIES:
        score += 9.0
    if category in SAFE_TOOL_CATEGORIES:
        score += 5.0
    return round(score, 2)


def aggregate_prompts(
    rows: list[dict[str, Any]],
    prompt_catalog: list[dict[str, str]],
) -> list[dict[str, Any]]:
    by_prompt: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        prompt_id = row.get("prompt_id")
        if isinstance(prompt_id, str):
            by_prompt[prompt_id].append(row)

    items: list[dict[str, Any]] = []
    for prompt in prompt_catalog:
        prompt_id = prompt["id"]
        prompt_rows = by_prompt.get(prompt_id, [])
        ok_rows = [row for row in prompt_rows if row.get("ok")]
        rule_scores = [
            score
            for row in ok_rows
            if (score := _float(row.get("grade", {}).get("score_0_10"))) is not None
        ]
        judge_scores = [score for row in ok_rows for score in _judge_scores(row)]
        flags = [flag for row in ok_rows for flag in _judge_flags(row)]
        verdicts = [verdict for row in ok_rows for verdict in _judge_verdicts(row)]
        item = {
            "prompt_id": prompt_id,
            "category": prompt["category"],
            "text": prompt["text"],
            "candidate_count": len(ok_rows),
            "error_count": len(prompt_rows) - len(ok_rows),
            "providers": sorted({str(row.get("provider")) for row in ok_rows if row.get("provider")}),
            "avg_rule_score_0_10": _avg(rule_scores),
            "avg_llm_judge_score_0_10": _avg(judge_scores),
            "min_llm_judge_score_0_10": round(min(judge_scores), 2) if judge_scores else None,
            "judge_count": len(judge_scores),
            "max_rule_judge_gap": _max_rule_judge_gap(ok_rows),
            "risk_flags": sorted(set(flags))[:8],
            "verdicts": sorted(set(verdicts)),
        }
        item["bucket"] = classify_bucket(item)
        item["priority_score"] = priority_score(item)
        item["why"] = explain_priority(item)
        items.append(item)
    return sorted(items, key=lambda item: (-item["priority_score"], item["prompt_id"]))


def explain_priority(item: dict[str, Any]) -> str:
    reasons: list[str] = []
    if item["risk_flags"]:
        reasons.append("LLM judge risk flags")
    min_judge = item.get("min_llm_judge_score_0_10")
    if min_judge is not None and min_judge < 5.0:
        reasons.append(f"low judge score {min_judge:.1f}")
    if item["max_rule_judge_gap"] >= 2.5:
        reasons.append(f"rule/judge gap {item['max_rule_judge_gap']:.1f}")
    if item["judge_count"] == 0:
        reasons.append("needs paid judge coverage")
    if item["category"] in RELATIONSHIP_CATEGORIES:
        reasons.append("relationship/semantic edge case")
    if item["category"] in SAFE_TOOL_CATEGORIES:
        reasons.append("safe-tool positive control")
    return "; ".join(reasons) or "balanced regression coverage"


def select_prompt_plan(items: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    if limit <= 0:
        return []
    by_bucket: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in items:
        by_bucket[item["bucket"]].append(item)
    selected: list[dict[str, Any]] = []
    selected_ids: set[str] = set()
    bucket_counts: Counter[str] = Counter()
    bucket_caps = {
        bucket: max(1, int(round(limit * share)))
        for bucket, share in BUCKET_MAX_SHARE.items()
    }

    def add_item(item: dict[str, Any], *, enforce_cap: bool) -> bool:
        bucket = str(item["bucket"])
        if item["prompt_id"] in selected_ids:
            return False
        if enforce_cap and bucket_counts[bucket] >= bucket_caps.get(bucket, limit):
            return False
        selected.append(item)
        selected_ids.add(item["prompt_id"])
        bucket_counts[bucket] += 1
        return True

    def category_balanced_order(bucket_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        by_category: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for item in bucket_items:
            by_category[str(item["category"])].append(item)
        categories = sorted(
            by_category,
            key=lambda category: (-by_category[category][0]["priority_score"], category),
        )
        positions = {category: 0 for category in categories}
        ordered: list[dict[str, Any]] = []
        while True:
            progressed = False
            for category in categories:
                position = positions[category]
                category_items = by_category[category]
                if position >= len(category_items):
                    continue
                ordered.append(category_items[position])
                positions[category] = position + 1
                progressed = True
            if not progressed:
                return ordered

    for bucket, share in BUCKET_MIX.items():
        bucket_items = by_bucket.get(bucket, [])
        if not bucket_items:
            continue
        quota = max(1, int(round(limit * share)))
        for item in category_balanced_order(bucket_items):
            if len(selected) >= limit:
                break
            if bucket_counts[bucket] >= quota:
                break
            add_item(item, enforce_cap=True)
    if len(selected) < limit:
        for item in items:
            add_item(item, enforce_cap=True)
            if len(selected) >= limit:
                break
    if len(selected) < limit:
        for item in items:
            add_item(item, enforce_cap=False)
            if len(selected) >= limit:
                break
    return sorted(selected, key=lambda item: (-item["priority_score"], item["prompt_id"]))


def estimate_tokens_for_prompt(prompt_text: str) -> int:
    return max(80, math.ceil((len(prompt_text) + 900) / 4))


def model_cost(provider_key: str, prompt_tokens: int, completion_tokens: int) -> float:
    model = OPENROUTER_MODEL_ROSTER[provider_key]
    return (
        prompt_tokens * float(model["prompt_cost"])
        + completion_tokens * float(model["completion_cost"])
    )


def estimate_costs(
    prompts: list[dict[str, Any]],
    candidate_providers: list[str],
    primary_judges: list[str],
    critical_judges: list[str],
    arbiter_judges: list[str],
    *,
    candidate_max_tokens: int,
    judge_input_tokens: int,
    judge_max_tokens: int,
) -> dict[str, Any]:
    candidate_calls = len(prompts) * len(candidate_providers)
    critical_prompts = [
        item for item in prompts if item["bucket"] in {"harm_stress", "rule_calibration"}
    ]
    primary_judge_calls = candidate_calls * len(primary_judges)
    critical_judge_calls = len(critical_prompts) * len(candidate_providers) * len(critical_judges)
    arbiter_prompt_count = len([item for item in critical_prompts if item["priority_score"] >= 45.0])
    arbiter_calls = arbiter_prompt_count * len(candidate_providers) * len(arbiter_judges)

    line_items: list[dict[str, Any]] = []
    for provider in candidate_providers:
        cost = sum(
            model_cost(
                provider,
                estimate_tokens_for_prompt(item["text"]),
                candidate_max_tokens,
            )
            for item in prompts
        )
        line_items.append({
            "phase": "candidate",
            "provider": provider,
            "calls": len(prompts),
            "estimated_cost_usd": round(cost, 4),
        })

    for judge in primary_judges:
        calls = candidate_calls
        cost = calls * model_cost(judge, judge_input_tokens, judge_max_tokens)
        line_items.append({
            "phase": "primary_judge",
            "provider": judge,
            "calls": calls,
            "estimated_cost_usd": round(cost, 4),
        })
    for judge in critical_judges:
        calls = len(critical_prompts) * len(candidate_providers)
        cost = calls * model_cost(judge, judge_input_tokens, judge_max_tokens)
        line_items.append({
            "phase": "critical_second_judge",
            "provider": judge,
            "calls": calls,
            "estimated_cost_usd": round(cost, 4),
        })
    for judge in arbiter_judges:
        calls = arbiter_prompt_count * len(candidate_providers)
        cost = calls * model_cost(judge, judge_input_tokens, judge_max_tokens)
        line_items.append({
            "phase": "arbiter_judge",
            "provider": judge,
            "calls": calls,
            "estimated_cost_usd": round(cost, 4),
        })
    total = round(sum(float(item["estimated_cost_usd"]) for item in line_items), 4)
    return {
        "candidate_calls": candidate_calls,
        "primary_judge_calls": primary_judge_calls,
        "critical_second_judge_calls": critical_judge_calls,
        "arbiter_judge_calls": arbiter_calls,
        "total_calls": candidate_calls + primary_judge_calls + critical_judge_calls + arbiter_calls,
        "estimated_cost_usd": total,
        "line_items": line_items,
    }


def phase_call_counts(costs: dict[str, Any]) -> dict[str, int]:
    return {
        "candidate": int(costs["candidate_calls"]),
        "primary_judge": int(costs["primary_judge_calls"]),
        "critical_second_judge": int(costs["critical_second_judge_calls"]),
        "arbiter_judge": int(costs["arbiter_judge_calls"]),
    }


def sibling_prompt_file(prompt_file: str, file_name: str) -> str:
    normalized = prompt_file.replace("\\", "/")
    if "/" not in normalized:
        return file_name
    return f"{normalized.rsplit('/', 1)[0]}/{file_name}"


def command_block(
    out_dir: str,
    prompt_file: str,
    critical_prompt_file: str,
    arbiter_prompt_file: str,
    candidate_providers: list[str],
    primary_judges: list[str],
    critical_judges: list[str],
    arbiter_judges: list[str],
    critical_prompt_ids: list[str],
    arbiter_prompt_ids: list[str],
    phase_counts: dict[str, int],
) -> dict[str, str]:
    provider_arg = ",".join(candidate_providers)
    commands = {
        "candidate": (
            "python scripts\\free_api_prompt_eval.py "
            f"--providers {provider_arg} --prompt-file {prompt_file} --out-dir {out_dir} "
            f"--max-planned-calls {phase_counts['candidate']} "
            "--max-tokens 700 --timeout 240 --sleep 0.5 --resume --fail-on-missing-keys "
            "--retry-errors --compact-results"
        ),
        "primary_judge": (
            "python scripts\\free_api_prompt_eval.py "
            f"--providers {provider_arg} --prompt-file {prompt_file} --out-dir {out_dir} "
            f"--max-planned-calls {phase_counts['primary_judge']} "
            f"--judge-only --judge-providers {','.join(primary_judges)} "
            "--judge-timeout 240 --judge-max-tokens 900 --judge-response-char-limit 3500 "
            "--resume --fail-on-missing-keys "
            "--retry-judge-errors --judge-sleep 2 --compact-results"
        ),
    }
    if critical_prompt_ids:
        commands["critical_second_judge"] = (
            "python scripts\\free_api_prompt_eval.py "
            f"--providers {provider_arg} --prompt-file {critical_prompt_file} --out-dir {out_dir} "
            f"--max-planned-calls {phase_counts['critical_second_judge']} "
            f"--judge-only --judge-providers {','.join(critical_judges)} "
            "--judge-timeout 300 --judge-max-tokens 1000 --judge-response-char-limit 4200 "
            "--resume --fail-on-missing-keys "
            "--retry-judge-errors --judge-sleep 2 --compact-results"
        )
    if arbiter_prompt_ids:
        commands["arbiter_judge"] = (
            "python scripts\\free_api_prompt_eval.py "
            f"--providers {provider_arg} --prompt-file {arbiter_prompt_file} --out-dir {out_dir} "
            f"--max-planned-calls {phase_counts['arbiter_judge']} "
            f"--judge-only --judge-providers {','.join(arbiter_judges)} "
            "--judge-timeout 300 --judge-max-tokens 1000 --judge-response-char-limit 4200 "
            "--resume --fail-on-missing-keys "
            "--retry-judge-errors --judge-sleep 2 --compact-results"
        )
    return commands


def preflight_command_block(commands: dict[str, str]) -> dict[str, str]:
    return {phase: f"{command} --dry-run" for phase, command in commands.items()}


def build_plan(
    rows: list[dict[str, Any]],
    *,
    prompt_catalog: list[dict[str, str]],
    prompt_limit: int,
    budget_usd: float,
    out_dir: str,
    prompt_file: str,
    result_paths: list[Path],
    candidate_providers: list[str] | None = None,
    primary_judges: list[str] | None = None,
    critical_judges: list[str] | None = None,
    arbiter_judges: list[str] | None = None,
    pricing_source: str = STATIC_PRICING_SOURCE,
    pricing_refreshed_at: str | None = None,
) -> dict[str, Any]:
    candidate_providers = candidate_providers or DEFAULT_CANDIDATE_PROVIDERS
    primary_judges = primary_judges or DEFAULT_PRIMARY_JUDGES
    critical_judges = critical_judges or DEFAULT_CRITICAL_JUDGES
    arbiter_judges = arbiter_judges or DEFAULT_ARBITER_JUDGES
    items = aggregate_prompts(rows, prompt_catalog)
    selected = select_prompt_plan(items, prompt_limit)
    critical_prompt_file = sibling_prompt_file(prompt_file, "critical_prompts.jsonl")
    arbiter_prompt_file = sibling_prompt_file(prompt_file, "arbiter_prompts.jsonl")
    critical_prompt_ids = [
        item["prompt_id"] for item in selected if item["bucket"] in {"harm_stress", "rule_calibration"}
    ]
    arbiter_prompt_ids = [
        item["prompt_id"]
        for item in selected
        if item["bucket"] == "harm_stress" or item["priority_score"] >= 45.0
    ]
    costs = estimate_costs(
        selected,
        candidate_providers,
        primary_judges,
        critical_judges,
        arbiter_judges,
        candidate_max_tokens=700,
        judge_input_tokens=2200,
        judge_max_tokens=900,
    )
    phase_counts = phase_call_counts(costs)
    commands = command_block(
        out_dir,
        prompt_file,
        critical_prompt_file,
        arbiter_prompt_file,
        candidate_providers,
        primary_judges,
        critical_judges,
        arbiter_judges,
        critical_prompt_ids,
        arbiter_prompt_ids,
        phase_counts,
    )
    return {
        "generated_at": utc_now(),
        "source_result_paths": [str(path) for path in result_paths],
        "prompt_catalog_count": len(prompt_catalog),
        "budget_usd": budget_usd,
        "budget_note": budget_note(costs["estimated_cost_usd"], budget_usd),
        "pricing_source": pricing_source,
        "pricing_refreshed_at": pricing_refreshed_at,
        "model_roster": OPENROUTER_MODEL_ROSTER,
        "candidate_providers": candidate_providers,
        "primary_judges": primary_judges,
        "critical_judges": critical_judges,
        "arbiter_judges": arbiter_judges,
        "selected_prompt_file": prompt_file,
        "critical_prompt_file": critical_prompt_file,
        "arbiter_prompt_file": arbiter_prompt_file,
        "selected_prompts": selected,
        "critical_prompt_ids": critical_prompt_ids,
        "arbiter_prompt_ids": arbiter_prompt_ids,
        "bucket_counts": dict(Counter(item["bucket"] for item in selected)),
        "phase_call_counts": phase_counts,
        "cost_estimate": costs,
        "preflight_commands": preflight_command_block(commands),
        "commands": commands,
    }


def budget_note(estimated: float, budget: float) -> str:
    if budget <= 0:
        return "No budget ceiling supplied."
    pct = estimated / budget
    if pct <= 0.2:
        return "Plan is a conservative first tranche; leave the rest for retries and broader coverage."
    if pct <= 0.75:
        return "Plan fits the budget with room for reruns and adjudication."
    return "Plan is close to budget; reduce prompt_limit or candidate providers before running."


def render_markdown(plan: dict[str, Any]) -> str:
    lines = [
        "# OpenRouter Evaluation Plan",
        "",
        f"Generated: {plan['generated_at']}",
        "",
        "This is an offline spending plan. It contains no API keys and does not call OpenRouter.",
        "",
        "## Model Mix",
        "",
        "| Provider key | Model | Role | Prompt $/tok | Completion $/tok |",
        "|---|---|---|---:|---:|",
    ]
    for key, item in plan["model_roster"].items():
        lines.append(
            f"| `{key}` | `{item['model']}` | {item['role']} | "
            f"{item['prompt_cost']} | {item['completion_cost']} |"
        )
    lines.extend([
        "",
        "## Spend Estimate",
        "",
        f"- Estimated total: `${plan['cost_estimate']['estimated_cost_usd']:.4f}`",
        f"- Budget ceiling: `${plan['budget_usd']:.2f}`",
        f"- Pricing source: {plan['pricing_source']}",
        *(
            [f"- Pricing refreshed at: {plan['pricing_refreshed_at']}"]
            if plan.get("pricing_refreshed_at")
            else []
        ),
        f"- Candidate providers: {', '.join(f'`{key}`' for key in plan['candidate_providers'])}",
        f"- Prompts per candidate provider: {len(plan['selected_prompts'])}",
        f"- Prompt catalog size: {plan['prompt_catalog_count']}",
        f"- Selected prompt file: `{plan['selected_prompt_file']}`",
        f"- Critical prompt file: `{plan['critical_prompt_file']}`",
        f"- Arbiter prompt file: `{plan['arbiter_prompt_file']}`",
        f"- Calls: {plan['cost_estimate']['total_calls']}",
        f"- Phase calls: {json.dumps(plan['phase_call_counts'], sort_keys=True)}",
        f"- Note: {plan['budget_note']}",
        "",
        "| Phase | Provider | Calls | Estimated cost |",
        "|---|---|---:|---:|",
    ])
    for item in plan["cost_estimate"]["line_items"]:
        lines.append(
            f"| {item['phase']} | `{item['provider']}` | {item['calls']} | "
            f"${item['estimated_cost_usd']:.4f} |"
        )
    lines.extend([
        "",
        "## Prompt Mix",
        "",
        f"Bucket counts: {json.dumps(plan['bucket_counts'], sort_keys=True)}",
        "",
        "| Priority | Bucket | Prompt | Category | Rule | Judge | Gap | Why |",
        "|---:|---|---|---|---:|---:|---:|---|",
    ])
    for item in plan["selected_prompts"]:
        rule = "-" if item["avg_rule_score_0_10"] is None else f"{item['avg_rule_score_0_10']:.2f}"
        judge = "-" if item["avg_llm_judge_score_0_10"] is None else f"{item['avg_llm_judge_score_0_10']:.2f}"
        lines.append(
            f"| {item['priority_score']:.2f} | {item['bucket']} | `{item['prompt_id']}` | "
            f"{item['category']} | {rule} | {judge} | {item['max_rule_judge_gap']:.2f} | "
            f"{item['why']} |"
        )
    lines.extend([
        "",
        "## Spend Run Sequence",
        "",
        "1. Regenerate this plan with `--refresh-openrouter-pricing` immediately before spending.",
        "2. Export `OPENROUTER_API_KEY` in the shell environment; do not place the key in repo files.",
        "3. For each phase, run the matching preflight command first and confirm the planned call count.",
        "4. Run the matching spend command only if the preflight call count matches this plan.",
        "5. After each phase, rerun the report command or planner before continuing to the next phase.",
        "",
        "## Preflight Commands",
        "",
        "Run each preflight immediately before its matching spend phase. These commands do not call APIs.",
        "",
    ])
    for name, command in plan["preflight_commands"].items():
        lines.extend([f"### {name}", "", "```powershell", command, "```", ""])
    lines.extend([
        "",
        "## Commands",
        "",
    ])
    for name, command in plan["commands"].items():
        lines.extend([f"### {name}", "", "```powershell", command, "```", ""])
    return "\n".join(lines)


def write_plan(plan: dict[str, Any], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    selected_path = out_dir / "selected_prompts.jsonl"
    critical_path = out_dir / "critical_prompts.jsonl"
    arbiter_path = out_dir / "arbiter_prompts.jsonl"

    def prompt_rows(items: list[dict[str, Any]]) -> str:
        return "".join(
            json.dumps(
                {
                    "id": item["prompt_id"],
                    "category": item["category"],
                    "text": item["text"],
                    "priority_score": item["priority_score"],
                    "bucket": item["bucket"],
                    "selection_reason": item["why"],
                },
                ensure_ascii=False,
            )
            + "\n"
            for item in items
        )

    selected_prompts = plan["selected_prompts"]
    critical_ids = set(plan["critical_prompt_ids"])
    arbiter_ids = set(plan["arbiter_prompt_ids"])
    critical_prompts = [item for item in selected_prompts if item["prompt_id"] in critical_ids]
    arbiter_prompts = [item for item in selected_prompts if item["prompt_id"] in arbiter_ids]

    selected_path.write_text(prompt_rows(selected_prompts), encoding="utf-8")
    critical_path.write_text(prompt_rows(critical_prompts), encoding="utf-8")
    arbiter_path.write_text(prompt_rows(arbiter_prompts), encoding="utf-8")
    (out_dir / "openrouter_eval_plan.json").write_text(
        json.dumps(plan, indent=2),
        encoding="utf-8",
    )
    (out_dir / "openrouter_eval_plan.md").write_text(render_markdown(plan), encoding="utf-8")
    print(f"wrote {selected_path}")
    print(f"wrote {critical_path}")
    print(f"wrote {arbiter_path}")
    print(f"wrote {out_dir / 'openrouter_eval_plan.json'}")
    print(f"wrote {out_dir / 'openrouter_eval_plan.md'}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--results-root",
        default=str(REPO / "reports/free_api_prompt_eval"),
        help="directory containing */results.jsonl, or one results.jsonl file",
    )
    parser.add_argument(
        "--prompt-source",
        action="append",
        default=[],
        help="JSON/JSONL prompt source; may be repeated. Defaults to large harness prompt files.",
    )
    parser.add_argument("--prompt-limit", type=int, default=1000)
    parser.add_argument("--budget-usd", type=float, default=100.0)
    parser.add_argument(
        "--candidate-providers",
        default=",".join(DEFAULT_CANDIDATE_PROVIDERS),
        help=(
            "comma-separated OpenRouter provider keys to evaluate. "
            f"Use {','.join(COMPARISON_CANDIDATE_PROVIDERS)} for the older comparison tranche."
        ),
    )
    parser.add_argument(
        "--primary-judges",
        default=",".join(DEFAULT_PRIMARY_JUDGES),
        help="comma-separated OpenRouter provider keys for broad first-pass LLM judging",
    )
    parser.add_argument(
        "--critical-judges",
        default=",".join(DEFAULT_CRITICAL_JUDGES),
        help="comma-separated OpenRouter provider keys for harm/calibration second judging",
    )
    parser.add_argument(
        "--arbiter-judges",
        default=",".join(DEFAULT_ARBITER_JUDGES),
        help="comma-separated OpenRouter provider keys for high-risk arbitration",
    )
    parser.add_argument(
        "--refresh-openrouter-pricing",
        action="store_true",
        help="fetch OpenRouter's public model catalog and refresh planned token prices",
    )
    parser.add_argument(
        "--paid-run-dir",
        default=str(REPO / "reports/free_api_prompt_eval/openrouter_paid_20260609"),
    )
    parser.add_argument(
        "--out-dir",
        default=str(REPO / "reports/openrouter_eval_plan"),
    )
    args = parser.parse_args()

    result_paths = discover_result_paths(Path(args.results_root))
    if not result_paths:
        raise SystemExit(f"No results.jsonl files found under {args.results_root}")
    rows = load_rows(result_paths)
    pricing_source = STATIC_PRICING_SOURCE
    pricing_refreshed_at: str | None = None
    if args.refresh_openrouter_pricing:
        catalog_rows = fetch_openrouter_model_catalog()
        refreshed = refresh_model_roster_from_catalog(OPENROUTER_MODEL_ROSTER, catalog_rows)
        OPENROUTER_MODEL_ROSTER.clear()
        OPENROUTER_MODEL_ROSTER.update(refreshed)
        pricing_source = OPENROUTER_MODELS_URL
        pricing_refreshed_at = utc_now()
    candidate_providers = parse_provider_keys(args.candidate_providers, DEFAULT_CANDIDATE_PROVIDERS)
    primary_judges = parse_provider_keys(args.primary_judges, DEFAULT_PRIMARY_JUDGES)
    critical_judges = parse_provider_keys(args.critical_judges, DEFAULT_CRITICAL_JUDGES)
    arbiter_judges = parse_provider_keys(args.arbiter_judges, DEFAULT_ARBITER_JUDGES)
    prompt_sources = args.prompt_source or [str(path) for path in DEFAULT_PROMPT_SOURCES]
    prompt_catalog = load_prompt_files(",".join(prompt_sources))
    selected_prompt_file = str(Path(args.out_dir) / "selected_prompts.jsonl").replace("\\", "/")
    plan = build_plan(
        rows,
        prompt_catalog=prompt_catalog,
        prompt_limit=args.prompt_limit,
        budget_usd=args.budget_usd,
        out_dir=args.paid_run_dir,
        prompt_file=selected_prompt_file,
        result_paths=result_paths,
        candidate_providers=candidate_providers,
        primary_judges=primary_judges,
        critical_judges=critical_judges,
        arbiter_judges=arbiter_judges,
        pricing_source=pricing_source,
        pricing_refreshed_at=pricing_refreshed_at,
    )
    write_plan(plan, Path(args.out_dir))
    print(
        f"selected {len(plan['selected_prompts'])} prompts; "
        f"estimated ${plan['cost_estimate']['estimated_cost_usd']:.4f} "
        f"across {plan['cost_estimate']['total_calls']} calls"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
