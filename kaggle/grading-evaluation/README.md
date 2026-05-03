# Duecare Grading Evaluation (A6)

Side-by-side rubric evaluation: runs N curated prompts through Gemma 4
twice each — once with the harness OFF, once with full harness ON
(Persona + GREP + RAG + Tools) — and grades both with the universal
v2 grader. Produces the falsifiable headline lift number with
per-prompt + per-dimension detail.

## What it produces

1. **`duecare_lift_eval.json`** — full per-prompt detail (responses,
   grades, lift deltas, intents, citations) + provenance tuple
2. **`duecare_lift_eval.md`** — human-readable Markdown report ready
   for inclusion in `docs/harness_lift_report.md` or the writeup
3. **Inline notebook output** — the Markdown report renders directly
   in Kaggle's saved-output viewer

## Headline metrics it computes

- Mean rubric score (universal v2): OFF vs ON, delta in percentage
  points
- Per-dimension status change across the test set (improved / same
  / regressed)
- Citation grounding %: how many cited statutes appear in our
  bundled 26-doc RAG corpus (hallucination check)
- Mean cited statutes per response: OFF vs ON
- Intent shift: which intent the response moves toward when the
  harness is enabled
- Helped / Unchanged / Hurt counts (the "100% of prompts saw the
  harness help" story)

## Test set

By default, runs **5 textbook-shape prompts**:
- `textbook_loan_68pct` — compound 68%-APR + novation scenario
- `textbook_loan_18pct` — compound 18%-loan + salary deduction
- `traf_002` — passport "safekeeping"
- `traf_009` — 3-month "performance guarantee"
- `traf_001` — employer-pays-tax framing

Override with `DUECARE_EVAL_PROMPT_IDS=traf_005,traf_007,...` env var
to run a different subset.

## Required resources

- **GPU:** T4 (`enable_gpu: true`)
- **Internet:** required to download Gemma 4 weights (`enable_internet: true`)
- **HF_TOKEN:** set as a Kaggle Secret if you want to pull gated
  Gemma 4 variants
- **Runtime:** ~15 min for 5 prompts × 2 conditions on T4 (Gemma
  generation is the bottleneck; grading takes <100ms per response)

## Reproducibility

Every report includes a provenance tuple
`(model_name, git_sha, dataset_version)`. Re-run from the same git
SHA + dataset version to reproduce the numbers exactly. The
universal grader is deterministic (keyword + regex matching); only
Gemma generation has stochasticity (controlled by `temperature` and
`top_p` in the kernel).

## Architecture

This notebook is **NOT a chat playground** — it's the dedicated
EVALUATION harness. Compare with:
- `duecare-chat-playground` — interactive raw Gemma 4 chat (no
  harness)
- `duecare-chat-playground-with-grep-rag-tools` — interactive chat
  with toggleable harness
- `duecare-grading-evaluation` (this one) — end-to-end automated
  OFF-vs-ON comparison with reports

## Kaggle URL

https://www.kaggle.com/code/taylorsamarel/duecare-grading-evaluation
