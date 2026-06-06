"""Scaled near-duplicate detection for the acquisition pipeline.

The existing merge dedups on exact id only; at 10k-doc scale that lets in
paraphrase / boilerplate / re-fetched near-duplicates. This adds two
DETERMINISTIC, OFFLINE, stdlib signals:

  * ``content_key`` -- sha256 of normalized text (exact-dup, fast).
  * ``simhash64``   -- a 64-bit SimHash over word-shingles; two texts are
    near-duplicates when their signatures are within a small Hamming distance.

No RNG, no model, no network -- a given text always yields the same signature,
so dedup decisions are reproducible (the project's "real, not faked" invariant).
"""
from __future__ import annotations

import hashlib
import re
from typing import Callable, Iterable

_WS = re.compile(r"\s+")
_WORD = re.compile(r"\w+", re.UNICODE)


def normalize(text: str) -> str:
    return _WS.sub(" ", (text or "")).strip().lower()


def content_key(text: str) -> str:
    """sha256 of normalized text -- exact-duplicate key."""
    return hashlib.sha256(normalize(text).encode("utf-8", "ignore")).hexdigest()


def _shingles(text: str, k: int = 5) -> list[str]:
    """Overlapping k-word shingles of the normalized text (dedup unit)."""
    words = _WORD.findall(normalize(text))
    if len(words) < k:
        return [" ".join(words)] if words else []
    return [" ".join(words[i:i + k]) for i in range(len(words) - k + 1)]


def _h64(s: str) -> int:
    """Stable 64-bit hash of a shingle (blake2b, unsalted -> deterministic)."""
    return int.from_bytes(hashlib.blake2b(s.encode("utf-8"), digest_size=8).digest(), "big")


def simhash64(text: str, *, k: int = 5) -> int:
    """64-bit SimHash. Similar texts -> small Hamming distance. Deterministic."""
    shingles = _shingles(text, k)
    if not shingles:
        return 0
    bits = [0] * 64
    for sh in shingles:
        h = _h64(sh)
        for b in range(64):
            bits[b] += 1 if (h >> b) & 1 else -1
    sig = 0
    for b in range(64):
        if bits[b] > 0:
            sig |= (1 << b)
    return sig


def hamming(a: int, b: int) -> int:
    return bin(a ^ b).count("1")


def is_near_dup(sig: int, existing_sigs: Iterable[int], *, max_dist: int = 3) -> bool:
    """True if ``sig`` is within ``max_dist`` bits of any existing signature."""
    return any(hamming(sig, e) <= max_dist for e in existing_sigs)


def dedup_new(
    candidates: list[dict],
    *,
    text_of: Callable[[dict], str],
    existing_keys: set[str] | None = None,
    existing_sigs: list[int] | None = None,
    max_dist: int = 3,
) -> tuple[list[dict], list[dict]]:
    """Partition ``candidates`` into (kept, dropped) by exact + near-dup against
    the existing corpus AND against earlier-kept candidates in this batch.

    ``text_of`` extracts the dedup text from a candidate dict. Deterministic:
    candidates are processed in order, first occurrence wins. Each dropped item
    is annotated with ``_dup_reason`` ('exact' | 'near'). Pure -- writes nothing.
    """
    seen_keys: set[str] = set(existing_keys or set())
    sigs: list[int] = list(existing_sigs or [])
    kept: list[dict] = []
    dropped: list[dict] = []
    for c in candidates:
        text = text_of(c)
        key = content_key(text)
        if key in seen_keys:
            dropped.append({**c, "_dup_reason": "exact"})
            continue
        sig = simhash64(text)
        if sigs and is_near_dup(sig, sigs, max_dist=max_dist):
            dropped.append({**c, "_dup_reason": "near"})
            continue
        seen_keys.add(key)
        sigs.append(sig)
        kept.append(c)
    return kept, dropped
