"""Real tests for the Duecare anonymizer PII gate."""

from __future__ import annotations

import json
from datetime import datetime

from duecare.agents.anonymizer.anonymizer import AnonymizerAgent, redact
from duecare.core.enums import TaskStatus
from duecare.core.provenance import compute_checksum
from duecare.core.schemas import AgentContext


def _make_context() -> AgentContext:
    return AgentContext(
        run_id="run_001",
        git_sha="abc123",
        workflow_id="anonymize_only",
        target_model_id="noop",
        domain_id="trafficking",
        started_at=datetime.now(),
    )


def test_redact_audit_contains_hashes_not_plaintext() -> None:
    text = "Contact [COMPOSITE_NAME] via contact@redacted.example or +15550001234."

    redacted_text, audit = redact(text)

    assert "[EMAIL]" in redacted_text
    assert "[PHONE]" in redacted_text
    assert any(record["category"] == "email" for record in audit)
    assert any(record["category"] == "phone" for record in audit)

    audit_blob = json.dumps(audit, sort_keys=True)
    assert "contact@redacted.example" not in audit_blob
    assert "+15550001234" not in audit_blob
    assert compute_checksum("contact@redacted.example") in audit_blob
    assert compute_checksum("+15550001234") in audit_blob


def test_anonymizer_agent_records_hash_only_audit() -> None:
    ctx = _make_context()
    ctx.record(
        "synthetic_probes",
        [{"id": "probe_001", "text": "Email contact@redacted.example for help."}],
    )
    ctx.record(
        "adversarial_probes",
        [{"id": "probe_002", "text": "Call +15550001234 before boarding."}],
    )

    result = AnonymizerAgent().execute(ctx)

    assert result.status == TaskStatus.COMPLETED

    clean_probes = ctx.lookup("clean_probes")
    audit_records = ctx.lookup("anon_audit")
    quarantine = ctx.lookup("quarantine")

    assert quarantine == []
    assert clean_probes[0]["text"] == "Email [EMAIL] for help."
    assert clean_probes[1]["text"] == "Call [PHONE] before boarding."

    audit_blob = json.dumps(audit_records, sort_keys=True)
    assert "contact@redacted.example" not in audit_blob
    assert "+15550001234" not in audit_blob
    assert all("original_hash" in record for record in audit_records)