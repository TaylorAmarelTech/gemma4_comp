"""Triage harness — waterfall screening for platform-scale content.

The platform-safety lane's live surface: screen batches of job ads and
recruiter messages through GREP rules (deterministic, microseconds), a fast
model tier (DiffusionGemma-class endpoint or any OpenAI-compatible model),
and escalate only the risky few to the deep Gemma 4 analysis. The fast tier
routes; it never produces user-facing answers.
"""
from __future__ import annotations

from .handler import register_routes
from ..base import HarnessLogicPath, HarnessModelTarget, HarnessPackContract, HarnessSpec

name = "triage"
applied_layers: tuple[str, ...] = ("grep",)
consumes: tuple[str, ...] = (
    "grep_rule",          # deterministic first tier
    "prompt_template",    # fast-screen + deep-review prompts
)
emits: tuple[str, ...] = (
    "audit_template",     # per-batch screening audit row (counts + hashes)
)
capabilities = {
    "waterfall_screen": "GREP -> fast-model verdict -> deep-model escalation routing for content batches.",
    "fast_tier_endpoint": "OpenAI-compatible fast tier (DiffusionGemma-class) via DUECARE_FAST_MODEL_BASE_URL.",
    "honest_degradation": "Without any model the result is 'passed_grep_only', never 'cleared'.",
    "measured_throughput": "Per-stage timings and measured fast-tier items/min in every response.",
}

