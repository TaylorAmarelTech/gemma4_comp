# Data Primitives

This page defines the shared artifact shapes used by active Kaggle kernels,
demo exports, and reviewer handoff bundles.

## BundleEnvelope v1.0

Use `duecare.appendix_primitives.BundleEnvelope` and
`duecare.appendix_primitives.write_v1_bundle()` when a kernel writes a
portable run artifact under `/kaggle/working`.

Required top-level fields:

| Field | Type | Meaning |
|---|---|---|
| `schema_version` | string | Literal `"1.0"` for this envelope contract. |
| `kernel_id` | string | Stable kernel or surface identifier. |
| `run_id` | string | Unique run identifier, normally from `make_run_id()`. |
| `config` | object | Runtime settings needed to reproduce the run. |
| `metadata` | object | Timestamps, model identifiers, git sha, dataset version, or other run metadata. |
| `summary` | object | Small aggregate summary for dashboards and reviewers. |
| `results` | array | Per-row outputs with prompt/source ids, response or extracted facts, trace fields, and row-level errors when present. |

Minimal shape:

```json
{
  "schema_version": "1.0",
  "kernel_id": "01-duecare-exploration-workbench",
  "run_id": "demo_20260519_000000",
  "config": {},
  "metadata": {},
  "summary": {},
  "results": []
}
```

`write_v1_bundle()` writes four reviewer-friendly artifacts:

- `<RUN_ID>_results.json` - the full `BundleEnvelope`.
- `<RUN_ID>_run.jsonl` - one result per line.
- `<RUN_ID>_metadata.json` - envelope metadata without the heavy results array.
- `<RUN_ID>_bundle.zip` - manifest plus the files above.

## KnowledgeObject Envelope

Knowledge extraction and sharing use reviewable KnowledgeObject envelopes.
They should remain draft objects until a human promotes them into a local pack.

Common fields:

| Field | Meaning |
|---|---|
| `schema_version` | Knowledge-object schema version. |
| `knowledge_object_type` | Target taxonomy leaf such as GREP rule, RAG document, context snippet, contact, or rubric dimension. |
| `id` | Stable kebab-case object id. |
| `version` | Object version. |
| `provenance` | Source hash, run id, reviewer, and timestamps. |
| `content` | Typed content for the selected leaf. |
| `extensions` | Optional trace, grounding, or review metadata. |

## Validation

Run the public-surface validator before opening a PR:

```bash
python scripts/validate_public_surface.py
```

The `bundle_envelope_v1` check flags kernels that emit custom
`schema_version` strings, legacy aggregate-only fields, or result arrays that
are not exposed as top-level `results[]`.

