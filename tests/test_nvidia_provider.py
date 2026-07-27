"""NVIDIA build provider routing (a second OpenAI-compatible inference provider).

provider_chat routes a model string by prefix: `nvidia:<id>` -> nvidia_chat (integrate.api.nvidia.com),
everything else -> ollama_chat (unchanged). This lets the benchmark grade via NVIDIA when Ollama is
rate-limited, or mix providers in one judge panel, with no other code change. No live HTTP here -- the
callers are monkeypatched and the key comes from the environment.
"""
from __future__ import annotations

import importlib.util
import sys
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


@pytest.fixture(autouse=True)
def _force_urlopen_transport(monkeypatch):
    # The urlopen-mocking test drives nvidia_chat's retry path; force the legacy transport (the
    # ``DUECARE_HTTP_POOL=0`` fallback) so the mock is hit. Pooled transport: test_http_pool.py.
    monkeypatch.setattr(lg, "_HTTP_POOL_ENABLED", False)
    monkeypatch.setattr(
        lg.provider_budget,
        "environment_ledger",
        lambda: lg.provider_budget.DisabledProviderBudget(),
    )


def test_provider_chat_routes_by_prefix(monkeypatch):
    seen = {}

    def _nv(p, *, model, **kw):
        seen["nvidia"] = model
        return "N"

    def _ol(p, *, model, **kw):
        seen["ollama"] = model
        return "O"

    monkeypatch.setattr(lg, "nvidia_chat", _nv)
    monkeypatch.setattr(lg, "ollama_chat", _ol)

    assert lg.provider_chat("hi", model="nvidia:openai/gpt-oss-120b") == "N"
    assert seen["nvidia"] == "nvidia:openai/gpt-oss-120b"     # nvidia_chat strips the prefix itself
    assert lg.provider_chat("hi", model="gemma4:31b") == "O"
    assert seen["ollama"] == "gemma4:31b"


def test_provider_chat_drops_num_ctx_for_nvidia(monkeypatch):
    captured = {}
    monkeypatch.setattr(lg, "nvidia_chat", lambda p, *, model, **kw: captured.update(kw) or "ok")
    lg.provider_chat("hi", model="nvidia:qwen/qwen3.5-397b-a17b", num_ctx=32768, max_tokens=16)
    assert "num_ctx" not in captured                          # strict-OpenAI NVIDIA path drops the Ollama option
    assert captured.get("max_tokens") == 16


def test_nvidia_chat_strips_prefix_and_reads_env_key(monkeypatch):
    monkeypatch.setenv("NVIDIA_API_KEY", "nvapi-TESTONLY")
    # point the .env scan at a nonexistent path so it falls through to the env var
    monkeypatch.setattr(lg, "_ROOT", _ROOT / "does_not_exist_dir")
    captured = {}

    class _Resp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return b'{"choices":[{"message":{"content":"OK"}}]}'

    def _fake_urlopen(req, timeout=0):
        captured["url"] = req.full_url
        captured["auth"] = req.headers.get("Authorization")
        import json as _j
        captured["model"] = _j.loads(req.data)["model"]
        return _Resp()

    monkeypatch.setattr(lg.urllib.request, "urlopen", _fake_urlopen)
    out = lg.nvidia_chat("hi", model="nvidia:meta/llama-3.1-8b-instruct", max_tokens=8)
    assert out == "OK"
    assert captured["url"].startswith("https://integrate.api.nvidia.com/v1")
    assert captured["auth"] == "Bearer nvapi-TESTONLY"
    assert captured["model"] == "meta/llama-3.1-8b-instruct"  # prefix stripped before the API sees it


def test_nvidia_key_missing_raises(monkeypatch):
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    monkeypatch.setattr(lg, "_ROOT", _ROOT / "does_not_exist_dir")
    with pytest.raises(RuntimeError, match="NVIDIA_API_KEY"):
        lg._load_nvidia_key()
