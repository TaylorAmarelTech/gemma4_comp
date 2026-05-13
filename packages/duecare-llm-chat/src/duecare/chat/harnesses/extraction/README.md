# Knowledge Extraction harness

Paste raw text -> Gemma 4 drafts a typed KnowledgeObject envelope.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/knowledge/draft-envelope` | Gemma-drafted envelope from raw text |

## Request body

```json
{
  "raw_text": "string (required)",
  "target_type": "grep_rule | glossary_term | statute_citation | indicator | fact_template",
  "target_leaf": "alias for target_type (UI sends this)",
  "anonymize": false
}
```

## Files

- `handler.py` -- the route handler + light-anonymize helper
- `prompts.py` -- system prompt template
