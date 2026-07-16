# Training-dataset publication and safety-evaluation practices

Last reviewed: 2026-07-15

This guide turns current practices from Google, Hugging Face, MLCommons,
Kaggle, and established safety-evaluation projects into a practical adoption
plan for DueCare. It covers dataset design, fine-tuning, publishing, loading,
adapter management, human review, and defensive jailbreak evaluation.

The short recommendation is:

1. Keep checksummed JavaScript Object Notation Lines (JSON Lines) as the
   authoritative release format.
2. Publish small comma-separated values (CSV) previews and, when useful,
   optional Parquet analytics mirrors.
3. Add Machine Learning Commons Croissant metadata, plain-language loading
   instructions, a dataset card, a source and rights record, limitations, and
   exact release checksums.
4. Keep supervised fine-tuning examples, preference pairs, reward labels, and
   evaluation prompts in separate lanes.
5. Split by source lineage or scenario family, not by individual row.
6. Keep jailbreak and red-team material in versioned, held-out safety
   evaluation lanes unless a separate review explicitly approves a training
   use.
7. Compare the unchanged base model, each trained adapter, the harness alone,
   and the adapter plus harness on a lineage-independent evaluation set.

## Terms used in this guide

- **Supervised fine-tuning** means updating a model using examples that pair an
  input with the desired answer. It is sometimes abbreviated as **SFT**.
- **Direct Preference Optimization** is a method that trains a model from a
  prompt, a preferred response, and a nonpreferred response. It is sometimes
  abbreviated as **DPO**.
- **Low-Rank Adaptation** is a parameter-efficient method that trains small
  adapter weights while leaving most base-model weights frozen. It is
  sometimes abbreviated as **LoRA**.
- **Quantized Low-Rank Adaptation** applies Low-Rank Adaptation while the base
  model is stored in a lower-precision representation to reduce memory use. It
  is sometimes abbreviated as **QLoRA**.
- **Personally identifiable information** is data that can identify or help
  identify a person. It is sometimes abbreviated as **PII**.
- **JSON Lines** stores one complete JavaScript Object Notation object on each
  line. Files commonly use the `.jsonl` extension.
- **Parquet** is a compressed, column-oriented file format designed for fast
  analytics and selective column loading.
- **Croissant** is an MLCommons metadata format that describes a dataset's
  identity, license, resources, checksums, record structure, and machine
  learning use.
- **Adapter** means the smaller set of trained weights produced by a
  parameter-efficient fine-tuning method. The original base model remains a
  separate dependency unless the adapter is deliberately merged.
- **Contamination** means that information used to construct or select
  training data also appears in an evaluation set, making that evaluation
  unsuitable as independent evidence of improvement.
- **Pretraining from random initialization** starts with newly sampled model
  weights and learns next-token prediction without loading a pretrained
  checkpoint. It is not fine-tuning.
- **Continued pretraining** starts from an existing checkpoint and continues
  next-token training on a new mixture before task-specific post-training.
- **Post-training** is the broad stage after pretraining that can include
  supervised fine-tuning, preference optimization, reward modeling, and
  reinforcement learning.
- **Model resolution receipt** records every configured model or accelerator
  route, its preflight or execution result, the selected route, immutable
  revision information when available, and the reason any route failed.

## Recommended release architecture

Use three layers instead of one undifferentiated dataset.

### 1. Authoritative data layer

The authoritative layer should be immutable, checksummed JSON Lines shards.
Each row should carry a stable identifier, split, lineage, allowed use,
license or rights status, privacy result, and a row checksum.

