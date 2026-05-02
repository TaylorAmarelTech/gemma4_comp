"""Evidence-store schema. Backend-agnostic SQL DDL.

Every table is normalised so the same schema works under DuckDB, SQLite,
and PostgreSQL with at most light dialect tweaks (handled by the backend
modules in `backends/`).

Schema version is monotonic; migrations live in `_migrations` and run on
`EvidenceStore.open(...)` if the persisted version is older.
"""
from __future__ import annotations

SCHEMA_VERSION = 1


# ---------------------------------------------------------------------------
# DDL -- written once, used by every backend. Backend modules apply small
# dialect tweaks (e.g. SERIAL vs INTEGER PRIMARY KEY AUTOINCREMENT).
# ---------------------------------------------------------------------------
_DDL_RUNS = """
CREATE TABLE IF NOT EXISTS runs (
    run_id              TEXT PRIMARY KEY,
    started_at          TIMESTAMP NOT NULL,
    completed_at        TIMESTAMP,
    pipeline_version    TEXT NOT NULL,
    input_root          TEXT,
    n_documents         INTEGER DEFAULT 0,
    n_entities          INTEGER DEFAULT 0,
    n_edges             INTEGER DEFAULT 0,
    n_findings          INTEGER DEFAULT 0,
    config_json         TEXT
);
"""

_DDL_DOCUMENTS = """
CREATE TABLE IF NOT EXISTS documents (
    doc_id              TEXT PRIMARY KEY,
    run_id              TEXT NOT NULL,
    image_path          TEXT NOT NULL,
    source_pdf          TEXT,
    bundle              TEXT,
    category            TEXT,
    language            TEXT,
    parsed_at           TIMESTAMP NOT NULL,
    page_count          INTEGER DEFAULT 1,
    triage_score        REAL,
    raw_response        TEXT,
    parsed_response     TEXT
);
"""

_DDL_ENTITIES = """
CREATE TABLE IF NOT EXISTS entities (
    entity_id           TEXT PRIMARY KEY,
    run_id              TEXT NOT NULL,
    etype               TEXT NOT NULL,
    canonical_name      TEXT NOT NULL,
    raw_spellings_json  TEXT,
    doc_count           INTEGER DEFAULT 0,
    bundle_count        INTEGER DEFAULT 0,
    severity_max        REAL DEFAULT 0,
    consolidated_from_json TEXT
);
"""

_DDL_ENTITY_DOC = """
CREATE TABLE IF NOT EXISTS entity_documents (
    entity_id           TEXT NOT NULL,
    doc_id              TEXT NOT NULL,
    raw_spelling        TEXT,
    page                INTEGER,
    confidence          REAL,
    source              TEXT,
    PRIMARY KEY (entity_id, doc_id)
);
"""

_DDL_EDGES = """
CREATE TABLE IF NOT EXISTS edges (
    edge_id             TEXT PRIMARY KEY,
    run_id              TEXT NOT NULL,
    a_entity_id         TEXT NOT NULL,
    b_entity_id         TEXT NOT NULL,
    relation_type       TEXT,
    confidence          REAL DEFAULT 0,
    doc_count           INTEGER DEFAULT 0,
    source              TEXT,
    evidence_text       TEXT,
    gemma_confirmed     BOOLEAN DEFAULT FALSE,
    gemma_confidence    REAL,
    gemma_reasoning     TEXT
);
"""

_DDL_EDGE_DOC = """
CREATE TABLE IF NOT EXISTS edge_documents (
    edge_id             TEXT NOT NULL,
    doc_id              TEXT NOT NULL,
    PRIMARY KEY (edge_id, doc_id)
);
"""

_DDL_FINDINGS = """
CREATE TABLE IF NOT EXISTS findings (
    finding_id          TEXT PRIMARY KEY,
    run_id              TEXT NOT NULL,
    doc_id              TEXT,
    bundle              TEXT,
    trigger_name        TEXT NOT NULL,
    finding_type        TEXT NOT NULL,
    severity            REAL DEFAULT 0,
    statute_violated    TEXT,
    jurisdiction        TEXT,
    fee_value           TEXT,
    scheme_pattern      TEXT,
    raw_response        TEXT,
    parsed_json         TEXT,
    detected_at         TIMESTAMP NOT NULL
);
"""

_DDL_TOOL_CACHE = """
CREATE TABLE IF NOT EXISTS tool_call_cache (
    call_id             TEXT PRIMARY KEY,
    tool_name           TEXT NOT NULL,
    args_hash           TEXT NOT NULL,
    args_json           TEXT NOT NULL,
    result_json         TEXT NOT NULL,
    fetched_at          TIMESTAMP NOT NULL,
    ttl_seconds         INTEGER DEFAULT 86400,
    hit_count           INTEGER DEFAULT 1
);
"""

