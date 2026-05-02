# Results & provenance

> **What this file is.** Every headline metric in the writeup, video,
> and Kaggle notebooks is reproduced here against the exact `(git_sha,
> dataset_version, model_revision)` tuple it was measured on. If a
> number can't be re-computed from this table, it doesn't get used in
> the submission.
>
> Per `.claude/rules/00_overarching_goals.md` rule 3:
> *"Real, not faked" is an enforced invariant.*

## Submission version

| Field | Value |
|---|---|
| **Submission tag** | `v0.1.0` (bumped on submission day, on or before 2026-05-18) |
| **Submission SHA** | set at tag time — verify with `git rev-parse v0.1.0` |
| **Submission date** | on or before 2026-05-18 |
| **Wheels built** | `dist/duecare_llm_*-0.1.0-py3-none-any.whl` (17 wheels — full inventory in `docs/current_kaggle_notebook_state.md`) |

## Headline metrics — harness lift (the central claim)

The numbers below are reproduced verbatim from
[`docs/harness_lift_report.md`](./docs/harness_lift_report.md), which
benchmarked Gemma 4 with the harness OFF vs ON across 207 hand-graded
prompts on the `legal_citation_quality` rubric (12 criteria across 3
user-facing dimensions: jurisdiction-specific rules, ILO/international
regulations, substance-over-form analysis).

| Dimension | n criteria | OFF mean | ON mean | **Lift** |
|---|---:|---:|---:|---:|
| Jurisdiction-specific rules | 4 | 0.4% | **87.8%** | **+87.5 pp** |
| ILO / international regulations | 4 | 0.1% | **51.3%** | **+51.2 pp** |
| Substance-over-form analysis | 4 | 0.8% | **34.8%** | **+34.1 pp** |

| Aggregate metric | Value |
|---|---|
| Prompts compared | 207 |
| Mean score, harness OFF | 0.5% |
| Mean score, harness ON | **56.9%** |
| **Mean lift** | **+56.5 pp** |
| Median lift | +53.3 pp |
| Max single-prompt lift | +95.6 pp |
| Min single-prompt lift | +15.6 pp |
| Prompts where harness helped | **207 / 207 (100%)** |
| Prompts where harness hurt | 0 / 207 |

**Per category:**

| Category | n | OFF mean | ON mean | Lift |
|---|---:|---:|---:|---:|
| amplification_known_attacks | 78 | 0.9% | 64.8% | +63.9 pp |
| financial_crime_blindness | 25 | 0.0% | 49.7% | +49.7 pp |
| jurisdictional_hierarchy | 55 | 0.3% | 57.5% | +57.1 pp |
| victim_revictimization | 49 | 0.2% | 47.4% | +47.3 pp |

**Source notebook:** the harness-lift report draws from notebook 130
(distilled scoring) and notebook 140 (evaluation mechanics). See
`docs/harness_lift_report.md` for the full methodology, layer-ablation
appendix (GREP-only / RAG-only / Both), refusal-rate appendix, and
per-prompt top/bottom-25 tables.

## Headline metrics — fine-tune lift (Phase 3)

The fine-tune track (Unsloth SFT + DPO via notebook A2 / `bench-and-tune`)
is end-to-end runnable. Final numbers + HF Hub revisions land at the
moment a successful T4×2 run completes on Kaggle. Until then:

| Metric | Number | Status |
|---|---|---|
| Stock Gemma 4 E4B refusal rate on harmful prompts | pending T4×2 run | scheduled — script ready in `kaggle/bench-and-tune/kernel.py` |
| SFT refusal rate uplift vs stock | pending T4×2 run | scheduled — Unsloth LoRA on harness-distilled pairs |
| DPO refusal rate uplift vs SFT | pending T4×2 run | scheduled — chosen / rejected pairs from grading rubric |
| Gemma 4 E4B vs GPT-OSS-20B on smoke_25 | pending notebook 210 push | notebook built |
| Gemma 4 E4B vs Mistral 8x22B on smoke_25 | pending notebook 230 push | notebook built |
| Cross-domain proof (trafficking + tax_evasion + financial_crime) | pending notebook 200 push | notebook built |
| End-to-end safety-harness latency (E4B, T4 ×2) | pending live-demo run | notebook built |
| Audit trail completeness | 100% by construction (every decision logged via `duecare.observability`) | implementation-verified, end-to-end test pending |

When the fine-tune runs land, this section will gain the same
`(notebook, dataset version, HF revision)` columns as the harness-lift
section above.

## How to reproduce

### From the GitHub repo

```bash
git checkout v0.1.0                   # pin to the submission SHA
make build                            # rebuild all 17 wheels into dist/
make test                             # run the 194-test suite
python scripts/run_local_gemma.py --max-prompts 10   # 10-prompt sanity check via Ollama
```

### From a Kaggle notebook

1. Open the relevant notebook from the table above.
2. Open the **Save Versions** dropdown → confirm the version pinned to
   `v0.1.0` is the one that produced the headline number.
3. Click **Run All**. Numbers appear in the same cells linked from the
   writeup.

### From the HF Hub model

```python
from unsloth import FastModel
model, tokenizer = FastModel.from_pretrained(
    "taylorscottamarel/Duecare-Gemma-4-E4B-it-SafetyJudge-v0.1.0",
    revision="main",  # or pin to the SHA listed in the table
    max_seq_length=4096,
)
```

## What is NOT in this table

- **Anecdotal demo runs.** A judge running the live demo with their own
  prompts produces fresh numbers — those don't go in this table because
  they aren't reproducible. The live-demo Kaggle URL is itself the
  reproducibility artifact for those.
- **Numbers from the 76-notebook research pipeline that aren't headline.**
  Each notebook prints its own per-run summary; they're tracked but not
  in this top-level table.
- **Skunkworks (jailbreak) numbers.** Those live in
  [`skunkworks/`](./skunkworks/) and are explicitly outside the safety-
  harness story.

## When this file changes

Update RESULTS.md whenever:

- A headline number is re-measured against a different
  `(git_sha, dataset_version, model_revision)`.
- A new headline number is added to the writeup or video.
- A model revision on HF Hub is bumped.

Don't update RESULTS.md for:

- Internal metric tracking (use the per-notebook output for that).
- Skunkworks experiments.
- Pre-submission iteration on numbers; only update when the submitted
  version of the writeup/video changes.
