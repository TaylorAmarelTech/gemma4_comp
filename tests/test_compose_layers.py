"""Unit tests for harnesses._layers.compose_layers."""
from __future__ import annotations

from types import SimpleNamespace

from duecare.chat.harnesses._layers import compose_layers


def _app_with(**callables):
    return SimpleNamespace(state=SimpleNamespace(**callables))


def test_no_layers_wired_returns_empty_trace_and_grounding():
    app = _app_with()
    out = compose_layers(app, "any text")
    assert out["trace"]["grep"]["fired"] is False
    assert out["trace"]["rag"]["fired"] is False
    assert out["trace"]["tools"]["fired"] is False
    assert out["trace"]["online"]["fired"] is False
    assert out["grounding"] == ""


def test_grep_fires_with_hits_and_appears_in_grounding():
    def fake_grep(text):
        return {"hits": [
            {"rule_id": "rule_a", "severity": "high", "match_text": "fee 30k"},
            {"rule_id": "rule_b", "severity": "low", "match_text": "passport"},
        ]}
    app = _app_with(grep_call=fake_grep)
    out = compose_layers(app, "recruiter wants fee", layers=("grep",))
    assert out["trace"]["grep"]["fired"] is True
    assert out["trace"]["grep"]["n_hits"] == 2
    assert "rule_a" in out["grounding"]
    assert "rule_b" in out["grounding"]


def test_rag_fires_with_docs():
    def fake_rag(text, top_k=5):
        return {"docs": [{"id": "doc_x", "title": "ILO C181", "snippet": "fee prohibition"}]}
    app = _app_with(rag_call=fake_rag)
    out = compose_layers(app, "fee question", layers=("rag",))
    assert out["trace"]["rag"]["fired"] is True
    assert out["trace"]["rag"]["doc_ids"] == ["doc_x"]
    assert "ILO C181" in out["grounding"]


def test_tools_fires_with_calls():
    def fake_tools(messages):
        return {"tool_calls": [{"name": "lookup", "args": {"q": "PH-HK"}, "result": "0 PHP"}]}
    app = _app_with(tools_call=fake_tools)
    out = compose_layers(app, "any", layers=("tools",))
    assert out["trace"]["tools"]["fired"] is True
    assert out["trace"]["tools"]["tool_names"] == ["lookup"]
    assert "lookup" in out["grounding"]


def test_online_fires_with_results():
    def fake_online(text, top_n=5):
        return {"results": [{"title": "art", "url": "http://x", "snippet": "..."}],
                "source": "ddg"}
    app = _app_with(online_search_call=fake_online)
    out = compose_layers(app, "any", layers=("online",))
    assert out["trace"]["online"]["fired"] is True
    assert out["trace"]["online"]["source"] == "ddg"


def test_failing_layer_captured_in_trace_does_not_raise():
    def boom(text):
        raise RuntimeError("layer kaboom")
    app = _app_with(grep_call=boom)
    out = compose_layers(app, "any", layers=("grep",))
    assert out["trace"]["grep"]["fired"] is False
    assert "kaboom" in out["trace"]["grep"]["error"]


def test_only_requested_layers_fan_out():
    calls = {"grep": 0, "rag": 0, "tools": 0}
    def fake_grep(text):
        calls["grep"] += 1
        return {"hits": []}
    def fake_rag(text):
        calls["rag"] += 1
        return {"docs": []}
    def fake_tools(msgs):
        calls["tools"] += 1
        return {"tool_calls": []}
    app = _app_with(grep_call=fake_grep, rag_call=fake_rag, tools_call=fake_tools)
    compose_layers(app, "any", layers=("grep",))
    assert calls == {"grep": 1, "rag": 0, "tools": 0}
