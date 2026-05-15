# Knowledge Extraction harness

Upload a source bundle or paste compact source text -> reuse the Process
parser for local summaries -> auto-suggest useful KnowledgeObject leaves ->
Gemma 4 drafts typed envelopes when loaded -> a reviewer promotes useful
objects into the local knowledge store.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/knowledge/source-file` | Parse source files through the Process parser |
| POST | `/api/knowledge/draft-envelope` | Gemma or deterministic draft envelope from source text |
| POST | `/api/knowledge/promote` | Promote a reviewed draft to the local knowledge store |
| POST | `/api/knowledge/import` | Import a vetted knowledge-files ZIP |

## Request body

```json
{
  "raw_text": "string (required)",
  "target_type": "grep_rule | glossary_term | statute_citation | indicator | fact_template",
  "target_leaf": "alias for target_type (UI sends this)",
  "anonymize": false
}
```

## Prompt path

1. Infer target leaves from deterministic signals in the source text.
2. Compose GREP/RAG grounding from existing local knowledge.
3. Select `EXTRACTION_SYSTEM_PROMPT` plus the schema hint for the target type.
4. Ask Gemma for JSON-only `content` when a model is loaded.
5. Normalize and validate the draft envelope; otherwise return a deterministic
   skeleton marked `needs_review`.

Volatile facts such as phone numbers, regulator URLs, current statutes,
contact details, and media-derived claims should keep verification notes or
remain `needs_review`; they should not become hardcoded prompt text.

## Files

- `handler.py` -- the route handler + light-anonymize helper
- `prompts.py` -- system prompt template
- `__init__.py` -- `HarnessSpec` route, workflow, prompt-set, and model-fit contract
