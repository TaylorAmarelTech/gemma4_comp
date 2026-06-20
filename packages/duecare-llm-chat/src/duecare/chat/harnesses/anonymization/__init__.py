"""Anonymization & Sharing harness — PII gate (regex-only by design)."""
from __future__ import annotations

from .handler import register_routes
from .knowledge import CONSUMES as consumes, EMITS as emits
from ..base import HarnessLogicPath, HarnessModelTarget, HarnessPackContract, HarnessSpec
from ..base import BaseHarness

name = "anonymization"
applied_layers: tuple[str, ...] = ()  # regex-only by design
capabilities: tuple[str, ...] = ()  # stateless gate; multi_turn not applicable

spec = HarnessSpec(
    name=name,
    tier="primary",
    kind="safety_gate",
    label="Anonymization gate",
    summary="Hard privacy gate before data crosses a trust boundary.",
    applied_layers=applied_layers,
    consumes=consumes,
    emits=emits,
    gemma_mode="optional",
    model_role="Regex redaction is mandatory; Gemma 4 can review already-redacted text for residual PII before hub submission.",
    test_pages=(
        {"label": "Anonymization and sharing", "href": "/static/share.html"},
        {"label": "Preview redaction", "href": "/static/anonymization-preview.html"},
    ),
    endpoints=(
        {"method": "POST", "path": "/api/anonymize", "summary": "Redact PII and optionally run Gemma privacy review"},
        {"method": "POST", "path": "/api/submit/knowledge", "summary": "Submit sanitized knowledge"},
        {"method": "POST", "path": "/api/submit/local", "summary": "Deprecated local-submit alias"},
    ),
    examples=(
        "Redact names, phones, and document IDs before sharing a case summary.",
        "Verify only sha256 fingerprints, not plaintext, enter the audit log.",
    ),
    comparison="Compare raw vs redacted output on the preview page before submission.",
    workflow=(
        "Process uploaded source bundle or knowledge files locally.",
        "Reviewer selects items for submission.",
        "Run deterministic redaction and salted-hash placeholder replacement.",
        "Optionally ask Gemma to review already-redacted text, then submit sanitized knowledge to the hub.",
    ),
    prompt_sets=(
        "deterministic redaction patterns",
        "optional Gemma residual-PII review prompt",
    ),
    knowledge_flow=(
        "Consumes submission schemas and prompt templates; emits audit records "
        "and sanitized submission envelopes. Raw case data is never a knowledge "
        "object for hub submission."
    ),
    model_fit=(
        "Redaction does not require Gemma. Gemma privacy review is a redundant "
        "second local check, not a guarantee. Smaller models may miss residual "
        "PII, so human review remains required before submission."
    ),
    logic_paths=(
        HarnessLogicPath(
            id="redact_and_review",
            label="Redact and review before egress",
            entrypoints=("/api/anonymize", "/api/submit/knowledge", "/static/share.html"),
            steps=(
                "receive local text or knowledge proposal",
                "run deterministic PII and confidential marker detection",
                "replace sensitive values with salted placeholders and hashes",
                "optionally ask Gemma 4 to review already-redacted text",
                "return sanitized payload and audit record",
            ),
            consumes=("prompt_template",),
            emits=("audit_template", "submission_schema"),
            model_call="optional",
            verification=("deterministic PII detector", "sha256-only audit metadata", "human review before submission"),
        ),
    ),
    knowledge_packs=(
        HarnessPackContract("privacy_patterns", "Privacy and PII patterns", "logic_pack", ("grep_rule", "prompt_template"), True, "local"),
    ),
    logic_packs=(
        HarnessPackContract("submission_schema", "Hub/local submission schema", "logic_pack", ("submission_schema", "audit_template"), True, "local"),
    ),
    model_io={
        "input": "raw or already-redacted text, submission proposal, redaction options",
        "output": "redacted text, redaction audit, optional residual-PII review",
        "model_transport": "optional Gemma 4 review over redacted text only",
    },
    model_targets=(
        HarnessModelTarget(
            "deterministic_redactor",
            "Deterministic redactor",
            "none",
            "Required local privacy gate before any model or external boundary.",
            ("privacy_review", "structured_json"),
            required=True,
            default=True,
            trust_boundary="local",
        ),
        HarnessModelTarget(
            "local_gemma4_privacy_review",
            "Local Gemma 4 privacy review",
            "gemma4_runtime",
            "Optional second pass over already-redacted text.",
            ("text_generation", "chat_messages", "privacy_review", "structured_json"),
            trust_boundary="local",
        ),
        HarnessModelTarget(
            "external_privacy_reviewer",
            "External privacy reviewer",
            "frontier_api",
            "Optional redundant review only after deterministic redaction and reviewer approval.",
            ("text_generation", "chat_messages", "privacy_review", "structured_json"),
            trust_boundary="external",
            credential_env=("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GOOGLE_API_KEY"),
        ),
    ),
    input_verification=("regex PII detection", "confidential-marker detection", "submission schema checks"),
    output_verification=("no direct identifiers in sanitized payload", "hashes recorded instead of raw values"),
    privacy_boundaries=("raw content must not leave the local runtime", "Gemma review sees redacted text only"),
)


class AnonymizationHarness(BaseHarness):
    """Extends the thin BaseHarness for its shared helpers (emit_training_row / compose).
    Single source of the harness primitive is the module attrs above; the `harness`
    singleton carries them for handlers + the registry."""

    name = name
    applied_layers = applied_layers
    consumes = consumes
    emits = emits


harness = AnonymizationHarness()

__all__ = ["name", "applied_layers", "capabilities", "consumes", "emits", "register_routes", "spec"]
