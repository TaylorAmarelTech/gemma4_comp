# Model-failure study — funded-run readiness (preflight before turning on OpenRouter credit)

> Question this answers: *"Is everything ready for me to turn credits on?"* and
> *"Do we have a clear pipeline, report template, mid-investigation checkpoints,
> validation, so we can test this via OpenRouter and more advanced LLMs?"*
>
> **Verdict: YES — the machine is built, wired, and proven end-to-end on the free
> Ollama-cloud provider. Turning on OpenRouter credit changes ONE flag
> (`--provider openrouter`); nothing else in the pipeline changes.** Compiled 2026-06-08.

## 1. One-command run after you fund the key

```bash
set -a; . ./.env; set +a                                   # OPENROUTER_API_KEY now funded
PY="$LOCALAPPDATA/gemma4-testenv/venv/Scripts/python.exe"

# Dry-run first (zero spend) -- confirms the key is live + shows the plan:
"$PY" scripts/model_failure_loop.py --provider openrouter --dry-run

# Then the real frontier run (generation + judge + report, self-healing):
"$PY" scripts/model_failure_loop.py --provider openrouter --run-tag frontier \
  --include-seeds --limit 160 --gen-quota 160 --judge-model anthropic/claude-3.7-sonnet
```

That is the entire operator action. The loop probes the key, generates across the
frontier roster, judges one dimension per call, validates coverage, self-heals
transient errors, and renders the report — checkpointing after every stage.

## 2. Readiness checklist (with evidence)

| # | Requirement | Status | Evidence |
|---|---|---|---|
| 1 | **Clear pipeline** (one command, all stages) | READY | `scripts/model_failure_loop.py`: preflight → generate → validate → judge → validate → report. `py_compile` clean. |
| 2 | **Provider-switchable to OpenRouter / advanced LLMs** | READY | `--provider auto\|ollama\|openrouter`; `auto` probed OpenRouter (401, no credit) → fell back to Ollama-cloud (live) automatically. One flag to switch. |
| 3 | **Report template** | READY | `docs/research/model_failure_report_TEMPLATE.md` (annotated) + `model_failure_report.py` auto-renders §2–6. |
| 4 | **Report methodology** | READY | `docs/research/model_failure_study_methodology.md` — RQs, roster, two-layer grading, cost model, §7 turnkey run plan. |
| 5 | **Mid-investigation checkpoints** | READY | `loop_state_<tag>.json` written after EVERY stage; report re-rendered each round → a current artifact always exists mid-run. |
| 6 | **Validation gates** | READY | preflight provider probe (abort if no live provider); validate-gen (abort on zero responses, list below-quota models); validate-judge (coverage %, ERROR/UNPARSED count). |
| 7 | **Self-healing / no-error loop** | READY | ERROR/UNPARSED verdicts auto-retried next round (`_done` excludes non-final); generation `--retry-errors`; loop-until-dry stop when no progress. |
| 8 | **Judge integrity** | READY | One dimension per judge call (per project rule — never batched). Cross-family judge for the funded run (Claude judging the open/frontier roster). |
| 9 | **Robust verdict parsing** | READY | `parse_verdict` takes the LAST valid JSON object (after reasoning) — unit-tested incl. the "PARTIAL-mentioned-first but answer FAIL" trap. Fixes a real misclassification that would have corrupted frontier verdicts. |
| 10 | **Reproducibility** | READY | `git_sha` + provider + models + judge recorded in every checkpoint; temp 0; full responses stored (no truncation); synthetic probes only (no PII). |
| 11 | **End-to-end PROOF on free provider** | DONE | The free Ollama-cloud run judged the 120-response pilot set with `gemma4:31b` (zero UNPARSED/ERROR) and rendered the full two-layer report — see `model_failure_on_human_exploitation.md`. |

## 3. What the free-provider proof demonstrated

Running the identical loop on Ollama-cloud (no funded key) end-to-end proved every
moving part **before** any spend:

- Provider auto-resolution works (OpenRouter dead → Ollama live, logged).
- The judge produces clean per-dimension verdicts (PASS/FAIL/PARTIAL, 0 UNPARSED).
- The differentiated distribution (not all-PARTIAL) confirmed the hardened parser; an
  earlier reasoning-model judge had collapsed everything to PARTIAL via a parse bug —
  caught and fixed here, which is exactly the kind of failure you do NOT want to
  discover *after* paying for frontier generation.
- The two-layer report (deterministic screen + LLM-judge table) renders.

So the funded run is not a first attempt — it is the same proven loop pointed at a
better roster and a stronger (cross-family) judge.

## 4. Cost when you fund (from the measured cost model)

~760 tokens/call generation. With the frontier roster (~7 models) + a Claude
per-dimension judge over ~160 prompts/model: generation ≈ $15–30, judge ≈ $20–40,
optional DueCare-harnessed arm ≈ $10–20 → a publishable report well within **$100**,
with headroom. Deterministic grading is free. See methodology §6 for the table.

## 5. What changes vs. the free proof (be explicit)

- **Roster:** open-weight models → closed frontier (GPT-4o/4.1, Claude 3.7/3.5,
  Gemini 2.5 Pro) + cheap anchors.
- **Judge:** `gemma4:31b` (fast proof judge, self-judges its own rows) → cross-family
  `anthropic/claude-3.7-sonnet` (the scientifically preferred independent judge).
- **Throughput:** Ollama-cloud serialises (slow but free) → OpenRouter parallelises
  (faster, billed). `--workers` already set.
- **Nothing else** — same prompts, same dimensions, same grading, same report.

## 6. Residual caveats (honest)

- The funded run's verdicts are only as good as the judge; we report the judge model
  and use a cross-family judge to limit self-preference bias.
- Model versions drift — the run is pinned + dated in the checkpoint header.
- The DueCare-harnessed arm (the lift number) is the highest-value add; budget for it
  explicitly or label it deferred in the report (§5 of the template forbids implying
  it ran when it didn't).
