# DueCare — Runtime harness-lift regenerator (#A11 appendix)
<!-- duecare:lane-label -->
> **Serves lanes:** 04 Researcher

<!-- duecare:judge-quick-path -->

## Judge quick path

| Section | This notebook |
|---|---|
| **Lede** | Falsifiable harness-lift regenerator that reruns prompts with the harness off and on, then grades the delta. |
| **What it does** | Produces per-prompt and per-dimension scorecards for the same Gemma weights with DueCare runtime layers off versus on. |
| **Demo path** | Run a small prompt set, open the lift dashboard, scan the KPI cards, and download the JSON/Markdown/CSV artifacts. |
| **Audience** | Researcher. |
| **Outputs** | `duecare_lift_eval.json`, `duecare_lift_eval.md`, CSV export, inline report, and dashboard scorecards. |
| **Cross-links** | Use the quick links at the bottom for the full workbench, live demo, fine-tune pipeline, and public website. |

Side-by-side rubric evaluation: runs N curated prompts through the same
Gemma 4 weights twice each — once with the harness OFF, once with full
harness ON (Persona + GREP + RAG + Tools) — and grades both with the
Rule-Based v2 grader. Produces the falsifiable headline lift number with
per-prompt + per-dimension detail.

This notebook **does not train a model** and **does not compare stock
weights against fine-tuned weights**. For stock-vs-SafetyJudge-adapter
benchmarking, use A7 and its `eval_results.json`. A11 answers a different
question: how much the runtime harness helps when weights are held
constant.

| Field | Value |
|---|---|
| **Status** | Appendix evaluation kernel; public-ready metadata; manual Kaggle publication only |
| **Kernel type** | Script kernel by design (`kernel.py` is the source of truth) |
| **Kaggle URL** | https://www.kaggle.com/code/taylorsamarel/duecare-grading-evaluation |
| **Wheels dataset** | `taylorsamarel/duecare-grading-evaluation-wheels` |
| **Models attached** | Gemma 4 E2B / E4B / 26B-A4B / 31B metadata declared; kernel can also download by `DUECARE_MODEL_NAME` with `HF_TOKEN` |
| **GPU** | T4 |
| **Internet** | Required for runtime model download when not using attached weights |

## What it produces

1. **`duecare_lift_eval.json`** — full per-prompt detail (responses,
   grades, lift deltas, intents, citations) + provenance tuple
2. **`duecare_lift_eval.md`** — human-readable Markdown report ready
   for inclusion in `docs/harness_lift_report.md` or the writeup
3. **Inline notebook output** — the Markdown report renders directly
   in Kaggle's saved-output viewer

## Headline metrics it computes

- Mean rubric score (Rule-Based v3.10): OFF vs ON, delta in percentage
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
Rule-Based grader is deterministic (keyword + regex matching); only
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

## Files in this folder

```text
grading-evaluation/
├── kernel.py            ← source-of-truth script kernel
├── kernel-metadata.json ← Kaggle metadata; public-ready, script kernel
├── README.md            ← this file
└── wheels/              ← local wheels for manual Kaggle dataset upload
```

## Publishing

Do not auto-publish this kernel. Taylor performs the final Kaggle UI / CLI
push manually after checking the public links and attached wheel dataset.
This README intentionally documents the script-kernel shape because A-11 is
an automated evaluator, not an interactive notebook UI.

---

<!-- duecare:quick-cross-links -->

### Quick cross-links

- **Core workbench:** [#01 core: Migrant-worker safety playground](../01-duecare-exploration-workbench/README.md).
- **Focused live demo:** [#02 core: Live demo](../02-live-demo/README.md).
- **Natural next appendix:** [#A07 appendix: Adapter training + new-model benchmark](../A-07-bench-and-tune/README.md).
- **Public website:** [duecare-ai.com](https://duecare-ai.com).

---

<!-- duecare:kernel-footer -->

### All DueCare kernels

You are here: **#A11 appendix — Runtime harness-lift regenerator**.

- [#01 core: Migrant-worker safety playground](../01-duecare-exploration-workbench/README.md)
- [#02 core: Live demo (focused walkthrough)](../02-live-demo/README.md)
- [#A01 appendix: Stock Gemma 4 chat baseline](../A-01-chat-playground/README.md)
- [#A02 appendix: Harness ablation runner](../A-02-chat-playground-with-grep-rag-tools/README.md)
- [#A03 appendix: Hands-on classification sandbox](../A-03-content-classification-playground/README.md)
- [#A04 appendix: Knowledge-builder sandbox + JSON export](../A-04-content-knowledge-builder-playground/README.md)
- [#A05 appendix: NGO classifier evaluation dashboard](../A-05-gemma-content-classification-evaluation/README.md)
- [#A06 appendix: Two-track synthetic data generator](../A-06-prompt-generation/README.md)
- [#A07 appendix: Adapter training + new-model benchmark](../A-07-bench-and-tune/README.md)
- [#A08 appendix: Research graphs (CPU-only)](../A-08-research-graphs/README.md)
- [#A09 appendix: Agentic-research chat (BYOK + Playwright)](../A-09-chat-playground-with-agentic-research/README.md)
- [#A10 appendix: Jailbroken-Gemma comparison](../A-10-chat-playground-jailbroken-models/README.md)
- **[#A11 appendix: Runtime harness-lift regenerator](../A-11-grading-evaluation/README.md)**

Index page: [`kaggle/_INDEX.md`](../_INDEX.md).

---

## Cross-links

- **[DueCare Exploration Workbench (#01)](https://www.kaggle.com/code/taylorsamarel/duecare-exploration-workbench)** -- the full chat playground with all 6 harness layers, 9-variant model picker, 4 grading modes, A/B compare, and every visualization in one place.
- **[Live demo (#02)](https://www.kaggle.com/code/taylorsamarel/duecare-live-demo)** -- focused public-hub walkthrough demonstrating the +56.5pp lift on a curated set of compound-indicator prompts.
- **[Next step -> DueCare Exploration Workbench (#01)](https://www.kaggle.com/code/taylorsamarel/duecare-exploration-workbench)** -- open the live workbench Grade panel to score any prompt + response interactively.
- **[Public hub: duecare-ai.com](https://duecare-ai.com)** -- knowledge-pack registry, anonymized signal intake, public-source proposal intake, and the 5-lane audience showcase.
