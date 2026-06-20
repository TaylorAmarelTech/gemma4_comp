"""Triage harness — waterfall screening for platform-scale content.

The platform-safety lane's live surface: screen batches of job ads and
recruiter messages through GREP rules (deterministic, microseconds) and one
flag/clear verdict from the already-loaded Gemma -- the same model the chat
page uses, so there is no second model and no model switch. Flagged items can
get an optional deeper grounded pass on that same model. The verdict routes;
it never produces user-facing answers.
"""
from __future__ import annotations

from .handler import harness, register_routes
from ..base import HarnessLogicPath, HarnessModelTarget, HarnessPackContract, HarnessSpec

# The harness primitive attributes live ONCE on the BaseHarness subclass
# (handler.TriageHarness) and are re-exported here for the registry + the spec.
name = harness.name
applied_layers = harness.applied_layers
consumes = harness.consumes
emits = harness.emits
capabilities = {
    "batch_screen": "GREP rules -> one loaded-Gemma flag/clear verdict -> optional deeper grounded pass on flagged items.",
    "one_model": "Uses only the already-loaded Gemma (the chat page's model) -- no second model, no endpoint, no model switch.",
    "honest_degradation": "Without a model loaded the result is 'passed_grep_only', never 'cleared'.",
    "measured_throughput": "Per-stage timings and measured items/min in every response.",
}

spec = HarnessSpec(
    name=name,
    tier="primary",
    kind="gemma_harness",
    label="Platform triage waterfall",
    summary=(
        "Screen content batches: deterministic GREP rules plus one flag/clear "
        "verdict from the already-loaded Gemma, with an optional deeper grounded "
        "pass on flagged items — one model, no switch."
    ),
    applied_layers=applied_layers,
    consumes=consumes,
    emits=emits,
    gemma_mode="optional",
    model_role=(
        "The already-loaded Gemma gives one flag/clear verdict per item; the same "
        "model, with full GREP/RAG/tools grounding, runs the optional deeper pass on "
        "flagged items. One model, no switch."
    ),
    test_pages=(
        {"label": "Platform Triage", "href": "/static/triage.html"},
        {"label": "Harness Workbench", "href": "/static/harness.html"},
    ),
    endpoints=(
        {"method": "POST", "path": "/api/triage/screen", "summary": "Screen a batch of items through the waterfall"},
        {"method": "GET", "path": "/api/triage/status", "summary": "Report the loaded model and routing policy"},
    ),
    examples=(
        "Screen 50 scraped job ads; GREP flags 3 on fee patterns, the loaded Gemma flags 4 more, 43 clear — only 7 are escalated.",
        "Run GREP-only mode on an air-gapped box: items report 'passed_grep_only', never a false 'cleared'.",
    ),
    comparison=(
        "Compare the loaded-Gemma verdict against the deeper grounded pass on "
        "flagged items to calibrate the clear threshold."
    ),
    capabilities=capabilities,
    workflow=(
        "Receive a batch of items (job ads, recruiter messages).",
        "Run GREP rules per item; high-severity hits flag immediately.",
        "Ask the loaded Gemma for a flag/clear verdict on the rest.",
        "Route low-confidence or soft-signal items to 'review'.",
        "Optionally run the deeper grounded pass (same model) on flagged items.",
        "Return per-item statuses, per-stage timings, and measured throughput.",
    ),
    prompt_sets=(
        "screen JSON verdict prompt (exploitation risk signals)",
        "deep-review grounded analysis prompt (ILO indicators + evidence quotes)",
    ),
    knowledge_flow=(
        "Consumes GREP rules and prompt templates; emits a per-batch audit row "
        "with counts and item hashes only — raw item text is never persisted."
    ),
    model_fit=(
        "GREP does the cheap, high-volume first pass so the loaded Gemma is asked "
        "only for a short flag/clear verdict per item — keeping batches affordable "
        "on one model. The verdict only routes; depth comes from the optional "
        "grounded pass (same model) on the flagged few."
    ),
    logic_paths=(
        HarnessLogicPath(
            id="waterfall_screen",
            label="GREP -> loaded Gemma verdict -> optional grounded pass",
            entrypoints=("/api/triage/screen",),
            steps=(
                "validate batch (size, per-item length)",
                "run GREP rules per item",
                "flag high-severity GREP hits without spending model time",
                "loaded-Gemma flag/clear verdict for remaining items",
                "route parse failures and low confidence to review",
                "optional deeper grounded pass (same model) on flagged items",
                "emit audit row (counts + sha256s, no raw text)",
            ),
            consumes=("grep_rule", "prompt_template"),
            emits=("audit_template",),
            model_call="optional",
            verification=(
                "a malformed model reply can never clear an item",
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
            "Screen-verdict and deep-review prompt templates",
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
            "one in-process gemma4_runtime for both the verdict and the optional "
            "grounded pass — no external endpoint, no second model"
        ),
    },
    model_targets=(
        HarnessModelTarget(
            "loaded_gemma_screen",
            "Loaded Gemma (verdict)",
            "gemma4_runtime",
            "One flag/clear verdict per item -- the same loaded model the chat page uses, "
            "no second model and no model switch.",
            ("text_generation", "structured_json", "safety_filtering"),
            default=True,
            trust_boundary="local",
        ),
        HarnessModelTarget(
            "loaded_gemma_deep",
            "Loaded Gemma (deeper grounded pass)",
            "gemma4_runtime",
            "Optional GREP/RAG/tools-grounded analysis of flagged items -- the SAME loaded model.",
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
        "model parse failures degrade to review, never to cleared",
        "audit row stores counts and sha256 hashes only",
    ),
    privacy_boundaries=(
        "content stays local: screening runs entirely on the in-process loaded Gemma",
        "training log stores sha256 + counts, never raw item text",
        "model verdicts are routing signals, not user-facing answers",
    ),
)

__all__ = ["name", "applied_layers", "consumes", "emits", "capabilities", "register_routes", "spec"]
