"""End-to-end integration test exercising multiple harnesses in one chain."""
from __future__ import annotations

import pathlib

from fastapi.testclient import TestClient

from duecare.chat.app import create_app


def _fake_gemma(messages, **kw):
    """Deterministic JSON envelope content body."""
    return '{"pattern": "fee\\s*[\\d,]+", "category": "fee_bondage", "severity": "high"}'


def test_extract_then_anonymize_then_submit_chain():
    app = create_app(gemma_call=_fake_gemma, model_info={"loaded": True})
    c = TestClient(app)

    raw_with_pii = "Ms. Jane Doe at jane@example.com saw recruiter charge PHP 30,000 fee"

    r1 = c.post("/api/knowledge/draft-envelope", json={
        "raw_text": raw_with_pii,
        "target_leaf": "grep_rule",
        "anonymize": True,
    })
    assert r1.status_code == 200, r1.text
    envelope = r1.json()["envelope"]
    assert envelope["knowledge_object_type"] == "grep_rule"
    assert envelope["extensions"]["anonymized_before_gemma"] is True
    assert "<EMAIL>" in envelope["extensions"]["placeholders_used"]

    r2 = c.post("/api/anonymize", json={"texts": [raw_with_pii]})
    assert r2.status_code == 200, r2.text
    redacted = r2.json()["redacted"][0]
    diffs = r2.json()["diffs"][0]
    assert "<PERSON_" in redacted
    assert "<EMAIL_" in redacted
    assert "<AMOUNT_" in redacted
    assert diffs["n_redactions"] >= 3

    r3 = c.post("/api/submit/knowledge", json={
        "knowledge": [envelope],
        "target_url": "http://127.0.0.1:1/unreachable",
    })
    assert r3.status_code == 200, r3.text
    body = r3.json()
    assert body["ok"] is True
    assert body["transmitted"] is False
    assert body["audit_entry"]["n_items"] == 1


def test_anonymization_gate_blocks_pii_before_extraction():
    app = create_app(gemma_call=_fake_gemma, model_info={"loaded": True})
    c = TestClient(app)

    r = c.post("/api/knowledge/draft-envelope", json={
        "raw_text": "Contact jane.doe@example.com about fee bondage",
        "target_leaf": "grep_rule",
        "anonymize": True,
    })
    assert r.status_code == 200
    ext = r.json()["envelope"]["extensions"]
    assert ext["anonymized_before_gemma"] is True
    assert "<EMAIL>" in ext["placeholders_used"]


def test_harness_training_logs_are_per_task():
    """Each harness writes to its own JSONL stream."""
    app = create_app(gemma_call=_fake_gemma, model_info={"loaded": True})
    c = TestClient(app)

    c.post("/api/anonymize", json={"texts": ["test"]})
    c.post("/api/knowledge/draft-envelope", json={
        "raw_text": "fee",
        "target_leaf": "grep_rule",
    })

    train_dir = pathlib.Path("/kaggle/working/training")
    if train_dir.exists():
        files = {p.name for p in train_dir.glob("*.jsonl")}
        assert "anonymization.jsonl" in files
        assert "extraction.jsonl" in files
