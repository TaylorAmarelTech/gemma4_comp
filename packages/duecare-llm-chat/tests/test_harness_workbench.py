from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    from duecare.chat.app import create_app
    app = create_app()
    return TestClient(app)


def test_harness_contract_endpoint_lists_registered_surfaces(client):
    from duecare.chat.harnesses import all_harnesses

    r = client.get("/api/harnesses")
    assert r.status_code == 200
    data = r.json()
    names = [h["name"] for h in data["harnesses"]]
    expected_names = [h.name for h in all_harnesses()]
    assert names == expected_names
    assert data["n_harnesses"] == len(expected_names)
    required_primary = {
        "chat",
        "process",
        "extraction",
        "anonymization",
        "search_safety",
        "post_search_verification",
    }
    assert required_primary.issubset({h["name"] for h in data["primary"]})
    assert {"search", "import_corpus"}.issubset({h["name"] for h in data["secondary"]})


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
    assert "workflow" in data["contract_fields"]
    assert "logic_paths" in data["contract_fields"]
    assert "knowledge_packs" in data["contract_fields"]
    assert "logic_packs" in data["contract_fields"]
    assert "model_targets" in data["contract_fields"]
    assert "input_verification" in data["contract_fields"]
    assert "prompt_sets" in data["contract_fields"]
    assert "model_fit" in data["contract_fields"]
    assert by_name["process"]["workflow"]
    assert by_name["chat"]["logic_paths"][0]["id"] == "chat_response"
    assert by_name["chat"]["model_targets"][0]["transport"] == "gemma4_runtime"
    assert by_name["search_safety"]["logic_paths"][0]["id"] == "sanitize_query"
    assert by_name["post_search_verification"]["logic_paths"][0]["id"] == "verify_search_results"
    assert by_name["post_search_verification"]["kind"] == "safety_gate"
    assert by_name["post_search_verification"]["model_targets"][0]["transport"] == "none"
    assert any("PAGE_ITEM_PROMPT_TREE" in p for p in by_name["process"]["prompt_sets"])
    assert "Multimodal" in by_name["process"]["model_fit"]
    assert "EXTRACTION_SYSTEM_PROMPT" in " ".join(by_name["extraction"]["prompt_sets"])
    assert "human review" in by_name["anonymization"]["model_fit"]


def test_harness_modules_expose_specs():
    from duecare.chat.harnesses import all_harnesses
    from duecare.chat.harnesses.base import HarnessSpec

    for module in all_harnesses():
        spec = getattr(module, "spec", None)
        assert isinstance(spec, HarnessSpec), getattr(module, "name", module)
        assert spec.workflow, spec.name
        assert spec.prompt_sets, spec.name
        assert spec.model_fit, spec.name


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
        "Post-search verification gate",
        "Workflow Path",
        "Standard Logic Paths",
        "Knowledge Packs",
        "Logic Packs",
        "Model Targets",
        "Verification and Privacy",
        "Prompt Sets",
        "Model fit",
        "Knowledge flow",
        'id="workflow-list"',
        'id="logic-path-list"',
        'id="knowledge-pack-list"',
        'id="logic-pack-list"',
        'id="model-target-list"',
        'id="verification-list"',
        'id="prompt-list"',
    ]:
        assert marker in text
    assert "function boundaryClass" in text
    assert 'class="target-boundary ${boundaryClass(boundary)}"' in text
    assert ".target-boundary.external" in text


def test_post_search_verification_endpoint_scores_candidates(client):
    r = client.post("/api/search/verify-results", json={
        "query": "ILO C181 recruitment fee Hong Kong domestic worker",
        "results": [
            {
                "title": "ILO C181 private employment agencies",
                "url": "https://www.ilo.org/example",
                "snippet": "C181 prohibits recruitment fees charged to workers.",
            },
            {
                "title": "Worker private phone number",
                "url": "https://example.com/post",
                "snippet": "Call +852 1234 5678 for the worker case.",
            },
        ],
    })
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["n_results"] == 2
    assert data["n_blocked"] == 1
    assert data["verified_results"][0]["source_quality"] == "high"
    assert data["verified_results"][0]["status"] == "accepted"
    assert data["blocked_results"][0]["deanonymization_risk"] == "high"


