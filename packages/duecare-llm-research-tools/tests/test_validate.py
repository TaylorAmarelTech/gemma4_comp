"""Tests for the acquisition validation suite (meaningfulness + retrieval + semantic)."""
from __future__ import annotations

from duecare.research_tools.validate import (
    cosine, meaningful_enough, meaningfulness, query_utility,
    summarize_retrieval, summarize_semantic,
)

PROSE = ("Under the convention a domestic worker keeps custody of her passport at all "
         "times during employment, and the employer bears the full cost of recruitment, "
         "deployment, medical examination, and travel. Any fee collected from the worker "
         "is unlawful and must be refunded in full, because charging the worker shifts the "
         "cost of recruitment onto the person least able to bear it and creates a debt that "
         "can be used to coerce continued labour.")
NAV = "Home About Contact Privacy Terms Login Search Help FAQ Careers News Events Sitemap"
STUFFED = ("fee fee fee visa visa visa passport passport passport worker worker worker "
           "agency agency agency permit permit permit deduction deduction deduction wages wages")


def test_meaningfulness_prose_is_high():
    m = meaningfulness(PROSE)
    assert m["tier"] in ("medium", "high")
    assert m["n_words"] >= 60


def test_meaningfulness_short_nav_is_low():
    assert meaningfulness(NAV)["tier"] == "low"           # too short / fragment


def test_meaningfulness_keyword_stuffed_is_low():
    m = meaningfulness(STUFFED)
    assert m["tier"] == "low" and m["ttr"] < 0.3          # repetitive -> fails ttr band


def test_meaningful_enough_threshold():
    assert meaningful_enough(PROSE, min_tier="medium") is True
    assert meaningful_enough(NAV, min_tier="medium") is False


def test_query_utility_flags():
    retrieved = [
        {"id": "corpus_a", "is_custom": False},
        {"id": "acq_1", "is_custom": True},
        {"id": "corpus_b", "is_custom": False},
    ]
    u = query_utility(retrieved, k=3)
    assert u["any"] is True and u["top1"] is False
    assert u["ids"] == ["acq_1"] and u["best_rank"] == 2
    # acquired at rank 1 -> outranks corpus
    u2 = query_utility([{"id": "acq_x", "is_custom": True}, {"id": "c", "is_custom": False}], k=3)
    assert u2["top1"] is True


def test_summarize_retrieval():
    per_q = [
        {"any": True, "top1": True, "ids": ["a1"]},
        {"any": True, "top1": False, "ids": ["a2"]},
        {"any": False, "top1": False, "ids": []},
    ]
    s = summarize_retrieval(per_q, n_acquired=5)
    assert s["pct_queries_acquired_in_topk"] == round(100 * 2 / 3, 1)
    assert s["pct_queries_acquired_top1"] == round(100 * 1 / 3, 1)
    assert s["acquired_utilized"] == 2 and s["pct_acquired_utilized"] == 40.0


def test_cosine():
    assert cosine([1.0, 0.0], [0.0, 1.0]) == 0.0
    assert round(cosine([1.0, 1.0], [1.0, 1.0]), 5) == 1.0
    assert cosine([], [1.0]) == 0.0


def test_summarize_semantic():
    s = summarize_semantic([0.5, 0.2, 0.4], threshold=0.35)
    assert s["pct_queries_semantic_match"] == round(100 * 2 / 3, 1)
    assert s["mean_best_similarity"] == round((0.5 + 0.2 + 0.4) / 3, 3)
