"""Tests for the outbound hardening on /api/submit/knowledge.

The submit boundary must strip process-internal bookkeeping (which embeds
the original upload folder structure -- worker-named dirs on real intake)
and must count residual person-identifying PII into the audit without
counting legitimate monetary amounts.
"""
from __future__ import annotations

import json

from duecare.chat.harnesses.anonymization import handler as h


def test_strip_internal_fields_removes_folder_bookkeeping() -> None:
    item = {
        "schema_version": "1.0",
        "knowledge_object_type": "extracted_fact",
        "id": "fee-signal-1",
        "source_path": "DC-PH-HK-101_Ana_Cruz/intake_form.pdf",
        "row_id": "DC-PH-HK-101_Ana_Cruz/intake#page-001-chunk-001",
        "content": {
            "fact_type": "fee_overcharge",
            "amount": 15000,
            "currency": "PHP",
            "aggregation_keys": {
                "source_node": "process:DC-PH-HK-101_Ana_Cruz/intake_form.pdf",
                "case_id": "dc-ph-hk-101",
            },
        },
    }
    cleaned = h._strip_internal_fields(item)
    assert "source_path" not in cleaned
    assert "row_id" not in cleaned
    assert "aggregation_keys" not in cleaned["content"]
    assert cleaned["content"]["amount"] == 15000
    assert cleaned["content"]["currency"] == "PHP"
    assert cleaned["id"] == "fee-signal-1"
    assert "Ana_Cruz" not in json.dumps(cleaned)


def test_count_residual_pii_ignores_amounts_flags_identifiers() -> None:
    clean = [{"content": {"amount": 42000, "currency": "PHP", "fact_type": "fee"}}]
    assert h._count_residual_pii(clean) == 0
    leaked = [{"content": {"note": "contact maria@example.com for details"}}]
    assert h._count_residual_pii(leaked) == 1
    phone = [{"content": {"note": "call +63 917 555 0144"}}]
    assert h._count_residual_pii(phone) == 1


def test_strip_is_idempotent_and_handles_plain_values() -> None:
    assert h._strip_internal_fields("plain") == "plain"
    assert h._strip_internal_fields(7) == 7
    once = h._strip_internal_fields({"a": 1, "source_path": "x/y"})
    assert h._strip_internal_fields(once) == once
