from __future__ import annotations

import importlib.util
import io
import json
import shutil
import zipfile
from pathlib import Path

from fastapi.testclient import TestClient

# With pypdf installed contract_excerpt.pdf parses as text and stops counting
# as a media asset, so only receipt_photo.jpeg remains; without pypdf the PDF
# is an OCR work item too.
_HAS_PYPDF = importlib.util.find_spec("pypdf") is not None


SAMPLES = (
    Path(__file__).parents[1]
    / "src"
    / "duecare"
    / "chat"
    / "static"
    / "samples"
)


def _zip_names(name: str) -> list[str]:
    with zipfile.ZipFile(SAMPLES / name) as zf:
        return [n for n in zf.namelist() if not n.endswith("/")]


def test_static_sample_catalog_contains_rich_downloadables():
    expected = {
        "case_files_sample.zip",
        "case_files_streamlined_demo.zip",
        "case_files_media_rich_sample.zip",
        "knowledge_bundle_sample.zip",
        "knowledge_files_sample.zip",
        "knowledge_pack_rich_sample.zip",
        "knowledge_source_examples_sample.zip",
        "search_intake_examples_sample.zip",
        "prompt_eval_training_seed_sample.zip",
    }
    missing = [name for name in expected if not (SAMPLES / name).exists()]
    assert not missing
    assert all((SAMPLES / name).stat().st_size > 1000 for name in expected)


def test_streamlined_process_demo_is_small_and_explains_expected_path():
    names = _zip_names("case_files_streamlined_demo.zip")
    assert len(names) == 8
    required = {
        "README.md",
        "manifest.json",
        "expected_outputs/streamlined_demo_expected.json",
    }
    assert required.issubset(set(names))
    assert any(n.endswith("/01_chat/recruiter_chat.txt") for n in names)
    assert any(n.endswith("/02_contract/deployment_side_letter.txt") for n in names)
    assert any(n.endswith("/03_receipts/payment_receipt.txt") for n in names)
    assert any(n.endswith("/04_timeline/deployment_timeline.csv") for n in names)
    assert any(n.endswith("/05_caseworker/caseworker_note.txt") for n in names)
    with zipfile.ZipFile(SAMPLES / "case_files_streamlined_demo.zip") as zf:
        manifest = json.loads(zf.read("manifest.json"))
        expected = json.loads(zf.read("expected_outputs/streamlined_demo_expected.json"))
        readme = zf.read("README.md").decode("utf-8")
    assert manifest["recommended_settings"]["review_mode"] == "quick_triage"
    assert manifest["recommended_settings"]["max_gemma_calls"] == 8
    assert expected["expected_patterns"] == [
        "fee_camouflage",
        "fee_rerouting",
        "restricted_provider_choice",
        "salary_deduction",
        "retaliation_risk",
    ]
    assert "Upload ZIP" in readme
    assert "Ask conversational questions" in readme


def test_media_rich_sample_has_expected_outputs_and_public_record_policy():
    names = _zip_names("case_files_media_rich_sample.zip")
    required = {
        "expected_outputs/README.md",
        "expected_outputs/strongest_cases_expected.json",
        "expected_outputs/overcharging_entities_expected.json",
        "expected_outputs/salary_deduction_evidence_expected.json",
        "public_records_synthetic/README.md",
        "public_records_synthetic/public_record_source_candidates.json",
        "public_records_synthetic/synthetic_magistrates_judgment_excerpt.pdf",
        "public_records_synthetic/synthetic_labour_department_press_release.html",
        "format_edge_cases/nested_archives/phone_export_nested.zip",
        "format_edge_cases/image_formats/receipt_scan.tiff",
        "format_edge_cases/image_formats/chat_screenshot.webp",
        "format_edge_cases/image_formats/phone_photo_placeholder.heic",
        "format_edge_cases/audio_placeholders/voice_note.opus",
        "format_edge_cases/audio_placeholders/caseworker_note.m4a",
    }
    assert required.issubset(set(names))
    assert any(n.startswith("calibration_cases/clean_compliant/") for n in names)
    assert any(n.startswith("calibration_cases/borderline_incomplete/") for n in names)
    assert any(n.startswith("calibration_cases/false_positive_bait/") for n in names)

    with zipfile.ZipFile(SAMPLES / "case_files_media_rich_sample.zip") as zf:
        expected = json.loads(zf.read("expected_outputs/strongest_cases_expected.json"))
        assert expected["expected_top_cases"][0]["case_id"] == "DC-PH-HK-106"
        policy = zf.read("public_records_synthetic/README.md").decode("utf-8")
        assert "license or public-domain basis" in policy
        assert "do not embed the document" in policy


