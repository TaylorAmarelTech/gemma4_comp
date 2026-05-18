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


def test_process_batch_returns_intelligence_for_streamlined_demo():
    from duecare.chat.app import create_app

    client = TestClient(create_app())
    sample = (
        Path(__file__).parents[1]
        / "src"
        / "duecare"
        / "chat"
        / "static"
        / "samples"
        / "case_files_streamlined_demo.zip"
    )
    data = sample.read_bytes()
    resp = client.post(
        "/api/process/batch",
        files={"file": ("case_files_streamlined_demo.zip", io.BytesIO(data), "application/zip")},
        data={"review_mode": "quick_triage", "max_gemma_calls": "8"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    summary = body["summary"]
    intel = body["intelligence"]
    assert summary["n_rows_processed"] >= 7
    assert summary["n_rows_processed"] <= 12
    assert intel["n_people"] >= 1
    assert intel["n_evidence_edges"] >= 8
    assert intel["n_typed_edges"] >= intel["n_evidence_edges"]
    assert intel["rag_candidates"]
    assert intel["processing_plan"]["review_mode"]["id"] == "quick_triage"
    assert intel["processing_plan"]["gemma_budget"]["max_gemma_calls"] == 8
    joined = "\n".join(
        (edge.get("label") or "") + " " + ((edge.get("evidence") or {}).get("quote") or "")
        for edge in intel["typed_edges"]
    ).lower()
    assert "php 45,500" in joined or "45500" in joined
    assert "salary" in joined or "deduct" in joined
    assert any(p["stage"] == "payment_and_debt" for p in intel["journey_points"])


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
    assert body["config"]["gemma_case_brief"] == "deterministic_deferred_model"
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

    start = client.post(
        "/api/process/graph-extract/start",
        json={"prompt_id": "case_graph_edges", "limit": 12},
    )
    assert start.status_code == 200, start.text
    job_id = start.json()["job_id"]
    for _ in range(20):
        poll = client.get(f"/api/process/graph-extract/status/{job_id}")
        assert poll.status_code == 200, poll.text
        job = poll.json()
        if job["status"] == "complete":
            break
        time.sleep(0.05)
    else:
        raise AssertionError("graph-extract job did not complete")
    assert job["result"]["status"] == "deterministic_no_model"
    assert job["result"]["typed_edges"]
    assert len(job["events"]) >= 3
    assert any(evt["phase"] == "seed_edges" for evt in job["events"])


def test_process_background_job_calls_loaded_gemma_for_brief_and_edges():
    from duecare.chat.app import create_app

    calls = []

    def gemma_call(messages, **kwargs):
        text = "\n".join(
            part.get("text", "")
            for msg in messages
            for part in (msg.get("content") or [])
            if isinstance(part, dict)
        )
        calls.append({"text": text, "kwargs": kwargs})
        if "case_theory" in text and "priority_people" in text:
            return (
                '{"case_theory":"Model-authored case brief",'
                '"priority_people":[],"risk_clusters":["fee camouflage"],'
                '"missing_evidence":[],"recommended_questions":["Which rows support fees?"]}'
            )
        return (
            '{"edges":[{"edge_type":"fee_camouflage_evidence",'
            '"source_node":"person:worker","target_node":"fee:training",'
            '"row_id":"row-1","label":"training fee",'
            '"evidence":{"quote":"training fee PHP 45000"},'
            '"confidence":0.82}],"rag_candidates":[],"uncertainties":[]}'
        )

    sample = (
        Path(__file__).parents[1]
        / "src"
        / "duecare"
        / "chat"
        / "static"
        / "samples"
        / "case_files_streamlined_demo.zip"
    )
    client = TestClient(create_app(gemma_call=gemma_call))
    start = client.post(
        "/api/process/batch/start",
        data={
            "review_mode": "quick_triage",
            "max_gemma_calls": "3",
            "gemma_calls_per_item": "1",
            "run_inline_gemma_text": "true",
        },
        files={"file": (sample.name, io.BytesIO(sample.read_bytes()), "application/zip")},
    )
    assert start.status_code == 200, start.text
    job_id = start.json()["job_id"]
    final = None
    for _ in range(80):
        poll = client.get(f"/api/process/batch/status/{job_id}")
        assert poll.status_code == 200, poll.text
        body = poll.json()
        if body.get("status") in {"complete", "error"}:
            final = body
            break
        time.sleep(0.05)
    assert final is not None
    assert final["status"] == "complete", final
    bundle = final["result"]
    summary = bundle["summary"]
    intel = bundle["intelligence"]
    assert len(calls) >= 2
    assert summary["gemma_model_loaded"] is True
    assert summary["n_gemma_calls_attempted"] >= 2
    assert summary["gemma_case_brief_status"] == "ok"
    assert summary["gemma_edge_pass_status"] == "ok"
    assert summary["n_model_proposed_edges"] == 1
    assert intel["gemma_case_brief"]["deferred"] is False
    assert intel["gemma_edge_pass"]["model_edges"][0]["edge_type"] == "fee_camouflage_evidence"
    trace = {step["id"]: step for step in intel["harness_trace"]}
    assert trace["gemma_text"]["status"] == "complete"
    assert "model_calls_attempted" in trace["gemma_text"]["detail"]


def test_process_batch_start_defers_gemma_by_default_even_when_model_loaded():
    """The async upload endpoint powers the recording UI. It must not
    block at the Gemma case-brief phase merely because a model is loaded;
    model-backed passes are explicit follow-up work unless the request
    opts into inline Gemma text processing.
    """
    from duecare.chat.app import create_app

    calls = []

    def gemma_call(messages, **kwargs):
        calls.append((messages, kwargs))
        return '{"case_theory":"should not be called"}'

    sample = (
        Path(__file__).parents[1]
        / "src"
        / "duecare"
        / "chat"
        / "static"
        / "samples"
        / "case_files_streamlined_demo.zip"
    )
    client = TestClient(create_app(gemma_call=gemma_call))
    start = client.post(
        "/api/process/batch/start",
        data={"review_mode": "quick_triage", "max_gemma_calls": "12", "gemma_calls_per_item": "1"},
        files={"file": (sample.name, io.BytesIO(sample.read_bytes()), "application/zip")},
    )
    assert start.status_code == 200, start.text
    job_id = start.json()["job_id"]
    final = None
    for _ in range(80):
        poll = client.get(f"/api/process/batch/status/{job_id}")
        assert poll.status_code == 200, poll.text
        body = poll.json()
        if body.get("status") in {"complete", "error"}:
            final = body
            break
        time.sleep(0.05)
    assert final is not None
    assert final["status"] == "complete", final
    assert calls == []
    bundle = final["result"]
    assert bundle["summary"]["gemma_model_loaded"] is True
    assert bundle["summary"]["n_gemma_calls_attempted"] == 0
    assert bundle["summary"]["gemma_case_brief_status"] == "deterministic_deferred_model"
    detail = bundle["intelligence"]["gemma_case_brief"]["detail"]
    assert "inline Gemma text passes disabled" in detail
    assert bundle["config"]["process_settings"]["run_inline_gemma_text"] is False


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


def test_process_graph_chat_answers_fee_camouflage_and_provider_choice():
    """The demo's flagship question must trip a dedicated deterministic
    branch that names both signal families, surfaces the available
    proxy edges from the bundle, and points the reviewer at the
    optional Gemma edge pass for explicit upgrade."""
    from duecare.chat.app import create_app

    samples = Path(__file__).resolve().parents[1] / "src" / "duecare" / "chat" / "static" / "samples"
    bundle_path = samples / "case_files_streamlined_demo.zip"
    data = bundle_path.read_bytes()

    client = TestClient(create_app())
    upload = client.post(
        "/api/process/batch",
        files={"file": ("case_files_streamlined_demo.zip", io.BytesIO(data), "application/zip")},
    )
    assert upload.status_code == 200, upload.text

    question = "Which rows support fee camouflage and restricted provider choice?"
    reply = client.post("/api/process/graph-chat", json={"question": question})
    assert reply.status_code == 200, reply.text
    body = reply.json()
    assert body["analysis_kind"] == "fee_camouflage_and_provider_choice"
    answer = body["answer"]
    assert "Fee camouflage candidates" in answer
    assert "Restricted provider choice candidates" in answer
    assert "Gemma edge pass" in answer
    assert "fee_camouflage_evidence" in answer
    assert "provider_choice_restriction" in answer


def test_process_batch_completion_detail_honestly_reports_queued_media():
    """When the batch worker completes at pct=100 the detail must
    honestly reflect queued OCR/Gemma vision items rather than imply
    the multimodal work is finished."""
    from duecare.chat.app import create_app

    samples = Path(__file__).resolve().parents[1] / "src" / "duecare" / "chat" / "static" / "samples"
    media_rich = samples / "case_files_media_rich_sample.zip"
    data = media_rich.read_bytes()

    client = TestClient(create_app())
    start = client.post(
        "/api/process/batch/start",
        files={"file": ("case_files_media_rich_sample.zip", io.BytesIO(data), "application/zip")},
    )
    assert start.status_code == 200, start.text
    job_id = start.json()["job_id"]

    final = None
    for _ in range(120):
        poll = client.get(f"/api/process/batch/status/{job_id}")
        body = poll.json()
        if body.get("status") in {"complete", "error"}:
            final = body
            break
        time.sleep(0.1)
    assert final is not None
    assert final["status"] == "complete"
    assert final["pct"] == 100

    events = final.get("events") or []
    # The worker emits a final completion event with status="complete"
    # AFTER the inner deterministic-parse marker. Walk the events in
    # reverse so the final completion (with the truthful media-queued
    # detail) is selected.
    complete_event = next(
        (
            e for e in reversed(events)
            if e.get("status") == "complete" and e.get("pct") == 100
        ),
        None,
    )
    assert complete_event is not None, "final completion event missing"
    detail = str(complete_event.get("detail") or "")
    media_queued = int(complete_event.get("media_assets_queued") or 0)
    assert "Deterministic parsing complete" in detail
    if media_queued:
        assert "media asset" in detail
        assert "OCR or Gemma 4 vision review" in detail
    else:
        assert "no media items queued" in detail


def test_graph_chat_deterministic_branch_uses_typed_edges_only():
    """The fee_camouflage / provider_choice branch must not invent
    edges. The answer must cite only rows that come from typed_edges
    or people.risk_signals on the bundle."""
    from duecare.chat.harnesses.process.handler import _graph_chat_deterministic_answer

    bundle = {
        "intelligence": {
            "typed_edges": [
                {
                    "edge_type": "fee_amount_observed",
                    "row_id": "row-A",
                    "label": "$3,000 placement fee",
                    "evidence": {"quote": "Recruiter says training fee $3,000."},
                },
                {
                    "edge_type": "salary_deduction_signal",
                    "row_id": "row-B",
                    "label": "wage deduction",
                    "evidence": {"quote": "$50/month deduction for transport."},
                },
                {
                    "edge_type": "journey_stage_observation",
                    "row_id": "row-C",
                    "label": "recruitment",
                    "evidence": {"quote": "Agency arranged everything."},
                },
            ],
            "people": [
                {
                    "case_id": "CASE-1",
                    "name": "Composite Worker",
                    "risk_signals": ["single_provider_agency_control"],
                    "row_ids": ["row-D", "row-payment-001"],
                },
            ],
        },
        "summary": {},
    }

    result = _graph_chat_deterministic_answer(
        bundle,
        "Which rows support fee camouflage and restricted provider choice?",
    )
    assert result is not None
    assert result["analysis_kind"] == "fee_camouflage_and_provider_choice"
    cited = result["cited_rows"]
    allowed = {"row-A", "row-B", "row-C", "row-D", "row-payment-001"}
    assert all(r in allowed for r in cited), cited
    assert "row-A" in cited or "row-B" in cited
    assert any(r in cited for r in ("row-C", "row-D", "row-payment-001"))
