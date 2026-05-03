"""Behavioral tests for the duecare.chat.harness module.

Tests the public callable contracts: GREP layer fires on known patterns,
RAG layer returns ranked docs, tool dispatch invokes the right tools,
and the layer outputs are composable into a single pre-context string.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


def _load_harness():
    p = (Path(__file__).parent.parent / "src" / "duecare" / "chat"
         / "harness" / "__init__.py")
    spec = importlib.util.spec_from_file_location("h", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_grep_fires_on_predatory_lending() -> None:
    """The GREP layer should detect 68% APR as a usury pattern."""
    h = _load_harness()
    grep = h.default_harness()["grep_call"]
    res = grep("Recruitment loan at 68% APR for placement to Hong Kong")
    assert isinstance(res, dict)
    assert "hits" in res
    # At least one hit should fire on a 68% APR scenario
    assert len(res["hits"]) >= 1, f"no hits on usury pattern; got {res}"


def test_grep_fires_on_passport_retention() -> None:
    h = _load_harness()
    grep = h.default_harness()["grep_call"]
    res = grep("Employer holds passport during 2-year contract for safekeeping")
    assert len(res["hits"]) >= 1


def test_grep_returns_no_hits_on_benign_text() -> None:
    h = _load_harness()
    grep = h.default_harness()["grep_call"]
    res = grep("I'm baking sourdough this weekend.")
    assert res["hits"] == []


def test_grep_hits_carry_required_fields() -> None:
    h = _load_harness()
    grep = h.default_harness()["grep_call"]
    res = grep("Recruitment loan at 68% APR for placement to Hong Kong")
    for hit in res["hits"]:
        assert "rule" in hit
        assert "severity" in hit
        # citation + indicator are documented but optional in some rules
        for key in ("rule", "severity"):
            assert hit[key] is not None


def test_rag_returns_top_k_docs() -> None:
    h = _load_harness()
    rag = h.default_harness()["rag_call"]
    res = rag("trafficking debt bondage", top_k=3)
    assert isinstance(res, dict)
    assert "docs" in res
    assert len(res["docs"]) <= 3


def test_rag_top_doc_relevant() -> None:
    """Querying for ILO C029 should retrieve the C029 doc as one of top-3."""
    h = _load_harness()
    rag = h.default_harness()["rag_call"]
    res = rag("ILO C029 forced labour convention", top_k=5)
    titles = " ".join((d.get("title", "") + " " + d.get("id", ""))
                      for d in res["docs"]).upper()
    assert "C029" in titles or "FORCED" in titles, \
        f"C029 not in top-5: {[d.get('id') for d in res['docs']]}"


def test_rag_doc_fields() -> None:
    h = _load_harness()
    rag = h.default_harness()["rag_call"]
    res = rag("trafficking", top_k=2)
    for doc in res["docs"]:
        assert "id" in doc
        assert "title" in doc
        assert "snippet" in doc or "source" in doc


def test_tools_call_returns_tool_calls_list() -> None:
    h = _load_harness()
    tools = h.default_harness()["tools_call"]
    msgs = [{"role": "user",
             "content": [{"type": "text",
                          "text": "Philippines to Hong Kong domestic worker"}]}]
    res = tools(msgs)
    assert isinstance(res, dict)
    assert "tool_calls" in res
    assert isinstance(res["tool_calls"], list)


def test_extra_grep_rules_merge() -> None:
    """A custom rule passed via extra_rules should fire alongside built-ins."""
    h = _load_harness()
    grep = h.default_harness()["grep_call"]
    custom = [{
        "rule": "test_custom_marker",
        "patterns": [r"\bSPECIAL_TEST_TOKEN_XYZ\b"],
        "all_required": True,
        "severity": "high",
        "citation": "Test §1",
        "indicator": "Custom test marker fired",
    }]
    res = grep("This text contains SPECIAL_TEST_TOKEN_XYZ as a marker.",
               extra_rules=custom)
    rule_names = {h_.get("rule") for h_ in res["hits"]}
    assert "test_custom_marker" in rule_names, \
        f"custom rule did not fire; rules that fired: {rule_names}"


def test_layer_docs_present() -> None:
    h = _load_harness()
    docs = h.default_harness()["layer_docs"]
    for layer in ("persona", "grep", "rag", "tools"):
        assert layer in docs
        assert len(docs[layer]) > 50, f"layer {layer} doc too short"


# =============================================================================
# CATEGORY F: 5 sector-specific GREP rules backported from Android v0.9
# (kafala-huroob, H-2A/H-2B, fishing-vessel, smuggler-fee, domestic-locked-in)
# =============================================================================


def _grep_rule_ids(text: str):
    h = _load_harness()
    grep = h.default_harness()["grep_call"]
    return {hit.get("rule") for hit in grep(text)["hits"]}


def test_grep_42_rules_total() -> None:
    """The Python harness should ship 42 GREP rules in lockstep with Android v0.9."""
    h = _load_harness()
    assert len(h.GREP_RULES) == 42, f"expected 42 GREP rules, got {len(h.GREP_RULES)}"


def test_kafala_huroob_fires_on_huroob_status() -> None:
    """A worker reporting 'huroob' status from a Saudi kafeel should match."""
    text = "My kafeel filed huroob status against me when I asked to leave."
    assert "kafala_huroob_absconder" in _grep_rule_ids(text)


def test_kafala_huroob_fires_on_absconder_label() -> None:
    """The Lebanese 'absconder' framing should also fire the rule."""
    text = "The agent threatened to file me as an absconder if I complain."
    assert "kafala_huroob_absconder" in _grep_rule_ids(text)


def test_h2a_h2b_fee_fires_on_h2a_with_deduction() -> None:
    """An H-2A worker charged for transportation should fire the rule."""
    text = ("I came on an H-2A petition and they charged me $850 in "
            "transportation deductions from my first paycheck.")
    assert "h2a_h2b_fee_violation" in _grep_rule_ids(text)


def test_h2a_h2b_fee_fires_on_h2b_with_housing() -> None:
    """An H-2B worker with housing deduction should fire the rule."""
    text = ("I work on an H-2B visa as a landscaper, they deduct housing "
            "and tool rental from my pay every week.")
    assert "h2a_h2b_fee_violation" in _grep_rule_ids(text)


def test_fishing_vessel_fires_on_at_sea_debt_pattern() -> None:
    """Fishing vessel + debt + at-sea confinement should fire the rule."""
    text = ("I work on a fishing trawler at sea for 6 months and they "
            "deduct my advance loan from each catch settlement.")
    assert "fishing_vessel_debt_confinement" in _grep_rule_ids(text)


def test_fishing_vessel_fires_on_transhipment_confinement() -> None:
    """Transhipment-at-sea + can't go ashore should fire the rule."""
    text = ("Workers on the long-liner cannot leave to go ashore and the "
            "captain transships the catch to a reefer to keep us at sea.")
    assert "fishing_vessel_debt_confinement" in _grep_rule_ids(text)


