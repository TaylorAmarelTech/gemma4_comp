"""Salted-hash placeholder builder."""
from __future__ import annotations

import hashlib


DEFAULT_SALT = "duecare-default-salt-v1"


def placeholder(label: str, raw: str, salt: str = DEFAULT_SALT) -> str:
    """Deterministic placeholder for a raw PII string, stable per (salt, raw)."""
    h = hashlib.sha256((salt + "::" + raw).encode("utf-8")).hexdigest()[:8]
    return f"<{label}_{h}>"


def raw_sha256(raw: str) -> str:
    """SHA-256 of the raw string. Stored in the audit trail; the raw is not."""
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
