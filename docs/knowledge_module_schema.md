# DueCare KnowledgeObject schema (kernel-side mirror)

> **Purpose.** A single standardized envelope shape that the kernel
> emits, the harness re-digests, and the public hub at
> [`duecare-ai.com`](https://duecare-ai.com) accepts. Mirrors the
> website-side KnowledgeObject defined in `apps/duecare-ai.com/app/schema.py`
> (see `docs/data_primitives.md` Section 0).

## 1. Envelope shape

```json
{
  "schema_version": "1.0",
  "knowledge_object_type": "grep_rule" | "rag_doc" | "citation_edge"
                           | "fact_template" | "context_snippet",
  "id": "<kebab-case-slug>",
  "version": "v1",
  "provenance": {
    "created_at": "2026-05-12T19-30-00Z",
    "created_by": "kernel-01|caseworker|automated",
    "source_run_id": "01_process_2026-05-12T19-25-00Z",
    "source_row_ids": ["row_3", "row_7"]
  },
  "content": { /* type-specific; see Section 2 */ },
  "tags": ["corridor:PH-HK", "indicator:fee_camouflage"],
  "extensions": {}
}
```

Required: `schema_version`, `knowledge_object_type`, `id`, `content`.
Optional but recommended: `version`, `provenance`, `tags`, `extensions`.

## 2. Per-type `content` payloads

### 2.1 `grep_rule`

Re-digested as a regex pattern in the GREP layer.

```json
{
  "rule_id": "ph_hk_placement_fee_zero_cap",
  "category": "fee_bondage",
  "severity": "low|medium|high|critical",
  "pattern": "(?i)placement\\s+fee\\s*[:=]\\s*(?:PHP|HKD)\\s*[1-9]",
  "description": "...",
  "examples": ["Placement fee: PHP 50,000", ...],
  "fires_on_test_corpus": 47
}
```

### 2.2 `rag_doc`

Re-digested into the BM25 + optional dense index.

```json
{
  "title": "POEA Memorandum Circular 14-2017",
  "jurisdiction": "PH",
  "doc_type": "regulation",
  "text": "<full text>",
  "source_url": "https://www.dmw.gov.ph/...",
  "fetched_at": "2026-05-12T18-00-00Z",
  "fetched_sha256": "ab12cd34...",
  "applicable_corridors": ["PH-HK", "PH-SG"]
}
```

### 2.3 `citation_edge`

Adds an edge to the 46-edge citation graph.

```json
{
  "from_statute": "POEA MC 14-2017",
  "to_statute": "ILO C189",
  "relation": "implements" | "supersedes" | "references" | "cites",
  "weight": 1.0,
  "evidence_quote": "..."
}
```

### 2.4 `fact_template`

Structured form rendered on the Anonymization and Sharing tab.

```json
{
  "template_id": "fee_violation_v1",
  "label": "Recruitment-fee violation",
  "applies_to_indicators": ["fee_camouflage", "fee_bondage"],
  "fields": [
    {"name": "corridor", "type": "string", "required": true,
     "enum": ["PH-HK", "PH-SG", "PH-UAE", "ID-HK", "NP-Gulf", "BD-Gulf"]},
    {"name": "fee_amount_raw", "type": "string", "required": true},
    {"name": "statute_violated", "type": "string", "required": true},
    {"name": "evidence_text", "type": "text", "required": false}
  ],
  "submission_schema_url": "https://duecare-ai.com/schema/fact/v1"
}
```

### 2.5 `context_snippet`

Reusable prompt-prepend text for specific corridors / indicators.

```json
{
  "snippet_id": "ph-hk-corridor-overview",
  "applies_to_corridors": ["PH-HK"],
  "applies_to_indicators": ["fee_camouflage", "passport_retention"],
  "text": "Filipino domestic workers bound for Hong Kong should pay zero placement fee under POEA MC 14-2017...",
  "max_tokens_when_prepended": 200
}
```

## 3. Persistence

Each KnowledgeObject lands at
`/kaggle/working/knowledge/<knowledge_object_type>/<id>.json` (local-dev
fallback: `./.duecare-knowledge/`). One file per object, indented JSON
for diff-ability.

## 4. APIs

| Verb | Path | Body | Returns |
|---|---|---|---|
| POST | `/api/knowledge/promote` | KnowledgeObject envelope | `{ok, id, type, written_to, envelope}` |
| GET | `/api/knowledge/list?type=<kind>?` | -- | `{objects: [...], n}` |
| GET | `/api/knowledge/export` | -- | ZIP (Content-Type: application/zip) |

## 5. Validation

`POST /api/knowledge/promote` rejects (HTTP 400) if:
- `schema_version` != `"1.0"`
- `knowledge_object_type` not in the 5-value enum
- `id` not kebab-case non-empty
- `content` not a JSON object

## 6. Round-trip example

1. User clicks Accept on a GREP rule candidate -> `POST /api/knowledge/promote`.
2. Tab refreshes the persisted set via `GET /api/knowledge/list`.
3. Reviewer downloads via `GET /api/knowledge/export`.
4. Next kernel boot (or the public hub) reads the ZIP and the rule
   is back in the harness.

One envelope, five payload types, three endpoints, one persistence
convention. No bespoke formats per artefact kind.