def test_smuggler_fee_fires_on_dollar_crossing_pattern() -> None:
    """A smuggler-fee + crossing-fee pattern should fire the rule."""
    text = "The coyote charged me USD 4500 to cross and another $1200 mid-journey."
    assert "smuggler_fee_and_coercion" in _grep_rule_ids(text)


def test_smuggler_fee_fires_on_passage_fee() -> None:
    """The 'passage fee' framing should also fire the rule."""
    text = "The smuggler asked for a passage fee of EUR 800 to take me across."
    assert "smuggler_fee_and_coercion" in _grep_rule_ids(text)


def test_domestic_locked_in_fires_on_live_in_employer() -> None:
    """Live-in domestic worker arrangement should fire the rule."""
    text = "I am a live-in maid and must sleep at the employer household every night."
    assert "domestic_work_locked_in_residence" in _grep_rule_ids(text)


def test_domestic_locked_in_fires_on_24_7_availability() -> None:
    """24/7 availability requirement should fire the rule."""
    text = ("They told me I must be on call 24/7 and cannot leave the "
            "house without permission.")
    assert "domestic_work_locked_in_residence" in _grep_rule_ids(text)


def test_new_rules_dont_fire_on_benign_text() -> None:
    """None of the 5 new rules should fire on unrelated text."""
    benign = "I'm planning a hiking trip with friends next weekend."
    new_rule_ids = {
        "kafala_huroob_absconder",
        "h2a_h2b_fee_violation",
        "fishing_vessel_debt_confinement",
        "smuggler_fee_and_coercion",
        "domestic_work_locked_in_residence",
    }
    fired = _grep_rule_ids(benign)
    assert fired & new_rule_ids == set(), \
        f"benign text triggered new rules: {fired & new_rule_ids}"


def test_new_rules_have_required_metadata() -> None:
    """All 5 new rules must have severity + citation + indicator."""
    h = _load_harness()
    new_rule_ids = {
        "kafala_huroob_absconder",
        "h2a_h2b_fee_violation",
        "fishing_vessel_debt_confinement",
        "smuggler_fee_and_coercion",
        "domestic_work_locked_in_residence",
    }
    matched = [r for r in h.GREP_RULES if r["rule"] in new_rule_ids]
    assert len(matched) == 5, f"expected 5 new rules, found {len(matched)}"
    for rule in matched:
        assert rule.get("severity") in ("critical", "high", "medium", "low")
        assert rule.get("citation"), f"{rule['rule']} missing citation"
        assert rule.get("indicator"), f"{rule['rule']} missing indicator"
        assert rule.get("citation").startswith(("Saudi", "US DOL", "ILO", "UN")), \
            f"{rule['rule']} citation should reference real statute: {rule.get('citation')[:80]}"
