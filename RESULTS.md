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
| **Submission snapshot** | commit `d3ab6588` — the last commit of the 2026-05-18 submission window. No release tag was cut; verify with `git log --until=2026-05-19 -1 --format="%h %ad %s" --date=short` |
| **Headline-number pin** | the A-00 smoke matrix below is pinned by its Kaggle run id (`e2b-full-train-eval`) and the kernel's exported artifact bundle, not by a git SHA |
| **Submission date** | on or before 2026-05-18 |
| **Wheels built** | `dist/duecare_llm_*-0.1.0-py3-none-any.whl` (17 wheels — full inventory in `docs/current_kaggle_notebook_state.md`) |

## Headline metrics — A-00 four-arm smoke matrix (2026-05-18)

These are the four numbers quoted in the video voiceover, the writeup's
evaluation section, and the README headline. It is a smoke run, not a
final benchmark — exactly as the writeup labels it.

| Arm | Score |
|---|---:|
| Stock Gemma 4 2B | 29.5% |
| Stock + chat-offline harness | **35.6%** |
| Fine-tuned | 26.4% |
| Fine-tuned + harness | **41.2%** |

Deltas: harness **+6.1 pp** over stock; fine-tuned + harness **+14.8 pp**
over fine-tuning alone and **+11.7 pp** over stock. Fine-tuning alone
dipped below stock because the small 2B fine-tune traded factual recall
for refusal shape — the expected pattern, and exactly the gap the
harness closes.

| Provenance field | Value |
|---|---|
| Kernel | **DueCare Fine-tuning and Evaluation** (`kaggle/A-00-omni-experiment-workbench/kernel.py`) |
| Run id | `e2b-full-train-eval` (2026-05-18) |
| Model | Gemma 4 E2B — the run id's `e2b`; the video shorthand is "stock Gemma 4" |
| Judge | combined rule + LLM judging (same primitives as Kernel 01: `grade_response_combined` / `grade_response_universal`) |
| Artifacts | A-00 report, CSV, JSON, and manifest bundle exported under `/kaggle/working` |

Guard: `tests/test_doc_count_drift.py` asserts these four arm scores stay
identical between this file and `docs/writeup_draft.md`.

## Headline metrics — harness lift (the central claim)

The numbers below are reproduced verbatim from
[`docs/harness_lift_report.md`](./docs/harness_lift_report.md), which
benchmarked Gemma 4 with the harness OFF vs ON across 207 hand-graded
prompts on the `legal_citation_quality` rubric (12 criteria across 3
user-facing dimensions: jurisdiction-specific rules, ILO/international
regulations, substance-over-form analysis).

| Dimension | n criteria | OFF mean | ON mean | **Lift** |
|---|---:|---:|---:|---:|
| Jurisdiction-specific rules | 4 | 0.4% | **74.2%** | **+73.8 pp** |
| ILO / international regulations | 4 | 0.1% | **55.6%** | **+55.4 pp** |
| Substance-over-form analysis | 4 | 0.8% | **22.0%** | **+21.2 pp** |

| Aggregate metric | Value |
|---|---|
| Prompts compared | 207 |
| Mean score, harness OFF | 0.5% |
| Mean score, harness ON | **51.9%** |
| **Mean lift** | **+51.4 pp** |
| Median lift | +53.5 pp |
| Max single-prompt lift | +91.1 pp |
| Min single-prompt lift | -10.0 pp |
| Prompts where harness helped | **206 / 207 (99%)** |
| Prompts where harness hurt | 1 / 207 |

> **Caveat:** these are proxy/regression figures measured on the checked-in
> response set, not a live multi-hour Gemma run. See
> `docs/harness_lift_report.md` for the full scope caveat and methodology.
> A separate, independently-judged paired-score benchmark (gpt-oss:120b judge,
> 911 prompts) is reported in `docs/research/harness_lift_report.md`:
> gemma4:31b **+1.73 / 10** mean paired lift, 95% CI [+1.57, +1.89], 73.3% win rate.

**Per category:**

| Category | n | OFF mean | ON mean | Lift |
|---|---:|---:|---:|---:|
| amplification_known_attacks | 78 | 1.0% | 54.5% | +53.5 pp |
| financial_crime_blindness | 25 | 0.0% | 47.8% | +47.8 pp |
| jurisdictional_hierarchy | 55 | 0.4% | 62.5% | +62.1 pp |
| victim_revictimization | 49 | 0.2% | 38.1% | +37.8 pp |

**Source notebook:** the harness-lift report draws from notebook 130
(distilled scoring) and notebook 140 (evaluation mechanics). See
`docs/harness_lift_report.md` for the full methodology, layer-ablation
appendix (GREP-only / RAG-only / Both), refusal-rate appendix, and
per-prompt top/bottom-25 tables.

## Fine-tune lift

The measured fine-tune result is the A-00 four-arm smoke matrix at the
top of this file (fine-tuned + harness 41.2% vs stock 29.5%). The
training path is Unsloth LoRA SFT inside the A-00 kernel
(`_create_training_job` → `FastModel.get_peft_model` → `SFTTrainer`).

| Metric | Number | Status |
|---|---|---|
| Four-arm smoke matrix (stock / +harness / fine-tuned / fine-tuned+harness) | 29.5% / 35.6% / 26.4% / 41.2% | measured 2026-05-18, run `e2b-full-train-eval` |
| Audit trail completeness | 100% by construction (every decision logged via `duecare.observability`) | implementation-verified, end-to-end test pending |

### Future work (not yet measured)

These do NOT appear in the writeup or video; they are listed so the
boundary between measured and planned stays explicit:

- Head-to-head smoke comparisons vs GPT-OSS-20B and Mistral-class models
  (`kaggle/03-universal-llm-benchmark` accepts any OpenAI-compatible
  endpoints for this).
- Cross-domain proof (trafficking + tax_evasion + financial_crime) in one run.
- End-to-end safety-harness latency on T4 ×2.
- DiffusionGemma fast-tier throughput for the triage harness
  (`docs/diffusiongemma_fast_tier.md`).

## How to reproduce

### From the GitHub repo

```bash
git checkout d3ab6588                 # last submission-window commit (2026-05-18); HEAD also works
make build                            # rebuild all 17 wheels into dist/
make test                             # full package + top-level suite (1,877 pass / 2 skip as of 2026-06-10)
python scripts/run_local_gemma.py --max-prompts 10   # 10-prompt sanity check via Ollama
```

### From a Kaggle notebook

1. Open the relevant notebook from the table above.
2. Open the **Save Versions** dropdown → pick the version saved on or
   before 2026-05-18 (the run that produced the headline number).
3. Click **Run All**. Numbers appear in the same cells linked from the
   writeup.

### From the HF Hub model

```python
from unsloth import FastModel
model, tokenizer = FastModel.from_pretrained(
    "TaylorScottAmarel/duecare-gemma-4-e4b-safetyjudge",  # the published repo id
    max_seq_length=4096,
)
```

## What is NOT in this table

- **Anecdotal demo runs.** A judge running the live demo with their own
  prompts produces fresh numbers — those don't go in this table because
  they aren't reproducible. The live-demo Kaggle URL is itself the
  reproducibility artifact for those.
- **Numbers from archived research notebooks.** Pre-submission research
  surfaces print their own per-run summaries; they are historical, not
  headline material.
- **Red-team (jailbreak) numbers.** Those live in archived research
  folders outside the public tree and are explicitly outside the
  safety-harness story.

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
