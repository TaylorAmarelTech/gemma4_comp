"""Deterministic checks for the free/freemium LLM provider registry."""
from __future__ import annotations

import sys
from pathlib import Path

_SCRIPTS = str(Path(__file__).resolve().parents[1] / "scripts")
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

import llm_providers as lp  # noqa: E402


def test_registry_includes_smoked_provider_ids() -> None:
    keys = {provider.key for provider in lp.REGISTRY}
    assert {
        "github",
        "groq",
        "huggingface",
        "upstage",
        "sambanova",
        "nvidia",
        "llm7",
        "rapidapi_gemma4_26b",
        "rapidapi_cheap_claude_opus45",
        "rapidapi_claude_opus47",
        "rapidapi_claude_opus47_coding",
        "rapidapi_claude_opus46",
        "rapidapi_claude_sonnet46",
        "rapidapi_claude_opus46_agents",
        "openrouter_claude_opus48",
        "openrouter_gemini35_flash",
        "openrouter_grok43",
        "openrouter_nemotron_ultra",
        "openrouter_qwen37max",
        "openrouter_qwen37plus",
    } <= keys


def test_loop_configs_excludes_non_openai_compatible_rapidapi_shapes() -> None:
    configs = lp.loop_configs()
    assert "groq" in configs
    assert "nvidia" in configs
    assert configs["groq"]["health"] == "proven"
    assert "rapidapi_gemma4_26b" not in configs
    assert "rapidapi_claude_opus47" not in configs


def test_provider_health_labels_capture_flaky_and_quota_sensitive_endpoints() -> None:
    assert lp.provider_health(lp.BY_KEY["groq"]) == "proven"
    assert lp.provider_health(lp.BY_KEY["cerebras"]) == "quota_limited"
    assert lp.provider_health(lp.BY_KEY["opencode_zen"]) == "unreliable"
    assert lp.provider_health(lp.BY_KEY["rapidapi_gemma4_26b"]) == "transport_flaky"
    assert lp.provider_health(lp.BY_KEY["rapidapi_cheap_claude_opus45"]) == "auth_or_quota_blocked"
    assert lp.provider_health(lp.BY_KEY["rapidapi_claude_opus47"]) == "quota_sensitive"
    assert lp.provider_health(lp.BY_KEY["openrouter_claude_opus48"]) == "paid_planned"
    assert lp.provider_health(lp.BY_KEY["openrouter_qwen37plus"]) == "paid_planned"


def test_probe_headers_support_rapidapi_and_github() -> None:
    rapidapi = lp.BY_KEY["rapidapi_gemma4_26b"]
    headers = lp._probe_headers(rapidapi, "secret")
    assert headers["x-rapidapi-host"] == "gemma-4-26b-by-google.p.rapidapi.com"
    assert headers["x-rapidapi-key"] == "secret"
    assert headers["User-Agent"].startswith("Mozilla/5.0")
    assert "Authorization" not in headers

    github = lp.BY_KEY["github"]
    headers = lp._probe_headers(github, "secret")
    assert headers["Authorization"] == "Bearer secret"
    assert headers["Accept"] == "application/vnd.github+json"
    assert headers["X-GitHub-Api-Version"] == "2022-11-28"

    openrouter = lp.BY_KEY["openrouter_grok43"]
    headers = lp._probe_headers(openrouter, "secret")
    assert headers["Authorization"] == "Bearer secret"
    assert headers["X-OpenRouter-Title"] == "DueCare Evaluation"


def test_probe_body_supports_rapidapi_chat_and_text_shapes() -> None:
    chat = lp._probe_body(lp.BY_KEY["rapidapi_gemma4_26b"], "rapidapi/gemma-4-26b").decode("utf-8")
    assert '"messages"' in chat
    assert '"reasoning_effort": "low"' in chat
    assert '"max_tokens": 64' in chat
    assert '"temperature": 0.1' in chat
    assert "Reply with exactly: ok" in chat
    assert '"model"' not in chat

    text = lp._probe_body(lp.BY_KEY["rapidapi_claude_opus47"], "ignored").decode("utf-8")
    assert '"prompt"' in text
    assert '"system"' in text
    assert '"outputType": "text"' in text
    assert '"messages"' not in text


def test_probe_text_extractor_accepts_reasoning_content_fallback() -> None:
    data = {"choices": [{"message": {"content": "", "reasoning_content": "OK"}}]}
    assert lp._extract_probe_text(data) == "OK"
