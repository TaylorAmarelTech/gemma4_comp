# ADR-007 -- KnowledgeObject canonical taxonomy

**Status:** Accepted
**Date:** 2026-05-12

## Context

DueCare grows by accumulating reusable artefacts: regex rules, retrieval
docs, citation links, persona prompts, tool definitions, fact templates,
schemas. Pre-ADR each artefact had its own format. Surfaces (kernel,
website, writeup, system map) used incompatible vocabularies.

## Decision

One canonical envelope -- `KnowledgeObject (v1.0)` -- carries every kind
of knowledge. 6 branches, 21 leaves.

```
KnowledgeObject (v1.0)
+- matching_knowledge   grep_rule | glob_rule | classifier_rule | heuristic_rule
+- grounding_knowledge  rag_doc | citation_edge | corridor_profile | ngo_directory
+- reasoning_knowledge  persona_block | context_snippet | reasoning_step | rubric_dimension
+- tool_knowledge       tool_definition | tool_example | tool_chain
+- input_knowledge      fact_template | upload_schema | prompt_template
+- output_knowledge     envelope_schema | audit_template | submission_schema
```

Envelope: `{schema_version: "1.0", knowledge_object_type, id, version,
provenance, content, tags, extensions}`.

## Consequences

- One persistence: `/kaggle/working/knowledge/<type>/<id>.json`
- One runtime API: `POST /api/knowledge/promote`, `GET /list?branch=?type=?`,
  `GET /api/knowledge/{type}/{id}`, `POST /import`, `GET /export`,
  `GET /api/knowledge/taxonomy`
- One vocabulary across kernel / website / writeup / system map
- 5-step expansion contract (docs/knowledge_module_schema.md Section 8)

## Alternatives rejected

1. Flat type list (no branches) -- 21+ flat names are unbrowseable.
2. Per-kind formats with meta-registry -- expensive per-kind work.
3. YAML envelope -- JSON beats YAML for diff + round-trip.

## References

- `docs/knowledge_module_schema.md` -- canonical spec
- `docs/data_primitives.md` Section 0 -- website-side mirror
- `packages/duecare-llm-chat/src/duecare/chat/app.py` -- `KO_BRANCHES`
- `packages/duecare-llm-chat/src/duecare/chat/static/knowledge.html` -- UI
