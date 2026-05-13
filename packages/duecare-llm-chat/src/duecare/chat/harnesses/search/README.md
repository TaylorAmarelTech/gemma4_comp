# Search harness

Server-automated + client-triggered web search across multiple backends.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/search/server` | server-automated (sentinel, batch enrichment) |
| POST | `/api/search/client` | user-triggered (chat "online" button) |
| GET | `/api/search/backends` | list available backends |

## Body shape (POST)

```json
{
  "query": "ILO C181 fee prohibition",
  "top_n": 5,
  "backend": "searxng",
  "anonymize_query": false
}
```

## Backends

| Name | Source | Config |
|---|---|---|
| `searxng` | Self-hosted SearXNG (preferred) | `DUECARE_SEARXNG_URL` env var |
| `legacy` | Existing `app.state.online_search_call` | Wired via `kernel_helpers.default_optional_hooks()` |

## Phase 12 — Gemma-guided orchestration (deferred)

`orchestrator.py` is a stub. Enabling needs `capabilities += ("multi_turn",)`,
per-step training-log emission, bounded retry budget, and optional
fine-tuned Gemma LoRA on search trajectories.
