# DueCare — Grading-lift regenerator (#A11 appendix)

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

- Mean rubric score (universal v3.10): OFF vs ON, delta in percentage
  points
- Per-dimension status change across the test set (improved / same
  / regressed)
- Citation grounding %: how many cited statutes appear in our
  bundled 46-doc RAG corpus (hallucination check)
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

---

<!-- duecare:kernel-footer -->

### All DueCare notebooks

You are here: **#A11 appendix — Grading-lift regenerator**.

- [#01 core: Migrant-worker safety playground](../01-duecare-harness-chat/README.md)
- [#02 core: Live demo (focused walkthrough)](../02-live-demo/README.md)
- [#A01 appendix: Stock Gemma 4 chat baseline](../A-01-chat-playground/README.md)
- [#A02 appendix: Original 4-toggle subset playground](../A-02-chat-playground-with-grep-rag-tools/README.md)
- [#A03 appendix: Hands-on classification sandbox](../A-03-content-classification-playground/README.md)
- [#A04 appendix: Knowledge-builder sandbox + JSON export](../A-04-content-knowledge-builder-playground/README.md)
- [#A05 appendix: NGO classifier evaluation dashboard](../A-05-gemma-content-classification-evaluation/README.md)
- [#A06 appendix: Gemma generates evaluation prompts](../A-06-prompt-generation/README.md)
- [#A07 appendix: Unsloth fine-tune + GGUF export pipeline](../A-07-bench-and-tune/README.md)
- [#A08 appendix: Research graphs (CPU-only)](../A-08-research-graphs/README.md)
- [#A09 appendix: Agentic-research chat (BYOK + Playwright)](../A-09-chat-playground-with-agentic-research/README.md)
- [#A10 appendix: Jailbroken-Gemma comparison](../A-10-chat-playground-jailbroken-models/README.md)
- **[#A11 appendix: Grading-lift regenerator](../A-11-grading-evaluation/README.md)**

Index page: [`kaggle/_INDEX.md`](../_INDEX.md).
