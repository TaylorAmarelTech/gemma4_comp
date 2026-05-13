"""Regression tests for reproducible Kaggle bootstrap installs.

Two-phase policy:
  - DEV (``configs/submission_freeze.json`` ``frozen=false``):
    Moving Git refs like ``main`` are allowed so we can iterate fast
    without re-pinning every commit.
  - SUBMISSION (``frozen=true``):
    Only immutable SHA pins are allowed. Run
    ``scripts/freeze_kernels_for_submission.py`` to flip this flag.
"""

from __future__ import annotations

import json
import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
UNPINNED_GIT_INSTALL_RE = re.compile(
    r"git\+https://[^\s\'\")]+\.git(?=$|[\s\'\")])"
)
MOVING_GIT_BRANCH_RE = re.compile(
    r"git\+https://[^\s\'\")]+\.git@(?:main|master|HEAD)(?=[#\s\'\")])",
    re.IGNORECASE,
)
MOVING_RAW_GITHUB_REF_RE = re.compile(
    r"https://raw\.githubusercontent\.com/[^\s\'\")]+/(?:main|master|HEAD)/",
    re.IGNORECASE,
)
MOVING_REF_ASSIGNMENT_RE = re.compile(
    r"\b(?:COMMIT_SHA|PINNED_COMMIT|GIT_REF|DUECARE_COMMIT_SHA)\s*=\s*[\'\"](?:main|master|HEAD)[\'\"]",
    re.IGNORECASE,
)


def _submission_is_frozen() -> bool:
    freeze_path = REPO_ROOT / "configs" / "submission_freeze.json"
    if not freeze_path.exists():
        return False
    try:
        payload = json.loads(freeze_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    return bool(payload.get("frozen"))


def _active_install_sources() -> list[Path]:
    kaggle_sources = sorted((REPO_ROOT / "kaggle").glob("*/kernel.py"))
    builder_sources = sorted((REPO_ROOT / "scripts").glob("build_notebook_*.py"))
    helper_sources = [REPO_ROOT / "scripts" / "finetune_unsloth.py"]
    return [
        path
        for path in [*kaggle_sources, *builder_sources, *helper_sources]
        if path.exists() and "_archive" not in path.parts
    ]


def test_kaggle_bootstrap_installs_have_no_unpinned_git_urls() -> None:
    """Even in dev mode, a bare ``git+https://...gh.git`` (no @ref) is rejected."""
    offenders: list[str] = []
    for path in _active_install_sources():
        text = path.read_text(encoding="utf-8")
        for match in UNPINNED_GIT_INSTALL_RE.finditer(text):
            rel_path = path.relative_to(REPO_ROOT).as_posix()
            offenders.append(f"{rel_path}: {match.group(0)}")
    assert offenders == []


def test_kaggle_bootstrap_installs_do_not_use_moving_git_branches() -> None:
    """When the submission freeze is on, every install must pin an immutable SHA."""
    if not _submission_is_frozen():
        return

    offenders: list[str] = []
    for path in _active_install_sources():
        text = path.read_text(encoding="utf-8")
        for match in MOVING_GIT_BRANCH_RE.finditer(text):
            rel_path = path.relative_to(REPO_ROOT).as_posix()
            offenders.append(f"{rel_path}: {match.group(0)}")
        for match in MOVING_RAW_GITHUB_REF_RE.finditer(text):
            rel_path = path.relative_to(REPO_ROOT).as_posix()
            offenders.append(f"{rel_path}: {match.group(0)}")
        for match in MOVING_REF_ASSIGNMENT_RE.finditer(text):
            rel_path = path.relative_to(REPO_ROOT).as_posix()
            offenders.append(f"{rel_path}: {match.group(0)}")
    assert offenders == [], (
        "Submission freeze is enabled but the following kernels still "
        "use moving refs. Re-run scripts/freeze_kernels_for_submission.py: "
        + ", ".join(offenders)
    )


def test_active_preview_notebooks_have_cell_language_metadata() -> None:
    offenders: list[str] = []
    for notebook_path in sorted((REPO_ROOT / "kaggle").glob("*/notebook.ipynb")):
        notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
        for index, cell in enumerate(notebook.get("cells", []), start=1):
            metadata = cell.get("metadata") or {}
            expected_language = (
                "python" if cell.get("cell_type") == "code" else cell.get("cell_type")
            )
            if "id" not in metadata or metadata.get("language") != expected_language:
                rel_path = notebook_path.relative_to(REPO_ROOT).as_posix()
                offenders.append(f"{rel_path} cell {index}")

    assert offenders == []
