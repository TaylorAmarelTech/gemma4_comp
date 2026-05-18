from __future__ import annotations

import io
import time
import zipfile
from pathlib import Path

from fastapi.testclient import TestClient


def test_case_files_sample_has_ph_hk_bulk_review_depth():
    sample = (
        Path(__file__).parents[1]
        / "src"
        / "duecare"
        / "chat"
        / "static"
        / "samples"
        / "case_files_sample.zip"
    )
    assert sample.exists()
    with zipfile.ZipFile(sample) as zf:
        names = zf.namelist()
        case_ids = set()
        for name in names:
            if name.endswith("/"):
                continue
            text = zf.read(name).decode("utf-8", errors="replace")
            for i in range(1, 31):
                marker = f"DC-PH-HK-{i:03d}"
                if marker in text or marker.lower() in name.lower():
                    case_ids.add(marker)
        assert len(case_ids) == 30
        for required_dir in [
            "id_cards/",
            "complaints/",
            "police_reports/",
            "travel_history/",
            "location_history/",
            "payment_history/",
            "chats/",
        ]:
            assert any(required_dir in n for n in names)
        assert sum(n.lower().endswith(".png") for n in names) >= 18
        assert sum(n.lower().endswith(".jpg") for n in names) >= 12
        assert sum(n.lower().endswith(".jpeg") for n in names) >= 10
        assert sum(n.lower().endswith(".pdf") for n in names) >= 10
        assert sum(n.lower().endswith(".docx") for n in names) >= 12
        assert sum(n.lower().endswith(".doc") for n in names) >= 4
        assert sum(n.lower().endswith(".xlsx") for n in names) >= 5
        assert sum(n.lower().endswith(".eml") for n in names) >= 4
        assert sum(n.lower().endswith(".html") for n in names) >= 2
        assert any("facebook_messenger/" in n for n in names)
        assert any("receipt_photos/" in n for n in names)
        assert any(n.startswith("case_folders/") for n in names)


def test_case_files_media_rich_sample_has_messy_intake_depth():
    sample = (
        Path(__file__).parents[1]
        / "src"
        / "duecare"
        / "chat"
        / "static"
        / "samples"
        / "case_files_media_rich_sample.zip"
    )
    assert sample.exists()
    with zipfile.ZipFile(sample) as zf:
        names = [n for n in zf.namelist() if not n.endswith("/")]
        assert len(names) < 300
        assert any(n.startswith("media_rich_cases/") for n in names)
        assert "00_reference_sources/official_source_catalog.json" in names
        assert "00_demo_story/UNIFIED_DEMO_STORY.md" in names
        assert "expected_outputs/strongest_cases_expected.json" in names
        assert "expected_outputs/overcharging_entities_expected.json" in names
        assert "public_records_synthetic/public_record_source_candidates.json" in names
        assert any(n.startswith("calibration_cases/clean_compliant/") for n in names)
        assert any(n.startswith("calibration_cases/borderline_incomplete/") for n in names)
        assert any(n.startswith("calibration_cases/false_positive_bait/") for n in names)
        assert any(n.endswith(".mbox") for n in names)
        assert any(n.endswith(".tiff") for n in names)
        assert any(n.endswith(".webp") for n in names)
        assert any(n.endswith(".heic") for n in names)
        assert any(n.endswith(".opus") for n in names)
        assert any(n.endswith(".m4a") for n in names)
        assert any(n.endswith(".odt") for n in names)
        assert any(n.endswith("phone_export_nested.zip") for n in names)
        for marker in [
            "facebook_messenger/",
            "whatsapp_retaliation",
            "receipt_photo",
            "passport_page_photo",
            "worker_intake",
            "employment_contract_extractable",
            "receipt_scan_ocr_needed",
            "legacy_case_note",
            "email_handoff",
            "payment_schedule",
            "travel_location_timeline",
            "unparsed_binary",
        ]:
            assert any(marker in n for n in names)
        assert sum(n.lower().endswith(".png") for n in names) >= 12
        assert sum(n.lower().endswith(".jpg") for n in names) >= 12
        assert sum(n.lower().endswith(".jpeg") for n in names) >= 6
        assert sum(n.lower().endswith(".pdf") for n in names) >= 12
        assert sum(n.lower().endswith(".docx") for n in names) >= 6
        assert sum(n.lower().endswith(".doc") for n in names) >= 6
        assert sum(n.lower().endswith(".xlsx") for n in names) >= 6
        assert sum(n.lower().endswith(".eml") for n in names) >= 6
        assert sum(n.lower().endswith(".pptx") for n in names) >= 3
        assert sum(n.lower().endswith(".msg") for n in names) >= 3
        with zf.open("public_records_synthetic/README.md") as handle:
            assert "do not embed the document" in handle.read().decode("utf-8")


