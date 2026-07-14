# duecare-llm-training

Closes the loop from pipeline outputs to a custom Gemma 4 LoRA without
requiring hand-labeled data.

## Why this exists

You have a working harness that produces many document, classification,
entity, edge, and finding records. You do not automatically have an approved
training set. The semi-supervised workflow turns reviewed records into
candidate data:

1. **Cluster pipeline outputs** by entity type or document category.
2. **Confidence-weighted majority vote** within each cluster produces
   synthetic labels.
3. **Multi-pass agreement** acts as a corroboration check.
4. **Cross-document consistency** promotes labels that hold across multiple
   documents.
5. **Tool-call validation** can support high-confidence positive labels.
6. **Active learning review** sends low-confidence items to a human before
   they become candidate training data.

The output is chat-format JSONL that must pass the canonical training gates
before use.

## Pipeline overview

```text
EvidenceStore (DuckDB)
       |
       v
duecare.training.labels.SyntheticLabelGenerator
       |   weighted multi-strategy vote
       v
labeled_examples table <--- duecare.training.review.ReviewQueue
       |                        (human-in-the-loop)
       v
duecare.training.dataset.UnslothDatasetBuilder
       |   candidate chat JSONL + stratified splits
       v
duecare.training.trainer.UnslothTrainer
       |   plan only; direct training fails closed
       v
scripts/training_engine.py or kaggle/A-00-omni-experiment-workbench
       quality + privacy + provenance + integrity + held-out gates
       then SFT + DPO on an explicitly enabled GPU run
```

## CLI

```bash
duecare train labels --strategy all --min-confidence 0.7
duecare train review next
duecare train dataset --output train.jsonl
duecare train kickoff --dry-run
duecare train status
```

The package kickoff writes a plan but never starts an unaudited run. Use
`python scripts/training_engine.py --with-gpu` for the strict local or
GPU-hosted path, or attach the verified training bundle in
`kaggle/A-00-omni-experiment-workbench`.

Candidate data is not approved training data until the quality, privacy,
provenance, integrity, license, and held-out-contamination gates pass. Hidden
chain-of-thought is excluded: targets may contain only visible answers or
deliberately authored, reviewable structured rationale.

## What's deliberately simple

- Embeddings are optional; sentence-transformers is preferred and a TF-IDF
  fallback is available.
- Clustering uses HDBSCAN when installed and otherwise falls back to k-means.
- This package is a data-preparation and planning surface. The canonical
  training engine owns GPU execution, evaluation, and registration.
