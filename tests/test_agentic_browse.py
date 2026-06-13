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

    def paginate(self, count=1):
        self.calls.append(("paginate", count))
        return {"fetched_now": 0, "pages_fetched": 1, "last_page": 1}

    def extract(self, endpoint="", field_map=None):
        self.calls.append(("extract", endpoint))
        base = endpoint.split("?")[0] if endpoint else ""
        payloads = [c for c in self.captured if not base or base in c["url"].split("?")[0]]
        res = bs.CaptureResult(payloads=payloads)
        profiles, _ = bs.captures_to_profiles(res, source="agentic-test")
        return profiles


class PagedFakeExecutor(FakeExecutor):
    """A multi-page registry: navigate seeds page 1; paginate fetches the rest;
    extract aggregates every page. Mirrors the live DMW pagination contract."""

    def __init__(self, pages=3):
        super().__init__()
        self.total_pages = pages
        self.base = ""

    def _page(self, n):
        return json.dumps({"meta": {"lastPage": self.total_pages, "currentPage": n}, "data": [
            {"name": f"Agency {n:03d}", "classification": "Private Employment Agency",
             "license_status": "Valid License", "is_valid": True, "address": f"{n} Main St"},
        ]})

    def _fetched(self):
        import re
        return {int(re.search(r"page=(\d+)", c["url"]).group(1)) for c in self.captured}

    def navigate(self, url):
        self.base = url.rstrip("/") + "/api/v1/public/licensed-agencies"
        self.captured = [{"url": self.base + "?page=1", "text": self._page(1)}]
        return self.observe()

    def observe(self):
        obs = super().observe()
        obs["pagination"] = {"last_page": self.total_pages, "pages_fetched": len(self._fetched())}
        obs["data_endpoints"] = [c["url"] for c in self.captured]
        return obs

    def paginate(self, count=1):
        done = self._fetched()
        fetched = 0
        for n in range(2, self.total_pages + 1):
            if fetched >= count:
                break
            if n in done:
                continue
            self.captured.append({"url": self.base + f"?page={n}", "text": self._page(n)})
            fetched += 1
        return {"fetched_now": fetched, "pages_fetched": len(self._fetched()), "last_page": self.total_pages}


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


def test_agent_paginates_all_pages_then_extracts():
    """Gemma drives next_page until pages_fetched == last_page, then extract
    aggregates every page -- the full-dataset path."""
    ex = PagedFakeExecutor(pages=4)
    ex.navigate("https://reg.test")
    model = _scripted_model([
        {"tool": "next_page", "args": {"count": 1}},   # -> page 2
        {"tool": "next_page", "args": {"count": 5}},   # -> remaining pages (3,4)
        {"tool": "extract", "args": {}},
        {"tool": "finish", "args": {"reason": "all pages fetched"}},
    ])
    result = ab.run_agent("get every agency", ex, model, max_steps=10)
    assert result["stop_reason"] == "finish"
    assert len(result["records"]) == 4  # one per page, all aggregated
    assert {r["name"] for r in result["records"]} == {f"Agency {n:03d}" for n in range(1, 5)}
    # the pagination tool reported full coverage before extract
    pag_results = [t["result"] for t in result["transcript"] if t["tool"] == "next_page"]
    assert pag_results[-1]["pages_fetched"] == pag_results[-1]["last_page"] == 4


def test_paginate_count_fetches_multiple_pages_in_one_call():
    ex = PagedFakeExecutor(pages=76)
    ex.navigate("https://reg.test")
    res = ex.paginate(75)  # fetch all remaining in one call (the efficient path)
    assert res == {"fetched_now": 75, "pages_fetched": 76, "last_page": 76}


def test_extract_with_page_param_endpoint_aggregates_all_pages():
    """Regression for the live 550-vs-3790 bug: when the model passes an endpoint
    that still carries ?page=1, extract must match by BASE path and aggregate
    EVERY captured page -- not the substring-colliding subset (page 1, 10, 11, 12)."""
    ex = PagedFakeExecutor(pages=12)
    ex.navigate("https://reg.test")
    ex.paginate(11)  # fetch pages 2..12
    recs = ex.extract(endpoint=ex.base + "?page=1")  # the exact form Gemma emitted
    assert len(recs) == 12  # all pages, not 4


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
