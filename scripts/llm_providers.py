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
             ("llama-3.3-70b-versatile", "llama-3.1-8b-instant",
              "deepseek-r1-distill-llama-70b", "openai/gpt-oss-120b"),
             "llama-3.3-70b-versatile", "https://console.groq.com/keys",
             "Very fast; generous free RPM/RPD, no card."),
    Provider("cerebras", "Cerebras", "https://api.cerebras.ai/v1/chat/completions",
             "CEREBRAS_API_KEY", "free", "US",
             ("llama-3.3-70b", "llama3.1-8b", "gpt-oss-120b", "qwen-3-235b-a22b"),
             "llama-3.3-70b", "https://cloud.cerebras.ai/",
             "1M tokens/day; 8K context cap on free tier."),
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
             ("meta/llama-3.3-70b-instruct", "deepseek-ai/deepseek-r1",
              "nvidia/llama-3.1-nemotron-70b-instruct"),
             "meta/llama-3.3-70b-instruct", "https://build.nvidia.com/",
             "Free with NVIDIA Developer Program; phone verify; ~40 RPM."),
    Provider("github", "GitHub Models", "https://models.github.ai/inference/chat/completions",
             "GITHUB_TOKEN", "free", "US",
             ("gpt-4o", "gpt-4.1", "gpt-4o-mini", "meta/Llama-4-Scout-17B-16E-Instruct"),
             "gpt-4o", "https://github.com/marketplace/models",
             "Free for any GitHub user; VERY restrictive token limits (prototyping)."),
    Provider("huggingface", "HuggingFace Router",
             "https://router.huggingface.co/v1/chat/completions", "HF_TOKEN", "free", "US",
             ("meta-llama/Llama-3.3-70B-Instruct", "mistralai/Mistral-7B-Instruct-v0.3",
              "Qwen/Qwen2.5-7B-Instruct"),
             "meta-llama/Llama-3.3-70B-Instruct", "https://huggingface.co/settings/tokens",
             "~$0.10-100K monthly inference credits; routes to multiple providers."),
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
             ("gpt-4o-mini-2024-07-18", "deepseek-r1", "deepseek-v3"),
             "gpt-4o-mini-2024-07-18", "https://token.llm7.io",
             "30 RPM with NO token; 120 RPM with a free token. Key is OPTIONAL."),

    # ---------------- trial credits (use once; not permanent) ----------------
    Provider("openrouter", "OpenRouter (free models)",
             "https://openrouter.ai/api/v1/chat/completions", "OPENROUTER_API_KEY", "trial", "US",
             ("deepseek/deepseek-r1:free", "meta-llama/llama-3.3-70b-instruct:free",
              "qwen/qwen3-235b-a22b:free"),
             "meta-llama/llama-3.3-70b-instruct:free", "https://openrouter.ai/keys",
             "~28 ':free' models (20 RPM/50 RPD) even without credit, BUT needs a VALID key "
             "(the current .env key returns 401 'User not found' -- regenerate it)."),
    Provider("xai", "xAI (Grok)", "https://api.x.ai/v1/chat/completions", "XAI_API_KEY",
             "trial", "US", ("grok-3-mini", "grok-4.1-fast"), "grok-3-mini",
             "https://console.x.ai", "$25 sign-up credit, no card."),
    Provider("sambanova", "SambaNova Cloud", "https://api.sambanova.ai/v1/chat/completions",
             "SAMBANOVA_API_KEY", "trial", "US",
             ("Meta-Llama-3.3-70B-Instruct", "DeepSeek-V3-0324"), "Meta-Llama-3.3-70B-Instruct",
             "https://cloud.sambanova.ai/", "$5 credits (3 months); very fast."),
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


def loop_configs() -> dict[str, dict]:
    """Map the registry into the shape `model_failure_loop.py` consumes."""
    out: dict[str, dict] = {}
    for p in REGISTRY:
        judge = p.judge_model or (p.models[0] if p.models else "")
        out[p.key] = {
            "base_url": p.chat_url,
            "key_env": p.key_env,
            "gen_models": list(p.models),
            "judge_model": judge,
            "probe_model": judge,
            "tier": p.tier,
        }
    return out


# --- liveness probe ---------------------------------------------------------
def probe(p: Provider, *, timeout: int = 30) -> tuple[bool, str]:
    """One tiny chat call. Returns (live, detail). Never raises."""
    api_key = os.environ.get(p.key_env) if p.key_env else None
    if p.key_env and not api_key:
        return False, f"{p.key_env} not set"
    model = p.judge_model or (p.models[0] if p.models else "")
    if not model:
        return False, "no model id in registry"
    body = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": "reply with the single word OK"}],
        "max_tokens": 16, "temperature": 0,
    }).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    req = urllib.request.Request(p.chat_url, data=body, method="POST", headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        if data.get("choices"):
            msg = data["choices"][0].get("message", {})
            has_content = bool((msg.get("content") or "").strip())
            tag = "" if has_content else " (empty content -- poor judge, text in reasoning)"
            return True, f"live: {model}{tag}"
        return False, f"no choices: {str(data)[:100]}"
    except urllib.error.HTTPError as e:
        return False, f"HTTP {e.code}: {e.read().decode('utf-8','replace')[:140]}"
    except Exception as e:  # noqa: BLE001
        return False, f"{type(e).__name__}: {e}"


# --- CLI --------------------------------------------------------------------
def _cmd_list(args) -> int:
    rows = [p for p in REGISTRY if args.tier in (None, "all", p.tier)]
    print(f"{'key':14s} {'tier':6s} {'region':3s} {'env var':20s} provider")
    print("-" * 88)
    for p in rows:
        print(f"{p.key:14s} {p.tier:6s} {p.region:3s} {(p.key_env or '(none)'):20s} {p.name}")
        print(f"{'':14s} models: {', '.join(p.models[:4])}")
        print(f"{'':14s} signup: {p.signup}")
        if p.notes:
            print(f"{'':14s} note  : {p.notes}")
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
    if live:
        print("\nRun the study on a live free provider, e.g.:")
        print(f"  python scripts/model_failure_loop.py --provider {live[0]} --run-tag {live[0]} "
              "--skip-generation --responses reports/model_failure_study/study_v1.jsonl")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    pl = sub.add_parser("list"); pl.add_argument("--tier", choices=["free", "anon", "trial", "all"])
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
