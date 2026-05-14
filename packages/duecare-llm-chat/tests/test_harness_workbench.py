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


def test_search_page_blocks_when_page_sanitizer_fails(client):
    """The search page must not silently send a raw query after the
    page-side Search Safety gate errors.
    """
    r = client.get("/static/search.html")
    assert r.status_code == 200
    text = r.text
    assert "Search stopped because sanitization failed" in text
    assert "sending raw query" not in text
    assert "Kernel search hook" in text


def test_search_backends_contract_has_human_labels(client):
    r = client.get("/api/search/backends")
    assert r.status_code == 200
    data = r.json()
    by_name = {b["name"]: b for b in data["backends"]}
    assert by_name["searxng"]["display_name"] == "SearXNG"
    assert by_name["legacy"]["display_name"] == "Kernel search hook"
    assert "default_preference_labels" in data


def test_search_client_rejects_bad_top_n(client):
    r = client.post("/api/search/client", json={
        "query": "ILO C181 recruitment fee",
        "top_n": "not-a-number",
    })
    assert r.status_code == 400


def test_share_page_has_bulk_review_selection_controls(client):
    r = client.get("/static/share.html")
    assert r.status_code == 200
    text = r.text
    assert 'id="wb-select-all-btn"' in text
    assert 'id="wb-clear-all-btn"' in text
    assert "function escapeHtml" in text


def test_process_page_has_graph_visualization_and_graph_chat_logging(client):
    r = client.get("/static/process.html")
    assert r.status_code == 200
    text = r.text
    assert 'id="wb-graph-viz"' in text
    assert "function wbRenderGraph" in text
    assert "Download graph SVG" in text
    assert "Overcharging entities" in text
    assert "Strongest cases" in text
    assert "Grouped action" in text
    assert "Folder clues" in text
    assert "Media queue" in text
    assert "POST /api/process/graph-chat" in text
    assert "wbLog('net', 'POST /api/process/graph-chat'" in text


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
