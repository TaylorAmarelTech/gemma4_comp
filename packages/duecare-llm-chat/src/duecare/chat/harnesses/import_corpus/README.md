# Import Corpus harness

User-attached evidence: ZIPs and snippets the chat surface retrieves from.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/import/upload` | accept ZIP / single text file |
| POST | `/api/import/snippet` | paste a single titled snippet |
| GET | `/api/import/list` | metadata for the store |
| GET | `/api/import/{doc_id}` | full body of one doc |
| DELETE | `/api/import/{doc_id}` | remove one doc |
| DELETE | `/api/import` | clear the store |

## Why `applied_layers = ()`

This is a CRUD surface, not an LLM-bearing one. Gemma 4 sees imported
docs only at chat time via the chat harness's import toggle; the
import_corpus harness itself never calls Gemma.

## State

All state lives in `app.py` module-level globals (`_IMPORT_STORE`,
`_IMPORT_LOCK`, `_import_*` helpers — BM25 indexing, chunk extraction,
LRU eviction). This module just wires FastAPI routes to them.
