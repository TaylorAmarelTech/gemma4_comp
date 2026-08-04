"""Validate the public-facing surface for known drift categories.

Bundles the audits that have caught real defects this hackathon:

1. **Stale wording grep** in active docs/templates/notebooks
   (excluding frozen artifacts under _archive, docs/adr, dated
   CHECKPOINT_, GPT55_*, REPO_LAYOUT, _reference)
2. **Route 200 sweep** — every PAGE_ROUTES entry + every link in
   _nav.html / _footer.html must return 200 via TestClient
3. **Six-lane consistency** — confirms the canonical lane order
   appears intact on the homepage / setup / use-cases / README
4. **Lane labels on Kaggle READMEs** — every kaggle/{01,02,A-*}/
   README.md should carry the "Serves lanes:" line so judges
   clicking from the website see continuity
5. **Privacy-slogan headline** — flags any surface that uses
   "Privacy is non-negotiable." as a headline tagline (saved
   feedback: it should be a concrete data rule in plain English,
   not a slogan)
6. **Bundle envelope v1** — every kaggle/*/kernel.py that emits a
   JSON payload should use the canonical v1.0 BundleEnvelope shape
   from docs/data_primitives.md (schema_version='1.0', 'summary'
   and 'results' as the top-level keys, no legacy-only field
   names). Kernels emitting BOTH canonical + legacy alias
   (Tier-1+2 rollover state) pass this check.

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
import urllib.parse
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
    "CONTRIBUTING.md",
    "CODE_OF_CONDUCT.md",
    "SECURITY.md",
    "docs/**/*.md",
    "examples/**/*.md",
    "kaggle/**/README.md",
    "kaggle/_INDEX.md",
    "apps/duecare-ai.com/app/templates/*.html",
    "packages/*/README.md",
)

# Paths that are intentionally frozen point-in-time snapshots — they
# reference stale terms on purpose. Don't fail the audit on them.
EXCLUDE_PATTERNS: tuple[str, ...] = (
    "_archive/",
    "_reference/",
    "docs/adr/",
    "docs/duecare_adversarial_audit.md",  # frozen audit
    "docs/REPO_LAYOUT.md",                # documents the rename
    "docs/notes/",
    ".venv/",
    "node_modules/",
    "site-packages/",
)

# --- Drift terms --------------------------------------------------------------

# (pattern, human label, why it's drift, suggested replacement)
DRIFT_TERMS: tuple[tuple[str, str, str], ...] = (
    (r"\b6 core \+ 5\b", "stale notebook split", "use 3 core + 24 appendix = 27"),
    (r"all 11 submission notebooks", "stale notebook count", "27 submission notebooks (3 core + 24 appendix)"),
    (r"2 core \+ 11 appendix", "stale 13-kernel roster phrase", "3 core + 24 appendix = 27"),
    (r"3 core \+ 23 appendix", "pre-Phase-1 roster phrase (missing A-24)", "3 core + 24 appendix = 27"),
    (r"\b3 hackathon notebooks\b", "stale hackathon-notebook count", "27 competition notebooks"),
    (r"\b7[67]-notebook\b", "stale research-pipeline count (archived)", "drop the explicit count; the legacy notebook arc is archived under _archive/"),
    (r"\bduecare packs pull\b", "unverified CLI command on a public surface", "remove or label as planned"),
    (r"\bduecare packs verify\b", "unverified CLI command on a public surface", "remove or label as planned"),
    (r"\bduecare harness run\b", "unverified CLI command on a public surface", "remove or label as planned"),
    (r"\bsigned pack\b", "stale terminology", "vetted pack"),
    (r"\bOpenClaw\b", "non-DueCare brand name in active prose", "server automation"),
    (r"Try DueCare in 30 seconds", "fragile startup promise", "Try DueCare on Kaggle"),
    (r"Within roughly thirty seconds", "fragile startup promise", "describe startup as variable"),
    (r"About 30 seconds for E4B", "fragile startup promise", "describe startup as variable"),
    (r"Gemma 4 never produced harmful content", "overbroad safety claim", "limit the claim to the dated checked run"),
    (r"\b207 5-tier rubrics\b", "fragile rubric magic number", "cite the current rubric manifest or use a generalized phrase"),
    (r"^# .*Privacy is non-negotiable", "privacy slogan as h1 headline", "concrete data-rule sentence"),
    (r"<h[1-3][^>]*>\s*Privacy is non-negotiable", "privacy slogan as h1-h3 headline", "concrete data-rule sentence"),
)

# --- Six-lane canonical order -------------------------------------------------

# Each lane is a tuple of accepted tokens (any one matches). The lane
# order itself is what we enforce; within a lane, any of the listed
# spellings is acceptable. Add new aliases here when public copy
# legitimately uses a synonym.
LANE_ALIASES_ORDERED: tuple[tuple[str, ...], ...] = (
    ("Platform safety",),
    ("NGO &amp; regulator", "NGO & regulator"),
    ("Individual worker / mobile", "Migrant worker chat", "Migrant worker / mobile"),
    ("Researcher", "Academic research"),
    ("Anonymized knowledge sharing", "Knowledge sharing", "Anonymized sharing"),
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
# Whole-file opt-out only honored when the marker appears in the first
# N lines — typically as a top-of-file HTML comment with a reason.
# This stops documentation files (e.g. docs/AUDIT.md) that explain the
# marker syntax in a body code block from accidentally opting out.
_ALLOW_FILE_HEADER_LINES = 12
_ALLOW_FILE_COMMENT_RE = re.compile(r"^\s*<!--\s*audit-allow-file:drift\b")


def _has_file_allow(text: str) -> bool:
    """Return True only for a real whole-file opt-out marker."""
    in_fence = False
    for line in text.splitlines()[:_ALLOW_FILE_HEADER_LINES]:
        stripped = line.lstrip()
        if stripped.startswith(("```", "~~~")):
            in_fence = not in_fence
            continue
        if not in_fence and _ALLOW_FILE_COMMENT_RE.search(line):
            return True
    return False


def check_drift_terms() -> CheckResult:
    result = CheckResult(name="drift_terms")
    compiled = [(re.compile(p, re.MULTILINE), label, suggest) for p, label, suggest in DRIFT_TERMS]
    files_scanned = 0
    skipped_files: list[str] = []
    for path in _walk_active():
        files_scanned += 1
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        rel = str(path.relative_to(ROOT)).replace("\\", "/")
        # Whole-file opt-out only counts when the marker is an HTML
        # comment in the file's header — not prose or body code blocks.
        if _has_file_allow(text):
            skipped_files.append(rel)
            continue
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
        f"Scanned {files_scanned} active files ({len(skipped_files)} skipped via {_ALLOW_FILE} marker)."
    )
    if skipped_files:
        for rel in sorted(skipped_files):
            result.info.append(f"  skipped: {rel}")
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


# --- Check 3: six-lane order on anchor templates -----------------------------

def check_lane_order() -> CheckResult:
    result = CheckResult(name="six_lane_order")
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
    folders = (sorted(KAGGLE.glob("01-*")) + sorted(KAGGLE.glob("02-*"))
               + sorted(KAGGLE.glob("03-*")) + sorted(KAGGLE.glob("A-*")))
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


# --- Check 5: bundle envelope v1 conformance --------------------------------

# A v1.0 BundleEnvelope (docs/data_primitives.md section 1.1) uses
# schema_version='1.0' and the canonical 'summary' + 'results' top-
# level keys. Kernels emitting BOTH canonical + legacy alias side-by-
# side (Tier-1+2 rollover state) pass — only legacy-ONLY emissions
# fail. The check is regex-based on kernel.py text; it does not
# import the kernel.
_CUSTOM_SCHEMA_VERSION_RE = re.compile(
    r'"schema_version"\s*:\s*"(?!1\.0")[^"]+"'
)
_AGGREGATE_FIELD_RE = re.compile(r'"aggregate"\s*:')
_SUMMARY_FIELD_RE = re.compile(r'"summary"\s*:')
_RESULTS_FIELD_RE = re.compile(r'"results"\s*:')
_LEGACY_RESULTS_FIELD_NAMES: tuple[str, ...] = (
    "ingested", "proposals", "packs_built",
)


def _line_or_above_has_allow(lines: list[str], line_idx_1based: int) -> bool:
    """Return True if line N (1-based) or line N-1 carries _ALLOW_TOKEN."""
    if line_idx_1based < 1 or line_idx_1based > len(lines):
        return False
    if _ALLOW_TOKEN in lines[line_idx_1based - 1]:
        return True
    if line_idx_1based >= 2 and _ALLOW_TOKEN in lines[line_idx_1based - 2]:
        return True
    return False


# Kernels that build a bundle.zip + manifest.json today but omit the
# per-file sha256 checksum map. Grandfathered as of 2026-05-12 so the
# audit's green baseline isn't broken; each one can either adopt the
# duecare.appendix_primitives helpers (which include checksums by
# default) or add an `audit-allow:drift -- <reason>` marker on the
# manifest dict literal in their kernel.py. New kernels written after
# this commit MUST include checksums or join this list with a
# documented reason.
_MANIFEST_CHECKSUM_GRANDFATHERED: frozenset[str] = frozenset({
    "kaggle/_archive/notebooks/A-09-chat-playground-with-agentic-research/kernel.py",
    "kaggle/_archive/notebooks/A-10-runtime-vs-weights-safety-study/kernel.py",
    "kaggle/_archive/notebooks/A-12-pii-fine-tune-eval/kernel.py",
    "kaggle/_archive/notebooks/A-13-multimodal-document-analyzer/kernel.py",
    "kaggle/_archive/notebooks/A-14-on-device-export/kernel.py",
    "kaggle/_archive/notebooks/A-15-ugc-batch-moderator/kernel.py",
    "kaggle/_archive/notebooks/A-16-ngo-local-kb/kernel.py",
    "kaggle/_archive/notebooks/A-17-knowledge-pack-builder/kernel.py",
    "kaggle/_archive/notebooks/A-18-sentinel-research-monitor/kernel.py",
})


def check_bundle_envelope_manifest_checksums() -> CheckResult:
    """Flag kernels that build bundle.zip + manifest.json without checksums.

    Tier-5 standardization (post-Tier 1-4): every kernel that ships
    a `manifest.json` inside `<RUN>_bundle.zip` should also carry the
    canonical `checksums: {filename: sha256_hex, ...}` map so a
    downstream consumer can verify integrity without re-reading the
    full payload. The `duecare.appendix_primitives.write_v1_bundle`
    helper produces this map automatically.

    Honors:
      - the inline ``audit-allow:drift`` marker (line or line-above)
      - the file-level grandfathered list
        ``_MANIFEST_CHECKSUM_GRANDFATHERED`` for the 9 kernels that
        existed pre-Tier-5
    """
    result = CheckResult(name="bundle_envelope_manifest_checksums")
    kernels = sorted(KAGGLE.glob("*/kernel.py"))
    result.info.append(
        f"Inspected {len(kernels)} kernel.py files for manifest checksum map. "
        f"{len(_MANIFEST_CHECKSUM_GRANDFATHERED)} kernels grandfathered."
    )
    manifest_writestr_re = re.compile(
        r'writestr\(\s*[\'"]manifest\.json[\'"]', re.DOTALL
    )
    checksums_key_re = re.compile(r'[\'"]checksums[\'"]\s*:')
    for kp in kernels:
        rel = str(kp.relative_to(ROOT)).replace("\\", "/")
        try:
            text = kp.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if rel in _MANIFEST_CHECKSUM_GRANDFATHERED:
            continue
        if not manifest_writestr_re.search(text):
            continue
        if checksums_key_re.search(text):
            continue
        m = manifest_writestr_re.search(text)
        line_idx = text[: m.start()].count("\n") + 1 if m else 0
        lines = text.splitlines()
        if _line_or_above_has_allow(lines, line_idx):
            continue
        result.findings.append(
            Finding(
                file=rel,
                line=line_idx,
                rule="bundle_envelope_v1.manifest_checksums",
                snippet='manifest.json written without "checksums" map',
                suggestion=(
                    "use duecare.appendix_primitives.write_v1_bundle "
                    "(emits checksums automatically) OR add a "
                    "'\"checksums\": {filename: sha256_hex, ...}' entry "
                    "to the manifest dict OR add this folder to "
                    "_MANIFEST_CHECKSUM_GRANDFATHERED with a documented "
                    "reason"
                ),
            )
        )
    return result


def check_bundle_envelope_v1() -> CheckResult:
    """Scan each kaggle/*/kernel.py for v1.0 BundleEnvelope drift.

    Honors the same ``audit-allow:drift`` inline / above-line marker
    as check_drift_terms, so a kernel using a flagged key for a
    non-envelope purpose can opt out at the source line with a
    one-sentence justification.
    """
    result = CheckResult(name="bundle_envelope_v1")
    kernels = sorted(KAGGLE.glob("*/kernel.py"))
    result.info.append(
        f"Inspected {len(kernels)} kernel.py files for v1.0 envelope shape."
    )
    for kp in kernels:
        rel = str(kp.relative_to(ROOT)).replace("\\", "/")
        try:
            text = kp.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        lines = text.splitlines()

        # Drift 1: custom schema_version strings (not the literal "1.0")
        for m in _CUSTOM_SCHEMA_VERSION_RE.finditer(text):
            line_idx = text[: m.start()].count("\n") + 1
            if _line_or_above_has_allow(lines, line_idx):
                continue
            result.findings.append(
                Finding(
                    file=rel,
                    line=line_idx,
                    rule="bundle_envelope_v1.schema_version",
                    snippet=m.group(0)[:120],
                    suggestion=(
                        "use schema_version: '1.0' "
                        "(move semantic identifier to a separate field "
                        "like 'handoff_kind')"
                    ),
                )
            )

        # Drift 2: 'aggregate' field used WITHOUT canonical 'summary' alongside
        if _AGGREGATE_FIELD_RE.search(text) and not _SUMMARY_FIELD_RE.search(text):
            agg_line_idx = next(
                (i for i, ln in enumerate(lines, start=1)
                 if _AGGREGATE_FIELD_RE.search(ln)),
                0,
            )
            if not _line_or_above_has_allow(lines, agg_line_idx):
                result.findings.append(
                    Finding(
                        file=rel,
                        line=agg_line_idx,
                        rule="bundle_envelope_v1.aggregate",
                        snippet='emits "aggregate" with no "summary" alongside',
                        suggestion=(
                            "rename to 'summary' "
                            "(or emit BOTH during rollover)"
                        ),
                    )
                )

        # Drift 3: legacy results-array name WITHOUT canonical 'results' alongside
        if not _RESULTS_FIELD_RE.search(text):
            for alias in _LEGACY_RESULTS_FIELD_NAMES:
                alias_re = re.compile(rf'"{alias}"\s*:')
                if alias_re.search(text):
                    alias_line_idx = next(
                        (i for i, ln in enumerate(lines, start=1)
                         if alias_re.search(ln)),
                        0,
                    )
                    if _line_or_above_has_allow(lines, alias_line_idx):
                        continue
                    result.findings.append(
                        Finding(
                            file=rel,
                            line=alias_line_idx,
                            rule="bundle_envelope_v1.results_alt",
                            snippet=(
                                f'emits "{alias}" with no '
                                f'"results" alongside'
                            ),
                            suggestion=(
                                f"rename '{alias}[]' to 'results[]' "
                                "(or emit BOTH during rollover)"
                            ),
                        )
                    )
    return result


