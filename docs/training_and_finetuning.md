# Training data and fine-tuning

DueCare can turn evaluated harness runs into reviewable training data, train a
Low-Rank Adaptation adapter, and compare the result against the stock model.
The code and notebook workflow now include two real local graphics-processor
runs, a public relative adapter, a four-arm ablation, and a Tensor Processing
Unit continuation. **No merged production model is published.** The public
adapter is a deliberately small learning artifact, not a production release.

## Terms used in this guide

- **Supervised fine-tuning (SFT)** trains a model with inputs paired with
  desired answers.
- **Direct Preference Optimization (DPO)** trains from prompts with preferred
  and nonpreferred responses.
- **Low-Rank Adaptation (LoRA)** trains small adapter weights while leaving
  most base-model weights frozen.
- **Parameter-Efficient Fine-Tuning (PEFT)** is the broader family of methods
  that update a small part of a model; Low-Rank Adaptation is one example.
- **JavaScript Object Notation Lines (JSON Lines)** stores one complete JSON
  object per line in a `.jsonl` file.
- **Central processing unit (CPU)** and **graphics processing unit (GPU)**
  identify the compute path used by a notebook.
- **Tensor Processing Unit (TPU)** is Google's accelerator for large tensor
  computations. Kaggle runtime topology can change, so every notebook detects
  and records the devices it actually receives instead of assuming a fixed
  core count.
- **Compute Unified Device Architecture (CUDA)** is NVIDIA's software platform
  for graphics-processing-unit computation.
- **Secure Hash Algorithm 256-bit (SHA-256)** is the checksum used to bind
  files and manifests.
- **Comma-separated values (CSV)** and **Portable Network Graphics (PNG)** are
  table and chart file formats used in notebook outputs.

The architectural boundaries behind these artifacts are defined in the
[evidence-grounded synthetic-training blueprint](research/evidence_grounded_synthetic_training_blueprint.md).
Current publication, loading, interoperability, and defensive safety-evaluation
practices are documented in
[training-dataset publication and safety-evaluation practices](research/training_dataset_publication_and_safety_practices.md).

