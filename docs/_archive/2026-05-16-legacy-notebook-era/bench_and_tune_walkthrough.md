# Bench-and-Tune Walkthrough — A07 notebook on Kaggle T4×2

> Step-by-step guide for running `kaggle/A-07-bench-and-tune/kernel.py`
> end-to-end. This is the Special Tech Track Unsloth angle ($10k
> bonus): smoke benchmark stock Gemma 4 → Unsloth SFT (LoRA) → DPO
> → re-benchmark → GGUF export → HF Hub push.
>
> **Time budget:** ~30-50 minutes for the smoke path, or ~3-4 hours for
> a larger `full_207` + 1,000-example run. Most time is Phase 5 SFT,
> Phase 7 DPO, and Phase 8 re-benchmark. **Cost: 0** if you stay within Kaggle's
> free GPU quota. Outputs the
> `Duecare-Gemma-4-E4B-it-SafetyJudge-v0.1.0` model on HF Hub.

## Short answer: yes, the harness traces are training data

The repository already has the fine-tuning notebook: `A-07-bench-and-tune`.
It is not pure RLHF. The safer, reproducible path is:

1. **SFT distillation.** Run prompts through Persona + GREP + RAG + Tools,
  then train Gemma 4 LoRA on the harness-grounded answer. The bare user
  prompt is the training input; the cited harness answer is the target.
2. **Preference optimization.** Pair the harness-on answer as `chosen`
  against the raw Gemma answer as `rejected`, then run DPO on top of SFT.
  This gives the same practical benefit the user described as
  "reinforcement" without needing an online reward loop.
3. **Evaluation gate.** Re-run stock vs. SFT vs. DPO with the same benchmark
  and publish only if the adapter beats stock without increasing PII,
  hallucination, or unsafe-help rates.

Do not train on raw worker chats. Eligible rows are public-source,
synthetic, composite, or anonymized partner-reviewed examples with
provenance. The local runtime can generate candidates, but the anonymizer
and curator gate decide whether they are training data.

## Prerequisites

| What | Where | Required? |
|---|---|---|
| Kaggle account with verified phone | kaggle.com | Required (GPU access) |
| Kaggle GPU T4×2 quota | Kaggle quota dashboard | Required (~30 hrs/week free) |
| HF_TOKEN with write scope | huggingface.co/settings/tokens | Required for Phase 10 (HF push) |
| `duecare-bench-and-tune-wheels` dataset attached | Kaggle dataset settings | Required (auto-detected at startup) |
| `google/gemma-4` model (any variant) attached | Kaggle Models tab | Required (auto-detected) |

## Phase reference (10 phases + summary)

| Phase | What it does | ETA on T4×2 | Output |
|---|---|---:|---|
| 0 | Install Hanchen's pinned Unsloth stack + restart | 8-12 min | `/tmp/.duecare_unsloth_stack_v1_done` marker |
| 1 | Verify environment (CUDA, VRAM, Unsloth version) | 30 sec | banner with VRAM allocated/reserved |
| 2 | Load Gemma 4 via Unsloth FastModel | 2-3 min | model + tokenizer in memory |
| 3 | Stock benchmark (baseline before SFT) | 8-15 min | `/kaggle/working/bench_stock.json` |
| 4 | Build SFT training data from harness-distilled or A06-generated pairs | 2-5 min | `/kaggle/working/sft_dataset.jsonl` |
| 5 | SFT (LoRA on Gemma 4) | 60-90 min | `/kaggle/working/duecare_sft_lora/adapter_model.safetensors` |
| 6 | Build DPO preference pairs | 1-3 min | `/kaggle/working/dpo_dataset.jsonl` |
| 7 | DPO (preference-tuning on top of SFT) | 30-60 min | `/kaggle/working/duecare_dpo_lora/adapter_model.safetensors` |
| 8 | Re-benchmark fine-tuned model | 8-15 min | `/kaggle/working/bench_ft.json` |
| 9 | GGUF Q8_0 export (for llama.cpp / Ollama distribution) | 8-15 min | `/kaggle/working/duecare_gguf/Duecare-Gemma-4-E4B-it-SafetyJudge-v0.1.0.Q8_0.gguf` |
| 10 | HF Hub push (model + tokenizer + GGUF) | 3-8 min | `huggingface.co/<user>/Duecare-Gemma-4-E4B-it-SafetyJudge-v0.1.0` |
| 11 | Write summary JSON with provenance + lift delta | 5 sec | `/kaggle/working/bench_and_tune_summary.json` |

**Total: ~3 hours for the full pipeline**, mostly Phase 5 + Phase 8.

## Configuration (top of kernel.py)

The five toggle flags let you skip phases. Defaults run everything:

```python
RUN_BENCHMARK_STOCK = True   # Phase 3 — disable to skip baseline (rare)
RUN_SFT             = True   # Phase 5 — disable to evaluate stock only
RUN_DPO             = True   # Phase 7 — disable for SFT-only fine-tune
RUN_BENCHMARK_FT    = True   # Phase 8 — disable to skip post-tune eval
RUN_GGUF_EXPORT     = True   # Phase 9 — disable if you don't want GGUF
RUN_HF_PUSH         = True   # Phase 10 — disable for local-only experiment
```

