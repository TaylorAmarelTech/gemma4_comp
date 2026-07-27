"""Tests for ollama_chat retry/backoff in scripts/llm_generate.py (offline; urlopen mocked)."""
from __future__ import annotations

import importlib.util
import json
import sys
import urllib.error
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "scripts"))


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


lg = _load("llm_generate", _ROOT / "scripts" / "llm_generate.py")


class _FakeResp:
    def __init__(self, payload):
        self._p = payload

    def __enter__(self):
        return self

    def __exit__(self, *_a):
        return False

    def read(self):
        return json.dumps(self._p).encode("utf-8")


def _patch(monkeypatch, urlopen):
    monkeypatch.setattr(lg, "_load_key", lambda: "k")
    # Exercise the legacy urlopen transport (the DUECARE_HTTP_POOL=0 fallback)
    # so these assertions keep hitting the mock. The pooled transport has its own tests.
    monkeypatch.setattr(lg, "_HTTP_POOL_ENABLED", False)
    monkeypatch.setattr(lg.urllib.request, "urlopen", urlopen)
    monkeypatch.setattr(lg.time, "sleep", lambda _s: None)   # no real backoff sleep in tests


def test_retries_transient_then_succeeds(monkeypatch):
    calls = {"n": 0}

    def urlopen(req, timeout=None):
        calls["n"] += 1
        if calls["n"] < 3:
            raise urllib.error.URLError("transient")          # OSError subclass -> retried
        return _FakeResp({"choices": [{"message": {"content": "hi"}}]})

    _patch(monkeypatch, urlopen)
    assert lg.ollama_chat("q", model="m", max_retries=4) == "hi"
    assert calls["n"] == 3                                     # 2 retries, then success


def test_raises_immediately_on_non_retryable(monkeypatch):
    calls = {"n": 0}

    def urlopen(req, timeout=None):
        calls["n"] += 1
        raise urllib.error.HTTPError("http://x", 401, "auth", {}, None)   # 401 -> not retryable

    _patch(monkeypatch, urlopen)
    with pytest.raises(urllib.error.HTTPError):
        lg.ollama_chat("q", model="m", max_retries=4)
    assert calls["n"] == 1                                     # no retry on auth failure


def test_retries_429_then_exhausts(monkeypatch):
    calls = {"n": 0}

    def urlopen(req, timeout=None):
        calls["n"] += 1
        # 429 is retryable and eventually propagates when the allowance is exhausted.
        raise urllib.error.HTTPError("http://x", 429, "rate", {}, None)

    _patch(monkeypatch, urlopen)
    with pytest.raises(urllib.error.HTTPError):
        lg.ollama_chat("q", model="m", max_retries=2)
    assert calls["n"] == 3                                     # initial attempt + 2 retries


def test_retry_after_header_is_honoured():
    class _Exc:
        def __init__(self, headers):
            self.headers = headers
    assert lg._retry_after(_Exc({"Retry-After": "3"})) == 3.0   # delta-seconds parsed
    assert lg._retry_after(_Exc({})) is None  # no header -> exponential backoff
    assert lg._retry_after(_Exc({"Retry-After": "not-a-date"})) is None  # unparseable -> None


def test_zero_call_budget_blocks_before_http_transport(monkeypatch, tmp_path):
    ledger = lg.provider_budget.ProviderBudgetLedger(
        tmp_path / "budget.sqlite3",
        run_id="zero-call-test",
        policy=lg.provider_budget.BudgetPolicy(0, 0, 0, 0, False),
        receipt_path=tmp_path / "receipt.json",
    )
    transport_calls = {"n": 0}

    def transport(*_args, **_kwargs):
        transport_calls["n"] += 1
        raise AssertionError("transport must not run")

    monkeypatch.setattr(lg.provider_budget, "environment_ledger", lambda: ledger)
    monkeypatch.setattr(lg, "_http_post_json", transport)
    with pytest.raises(lg.provider_budget.BudgetExceededError, match="attempts"):
        lg.ollama_chat("q", model="m", key="offline-key", max_tokens=16, max_retries=0)
    assert transport_calls["n"] == 0
    assert ledger.receipt()["totals"]["denied_attempts"] == 1


def test_retry_consumes_a_new_budget_reservation(monkeypatch, tmp_path):
    ledger = lg.provider_budget.ProviderBudgetLedger(
        tmp_path / "budget.sqlite3",
        run_id="retry-test",
        policy=lg.provider_budget.BudgetPolicy(3, 1_000, 1_000, 1_000, True),
        receipt_path=tmp_path / "receipt.json",
    )
    calls = {"n": 0}

    def transport(*_args, **_kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            raise urllib.error.HTTPError("https://example.invalid", 429, "rate", {}, None)
        return json.dumps(
            {
                "choices": [{"message": {"content": "ok"}}],
                "usage": {"prompt_tokens": 3, "completion_tokens": 2},
            }
        ).encode("utf-8")

    monkeypatch.setattr(lg.provider_budget, "environment_ledger", lambda: ledger)
    monkeypatch.setattr(lg, "_http_post_json", transport)
    monkeypatch.setattr(lg.time, "sleep", lambda _seconds: None)
    assert lg.ollama_chat(
        "q", model="m", key="offline-key", max_tokens=16, max_retries=1
    ) == "ok"
    totals = ledger.receipt()["totals"]
    assert calls["n"] == 2
    assert totals["reserved_attempts"] == 2
    assert totals["failed_attempts"] == 1
    assert totals["succeeded_attempts"] == 1
