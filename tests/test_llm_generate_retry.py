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
        raise urllib.error.HTTPError("http://x", 429, "rate", {}, None)   # 429 -> retried, then raises

    _patch(monkeypatch, urlopen)
    with pytest.raises(urllib.error.HTTPError):
        lg.ollama_chat("q", model="m", max_retries=2)
    assert calls["n"] == 3                                     # initial attempt + 2 retries
