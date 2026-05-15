"""Anonymization & Sharing harness — PII gate (regex-only by design)."""
from __future__ import annotations

from .handler import register_routes
from .knowledge import CONSUMES as consumes, EMITS as emits
from ..base import HarnessSpec

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
)

__all__ = ["name", "applied_layers", "capabilities", "consumes", "emits", "register_routes", "spec"]
