"""Tests for scaled near-duplicate detection (acquisition pipeline)."""
from __future__ import annotations

from duecare.research_tools.dedup import (
    content_key, simhash64, hamming, dedup_new,
)

# Synthetic public-law-style paragraphs (no real PII). A and B are near-dups
# (a few words changed); C is a distinct topic.
A = ("Recruitment fees may not be charged to the migrant worker under any "
     "circumstances. The employer or principal bears the full cost of "
     "recruitment, deployment, medical examination, and travel. Any fee "
     "collected from the worker is illegal and must be refunded in full, and "
     "passport retention to secure repayment is prohibited.")
B = ("Recruitment charges may not be billed to the migrant worker under any "
     "circumstances. The employer or principal bears the entire cost of "
     "recruitment, deployment, medical examination, and travel. Any fee "
     "collected from the worker is unlawful and must be refunded in full, and "
     "passport retention to secure repayment is prohibited.")
C = ("Carbon border adjustment mechanisms require importers to surrender "
     "certificates matching the embedded emissions of covered goods. The "
     "scheme phases in alongside the emissions trading system and aims to "
     "prevent carbon leakage to jurisdictions with weaker climate policy.")


def test_content_key_normalizes_whitespace_and_case():
    assert content_key("Hello   World") == content_key("hello world")
    assert content_key("a") != content_key("b")


def test_simhash_deterministic():
    assert simhash64(A) == simhash64(A)


def test_near_dup_closer_than_distinct():
    near = hamming(simhash64(A), simhash64(B))
    far = hamming(simhash64(A), simhash64(C))
    assert near < far  # a near-paraphrase is closer than an unrelated doc


def test_exact_dup_dropped():
    kept, dropped = dedup_new([{"t": A}, {"t": A}], text_of=lambda d: d["t"])
    assert len(kept) == 1 and len(dropped) == 1
    assert dropped[0]["_dup_reason"] == "exact"


def test_near_dropped_distinct_kept():
    near = hamming(simhash64(A), simhash64(B))
    far = hamming(simhash64(A), simhash64(C))
    thr = (near + far) // 2  # threshold between near and distinct
    kept, dropped = dedup_new(
        [{"t": A}, {"t": B}, {"t": C}], text_of=lambda d: d["t"], max_dist=thr)
    kept_t = {k["t"] for k in kept}
    assert A in kept_t and C in kept_t and B not in kept_t
    assert any(d["_dup_reason"] == "near" for d in dropped)


def test_dedup_against_existing_corpus():
    kept, dropped = dedup_new(
        [{"t": A}], text_of=lambda d: d["t"], existing_keys={content_key(A)})
    assert kept == [] and dropped[0]["_dup_reason"] == "exact"


def test_distinct_all_kept():
    kept, _ = dedup_new([{"t": A}, {"t": C}], text_of=lambda d: d["t"], max_dist=3)
    assert len(kept) == 2
