"""Tests for scripts/agentic_browse.py -- the Gemma-4 function-calling browser agent.

Fully offline: the model and the executor are both injectable, so the planner
loop, tool dispatch, transcript, record aggregation, the tool-call parser, and
the endpoint-config resolution are tested with a scripted model + a fake
executor -- no browser, no GPU, no network. Record extraction runs through the
real browser_scrape parser on a synthetic DMW payload.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


ab = _load("agentic_browse", _ROOT / "scripts" / "agentic_browse.py")
bs = _load("browser_scrape_for_agentic_test", _ROOT / "scripts" / "browser_scrape.py")

_DMW_PAGE = json.dumps({"meta": {"total": 1, "lastPage": 1}, "data": [
    {"name": "Sunrise Overseas Manpower Inc.", "classification": "Private Employment Agency",
     "license_status": "Valid License", "is_valid": True, "address": "12 Mabini St",
     "municipality_province": "MALATE", "city_province": "MANILA", "contact_number": "(02) 5550-1"},
]})


class FakeExecutor:
    """A scripted browser: navigate seeds a captured DMW endpoint; extract runs
    the REAL browser_scrape parser over it."""

    def __init__(self):
        self.captured = []
        self.calls = []

    def navigate(self, url):
        self.calls.append(("navigate", url))
        self.captured = [{"url": url.rstrip("/") + "/api/v1/public/licensed-agencies?page=1",
                          "text": _DMW_PAGE}]
        return self.observe()

    def observe(self):
        return ab.Observation(title="Registry", url="https://reg.test",
                              elements=[{"tag": "input", "text": "Search"}],
                              data_endpoints=[c["url"] for c in self.captured])

    def click(self, target):
        self.calls.append(("click", target))
        return self.observe()

    def fill(self, target, text):
        self.calls.append(("fill", target, text))
        return self.observe()

    def extract(self, endpoint="", field_map=None):
        self.calls.append(("extract", endpoint))
        res = bs.CaptureResult(payloads=[c for c in self.captured if not endpoint or endpoint in c["url"]])
        profiles, _ = bs.captures_to_profiles(res, source="agentic-test")
        return profiles


def _scripted_model(actions):
    seq = list(actions)
    def model_fn(**_kw):
        return seq.pop(0) if seq else {"tool": "finish", "args": {"reason": "exhausted"}}
    return model_fn


def test_agent_navigates_then_extracts_then_finishes():
    ex = FakeExecutor()
    ex.navigate("https://reg.test")  # seed a page (as the CLI does before the loop)
    model = _scripted_model([
        {"tool": "observe", "args": {}},
        {"tool": "extract", "args": {"endpoint": "licensed-agencies"}},
        {"tool": "finish", "args": {"reason": "list extracted"}},
    ])
    result = ab.run_agent("extract all licensed agencies", ex, model)
    assert result["stop_reason"] == "finish"
    assert len(result["records"]) == 1
    assert result["records"][0]["name"] == "Sunrise Overseas Manpower Inc."
    assert result["records"][0]["status"] == "valid"  # DMW transform applied via browser_scrape
    assert [t["tool"] for t in result["transcript"]] == ["observe", "extract", "finish"]


def test_agent_dedups_repeated_extractions():
    ex = FakeExecutor(); ex.navigate("https://reg.test")
    model = _scripted_model([
        {"tool": "extract", "args": {"endpoint": "licensed-agencies"}},
        {"tool": "extract", "args": {"endpoint": "licensed-agencies"}},  # same data again
        {"tool": "finish", "args": {"reason": "done"}},
    ])
    result = ab.run_agent("extract", ex, model)
    assert len(result["records"]) == 1  # identical records deduped


def test_agent_stops_on_invalid_tool():
    ex = FakeExecutor()
    model = _scripted_model([{"tool": "frobnicate", "args": {}}])
    result = ab.run_agent("x", ex, model)
    assert result["stop_reason"].startswith("invalid_tool")


def test_agent_handles_model_exception():
    ex = FakeExecutor()
    def boom(**_kw):
        raise ValueError("model down")
    result = ab.run_agent("x", ex, boom)
    assert result["stop_reason"].startswith("model_error")


def test_agent_is_bounded_by_max_steps():
    ex = FakeExecutor()
    model = _scripted_model([{"tool": "observe", "args": {}}] * 100)
    result = ab.run_agent("x", ex, model, max_steps=5)
    assert result["steps"] == 5 and result["stop_reason"] == "max_steps"


def test_extract_tool_error_is_caught_not_fatal():
    class Boom(FakeExecutor):
        def extract(self, endpoint="", field_map=None):
            raise RuntimeError("parse failed")
    ex = Boom()
    model = _scripted_model([{"tool": "extract", "args": {}}, {"tool": "finish", "args": {}}])
    result = ab.run_agent("x", ex, model)
    assert result["stop_reason"] == "finish"
    assert "error" in result["transcript"][0]["result"]


# ---- tool-call parsing ----------------------------------------------------

def test_parse_tool_call_extracts_json_from_prose():
    assert ab._parse_tool_call('Sure: {"tool":"navigate","args":{"url":"https://x"}} done')["tool"] == "navigate"
    fenced = '```json\n{"tool":"extract","args":{"endpoint":"e"}}\n```'
    assert ab._parse_tool_call(fenced)["args"]["endpoint"] == "e"


def test_parse_tool_call_defaults_args_and_handles_garbage():
    assert ab._parse_tool_call('{"tool":"finish"}')["args"] == {}
    assert ab._parse_tool_call("no json here")["tool"] == "finish"
    assert ab._parse_tool_call("")["tool"] == "finish"


# ---- live-model plumbing (with an injected caller, still offline) ----------

def test_gemma_model_fn_uses_injected_caller():
    captured = {}
    def fake_caller(*, system, user, cfg):
        captured["user"] = user
        return 'I will look at the data. {"tool":"extract","args":{"endpoint":"licensed-agencies"}}'
    action = ab.gemma_model_fn(goal="g", observation=ab.Observation(title="t"),
                               tools=ab.TOOLS, transcript=[], cfg={"base_url": "x"}, caller=fake_caller)
    assert action == {"tool": "extract", "args": {"endpoint": "licensed-agencies"}}
    assert "data_endpoints" in captured["user"] or "observation" in captured["user"]


def test_model_config_resolves_ollama_env(monkeypatch):
    monkeypatch.delenv("DUECARE_MODEL_BASE_URL", raising=False)
    monkeypatch.setenv("OLLAMA_HOST", "https://ollama.example.com")
    monkeypatch.setenv("OLLAMA_API_KEY", "k")
    cfg = ab._model_config("gemma4:31b")
    assert cfg["base_url"].endswith("/v1") and cfg["api_key"] == "k" and cfg["model"] == "gemma4:31b"


def test_model_config_prefers_explicit_duecare_vars(monkeypatch):
    monkeypatch.setenv("DUECARE_MODEL_BASE_URL", "https://api.example.com/v1")
    monkeypatch.setenv("DUECARE_MODEL_API_KEY", "kk")
    monkeypatch.setenv("DUECARE_MODEL_NAME", "gemma4:custom")
    cfg = ab._model_config()
    assert cfg == {"base_url": "https://api.example.com/v1", "api_key": "kk", "model": "gemma4:custom"}