def test_post_search_verification_allows_generic_passport_topics(client):
    r = client.post("/api/search/verify-results", json={
        "query": "passport retention ILO indicator domestic worker",
        "results": [
            {
                "title": "ILO forced labour indicators",
                "url": "https://www.ilo.org/example",
                "snippet": "Retention of identity documents can be a forced labour indicator.",
            },
        ],
    })
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["n_blocked"] == 0
    assert data["verified_results"][0]["deanonymization_risk"] == "low"


def test_shared_workflow_helper_serves(client):
    r = client.get("/static/_workflow.js")
    assert r.status_code == 200
    text = r.text
    assert "window.dcWorkflow" in text
    assert "createStepper" in text
    assert "completeWhen" in text
    assert "stateIdFor" in text


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
    assert "use_gemma: false" in text
    assert "avoids long tunnel waits" in text
    assert "searchSaveOneDraft" in text
    assert "body: JSON.stringify(envelope)" in text
    assert 'id="search-step-query" open' in text
    assert "What this workflow does" in text
    assert "Search does not require Gemma" in text
    assert "Result-to-knowledge path" in text
    assert "deeper Gemma drafting belongs in Knowledge Extraction" in text
    assert "Current phone numbers" in text
    assert 'id="results-card"' in text
    assert 'id="drafts-card"' in text
    assert 'id="search-activity-card"' in text
    assert "searchGetLog" in text
    assert "Draft from all results" in text
    assert "Download evidence set" in text
    assert 'id="search-draft-progress"' in text
    assert "HK EA enforcement" in text
    assert "DMW anti-illegal recruitment" in text
    assert "Financial crime typology" in text
    assert "Retaliation after complaint" in text
    assert "Current commission cap" in text
    assert "HK ID 407" in text
    assert "POEA zero fee" in text
    assert "Unified demo story" in text
    assert "searchReadJsonOrText" in text
    assert "returned non-JSON" in text
    assert "Drafting moved to Step 3" in text
    assert "search-step-actions" in text
    assert "function searchSetWorkflow" in text
    assert '/static/_workflow.js' in text
    assert "window.dcWorkflow.createStepper" in text
    assert 'id="search-pipeline"' not in text
    assert 'id="search-step-log"' not in text
    assert "searchSendToShare" not in text


