"""Multi-provider fan-out: many OpenAI-compatible endpoints + per-provider KEY POOLS with rotation.

provider_chat routes ``<provider>:<id>`` (openrouter/groq/cerebras/together/sambanova/featherless/
mistral) to a pooled, key-rotating caller; ``nvidia:`` keeps its own path; no prefix stays Ollama
(unchanged, so the live engine is untouched). The point is resilience: when one account's credits reset,
the sweep keeps running on the others instead of stalling. No live HTTP -- urlopen is monkeypatched.
"""
from __future__ import annotations

import importlib.util
import io
import sys
import urllib.error
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


sys.path.insert(0, str(_ROOT / "scripts"))
lg = _load("llm_generate", _ROOT / "scripts" / "llm_generate.py")


def _http_error(code: int) -> urllib.error.HTTPError:
    return urllib.error.HTTPError("https://x/v1/chat/completions", code, f"HTTP {code}",
                                  {}, io.BytesIO(b"{}"))


class _Resp:
    def __init__(self, content: str):
        self._c = content

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def read(self):
        import json as _j
        return _j.dumps({"choices": [{"message": {"content": self._c}}]}).encode()


def test_provider_chat_routes_registry_prefix_to_pool(monkeypatch):
    seen = {}

    def _oc(p, *, model, base_url, keys, provider, **kw):
        seen.update(model=model, base_url=base_url, provider=provider, keys=keys)
        return "R"

    monkeypatch.setattr(lg, "openai_compatible_chat", _oc)
    monkeypatch.setattr(lg, "_load_key_pool", lambda env: ["k1", "k2"])
    out = lg.provider_chat("hi", model="openrouter:z-ai/glm-5.2", num_ctx=32768, max_tokens=16)
    assert out == "R"
    assert seen["model"] == "z-ai/glm-5.2"                       # prefix stripped for the API
    assert seen["base_url"] == "https://openrouter.ai/api/v1"
    assert seen["provider"] == "openrouter"
    assert seen["keys"] == ["k1", "k2"]


def test_provider_chat_no_prefix_still_ollama(monkeypatch):
    seen = {}
    monkeypatch.setattr(lg, "ollama_chat", lambda p, *, model, **kw: seen.update(model=model) or "O")
    assert lg.provider_chat("hi", model="gemma4:31b") == "O"     # default path unchanged (engine safe)
    assert seen["model"] == "gemma4:31b"


def test_load_key_pool_gathers_and_dedups(monkeypatch, tmp_path):
    monkeypatch.setattr(lg, "_ROOT", tmp_path)                   # no .env / .agent in tmp
    monkeypatch.setattr(lg, "_AGENT_KEYS_JSON", tmp_path / ".agent" / "provider_keys.json")
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-A")
    monkeypatch.setenv("OPENROUTER_API_KEY_2", "sk-or-B")
    monkeypatch.setenv("OPENROUTER_API_KEY_3", "sk-or-A")        # duplicate -> dropped
    pool = lg._load_key_pool("OPENROUTER")
    assert pool == ["sk-or-A", "sk-or-B"]


def test_load_key_pool_reads_agent_json_first(monkeypatch, tmp_path):
    agent = tmp_path / ".agent"
    agent.mkdir()
    (agent / "provider_keys.json").write_text('{"groq": ["gsk_pool1", "gsk_pool2"]}', encoding="utf-8")
    monkeypatch.setattr(lg, "_ROOT", tmp_path)
    monkeypatch.setattr(lg, "_AGENT_KEYS_JSON", agent / "provider_keys.json")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    assert lg._load_key_pool("GROQ") == ["gsk_pool1", "gsk_pool2"]


def test_openai_compatible_rotates_off_spent_key(monkeypatch):
    """First key returns 429 (spent) -> caller drops it and the second key succeeds."""
    calls = []

    def _fake_urlopen(req, timeout=0):
        auth = req.headers.get("Authorization")
        calls.append(auth)
        if auth == "Bearer good":
            return _Resp("ANSWER")
        raise _http_error(429)

    monkeypatch.setattr(lg.urllib.request, "urlopen", _fake_urlopen)
    out = lg.openai_compatible_chat("hi", model="m", base_url="https://x/v1",
                                    keys=["spent", "good"], provider="groq", max_retries=0)
    assert out == "ANSWER"
    assert "Bearer spent" in calls and "Bearer good" in calls    # tried spent, rotated to good


