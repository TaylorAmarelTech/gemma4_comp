"""Integration tests for the DueCare demo FastAPI application."""

from __future__ import annotations

import io
import json
import zipfile

import pytest
from fastapi.testclient import TestClient

from src.demo.app import app


def _minimal_docx_bytes(text: str) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(
            "word/document.xml",
            (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
                '<w:body><w:p><w:r><w:t>'
                + text
                + "</w:t></w:r></w:p></w:body></w:document>"
            ),
        )
    return buffer.getvalue()


@pytest.fixture
def client():
    return TestClient(app)


class TestHealth:
    def test_health_returns_ok(self, client):
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["rubrics_loaded"] >= 1

    def test_root_returns_html(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]
        assert "DueCare" in resp.text


class TestDomains:
    def test_domains_lists_trafficking(self, client):
        resp = client.get("/api/v1/domains")
        assert resp.status_code == 200
        domains = resp.json()
        assert len(domains) >= 1
        assert any(d["id"] == "trafficking" for d in domains)


class TestRubrics:
    def test_rubrics_returns_five(self, client):
        resp = client.get("/api/v1/rubrics")
        assert resp.status_code == 200
        rubrics = resp.json()
        assert len(rubrics) == 5
        for r in rubrics:
            assert "name" in r
            assert "n_criteria" in r
            assert r["n_criteria"] > 0


class TestCaseExamples:
    def test_case_examples_routes_list_and_fetch_examples(self, client):
        resp = client.get("/api/v1/case-examples")
        assert resp.status_code == 200
        data = resp.json()
        ids = {item["id"] for item in data}
        assert {
            "employment_agency_case",
            "overcharging_case",
            "medical_clinic_case",
            "money_lender_case",
            "legal_packet_case",
        }.issubset(ids)

        example_resp = client.get("/api/v1/case-examples/medical_clinic_case")
        assert example_resp.status_code == 200
        example = example_resp.json()
        assert example["case_id"] == "case-medical-001"
        assert example["documents"][0]["context"] == "medical_record"

        legal_resp = client.get("/api/v1/case-examples/legal_packet_case")
        assert legal_resp.status_code == 200
        legal_example = legal_resp.json()
        assert legal_example["case_id"] == "case-legal-001"
        assert any(document["context"] == "legal_intake" for document in legal_example["documents"])


