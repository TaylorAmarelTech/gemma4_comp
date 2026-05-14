from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[1]
KAGGLE = ROOT / "kaggle"
STATIC = ROOT / "packages" / "duecare-llm-chat" / "src" / "duecare" / "chat" / "static"
MANIFEST = STATIC / "ui_audit_manifest.json"


def _manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def test_ui_audit_manifest_covers_all_runnable_kernels():
    data = _manifest()
    kernels = data["kernels"]
    assert len(kernels) == 28
    for item in kernels:
        folder = KAGGLE / item["folder"]
        assert folder.exists(), item
        assert (folder / "kernel.py").exists(), item
        assert (folder / "README.md").exists(), item
        assert (folder / "kernel-metadata.json").exists(), item


def test_ui_audit_manifest_covers_top_level_static_pages():
    data = _manifest()
    listed = {item["file"] for item in data["static_pages"]}
    actual = {
        p.name
        for p in STATIC.glob("*.html")
        if not p.name.startswith("_")
    }
    assert actual.issubset(listed)
    for item in data["static_pages"]:
        assert (STATIC / item["file"]).exists(), item
        assert item["controls"], item
        assert item["outputs"], item
        assert item["audit"], item


def test_ui_audit_page_and_manifest_are_served():
    from duecare.chat.app import create_app

    client = TestClient(create_app())
    page = client.get("/static/ui-audit.html")
    assert page.status_code == 200
    assert 'data-nav="audit"' in page.text
    assert "/static/ui_audit_manifest.json" in page.text
    manifest = client.get("/static/ui_audit_manifest.json")
    assert manifest.status_code == 200
    assert manifest.json()["schema_version"] == "duecare.ui_audit.v1"

    contacts = client.get("/api/contacts")
    assert contacts.status_code == 200
    body = contacts.json()
    assert body["pack_type"] == "volatile_contact_knowledge_pack"
    assert body["update_policy"]


def test_shared_nav_links_ui_audit_and_has_no_mojibake():
    nav = (STATIC / "_nav.html").read_text(encoding="utf-8")
    assert 'data-nav-key="audit"' in nav
    assert "/static/ui-audit.html" in nav
    assert 'data-nav-key="ecosystem"' in nav
    assert "/static/ecosystem.html" in nav
    for marker in ("\u00e2", "\u00c2", "\u00c3"):
        assert marker not in nav


def test_ecosystem_page_maps_runtime_and_training_flywheel():
    html = (STATIC / "ecosystem.html").read_text(encoding="utf-8")
    for marker in [
        "DueCare Ecosystem Map",
        "Runtime System",
        "Seven Surfaces",
        "Experiment Flywheel",
        "rubric_polisher",
        "Fine-tune smoke",
    ]:
        assert marker in html


def test_bulk_review_exposes_advanced_processing_and_journey_views():
    html = (STATIC / "process.html").read_text(encoding="utf-8")
    for marker in [
        "Advanced processing plan",
        "wb-processing-plan",
        "OCR and multimodal queue",
        "Migrant worker journey: critical points",
        "wb-journey",
        "wbRenderProcessingPlan",
        "wbRenderJourney",
    ]:
        assert marker in html


def test_primary_notebook_copy_is_consistent():
    primary_files = [
        KAGGLE / "01-duecare-exploration-workbench" / "kernel.py",
        KAGGLE / "01-duecare-exploration-workbench" / "README.md",
        KAGGLE / "02-live-demo" / "kernel.py",
        KAGGLE / "02-live-demo" / "README.md",
        KAGGLE / "03-duecare-video-pitch" / "kernel.py",
        KAGGLE / "03-duecare-video-pitch" / "README.md",
        KAGGLE / "A-00-omni-experiment-workbench" / "kernel.py",
        KAGGLE / "A-00-omni-experiment-workbench" / "README.md",
    ]
    stale_markers = [
        "Core notebook #01 of 27",
        "Core notebook #02 of 27",
        "3 core + 24 appendix",
        "all 6 safety layers",
        "All 6 harness layers",
        "ALL 6 layers",
        "6-layer story",
        "6-layer metadata",
    ]
    for path in primary_files:
        text = path.read_text(encoding="utf-8")
        for marker in stale_markers:
            assert marker not in text, f"{marker!r} found in {path}"


def test_primary_kernel_metadata_has_keywords():
    metadata_files = [
        KAGGLE / "01-duecare-exploration-workbench" / "kernel-metadata.json",
        KAGGLE / "02-live-demo" / "kernel-metadata.json",
        KAGGLE / "03-duecare-video-pitch" / "kernel-metadata.json",
        KAGGLE / "A-00-omni-experiment-workbench" / "kernel-metadata.json",
    ]
    for path in metadata_files:
        data = json.loads(path.read_text(encoding="utf-8"))
        keywords = data.get("keywords", [])
        assert "gemma-4" in keywords, path
        assert any(k in keywords for k in ["anti-trafficking", "safety-harness", "red-team"]), path


def test_video_pitch_routes_contacts_through_vetted_pack():
    text = (KAGGLE / "03-duecare-video-pitch" / "kernel.py").read_text(encoding="utf-8")
    for marker in [
        "8722-1144",
        "8833-0596",
        "2717-1771",
        "2823-8500",
        "2523-4020",
        "e56c818",
        "Polaris Project (verified)",
        "curator signature: Polaris Project",
    ]:
        assert marker not in text
    assert "vetted contacts pack" in text
    assert "contacts tool" in text


def test_default_personas_treat_contact_details_as_pack_data():
    harness = ROOT / "packages" / "duecare-llm-chat" / "src" / "duecare" / "chat" / "harness"
    personas = harness / "_personas.json"
    rubrics = harness / "_rubrics_5tier.json"
    classifier_examples = harness / "_classifier_examples.json"
    evaluation_questions = harness / "_evaluation_questions.json"
    rubric_hints = harness / "_rubric_hints.json"
    rubric_universal = harness / "_rubric_universal.json"
    harness_init = harness / "__init__.py"
    knowledge = STATIC / "knowledge.html"
    grade = STATIC / "grade.html"
    index = STATIC / "index.html"
    combined = "\n".join(
        path.read_text(encoding="utf-8")
        for path in [
            personas, rubrics, classifier_examples, evaluation_questions,
            rubric_hints, rubric_universal, harness_init, knowledge, grade, index,
        ]
    )
    for marker in [
        "PROVIDE NUMBERS",
        "+63-2-8721-1144",
        "+63-2-8722-1144",
        "+852-2522-8264",
        "+852-2866-0800",
        "+852-2523-4020",
        "+852-2717-1771",
        "+852-2823-8500",
        "1-866-487-9243",
        "1-888-373-7888",
        "specific NGO + phone",
        "specific regulator + phone",
        'placeholder="+63-2-8722-1144"',
    ]:
        assert marker not in combined
    assert "contacts tool" in combined
    assert "vetted contacts pack" in combined


def test_contacts_are_versioned_knowledge_pack_data():
    contacts = ROOT / "packages" / "duecare-llm-chat" / "src" / "duecare" / "chat" / "harness" / "_contacts.json"
    data = json.loads(contacts.read_text(encoding="utf-8"))
    assert data["pack_type"] == "volatile_contact_knowledge_pack"
    assert "version" in data
    assert "last_updated" in data
    assert "update_policy" in data
    assert "must never act on behalf of the user" in data["notes"]