_DDL_BUNDLE_SUMMARIES = """
CREATE TABLE IF NOT EXISTS bundle_summaries (
    bundle              TEXT PRIMARY KEY,
    run_id              TEXT NOT NULL,
    n_documents         INTEGER DEFAULT 0,
    n_entities          INTEGER DEFAULT 0,
    n_findings          INTEGER DEFAULT 0,
    severity_max        REAL DEFAULT 0,
    brief_text          TEXT,
    top_actors_json     TEXT,
    generated_at        TIMESTAMP NOT NULL
);
"""

_DDL_PAIRWISE_LINKS = """
CREATE TABLE IF NOT EXISTS pairwise_links (
    link_id             TEXT PRIMARY KEY,
    run_id              TEXT NOT NULL,
    doc_a_id            TEXT NOT NULL,
    doc_b_id            TEXT NOT NULL,
    relationship_type   TEXT,
    confidence          REAL DEFAULT 0,
    explanation         TEXT,
    visual_similarities_json TEXT,
    shared_entities_json TEXT
);
"""

_DDL_SCHEMA_META = """
CREATE TABLE IF NOT EXISTS schema_meta (
    key                 TEXT PRIMARY KEY,
    value               TEXT
);
"""


# Index DDL -- separate from table creation so backends that don't
# support some clauses can skip silently.
_INDEXES = [
    ("idx_doc_run",          "CREATE INDEX IF NOT EXISTS idx_doc_run ON documents (run_id)"),
    ("idx_doc_bundle",       "CREATE INDEX IF NOT EXISTS idx_doc_bundle ON documents (bundle)"),
    ("idx_doc_category",     "CREATE INDEX IF NOT EXISTS idx_doc_category ON documents (category)"),
    ("idx_ent_run",          "CREATE INDEX IF NOT EXISTS idx_ent_run ON entities (run_id)"),
    ("idx_ent_etype",        "CREATE INDEX IF NOT EXISTS idx_ent_etype ON entities (etype)"),
    ("idx_ent_doccount",     "CREATE INDEX IF NOT EXISTS idx_ent_doccount ON entities (doc_count)"),
    ("idx_entdoc_doc",       "CREATE INDEX IF NOT EXISTS idx_entdoc_doc ON entity_documents (doc_id)"),
    ("idx_edge_run",         "CREATE INDEX IF NOT EXISTS idx_edge_run ON edges (run_id)"),
    ("idx_edge_relation",    "CREATE INDEX IF NOT EXISTS idx_edge_relation ON edges (relation_type)"),
    ("idx_find_run",         "CREATE INDEX IF NOT EXISTS idx_find_run ON findings (run_id)"),
    ("idx_find_trigger",     "CREATE INDEX IF NOT EXISTS idx_find_trigger ON findings (trigger_name)"),
    ("idx_find_severity",    "CREATE INDEX IF NOT EXISTS idx_find_severity ON findings (severity)"),
    ("idx_tool_args_hash",   "CREATE INDEX IF NOT EXISTS idx_tool_args_hash ON tool_call_cache (tool_name, args_hash)"),
    ("idx_pair_a",           "CREATE INDEX IF NOT EXISTS idx_pair_a ON pairwise_links (doc_a_id)"),
    ("idx_pair_b",           "CREATE INDEX IF NOT EXISTS idx_pair_b ON pairwise_links (doc_b_id)"),
]


ALL_TABLES = [
    "schema_meta",
    "runs",
    "documents",
    "entities",
    "entity_documents",
    "edges",
    "edge_documents",
    "findings",
    "tool_call_cache",
    "bundle_summaries",
    "pairwise_links",
]


def all_ddl() -> list[str]:
    """Return every CREATE TABLE statement in dependency order."""
    return [
        _DDL_SCHEMA_META,
        _DDL_RUNS,
        _DDL_DOCUMENTS,
        _DDL_ENTITIES,
        _DDL_ENTITY_DOC,
        _DDL_EDGES,
        _DDL_EDGE_DOC,
        _DDL_FINDINGS,
        _DDL_TOOL_CACHE,
        _DDL_BUNDLE_SUMMARIES,
        _DDL_PAIRWISE_LINKS,
    ]


def all_indexes() -> list[tuple[str, str]]:
    """Return [(name, ddl), ...] for every index. Backend can skip on
    unsupported syntax."""
    return list(_INDEXES)