class TestAnalyze:
    def test_analyze_illegal_fee(self, client):
        resp = client.post("/api/v1/analyze", json={
            "text": "I need to pay 50000 PHP recruitment fee to my agency before working in Hong Kong.",
            "context": "chat",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "score" in data
        assert "grade" in data
        assert "action" in data
        assert "legal_refs" in data
        assert "resources" in data
        assert len(data["resources"]) > 0
        assert len(data["legal_refs"]) > 0

    def test_analyze_safe_text(self, client):
        resp = client.post("/api/v1/analyze", json={
            "text": "The weather is nice today.",
            "context": "chat",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["score"] >= 0.0

    def test_analyze_passport_retention(self, client):
        resp = client.post("/api/v1/analyze", json={
            "text": "Give me your passport, I will keep it safe during your employment.",
            "context": "chat",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "score" in data

    def test_analyze_returns_warning_text(self, client):
        resp = client.post("/api/v1/analyze", json={
            "text": "Workers must pay placement fees before departure.",
            "context": "job_posting",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "warning_text" in data


class TestBatch:
    def test_batch_analyze(self, client):
        resp = client.post("/api/v1/batch", json={
            "items": [
                {"text": "Pay 50000 PHP recruitment fee", "context": "chat"},
                {"text": "Normal job posting", "context": "job_posting"},
            ]
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "results" in data
        assert len(data["results"]) == 2


class TestStats:
    def test_stats_after_analysis(self, client):
        # Run one analysis first
        client.post("/api/v1/analyze", json={
            "text": "Test prompt for stats",
            "context": "chat",
        })
        resp = client.get("/api/v1/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_analyses" in data
        assert data["total_analyses"] >= 1


class TestDocumentAnalysis:
    def test_document_analysis_returns_structured_fields(self, client):
        resp = client.post(
            "/api/v1/analyze-document",
            json={
                "text": "Employment contract: Employer will retain the passport and deduct HKD 20000 over 7 months.",
                "context": "contract",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["document_type"] == "employment_contract"
        assert "passport_retention" in data["indicator_flags"]
        assert "worker_paid_placement_fee" in data["indicator_flags"]
        assert "amounts" in data["extracted_fields"]
        assert data["risk_level"] in {"HIGH", "MEDIUM", "LOW"}


class TestMigrationCaseWorkflow:
    def test_migration_case_route_builds_timeline_and_templates(self, client):
        resp = client.post(
            "/api/v1/migration-case",
            json={
                "case_id": "case-demo-001",
                "corridor": "PH_HK",
                "documents": [
                    {
                        "document_id": "doc-01",
                        "title": "Agency receipt",
                        "context": "receipt",
                        "captured_at": "2026-01-05",
                        "text": "Receipt for placement fee: HKD 20000 paid by worker before deployment.",
                    },
                    {
                        "document_id": "doc-02",
                        "title": "Employment contract",
                        "context": "contract",
                        "captured_at": "2026-01-12",
                        "text": "Employer will retain passport during contract period and deduct fees over 7 months.",
                    },
                    {
                        "document_id": "doc-03",
                        "title": "Recruiter chat",
                        "context": "chat",
                        "captured_at": "2026-01-15",
                        "text": "Pay the remaining fee now or you cannot leave. We will keep your passport until the debt is cleared.",
                    },
                ],
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["case_id"] == "case-demo-001"
        assert data["corridor"] == "PH_HK"
        assert data["document_count"] == 3
        assert data["timeline"]
        assert data["complaint_templates"]
        assert data["tool_results"]
        assert data["applicable_laws"]
        assert "employment_agency_misconduct" in data["case_categories"]
        assert "worker_paid_placement_fee" in data["detected_indicators"]
        assert any(template["name"] == "employment_agency_complaint" for template in data["complaint_templates"])
        assert any(template["name"] == "written_interrogatory_prep" for template in data["complaint_templates"])
        assert any(item["tool"] == "lookup_hotline" for item in data["tool_results"])

    @pytest.mark.parametrize(
        ("example_id", "expected_category", "expected_template"),
        [
            ("employment_agency_case", "employment_agency_misconduct", "employment_agency_complaint"),
            ("overcharging_case", "worker_fee_overcharge", "fee_overcharge_recovery_request"),
            ("medical_clinic_case", "medical_clinic_fee_abuse", "medical_clinic_fee_complaint"),
            ("money_lender_case", "money_lender_debt_pressure", "money_lender_debt_complaint"),
            ("legal_packet_case", "employment_agency_misconduct", "written_interrogatory_prep"),
        ],
    )
    def test_example_case_bundles_generate_targeted_templates(
        self,
        client,
        example_id,
        expected_category,
        expected_template,
    ):
        example_resp = client.get(f"/api/v1/case-examples/{example_id}")
        assert example_resp.status_code == 200

        resp = client.post("/api/v1/migration-case", json=example_resp.json())
        assert resp.status_code == 200
        data = resp.json()

        assert expected_category in data["case_categories"]
        assert any(template["name"] == expected_template for template in data["complaint_templates"])

    def test_legal_packet_case_surfaces_intake_and_government_docs(self, client):
        example_resp = client.get("/api/v1/case-examples/legal_packet_case")
        assert example_resp.status_code == 200

        resp = client.post("/api/v1/migration-case", json=example_resp.json())
        assert resp.status_code == 200
        data = resp.json()

        assert data["document_type_counts"]["government_letter"] >= 1
        assert data["document_type_counts"]["legal_intake_form"] >= 1
        assert any(template["name"] == "written_interrogatory_prep" for template in data["complaint_templates"])
        assert data["applicable_laws"]

    def test_migration_case_upload_route_parses_mixed_bundle(self, client):
        files = [
            (
                "files",
                (
                    "agency_receipt.txt",
                    b"Receipt for placement fee: HKD 20000 paid by worker before deployment.",
                    "text/plain",
                ),
            ),
            (
                "files",
                (
                    "recruiter_chat.json",
                    json.dumps(
                        {
                            "messages": [
                                {"sender": "recruiter", "text": "Pay the remaining fee now or you cannot leave."},
                                {"sender": "recruiter", "text": "We will keep your passport until the debt is cleared."},
                            ]
                        }
                    ).encode("utf-8"),
                    "application/json",
                ),
            ),
            (
                "files",
                (
                    "employment_contract.docx",
                    _minimal_docx_bytes(
                        "Employment contract. Employer will retain the passport during the contract period and deduct fees over 7 months."
                    ),
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                ),
            ),
        ]

        resp = client.post(
            "/api/v1/migration-case-upload",
            data={
                "case_id": "case-upload-001",
                "corridor": "PH_HK",
                "case_notes": "Interview narrative: the worker says the recruiter threatened to blacklist her if she refused payment.",
                "document_contexts_json": json.dumps(
                    {
                        "agency_receipt.txt": "receipt",
                        "recruiter_chat.json": "chat",
                        "employment_contract.docx": "contract",
                    }
                ),
                "document_notes_json": json.dumps(
                    {
                        "employment_contract.docx": "Operator note: recruiter said the passport would stay with the agency office until the debt was repaid.",
                    }
                ),
            },
            files=files,
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["case_id"] == "case-upload-001"
        assert data["corridor"] == "PH_HK"
        assert data["document_count"] == 4
        assert data["risk_level"] == "HIGH"
        assert data["timeline"]
        assert "employment_agency_misconduct" in data["case_categories"]
        assert data["risk_reasons"]
        assert data["indicator_counts"]["worker_paid_placement_fee"] >= 1
        assert data["document_type_counts"]["payment_receipt"] >= 1
        assert data["document_type_counts"]["worker_statement"] >= 1
        assert any(template["name"] == "employment_agency_complaint" for template in data["complaint_templates"])
        assert any(item["tool"] == "score_exploitation_risk" for item in data["tool_results"])
