# Provider Budgeting

DueCare has a shared, fail-closed budget ledger for every model-network attempt
that enters the primary generation router in `scripts/llm_generate.py`, the
optional OpenAI-compatible classifier in `scripts/adverse_media.py`, and the
baseline candidate and contextual judge clients in
`scripts/model_failure_study.py` and `scripts/model_failure_judge.py`. The
ledger and direct-client migrations are tested offline. The later Kimi access
check and frozen Kimi/Gemini campaign are recorded separately below.

## What The Ledger Enforces

Before each HTTP attempt, `scripts/provider_budget.py` atomically reserves:

- one provider attempt;
- a conservative input-token estimate;
- the caller's finite maximum output tokens; and
- the worst-case cost implied by an operator-reviewed pricing file.

SQLite `BEGIN IMMEDIATE` transactions make the reservation safe across threads
and processes sharing one run. A retry, key rotation, or resilient re-question
is a new attempt and consumes a new reservation. Failed and canceled attempts
are not refunded. If exact OpenAI-compatible, Anthropic, or Ollama usage is in
the response, the ledger records it; otherwise it records a deterministic
estimate. An actual overrun marks the run breached and blocks the next attempt.

The ledger stores provider labels, counts, status classes, timestamps, and
SHA-256 values for prompts and model IDs. It does not store prompts, responses,
keys, URLs, model IDs, or raw error messages. The SQLite file is authoritative;
the JSON receipt is a sanitized convenience export. Both default below ignored
`reports/provider_budget/`.

## Keep All Covered Calls At Zero

For deterministic maintenance:

```powershell
$env:DUECARE_MAX_PLANNED_MODEL_CALLS='0'
python scripts/provider_budget.py
python scripts/validate_provider_budget_coverage.py
```

The zero-call value activates transport enforcement, not merely planning. The
offline integration tests assert that `ollama_chat()` raises before
`_http_post_json()` and that the adverse-media classifier raises before
`urlopen()`.

For the stronger Windows host-level stopping posture, also stop and inspect the
whole model/flywheel stack:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/stop_ollama_stack.ps1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/stop_ollama_stack.ps1 -Status
```

The status succeeds only when all five recurring tasks are disabled, all four
daemon sentinels exist, and no exact repository daemon process remains. The
default stop does not regenerate, commit, or push leaderboard files.

## Daemon Startup Boundary

The autonomous-engine, Hermes discovery, and server-automation vetter wrappers
call the primary router and now refuse their run, one-shot, restart, watchdog,
or resume paths unless all of these are explicit:

- a positive `DUECARE_MAX_PLANNED_MODEL_CALLS`;
- a stable `DUECARE_PROVIDER_RUN_ID`;
- finite input-token, output-token, and cash caps; and
- a reviewed pricing file or a deliberately recorded unknown-cost override.

The wrappers run `provider_budget.py` before removing a pause sentinel or
starting a process. Their scheduled `-Run` paths preserve sentinels, and
registering a watchdog no longer resumes work. Process-scoped environment
settings take precedence over `.env`, so an operator can tighten a stale local
configuration. This protects these three entry points; it is not a universal
interceptor for every direct client in the repository.

## Configure A Deliberately Bounded Run

Do this only after a maintainer authorizes provider spend:

```powershell
Copy-Item configs/duecare/provider_pricing.example.json `
  reports/provider_budget/pricing.reviewed.json
# Edit the ignored copy: add a verification date, exact immutable model IDs,
# and rates checked against each provider's official pricing page.

$env:DUECARE_PROVIDER_RUN_ID='sampled-study-20260727'
$env:DUECARE_MAX_PLANNED_MODEL_CALLS='12'
$env:DUECARE_MAX_INPUT_TOKENS='120000'
$env:DUECARE_MAX_OUTPUT_TOKENS='24000'
$env:DUECARE_MAX_PROVIDER_COST_USD='5.00'
$env:DUECARE_PROVIDER_PRICING_FILE='reports/provider_budget/pricing.reviewed.json'
$env:DUECARE_PROVIDER_BUDGET_FILE='reports/provider_budget/sampled-study.sqlite3'
$env:DUECARE_PROVIDER_BUDGET_RECEIPT='reports/provider_budget/sampled-study.receipt.json'
python scripts/provider_budget.py --json
```

Positive call allowances require the run ID and all three finite token/cash
caps. A run ID freezes its policy; reusing that ID with different limits fails.
Unknown provider/model pricing also fails before transport. The explicit
`DUECARE_ALLOW_UNKNOWN_PROVIDER_COST=1` override exists for a genuinely
zero-priced or internally metered endpoint, but it disables meaningful cash
enforcement for those attempts and must be recorded as a review decision.

