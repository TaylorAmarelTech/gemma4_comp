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
    """True if ``sig`` is within ``max_dist`` bits of any existing signature.
    O(N) linear scan -- fine for small sets; use ``SimHashIndex`` at scale."""
    return any(hamming(sig, e) <= max_dist for e in existing_sigs)


class SimHashIndex:
    """Banded LSH over 64-bit SimHashes for fast near-dup queries at scale.

    By the pigeonhole principle, two signatures within Hamming distance ``d``
    must agree exactly on at least one of ``B`` equal bands whenever ``B > d``.
    So we bucket each signature by ``(band_index, band_value)`` and, on query,
    only Hamming-check signatures sharing a band -- turning the O(N) linear scan
    into O(bucket size). EXACT (no false negatives) as long as ``bands > max_dist``
    on every query; the default 4 bands covers the default ``max_dist <= 3``.
    Deterministic; no RNG.
    """

    def __init__(self, sigs: Iterable[int] = (), *, bands: int = 4) -> None:
        self.bands = max(2, bands)
        self.width = 64 // self.bands
        self._buckets: dict[tuple[int, int], list[int]] = {}
        self._n = 0
        for s in sigs:
            self.add(s)

    def _band_keys(self, sig: int) -> list[tuple[int, int]]:
        keys = []
        for b in range(self.bands):
            shift = b * self.width
            w = self.width if b < self.bands - 1 else 64 - shift  # last band takes the remainder
            keys.append((b, (sig >> shift) & ((1 << w) - 1)))
        return keys

    def add(self, sig: int) -> None:
        for k in self._band_keys(sig):
            self._buckets.setdefault(k, []).append(sig)
        self._n += 1

    def query_near(self, sig: int, *, max_dist: int = 3) -> bool:
        """True if any indexed signature is within ``max_dist`` bits of ``sig``."""
        checked: set[int] = set()
        for k in self._band_keys(sig):
            for cand in self._buckets.get(k, ()):
                if cand in checked:
                    continue
                checked.add(cand)
                if hamming(sig, cand) <= max_dist:
                    return True
        return False

    def __len__(self) -> int:
        return self._n


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
