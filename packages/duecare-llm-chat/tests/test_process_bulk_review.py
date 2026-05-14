from __future__ import annotations

import io
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
            assert any(n.startswith(required_dir) for n in names)


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
    assert intel["n_people"] == 30
    assert intel["n_documents"] >= 180
    assert intel["document_type_counts"]["id_card"] == 30
    assert intel["document_type_counts"]["payment_history"] == 30
    assert intel["gemma_case_brief"]["status"] == "no_model_loaded"
    assert len(intel["harness_trace"]) >= 5
    assert intel["journey_points"]
    assert intel["critical_fee_points"]
    stages = {point["stage"] for point in intel["journey_points"]}
    assert {"payment_and_debt", "travel"}.issubset(stages)
    assert len(stages) >= 3


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
    assert any(p["id"] == "ocr" and p["status"] == "queued_contract" for p in plan["passes"])
    assert any(p["id"] == "gemma_multimodal" for p in plan["passes"])
