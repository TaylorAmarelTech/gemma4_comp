from __future__ import annotations

import zipfile
from pathlib import Path

from scripts.ingest_google_drive_reference_material import (
    _extract_docx_text,
    _build_tool_call_examples,
    _build_specific_tool_call_scenarios,
    _select_manifest_items,
    _source_id,
    extract_text,
    infer_audience,
    infer_context_hint,
    infer_document_kind,
    infer_use_case_tags,
    DriveManifestItem,
    ProcessedRecord,
)
from duecare.agents.anonymizer.anonymizer import redact


def _write_minimal_docx(path: Path, *, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content_types = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>
"""
    rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>
"""
    document = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p><w:r><w:t>{text}</w:t></w:r></w:p>
  </w:body>
</w:document>
"""
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", rels)
        archive.writestr("word/document.xml", document)


def test_extract_docx_text_reads_minimal_document(tmp_path: Path) -> None:
    document_path = tmp_path / "sample.docx"
    _write_minimal_docx(document_path, text="Workers must pay a recruitment fee.")

    extracted = _extract_docx_text(document_path)

    assert "recruitment fee" in extracted


def test_anonymized_complaint_routes_to_templates_and_examples() -> None:
    raw_text = (
        "Cease and Desist Letter to OWTEL. Contact maria@example.com or +1 555 000 1234. "
        "Worker paid a recruitment fee before Hong Kong deployment."
    )
    anonymized_text, audit = redact(raw_text)

    document_kind = infer_document_kind("templates/cease_and_desist_letter.docx", anonymized_text)
    audience = infer_audience(document_kind)
    context_hint = infer_context_hint(document_kind, anonymized_text)

    assert document_kind == "cease_and_desist_template"
    assert audience == "Company legal or compliance team"
    assert context_hint == "receipt"
    assert "maria@example.com" not in anonymized_text
    assert "+1 555 000 1234" not in anonymized_text
    assert audit


def test_extract_text_quarantines_html_disguised_as_pdf(tmp_path: Path) -> None:
    pdf_path = tmp_path / "broken.pdf"
    pdf_path.write_text("<!DOCTYPE html><html><body>Google Docs interstitial</body></html>", encoding="utf-8")

    text, status = extract_text(pdf_path)

    assert text == ""
    assert status == "download_interstitial"


def test_build_tool_call_examples_uses_repo_tool_names() -> None:
    record = ProcessedRecord(
        source_id=_source_id("collection", "complaint.docx"),
        collection="collection",
        relative_path="complaint.docx",
        local_path="C:/tmp/complaint.docx",
        suffix=".docx",
        extraction_status="docx",
        anonymization_status="redacted",
        redaction_count=2,
        text_chars=120,
        document_kind="complaint_template",
        audience="Regulator or platform complaints desk",
        context_hint="complaint",
        template_candidate=True,
        example_candidate=True,
        tool_call_candidate=True,
        use_case_tags=["overcharging", "complaint_against_agency"],
        sector="domestic_work",
        corridor="PH-HK",
        exploitation_type="excessive_fees",
        severity="medium",
        confidence=0.72,
    )

    examples = _build_tool_call_examples(record, "[EMAIL] [PHONE] worker paid HKD 20000 placement fee")

    assert [example["tool_name"] for example in examples] == [
        "identify_trafficking_indicators",
        "score_exploitation_risk",
        "check_legal_framework",
        "check_fee_legality",
        "lookup_hotline",
    ]
    assert examples[0]["expected"]["document_kind"] == "complaint_template"
    assert examples[3]["arguments"]["currency"] == "HKD"


def test_use_case_tags_and_specific_scenarios_cover_requested_categories() -> None:
    text = (
        "Facebook chat shows the recruiter demanding a placement fee and routing the worker "
        "to OWTEL for loan financing. The employment contract says the employer will retain the passport."
    )
    tags = infer_use_case_tags("complaint_example", text, "chat")

    assert "overcharging" in tags
    assert "chat_message_analytics" in tags
    assert "contract_data_extraction" in tags
    assert "complaint_against_money_lender" in tags

    record = ProcessedRecord(
        source_id=_source_id("collection", "chat_example.docx"),
        collection="collection",
        relative_path="chat_example.docx",
        local_path="C:/tmp/chat_example.docx",
        suffix=".docx",
        extraction_status="docx",
        anonymization_status="redacted",
        redaction_count=1,
        text_chars=len(text),
        document_kind="complaint_example",
        audience="Researcher reviewing complaint patterns",
        context_hint="chat",
        template_candidate=False,
        example_candidate=True,
        tool_call_candidate=True,
        use_case_tags=tags,
        sector="domestic_work",
        corridor="PH-HK",
        exploitation_type="passport_retention",
        severity="high",
        confidence=0.81,
    )

    scenarios = _build_specific_tool_call_scenarios(record, text)
    scenario_names = {scenario["use_case"] for scenario in scenarios}
    all_tools = {tool for scenario in scenarios for tool in scenario["tool_flow"]}

    assert {"overcharging", "chat_message_analytics", "contract_data_extraction"}.issubset(scenario_names)
    assert "draft_money_lender_complaint" in all_tools
    assert "extract_contract_terms" in all_tools
    assert "analyze_chat_messages" in all_tools


def test_disk_conscious_manifest_selection_prefers_high_value_gmlc_documents() -> None:
    manifest_items = [
        DriveManifestItem(
            collection="gmlc_cases",
            file_id="1",
            relative_path="Template - law letters/Cease and Desist - Sample.pdf",
        ),
        DriveManifestItem(
            collection="gmlc_cases",
            file_id="2",
            relative_path="Money Lenders - OPERATION STARVE THE HYDRA/True Credit Demand Letter.docx",
        ),
        DriveManifestItem(
            collection="gmlc_cases",
            file_id="3",
            relative_path="Client Folders - Generic/123 Loan Page 1.jpg",
        ),
        DriveManifestItem(
            collection="gmlc_cases",
            file_id="4",
            relative_path="BULK SCANS/31 AUGUST 2020/scan001.jpg",
        ),
    ]

    selected, plan = _select_manifest_items("gmlc_cases", manifest_items, selection_policy="auto")

    assert {item.relative_path for item in selected} == {
        "Template - law letters/Cease and Desist - Sample.pdf",
        "Money Lenders - OPERATION STARVE THE HYDRA/True Credit Demand Letter.docx",
    }
    assert plan.total_candidates == 4
    assert plan.selected_candidates == 2


def test_full_selection_policy_keeps_all_manifest_items() -> None:
    manifest_items = [
        DriveManifestItem(collection="gmlc_cases", file_id="1", relative_path="Template - law letters/Sample.pdf"),
        DriveManifestItem(collection="gmlc_cases", file_id="2", relative_path="Client Folders - Generic/123 Loan Page 1.jpg"),
    ]

    selected, plan = _select_manifest_items("gmlc_cases", manifest_items, selection_policy="all")

    assert [item.relative_path for item in selected] == [item.relative_path for item in manifest_items]
    assert plan.selected_candidates == 2