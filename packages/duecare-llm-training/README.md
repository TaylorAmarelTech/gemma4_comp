# duecare-llm-training

Closes the loop from pipeline outputs → custom Gemma 4 LoRA without
requiring hand-labeled data.

## Why this exists

You have a working harness that produces lots of (document,
classification, extracted entities, edges, findings) tuples. You DO
NOT have a hand-labeled training set. The standard semi-supervised
playbook turns the former into the latter:

1. **Cluster pipeline outputs** by entity type / document category.
2. **Confidence-weighted majority vote** within each cluster
   produces synthetic labels.
3. **Multi-pass agreement** (Stage 3 vs Stage 5b vs Stage 5c) acts
   as a corroboration check.
4. **Cross-document consistency** promotes labels that hold across
   ≥4 documents.
5. **Tool-call validation** (when `lookup_statute` confirmed a fee
   violation) produces strong positive labels.
6. **Active learning queue** sends low-confidence items to a human
   for one-click review — those reviews become training data
   immediately.

The output is a plain JSONL file ready for Unsloth.

## Pipeline overview

```
EvidenceStore (DuckDB)
       │
       ▼
duecare.training.labels.SyntheticLabelGenerator
       │   four strategies, weighted vote
       ▼
labeled_examples table   ←── duecare.training.review.ReviewQueue
       │                        (CLI / web for human-in-the-loop)
       ▼
duecare.training.dataset.UnslothDatasetBuilder
       │   chat-format JSONL, stratified splits
       ▼
duecare.training.trainer.UnslothTrainer
    (gated by MM_TRAINING_ENABLED + GPU check; "Coming Soon"
     scaffold today, real kickoff hand-off to NB 530)
```

## CLI

```bash
duecare train labels --strategy all --min-confidence 0.7
duecare train review next                    # one-at-a-time
duecare train dataset --output train.jsonl
duecare train kickoff --dry-run              # always works
duecare train kickoff                        # gated
duecare train status
```

## What's deliberately simple

- Embeddings are optional (sentence-transformers preferred but a
  TF-IDF fallback works).
- Clustering is HDBSCAN by default with a k-means fallback so the
  package runs without `hdbscan` installed.
- The "kickoff" stage today writes a manifest the existing Phase 3
  notebook (`530_phase3_unsloth_finetune`) consumes — we don't
  duplicate the actual training code.