def test_openai_compatible_all_keys_spent_raises(monkeypatch):
    def _boom(req, timeout=0):
        raise _http_error(402)

    monkeypatch.setattr(lg.urllib.request, "urlopen", _boom)
    with pytest.raises(lg.AllKeysExhausted):
        lg.openai_compatible_chat("hi", model="m", base_url="https://x/v1",
                                  keys=["a", "b", "c"], provider="together", max_retries=0)


def test_openai_compatible_empty_pool_raises():
    with pytest.raises(lg.AllKeysExhausted, match="no keys"):
        lg.openai_compatible_chat("hi", model="m", base_url="https://x/v1", keys=[], provider="cerebras")


def test_complete_defaults_to_provider_router(monkeypatch):
    """complete()'s default backend is provider_chat, so generation tooling can offload to a prefixed
    provider (off the engine's Ollama quota) while a bare model still routes to Ollama."""
    seen = {}
    monkeypatch.setattr(lg, "provider_chat",
                        lambda p, *, model, **kw: seen.update(model=model, system=kw.get("system")) or "X")
    out = lg.complete("hi", model="sambanova:DeepSeek-V3.1", system="S")
    assert out == "X"
    assert seen["model"] == "sambanova:DeepSeek-V3.1"    # prefixed model reaches the multi-provider router
    assert seen["system"] == "S"                          # system prompt threaded through
    lg.complete("hi", model="glm-5.2")
    assert seen["model"] == "glm-5.2"                     # bare model also goes through the router (-> Ollama)


def test_next_key_offset_round_robins():
    lg._key_cursors.pop("unittest_prov", None)
    offs = [lg._next_key_offset("unittest_prov", 3) for _ in range(4)]
    assert offs == [0, 1, 2, 0]                                  # cycles across the pool
    assert lg._next_key_offset("solo", 1) == 0                   # single key -> always 0


# --- resilient_chat: iterative re-questioning on a refusal, recover + flag ---------------------------
def _useful(text):
    """test stand-in for refusal_detector.classify: 'REFUSE' -> refusal, else useful."""
    return (False, "refusal") if text == "REFUSE" else (True, "useful")


def test_resilient_chat_recovers_from_refusal(monkeypatch):
    replies = iter(["REFUSE", "here is the grounded answer"])   # refuse first, answer on retry

    def _pc(prompt, *, model, **kw):
        return next(replies)

    monkeypatch.setattr(lg, "provider_chat", _pc)
    text, meta = lg.resilient_chat("q", model="gemma4:31b", is_useful=_useful)
    assert text == "here is the grounded answer"
    assert meta["refused_initially"] is True and meta["recovered"] is True
    assert meta["attempts"] == 2 and meta["final_useful"] is True


def test_resilient_chat_no_retry_when_useful(monkeypatch):
    monkeypatch.setattr(lg, "provider_chat", lambda p, *, model, **kw: "a full grounded answer")
    text, meta = lg.resilient_chat("q", model="m", is_useful=_useful)
    assert meta["attempts"] == 1 and meta["refused_initially"] is False and meta["recovered"] is False


def test_resilient_chat_flags_persistent_refusal(monkeypatch):
    monkeypatch.setattr(lg, "provider_chat", lambda p, *, model, **kw: "REFUSE")  # never recovers
    text, meta = lg.resilient_chat("q", model="m", max_attempts=3, is_useful=_useful)
    assert meta["attempts"] == 3 and meta["final_useful"] is False and meta["recovered"] is False
    assert meta["refused_initially"] is True                     # the collapse is FLAGGED, not hidden


def test_resilient_chat_retry_pushes_but_keeps_prompt(monkeypatch):
    seen = []

    def _pc(prompt, *, model, **kw):
        seen.append(prompt)
        return "REFUSE" if len(seen) == 1 else "answer"

    monkeypatch.setattr(lg, "provider_chat", _pc)
    lg.resilient_chat("ORIGINAL QUESTION", model="m", is_useful=_useful)
    assert seen[0] == "ORIGINAL QUESTION"                        # first attempt is the raw prompt
    assert seen[1].startswith("ORIGINAL QUESTION")              # retry KEEPS the question (comparable)
    assert "[RETRY" in seen[1]                                   # ...plus the push past the refusal
