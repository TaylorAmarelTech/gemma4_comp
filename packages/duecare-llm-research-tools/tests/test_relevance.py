"""Tests for trafficking-domain relevance scoring (the promotion confidence gate)."""
from __future__ import annotations

from duecare.research_tools.relevance import passes, relevance

STRONG = ("Under ILO C189 a domestic worker on the PH-HK corridor keeps her passport; "
          "recruitment fees may not be charged and debt bondage via salary deduction is forced labour.")
MEDIUM = "The recruitment agency deployed several overseas workers last quarter."
OFFTOPIC = ("Carbon border adjustment mechanisms require importers to surrender certificates "
            "matching the embedded emissions of covered goods under the trading scheme.")


def test_strong_passage_is_high():
    r = relevance(STRONG)
    assert r["tier"] == "high"
    assert r["entities"] and len(r["families"]) >= 2


def test_medium_passage():
    r = relevance(MEDIUM)
    assert r["tier"] == "medium"            # 'migrant' family (recruitment agency / overseas workers)


def test_offtopic_is_low():
    r = relevance(OFFTOPIC)
    assert r["tier"] == "low"
    assert not r["entities"] and not r["families"]


def test_source_signal_scores_but_does_not_gate():
    # a generic page from a trafficking-adjacent domain must earn promotion on its
    # own text: an inherited source tag raises the score but NOT the tier.
    generic = "This page describes administrative procedures and office hours."
    assert relevance(generic)["tier"] == "low"
    tagged = relevance(generic, signals=["debt_bondage"])
    assert tagged["tier"] == "low"                  # still gated out
    assert tagged["signal_tags"] == ["debt_bondage"] and tagged["score"] >= 1


def test_passes_threshold():
    assert passes(STRONG, min_tier="high") is True
    assert passes(MEDIUM, min_tier="high") is False
    assert passes(MEDIUM, min_tier="medium") is True
    assert passes(OFFTOPIC, min_tier="medium") is False