# --- Check 7: local documentation links --------------------------------------

_LOCAL_LINK_RE = re.compile(
    r"(?<!!)\[[^\]]+\]\(([^)]+)\)|(?:href|src)=[\"']([^\"']+)[\"']",
    re.IGNORECASE,
)
_SCHEME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*:")


def _normalise_local_link(raw: str) -> str | None:
    """Return a repo-local link target, or None for ignored links."""

    value = raw.strip()
    if not value or value.startswith("#"):
        return None
    if value.startswith(("/", "{", "$", "`")):
        return None
    if "${" in value or "{{" in value or "}}" in value:
        return None
    if _SCHEME_RE.match(value):
        return None

    if value.startswith("<") and value.endswith(">"):
        value = value[1:-1].strip()
    elif " " in value:
        # Markdown allows optional titles after whitespace:
        # [text](path.md "title"). Keep the target only.
        value = value.split()[0]

    value = value.split("#", 1)[0].split("?", 1)[0].strip()
    if not value:
        return None
    value = urllib.parse.unquote(value)
    if value.startswith(("/", "{", "$")) or "${" in value:
        return None
    return value


def _fenced_code_ranges(text: str) -> list[tuple[int, int]]:
    ranges: list[tuple[int, int]] = []
    in_fence = False
    start = 0
    offset = 0
    for line in text.splitlines(keepends=True):
        stripped = line.lstrip()
        if stripped.startswith(("```", "~~~")):
            if in_fence:
                ranges.append((start, offset + len(line)))
                in_fence = False
            else:
                start = offset
                in_fence = True
        offset += len(line)
    if in_fence:
        ranges.append((start, len(text)))
    return ranges


