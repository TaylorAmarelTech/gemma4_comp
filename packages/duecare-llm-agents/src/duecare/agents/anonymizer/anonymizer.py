"""Anonymizer agent - PII gate.

Runs regex-based PII detection on every probe. Items with detected PII
get redacted. Items whose redaction fails verification go to quarantine.
MVP: regex-only. Full impl: Presidio + Gemma E2B NER.
"""

from __future__ import annotations

import re

from duecare.core.enums import AgentRole, TaskStatus
from duecare.core.provenance import compute_checksum
from duecare.core.schemas import AgentContext, AgentOutput, ToolSpec
from duecare.agents import agent_registry
from duecare.agents.base import fresh_agent_output, noop_model


PII_PATTERNS = [
    ("phone", re.compile(r"\+?\d{1,3}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,9}")),
    ("email", re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")),
    ("passport", re.compile(r"\b[A-Z]{1,2}\d{6,9}\b")),
    ("iban", re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{10,30}\b")),
]


def redact(text: str) -> tuple[str, list[dict]]:
    """Regex-redact PII. Returns (redacted_text, audit_records)."""
    audit: list[dict] = []
    out = text
    for category, pattern in PII_PATTERNS:
        for m in pattern.finditer(text):
            audit.append({
                "category": category,
                "span": (m.start(), m.end()),
                "original_hash": compute_checksum(m.group(0)),
                "replacement": f"[{category.upper()}]",
            })
        out = pattern.sub(lambda m, c=category: f"[{c.upper()}]", out)
    return out, audit


class AnonymizerAgent:
    id = "anonymizer"
    role = AgentRole.ANONYMIZER
    version = "0.1.0"
    model = noop_model()
    tools: list[ToolSpec] = []
    inputs: set[str] = {"synthetic_probes", "adversarial_probes"}
    outputs: set[str] = {"clean_probes", "anon_audit", "quarantine"}
    cost_budget_usd = 0.0

    def execute(self, ctx: AgentContext) -> AgentOutput:
        out = fresh_agent_output(self.id, self.role)
        try:
            synthetic = ctx.lookup("synthetic_probes") or []
            adversarial = ctx.lookup("adversarial_probes") or []
            all_probes = list(synthetic) + list(adversarial)

            clean_probes: list[dict] = []
            audit_records: list[dict] = []
            quarantine: list[dict] = []

            for p in all_probes:
                redacted_text, probe_audit = redact(p.get("text", ""))
                # Verify: re-scan the redacted text
                _, remaining = redact(redacted_text)
                if remaining:
                    quarantine.append(p)
                    continue

                clean = dict(p)
                clean["text"] = redacted_text
                clean_probes.append(clean)
                for a in probe_audit:
                    audit_records.append({"item_id": p.get("id", "?"), **a})

            ctx.record("clean_probes", clean_probes)
            ctx.record("anon_audit", audit_records)
            ctx.record("quarantine", quarantine)

            out.status = TaskStatus.COMPLETED
            out.decision = (
                f"Anonymized {len(clean_probes)}/{len(all_probes)} probes "
                f"({len(quarantine)} quarantined, {len(audit_records)} redactions)"
            )
            out.metrics = {
                "n_input": float(len(all_probes)),
                "n_clean": float(len(clean_probes)),
                "n_quarantined": float(len(quarantine)),
                "n_redactions": float(len(audit_records)),
            }
        except Exception as e:
            out.status = TaskStatus.FAILED
            out.decision = f"failed: {e}"
            out.error = str(e)
        return out

    def explain(self) -> str:
        return "Hard PII gate: detect + redact + verify."


agent_registry.add("anonymizer", AnonymizerAgent())
