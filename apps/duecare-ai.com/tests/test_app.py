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


def test_pack_registry_list_and_filter(tmp_path) -> None:
    client = TestClient(create_app(data_dir=tmp_path))

    all_packs = client.get("/api/hub/packs").json()
    assert all_packs["count"] >= 4
    kinds = {pack["@type"] for pack in all_packs["packs"]}
    assert {"ContextPack", "GrepRulePack", "ContactPack", "RubricPack"} <= kinds

    grep_only = client.get("/api/hub/packs?kind=GrepRulePack").json()
    assert grep_only["count"] >= 1
    assert all(pack["@type"] == "GrepRulePack" for pack in grep_only["packs"])

    phl_only = client.get("/api/hub/packs?jurisdiction=PHL").json()
    assert any(pack["id"] == "phl-kwt-domestic" for pack in phl_only["packs"])


def test_pack_registry_get_latest_and_pin(tmp_path) -> None:
    client = TestClient(create_app(data_dir=tmp_path))

    latest = client.get("/api/hub/packs/phl-kwt-domestic").json()
    assert latest["id"] == "phl-kwt-domestic"
    assert latest["@type"] == "ContextPack"
    assert "content" in latest

    pinned = client.get("/api/hub/packs/phl-kwt-domestic/1.7.2").json()
    assert pinned["version"] == "1.7.2"

    versions = client.get("/api/hub/packs/phl-kwt-domestic/versions").json()
    assert versions["count"] >= 1

    missing = client.get("/api/hub/packs/does-not-exist")
    assert missing.status_code == 404


def test_pack_registry_sync(tmp_path) -> None:
    from urllib.parse import quote

    client = TestClient(create_app(data_dir=tmp_path))

    full = client.get("/api/hub/sync").json()
    assert full["count"] >= 4
    assert full["next_cursor"] is not None

    # The cursor contains a `+` for the timezone offset; URL-encode it so
    # the query parser doesn't strip it to a space.
    delta = client.get(f"/api/hub/sync?since={quote(full['next_cursor'], safe='')}").json()
    assert delta["count"] == 0


def test_retract_unvetted_submission(tmp_path) -> None:
    client = TestClient(create_app(data_dir=tmp_path))

    posted = client.post(
        "/api/hub/client/submission",
        json={
            "kind": "context",
            "summary": "Public-source advisory describes a fee cap update for the test corridor.",
            "consent_public_proposal": True,
        },
    ).json()
    submission_id = posted["id"]

    retract = client.post(
        "/api/hub/client/submission/retract",
        json={"submission_id": submission_id, "reason": "operator changed their mind"},
    )
    assert retract.status_code == 200
    payload = retract.json()
    assert payload["retracted"] is True
    assert payload["new_status"] == "retracted"

    # A second retract attempt finds the record but blocks because it is no
    # longer in proposed / needs_review status.
    second = client.post(
        "/api/hub/client/submission/retract",
        json={"submission_id": submission_id},
    )
    assert second.status_code == 409


def test_retract_unknown_submission_404(tmp_path) -> None:
    client = TestClient(create_app(data_dir=tmp_path))
    response = client.post(
        "/api/hub/client/submission/retract",
        json={"submission_id": "cli_not_a_real_id"},
    )
    assert response.status_code == 404


def test_local_kb_ingest_and_list(tmp_path, monkeypatch) -> None:
    # Local KB lives in its own SQLite file; redirect to a tmp dir for
    # test isolation.
    monkeypatch.setenv("DUECARE_LOCAL_KB", str(tmp_path / "local-kb.db"))
    monkeypatch.setenv("DUECARE_LOCAL_KB_SALT", "test-salt")

    # Reload the local_kb module so the env var picks up the new path.
    import importlib

    from app import local_kb as _lk

    importlib.reload(_lk)

    client = TestClient(create_app(data_dir=tmp_path))

    # The route binds to a LocalKB() instance created at app build time, which
    # captured the old default. To work around without restructuring main.py,
    # we point the binding at the same path manually.
    from app import main as _main

    _main._kb = _lk.LocalKB(_lk.DEFAULT_KB_PATH)

    response = client.post(
        "/api/local-kb/ingest",
        json={
            "text": "Composite recruiter case in the PHL-KWT corridor describing fee patterns and an agency named ExampleCo.",
            "source_filename": "test-case-001.txt",
            "corridor": "PHL-KWT",
            "sector": "domestic-work",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["case_id"].startswith("case_")
    assert body["status"] == "processed"
    assert body["corridor"] == "PHL-KWT"

    cases = client.get("/api/local-kb/cases").json()
    assert cases["count"] >= 1

    stats = client.get("/api/local-kb/stats").json()
    assert stats["n_cases"] >= 1


def test_local_kb_forget(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DUECARE_LOCAL_KB", str(tmp_path / "local-kb-forget.db"))

    import importlib

    from app import local_kb as _lk

    importlib.reload(_lk)

    client = TestClient(create_app(data_dir=tmp_path))
    from app import main as _main

    _main._kb = _lk.LocalKB(_lk.DEFAULT_KB_PATH)

    client.post(
        "/api/local-kb/ingest",
        json={
            "text": "Demo case content for forget test, with at least the minimum length.",
            "source_filename": "tmp.txt",
        },
    )
    forgotten = client.post("/api/local-kb/forget").json()
    assert forgotten["ok"] is True
    after = client.get("/api/local-kb/stats").json()
    assert after["n_cases"] == 0


def test_client_submission_endpoint(tmp_path) -> None:
    client = TestClient(create_app(data_dir=tmp_path))

    response = client.post(
        "/api/hub/client/submission",
        json={
            "kind": "context",
            "deployment_id": "test-suite",
            "organization": "Test NGO",
            "summary": "Public-source update on placement-fee cap for the demo corridor; please review.",
            "consent_public_proposal": True,
        },
    )
    assert response.status_code == 202
    payload = response.json()
    assert payload["accepted"] is True
    assert payload["status"] in {"proposed", "needs_review"}
    assert payload["automation_verdict"] in {"accept", "needs_curator_review"}


def test_client_submission_rejects_pii(tmp_path) -> None:
    client = TestClient(create_app(data_dir=tmp_path))

    response = client.post(
        "/api/hub/client/submission",
        json={
            "kind": "context",
            "summary": "Worker email is alice@example.org and they reported the issue.",
            "consent_public_proposal": True,
        },
    )
    assert response.status_code == 422


def test_client_submission_requires_consent(tmp_path) -> None:
    client = TestClient(create_app(data_dir=tmp_path))

    response = client.post(
        "/api/hub/client/submission",
        json={
            "kind": "context",
            "summary": "Public-source advisory describes a regulator clarification on fees.",
            "consent_public_proposal": False,
        },
    )
    assert response.status_code == 422
