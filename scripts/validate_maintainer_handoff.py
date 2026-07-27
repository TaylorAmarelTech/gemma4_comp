#!/usr/bin/env python3
"""Validate DueCare's durable maintainer handoff without network or model calls.

The validator is read-only. Sensitive-data findings are reported only by
category and count; matched payloads are never printed or returned by the
top-level validation result.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]

HANDOFF_DOC = Path("docs/MAINTAINER_HANDOFF.md")
TRANSITION_DOC = Path("docs/PROJECT_TRANSITION_PLAN.md")

REQUIRED_FILES: tuple[Path, ...] = (
    HANDOFF_DOC,
    TRANSITION_DOC,
    Path("docs/PUBLICATION_READINESS.md"),
    Path("docs/project_status.md"),
    Path("docs/codex/PROJECT_BIBLE.md"),
    Path("AGENTS.md"),
    Path("kaggle/_INDEX.md"),
)

HANDOFF_MARKERS: tuple[str, ...] = (
    "## First 30 Minutes",
    "## Sources Of Truth",
    "## Architecture And Boundaries",
    "## Public Deployment Ownership",
    "## Local Environment",
    "## Validation Ladder",
    "## Routine Operations",
    "## Current Open Work",
    "## Access And Ownership Transfer",
    "## Incident And Recovery",
    "## First Week For A New Maintainer",
    "## Handoff Acceptance",
    "DUECARE_MAX_PLANNED_MODEL_CALLS",
    "validate_publication_readiness.py --scope handoff",
)

TRANSITION_MARKERS: tuple[str, ...] = (
    "**Status:**",
    "**Start date:**",
    "**Target handoff date:**",
    "2026-07-26",
    "2026-08-25",
    "## Definition Of Done",
    "## Week 1",
    "## Week 2",
    "## Week 3",
    "## Week 4",
    "## Final 72 Hours",
    "## Owner-Only Actions",
    "## Decision Register",
    "## Exit Criteria",
    "## If No Successor Is Available",
    "## Future Improvements",
)

DISCOVERY_LINKS: dict[Path, tuple[str, ...]] = {
    Path("README.md"): (
        "docs/MAINTAINER_HANDOFF.md",
        "docs/PROJECT_TRANSITION_PLAN.md",
    ),
    Path("PROJECT_BIBLE.md"): (
        "docs/MAINTAINER_HANDOFF.md",
        "docs/PROJECT_TRANSITION_PLAN.md",
    ),
    Path("docs/index.md"): (
        "MAINTAINER_HANDOFF.md",
        "PROJECT_TRANSITION_PLAN.md",
    ),
    Path("docs/FILE_PURPOSE_GUIDE.md"): (
        "MAINTAINER_HANDOFF.md",
        "PROJECT_TRANSITION_PLAN.md",
    ),
    Path("mkdocs.yml"): (
        "MAINTAINER_HANDOFF.md",
        "PROJECT_TRANSITION_PLAN.md",
    ),
}

DOC_CROSS_LINKS: dict[Path, tuple[str, ...]] = {
    HANDOFF_DOC: ("PROJECT_TRANSITION_PLAN.md", "PUBLICATION_READINESS.md"),
    TRANSITION_DOC: ("MAINTAINER_HANDOFF.md", "PUBLICATION_READINESS.md"),
}

SENSITIVE_PATTERNS: dict[str, re.Pattern[str]] = {
    "email_address": re.compile(
        r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",
        re.IGNORECASE,
    ),
    "phone_number": re.compile(
        r"(?<![\w-])(?:\+\d{1,3}[ .-]?)?"
        r"(?:\(\d{2,4}\)|\d{2,4})[ .-]\d{3,4}[ .-]\d{3,4}(?![\w-])"
    ),
    "windows_user_path": re.compile(
        r"(?<![A-Za-z0-9_])[A-Za-z]:\\(?:Users|Documents|Desktop|OneDrive)\\[^\r\n`]+",
        re.IGNORECASE,
    ),
    "secret_token": re.compile(
        r"\b(?:sk|ghp|github_pat|hf|xox[baprs])[-_][A-Za-z0-9_-]{8,}\b"
        r"|\bAKIA[A-Z0-9]{16}\b",
        re.IGNORECASE,
    ),
    "private_key": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
}

PLACEHOLDER_PATTERNS: dict[str, re.Pattern[str]] = {
    "tbd": re.compile(r"\bTBD\b", re.IGNORECASE),
    "todo": re.compile(r"\bTODO\b", re.IGNORECASE),
    "fill_in": re.compile(r"<\s*fill[ -]?in\s*>", re.IGNORECASE),
}

MARKDOWN_LINK_RE = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")


def missing_markers(text: str, markers: tuple[str, ...]) -> list[str]:
    """Return required markers absent from *text*."""
    return [marker for marker in markers if marker not in text]


def sensitive_category_counts(text: str) -> dict[str, int]:
    """Return nonzero sensitive-pattern counts without returning matches."""
    return {
        category: len(pattern.findall(text))
        for category, pattern in SENSITIVE_PATTERNS.items()
        if pattern.search(text)
    }


def placeholder_category_counts(text: str) -> dict[str, int]:
    """Return nonzero unresolved-placeholder counts."""
    return {
        category: len(pattern.findall(text))
        for category, pattern in PLACEHOLDER_PATTERNS.items()
        if pattern.search(text)
    }


def summarize_category_counts(counts: dict[str, int]) -> str:
    """Render only category names and integer counts."""
    if not counts:
        return "none"
    return ", ".join(f"{category}={counts[category]}" for category in sorted(counts))


def _inside_root(candidate: Path, root: Path) -> bool:
    try:
        candidate.relative_to(root)
    except ValueError:
        return False
    return True


def broken_local_links(document: Path, root: Path = ROOT) -> list[str]:
    """Return local Markdown targets that are missing or escape *root*."""
    root = root.resolve()
    document = document.resolve()
    text = document.read_text(encoding="utf-8")
    broken: list[str] = []

    for match in MARKDOWN_LINK_RE.finditer(text):
        target = match.group(1).strip().strip("<>")
        parsed = urlsplit(target)
        if parsed.scheme or parsed.netloc or target.startswith("#"):
            continue
        local_path = unquote(parsed.path)
        if not local_path:
            continue
        if local_path.startswith("/"):
            candidate = (root / local_path.lstrip("/")).resolve()
        else:
            candidate = (document.parent / local_path).resolve()
        if not _inside_root(candidate, root) or not candidate.exists():
            broken.append(target)
    return broken


def _safe_read(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return None


def deployment_contract_findings(root: Path = ROOT) -> list[str]:
    """Return safe labels for website/Pages ownership contract violations."""
    root = root.resolve()
    findings: list[str] = []
    docs_workflow = _safe_read(root / ".github/workflows/docs-deploy.yml") or ""
    site_workflow = _safe_read(root / ".github/workflows/duecare-site-build.yml") or ""
    render_blueprint = _safe_read(root / "render.yaml") or ""
    site_readme = _safe_read(root / "apps/duecare-ai.com/README.md") or ""

    if (root / ".github/workflows/pages.yml").exists():
        findings.append("competing Pages deploy workflow exists")
    for marker in ("branches: [master]", "mkdocs build", "actions/deploy-pages@v4"):
        if marker not in docs_workflow:
            findings.append("docs Pages workflow contract incomplete")
            break
    if "actions/upload-artifact@v4" not in site_workflow:
        findings.append("website artifact workflow missing upload")
    if "actions/deploy-pages" in site_workflow:
        findings.append("website artifact workflow deploys to Pages")
    for marker in ("rootDir: apps/duecare-ai.com", "branch: master"):
        if marker not in render_blueprint:
            findings.append("Render website blueprint contract incomplete")
            break
    for marker in ("Render-hosted FastAPI app", "GitHub Pages docs"):
        if marker not in site_readme:
            findings.append("website ownership documentation incomplete")
            break
    return findings


def public_continuity_surface_findings(root: Path = ROOT) -> list[str]:
    """Return safe labels for missing public handoff/status discovery."""
    root = root.resolve()
    route_source = _safe_read(root / "apps/duecare-ai.com/app/main.py") or ""
    template = _safe_read(root / "apps/duecare-ai.com/app/templates/project-status.html") or ""
    footer = _safe_read(root / "apps/duecare-ai.com/app/templates/_footer.html") or ""
    findings: list[str] = []

    if '"/project-status": "project-status.html"' not in route_source:
        findings.append("project status route missing")
    for marker in (
        "MAINTAINER_HANDOFF",
        "PROJECT_TRANSITION_PLAN",
        "PUBLICATION_READINESS",
        "docs-deploy.yml",
        "duecare-site-build.yml",
    ):
        if marker not in template:
            findings.append("project status content incomplete")
            break
    if 'href="/project-status"' not in footer:
        findings.append("project status footer link missing")
    return findings


def _check(name: str, ok: bool, detail: str) -> dict[str, object]:
    return {"name": name, "ok": ok, "detail": detail}


def validate(root: Path = ROOT) -> dict[str, object]:
    """Return a JSON-serializable handoff validation result."""
    root = root.resolve()
    checks: list[dict[str, object]] = []

    missing_files = [str(path) for path in REQUIRED_FILES if not (root / path).is_file()]
    checks.append(
        _check(
            "required handoff files",
            not missing_files,
            "all present" if not missing_files else f"missing: {', '.join(missing_files)}",
        )
    )

    doc_specs = (
        (HANDOFF_DOC, HANDOFF_MARKERS),
        (TRANSITION_DOC, TRANSITION_MARKERS),
    )
    handoff_texts: dict[Path, str] = {}
    for relative_path, markers in doc_specs:
        absolute_path = root / relative_path
        content = _safe_read(absolute_path)
        if content is None:
            checks.append(_check(f"{relative_path} structure", False, "unreadable"))
            continue
        handoff_texts[relative_path] = content
        absent = missing_markers(content, markers)
        detail = "all required sections present"
        if absent:
            detail = f"missing {len(absent)} marker(s): {', '.join(absent)}"
        checks.append(_check(f"{relative_path} structure", not absent, detail))

    for source, required_targets in DISCOVERY_LINKS.items():
        content = _safe_read(root / source)
        missing_targets = (
            list(required_targets)
            if content is None
            else [target for target in required_targets if target not in content]
        )
        detail = "both succession documents linked"
        if missing_targets:
            detail = f"missing {len(missing_targets)} required link(s)"
        checks.append(_check(f"{source} discovery links", not missing_targets, detail))

    for source, required_targets in DOC_CROSS_LINKS.items():
        content = handoff_texts.get(source)
        missing_targets = (
            list(required_targets)
            if content is None
            else [target for target in required_targets if target not in content]
        )
        detail = "release and succession cross-links present"
        if missing_targets:
            detail = f"missing {len(missing_targets)} required cross-link(s)"
        checks.append(_check(f"{source} cross-links", not missing_targets, detail))

    combined_text = "\n".join(handoff_texts.values())
    sensitive_counts = sensitive_category_counts(combined_text)
    checks.append(
        _check(
            "handoff sensitive-data scan",
            not sensitive_counts,
            summarize_category_counts(sensitive_counts),
        )
    )
    placeholder_counts = placeholder_category_counts(combined_text)
    checks.append(
        _check(
            "handoff unresolved placeholders",
            not placeholder_counts,
            summarize_category_counts(placeholder_counts),
        )
    )

    for source in (HANDOFF_DOC, TRANSITION_DOC):
        absolute_path = root / source
        broken = broken_local_links(absolute_path, root) if absolute_path.is_file() else []
        detail = "all local Markdown links resolve"
        if broken:
            detail = f"{len(broken)} missing or out-of-root local link(s)"
        checks.append(_check(f"{source} local links", not broken, detail))

    deployment_findings = deployment_contract_findings(root)
    checks.append(
        _check(
            "public deployment ownership",
            not deployment_findings,
            "Render website and MkDocs Pages ownership are unambiguous"
            if not deployment_findings
            else f"{len(deployment_findings)} deployment contract finding(s)",
        )
    )
    continuity_findings = public_continuity_surface_findings(root)
    checks.append(
        _check(
            "public continuity surface",
            not continuity_findings,
            "website status route and succession links present"
            if not continuity_findings
            else f"{len(continuity_findings)} continuity finding(s)",
        )
    )

    passed = sum(1 for check in checks if check["ok"])
    failed = len(checks) - passed
    return {
        "ok": failed == 0,
        "passed": passed,
        "failed": failed,
        "checks": checks,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="emit JSON instead of text")
    args = parser.parse_args(argv)

    result = validate()
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print("DueCare maintainer handoff validation (read-only, no model/network calls)")
        for check in result["checks"]:
            status = "PASS" if check["ok"] else "FAIL"
            print(f"[{status}] {check['name']}: {check['detail']}")
        print(f"Summary: {result['passed']} passed, {result['failed']} failed")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
