# Training data and fine-tuning

DueCare can turn evaluated harness runs into reviewable training data, stage a
LoRA job, and compare the result against the stock model. The code and notebook
workflow exist today, including a tiny end-to-end smoke path. **No trained
weights are published yet.** A generated dataset, script, or smoke adapter is
not a production model release.

The active source is the
[A-00 Fine-tuning and Evaluation workbench](https://github.com/TaylorAmarelTech/gemma4_comp/blob/master/kaggle/A-00-omni-experiment-workbench/README.md).
The [public Kaggle notebook](https://www.kaggle.com/code/taylorsamarel/duecare-fine-tuning-and-evaluation)
is live, but its public metadata identifies the current Kaggle copy as a May
2026 version. The July 2026 guarded dataset/training update in this repository
has not yet been pushed to Kaggle. The source workbench accepts Gemma 4, a
compatible Hugging Face model, or a local model path; exports portable JSONL
and manifests; and can prepare or execute an Unsloth or PEFT LoRA job when a
compatible CUDA environment is available.

## Current publication status

Status reviewed 2026-07-14:

- A public GET of the A-00 Kaggle URL returned HTTP 200 with page title
  `Duecare Fine Tuning and Evaluation`; its embedded metadata reported
  `dateModified=2026-05-17T23:17:31.9566667Z` and script version `320178883`.
- The repository's current A-00 `kernel-metadata.json` deliberately has an
  empty `dataset_sources` list. There is no dedicated public advanced-training
  dataset attached to it yet.
- The current local candidate audit is not clean: it includes a
  single-corridor shortcut risk, and older candidate rows do not yet satisfy
  all required lineage, source, licensing, and privacy fields.
- No production Gemma adapter, merged weights, or eligible complete advanced
  training dataset is published. The tiny smoke path remains plumbing proof.

The documentation-only future dataset surface is
[`kaggle/shared-datasets/training-data/`](../kaggle/shared-datasets/training-data/).
It intentionally contains no `dataset-metadata.json` and no data rows, so it
cannot be mistaken for a publishable Kaggle Dataset directory.

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

## Local Ollama adversarial candidate loop

Use `scripts/ollama_adversarial_flywheel.py` when you want a local Ollama
model to help expand the candidate pool before GPU training. The script runs a
three-model loop over approved seed prompts: adversarial rewrite, protective
answer generation, and strict judge review. The three roles can use the same
Ollama model or separate local models.

```bash
python scripts/ollama_adversarial_flywheel.py \
  --seed-jsonl reports/approved_seed_prompts.jsonl \
  --output-dir reports/ollama_flywheel/run-YYYYMMDD \
  --generator-model gemma4:latest \
  --adversary-model gemma4:latest \
  --judge-model gemma4:latest
```

Outputs are:

- `sft_candidates.jsonl`
- `preference_candidates.jsonl`
- `quarantine.json`
- `manifest.json`

The manifest is deliberately `safe_to_train=false`. Ollama output is candidate
evidence, not approval. Before it can feed A-00, Kaggle, Unsloth, or another
GPU trainer, the downstream bundle/release gates must still prove held-out
prompt and lineage isolation, source and license eligibility, curator approval,
privacy clearance, immutable train target revision, artifact hashes, and
publication approval. Hidden-thought markup, PII-like material, unsafe advice,
or judge rejection moves the item into a raw-text-free quarantine record.

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

### External importer boundary

A-00's **Already have a file?** importer can inspect a JSON, JSONL, or ZIP
export from a prior DueCare run or another controlled system. It can recognize
prompt/response rows, SFT rows, preference rows, manifests, and run bundles and
suggest the relevant next workflow. Import is not approval:

1. A loose JSONL can be inspected and triaged, but training remains blocked
   unless the SFT/DPO artifacts arrive with the required manifest.
2. The manifest must bind artifact hashes, base-model ID and immutable
   revision, prompt and source lineages, frozen held-out prompt hashes and
   lineage IDs, license/allowed-use records, privacy results, and clean quality
   gates.
3. Imported final answers, citations, tool/harness traces, and deliberately
   authored visible rationales may become candidates when their provenance and
   permissions allow it. Private hidden chain-of-thought is neither an import
   target nor an allowed training field.
4. Imported rows stay quarantined or candidate-only until the same validation
   contract passes; attaching a file or Kaggle Dataset never sets
   `safe_to_train` by itself.

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
- [`ollama_adversarial_flywheel.py`](https://github.com/TaylorAmarelTech/gemma4_comp/blob/master/scripts/ollama_adversarial_flywheel.py)
  generates local Ollama-backed SFT/DPO candidates and a quarantine manifest;
  its output remains candidate-only until the same training and publication
  gates pass.

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