To run **only the stock benchmark** (e.g., to compare against the
v3.16 chat wheel without fine-tuning):

```python
RUN_SFT = RUN_DPO = RUN_BENCHMARK_FT = RUN_GGUF_EXPORT = RUN_HF_PUSH = False
```

## Hyperparameters (defaults)

The defaults are tuned for the bundled `smoke_25` benchmark + a
~200-example SFT dataset. They produce a noticeable lift without
overfitting:

```python
# SFT (LoRA)
SFT_MAX_EXAMPLES        = 200
SFT_NUM_EPOCHS          = 2
SFT_LEARNING_RATE       = 2e-4
SFT_PER_DEVICE_BATCH    = 2
SFT_GRAD_ACCUM_STEPS    = 4    # effective batch = 8
SFT_LORA_R              = 16
SFT_LORA_ALPHA          = 32
SFT_LORA_DROPOUT        = 0.05

# DPO
DPO_MAX_PAIRS           = 100
DPO_NUM_EPOCHS          = 1
DPO_LEARNING_RATE       = 5e-6
DPO_BETA                = 0.1
```

For a longer-running production fine-tune: bump `SFT_MAX_EXAMPLES`
to 1000+, `SFT_NUM_EPOCHS` to 3, and use the full benchmark
(`BENCHMARK_SET = "full_207"`) instead of `smoke_25`. Expect ~12
hours on T4×2.

## Common failure modes

### "OOM during Phase 5 SFT"

- T4×2 = 32GB total. Gemma 4 E4B in 4-bit + LoRA = ~16GB. Fitting:
  - Reduce `SFT_PER_DEVICE_BATCH` from 2 to 1
  - Reduce `GEMMA_MAX_SEQ_LEN` from 4096 to 2048
  - Switch to `e2b-it` (uses ~6GB instead of 16GB)
- 26B-A4B / 31B variants need larger GPU; recommend P100 16GB or
  A100 40GB

### "Phase 0 install hangs / fails"

- This is Hanchen's pinned recipe — DO NOT change it. The pinning
  exists because Unsloth + transformers + torch interact in
  fragile ways at v3.16.
- If the install finishes but Unsloth import fails, restart the
  Kaggle session and re-run. The restart is sometimes mandatory
  for the Phase 0 `del sys.modules[...]` purge to take effect.

### "HF push fails with 401"

- Confirm `HF_TOKEN` is set in Kaggle Add-ons → Secrets with
  **write** scope (not just read).
- Confirm `HUGGING_FACE_HUB_TOKEN` is also set (some libraries read
  this name instead of `HF_TOKEN`).
- Test: `from huggingface_hub import HfApi; HfApi().whoami()` —
  should return your username.

### "GGUF export fails / takes forever"

- Phase 9 calls `llama.cpp`'s convert script under the hood; first
  invocation pulls llama.cpp from GitHub.
- If the GGUF artifact ends up larger than 4GB, the upload to HF
  Hub may rate-limit. Use the `huggingface-cli upload-large`
  fallback or split.
- Alternative: skip Phase 9 and `git lfs push` the GGUF separately
  from your laptop.

### "Phase 8 re-benchmark gives lift but smaller than expected"

- The default 200-example SFT is intentionally small (under-fit safe).
  For the headline +56.5pp lift number, use the full 207 prompts +
  the harness-distilled response pairs (set `SFT_MAX_EXAMPLES = 1000`).
- DPO contributes ~5-15pp on top of SFT; if Phase 7 was skipped,
  expect lift ~10-20pp lower than the Phase 8 + Phase 7 combination.

## What to watch in the output

### After Phase 3 (stock benchmark)

```
Phase 3: stock benchmark
  ✓ ran 25 prompts on stock Gemma 4 E4B (Unsloth FastModel, 4-bit)
  ✓ pass_rate: 0.36
  ✓ verdict_acc: 0.41
  ✓ wrote /kaggle/working/bench_stock.json
```

Lower pass_rate = more headroom for the fine-tune to lift. The
typical stock E4B baseline on `smoke_25` is 30-40%.

### After Phase 5 (SFT)

```
Phase 5: SFT
  ✓ trained 200 examples × 2 epochs (effective batch 8)
  ✓ final loss: 0.42 (start: 1.81)
  ✓ wrote LoRA adapter to /kaggle/working/duecare_sft_lora
```

Final loss below 0.6 is healthy. Below 0.2 = likely over-fitting;
reduce epochs.

### After Phase 8 (re-benchmark)

```
Phase 8: re-benchmark
  ✓ ran 25 prompts on duecare-fine-tuned Gemma 4 E4B
  ✓ pass_rate: 0.84  (Δ +0.48 vs stock)
  ✓ verdict_acc: 0.89  (Δ +0.48 vs stock)
  ✓ lift summary: HUGE (+48pp pass / +48pp verdict)
```

Δ +30pp or higher is the floor for "fine-tune is real". If Δ <
+15pp, something went wrong (LoRA didn't apply, training data
contaminated, etc.).

### After Phase 10 (HF Hub push)

