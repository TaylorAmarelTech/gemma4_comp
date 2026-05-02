# duecare-llm-evidence-db

Queryable evidence store for the Duecare pipeline. Persists everything the
multimodal-graph pipeline produces — entities, edges, findings, tool-call
results, document metadata, bundle summaries — into a single normalised
schema that can be queried via SQL or via natural language (through
`duecare-llm-nl2sql`).

**Default backend:** local DuckDB (zero-config, in-process, fast).
**Other backends:** SQLite (mobile/edge) and PostgreSQL (multi-NGO server).

## Quickstart

```python
from duecare.evidence import EvidenceStore

store = EvidenceStore.open("duecare.duckdb")             # local DuckDB
store.ingest_run("/path/to/multimodal_v1_output")        # pulls every JSON
print(store.run_template("avg_fee_by_corridor"))         # parameterised query
store.close()
```

## Backends

| Backend | Connection string | Use for |
|---|---|---|
| DuckDB | `"duecare.duckdb"` or `"duckdb:///path/to/file.db"` | demos, single-user, default |
| SQLite | `"sqlite:///path/to/file.db"` | mobile, edge |
| PostgreSQL | `"postgresql://user:pass@host:port/db"` | NGO server, multi-user |
