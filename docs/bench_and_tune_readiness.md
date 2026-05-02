# Bench-and-tune (A2) readiness checklist

> **When to use this doc.** When your Kaggle GPU quota resets and
> you're about to run the `bench-and-tune` notebook (A2) on T4×2.
> Walk through the checklist beforehand; it surfaces issues you
> can fix before burning compute.
>
> **Time budget.** ~30 min of pre-flight work; ~3-6 hours of GPU
> runtime for the actual fine-tune; ~30 min of post-run verification
> + HF Hub push.

## Pre-flight (do BEFORE consuming any GPU)

### 1. Verify the wheels dataset is current

The bench-and-tune notebook installs from a Kaggle wheels dataset.
Verify the dataset has the correct Unsloth + transformers + flash-attn
version pins:

```bash
# Locally
ls kaggle/bench-and-tune/wheels/ | grep -E "unsloth|transformers|flash"
# Expect:
#   unsloth-2024.X.X-py3-none-any.whl
#   transformers-4.46.X-py3-none-any.whl
#   flash_attn-2.X.X-...whl  (may need cu121 / cu124 variant)
```

If the wheels are stale or the version pins don't match Kaggle's
current CUDA / Python (3.11 typically), rebuild:

```bash
python scripts/build_kaggle_wheels.py --notebook bench-and-tune
```

Then re-push the wheels dataset to Kaggle. **Do NOT skip this step
— Unsloth + flash-attn versioning is the most common A2 failure mode.**

### 2. Verify the smoke_25 dataset is in the wheels

The notebook needs the 25-prompt smoke benchmark + the chosen/rejected
pairs for DPO. Both should be embedded in the wheels (not separate
attached datasets).

```bash
unzip -l kaggle/bench-and-tune/wheels/duecare_llm_benchmark-*.whl | grep -E "smoke_25|dpo_pairs"
# Expect 2-4 files
```

If missing, rebuild the benchmark wheel:

```bash
python -m build --wheel --outdir kaggle/bench-and-tune/wheels packages/duecare-llm-benchmark
```

### 3. Confirm HF token is configured for the push step

The A2 notebook's final cell pushes the fine-tuned weights to
`taylorscottamarel/Duecare-Gemma-4-E4B-it-SafetyJudge-v0.1.0`.

