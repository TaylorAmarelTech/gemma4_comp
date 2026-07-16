# DueCare advanced training-data contract

Status: **documentation and schema map**. This repository directory contains
no training rows and is not itself a Kaggle upload directory. The generated,
manifest-bound releases are public on Kaggle:

- [DueCare Measured Response Training Corpus](https://www.kaggle.com/datasets/taylorsamarel/duecare-measured-response-training-corpus)
- [DueCare Multiperspective Fine-Tuning Corpus](https://www.kaggle.com/datasets/taylorsamarel/duecare-multiperspective-finetuning-corpus)
- [DueCare Measured Review Curriculum 200K](https://www.kaggle.com/datasets/taylorsamarel/duecare-measured-review-curriculum-200k)
- [DueCare Gemma 4 Adapter Learning Study](https://www.kaggle.com/datasets/taylorsamarel/duecare-gemma4-adapter-learning-study)
- [DueCare Grounded Byte Model Learning Study](https://www.kaggle.com/datasets/taylorsamarel/duecare-grounded-byte-model-learning-study)

Supervised fine-tuning (SFT) trains on inputs paired with reviewed desired
answers. Direct Preference Optimization (DPO) trains from a prompt, a
preferred answer, and a nonpreferred answer. A central processing unit (CPU)
is used for the public lightweight diagnostics. A separate, public Gemma 4
learning study records two real graphics processing unit (GPU) runs and a
relative Low-Rank Adaptation adapter; it remains a research artifact rather
than a production model.

The smaller public proof dataset remains available separately:
[`taylorsamarel/duecare-proof-finetuning-data`](https://www.kaggle.com/datasets/taylorsamarel/duecare-proof-finetuning-data).
That preview proves the release contract row by row.

Two public, purpose-specific views of that same approved preview are also
available: the
[`visible-reasoning SFT preview`](https://www.kaggle.com/datasets/taylorsamarel/duecare-visible-reasoning-sft-preview)
and the
[`preference-pairs preview`](https://www.kaggle.com/datasets/taylorsamarel/duecare-preference-pairs-preview).
They contain exact copies of already approved rows, bind the source release and
approval hashes, and must not be counted as independent experiments. Their
companion [integrity](https://www.kaggle.com/code/taylorsamarel/duecare-training-data-integrity-audit),
[training-plan](https://www.kaggle.com/code/taylorsamarel/duecare-gemma-4-lora-training-starter),
and [evaluation-plan](https://www.kaggle.com/code/taylorsamarel/duecare-four-arm-fine-tuning-evaluation)
notebooks are auxiliary proof surfaces; the default training-plan run is CPU
only and publishes no adapter.

This folder documents what every versioned Kaggle Dataset must contain. It
intentionally uses `dataset-metadata.template.json` instead of Kaggle's active
`dataset-metadata.json` filename. Do not rename it or add data here until an
eligible release bundle passes every gate below.

## Current public release evidence (reviewed 2026-07-15)

- The multiperspective release contains 25,600 SFT training rows, 25,600
  preference-training rows, 2,048 validation rows, and 2,048 test rows. Its
  release-manifest SHA-256 is
  `ea644df422d9e8c43003805f49a227d441e3a952d6deb3ea3e6fb3b6b579211d`.
  Downloaded remote output from its visual explorer contains 15 charts, 7
  review tables, a strict JavaScript Object Notation summary, and a Markdown
  report.
- The measured-response release contains 791 SFT rows, 791 preference pairs,
  1,582 reward-label rows, 184,650 raw-text-free inventory rows, and 6,884
  raw-text-free quarantine rows. Its release-manifest SHA-256 is
  `56fa69c19990c524002e4f91b833faef58648a66d87729a8f4c61dd56722b74b`.
  Downloaded remote visual output contains 11 charts and 10 review tables.
  The package is public and approved for its stated training uses, but its
  benchmark contamination ledger prohibits treating results on the source
  benchmark as independent model-improvement evidence.
- Nine public notebooks provide loading, integrity, visual exploration,
  training plans, a bounded CPU baseline, and cross-dataset split auditing.
- The measured review curriculum contains 207,680 supervised training rows,
  207,680 preference-training pairs, 528 validation rows, and 608 test rows.
  Its release-manifest SHA-256 is
  `1b062ce12fe43494f7d63659a53017c857e0ac0103759d8f71b3340f63bdc2b7`.
  Its apparent scale is augmentation scale: descendants preserve parent hashes
  and are not independent cases.
- The adapter learning study contains two real Gemma 4 E2B Low-Rank Adaptation
  runs and the base/trained by harness/no-harness four-arm record. Its current
  release-manifest SHA-256 is
  `4c300a3b277009e1488979bb6579859a59f0dbfeecf4c31a0d4251ea837572f4`.
  Its recorded harmful-request study uses six real benchmark response pairs,
  one frozen judge, anonymous candidates, and both presentation orders. The
  harness won 6/6 pairs with mean +9.67/10 and a pair-bootstrap 95% interval
  of [+9.0, +10.0]. This is a harmful-request-handling result, not a claim that
  the adapter or harness identifies trafficking victims in real-world data.
  A separate checksummed receipt carries the 911-pair model-judge harness
  result (+1.73/10), the 998-pair deterministic cross-check (+0.18/10), and
  140 adversarial transformations (+4.39/10). Those use synthetic/composite
  prompts and measure response quality, not real-case detection accuracy.
  Start with the public
  [learning curves](https://www.kaggle.com/code/taylorsamarel/duecare-gemma4-learning-curves),
  [four-arm before/after study](https://www.kaggle.com/code/taylorsamarel/duecare-gemma4-four-arm-before-after),
  [lineage and receipts](https://www.kaggle.com/code/taylorsamarel/duecare-grounded-lineage-and-training-receipts),
  [judge audit](https://www.kaggle.com/code/taylorsamarel/duecare-frontier-judge-measurement-audit),
  [integrated evidence-to-triage system and publication showcase](https://www.kaggle.com/code/taylorsamarel/duecare-training-publication-toolchain),
  and [Tensor Processing Unit training lab](https://www.kaggle.com/code/taylorsamarel/duecare-gemma-4-tpu-lora-training-lab).
- Older experimental rows outside the v2 candidate bundle remain
  candidate-only unless regenerated or normalized into the current lineage,
  source, licensing, privacy, and held-out metadata contract.
- The stronger 60-step graphics-processor run trained 817,152 parameters and
  produced a relative adapter with SHA-256
  `93fcb82460b8d7ae21737e1cd88fea711cb8c1f3ee5e82d4f313edc54bcc5347`.
  Its +0.15 structural-score change on eight grounded-remix holdout rows is a
  narrow learning observation, not independent domain-quality evidence.
- A central-processing-unit compatibility run also trained two complete
  byte-level transformers from random weights for two steps per arm. Both
  NumPy parameter archives passed exact reload verification. Held-out
  next-byte loss changed from 5.5479 to 5.1164 and from 5.5990 to 4.7361;
  these are mechanism observations, not useful-language or domain-lift claims.
  The full models and receipts are public under release-manifest SHA-256
  `9bc416a67de030243429857fa7af4ee7087bead4c85ef2566a3838f6f95e7d4a`.
- No merged weights, independently demonstrated victim-identification or
  field-detection lift, legal-quality result, or production release was
  produced by this slice.

## Release contents

Only a separately built, manifest-bound release directory may become a Kaggle
Dataset. Its expected public files are:

| File | Required content |
|---|---|
| `sft-*.jsonl` | Approved final answers, citations, optional deliberately authored visible rationales, row hashes, permissions, and lineage IDs. |
| `preference-*.jsonl` or `dpo-preference-*.jsonl` | Prompt, chosen/rejected answers, preference reason, row hashes, permissions, and lineage IDs. |
| `reward-labels-*.jsonl` | Bounded positive and negative quality labels when that lane exists. |
| validation and test shards | Held-out rows whose prompt and source lineages do not occur in training. |
| `release-manifest.json` | Artifact hashes, schema/generator versions, exact base-model revision, split policy, frozen holdout identities, gate summaries, and source/license inventory. |
| `DATA_CARD.md` | Intended use, exclusions, provenance, licenses, privacy method, limitations, known risks, and reproducibility instructions. |
| `LOADING.md` | Standard local, Kaggle, pandas, Hugging Face Datasets, and Polars loading examples. |
| `croissant.json` | Machine-readable MLCommons Croissant metadata and payload checksums. |
| `dataset-metadata.json` | Final Kaggle metadata created only inside the verified release directory, never copied from this template unchanged. |

Evaluation holdout rows are training-excluded. A public release may describe
their hashes, lineage IDs, rubric, and aggregate results, but it must not place
the held-out prompts into the training files.

## External import contract

The A-00 **Already have a file?** path can inspect JSON, JSONL, or ZIP exports
from DueCare or another controlled system. Inspection does not grant training
or redistribution permission:

1. The importer may identify loose prompt/response, SFT, or preference rows
   and show a validation preview.
2. Training remains blocked until a bundle manifest binds the SFT/DPO files,
   hashes, model revision, licenses, allowed uses, privacy checks, source and
   prompt lineages, frozen holdouts, and clean quality results.
3. Imported final answers, citations, harness/tool traces, and deliberately
   authored model-visible rationales may become review candidates.
4. Provider-private or otherwise hidden chain-of-thought must not be requested,
   inferred, imported, stored, or published. Hidden-thought markup is a
   blocking failure, not a training feature.
5. An external URL, Kaggle attachment, or high judge score never sets
   `safe_to_train` by itself.

## Promotion sequence

1. Complete exact response and per-dimension grading coverage.
2. Curate provenance, licenses, privacy, citations, and unsafe-advice results.
3. Regenerate rows under the current contract and freeze lineage-safe splits.
4. Produce a clean audit and an independently verified release manifest.
5. Build a new release directory containing the files above.
6. Publish and re-download the Kaggle Dataset, verify every checksum, and only
   then attach its immutable version to an updated A-00 notebook.
7. Run SFT and the requested preference stage, followed by untouched four-arm
   evaluation, before considering any adapter release.

See [`docs/training_and_finetuning.md`](../../../docs/training_and_finetuning.md)
and the active
[`A-00 workbench`](../../A-00-omni-experiment-workbench/README.md) for the full
method and executable gates.
