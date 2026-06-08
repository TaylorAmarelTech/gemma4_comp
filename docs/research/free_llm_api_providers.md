# Free LLM API providers — the "plate" + setup guide

> Goal: run the model-failure study (and any DueCare cross-model comparison) across
> as many **free / freemium** OpenAI-compatible endpoints as possible **before**
> spending on a paid roster. The registry is `scripts/llm_providers.py`; it plugs
> straight into `scripts/model_failure_loop.py` (`--provider <key>`).
>
> Compiled 2026-06-08 from
> [cheahjs/free-llm-api-resources](https://github.com/cheahjs/free-llm-api-resources),
> [mnfst/awesome-free-llm-apis](https://github.com/mnfst/awesome-free-llm-apis), and
> [analyticsvidhya: top free LLM APIs](https://www.analyticsvidhya.com/blog/2026/01/top-free-llm-apis/).
> These lists change fast — re-verify model ids against each provider's `/models`.

## TL;DR (three commands)

```bash
set -a; . ./.env; set +a
PY="$LOCALAPPDATA/gemma4-testenv/venv/Scripts/python.exe"   # or any python3

python scripts/llm_providers.py list           # the full catalog
python scripts/llm_providers.py env-template    # the .env keys to fill + signup URLs
python scripts/llm_providers.py probe           # which providers are LIVE right now
```

`probe` is the one that matters day-to-day: it sends one tiny chat to every provider
whose key is present and prints LIVE/dead, so you always know what you can use without
paying. As of 2026-06-08 with the current `.env`: **`mistral` and `ollama` are LIVE**;
`ovhcloud` is reachable but rate-limited (anonymous 2 RPM/IP); `openrouter` returns 401
(dead key — regenerate it); everything else just needs a key.

## How it connects to the study

Every provider below is OpenAI-`/chat/completions`-shaped, so it drops into the loop
with no code change — only the `--provider` flag:

```bash
# 1) See what's live, 2) run the study on a live free provider, 3) aggregate.
python scripts/llm_providers.py probe
python scripts/model_failure_loop.py --provider mistral --run-tag mistral \
  --skip-generation --responses reports/model_failure_study/study_v1.jsonl
```

To compare **across many free providers**, run the loop once per provider (each writes
`study_<tag>.jsonl`), then aggregate all of them into one report — `report.py` already
accepts multiple inputs:

```bash
for P in groq cerebras gemini mistral ollama deepseek zhipu; do
  python scripts/model_failure_loop.py --provider $P --run-tag $P --max-rounds 1 || true
done
python scripts/model_failure_report.py \
  --in reports/model_failure_study/study_groq.jsonl \
       reports/model_failure_study/study_cerebras.jsonl \
       reports/model_failure_study/study_gemini.jsonl  ... \
  --judge reports/model_failure_study/judge_*.jsonl \
  --out docs/research/model_failure_on_human_exploitation.md
```

## Recommended keys to grab first (all free, no card)

Priority order — best speed/limits/coverage for the study, fastest to set up:

| Provider | Why first | Free tier | Get a key |
|---|---|---|---|
| **Groq** | fastest inference, big free RPD | free, no card | https://console.groq.com/keys |
| **Cerebras** | 1M tokens/day, strong models | free, no card | https://cloud.cerebras.ai/ |
| **Google Gemini** | Gemini 2.5 Flash/Pro free | free (not EU/UK/CH) | https://aistudio.google.com/app/apikey |
| **DeepSeek** 🇨🇳 | 5M free tokens on signup | free, no card | https://platform.deepseek.com/api_keys |
| **Z AI / Zhipu (GLM)** 🇨🇳 | **permanent** free GLM-Flash | free, no card | https://open.bigmodel.cn/usercenter/apikeys |
| **Mistral** | ~1B tokens/month | free (opt into data training) | https://console.mistral.ai/api-keys |
| **OVHcloud** | **no signup at all** (2 RPM/IP) | anonymous | — (just works) |
| **Ollama Cloud** | frontier-class open roster | free (slow) | https://ollama.com/settings/keys |

Chinese providers (`deepseek`, `zhipu`, `dashscope`, `modelscope`, `siliconflow`) are
all OpenAI-compatible; **Zhipu's GLM-*-Flash and DeepSeek's 5M-token grant are the
standouts** for genuinely-free, no-card access. Trial-credit providers (`xai` $25,
`sambanova` $5, `nebius` $1, `scaleway` 1M tokens) are worth one run each.

## Setup (3 steps)

1. **Generate the key block** and paste it into `.env` (repo root, gitignored):
   ```bash
   python scripts/llm_providers.py env-template >> .env   # then fill in the values
   ```
   `.env` (excerpt):
   ```dotenv
   GROQ_API_KEY=gsk_...
   CEREBRAS_API_KEY=csk-...
   GEMINI_API_KEY=AIza...
   DEEPSEEK_API_KEY=sk-...
   ZHIPU_API_KEY=...
   MISTRAL_API_KEY=...          # already present, LIVE
   OLLAMA_API_KEY=...           # already present, LIVE
   # OVHcloud + LLM7 need NO key
   ```
2. **Confirm liveness:** `python scripts/llm_providers.py probe` — fill keys until the
   providers you want show `[LIVE]`.
3. **Run the study:** `python scripts/model_failure_loop.py --provider <key> ...`
   (or `--provider auto` to use the first live one).

## Judge-model note (important)

The independent judge must return its verdict in the OpenAI `content` field. Good
content-emitting judges: `mistral-small-latest`, `llama-3.3-70b` (Groq/Cerebras),
`gpt-4o` (GitHub), `deepseek-chat`. Some reasoning models (`qwen3-next`, `glm-4.6`,
`gemini-3-flash-preview` on Ollama) leave `content` empty and put text in `reasoning`
— `parse_verdict` has a fallback, but prefer a content-emitter as the judge. (The
probe flags `empty content` as a heuristic; a reasoning model can still be fine with a
larger token budget — verify with a real judge call, not the 16-token probe.)

## Not an LLM API (so it's excluded)

- **Nokia** has a *Language Model & Generative AI* tool for **telecom network
  operations** (Bell Labs), not a public free LLM API hub. No OpenAI-compatible
  endpoint to integrate — excluded by design.

## Reference: an off-the-shelf aggregator (optional sidecar)

[`tashfeenahmed/freellmapi`](https://github.com/tashfeenahmed/freellmapi) is an OSS
proxy that stacks ~16 free tiers (~1.7B tokens/month) behind a single `/v1` endpoint
with smart routing + failover. If you'd rather hit one URL than manage per-provider
keys, run it as a local sidecar and point the loop at it
(`--provider` → a custom entry with its base URL). Our native registry is preferred
here because it keeps provenance per provider (which model on which endpoint produced
each response), which the study report needs.

## Maintenance

When a provider changes its endpoint, free tier, or model ids, edit the single
`REGISTRY` tuple in `scripts/llm_providers.py` and re-run `probe`. Keep this doc's
"recommended first" table and the registry in sync.