def test_process_batch_returns_intelligence_for_sample():
    from duecare.chat.app import create_app

    sample = (
        Path(__file__).parents[1]
        / "src"
        / "duecare"
        / "chat"
        / "static"
        / "samples"
        / "case_files_sample.zip"
    )
    client = TestClient(create_app())
    data = sample.read_bytes()
    response = client.post(
        "/api/process/batch",
        files={"file": ("case_files_sample.zip", io.BytesIO(data), "application/zip")},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    intel = body["intelligence"]
    assert body["summary"]["n_people_detected"] == 30
    assert body["summary"]["truncated"] is False
    assert intel["n_people"] == 30
    assert intel["n_documents"] >= 295
    assert intel["document_type_counts"]["id_card"] == 30
    assert intel["document_type_counts"]["payment_history"] >= 30
    assert intel["document_type_counts"]["chat_messages"] == 30
    assert intel["document_type_counts"]["media_image"] >= 50
    assert intel["document_type_counts"]["scanned_pdf"] >= 10
    assert body["staging"]["bytes"] == len(data)
    assert body["staging"]["sha256"]
    assert body["config"]["gemma_case_brief"] == "deferred"
    assert intel["gemma_case_brief"]["status"] == "deterministic_deferred_model"
    assert intel["gemma_case_brief"]["deferred"] is True
    assert len(intel["harness_trace"]) >= 5
    assert any(step["id"] == "stage" for step in intel["harness_trace"])
    assert intel["top_risk_signals"]
    assert not any(s["signal"] == "?" for s in intel["top_risk_signals"])
    assert intel["folder_counts"]
    assert intel["processing_plan"]["n_media_assets"] >= 60
    assert intel["n_evidence_edges"] > 100
    assert intel["n_typed_edges"] > intel["n_evidence_edges"]
    assert intel["typed_edges"]
    first_typed = intel["typed_edges"][0]
    assert first_typed["schema_version"] == "duecare.process.typed_edge.v1"
    assert first_typed["local_only"] is True
    assert first_typed["review_status"] == "needs_review"
    assert {"source_node", "target_node", "evidence", "extractors"}.issubset(first_typed)
    assert intel["typed_edge_counts"]
    assert intel["rag_candidates"]
    assert intel["processing_plan"]["local_processing_contract"]["remote_api_calls"] is False
    assert intel["processing_plan"]["scalable_queue_contract"]["batching_policy"]["queue_large_archives"] is True
    assert intel["processing_plan"]["review_mode"]["id"] == "standard_review"
    assert intel["processing_plan"]["gemma_budget"]["max_gemma_calls"] == 75
    assert intel["processing_plan"]["model_capability_notes"]
    assert {
        "deterministic_processing",
        "text_edge_pass",
        "multimodal_page_review",
        "exhaustive_review",
        "finetuned_document_classifier",
    }.issubset({n["capability"] for n in intel["processing_plan"]["model_capability_notes"]})
    assert intel["processing_plan"]["edge_quality_dimensions"]
    assert intel["processing_plan"]["pointed_edge_questions"]
    edge_quality_ids = {d["id"] for d in intel["processing_plan"]["edge_quality_dimensions"]}
    assert {
        "source_grounding_per_edge",
        "typed_relation_specificity",
        "payment_fee_completeness",
        "document_and_movement_control",
        "coercion_threat_retaliation",
        "cross_document_alias_linking",
        "pii_minimization_for_candidates",
    }.issubset(edge_quality_ids)
    assert intel["processing_plan"]["page_item_prompt_tree"]
    assert {
        "classify",
        "target_fee_payment",
        "target_chat",
        "target_contract",
        "cross_document_link",
        "knowledge_candidate",
    }.issubset({p["phase"] for p in intel["processing_plan"]["page_item_prompt_tree"]})
    assert intel["processing_plan"]["knowledge_context"]["local_only"] is True
    assert any(
        t["id"] == "case_graph_edges"
        for t in intel["processing_plan"]["gemma_edge_prompt_templates"]
    )
    assert intel["graph"]["schema_version"] == "duecare.process.graph.v1"
    assert intel["graph"]["meta"]["n_nodes"] > 20
    assert any(n["group"] == "folder" for n in intel["graph"]["nodes"])
    assert any(e["edge_type"] == "folder_context" for e in intel["evidence_edges"])
    assert "file_structure" in {
        method["id"] for method in intel["processing_plan"]["analysis_methods"]
    }
    assert "typed_graph_edges" in {
        method["id"] for method in intel["processing_plan"]["analysis_methods"]
    }
    assert intel["journey_points"]
    assert intel["critical_fee_points"]
    stages = {point["stage"] for point in intel["journey_points"]}
    assert {"payment_and_debt", "travel"}.issubset(stages)
    assert len(stages) >= 3

    chat = client.post(
        "/api/process/graph-chat",
        json={
            "question": (
                "Which individuals have the strongest cases to move forward "
                "first, and what row IDs support that ranking?"
            )
        },
    )
    assert chat.status_code == 200, chat.text
    chat_body = chat.json()
    assert chat_body["analysis_kind"] == "fee_or_priority_ranking"
    assert chat_body["cited_rows"]
    assert "The user is asking" not in chat_body["answer"]
    assert "|---" not in chat_body["answer"]

    edge_pass = client.post(
        "/api/process/graph-extract",
        json={"prompt_id": "case_graph_edges", "limit": 12},
    )
    assert edge_pass.status_code == 200, edge_pass.text
    edge_body = edge_pass.json()
    assert edge_body["status"] == "deterministic_no_model"
    assert edge_body["remote_api_calls"] is False
    assert edge_body["typed_edges"]
    assert edge_body["rag_candidates"]
    assert edge_body["page_item_prompt_tree"]
    assert edge_body["edge_quality_dimensions"]
    assert edge_body["pointed_edge_questions"]
    assert any(d["id"] == "uncertainty_review_status" for d in edge_body["edge_quality_dimensions"])
    assert edge_body["model_capability_notes"]
    assert edge_body["knowledge_context"]["local_only"] is True
    assert any(t["id"] == "case_graph_edges" for t in edge_body["prompt_templates"])


def test_process_batch_accepts_review_mode_settings():
    from duecare.chat.app import create_app

    sample = (
        Path(__file__).parents[1]
        / "src"
        / "duecare"
        / "chat"
        / "static"
        / "samples"
        / "case_files_media_rich_sample.zip"
    )
    client = TestClient(create_app())
    response = client.post(
        "/api/process/batch",
        data={
            "review_mode": "quick_triage",
            "runtime_budget_minutes": "5",
            "max_gemma_calls": "12",
            "gemma_calls_per_item": "1",
            "edge_strictness": "conservative",
            "generate_knowledge_candidates": "false",
            "include_imported_knowledge": "false",
            "page_item_types": '["text_block","receipt"]',
        },
        files={"file": (sample.name, io.BytesIO(sample.read_bytes()), "application/zip")},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    settings = body["config"]["process_settings"]
    plan = body["intelligence"]["processing_plan"]
    assert settings["review_mode"]["id"] == "quick_triage"
    assert settings["max_gemma_calls"] == 12
    assert settings["generate_knowledge_candidates"] is False
    assert settings["include_imported_knowledge"] is False
    assert settings["page_item_types"] == ["text_block", "receipt"]
    assert plan["gemma_budget"]["knowledge_candidates_enabled"] is False
    assert plan["knowledge_context"]["disabled_by_settings"] is True
    assert plan["page_item_prompt_tree"][0]["prompt_id"] == "page_item_classification"


def test_process_batch_returns_intelligence_for_media_rich_sample():
    from duecare.chat.app import create_app

    sample = (
        Path(__file__).parents[1]
        / "src"
        / "duecare"
        / "chat"
        / "static"
        / "samples"
        / "case_files_media_rich_sample.zip"
    )
    client = TestClient(create_app())
    response = client.post(
        "/api/process/batch",
        files={"file": (sample.name, io.BytesIO(sample.read_bytes()), "application/zip")},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    intel = body["intelligence"]
    assert body["summary"]["n_people_detected"] >= 6
    assert body["summary"]["truncated"] is False
    assert intel["n_documents"] >= 110
    assert intel["document_type_counts"]["media_image"] >= 30
    assert intel["document_type_counts"]["scanned_pdf"] >= 12
    assert intel["document_type_counts"]["payment_history"] >= 6
    assert intel["document_type_counts"]["chat_messages"] >= 6
    assert intel["processing_plan"]["n_media_assets"] >= 50
    assert intel["n_typed_edges"] >= intel["n_evidence_edges"]
    assert "media_requires_gemma_vision" in {c["edge_type"] for c in intel["typed_edge_counts"]}
    assert any(c["knowledge_object_type"] in {"modus_operandi", "fact_template"} for c in intel["rag_candidates"])
    assert intel["top_risk_signals"]
    assert not any(s["signal"] == "?" for s in intel["top_risk_signals"])
    assert any("media_rich_cases" in edge.get("source_path", "") for edge in intel["evidence_edges"])
    stages = {point["stage"] for point in intel["journey_points"]}
    assert {"recruitment", "payment_and_debt", "travel", "documents_and_identity"}.issubset(stages)


def test_process_batch_async_job_returns_media_rich_result():
    from duecare.chat.app import create_app

    sample = (
        Path(__file__).parents[1]
        / "src"
        / "duecare"
        / "chat"
        / "static"
        / "samples"
        / "case_files_media_rich_sample.zip"
    )
    client = TestClient(create_app())
    start = client.post(
        "/api/process/batch/start",
        files={"file": (sample.name, io.BytesIO(sample.read_bytes()), "application/zip")},
    )
    assert start.status_code == 200, start.text
    job_id = start.json()["job_id"]
    status = None
    for _ in range(20):
        poll = client.get(f"/api/process/batch/status/{job_id}")
        assert poll.status_code == 200, poll.text
        status = poll.json()
        if status["status"] == "complete":
            break
        time.sleep(0.05)
    assert status is not None
    assert status["status"] == "complete"
    assert status["pct"] == 100
    assert status["events"]
    assert any(e["phase"] == "parsing" for e in status["events"])
    body = status["result"]
    assert body["job_id"] == job_id
    assert body["config"]["processing_mode"] == "async_job"
    assert body["summary"]["n_people_detected"] >= 6
    assert body["intelligence"]["processing_plan"]["n_media_assets"] >= 50


def test_process_batch_surfaces_media_and_ocr_work_queue():
    from duecare.chat.app import create_app

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(
            "complaints/DC-PH-HK-999.txt",
            "worker_name: Test Person\n"
            "complaint date 2026-04-01. Recruiter demanded PHP 50000 placement fee.",
        )
        zf.writestr("scans/passport_page.png", b"\x89PNG\r\n\x1a\n" + b"\x00" * 64)
        zf.writestr("scans/contract.pdf", b"%PDF-1.7\n% synthetic scan placeholder\n")

    client = TestClient(create_app())
    response = client.post(
        "/api/process/batch",
        files={"file": ("mixed_media_bundle.zip", io.BytesIO(buf.getvalue()), "application/zip")},
    )
    assert response.status_code == 200, response.text
    intel = response.json()["intelligence"]
    plan = intel["processing_plan"]
    assert plan["n_media_assets"] == 2
    assert "n_pages" in plan
    assert {asset["media_type"] for asset in plan["media_assets"]} == {"image", "pdf"}
    assert all(asset["gemma_questions"] for asset in plan["media_assets"])
    assert any(p["id"] == "ocr" and p["status"] == "queued_contract" for p in plan["passes"])
    assert any(p["id"] == "gemma_multimodal" for p in plan["passes"])


def test_process_graph_chat_suppresses_plain_language_reasoning_leak():
    from duecare.chat.harnesses.process.handler import _looks_like_reasoning_leak

    leaked = (
        "The user is asking to identify people with the strongest evidence.\n\n"
        "1. Identify relevant information.\n"
        "2. Scan the summary for payment and debt signals."
    )
    assert _looks_like_reasoning_leak(leaked)
    assert not _looks_like_reasoning_leak(
        "People with strongest overcharging evidence:\n\n1. DC-PH-HK-001"
    )
