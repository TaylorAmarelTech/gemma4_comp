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
        "Evaluation And Training Flywheel",
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
