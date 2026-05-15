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
    assert "Draft this result" in text
    assert "target_leaf: 'auto'" in text
    assert "searchSaveOneDraft" in text
    assert "body: JSON.stringify(d.envelope)" in text


def test_knowledge_page_uses_guided_auto_suggestion_flow(client):
    r = client.get("/static/knowledge.html")
    assert r.status_code == 200
    text = r.text
    assert "Auto-suggest useful leaves" in text
    assert "Advanced: manual authoring for 21 leaf types" in text
    assert "kxToggleTaxonomy" in text
    assert "out.suggestions" in text
    assert 'id="kx-step-source" open' in text
    assert 'id="kx-step-draft"' in text
    assert 'id="kx-step-pack"' in text
    assert "function kxSetWorkflow" in text
    assert "Extraction harness path" not in text


def test_knowledge_draft_endpoint_auto_suggests_multiple_leaf_types(client):
    r = client.post("/api/knowledge/draft-envelope", json={
        "raw_text": (
            "ILO C181 Article 7 prohibits recruitment fees. Worker paid "
            "PHP 45000 for training and medical fees in the PH-HK corridor. "
            "Hotline contact details should be verified before use."
        ),
        "target_leaf": "auto",
        "anonymize": True,
    })
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["auto_suggested"] is True
    assert {"rag_doc", "grep_rule", "fact_template"}.issubset(data["suggested_types"])
    assert len(data["suggestions"]) >= 3


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
    assert '<details class="wb-step" id="wb-step-1" open>' in text
    assert "function wbSetStep" in text
    assert "wbSetStep(2)" in text


def test_sync_page_uses_guided_pack_flow(client):
    r = client.get("/static/sync.html")
    assert r.status_code == 200
    text = r.text
    assert 'id="sync-guide"' in text
    assert '<details class="sync-step" open>' in text
    assert "Choose source" in text
    assert "Validate envelopes" in text
    assert "Hot-load runtime extras" in text
    assert "function syncSetStep" in text


def test_import_page_uses_guided_local_import_flow(client):
    r = client.get("/static/import.html")
    assert r.status_code == 200
    text = r.text
    assert 'id="import-guide"' in text
    assert '<details class="import-step" id="import-step-1" open>' in text
    assert "This is a utility surface, not a Gemma harness" in text
    assert "function setImportStep" in text
    assert "No activity yet. Add content to populate." in text
    assert "â" not in text
    assert "Â" not in text
    assert "—" not in text


def test_grade_page_uses_guided_scoring_flow(client):
    r = client.get("/static/grade.html")
    assert r.status_code == 200
    text = r.text
    assert 'id="grade-guide"' in text
    assert '<details class="grade-step" id="grade-step-1" open>' in text
    assert "The prompt determines which dimensions are applicable" in text
    assert "authoritative contacts, regulator contacts, retaliation risk" in text
    assert "function gradeSetStep" in text
    assert "audit-allow" not in text
    assert "Grading..." in text
    assert "â" not in text
    assert "Â" not in text
    assert "—" not in text


def test_settings_page_uses_guided_configuration_flow(client):
    r = client.get("/static/settings.html")
    assert r.status_code == 200
    text = r.text
    assert 'id="settings-guide"' in text
    assert '<details class="settings-step" id="settings-step-1" open>' in text
    assert "Hybrid RAG should be the default path" in text
    assert "Search is optional and must remain downstream of search safety sanitization" in text
    assert "one-model Kaggle session constraint" in text
    assert "function settingsSetStep" in text


def test_anonymization_preview_uses_guided_boundary_flow(client):
    r = client.get("/static/anonymization-preview.html")
    assert r.status_code == 200
    text = r.text
    assert 'id="ap-guide"' in text
    assert '<details class="ap-step" id="ap-step-1" open>' in text
    assert "PII patterns are replaced before any hub request is possible" in text
    assert "function setAnonymizeStep" in text
    assert "No activity yet. Run anonymization to populate." in text
    assert "â" not in text
    assert "Â" not in text
    assert "—" not in text


def test_models_page_uses_guided_load_flow(client):
    r = client.get("/static/models.html")
    assert r.status_code == 200
    text = r.text
    assert 'id="model-guide"' in text
    assert '<details class="model-step" id="model-step-1" open>' in text
    assert "Kaggle is most reliable when one Gemma variant is resident at a time" in text
    assert "function modelSetStep" in text
    assert "No activity yet. Load a model to populate." in text
    assert "single T4 | fastest" in text
    assert "â" not in text
    assert "Â" not in text
    assert "—" not in text


def test_process_page_has_graph_visualization_and_graph_chat_logging(client):
    r = client.get("/static/process.html")
    assert r.status_code == 200
    text = r.text
    assert 'id="wb-step-upload" open' in text
    assert "Drop a bundle or use the sample" in text
    assert 'id="wb-step-process"' in text
    assert 'id="wb-step-intelligence"' in text
    assert 'id="wb-step-export"' in text
    assert "Process harness path" not in text
    assert 'id="wb-static-pipeline"' not in text
    assert 'id="pg-pipeline"' not in text
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


def test_chat_page_uses_shared_model_selector(client):
    r = client.get("/static/chat.html")
    assert r.status_code == 200
    text = r.text
    assert "function openModelPickerFromUI" in text
    assert "window.dcWbOpenModelSelector" in text
    assert "Open model selector" in text
    assert "if (!cachedLoaded)" not in text


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
