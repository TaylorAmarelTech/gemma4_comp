# Model-improvement runbook: train → eval → select

> An operator recipe for the DueCare **train→eval→select** loop — how to turn the harness's *measured*
> inference-time lift into a smaller model's *learned* behaviour, step by step, with the CPU/GPU
> boundary and the promotion gates made explicit. The design rationale is in
> [`phase3_training_framework.md`](phase3_training_framework.md); this is the "which command, in what
> order" companion. Every step is **propose-only** into gitignored stores until the select gate passes.
>
> Verify flags with `python scripts/<name>.py --help` before a real run — the pipeline evolves; this
> runbook names the steps and the gates, not a frozen flag set.

## The idea in one line

The harness proves the safety knowledge is *reachable* at inference; training asks whether the model can
learn to reach on its own. We **distil the harness's measured lift into the weights** for the stable
behaviours (indicator reasoning, grounded-refusal shape, evidence-first structure, ILO/AML framing) while
the harness keeps supplying **volatile** facts (current hotlines, fee caps, fresh statutes) via tools —
so the weights never go stale. A trained model and the harness should *stack*: better standalone **and**
better harnessed. We do not assume this; we measure it in four arms.

## Prerequisites

- A **graded benchmark panel** — `reports/rich_lift/panel.jsonl` + `results.jsonl` with baseline and
  harnessed arms scored (the same board this repo grades; the training signal is the per-prompt lift).
- The **CPU test env** for the `--validate` / analysis steps (`pwsh scripts/recover_test_env.ps1 -Run`;
  the clean venv lives outside the OneDrive tree — see [`local_test_env.md`](local_test_env.md)).
- A **Kaggle GPU session** for the actual train step (T4/A100), with `HF_TOKEN` if pushing weights.

## The steps

### 1. Build the training data (CPU, propose-only)

```bash
python scripts/build_lift_training_data.py
```

Distils high-lift `(baseline -> harnessed)` pairs from `panel.jsonl` into vetted **SFT** + **DPO** JSONL
in a gitignored `reports/training/` store, with a provenance manifest. The gates baked in here are the
P0 gold-sourcing discipline: teacher = the cheap **`harness_core`** arm (avoids memorising volatile
facts); `refusal_detector` drops bare refusals; a **grounding floor** on the A/B/D components requires
the target to *add grounding*, not just refuse; and a **citation gate** rejects hallucinated statutes.

### 2. Audit data quality (CPU)

```bash
python scripts/audit_training_quality.py
```

The pre-train guardrails: overfit / false-pattern / fragile-fact / jurisdiction checks over the candidate
set, so a systematic flaw is caught *before* the GPU spend, not after.

### 3. Organize splits (CPU)

```bash
python scripts/organize_training_data.py
```

Produces train/val/**held-out test** splits (`sft_train.jsonl` / `dpo_train.jsonl` / …). The held-out
split is load-bearing for the select gate (step 7): generalization is measured on prompts the model
never trained on.

### 4. Validate the training plan (CPU-safe — runs anywhere)

```bash
python scripts/train_lift_distill.py --validate
```

A data + plan check with no GPU: confirms the JSONL is well-formed, the recipe wiring is intact, and the
selected SFT/DPO variants resolve. Run this first every time; it is the cheap gate before Kaggle.

### 5. Train (Kaggle GPU)

```bash
# smoke first:
python scripts/train_lift_distill.py --test-run
# then the real fine-tune:
python scripts/train_lift_distill.py --base-model unsloth/gemma-4-E4B-it
```

The canonical Unsloth recipe: `FastModel.from_pretrained -> get_peft_model -> get_chat_template
gemma-4-thinking -> SFTTrainer + train_on_responses_only`, then an optional **DPO** pass over the
contract-derived hard-negative pairs (which target the weak chain links). Optional GGUF export gives the
on-device artifact. Comparison arms exist via `--sft-variant reasoning_repaired[_core]` and
`--dpo-variant contract | base_plus_contract` for ablations.

### 6. Evaluate in four arms (GPU to generate, CPU to analyze)

```bash
python scripts/four_arm_eval.py --run --adapter reports/training/adapter   # GPU: populate arms C/D
python scripts/four_arm_eval.py --analyze                                  # CPU: refresh the report
```

Grades the trained checkpoint on the **same board** in four arms — A stock/off, B stock/on, C
trained/off, D trained/on — so we can read (1) how much training internalised the harness lift
(**C-A** vs **B-A**) and (2) whether training and the harness **stack** (**D** vs B and C).

### 7. Select — the promotion gate (do NOT promote on one number)

Promote a checkpoint **only** if it clears all of:

1. **Internalisation:** trained-baseline (C) moves meaningfully toward the stock-harnessed ceiling (B).
2. **Stacking:** the harnessed-trained arm (D) is >= the best of B and C (training doesn't fight the harness).
3. **Smallest held-out generalization gap:** measured on the step-3 held-out split, not the train set —
   pick the variant with the smallest gap (`four_arm_eval --split-by-typology` surfaces it).
4. **No over-refusal regression:** the **intent split** (`rich_harness_lift --benign-control …`) shows
   the trained model does not lecture/refuse the benign control set more than stock — a big under-refusal
   lift with a big over-refusal cost is a *reject*.
5. **No criterion regresses, no PII leak, citations still real** (the deterministic gates from step 1,
   re-checked on the trained outputs).

### 8. Provenance + publish gate (CPU-safe)

```bash
python scripts/finetune_registry.py verify <model_id>          # re-check sha256/byte fingerprints
python scripts/build_model_card.py --require-verified-artifacts # refuse a card on stale evidence
python scripts/validate_training_provenance.py --model-id <model_id>  # one-shot publication gate
```

The registry records sha256/byte fingerprints of the exact selected data + manifests; the card build and
the provenance validator **fail closed** if that evidence is stale or missing, so a published model card
is always traceable to the data that made it (repo-relative paths, no local-workstation leakage).

## The discipline (same as the benchmark)

- **Stable vs volatile:** teach reasoning / refusal / indicator / evidence *shape*; never bake a hotline
  number or fee cap into the weights — those stay tool-supplied so the model never goes stale.
- **Circularity guard:** training on one judge's scores could teach that judge's preferences; we counter
  with the deterministic gates (citation, PII), a diverse judge panel, held-out evaluation, and human
  review for community-sourced / high-stakes examples.
- **Propose-only:** everything lands in gitignored `reports/training/` until the step-7 gate passes; the
  merge/promote step is supervised, exactly like the prompt-discovery flywheel.
