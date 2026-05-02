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