spec = HarnessSpec(
    name=name,
    tier="primary",
    kind="gemma_harness",
    label="Platform triage waterfall",
    summary=(
        "Screen content batches at platform scale: deterministic GREP rules, a "
        "fast model tier for quick flag/clear verdicts, and deep Gemma 4 "
        "analysis only for escalated items."
    ),
    applied_layers=applied_layers,
    consumes=consumes,
    emits=emits,
    gemma_mode="optional",
    model_role=(
        "The fast tier (DiffusionGemma-class endpoint or the loaded local Gemma) "
        "gives one quick verdict per item; the deep tier is the loaded Gemma 4 "
        "with full GREP/RAG/tools grounding, run only on escalated items."
    ),
    test_pages=(
        {"label": "Platform Triage", "href": "/static/triage.html"},
        {"label": "Harness Workbench", "href": "/static/harness.html"},
    ),
    endpoints=(
        {"method": "POST", "path": "/api/triage/screen", "summary": "Screen a batch of items through the waterfall"},
        {"method": "GET", "path": "/api/triage/status", "summary": "Report configured tiers and routing policy"},
    ),
    examples=(
        "Screen 50 scraped job ads; GREP flags 3 on fee patterns, the fast tier flags 4 more, 43 clear — only 7 reach the deep model.",
        "Run GREP-only mode on an air-gapped box: items report 'passed_grep_only', never a false 'cleared'.",
    ),
    comparison=(
        "Compare fast-tier verdicts against deep-model analysis on escalated items "
        "to calibrate the clear threshold."
    ),
    capabilities=capabilities,
    workflow=(
        "Receive a batch of items (job ads, recruiter messages).",
        "Run GREP rules per item; high-severity hits flag immediately.",
        "Ask the fast model for a flag/clear verdict on the rest.",
        "Route low-confidence or soft-signal items to 'review'.",
        "Optionally run the deep grounded Gemma 4 analysis on escalated items.",
        "Return per-item statuses, per-stage timings, and measured throughput.",
    ),
    prompt_sets=(
        "fast-screen JSON verdict prompt (exploitation risk signals)",
        "deep-review grounded analysis prompt (ILO indicators + evidence quotes)",
    ),
    knowledge_flow=(
        "Consumes GREP rules and prompt templates; emits a per-batch audit row "
        "with counts and item hashes only — raw item text is never persisted."
    ),
    model_fit=(
        "Fast tier favours throughput over depth: DiffusionGemma's parallel-block "
        "decode (up to 4x faster, quality below standard Gemma 4) is acceptable "
        "BECAUSE the verdict only routes items. Final analysis always comes from "
        "the slower, stronger deep tier."
    ),
    logic_paths=(
        HarnessLogicPath(
            id="waterfall_screen",
            label="GREP -> fast model -> deep escalation",
            entrypoints=("/api/triage/screen",),
            steps=(
                "validate batch (size, per-item length)",
                "run GREP rules per item",
                "flag high-severity GREP hits without spending model time",
                "fast-model flag/clear verdict for remaining items",
                "route parse failures and low confidence to review",
                "optional deep grounded analysis of escalated items",
                "emit audit row (counts + sha256s, no raw text)",
            ),
            consumes=("grep_rule", "prompt_template"),
            emits=("audit_template",),
            model_call="optional",
            verification=(
                "a malformed fast-model reply can never clear an item",
                "without a model, items are 'passed_grep_only', not 'cleared'",
                "raw item text is never echoed or persisted — sha256 only",
            ),
        ),
    ),
    knowledge_packs=(
        HarnessPackContract(
            "grep_rules",
            "Deterministic exploitation patterns",
            "knowledge_pack",
            ("grep_rule",),
            True,
            "local",
        ),
    ),
    logic_packs=(
        HarnessPackContract(
            "triage_prompts",
            "Fast-screen and deep-review prompt templates",
            "logic_pack",
            ("prompt_template",),
            True,
            "local",
        ),
    ),
    model_io={
        "input": "batch of public/scraped content items (job ads, recruiter messages)",
        "output": "per-item status (flagged/review/cleared/passed_grep_only), per-stage timings, escalation list",
        "model_transport": (
            "fast tier: openai_compatible endpoint (DiffusionGemma via vLLM) or "
            "in-process gemma4_runtime; deep tier: gemma4_runtime with grounding layers"
        ),
    },
    model_targets=(
        HarnessModelTarget(
            "fast_screen_endpoint",
            "Fast screen tier (DiffusionGemma via vLLM)",
            "openai_compatible",
            "First-pass flag/clear verdicts at platform throughput.",
            ("text_generation", "structured_json", "safety_filtering"),
            default=True,
            trust_boundary="local",
            credential_env=(
                "DUECARE_FAST_MODEL_BASE_URL",
                "DUECARE_FAST_MODEL_ID",
                "DUECARE_FAST_MODEL_API_KEY",
            ),
            notes=(
                "Designed for google/diffusiongemma-26B-A4B-it (26B MoE, 3.8B active, "
                "256-token parallel diffusion blocks, up to 4x faster generation, "
                "Apache 2.0). Its quality sits below standard Gemma 4, which is "
                "acceptable here because the verdict only ROUTES items — it never "
                "answers a worker or clears an item as 'safe'."
            ),
        ),
        HarnessModelTarget(
            "in_process_gemma_fast",
            "Loaded local Gemma (fast-tier fallback)",
            "gemma4_runtime",
            "Fast-tier fallback when no endpoint is configured.",
            ("text_generation", "structured_json"),
            trust_boundary="local",
        ),
        HarnessModelTarget(
            "deep_grounded_reviewer",
            "Deep grounded Gemma 4 reviewer",
            "gemma4_runtime",
            "Full GREP/RAG/tools-grounded analysis of escalated items only.",
            ("text_generation", "evidence_tracing", "safety_filtering"),
            trust_boundary="local",
        ),
        HarnessModelTarget(
            "deterministic_grep_only",
            "GREP-only deterministic screen",
            "none",
            "Air-gapped honest mode: flags known patterns, never claims 'cleared'.",
            ("safety_filtering",),
            trust_boundary="local",
        ),
    ),
    input_verification=(
        "batch capped at 200 items, 20k chars per item",
        "every item must be a non-empty string",
    ),
    output_verification=(
        "per-item status is one of flagged/review/cleared/passed_grep_only",
        "fast-model parse failures degrade to review, never to cleared",
        "audit row stores counts and sha256 hashes only",
    ),
    privacy_boundaries=(
        "content stays local unless the operator points DUECARE_FAST_MODEL_BASE_URL at a remote endpoint",
        "training log stores sha256 + counts, never raw item text",
        "fast-tier verdicts are routing signals, not user-facing answers",
    ),
)

__all__ = ["name", "applied_layers", "consumes", "emits", "capabilities", "register_routes", "spec"]
