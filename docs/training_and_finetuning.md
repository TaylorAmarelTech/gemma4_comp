# Training data and fine-tuning

DueCare can turn evaluated harness runs into reviewable training data, stage a
LoRA job, and compare the result against the stock model. The code and notebook
workflow exist today, including a tiny end-to-end smoke path. **No trained
weights are published yet.** A generated dataset, script, or smoke adapter is
not a production model release.

The active notebook is the
[A-00 Fine-tuning and Evaluation workbench](https://github.com/TaylorAmarelTech/gemma4_comp/blob/master/kaggle/A-00-omni-experiment-workbench/README.md),
also available as the
[public Kaggle notebook](https://www.kaggle.com/code/taylorsamarel/duecare-fine-tuning-and-evaluation).
It accepts Gemma 4, a compatible Hugging Face model, or a local model path;
exports portable JSONL and manifests; and can prepare or execute an Unsloth or
PEFT LoRA job when a compatible CUDA environment is available.

## The full flywheel

1. Run the same approved prompts through one exact model with the harness off
   and on. Record the model revision, prompt ID, pack versions, response,
   citations, tool trace, latency, and per-dimension grades.
2. Select candidate teaching rows from high-quality harness answers and useful
   baseline failures. Keep rejection reasons instead of silently dropping
   them.
3. Apply provenance, license, sensitive-data, citation, deduplication, and
   quality gates. Community or case-derived material also requires curator
   review and an allowed-use record.
4. Build SFT targets, DPO pairs, counterfactuals, contract hard negatives, and
   explicit reasoning-repair variants. Freeze lineage-, typology-, and
   corridor-aware train, validation, and holdout splits.
5. Train a base-model-specific LoRA adapter. Stable response behavior can be
   learned; volatile facts such as current contacts, rules, and fee caps stay
   in versioned retrieval or tools.
6. Evaluate four arms on the same untouched holdout: stock, stock + harness,
   trained, and trained + harness.
7. Promote nothing unless the trained arms improve the intended dimensions
   without worse citation faithfulness, privacy leakage, unsafe assistance, or
   benign over-refusal. Publish the manifest and reproducibility evidence with
   any future weights.

This process can start with Gemma 4 and then be repeated for other compatible
models. The dataset and evaluation contracts are portable; a LoRA adapter is
not. Train and evaluate a separate adapter for every base model and revision.

## Dataset contracts

| Artifact | Minimum content | Purpose |
|---|---|---|
| SFT JSONL | chat `messages`, source, model and prompt IDs, pack versions, grade, privacy result | Teach the approved answer and response structure. |
| DPO JSONL | prompt, `chosen`, `rejected`, pair reason, provenance, privacy result | Prefer a grounded answer over a specific failure mode. |
| Contract hard negative | chosen answer, one controlled ablation, failed contract link | Teach evidence, citation, action, and resource requirements without confounding failures. |
| Reasoning repair | source row, missing reasoning links, reviewed repair, verifier result | Compare ordinary SFT with a non-duplicating explicit-reasoning arm. |
| Counterfactual | linked scenario family, changed fact, expected behavior change | Test whether the model follows facts rather than memorizing surface patterns. |
| Evaluation holdout | immutable prompt lineage, rubric, expected safety behavior | Measure release quality; never include it in training. |

Every exported bundle should be reproducible from its Git commit, dataset
manifest hash, model revision, split policy, generator version, and gate
results. Credentials and local paths do not belong in the bundle.

## Answers, rationales, and chain-of-thought

A-00 can export complete model answers, harness traces, citations, rubric
scores, judge rationales, and an intentionally requested concise explanation.
Those are model-visible artifacts and can be downloaded with the run bundle
when their license and privacy status permit it.

Do **not** claim that the notebook can retrieve a provider's private or hidden
chain-of-thought. DueCare does not need that data. Training rows should contain
the final answer and, when useful, an explicit reviewable reasoning scaffold
such as:

```text
indicator -> applicable rule and exception -> protective action -> resources -> uncertainty
```

The legacy-named
[`build_legal_cot_training.py`](https://github.com/TaylorAmarelTech/gemma4_comp/blob/master/scripts/build_legal_cot_training.py) builds
this kind of visible, worker-facing reasoning chain; it does not extract hidden
model state. Its output remains propose-only until lineage splits and direct
factual grading pass. The production-oriented reasoning path is documented in
[Training for understanding](research/training_for_understanding.md) and uses
verified repair variants rather than unreviewed internal monologues.

## Kaggle and other training systems

In A-00:

1. Import a prior prompt/response bundle or run an approved prompt set.
2. Generate rubric-polished SFT and DPO data, or create the tiny smoke bundle.
3. Download the SFT JSONL, DPO JSONL, manifest, generated training script, and
   bundle ZIP before a session ends.
4. Run the training preflight. Keep execution disabled until the model ID and
   immutable revision, license, data paths, CUDA support, and dependencies are
   confirmed. The official E2B/E4B presets are commit-pinned; custom remote
   models must supply their own immutable revision.
5. Execute the LoRA job, reload the exact base model plus adapter, and run all
   four evaluation arms.
6. Export the adapter only with its dataset and evaluation manifests.

The same JSONL and manifest contract can be handed to another controlled
Unsloth, TRL, or PEFT environment. Trainer-specific formatting should be a
derived artifact; the canonical source rows and holdout assignments stay
unchanged.

The implementation follows the current primary training references: Google's
[Gemma tuning overview](https://ai.google.dev/gemma/docs/tune) and
[Gemma 4 QLoRA guide](https://ai.google.dev/gemma/docs/core/huggingface_text_finetune_qlora),
the Hugging Face TRL [SFT](https://huggingface.co/docs/trl/en/sft_trainer) and
[DPO](https://huggingface.co/docs/trl/en/dpo_trainer) trainers, and PEFT's
[LoRA configuration](https://huggingface.co/docs/peft/en/package_reference/lora).
DueCare adds stricter dataset, privacy, lineage, and four-arm release gates on
top of those trainer mechanics.

## Existing implementation surfaces

- [`build_lift_training_data.py`](https://github.com/TaylorAmarelTech/gemma4_comp/blob/master/scripts/build_lift_training_data.py)
  selects and gates harness-distilled SFT and DPO candidates.
- [`organize_training_data.py`](https://github.com/TaylorAmarelTech/gemma4_comp/blob/master/scripts/organize_training_data.py) creates
  leakage-aware splits and the organization manifest.
- [`build_reasoning_targets.py`](https://github.com/TaylorAmarelTech/gemma4_comp/blob/master/scripts/build_reasoning_targets.py),
  [`build_reasoning_repairs.py`](https://github.com/TaylorAmarelTech/gemma4_comp/blob/master/scripts/build_reasoning_repairs.py), and
  [`build_reasoning_sft_variant.py`](https://github.com/TaylorAmarelTech/gemma4_comp/blob/master/scripts/build_reasoning_sft_variant.py)
  stage explicit-reasoning comparison arms.
- [`build_dpo_mix_variant.py`](https://github.com/TaylorAmarelTech/gemma4_comp/blob/master/scripts/build_dpo_mix_variant.py) stages a
  traceable base-plus-contract DPO arm without mutating the base split.
- [`train_lift_distill.py`](https://github.com/TaylorAmarelTech/gemma4_comp/blob/master/scripts/train_lift_distill.py) owns the LoRA
  training handoff and preflight checks.
- [`four_arm_eval.py`](https://github.com/TaylorAmarelTech/gemma4_comp/blob/master/scripts/four_arm_eval.py) measures training and
  harness effects separately.

For the deeper design and exact gates, see the
[Phase 3 training framework](phase3_training_framework.md),
[fine-tuning data strategy](finetuning_data_strategy.md),
[training methodology](research/training_methodology.md), and
[training regimes and systems](research/training_regimes_and_systems.md).

## Non-negotiable data rules

- Never train on raw worker chats, private case files, identity documents, or
  unredacted contact details.
- Never let evaluation holdouts or near-duplicate lineages enter training.
- Never treat a high judge score as sufficient evidence by itself; retain
  deterministic, cross-family, and human checks.
- Never bake volatile operational facts into weights when a versioned tool or
  knowledge object can supply them at inference time.
- Never publish an adapter without its base-model revision, data manifest,
  license record, gate results, and four-arm evaluation.
