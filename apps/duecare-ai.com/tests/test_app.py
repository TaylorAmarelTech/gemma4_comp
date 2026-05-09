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


def test_public_website_pages_render_design_templates(tmp_path) -> None:
    client = TestClient(create_app(data_dir=tmp_path))

    expected = {
        "/": "AI infrastructure to",
        "/components": "The full system, with honest labels.",
        "/grep-rules": "Rules fire <em>before</em> the model speaks.",
        "/tools": "Six tools. All local. All draft-only.",
        "/context": "Knowledge moves. Cases don't.",
        "/use-cases": "Five ways teams put DueCare to work.",
        "/dashboard": "The live hub. Not the model chat UI.",
    }

    for path, marker in expected.items():
        response = client.get(path)

        assert response.status_code == 200, f"{path} returned {response.status_code}"
        assert marker in response.text, f"{path} missing marker {marker!r}"


def test_every_design_route_renders(tmp_path) -> None:
    """Every entry in PAGE_ROUTES must serve a 200 with linked CSS."""
    from app.main import PAGE_ROUTES

    client = TestClient(create_app(data_dir=tmp_path))
    for path in PAGE_ROUTES:
        response = client.get(path)
        assert response.status_code == 200, f"{path} returned {response.status_code}"
        assert "/static/styles.css" in response.text, f"{path} did not link the design CSS"


def test_use_cases_audiences_appear_in_design_order(tmp_path) -> None:
    client = TestClient(create_app(data_dir=tmp_path))

    response = client.get("/use-cases")

    assert response.status_code == 200
    ordered = [
        "Platform safety screening",
        "NGO &amp; regulator copilot",
        "Migrant worker chat",
        "Academic research",
    ]
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
