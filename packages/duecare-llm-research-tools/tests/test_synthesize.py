"""Tests for the knowledge synthesizer + trend miner."""
from __future__ import annotations

from duecare.research_tools.synthesize import (
    mine_fee_euphemisms, synthesize, trend_signals,
)


def test_trend_signals_detects_categories():
    assert "scam_compound" in trend_signals("victims forced to scam inside a compound in Myawaddy")
    assert "digital_coercion" in trend_signals(
        "her wages held in the app and a biometric scan required to withdraw pay")
    assert "enforcement" in trend_signals("the recruitment agency licence was revoked last month")
    assert trend_signals("a plain sentence about the weather and the harvest season") == {}


def test_mine_fee_euphemisms():
    found = mine_fee_euphemisms("They charged a training bond and a documentation fee on arrival.")
    assert "training bond" in found and "documentation fee" in found
    # already-known euphemism is excluded
    assert "training bond" not in mine_fee_euphemisms("training bond", known={"training bond"})
    # generic stopword modifiers (annual/late) are not flagged as camouflage
    assert mine_fee_euphemisms("an annual fee and a late charge applied") == set()


def test_synthesize_emits_multiple_envelope_types_and_report():
    chunks = [
        {"text": "Workers were forced to scam inside a KK Park compound; wages locked in the app.",
         "url": "u1"},
        {"text": "The recruiter charged a loyalty deduction and a mobilization fee before deployment.",
         "url": "u2"},
    ]
    out = synthesize(chunks, created_at="2026-06-07T00:00:00Z")
    types = {e["knowledge_object_type"] for e in out["envelopes"]}
    assert "grep_rule" in types and "context_snippet" in types        # MORE than rag_doc
    assert "scam_compound" in out["report"]["trend_categories"]
    novel = {lab for lab, _ in out["report"]["novel_fee_euphemisms"]}
    assert "loyalty deduction" in novel and "mobilization fee" in novel
    assert out["report"]["envelopes_generated"] == len(out["envelopes"])
