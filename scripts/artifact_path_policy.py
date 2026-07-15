#!/usr/bin/env python3
"""Shared path policy for generated handoff artifact maps.

Generated report metadata should expose normal repo artifacts as repo-relative
paths, but scratch/temp output under hidden workspace directories should be
reported as external handoff artifacts.
"""
from __future__ import annotations

import pathlib
import re


PRIVATE_PATH_HINT_RE = re.compile(
    r"(?i)(?:[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}|(?:file|https?|ftp|s3|mailto):|\\Users\\|/users/|OneDrive/Documents|AppData/Local|\d{8,})"
)
SAFE_EXTERNAL_ARTIFACT_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,120}$")


def _external_artifact_path(path: pathlib.Path) -> str:
    name = path.name
    if SAFE_EXTERNAL_ARTIFACT_NAME_RE.fullmatch(name) and not PRIVATE_PATH_HINT_RE.search(name):
        return f"external/{name}"
    return "external/custom_or_invalid"


def handoff_artifact_path(path: pathlib.Path, *, root: pathlib.Path) -> str:
    """Return the stable artifact-map path for ``path`` relative to ``root``."""
    candidate = path if path.is_absolute() else (root / path)
    try:
        rel = candidate.resolve().relative_to(root.resolve())
    except (OSError, ValueError):
        return _external_artifact_path(path)
    if any(part.startswith(".") for part in rel.parts):
        return _external_artifact_path(path)
    rel_text = rel.as_posix()
    if PRIVATE_PATH_HINT_RE.search(rel_text):
        return "external/custom_or_invalid"
    return rel_text
