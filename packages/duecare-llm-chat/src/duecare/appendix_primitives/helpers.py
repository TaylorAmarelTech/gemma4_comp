"""Shared utility helpers for kernel bundle building.

These are the small pieces hand-rolled in many kernels.py files;
centralizing them here lets future migrations swap a 4-line helper
for a 1-line import without changing semantics.
"""
from __future__ import annotations

import hashlib
from pathlib import Path


def sha256_of_file(path: Path, *, chunk_size: int = 8192) -> str:
    """Return the SHA-256 hex digest of the file at ``path``.

    Mirrors the helper used inside ``write_v1_bundle`` but exposed
    so kernels that build their own zip layout can still emit the
    canonical ``manifest.json -> checksums`` block without
    duplicating the SHA-256 helper.
    """
    h = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()
