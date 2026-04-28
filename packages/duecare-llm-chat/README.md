# duecare-llm-chat

Minimal **Gemma 4 chat playground**. Single FastAPI app + one chat
HTML page. No audit trail, no Duecare pipeline, no evidence DB,
no slideshow — just a clean chat UI bound to a Gemma 4 callable
that you supply at startup time.

Designed to pair with the Unsloth FastModel loader so it can serve
any Gemma 4 variant (E2B, E4B, 26B-A4B, 31B). Multimodal-capable:
the chat UI accepts image uploads which get inlined into the
Gemma message format.

## Public API

```python
from duecare.chat import create_app, run_server

# Pass a callable: (messages: list[dict], **gen_kwargs) -> str
def my_gemma_call(messages, max_new_tokens=512,
                    temperature=1.0, top_p=0.95, top_k=64):
    ...

app = create_app(gemma_call=my_gemma_call,
                   model_info={"name": "gemma-4-31b-it",
                                "size_b": 31.0,
                                "device": "balanced (2x T4)"})

# Or just one-shot:
run_server(gemma_call=my_gemma_call, port=8080)
```

## Routes

| Method | Path | Returns |
|---|---|---|
| GET | `/` | chat UI |
| POST | `/api/chat/send` | `{messages, generation}` -> `{response, elapsed_ms}` |
| POST | `/api/chat/upload-image` | image bytes -> `{path, mime}` (transient, in-memory) |
| GET | `/api/model-info` | `{name, size_b, quantization, device, display}` |
| GET | `/healthz` | `{ok: true, ts}` |

## Why a separate package

Bench-and-tune notebooks don't need it (they don't run a chat UI).
The full demo notebook already has Workbench / chat surfaces. This
package is for the third notebook (`taylorsamarel/duecare-gemma-chat`)
which is purely a Gemma 4 playground with no Duecare pipeline —
useful for letting people kick the tyres on 31B without touching
the moderation / safety surfaces.
