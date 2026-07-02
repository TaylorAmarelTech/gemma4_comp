#!/usr/bin/env python3
"""Shared path policy for generated handoff artifact maps.

Generated report metadata should expose normal repo artifacts as repo-relative
paths, but scratch/temp output under hidden workspace directories should be
reported as external handoff artifacts.
"""
from __future__ import annotations

import pathlib


def handoff_artifact_path(path: pathlib.Path, *, root: pathlib.Path) -> str:
    """Return the stable artifact-map path for ``path`` relative to ``root``."""
    candidate = path if path.is_absolute() else (root / path)
    try:
        rel = candidate.resolve().relative_to(root.resolve())
    except ValueError:
        return f"external/{path.name}"
    if any(part.startswith(".") for part in rel.parts):
        return f"external/{path.name}"
    return rel.as_posix()
