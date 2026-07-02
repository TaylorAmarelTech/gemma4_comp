"""Tests for the active Kaggle/page source gate."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _load_validator():
    path = ROOT / "scripts" / "validate_kaggle_page_sources.py"
    spec = importlib.util.spec_from_file_location("validate_kaggle_page_sources_for_tests", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


vks = _load_validator()


PRIMARY_PAGES = {
    "index.html": "chat-activity-log",
    "compare.html": "cmp-log",
    "process.html": "wb-log",
    "knowledge.html": "wb-log",
    "search.html": "search-log",
    "share.html": "wb-log",
    "templates.html": "tpl-log",
    "status.html": "status-log",
}


def _valid_page(log_id: str, *, extra: str = "") -> str:
    return f"""
<!doctype html>
<html>
<head>
  <link rel="stylesheet" href="/static/_chrome.css">
  <script src="/static/_nav.js" defer></script>
  <script src="/static/_activity_log.js" defer></script>
</head>
<body>
  <div class="dc-trust-row" role="note" aria-label="Trust boundary">Local test boundary</div>
  <div id="{log_id}" class="dc-activity-log" role="log" aria-label="Activity log" aria-live="polite" data-toolbar="copy-json"></div>
  {extra}
</body>
</html>
"""


def _write_valid_workbench(root: Path) -> None:
    root.mkdir(parents=True)
    process_markers = "\n".join(
        (
            "Gemma 4 text case brief",
            "Gemma 4 typed-edge + RAG synthesis",
            "Gemma 4 hierarchical item graph pass",
            "Gemma 4 contextual media review",
            "wb-max-gemma-calls",
            "/api/process/graph-extract/start",
        )
    )
    template_markers = "\n".join(
        (
            'id="tpl-fill-progress-box"',
            "function tplSetProgress",
            "Draft ready for review",
            'data-toolbar="copy-json"',
            "Where Gemma 4 runs on this page",
        )
    )
    for name, log_id in PRIMARY_PAGES.items():
        extra = process_markers if name == "process.html" else ""
        if name == "templates.html":
            extra = template_markers
        (root / name).write_text(_valid_page(log_id, extra=extra), encoding="utf-8")


def _write_valid_server_recording(root: Path) -> None:
    root.mkdir(parents=True)
    trust = (
        '<div role="note" aria-label="Recording trust boundary">'
        "Raw case files stay out of the slide deck. localStorage stores only cached recording rows."
        "</div>"
    )
    (root / "start.html").write_text(
        f"""
<!doctype html>
<html>
<head><link rel="stylesheet" href="/static/style.css"></head>
<body>
{trust}
<a href="/slides">slides</a>
<a href="/slides/setup">setup</a>
<a href="/wb-static/process.html">process</a>
Platform safety
NGO &amp; regulator
Individual worker / mobile
Researcher
Anonymized knowledge sharing
Developer / integration partner
</body>
</html>
""",
        encoding="utf-8",
    )
    (root / "slides-setup.html").write_text(
        f"""
<!doctype html>
<html>
<head><link rel="stylesheet" href="/static/style.css"></head>
<body>
{trust}
/api/slides/cached-io
/api/slides/recording-pack
duecare.slides.demo.chat
duecare.slides.demo.pack
</body>
</html>
""",
        encoding="utf-8",
    )


def test_workbench_primary_pages_require_visible_trust_boundary(tmp_path, monkeypatch):
    workbench = tmp_path / "static"
    _write_valid_workbench(workbench)
    compare = workbench / "compare.html"
    compare.write_text(compare.read_text(encoding="utf-8").replace("dc-trust-row", "dc-no-trust-row"), encoding="utf-8")
    monkeypatch.setattr(vks, "WORKBENCH_STATIC", workbench)

    findings = vks._check_workbench_primary_pages()

    assert any(f.path.name == "compare.html" and "dc-trust-row" in f.message for f in findings)


def test_workbench_primary_pages_require_accessible_exportable_activity_log(tmp_path, monkeypatch):
    workbench = tmp_path / "static"
    _write_valid_workbench(workbench)
    status = workbench / "status.html"
    status.write_text(status.read_text(encoding="utf-8").replace('aria-live="polite"', ""), encoding="utf-8")
    monkeypatch.setattr(vks, "WORKBENCH_STATIC", workbench)

    findings = vks._check_workbench_primary_pages()

    assert any(f.path.name == "status.html" and 'aria-live="polite"' in f.message for f in findings)


def test_server_recording_pages_require_cache_boundary_copy(tmp_path, monkeypatch):
    server_static = tmp_path / "server-static"
    _write_valid_server_recording(server_static)
    start = server_static / "start.html"
    start.write_text(
        start.read_text(encoding="utf-8").replace(
            "Raw case files stay out of the slide deck.",
            "Cached rows stay small.",
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(vks, "SERVER_STATIC", server_static)

    findings = vks._check_server_recording_pages()

    assert any(
        f.path.name == "start.html" and "Raw case files stay out of the slide deck" in f.message
        for f in findings
    )