def _inside_ranges(index: int, ranges: list[tuple[int, int]]) -> bool:
    return any(start <= index < end for start, end in ranges)


def check_local_doc_links() -> CheckResult:
    result = CheckResult(name="local_doc_links")
    files_scanned = 0
    links_checked = 0
    for path in _walk_active():
        if path.suffix.lower() not in {".md", ".html"}:
            continue
        rel = str(path.relative_to(ROOT)).replace("\\", "/")
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        files_scanned += 1
        code_ranges = _fenced_code_ranges(text)
        for match in _LOCAL_LINK_RE.finditer(text):
            if _inside_ranges(match.start(), code_ranges):
                continue
            raw = (match.group(1) or match.group(2) or "").strip()
            target_rel = _normalise_local_link(raw)
            if target_rel is None:
                continue
            links_checked += 1
            target = (path.parent / target_rel).resolve()
            try:
                inside_repo = target == ROOT or ROOT in target.parents
            except RuntimeError:
                inside_repo = False
            if not inside_repo or not target.exists():
                line = text[: match.start()].count("\n") + 1
                result.findings.append(
                    Finding(
                        file=rel,
                        line=line,
                        rule="missing_local_link",
                        snippet=raw[:160],
                        suggestion=(
                            "point this link at an existing repo file, "
                            "or make it an explicit external URL"
                        ),
                    )
                )
    result.info.append(
        f"Checked {links_checked} repo-local links across {files_scanned} public files."
    )
    return result


