"""llm_providers.py -- the free / freemium LLM API "plate": one registry of
OpenAI-compatible endpoints, a liveness probe, and an .env template generator.

Why: before spending on a paid roster (OpenRouter), run the model-failure study
across as many FREE providers as possible. Almost every provider below speaks the
OpenAI `/chat/completions` shape, so each drops straight into
`model_failure_study.py` / `model_failure_judge.py` (`--base-url <chat_url>
--key-env <KEY>`) and into `model_failure_loop.py` (`--provider <key>`).

Sources (lists change fast -- re-verify model ids against each provider's /models):
  - https://github.com/cheahjs/free-llm-api-resources
  - https://github.com/mnfst/awesome-free-llm-apis
  - https://www.analyticsvidhya.com/blog/2026/01/top-free-llm-apis/

CLI:
    python scripts/llm_providers.py list                 # the catalog
    python scripts/llm_providers.py list --tier free     # only permanent-free
    python scripts/llm_providers.py env-template          # .env keys + signup URLs
    python scripts/llm_providers.py probe                 # which are live RIGHT NOW
    python scripts/llm_providers.py probe --only groq,cerebras,gemini
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

# tier: "free"  = permanent free tier (no card)        "anon" = no key needed
#       "trial" = one-off free credits / time-limited   (still worth using once)


@dataclass(frozen=True)
class Provider:
    key: str                      # short id used as --provider <key>
    name: str
    chat_url: str                 # FULL OpenAI-compatible chat/completions URL
    key_env: str                  # env var holding the bearer key ("" = anonymous)
    tier: str                     # free | anon | trial
    region: str                   # flag emoji or country
    models: tuple[str, ...]       # example usable model ids (verify against /models)
    judge_model: str              # a content-emitting model good for judging ("" = none)
    signup: str                   # where to get the key
    notes: str = ""
    openai_compatible: bool = True
    extra: dict = field(default_factory=dict)


# --- THE REGISTRY -----------------------------------------------------------
REGISTRY: tuple[Provider, ...] = (
    # ---------------- permanent free, OpenAI-compatible ----------------
    Provider("groq", "Groq", "https://api.groq.com/openai/v1/chat/completions",
             "GROQ_API_KEY", "free", "US",
             ("llama-3.1-8b-instant", "llama-3.3-70b-versatile",
              "deepseek-r1-distill-llama-70b", "openai/gpt-oss-120b"),
             "llama-3.1-8b-instant", "https://console.groq.com/keys",
             "Very fast; generous free RPM/RPD, no card.",
             extra={"health": "proven", "probe_note": "2026-06-09 smoke returned content."}),
    Provider("cerebras", "Cerebras", "https://api.cerebras.ai/v1/chat/completions",
             "CEREBRAS_API_KEY", "free", "US",
             ("llama-3.3-70b", "llama3.1-8b", "gpt-oss-120b", "qwen-3-235b-a22b"),
             "llama-3.3-70b", "https://cloud.cerebras.ai/",
             "1M tokens/day; 8K context cap on free tier.",
             extra={"health": "quota_limited", "probe_note": "2026-06-09 auth passed; probes hit 429/404."}),
    Provider("gemini", "Google Gemini (AI Studio)",
             "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
             "GEMINI_API_KEY", "free", "US",
             ("gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.0-flash"),
             "gemini-2.5-flash", "https://aistudio.google.com/app/apikey",
             "Free tier varies by region; NOT available in EU/UK/CH. Data may train."),
    Provider("mistral", "Mistral (La Plateforme)",
             "https://api.mistral.ai/v1/chat/completions", "MISTRAL_API_KEY", "free", "FR",
             ("mistral-small-latest", "mistral-large-latest", "open-mistral-nemo"),
             "mistral-small-latest", "https://console.mistral.ai/api-keys",
             "~1B tokens/month Experiment plan; must opt into data training; phone verify."),
    Provider("nvidia", "NVIDIA NIM", "https://integrate.api.nvidia.com/v1/chat/completions",
             "NVIDIA_API_KEY", "free", "US",
             ("nvidia/llama-3.3-nemotron-super-49b-v1",
              "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning",
              "deepseek-ai/deepseek-r1"),
             "nvidia/llama-3.3-nemotron-super-49b-v1", "https://build.nvidia.com/",
             "Free with NVIDIA Developer Program; phone verify; ~40 RPM.",
             extra={"health": "proven", "probe_note": "Super 49B returned content; nano endpoint may return blank."}),
    Provider("github", "GitHub Models", "https://models.github.ai/inference/chat/completions",
             "GITHUB_TOKEN", "free", "US",
             ("openai/gpt-4.1-mini", "openai/gpt-4.1",
              "openai/gpt-4o-mini", "meta/Llama-4-Scout-17B-16E-Instruct"),
             "openai/gpt-4.1-mini", "https://github.com/marketplace/models",
             "Free for any GitHub user; restrictive token limits (prototyping).",
             extra={"headers": {"Accept": "application/vnd.github+json",
                                "X-GitHub-Api-Version": "2022-11-28"},
                    "health": "proven",
                    "probe_note": "2026-06-09 smoke returned content."}),
    Provider("huggingface", "HuggingFace Router",
             "https://router.huggingface.co/v1/chat/completions", "HF_TOKEN", "free", "US",
             ("moonshotai/Kimi-K2-Instruct-0905",
              "meta-llama/Llama-3.3-70B-Instruct",
              "mistralai/Mistral-7B-Instruct-v0.3"),
             "moonshotai/Kimi-K2-Instruct-0905", "https://huggingface.co/settings/tokens",
             "~$0.10-100K monthly inference credits; routes to multiple providers.",
             extra={"health": "proven", "probe_note": "2026-06-09 smoke returned content."}),
    Provider("ollama", "Ollama Cloud", "https://ollama.com/v1/chat/completions",
             "OLLAMA_API_KEY", "free", "US",
             ("deepseek-v3.2", "deepseek-v4-flash", "qwen3-next:80b", "glm-4.6", "glm-5",
              "kimi-k2.5", "minimax-m2", "mistral-large-3:675b", "nemotron-3-super",
              "cogito-2.1:671b", "gemini-3-flash-preview", "gemma4:31b"),
             "deepseek-v3.2", "https://ollama.com/settings/keys",
             "Frontier-class open-weight roster; serialises (slow but free). PROVEN here."),

    # ---------------- Chinese providers, OpenAI-compatible ----------------
    Provider("zhipu", "Z AI / Zhipu (GLM)", "https://open.bigmodel.cn/api/paas/v4/chat/completions",
             "ZHIPU_API_KEY", "free", "CN",
             ("glm-4-flash", "glm-4.5-flash", "glm-4-flashx"),
             "glm-4-flash", "https://open.bigmodel.cn/usercenter/apikeys",
             "PERMANENT free GLM-*-Flash models, no card. Intl mirror: https://api.z.ai/api/paas/v4 ."),
    Provider("deepseek", "DeepSeek", "https://api.deepseek.com/v1/chat/completions",
             "DEEPSEEK_API_KEY", "free", "CN",
             ("deepseek-chat", "deepseek-reasoner"),
             "deepseek-chat", "https://platform.deepseek.com/api_keys",
             "5M free tokens on signup, no card; then very cheap."),
    Provider("dashscope", "Alibaba DashScope (Qwen)",
             "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions",
             "DASHSCOPE_API_KEY", "free", "CN",
             ("qwen-plus", "qwen-max", "qwen-turbo"),
             "qwen-plus", "https://bailian.console.alibabacloud.com/",
             "1M free tokens PER Qwen model on signup, expires in 90 days (intl endpoint)."),
    Provider("modelscope", "ModelScope (Alibaba)",
             "https://api-inference.modelscope.cn/v1/chat/completions", "MODELSCOPE_API_KEY",
             "free", "CN",
             ("Qwen/Qwen2.5-72B-Instruct", "deepseek-ai/DeepSeek-V3"),
             "Qwen/Qwen2.5-72B-Instruct", "https://modelscope.cn/my/myaccesstoken",
             "Free API-Inference for registered users; bind a phone."),
    Provider("siliconflow", "SiliconFlow", "https://api.siliconflow.cn/v1/chat/completions",
             "SILICONFLOW_API_KEY", "free", "CN",
             ("Qwen/Qwen2.5-7B-Instruct", "deepseek-ai/DeepSeek-R1-Distill-Qwen-7B"),
             "Qwen/Qwen2.5-7B-Instruct", "https://cloud.siliconflow.cn/account/ak",
             "3 permanently-free models; ~50 req/day cap. Intl: https://api.siliconflow.com/v1 ."),

    # ---------------- anonymous / no signup ----------------
    Provider("ovhcloud", "OVHcloud AI Endpoints",
             "https://oai.endpoints.kepler.ai.cloud.ovh.net/v1/chat/completions", "", "anon", "FR",
             ("Meta-Llama-3_3-70B-Instruct", "Qwen3-32B", "DeepSeek-R1-Distill-Llama-70B"),
             "Meta-Llama-3_3-70B-Instruct", "https://endpoints.ai.cloud.ovh.net/",
             "NO signup / NO key for 2 RPM per IP per model. Great for instant smoke tests."),
    Provider("llm7", "LLM7.io", "https://api.llm7.io/v1/chat/completions", "LLM7_API_KEY",
             "anon", "GB",
             ("default", "fast", "pro", "deepseek-r1", "deepseek-v3"),
             "default", "https://token.llm7.io",
             "30 RPM with NO token; 120 RPM with a free token. Key is OPTIONAL.",
             extra={"key_optional": True, "health": "proven",
                    "probe_note": "2026-06-09 smoke returned content."}),

    # ---------------- trial credits (use once; not permanent) ----------------
    Provider("openrouter", "OpenRouter (free models)",
             "https://openrouter.ai/api/v1/chat/completions", "OPENROUTER_API_KEY", "trial", "US",
             ("deepseek/deepseek-r1:free", "meta-llama/llama-3.3-70b-instruct:free",
              "qwen/qwen3-235b-a22b:free"),
             "meta-llama/llama-3.3-70b-instruct:free", "https://openrouter.ai/keys",
             "~28 ':free' models (20 RPM/50 RPD) even without credit, BUT needs a VALID key "
             "(the current .env key returns 401 'User not found' -- regenerate it)."),
    Provider("openrouter_claude_opus48", "OpenRouter Claude Opus 4.8",
             "https://openrouter.ai/api/v1/chat/completions", "OPENROUTER_API_KEY", "trial", "US",
             ("anthropic/claude-opus-4.8",), "anthropic/claude-opus-4.8",
             "https://openrouter.ai/keys",
             "Paid frontier candidate/judge slot. Refresh model availability and pricing via "
             "https://openrouter.ai/api/v1/models before a paid run.",
             extra={"health": "paid_planned", "headers": {"X-OpenRouter-Title": "DueCare Evaluation"}}),
    Provider("openrouter_gemini35_flash", "OpenRouter Gemini 3.5 Flash",
             "https://openrouter.ai/api/v1/chat/completions", "OPENROUTER_API_KEY", "trial", "US",
             ("google/gemini-3.5-flash",), "google/gemini-3.5-flash",
             "https://openrouter.ai/keys",
             "Paid broad-coverage candidate/judge slot. Refresh model availability and pricing via "
             "https://openrouter.ai/api/v1/models before a paid run.",
             extra={"health": "paid_planned", "headers": {"X-OpenRouter-Title": "DueCare Evaluation"}}),
    Provider("openrouter_grok43", "OpenRouter Grok 4.3",
             "https://openrouter.ai/api/v1/chat/completions", "OPENROUTER_API_KEY", "trial", "US",
             ("x-ai/grok-4.3",), "x-ai/grok-4.3",
             "https://openrouter.ai/keys",
             "Paid fast reasoning candidate/arbiter slot. Refresh model availability and pricing via "
             "https://openrouter.ai/api/v1/models before a paid run.",
             extra={"health": "paid_planned", "headers": {"X-OpenRouter-Title": "DueCare Evaluation"}}),
    Provider("openrouter_nemotron_ultra", "OpenRouter Nemotron 3 Ultra",
             "https://openrouter.ai/api/v1/chat/completions", "OPENROUTER_API_KEY", "trial", "US",
             ("nvidia/nemotron-3-ultra-550b-a55b",), "nvidia/nemotron-3-ultra-550b-a55b",
             "https://openrouter.ai/keys",
             "Paid low-cost large-model candidate slot. Refresh model availability and pricing via "
             "https://openrouter.ai/api/v1/models before a paid run.",
             extra={"health": "paid_planned", "headers": {"X-OpenRouter-Title": "DueCare Evaluation"}}),
    Provider("openrouter_qwen37max", "OpenRouter Qwen 3.7 Max",
             "https://openrouter.ai/api/v1/chat/completions", "OPENROUTER_API_KEY", "trial", "US",
             ("qwen/qwen3.7-max",), "qwen/qwen3.7-max",
             "https://openrouter.ai/keys",
             "Paid cost-effective agentic candidate slot. Refresh model availability and pricing via "
             "https://openrouter.ai/api/v1/models before a paid run.",
             extra={"health": "paid_planned", "headers": {"X-OpenRouter-Title": "DueCare Evaluation"}}),
    Provider("openrouter_qwen37plus", "OpenRouter Qwen 3.7 Plus",
             "https://openrouter.ai/api/v1/chat/completions", "OPENROUTER_API_KEY", "trial", "US",
             ("qwen/qwen3.7-plus",), "qwen/qwen3.7-plus",
             "https://openrouter.ai/keys",
             "Recent low-cost Qwen 3.7 candidate with text+image input and long context. "
             "Refresh model availability and pricing via https://openrouter.ai/api/v1/models before a paid run.",
             extra={"health": "paid_planned", "headers": {"X-OpenRouter-Title": "DueCare Evaluation"}}),
    Provider("xai", "xAI (Grok)", "https://api.x.ai/v1/chat/completions", "XAI_API_KEY",
             "trial", "US", ("grok-3-mini", "grok-4.1-fast"), "grok-3-mini",
             "https://console.x.ai", "$25 sign-up credit, no card."),
    Provider("sambanova", "SambaNova Cloud", "https://api.sambanova.ai/v1/chat/completions",
             "SAMBANOVA_API_KEY", "trial", "US",
             ("DeepSeek-V3.1", "Meta-Llama-3.3-70B-Instruct", "DeepSeek-V3-0324"), "DeepSeek-V3.1",
             "https://cloud.sambanova.ai/", "$5 credits (3 months); very fast.",
             extra={"health": "proven", "probe_note": "2026-06-09 smoke returned content."}),
    Provider("upstage", "Upstage", "https://api.upstage.ai/v1/chat/completions",
             "UPSTAGE_API_KEY", "trial", "KR",
             ("solar-pro3",), "solar-pro3", "https://console.upstage.ai/",
             "$10 signup credit; OpenAI-compatible chat endpoint.",
             extra={"health": "proven", "probe_note": "2026-06-09 smoke returned content."}),
    Provider("opencode_zen", "OpenCode Zen", "https://opencode.ai/zen/v1/chat/completions",
             "OPENCODE_API_KEY", "trial", "US",
             ("deepseek-v4-flash-free", "opencode/deepseek-v4-flash-free"),
             "deepseek-v4-flash-free", "https://opencode.ai/docs/zen",
             "OpenAI-compatible Zen endpoint; smoke may return blank content on some free models.",
             extra={"health": "unreliable", "probe_note": "2026-06-09 endpoint responded but free-model content was blank/odd."}),
    Provider("rapidapi_gemma4_26b", "RapidAPI Gemma 4 26B",
             "https://gemma-4-26b-by-google.p.rapidapi.com/chat/completions",
             "RAPIDAPI_KEY", "trial", "US",
             ("rapidapi/gemma-4-26b",), "rapidapi/gemma-4-26b",
             "https://rapidapi.com/",
             "RapidAPI chat-completions endpoint; uses x-rapidapi-key auth. "
             "Verify before judging: Python transports may receive empty content/provider 502.",
             openai_compatible=False,
             extra={"auth": "rapidapi", "host": "gemma-4-26b-by-google.p.rapidapi.com",
                    "omit_model": True, "reasoning_effort": "low", "probe_max_tokens": 64,
                    "probe_temperature": 0.1, "probe_prompt": "Reply with exactly: ok",
                    "health": "transport_flaky",
                    "probe_note": "PowerShell returned content; Python urllib got empty content and requests got provider 502."}),
    Provider("rapidapi_cheap_claude_opus45", "RapidAPI cheap Claude Opus 4.5 chat",
             "https://cheap-claude-opus-4-5.p.rapidapi.com/v1/chat/completions",
             "RAPIDAPI_KEY", "trial", "US",
             ("rapidapi/claude-opus-4.5-cheap",), "rapidapi/claude-opus-4.5-cheap",
             "https://rapidapi.com/",
             "RapidAPI chat-completions endpoint; observed 401/account-side failure in smoke.",
             openai_compatible=False,
             extra={"auth": "rapidapi", "host": "cheap-claude-opus-4-5.p.rapidapi.com",
                    "omit_model": True, "health": "auth_or_quota_blocked",
                    "probe_note": "2026-06-09 smoke reached provider but returned 401/quota/account-side failure."}),
    Provider("rapidapi_claude_opus47", "RapidAPI Claude Opus 4.7 text",
             "https://claude-opus-4-7-anthropic-ai-code-generator.p.rapidapi.com/api/generate/text",
             "RAPIDAPI_KEY", "trial", "US",
             ("rapidapi/claude-opus-4.7-code-generator",), "rapidapi/claude-opus-4.7-code-generator",
             "https://rapidapi.com/",
             "RapidAPI prompt/system/outputType endpoint; uses x-rapidapi-key auth.",
             openai_compatible=False,
             extra={"auth": "rapidapi", "host": "claude-opus-4-7-anthropic-ai-code-generator.p.rapidapi.com",
                    "body_shape": "rapidapi_text", "health": "quota_sensitive",
                    "probe_note": "Direct smoke returned content; later Basic-plan probe hit monthly quota."}),
    Provider("rapidapi_claude_opus47_coding", "RapidAPI Claude Opus 4.7 coding text",
             "https://claude-opus-4-7-ai-code-generator-by-anthropic-coding.p.rapidapi.com/api/generate/text",
             "RAPIDAPI_KEY", "trial", "US",
             ("rapidapi/claude-opus-4.7-anthropic-coding",), "rapidapi/claude-opus-4.7-anthropic-coding",
             "https://rapidapi.com/",
             "RapidAPI prompt/system/outputType endpoint; uses x-rapidapi-key auth.",
             openai_compatible=False,
             extra={"auth": "rapidapi", "host": "claude-opus-4-7-ai-code-generator-by-anthropic-coding.p.rapidapi.com",
                    "body_shape": "rapidapi_text", "health": "quota_sensitive",
                    "probe_note": "Direct smoke returned content; later Basic-plan probe hit monthly quota."}),
    Provider("rapidapi_claude_opus46", "RapidAPI Claude Opus 4.6 text",
             "https://claude-opus-4-6-anthropic-ai-code-generator.p.rapidapi.com/api/generate/text",
             "RAPIDAPI_KEY", "trial", "US",
             ("rapidapi/claude-opus-4.6-primary",), "rapidapi/claude-opus-4.6-primary",
             "https://rapidapi.com/",
             "RapidAPI prompt/system/outputType endpoint; uses x-rapidapi-key auth.",
             openai_compatible=False,
             extra={"auth": "rapidapi", "host": "claude-opus-4-6-anthropic-ai-code-generator.p.rapidapi.com",
                    "body_shape": "rapidapi_text", "health": "quota_sensitive",
                    "probe_note": "Direct smoke returned content; later Basic-plan probe hit monthly quota."}),
    Provider("rapidapi_claude_sonnet46", "RapidAPI Claude Sonnet 4.6 text",
             "https://claude-sonnet-4-6-ai-text-generator-for-coding-agents.p.rapidapi.com/api/generate/text",
             "RAPIDAPI_KEY", "trial", "US",
             ("rapidapi/claude-sonnet-4.6-coding-agents",), "rapidapi/claude-sonnet-4.6-coding-agents",
             "https://rapidapi.com/",
             "RapidAPI prompt/system/outputType endpoint; uses x-rapidapi-key auth.",
             openai_compatible=False,
             extra={"auth": "rapidapi", "host": "claude-sonnet-4-6-ai-text-generator-for-coding-agents.p.rapidapi.com",
                    "body_shape": "rapidapi_text", "health": "quota_sensitive",
                    "probe_note": "Direct smoke returned content; later Basic-plan probe hit monthly quota."}),
    Provider("rapidapi_claude_opus46_agents", "RapidAPI Claude Opus 4.6 agents text",
             "https://claude-opus-4-6-api-best-ai-code-generator-for-agents.p.rapidapi.com/api/generate/text",
             "RAPIDAPI_KEY", "trial", "US",
             ("rapidapi/claude-opus-4.6-agent-generator",), "rapidapi/claude-opus-4.6-agent-generator",
             "https://rapidapi.com/",
             "RapidAPI prompt/system/outputType endpoint; uses x-rapidapi-key auth.",
             openai_compatible=False,
             extra={"auth": "rapidapi", "host": "claude-opus-4-6-api-best-ai-code-generator-for-agents.p.rapidapi.com",
                    "body_shape": "rapidapi_text", "health": "quota_sensitive",
                    "probe_note": "Direct smoke returned content; later Basic-plan probe hit monthly quota."}),
    Provider("nebius", "Nebius Token Factory", "https://api.studio.nebius.com/v1/chat/completions",
             "NEBIUS_API_KEY", "trial", "NL",
             ("meta-llama/Llama-3.3-70B-Instruct", "deepseek-ai/DeepSeek-V3"),
             "meta-llama/Llama-3.3-70B-Instruct", "https://studio.nebius.com/settings/api-keys",
             "$1 free signup credit, no card."),
    Provider("scaleway", "Scaleway Generative APIs",
             "https://api.scaleway.ai/v1/chat/completions", "SCALEWAY_API_KEY", "trial", "FR",
             ("gemma-3-27b-it", "llama-3.3-70b-instruct", "qwen3-235b-a22b"),
             "llama-3.3-70b-instruct", "https://console.scaleway.com/generative-api/models",
             "1,000,000 free tokens."),
)

BY_KEY = {p.key: p for p in REGISTRY}


def provider_health(p: Provider) -> str:
    """Human-readable reliability label from local probes and known behavior."""
    return str(p.extra.get("health") or "unverified")


def loop_configs() -> dict[str, dict]:
    """Map the registry into the shape `model_failure_loop.py` consumes."""
    out: dict[str, dict] = {}
    for p in REGISTRY:
        if not p.openai_compatible:
            continue
        judge = p.judge_model or (p.models[0] if p.models else "")
        out[p.key] = {
            "base_url": p.chat_url,
            "key_env": p.key_env,
            "gen_models": list(p.models),
            "judge_model": judge,
            "probe_model": judge,
            "tier": p.tier,
            "health": provider_health(p),
            "notes": p.notes,
        }
    return out


# --- liveness probe ---------------------------------------------------------
def _probe_body(p: Provider, model: str) -> bytes:
    if p.extra.get("body_shape") == "rapidapi_text":
        body = {
            "prompt": "reply with the single word OK",
            "system": "You are a concise test assistant.",
            "outputType": "text",
        }
    else:
        body = {
            "messages": [{"role": "user", "content": str(p.extra.get("probe_prompt") or "reply with the single word OK")}],
            "max_tokens": int(p.extra.get("probe_max_tokens") or 16),
            "temperature": float(p.extra.get("probe_temperature", 0)),
            "stream": False,
        }
        if not p.extra.get("omit_model"):
            body["model"] = model
        if p.extra.get("reasoning_effort"):
            body["reasoning_effort"] = p.extra["reasoning_effort"]
    return json.dumps(body).encode("utf-8")


def _probe_headers(p: Provider, api_key: str | None) -> dict[str, str]:
    headers = {
        "Content-Type": "application/json",
        "User-Agent": os.environ.get(
            "DUECARE_PROVIDER_PROBE_USER_AGENT",
            "Mozilla/5.0 DueCare-Provider-Probe/1.0",
        ),
    }
    headers.update({str(k): str(v) for k, v in (p.extra.get("headers") or {}).items()})
    if p.extra.get("auth") == "rapidapi":
        if p.extra.get("host"):
            headers["x-rapidapi-host"] = str(p.extra["host"])
        if api_key:
            headers["x-rapidapi-key"] = api_key
    elif api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


def _extract_probe_text(data: object) -> str:
    if isinstance(data, str):
        return data.strip()
    if isinstance(data, list):
        for item in data:
            text = _extract_probe_text(item)
            if text:
                return text
        return ""
    if not isinstance(data, dict):
        return ""
    choices = data.get("choices")
    if isinstance(choices, list) and choices:
        for choice in choices:
            text = _extract_probe_text(choice)
            if text:
                return text
    message = data.get("message")
    if isinstance(message, (dict, list, str)):
        text = _extract_probe_text(message)
        if text:
            return text
    for key in (
        "content",
        "reasoning_content",
        "reasoning",
        "text",
        "output",
        "result",
        "response",
        "generated_text",
        "completion",
    ):
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
        if isinstance(value, (dict, list)):
            text = _extract_probe_text(value)
            if text:
                return text
    nested = data.get("data")
    if isinstance(nested, (dict, list, str)):
        return _extract_probe_text(nested)
    return ""


def probe(p: Provider, *, timeout: int = 30) -> tuple[bool, str]:
    """One tiny chat call. Returns (live, detail). Never raises."""
    api_key = os.environ.get(p.key_env) if p.key_env else None
    if p.key_env and not api_key and not p.extra.get("key_optional"):
        return False, f"{p.key_env} not set"
    model = p.judge_model or (p.models[0] if p.models else "")
    if not model:
        return False, "no model id in registry"
    body = _probe_body(p, model)
    headers = _probe_headers(p, api_key)
    req = urllib.request.Request(p.chat_url, data=body, method="POST", headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", "replace")
        try:
            data: object = json.loads(raw)
        except json.JSONDecodeError:
            data = raw
        text = _extract_probe_text(data)
        if text:
            return True, f"live: {model}"
        return False, f"no content: {str(data)[:100]}"
    except urllib.error.HTTPError as e:
        return False, f"HTTP {e.code}: {e.read().decode('utf-8','replace')[:140]}"
    except Exception as e:  # noqa: BLE001
        return False, f"{type(e).__name__}: {e}"


# --- CLI --------------------------------------------------------------------
def _cmd_list(args) -> int:
    rows = [p for p in REGISTRY if args.tier in (None, "all", p.tier)]
    if args.health:
        wanted = {item.strip().lower() for item in args.health.split(",") if item.strip()}
        rows = [p for p in rows if provider_health(p).lower() in wanted]
    print(f"{'key':30s} {'tier':6s} {'health':18s} {'env var':20s} provider")
    print("-" * 112)
    for p in rows:
        print(f"{p.key:30s} {p.tier:6s} {provider_health(p):18s} {(p.key_env or '(none)'):20s} {p.name}")
        print(f"{'':30s} models: {', '.join(p.models[:4])}")
        print(f"{'':30s} signup: {p.signup}")
        if p.notes:
            print(f"{'':30s} note  : {p.notes}")
        if p.extra.get("probe_note"):
            print(f"{'':30s} probe : {p.extra['probe_note']}")
    print(f"\n{len(rows)} providers ({sum(p.tier=='free' for p in rows)} permanent-free, "
          f"{sum(p.tier=='anon' for p in rows)} anonymous, {sum(p.tier=='trial' for p in rows)} trial-credit)")
    return 0


def _env_file_keys() -> set[str]:
    """Names of keys already assigned a NON-empty value in repo .env (so the
    template can skip them -- appending `KEY=` empty would clobber a live key when
    .env is sourced top-to-bottom). Reads names only; never reads/echoes values."""
    have: set[str] = set()
    env_path = REPO / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            if v.strip():
                have.add(k.strip())
    return have


def _cmd_env_template(args) -> int:
    have = _env_file_keys() | {k for k in os.environ if (os.environ.get(k) or "").strip()}
    print("# --- Free LLM API keys (append to .env with '>> .env', then fill values) ---")
    print("# Anonymous providers need NO key: " +
          ", ".join(p.key for p in REGISTRY if p.tier == "anon" and not p.key_env))
    seen: set[str] = set()
    emitted = 0
    for p in REGISTRY:
        if not p.key_env or p.key_env in seen:
            continue
        seen.add(p.key_env)
        if p.key_env in have and not args.all:
            print(f"# {p.key_env} already set -- skipping ({p.name})")
            continue
        print(f"{p.key_env}=        # {p.name} ({p.tier}) -> {p.signup}")
        emitted += 1
    if not emitted and not args.all:
        print("# (every known provider key is already set -- nothing to add)")
    return 0


def _cmd_probe(args) -> int:
    only = {k.strip() for k in args.only.split(",")} if args.only else None
    rows = [p for p in REGISTRY if (only is None or p.key in only)
            and (args.tier in (None, "all", p.tier))]
    live = []
    print(f"Probing {len(rows)} providers...\n")
    for p in rows:
        ok, detail = probe(p)
        print(f"  [{'LIVE' if ok else 'dead'}] {p.key:14s} {detail}")
        if ok:
            live.append(p.key)
    print(f"\n{len(live)} live: {', '.join(live) if live else '(none)'}")
    loop_ready = [key for key in live if BY_KEY.get(key) and BY_KEY[key].openai_compatible]
    if loop_ready:
        print("\nRun the study on a live free provider, e.g.:")
        print(f"  python scripts/model_failure_loop.py --provider {loop_ready[0]} --run-tag {loop_ready[0]} "
              "--skip-generation --responses reports/model_failure_study/study_v1.jsonl")
    elif live:
        print("\nLive providers in this probe use non-OpenAI-compatible auth/body shapes; use them through A-00 "
              "rapidapi_chat / rapidapi_text or provider-specific scripts.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    pl = sub.add_parser("list")
    pl.add_argument("--tier", choices=["free", "anon", "trial", "all"])
    pl.add_argument("--health", default=None, help="comma-separated health labels, e.g. proven,quota_sensitive")
    pe = sub.add_parser("env-template")
    pe.add_argument("--all", action="store_true",
                    help="emit every key (default: skip keys already set in .env, so '>> .env' is safe)")
    pp = sub.add_parser("probe")
    pp.add_argument("--only", default=None, help="comma-separated provider keys")
    pp.add_argument("--tier", choices=["free", "anon", "trial", "all"])
    args = ap.parse_args()
    if args.cmd == "list":
        return _cmd_list(args)
    if args.cmd == "env-template":
        return _cmd_env_template(args)
    if args.cmd == "probe":
        return _cmd_probe(args)
    return 1


if __name__ == "__main__":
    sys.exit(main())