```
Phase 10: HF Hub push
  ✓ pushed Duecare-Gemma-4-E4B-it-SafetyJudge-v0.1.0
  ✓ URL: https://huggingface.co/<user>/Duecare-Gemma-4-E4B-it-SafetyJudge-v0.1.0
  ✓ also uploaded GGUF: <url>/blob/main/Duecare-Gemma-4-E4B-it-SafetyJudge-v0.1.0.Q8_0.gguf
```

Visit the URL to confirm the model card was generated and the
adapter weights are visible.

## Provenance JSON (Phase 11)

The summary JSON writes everything reproducibility needs:

```json
{
  "model_base":           "google/gemma-4-4b-it",
  "model_finetuned":      "<user>/Duecare-Gemma-4-E4B-it-SafetyJudge-v0.1.0",
  "git_sha":              "<from DUECARE_GIT_SHA env or 'unknown'>",
  "wheel_versions":       {"chat": "0.1.0", "core": "0.1.0", "models": "0.1.0"},
  "harness_counts":       {"grep_rules": 108, "rag_docs": 33, "tools": 5,
                            "rubric_dimensions": 21, "evaluation_questions": 21,
                            "example_prompts": 407, "classifier_examples": 51},
  "benchmark":            "smoke_25",
  "n_prompts":            25,
  "stock_pass_rate":      0.36,
  "ft_pass_rate":         0.84,
  "lift_pp":              48,
  "stock_verdict_acc":    0.41,
  "ft_verdict_acc":       0.89,
  "verdict_lift_pp":      48,
  "sft_max_examples":     200,
  "sft_num_epochs":       2,
  "dpo_max_pairs":        100,
  "dpo_num_epochs":       1,
  "gguf_path":            "duecare_gguf/Duecare-Gemma-4-E4B-it-SafetyJudge-v0.1.0.Q8_0.gguf",
  "hf_url":               "https://huggingface.co/<user>/Duecare-Gemma-4-E4B-it-SafetyJudge-v0.1.0",
  "timestamp_utc":        "2026-05-XX..."
}
```

This is the artifact that lets reproducibility-focused judges verify
the lift claim independently.

## After the run finishes

1. **Verify the HF Hub model card.** Visit the URL; confirm the
   model card mentions Duecare, the lift number, and the
   reproducibility tuple.
2. **Test the GGUF locally.** Download the GGUF, then:
   ```bash
   ollama create duecare -f Modelfile  # Modelfile points at the .gguf
   ollama run duecare "I run an agency in Hong Kong charging 68% APR..."
   ```
   The fine-tuned model should respond with the same kind of
   citation-rich refusal as the harness-ON Gemma 4 demonstrates in
   the live-demo notebook — but without needing the GREP/RAG/Tools
   stack at inference time. (The fine-tune absorbs the harness's
   knowledge into the weights themselves.)
3. **Update `docs/writeup_draft.md`** with the actual fine-tune lift
   numbers from the summary JSON. Replace any placeholder text
   that previously said "fine-tune pending".
4. **Update the bench-and-tune dataset description** on Kaggle:
   ```
   v3.16 — fine-tune complete: <stock pp> → <ft pp> on smoke_25
   (Δ +<lift> pp). Model: Duecare-Gemma-4-E4B-it-SafetyJudge-v0.1.0
   on HF Hub. Special Tech Track (Unsloth) angle.
   ```
5. **(Optional) Push the GGUF separately to llama.cpp release**
   for users who want a one-line Ollama install:
   ```bash
   ollama push duecare/safetyjudge-v0.1.0
   ```

## Why this matters for the rubric

- **Special Tech Track Unsloth ($10k bonus):** the bench-and-tune
  notebook is the literal "we used Unsloth" artifact. The HF Hub URL
  in the writeup is the verifiable proof.
- **Special Tech Track llama.cpp ($10k bonus):** the GGUF artifact
  is the on-device deployment story. Pair with the Android v0.9 APK
  (which uses MediaPipe Gemma 4 E2B/E4B) for the full on-device
  narrative.
- **Technical Depth & Execution (30 pts):** end-to-end SFT → DPO →
  GGUF → HF Hub push is exactly the engineering depth signal judges
  look for. The pipeline is real, the lift is measurable, the model
  is downloadable.

## When to NOT run this

- If you're under deadline pressure and the chat-playground +
  live-demo + omni notebook already demonstrate the lift via the
  harness, the fine-tune is **bonus, not required**. The Impact &
  Vision and Video Pitch are 70 of 100 points; the fine-tune adds
  ~5-10 points of bonus to the Tech Depth score.
- If your Kaggle GPU quota is exhausted, defer to next week or
  switch to the Special Tech Track llama.cpp angle (run the GGUF
  through Ollama on a laptop instead).

## Critical-path summary

1. Open `kaggle/A-07-bench-and-tune/kernel.py` on Kaggle
2. Attach `duecare-bench-and-tune-wheels` + `google/gemma-4` model
3. Add `HF_TOKEN` (write scope) to Kaggle Secrets
4. Run cell — leave for ~3 hours
5. Check HF Hub URL is live
6. Update writeup with actual lift numbers