def check_training_model_fallback_registry() -> CheckResult:
    """Require every governed training or judge role to retain multiple routes."""
    result = CheckResult(name="training_model_fallback_registry")
    registry_path = ROOT / "configs" / "duecare" / "model_fallbacks.json"
    try:
        from validate_model_fallback_registry import validate_registry

        summary = validate_registry(json.loads(registry_path.read_text(encoding="utf-8")))
    except Exception as exc:
        result.findings.append(
            Finding(
                file=registry_path.relative_to(ROOT).as_posix(),
                line=0,
                rule="invalid_model_fallback_registry",
                snippet=f"{type(exc).__name__}: {exc}",
                suggestion=(
                    "declare at least two capability-compatible candidates per policy "
                    "and retain the attempt-receipt rule"
                ),
            )
        )
        return result
    policy_counts = {
        name: policy["candidate_count"] for name, policy in summary["policies"].items()
    }
    result.info.append(f"Validated governed model candidate counts: {policy_counts}")
    return result


def check_published_dataset_claims() -> CheckResult:
    """Every dataset SHA in the claims registry must appear in the public docs.

    This keeps docs/training_and_finetuning.md and the committed
    published_dataset_claims.json registry from drifting apart. It does not
    require the gitignored staged artifacts (use
    scripts/verify_training_dataset_claims.py for the byte-level re-derivation),
    so it stays green on a clean checkout while still catching a stale doc SHA.
    """
    result = CheckResult(name="published_dataset_claims")
    registry_path = ROOT / "configs" / "duecare" / "training" / "published_dataset_claims.json"
    doc_path = ROOT / "docs" / "training_and_finetuning.md"
    try:
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        docs = doc_path.read_text(encoding="utf-8")
    except OSError as exc:
        result.findings.append(
            Finding(
                file=registry_path.relative_to(ROOT).as_posix(),
                line=0,
                rule="missing_published_dataset_claims",
                snippet=f"{type(exc).__name__}: {exc}",
                suggestion="restore the committed published-dataset claims registry",
            )
        )
        return result
    claims = registry.get("claims") or []
    for claim in claims:
        sha = str(claim.get("release_manifest_sha256") or "")
        if sha and sha not in docs:
            result.findings.append(
                Finding(
                    file=doc_path.relative_to(ROOT).as_posix(),
                    line=0,
                    rule="dataset_claim_not_in_docs",
                    snippet=f"{claim.get('dataset_id')} sha {sha[:16]}… absent from training doc",
                    suggestion="update the doc SHA or the claims registry so they match",
                )
            )
    result.info.append(f"Cross-checked {len(claims)} published-dataset claim SHAs against the training doc.")
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
        choices=[
            "drift_terms",
            "hub_routes_200",
            "six_lane_order",
            "kaggle_lane_labels",
            "bundle_envelope_v1",
            "bundle_envelope_manifest_checksums",
            "local_doc_links",
            "training_model_fallback_registry",
            "published_dataset_claims",
        ],
        help="skip a check (repeatable)",
    )
    args = parser.parse_args()

    runners = [
        ("drift_terms", check_drift_terms),
        ("hub_routes_200", check_routes_200),
        ("six_lane_order", check_lane_order),
        ("kaggle_lane_labels", check_kaggle_lane_labels),
        ("bundle_envelope_v1", check_bundle_envelope_v1),
        ("bundle_envelope_manifest_checksums",
         check_bundle_envelope_manifest_checksums),
        ("local_doc_links", check_local_doc_links),
        ("training_model_fallback_registry", check_training_model_fallback_registry),
        ("published_dataset_claims", check_published_dataset_claims),
    ]
    checks = [run() for name, run in runners if name not in args.skip]

    if args.json:
        print(render_json(checks))
    else:
        print(render_text(checks))

    return 0 if all(c.ok for c in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
