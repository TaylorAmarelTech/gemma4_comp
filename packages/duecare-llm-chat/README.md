# duecare-llm-chat

DueCare reviewer workbench for Gemma 4 demos. The package serves the
FastAPI app, shared chrome, static workbench pages, harness contracts,
and local Gemma 4 integration used by the Kaggle kernels.

The workbench includes chat, model comparison, Bulk File Review,
Knowledge Extraction, Search, Templates, Anonymization & Sharing,
sync/status pages, replay artifacts, and sample bundles. It is designed
to pair with the Unsloth FastModel loader so it can serve any Gemma 4
variant (E2B, E4B, 26B-A4B, 31B) through the same app shell.

## Public API

```python
from duecare.chat import create_app, run_server

# Pass a callable: (messages: list[dict], **gen_kwargs) -> str
def my_gemma_call(messages, max_new_tokens=512,
                  temperature=1.0, top_p=0.95, top_k=64):
    ...

app = create_app(
    gemma_call=my_gemma_call,
    model_info={
        "name": "gemma-4-31b-it",
        "size_b": 31.0,
        "device": "balanced (2x T4)",
    },
)

# Or just one-shot:
run_server(gemma_call=my_gemma_call, port=8080)
```

## Routes

| Method | Path | Returns |
|---|---|---|
| GET | `/` | workbench chat UI |
| POST | `/api/chat/send` | `{messages, generation}` -> streamed chat response |
| POST | `/api/process/batch` | uploaded bundle -> Bulk File Review graph and brief |
| POST | `/api/knowledge/draft-envelope` | source text -> reviewable KnowledgeObject draft(s) |
| POST | `/api/search/client` | sanitized query -> public-source result cards |
| POST | `/api/search/verify-results` | result cards -> accepted/review/blocked verification envelope |
| POST | `/api/anonymize` | selected evidence -> redacted local sharing payload |
| GET | `/api/templates/list` | available complaint/referral templates |
| GET | `/api/model-info` | `{name, size_b, quantization, device, display}` |
| GET | `/healthz` | `{ok: true, ts}` |

## Why a separate package

The published Kaggle kernels install this package and open the shared
workbench through a Cloudflare tunnel. Keeping the routes, static pages,
sample artifacts, and model-loading chrome in this package lets the
notebook boot flow stay small while the reviewer-facing product can
continue to improve in source.
