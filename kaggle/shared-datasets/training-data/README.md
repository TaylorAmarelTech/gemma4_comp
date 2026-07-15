# DueCare advanced training-data contract

Status: **documentation and schema map**. This repository directory contains
no training rows and is not itself a Kaggle upload directory. The generated,
manifest-bound releases are public on Kaggle:

- [DueCare Measured Response Training Corpus](https://www.kaggle.com/datasets/taylorsamarel/duecare-measured-response-training-corpus)
- [DueCare Multiperspective Fine-Tuning Corpus](https://www.kaggle.com/datasets/taylorsamarel/duecare-multiperspective-finetuning-corpus)

Supervised fine-tuning (SFT) trains on inputs paired with reviewed desired
answers. Direct Preference Optimization (DPO) trains from a prompt, a
preferred answer, and a nonpreferred answer. A central processing unit (CPU)
is used for the public lightweight diagnostics; no graphics processing unit
(GPU) fine-tuning is claimed in this release.

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
- Older experimental rows outside the v2 candidate bundle remain
  candidate-only unless regenerated or normalized into the current lineage,
  source, licensing, privacy, and held-out metadata contract.
- The existing tiny adapter artifact is a plumbing smoke check, not model
  quality evidence and not a production release.
- No Gemma training, GPU run, production adapter, merged weights, or
  independently demonstrated model lift was produced by this publication
  slice.

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
