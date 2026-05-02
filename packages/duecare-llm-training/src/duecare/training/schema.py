"""Tables this package adds to the evidence store. Created lazily on
first SyntheticLabelGenerator/ReviewQueue/TrainingRunsTable use so the
core EvidenceStore doesn't have to know about training.
"""
from __future__ import annotations


_DDL_LABELED_EXAMPLES = """
CREATE TABLE IF NOT EXISTS labeled_examples (
    example_id          TEXT PRIMARY KEY,
    run_id              TEXT,
    target_kind         TEXT NOT NULL,        -- 'document_category' | 'entity_type' | 'fee_legitimacy' | 'finding_severity'
    target_id           TEXT NOT NULL,        -- doc_id / entity_id / finding_id
    input_text          TEXT NOT NULL,
    input_image_path    TEXT,
    label               TEXT NOT NULL,
    confidence          REAL DEFAULT 0,
    source_strategy     TEXT NOT NULL,        -- 'cluster_vote' | 'multi_pass_agreement' | ...
    review_status       TEXT DEFAULT 'auto',  -- 'auto' | 'pending_review' | 'human_approved' | 'human_rejected'
    review_notes        TEXT,
    created_at          TIMESTAMP NOT NULL,
    reviewed_at         TIMESTAMP
);
"""

_DDL_TRAINING_RUNS = """
CREATE TABLE IF NOT EXISTS training_runs (
    training_run_id     TEXT PRIMARY KEY,
    started_at          TIMESTAMP NOT NULL,
    completed_at        TIMESTAMP,
    status              TEXT NOT NULL,        -- 'pending' | 'running' | 'completed' | 'failed' | 'dry_run'
    base_model          TEXT,
    n_examples          INTEGER DEFAULT 0,
    n_train             INTEGER DEFAULT 0,
    n_val               INTEGER DEFAULT 0,
    n_test              INTEGER DEFAULT 0,
    dataset_path        TEXT,
    output_lora_path    TEXT,
    config_json         TEXT,
    metrics_json        TEXT,
    notes               TEXT
);
"""

_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_labels_target ON labeled_examples (target_kind, target_id)",
    "CREATE INDEX IF NOT EXISTS idx_labels_status ON labeled_examples (review_status)",
    "CREATE INDEX IF NOT EXISTS idx_labels_strategy ON labeled_examples (source_strategy)",
    "CREATE INDEX IF NOT EXISTS idx_labels_confidence ON labeled_examples (confidence)",
    "CREATE INDEX IF NOT EXISTS idx_runs_status ON training_runs (status)",
]


def ensure_tables(store) -> None:
    """Idempotent: create the training tables on first use."""
    for ddl in (_DDL_LABELED_EXAMPLES, _DDL_TRAINING_RUNS):
        store.execute(ddl)
    for ddl in _INDEXES:
        try:
            store.execute(ddl)
        except Exception:
            pass
