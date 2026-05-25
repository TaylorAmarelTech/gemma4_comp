"""Validate source assets for the active Kaggle page surfaces.

This is a pure-stdlib source gate. It complements
``validate_main_kaggle_kernels.py`` by checking the HTML/JS/CSS surfaces that
the active Kaggle kernels serve:

* Kernel 01 workbench pages under duecare-llm-chat static assets.
* Kernel 02 recording/demo pages under duecare-llm-server static assets.
* The optional benchmark kernels' source-level entrypoints.

It does not start FastAPI, import DueCare packages, install dependencies,
open a browser, or call a model.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SERVER_STATIC = (
    REPO_ROOT / "packages" / "duecare-llm-server" / "src" / "duecare" / "server" / "static"
)
WORKBENCH_STATIC = (
    REPO_ROOT / "packages" / "duecare-llm-chat" / "src" / "duecare" / "chat" / "static"
)
KAGGLE_ROOT = REPO_ROOT / "kaggle"

STATIC_REF_RE = re.compile(
    r"""(?:href|src)=["'](?P<url>/(?:static|wb-static)/[^"'\s>#?]+)"""
)


@dataclass(frozen=True)
class Finding:
    path: Path
    line: int
    message: str

    def render(self) -> str:
        rel = self.path.relative_to(REPO_ROOT).as_posix()
        return f"{rel}:{self.line}: {self.message}"


def _line_for(text: str, idx: int) -> int:
    return text.count("\n", 0, idx) + 1


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _html_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return sorted(root.glob("*.html"))


def _check_static_references() -> list[Finding]:
    findings: list[Finding] = []
    roots = (
        (SERVER_STATIC, SERVER_STATIC),
        (WORKBENCH_STATIC, WORKBENCH_STATIC),
    )
    for html_root, static_root in roots:
        for page in _html_files(html_root):
            text = _read(page)
            for match in STATIC_REF_RE.finditer(text):
                url = match.group("url")
                if "${" in url or "{" in url:
                    continue
                if url.startswith("/wb-static/"):
                    target = WORKBENCH_STATIC / url.removeprefix("/wb-static/")
                else:
                    target = static_root / url.removeprefix("/static/")
                if not target.exists():
                    findings.append(
                        Finding(
                            page,
                            _line_for(text, match.start()),
                            f"missing static asset referenced by {url!r}",
                        )
                    )
    return findings


def _check_server_recording_pages() -> list[Finding]:
    findings: list[Finding] = []
    for name in ("start.html", "slides-setup.html"):
        page = SERVER_STATIC / name
        if not page.exists():
            findings.append(Finding(page, 1, "missing Kernel 02 recording page"))
            continue
        text = _read(page)
        if "/static/styles.css" in text:
            findings.append(
                Finding(page, 1, "Kernel 02 pages must use /static/style.css, not /static/styles.css")
            )
        if 'href="/static/style.css"' not in text:
            findings.append(Finding(page, 1, "missing link to /static/style.css"))

    start = SERVER_STATIC / "start.html"
    if start.exists():
        text = _read(start)
        for marker in ('href="/slides"', 'href="/slides/setup"', 'href="/wb-static/process.html"'):
            if marker not in text:
                findings.append(Finding(start, 1, f"missing recording navigation marker {marker}"))
        for marker in (
            "Platform safety",
            "NGO &amp; regulator",
            "Individual worker / mobile",
            "Researcher",
            "Anonymized knowledge sharing",
            "Developer / integration partner",
        ):
            if marker not in text:
                findings.append(Finding(start, 1, f"missing public lane marker {marker}"))

    setup = SERVER_STATIC / "slides-setup.html"
    if setup.exists():
        text = _read(setup)
        for marker in (
            "/api/slides/cached-io",
            "/api/slides/recording-pack",
            "duecare.slides.demo.chat",
            "duecare.slides.demo.pack",
        ):
            if marker not in text:
                findings.append(Finding(setup, 1, f"missing slide setup marker {marker}"))

    slides = SERVER_STATIC / "slides.html"
    if slides.exists():
        text = _read(slides)
        if "substrate" in text.lower():
            findings.append(Finding(slides, 1, "submission deck should use safety/evidence stack wording"))
        for marker in (
            "Six public setup lanes, one shared local safety stack",
            "Shared local safety stack",
            "Anti-exploitation evidence stack",
            "Platform safety",
            "NGO &amp; regulator",
            "Individual worker / mobile",
            "Researcher",
            "Anonymized knowledge sharing",
            "Developer / integration partner",
        ):
            if marker not in text:
                findings.append(Finding(slides, 1, f"missing slide deck marker {marker}"))
    return findings


