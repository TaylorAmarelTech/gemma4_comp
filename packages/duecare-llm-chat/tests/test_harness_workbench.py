from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    from duecare.chat.app import create_app
    app = create_app()
    return TestClient(app)


def test_harness_contract_endpoint_lists_seven_surfaces(client):
    r = client.get("/api/harnesses")
    assert r.status_code == 200
    data = r.json()
    names = [h["name"] for h in data["harnesses"]]
    assert names == [
        "chat",
        "process",
        "extraction",
        "anonymization",
        "search_safety",
        "search",
        "import_corpus",
    ]
    assert data["n_harnesses"] == 7
    assert [h["name"] for h in data["primary"]] == [
        "chat",
        "process",
        "extraction",
        "anonymization",
        "search_safety",
    ]
    assert [h["name"] for h in data["secondary"]] == ["search", "import_corpus"]


def test_harness_contract_nomenclature_is_explicit(client):
    data = client.get("/api/harnesses").json()
    by_name = {h["name"]: h for h in data["harnesses"]}
    assert by_name["chat"]["kind"] == "gemma_harness"
    assert by_name["chat"]["applied_layers"] == ["persona", "grep", "rag", "tools", "online"]
    assert by_name["search_safety"]["kind"] == "safety_gate"
    assert by_name["search_safety"]["gemma_mode"] == "optional"
    assert by_name["search"]["kind"] == "utility_surface"
    assert by_name["import_corpus"]["gemma_mode"] == "not_required"
    assert all(h["register_routes"] for h in data["harnesses"])


def test_harness_workbench_page_serves(client):
    r = client.get("/static/harness.html")
    assert r.status_code == 200
    text = r.text
    for marker in [
        'data-nav="harness"',
        'id="harness-select"',
        "/api/harnesses",
        "Primary Safety Surfaces",
        "Secondary Utilities",
        "/static/search-safety.html",
    ]:
        assert marker in text


def test_search_safety_page_serves(client):
    r = client.get("/static/search-safety.html")
    assert r.status_code == 200
    text = r.text
    for marker in [
        "Search Safety Gate",
        "/api/search/sanitize",
        "/api/search/safety-info",
        "Compare strict vs rephrase",
        'id="mode-rephrase"',
    ]:
        assert marker in text


def test_use_cases_page_serves_five_audience_lanes(client):
    r = client.get("/static/use-cases.html")
    assert r.status_code == 200
    text = r.text
    for marker in [
        'data-nav="use-cases"',
        "Platform safety",
        "For NGOs &amp; regulators",
        "Individual worker / mobile",
        "Researcher",
        "Developer / integration partner",
        "/static/showcase-platform.html",
        "/static/showcase-ngo.html",
        "/static/showcase-worker.html",
        "/static/showcase-researcher.html",
        "/static/showcase-developer.html",
    ]:
        assert marker in text


def test_showcase_pages_use_consistent_chat_alias(client):
    pages = [
        "/static/showcase-platform.html",
        "/static/showcase-ngo.html",
        "/static/showcase-worker.html",
        "/static/showcase-researcher.html",
        "/static/showcase-developer.html",
    ]
    for page in pages:
        r = client.get(page)
        assert r.status_code == 200
        text = r.text
        assert 'data-nav="use-cases"' in text
        assert "/static/chat.html?audience=" in text
        assert 'href="/?audience=' not in text
        assert "window.location.href='/?prompt=" not in text