JSON Lines remains the best primary format here because it is readable,
streamable, diffable at the row level, and natively supported by common
training libraries. Hugging Face describes one-object-per-line JSON as the
most efficient JSON layout for its Datasets library. See the
[Hugging Face loading guide](https://huggingface.co/docs/datasets/loading).

### 2. Discovery and analytics layer

Provide all of the following:

- small, text-safe CSV previews for Kaggle's browser;
- a machine-readable lane and split catalog;
- optional Parquet mirrors for fast exploration of large, approved tables;
- charts and aggregate summaries produced by a notebook;
- Croissant metadata with file locations, formats, sizes, and Secure Hash
  Algorithm 256-bit checksums.

Parquet should be a mirror rather than the only source of truth. Its columnar
layout is faster for large analytical queries, while JSON Lines keeps the
release easy to inspect and verify. The
[Hugging Face loading guide](https://huggingface.co/docs/datasets/loading)
documents both formats, and the official
[Kagglehub loader](https://github.com/Kaggle/kagglehub/blob/main/README.md)
supports pandas, Hugging Face Datasets, and Polars adapters for JSON Lines and
Parquet.

### 3. Governance layer

Every release should include:

- `README.md`: a short reviewer route;
- `DATA_CARD.md`: intended uses, prohibited uses, composition, collection or
  generation process, known biases, and maintenance plan;
- `SCHEMA.md`: field meanings, required fields, and examples;
- `LOADING.md`: local, Kaggle, pandas, Hugging Face Datasets, and Polars
  loading examples;
- `SOURCES.md`: exact source lineage and rights status;
- `LIMITATIONS.md`: contamination, representativeness, grading, and legal
  limitations;
- `LICENSE`: the exact release license and any row-level exceptions;
- `CITATION.cff`: citation metadata;
- `croissant.json`: interoperable dataset metadata;
- `release-manifest.json`: exact artifacts, byte counts, checksums, row counts,
  release state, and claim state;
- a quarantine summary that contains reason codes and counts without unsafe
  raw text.

The [Croissant format specification](https://docs.mlcommons.org/croissant/docs/croissant-spec.html)
requires a versioned conformance declaration, description, license, name, URL,
creator, publication date, and file distributions. It also supports typed
record sets and responsible artificial intelligence metadata.

## Training lanes and schemas

Do not mix every record into one table and rely on a notebook to infer its
purpose. Publish explicit lanes.

### Supervised fine-tuning lane

Use this lane only for reviewed positive targets.

```json
{
  "row_id": "stable-id",
  "messages": [
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "reviewed desired answer"}
  ],
  "split": "train",
  "lineage_family_id": "family-id",
  "assistant_target_allowed": true,
  "source_manifest_sha256": "...",
  "sha256": "..."
}
```

### Preference lane

Use an explicit prompt and same-prompt preferred and nonpreferred responses.

```json
{
  "row_id": "stable-id",
  "prompt": "...",
  "chosen": "reviewed preferred answer",
  "rejected": "nonpreferred answer",
  "split": "train",
  "lineage_family_id": "family-id",
  "preference_source": "bounded rubric comparison",
  "sha256": "..."
}
```

Hugging Face's Transformer Reinforcement Learning library recommends explicit
prompt preference records for Direct Preference Optimization. Its
[dataset-format guide](https://huggingface.co/docs/trl/en/dataset_formats)
also distinguishes supervised fine-tuning, preference, reward, and prompt-only
datasets.

### Reward-label lane

Use this lane for response-quality classification or reward-model research.
The nonpreferred answer must not silently become a positive assistant target.

```json
{
  "row_id": "stable-id",
  "prompt": "...",
  "response": "...",
  "label": 0,
  "assistant_target_allowed": false,
  "split": "train",
  "lineage_family_id": "family-id",
  "sha256": "..."
}
```

### Prompt-only evaluation lane

Evaluation prompts should remain separate from training targets. Store the
expected rubric, threat category, success condition, refusal boundary, source,
and version, but do not store a target answer when that would leak the test.

### Quarantine lane

Quarantine is not a negative-training lane. It is an audit lane. Keep only
safe metadata such as row hashes, reason codes, counts, and review status when
the raw record is unsafe to redistribute.

## Data-quality and split practices

### Split by mechanism and lineage

Random row splits are insufficient for templated or synthetic data. Keep an
entire scenario graph, prompt family, source document family, worker journey,
or generation seed in one split. Add checks for:

- exact prompt duplicates;
- exact target duplicates;
- normalized text duplicates;
- near duplicates;
- shared source documents;
- shared synthetic graph identifiers;
- shared response bodies across splits;
- evaluation prompts that were used in selection or grading.

### Preserve labeling provenance

Separate these labels rather than flattening them:

- human-authored;
- human-reviewed;
- model-generated;
- model-graded;
- rule-derived;
- adjudicated after disagreement.

Record the grader model and revision, rubric version, prompt version, score
bounds, and review status. For critical subsets, measure agreement between
independent reviewers or graders and report disagreement rather than hiding it.

### Start with a small, trusted experiment

Google's current Gemma guidance recommends choosing a framework, collecting
data, tuning, and then testing with success, failure, and boundary cases. It
also recommends parameter-efficient tuning such as Low-Rank Adaptation when
compute is limited. See
[Google's Gemma fine-tuning guide](https://ai.google.dev/gemma/docs/tune).

For DueCare, the first credible training result should therefore be a bounded
smoke experiment with:

- one pinned base-model revision;
- one exact dataset manifest;
- a small reviewed training subset;
- deterministic seeds where supported;
- recorded package and hardware versions;
- checkpoints and resumability;
- a lineage-independent evaluation set;
- unchanged-base, adapter-only, harness-only, and adapter-plus-harness arms.

## Multi-model and accelerator fallback policy

Do not bury one model identifier in a notebook and call it a pipeline. Every
training, inference, and judge role should resolve through a versioned policy
with at least two capability-compatible candidates. An operator override may
be tried first, but it must not erase the declared fallback list or receipt.

The selection rules differ by task:

- **Training:** try complete model-plus-accelerator combinations in a declared
  order and retain each failure. Never silently replace a failed model with
  deterministic text and report that as training.
- **Comparable evaluation:** preflight several judges, select one, then freeze
  that exact judge, context, rubric, and decoding contract for the full study.
  Switching models halfway through destroys comparability.
- **Interactive inference:** health-check candidates and allow failover, but
  expose the active route in the response receipt so changes are observable.
- **Training from random initialization:** run each declared small architecture
  as its own arm. A larger architecture is not a hidden fallback result for a
  smaller one.

DueCare enforces the minimum candidate count and receipt rule with
`scripts/validate_model_fallback_registry.py`. The current registry is
`configs/duecare/model_fallbacks.json`.

## Fine-tuning versus training from random initialization

Use fine-tuning when the goal is to adapt language behavior with a bounded
dataset and modest compute. Use random-initialization pretraining only when the
research question is about architecture, tokenizer, optimizer, scaling, or a
genuinely new base model. Two hundred thousand examples can support a useful
post-training curriculum, but row count alone is not a pretraining budget:
token count, deduplicated source diversity, model size, context length, and
compute determine whether a new language model learns transferable language.

The public DueCare scratch notebook therefore uses two tiny decoder-only byte
transformers as mechanism studies. A byte tokenizer removes an external
tokenizer dependency and makes save/reload transparent, but it is less
efficient than a trained subword tokenizer for a serious model. Its outputs
must be described as small next-byte models, not frontier large language
models.

For a serious Tensor Processing Unit pretraining project, use a maintained
JAX stack instead of growing the demonstration loop indefinitely. Google's
[MaxText](https://github.com/AI-Hypercomputer/maxtext) combines JAX, Flax,
Optax, Grain, and Orbax for scalable pretraining and post-training, including
Gemma configurations. Use
[Orbax](https://orbax.readthedocs.io/en/latest/api_reference/checkpoint.v1.html)
for atomic, resumable parameter and optimizer-state checkpoints. The Kaggle
scratch notebook still writes a compact NumPy archive and performs an exact
reload check so the educational artifact is self-contained.

## Loading and unloading models and adapters

### Loading datasets

Support these paths in every public release:

1. Python standard-library streaming for zero-dependency verification.
2. pandas for quick charts and tables.
3. Hugging Face Datasets for training and streaming.
4. Kagglehub for loading directly from a Kaggle dataset.
5. Polars lazy loading for fast, memory-conscious analytics.

Do not require a custom executable dataset loader when generic JSON Lines,
CSV, or Parquet files are sufficient. Generic files reduce remote-code risk
and make the release usable outside one framework.

### Loading parameter-efficient adapters

Record the exact base-model identifier and revision, tokenizer revision,
adapter configuration, target modules, precision, and framework versions.
An adapter is not self-contained unless the base model is also available.

### Unloading, merging, and switching adapters

Treat these as distinct operations:

- **Unload without merging:** remove the adapter and return to base-model
  behavior.
- **Activate or switch:** load several adapters but enable only the intended
  one for a run.
- **Merge:** combine adapter weights into the model for inference. Verify the
  merged model before publishing it because this changes deployment and
  rollback behavior.
- **Delete:** remove an adapter configuration and its weights from the active
  model object.

Hugging Face's Parameter-Efficient Fine-Tuning documentation distinguishes
merging, unloading, unmerging, and deleting adapters. Keep the unmerged adapter
as the auditable artifact even if a merged inference copy is created. See the
[Low-Rank Adaptation adapter reference](https://huggingface.co/docs/peft/main/package_reference/lora).

## Defensive jailbreak and safety datasets

### Keep attack data separate from ordinary training data

Jailbreak prompts can be valuable for evaluating robustness, but directly
training on them can leak the test, teach attack syntax, or produce misleading
benchmark gains. The default DueCare policy should be:

- version the source benchmark and its license;
- record threat model, category, template, target model, system prompt, and
  scoring method;
- keep raw attack text access-controlled when redistribution is risky;
- use a held-out subset that never influenced training or threshold choices;
- evaluate both unsafe compliance and excessive refusal of benign requests;
- publish aggregate findings and safe examples, not unsafe operational details;
- require a separate review before promoting any attack prompt into training.

### Useful evaluation projects

- [JailbreakBench](https://github.com/JailbreakBench/jailbreakbench) provides a
  versioned behavior set, artifacts, threat model, chat templates, and scoring
  pipeline. Use it as an isolated benchmark lane after a license review.
- [HarmBench](https://arxiv.org/abs/2402.04249) provides a standardized
  framework for automated red teaming and robust refusal.
- [StrongREJECT](https://arxiv.org/abs/2402.10260) shows that simple refusal
  detection can overstate jailbreak success and evaluates whether a response
  is actually useful and specific to a harmful request.
- [garak](https://github.com/NVIDIA/garak) is an open-source vulnerability
  scanner with probes, detectors, generators, and JSON Lines reports. Run it
  in a separate environment and import only normalized result metadata into
  the comparable evaluation board.
- [Google's safety-evaluation guidance](https://ai.google.dev/responsible/docs/evaluation)
  distinguishes development evaluation, assurance evaluation, red teaming,
  and external evaluation. DueCare should preserve those distinctions.

No single benchmark proves that a model is safe. Use several complementary
benchmarks plus domain-specific success, failure, and boundary cases.

## Tool adoption decisions

| Tool or standard | Decision | DueCare use |
|---|---|---|
| JSON Lines plus release manifests | Adopt now | Authoritative, checksummed rows and provenance. |
| Croissant metadata | Adopt now | Machine-readable dataset identity, resources, checksums, and responsible-use metadata. |
| Kagglehub | Adopt in loading guides | Direct pandas, Hugging Face Datasets, and Polars loading from Kaggle. |
| Hugging Face Datasets | Adopt in loaders and training notebooks | Streaming, split mapping, transformation, and training integration. |
| Transformer Reinforcement Learning | Adopt for planned training | Supervised fine-tuning, preference optimization, and reward-model schemas. |
| Parameter-Efficient Fine-Tuning | Adopt for adapters | Low-Rank Adaptation loading, switching, merging, and unloading. |
| SafeTensors | Adopt for PyTorch model and adapter weights | Non-pickle tensor serialization, explicit metadata, and safer loading. |
| Orbax | Adopt for serious JAX and TPU checkpoints | Save and restore parameter, optimizer, step, and random state with preemption-aware checkpointing. |
| MaxText | Preferred serious TPU pretraining reference | Scalable JAX pretraining and post-training; keep the small Kaggle scratch loop educational. |
| Axolotl | Pilot as a configuration-driven post-training alternative | Gemma 4 support, full tuning, Low-Rank Adaptation, quantized adapters, preference methods, and streaming supervised fine-tuning. |
| LlamaFactory | Pilot as a second portable post-training route | Alpaca and ShareGPT-style datasets in JSON, JSON Lines, CSV, Parquet, or Arrow with explicit dataset metadata. |
| DataTrove | Pilot for scale | Filtering, exact and near deduplication, resumable local or cluster pipelines. |
| Argilla | Pilot for human review | Ranking, correction, disagreement, and adjudication workflows. |
| Microsoft Presidio | Pilot as a secondary privacy detector | Detect and anonymize common personal-data patterns; never treat it as complete. |
| garak | Pilot as an isolated safety-evaluation lane | Reproducible probes and normalized safety findings. |
| JailbreakBench, HarmBench, StrongREJECT | Evaluate licenses, then use held out | Complementary safety and refusal evaluation. |
| Data Version Control | Optional | Reproduce data-pipeline stages and large-artifact versions without committing data to Git. |
| Weights & Biases or MLflow | Optional | Experiment metrics, configurations, and artifact lineage. Keep a local export so evidence is not vendor-locked. |
| NVIDIA NeMo Curator | Later, when GPU scale justifies it | High-volume exact, fuzzy, and semantic deduplication. |
| Distilabel | Pilot only | Synthetic generation and model-feedback pipelines; pin versions and account for its community-maintained status. |
| Language Model Evaluation Harness | Adopt for isolated general benchmarks | Versioned tasks, integrity checks, adapter-aware evaluation, samples, and machine-readable result exports. |

[DataTrove](https://github.com/huggingface/datatrove) is the strongest immediate
candidate for scaling filtering and deduplication because it supports local,
Slurm, and Ray execution. It should be piloted on a copy of a candidate corpus
before becoming a release dependency.

### Privacy-tool boundary

Automated privacy tools are only one layer. Microsoft Presidio explicitly
warns that automated detection cannot guarantee discovery of every sensitive
item. Use deterministic patterns, named-entity detection, source-specific
rules, human review, and a final package scan together. See the
[Presidio documentation](https://microsoft.github.io/presidio/).

## Experiment tracking and reproducibility

Every run should emit a small, portable run manifest containing:

- run identifier and timestamp;
- exact Git commit and dirty-state declaration;
- dataset release-manifest checksum;
- training split and row count;
- base-model identifier and immutable revision;
- tokenizer revision;
- adapter configuration;
- random seeds;
- precision and quantization settings;
- hardware and software versions;
- hyperparameters;
- checkpoint paths and checksums;
- evaluation-set manifest checksum;
- per-arm metrics and confidence intervals where appropriate;
- failure counts and exclusion reasons;
- whether training completed, an adapter was produced, and model lift was
  independently demonstrated.

The portable manifest is authoritative even if a hosted tracker is also used.
Checkpoint resume should restore the optimizer, scheduler, and random state
where the framework supports it.

## Publication ladder

Use explicit states rather than the vague word "ready":

1. **Local candidate:** generated but not approved for training or publication.
2. **Train-approved private candidate:** privacy, rights, quality, and split
   gates allow private experiments.
3. **Public-safe preview:** small, reviewed metadata or examples suitable for
   public education.
4. **Public dataset release:** exact release approved, licensed, checksummed,
   documented, and verified after upload.
5. **Trained adapter:** training completed and adapter files were inspected.
6. **Evaluated adapter:** independent, lineage-separated comparison completed.
7. **Deployment candidate:** operational, safety, privacy, latency, and rollback
   checks completed for a defined environment.

The state must be encoded in the release manifest and repeated in the dataset
card and notebooks.

## Kaggle publication checklist

Before a public push:

- verify the source, candidate, and release manifest checksums;
- verify every shard byte count and row count;
- scan the exact package for credentials, personal information, private paths,
  hidden reasoning fields, and unsafe raw logs;
- confirm row-level and release-level license compatibility;
- confirm train, validation, test, and quarantine lane boundaries;
- confirm family-level split isolation and duplicate checks;
- execute the integrity and visual notebooks against the packaged directory;
- ensure notebooks use the correct Kaggle dataset source and are public only
  when the attached dataset is public;
- ensure each acronym is expanded at first use and a glossary is visible;
- state whether a graphics processing unit was used, whether training ran,
  whether an adapter exists, and whether independent lift was demonstrated;
- push as a new version, download the remote dataset, and verify remote
  checksums and notebook outputs.

## DueCare implementation sequence

### Completed learning slice

1. Published manifest-bound data cards, loading guides, safe previews, and
   Croissant metadata.
2. Published the 207,680-row grounded-remix curriculum with parent lineage.
3. Ran two local Gemma 4 Low-Rank Adaptation experiments and published the
   relative adapters, curves, paired generations, and four-arm study.
4. Ran one frozen, blinded, both-orders frontier-judge study and kept its
   verdicts excluded from training.
5. Published five visual notebooks for curves, four-arm comparison, lineage,
   judge measurement, and the publication toolchain.
6. Ran both random-initialization byte-transformer arms through the labeled
   central-processing-unit fallback, saved complete parameter trees, and
   verified exact reloads. This established the fallback mechanism, not model
   usefulness. Published the models, configs, curves, graphics, and receipts
   as the DueCare Grounded Byte Model Learning Study.

### Current TPU and data-engineering work

1. Complete the public Gemma adapter Tensor Processing Unit notebook using its
   ordered model and accelerator fallbacks.
2. Run the same two random-initialization byte-transformer arms on the public
   Tensor Processing Unit route and compare them with the completed
   central-processing-unit fallback receipt.
3. Pilot DataTrove exact and near-duplicate analysis without replacing parent
   lineage gates.
4. Add Parquet mirrors and streaming examples only when their hashes are bound
   into the same release manifest.
5. Build an independent, lineage-separated evaluation kernel before making
   any broader learning claim.

### Later pilots

1. Evaluate DataTrove on deduplication and resumable processing.
2. Evaluate Argilla for human ranking and adjudication.
3. Evaluate Presidio as a secondary privacy scan.
4. Run garak and selected benchmark suites in isolated safety lanes.
5. Add Parquet mirrors only after measuring storage, load speed, and nested
   schema fidelity against the authoritative JSON Lines files.

## What not to do

- Do not call every nonpreferred response "negative reinforcement training."
  Preference optimization and reward classification are more precise terms.
- Do not place nonpreferred or quarantined text into positive assistant targets.
- Do not publish hidden chain-of-thought or provider-private reasoning.
- Do not use the same benchmark for row selection and independent improvement
  claims.
- Do not merge providers, model revisions, rubrics, or endpoint types in one
  comparable result lane.
- Do not rely on one hard-coded model or accelerator route. Require multiple
  declared candidates, an operator override, preflight, and a selection
  receipt; freeze the selected judge during a comparable study.
- Do not call a tiny random-initialization mechanism run a competitive base
  language model or treat 200,000 augmented rows as 200,000 independent cases.
- Do not treat an automated privacy scan as a guarantee.
- Do not publish an adapter without its base-model dependency, configuration,
  license, run manifest, and evaluation boundary.
- Do not install every available data tool into the core environment. Pilot
  optional tools in isolated environments and promote them only when they
  improve a measured bottleneck.