def _check_workbench_primary_pages() -> list[Finding]:
    findings: list[Finding] = []
    primary_pages = {
        "index.html": ("_chrome.css", "_nav.js", "_activity_log.js"),
        "compare.html": ("_chrome.css", "_nav.js", "_activity_log.js", "cmp-log"),
        "process.html": ("_chrome.css", "_nav.js", "_activity_log.js", "wb-log"),
        "knowledge.html": ("_chrome.css", "_nav.js", "_activity_log.js", "wb-log"),
        "search.html": ("_chrome.css", "_nav.js", "_activity_log.js", "search-log"),
        "share.html": ("_chrome.css", "_nav.js", "_activity_log.js", "wb-log"),
        "templates.html": ("_chrome.css", "_nav.js", "_activity_log.js", "tpl-log"),
        "status.html": ("_chrome.css", "_nav.js", "_activity_log.js", "status-log"),
    }
    for name, markers in primary_pages.items():
        page = WORKBENCH_STATIC / name
        if not page.exists():
            findings.append(Finding(page, 1, "missing primary Kernel 01 workbench page"))
            continue
        text = _read(page)
        for marker in markers:
            if marker not in text:
                findings.append(Finding(page, 1, f"missing primary-page marker {marker}"))

    process = WORKBENCH_STATIC / "process.html"
    if process.exists():
        text = _read(process)
        honest_markers = (
            "Gemma 4 text case brief",
            "Gemma 4 typed-edge + RAG synthesis",
            "Gemma 4 hierarchical item graph pass",
            "Gemma 4 contextual media review",
            "wb-max-gemma-calls",
            "/api/process/graph-extract/start",
        )
        for marker in honest_markers:
            if marker not in text:
                findings.append(Finding(process, 1, f"missing Bulk File Review honesty marker {marker}"))

    templates = WORKBENCH_STATIC / "templates.html"
    if templates.exists():
        text = _read(templates)
        for marker in (
            'id="tpl-fill-progress-box"',
            "function tplSetProgress",
            "Draft ready for review",
            'data-toolbar="copy-json"',
            "Where Gemma 4 runs on this page",
        ):
            if marker not in text:
                findings.append(Finding(templates, 1, f"missing Templates reviewer-path marker {marker}"))

    chat_alias = WORKBENCH_STATIC / "chat.html"
    if chat_alias.exists():
        text = _read(chat_alias)
        for marker in (
            '<link rel="canonical" href="/static/index.html">',
            "window.location.search + window.location.hash",
            "window.location.replace(target)",
        ):
            if marker not in text:
                findings.append(Finding(chat_alias, 1, f"missing chat compatibility marker {marker}"))
    return findings


def _check_benchmark_kernel_markers() -> list[Finding]:
    findings: list[Finding] = []
    kernels = {
        "03-universal-llm-benchmark/kernel.py": (
            "DueCare Universal LLM Benchmark",
            "REPORT_SCHEMA",
            "DEFAULT_JUDGE_MODEL",
            "target_list_from_config",
            "redact_config",
            "run_benchmark",
            "calls.jsonl",
            "report.html",
            "make_app",
            "/api/run",
            "/api/runs/{run_id}/download/{name}",
            "deterministic_judge",
        ),
        "04-kaggle-community-benchmark/kernel.py": (
            "DueCare Kaggle Community Benchmark",
            "kaggle_benchmarks",
            "REPORT_SCHEMA",
            "duecare.kaggle_community_benchmark.v3",
            "duecare_migrant_worker_safety_benchmark",
            "local_preview",
            "local_preview_no_model",
            "row_coverage",
            "assertion_count",
            "task_registration",
            "fallback_alignment",
            "build_assertions",
            "default_fallback_rows",
        ),
    }
    for rel, markers in kernels.items():
        path = KAGGLE_ROOT / rel
        if not path.exists():
            findings.append(Finding(path, 1, "missing optional benchmark kernel"))
            continue
        text = _read(path)
        for marker in markers:
            if marker not in text:
                findings.append(Finding(path, 1, f"missing benchmark marker {marker}"))
    return findings


def main() -> int:
    checks = (
        ("static references", _check_static_references),
        ("Kernel 02 recording pages", _check_server_recording_pages),
        ("Kernel 01 primary pages", _check_workbench_primary_pages),
        ("benchmark kernels", _check_benchmark_kernel_markers),
    )
    all_findings: list[Finding] = []
    print("Kaggle page source gate")
    print("=" * 72)
    for label, fn in checks:
        findings = fn()
        all_findings.extend(findings)
        if findings:
            print(f"[FAIL] {label} ({len(findings)} finding(s))")
            for finding in findings:
                print("  - " + finding.render())
        else:
            print(f"[OK  ] {label}")
    print("=" * 72)
    if all_findings:
        print(f"FAILED: {len(all_findings)} finding(s)")
        return 1
    print(
        "PASS: active Kaggle page sources reference existing assets and keep "
        "the expected recording/workbench/benchmark markers"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