def test_rich_knowledge_pack_uses_importable_envelope_paths():
    from duecare.chat.app import KO_TYPES

    names = _zip_names("knowledge_pack_rich_sample.zip")
    assert "README.txt" in names
    envelope_names = [n for n in names if n.endswith(".json")]
    assert len(envelope_names) >= 25

    types_seen: set[str] = set()
    with zipfile.ZipFile(SAMPLES / "knowledge_pack_rich_sample.zip") as zf:
        for name in envelope_names:
            ko_type, leaf = name.split("/", 1)
            env = json.loads(zf.read(name))
            assert ko_type in KO_TYPES
            assert env["schema_version"] == "1.0"
            assert env["knowledge_object_type"] == ko_type
            assert leaf == env["id"] + ".json"
            assert isinstance(env["content"], dict)
            types_seen.add(ko_type)

    assert {
        "grep_rule",
        "rag_doc",
        "ngo_directory",
        "modus_operandi",
        "evaluation_dimension",
        "tool_definition",
        "fact_template",
        "submission_schema",
    }.issubset(types_seen)


def test_knowledge_files_sample_has_manifest_and_importable_objects(monkeypatch):
    from duecare.chat.app import create_app

    names = _zip_names("knowledge_files_sample.zip")
    assert "README.md" in names
    assert "manifest.json" in names
    assert any(n.startswith("grep_rule/") for n in names)
    assert any(n.startswith("rag_doc/") for n in names)

    knowledge_root = Path.cwd() / ".pytest-tmp-local" / "knowledge-import"
    shutil.rmtree(knowledge_root, ignore_errors=True)
    monkeypatch.setenv("DUECARE_KNOWLEDGE_ROOT", str(knowledge_root))
    client = TestClient(create_app())
    sample = SAMPLES / "knowledge_files_sample.zip"
    try:
        response = client.post(
            "/api/knowledge/import",
            files={"file": (sample.name, io.BytesIO(sample.read_bytes()), "application/zip")},
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["n_imported"] >= 20
        assert body["n_rejected"] == 0
    finally:
        shutil.rmtree(knowledge_root, ignore_errors=True)


def test_knowledge_source_examples_parse_for_drafting():
    from duecare.chat.app import create_app

    client = TestClient(create_app())
    sample = SAMPLES / "knowledge_source_examples_sample.zip"
    response = client.post(
        "/api/knowledge/source-file",
        files={"file": (sample.name, io.BytesIO(sample.read_bytes()), "application/zip")},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["n_rows_total"] >= 6
    assert body["n_media_assets"] >= (1 if _HAS_PYPDF else 2)
    assert "Knowledge source upload" in body["raw_text"]
    assert "retaliation" in body["raw_text"].lower()
    assert "salary deduction" in body["raw_text"].lower()


def test_search_and_training_seed_samples_have_expected_assets():
    search_names = _zip_names("search_intake_examples_sample.zip")
    assert "queries/public_source_queries.jsonl" in search_names
    assert "results/source_cards.json" in search_names
    assert any(n.startswith("draft_envelopes/rag_doc/") for n in search_names)
    assert "manifest/repeatability_manifest.json" in search_names

    training_names = _zip_names("prompt_eval_training_seed_sample.zip")
    assert "prompt_sets/use_case_prompts.jsonl" in training_names
    assert "prompt_sets/adversarial_prompts.jsonl" in training_names
    assert "manifest/unified_demo_story.json" in training_names
    assert "rubrics/evaluation_dimensions.json" in training_names
    assert "training/synthetic_sft_pairs.jsonl" in training_names
    assert "training/preference_pairs.jsonl" in training_names
    assert "training/tool_call_examples.jsonl" in training_names
    assert "manifest/finetune_seed_manifest.json" in training_names

    with zipfile.ZipFile(SAMPLES / "prompt_eval_training_seed_sample.zip") as zf:
        story = json.loads(zf.read("manifest/unified_demo_story.json"))
        assert story["case_id"] == "DC-PH-HK-101"
        assert story["agency"] == "Pearl Bridge Manpower"


def test_pages_link_downloadable_sample_packs():
    from duecare.chat.app import create_app

    client = TestClient(create_app())
    knowledge = client.get("/static/knowledge.html")
    assert knowledge.status_code == 200
    assert "knowledge_source_examples_sample.zip" in knowledge.text
    assert "knowledge_files_sample.zip" in knowledge.text
    assert "knowledge_pack_rich_sample.zip" in knowledge.text
    assert "Download sample bundle" not in knowledge.text

    search = client.get("/static/search.html")
    assert search.status_code == 200
    assert "search_intake_examples_sample.zip" in search.text
    assert "prompt_eval_training_seed_sample.zip" in search.text

    compare = client.get("/static/compare.html")
    assert compare.status_code == 200
    assert "prompt_eval_training_seed_sample.zip" in compare.text