In Kaggle:
- Settings → Add-ons → Secrets → Add `HF_TOKEN` with **write
  scope** (read scope won't work for push)
- Verify the token's HF account has the namespace
  `taylorscottamarel/` write access

If the model repo doesn't exist yet:

```bash
# From your local terminal (not in Kaggle):
huggingface-cli repo create Duecare-Gemma-4-E4B-it-SafetyJudge-v0.1.0 \
  --type model \
  --organization taylorscottamarel
```

The notebook will populate it on push.

### 4. Pre-stage the model card

The fine-tuned weights need a model card for HF Hub. Pre-write
it locally so the notebook can just upload at the end:

```bash
# Write to packages/duecare-llm-publishing/model_cards/duecare-gemma-4-e4b-safetyjudge.md
```

Reference template content:
- Model description (Gemma 4 E4B + Duecare safety harness fine-tune)
- Training data (207 hand-graded prompts + harness-generated pairs)
- Intended use (NGO + regulator + worker safety; not a primary
  safety classifier)
- Limitations (English-bias, single-domain, etc.)
- Citation (point to `CITATION.cff`)
- Licensing (Apache 2.0 inherited from Gemma 4)

Even if numbers come from the run, the structure can land first.

### 5. Check disk space + runtime budget

Kaggle's T4×2 instance has:
- ~15 GB system RAM
- ~32 GB GPU memory (16 GB × 2)
- ~75 GB ephemeral disk
- 9-hour hard runtime cap

A2's expected footprint:
- Stock Gemma 4 E4B: ~3.5 GB on disk, ~12 GB GPU at FP16
- Unsloth LoRA training: ~2 GB extra GPU
- DPO step: ~2 GB extra GPU
- GGUF Q8_0 export: ~6 GB on disk
- **Cumulative: ~25 GB GPU, ~12 GB disk** — well within Kaggle limits

If it OOMs:
- Drop to gradient_accumulation_steps × 2
- Drop max_seq_length from 2048 → 1024
- Switch to LoRA rank 8 instead of 16

## Run-time monitoring (during the run)

Watch the notebook output for these signals:

### Smoke benchmark on stock Gemma 4

Expected: ~5 minutes. Output should match the published numbers
(stock Gemma 4 E4B → ~0.5% mean on legal-citation-quality rubric).

If the smoke benchmark numbers differ significantly from the
harness_lift_report.md baseline:
- **Don't continue.** The dataset or model loading is wrong.
- Check that smoke_25 loaded the right rubric version
- Check that Gemma 4 E4B loaded (not E2B)

### SFT training loop

Expected:
- Loss decreases steadily over the first ~50 steps
- Plateau around step 200-300
- Total steps configurable; default ~500 for the notebook

If loss is NaN within first 10 steps:
- learning_rate is too high; the bundled config uses 2e-4 (Unsloth default)
- Try 5e-5

If loss bounces:
- gradient_accumulation_steps too low
- Try 4 instead of 1

### DPO step

Expected: 100-200 steps; faster than SFT.

If the DPO step produces a model that's WORSE than the SFT model
on the smoke benchmark:
- The chosen/rejected pairs are mis-labeled
- Roll back the DPO checkpoint; ship SFT-only

### GGUF Q8_0 export

Expected: ~3-5 minutes for a 4B model. File size ~4-5 GB.

If conversion fails (the most common failure: llama.cpp's gguf
quantizer hasn't been updated to support the latest Gemma
architecture):
- Fall back to GGUF F16 (no quantization). Larger file but works.
- Or skip GGUF; document weights as "FP16 only" in the model card.

### HF Hub push

Expected: 5-15 minutes (depends on Kaggle's outbound bandwidth).

If push fails:
- Verify HF_TOKEN is write-scoped
- Verify the target repo exists + has the right namespace
- Manual fallback: download the weights to your local machine,
  push from there

## Post-run verification

Once the run completes:

### 1. Numbers sanity-check

The post-fine-tune benchmark should show:
- Lift over stock: at least +5pp on the smoke_25 rubric
- Lift over harness-OFF: at least the harness-ON baseline (+56.5pp)
  PLUS the fine-tune contribution

If the post-fine-tune numbers are LOWER than the harness-on
baseline:
- The fine-tune may have over-fit to the SFT data
- Roll back to the SFT checkpoint OR skip the SFT step + ship
  base-model + harness only

### 2. RESULTS.md update

Update the table in `RESULTS.md` with actual numbers:

```markdown
| Stock Gemma 4 E4B refusal rate on harmful prompts | <X>% | bench-and-tune | smoke_25 | google/gemma-4-e4b-it@main |
| SFT refusal rate uplift vs stock | +<Y>pp | bench-and-tune | smoke_25 | taylorscottamarel/Duecare-Gemma-4-E4B-it-SafetyJudge-v0.1.0@main |
| DPO refusal rate uplift vs SFT | +<Z>pp | bench-and-tune | smoke_25 | taylorscottamarel/Duecare-Gemma-4-E4B-it-SafetyJudge-DPO-v0.1.0@main |
```

Each row's `git_sha` + `dataset_version` + `model_revision` triple
is the reproducibility commitment.

### 3. HF Hub model page

Visit https://huggingface.co/taylorscottamarel/Duecare-Gemma-4-E4B-it-SafetyJudge-v0.1.0
and verify:
- Model card renders
- Tags include "gemma-4", "safety", "trafficking-prevention"
- Dataset link points to the smoke_25 source
- Citation matches `CITATION.cff`

### 4. Update the writeup

In `docs/writeup_draft.md`, the section about Phase 3 fine-tune
becomes citable. Replace any "pending T4×2 run" language with
the actual lift numbers.

### 5. Notebook publish

Push the bench-and-tune notebook itself to Kaggle (it was
"publish pending"). Now its public URL works for judges.

## If the run fails entirely

Plan B (still legitimate for the submission):

- Document A2 as "scheduled post-hackathon" honestly in
  RESULTS.md + writeup_draft.md
- The harness-lift report (already complete, +56.5pp on 207
  prompts) is the stronger headline number
- Note that the fine-tune is "implemented but not yet run on
  Kaggle T4×2 due to quota timing; runnable from the published
  notebook"

This is honest and judge-acceptable. The harness's value doesn't
depend on the fine-tune; the fine-tune is incremental on top of
the harness.

## After A2 lands

Once weights are live + RESULTS.md is updated:

- Update `kaggle/_INDEX.md` to mark A2 as "live"
- Update `docs/FOR_JUDGES.md` to remove the "publish pending +
  T4×2 run pending" markers from A2
- Update the fine-tune row in `docs/rubric_evaluation_v07.md`
- Update the press kit's "Headline numbers" section if the
  fine-tune lift is publishable
- Consider adding a `docs/scenarios/fine-tune-your-own.md` for
  organizations that want to fine-tune on their own domain pack

## Adjacent reads

- [`docs/notebook_qa_companion.md`](notebook_qa_companion.md) — per-notebook test checklists (A2 is one of them)
- [`docs/two_week_submission_plan.md`](two_week_submission_plan.md) — when this happens in the schedule
- [`docs/harness_lift_report.md`](harness_lift_report.md) — the baseline numbers to compare against
- [`RESULTS.md`](https://github.com/TaylorAmarelTech/gemma4_comp/blob/master/RESULTS.md) — the table to update
- [`packages/duecare-llm-training/`](https://github.com/TaylorAmarelTech/gemma4_comp/tree/master/packages/duecare-llm-training) — the Unsloth integration package
