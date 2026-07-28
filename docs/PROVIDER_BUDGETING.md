# Provider Budgeting

DueCare has a shared, fail-closed budget ledger for every model-network attempt
that enters the primary generation router in `scripts/llm_generate.py` and the
optional OpenAI-compatible classifier in `scripts/adverse_media.py`. The ledger
and this first direct-client migration were tested offline through 2026-07-28;
they did not make an Ollama, Kaggle, or hosted-provider call.

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

- **Kimi K3.** On 2026-07-27 the verified identifiers were
  `kimi-k3:cloud` on [Ollama](https://ollama.com/library/kimi-k3) and
  `moonshotai/kimi-k3` on
  [OpenRouter](https://openrouter.ai/moonshotai/kimi-k3-20260715). Ollama
  labels the model as extra usage requiring an eligible paid plan, so a small
  cash-capped smoke comes before any broader matrix.
- **Meta Muse Spark 1.1.** This is the precise model name; "Meta Muse 1.1" is
  only shorthand. Meta announced developer access through the public-preview
  [Meta Model API](https://ai.meta.com/blog/introducing-muse-spark-meta-model-api/),
  and the verified OpenRouter identifier was
  [`meta/muse-spark-1.1`](https://openrouter.ai/meta/muse-spark-1.1) on
  2026-07-27.

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
| Autonomous-engine, discovery, and server-automation PowerShell model-call entry points | Enforced at startup and transport | Refuse launch without the finite shared budget; keep all watchdogs and sentinels cost-stopped during maintenance. |
| Rich-harness and judge paths that call `provider_chat()` or `resilient_chat()` | Enforced through the router | Keep the existing logical `--plan` ceiling too; planning and transport receipts answer different questions. |
| Self-contained Kaggle kernels, including active 01/A-00 and optional 03 | Not connected to the local SQLite ledger | Offline validation needs no secrets. For a live notebook run, use that notebook's explicit sample/call limits and inspect its export before claiming completion. |
| Package/application model adapters and standalone scripts that issue their own HTTP requests | Not yet universal | Remove or withhold credentials during maintenance; migrate the caller to this ledger contract before a funded broad run. This includes the optional website automation provider path. |
| Local deterministic inference without a metered provider | Outside cash accounting | Preserve its own timeout, context, and resource limits. |

The static coverage validator deliberately makes the first two model-call rows
exact: it parses the router and fails if any of its four HTTP transports moves
outside `_budget_attempt`, then checks the one direct adverse-media model
transport against `_provider_budget_attempt`. It does not claim to scan or
intercept every independent HTTP client in the repository.

## Verification

```powershell
python scripts/validate_provider_budget_coverage.py
python -m pytest tests/test_provider_budget.py `
  tests/test_adverse_media_budget.py `
  tests/test_adverse_media.py `
  tests/test_validate_provider_budget_coverage.py `
  tests/test_llm_generate_retry.py `
  tests/test_stop_ollama_stack.py -q
```

The contract tests cover zero-transport denial for both covered call paths,
concurrent atomic reservation, frozen policies, pricing lookup, token/cash
caps, sanitized receipts, exact and estimated usage, failed-attempt retention,
and retry accounting.

## Next Transport Work

The adverse-media verifier is the first direct standalone research client to
complete this migration. The next maintainer should inventory and migrate one
remaining direct caller per reviewable change, then decide how package and
application adapters should accept an injectable ledger. Notebook runtimes need
a portable equivalent because Kaggle cannot share the local SQLite file. Keep
those migrations separate from benchmark result lanes, and do not describe the
current two-surface guard as a repository-wide network interceptor.