When a caller omits an output cap, the router reserves a conservative fallback:
Ollama reserves its configured context window, Anthropic reserves the request's
required finite limit, and other compatible endpoints reserve
`DUECARE_DEFAULT_RESERVED_OUTPUT_TOKENS` (default 4096). A funded study should
still set a model-appropriate positive `max_tokens` explicitly.

The adverse-media classifier always sends and reserves a finite output cap from
`DUECARE_ADVERSE_MEDIA_MAX_OUTPUT_TOKENS` (default 512). Its short JSON verdicts
normally need much less; lower the cap only in a reviewed run manifest. Pricing
entries use the stable provider label `adverse-media-openai-compatible` plus
the exact configured model ID.

## Frontier Comparison Watchlist

The first approved frozen smoke matrix should treat these as required candidate
lanes, not optional substitutions:

- **Kimi K3.** On 2026-07-28 the verified identifiers were
  `kimi-k3:cloud` on [Ollama](https://ollama.com/library/kimi-k3:cloud) and
  `moonshotai/kimi-k3` on
  [OpenRouter](https://openrouter.ai/moonshotai/kimi-k3-20260715). Ollama
  labels the model as extra usage requiring an eligible paid plan and lists a
  one-million-token context plus $3/M input, $0.30/M cached input, and $15/M
  output. OpenRouter listed the same one-million-token context and $3/M input,
  $15/M output rates. A future smoke therefore needs both a cash cap and an
  output-token cap before any broader matrix.
- **Gemini 3.1 Pro.** The frozen cross-family judge uses
  [`gemini-3.1-pro-preview`](https://ai.google.dev/gemini-api/docs/models/gemini-3.1-pro-preview)
  through Google's official
  [OpenAI-compatible endpoint](https://ai.google.dev/gemini-api/docs/openai).
  The model card lists a 1,048,576-token input limit and 65,536-token output
  limit. [Pricing](https://ai.google.dev/gemini-api/docs/pricing) checked on
  2026-07-28 was $2/M input and $12/M output for prompts up to 200K tokens,
  with no free tier for this preview model.
- **Meta Muse Spark 1.1.** This is the precise model name; "Meta Muse 1.1" is
  only shorthand. Meta announced developer access through the public-preview
  [Meta Model API](https://ai.meta.com/blog/introducing-muse-spark-meta-model-api/),
  and the verified OpenRouter identifier was
  [`meta/muse-spark-1.1`](https://openrouter.ai/meta/muse-spark-1.1) on
  2026-07-28, with a one-million-token context and listed rates of $1.25/M
  input and $4.25/M output.

The 2026-07-28 closeout decision performed catalog verification only and made
no model call. Kimi K3 and Meta Muse Spark 1.1 remain required lanes if a future
frozen comparison is reopened; preserving credits is preferable to running an
unmotivated smoke merely to empty a checklist.

### Later Kimi K3 access check

After closeout, the owner separately authorized a bounded access check. Five
requests using Ollama's live `kimi-k3` ID were reserved under a five-attempt,
20,000-input-token, 3,840-output-token, US$0.25 policy. Ollama returned HTTP 402
for all five because Kimi K3 uses extra usage and the account's extra-usage
balance was empty. The privacy-minimized local ledger recorded zero successful
calls, zero provider tokens, and zero actual cost. Therefore:

- the endpoint and credential path were reachable;
- no Kimi completion or quality score was produced;
- the five failures are not benchmark rows; and
- the proposed 500-prompt run stays stopped until the billing owner funds and
  explicitly authorizes a new capped run.

The exact model-free directional plan is now reproducible with:

```powershell
python scripts/model_failure_study.py `
  --models kimi-k3 --include-seeds --limit 500 `
  --selection-mode category-balanced --selection-seed 20260728 `
  --max-tokens 768 `
  --out reports/model_failure_study/kimi_k3_directional_500.jsonl `
  --base-url https://ollama.com/v1/chat/completions `
  --key-env OLLAMA_API_KEY --plan
```

At the checked revision it selects 500 public synthetic prompts across 117
categories with selection SHA-256
`9d4aedf042f5f9d73e8372a8f1bf5538190d9791dbc692c38ca720aed1bc48eb`.
It plans exactly 500 Kimi calls, reserves 158,922 estimated input tokens and
384,000 maximum output tokens, and has a US$6.2368 worst-case reservation at
the verified $3/M input and $15/M output rates. Every returned response would
receive a local deterministic DueCare grade.

### Frozen contextual-judge extension

The authoritative
[`kimi_k3_500_context_judge_campaign.json`](../configs/duecare/benchmarks/kimi_k3_500_context_judge_campaign.json)
extends the candidate phase without blending evidence layers:

- 500 baseline Kimi answers plus zero-call deterministic grades;
- 500 `gemini-3.1-pro-preview` cross-family contextual judgments, eligible as
  the primary automated result; and
- 500 Kimi K3 contextual self-judgments, reported only as a bias diagnostic.

Both judges receive the same hash-bound `duecare-full` bundle (fired GREP
indicators, top-eight RAG excerpts, and deterministic tool results). The
one-call holistic protocol returns all four rubric dimensions and is labeled
directional. A publication-grade `--protocol per-dimension` run remains a
separate, four-times-larger judge plan.

The frozen aggregate maximum is 1,500 hosted calls, 7,296,582 estimated input
tokens, 1,152,000 maximum output tokens, and US$34.448916 worst-case under a
US$35 ceiling. No part has executed: Kimi extra usage is unfunded and no Gemini
API credential is present. See the
[run-readiness receipt](research/model_failure_run_readiness.md) for the exact
no-call commands, phase separation, resume rules, and reconciled report command.

Availability, access rules, context, and prices are volatile. Recheck the
official catalog immediately before approving a run; never use a paid prompt
as catalog discovery. Compare both models on the same hash-bound text slice,
rubric, harness arms, decoding policy, and output cap. Put image, video, audio,
PDF, tool-use, and long-context tests in separately labeled extensions so their
extra modalities do not confound the comparable text result. Record a required
lane as unavailable rather than silently replacing it.

This watchlist does not authorize a call. The whole-stack cost stop and the
finite run-ledger requirements above remain in force.

## Coverage Boundary

| Surface | State | Operator rule |
|---|---|---|
| `llm_generate.py` Ollama Cloud, NVIDIA, Anthropic, and registered OpenAI-compatible transports | Enforced | One shared run budget covers every attempt, retry, key rotation, and re-question that reaches this router. |
| `adverse_media.py` optional OpenAI-compatible verification classifier | Enforced | One reservation precedes its direct `urlopen()` transport; every manual retry consumes another reservation, and the request has a finite output cap. Keyless GDELT, Google News, and OpenSanctions retrieval are data-source calls, not model calls, and remain outside model-token accounting. |
| `model_failure_study.py` candidate generation and `model_failure_judge.py` contextual judging | Enforced | Each direct `urlopen()` attempt is inside the shared reservation. Both retain independent no-call planning ceilings and resumable result files. |
| Autonomous-engine, discovery, and server-automation PowerShell model-call entry points | Enforced at startup and transport | Refuse launch without the finite shared budget; keep all watchdogs and sentinels cost-stopped during maintenance. |
| Rich-harness and judge paths that call `provider_chat()` or `resilient_chat()` | Enforced through the router | Keep the existing logical `--plan` ceiling too; planning and transport receipts answer different questions. |
| Self-contained Kaggle kernels, including active 01/A-00 and optional 03 | Not connected to the local SQLite ledger | Offline validation needs no secrets. For a live notebook run, use that notebook's explicit sample/call limits and inspect its export before claiming completion. |
| Package/application model adapters and standalone scripts that issue their own HTTP requests | Not yet universal | Remove or withhold credentials during maintenance; migrate the caller to this ledger contract before a funded broad run. This includes the optional website automation provider path. |
| Local deterministic inference without a metered provider | Outside cash accounting | Preserve its own timeout, context, and resource limits. |

The static coverage validator deliberately makes these seven registered
transports exact: it parses the router and fails if any of its four HTTP
transports moves outside `_budget_attempt`, checks the direct adverse-media
transport against `_provider_budget_attempt`, and verifies the candidate and
judge `urlopen()` calls remain inside their ledger attempts. It does not claim
to scan or intercept every independent HTTP client in the repository.

## Verification

```powershell
python scripts/validate_provider_budget_coverage.py
python -m pytest tests/test_provider_budget.py `
  tests/test_adverse_media_budget.py `
  tests/test_adverse_media.py `
  tests/test_model_failure_study.py `
  tests/test_model_failure_judge.py `
  tests/test_kimi_k3_context_judge_campaign.py `
  tests/test_validate_provider_budget_coverage.py `
  tests/test_llm_generate_retry.py `
  tests/test_stop_ollama_stack.py -q
```

The contract tests cover zero-transport denial for the covered direct clients,
concurrent atomic reservation, frozen policies, pricing lookup, token/cash
caps, sanitized receipts, exact and estimated usage, failed-attempt retention,
and retry accounting.

## Next Transport Work

The adverse-media verifier and both direct model-failure clients have completed
this migration. The next maintainer should inventory and migrate one remaining
direct caller per reviewable change, then decide how package and application
adapters should accept an injectable ledger. Notebook runtimes need a portable
equivalent because Kaggle cannot share the local SQLite file. Keep those
migrations separate from benchmark result lanes, and do not describe the
current seven-transport guard as a repository-wide network interceptor.
