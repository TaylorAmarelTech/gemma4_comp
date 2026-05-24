from __future__ import annotations

import sys
from pathlib import Path


_SRC_ROOT = Path(__file__).parents[1] / "src"
if str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))


def _edge_fixture(**overrides):
    edge = {
        "schema_version": "duecare.process.typed_edge.v1",
        "edge_id": "edge-fixture-001",
        "edge_type": "charged_or_collected_fee",
        "source_node": "case:synthetic-worker-a",
        "target_node": "amount:php-50000",
        "case_id": "SYN-PH-HK-001",
        "row_id": "synthetic-row-001",
        "label": "processing fee charged before departure",
        "evidence": {
            "file": "caseworker_note.txt",
            "quote": (
                "The worker was asked to pay a PHP 50000 processing fee "
                "before departure and later saw deductions from salary."
            ),
        },
        "indicators": ["fee-camouflage"],
        "corridors": ["ph-hk"],
        "journey_stage": "payment",
        "confidence": 0.82,
    }
    edge.update(overrides)
    return edge


def _client_with_extraction(gemma_call=None):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from duecare.chat.harnesses.extraction.handler import register_routes

    app = FastAPI()
    if gemma_call is not None:
        app.state.gemma_call = gemma_call
    register_routes(app)
    return TestClient(app)


def test_shape_parity_with_draft_envelope():
    client = _client_with_extraction()
    response = client.post(
        "/api/knowledge/from-edge",
        json={"edge": _edge_fixture()},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    for key in {
        "envelope",
        "suggestions",
        "auto_suggested",
        "suggested_types",
        "model_call_requested",
        "model_call_available",
        "demo_replay",
    }:
        assert key in body
    assert body["suggestions"] == [body["envelope"]]
    assert body["auto_suggested"] is False
    assert body["suggested_types"] == ["extracted_fact"]
    assert body["model_call_requested"] is False
    assert body["envelope"]["knowledge_object_type"] == "extracted_fact"
    assert body["envelope"]["version"] == "v1-draft"


def test_no_gemma_call_during_from_edge():
    calls = {"n": 0}

    def fail_if_called(*_args, **_kwargs):
        calls["n"] += 1
        raise AssertionError("from-edge must not call Gemma")

    client = _client_with_extraction(gemma_call=fail_if_called)
    response = client.post(
        "/api/knowledge/from-edge",
        json={"edge": _edge_fixture()},
    )

    assert response.status_code == 200, response.text
    assert calls["n"] == 0
    assert response.json()["model_call_requested"] is False
    assert response.json()["model_call_available"] is True


def test_standardize_ran():
    client = _client_with_extraction()
    response = client.post(
        "/api/knowledge/from-edge",
        json={"edge": _edge_fixture(journey_stage="payment")},
    )

    assert response.status_code == 200, response.text
    envelope = response.json()["envelope"]
    assert envelope["extensions"]["standardized_shape"] is True
    assert envelope["content"]["journey_stage"] == "payment_and_debt"
    assert envelope["content"]["confidence_0_10"] == 8.2


def test_indicator_canonicalized():
    client = _client_with_extraction()
    response = client.post(
        "/api/knowledge/from-edge",
        json={
            "edge": _edge_fixture(
                indicators=["FeeCamouflage", "passport", "unknown-signal"],
                corridors=["ph-hk", "id_my"],
            )
        },
    )

    assert response.status_code == 200, response.text
    content = response.json()["envelope"]["content"]
    assert "fee_camouflage" in content["indicators"]
    assert "passport_retention" in content["indicators"]
    assert "unknown-signal" not in content["indicators"]
    assert content["corridors"] == ["PH-HK", "ID-MY"]
