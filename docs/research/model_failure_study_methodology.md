# Model-failure study — methodology & run plan

> Design for a rigorous, reproducible study of how LLMs handle human-exploitation
> / trafficking prompts, and how much the DueCare harness closes the gap. This doc
> is the spec; `scripts/model_failure_study.py` (generation), `scripts/model_failure_judge.py`
> (LLM judge), and `scripts/model_failure_report.py` (aggregation) are the
> implementation. Everything here is wired and validated on a 12-model open-roster
> pilot; the only thing gating the full run is a working frontier key (see §7).

## 1. Research questions

- **RQ1 (recognition):** At baseline (no harness), do models recognise exploitation
  framings as problematic?
- **RQ2 (grounding):** Do they *ground* the answer in the specific framework — debt
  bondage, kafala, recruitment-fee rules, ILO conventions — or stop at "this seems
  wrong"?
- **RQ3 (equivocation resistance):** Can a benign-domain analogy ("a worker bond is
  basically a financial instrument", "I'm just the sponsor, like sponsoring an
  event") launder an exploitative arrangement past the model?
- **RQ4 (harness lift):** How much does wrapping the same prompt in the DueCare
  harness (GREP + RAG + persona) change the answer?

## 2. What the pilot already showed (and why this design)

Pilot: 12 frontier-class open models (Ollama-cloud) × 10 equivocation probes =
120 responses, deterministic grading. Result: **99% did-not-resolve** the
trafficking sense (PARTIAL+FAIL), but **~0% endorsed** it (1 FAIL, and that one was
a grader false-positive — a good answer that *quoted* "safekeeping" to debunk it),
and only **1/108 fully resolved** (PASS).

Two lessons baked into this design:
1. **The honest finding is RQ2, not "models endorse exploitation".** Models broadly
   recognise the problem (good) but rarely ground it (the gap DueCare fills). The
   report must say this, not overclaim.
2. **A deterministic keyword grader is a screen, not a verdict.** It false-FAILs
   euphemism-debunking and can't separate "vaguely correct" from "properly
   grounded". **A definitive cross-model comparison requires an independent LLM
   judge** (§5). This is the single biggest reason to spend the budget.

## 3. Models (roster)

Two pools, judged identically:

- **Open / open-weight (Ollama-cloud, working today):** deepseek-v3.2,
  deepseek-v4-flash, qwen3-next:80b, glm-4.6, glm-5, kimi-k2.5, minimax-m2,
  mistral-large-3:675b, nemotron-3-super, cogito-2.1:671b, gemini-3-flash-preview,
  gemma4:31b. (gpt-oss excluded — returns empty content via the API.)
- **Closed frontier (OpenRouter, needs a funded key — the $100):** openai/gpt-4o,
  openai/gpt-4.1, anthropic/claude-3.7-sonnet, anthropic/claude-3.5-sonnet,
  google/gemini-2.5-pro, plus cheaper anchors (gpt-4o-mini, claude-3.5-haiku).

Gemma 4 (gemma4:31b) is included as the project's reference model — **not** as the
DueCare fine-tune; the DueCare harness arm (§4) is the product comparison.

## 4. Prompts & arms

- **Prompt corpus:** the 10 equivocation probes
  (`configs/duecare/domains/trafficking/ambiguity_probes.jsonl`) + a **stratified
  sample of the seed benchmark** (`seed_prompts.jsonl`), balanced across categories:
  business-framed exploitation, victim-voice, adversarial-recruiter, definitional.
  Target **~150 prompts/model** (the budget supports far more — see §6).
- **Arm A — baseline:** raw prompt, neutral "helpful assistant" system message,
  temperature 0. Measures the model's own behaviour.
- **Arm B — DueCare-harnessed (the lift):** same prompt wrapped with the DueCare
  GREP + RAG + persona harness before the model call. Run on a subset of models to
  quantify the lift. (Build: reuse `duecare.chat.harnesses.default_harness`.)

## 5. Grading — two layers

1. **Deterministic screen (free, fast):** `duecare.chat.harness.grade_response_universal`
   — every response, every dimension. Good for triage + the `domain_sense_resolution`
   signal. Known to be keyword-noisy; reported with caveats, never as the verdict.
2. **Independent LLM judge (the definitive measure):** `scripts/model_failure_judge.py`.
   - **One dimension per judge call** (per the project's per-dimension grading
     integrity rule — never batch dimensions into one call).
   - Judge dimensions: `sense_resolution`, `legal_grounding`, `harm_safety`,
     `actionability` (rubrics in the judge script).
   - **Judge model from a different family** than the model under test (reduce
     self-preference bias): e.g. judge open models with a frontier judge
     (Claude/GPT-4o) and frontier models with a second strong judge; report
     judge-model and note the bias control.
   - Temperature 0; structured PASS/PARTIAL/FAIL + one-line reason.

## 6. Cost model (measured)

Measured generation: **~760 tokens/call** (~60 in, ~700 out; cap 800). Deterministic
grading is free. With a 15-model roster, $100 buys (generation only):

| Roster | $/call | prompts per model within $100 |
|---|---|---|
| open/cheap | ~$0.0007 | ~9,500 |
| mixed | ~$0.004 | ~1,650 |
| all frontier-closed | ~$0.012 | ~550 |

So **prompts/model is not the constraint** — the prompt inventory and the LLM judge
are. With the judge: ~$0.02/prompt (cheap judge, key dims) → ~330 prompts/model;
~$0.15/prompt (frontier per-dimension judge) → ~45 prompts/model. **Recommended $100
allocation:** ~$15–30 generation across closed frontier models + ~$20–40 mid-tier
independent judge on key dimensions + the harnessed arm = a publishable report for
~$50–70, with headroom.

## 7. Run plan (turnkey)

```bash
set -a; . ./.env; set +a
PY="$LOCALAPPDATA/gemma4-testenv/venv/Scripts/python.exe"
export PYTHONPATH=$(ls -d packages/*/src | tr '\n' ';')

# (a) OPEN roster — works today (Ollama-cloud)
"$PY" scripts/model_failure_study.py \
  --base-url https://ollama.com/v1/chat/completions --key-env OLLAMA_API_KEY \
  --workers 8 --max-tokens 800 --include-seeds --limit 160 \
  --models "deepseek-v3.2,deepseek-v4-flash,qwen3-next:80b,glm-4.6,glm-5,kimi-k2.5,minimax-m2,mistral-large-3:675b,nemotron-3-super,cogito-2.1:671b,gemini-3-flash-preview,gemma4:31b" \
  --out reports/model_failure_study/open.jsonl

# (b) CLOSED frontier — after a funded OPENROUTER_API_KEY is in .env
"$PY" scripts/model_failure_study.py \
  --base-url https://openrouter.ai/api/v1/chat/completions --key-env OPENROUTER_API_KEY \
  --workers 8 --max-tokens 800 --include-seeds --limit 160 \
  --models "openai/gpt-4o,openai/gpt-4.1,anthropic/claude-3.7-sonnet,anthropic/claude-3.5-sonnet,google/gemini-2.5-pro,openai/gpt-4o-mini,anthropic/claude-3.5-haiku" \
  --out reports/model_failure_study/closed.jsonl

# (c) Independent LLM judge (one dimension per call) over both result sets
"$PY" scripts/model_failure_judge.py \
  --in reports/model_failure_study/open.jsonl reports/model_failure_study/closed.jsonl \
  --base-url https://openrouter.ai/api/v1/chat/completions --key-env OPENROUTER_API_KEY \
  --judge-model anthropic/claude-3.7-sonnet \
  --out reports/model_failure_study/judge.jsonl

# (d) Aggregate + render
"$PY" scripts/model_failure_report.py \
  --in reports/model_failure_study/open.jsonl reports/model_failure_study/closed.jsonl \
  --judge reports/model_failure_study/judge.jsonl \
  --out docs/research/model_failure_on_human_exploitation.md
```

## 8. Reproducibility & integrity

- Record `(git_sha, model_version, prompt_set_version)` in the results header; store
  every raw response (no truncation, per project rules).
- temperature 0 for both generation and judging; resumable (skip done pairs).
- Synthetic prompts only — no real PII (probes are composite).
- Report **confirmed findings separately from interpretation**; the deterministic
  screen is labelled a screen, the LLM judge is the verdict.

## 9. Limitations (state them in the report)

- Deterministic grader is keyword-noisy (false-FAIL on euphemism mention).
- LLM judge has its own biases → cross-family judge + report the judge model.
- Model versions drift; pin + date the run.
- Ollama-cloud serialises requests (~1–2 effective concurrency) → open-roster runs
  are slow but cheap; OpenRouter is faster but billed.
- Open vs closed pools use different endpoints; the judge normalises across them.

## 10. Report template

The final report (`model_failure_on_human_exploitation.md`, auto-rendered by
`model_failure_report.py`) follows: **(1)** scope + the read-before-tables caveat,
**(2)** per-model table (resolved / incomplete / endorsed / avg %, and — when a
judge file is supplied — judge PASS-rate per dimension), **(3)** per-probe and
per-category tables, **(4)** baseline-vs-harnessed lift, **(5)** method, **(6)**
limitations, **(7)** appendix of representative responses. The hand-written
executive summary leads with RQ2 (grounding), not an over-claimed "endorsement"
headline.
