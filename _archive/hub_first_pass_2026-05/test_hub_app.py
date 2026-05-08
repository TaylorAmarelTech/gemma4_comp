from __future__ import annotations

from fastapi.testclient import TestClient

from src.hub.app import create_app, detect_pii


def test_detect_pii_finds_disallowed_contact_details() -> None:
    text = "Pattern summary accidentally includes worker@example.org and +1 555 123 4567."

    findings = detect_pii(text)

    assert "email" in findings
    assert "phone" in findings


def test_hub_status_and_knowledge_packs() -> None:
    client = TestClient(create_app())

    status_response = client.get("/api/hub/status")
    packs_response = client.get("/api/hub/knowledge-packs")

    assert status_response.status_code == 200
    assert status_response.json()["privacy_mode"] == "anonymized_signals_only_no_raw_pii"
    assert packs_response.status_code == 200
    assert {pack["kind"] for pack in packs_response.json()} >= {"rag_docs", "grep_rules", "contacts"}


def test_hub_accepts_anonymized_signal() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/api/hub/signals",
        json={
            "source": "synthetic_demo",
            "jurisdiction": "Philippines",
            "corridor": "Philippines to Hong Kong",
            "language": "English",
            "risk_tags": ["illegal_fee", "document_retention"],
            "summary": (
                "Synthetic aggregate pattern: multiple recruitment messages promise placement, "
                "then mention large processing fees and document retention before travel."
            ),
            "evidence_hashes": ["sha256:demo-pattern-001"],
            "consent_basis": "synthetic_demo",
            "pack_version": "demo",
        },
    )

    assert response.status_code == 202
    payload = response.json()
    assert payload["accepted"] is True
    assert payload["summary_sha256"]


def test_hub_rejects_signal_with_raw_pii() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/api/hub/signals",
        json={
            "source": "synthetic_demo",
            "jurisdiction": "Demo",
            "risk_tags": ["unsafe"],
            "summary": "This unsafe summary includes contact worker@example.org and should be rejected.",
            "consent_basis": "synthetic_demo",
        },
    )

    assert response.status_code == 422


def test_hub_accepts_opencrawl_update_as_proposal_only() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/api/hub/opencrawl/updates",
        json={
            "source_name": "Demo public regulator page",
            "source_url": "https://example.org/public-labor-update",
            "proposed_pack_kind": "contacts",
            "jurisdiction": "Demo",
            "change_summary": (
                "Public-source crawler observed that a regulator complaint page changed "
                "its service hours and should be reviewed by a curator."
            ),
            "extracted_public_facts": ["Service hours changed on the public page."],
            "content_hash": "abc123demo",
            "crawler_version": "opencrawl-demo-v0",
        },
    )

    assert response.status_code == 202
    assert response.json()["status"] == "proposed"
