# Kimi K3 context-judge campaign readiness

**Status as of 2026-07-28: mechanically ready, externally access-blocked, and
not executed.** This is a preflight receipt, not a benchmark result.

The frozen campaign is
[`kimi_k3_500_context_judge_campaign.json`](../../configs/duecare/benchmarks/kimi_k3_500_context_judge_campaign.json).
It specifies one exact 500-prompt selection, three hosted lanes, a deterministic
cross-check, the context contract, provider rates, call/token/cash ceilings,
interpretation rules, and official provider sources.

## Exact study topology

| Phase | Calls | Role | Publication treatment |
|---|---:|---|---|
| Kimi K3 baseline answers | 500 | Candidate behavior without the DueCare harness | Model output, not a rating |
| DueCare deterministic grade | 0 hosted | Reproducible local cross-check on every successful answer | Conservative screen |
| Gemini 3.1 Pro contextual judge | 500 | Cross-family automated judge with the frozen DueCare context | Primary automated, directional |
| Kimi K3 contextual judge | 500 | Same-family self-critique over the same context and rubric | Secondary diagnostic only |
| Qualified human review | 0 planned here | Future independent adjudication of disagreements | Required before human-validation claims |

Total hosted-call ceiling: **1,500**. The frozen reservation is **7,296,582
input tokens**, **1,152,000 maximum output tokens**, and **US$34.448916
worst-case** at the rates checked on 2026-07-28. Use a **US$35 hard ceiling**;
this is a maximum reservation, not expected spend. Retries consume new attempt
budget.

The 500-prompt selection covers 117 categories with seed `20260728` and
selection SHA-256
`9d4aedf042f5f9d73e8372a8f1bf5538190d9791dbc692c38ca720aed1bc48eb`.
The real offline `duecare-full` context set has SHA-256
`109f18c68f7b09e193bc9e2a41b55628b9267fa2c73f10ab3fcb9fad098656db`.

## Current blockers

- Five separately authorized Kimi K3 access attempts reached Ollama and returned
  HTTP 402 because the account had no extra-usage balance. They produced zero
  completions, provider tokens, or actual cost.
- No `GEMINI_API_KEY` (or equivalent Google Gemini credential) is available in
  the project environment.
- The configured OpenRouter credential previously returned HTTP 401 and is not
  an authorized substitute.

Do not retry merely to clear a checklist. Execution begins only after the
billing owner funds Ollama extra usage, supplies a Gemini credential, rechecks
the official prices and model IDs, and creates one reviewed provider-budget
policy per authorized phase.

## Zero-call preflight

These commands need no provider credential, write no result file, and make no
network model call:

```powershell
python scripts/model_failure_study.py `
  --models kimi-k3 --include-seeds --limit 500 `
  --selection-mode category-balanced --selection-seed 20260728 `
  --max-tokens 768 `
  --out reports/model_failure_study/kimi_k3_directional_500.jsonl `
  --base-url https://ollama.com/v1/chat/completions `
  --key-env OLLAMA_API_KEY --max-planned-model-calls 500 --plan
```

The judge plans require successful candidate rows, so run them only after the
candidate phase exists:

```powershell
python scripts/model_failure_judge.py `
  --in reports/model_failure_study/kimi_k3_directional_500.jsonl `
  --out reports/model_failure_study/gemini_31_context_judge.jsonl `
  --base-url https://generativelanguage.googleapis.com/v1beta/openai/chat/completions `
  --key-env GEMINI_API_KEY --judge-model gemini-3.1-pro-preview `
  --context duecare-full --protocol holistic --response-byte-limit 6000 `
  --max-tokens 768 --planning-input-rate 2 --planning-output-rate 12 `
  --reasoning-effort low --json-mode --max-planned-model-calls 500 --plan

python scripts/model_failure_judge.py `
  --in reports/model_failure_study/kimi_k3_directional_500.jsonl `
  --out reports/model_failure_study/kimi_k3_context_self_judge.jsonl `
  --base-url https://ollama.com/v1/chat/completions `
  --key-env OLLAMA_API_KEY --judge-model kimi-k3 `
  --context duecare-full --protocol holistic --response-byte-limit 6000 `
  --max-tokens 768 --planning-input-rate 3 --planning-output-rate 15 `
  --max-planned-model-calls 500 --plan
```

Compare every plan to the frozen manifest. Any selection, context, call-count,
token, rate, or hash drift requires review before removing `--plan`.

## Execution and recovery contract

1. Follow [Provider Budgeting](../PROVIDER_BUDGETING.md) to set a stable run ID,
   reviewed pricing file, SQLite ledger, and finite attempt/input/output/cash
   caps for the current phase.
2. Execute candidate generation first. The JSONL appends completed results and
   supports a reviewed resume without repeating successful prompt/model pairs.
3. Re-run both judge commands with `--plan` against the actual answers. Actual
   answer lengths can change the reservation; do not rely only on the frozen
   conservative estimate.
4. Run Gemini and Kimi judge phases under separate run IDs and ledgers. Remove
   `--plan` only from the phase presently authorized.
5. Render one reconciled report with both files:

   ```powershell
   python scripts/model_failure_report.py `
     --in reports/model_failure_study/kimi_k3_directional_500.jsonl `
     --judge reports/model_failure_study/gemini_31_context_judge.jsonl `
             reports/model_failure_study/kimi_k3_context_self_judge.jsonl `
     --out reports/model_failure_study/kimi_k3_context_report.md
   ```

The renderer expands holistic dimension verdicts, keeps cross-family and
self-family panels separate, and reports deterministic/judge and
judge-to-judge exact agreement.

## What “ready” does and does not mean

Ready means the selection, context, prompts, parsing, hash-bound resume keys,
budget reservations, report reconciliation, and offline tests exist. It does
not mean provider access works, a Kimi answer exists, Gemini has judged
anything, a human has rated anything, or field effectiveness has been shown.

The economical one-call holistic protocol is a **directional pilot**. A later
publication-grade automated adjudication can use `--protocol per-dimension`,
which preserves one rubric dimension per provider call. That larger run must be
planned and funded separately; it is not hidden inside the 1,500-call ceiling.
