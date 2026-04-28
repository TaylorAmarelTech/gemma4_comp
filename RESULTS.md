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
| **Submission tag** | `v0.1.0` (TBD — bump on submission day) |
| **Submission SHA** | `(set at tag time — `git rev-parse v0.1.0`)` |
| **Submission date** | TBD (≤ 2026-05-18) |
| **Wheels built** | `dist/duecare_llm_*-0.1.0-py3-none-any.whl` (17 wheels) |

## Headline metrics

Each row is a number that appears in either the writeup or video.
Verifier columns: `Source notebook` (Kaggle URL), `Dataset version`
(Kaggle dataset version pin), `HF model revision` (HF Hub revision).

| Metric | Number | Source notebook | Dataset version | HF model revision |
|---|---|---|---|---|
| Stock Gemma 4 E4B refusal rate on harmful prompts | TBD | [100 — Gemma Exploration](https://www.kaggle.com/code/taylorsamarel/duecare-real-gemma-4-on-50-trafficking-prompts) | `duecare-trafficking-prompts/v?` | `google/gemma-4-e4b-it@main` |
| SFT refusal rate uplift vs stock | TBD | bench-and-tune (TBD URL) | `duecare-trafficking-prompts/v?` | `taylorscottamarel/Duecare-Gemma-4-E4B-it-SafetyJudge-v0.1.0@main` |
| DPO refusal rate uplift vs SFT | TBD | bench-and-tune (TBD URL) | `duecare-trafficking-prompts/v?` | `taylorscottamarel/Duecare-Gemma-4-E4B-it-SafetyJudge-DPO-v0.1.0@main` |
| Gemma 4 E4B vs GPT-OSS-20B on the smoke_25 set | TBD | [210 — OSS Model Comparison](https://www.kaggle.com/code/taylorsamarel/duecare-210-oss-model-comparison) | smoke_25 (in-wheel) | n/a |
| Gemma 4 E4B vs Mistral 8x22B on the smoke_25 set | TBD | [230 — Mistral Family Comparison](https://www.kaggle.com/code/taylorsamarel/duecare-230-mistral-family-comparison) | smoke_25 (in-wheel) | n/a |
| Cross-domain proof (trafficking + tax_evasion + financial_crime) | TBD | [200 — Cross-Domain Proof](https://www.kaggle.com/code/taylorsamarel/duecare-200-cross-domain-proof) | bundled YAML packs | `google/gemma-4-e4b-it@main` |
| End-to-end safety harness latency (E4B, T4 ×2) | TBD | [Live demo](https://www.kaggle.com/code/taylorsamarel/duecare-live-demo) | `duecare-llm-wheels/v?` | `google/gemma-4-e4b-it@main` |
| Audit trail completeness (% of decisions with full provenance) | TBD | [Live demo](https://www.kaggle.com/code/taylorsamarel/duecare-live-demo) | `duecare-llm-wheels/v?` | n/a |

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
