# Search Safety Harness

The search safety harness runs before any public-source lookup. It strips
PII-like strings, optionally asks the loaded local model to rephrase the
query, and records the redaction/rephrase trace so the Search page can show
exactly what left the kernel.

## Endpoints

| Verb | Path | Purpose |
|---|---|---|
| POST | `/api/search/sanitize` | Redact PII and optionally rephrase a search query |
| GET | `/api/search/safety-info` | Report patterns, model availability, and safety mode |

## Knowledge Flow

Consumes `grep_rule` and `prompt_template` knowledge for redaction and
safe-rephrase behavior. Emits `audit_template` style trace rows through the
page activity log; it does not publish knowledge files by itself.
