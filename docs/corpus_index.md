# Duecare Corpus Index

> **Current source-of-truth pointer for judges and reviewers.** The exact
> GREP-rule, RAG-document, tool, prompt, rubric, and citation counts are live
> runtime data, not static documentation claims.

Use the workbench and API endpoints below whenever exact counts matter:

- `/api/brand` for live harness and catalog counts.
- `/api/harness-catalog/grep` for the current GREP rule inventory.
- `/api/harness-catalog/rag` for the current RAG corpus inventory.
- `/api/harness-catalog/tools` for tool definitions and backing data.
- `packages/duecare-llm-chat/src/duecare/chat/harness/__init__.py` for the
  canonical in-code GREP, RAG, tool, and grading primitives.

Public prose should use approximate capacity language such as `100+ GREP
rules`, `50+ RAG documents`, and `multiple registered harnesses`. Exact numbers
belong in generated reports, runtime APIs, and reproducibility logs where they
are computed from the current source instead of copied by hand.

To regenerate a static appendix for a release candidate, use:

```bash
python scripts/generate_corpus_index.py
```

Commit generated exact-count appendices only when they are clearly labeled with
the commit SHA and generation date.