def test_knowledge_page_uses_guided_auto_suggestion_flow(client):
    r = client.get("/static/knowledge.html")
    assert r.status_code == 200
    text = r.text
    assert "Auto-suggest useful leaves" in text
    assert "Advanced: manual authoring for specialized leaf types" in text
    assert "kxToggleTaxonomy" in text
    assert "out.suggestions" in text
    assert 'id="kx-step-source" open' in text
    assert 'id="kx-step-draft"' in text
    assert 'id="kx-step-pack"' in text
    assert "Import or export knowledge files" in text
    assert "Import ZIP" in text
    assert "Export knowledge_files.zip" in text
    assert "Download sample bundle" not in text
    assert "Open Anonymization &amp; Sharing" not in text
    assert "extracted_fact: non-PII trend fact" in text
    assert "entity_signal: organization or actor signal" in text
    assert "modus_operandi: generalized abuse pattern" in text
    assert "evaluation_knowledge" in text
    assert "evaluation_dimension" in text
    assert "evaluation_prompt" in text
    assert "evaluation_metric" in text
    assert "evaluation_weighting" in text
    assert "/api/knowledge/type-catalog" in text
    assert "What this workflow does" in text
    assert "Continue to draft" in text
    assert "Upload a source bundle or add source text" in text
    assert 'id="kx-source-file-input"' in text
    assert "POST /api/process/batch" in text
    assert "case_files_media_rich_sample.zip" in text
    assert "kxUseSourceSample" in text
    assert "kxPollProcessJob" in text
    assert "kxLoadSourceFile" in text
    assert "kxBuildTextFromProcessBundle" in text
    assert "knowledge files" in text
    assert "Next: draft suggestions" not in text
    assert "Draft knowledge objects" in text
    assert "Finish review" in text
    assert "Promote draft" in text
    assert "kxPromotedDrafts" in text
    assert "function kxContinueToDraft" in text
    assert "function kxFinishDraftReview" in text
    assert "function kxOpenPackImport" in text
    assert "function kxSetWorkflow" in text
    assert '/static/_workflow.js' in text
    assert "window.dcWorkflow.createStepper" in text
    assert "let _dcLog = null" in text
    assert "window.addEventListener('DOMContentLoaded', wbGetLog)" in text
    assert "Model required before knowledge drafting" in text
    assert "Draft prompt path" in text
    assert "never treated as automatic truth" in text
    assert "Small text models work best" in text
    assert "media-derived claims should stay" in text
    assert "Extraction harness path" not in text