The active source is the
[A-00 Fine-tuning and Evaluation workbench](https://github.com/TaylorAmarelTech/gemma4_comp/blob/master/kaggle/A-00-omni-experiment-workbench/README.md).
The [public Kaggle notebook](https://www.kaggle.com/code/taylorsamarel/duecare-fine-tuning-and-evaluation)
is live. The proof dataset
[`taylorsamarel/duecare-proof-finetuning-data`](https://www.kaggle.com/datasets/taylorsamarel/duecare-proof-finetuning-data)
is public and attached in the source notebook metadata. The source workbench
accepts Gemma 4, a compatible Hugging Face model, or a local model path;
exports portable JSONL and manifests; and can prepare or execute an Unsloth or
PEFT LoRA job when a compatible CUDA environment is available.

## Current publication status

Status reviewed 2026-07-15. Every `release-manifest` SHA-256 and per-lane row
count below is also recorded in the committed registry
[`configs/duecare/training/published_dataset_claims.json`](../configs/duecare/training/published_dataset_claims.json)
so the numbers have a single source of truth. When the gitignored staged or
re-downloaded artifacts are present, `python scripts/verify_training_dataset_claims.py`
re-derives each SHA-256 from disk and fails closed on any mismatch; a clean
checkout reports each dataset as `published-only` instead. `scripts/validate_public_surface.py`
additionally fails if a registry SHA drifts out of this document.

- The [DueCare Measured Response Training Corpus](https://www.kaggle.com/datasets/taylorsamarel/duecare-measured-response-training-corpus)
  is public as Kaggle version 4. It contains 791 accepted supervised
  fine-tuning rows, 791 same-prompt preference pairs, 1,582 reward-label rows,
  184,650 raw-text-free inventory rows, and 6,884 raw-text-free quarantine
  rows. Its release-manifest SHA-256 is
  `56fa69c19990c524002e4f91b833faef58648a66d87729a8f4c61dd56722b74b`.
  The package is `safe_to_train=true` and `safe_to_publish=true`; its
  contamination ledger still prohibits treating results on the source
  benchmark as independent model-improvement evidence.
- The [DueCare Multiperspective Fine-Tuning Corpus](https://www.kaggle.com/datasets/taylorsamarel/duecare-multiperspective-finetuning-corpus)
  is public as Kaggle version 4. It contains 25,600 supervised fine-tuning
  training rows, 25,600 preference-training rows, 2,048 validation rows, and
  2,048 test rows. Its release-manifest SHA-256 is
  `ea644df422d9e8c43003805f49a227d441e3a952d6deb3ea3e6fb3b6b579211d`.
  The corpus contains deterministic fictional scenarios and visible decision
  scaffolds; it contains no real worker cases or private hidden reasoning.
- The [DueCare Measured Review Curriculum 200K](https://www.kaggle.com/datasets/taylorsamarel/duecare-measured-review-curriculum-200k)
  is a public, synthetic augmentation study with 207,680 supervised training
  rows, 207,680 preference-training pairs, 528 validation rows, and 608 test
  rows. It preserves 649/66/76 parent-bound train/validation/test groups. Its
  release-manifest SHA-256 is
  `1b062ce12fe43494f7d63659a53017c857e0ac0103759d8f71b3340f63bdc2b7`.
  Row count is not treated as independent sample size; descendants retain
  parent hashes, transformation identifiers, and family weight keys.
- The [DueCare Gemma 4 Adapter Learning Study](https://www.kaggle.com/datasets/taylorsamarel/duecare-gemma4-adapter-learning-study)
  publishes two real local Gemma 4 E2B training runs, relative Low-Rank
  Adaptation weights, exact optimization logs, paired generations, and the
  four-arm record. The current release-manifest SHA-256 is
  `4c300a3b277009e1488979bb6579859a59f0dbfeecf4c31a0d4251ea837572f4`.
  A frozen, blinded judge also compared six recorded high-severity Gemma
  harmful-request failures with their real DueCare harness responses in both
  presentation orders. The harness won all six pairs with mean delta +9.67/10,
  a pair-bootstrap 95% interval of [+9.0, +10.0], and zero mean order gap. This
  supports a bounded harmful-request-handling claim, not victim identification,
  prevalence estimation, legal findings, or field detection effectiveness.
  The same public release now includes a checksummed receipt over the earlier
  911-pair Gemma harness study (+1.73/10 by the model judge), its 998-pair
  deterministic cross-check (+0.18/10), and 140 adversarial transformations
  (+4.39/10 by the model judge). These are synthetic/composite benchmark
  response-quality results, not real-case detection metrics.
- A separate central-processing-unit compatibility run initialized two
  byte-level transformers from random weights, not a pretrained checkpoint.
  The 74,304-parameter arm changed held-out next-byte loss from 5.5479 to
  5.1164; the 452,224-parameter arm changed it from 5.5990 to 4.7361. Both
  complete NumPy parameter archives passed exact reload verification. This was
  a two-step mechanism check on 16 training and 4 held-out parent lineages,
  not evidence of useful language behavior or domain improvement. Its two
  complete models, configs, curves, graphics, and receipts are public in the
  [DueCare Grounded Byte Model Learning Study](https://www.kaggle.com/datasets/taylorsamarel/duecare-grounded-byte-model-learning-study),
  release-manifest SHA-256
  `9bc416a67de030243429857fa7af4ee7087bead4c85ef2566a3838f6f95e7d4a`.
- The original central-processing-unit-safe notebooks remain public.
  The expanded reviewer path also includes the
  [207,680-row curriculum atlas](https://www.kaggle.com/code/taylorsamarel/duecare-200k-curriculum-visual-atlas),
  [optimization and learning curves](https://www.kaggle.com/code/taylorsamarel/duecare-gemma4-learning-curves),
  [four-arm before/after study](https://www.kaggle.com/code/taylorsamarel/duecare-gemma4-four-arm-before-after),
  [lineage and receipt audit](https://www.kaggle.com/code/taylorsamarel/duecare-grounded-lineage-and-training-receipts),
  [frontier-judge measurement audit](https://www.kaggle.com/code/taylorsamarel/duecare-frontier-judge-measurement-audit),
  [integrated evidence-to-triage system and publication showcase](https://www.kaggle.com/code/taylorsamarel/duecare-training-publication-toolchain),
  and [Gemma 4 TPU training lab](https://www.kaggle.com/code/taylorsamarel/duecare-gemma-4-tpu-lora-training-lab).
  The original reviewer path is:
  [response integrity](https://www.kaggle.com/code/taylorsamarel/duecare-response-corpus-integrity),
  [response training plan](https://www.kaggle.com/code/taylorsamarel/duecare-response-training-plan),
  [response visual explorer](https://www.kaggle.com/code/taylorsamarel/duecare-response-dataset-visual-explorer),
  [large-corpus integrity](https://www.kaggle.com/code/taylorsamarel/duecare-large-corpus-integrity-and-exploration),
  [Gemma 4 plan and smoke preflight](https://www.kaggle.com/code/taylorsamarel/duecare-gemma-4-large-corpus-plan-and-smoke),
  [large-corpus visual explorer](https://www.kaggle.com/code/taylorsamarel/duecare-large-corpus-visual-explorer),
  [loading quickstart](https://www.kaggle.com/code/taylorsamarel/duecare-training-data-loading-quickstart),
  [response-quality baseline](https://www.kaggle.com/code/taylorsamarel/duecare-response-quality-baseline),
  and [training-data quality dashboard](https://www.kaggle.com/code/taylorsamarel/duecare-training-data-quality-dashboard).
- Downloaded Kaggle outputs prove that the response explorer produced 11
  Portable Network Graphics charts and 10 comma-separated-value review tables;
  the large explorer produced 15 charts and 7 tables; the quickstart produced
  3 charts; the response baseline produced 5 charts, metrics, and a report; and
  the cross-dataset quality dashboard produced 4 charts, a split audit, a
  strict summary, and a report.
- The response-quality notebook trained a small term-frequency/
  inverse-document-frequency plus logistic-regression diagnostic on the
  central processing unit. Its test balanced accuracy was 1.0 for text
  features and about 0.533 for the response-length-only comparator. This is a
  shortcut and data-quality diagnostic on contaminated reward labels, not
  evidence that Gemma improved.
- The earlier 24-row public proof datasets and their integrity, training-plan,
  and four-arm evaluation notebooks remain useful for inspecting the release
  contract row by row. They are smaller derived views, not independent
  experiments.
- Real Gemma 4 E2B Low-Rank Adaptation training ran on an NVIDIA GeForce RTX
  4060 Laptop GPU. The stronger run completed 60 optimizer steps, trained
  817,152 of 4,409,128,480 parameters, and produced an adapter with SHA-256
  `93fcb82460b8d7ae21737e1cd88fea711cb8c1f3ee5e82d4f313edc54bcc5347`.
  Its final training loss was 3.282865. On eight held-out grounded-remix rows,
  the declared structural score changed from 0.516667 to 0.666667, a +0.15
  delta. This supports a narrow format-learning observation, not real-world,
  legal-quality, or production-readiness claims.
- The four-arm result is base without harness 0.516667, trained without
  harness 0.666667, base with harness 1.000000, and trained with harness
  1.000000 on
  the declared structural objective. Harness gains are deterministic wrapper
  effects, not proof that factual validation or safety was learned in weights.
- The frozen pairwise judge used the same GLM-5.2 model, advanced context,
  rubric, decoding contract, and both A/B presentation orders across all 32
  verdicts. The context SHA-256 is
  `de96994f586b7d3aa991bdcd7c3f7e2023fc36f129acb788f54e2fab3dea9d3a`;
  the rubric SHA-256 is
  `8d715fca6bfd3cc9fa5cba94d964a7a312d9dd9c7f0c7db3158704c822f490f6`;
  and the judge-study manifest SHA-256 is
  `949a555103d5111eb0b8619f6099d7d9d7ca571777059f12375bc585399a5e97`.
  Its mean training delta was -1.5 without the harness and -0.75 with the
  harness. This model-based measurement did not demonstrate positive lift; it
  is evaluation evidence and is excluded from training. Study summaries now
  also report exact two-sided sign tests and an evidence-scale label (four
  non-tied pairs floor at p = 0.125), so bootstrap intervals at this scale
  cannot be over-read.
- A frozen recorded harmful-request expansion pack (2026-07-16) pins 46 real
  recorded Gemma 4 pairs of 52 qualifying ranked failures; the remaining 6
  lack a complete recorded response pair. It is joined from the actual
  egregiousness ranker and the recorded rich-lift ledger by
  `scripts/build_recorded_harmful_request_expansion.py`, with all 92 blinded
  two-order verdict requests frozen under request-pack SHA-256
  `ab76b2a655fe2245f0bbcd866a01a88e3a14f684bec83fc15c10d08247210232`. The pack
  is `prepared_not_executed`, local evidence only, and training-ineligible;
  running the frozen judge study waits for an explicit execution window.
- Training and judge selection now use a versioned fallback registry. Operator
  overrides are tried first, multiple model and accelerator candidates remain
  available, every attempt is receipted, and a judge model is frozen for an
  entire comparable study after preflight.
- No merged weights, independently demonstrated real-world model lift, legal
  correctness result, or production adapter is claimed.

The documentation-only future dataset surface is
[`kaggle/shared-datasets/training-data/`](../kaggle/shared-datasets/training-data/).
It intentionally contains no `dataset-metadata.json` and no data rows, so it
cannot be mistaken for a publishable Kaggle Dataset directory.

The public proof dataset is generated by
[`scripts/build_kaggle_proof_training_bundle.py`](../scripts/build_kaggle_proof_training_bundle.py),
then normalized and verified by
[`scripts/build_kaggle_training_release.py`](../scripts/build_kaggle_training_release.py).
It is intentionally small so reviewers can inspect every row and every gate.
The two derived dataset views and three companion notebooks are built by
[`scripts/build_kaggle_interim_collection.py`](../scripts/build_kaggle_interim_collection.py).
That builder first reverifies the approved source release, copies training rows
without modification, binds the source approval and SHA-256 manifest, and
labels the collection as interim proof rather than full-flywheel closure.

The two larger public releases are reproducible locally with their exact,
manifest-bound approval files:

```powershell
python scripts/build_response_preference_bundle.py build `
  --output-dir reports/response_preference_candidates/measured_response_v2

python scripts/build_response_kaggle_collection.py `
  --source-manifest reports/response_preference_candidates/measured_response_v2/candidate-manifest.json `
  --output reports/kaggle_publish/response_training_collection_v6 `
  --publication-approval reports/response_preference_candidates/measured_response_v2/publication-approval-2026-07-15.json

python scripts/build_large_multiperspective_training_bundle.py `
  --output-dir reports/multiperspective_training/large_candidate_v1 `
  --train-rows 25600 --validation-rows 2048 --test-rows 2048

python scripts/build_large_kaggle_training_collection.py `
  --source-manifest reports/multiperspective_training/large_candidate_v1/candidate-manifest.json `
  --output-root reports/kaggle_publish/large_training_collection_v4 `
  --publication-approval reports/multiperspective_training/large_candidate_v1/publication-approval-2026-07-15.json
```

The builders remain private-first when no exact approval is supplied. Building
or uploading a dataset still does not train a model; training completion,
adapter production, and model lift require separate artifacts and evaluation.

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

### Multi-perspective synthetic decision data

[`build_multiperspective_training_bundle.py`](../scripts/build_multiperspective_training_bundle.py)
is the deterministic generator for reasoning across roles and time. It defines
a 96,768-row logical space:

```text
12 mechanisms x 3 jurisdiction topologies x 8 perspectives
              x 7 journey stages x 4 temporal lenses x 4 evidence states
              x 3 view modes
```

The perspectives include a worker, newly arrived worker, third-party observer,
family member, NGO caseworker, origin-country official, destination regulator,
and comparative legal scholar. The view modes ask for a bounded single-persona
decision, a two-persona handoff, or a worker/support/origin/destination synthesis.
They are views into shared synthetic case graphs, not independent role labels.
Each graph contains seven dated events, two competing records at every stage,
actor and jurisdiction boundaries, pre-onset warning states, and later records
that are hidden when the focal decision could not have known them.

Every row carries a visible decision scaffold: exact synthetic record IDs and
dates, source/directness tags, authority boundaries, a journey timeline,
supported/inferred/unknown evidence, alternatives and counterfactuals,
jurisdiction questions, retrieval boundaries, and a consent-preserving next
action. Each DPO prompt is the same direct case task as its paired SFT prompt.
Its rejected completion is a plausible direct answer containing one controlled
failure such as single-jurisdiction shortcut, static-time collapse, unsupported
certainty, role overreach, evidence conflation, or action without consent; the
failure diagnosis remains in metadata rather than leaking into the completion.

The default build is a balanced Kaggle-sized preview: 2,048 SFT and 2,048
preference rows, plus 256 validation and 256 test rows. The split unit is an
entire mechanism family: eight mechanisms train, two validate, and two test.
All jurisdiction, persona, journey, time, evidence, and view derivatives of a
held-out mechanism stay out of training. The generated quality audit also
checks exact family isolation, deterministic row gates, PII findings, direct
SFT/DPO prompt alignment, unique rejects, pairwise length balance, axis
reflection, and sampled train-to-holdout content similarity. `--full-matrix`
emits all variants. Countries A, B, and C are placeholders; live rules, fee
caps, offices, and contacts remain retrieval-time facts.

Generation cannot approve its own publication. Build the candidate, inspect
`quality_audit.json`, `source_audit.json`, samples, rights, and license, then
record a separate manifest-bound decision:

```powershell
python scripts/build_multiperspective_training_bundle.py `
  --output-dir reports/multiperspective_training/source_bundle_v3

python scripts/build_multiperspective_training_bundle.py `
  --approve-manifest reports/multiperspective_training/source_bundle_v3/source_manifest.json `
  --approve-as "repository-owner-reviewed-2026-07-14"
```

The manifest includes a full-preview SFT-then-DPO suggestion sized to traverse
the released rows, plus a clearly labeled 60/30-step smoke profile. Both remain
non-executing until A-00 preflight and an explicit user action.

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
- [`build_multiperspective_training_bundle.py`](https://github.com/TaylorAmarelTech/gemma4_comp/blob/master/scripts/build_multiperspective_training_bundle.py)
  generates lineage-isolated multi-persona, journey-stage, temporal, evidence,
  and cross-jurisdiction SFT/preference data with visible decision scaffolds.
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
- [`build_kaggle_proof_training_bundle.py`](https://github.com/TaylorAmarelTech/gemma4_comp/blob/master/scripts/build_kaggle_proof_training_bundle.py)
  generates the public Kaggle proof dataset source bundle: synthetic
  cross-jurisdiction prompts, SFT rows, preference rows, held-out validation
  and test rows, source audit, and publication approval.

For the deeper design and exact gates, see the
[Phase 3 training framework](phase3_training_framework.md),
[fine-tuning data strategy](finetuning_data_strategy.md),
[evidence-grounded synthetic-training blueprint](research/evidence_grounded_synthetic_training_blueprint.md),
[training-dataset publication and safety-evaluation practices](research/training_dataset_publication_and_safety_practices.md),
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
