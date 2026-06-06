"""Validation suite for acquired content -- prove it's GENUINELY HELPFUL, not
just keyword-relevant. Four layers (this module holds the deterministic ones;
the semantic + lift layers are driven by scripts with pluggable backends):

  * meaningfulness  -- per-chunk substance gate (drop boilerplate / nav / list
    fragments that pass the relevance gate but carry no real information).
  * retrieval utility (keyword) -- does the REAL BM25 retrieval surface an
    acquired doc for real queries, and does it OUTRANK the existing corpus?
  * semantic        -- (script) embeddings similarity of acquired docs to real
    queries, via an injected embed backend.
  * lift            -- (script) does the enriched corpus improve harness outputs.

Deterministic + offline here; pure functions so they're testable without I/O.
"""
from __future__ import annotations

import re

_WORD = re.compile(r"[^\W\d_]+", re.UNICODE)   # alphabetic word runs
_SENTSPLIT = re.compile(r"[.!?]+(?:\s|$)")

_MEANING_MIN_WORDS = 30


def meaningfulness(text: str) -> dict:
    """Score whether a chunk is substantive prose vs boilerplate/nav/list noise.
    Returns ``{tier, score, n_words, ttr, avg_sentence_words, alpha_ratio}``.
    high = reads like real informative prose; low = too short / repetitive /
    fragment-y / symbol-heavy (gated out by default)."""
    t = text or ""
    words = _WORD.findall(t)
    n = len(words)
    if n < _MEANING_MIN_WORDS:
        return {"tier": "low", "score": 0.0, "n_words": n, "reason": "too_short",
                "ttr": 0.0, "avg_sentence_words": 0.0, "alpha_ratio": 0.0}
    uniq = len({w.lower() for w in words})
    ttr = uniq / n                                   # type-token ratio
    real_sents = [s for s in _SENTSPLIT.split(t) if len(s.split()) >= 4]
    n_sents = max(1, len(real_sents))
    avg_sentence_words = n / n_sents
    alpha_ratio = sum(len(w) for w in words) / max(1, len(t))  # letters / chars

    score = 0.0
    score += 1.0 if n >= 60 else 0.5                 # enough material
    score += 1.0 if 0.30 <= ttr <= 0.90 else 0.0     # not stuffed, not all-distinct (link list)
    score += 1.0 if 6 <= avg_sentence_words <= 55 else 0.0   # real sentences, not fragments
    score += 1.0 if alpha_ratio >= 0.55 else 0.0     # prose, not symbol/number soup
    tier = "high" if score >= 3.5 else "medium" if score >= 2.0 else "low"
    return {"tier": tier, "score": round(score, 1), "n_words": n,
            "ttr": round(ttr, 2), "avg_sentence_words": round(avg_sentence_words, 1),
            "alpha_ratio": round(alpha_ratio, 2)}


def meaningful_enough(text: str, *, min_tier: str = "medium") -> bool:
    rank = {"low": 0, "medium": 1, "high": 2}
    return rank[meaningfulness(text)["tier"]] >= rank.get(min_tier, 1)


# --- retrieval utility (keyword / BM25) ------------------------------------
def query_utility(retrieved: list[dict], *, k: int) -> dict:
    """Per-query signal from a top-k retrieval result (each doc has ``is_custom``
    True iff it's an acquired doc). ``any`` = an acquired doc made top-k;
    ``top1`` = an acquired doc OUTRANKED the whole existing corpus."""
    topk = retrieved[:k]
    acquired_ids = [d.get("id") for d in topk if d.get("is_custom")]
    best_rank = next((i + 1 for i, d in enumerate(topk) if d.get("is_custom")), None)
    return {"any": bool(acquired_ids), "top1": bool(topk and topk[0].get("is_custom")),
            "ids": acquired_ids, "best_rank": best_rank}


def summarize_retrieval(per_query: list[dict], *, n_acquired: int) -> dict:
    """Aggregate per-query utility into a 'is the added set genuinely retrieved'
    report. Low ``pct_acquired_utilized`` => much of what we added is never
    surfaced for real queries (relevant but not helpful)."""
    n = len(per_query) or 1
    used: set = set()
    for r in per_query:
        used.update(r["ids"])
    return {
        "queries": len(per_query),
        "pct_queries_acquired_in_topk": round(100 * sum(r["any"] for r in per_query) / n, 1),
        "pct_queries_acquired_top1": round(100 * sum(r["top1"] for r in per_query) / n, 1),
        "acquired_utilized": len(used),
        "acquired_total": n_acquired,
        "pct_acquired_utilized": round(100 * len(used) / (n_acquired or 1), 1),
    }


# --- semantic helpers (backend injected by the script) ---------------------
def cosine(a: list[float], b: list[float]) -> float:
    """Cosine similarity of two equal-length vectors (0 if either is empty)."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    return dot / (na * nb) if na and nb else 0.0


def summarize_semantic(best_sims: list[float], *, threshold: float = 0.35) -> dict:
    """Given, per query, the best cosine similarity to any acquired doc, report
    how often the acquired set is a SEMANTIC match (>= threshold)."""
    n = len(best_sims) or 1
    matched = sum(1 for s in best_sims if s >= threshold)
    return {
        "queries": len(best_sims),
        "threshold": threshold,
        "pct_queries_semantic_match": round(100 * matched / n, 1),
        "mean_best_similarity": round(sum(best_sims) / n, 3),
    }