def test_knowledge_source_file_endpoint_parses_upload(client):
    payload = (
        "case_id,agency,note\n"
        "DC-PH-HK-001,Pearl Bridge Manpower,"
        "Worker paid PHP 45000 processing fee and salary deduction was proposed\n"
    )
    r = client.post(
        "/api/knowledge/source-file",
        files={"file": ("source.csv", payload.encode("utf-8"), "text/csv")},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["filename"] == "source.csv"
    assert data["n_rows_included"] >= 1
    assert "Knowledge source upload: source.csv" in data["raw_text"]
    assert "PHP 45000" in data["raw_text"]
    assert data["row_summaries"]


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
    assert {"rag_doc", "grep_rule", "fact_template", "extracted_fact", "modus_operandi"}.issubset(data["suggested_types"])
    assert len(data["suggestions"]) >= 3
    by_type = {e["knowledge_object_type"]: e for e in data["suggestions"]}
    assert "aggregation_keys" in by_type["extracted_fact"]["content"]
    assert "fields" in by_type["fact_template"]["content"]


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
    assert "Upload source bundle or knowledge files" in text
    assert "gemma_review: true" in text
    assert "Gemma privacy review" in text
    assert "optionally Gemma-review selected items" in text
    assert "Gemma privacy review is a second local check" in text
    assert "human review remains required" in text
    assert "knowledge_files_sample.zip" in text
    assert "case_files_media_rich_sample.zip" in text
    assert '/static/_activity_log.js' in text
    assert '/static/_workflow.js' in text
    assert "window.dcWorkflow.createStepper" in text
    assert "function wbGetLog" in text


def test_contacts_api_exposes_versioned_last_verified_dates(client):
    r = client.get("/api/contacts")
    assert r.status_code == 200
    data = r.json()
    assert data["version"]
    assert data["last_updated"]
    assert data["entries"]
    assert all("last_verified_at" in entry for entry in data["entries"])
    assert all(entry.get("knowledge_pack_version") == data["version"] for entry in data["entries"])


def test_anonymization_endpoint_can_run_gemma_privacy_review():
    from duecare.chat.app import create_app

    calls = []

    def gemma_call(messages, **kwargs):
        calls.append((messages, kwargs))
        return '{"overall_status":"pass","findings":[],"recommended_action":"submit"}'

    local = TestClient(create_app(gemma_call=gemma_call))
    r = local.post("/api/anonymize", json={
        "texts": ["Worker Maria called +852 1234 5678 about PHP 45000."],
        "gemma_review": True,
    })
    assert r.status_code == 200, r.text
    data = r.json()
    assert calls
    assert data["gemma_review"]["status"] == "ok"
    assert data["gemma_review"]["overall_status"] == "pass"
    assert "<PHONE_" in data["redacted"][0]


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
    assert "/static/_workflow.js" in text
    assert "syncGetWorkflowStepper" in text
    assert "function wbGetLog" in text


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
    assert "BM25 is the responsive default path" in text
    assert "Hybrid dense/RRF" in text
    assert "CPU rerank remain available" in text
    assert "Search is optional and must remain downstream of search safety sanitization" in text
    assert "one-model Kaggle session constraint" in text
    assert "function settingsSetStep" in text


def test_retrieval_defaults_are_demo_safe(client):
    r = client.get("/api/retrieval/config")
    assert r.status_code == 200
    data = r.json()
    assert data["profile"] == "demo-safe bm25 default"
    assert data["retrieval_mode"] == "bm25"
    assert data["effective_mode"] == "bm25"
    assert data["rerank_enabled"] is False
    assert data["rerank_top_k"] == 24
    assert data["rerank_keep"] == 6
    assert data["dense_top_k"] == 16


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
    assert "What this workflow does" in text
    assert "Drop a bundle or use the sample" in text
    assert 'id="wb-step-process"' in text
    assert 'id="wb-step-intelligence"' in text
    assert 'id="wb-step-export"' in text
    assert "#wb-results { display: grid; gap: 16px; }" in text
    assert 'id="wb-process-progress-fill"' in text
    assert 'id="wb-process-progress-note"' in text
    assert 'id="wb-process-substeps"' in text
    assert "const WB_PROCESS_STAGES" in text
    assert "Uploading bundle to Kaggle kernel" in text
    assert "Queueing OCR and media work" in text
    assert "Still working locally" in text
    assert "function wbStartProcessProgressLoop" in text
    assert "function wbStopProcessProgressLoop" in text
    assert 'id="wb-confirm-intel-btn"' in text
    assert "function wbConfirmIntelligence" in text
    assert "Reviewer verification checklist" in text
    assert "Confirm extracted intelligence before downloading" in text
    assert "function wbRequireConfirmedNavigation" in text
    assert "Deterministic fallback" in text
    assert "Deterministic brief; Gemma/media deferred" in text
    assert "fine-tuned Gemma 4" in text
    assert "document classification" in text
    assert "graph-edge generation" in text
    assert "/api/process/batch/start" in text
    assert "/api/process/batch/status/" in text
    assert "Use primary sample" in text
    assert 'id="wb-activity-card"' in text
    assert '/static/_workflow.js' in text
    assert "function wbGetWorkflowStepper" in text
    assert "window.dcWorkflow.createStepper" in text
    assert "let _dcLog = null" in text
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


def test_process_case_brief_calls_gemma_with_message_contract():
    from types import SimpleNamespace

    from duecare.chat.harnesses.process.handler import _gemma_case_brief

    calls = []

    def gemma_call(messages, **kwargs):
        calls.append((messages, kwargs))
        return (
            '{"case_theory":"fee camouflage","priority_people":[],'
            '"risk_clusters":[],"missing_evidence":[],'
            '"recommended_questions":[]}'
        )

    app = SimpleNamespace(state=SimpleNamespace(gemma_call=gemma_call))
    out = _gemma_case_brief(app, {"summary": {}}, {"people": []})

    assert out["status"] == "ok"
    assert calls
    assert isinstance(calls[0][0], list)
    assert calls[0][0][0]["role"] == "user"


def test_chat_page_uses_shared_model_selector(client):
    r = client.get("/static/chat.html")
    assert r.status_code == 200
    text = r.text
    assert "function openModelPickerFromUI" in text
    assert "window.dcWbOpenModelSelector" in text
    assert "Open model selector" in text
    assert "align-items: center; justify-content: center;" in text
    assert "max-height: min(820px, calc(100dvh - 32px));" in text
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
