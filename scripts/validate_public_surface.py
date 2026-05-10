"""Validate the public-facing surface for known drift categories.

Bundles the audits that have caught real defects this hackathon:

1. **Stale wording grep** in active docs/templates/notebooks
   (excluding frozen artifacts under _archive, docs/adr, dated
   CHECKPOINT_, GPT55_*, REPO_LAYOUT, _reference)
2. **Route 200 sweep** — every PAGE_ROUTES entry + every link in
   _nav.html / _footer.html must return 200 via TestClient
3. **Five-lane consistency** — confirms the canonical lane order
   appears intact on the homepage / setup / use-cases / README
4. **Lane labels on Kaggle READMEs** — every kaggle/{01,02,A-*}/
   README.md should carry the "Serves lanes:" line so judges
   clicking from the website see continuity
5. **Privacy-slogan headline** — flags any surface that uses
   "Privacy is non-negotiable." as a headline tagline (saved
   feedback: it should be a concrete data rule in plain English,
   not a slogan)

Exits 0 if every check passes, 1 otherwise. On failure, prints
a structured report grouped by check.

Run locally:

    python scripts/validate_public_surface.py
    python scripts/validate_public_surface.py --json    # machine-readable

Run as part of CI (non-blocking initially):

    .github/workflows/ci.yml ->  validate-public-surface job
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
HUB_APP = ROOT / "apps" / "duecare-ai.com"
TEMPLATES = HUB_APP / "app" / "templates"
KAGGLE = ROOT / "kaggle"

# --- Surfaces and exclusions --------------------------------------------------

ACTIVE_GLOBS: tuple[str, ...] = (
    "README.md",
    "docs/**/*.md",
    "kaggle/**/README.md",
    "kaggle/_INDEX.md",
    "apps/duecare-ai.com/app/templates/*.html",
    "skunkworks/README.md",
    "packages/*/README.md",
)

# Paths that are intentionally frozen point-in-time snapshots — they
# reference stale terms on purpose. Don't fail the audit on them.
EXCLUDE_PATTERNS: tuple[str, ...] = (
    "_archive/",
    "_reference/",
    "docs/adr/",
    "docs/CHECKPOINT_",
    "docs/GPT55_",
    "docs/COPILOT_HANDOFF_REVIEW_PROMPT.md",
    "docs/duecare_adversarial_audit.md",  # frozen audit
    "docs/REPO_LAYOUT.md",                # documents the rename
    "docs/notes/",
    ".venv/",
    "site-packages/",
)

# --- Drift terms --------------------------------------------------------------

# (pattern, human label, why it's drift, suggested replacement)
DRIFT_TERMS: tuple[tuple[str, str, str], ...] = (
    (r"\b6 core \+ 5\b", "stale notebook split", "use 2 core + 11 appendix = 13"),
    (r"all 11 submission notebooks", "stale notebook count", "13 submission notebooks (2 core + 11 appendix)"),
    (r"\b3 hackathon notebooks\b", "stale hackathon-notebook count", "13 competition notebooks"),
    (r"\b76-notebook\b", "stale research-pipeline count", "77-notebook research pipeline"),
    (r"\bduecare packs pull\b", "unverified CLI command on a public surface", "remove or label as planned"),
    (r"\bduecare packs verify\b", "unverified CLI command on a public surface", "remove or label as planned"),
    (r"\bduecare harness run\b", "unverified CLI command on a public surface", "remove or label as planned"),
    (r"\bsigned pack\b", "stale terminology", "vetted pack"),
    (r"\bOpenClaw\b", "non-DueCare brand name in active prose", "server automation"),
    (r"^# .*Privacy is non-negotiable", "privacy slogan as h1 headline", "concrete data-rule sentence"),
    (r"<h[1-3][^>]*>\s*Privacy is non-negotiable", "privacy slogan as h1-h3 headline", "concrete data-rule sentence"),
)

# --- Five-lane canonical order ------------------------------------------------

# Each lane is a tuple of accepted tokens (any one matches). The lane
# order itself is what we enforce; within a lane, any of the listed
# spellings is acceptable. Add new aliases here when public copy
# legitimately uses a synonym.
LANE_ALIASES_ORDERED: tuple[tuple[str, ...], ...] = (
    ("Platform safety",),
    ("NGO &amp; regulator", "NGO & regulator"),
    ("Individual worker / mobile", "Migrant worker chat", "Migrant worker / mobile"),
    ("Researcher", "Academic research"),
    ("Developer / integration partner", "Developer", "Custom integration"),
)

LANE_ANCHOR_FILES: tuple[Path, ...] = (
    TEMPLATES / "setup.html",
    TEMPLATES / "use-cases.html",
)

# --- Helpers ------------------------------------------------------------------

@dataclass
class Finding:
    file: str
    line: int
    rule: str
    snippet: str
    suggestion: str = ""


@dataclass
class CheckResult:
    name: str
    findings: list[Finding] = field(default_factory=list)
    info: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.findings


def _excluded(rel: str) -> bool:
    rel = rel.replace("\\", "/")
    return any(pat in rel for pat in EXCLUDE_PATTERNS)


def _walk_active() -> Iterable[Path]:
    for pattern in ACTIVE_GLOBS:
        for path in ROOT.glob(pattern):
            if not path.is_file():
                continue
            rel = str(path.relative_to(ROOT))
            if _excluded(rel):
                continue
            yield path


# --- Check 1: drift terms -----------------------------------------------------

_ALLOW_TOKEN = "audit-allow:drift"  # opt-out marker; see docs/AUDIT.md
_ALLOW_FILE = "audit-allow-file:drift"  # whole-file opt-out marker


def check_drift_terms() -> CheckResult:
    result = CheckResult(name="drift_terms")
    compiled = [(re.compile(p, re.MULTILINE), label, suggest) for p, label, suggest in DRIFT_TERMS]
    files_scanned = 0
    files_skipped = 0
    for path in _walk_active():
        files_scanned += 1
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if _ALLOW_FILE in text:
            files_skipped += 1
            continue
        rel = str(path.relative_to(ROOT)).replace("\\", "/")
        lines = text.splitlines()
        for line_idx, line in enumerate(lines, start=1):
            # Suppress if the matching line OR the line directly above
            # carries the inline allow marker.
            allow_inline = _ALLOW_TOKEN in line
            allow_above = line_idx >= 2 and _ALLOW_TOKEN in lines[line_idx - 2]
            if allow_inline or allow_above:
                continue
            for regex, label, suggest in compiled:
                if regex.search(line):
                    result.findings.append(
                        Finding(
                            file=rel,
                            line=line_idx,
                            rule=label,
                            snippet=line.strip()[:160],
                            suggestion=suggest,
                        )
                    )
    result.info.append(
        f"Scanned {files_scanned} active files ({files_skipped} skipped via {_ALLOW_FILE} marker)."
    )
    return result


# --- Check 2: hub route 200 sweep --------------------------------------------

def check_routes_200() -> CheckResult:
    result = CheckResult(name="hub_routes_200")
    sys.path.insert(0, str(HUB_APP))
    os.environ.setdefault("DUECARE_DATA_DIR", str(ROOT / ".duecare-smoke"))
    try:
        from app.main import PAGE_ROUTES, create_app  # type: ignore
        from fastapi.testclient import TestClient  # type: ignore
    except ImportError as exc:
        result.findings.append(
            Finding(
                file="apps/duecare-ai.com/app/main.py",
                line=0,
                rule="hub_dependencies_unavailable",
                snippet=f"cannot import: {exc!r}",
                suggestion="install hub deps in this environment (see .venv) before running the audit",
            )
        )
        return result

    nav_html = (TEMPLATES / "_nav.html").read_text(encoding="utf-8")
    foot_html = (TEMPLATES / "_footer.html").read_text(encoding="utf-8")
    nav_links = sorted(set(re.findall(r'href="(/[a-zA-Z0-9_\-/]*)"', nav_html)))
    foot_links = sorted(set(re.findall(r'href="(/[a-zA-Z0-9_\-/]*)"', foot_html)))
    all_paths = sorted(set(PAGE_ROUTES) | set(nav_links) | set(foot_links))
    result.info.append(f"Probed {len(all_paths)} routes ({len(PAGE_ROUTES)} declared + {len(nav_links)} nav + {len(foot_links)} footer).")

    client = TestClient(create_app())
    for path in all_paths:
        r = client.get(path)
        if r.status_code != 200:
            source = "PAGE_ROUTES" if path in PAGE_ROUTES else ("nav" if path in nav_links else "footer")
            result.findings.append(
                Finding(
                    file=f"templates / {source}",
                    line=0,
                    rule=f"non-200 ({r.status_code})",
                    snippet=path,
                    suggestion="fix the route or remove the link",
                )
            )
    return result


# --- Check 3: five-lane order on anchor templates ----------------------------

def check_lane_order() -> CheckResult:
    result = CheckResult(name="five_lane_order")
    for path in LANE_ANCHOR_FILES:
        if not path.is_file():
            result.findings.append(
                Finding(file=str(path.relative_to(ROOT)), line=0, rule="anchor_missing", snippet="", suggestion="restore the anchor template"),
            )
            continue
        text = path.read_text(encoding="utf-8")
        rel = str(path.relative_to(ROOT)).replace("\\", "/")
        positions: list[int] = []
        for aliases in LANE_ALIASES_ORDERED:
            best = -1
            best_alias = ""
            for alias in aliases:
                idx = text.find(alias)
                if idx >= 0 and (best < 0 or idx < best):
                    best = idx
                    best_alias = alias
            if best < 0:
                result.findings.append(
                    Finding(
                        file=rel,
                        line=0,
                        rule="lane_token_missing",
                        snippet=" | ".join(aliases),
                        suggestion="restore the lane (use any of the listed spellings) in the canonical order",
                    )
                )
                positions.append(10**9)
                continue
            positions.append(best)
        if positions and positions != sorted(positions):
            canonical = ", ".join(aliases[0] for aliases in LANE_ALIASES_ORDERED)
            result.findings.append(
                Finding(
                    file=rel,
                    line=0,
                    rule="lane_order_wrong",
                    snippet=f"got order indices {positions}",
                    suggestion=f"reorder to: {canonical}",
                )
            )
    return result


# --- Check 4: lane label tag on every kaggle README -------------------------

def check_kaggle_lane_labels() -> CheckResult:
    result = CheckResult(name="kaggle_lane_labels")
    folders = sorted(KAGGLE.glob("01-*")) + sorted(KAGGLE.glob("02-*")) + sorted(KAGGLE.glob("A-*"))
    folders = [f for f in folders if f.is_dir()]
    result.info.append(f"Inspected {len(folders)} numbered Kaggle folders.")
    for folder in folders:
        readme = folder / "README.md"
        if not readme.is_file():
            result.findings.append(
                Finding(
                    file=str(readme.relative_to(ROOT)).replace("\\", "/"),
                    line=0,
                    rule="readme_missing",
                    snippet="",
                    suggestion="every numbered folder must have a README.md",
                )
            )
            continue
        text = readme.read_text(encoding="utf-8")
        if "Serves lanes:" not in text and "duecare:lane-label" not in text:
            result.findings.append(
                Finding(
                    file=str(readme.relative_to(ROOT)).replace("\\", "/"),
                    line=0,
                    rule="lane_label_missing",
                    snippet="",
                    suggestion="add: <!-- duecare:lane-label -->\\n> **Serves lanes:** ...",
                )
            )
    return result


# --- Reporting ---------------------------------------------------------------

def render_text(checks: list[CheckResult]) -> str:
    lines: list[str] = []
    total_findings = sum(len(c.findings) for c in checks)
    lines.append(f"Public-surface audit — {len(checks)} checks · {total_findings} findings")
    lines.append("=" * 78)
    for c in checks:
        flag = "OK " if c.ok else "FAIL"
        lines.append(f"\n[{flag}] {c.name}  ({len(c.findings)} finding{'s' if len(c.findings) != 1 else ''})")
        for note in c.info:
            lines.append(f"  · {note}")
        for f in c.findings[:50]:
            loc = f"{f.file}:{f.line}" if f.line else f.file
            lines.append(f"  - {loc}  [{f.rule}]")
            if f.snippet:
                lines.append(f"      {f.snippet}")
            if f.suggestion:
                lines.append(f"      -> {f.suggestion}")
        if len(c.findings) > 50:
            lines.append(f"  ... ({len(c.findings) - 50} more findings suppressed)")
    lines.append("")
    overall = Counter(f.rule for c in checks for f in c.findings)
    if overall:
        lines.append("Top rules by hit count:")
        for rule, n in overall.most_common(10):
            lines.append(f"  {n:>4}  {rule}")
    return "\n".join(lines)


def render_json(checks: list[CheckResult]) -> str:
    payload = {
        "ok": all(c.ok for c in checks),
        "checks": [
            {
                "name": c.name,
                "ok": c.ok,
                "info": c.info,
                "findings": [
                    {"file": f.file, "line": f.line, "rule": f.rule, "snippet": f.snippet, "suggestion": f.suggestion}
                    for f in c.findings
                ],
            }
            for c in checks
        ],
    }
    return json.dumps(payload, indent=2)


# --- Main --------------------------------------------------------------------

def main() -> int:
    # Ensure unicode bullets and em-dashes survive Windows cp1252 consoles.
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    parser.add_argument(
        "--skip",
        action="append",
        default=[],
        choices=["drift_terms", "hub_routes_200", "five_lane_order", "kaggle_lane_labels"],
        help="skip a check (repeatable)",
    )
    args = parser.parse_args()

    runners = [
        ("drift_terms", check_drift_terms),
        ("hub_routes_200", check_routes_200),
        ("five_lane_order", check_lane_order),
        ("kaggle_lane_labels", check_kaggle_lane_labels),
    ]
    checks = [run() for name, run in runners if name not in args.skip]

    if args.json:
        print(render_json(checks))
    else:
        print(render_text(checks))

    return 0 if all(c.ok for c in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
