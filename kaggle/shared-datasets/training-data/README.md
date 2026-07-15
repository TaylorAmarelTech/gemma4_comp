# DueCare advanced training data release template

Status: **documentation-only and not publishable**. No training rows, Kaggle
Dataset, production adapter, or merged weights are present in this directory.
The public proof dataset is separate:
[`taylorsamarel/duecare-proof-finetuning-data`](https://www.kaggle.com/datasets/taylorsamarel/duecare-proof-finetuning-data).
That preview proves the release contract; this folder remains the template for
a future full advanced corpus.

This folder documents what a future versioned Kaggle Dataset must contain. It
intentionally uses `dataset-metadata.template.json` instead of Kaggle's active
`dataset-metadata.json` filename. Do not rename it or add data here until an
eligible release bundle passes every gate below.

## Current blockers (reviewed 2026-07-15)

- `kaggle/A-00-omni-experiment-workbench/kernel-metadata.json` attaches the
  proof dataset. That preview is intentionally small and does not replace this
  future full-corpus template.
- The current larger multi-perspective source candidate is locally clean under
  the v2 quality audit, but it is not a publishable Kaggle Dataset until it has
  a separate publication approval and release manifest.
- Older experimental rows outside the v2 candidate bundle remain
  candidate-only unless regenerated or normalized into the current lineage,
  source, licensing, privacy, and held-out metadata contract.
- The existing tiny adapter artifact is a plumbing smoke check, not model
  quality evidence and not a production release.

## Future release contents

Only a separately built, manifest-bound release directory may become a Kaggle
Dataset. Its expected public files are:

| File | Required content |
|---|---|
| `sft_train.jsonl` | Approved final answers, citations, optional deliberately authored visible rationales, row hashes, permissions, and lineage IDs. |
| `preference_train.jsonl` | Prompt, chosen/rejected answers, preference reason, row hashes, permissions, and lineage IDs. |
| `validation.jsonl` | Validation-only rows whose prompt and source lineages do not occur in training. |
| `release-manifest.json` | Artifact hashes, schema/generator versions, exact base-model revision, split policy, frozen holdout identities, gate summaries, and source/license inventory. |
| `DATA_CARD.md` | Intended use, exclusions, provenance, licenses, privacy method, limitations, known risks, and reproducibility instructions. |
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
