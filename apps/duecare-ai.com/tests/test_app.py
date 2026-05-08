from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app, detect_pii


def test_detect_pii_blocks_obvious_contact_details() -> None:
    assert detect_pii("Contact worker@example.org for details") == {"email"}
    assert "phone" in detect_pii("Call +1 555 123 4567 immediately")
    assert "identity_document" in detect_pii("Passport A1234567 was retained")


def test_health_status_uses_file_storage(tmp_path) -> None:
    client = TestClient(create_app(data_dir=tmp_path))

    response = client.get("/api/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["storage"] == "file"
    assert payload["storage_ok"] is True
    assert (tmp_path / "signals.jsonl").exists()


def test_robots_and_sitemap_are_served(tmp_path) -> None:
    client = TestClient(create_app(data_dir=tmp_path))

    robots = client.get("/robots.txt")
    sitemap = client.get("/sitemap.xml")

    assert robots.status_code == 200
    assert "Sitemap: https://duecare-ai.com/sitemap.xml" in robots.text
    assert sitemap.status_code == 200
    assert "https://duecare-ai.com/" in sitemap.text
    assert "https://duecare-ai.com/docs" in sitemap.text
    assert "https://duecare-ai.com/grep-rules" in sitemap.text


def test_public_website_pages_explain_project(tmp_path) -> None:
    client = TestClient(create_app(data_dir=tmp_path))

    expected = {
        "/": "Centralized knowledge. Decentralized privacy.",
        "/components": "Plain-language components",
        "/grep-rules": "Deterministic rules before generation.",
        "/tools": "Tools draft; humans decide.",
        "/context": "Context organized by corridor and jurisdiction.",
        "/use-cases": "Four use cases, one privacy rule.",
        "/dashboard": "Try the privacy-preserving flow",
    }

    for path, marker in expected.items():
        response = client.get(path)

        assert response.status_code == 200
        assert marker in response.text


def test_use_cases_follow_canonical_order(tmp_path) -> None:
    client = TestClient(create_app(data_dir=tmp_path))

    response = client.get("/use-cases")

    assert response.status_code == 200
    ordered = ["Platform Safety", "NGO / Regulators", "Migrant Worker Chat", "Academic Research"]
    positions = [response.text.index(name) for name in ordered]
    assert positions == sorted(positions)


def test_accepts_anonymized_signal_and_persists(tmp_path) -> None:
    client = TestClient(create_app(data_dir=tmp_path))

    response = client.post(
        "/api/hub/signals",
        json={
            "source": "synthetic_demo",
            "jurisdiction": "Philippines / Hong Kong",
            "corridor": "PH-HK domestic work",
            "language": "English",
            "risk_tags": ["recruitment_fee", "document_retention"],
            "summary": "Synthetic aggregate pattern describing high recruitment fees and document pressure without person-specific details.",
            "evidence_hashes": ["sha256:synthetic-demo-pattern-001"],
            "consent_basis": "synthetic_demo",
            "pack_version": "0.14.x",
        },
    )

    assert response.status_code == 202
    assert response.json()["accepted"] is True

    second_client = TestClient(create_app(data_dir=tmp_path))
    status = second_client.get("/api/hub/status").json()
    assert status["signal_count"] == 1
    assert status["counters"]["risk:recruitment_fee"] == 1


def test_rejects_raw_pii_in_signal(tmp_path) -> None:
    client = TestClient(create_app(data_dir=tmp_path))

    response = client.post(
        "/api/hub/signals",
        json={
            "source": "synthetic_demo",
            "jurisdiction": "Philippines",
            "summary": "This includes a direct email address worker@example.org and should be rejected.",
            "consent_basis": "synthetic_demo",
        },
    )

    assert response.status_code == 422


def test_accepts_opencrawl_update_as_proposal(tmp_path) -> None:
    client = TestClient(create_app(data_dir=tmp_path))

    response = client.post(
        "/api/hub/opencrawl/updates",
        json={
            "source_name": "Synthetic public regulator page",
            "source_url": "https://example.org/public-advisory",
            "proposed_pack_kind": "contacts",
            "jurisdiction": "Hong Kong",
            "change_summary": "Synthetic public-source update proposing clearer complaint-routing language for curator review.",
            "extracted_public_facts": ["Synthetic public-source update; curator review required."],
            "content_hash": "synthetic-public-hash-001",
            "crawler_version": "opencrawl-demo/0.1",
        },
    )

    assert response.status_code == 202
    assert response.json()["status"] == "proposed"
    updates = client.get("/api/hub/opencrawl/updates").json()
    assert len(updates) == 1
