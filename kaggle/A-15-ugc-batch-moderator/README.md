# A-14 — UGC batch moderator

<!-- duecare:lane-label -->
> **Serves lanes:** 01 Platform safety

## Status

**Folder reserved; kernel.py pending.** This slot will:

1. Accept a CSV/JSONL of inbound posts/ads/listings via upload
2. Run each through the harness (Persona + GREP + RAG + Tools)
3. Produce a risk envelope per row: score / verdict / indicators /
   citations / suggested action
4. Emit a v1.0 batch bundle with per-row results + aggregate
   summary
5. Render top-indicators / corridor-concentration / false-positive
   examples in the workbench shell

Closes Lane 01 gap (the website's primary audience for the
"screen exploitative UGC at scale" use case).

See `docs/appendix_experiment_ladder.md` for the full ladder spec.
