"""Deterministic hashing helpers for config + content."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def hash_config(config: Any) -> str:
    """Deterministic sha256 of a JSON-serializable config object."""
    payload = json.dumps(config, sort_keys=True, default=str).encode()
    return hashlib.sha256(payload).hexdigest()


def compute_checksum(content: str | bytes) -> str:
    """SHA256 of arbitrary content. Used for staging-DB dedup and audit."""
    if isinstance(content, str):
        content = content.encode()
    return hashlib.sha256(content).hexdigest()


def simhash(text: str, num_bits: int = 64) -> int:
    """Cheap SimHash for near-duplicate detection.

    Not a production-grade SimHash, but good enough for deduping synthetic
    probes where we want near-duplicates collapsed. Uses word-level tokens.
    """
    from collections import Counter

    tokens = text.lower().split()
    if not tokens:
        return 0
    weights = Counter(tokens)
    v = [0] * num_bits
    for token, w in weights.items():
        token_hash = int(hashlib.md5(token.encode()).hexdigest(), 16)
        for i in range(num_bits):
            bit = (token_hash >> i) & 1
            v[i] += w if bit else -w
    result = 0
    for i in range(num_bits):
        if v[i] >= 0:
            result |= 1 << i
    return result
